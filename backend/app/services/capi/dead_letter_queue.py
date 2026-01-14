# =============================================================================
# Stratum AI - Dead Letter Queue for Failed Events (P0 Gap Fix)
# =============================================================================
"""
Dead Letter Queue (DLQ) implementation for CAPI event failures.

Fixes the P0 gap: Failed events are lost after max retries with no way
to investigate or replay them.

Features:
- Persistent storage of failed events in database
- Redis queue for fast access and retry scheduling
- Configurable retention period
- Replay capability for manual/automated recovery
- Detailed failure context for debugging
- Metrics and alerting hooks
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from uuid import uuid4
from enum import Enum

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


from app.core.config import settings

logger = logging.getLogger(__name__)


class DLQStatus(str, Enum):
    """Status of a DLQ entry."""
    PENDING = "pending"          # Waiting for retry
    RETRYING = "retrying"        # Currently being retried
    RECOVERED = "recovered"      # Successfully replayed
    EXPIRED = "expired"          # Past retention period
    DISCARDED = "discarded"      # Manually discarded


class FailureReason(str, Enum):
    """Categorized failure reasons."""
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    VALIDATION_ERROR = "validation_error"
    PLATFORM_ERROR = "platform_error"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"
    UNKNOWN = "unknown"


@dataclass
class DLQEntry:
    """
    Dead Letter Queue entry for a failed event.
    """
    id: str
    tenant_id: int
    platform: str
    event_name: str
    event_id: Optional[str]
    event_data: Dict[str, Any]
    failure_reason: str
    failure_category: FailureReason
    error_message: str
    retry_count: int
    max_retries: int
    first_failure_at: datetime
    last_failure_at: datetime
    status: DLQStatus = DLQStatus.PENDING
    platform_response: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    recovered_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["first_failure_at"] = self.first_failure_at.isoformat()
        data["last_failure_at"] = self.last_failure_at.isoformat()
        data["status"] = self.status.value
        data["failure_category"] = self.failure_category.value
        if self.recovered_at:
            data["recovered_at"] = self.recovered_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DLQEntry":
        """Create from dictionary."""
        data["first_failure_at"] = datetime.fromisoformat(data["first_failure_at"])
        data["last_failure_at"] = datetime.fromisoformat(data["last_failure_at"])
        data["status"] = DLQStatus(data["status"])
        data["failure_category"] = FailureReason(data["failure_category"])
        if data.get("recovered_at"):
            data["recovered_at"] = datetime.fromisoformat(data["recovered_at"])
        return cls(**data)


@dataclass
class DLQStats:
    """Statistics for the Dead Letter Queue."""
    total_entries: int = 0
    pending: int = 0
    retrying: int = 0
    recovered: int = 0
    expired: int = 0
    discarded: int = 0
    by_platform: Dict[str, int] = field(default_factory=dict)
    by_failure_category: Dict[str, int] = field(default_factory=dict)
    oldest_entry_age_hours: float = 0.0
    recovery_rate_pct: float = 0.0


class DeadLetterQueue:
    """
    Dead Letter Queue for failed CAPI events.

    Stores failed events for investigation and retry.
    Uses Redis for queue management and optionally database for persistence.
    """

    # Redis key prefixes
    QUEUE_KEY = "stratum:dlq:queue"
    ENTRY_PREFIX = "stratum:dlq:entry:"
    STATS_KEY = "stratum:dlq:stats"

    # Default retention period (7 days)
    DEFAULT_RETENTION_DAYS = 7

    # Maximum entries to keep in memory if Redis unavailable
    MAX_MEMORY_ENTRIES = 10000

    def __init__(
        self,
        redis_url: Optional[str] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        """
        Initialize the Dead Letter Queue.

        Args:
            redis_url: Redis connection URL
            retention_days: How long to retain failed events
        """
        self._redis_url = redis_url or settings.redis_url
        self._retention_days = retention_days
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False

        # In-memory fallback
        self._memory_queue: List[DLQEntry] = []

        # Statistics
        self._stats = DLQStats()

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available for DLQ, using in-memory fallback")
            return False

        try:
            self._redis = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Dead Letter Queue connected to Redis")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect DLQ to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False

    def _categorize_failure(self, error_message: str, platform_response: Optional[Dict] = None) -> FailureReason:
        """
        Categorize the failure reason from error message.

        Args:
            error_message: The error message string
            platform_response: Optional platform API response

        Returns:
            Categorized FailureReason
        """
        error_lower = error_message.lower()

        if any(term in error_lower for term in ["timeout", "timed out"]):
            return FailureReason.TIMEOUT

        if any(term in error_lower for term in ["rate limit", "too many requests", "429"]):
            return FailureReason.RATE_LIMITED

        if any(term in error_lower for term in ["auth", "unauthorized", "forbidden", "401", "403", "token"]):
            return FailureReason.AUTH_ERROR

        if any(term in error_lower for term in ["connection", "network", "dns", "socket"]):
            return FailureReason.NETWORK_ERROR

        if any(term in error_lower for term in ["circuit", "breaker", "open"]):
            return FailureReason.CIRCUIT_OPEN

        if any(term in error_lower for term in ["validation", "invalid", "missing", "required"]):
            return FailureReason.VALIDATION_ERROR

        if platform_response and platform_response.get("error"):
            return FailureReason.PLATFORM_ERROR

        return FailureReason.UNKNOWN

    async def add_failed_event(
        self,
        tenant_id: int,
        platform: str,
        event_name: str,
        event_data: Dict[str, Any],
        error_message: str,
        retry_count: int = 0,
        max_retries: int = 3,
        platform_response: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DLQEntry:
        """
        Add a failed event to the Dead Letter Queue.

        Args:
            tenant_id: Tenant ID
            platform: Platform name (meta, google, etc.)
            event_name: Event name (Purchase, Lead, etc.)
            event_data: Full event data
            error_message: Error message from failure
            retry_count: Number of retries attempted
            max_retries: Maximum retries configured
            platform_response: Optional platform API response
            context: Optional additional context

        Returns:
            Created DLQEntry
        """
        now = datetime.now(timezone.utc)

        entry = DLQEntry(
            id=str(uuid4()),
            tenant_id=tenant_id,
            platform=platform,
            event_name=event_name,
            event_id=event_data.get("event_id"),
            event_data=event_data,
            failure_reason=error_message,
            failure_category=self._categorize_failure(error_message, platform_response),
            error_message=error_message,
            retry_count=retry_count,
            max_retries=max_retries,
            first_failure_at=now,
            last_failure_at=now,
            status=DLQStatus.PENDING,
            platform_response=platform_response,
            context=context,
        )

        await self._store_entry(entry)

        logger.warning(
            f"DLQ: Added failed event {entry.id} | "
            f"platform={platform} event={event_name} "
            f"category={entry.failure_category.value} "
            f"retries={retry_count}/{max_retries}"
        )

        return entry

    async def _store_entry(self, entry: DLQEntry):
        """Store entry in Redis or memory."""
        if self._connected and self._redis:
            try:
                # Store entry data
                entry_key = f"{self.ENTRY_PREFIX}{entry.id}"
                await self._redis.set(
                    entry_key,
                    json.dumps(entry.to_dict()),
                    ex=self._retention_days * 86400,  # TTL in seconds
                )

                # Add to sorted set for ordering (score = timestamp)
                await self._redis.zadd(
                    self.QUEUE_KEY,
                    {entry.id: entry.last_failure_at.timestamp()},
                )

                return
            except Exception as e:
                logger.warning(f"Failed to store DLQ entry in Redis: {e}")

        # Fallback to memory
        self._memory_queue.append(entry)

        # Trim if too large
        if len(self._memory_queue) > self.MAX_MEMORY_ENTRIES:
            self._memory_queue = self._memory_queue[-self.MAX_MEMORY_ENTRIES:]

    async def get_entry(self, entry_id: str) -> Optional[DLQEntry]:
        """
        Get a specific DLQ entry.

        Args:
            entry_id: Entry UUID

        Returns:
            DLQEntry if found, None otherwise
        """
        if self._connected and self._redis:
            try:
                entry_key = f"{self.ENTRY_PREFIX}{entry_id}"
                data = await self._redis.get(entry_key)
                if data:
                    return DLQEntry.from_dict(json.loads(data))
            except Exception as e:
                logger.warning(f"Failed to get DLQ entry from Redis: {e}")

        # Check memory
        for entry in self._memory_queue:
            if entry.id == entry_id:
                return entry

        return None

    async def get_pending_entries(
        self,
        platform: Optional[str] = None,
        tenant_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DLQEntry]:
        """
        Get pending DLQ entries for retry.

        Args:
            platform: Filter by platform
            tenant_id: Filter by tenant
            limit: Maximum entries to return
            offset: Offset for pagination

        Returns:
            List of pending DLQEntry objects
        """
        entries = []

        if self._connected and self._redis:
            try:
                # Get entry IDs from sorted set
                entry_ids = await self._redis.zrange(
                    self.QUEUE_KEY,
                    offset,
                    offset + limit - 1,
                )

                for entry_id in entry_ids:
                    entry = await self.get_entry(entry_id)
                    if entry and entry.status == DLQStatus.PENDING:
                        if platform and entry.platform != platform:
                            continue
                        if tenant_id and entry.tenant_id != tenant_id:
                            continue
                        entries.append(entry)

                return entries
            except Exception as e:
                logger.warning(f"Failed to get pending DLQ entries from Redis: {e}")

        # Fallback to memory
        filtered = [
            e for e in self._memory_queue
            if e.status == DLQStatus.PENDING
            and (platform is None or e.platform == platform)
            and (tenant_id is None or e.tenant_id == tenant_id)
        ]
        return filtered[offset:offset + limit]

    async def mark_recovered(self, entry_id: str) -> bool:
        """
        Mark an entry as successfully recovered.

        Args:
            entry_id: Entry UUID

        Returns:
            True if updated, False otherwise
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return False

        entry.status = DLQStatus.RECOVERED
        entry.recovered_at = datetime.now(timezone.utc)

        await self._store_entry(entry)
        logger.info(f"DLQ: Entry {entry_id} marked as recovered")
        return True

    async def mark_discarded(self, entry_id: str, reason: str = "") -> bool:
        """
        Mark an entry as discarded (will not retry).

        Args:
            entry_id: Entry UUID
            reason: Reason for discarding

        Returns:
            True if updated, False otherwise
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return False

        entry.status = DLQStatus.DISCARDED
        if reason:
            entry.context = entry.context or {}
            entry.context["discard_reason"] = reason

        await self._store_entry(entry)
        logger.info(f"DLQ: Entry {entry_id} discarded - {reason}")
        return True

    async def update_retry(self, entry_id: str, error_message: str) -> bool:
        """
        Update an entry after a retry attempt.

        Args:
            entry_id: Entry UUID
            error_message: New error message from retry

        Returns:
            True if updated, False otherwise
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return False

        entry.retry_count += 1
        entry.last_failure_at = datetime.now(timezone.utc)
        entry.error_message = error_message
        entry.status = DLQStatus.PENDING

        await self._store_entry(entry)
        return True

    async def get_stats(self) -> DLQStats:
        """
        Get DLQ statistics.

        Returns:
            DLQStats object with current statistics
        """
        stats = DLQStats()

        entries = []

        if self._connected and self._redis:
            try:
                entry_ids = await self._redis.zrange(self.QUEUE_KEY, 0, -1)
                for entry_id in entry_ids:
                    entry = await self.get_entry(entry_id)
                    if entry:
                        entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to get DLQ stats from Redis: {e}")
                entries = self._memory_queue
        else:
            entries = self._memory_queue

        stats.total_entries = len(entries)

        for entry in entries:
            # By status
            if entry.status == DLQStatus.PENDING:
                stats.pending += 1
            elif entry.status == DLQStatus.RETRYING:
                stats.retrying += 1
            elif entry.status == DLQStatus.RECOVERED:
                stats.recovered += 1
            elif entry.status == DLQStatus.EXPIRED:
                stats.expired += 1
            elif entry.status == DLQStatus.DISCARDED:
                stats.discarded += 1

            # By platform
            stats.by_platform[entry.platform] = stats.by_platform.get(entry.platform, 0) + 1

            # By failure category
            category = entry.failure_category.value
            stats.by_failure_category[category] = stats.by_failure_category.get(category, 0) + 1

        # Calculate oldest entry age
        if entries:
            oldest = min(entries, key=lambda e: e.first_failure_at)
            age = datetime.now(timezone.utc) - oldest.first_failure_at
            stats.oldest_entry_age_hours = age.total_seconds() / 3600

        # Calculate recovery rate
        total_processed = stats.recovered + stats.discarded + stats.expired
        if total_processed > 0:
            stats.recovery_rate_pct = (stats.recovered / total_processed) * 100

        return stats

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        removed = 0

        if self._connected and self._redis:
            try:
                # Get entries older than cutoff
                entry_ids = await self._redis.zrangebyscore(
                    self.QUEUE_KEY,
                    "-inf",
                    cutoff.timestamp(),
                )

                for entry_id in entry_ids:
                    entry = await self.get_entry(entry_id)
                    if entry and entry.status == DLQStatus.PENDING:
                        entry.status = DLQStatus.EXPIRED
                        await self._store_entry(entry)

                    # Remove from queue
                    await self._redis.zrem(self.QUEUE_KEY, entry_id)
                    removed += 1

                return removed
            except Exception as e:
                logger.warning(f"Failed to cleanup expired DLQ entries: {e}")

        # Fallback to memory cleanup
        original_len = len(self._memory_queue)
        self._memory_queue = [
            e for e in self._memory_queue
            if e.first_failure_at > cutoff or e.status in [DLQStatus.RECOVERED, DLQStatus.DISCARDED]
        ]
        removed = original_len - len(self._memory_queue)

        return removed

    async def replay_event(self, entry_id: str) -> Dict[str, Any]:
        """
        Prepare an event for replay.

        Args:
            entry_id: Entry UUID

        Returns:
            Event data ready for re-sending
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            raise ValueError(f"DLQ entry not found: {entry_id}")

        # Mark as retrying
        entry.status = DLQStatus.RETRYING
        await self._store_entry(entry)

        return {
            "dlq_entry_id": entry.id,
            "tenant_id": entry.tenant_id,
            "platform": entry.platform,
            "event_data": entry.event_data,
            "original_retry_count": entry.retry_count,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the DLQ.

        Returns:
            Health status dictionary
        """
        stats = await self.get_stats()

        health = {
            "status": "healthy",
            "redis_connected": self._connected,
            "mode": "redis" if self._connected else "memory",
            "pending_count": stats.pending,
            "total_entries": stats.total_entries,
        }

        # Warning thresholds
        if stats.pending > 1000:
            health["status"] = "warning"
            health["warning"] = f"High pending count: {stats.pending}"

        if stats.oldest_entry_age_hours > 24:
            health["status"] = "warning"
            health["warning"] = f"Old entries: {stats.oldest_entry_age_hours:.1f} hours"

        return health


# =============================================================================
# Singleton Instance
# =============================================================================

# Global DLQ instance
dead_letter_queue = DeadLetterQueue()


async def get_dlq() -> DeadLetterQueue:
    """
    Get the DLQ instance, ensuring connection.

    Returns:
        Connected DeadLetterQueue instance.
    """
    if not dead_letter_queue._connected:
        await dead_letter_queue.connect()
    return dead_letter_queue
