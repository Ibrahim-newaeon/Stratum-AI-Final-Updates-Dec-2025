# =============================================================================
# Stratum AI - CAPI DeliveryLogger Pure-Logic Unit Tests
# =============================================================================
"""
Unit tests for the DB-free logic in ``app.services.capi.delivery_logger``:

- ``DeliveryStatus`` enum values
- ``DeliveryLogEntry.to_dict`` (enum->value, isoformat, PII excluded)
- ``DeliveryMetrics.__post_init__`` dict defaults
- ``DeliveryLogger.log_delivery`` buffering + flush triggers (flush mocked)
- ``get_delivery_logger`` singleton

The database persistence paths (flush write, get_delivery_history, get_metrics,
cleanup_old_logs) need a live session and are out of scope here — same split as
``test_dlq_pure.py``. delivery_logger.py stays in the .coveragerc omit until a
live-env run can confirm those paths don't drop the coverage floor.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.services.capi.delivery_logger import (
    DeliveryLogEntry,
    DeliveryLogger,
    DeliveryMetrics,
    DeliveryStatus,
    get_delivery_logger,
)

_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _entry(**overrides) -> DeliveryLogEntry:
    base = dict(
        id="d1",
        tenant_id=7,
        platform="meta",
        event_id="e1",
        event_name="Purchase",
        event_time=_NOW,
        delivery_time=_NOW,
        status=DeliveryStatus.SUCCESS,
        latency_ms=12.5,
        retry_count=0,
        error_message=None,
        request_id="req1",
        platform_response={"ok": True},
        user_data_hash="abc123",
        event_value=50.0,
        currency="USD",
    )
    base.update(overrides)
    return DeliveryLogEntry(**base)


def test_status_enum_values():
    assert DeliveryStatus.SUCCESS.value == "success"
    assert DeliveryStatus.FAILED.value == "failed"
    assert {s.value for s in DeliveryStatus} >= {
        "success",
        "failed",
        "retrying",
        "rate_limited",
        "circuit_open",
    }


def test_entry_to_dict_core_fields_and_pii_excluded():
    d = _entry().to_dict()
    assert d["id"] == "d1"
    assert d["tenant_id"] == 7
    assert d["status"] == "success"  # enum -> value
    assert d["event_time"].endswith("+00:00")  # isoformat
    assert d["latency_ms"] == 12.5
    assert d["event_value"] == 50.0
    # Hashed PII and raw platform_response are intentionally NOT serialized.
    assert "user_data_hash" not in d
    assert "platform_response" not in d


def test_metrics_dict_defaults():
    m = DeliveryMetrics()
    assert m.by_platform == {}
    assert m.by_event_type == {}
    assert m.total_events == 0
    # Explicit dicts are preserved (not overwritten by the default).
    m2 = DeliveryMetrics(by_platform={"meta": {"successful": 1}})
    assert m2.by_platform == {"meta": {"successful": 1}}


def test_get_delivery_logger_is_singleton():
    assert get_delivery_logger() is get_delivery_logger()


async def test_log_delivery_buffers_without_flush():
    logger = DeliveryLogger(buffer_size=3)
    logger._buffer = []  # isolate from the shared class-level buffer
    logger.flush = AsyncMock()

    for _ in range(2):
        await logger.log_delivery(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            status=DeliveryStatus.SUCCESS,
            latency_ms=5.0,
        )

    assert len(logger._buffer) == 2
    logger.flush.assert_not_called()


async def test_log_delivery_flushes_when_buffer_full():
    logger = DeliveryLogger(buffer_size=2)
    logger._buffer = []
    logger.flush = AsyncMock()

    for _ in range(2):
        await logger.log_delivery(
            tenant_id=1,
            platform="meta",
            event_name="Purchase",
            status=DeliveryStatus.SUCCESS,
            latency_ms=5.0,
        )

    logger.flush.assert_awaited()


async def test_log_delivery_flushes_after_time_window():
    logger = DeliveryLogger(buffer_size=100)
    logger._buffer = []
    logger.flush = AsyncMock()
    # Last flush was long ago -> the >30s time-based flush should trigger.
    logger._last_flush = datetime.now(timezone.utc) - timedelta(seconds=60)

    await logger.log_delivery(
        tenant_id=1,
        platform="meta",
        event_name="Purchase",
        status=DeliveryStatus.FAILED,
        latency_ms=5.0,
        error_message="boom",
    )

    logger.flush.assert_awaited()
