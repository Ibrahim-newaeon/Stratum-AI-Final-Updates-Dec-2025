# =============================================================================
# Stratum AI - CAPI DeliveryLogger Persistence Unit Tests [CAPI-04]
# =============================================================================
"""
Covers the database-backed paths of ``app.services.capi.delivery_logger`` that
the pure-logic suite left out: ``flush`` (write + re-buffer on error),
``get_delivery_history`` (row->entry mapping, filters, error), ``get_metrics``
(counts, success rate, latency percentiles, by-platform/event, error), and
``cleanup_old_logs``.

Same mock-at-the-session-boundary technique as ``test_capi_dlq_postgres.py``:
``async_session_factory`` is patched with a fake factory yielding a mock ``db``,
so these run as fast unit tests with no real database — which is what let
delivery_logger.py come out of the .coveragerc omit.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.services.capi.delivery_logger import (
    DeliveryLogEntry,
    DeliveryLogger,
    DeliveryMetrics,
    DeliveryStatus,
)

_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_MODULE = "app.services.capi.delivery_logger.async_session_factory"


def _fake_session_factory(db):
    @asynccontextmanager
    async def _factory():
        yield db

    return _factory


def _mock_db():
    db = MagicMock()
    db.add = MagicMock()  # Session.add is synchronous
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


def _entry(**overrides) -> DeliveryLogEntry:
    base = dict(
        id=str(uuid4()),
        tenant_id=7,
        platform="meta",
        event_id="e1",
        event_name="Purchase",
        event_time=_NOW,
        delivery_time=_NOW,
        status=DeliveryStatus.SUCCESS,
        latency_ms=120.0,
        retry_count=0,
        error_message=None,
        request_id="req-1",
        platform_response={"ok": True},
        user_data_hash="abc123",
        event_value=49.99,
        currency="USD",
    )
    base.update(overrides)
    return DeliveryLogEntry(**base)


@pytest.fixture(autouse=True)
def _clear_shared_buffer():
    # DeliveryLogger._buffer is a class attribute shared across all instances
    # (incl. the module singleton), so isolate every test from cross-contamination.
    DeliveryLogger._buffer.clear()
    yield
    DeliveryLogger._buffer.clear()


# ---------------------------------------------------------------------------
# flush
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flush_writes_each_buffered_entry():
    db = _mock_db()
    logger = DeliveryLogger(buffer_size=100)
    logger._buffer.extend([_entry(platform="meta"), _entry(platform="google")])

    with patch(_MODULE, new=_fake_session_factory(db)):
        await logger.flush()

    assert db.add.call_count == 2
    db.commit.assert_awaited_once()
    # Buffer is drained on a successful flush.
    assert logger._buffer == []
    # event_value dollars -> cents, and the enum is stored as its string value.
    written = db.add.call_args_list[0].args[0]
    assert written.event_value_cents == 4999
    assert written.status == "success"


@pytest.mark.asyncio
async def test_flush_noop_on_empty_buffer():
    factory = MagicMock()
    with patch(_MODULE, new=factory):
        logger = DeliveryLogger()
        await logger.flush()
    # No session opened when there is nothing to write.
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_flush_reenqueues_entries_when_commit_fails():
    db = _mock_db()
    db.commit = AsyncMock(side_effect=SQLAlchemyError("db down"))
    logger = DeliveryLogger(buffer_size=100)
    entries = [_entry(), _entry()]
    logger._buffer.extend(entries)

    with patch(_MODULE, new=_fake_session_factory(db)):
        await logger.flush()

    # Failed entries are put back so a later flush retries them.
    assert logger._buffer == entries


@pytest.mark.asyncio
async def test_none_event_value_maps_to_null_cents():
    db = _mock_db()
    logger = DeliveryLogger(buffer_size=100)
    logger._buffer.append(_entry(event_value=None))

    with patch(_MODULE, new=_fake_session_factory(db)):
        await logger.flush()

    assert db.add.call_args.args[0].event_value_cents is None


# ---------------------------------------------------------------------------
# get_delivery_history
# ---------------------------------------------------------------------------


def _history_row(**overrides):
    base = dict(
        id=uuid4(),
        tenant_id=7,
        platform="meta",
        event_id="e1",
        event_name="Purchase",
        event_time=_NOW,
        delivery_time=_NOW,
        status="success",
        latency_ms=88.0,
        retry_count=1,
        error_message=None,
        request_id="req-9",
        platform_response={"ok": True},
        user_data_hash="h1",
        event_value_cents=4999,
        currency="USD",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_get_delivery_history_maps_rows_to_entries():
    db = _mock_db()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _history_row(),
        _history_row(status="failed", event_value_cents=None),
    ]
    db.execute = AsyncMock(return_value=result)

    with patch(_MODULE, new=_fake_session_factory(db)):
        entries = await DeliveryLogger().get_delivery_history(
            tenant_id=7,
            platform="meta",
            event_name="Purchase",
            status=DeliveryStatus.SUCCESS,
            start_time=_NOW - timedelta(hours=1),
            end_time=_NOW,
            limit=50,
            offset=5,
        )

    assert len(entries) == 2
    assert entries[0].status is DeliveryStatus.SUCCESS
    assert entries[0].event_value == 49.99  # cents -> dollars
    # None cents -> None dollars
    assert entries[1].event_value is None


@pytest.mark.asyncio
async def test_get_delivery_history_returns_empty_on_db_error():
    db = _mock_db()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("boom"))
    with patch(_MODULE, new=_fake_session_factory(db)):
        entries = await DeliveryLogger().get_delivery_history(tenant_id=7)
    assert entries == []


# ---------------------------------------------------------------------------
# get_metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_metrics_aggregates_counts_percentiles_and_breakdowns():
    db = _mock_db()

    totals = MagicMock()
    totals.one.return_value = SimpleNamespace(
        total=200, successful=180, failed=20, avg_latency=95.0
    )
    latencies = MagicMock()
    # >100 successful latencies so the p95/p99 index branches are exercised.
    latencies.all.return_value = [(float(i),) for i in range(1, 121)]
    by_platform = MagicMock()
    by_platform.all.return_value = [
        SimpleNamespace(platform="meta", status="success", count=180),
        SimpleNamespace(platform="meta", status="failed", count=20),
    ]
    by_event = MagicMock()
    by_event.all.return_value = [
        SimpleNamespace(event_name="Purchase", status="success", count=180),
    ]
    db.execute = AsyncMock(side_effect=[totals, latencies, by_platform, by_event])

    with patch(_MODULE, new=_fake_session_factory(db)):
        metrics = await DeliveryLogger().get_metrics(tenant_id=7)

    assert metrics.total_events == 200
    assert metrics.successful == 180
    assert metrics.failed == 20
    assert metrics.success_rate_pct == 90.0
    assert metrics.avg_latency_ms == 95.0
    assert metrics.p50_latency_ms > 0
    assert metrics.p95_latency_ms > metrics.p50_latency_ms
    assert metrics.by_platform["meta"] == {"success": 180, "failed": 20}
    assert metrics.by_event_type["Purchase"]["success"] == 180


@pytest.mark.asyncio
async def test_get_metrics_zero_events_leaves_defaults():
    db = _mock_db()
    totals = MagicMock()
    totals.one.return_value = SimpleNamespace(
        total=0, successful=0, failed=0, avg_latency=None
    )
    empty = MagicMock()
    empty.all.return_value = []
    db.execute = AsyncMock(side_effect=[totals, empty, empty, empty])

    with patch(_MODULE, new=_fake_session_factory(db)):
        metrics = await DeliveryLogger().get_metrics(
            tenant_id=7,
            start_time=_NOW - timedelta(hours=1),
            end_time=_NOW,
        )

    assert metrics.total_events == 0
    assert metrics.success_rate_pct == 0.0
    assert metrics.p50_latency_ms == 0.0


@pytest.mark.asyncio
async def test_get_metrics_returns_defaults_on_db_error():
    db = _mock_db()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("boom"))
    with patch(_MODULE, new=_fake_session_factory(db)):
        metrics = await DeliveryLogger().get_metrics(tenant_id=7)
    assert isinstance(metrics, DeliveryMetrics)
    assert metrics.total_events == 0


# ---------------------------------------------------------------------------
# cleanup_old_logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_old_logs_returns_deleted_count():
    db = _mock_db()
    result = MagicMock()
    result.rowcount = 42
    db.execute = AsyncMock(return_value=result)

    with patch(_MODULE, new=_fake_session_factory(db)):
        deleted = await DeliveryLogger().cleanup_old_logs(retention_days=30)

    assert deleted == 42
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_old_logs_returns_zero_on_db_error():
    db = _mock_db()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("boom"))
    with patch(_MODULE, new=_fake_session_factory(db)):
        deleted = await DeliveryLogger().cleanup_old_logs()
    assert deleted == 0
