# =============================================================================
# Stratum AI - Base Audience Connector
# =============================================================================
"""
Abstract base class for platform-specific audience connectors.

All platform connectors (Meta, Google, TikTok, Snapchat) inherit from this base
and implement platform-specific API calls.
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import structlog

logger = structlog.get_logger()


# =============================================================================
# Data Classes
# =============================================================================

class IdentifierType(str, Enum):
    """Supported identifier types for audience matching."""
    EMAIL = "email"
    PHONE = "phone"
    MOBILE_ADVERTISER_ID = "mobile_id"  # IDFA/GAID
    EXTERNAL_ID = "external_id"


@dataclass
class UserIdentifier:
    """
    Represents a user identifier for audience matching.
    Identifiers are hashed before sending to platforms.
    """
    identifier_type: IdentifierType
    raw_value: Optional[str] = None
    hashed_value: Optional[str] = None

    def get_hashed(self) -> Optional[str]:
        """Get SHA256 hash of identifier."""
        if self.hashed_value:
            return self.hashed_value
        if self.raw_value:
            # Normalize and hash
            normalized = self._normalize(self.raw_value)
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        return None

    def _normalize(self, value: str) -> str:
        """Normalize identifier value before hashing."""
        value = value.strip().lower()
        if self.identifier_type == IdentifierType.EMAIL:
            # Remove dots from gmail addresses (optional)
            return value
        if self.identifier_type == IdentifierType.PHONE:
            # Remove non-digit characters
            return ''.join(c for c in value if c.isdigit() or c == '+')
        return value


@dataclass
class AudienceUser:
    """
    Represents a user to be added/removed from an audience.
    Contains all available identifiers for matching.
    """
    profile_id: str
    identifiers: List[UserIdentifier] = field(default_factory=list)

    # Optional additional data for enhanced matching
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYYMMDD
    gender: Optional[str] = None  # m/f


@dataclass
class AudienceSyncResult:
    """
    Result of an audience sync operation.
    """
    success: bool
    operation: str  # create, update, delete

    # Platform response
    platform_audience_id: Optional[str] = None
    platform_audience_name: Optional[str] = None

    # Metrics
    users_sent: int = 0
    users_added: int = 0
    users_removed: int = 0
    users_failed: int = 0

    # Size information
    audience_size: Optional[int] = None
    matched_size: Optional[int] = None
    match_rate: Optional[float] = None

    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)

    # Raw platform response
    platform_response: Dict[str, Any] = field(default_factory=dict)

    # Timing
    duration_ms: int = 0


@dataclass
class AudienceConfig:
    """
    Configuration for creating/updating an audience on a platform.
    """
    name: str
    description: Optional[str] = None

    # Platform-specific settings
    customer_file_source: Optional[str] = None  # Meta: USER_PROVIDED_ONLY, etc.
    audience_type: str = "customer_list"

    # Retention settings
    retention_days: Optional[int] = None

    # Additional platform-specific config
    extra_config: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Base Connector Class
# =============================================================================

class BaseAudienceConnector(ABC):
    """
    Abstract base class for platform audience connectors.

    Each platform connector must implement:
    - create_audience: Create a new custom audience
    - add_users: Add users to an existing audience
    - remove_users: Remove users from an audience
    - delete_audience: Delete an audience
    - get_audience_info: Get audience metadata/size
    """

    PLATFORM_NAME: str = "unknown"
    BATCH_SIZE: int = 10000  # Default batch size for uploads

    def __init__(
        self,
        access_token: str,
        ad_account_id: str,
        **kwargs
    ):
        self.access_token = access_token
        self.ad_account_id = ad_account_id
        self.logger = logger.bind(
            platform=self.PLATFORM_NAME,
            ad_account_id=ad_account_id,
        )

    @abstractmethod
    async def create_audience(
        self,
        config: AudienceConfig,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Create a new custom audience with initial users.

        Args:
            config: Audience configuration
            users: Initial users to add

        Returns:
            AudienceSyncResult with platform audience ID
        """
        pass

    @abstractmethod
    async def add_users(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Add users to an existing audience.

        Args:
            audience_id: Platform audience ID
            users: Users to add

        Returns:
            AudienceSyncResult with add metrics
        """
        pass

    @abstractmethod
    async def remove_users(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Remove users from an audience.

        Args:
            audience_id: Platform audience ID
            users: Users to remove

        Returns:
            AudienceSyncResult with removal metrics
        """
        pass

    @abstractmethod
    async def replace_audience(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Replace entire audience with new user list.

        Args:
            audience_id: Platform audience ID
            users: Complete list of users (replaces existing)

        Returns:
            AudienceSyncResult
        """
        pass

    @abstractmethod
    async def delete_audience(
        self,
        audience_id: str,
    ) -> AudienceSyncResult:
        """
        Delete an audience from the platform.

        Args:
            audience_id: Platform audience ID

        Returns:
            AudienceSyncResult
        """
        pass

    @abstractmethod
    async def get_audience_info(
        self,
        audience_id: str,
    ) -> Dict[str, Any]:
        """
        Get audience information including size and status.

        Args:
            audience_id: Platform audience ID

        Returns:
            Dict with audience metadata
        """
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _hash_identifier(self, value: str, identifier_type: IdentifierType) -> str:
        """Hash an identifier value using SHA256."""
        normalized = self._normalize_identifier(value, identifier_type)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _normalize_identifier(self, value: str, identifier_type: IdentifierType) -> str:
        """Normalize identifier before hashing (platform-specific)."""
        value = value.strip().lower()
        if identifier_type == IdentifierType.PHONE:
            # Remove non-digit characters except +
            return ''.join(c for c in value if c.isdigit() or c == '+')
        return value

    def _prepare_users_for_upload(
        self,
        users: List[AudienceUser],
    ) -> List[Dict[str, Any]]:
        """
        Prepare user data for upload (platform-specific format).
        Override in subclasses for platform-specific formatting.
        """
        prepared = []
        for user in users:
            user_data = {}
            for identifier in user.identifiers:
                hashed = identifier.get_hashed()
                if hashed:
                    user_data[identifier.identifier_type.value] = hashed
            if user_data:
                prepared.append(user_data)
        return prepared

    def _chunk_list(self, lst: List, chunk_size: int) -> List[List]:
        """Split a list into chunks of specified size."""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
