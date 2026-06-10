# =============================================================================
# Stratum AI - Conversion Latency Service unit tests
# =============================================================================
"""Unit tests for app.services.conversion_latency_service.

Pure in-memory latency tracking + analytics, no I/O. Covers the
ConversionLatencyTracker lifecycle (start/end/record/stats/timeline/cleanup),
the convenience integration functions, LatencyAnomalyDetector,
LatencyForecaster, and AttributionWindowOptimizer.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.conversion_latency_service import (
    AttributionWindowOptimizer,
    ConversionLatencyTracker,
    LatencyAnomalyDetector,
    LatencyForecaster,
    LatencyStats,
    get_conversion_latency_stats,
    track_capi_ack,
    track_capi_send,
    track_click,
    track_conversion,
    track_pixel_fire,
)

pytestmark = pytest.mark.unit


def _now():
    return datetime.now(timezone.utc)


# =============================================================================
# Tracker: start / end lifecycle
# =============================================================================
class TestStartEndTracking:
    def test_start_then_end_returns_latency(self):
        tracker = ConversionLatencyTracker()
        start = _now() - timedelta(seconds=1)
        tracker.start_tracking("e1", "meta", "click_to_conversion", start_time=start)
        latency = tracker.end_tracking(
            "e1", "meta", "click_to_conversion", end_time=start + timedelta(seconds=1)
        )
        assert latency == pytest.approx(1000.0)

    def test_end_without_start_returns_none(self):
        tracker = ConversionLatencyTracker()
        assert tracker.end_tracking("ghost", "meta", "click_to_conversion") is None

    def test_restart_overwrites_pending(self):
        tracker = ConversionLatencyTracker()
        t0 = _now() - timedelta(seconds=10)
        t1 = _now() - timedelta(seconds=2)
        tracker.start_tracking("e1", "meta", "click_to_conversion", start_time=t0)
        tracker.start_tracking("e1", "meta", "click_to_conversion", start_time=t1)
        latency = tracker.end_tracking(
            "e1", "meta", "click_to_conversion", end_time=t1 + timedelta(seconds=2)
        )
        # measured from the second start, not the first
        assert latency == pytest.approx(2000.0)

    def test_negative_latency_rejected(self):
        tracker = ConversionLatencyTracker()
        start = _now()
        tracker.start_tracking("e1", "meta", "click_to_conversion", start_time=start)
        latency = tracker.end_tracking(
            "e1", "meta", "click_to_conversion", end_time=start - timedelta(seconds=5)
        )
        assert latency is None
        assert tracker.get_stats("meta", "click_to_conversion").count == 0

    def test_naive_start_aware_end_handled(self):
        tracker = ConversionLatencyTracker()
        naive_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            seconds=3
        )
        tracker.start_tracking("e1", "meta", "pixel_to_capi", start_time=naive_start)
        latency = tracker.end_tracking("e1", "meta", "pixel_to_capi")
        assert latency is not None
        assert latency >= 0

    def test_metadata_merged_on_end(self):
        tracker = ConversionLatencyTracker()
        start = _now() - timedelta(seconds=1)
        tracker.start_tracking(
            "e1", "meta", "click_to_conversion", start_time=start, metadata={"a": 1}
        )
        tracker.end_tracking("e1", "meta", "click_to_conversion", metadata={"b": 2})
        m = tracker._measurements[-1]
        assert m.metadata == {"a": 1, "b": 2}

    def test_keys_namespaced_by_platform_and_type(self):
        tracker = ConversionLatencyTracker()
        start = _now() - timedelta(seconds=1)
        tracker.start_tracking("e1", "meta", "click_to_conversion", start_time=start)
        # same event id on a different platform is not the same pending entry
        assert tracker.end_tracking("e1", "google", "click_to_conversion") is None
        assert tracker.end_tracking("e1", "meta", "click_to_conversion") is not None


# =============================================================================
# Tracker: direct record + stats
# =============================================================================
class TestRecordAndStats:
    def test_record_latency_feeds_stats(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 250.0)
        stats = tracker.get_stats("meta", "send_to_ack")
        assert stats.count == 1
        assert stats.avg_ms == 250.0

    def test_empty_stats(self):
        tracker = ConversionLatencyTracker()
        stats = tracker.get_stats("meta", "click_to_conversion")
        assert stats == LatencyStats()
        assert stats.count == 0

    def test_single_measurement_percentiles_collapse(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 100.0)
        stats = tracker.get_stats("meta", "send_to_ack")
        assert stats.p75_ms == stats.p95_ms == stats.p99_ms == 100.0
        assert stats.std_dev_ms == 0.0

    def test_percentile_math_on_uniform_distribution(self):
        tracker = ConversionLatencyTracker()
        for i in range(1, 101):
            tracker.record_latency("meta", "send_to_ack", float(i))
        stats = tracker.get_stats("meta", "send_to_ack")
        assert stats.count == 100
        assert stats.min_ms == 1.0
        assert stats.max_ms == 100.0
        assert stats.avg_ms == 50.5
        assert stats.median_ms == 50.5
        assert stats.p75_ms == 76.0  # sorted[75]
        assert stats.p90_ms == 91.0
        assert stats.p95_ms == 96.0
        assert stats.p99_ms == 100.0
        assert stats.std_dev_ms > 0

    def test_platform_filter(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 100.0)
        tracker.record_latency("google", "send_to_ack", 900.0)
        assert tracker.get_stats("meta", "send_to_ack").avg_ms == 100.0
        assert tracker.get_stats("google", "send_to_ack").avg_ms == 900.0
        # no filter -> both
        assert tracker.get_stats(None, "send_to_ack").count == 2

    def test_period_cutoff_excludes_old_measurements(self):
        tracker = ConversionLatencyTracker()
        old_start = _now() - timedelta(hours=50)
        tracker.start_tracking(
            "old", "meta", "click_to_conversion", start_time=old_start
        )
        tracker.end_tracking(
            "old",
            "meta",
            "click_to_conversion",
            end_time=old_start + timedelta(seconds=1),
        )
        tracker.record_latency("meta", "click_to_conversion", 500.0)
        stats = tracker.get_stats("meta", "click_to_conversion", period_hours=24)
        assert stats.count == 1
        assert stats.avg_ms == 500.0

    def test_stats_by_platform_groups(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 100.0)
        tracker.record_latency("google", "send_to_ack", 300.0)
        by_platform = tracker.get_stats_by_platform()
        assert set(by_platform) == {"meta", "google"}
        assert by_platform["meta"].avg_ms == 100.0

    def test_stats_by_event_type_groups_and_filters(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 100.0)
        tracker.record_latency("meta", "pixel_to_capi", 50.0)
        tracker.record_latency("google", "send_to_ack", 900.0)
        by_type = tracker.get_stats_by_event_type(platform="meta")
        assert set(by_type) == {"send_to_ack", "pixel_to_capi"}
        assert by_type["send_to_ack"].avg_ms == 100.0


# =============================================================================
# Tracker: timeline, slow conversions, cleanup, diagnostics
# =============================================================================
class TestTimeline:
    def test_empty_timeline(self):
        tracker = ConversionLatencyTracker()
        assert tracker.get_latency_timeline("meta", "click_to_conversion") == []

    def test_measurements_bucketed_hourly(self):
        tracker = ConversionLatencyTracker()
        base = _now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
        for minute, latency_ms in [(15, 100.0), (45, 300.0)]:
            end = base + timedelta(minutes=minute)
            tracker.start_tracking(
                f"e{minute}",
                "meta",
                "click_to_conversion",
                start_time=end - timedelta(milliseconds=latency_ms),
            )
            tracker.end_tracking(
                f"e{minute}", "meta", "click_to_conversion", end_time=end
            )
        timeline = tracker.get_latency_timeline(
            "meta", "click_to_conversion", bucket_minutes=60
        )
        assert len(timeline) == 1
        assert timeline[0]["count"] == 2
        assert timeline[0]["avg_ms"] == 200.0


class TestSlowConversions:
    def test_threshold_filter_sort_and_limit(self):
        tracker = ConversionLatencyTracker()
        hours_ms = 3600 * 1000
        tracker.record_latency("meta", "click_to_conversion", 30 * hours_ms)
        tracker.record_latency("meta", "click_to_conversion", 50 * hours_ms)
        tracker.record_latency("meta", "click_to_conversion", 2 * hours_ms)  # fast
        slow = tracker.get_slow_conversions(platform="meta", threshold_hours=24)
        assert [s["latency_hours"] for s in slow] == [50.0, 30.0]
        assert (
            tracker.get_slow_conversions(threshold_hours=24, limit=1)[0][
                "latency_hours"
            ]
            == 50.0
        )


class TestCleanupAndDiagnostics:
    def test_cleanup_removes_only_stale_pending(self):
        tracker = ConversionLatencyTracker(max_pending_age_hours=1)
        tracker.start_tracking(
            "stale",
            "meta",
            "click_to_conversion",
            start_time=_now() - timedelta(hours=2),
        )
        tracker.start_tracking("fresh", "meta", "click_to_conversion")
        tracker.cleanup_stale_pending()
        assert tracker.get_pending_count() == {"meta": 1}

    def test_pending_count_by_platform(self):
        tracker = ConversionLatencyTracker()
        tracker.start_tracking("a", "meta", "click_to_conversion")
        tracker.start_tracking("b", "meta", "pixel_to_capi")
        tracker.start_tracking("c", "google", "click_to_conversion")
        assert tracker.get_pending_count() == {"meta": 2, "google": 1}

    def test_diagnostics_shape(self):
        tracker = ConversionLatencyTracker()
        tracker.record_latency("meta", "send_to_ack", 100.0)
        tracker.start_tracking("p", "google", "click_to_conversion")
        diag = tracker.get_diagnostics()
        assert diag["total_measurements"] == 1
        assert diag["pending_conversions"] == 1
        assert diag["platforms_tracked"] == ["meta"]
        assert diag["event_types_tracked"] == ["send_to_ack"]
        assert diag["oldest_measurement"] is not None
        assert diag["newest_measurement"] is not None

    def test_diagnostics_empty(self):
        diag = ConversionLatencyTracker().get_diagnostics()
        assert diag["total_measurements"] == 0
        assert diag["oldest_measurement"] is None


# =============================================================================
# Convenience integration functions (module singleton; unique ids/platforms)
# =============================================================================
class TestConvenienceFunctions:
    def test_click_to_conversion_roundtrip(self):
        track_click("ut_click_1", "ut_platform_a")
        latency = track_conversion("ut_click_1", "ut_platform_a")
        assert latency is not None
        assert latency >= 0

    def test_conversion_without_click_returns_none(self):
        assert track_conversion("ut_never_clicked", "ut_platform_a") is None

    def test_pixel_to_capi_roundtrip(self):
        track_pixel_fire("ut_px_1", "ut_platform_b")
        latency = track_capi_send("ut_px_1", "ut_platform_b")
        assert latency is not None

    def test_capi_ack_recorded(self):
        track_capi_ack("ut_ack_1", "ut_platform_c", latency_ms=123.0)
        stats = get_conversion_latency_stats(platform="ut_platform_c")
        # send_to_ack is a different event type, so conversion stats stay empty
        assert stats["sample_count"] == 0

    def test_latency_stats_in_hours(self):
        track_click("ut_click_h", "ut_platform_d")
        track_conversion("ut_click_h", "ut_platform_d")
        stats = get_conversion_latency_stats(platform="ut_platform_d")
        assert stats["sample_count"] == 1
        assert stats["avg_latency_hours"] >= 0
        assert set(stats) == {
            "avg_latency_hours",
            "median_latency_hours",
            "p95_latency_hours",
            "sample_count",
        }


# =============================================================================
# LatencyAnomalyDetector
# =============================================================================
def _stats(count=100, avg=100.0, p95=200.0, std=10.0):
    return LatencyStats(count=count, avg_ms=avg, p95_ms=p95, std_dev_ms=std)


class TestAnomalyDetector:
    def test_no_baseline_returns_empty(self):
        detector = LatencyAnomalyDetector()
        assert detector.detect_anomalies("meta", "click_to_conversion", _stats()) == []

    def test_small_baseline_returns_empty(self):
        detector = LatencyAnomalyDetector()
        detector.update_baseline("meta", "click_to_conversion", _stats(count=5))
        assert detector.detect_anomalies("meta", "click_to_conversion", _stats()) == []

    def test_p95_spike_detected_with_severity(self):
        detector = LatencyAnomalyDetector(sensitivity=2.0)
        detector.update_baseline("meta", "click_to_conversion", _stats())
        current = _stats(avg=100.0, p95=300.0)  # z = (300-200)/10 = 10
        anomalies = detector.detect_anomalies("meta", "click_to_conversion", current)
        assert len(anomalies) == 1
        a = anomalies[0]
        assert a.severity == "critical"
        assert a.deviation_percent == 50.0
        assert "P95 latency increased" in a.description

    def test_no_anomaly_within_sensitivity(self):
        detector = LatencyAnomalyDetector(sensitivity=2.0)
        detector.update_baseline("meta", "click_to_conversion", _stats())
        current = _stats(p95=210.0)  # z = 1
        assert detector.detect_anomalies("meta", "click_to_conversion", current) == []

    def test_avg_drift_detected(self):
        detector = LatencyAnomalyDetector()
        detector.update_baseline("meta", "click_to_conversion", _stats())
        current = _stats(avg=160.0, p95=200.0)  # +60% avg, p95 unchanged
        anomalies = detector.detect_anomalies("meta", "click_to_conversion", current)
        assert len(anomalies) == 1
        assert anomalies[0].severity == "medium"
        assert "drifting" in anomalies[0].description

    @pytest.mark.parametrize(
        "z,expected",
        [(4.5, "critical"), (3.2, "high"), (2.7, "medium"), (2.1, "low")],
    )
    def test_severity_thresholds(self, z, expected):
        assert LatencyAnomalyDetector()._calculate_severity(z) == expected

    def test_impact_estimates(self):
        detector = LatencyAnomalyDetector()
        assert "attribution window" in detector._estimate_impact(
            "click_to_conversion", 150.0
        )
        assert "platform status" in detector._estimate_impact("send_to_ack", 250.0)
        assert (
            detector._estimate_impact("pixel_to_capi", 10.0)
            == "Impact varies by use case"
        )

    def test_recommendations(self):
        detector = LatencyAnomalyDetector()
        assert "attribution window" in detector._get_recommendation(
            "click_to_conversion", 3.5
        )
        assert "API status" in detector._get_recommendation("send_to_ack", 3.5)


# =============================================================================
# LatencyForecaster
# =============================================================================
class TestForecaster:
    def test_insufficient_history_returns_empty(self):
        forecaster = LatencyForecaster()
        for _ in range(3):
            forecaster.record_stats("meta", "click_to_conversion", _stats())
        assert forecaster.forecast("meta", "click_to_conversion") == []

    def test_increasing_trend(self):
        forecaster = LatencyForecaster()
        for median in [100.0] * 7 + [200.0] * 7:
            forecaster.record_stats(
                "meta",
                "click_to_conversion",
                LatencyStats(count=10, median_ms=median, p95_ms=median * 2),
            )
        forecasts = forecaster.forecast("meta", "click_to_conversion", days_ahead=3)
        assert len(forecasts) == 3
        assert all(f.trend == "increasing" for f in forecasts)
        assert forecasts[0].predicted_p50_ms > 100.0

    def test_stable_trend_and_widening_interval(self):
        forecaster = LatencyForecaster()
        for _ in range(14):
            forecaster.record_stats(
                "meta",
                "click_to_conversion",
                LatencyStats(count=10, median_ms=100.0, p95_ms=200.0),
            )
        forecasts = forecaster.forecast("meta", "click_to_conversion", days_ahead=5)
        assert forecasts[0].trend == "stable"
        assert forecasts[0].predicted_p50_ms == 100.0
        # constant series -> stdev 0 -> CI equals the point estimates
        assert forecasts[0].confidence_interval_high == 200.0


# =============================================================================
# AttributionWindowOptimizer
# =============================================================================
class TestAttributionOptimizer:
    def test_no_data_assumes_full_coverage(self):
        optimizer = AttributionWindowOptimizer(ConversionLatencyTracker())
        assert optimizer.analyze_coverage("meta", 7) == 100.0

    def test_short_latencies_high_coverage(self):
        tracker = ConversionLatencyTracker()
        for _ in range(20):
            tracker.record_latency("meta", "click_to_conversion", 3600 * 1000.0)  # 1h
        optimizer = AttributionWindowOptimizer(tracker)
        assert optimizer.analyze_coverage("meta", 1) == 99.0

    def test_tiny_window_interpolates(self):
        tracker = ConversionLatencyTracker()
        thirty_days_ms = 30 * 24 * 3600 * 1000.0
        for _ in range(20):
            tracker.record_latency("meta", "click_to_conversion", thirty_days_ms)
        optimizer = AttributionWindowOptimizer(tracker)
        coverage = optimizer.analyze_coverage("meta", 1)
        assert 0 < coverage < 50.0

    def test_recommend_window_can_shrink(self):
        tracker = ConversionLatencyTracker()
        for _ in range(20):
            tracker.record_latency("meta", "click_to_conversion", 3600 * 1000.0)
        optimizer = AttributionWindowOptimizer(tracker)
        rec = optimizer.recommend_window("meta", target_coverage=95.0)
        assert rec.current_window_days == 7
        assert rec.recommended_window_days == 1
        assert "reduce" in rec.rationale

    def test_all_recommendations_cover_default_platforms(self):
        optimizer = AttributionWindowOptimizer(ConversionLatencyTracker())
        recs = optimizer.get_all_recommendations()
        assert {r.platform for r in recs} == set(
            AttributionWindowOptimizer.DEFAULT_WINDOWS
        )
