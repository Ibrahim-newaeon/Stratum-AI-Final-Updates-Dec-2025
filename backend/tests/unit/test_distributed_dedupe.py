# =============================================================================
# Stratum AI - Distributed Event Deduplication unit tests
# =============================================================================
"""Unit tests for app.services.capi.distributed_dedupe.

Covers the in-memory fallback (pure logic) and the Redis path via AsyncMock —
no live Redis is required. asyncio_mode=auto runs the async tests directly.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

import app.services.capi.distributed_dedupe as dd_mod
from app.services.capi.distributed_dedupe import (
    DedupeStats,
    DistributedEventDeduplicator,
    distributed_deduplicator,
    get_deduplicator,
)

pytestmark = pytest.mark.unit


def _mem_dedup(**kw) -> DistributedEventDeduplicator:
    """Deduper that never connects → always uses the in-memory path."""
    return DistributedEventDeduplicator(**kw)


# =============================================================================
# DedupeStats
# =============================================================================
class TestDedupeStats:
    def test_duplicate_rate_zero_checks(self):
        assert DedupeStats().duplicate_rate == 0.0

    def test_duplicate_rate_computed(self):
        s = DedupeStats(total_checks=10, duplicates_found=3)
        assert s.duplicate_rate == 30.0

    def test_to_dict_shape(self):
        d = DedupeStats(total_checks=4, duplicates_found=1).to_dict()
        assert d["duplicate_rate_pct"] == 25.0
        assert {"total_checks", "redis_hits", "fallback_to_memory", "last_reset"} <= set(d)
        # last_reset serialized as ISO string
        assert isinstance(d["last_reset"], str)


# =============================================================================
# Key generation
# =============================================================================
class TestGenerateKey:
    def test_event_id_takes_priority(self):
        d = _mem_dedup()
        assert d._generate_key({"event_id": "abc"}, "meta") == "meta:abc"

    def test_content_hash_is_md5_hex(self):
        d = _mem_dedup()
        key = d._generate_key(
            {"event_name": "Purchase", "event_time": 123,
             "user_data": {"em": "h"}, "parameters": {"value": 10}},
            "meta",
        )
        assert len(key) == 32
        int(key, 16)  # valid hex

    def test_content_hash_is_deterministic(self):
        d = _mem_dedup()
        ev = {"event_name": "P", "parameters": {"value": 5}}
        assert d._generate_key(ev, "meta") == d._generate_key(ev, "meta")

    def test_different_content_differs(self):
        d = _mem_dedup()
        a = d._generate_key({"event_name": "P", "parameters": {"value": 5}}, "m")
        b = d._generate_key({"event_name": "P", "parameters": {"value": 6}}, "m")
        assert a != b

    def test_email_and_phone_fallback_keys(self):
        d = _mem_dedup()
        # uses 'email'/'phone' when 'em'/'ph' absent — must not raise
        k = d._generate_key({"user_data": {"email": "x@y.z", "phone": "12345"}}, "m")
        assert len(k) == 32


# =============================================================================
# In-memory dedupe path
# =============================================================================
class TestInMemoryDedupe:
    @pytest.mark.asyncio
    async def test_first_unique_then_duplicate(self):
        d = _mem_dedup()
        ev = {"event_id": "e1"}
        assert await d.is_duplicate(ev, "meta") is False
        assert await d.is_duplicate(ev, "meta") is True
        assert d._stats.total_checks == 2
        assert d._stats.duplicates_found == 1
        assert d._stats.unique_events == 1

    @pytest.mark.asyncio
    async def test_distinct_events_not_duplicate(self):
        d = _mem_dedup()
        assert await d.is_duplicate({"event_id": "a"}, "m") is False
        assert await d.is_duplicate({"event_id": "b"}, "m") is False

    @pytest.mark.asyncio
    async def test_mark_as_seen_then_duplicate(self):
        d = _mem_dedup()
        ev = {"event_id": "m1"}
        assert await d.mark_as_seen(ev, "meta") is True
        assert await d.is_duplicate(ev, "meta") is True

    @pytest.mark.asyncio
    async def test_remove_allows_reprocessing(self):
        d = _mem_dedup()
        ev = {"event_id": "r1"}
        await d.mark_as_seen(ev, "meta")
        assert await d.remove(ev, "meta") is True
        assert await d.is_duplicate(ev, "meta") is False

    @pytest.mark.asyncio
    async def test_remove_missing_returns_false(self):
        d = _mem_dedup()
        assert await d.remove({"event_id": "never"}, "m") is False

    def test_check_memory_expired_entry_not_duplicate(self):
        d = _mem_dedup(ttl_seconds=60)
        key = "k"
        d._memory_cache[key] = datetime.now(timezone.utc) - timedelta(seconds=120)
        assert d._check_memory(key) is False  # expired
        assert key in d._memory_cache  # re-added fresh

    def test_cleanup_removes_only_expired(self):
        d = _mem_dedup(ttl_seconds=60)
        now = datetime.now(timezone.utc)
        d._memory_cache["old"] = now - timedelta(seconds=120)
        d._memory_cache["fresh"] = now
        d._cleanup_memory()
        assert "old" not in d._memory_cache
        assert "fresh" in d._memory_cache


# =============================================================================
# Stats / lifecycle
# =============================================================================
class TestStatsLifecycle:
    @pytest.mark.asyncio
    async def test_get_stats_memory_mode(self):
        d = _mem_dedup()
        await d.is_duplicate({"event_id": "s"}, "m")
        st = await d.get_stats()
        assert st["redis_connected"] is False
        assert st["memory_cache_size"] >= 1
        assert st["memory_cache_max"] == d._memory_max_size

    def test_reset_stats(self):
        d = _mem_dedup()
        d._stats.total_checks = 5
        d.reset_stats()
        assert d._stats.total_checks == 0


# =============================================================================
# Redis path (mocked)
# =============================================================================
class TestRedisPath:
    def _connected(self) -> DistributedEventDeduplicator:
        d = _mem_dedup()
        d._connected = True
        d._redis = AsyncMock()
        return d

    @pytest.mark.asyncio
    async def test_is_duplicate_redis_hit(self):
        d = self._connected()
        d._redis.set.return_value = None  # SET NX returns None when key exists
        assert await d.is_duplicate({"event_id": "x"}, "meta") is True
        assert d._stats.redis_hits == 1
        assert d._stats.duplicates_found == 1

    @pytest.mark.asyncio
    async def test_is_duplicate_redis_miss(self):
        d = self._connected()
        d._redis.set.return_value = "OK"
        assert await d.is_duplicate({"event_id": "y"}, "meta") is False
        assert d._stats.redis_misses == 1

    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_memory(self):
        d = self._connected()
        d._redis.set.side_effect = ConnectionError("down")
        result = await d.is_duplicate({"event_id": "z"}, "meta")
        assert result is False  # memory path, first sighting
        assert d._stats.fallback_to_memory == 1
        assert d._connected is False

    @pytest.mark.asyncio
    async def test_mark_as_seen_redis(self):
        d = self._connected()
        assert await d.mark_as_seen({"event_id": "a"}, "meta") is True
        d._redis.set.assert_awaited()

    @pytest.mark.asyncio
    async def test_remove_redis(self):
        d = self._connected()
        assert await d.remove({"event_id": "a"}, "meta") is True
        d._redis.delete.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_stats_samples_redis_keys(self):
        d = self._connected()
        d._redis.scan.return_value = (0, ["k1", "k2", "k3"])
        st = await d.get_stats()
        assert st["redis_connected"] is True
        assert st["redis_keys_sample"] == 3


# =============================================================================
# Connection lifecycle (mocked aioredis)
# =============================================================================
class TestConnection:
    @pytest.mark.asyncio
    async def test_connect_without_redis_lib(self, monkeypatch):
        monkeypatch.setattr(dd_mod, "REDIS_AVAILABLE", False)
        assert await _mem_dedup().connect() is False

    @pytest.mark.asyncio
    async def test_connect_success(self, monkeypatch):
        fake = AsyncMock()
        fake.ping = AsyncMock()
        monkeypatch.setattr(dd_mod, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(dd_mod.aioredis, "from_url", lambda *a, **k: fake)
        d = _mem_dedup()
        assert await d.connect() is True
        assert d._connected is True

    @pytest.mark.asyncio
    async def test_connect_failure_increments_attempts(self, monkeypatch):
        fake = AsyncMock()
        fake.ping = AsyncMock(side_effect=ConnectionError("nope"))
        monkeypatch.setattr(dd_mod, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(dd_mod.aioredis, "from_url", lambda *a, **k: fake)
        d = _mem_dedup()
        assert await d.connect() is False
        assert d._connected is False
        assert d._connection_attempts == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        d = _mem_dedup()
        d._redis = AsyncMock()
        d._connected = True
        await d.disconnect()
        assert d._redis is None
        assert d._connected is False

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_no_redis(self, monkeypatch):
        d = _mem_dedup()

        async def fake_connect():
            return False

        monkeypatch.setattr(d, "connect", fake_connect)
        h = await d.health_check()
        assert h["status"] == "degraded"
        assert h["mode"] == "memory"
        assert "warning" in h

    @pytest.mark.asyncio
    async def test_health_check_healthy_when_connected(self):
        d = _mem_dedup()
        d._connected = True
        h = await d.health_check()
        assert h["status"] == "healthy"
        assert h["mode"] == "redis"

    @pytest.mark.asyncio
    async def test_get_deduplicator_connects_singleton(self, monkeypatch):
        calls = {"n": 0}

        async def fake_connect():
            calls["n"] += 1
            distributed_deduplicator._connected = True
            return True

        monkeypatch.setattr(distributed_deduplicator, "_connected", False)
        monkeypatch.setattr(distributed_deduplicator, "connect", fake_connect)
        result = await get_deduplicator()
        assert result is distributed_deduplicator
        assert calls["n"] == 1
