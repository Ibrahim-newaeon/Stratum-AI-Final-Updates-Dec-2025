# =============================================================================
# Stratum AI - Signal Health Calculator unit tests
# =============================================================================
"""Unit tests for app.stratum.core.signal_health.

Core Trust Engine module — composite signal-health scoring that gates
autopilot. Pure math, no I/O. Covers component-weight redistribution, each
weighted component (EMQ / freshness / variance / anomaly / CDP), the composite
calculate(), and the 5-driver compatibility path.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.stratum.core.signal_health import (
    HealthStatus,
    SignalHealthCalculator,
    SignalHealthConfig,
)
from app.stratum.models import SignalHealth

pytestmark = pytest.mark.unit


@pytest.fixture
def calc() -> SignalHealthCalculator:
    return SignalHealthCalculator()


# =============================================================================
# Config weights
# =============================================================================
class TestWeights:
    def test_base_weights_without_cdp(self):
        w = SignalHealthConfig().get_weights(include_cdp=False)
        assert w["cdp"] == 0.0
        assert w["emq"] == 0.40
        assert sum(w.values()) == pytest.approx(1.0)

    def test_weights_with_cdp_sum_to_one(self):
        w = SignalHealthConfig().get_weights(include_cdp=True)
        assert w["cdp"] == 0.10
        assert sum(w.values()) == pytest.approx(1.0)
        # base weights scaled down to make room for CDP
        assert w["emq"] == pytest.approx(0.40 * 0.9)

    def test_cdp_disabled_ignores_include_flag(self):
        cfg = SignalHealthConfig()
        cfg.cdp_enabled = False
        w = cfg.get_weights(include_cdp=True)
        assert w["cdp"] == 0.0


# =============================================================================
# EMQ component
# =============================================================================
class TestEmqComponent:
    def test_no_scores_default_with_issue(self, calc):
        issues = []
        assert calc._calculate_emq_component(None, issues) == 75.0
        assert any("No EMQ data" in i for i in issues)

    def test_converts_0_10_to_0_100(self, calc):
        issues = []
        # (8.5 + 9.0)/2 * 10 = 87.5
        assert calc._calculate_emq_component([8.5, 9.0], issues) == pytest.approx(87.5)
        assert issues == []

    def test_low_emq_adds_issue(self, calc):
        issues = []
        score = calc._calculate_emq_component([5.0], issues)
        assert score == 50.0
        assert any("below target" in i for i in issues)


# =============================================================================
# Freshness component
# =============================================================================
class TestFreshnessComponent:
    def test_none_timestamp_moderate_penalty(self, calc):
        issues = []
        assert calc._calculate_freshness_component(None, issues) == 50.0
        assert issues

    def test_recent_is_perfect(self, calc):
        issues = []
        recent = datetime.now(UTC) - timedelta(hours=2)
        assert calc._calculate_freshness_component(recent, issues) == 100.0

    def test_stale_is_zero(self, calc):
        issues = []
        stale = datetime.now(UTC) - timedelta(hours=72)
        assert calc._calculate_freshness_component(stale, issues) == 0.0
        assert any("stale" in i for i in issues)

    def test_linear_decay_between_thresholds(self, calc):
        issues = []
        # 36h: halfway between 24 and 48 -> ~50
        mid = datetime.now(UTC) - timedelta(hours=36)
        score = calc._calculate_freshness_component(mid, issues)
        assert score == pytest.approx(50.0, abs=2.0)


# =============================================================================
# Variance component
# =============================================================================
class TestVarianceComponent:
    def test_missing_data_defaults(self, calc):
        assert calc._calculate_variance_component(None, None, None, []) == 80.0

    def test_uses_historical_when_current_missing(self, calc):
        # avg historical variance 0.05 (<= warning) -> 100
        assert calc._calculate_variance_component(None, None, [0.05, 0.05], []) == 100.0

    def test_low_variance_perfect(self, calc):
        assert calc._calculate_variance_component(1000, 1000, None, []) == 100.0

    def test_ga4_zero_platform_positive_max_variance(self, calc):
        issues = []
        # variance 1.0 -> 0 score
        assert calc._calculate_variance_component(1000, 0, None, issues) == 0.0

    @pytest.mark.parametrize(
        "variance,expected",
        [(0.05, 100.0), (0.125, 85.0), (0.15, 50.0), (0.25, 0.0)],
    )
    def test_variance_to_score_bands(self, calc, variance, expected):
        assert calc._variance_to_score(variance, []) == pytest.approx(expected, abs=0.1)


# =============================================================================
# Anomaly component
# =============================================================================
class TestAnomalyComponent:
    def test_insufficient_history_default_good(self, calc):
        assert calc._calculate_anomaly_component({"spend": 100}, [], []) == 90.0

    def test_no_anomalies_perfect(self, calc):
        hist = [{"spend": 100.0} for _ in range(10)]
        score = calc._calculate_anomaly_component({"spend": 101.0}, hist, [])
        assert score == 100.0

    def test_anomaly_detected_lowers_score(self, calc):
        issues = []
        hist = [{"spend": 100.0 + i * 0.1} for i in range(10)]  # tight cluster
        score = calc._calculate_anomaly_component({"spend": 500.0}, hist, issues)
        assert score < 100.0
        assert any("Anomaly detected" in i for i in issues)


# =============================================================================
# Composite calculate()
# =============================================================================
class TestCalculate:
    def test_healthy_is_autopilot_safe(self, calc):
        health = calc.calculate(
            emq_scores=[9.0, 9.0],
            last_data_received=datetime.now(UTC) - timedelta(hours=1),
            platform_revenue=10000,
            ga4_revenue=10000,
        )
        assert isinstance(health, SignalHealth)
        assert health.status == HealthStatus.HEALTHY.value
        assert health.overall_score >= 70
        assert health.is_autopilot_safe() is True

    def test_critical_blocks_autopilot(self, calc):
        health = calc.calculate(
            emq_scores=[2.0],
            last_data_received=datetime.now(UTC) - timedelta(hours=72),
            platform_revenue=10000,
            ga4_revenue=5000,
        )
        assert health.status == HealthStatus.CRITICAL.value
        assert health.is_autopilot_safe() is False
        assert health.issues

    def test_cdp_component_included(self, calc):
        health = calc.calculate(emq_scores=[8.0], cdp_emq_score=85.0)
        assert health.cdp_emq_score == 85.0
        assert health.has_cdp_data() is True

    def test_no_data_uses_defaults_and_flags_issues(self, calc):
        health = calc.calculate()
        # defaults: emq 75, freshness 50, variance 80, anomaly 90
        assert health.emq_score == 75.0
        assert health.issues  # missing-data issues recorded


# =============================================================================
# 5-driver compatibility path
# =============================================================================
class TestFromEmqDrivers:
    def test_strong_drivers_healthy(self, calc):
        health = calc.calculate_from_emq_drivers(
            event_match_rate=95,
            pixel_coverage=95,
            conversion_latency=90,
            attribution_accuracy=90,
            data_freshness=95,
        )
        assert health.status == HealthStatus.HEALTHY.value
        assert health.issues == []

    def test_weak_drivers_flag_issues(self, calc):
        health = calc.calculate_from_emq_drivers(
            event_match_rate=50,
            pixel_coverage=50,
            conversion_latency=40,
            attribution_accuracy=50,
            data_freshness=60,
        )
        assert health.issues
        assert any("Event match rate low" in i for i in health.issues)
