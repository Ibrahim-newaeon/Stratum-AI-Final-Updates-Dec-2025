# =============================================================================
# Stratum AI - Creative Scoring unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.creative_scoring.

Deterministic scoring math + narrative assembly, no I/O. Covers the grade /
fatigue / status classifiers, the per-metric scorers, fatigue estimation, and
the build_creative_scoring entry point.
"""

import pytest

from app.analytics.logic import creative_scoring as cs
from app.analytics.logic.creative_scoring import (
    CreativeScoringResponse,
    build_creative_scoring,
)

pytestmark = pytest.mark.unit


def _campaign(name, platform, spend, revenue, conversions, impressions, clicks, days):
    return {
        "name": name,
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
        "impressions": impressions,
        "clicks": clicks,
        "days_running": days,
    }


# =============================================================================
# Classifiers
# =============================================================================
class TestClassifiers:
    @pytest.mark.parametrize(
        "score,grade",
        [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (20, "F")],
    )
    def test_grade(self, score, grade):
        assert cs._grade(score) == grade

    @pytest.mark.parametrize(
        "score,level",
        [(75, "high"), (50, "medium"), (20, "low"), (5, "none")],
    )
    def test_fatigue_level(self, score, level):
        assert cs._fatigue_level(score) == level

    def test_status_fatigue_overrides_score(self):
        # high fatigue -> fatigued even with a great score
        assert cs._creative_status(90, 75) == "fatigued"

    def test_status_winner(self):
        assert cs._creative_status(80, 10) == "winner"

    def test_status_underperforming(self):
        assert cs._creative_status(30, 10) == "underperforming"

    def test_status_active(self):
        assert cs._creative_status(50, 10) == "active"


# =============================================================================
# Per-metric scorers
# =============================================================================
class TestScorers:
    @pytest.mark.parametrize(
        "ctr,expected",
        [(2.0, 100), (1.5, 85), (1.0, 70), (0.7, 50), (0.4, 30)],
    )
    def test_score_ctr_bands(self, ctr, expected):
        # platform "default" benchmark is 1.0, so ratio == ctr
        assert cs._score_ctr(ctr, "default") == expected

    def test_score_ctr_floor_is_proportional(self):
        assert cs._score_ctr(0.2, "default") == pytest.approx(10.0)

    @pytest.mark.parametrize(
        "cvr,expected",
        [(8, 100), (5, 85), (3, 70), (1.5, 50), (0.5, 30)],
    )
    def test_score_cvr_bands(self, cvr, expected):
        assert cs._score_cvr(cvr) == expected

    @pytest.mark.parametrize(
        "roas,expected",
        [(8, 100), (5, 85), (3, 70), (2, 55), (1, 35)],
    )
    def test_score_roas_bands(self, roas, expected):
        assert cs._score_roas(roas) == expected

    def test_score_roas_floor(self):
        assert cs._score_roas(0.5) == pytest.approx(15.0)

    def test_score_cpa_zero_avg_returns_midpoint(self):
        assert cs._score_cpa(50, 0) == 50

    @pytest.mark.parametrize(
        "ratio,expected",
        [(0.5, 100), (0.7, 85), (1.0, 65), (1.3, 45), (1.8, 25), (3.0, 10)],
    )
    def test_score_cpa_bands(self, ratio, expected):
        assert cs._score_cpa(ratio * 100, 100) == expected


# =============================================================================
# Fatigue estimation
# =============================================================================
class TestFatigue:
    def test_zero_days_or_impressions_no_fatigue(self):
        assert cs._estimate_fatigue(1000, 0, 30) == 0
        assert cs._estimate_fatigue(1000, 100000, 0) == 0

    def test_maxed_out_fatigue(self):
        # 30+ days, >=50k daily impressions, >=10k spend -> 40+30+30 = 100
        f = cs._estimate_fatigue(spend=10000, impressions=30 * 50000, days=30)
        assert f == pytest.approx(100.0)

    def test_low_run_low_fatigue(self):
        f = cs._estimate_fatigue(spend=1000, impressions=70000, days=7)
        assert 0 < f < 30


# =============================================================================
# build_creative_scoring
# =============================================================================
class TestBuildCreativeScoring:
    def test_empty_returns_grade_f(self):
        resp = build_creative_scoring([])
        assert isinstance(resp, CreativeScoringResponse)
        assert resp.overall_grade == "F"
        assert "No campaign data" in resp.summary

    def test_single_winner(self):
        resp = build_creative_scoring(
            [_campaign("Star", "meta", 1000, 10000, 200, 20000, 2000, 7)]
        )
        assert resp.total_creatives == 1
        cr = resp.creatives[0]
        assert cr.status == "winner"
        assert cr.grade == "A"
        assert "Scale budget" in cr.recommendation
        assert resp.winners_count == 1

    def test_mixed_portfolio_classification(self):
        campaigns = [
            _campaign("Winner", "meta", 1000, 10000, 200, 20000, 2000, 7),
            _campaign("Tired", "google", 10000, 25000, 200, 3_000_000, 15000, 60),
            _campaign("Weak", "tiktok", 2000, 200, 2, 500000, 500, 10),
        ]
        resp = build_creative_scoring(campaigns)
        assert resp.total_creatives == 3
        assert resp.winners_count == 1
        assert resp.fatigued_count == 1
        assert resp.underperforming_count == 1
        # sorted by score descending
        scores = [c.overall_score for c in resp.creatives]
        assert scores == sorted(scores, reverse=True)
        # three platforms -> three summaries
        assert len(resp.platform_summaries) == 3
        # majority need attention -> refresh insight present
        assert resp.refresh_needed_pct > 50
        assert any("Sprint" in i.action_label for i in resp.insights)

    def test_all_healthy_emits_positive_insight(self):
        campaigns = [
            _campaign("A", "meta", 1000, 8000, 150, 20000, 1500, 5),
            _campaign("B", "meta", 1200, 9000, 160, 22000, 1600, 6),
        ]
        resp = build_creative_scoring(campaigns)
        assert resp.fatigued_count == 0
        assert resp.underperforming_count == 0
        assert any(i.severity == "positive" for i in resp.insights)

    def test_platform_name_is_titlecased(self):
        resp = build_creative_scoring(
            [_campaign("X", "google_ads", 1000, 5000, 100, 20000, 1000, 10)]
        )
        assert resp.creatives[0].platform == "Google Ads"
