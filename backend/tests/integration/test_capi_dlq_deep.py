# =============================================================================
# Stratum AI - CAPI Dead Letter Queue Deep Integration Tests (#342 Batch 5)
# =============================================================================
"""Deep integration tests for ``app.services.capi.dead_letter_queue``.

Exercises both storage backends:

- **Real Redis** (the compose ``redis`` service via ``settings.redis_url``):
  enqueue, lookup, pending listing with filters, recover/discard/retry
  transitions, stats aggregation, expiry cleanup, replay, and health check.
- **In-memory fallback** (no ``connect()``): same lifecycle plus buffer
  trimming and memory-side cleanup.
- **Degraded Redis** (mocked client raising builtin ``ConnectionError``):
  the documented fallback-to-memory branches.

Unit-level pure logic (serialization round-trip, ``_categorize_failure``)
is already covered by ``tests/unit/test_dlq_pure.py`` and not repeated here.

PRODUCTION BUG (pinned below, not fixed): every Redis ``except`` clause in
the module catches builtin ``ConnectionError/TimeoutError/OSError``, but
redis-py (8.x) raises ``redis.exceptions.ConnectionError`` which subclasses
``RedisError -> Exception`` — NOT the builtins. A genuinely unreachable
Redis therefore crashes callers instead of triggering the memory fallback.
"""

from datetime import datetime, timedelta, timezone
from unittest import mock
from uuid import uuid4

import pytest
import pytest_asyncio
import redis.exceptions as redis_exceptions

from app.services.capi import dead_letter_queue as dlq_module
from app.services.capi.dead_letter_queue import (
    DeadLetterQueue,
    DLQEntry,
    DLQStats,
    DLQStatus,
    FailureReason,
    dead_letter_queue,
    get_dlq,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# Helpers / fixtures
# =============================================================================


def _make_entry(
    status: DLQStatus = DLQStatus.PENDING,
    platform: str = "meta",
    tenant_id: int = 1,
    age: timedelta = timedelta(0),
    category: FailureReason = FailureReason.TIMEOUT,
) -> DLQEntry:
    ts = datetime.now(timezone.utc) - age
    return DLQEntry(
        id=str(uuid4()),
        tenant_id=tenant_id,
        platform=platform,
        event_name="Purchase",
        event_id="evt-1",
        event_data={"event_id": "evt-1", "value": 9.99},
        failure_reason="timed out",
        failure_category=category,
        error_message="timed out",
        retry_count=0,
        max_retries=3,
        first_failure_at=ts,
        last_failure_at=ts,
        status=status,
    )


async def _purge(dlq: DeadLetterQueue) -> None:
    """Remove all DLQ keys so tests are isolated on the shared Redis."""
    keys = await dlq._redis.keys(f"{dlq.ENTRY_PREFIX}*")
    if keys:
        await dlq._redis.delete(*keys)
    await dlq._redis.delete(dlq.QUEUE_KEY)


@pytest_asyncio.fixture
async def redis_dlq():
    """A DLQ connected to the real compose Redis, purged before and after."""
    dlq = DeadLetterQueue()
    try:
        connected = await dlq.connect()
    except redis_exceptions.RedisError:
        connected = False
    if not connected:
        pytest.skip("Redis not reachable from test environment")
    await _purge(dlq)
    yield dlq
    await _purge(dlq)
    await dlq.disconnect()


@pytest.fixture
def memory_dlq() -> DeadLetterQueue:
    """A DLQ that was never connected -> in-memory fallback paths."""
    return DeadLetterQueue()


@pytest.fixture
def broken_dlq() -> DeadLetterQueue:
    """A DLQ that believes it is connected but whose client raises the
    builtin ConnectionError the code is written to handle."""
    dlq = DeadLetterQueue()
    dlq._connected = True
    dlq._redis = mock.AsyncMock()
    for method in ("set", "get", "zadd", "zrange", "zrangebyscore", "zrem"):
        getattr(dlq._redis, method).side_effect = ConnectionError("redis down")
    return dlq


# =============================================================================
# Connection lifecycle
# =============================================================================


class TestConnection:
    async def test_connect_and_disconnect(self):
        dlq = DeadLetterQueue()
        assert await dlq.connect() is True
        assert dlq._connected is True
        assert dlq._redis is not None

        await dlq.disconnect()
        assert dlq._redis is None
        assert dlq._connected is False

    async def test_connect_without_redis_library(self):
        dlq = DeadLetterQueue()
        with mock.patch.object(dlq_module, "REDIS_AVAILABLE", False):
            assert await dlq.connect() is False
        assert dlq._connected is False

    async def test_connect_unreachable_redis_raises_redis_error(self):
        """PRODUCTION BUG (pinned): ``connect()`` catches builtin
        ConnectionError/TimeoutError/OSError (dead_letter_queue.py:187),
        but redis-py raises ``redis.exceptions.ConnectionError`` (a plain
        ``Exception`` subclass). An unreachable Redis therefore propagates
        instead of returning False and enabling the memory fallback.

        Repro: DeadLetterQueue(redis_url=<closed port>).connect().
        Severity: medium — DLQ hard-fails at startup when Redis is down,
        defeating its own degradation design. Fix: also catch
        ``redis.exceptions.RedisError`` (here and in every method-level
        except clause in this module).
        """
        dlq = DeadLetterQueue(redis_url="redis://127.0.0.1:6399/0")
        with pytest.raises(redis_exceptions.ConnectionError):
            await dlq.connect()
        assert dlq._connected is False

    async def test_connect_handles_builtin_connection_error(self):
        """The branch connect() was *written* to handle: a client whose
        ping raises builtin ConnectionError -> returns False, no raise."""
        dlq = DeadLetterQueue()
        fake_client = mock.AsyncMock()
        fake_client.ping.side_effect = ConnectionError("refused")
        with mock.patch.object(
            dlq_module.aioredis, "from_url", mock.Mock(return_value=fake_client)
        ):
            assert await dlq.connect() is False
        assert dlq._connected is False

    async def test_disconnect_noop_when_never_connected(self):
        dlq = DeadLetterQueue()
        await dlq.disconnect()  # no error
        assert dlq._redis is None

    async def test_get_dlq_connects_module_singleton(self):
        # Reset the singleton so get_dlq() takes the connect path.
        dead_letter_queue._connected = False
        dead_letter_queue._redis = None

        instance = await get_dlq()

        assert instance is dead_letter_queue
        assert instance._connected is True

        # Second call short-circuits: already connected -> same instance.
        again = await get_dlq()
        assert again is instance

        # Detach from this test's event loop so later tests are unaffected.
        await instance.disconnect()


# =============================================================================
# Redis-backed lifecycle
# =============================================================================


class TestRedisLifecycle:
    async def test_add_failed_event_persists_entry(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=7,
            platform="meta",
            event_name="Purchase",
            event_data={"event_id": "evt-42", "value": 99.0},
            error_message="Request timed out",
            retry_count=2,
            max_retries=3,
            platform_response={"error": {"code": 1}},
            context={"batch": "b-1"},
        )

        assert entry.failure_category == FailureReason.TIMEOUT
        assert entry.event_id == "evt-42"
        assert entry.status == DLQStatus.PENDING

        # Entry readable back from Redis
        stored = await redis_dlq.get_entry(entry.id)
        assert stored is not None
        assert stored.tenant_id == 7
        assert stored.retry_count == 2
        assert stored.platform_response == {"error": {"code": 1}}
        assert stored.context == {"batch": "b-1"}

        # Retention TTL set on the entry key; id queued in the sorted set
        ttl = await redis_dlq._redis.ttl(f"{redis_dlq.ENTRY_PREFIX}{entry.id}")
        assert 0 < ttl <= redis_dlq._retention_days * 86400
        score = await redis_dlq._redis.zscore(redis_dlq.QUEUE_KEY, entry.id)
        assert score == pytest.approx(entry.last_failure_at.timestamp())

    async def test_get_entry_missing_returns_none(self, redis_dlq):
        assert await redis_dlq.get_entry("no-such-id") is None

    async def test_get_entry_corrupt_json_falls_back_to_memory(self, redis_dlq):
        """Invalid JSON raises ValueError, which IS caught -> memory scan."""
        entry_id = str(uuid4())
        await redis_dlq._redis.set(f"{redis_dlq.ENTRY_PREFIX}{entry_id}", "{not json")

        assert await redis_dlq.get_entry(entry_id) is None

        # And a memory-resident entry with that id is still found
        mem_entry = _make_entry()
        mem_entry.id = entry_id
        redis_dlq._memory_queue.append(mem_entry)
        found = await redis_dlq.get_entry(entry_id)
        assert found is mem_entry

    async def test_get_pending_entries_filters(self, redis_dlq):
        meta_t1 = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="connection refused",
        )
        google_t1 = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="google",
            event_name="Lead",
            event_data={},
            error_message="rate limit exceeded",
        )
        meta_t2 = await redis_dlq.add_failed_event(
            tenant_id=2,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="401 unauthorized",
        )
        recovered = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
        )
        await redis_dlq.mark_recovered(recovered.id)

        all_pending = await redis_dlq.get_pending_entries()
        assert {e.id for e in all_pending} == {meta_t1.id, google_t1.id, meta_t2.id}

        meta_only = await redis_dlq.get_pending_entries(platform="meta")
        assert {e.id for e in meta_only} == {meta_t1.id, meta_t2.id}

        tenant1 = await redis_dlq.get_pending_entries(tenant_id=1)
        assert {e.id for e in tenant1} == {meta_t1.id, google_t1.id}

        both = await redis_dlq.get_pending_entries(platform="meta", tenant_id=2)
        assert [e.id for e in both] == [meta_t2.id]

        # Pagination over the sorted set
        page = await redis_dlq.get_pending_entries(limit=1)
        assert len(page) <= 1

    async def test_mark_recovered(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
        )

        assert await redis_dlq.mark_recovered(entry.id) is True

        stored = await redis_dlq.get_entry(entry.id)
        assert stored.status == DLQStatus.RECOVERED
        assert stored.recovered_at is not None
        assert stored.recovered_at.tzinfo is not None

    async def test_mark_recovered_missing_returns_false(self, redis_dlq):
        assert await redis_dlq.mark_recovered("no-such-id") is False

    async def test_mark_discarded_with_reason(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="invalid payload",
        )

        assert await redis_dlq.mark_discarded(entry.id, reason="stale event") is True

        stored = await redis_dlq.get_entry(entry.id)
        assert stored.status == DLQStatus.DISCARDED
        assert stored.context["discard_reason"] == "stale event"

    async def test_mark_discarded_without_reason(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="invalid payload",
        )

        assert await redis_dlq.mark_discarded(entry.id) is True
        stored = await redis_dlq.get_entry(entry.id)
        assert stored.status == DLQStatus.DISCARDED
        assert not (stored.context or {}).get("discard_reason")

    async def test_mark_discarded_missing_returns_false(self, redis_dlq):
        assert await redis_dlq.mark_discarded("no-such-id") is False

    async def test_update_retry_increments_and_resets_status(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
            retry_count=1,
        )
        # Simulate an in-flight replay that failed again
        await redis_dlq.replay_event(entry.id)

        assert await redis_dlq.update_retry(entry.id, "still timing out") is True

        stored = await redis_dlq.get_entry(entry.id)
        assert stored.retry_count == 2
        assert stored.error_message == "still timing out"
        assert stored.status == DLQStatus.PENDING
        assert stored.last_failure_at >= stored.first_failure_at

    async def test_update_retry_missing_returns_false(self, redis_dlq):
        assert await redis_dlq.update_retry("no-such-id", "err") is False

    async def test_replay_event_marks_retrying(self, redis_dlq):
        entry = await redis_dlq.add_failed_event(
            tenant_id=3,
            platform="tiktok",
            event_name="CompletePayment",
            event_data={"value": 5},
            error_message="dns failure",
            retry_count=2,
        )

        payload = await redis_dlq.replay_event(entry.id)

        assert payload == {
            "dlq_entry_id": entry.id,
            "tenant_id": 3,
            "platform": "tiktok",
            "event_data": {"value": 5},
            "original_retry_count": 2,
        }
        stored = await redis_dlq.get_entry(entry.id)
        assert stored.status == DLQStatus.RETRYING

    async def test_replay_event_missing_raises(self, redis_dlq):
        with pytest.raises(ValueError, match="DLQ entry not found"):
            await redis_dlq.replay_event("no-such-id")

    async def test_get_stats_aggregates(self, redis_dlq):
        pending = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timed out",
        )
        recovered = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="google",
            event_name="Lead",
            event_data={},
            error_message="rate limit",
        )
        discarded = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="invalid payload",
        )
        retrying = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="snapchat",
            event_name="PURCHASE",
            event_data={},
            error_message="connection reset",
        )
        await redis_dlq.mark_recovered(recovered.id)
        await redis_dlq.mark_discarded(discarded.id)
        await redis_dlq.replay_event(retrying.id)

        # Backdate one entry so oldest-age is meaningful
        old = _make_entry(age=timedelta(hours=5))
        await redis_dlq._store_entry(old)

        stats = await redis_dlq.get_stats()

        assert stats.total_entries == 5
        assert stats.pending == 2  # pending + the backdated memory entry
        assert stats.recovered == 1
        assert stats.discarded == 1
        assert stats.retrying == 1
        assert stats.by_platform["meta"] == 3
        assert stats.by_platform["google"] == 1
        assert stats.by_failure_category[FailureReason.TIMEOUT.value] >= 2
        assert stats.by_failure_category[FailureReason.RATE_LIMITED.value] == 1
        assert stats.oldest_entry_age_hours == pytest.approx(5, abs=0.2)
        # 1 recovered / (1 recovered + 1 discarded + 0 expired)
        assert stats.recovery_rate_pct == pytest.approx(50.0)
        assert pending.id  # silence unused warning

    async def test_get_stats_empty(self, redis_dlq):
        stats = await redis_dlq.get_stats()
        assert stats.total_entries == 0
        assert stats.recovery_rate_pct == 0.0
        assert stats.oldest_entry_age_hours == 0.0

    async def test_get_stats_skips_orphaned_queue_ids(self, redis_dlq):
        """A queued id whose entry key expired (TTL) is skipped."""
        await redis_dlq._redis.zadd(redis_dlq.QUEUE_KEY, {"orphan-id": 1.0})
        live = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
        )

        stats = await redis_dlq.get_stats()

        assert stats.total_entries == 1
        assert stats.by_platform == {"meta": 1}
        assert live.id

    async def test_categorization_circuit_platform_and_unknown(self, redis_dlq):
        circuit = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="circuit breaker tripped",
        )
        assert circuit.failure_category == FailureReason.CIRCUIT_OPEN

        platform_err = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="???",
            platform_response={"error": {"code": 100}},
        )
        assert platform_err.failure_category == FailureReason.PLATFORM_ERROR

        unknown = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="???",
        )
        assert unknown.failure_category == FailureReason.UNKNOWN

    async def test_cleanup_expired_redis(self, redis_dlq):
        # Old PENDING entry -> should be marked EXPIRED and dequeued
        old_pending = _make_entry(age=timedelta(days=10))
        await redis_dlq._store_entry(old_pending)
        # Old RECOVERED entry -> dequeued but not re-marked
        old_recovered = _make_entry(status=DLQStatus.RECOVERED, age=timedelta(days=10))
        await redis_dlq._store_entry(old_recovered)
        # Fresh entry -> untouched
        fresh = await redis_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
        )

        removed = await redis_dlq.cleanup_expired()

        assert removed == 2
        expired = await redis_dlq.get_entry(old_pending.id)
        assert expired.status == DLQStatus.EXPIRED
        recovered = await redis_dlq.get_entry(old_recovered.id)
        assert recovered.status == DLQStatus.RECOVERED
        # Old ids removed from the queue, fresh one still present
        assert (
            await redis_dlq._redis.zscore(redis_dlq.QUEUE_KEY, old_pending.id) is None
        )
        assert await redis_dlq._redis.zscore(redis_dlq.QUEUE_KEY, fresh.id) is not None

    async def test_health_check_healthy(self, redis_dlq):
        health = await redis_dlq.health_check()
        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert health["mode"] == "redis"
        assert health["pending_count"] == 0

    async def test_health_check_warns_on_old_entries(self, redis_dlq):
        stale = _make_entry(age=timedelta(hours=48))
        await redis_dlq._store_entry(stale)

        health = await redis_dlq.health_check()

        assert health["status"] == "warning"
        assert "Old entries" in health["warning"]


# =============================================================================
# In-memory fallback (never connected)
# =============================================================================


class TestMemoryFallback:
    async def test_add_and_get_in_memory(self, memory_dlq):
        entry = await memory_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={"event_id": "m-1"},
            error_message="socket closed",
        )

        assert memory_dlq._memory_queue == [entry]
        assert entry.failure_category == FailureReason.NETWORK_ERROR
        assert await memory_dlq.get_entry(entry.id) is entry
        assert await memory_dlq.get_entry("missing") is None

    async def test_memory_queue_trims_at_max(self, memory_dlq):
        memory_dlq.MAX_MEMORY_ENTRIES = 3
        entries = []
        for i in range(5):
            entries.append(
                await memory_dlq.add_failed_event(
                    tenant_id=i,
                    platform="meta",
                    event_name="Purchase",
                    event_data={},
                    error_message="timeout",
                )
            )

        assert len(memory_dlq._memory_queue) == 3
        assert memory_dlq._memory_queue == entries[-3:]

    async def test_get_pending_entries_memory_filters_and_pagination(self, memory_dlq):
        e1 = _make_entry(platform="meta", tenant_id=1)
        e2 = _make_entry(platform="google", tenant_id=1)
        e3 = _make_entry(platform="meta", tenant_id=2)
        e4 = _make_entry(platform="meta", tenant_id=1, status=DLQStatus.DISCARDED)
        memory_dlq._memory_queue.extend([e1, e2, e3, e4])

        assert {e.id for e in await memory_dlq.get_pending_entries()} == {
            e1.id,
            e2.id,
            e3.id,
        }
        assert [
            e.id for e in await memory_dlq.get_pending_entries(platform="google")
        ] == [e2.id]
        assert {e.id for e in await memory_dlq.get_pending_entries(tenant_id=1)} == {
            e1.id,
            e2.id,
        }
        # offset/limit slice
        paged = await memory_dlq.get_pending_entries(limit=1, offset=1)
        assert [e.id for e in paged] == [e2.id]

    async def test_status_transitions_in_memory(self, memory_dlq):
        entry = _make_entry()
        memory_dlq._memory_queue.append(entry)

        assert await memory_dlq.mark_recovered(entry.id) is True
        assert entry.status == DLQStatus.RECOVERED

        assert await memory_dlq.update_retry(entry.id, "again") is True
        assert entry.retry_count == 1
        assert entry.status == DLQStatus.PENDING

        payload = await memory_dlq.replay_event(entry.id)
        assert payload["dlq_entry_id"] == entry.id
        assert entry.status == DLQStatus.RETRYING

        assert await memory_dlq.mark_discarded(entry.id, "give up") is True
        assert entry.status == DLQStatus.DISCARDED

    async def test_get_stats_memory(self, memory_dlq):
        memory_dlq._memory_queue.extend(
            [
                _make_entry(),
                _make_entry(status=DLQStatus.EXPIRED, platform="google"),
                _make_entry(
                    status=DLQStatus.RECOVERED, category=FailureReason.AUTH_ERROR
                ),
            ]
        )

        stats = await memory_dlq.get_stats()

        assert isinstance(stats, DLQStats)
        assert stats.total_entries == 3
        assert stats.pending == 1
        assert stats.expired == 1
        assert stats.recovered == 1
        assert stats.by_platform == {"meta": 2, "google": 1}
        # 1 recovered / (1 recovered + 0 discarded + 1 expired)
        assert stats.recovery_rate_pct == pytest.approx(50.0)

    async def test_cleanup_expired_memory(self, memory_dlq):
        old_pending = _make_entry(age=timedelta(days=10))
        old_recovered = _make_entry(status=DLQStatus.RECOVERED, age=timedelta(days=10))
        old_discarded = _make_entry(status=DLQStatus.DISCARDED, age=timedelta(days=10))
        fresh = _make_entry()
        memory_dlq._memory_queue.extend(
            [old_pending, old_recovered, old_discarded, fresh]
        )

        removed = await memory_dlq.cleanup_expired()

        assert removed == 1  # only the old PENDING entry is dropped
        remaining = {e.id for e in memory_dlq._memory_queue}
        assert remaining == {old_recovered.id, old_discarded.id, fresh.id}

    async def test_health_check_memory_mode_and_pending_warning(self, memory_dlq):
        memory_dlq._memory_queue.extend(_make_entry() for _ in range(1001))

        health = await memory_dlq.health_check()

        assert health["mode"] == "memory"
        assert health["redis_connected"] is False
        assert health["status"] == "warning"
        assert "High pending count" in health["warning"]


# =============================================================================
# Degraded Redis -> documented fallback branches
# =============================================================================


class TestDegradedRedisFallback:
    """The module's except clauses handle builtin ConnectionError; these
    tests drive those branches with a mocked client. (Real redis-py raises
    redis.exceptions.* which is NOT caught — see TestConnection bug pin.)"""

    async def test_store_entry_falls_back_to_memory(self, broken_dlq):
        entry = await broken_dlq.add_failed_event(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            event_data={},
            error_message="timeout",
        )
        assert broken_dlq._memory_queue == [entry]

    async def test_get_entry_falls_back_to_memory(self, broken_dlq):
        entry = _make_entry()
        broken_dlq._memory_queue.append(entry)
        assert await broken_dlq.get_entry(entry.id) is entry

    async def test_get_pending_falls_back_to_memory(self, broken_dlq):
        entry = _make_entry()
        broken_dlq._memory_queue.append(entry)
        pending = await broken_dlq.get_pending_entries()
        assert [e.id for e in pending] == [entry.id]

    async def test_get_stats_falls_back_to_memory(self, broken_dlq):
        broken_dlq._memory_queue.append(_make_entry())
        stats = await broken_dlq.get_stats()
        assert stats.total_entries == 1
        assert stats.pending == 1

    async def test_cleanup_expired_falls_back_to_memory(self, broken_dlq):
        broken_dlq._memory_queue.append(_make_entry(age=timedelta(days=10)))
        removed = await broken_dlq.cleanup_expired()
        assert removed == 1
        assert broken_dlq._memory_queue == []

    async def test_real_redis_error_propagates_from_get_entry(self):
        """PRODUCTION BUG (pinned): method-level except clauses miss
        redis.exceptions errors, so a live-but-failing Redis crashes
        get_entry() instead of falling back to memory
        (dead_letter_queue.py:353)."""
        dlq = DeadLetterQueue()
        dlq._connected = True
        dlq._redis = mock.AsyncMock()
        dlq._redis.get.side_effect = redis_exceptions.ConnectionError("gone")

        with pytest.raises(redis_exceptions.ConnectionError):
            await dlq.get_entry("any-id")
