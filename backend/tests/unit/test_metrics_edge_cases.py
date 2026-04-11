# =============================================================================
# Stratum AI - Negative & Edge-Case Metric Value Tests
# =============================================================================
"""
Tests for edge cases in analytics logic:
- Zero metric values
- Negative metric values
- Very large values
- NaN/None handling
- Division by zero scenarios
"""

import math
import pytest
from datetime import datetime, timezone

from app.analytics.logic.types import (
    EntityMetrics,
    BaselineMetrics,
    Platform,
    EntityLevel,
    ScalingAction,
    FatigueState,
    SignalHealthStatus,
)
from app.analytics.logic.scoring import scaling_score, batch_scaling_scores
from app.analytics.logic.fatigue import creative_fatigue
from app.analytics.logic.anomalies import anomaly_zscore, get_severity
from app.analytics.logic.signal_health import signal_health


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def zero_metrics() -> EntityMetrics:
    """Metrics where all values are zero."""
    return EntityMetrics(
        entity_id="zero_001",
        entity_name="Zero Campaign",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(timezone.utc),
        spend=0.0,
        impressions=0,
        clicks=0,
        conversions=0,
        revenue=0.0,
        cpa=0.0,
        roas=0.0,
        cvr=0.0,
        ctr=0.0,
        cpm=0.0,
        frequency=0.0,
    )


@pytest.fixture
def negative_metrics() -> EntityMetrics:
    """Metrics with negative values (refund/adjustment scenario)."""
    return EntityMetrics(
        entity_id="neg_001",
        entity_name="Negative Revenue Campaign",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(timezone.utc),
        spend=500.0,
        impressions=10000,
        clicks=100,
        conversions=5,
        revenue=-200.0,  # Refund scenario
        cpa=100.0,
        roas=-0.4,       # Negative ROAS
        cvr=0.05,
        ctr=0.01,
        cpm=50.0,
        frequency=3.0,
    )


@pytest.fixture
def extreme_metrics() -> EntityMetrics:
    """Metrics with extremely large values."""
    return EntityMetrics(
        entity_id="extreme_001",
        entity_name="Extreme Campaign",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(timezone.utc),
        spend=999999999.0,
        impressions=999999999,
        clicks=999999999,
        conversions=999999999,
        revenue=999999999.0,
        cpa=1.0,
        roas=999999.0,
        cvr=1.0,
        ctr=1.0,
        cpm=999999.0,
        frequency=100.0,
    )


@pytest.fixture
def zero_baseline() -> BaselineMetrics:
    """Baseline with zero values — tests division-by-zero protection."""
    return BaselineMetrics(
        spend=0.0,
        impressions=0,
        clicks=0,
        conversions=0,
        revenue=0.0,
        cpa=0.0,
        roas=0.0,
        cvr=0.0,
        ctr=0.0,
        cpm=0.0,
        frequency=0.0,
    )


@pytest.fixture
def normal_baseline() -> BaselineMetrics:
    return BaselineMetrics(
        spend=1000.0,
        impressions=50000,
        clicks=500,
        conversions=25,
        revenue=5000.0,
        cpa=40.0,
        roas=5.0,
        cvr=0.05,
        ctr=0.01,
        cpm=20.0,
        frequency=2.0,
        emq_score=90.0,
    )


# =============================================================================
# Zero Metric Tests
# =============================================================================

class TestZeroMetrics:
    """Ensure the system handles zero metric values gracefully."""

    def test_scaling_score_zero_metrics(self, zero_metrics, normal_baseline):
        """Zero metrics should not crash — should produce a valid result."""
        result = scaling_score(zero_metrics, normal_baseline)
        assert result is not None
        assert isinstance(result.score, (int, float))
        assert not math.isnan(result.score)
        assert result.action in (ScalingAction.SCALE, ScalingAction.FIX, ScalingAction.WATCH)

    def test_scaling_score_zero_baseline(self, zero_metrics, zero_baseline):
        """Zero baseline should not cause division by zero."""
        result = scaling_score(zero_metrics, zero_baseline)
        assert result is not None
        assert not math.isnan(result.score)

    def test_fatigue_zero_frequency(self, zero_metrics):
        """Creative with zero frequency should not be flagged as fatigued."""
        result = creative_fatigue(zero_metrics)
        assert result is not None
        assert result.state != FatigueState.CRITICAL

    def test_anomaly_zero_values(self):
        """Z-score of zero against zero mean should not crash."""
        result = anomaly_zscore(0.0, 0.0, 0.0)
        assert result is not None
        assert not math.isnan(result)


# =============================================================================
# Negative Metric Tests
# =============================================================================

class TestNegativeMetrics:
    """Ensure negative values (refunds, adjustments) are handled safely."""

    def test_scaling_score_negative_revenue(self, negative_metrics, normal_baseline):
        """Negative revenue should produce a low/negative score, not crash."""
        result = scaling_score(negative_metrics, normal_baseline)
        assert result is not None
        assert isinstance(result.score, (int, float))
        assert not math.isnan(result.score)
        # Negative revenue should not be a SCALE action
        assert result.action != ScalingAction.SCALE

    def test_negative_roas_handled(self, negative_metrics, normal_baseline):
        """Negative ROAS delta should be computed correctly."""
        result = scaling_score(negative_metrics, normal_baseline)
        assert result.roas_delta < 0, "Negative ROAS should produce negative delta"

    def test_anomaly_severity_negative(self):
        """Negative z-scores should still produce valid severity."""
        severity = get_severity(-5.0)
        assert severity is not None


# =============================================================================
# Extreme Value Tests
# =============================================================================

class TestExtremeMetrics:
    """Ensure very large values don't cause overflow or NaN."""

    def test_scaling_score_extreme_values(self, extreme_metrics, normal_baseline):
        """Extremely large values should not overflow."""
        result = scaling_score(extreme_metrics, normal_baseline)
        assert result is not None
        assert not math.isnan(result.score)
        assert not math.isinf(result.score)

    def test_batch_scaling_handles_mixed(self, zero_metrics, negative_metrics, extreme_metrics, normal_baseline):
        """Batch scoring with mixed edge cases should complete without errors."""
        results = batch_scaling_scores(
            [zero_metrics, negative_metrics, extreme_metrics],
            normal_baseline,
        )
        assert len(results) == 3
        for r in results:
            assert not math.isnan(r.score)


# =============================================================================
# Signal Health Edge Cases
# =============================================================================

class TestSignalHealthEdgeCases:
    """Signal health should handle edge inputs gracefully."""

    def test_signal_health_zero_emq(self):
        """Zero EMQ should produce low signal health, not crash."""
        result = signal_health(emq_score=0.0, api_health=100.0, event_loss=0.0)
        assert result is not None
        assert result.score >= 0

    def test_signal_health_all_zero(self):
        """All-zero inputs should produce a valid status."""
        result = signal_health(emq_score=0.0, api_health=0.0, event_loss=100.0)
        assert result is not None
        assert result.status in (
            SignalHealthStatus.HEALTHY,
            SignalHealthStatus.DEGRADED,
            SignalHealthStatus.UNHEALTHY,
        )

    def test_signal_health_perfect_scores(self):
        """Perfect inputs should produce HEALTHY status."""
        result = signal_health(emq_score=100.0, api_health=100.0, event_loss=0.0)
        assert result is not None
        assert result.status == SignalHealthStatus.HEALTHY
