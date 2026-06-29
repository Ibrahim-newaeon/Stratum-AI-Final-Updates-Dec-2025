# =============================================================================
# Stratum AI - Dead Letter Queue Pure-Logic Unit Tests
# =============================================================================
"""Unit tests for the pure logic in
``app.services.capi.dead_letter_queue``:

- ``DLQEntry.to_dict`` / ``from_dict`` serialization round-trip
- ``DeadLetterQueue._categorize_failure`` error-string classification
- ``DLQStats`` defaults

Redis connection and persistence paths are out of scope here; the queue is
constructed without connecting (``__init__`` only stores config).
"""

from datetime import datetime, timezone

import pytest

from app.services.capi.dead_letter_queue import (
    DeadLetterQueue,
    DLQEntry,
    DLQStats,
    DLQStatus,
    FailureReason,
)

pytestmark = pytest.mark.unit


def _entry(**overrides) -> DLQEntry:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    base = dict(
        id="dlq_1",
        tenant_id=7,
        platform="meta",
        event_name="Purchase",
        event_id="evt_1",
        event_data={"value": 99.99},
        failure_reason="timeout",
        failure_category=FailureReason.TIMEOUT,
        error_message="Request timed out",
        retry_count=1,
        max_retries=3,
        first_failure_at=now,
        last_failure_at=now,
    )
    base.update(overrides)
    return DLQEntry(**base)


# =============================================================================
# DLQEntry serialization
# =============================================================================
class TestDLQEntrySerialization:
    def test_to_dict_serializes_enums_and_dates(self):
        d = _entry().to_dict()
        assert d["status"] == "pending"
        assert d["failure_category"] == "timeout"
        assert d["first_failure_at"] == "2026-06-01T12:00:00+00:00"
        assert d["recovered_at"] is None

    def test_round_trip_preserves_fields(self):
        original = _entry(
            status=DLQStatus.RECOVERED,
            recovered_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        restored = DLQEntry.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.tenant_id == original.tenant_id
        assert restored.status == DLQStatus.RECOVERED
        assert restored.failure_category == FailureReason.TIMEOUT
        assert restored.first_failure_at == original.first_failure_at
        assert restored.recovered_at == original.recovered_at


# =============================================================================
# _categorize_failure
# =============================================================================
class TestCategorizeFailure:
    @pytest.fixture
    def dlq(self) -> DeadLetterQueue:
        # Constructor only stores config; no Redis connection is made.
        return DeadLetterQueue()

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Request timed out", FailureReason.TIMEOUT),
            ("connection timeout", FailureReason.TIMEOUT),
            ("Rate limit exceeded (429)", FailureReason.RATE_LIMITED),
            ("too many requests", FailureReason.RATE_LIMITED),
            ("401 Unauthorized: bad token", FailureReason.AUTH_ERROR),
            ("forbidden", FailureReason.AUTH_ERROR),
            ("connection refused", FailureReason.NETWORK_ERROR),
            ("dns lookup failed", FailureReason.NETWORK_ERROR),
            ("circuit breaker open", FailureReason.CIRCUIT_OPEN),
            ("validation failed: missing field", FailureReason.VALIDATION_ERROR),
            ("invalid payload", FailureReason.VALIDATION_ERROR),
            ("something weird happened", FailureReason.UNKNOWN),
        ],
    )
    def test_categorizes_by_message(self, dlq, message, expected):
        assert dlq._categorize_failure(message) == expected

    def test_platform_response_error_when_message_unmatched(self, dlq):
        assert (
            dlq._categorize_failure("???", platform_response={"error": "boom"})
            == FailureReason.PLATFORM_ERROR
        )

    def test_timeout_precedes_rate_limit(self, dlq):
        # "timeout" is checked before "rate limit"; first match wins.
        assert (
            dlq._categorize_failure("timeout while rate limited")
            == FailureReason.TIMEOUT
        )


# =============================================================================
# DLQStats
# =============================================================================
class TestDLQStats:
    def test_defaults_are_zeroed(self):
        stats = DLQStats()
        assert stats.total_entries == 0
        assert stats.by_platform == {}
        assert stats.recovery_rate_pct == 0.0
