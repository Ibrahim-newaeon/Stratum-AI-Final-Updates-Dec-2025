# =============================================================================
# Stratum AI - Trust Gate unit tests
# =============================================================================
"""Unit tests for app.stratum.core.trust_gate.

Core Trust Engine — the gate that decides PASS/HOLD/BLOCK for each automation
action based on signal health. Pure logic, no I/O. Covers action-risk
thresholds, the pass/hold/block decision, always-allowed safety actions,
allowed/restricted action sets, recommendations, result serialization, and the
autopilot-mode helper.
"""

import pytest

from app.stratum.core.trust_gate import (
    GateDecision,
    TrustGate,
    evaluate_automation,
    get_autopilot_mode,
)
from app.stratum.models import AutomationAction, Platform, SignalHealth

pytestmark = pytest.mark.unit


def _health(score, emq=80.0, fresh=80.0, var=80.0, anom=80.0, issues=None, cdp=None):
    status = "healthy" if score >= 70 else ("degraded" if score >= 40 else "critical")
    return SignalHealth(
        overall_score=score,
        emq_score=emq,
        freshness_score=fresh,
        variance_score=var,
        anomaly_score=anom,
        cdp_emq_score=cdp,
        status=status,
        issues=issues or [],
    )


def _action(action_type):
    return AutomationAction(
        platform=Platform.META,
        account_id="acc_1",
        entity_type="campaign",
        entity_id="c_1",
        action_type=action_type,
    )


@pytest.fixture
def gate() -> TrustGate:
    return TrustGate()


# =============================================================================
# Thresholds
# =============================================================================
class TestThresholds:
    @pytest.mark.parametrize(
        "action_type,threshold",
        [
            ("increase_budget", 80.0),  # high-risk
            ("reduce_budget", 60.0),  # conservative
            ("update_budget", 70.0),  # standard
        ],
    )
    def test_threshold_for_action(self, gate, action_type, threshold):
        assert gate._get_threshold_for_action(_action(action_type)) == threshold


# =============================================================================
# evaluate() decisions
# =============================================================================
class TestEvaluate:
    def test_always_allowed_passes_regardless(self, gate):
        r = gate.evaluate(_health(10), _action("pause_all"))
        assert r.decision == GateDecision.PASS

    @pytest.mark.parametrize(
        "score,decision",
        [(85, GateDecision.PASS), (75, GateDecision.HOLD), (30, GateDecision.BLOCK)],
    )
    def test_high_risk_action(self, gate, score, decision):
        r = gate.evaluate(_health(score), _action("increase_budget"))
        assert r.decision == decision

    @pytest.mark.parametrize(
        "score,decision",
        [(75, GateDecision.PASS), (50, GateDecision.HOLD), (30, GateDecision.BLOCK)],
    )
    def test_standard_action(self, gate, score, decision):
        r = gate.evaluate(_health(score), _action("update_budget"))
        assert r.decision == decision

    @pytest.mark.parametrize(
        "score,decision",
        [(65, GateDecision.PASS), (50, GateDecision.HOLD), (30, GateDecision.BLOCK)],
    )
    def test_conservative_action(self, gate, score, decision):
        r = gate.evaluate(_health(score), _action("reduce_budget"))
        assert r.decision == decision

    def test_batch(self, gate):
        results = gate.evaluate_batch(
            _health(85), [_action("update_budget"), _action("increase_budget")]
        )
        assert len(results) == 2


# =============================================================================
# Allowed / restricted action sets
# =============================================================================
class TestAllowedActions:
    def test_excellent_allows_high_risk(self, gate):
        allowed, _ = gate.get_allowed_actions(_health(85))
        assert "increase_budget" in allowed
        assert "update_budget" in allowed

    def test_good_allows_standard_not_high_risk(self, gate):
        allowed, restricted = gate.get_allowed_actions(_health(75))
        assert "update_budget" in allowed
        assert "increase_budget" in restricted

    def test_degraded_allows_only_conservative(self, gate):
        allowed, restricted = gate.get_allowed_actions(_health(50))
        assert "reduce_budget" in allowed
        assert "update_budget" in restricted

    def test_critical_only_safety_actions(self, gate):
        allowed, restricted = gate.get_allowed_actions(_health(30))
        assert "pause_all" in allowed
        assert "reduce_budget" in restricted


# =============================================================================
# Recommendations + serialization
# =============================================================================
class TestResult:
    def test_block_recommends_manual_review(self, gate):
        r = gate.evaluate(
            _health(30, issues=["EMQ score below target"]), _action("update_budget")
        )
        assert any("Manual review" in rec for rec in r.recommendations)

    def test_to_dict_shape(self, gate):
        r = gate.evaluate(_health(85, cdp=90), _action("update_budget"))
        d = r.to_dict()
        assert d["decision"] == "pass"
        assert d["signalHealth"]["score"] == 85
        assert d["signalHealth"]["hasCdpData"] is True
        assert d["action"]["type"] == "update_budget"
        assert "recommendations" in d


# =============================================================================
# Convenience helpers
# =============================================================================
class TestHelpers:
    def test_evaluate_automation(self):
        r = evaluate_automation(_health(85), _action("update_budget"))
        assert r.decision == GateDecision.PASS

    @pytest.mark.parametrize(
        "score,mode",
        [
            (85, "normal"),
            (75, "normal"),
            (65, "limited"),
            (50, "cuts_only"),
            (30, "frozen"),
        ],
    )
    def test_autopilot_mode(self, score, mode):
        result_mode, reason = get_autopilot_mode(_health(score))
        assert result_mode == mode
        assert isinstance(reason, str) and reason
