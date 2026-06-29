# =============================================================================
# Stratum AI - EMQ Calculation unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.emq_calculation.

Core Trust Engine module — EMQ (Event Match Quality) drivers and composite
scoring. Pure math + dataclasses, no I/O. Covers each of the five weighted
drivers, the composite score + confidence bands, cross-platform aggregation,
autopilot mode determination, and event-loss percentage.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.logic.emq_calculation import (
    DriverStatus,
    DriverTrend,
    PlatformMetrics,
    calculate_aggregate_emq,
    calculate_attribution_accuracy,
    calculate_conversion_latency,
    calculate_data_freshness,
    calculate_emq_score,
    calculate_event_loss_percentage,
    calculate_event_match_rate,
    calculate_pixel_coverage,
    determine_autopilot_mode,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


def _good_metrics(**kw) -> PlatformMetrics:
    base = dict(
        platform="meta",
        pixel_events=1000,
        capi_events=1000,
        matched_events=950,
        pages_with_pixel=10,
        total_pages=10,
        events_configured=10,
        events_expected=10,
        avg_conversion_latency_hours=0.5,
        platform_conversions=100,
        ga4_conversions=100,
        platform_revenue=1000.0,
        ga4_revenue=1000.0,
        last_event_at=NOW,
    )
    base.update(kw)
    return PlatformMetrics(**base)


# =============================================================================
# Event match rate (30%)
# =============================================================================
class TestEventMatchRate:
    def test_no_events_is_critical(self):
        d = calculate_event_match_rate(PlatformMetrics(platform="meta"))
        assert d.value == 0.0
        assert d.status == DriverStatus.CRITICAL
        assert d.weight == 0.30
        assert "No events" in d.details

    def test_explicit_matched_events(self):
        d = calculate_event_match_rate(
            PlatformMetrics(
                platform="m", pixel_events=100, capi_events=90, matched_events=95
            )
        )
        assert d.value == 95.0
        assert d.status == DriverStatus.GOOD

    def test_estimated_from_overlap_warning(self):
        d = calculate_event_match_rate(
            PlatformMetrics(platform="m", pixel_events=80, capi_events=100)
        )
        assert d.value == 80.0
        assert d.status == DriverStatus.WARNING

    def test_low_match_is_critical(self):
        d = calculate_event_match_rate(
            PlatformMetrics(platform="m", pixel_events=50, capi_events=100)
        )
        assert d.value == 50.0
        assert d.status == DriverStatus.CRITICAL


# =============================================================================
# Pixel coverage (25%)
# =============================================================================
class TestPixelCoverage:
    def test_no_data_defaults_good(self):
        d = calculate_pixel_coverage(PlatformMetrics(platform="m"))
        assert d.value == 90.0
        assert d.status == DriverStatus.GOOD

    def test_combined_coverage_average(self):
        d = calculate_pixel_coverage(
            PlatformMetrics(
                platform="m",
                pages_with_pixel=9,
                total_pages=10,
                events_configured=8,
                events_expected=10,
            )
        )
        assert d.value == 85.0  # (90 + 80) / 2
        assert d.status == DriverStatus.WARNING

    def test_full_coverage_good(self):
        d = calculate_pixel_coverage(
            PlatformMetrics(
                platform="m",
                pages_with_pixel=10,
                total_pages=10,
                events_configured=10,
                events_expected=10,
            )
        )
        assert d.value == 100.0
        assert d.status == DriverStatus.GOOD

    def test_low_coverage_critical(self):
        d = calculate_pixel_coverage(
            PlatformMetrics(platform="m", pages_with_pixel=5, total_pages=10)
        )
        assert d.value == 50.0
        assert d.status == DriverStatus.CRITICAL


# =============================================================================
# Conversion latency (20%)
# =============================================================================
class TestConversionLatency:
    @pytest.mark.parametrize(
        "hours,expected,status",
        [
            (0.0, 100.0, DriverStatus.GOOD),
            (0.5, 95.0, DriverStatus.GOOD),
            (8.0, 55.0, DriverStatus.WARNING),
            (18.0, 20.0, DriverStatus.CRITICAL),
            (30.0, 0.0, DriverStatus.CRITICAL),
        ],
    )
    def test_latency_bands(self, hours, expected, status):
        d = calculate_conversion_latency(
            PlatformMetrics(platform="m", avg_conversion_latency_hours=hours)
        )
        assert d.value == pytest.approx(expected, abs=0.2)
        assert d.status == status
        assert d.weight == 0.20


# =============================================================================
# Attribution accuracy (15%)
# =============================================================================
class TestAttributionAccuracy:
    def test_perfect_alignment(self):
        d = calculate_attribution_accuracy(
            PlatformMetrics(
                platform="m",
                platform_conversions=100,
                ga4_conversions=100,
                platform_revenue=1000,
                ga4_revenue=1000,
            )
        )
        assert d.value == 100.0
        assert d.status == DriverStatus.GOOD

    def test_both_zero_no_variance(self):
        d = calculate_attribution_accuracy(PlatformMetrics(platform="m"))
        assert d.value == 100.0

    def test_ga4_zero_platform_nonzero_max_variance(self):
        d = calculate_attribution_accuracy(
            PlatformMetrics(platform="m", platform_conversions=50, platform_revenue=500)
        )
        # conv + rev variance both 1.0 -> value 100 - 200 -> clamped 0
        assert d.value == 0.0
        assert d.status == DriverStatus.CRITICAL

    def test_moderate_variance_warning(self):
        d = calculate_attribution_accuracy(
            PlatformMetrics(
                platform="m",
                platform_conversions=120,
                ga4_conversions=100,
                platform_revenue=1200,
                ga4_revenue=1000,
            )
        )
        # 20% variance each -> avg 0.2 -> 100 - 40 = 60
        assert d.value == 60.0
        assert d.status == DriverStatus.WARNING


# =============================================================================
# Data freshness (10%)
# =============================================================================
class TestDataFreshness:
    def test_unknown_update_warning(self):
        d = calculate_data_freshness(PlatformMetrics(platform="m"), now=NOW)
        assert d.value == 50.0
        assert d.status == DriverStatus.WARNING

    def test_recent_is_perfect(self):
        d = calculate_data_freshness(
            PlatformMetrics(platform="m", last_event_at=NOW), now=NOW
        )
        assert d.value == 100.0
        assert d.status == DriverStatus.GOOD

    def test_twelve_hours_old_warning(self):
        m = PlatformMetrics(platform="m", last_event_at=NOW - timedelta(hours=12))
        d = calculate_data_freshness(m, now=NOW)
        assert d.value == pytest.approx(66.7, abs=0.3)
        assert d.status == DriverStatus.WARNING

    def test_very_stale_critical(self):
        m = PlatformMetrics(platform="m", last_event_at=NOW - timedelta(hours=48))
        d = calculate_data_freshness(m, now=NOW)
        assert d.value == 0.0
        assert d.status == DriverStatus.CRITICAL

    def test_naive_datetime_handled(self):
        naive_now = datetime(2026, 6, 9, 12, 0, 0)
        m = PlatformMetrics(
            platform="m", last_event_at=datetime(2026, 6, 9, 9, 0, 0)
        )  # 3h before, naive
        d = calculate_data_freshness(m, now=naive_now)
        assert d.value == pytest.approx(92.0, abs=0.2)


# =============================================================================
# Composite EMQ score
# =============================================================================
class TestEmqScore:
    def test_high_quality_reliable(self):
        result = calculate_emq_score(_good_metrics(), now=NOW)
        assert result.score == pytest.approx(97.5, abs=0.5)
        assert result.confidence_band == "reliable"
        assert len(result.drivers) == 5
        assert result.previous_score is None
        # weights sum to 1.0
        assert sum(d.weight for d in result.drivers) == pytest.approx(1.0)

    def test_confidence_band_directional(self):
        # moderate metrics -> score in [60, 80)
        m = _good_metrics(
            matched_events=0,
            pixel_events=70,
            capi_events=100,
            avg_conversion_latency_hours=8.0,
            platform_conversions=120,
            ga4_conversions=100,
        )
        result = calculate_emq_score(m, now=NOW)
        assert 60 <= result.score < 80
        assert result.confidence_band == "directional"

    def test_unsafe_band_low_score(self):
        poor = PlatformMetrics(
            platform="m",
            pixel_events=10,
            capi_events=100,
            avg_conversion_latency_hours=30,
            last_event_at=NOW - timedelta(hours=48),
        )
        result = calculate_emq_score(poor, now=NOW)
        assert result.confidence_band == "unsafe"

    def test_trend_up_with_improving_previous(self):
        current = _good_metrics()
        previous = _good_metrics(matched_events=700)  # lower match rate before
        result = calculate_emq_score(current, previous_metrics=previous, now=NOW)
        assert result.previous_score is not None
        assert result.previous_score < result.score
        match_driver = next(d for d in result.drivers if d.name == "Event Match Rate")
        assert match_driver.trend == DriverTrend.UP


# =============================================================================
# Aggregate EMQ
# =============================================================================
class TestAggregate:
    def test_empty_is_unsafe_zero(self):
        agg = calculate_aggregate_emq([])
        assert agg.score == 0.0
        assert agg.confidence_band == "unsafe"
        assert agg.drivers == []

    def test_averages_platforms_and_worst_status_wins(self):
        good = calculate_emq_score(_good_metrics(), now=NOW)
        weak = calculate_emq_score(
            PlatformMetrics(
                platform="g",
                pixel_events=50,
                capi_events=100,
                avg_conversion_latency_hours=30,
                last_event_at=NOW - timedelta(hours=48),
            ),
            now=NOW,
        )
        agg = calculate_aggregate_emq([good, weak])
        assert agg.score == pytest.approx((good.score + weak.score) / 2, abs=0.1)
        # at least one driver should reflect the worst (critical) platform
        assert any(d.status == DriverStatus.CRITICAL for d in agg.drivers)


# =============================================================================
# Autopilot mode
# =============================================================================
class TestAutopilotMode:
    @pytest.mark.parametrize(
        "score,mode",
        [(85, "normal"), (70, "limited"), (50, "cuts_only"), (30, "frozen")],
    )
    def test_modes(self, score, mode):
        result_mode, reason = determine_autopilot_mode(score)
        assert result_mode == mode
        assert isinstance(reason, str) and reason


# =============================================================================
# Event loss
# =============================================================================
class TestEventLoss:
    def test_no_expected_is_zero(self):
        assert calculate_event_loss_percentage(PlatformMetrics(platform="m")) == 0.0

    def test_loss_computed(self):
        m = PlatformMetrics(
            platform="m",
            events_expected=1000,
            pixel_events=400,
            capi_events=400,
            matched_events=100,
        )
        # received = 400 + 400 - 100 = 700 -> loss 30%
        assert calculate_event_loss_percentage(m) == pytest.approx(30.0, abs=0.1)

    def test_no_loss_when_received_exceeds_expected(self):
        m = PlatformMetrics(
            platform="m",
            events_expected=100,
            pixel_events=200,
            capi_events=200,
            matched_events=0,
        )
        assert calculate_event_loss_percentage(m) == 0.0
