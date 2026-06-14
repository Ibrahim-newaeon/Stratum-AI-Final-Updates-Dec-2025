# =============================================================================
# Stratum AI - CAPI Connector Health Monitor Unit Tests
# =============================================================================
"""Unit tests for ``ConnectorHealthMonitor`` in
``app.services.capi.platform_connectors`` — the pure health-scoring logic
that turns recent delivery logs + circuit state into a health status.

The monitor is exercised with a duck-typed connector (just ``PLATFORM_NAME``
+ ``get_circuit_state``) and explicit delivery logs, so no real connector,
network, or module-global log store is touched.
"""

from datetime import datetime, timezone

import pytest

from app.services.capi.platform_connectors import (
    ConnectorHealthMonitor,
    EventDeliveryLog,
)

pytestmark = pytest.mark.unit


class _FakeConnector:
    """Minimal stand-in: the monitor only needs name + circuit state."""

    def __init__(self, platform: str = "meta", circuit_state: str = "closed"):
        self.PLATFORM_NAME = platform
        self._circuit_state = circuit_state

    def get_circuit_state(self):
        return {"state": self._circuit_state}


def _log(success: bool, latency_ms: float = 100.0) -> EventDeliveryLog:
    return EventDeliveryLog(
        event_id="evt",
        platform="meta",
        event_name="Purchase",
        timestamp=datetime.now(timezone.utc),
        success=success,
        latency_ms=latency_ms,
    )


@pytest.fixture
def monitor() -> ConnectorHealthMonitor:
    return ConnectorHealthMonitor()


# =============================================================================
# check_health status thresholds
# =============================================================================
class TestCheckHealth:
    def test_no_logs_is_healthy(self, monitor):
        health = monitor.check_health(_FakeConnector(), delivery_logs=[])
        assert health.status == "healthy"
        assert health.success_rate_1h == 100.0
        assert health.events_processed_1h == 0

    def test_all_success_low_latency_is_healthy(self, monitor):
        logs = [_log(True, 100.0) for _ in range(10)]
        health = monitor.check_health(_FakeConnector(), delivery_logs=logs)
        assert health.status == "healthy"
        assert health.success_rate_1h == 100.0
        assert health.error_count_1h == 0

    def test_moderate_failure_rate_is_degraded(self, monitor):
        # 8/10 success = 80% -> below 90 but above 70 => degraded.
        logs = [_log(True) for _ in range(8)] + [_log(False) for _ in range(2)]
        health = monitor.check_health(_FakeConnector(), delivery_logs=logs)
        assert health.status == "degraded"
        assert any("success rate" in i.lower() for i in health.issues)

    def test_severe_failure_rate_is_unhealthy(self, monitor):
        # 6/10 success = 60% -> below 70 => unhealthy.
        logs = [_log(True) for _ in range(6)] + [_log(False) for _ in range(4)]
        health = monitor.check_health(_FakeConnector(), delivery_logs=logs)
        assert health.status == "unhealthy"

    def test_open_circuit_is_unhealthy(self, monitor):
        health = monitor.check_health(
            _FakeConnector(circuit_state="open"), delivery_logs=[_log(True)]
        )
        assert health.status == "unhealthy"
        assert health.circuit_state == "open"

    def test_half_open_circuit_is_degraded(self, monitor):
        health = monitor.check_health(
            _FakeConnector(circuit_state="half_open"), delivery_logs=[_log(True)]
        )
        assert health.status == "degraded"

    def test_high_latency_is_degraded(self, monitor):
        logs = [_log(True, 6000.0) for _ in range(5)]
        health = monitor.check_health(_FakeConnector(), delivery_logs=logs)
        assert health.status == "degraded"
        assert any("latency" in i.lower() for i in health.issues)

    def test_extreme_latency_is_unhealthy(self, monitor):
        logs = [_log(True, 12000.0) for _ in range(5)]
        health = monitor.check_health(_FakeConnector(), delivery_logs=logs)
        assert health.status == "unhealthy"


# =============================================================================
# alerts
# =============================================================================
class TestAlerts:
    def test_unhealthy_triggers_callback_once_within_cooldown(self, monitor):
        fired = []
        monitor.register_alert_callback(lambda h: fired.append(h.platform))
        bad = _FakeConnector(circuit_state="open")
        monitor.check_health(bad, delivery_logs=[_log(False)])
        monitor.check_health(bad, delivery_logs=[_log(False)])
        # Second check is within the 15-min cooldown -> only one alert.
        assert fired == ["meta"]

    def test_healthy_does_not_alert(self, monitor):
        fired = []
        monitor.register_alert_callback(lambda h: fired.append(h))
        monitor.check_health(_FakeConnector(), delivery_logs=[_log(True)])
        assert fired == []


# =============================================================================
# summary + history
# =============================================================================
class TestSummaryAndHistory:
    def test_summary_overall_is_worst_status(self, monitor):
        healthy = _FakeConnector(platform="google", circuit_state="closed")
        broken = _FakeConnector(platform="meta", circuit_state="open")
        summary = monitor.get_health_summary([healthy, broken])
        assert summary["overall_status"] == "unhealthy"
        assert summary["platforms"]["meta"]["status"] == "unhealthy"
        assert summary["platforms"]["google"]["status"] == "healthy"

    def test_history_records_each_check(self, monitor):
        c = _FakeConnector()
        monitor.check_health(c, delivery_logs=[_log(True)])
        monitor.check_health(c, delivery_logs=[_log(True)])
        history = monitor.get_health_history("meta")
        assert len(history) == 2
        assert all("status" in h and "timestamp" in h for h in history)

    def test_history_empty_for_unknown_platform(self, monitor):
        assert monitor.get_health_history("tiktok") == []
