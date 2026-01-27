# =============================================================================
# Stratum AI - OAuth Base Service
# =============================================================================
"""
Abstract base class for OAuth services.
Defines the interface that all platform OAuth implementations must follow.
"""

import json
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
from urllib.parse import urlencode

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_pii, encrypt_pii

logger = get_logger(__name__)

# Redis key prefixes for OAuth state
OAUTH_STATE_PREFIX = "oauth_state:"
OAUTH_STATE_EXPIRY = 600  # 10 minutes


@dataclass
class OAuthState:
    """OAuth state for CSRF protection and session tracking."""

    state_token: str
    tenant_id: int
    user_id: int
    platform: str
    redirect_uri: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        """Serialize to JSON for Redis storage."""
        return json.dumps(
            {
                "state_token": self.state_token,
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "platform": self.platform,
                "redirect_uri": self.redirect_uri,
                "created_at": self.created_at.isoformat(),
            }
        )

    @classmethod
    def from_json(cls, data: str) -> "OAuthState":
        """Deserialize from JSON."""
        parsed = json.loads(data)
        return cls(
            state_token=parsed["state_token"],
            tenant_id=parsed["tenant_id"],
            user_id=parsed["user_id"],
            platform=parsed["platform"],
            redirect_uri=parsed["redirect_uri"],
            created_at=datetime.fromisoformat(parsed["created_at"]),
        )


@dataclass
class OAuthTokens:
    """OAuth tokens returned from token exchange."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None  # Seconds until expiration
    expires_at: Optional[datetime] = None
    scopes: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at


@dataclass
class AdAccountInfo:
    """Information about an ad account from the platform."""

    account_id: str  # Platform's account ID (e.g., act_123456789)
    name: str
    business_name: Optional[str] = None
    currency: str = "USD"
    timezone: str = "UTC"
    status: str = "active"
    spend_cap: Optional[float] = None
    amount_spent: Optional[float] = None
    permissions: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


class OAuthService(ABC):
    """
    Abstract base class for OAuth services.

    Each platform implementation must provide:
    - get_authorization_url: Generate OAuth authorization URL
    - exchange_code_for_tokens: Exchange authorization code for tokens
    - refresh_access_token: Refresh expired access token
    - fetch_ad_accounts: List available ad accounts
    - revoke_access: Revoke OAuth access
    """

    platform: str = "base"

    def __init__(self) -> None:
        self.logger = get_logger(f"{__name__}.{self.platform}")

    # =========================================================================
    # State Management (Redis-based)
    # =========================================================================

    async def _get_redis_client(self) -> redis.Redis:
        """Get Redis client for state storage."""
        return redis.from_url(settings.redis_url, decode_responses=True)

    async def create_state(
        self,
        tenant_id: int,
        user_id: int,
        redirect_uri: str,
    ) -> OAuthState:
        """
        Create and store OAuth state for CSRF protection.

        Args:
            tenant_id: Tenant initiating OAuth
            user_id: User initiating OAuth
            redirect_uri: Where to redirect after OAuth

        Returns:
            OAuthState with unique state token
        """
        state_token = secrets.token_urlsafe(32)

        state = OAuthState(
            state_token=state_token,
            tenant_id=tenant_id,
            user_id=user_id,
            platform=self.platform,
            redirect_uri=redirect_uri,
        )

        try:
            client = await self._get_redis_client()
            key = f"{OAUTH_STATE_PREFIX}{state_token}"
            await client.setex(key, OAUTH_STATE_EXPIRY, state.to_json())
            await client.close()
        except Exception as e:
            self.logger.error("Failed to store OAuth state", error=str(e))
            raise

        return state

    async def validate_state(self, state_token: str) -> Optional[OAuthState]:
        """
        Validate and consume OAuth state token.

        Args:
            state_token: State token from OAuth callback

        Returns:
            OAuthState if valid, None if invalid or expired
        """
        try:
            client = await self._get_redis_client()
            key = f"{OAUTH_STATE_PREFIX}{state_token}"

            data = await client.get(key)
            if not data:
                await client.close()
                return None

            # Delete state (single use)
            await client.delete(key)
            await client.close()

            state = OAuthState.from_json(data)

            # Verify platform matches
            if state.platform != self.platform:
                self.logger.warning(
                    "State platform mismatch",
                    expected=self.platform,
                    got=state.platform,
                )
                return None

            return state

        except Exception as e:
            self.logger.error("Failed to validate OAuth state", error=str(e))
            return None

    # =========================================================================
    # Token Encryption
    # =========================================================================

    def encrypt_token(self, token: str) -> str:
        """Encrypt token for storage."""
        return encrypt_pii(token)

    def decrypt_token(self, encrypted: str) -> str:
        """Decrypt token from storage."""
        return decrypt_pii(encrypted)

    # =========================================================================
    # Abstract Methods (Platform-specific)
    # =========================================================================

    @abstractmethod
    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: OAuth state for CSRF protection
            scopes: Optional list of scopes to request

        Returns:
            Authorization URL to redirect user to
        """
        pass

    @abstractmethod
    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization request

        Returns:
            OAuthTokens with access and refresh tokens
        """
        pass

    @abstractmethod
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh expired access token.

        Args:
            refresh_token: Refresh token from previous token exchange

        Returns:
            New OAuthTokens with refreshed access token
        """
        pass

    @abstractmethod
    async def fetch_ad_accounts(
        self,
        access_token: str,
    ) -> list[AdAccountInfo]:
        """
        Fetch available ad accounts for the authenticated user.

        Args:
            access_token: Valid access token

        Returns:
            List of AdAccountInfo for available accounts
        """
        pass

    @abstractmethod
    async def revoke_access(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke OAuth access.

        Args:
            access_token: Token to revoke

        Returns:
            True if revocation successful
        """
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_redirect_uri(self) -> str:
        """Get the OAuth callback redirect URI for this platform."""
        base_url = settings.oauth_redirect_base_url.rstrip("/")
        return f"{base_url}/api/v1/oauth/{self.platform}/callback"

    def build_url(self, base_url: str, params: dict[str, Any]) -> str:
        """Build URL with query parameters."""
        # Filter out None values
        filtered_params = {k: v for k, v in params.items() if v is not None}
        if filtered_params:
            return f"{base_url}?{urlencode(filtered_params)}"
        return base_url
