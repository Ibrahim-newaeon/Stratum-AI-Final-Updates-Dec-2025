# =============================================================================
# Stratum AI - LTV Forecasting unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.ltv_forecasting.

Pure LTV / unit-economics logic, no I/O. Covers the health + risk classifiers,
currency formatting, cohort / segment / distribution builders, and the
build_ltv_forecast entry point.
"""

import pytest

from app.analytics.logic import ltv_forecasting as ltv
from app.analytics.logic.ltv_forecasting import (
    LTVForecastResponse,
    SegmentForecast,
    build_ltv_forecast,
)

pytestmark = pytest.mark.unit


def _seg(platform, avg_ltv, customers, revenue, risk="low"):
    return SegmentForecast(
        segment=platform,
        segment_label=platform.title(),
        customer_count=customers,
        current_avg_ltv=avg_ltv,
        projected_12m_ltv=avg_ltv * 1.65,
        growth_rate=10.0,
        risk_level=risk,
        revenue_contribution_pct=50.0,
        total_revenue=revenue,
        avg_order_value=avg_ltv,
        cac=10.0,
        ltv_to_cac_ratio=avg_ltv / 10.0,
    )


# =============================================================================
# Classifiers + formatting
# =============================================================================
class TestClassifiers:
    @pytest.mark.parametrize(
        "ratio,health",
        [(5.0, "excellent"), (3.0, "good"), (1.5, "needs_attention"), (1.0, "poor")],
    )
    def test_ltv_health(self, ratio, health):
        assert ltv._ltv_health(ratio) == health

    @pytest.mark.parametrize(
        "ratio,risk",
        [(3.0, "low"), (2.0, "medium"), (1.0, "high"), (0.5, "critical")],
    )
    def test_risk_level(self, ratio, risk):
        assert ltv._risk_level(ratio) == risk

    @pytest.mark.parametrize(
        "value,expected",
        [(500.0, "$500"), (1500.0, "$1.5K"), (2_500_000.0, "$2.5M")],
    )
    def test_format_currency(self, value, expected):
        assert ltv._format_currency(value) == expected


# =============================================================================
# Cohorts
# =============================================================================
class TestCohorts:
    def test_zero_conversions_no_cohorts(self):
        data = {"meta": {"spend": 100, "revenue": 0, "conversions": 0}}
        assert ltv._build_cohorts(data, 0) == []

    def test_builds_six_declining_cohorts(self):
        data = {"meta": {"spend": 1000, "revenue": 5000, "conversions": 100}}
        cohorts = ltv._build_cohorts(data, 100)
        assert len(cohorts) == 6
        sizes = [c.size for c in cohorts]
        assert sizes == sorted(sizes, reverse=True)  # declining
        for c in cohorts:
            assert c.projected_ltv_12m >= c.avg_ltv  # projection grows


# =============================================================================
# Segments
# =============================================================================
class TestSegments:
    def test_sorted_by_revenue_and_skips_zero(self):
        data = {
            "meta": {"spend": 1000, "revenue": 5000, "conversions": 100},
            "google": {"spend": 2000, "revenue": 2000, "conversions": 50},
            "tiktok": {"spend": 500, "revenue": 0, "conversions": 0},  # skipped
        }
        segs = ltv._build_segments(data, total_revenue=7000)
        assert [s.segment for s in segs] == ["meta", "google"]
        meta = segs[0]
        assert meta.ltv_to_cac_ratio == pytest.approx(5.0, abs=0.01)  # 50/10
        assert meta.growth_rate == 25.0  # ltv_cac >= 5
        assert meta.risk_level == "low"

    def test_low_ltv_cac_negative_growth(self):
        data = {"meta": {"spend": 1000, "revenue": 1200, "conversions": 100}}
        segs = ltv._build_segments(data, total_revenue=1200)
        # ltv 12, cac 10 -> ltv_cac 1.2 -> growth -5
        assert segs[0].growth_rate == -5.0


# =============================================================================
# Distribution
# =============================================================================
class TestDistribution:
    def test_buckets_only_nonempty(self):
        segments = [
            _seg("meta", avg_ltv=75, customers=100, revenue=7500),  # $50-$100
            _seg("google", avg_ltv=300, customers=50, revenue=15000),  # $250-$500
        ]
        buckets = ltv._build_distribution(
            segments, total_customers=150, total_revenue=22500
        )
        labels = {b.bucket_label for b in buckets}
        assert "$50–$100" in labels
        assert "$250–$500" in labels
        # every returned bucket has customers
        assert all(b.count > 0 for b in buckets)


# =============================================================================
# build_ltv_forecast
# =============================================================================
class TestBuild:
    def test_empty_campaigns(self):
        resp = build_ltv_forecast([])
        assert isinstance(resp, LTVForecastResponse)
        assert resp.ltv_health == "poor"
        assert "No campaign data" in resp.summary

    def test_no_conversions(self):
        resp = build_ltv_forecast(
            [{"platform": "meta", "spend": 1000, "revenue": 0, "conversions": 0}]
        )
        assert resp.ltv_health == "poor"
        assert "No conversions" in resp.summary

    def test_full_forecast(self):
        campaigns = [
            {"platform": "meta", "spend": 1000, "revenue": 5000, "conversions": 100},
            {"platform": "google", "spend": 2000, "revenue": 2000, "conversions": 50},
        ]
        resp = build_ltv_forecast(campaigns)
        assert resp.total_customers == 150
        assert resp.overall_avg_ltv == pytest.approx(46.67, abs=0.1)  # 7000/150
        assert resp.avg_ltv_to_cac == pytest.approx(2.33, abs=0.05)  # ltv/cac
        assert resp.ltv_health == "needs_attention"
        assert resp.segments
        assert resp.cohorts
        assert resp.projected_avg_ltv_12m > resp.overall_avg_ltv

    def test_healthy_economics_summary(self):
        campaigns = [
            {"platform": "meta", "spend": 500, "revenue": 5000, "conversions": 100}
        ]
        resp = build_ltv_forecast(campaigns)
        # ltv 50, cac 5 -> 10x -> excellent
        assert resp.ltv_health == "excellent"
        assert "healthy" in resp.summary.lower()
