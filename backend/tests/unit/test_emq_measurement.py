# =============================================================================
# Stratum AI - Real EMQ Measurement Service unit tests
# =============================================================================
"""Unit tests for app.services.emq_measurement_service.

Pure in-memory EMQ measurement from CAPI delivery logs / pixel events /
GA4 data, no I/O. Covers the recorders, real-metric calculation
(matching, latency, delivery, attribution), conversion to
PlatformMetrics, the RealEMQService (scoring, caching, diagnostics,
autopilot recommendation), and the P0 analytics (anomaly detector,
forecaster, cross-platform analyzer).

Module-level stores are shared, so every test uses a unique platform
name to stay isolated.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.logic.emq_calculation import EmqCalculationResult
from app.services.capi.platform_connectors import (
    EventDeliveryLog,
    log_event_delivery,
)
from app.services.emq_measurement_service import (
    ConversionEvent,
    CrossPlatformEMQAnalyzer,
    EMQAnomalyDetector,
    EMQForecaster,
    GA4ConversionData,
    PixelEvent,
    RealEMQService,
    calculate_real_emq_metrics,
    convert_real_to_platform_metrics,
    record_conversion,
    record_ga4_data,
    record_pixel_event,
)

pytestmark = pytest.mark.unit


def _now():
    return datetime.now(timezone.utc)


def _capi_log(platform, event_id, success=True, latency_ms=100.0, event_name="view"):
    return EventDeliveryLog(
        event_id=event_id,
        platform=platform,
        event_name=event_name,
        timestamp=_now(),
        success=success,
        latency_ms=latency_ms,
    )


def _pixel(platform, event_id):
    return PixelEvent(
        event_id=event_id,
        platform=platform,
        event_name="view",
        timestamp=_now(),
    )


# =============================================================================
# Real metric calculation
# =============================================================================
class TestCalculateRealMetrics:
    def test_empty_platform_all_zero(self):
        metrics = calculate_real_emq_metrics("ut_emq_empty")
        assert metrics.capi_events_count == 0
        assert metrics.pixel_events_count == 0
        assert metrics.match_rate == 0.0
        assert metrics.last_capi_event is None

    def test_capi_delivery_stats(self):
        platform = "ut_emq_capi"
        log_event_delivery(_capi_log(platform, "e1", success=True, latency_ms=100.0))
        log_event_delivery(_capi_log(platform, "e2", success=True, latency_ms=300.0))
        log_event_delivery(_capi_log(platform, "e3", success=False, latency_ms=0.0))
        metrics = calculate_real_emq_metrics(platform)
        assert metrics.capi_events_count == 3
        assert metrics.capi_success_count == 2
        assert metrics.capi_failure_count == 1
        assert metrics.capi_delivery_rate == pytest.approx(66.666, abs=0.01)
        assert metrics.avg_capi_latency_ms == 200.0  # successes only
        assert metrics.last_capi_event is not None

    def test_match_rate_intersection_over_union(self):
        platform = "ut_emq_match"
        record_pixel_event(_pixel(platform, "a"))
        record_pixel_event(_pixel(platform, "b"))
        log_event_delivery(_capi_log(platform, "b"))
        log_event_delivery(_capi_log(platform, "c"))
        metrics = calculate_real_emq_metrics(platform)
        assert metrics.pixel_events_count == 2
        assert metrics.matched_events_count == 1  # only "b"
        assert metrics.match_rate == pytest.approx(33.333, abs=0.01)
        assert metrics.last_pixel_event is not None

    def test_failed_capi_events_excluded_from_matching(self):
        platform = "ut_emq_match_fail"
        record_pixel_event(_pixel(platform, "x"))
        log_event_delivery(_capi_log(platform, "x", success=False))
        metrics = calculate_real_emq_metrics(platform)
        assert metrics.matched_events_count == 0

    def test_conversion_latency_percentiles(self):
        platform = "ut_emq_latency"
        base = _now() - timedelta(hours=1)
        for i, seconds in enumerate([1, 2, 3]):
            record_conversion(
                ConversionEvent(
                    event_id=f"ut_lat_{platform}_{i}",
                    platform=platform,
                    pixel_timestamp=base,
                    capi_timestamp=base + timedelta(seconds=seconds),
                )
            )
        # negative latency must be ignored
        record_conversion(
            ConversionEvent(
                event_id=f"ut_lat_{platform}_neg",
                platform=platform,
                pixel_timestamp=base,
                capi_timestamp=base - timedelta(seconds=5),
            )
        )
        metrics = calculate_real_emq_metrics(platform)
        assert sorted(metrics.latencies_ms) == [1000.0, 2000.0, 3000.0]
        assert metrics.avg_latency_ms == 2000.0
        assert metrics.p50_latency_ms == 2000.0
        assert metrics.p95_latency_ms == 3000.0

    def test_ga4_attribution_aggregated(self):
        platform = "ut_emq_ga4"
        record_ga4_data(
            GA4ConversionData(
                platform=platform, conversions=10, revenue=500.0, date=_now()
            )
        )
        record_ga4_data(
            GA4ConversionData(
                platform=platform, conversions=5, revenue=250.0, date=_now()
            )
        )
        metrics = calculate_real_emq_metrics(platform)
        assert metrics.ga4_conversions == 15
        assert metrics.ga4_revenue == 750.0

    def test_platform_conversions_from_purchase_events(self):
        platform = "ut_emq_purchase"
        log_event_delivery(_capi_log(platform, "p1", event_name="Purchase"))
        log_event_delivery(_capi_log(platform, "p2", event_name="purchase"))
        log_event_delivery(_capi_log(platform, "v1", event_name="view"))
        metrics = calculate_real_emq_metrics(platform)
        assert metrics.platform_conversions == 2
        assert metrics.platform_revenue == 100.0  # 2 * $50 estimate


# =============================================================================
# Conversion to PlatformMetrics
# =============================================================================
class TestConvertToPlatformMetrics:
    def test_conversion_bridges_fields(self):
        platform = "ut_emq_convert"
        log_event_delivery(_capi_log(platform, "e1", latency_ms=3_600_000.0))
        record_conversion(
            ConversionEvent(
                event_id=f"ut_conv_{platform}",
                platform=platform,
                pixel_timestamp=_now() - timedelta(hours=2),
                capi_timestamp=_now() - timedelta(hours=1),
            )
        )
        real = calculate_real_emq_metrics(platform)
        pm = convert_real_to_platform_metrics(real)
        assert pm.platform == platform
        assert pm.capi_events == 1
        assert pm.avg_conversion_latency_hours == pytest.approx(1.0)
        assert pm.api_error_count == 0
        assert pm.api_request_count == 1

    def test_default_events_configured_when_no_delivery(self):
        real = calculate_real_emq_metrics("ut_emq_convert_empty")
        pm = convert_real_to_platform_metrics(real)
        assert pm.events_configured == 90  # fallback estimate


# =============================================================================
# RealEMQService
# =============================================================================
class TestRealEMQService:
    def test_platform_emq_returns_result_with_details(self):
        platform = "ut_emq_svc_basic"
        record_pixel_event(_pixel(platform, "m1"))
        log_event_delivery(_capi_log(platform, "m1"))
        svc = RealEMQService()
        result = svc.get_platform_emq(platform)
        assert isinstance(result, EmqCalculationResult)
        assert 0 <= result.score <= 100
        assert "Match rate" in result.drivers[0].details
        assert "Avg latency" in result.drivers[2].details

    def test_cache_hit_and_bypass(self):
        platform = "ut_emq_svc_cache"
        log_event_delivery(_capi_log(platform, "c1"))
        svc = RealEMQService()
        first = svc.get_platform_emq(platform)
        assert svc.get_platform_emq(platform) is first  # cached object
        assert svc.get_platform_emq(platform, use_cache=False) is not first

    def test_measure_emq_flags_quality_issues(self):
        platform = "ut_emq_svc_issues"
        # one pixel event with no CAPI match -> 0% match, 0% delivery
        record_pixel_event(_pixel(platform, "lonely"))
        svc = RealEMQService()
        measurement = svc.measure_emq(platform, "pixel_1", "t1")
        joined = " ".join(measurement.recommendations)
        assert "Low match rate" in joined
        assert "CAPI delivery issues" in joined

    def test_measure_emq_healthy_signal(self):
        platform = "ut_emq_svc_healthy"
        for i in range(10):
            record_pixel_event(_pixel(platform, f"h{i}"))
            log_event_delivery(_capi_log(platform, f"h{i}", latency_ms=100.0))
        svc = RealEMQService()
        measurement = svc.measure_emq(platform, "pixel_1", "t1")
        assert measurement.match_rate == 100.0
        assert measurement.event_coverage == 100.0
        assert measurement.recommendations == [
            "Event quality looks good. Continue monitoring for consistency."
        ]

    def test_history_shape(self):
        svc = RealEMQService()
        history = svc.get_history("meta", "px", "t1", days=7)
        assert len(history) == 7
        assert set(history[0]) == {
            "date",
            "overall_score",
            "parameter_quality",
            "event_coverage",
            "match_rate",
        }

    def test_autopilot_recommendation_structure(self):
        platform = "ut_emq_svc_auto"
        log_event_delivery(_capi_log(platform, "a1"))
        svc = RealEMQService()
        rec = svc.get_autopilot_recommendation(platform)
        assert set(rec) >= {
            "emq_score",
            "confidence_band",
            "autopilot_mode",
            "reason",
            "drivers",
        }
        assert rec["drivers"]  # driver dicts present

    def test_diagnostics_attribution_variance_flagged(self):
        platform = "ut_emq_svc_diag"
        log_event_delivery(_capi_log(platform, "d1", event_name="purchase"))
        record_ga4_data(
            GA4ConversionData(
                platform=platform, conversions=100, revenue=5000.0, date=_now()
            )
        )
        svc = RealEMQService()
        diag = svc.get_emq_diagnostics(platform)
        assert diag["platform"] == platform
        assert diag["metrics"]["attribution"]["ga4_conversions"] == 100
        issues = [r["issue"] for r in diag["recommendations"]]
        assert any("Attribution variance" in i for i in issues)
        assert any("Low event match rate" in i for i in issues)


# =============================================================================
# EMQAnomalyDetector
# =============================================================================
class TestAnomalyDetector:
    def _seed(self, detector, platform, metric, n=20):
        for i in range(n):
            detector.record_metric(platform, metric, 100.0 + (i % 2) * 2)  # 100/102

    def test_insufficient_history(self):
        detector = EMQAnomalyDetector()
        assert detector.detect_anomalies("meta", {"match_rate": 50.0}) == []

    def test_spike_detected_high_and_low(self):
        detector = EMQAnomalyDetector(sensitivity=2.0)
        self._seed(detector, "meta", "match_rate")
        high = detector.detect_anomalies("meta", {"match_rate": 130.0})
        assert len(high) == 1
        assert high[0].severity == "critical"
        assert "higher" in high[0].description
        assert "spike" in high[0].recommended_action
        low = detector.detect_anomalies("meta", {"match_rate": 70.0})
        assert "lower" in low[0].description
        assert "declining" in low[0].recommended_action

    def test_constant_history_skipped(self):
        detector = EMQAnomalyDetector()
        for _ in range(20):
            detector.record_metric("meta", "flat_metric", 50.0)
        assert detector.detect_anomalies("meta", {"flat_metric": 80.0}) == []

    @pytest.mark.parametrize(
        "z,expected",
        [(5.0, "critical"), (3.5, "high"), (2.7, "medium"), (2.1, "low")],
    )
    def test_severity_tiers(self, z, expected):
        assert EMQAnomalyDetector()._determine_severity(z) == expected

    def test_known_metric_recommendation(self):
        detector = EMQAnomalyDetector()
        rec = detector._generate_recommendation("capi_delivery_rate", 3.0)
        assert "API credentials" in rec


# =============================================================================
# EMQForecaster
# =============================================================================
class TestForecaster:
    def test_no_history_projects_default(self):
        forecasts = EMQForecaster().forecast("meta", days_ahead=3)
        assert len(forecasts) == 3
        assert forecasts[0].predicted_score == 75.0
        assert forecasts[0].trend == "stable"
        assert "Insufficient historical data" in forecasts[0].factors[0]

    def test_short_history_uses_last_score(self):
        forecaster = EMQForecaster()
        forecaster.record_score("meta", 88.0)
        forecasts = forecaster.forecast("meta", days_ahead=2)
        assert forecasts[0].predicted_score == 88.0

    def test_stable_trend(self):
        forecaster = EMQForecaster()
        for _ in range(20):
            forecaster.record_score("meta", 80.0)
        forecasts = forecaster.forecast("meta", days_ahead=5)
        assert forecasts[0].trend == "stable"
        assert forecasts[0].predicted_score == 80.0
        assert forecasts[0].factors == ["Metrics within normal operating range"]

    def test_improving_trend_increases_forecast(self):
        forecaster = EMQForecaster()
        for score in [60.0] * 14 + [80.0] * 14:
            forecaster.record_score("meta", score)
        forecasts = forecaster.forecast("meta", days_ahead=5)
        assert forecasts[0].trend == "improving"
        assert forecasts[4].predicted_score > forecasts[0].predicted_score
        assert "trending upward" in forecasts[0].factors[0]

    def test_declining_trend(self):
        forecaster = EMQForecaster()
        for score in [80.0] * 14 + [60.0] * 14:
            forecaster.record_score("meta", score)
        forecasts = forecaster.forecast("meta", days_ahead=2)
        assert forecasts[0].trend == "declining"
        assert any("pixel implementation" in f for f in forecasts[0].factors)

    def test_confidence_interval_widens(self):
        forecaster = EMQForecaster()
        for score in [70.0, 75.0] * 10:
            forecaster.record_score("meta", score)
        forecasts = forecaster.forecast("meta", days_ahead=7)
        width_first = (
            forecasts[0].confidence_interval_high - forecasts[0].confidence_interval_low
        )
        width_last = (
            forecasts[-1].confidence_interval_high
            - forecasts[-1].confidence_interval_low
        )
        assert width_last > width_first


# =============================================================================
# CrossPlatformEMQAnalyzer
# =============================================================================
class TestCrossPlatformAnalyzer:
    def test_needs_two_platforms(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        result = analyzer.analyze_correlation(["solo"])
        assert "error" in result

    def test_correlated_histories(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        for i in range(6):
            analyzer.record_scores({"ut_xp_a": 60.0 + i * 2, "ut_xp_b": 50.0 + i * 2})
        result = analyzer.analyze_correlation(["ut_xp_a", "ut_xp_b"])
        assert result["platforms_analyzed"] == 2
        assert result["correlations"]["ut_xp_a_vs_ut_xp_b"] == 1.0
        assert result["best_performer"] is not None

    def test_pearson_correlation(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        assert analyzer._calculate_correlation([1, 2, 3], [2, 4, 6]) == pytest.approx(
            1.0
        )
        assert analyzer._calculate_correlation([1, 2, 3], [6, 4, 2]) == pytest.approx(
            -1.0
        )
        assert analyzer._calculate_correlation([1.0], [2.0]) == 0.0
        assert analyzer._calculate_correlation([5, 5, 5], [1, 2, 3]) == 0.0

    def test_recommendations_correlated_low_scores(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        recs = analyzer._generate_cross_platform_recommendations(
            scores={"meta": 50.0, "google": 55.0},
            correlations={"meta_vs_google": 0.9},
        )
        assert any("correlated issues" in r for r in recs)

    def test_recommendations_gap_learning(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        recs = analyzer._generate_cross_platform_recommendations(
            scores={"meta": 95.0, "tiktok": 60.0},
            correlations={},
        )
        assert any("Apply meta configuration" in r for r in recs)

    def test_recommendations_balanced(self):
        analyzer = CrossPlatformEMQAnalyzer(RealEMQService())
        recs = analyzer._generate_cross_platform_recommendations(
            scores={"meta": 85.0, "google": 82.0},
            correlations={"meta_vs_google": 0.3},
        )
        assert recs == ["Cross-platform EMQ is well-balanced"]
