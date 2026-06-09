# =============================================================================
# Stratum AI - Predictive Budget unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.predictive_budget.

Pure budget-scoring + trust-gate logic, no I/O. Covers campaign scoring,
action determination, reasoning, recommended-spend math, risk factors, and the
build_predictive_budget entry point (including trust-gate states).
"""

import pytest

from app.analytics.logic import predictive_budget as pb
from app.analytics.logic.predictive_budget import (
    PredictiveBudgetResponse,
    build_predictive_budget,
)

pytestmark = pytest.mark.unit


def _campaign(cid, name, spend, revenue, conversions, platform="meta"):
    return {
        "id": cid,
        "name": name,
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Campaign scoring
# =============================================================================
class TestCampaignScore:
    def test_above_average_scores_positive(self):
        s = pb._calculate_campaign_score(
            spend=100,
            revenue=500,
            conversions=50,
            avg_spend=100,
            avg_revenue=250,
            avg_conversions=25,
        )
        assert s["roas"] == 5.0
        assert s["cpa"] == 2.0
        assert s["score"] == pytest.approx(0.8, abs=0.01)
        assert s["confidence"] == pytest.approx(0.96, abs=0.01)

    def test_below_average_scores_negative(self):
        s = pb._calculate_campaign_score(
            spend=100,
            revenue=80,
            conversions=2,
            avg_spend=100,
            avg_revenue=400,
            avg_conversions=40,
        )
        assert s["score"] < 0

    def test_zero_spend_roas_zero(self):
        s = pb._calculate_campaign_score(0, 0, 0, 100, 200, 20)
        assert s["roas"] == 0.0
        assert s["cpa"] == 0.0


# =============================================================================
# Action determination
# =============================================================================
class TestDetermineAction:
    def test_scale(self):
        assert pb._determine_action(score=0.5, confidence=0.8, roas=5.0) == "scale"

    def test_pause_when_roas_critical(self):
        assert pb._determine_action(score=-0.5, confidence=0.6, roas=0.3) == "pause"

    def test_reduce_when_below_but_not_critical(self):
        assert pb._determine_action(score=-0.5, confidence=0.6, roas=2.0) == "reduce"

    def test_maintain_low_score(self):
        assert pb._determine_action(score=0.1, confidence=0.9, roas=3.0) == "maintain"

    def test_maintain_low_confidence(self):
        # strong score but not enough confidence to scale
        assert pb._determine_action(score=0.5, confidence=0.3, roas=3.0) == "maintain"


# =============================================================================
# Reasoning
# =============================================================================
class TestReasoning:
    def test_scale_reasoning(self):
        r = pb._generate_reasoning("scale", 5.0, 0.8, 2.0, 0.5, 30)
        assert "increasing budget by 15-20%" in r

    def test_reduce_reasoning(self):
        r = pb._generate_reasoning("reduce", 1.2, -0.5, 40.0, -0.3, 10)
        assert "reducing budget by 15-20%" in r

    def test_pause_reasoning(self):
        r = pb._generate_reasoning("pause", 0.3, -0.8, 200.0, -0.9, 2)
        assert "pausing" in r.lower()

    def test_maintain_reasoning(self):
        r = pb._generate_reasoning("maintain", 2.5, 0.0, 20.0, 0.0, 15)
        assert "Maintain current budget" in r


# =============================================================================
# Recommended spend
# =============================================================================
class TestRecommendedSpend:
    def test_scale_increases(self):
        out = pb._calculate_recommended_spend(1000, "scale", 0.5, 0.9)
        assert out == pytest.approx(1202.5, abs=0.5)
        assert out > 1000

    def test_reduce_decreases(self):
        out = pb._calculate_recommended_spend(1000, "reduce", -0.5, 0.8)
        assert out == pytest.approx(880.0, abs=0.5)
        assert out < 1000

    def test_pause_is_zero(self):
        assert pb._calculate_recommended_spend(1000, "pause", -0.9, 0.7) == 0.0

    def test_maintain_unchanged(self):
        assert pb._calculate_recommended_spend(1000, "maintain", 0.1, 0.9) == 1000


# =============================================================================
# Risk factors
# =============================================================================
class TestRiskFactors:
    def test_all_risks_flagged(self):
        risks = pb._identify_risk_factors(
            roas=0.5, conversions=5, confidence=0.5, spend=30
        )
        joined = " ".join(risks)
        assert "Low conversion volume" in joined
        assert "confidence threshold" in joined
        assert "below breakeven" in joined
        assert "learning phase" in joined

    def test_healthy_campaign_no_risks(self):
        assert (
            pb._identify_risk_factors(
                roas=3.0, conversions=50, confidence=0.9, spend=1000
            )
            == []
        )


# =============================================================================
# build_predictive_budget — trust gate
# =============================================================================
class TestTrustGate:
    def test_empty_blocks(self):
        resp = build_predictive_budget([], signal_health_score=90)
        assert isinstance(resp, PredictiveBudgetResponse)
        assert resp.trust_gate_status == "block"
        assert resp.autopilot_eligible is False
        assert resp.total_campaigns_analyzed == 0

    def test_healthy_signal_passes(self):
        resp = build_predictive_budget(
            [_campaign(1, "A", 1000, 5000, 100)], signal_health_score=80
        )
        assert resp.trust_gate_status == "pass"

    def test_degraded_signal_holds(self):
        resp = build_predictive_budget(
            [_campaign(1, "A", 1000, 5000, 100)], signal_health_score=50
        )
        assert resp.trust_gate_status == "hold"
        assert resp.autopilot_eligible is False  # hold never auto-eligible

    def test_unhealthy_signal_blocks(self):
        resp = build_predictive_budget(
            [_campaign(1, "A", 1000, 5000, 100)], signal_health_score=20
        )
        assert resp.trust_gate_status == "block"

    def test_custom_threshold(self):
        # threshold 85 means health 80 is no longer a pass
        resp = build_predictive_budget(
            [_campaign(1, "A", 1000, 5000, 100)],
            signal_health_score=80,
            autopilot_threshold=85,
        )
        assert resp.trust_gate_status == "hold"


# =============================================================================
# build_predictive_budget — recommendations
# =============================================================================
class TestBuildRecommendations:
    def _mixed(self):
        return [
            _campaign(1, "Strong", 1000, 8000, 200),  # 8x ROAS, well above avg
            _campaign(2, "Weak", 1000, 800, 20),  # 0.8x ROAS, below avg
        ]

    def test_scale_candidate_detected(self):
        resp = build_predictive_budget(self._mixed(), signal_health_score=80)
        assert resp.scale_candidates >= 1
        # scale recommendations sort to the front
        assert resp.recommendations[0].action == "scale"
        assert (
            resp.recommendations[0].recommended_spend
            > resp.recommendations[0].current_spend
        )

    def test_zero_spend_campaign_skipped(self):
        campaigns = [
            _campaign(1, "Real", 1000, 5000, 100),
            _campaign(2, "Empty", 0, 0, 0),
        ]
        resp = build_predictive_budget(campaigns, signal_health_score=80)
        assert resp.total_campaigns_analyzed == 1

    def test_forecast_present_with_spend(self):
        resp = build_predictive_budget(self._mixed(), signal_health_score=80)
        assert resp.forecast is not None
        assert resp.forecast.projected_spend > 0
        assert resp.forecast.confidence_level in {"high", "medium", "low"}

    def test_autopilot_eligible_requires_pass_and_confidence(self):
        resp = build_predictive_budget(self._mixed(), signal_health_score=80)
        assert resp.autopilot_eligible == (
            resp.trust_gate_status == "pass" and resp.avg_confidence >= 0.6
        )
