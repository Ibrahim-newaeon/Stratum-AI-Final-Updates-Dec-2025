# =============================================================================
# Stratum AI - A/B Test Analysis unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.ab_test_analysis.

Pure A/B detection + significance logic, no I/O. Covers the two-proportion
z-test, name-similarity pairing, variant metric building, and the
build_ab_test_analysis entry point (empty / no-pairs / winner-found).
"""

import pytest

from app.analytics.logic import ab_test_analysis as ab
from app.analytics.logic.ab_test_analysis import (
    ABTestAnalysisResponse,
    build_ab_test_analysis,
)

pytestmark = pytest.mark.unit


def _campaign(
    name,
    platform="meta",
    spend=500,
    impressions=10000,
    clicks=1000,
    conversions=100,
    revenue=2000,
):
    return {
        "name": name,
        "platform": platform,
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "revenue": revenue,
    }


# =============================================================================
# Two-proportion z-test
# =============================================================================
class TestZTest:
    def test_zero_trials_returns_zero(self):
        assert ab._z_test_proportions(0, 0, 5, 100) == (0.0, 0.0)

    def test_degenerate_pool_returns_zero(self):
        # all conversions -> p_pool == 1 -> guarded
        assert ab._z_test_proportions(100, 100, 100, 100) == (0.0, 0.0)
        # no conversions -> p_pool == 0 -> guarded
        assert ab._z_test_proportions(0, 100, 0, 100) == (0.0, 0.0)

    def test_significant_difference_high_confidence(self):
        z, conf = ab._z_test_proportions(200, 1000, 100, 1000)
        assert z > 2.576
        assert conf >= 95

    def test_small_difference_low_confidence(self):
        _z, conf = ab._z_test_proportions(50, 100, 52, 100)
        assert conf < 80


# =============================================================================
# Name matching
# =============================================================================
class TestNamesMatch:
    @pytest.mark.parametrize(
        "a,b",
        [
            ("promo variant a", "promo variant b"),
            ("control group", "test group"),
            ("summer sale v1", "summer sale v2"),
            ("brand awareness campaign", "brand awareness promo"),  # 2/3 word overlap
        ],
    )
    def test_matches(self, a, b):
        assert ab._names_match(a, b) is True

    def test_no_match(self):
        assert ab._names_match("apples", "oranges") is False

    def test_empty_no_match(self):
        assert ab._names_match("", "anything") is False


# =============================================================================
# Variant building
# =============================================================================
class TestBuildVariant:
    def test_metrics_computed(self):
        v = ab._build_variant(
            _campaign(
                "X",
                spend=100,
                impressions=10000,
                clicks=500,
                conversions=50,
                revenue=300,
            ),
            "A",
            0,
        )
        assert v.ctr == 5.0  # 500/10000
        assert v.cvr == 10.0  # 50/500
        assert v.cpa == 2.0  # 100/50
        assert v.roas == 3.0  # 300/100


# =============================================================================
# build_ab_test_analysis
# =============================================================================
class TestBuild:
    def test_empty(self):
        resp = build_ab_test_analysis([])
        assert isinstance(resp, ABTestAnalysisResponse)
        assert "No campaign data" in resp.summary

    def test_no_pairs_single_campaign(self):
        resp = build_ab_test_analysis([_campaign("Solo Campaign")])
        assert "No A/B test pairs detected" in resp.summary
        assert resp.insights

    def test_winner_found(self):
        campaigns = [
            _campaign("Promo Variant A", clicks=1000, conversions=200, spend=500),
            _campaign("Promo Variant B", clicks=1000, conversions=120, spend=500),
        ]
        resp = build_ab_test_analysis(campaigns)
        assert resp.total_tests == 1
        assert resp.winners_found == 1
        test = resp.tests[0]
        assert test.status == "winner_found"
        assert test.winning_variant == "A"  # higher CVR
        assert test.confidence >= 95
        assert test.min_sample_reached is True

    def test_needs_more_data_when_low_conversions(self):
        campaigns = [
            _campaign("Test Variant A", clicks=200, conversions=20, spend=100),
            _campaign("Test Variant B", clicks=200, conversions=10, spend=100),
        ]
        resp = build_ab_test_analysis(campaigns)
        # below MIN_SAMPLE_SIZE (100 conversions) -> not a confirmed winner
        assert resp.tests[0].min_sample_reached is False
