# =============================================================================
# Stratum AI - Distributed Event Deduplication (P0 Gap Fix)
# =============================================================================
"""
Redis-backed distributed deduplication for CAPI events.

Fixes the P0 gap: In-memory dedupe loses state on restart and doesn't
work across multiple worker processes.

Features:
- Redis-backed shared state across all workers
- 24-hour TTL with automatic expiration
- Fallback to in-memory if Redis unavailable
- Atomic operations for thread safety
- Metrics tracking for monitoring
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import json

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DedupeStats:
    """Statistics for deduplication performance."""
    total_checks: int = 0
    duplicates_found: int = 0
    unique_events: int = 0
    redis_hits: int = 0
    redis_misses: int = 0
    fallback_to_memory: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def duplicate_rate(self) -> float:
        """Calculate duplicate rate percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.duplicates_found / self.total_checks) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "total_checks": self.total_checks,
            "duplicates_found": self.duplicates_found,
            "unique_events": self.unique_events,
            "duplicate_rate_pct": round(self.duplicate_rate, 2),
            "redis_hits": self.redis_hits,
            "redis_misses": self.redis_misses,
            "fallback_to_memory": self.fallback_to_memory,
            "last_reset": self.last_reset.isoformat(),
        }


class DistributedEventDeduplicator:
    """
    Redis-backed distributed event deduplicator.

    Provides cross-process deduplication using Redis as shared state.
    Falls back to in-memory deduplication if Redis is unavailable.
    """

    # Redis key prefix for dedupe keys
    KEY_PREFIX = "stratum:dedupe:event:"

    # Default TTL in seconds (24 hours)
    DEFAULT_TTL_SECONDS = 86400

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        key_prefix: str = KEY_PREFIX,
    ):
        """
        Initialize the distributed deduplicator.

        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
            ttl_seconds: Time-to-live for dedupe keys in seconds
            key_prefix: Prefix for Redis keys
        """
        self._redis_url = redis_url or settings.redis_url
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False

        # In-memory fallback
        self._memory_cache: Dict[str, datetime] = {}
        self._memory_max_size = 100000

        # Statistics
        self._stats = DedupeStats()

        # Connection state
        self._connection_attempts = 0
        self._last_connection_attempt: Optional[datetime] = None

    async def connect(self) -> bool:
        """
        Establish connection to Redis.

        Returns:
            True if connected successfully, False otherwise.
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, using in-memory fallback")
            return False

        try:
            self._redis = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            self._connection_attempts = 0
            logger.info("Distributed deduplicator connected to Redis")
            return True

        except Exception as e:
            self._connection_attempts += 1
            self._last_connection_attempt = datetime.now(timezone.utc)
            logger.warning(f"Failed to connect to Redis (attempt {self._connection_attempts}): {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False
            logger.info("Distributed deduplicator disconnected from Redis")

    async def is_duplicate(self, event: Dict[str, Any], platform: str = "") -> bool:
        """
        Check if an event is a duplicate.

        Args:
            event: Event data dictionary
            platform: Platform identifier (meta, google, etc.)

        Returns:
            True if event is a duplicate, False otherwise.
        """
        self._stats.total_checks += 1
        event_key = self._generate_key(event, platform)
        full_key = f"{self._key_prefix}{event_key}"

        # Try Redis first
        if self._connected and self._redis:
            try:
                # Use SETNX (SET if Not eXists) with TTL for atomic check-and-set
                result = await self._redis.set(
                    full_key,
                    datetime.now(timezone.utc).isoformat(),
                    nx=True,  # Only set if not exists
                    ex=self._ttl_seconds,  # Expiration in seconds
                )

                if result is None:
                    # Key already existed - duplicate
                    self._stats.duplicates_found += 1
                    self._stats.redis_hits += 1
                    logger.debug(f"Duplicate event detected (Redis): {event_key[:20]}...")
                    return True
                else:
                    # Key was set - unique event
                    self._stats.unique_events += 1
                    self._stats.redis_misses += 1
                    return False

            except Exception as e:
                logger.warning(f"Redis error during dedupe check: {e}")
                self._connected = False
                self._stats.fallback_to_memory += 1
                # Fall through to memory check

        # Fallback to in-memory
        return self._check_memory(event_key)

    def _check_memory(self, event_key: str) -> bool:
        """
        In-memory deduplication fallback.

        Args:
            event_key: Generated event key

        Returns:
            True if duplicate, False otherwise.
        """
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self._ttl_seconds)

        # Cleanup expired entries periodically
        if len(self._memory_cache) > self._memory_max_size // 2:
            self._cleanup_memory()

        if event_key in self._memory_cache:
            if now - self._memory_cache[event_key] < ttl:
                self._stats.duplicates_found += 1
                return True
            # Expired, remove and allow
            del self._memory_cache[event_key]

        # Add to cache
        if len(self._memory_cache) < self._memory_max_size:
            self._memory_cache[event_key] = now

        self._stats.unique_events += 1
        return False

    def _cleanup_memory(self):
        """Remove expired entries from memory cache."""
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self._ttl_seconds)

        expired_keys = [
            key for key, timestamp in self._memory_cache.items()
            if now - timestamp > ttl
        ]

        for key in expired_keys:
            del self._memory_cache[key]

        # If still too large, remove oldest
        if len(self._memory_cache) > self._memory_max_size:
            sorted_items = sorted(self._memory_cache.items(), key=lambda x: x[1])
            to_remove = len(self._memory_cache) - (self._memory_max_size // 2)
            for key, _ in sorted_items[:to_remove]:
                del self._memory_cache[key]

    def _generate_key(self, event: Dict[str, Any], platform: str = "") -> str:
        """
        Generate a unique key for an event.

        Priority:
        1. Explicit event_id (most reliable)
        2. Content-based MD5 hash (fallback)

        Args:
            event: Event data dictionary
            platform: Platform identifier

        Returns:
            Unique event key string.
        """
        # Priority 1: Use explicit event_id
        event_id = event.get("event_id")
        if event_id:
            return f"{platform}:{event_id}"

        # Priority 2: Generate content-based hash
        user_data = event.get("user_data", {})
        parameters = event.get("parameters", {})

        components = [
            platform,
            event.get("event_name", ""),
            str(event.get("event_time", "")),
            user_data.get("em", user_data.get("email", "")),
            user_data.get("ph", user_data.get("phone", "")),
            str(parameters.get("value", "")),
            str(parameters.get("order_id", "")),
        ]

        content = "|".join(str(c) for c in components)
        return hashlib.md5(content.encode()).hexdigest()

    async def mark_as_seen(self, event: Dict[str, Any], platform: str = "") -> bool:
        """
        Explicitly mark an event as seen without checking duplicate status.

        Useful for pre-registering events before processing.

        Args:
            event: Event data dictionary
            platform: Platform identifier

        Returns:
            True if successfully marked, False otherwise.
        """
        event_key = self._generate_key(event, platform)
        full_key = f"{self._key_prefix}{event_key}"

        if self._connected and self._redis:
            try:
                await self._redis.set(
                    full_key,
                    datetime.now(timezone.utc).isoformat(),
                    ex=self._ttl_seconds,
                )
                return True
            except Exception as e:
                logger.warning(f"Failed to mark event as seen in Redis: {e}")

        # Fallback to memory
        self._memory_cache[event_key] = datetime.now(timezone.utc)
        return True

    async def remove(self, event: Dict[str, Any], platform: str = "") -> bool:
        """
        Remove an event from the deduplication cache.

        Useful when an event fails and needs to be retried.

        Args:
            event: Event data dictionary
            platform: Platform identifier

        Returns:
            True if removed, False otherwise.
        """
        event_key = self._generate_key(event, platform)
        full_key = f"{self._key_prefix}{event_key}"

        if self._connected and self._redis:
            try:
                await self._redis.delete(full_key)
                return True
            except Exception as e:
                logger.warning(f"Failed to remove event from Redis: {e}")

        # Fallback to memory
        if event_key in self._memory_cache:
            del self._memory_cache[event_key]
            return True

        return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.

        Returns:
            Dictionary with statistics.
        """
        stats = self._stats.to_dict()
        stats["redis_connected"] = self._connected
        stats["memory_cache_size"] = len(self._memory_cache)
        stats["memory_cache_max"] = self._memory_max_size

        if self._connected and self._redis:
            try:
                # Count keys in Redis (sampling for performance)
                cursor = 0
                count = 0
                pattern = f"{self._key_prefix}*"
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                count = len(keys)
                stats["redis_keys_sample"] = count
            except Exception:
                pass

        return stats

    def reset_stats(self):
        """Reset statistics counters."""
        self._stats = DedupeStats()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the deduplicator.

        Returns:
            Health status dictionary.
        """
        health = {
            "status": "healthy",
            "redis_connected": self._connected,
            "mode": "redis" if self._connected else "memory",
            "memory_usage": len(self._memory_cache),
        }

        if not self._connected:
            # Try to reconnect
            connected = await self.connect()
            health["redis_connected"] = connected
            health["mode"] = "redis" if connected else "memory"

            if not connected:
                health["status"] = "degraded"
                health["warning"] = "Using in-memory fallback - duplicates may occur across processes"

        return health


# =============================================================================
# Singleton Instance
# =============================================================================

# Global distributed deduplicator instance
distributed_deduplicator = DistributedEventDeduplicator()


async def get_deduplicator() -> DistributedEventDeduplicator:
    """
    Get the distributed deduplicator instance, ensuring connection.

    Returns:
        Connected DistributedEventDeduplicator instance.
    """
    if not distributed_deduplicator._connected:
        await distributed_deduplicator.connect()
    return distributed_deduplicator
