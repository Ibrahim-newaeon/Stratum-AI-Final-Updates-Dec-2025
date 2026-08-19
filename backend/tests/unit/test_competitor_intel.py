# =============================================================================
# Stratum AI - Competitor Intel unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.competitor_intel.

Pure competitive-analysis logic, no I/O. Covers the competition-level
classifier, competition scoring, opportunity generation, and the
build_competitor_intel entry point.

The market-position and threat-level classifiers, the competitor-profile
generator, and the saturation term in the score are all gone: each was computed
from ``your_spend * MARKET_MULTIPLIER``, so none of them carried information
about anything outside the tenant's own campaigns. See
``test_competitor_intel_no_fabrication.py`` for what replaced them.
"""

import pytest

from app.analytics.logic import competitor_intel as ci
from app.analytics.logic.competitor_intel import (
    CompetitorIntelResponse,
    build_competitor_intel,
)

pytestmark = pytest.mark.unit


def _campaign(platform, spend, revenue, conversions, impressions=100000, clicks=2000):
    return {
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
        "impressions": impressions,
        "clicks": clicks,
    }


# =============================================================================
# Classifiers
# =============================================================================
class TestClassifiers:
    @pytest.mark.parametrize(
        "score,level",
        [(80, "saturated"), (60, "high"), (35, "medium"), (10, "low")],
    )
    def test_competition_level(self, score, level):
        assert ci._competition_level(score) == level


# =============================================================================
# Competition score
# =============================================================================
class TestCompetitionScore:
    def test_high_competition_low_roas(self):
        score = ci._estimate_competition_score(
            your_roas=1.5,
            cpm=20,
            benchmark_cpm=10,
        )
        # cpm ratio 2.0 -> min(70, 60) = 60, roas < 2 -> 40
        assert score == pytest.approx(100.0, abs=1.0)

    def test_low_competition_high_roas(self):
        score = ci._estimate_competition_score(
            your_roas=8.0,
            cpm=5,
            benchmark_cpm=10,
        )
        # cpm ratio 0.5 -> 17.5, roas >= 5 -> 5
        assert score < 40

    def test_score_capped_at_100(self):
        score = ci._estimate_competition_score(
            your_roas=0.5,
            cpm=100,
            benchmark_cpm=1,
        )
        assert score <= 100


# =============================================================================
# build_competitor_intel
# =============================================================================
class TestBuild:
    def test_empty(self):
        resp = build_competitor_intel([])
        assert isinstance(resp, CompetitorIntelResponse)
        assert resp.platform_competition == []
        assert "No campaign data" in resp.summary

    def test_full_structure(self):
        campaigns = [
            _campaign("meta", 1000, 3000, 50),
            _campaign("google", 800, 4000, 60),
        ]
        resp = build_competitor_intel(campaigns)
        assert resp.platform_competition
        assert {p.platform for p in resp.platform_competition} == {"Meta", "Google"}
        assert 0 <= resp.competitive_pressure <= 100
        # opportunities generated (untapped channels at minimum)
        assert resp.opportunities

    def test_underserved_channel_opportunity(self):
        # only on meta -> Google/TikTok/LinkedIn flagged untapped
        resp = build_competitor_intel([_campaign("meta", 1000, 3000, 50)])
        types = {o.opportunity_type for o in resp.opportunities}
        assert "underserved" in types
