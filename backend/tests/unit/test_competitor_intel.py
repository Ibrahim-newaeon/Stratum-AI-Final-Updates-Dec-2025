# =============================================================================
# Stratum AI - Competitor Intel unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.competitor_intel.

Pure competitive-analysis logic, no I/O. Covers the competition/position/threat
classifiers, competition scoring, competitor-profile + opportunity generation,
and the build_competitor_intel entry point.
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

    @pytest.mark.parametrize(
        "sov,pos",
        [(25, "leader"), (15, "challenger"), (8, "mid-pack"), (3, "underdog")],
    )
    def test_market_position(self, sov, pos):
        assert ci._market_position(sov) == pos

    @pytest.mark.parametrize(
        "ratio,threat",
        [(3.0, "critical"), (1.5, "high"), (0.7, "medium"), (0.3, "low")],
    )
    def test_threat_level(self, ratio, threat):
        assert ci._threat_level(ratio) == threat


# =============================================================================
# Competition score
# =============================================================================
class TestCompetitionScore:
    def test_high_competition_low_roas(self):
        score = ci._estimate_competition_score(
            your_spend=100,
            market_spend=10000,
            your_roas=1.5,
            cpm=20,
            benchmark_cpm=10,
        )
        # cpm 40 + saturation ~29 + roas 30 -> ~99
        assert score == pytest.approx(99.0, abs=1.0)

    def test_low_competition_high_roas(self):
        score = ci._estimate_competition_score(
            your_spend=5000,
            market_spend=10000,
            your_roas=8.0,
            cpm=5,
            benchmark_cpm=10,
        )
        # low cpm ratio, high SOV, high ROAS -> low score
        assert score < 40

    def test_score_capped_at_100(self):
        score = ci._estimate_competition_score(
            your_spend=1,
            market_spend=1_000_000,
            your_roas=0.5,
            cpm=100,
            benchmark_cpm=1,
        )
        assert score <= 100


# =============================================================================
# Competitor generation
# =============================================================================
class TestCompetitors:
    def test_generates_five_profiles(self):
        comps = ci._generate_competitors({"meta": {"spend": 1000}}, total_spend=1000)
        assert len(comps) == 5
        names = {c.name for c in comps}
        assert "Apex Digital Group" in names
        # strongest competitor (2.5x spend) is "stronger" and high/critical threat
        apex = next(c for c in comps if c.name == "Apex Digital Group")
        assert apex.relative_strength == "stronger"
        assert apex.threat_level in {"high", "critical"}
        # weakest (0.3x) is weaker / low threat
        pinpoint = next(c for c in comps if c.name == "PinPoint Ads")
        assert pinpoint.relative_strength == "weaker"
        assert pinpoint.threat_level == "low"


# =============================================================================
# build_competitor_intel
# =============================================================================
class TestBuild:
    def test_empty(self):
        resp = build_competitor_intel([])
        assert isinstance(resp, CompetitorIntelResponse)
        assert resp.market_position == "unknown"
        assert "No campaign data" in resp.summary

    def test_full_structure(self):
        campaigns = [
            _campaign("meta", 1000, 3000, 50),
            _campaign("google", 800, 4000, 60),
        ]
        resp = build_competitor_intel(campaigns)
        assert resp.market_position in {"leader", "challenger", "mid-pack", "underdog"}
        assert resp.platform_competition
        assert len(resp.competitors) == 5
        # opportunities generated (untapped channels at minimum)
        assert resp.opportunities

    def test_underserved_channel_opportunity(self):
        # only on meta -> Google/TikTok/LinkedIn flagged untapped
        resp = build_competitor_intel([_campaign("meta", 1000, 3000, 50)])
        types = {o.opportunity_type for o in resp.opportunities}
        assert "underserved" in types
