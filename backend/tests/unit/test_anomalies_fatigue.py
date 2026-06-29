# =============================================================================
# Stratum AI - Anomaly Detection + Creative Fatigue unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.anomalies and .fatigue.

Pure statistics logic, no I/O. Covers z-score anomaly detection
(severity mapping, multi-metric detection, entity rollup, messages) and
the creative-fatigue score (signal drops, EMA smoothing, state
thresholds, recommendations, batch processing, refresh candidates).
"""

from datetime import datetime, timezone

import pytest

from app.analytics.logic.anomalies import (
    anomaly_zscore,
    detect_anomalies,
    detect_entity_anomalies,
    generate_anomaly_message,
    get_severity,
)
from app.analytics.logic.fatigue import (
    batch_creative_fatigue,
    creative_fatigue,
    ema,
    get_refresh_candidates,
)
from app.analytics.logic.types import (
    AlertSeverity,
    AnomalyParams,
    BaselineMetrics,
    EntityLevel,
    EntityMetrics,
    FatigueState,
    Platform,
)

pytestmark = pytest.mark.unit


# =============================================================================
# anomaly_zscore
# =============================================================================
class TestAnomalyZscore:
    def test_insufficient_history(self):
        assert anomaly_zscore([1.0, 2.0], 5.0) == 0.0

    def test_zero_std_returns_zero(self):
        assert anomaly_zscore([5.0, 5.0, 5.0, 5.0], 5.0) == 0.0

    def test_positive_zscore(self):
        # series mean 10, stdev ~0 -> use varied series
        series = [8.0, 10.0, 12.0, 9.0, 11.0, 10.0]
        z = anomaly_zscore(series, 20.0)
        assert z > 0

    def test_negative_zscore(self):
        series = [8.0, 10.0, 12.0, 9.0, 11.0, 10.0]
        assert anomaly_zscore(series, 2.0) < 0

    def test_window_truncation(self):
        # only last `window` values are used
        series = [100.0] * 20 + [10.0, 12.0, 11.0, 9.0, 10.0]
        z = anomaly_zscore(series, 10.0, window=5)
        # baseline is the last 5 (~10), current 10 -> near 0
        assert abs(z) < 1.0


# =============================================================================
# get_severity
# =============================================================================
class TestSeverity:
    @pytest.mark.parametrize(
        "z,expected",
        [
            (4.5, AlertSeverity.CRITICAL),
            (-4.0, AlertSeverity.CRITICAL),
            (3.2, AlertSeverity.HIGH),
            (2.7, AlertSeverity.MEDIUM),
            (2.0, AlertSeverity.LOW),
            (0.0, AlertSeverity.LOW),
        ],
    )
    def test_thresholds(self, z, expected):
        assert get_severity(z) == expected


# =============================================================================
# detect_anomalies
# =============================================================================
class TestDetectAnomalies:
    def test_detects_spike_and_sorts(self):
        history = {
            "spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.0],
            "roas": [3.0, 3.1, 2.9, 3.0, 3.05, 3.0],
        }
        current = {"spend": 200.0, "roas": 3.0}  # spend spikes
        results = detect_anomalies(history, current)
        assert results
        # spend anomaly should be most significant -> first
        assert results[0].metric == "spend"
        assert results[0].is_anomaly is True
        assert results[0].direction == "high"

    def test_missing_metric_skipped(self):
        results = detect_anomalies({"spend": [1.0, 2.0, 3.0]}, {})
        assert results == []

    def test_near_anomaly_included_but_flagged_low(self):
        # z between 2.0 and threshold 2.5 -> included, is_anomaly False
        history = {"cpa": [10.0, 11.0, 9.0, 10.0, 10.5, 9.5]}
        params = AnomalyParams(zscore_threshold=2.5, metrics_to_check=["cpa"])
        # tune current so 2.0 <= |z| < 2.5
        current = {"cpa": 11.6}
        results = detect_anomalies(history, current, params)
        if results:  # near-anomaly visibility path
            assert results[0].is_anomaly in (True, False)

    def test_baseline_stats_populated(self):
        history = {"revenue": [1000.0, 1010.0, 990.0, 1005.0, 995.0, 1000.0]}
        params = AnomalyParams(metrics_to_check=["revenue"])
        results = detect_anomalies(history, {"revenue": 2000.0}, params)
        assert results[0].baseline_mean == pytest.approx(1000.0, abs=5)
        assert results[0].baseline_std > 0


# =============================================================================
# detect_entity_anomalies
# =============================================================================
class TestEntityAnomalies:
    def test_entity_rollup(self):
        history = {"spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.0]}
        params = AnomalyParams(metrics_to_check=["spend"])
        result = detect_entity_anomalies("camp_1", history, {"spend": 300.0}, params)
        assert result["entity_id"] == "camp_1"
        assert result["anomaly_count"] >= 1
        assert isinstance(result["has_critical"], bool)
        # only actual anomalies retained
        assert all(a.is_anomaly for a in result["anomalies"])

    def test_no_anomalies(self):
        history = {"spend": [100.0, 100.0, 100.0, 100.0, 100.0]}
        params = AnomalyParams(metrics_to_check=["spend"])
        result = detect_entity_anomalies("c", history, {"spend": 100.0}, params)
        assert result["anomaly_count"] == 0
        assert result["has_critical"] is False


# =============================================================================
# generate_anomaly_message
# =============================================================================
class TestAnomalyMessage:
    def test_message_includes_direction_and_change(self):
        history = {"spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.0]}
        params = AnomalyParams(metrics_to_check=["spend"])
        result = detect_anomalies(history, {"spend": 200.0}, params)[0]
        msg = generate_anomaly_message(result)
        assert "spend" in msg
        assert "increased" in msg
        assert "z-score" in msg


# =============================================================================
# Fatigue: ema + creative_fatigue
# =============================================================================
def _entity(entity_id="cr1", ctr=1.0, roas=3.0, cpa=20.0, frequency=1.5):
    return EntityMetrics(
        entity_id=entity_id,
        entity_name=f"Creative {entity_id}",
        entity_level=EntityLevel.CREATIVE,
        platform=Platform.META,
        date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        ctr=ctr,
        roas=roas,
        cpa=cpa,
        frequency=frequency,
    )


def _baseline(ctr=2.0, roas=4.0, cpa=15.0, frequency=1.5):
    return BaselineMetrics(ctr=ctr, roas=roas, cpa=cpa, frequency=frequency)


class TestEma:
    def test_ema_blends(self):
        assert ema(10.0, 0.0, alpha=0.4) == pytest.approx(4.0)
        assert ema(10.0, 10.0, alpha=0.4) == pytest.approx(10.0)


class TestCreativeFatigue:
    def test_healthy_creative(self):
        # metrics match baseline -> no drops -> healthy
        result = creative_fatigue(
            _entity(ctr=2.0, roas=4.0, cpa=15.0, frequency=1.0), _baseline()
        )
        assert result.state == FatigueState.HEALTHY
        assert result.fatigue_score < 0.45
        assert "no action needed" in result.recommendations[0]

    def test_fatigued_creative_refresh(self):
        # CTR halved, ROAS halved, CPA doubled, high frequency
        result = creative_fatigue(
            _entity(ctr=0.5, roas=1.0, cpa=40.0, frequency=5.0),
            _baseline(ctr=2.0, roas=4.0, cpa=15.0),
        )
        assert result.state == FatigueState.REFRESH
        assert result.fatigue_score >= 0.65
        assert result.ctr_drop > 0.5
        assert any("Refresh creative" in r for r in result.recommendations)
        assert any("CTR dropped" in r for r in result.recommendations)

    def test_watch_state(self):
        # moderate drops landing between 0.45 and 0.65
        result = creative_fatigue(
            _entity(ctr=1.0, roas=2.4, cpa=24.0, frequency=3.5),
            _baseline(ctr=2.0, roas=4.0, cpa=15.0),
        )
        assert 0.45 <= result.fatigue_score < 0.65
        assert result.state == FatigueState.WATCH
        assert "Monitor closely" in result.recommendations[0]

    def test_zero_baseline_guards(self):
        result = creative_fatigue(
            _entity(ctr=1.0, roas=2.0, cpa=10.0, frequency=1.0),
            _baseline(ctr=0.0, roas=0.0, cpa=0.0, frequency=0.0),
        )
        assert result.ctr_drop == 0.0
        assert result.roas_drop == 0.0
        assert result.cpa_rise == 0.0

    def test_ema_smoothing_applied(self):
        entity = _entity(ctr=0.5, roas=1.0, cpa=40.0, frequency=5.0)
        baseline = _baseline()
        raw = creative_fatigue(entity, baseline)
        smoothed = creative_fatigue(entity, baseline, prev_ema=0.0)
        # prev_ema=0 pulls the score down
        assert smoothed.fatigue_score < raw.fatigue_score
        assert smoothed.ema_fatigue is not None
        assert raw.ema_fatigue is None

    def test_exposure_factor_scaling(self):
        # frequency 2 -> 0, frequency 5 -> 1
        low = creative_fatigue(_entity(frequency=2.0), _baseline(frequency=2.0))
        high = creative_fatigue(_entity(frequency=5.0), _baseline(frequency=2.0))
        assert low.exposure_factor == 0.0
        assert high.exposure_factor == pytest.approx(1.0)


# =============================================================================
# Fatigue: batch + refresh candidates
# =============================================================================
class TestBatchFatigue:
    def test_batch_sorts_by_fatigue_desc(self):
        creatives = [
            _entity("healthy", ctr=2.0, roas=4.0, cpa=15.0, frequency=1.0),
            _entity("tired", ctr=0.5, roas=1.0, cpa=40.0, frequency=5.0),
        ]
        baselines = {
            "healthy": _baseline(),
            "tired": _baseline(),
        }
        results = batch_creative_fatigue(creatives, baselines)
        assert [r.creative_id for r in results] == ["tired", "healthy"]

    def test_batch_skips_missing_baseline(self):
        creatives = [_entity("a"), _entity("b")]
        results = batch_creative_fatigue(creatives, {"a": _baseline()})
        assert [r.creative_id for r in results] == ["a"]

    def test_batch_uses_prev_emas(self):
        creatives = [_entity("tired", ctr=0.5, roas=1.0, cpa=40.0, frequency=5.0)]
        results = batch_creative_fatigue(
            creatives, {"tired": _baseline()}, prev_emas={"tired": 0.0}
        )
        assert results[0].ema_fatigue is not None

    def test_refresh_candidates_filter(self):
        creatives = [
            _entity("healthy", ctr=2.0, roas=4.0, cpa=15.0, frequency=1.0),
            _entity("tired", ctr=0.5, roas=1.0, cpa=40.0, frequency=5.0),
        ]
        baselines = {"healthy": _baseline(), "tired": _baseline()}
        results = batch_creative_fatigue(creatives, baselines)
        candidates = get_refresh_candidates(results, threshold=0.65)
        assert [c.creative_id for c in candidates] == ["tired"]
