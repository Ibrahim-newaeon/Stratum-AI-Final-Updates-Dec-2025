# =============================================================================
# Stratum AI - Base Platform Adapter
# =============================================================================
"""
Base Adapter Interface for Platform Integrations.

This module defines the abstract interface that all platform adapters must implement.
By defining a consistent interface, Stratum's core automation logic can work with
any advertising platform without knowing the specific API details.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Optional

from app.stratum.models import (
    AutomationAction,
    EMQScore,
    EntityStatus,
    PerformanceMetrics,
    Platform,
    UnifiedAccount,
    UnifiedAd,
    UnifiedAdSet,
    UnifiedCampaign,
    WebhookEvent,
)

logger = logging.getLogger("stratum.adapters")


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Each platform has different rate limits:
    - Meta: ~4800/hour calculated dynamically
    - Google: 10,000 operations per day
    - TikTok: 1000 requests per minute
    - Snapchat: 1000 requests per 5 minutes
    """

    def __init__(self, calls_per_minute: int = 60, burst_size: int = 10):
        """
        Initialize the rate limiter.

        Args:
            calls_per_minute: Maximum sustained rate
            burst_size: Maximum instant calls
        """
        self.calls_per_minute = calls_per_minute
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = datetime.now(UTC)
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a rate limit token is available."""
        async with self._lock:
            now = datetime.now(UTC)
            time_passed = (now - self.last_update).total_seconds()

            # Regenerate tokens
            self.tokens = min(
                self.burst_size, self.tokens + (time_passed * self.calls_per_minute / 60)
            )
            self.last_update = now

            # Wait if no tokens
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * 60 / self.calls_per_minute
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1


class BaseAdapter(ABC):
    """
    Abstract base class for all advertising platform adapters.

    Each platform adapter must implement these methods to enable
    bi-directional integration with Stratum's autopilot engine.

    Key Design Principles:
    1. Async by default: All methods are async for concurrency
    2. Unified models: All methods return Stratum's unified models
    3. Error handling: Raise specific exceptions for proper recovery
    4. Rate limiting: Built-in to prevent API quota exhaustion

    Usage:
        adapter = MetaAdapter(credentials)
        await adapter.initialize()

        # Pull data
        campaigns = await adapter.get_campaigns(account_id)
        metrics = await adapter.get_metrics(account_id, date_range)
        emq = await adapter.get_emq_scores(account_id)

        # Push changes
        action = AutomationAction(action_type="update_budget", ...)
        result = await adapter.execute_action(action)

        await adapter.cleanup()
    """

    def __init__(self, credentials: dict[str, str]):
        """
        Initialize the adapter with platform credentials.

        Args:
            credentials: Platform-specific authentication credentials
        """
        self.credentials = credentials
        self.rate_limiter = RateLimiter()
        self._initialized = False

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform identifier for this adapter."""
        pass

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the adapter and validate credentials.

        Should:
        1. Validate required credentials
        2. Initialize the platform SDK/client
        3. Make a test API call to verify authentication
        4. Set up persistent connections
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up adapter resources."""
        pass

    async def health_check(self) -> bool:
        """Verify the adapter can communicate with the platform."""
        try:
            accounts = await self.get_accounts()
            return len(accounts) > 0
        except Exception as e:
            logger.error(f"{self.platform.value} health check failed: {e}")
            return False

    # ========================================================================
    # READ OPERATIONS
    # ========================================================================

    @abstractmethod
    async def get_accounts(self) -> list[UnifiedAccount]:
        """Get all accessible advertising accounts."""
        pass

    @abstractmethod
    async def get_campaigns(
        self, account_id: str, status_filter: Optional[list[EntityStatus]] = None
    ) -> list[UnifiedCampaign]:
        """Get campaigns, optionally filtered by status."""
        pass

    @abstractmethod
    async def get_adsets(
        self, account_id: str, campaign_id: Optional[str] = None
    ) -> list[UnifiedAdSet]:
        """Get ad sets, optionally filtered to a campaign."""
        pass

    @abstractmethod
    async def get_ads(self, account_id: str, adset_id: Optional[str] = None) -> list[UnifiedAd]:
        """Get ads, optionally filtered to an ad set."""
        pass

    @abstractmethod
    async def get_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        date_start: datetime,
        date_end: datetime,
        breakdown: Optional[str] = None,
    ) -> dict[str, PerformanceMetrics]:
        """Get performance metrics for entities."""
        pass

    @abstractmethod
    async def get_emq_scores(self, account_id: str) -> list[EMQScore]:
        """Get Event Match Quality scores."""
        pass

    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================

    @abstractmethod
    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        """Execute an automation action on the platform."""
        pass

    async def execute_actions_batch(
        self, actions: list[AutomationAction]
    ) -> list[AutomationAction]:
        """Execute multiple actions efficiently."""
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
        return results

    # ========================================================================
    # CREATIVE OPERATIONS
    # ========================================================================

    @abstractmethod
    async def upload_image(self, account_id: str, image_data: bytes, filename: str) -> str:
        """Upload an image and return the platform image ID."""
        pass

    @abstractmethod
    async def upload_video(self, account_id: str, video_data: bytes, filename: str) -> str:
        """Upload a video and return the platform video ID."""
        pass

    # ========================================================================
    # WEBHOOK OPERATIONS
    # ========================================================================

    async def setup_webhooks(self, callback_url: str, event_types: list[str]) -> bool:
        """Register webhook subscriptions (if supported)."""
        logger.info(f"{self.platform.value} webhooks not implemented")
        return False

    async def process_webhook(self, payload: dict[str, Any]) -> WebhookEvent:
        """Process an incoming webhook payload."""
        return WebhookEvent(platform=self.platform, event_type="unknown", payload=payload)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _map_status_to_platform(self, status: EntityStatus) -> str:
        """Convert unified status to platform-specific status."""
        raise NotImplementedError("Subclass must implement")

    def _map_status_from_platform(self, platform_status: str) -> EntityStatus:
        """Convert platform-specific status to unified status."""
        raise NotImplementedError("Subclass must implement")


# =============================================================================
# Exceptions
# =============================================================================


class AdapterError(Exception):
    """Base exception for adapter errors."""

    pass


class AuthenticationError(AdapterError):
    """Raised when API authentication fails."""

    pass


class RateLimitError(AdapterError):
    """Raised when API rate limit is exceeded."""

    pass


class ValidationError(AdapterError):
    """Raised when input validation fails."""

    pass


class PlatformError(AdapterError):
    """Raised when the platform returns an error."""

    def __init__(self, message: str, platform_code: Optional[str] = None):
        super().__init__(message)
        self.platform_code = platform_code
