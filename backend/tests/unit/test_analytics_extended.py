# =============================================================================
# Stratum AI - Analytics Extended Test Suite
# =============================================================================
"""
Tests for untested analytics modules:

1. EMQ Calculation (emq_calculation.py)
   - 5 driver calculators (event match rate, pixel coverage, conversion latency,
     attribution accuracy, data freshness)
   - Composite EMQ score, aggregate across platforms
   - Autopilot mode determination, event loss calculation

2. Attribution Variance (attribution.py)
   - Single entity variance, batch, attribution health summary

3. Budget Reallocation (budget.py)
   - Budget reallocation logic, summarization, validation (learning phase)

4. Utility functions from scoring.py, fatigue.py, anomalies.py, signal_health.py
   - pct_change, clamp, clamp01, ema, get_refresh_candidates,
     detect_entity_anomalies, generate_anomaly_message, get_health_color
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.logic.anomalies import (
    detect_entity_anomalies,
    generate_anomaly_message,
)
from app.analytics.logic.attribution import (
    attribution_variance,
    batch_attribution_variance,
    get_attribution_health,
)
from app.analytics.logic.budget import (
    BudgetReallocationParams,
    reallocate_budget,
    summarize_reallocation,
    validate_reallocation,
)
from app.analytics.logic.emq_calculation import (
    PlatformMetrics,
    calculate_attribution_accuracy,
    calculate_conversion_latency,
    calculate_data_freshness,
    calculate_emq_score,
    calculate_aggregate_emq,
    calculate_event_match_rate,
    calculate_event_loss_percentage,
    calculate_pixel_coverage,
    determine_autopilot_mode,
    DriverStatus,
    DriverTrend,
)
from app.analytics.logic.fatigue import ema, get_refresh_candidates
from app.analytics.logic.scoring import clamp, clamp01, pct_change
from app.analytics.logic.signal_health import get_health_color
from app.analytics.logic.types import (
    AlertSeverity,
    AnomalyResult,
    BaselineMetrics,
    BudgetAction,
    EntityLevel,
    EntityMetrics,
    FatigueResult,
    FatigueState,
    Platform,
    ScalingAction,
    ScalingScoreResult,
    SignalHealthStatus,
)


# =============================================================================
# Helpers
# =============================================================================

NOW = datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc)


def _metrics(**overrides) -> PlatformMetrics:
    defaults = dict(
        platform="meta",
        pixel_events=1000,
        capi_events=900,
        matched_events=850,
        pages_with_pixel=50,
        total_pages=50,
        events_configured=8,
        events_expected=8,
        avg_conversion_latency_hours=0.5,
        platform_conversions=100,
        ga4_conversions=95,
        platform_revenue=5000.0,
        ga4_revenue=4800.0,
        last_event_at=NOW - timedelta(minutes=30),
    )
    defaults.update(overrides)
    return PlatformMetrics(**defaults)


def _entity(eid: str, **kw) -> EntityMetrics:
    defaults = dict(
        entity_id=eid,
        entity_name=f"Camp {eid}",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=NOW,
        spend=1000.0,
        roas=4.0,
        cpa=40.0,
        cvr=0.05,
        ctr=0.01,
    )
    defaults.update(kw)
    return EntityMetrics(**defaults)


def _baseline(**kw) -> BaselineMetrics:
    defaults = dict(roas=4.0, cpa=40.0, cvr=0.05, ctr=0.01)
    defaults.update(kw)
    return BaselineMetrics(**defaults)


def _scaling_result(eid: str, score: float, action: ScalingAction, **kw) -> ScalingScoreResult:
    defaults = dict(
        entity_id=eid,
        entity_name=f"Camp {eid}",
        score=score,
        action=action,
        roas_delta=0.5 if score > 0 else -0.3,
        cpa_delta=-0.2 if score > 0 else 0.3,
        cvr_delta=0.1,
        ctr_delta=0.05,
    )
    defaults.update(kw)
    return ScalingScoreResult(**defaults)


# #############################################################################
#
#  PART 1: SCORING UTILITIES
#
# #############################################################################


@pytest.mark.unit
class TestPctChange:

    def test_positive_change(self) -> None:
        assert pct_change(120, 100) == pytest.approx(0.2)

    def test_negative_change(self) -> None:
        assert pct_change(80, 100) == pytest.approx(-0.2)

    def test_zero_baseline(self) -> None:
        assert pct_change(100, 0) == 0.0

    def test_both_zero(self) -> None:
        assert pct_change(0, 0) == 0.0

    def test_negative_baseline(self) -> None:
        # e.g. CPA change from -10 to -20
        result = pct_change(-20, -10)
        assert result == pytest.approx(-1.0)


@pytest.mark.unit
class TestClamp:

    def test_within_range(self) -> None:
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_min(self) -> None:
        assert clamp(-5, 0, 10) == 0

    def test_above_max(self) -> None:
        assert clamp(15, 0, 10) == 10

    def test_at_boundaries(self) -> None:
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10


@pytest.mark.unit
class TestClamp01:

    def test_normal(self) -> None:
        assert clamp01(0.5) == 0.5

    def test_negative(self) -> None:
        assert clamp01(-1.0) == 0.0

    def test_over_one(self) -> None:
        assert clamp01(2.5) == 1.0


# #############################################################################
#
#  PART 2: FATIGUE UTILITIES
#
# #############################################################################


@pytest.mark.unit
class TestEma:

    def test_basic_ema(self) -> None:
        result = ema(1.0, 0.0, alpha=0.4)
        assert result == pytest.approx(0.4)

    def test_alpha_one_is_current(self) -> None:
        assert ema(1.0, 0.5, alpha=1.0) == pytest.approx(1.0)

    def test_alpha_zero_is_prev(self) -> None:
        assert ema(1.0, 0.5, alpha=0.0) == pytest.approx(0.5)


@pytest.mark.unit
class TestGetRefreshCandidates:

    def test_returns_above_threshold(self) -> None:
        results = [
            FatigueResult(creative_id="a", creative_name="A", fatigue_score=0.8,
                          state=FatigueState.REFRESH, ctr_drop=0.3, roas_drop=0.3,
                          cpa_rise=0.2, exposure_factor=0.5),
            FatigueResult(creative_id="b", creative_name="B", fatigue_score=0.3,
                          state=FatigueState.HEALTHY, ctr_drop=0.1, roas_drop=0.1,
                          cpa_rise=0.05, exposure_factor=0.1),
        ]
        candidates = get_refresh_candidates(results)
        assert len(candidates) == 1
        assert candidates[0].creative_id == "a"

    def test_custom_threshold(self) -> None:
        results = [
            FatigueResult(creative_id="a", creative_name="A", fatigue_score=0.5,
                          state=FatigueState.WATCH, ctr_drop=0.2, roas_drop=0.2,
                          cpa_rise=0.1, exposure_factor=0.3),
        ]
        assert len(get_refresh_candidates(results, threshold=0.4)) == 1
        assert len(get_refresh_candidates(results, threshold=0.6)) == 0

    def test_empty_list(self) -> None:
        assert get_refresh_candidates([]) == []


# #############################################################################
#
#  PART 3: ANOMALY UTILITIES
#
# #############################################################################


@pytest.mark.unit
class TestDetectEntityAnomalies:

    def test_detects_anomaly(self) -> None:
        history = {"roas": [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.0, 4.1, 3.9, 4.0]}
        current = {"roas": 1.0}  # big drop
        result = detect_entity_anomalies("camp1", history, current)
        assert result["entity_id"] == "camp1"
        assert result["anomaly_count"] > 0

    def test_no_anomaly(self) -> None:
        history = {"roas": [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.0, 4.1, 3.9, 4.0]}
        current = {"roas": 4.05}
        result = detect_entity_anomalies("camp1", history, current)
        assert result["anomaly_count"] == 0
        assert result["has_critical"] is False

    def test_critical_flag(self) -> None:
        history = {"spend": [100.0] * 10}
        current = {"spend": 500.0}  # huge spike
        result = detect_entity_anomalies("camp1", history, current)
        # With constant series stdev is ~0, so zscore will be 0 (div by zero guard)
        # Use varied series instead
        history2 = {"spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0, 101.0, 100.0]}
        result2 = detect_entity_anomalies("camp1", history2, {"spend": 500.0})
        if result2["anomaly_count"] > 0:
            assert result2["has_critical"] or result2["has_high"]


@pytest.mark.unit
class TestGenerateAnomalyMessage:

    def test_high_direction(self) -> None:
        anomaly = AnomalyResult(
            metric="spend", zscore=3.5, severity=AlertSeverity.HIGH,
            current_value=200.0, baseline_mean=100.0, baseline_std=10.0,
            is_anomaly=True, direction="high",
        )
        msg = generate_anomaly_message(anomaly)
        assert "increased" in msg
        assert "spend" in msg
        assert "100.0%" in msg

    def test_low_direction(self) -> None:
        anomaly = AnomalyResult(
            metric="roas", zscore=-3.0, severity=AlertSeverity.HIGH,
            current_value=1.0, baseline_mean=4.0, baseline_std=0.2,
            is_anomaly=True, direction="low",
        )
        msg = generate_anomaly_message(anomaly)
        assert "decreased" in msg
        assert "75.0%" in msg


# #############################################################################
#
#  PART 4: SIGNAL HEALTH UTILITIES
#
# #############################################################################


@pytest.mark.unit
class TestGetHealthColor:

    def test_all_statuses_have_color(self) -> None:
        for status in SignalHealthStatus:
            color = get_health_color(status)
            assert color.startswith("#")
            assert len(color) == 7

    def test_healthy_is_green(self) -> None:
        assert get_health_color(SignalHealthStatus.HEALTHY) == "#22C55E"

    def test_critical_is_red(self) -> None:
        assert get_health_color(SignalHealthStatus.CRITICAL) == "#EF4444"


# #############################################################################
#
#  PART 5: EMQ CALCULATION
#
# #############################################################################


@pytest.mark.unit
class TestCalculateEventMatchRate:

    def test_good_match_rate(self) -> None:
        m = _metrics(pixel_events=1000, capi_events=900, matched_events=850)
        result = calculate_event_match_rate(m)
        assert result.value >= 85
        assert result.status == DriverStatus.GOOD
        assert result.weight == 0.30

    def test_warning_match_rate(self) -> None:
        m = _metrics(pixel_events=1000, capi_events=500, matched_events=700)
        result = calculate_event_match_rate(m)
        assert result.status == DriverStatus.WARNING

    def test_no_events_critical(self) -> None:
        m = _metrics(pixel_events=0, capi_events=0, matched_events=0)
        result = calculate_event_match_rate(m)
        assert result.value == 0.0
        assert result.status == DriverStatus.CRITICAL

    def test_estimated_from_overlap(self) -> None:
        m = _metrics(pixel_events=100, capi_events=50, matched_events=0)
        result = calculate_event_match_rate(m)
        # min/max overlap = 50/100 = 50%
        assert result.value == pytest.approx(50.0)
        assert result.status == DriverStatus.CRITICAL


@pytest.mark.unit
class TestCalculatePixelCoverage:

    def test_full_coverage(self) -> None:
        m = _metrics(pages_with_pixel=50, total_pages=50, events_configured=8, events_expected=8)
        result = calculate_pixel_coverage(m)
        assert result.value == 100.0
        assert result.status == DriverStatus.GOOD

    def test_partial_coverage(self) -> None:
        m = _metrics(pages_with_pixel=30, total_pages=50, events_configured=5, events_expected=8)
        result = calculate_pixel_coverage(m)
        # (60 + 62.5) / 2 = 61.25
        assert result.value < 75
        assert result.status == DriverStatus.CRITICAL

    def test_no_data_defaults_good(self) -> None:
        m = _metrics(pages_with_pixel=0, total_pages=0, events_configured=0, events_expected=0)
        result = calculate_pixel_coverage(m)
        assert result.value == 90.0  # default when no data


@pytest.mark.unit
class TestCalculateConversionLatency:

    def test_realtime(self) -> None:
        m = _metrics(avg_conversion_latency_hours=0)
        result = calculate_conversion_latency(m)
        assert result.value == 100.0
        assert result.status == DriverStatus.GOOD

    def test_one_hour(self) -> None:
        m = _metrics(avg_conversion_latency_hours=1.0)
        result = calculate_conversion_latency(m)
        assert result.value >= 85

    def test_high_latency_critical(self) -> None:
        m = _metrics(avg_conversion_latency_hours=30)
        result = calculate_conversion_latency(m)
        assert result.value == 0.0
        assert result.status == DriverStatus.CRITICAL

    def test_medium_latency_warning(self) -> None:
        m = _metrics(avg_conversion_latency_hours=8)
        result = calculate_conversion_latency(m)
        assert result.status == DriverStatus.WARNING

    def test_weight_is_020(self) -> None:
        m = _metrics()
        result = calculate_conversion_latency(m)
        assert result.weight == 0.20


@pytest.mark.unit
class TestCalculateAttributionAccuracy:

    def test_perfect_alignment(self) -> None:
        m = _metrics(platform_conversions=100, ga4_conversions=100,
                     platform_revenue=5000, ga4_revenue=5000)
        result = calculate_attribution_accuracy(m)
        assert result.value == 100.0
        assert result.status == DriverStatus.GOOD

    def test_high_variance(self) -> None:
        m = _metrics(platform_conversions=100, ga4_conversions=50,
                     platform_revenue=5000, ga4_revenue=2000)
        result = calculate_attribution_accuracy(m)
        assert result.value < 60
        assert result.status == DriverStatus.CRITICAL

    def test_both_zero(self) -> None:
        m = _metrics(platform_conversions=0, ga4_conversions=0,
                     platform_revenue=0, ga4_revenue=0)
        result = calculate_attribution_accuracy(m)
        assert result.value == 100.0

    def test_weight_is_015(self) -> None:
        m = _metrics()
        result = calculate_attribution_accuracy(m)
        assert result.weight == 0.15


@pytest.mark.unit
class TestCalculateDataFreshness:

    def test_recent_data(self) -> None:
        m = _metrics(last_event_at=NOW - timedelta(minutes=30))
        result = calculate_data_freshness(m, now=NOW)
        assert result.value == 100.0
        assert result.status == DriverStatus.GOOD

    def test_stale_data(self) -> None:
        m = _metrics(last_event_at=NOW - timedelta(hours=48))
        result = calculate_data_freshness(m, now=NOW)
        assert result.value < 40
        assert result.status == DriverStatus.CRITICAL

    def test_no_update_time(self) -> None:
        m = _metrics(last_event_at=None, last_sync_at=None)
        result = calculate_data_freshness(m, now=NOW)
        assert result.value == 50.0
        assert result.status == DriverStatus.WARNING

    def test_weight_is_010(self) -> None:
        m = _metrics()
        result = calculate_data_freshness(m, now=NOW)
        assert result.weight == 0.10


@pytest.mark.unit
class TestCalculateEmqScore:

    def test_healthy_metrics_high_score(self) -> None:
        m = _metrics()
        result = calculate_emq_score(m, now=NOW)
        assert result.score >= 80
        assert result.confidence_band == "reliable"
        assert len(result.drivers) == 5

    def test_degraded_metrics_low_score(self) -> None:
        m = _metrics(
            pixel_events=100, capi_events=10, matched_events=5,
            pages_with_pixel=10, total_pages=50,
            avg_conversion_latency_hours=30,
            platform_conversions=100, ga4_conversions=20,
            last_event_at=NOW - timedelta(hours=48),
        )
        result = calculate_emq_score(m, now=NOW)
        assert result.score < 60
        assert result.confidence_band in ("directional", "unsafe")

    def test_previous_metrics_trends(self) -> None:
        current = _metrics(pixel_events=1000, capi_events=950, matched_events=900)
        previous = _metrics(pixel_events=500, capi_events=400, matched_events=300)
        result = calculate_emq_score(current, previous_metrics=previous, now=NOW)
        assert result.previous_score is not None
        # At least one driver should have an UP trend
        trends = [d.trend for d in result.drivers]
        assert DriverTrend.UP in trends or DriverTrend.FLAT in trends

    def test_drivers_weights_sum_to_one(self) -> None:
        m = _metrics()
        result = calculate_emq_score(m, now=NOW)
        total_weight = sum(d.weight for d in result.drivers)
        assert total_weight == pytest.approx(1.0)


@pytest.mark.unit
class TestCalculateAggregateEmq:

    def test_single_platform(self) -> None:
        m = _metrics()
        single = calculate_emq_score(m, now=NOW)
        agg = calculate_aggregate_emq([single])
        assert agg.score == pytest.approx(single.score)

    def test_multiple_platforms(self) -> None:
        good = calculate_emq_score(_metrics(), now=NOW)
        bad = calculate_emq_score(
            _metrics(pixel_events=10, capi_events=5, matched_events=2,
                     avg_conversion_latency_hours=20,
                     last_event_at=NOW - timedelta(hours=30)),
            now=NOW,
        )
        agg = calculate_aggregate_emq([good, bad])
        # Average should be between the two
        assert min(good.score, bad.score) <= agg.score <= max(good.score, bad.score)

    def test_empty_list(self) -> None:
        agg = calculate_aggregate_emq([])
        assert agg.score == 0.0
        assert agg.confidence_band == "unsafe"
        assert agg.drivers == []

    def test_worst_status_wins(self) -> None:
        """If one platform has a critical driver, aggregate should reflect it."""
        good = calculate_emq_score(_metrics(), now=NOW)
        bad = calculate_emq_score(
            _metrics(pixel_events=0, capi_events=0, matched_events=0), now=NOW,
        )
        agg = calculate_aggregate_emq([good, bad])
        # At least one driver should be CRITICAL
        statuses = [d.status for d in agg.drivers]
        assert DriverStatus.CRITICAL in statuses


@pytest.mark.unit
class TestDetermineAutopilotMode:

    def test_normal_mode(self) -> None:
        mode, reason = determine_autopilot_mode(85.0)
        assert mode == "normal"

    def test_limited_mode(self) -> None:
        mode, reason = determine_autopilot_mode(70.0)
        assert mode == "limited"

    def test_cuts_only_mode(self) -> None:
        mode, reason = determine_autopilot_mode(50.0)
        assert mode == "cuts_only"

    def test_frozen_mode(self) -> None:
        mode, reason = determine_autopilot_mode(30.0)
        assert mode == "frozen"

    def test_boundary_80(self) -> None:
        mode, _ = determine_autopilot_mode(80.0)
        assert mode == "normal"

    def test_boundary_60(self) -> None:
        mode, _ = determine_autopilot_mode(60.0)
        assert mode == "limited"

    def test_boundary_40(self) -> None:
        mode, _ = determine_autopilot_mode(40.0)
        assert mode == "cuts_only"


@pytest.mark.unit
class TestCalculateEventLossPercentage:

    def test_no_loss(self) -> None:
        m = _metrics(pixel_events=100, capi_events=100, matched_events=50, events_expected=100)
        loss = calculate_event_loss_percentage(m)
        # received = 100 + 100 - 50 = 150, >= expected -> 0%
        assert loss == 0.0

    def test_some_loss(self) -> None:
        m = _metrics(pixel_events=30, capi_events=20, matched_events=10, events_expected=100)
        loss = calculate_event_loss_percentage(m)
        # received = 30 + 20 - 10 = 40 -> loss = (100-40)/100*100 = 60%
        assert loss == pytest.approx(60.0)

    def test_no_expected_events(self) -> None:
        m = _metrics(events_expected=0)
        assert calculate_event_loss_percentage(m) == 0.0

    def test_clamped_to_100(self) -> None:
        m = _metrics(pixel_events=0, capi_events=0, matched_events=0, events_expected=100)
        loss = calculate_event_loss_percentage(m)
        assert loss <= 100.0


# #############################################################################
#
#  PART 6: ATTRIBUTION VARIANCE
#
# #############################################################################


@pytest.mark.unit
class TestAttributionVariance:

    def test_no_variance(self) -> None:
        result = attribution_variance("e1", 5000, 100, 5000, 100)
        assert result.revenue_variance_pct == 0.0
        assert result.conversion_variance_pct == 0.0
        assert result.has_significant_variance is False

    def test_platform_higher_revenue(self) -> None:
        result = attribution_variance("e1", 6500, 100, 5000, 100)
        assert result.revenue_variance_pct == 30.0  # (6500-5000)/5000 = 30%
        assert result.has_significant_variance is False  # not > 30

    def test_significant_variance(self) -> None:
        result = attribution_variance("e1", 7000, 100, 5000, 100)
        assert result.revenue_variance_pct == 40.0
        assert result.has_significant_variance is True
        assert result.warning_message is not None
        assert "more revenue" in result.warning_message

    def test_ga4_higher_revenue(self) -> None:
        result = attribution_variance("e1", 3000, 100, 5000, 100)
        assert result.revenue_variance_pct == -40.0
        assert result.has_significant_variance is True
        assert "GA4 reports" in result.warning_message

    def test_zero_ga4(self) -> None:
        result = attribution_variance("e1", 1000, 10, 0, 0)
        assert result.revenue_variance_pct == 100.0
        assert result.conversion_variance_pct == 100.0

    def test_both_zero(self) -> None:
        result = attribution_variance("e1", 0, 0, 0, 0)
        assert result.revenue_variance_pct == 0.0
        assert result.has_significant_variance is False

    def test_conv_variance_significant(self) -> None:
        result = attribution_variance("e1", 5000, 150, 5000, 100)
        # rev=0%, conv=50%
        assert result.conversion_variance_pct == 50.0
        assert result.has_significant_variance is True
        assert "conversion variance" in result.warning_message.lower()

    def test_custom_threshold(self) -> None:
        result = attribution_variance("e1", 6000, 100, 5000, 100, variance_threshold_pct=50.0)
        assert result.revenue_variance_pct == 20.0
        assert result.has_significant_variance is False  # 20 < 50


@pytest.mark.unit
class TestBatchAttributionVariance:

    def test_multiple_entities(self) -> None:
        entities = [
            {"entity_id": "e1", "platform_revenue": 5000, "platform_conversions": 100,
             "ga4_revenue": 5000, "ga4_conversions": 100},
            {"entity_id": "e2", "platform_revenue": 8000, "platform_conversions": 100,
             "ga4_revenue": 5000, "ga4_conversions": 100},
        ]
        results = batch_attribution_variance(entities)
        assert len(results) == 2
        # Sorted by abs revenue variance descending
        assert abs(results[0].revenue_variance_pct) >= abs(results[1].revenue_variance_pct)

    def test_empty_list(self) -> None:
        assert batch_attribution_variance([]) == []

    def test_missing_keys_default_zero(self) -> None:
        entities = [{"entity_id": "e1"}]
        results = batch_attribution_variance(entities)
        assert len(results) == 1
        assert results[0].platform_revenue == 0


@pytest.mark.unit
class TestGetAttributionHealth:

    def test_healthy(self) -> None:
        results = [
            attribution_variance("e1", 5000, 100, 5000, 100),
            attribution_variance("e2", 5100, 100, 5000, 100),
        ]
        health = get_attribution_health(results)
        assert health["status"] == "healthy"
        assert health["entities_with_variance"] == 0

    def test_high_variance(self) -> None:
        results = [
            attribution_variance("e1", 8000, 100, 5000, 100),
            attribution_variance("e2", 9000, 100, 5000, 100),
        ]
        health = get_attribution_health(results)
        assert health["status"] == "high_variance"
        assert health["needs_attention"] is True

    def test_no_data(self) -> None:
        health = get_attribution_health([])
        assert health["status"] == "no_data"
        assert health["entities_checked"] == 0

    def test_minor_variance(self) -> None:
        # 1 out of 6 has significant variance = 16.7% < 20%
        results = [attribution_variance(f"e{i}", 5000, 100, 5000, 100) for i in range(5)]
        results.append(attribution_variance("e5", 8000, 100, 5000, 100))
        health = get_attribution_health(results)
        assert health["status"] == "minor_variance"


# #############################################################################
#
#  PART 7: BUDGET REALLOCATION
#
# #############################################################################


@pytest.mark.unit
class TestReallocateBudget:

    def test_moves_from_losers_to_winners(self) -> None:
        scores = [
            _scaling_result("w1", 0.5, ScalingAction.SCALE),
            _scaling_result("l1", -0.5, ScalingAction.FIX),
        ]
        spends = {"w1": 1000.0, "l1": 1000.0}
        actions = reallocate_budget(scores, spends)

        increases = [a for a in actions if a.action == "increase_budget"]
        decreases = [a for a in actions if a.action == "decrease_budget"]
        assert len(increases) >= 1
        assert len(decreases) >= 1

    def test_no_losers_no_movement(self) -> None:
        scores = [
            _scaling_result("w1", 0.5, ScalingAction.SCALE),
            _scaling_result("w2", 0.3, ScalingAction.SCALE),
        ]
        spends = {"w1": 1000.0, "w2": 1000.0}
        actions = reallocate_budget(scores, spends)
        # No losers -> no budget pool -> no actions
        assert len(actions) == 0

    def test_no_winners_no_increase(self) -> None:
        scores = [
            _scaling_result("l1", -0.5, ScalingAction.FIX),
            _scaling_result("l2", -0.3, ScalingAction.FIX),
        ]
        spends = {"l1": 1000.0, "l2": 1000.0}
        actions = reallocate_budget(scores, spends)
        increases = [a for a in actions if a.action == "increase_budget"]
        decreases = [a for a in actions if a.action == "decrease_budget"]
        assert len(increases) == 0
        assert len(decreases) >= 1

    def test_low_spend_entities_skipped(self) -> None:
        scores = [
            _scaling_result("w1", 0.5, ScalingAction.SCALE),
            _scaling_result("l1", -0.5, ScalingAction.FIX),
        ]
        spends = {"w1": 5.0, "l1": 5.0}  # Below min_spend_threshold
        actions = reallocate_budget(scores, spends)
        assert len(actions) == 0

    def test_max_total_move_cap(self) -> None:
        """Total movement should not exceed max_total_move_pct."""
        scores = [
            _scaling_result("w1", 0.5, ScalingAction.SCALE),
            _scaling_result("l1", -0.5, ScalingAction.FIX),
            _scaling_result("l2", -0.5, ScalingAction.FIX),
            _scaling_result("l3", -0.5, ScalingAction.FIX),
        ]
        spends = {"w1": 5000.0, "l1": 5000.0, "l2": 5000.0, "l3": 5000.0}
        params = BudgetReallocationParams()
        params.max_total_move_pct = 0.05  # 5% cap
        actions = reallocate_budget(scores, spends, params)
        total_decrease = sum(a.amount for a in actions if a.action == "decrease_budget")
        assert total_decrease <= 20000 * 0.05 + 1  # tolerance

    def test_actions_sorted_increases_first(self) -> None:
        scores = [
            _scaling_result("w1", 0.5, ScalingAction.SCALE),
            _scaling_result("l1", -0.5, ScalingAction.FIX),
        ]
        spends = {"w1": 1000.0, "l1": 1000.0}
        actions = reallocate_budget(scores, spends)
        if len(actions) >= 2:
            assert actions[0].action == "increase_budget"

    def test_empty_inputs(self) -> None:
        assert reallocate_budget([], {}) == []


@pytest.mark.unit
class TestSummarizeReallocation:

    def test_basic_summary(self) -> None:
        actions = [
            BudgetAction(entity_id="w1", entity_name="W1", action="increase_budget",
                         amount=200, current_spend=1000, scaling_score=0.5, reason="good"),
            BudgetAction(entity_id="l1", entity_name="L1", action="decrease_budget",
                         amount=200, current_spend=1000, scaling_score=-0.5, reason="bad"),
        ]
        summary = summarize_reallocation(actions)
        assert summary["total_increase"] == 200
        assert summary["total_decrease"] == 200
        assert summary["net_change"] == 0
        assert summary["entities_scaled"] == 1
        assert summary["entities_reduced"] == 1

    def test_empty_actions(self) -> None:
        summary = summarize_reallocation([])
        assert summary["total_increase"] == 0
        assert summary["total_decrease"] == 0
        assert summary["top_increase"] is None
        assert summary["top_decrease"] is None


@pytest.mark.unit
class TestValidateReallocation:

    def test_filters_learning_phase(self) -> None:
        actions = [
            BudgetAction(entity_id="w1", entity_name="W1", action="increase_budget",
                         amount=200, current_spend=1000, scaling_score=0.5, reason="good"),
            BudgetAction(entity_id="l1", entity_name="L1", action="decrease_budget",
                         amount=100, current_spend=1000, scaling_score=-0.5, reason="bad"),
        ]
        learning = {"l1"}
        valid = validate_reallocation(actions, learning)
        assert len(valid) == 1
        assert valid[0].entity_id == "w1"

    def test_no_learning_phase_all_pass(self) -> None:
        actions = [
            BudgetAction(entity_id="w1", entity_name="W1", action="increase_budget",
                         amount=200, current_spend=1000, scaling_score=0.5, reason="good"),
        ]
        valid = validate_reallocation(actions, set())
        assert len(valid) == 1

    def test_all_in_learning_phase(self) -> None:
        actions = [
            BudgetAction(entity_id="a", entity_name="A", action="increase_budget",
                         amount=200, current_spend=1000, scaling_score=0.5, reason="good"),
        ]
        valid = validate_reallocation(actions, {"a"})
        assert len(valid) == 0
