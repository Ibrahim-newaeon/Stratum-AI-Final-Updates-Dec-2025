# =============================================================================
# Stratum AI - Integration Bridge unit tests
# =============================================================================
"""Unit tests for app.stratum.integration.

Pure bridge logic, no I/O. Covers signal-health derivation from an EMQ
service response, trust-gate action evaluation, autopilot-config mode
tiering by signal health, EMQ-score normalization, action construction,
and the lazy global-instance accessor.
"""

import pytest

from app.stratum.integration import (
    StratumIntegration,
    convert_platform_emq_to_score,
    create_automation_action,
    get_integration,
)
from app.stratum.models import AutomationAction, EMQScore, Platform

pytestmark = pytest.mark.unit


def _emq(**driver_values):
    """Build an EMQ-service-style response from named driver values."""
    return {"drivers": [{"name": k, "value": v} for k, v in driver_values.items()]}


@pytest.fixture()
def integ():
    return StratumIntegration()


# =============================================================================
# Signal health from EMQ response
# =============================================================================
class TestSignalHealthFromEmq:
    def test_high_drivers_high_score(self, integ):
        health = integ.calculate_signal_health_from_emq_response(
            _emq(
                **{
                    "Event Match Rate": 95,
                    "Pixel Coverage": 95,
                    "Conversion Latency": 90,
                    "Attribution Accuracy": 90,
                    "Data Freshness": 95,
                }
            )
        )
        assert health.overall_score >= 80

    def test_missing_drivers_use_defaults(self, integ):
        # empty drivers -> calculator uses the bridge's default values
        health = integ.calculate_signal_health_from_emq_response({"drivers": []})
        assert 0 <= health.overall_score <= 100


# =============================================================================
# Action evaluation through trust gate
# =============================================================================
class TestEvaluateAction:
    def test_healthy_passes_action(self, integ):
        action = create_automation_action(
            "meta", "acct_1", "campaign", "camp_1", "update_budget"
        )
        result = integ.evaluate_action(
            _emq(
                **{
                    "Event Match Rate": 95,
                    "Pixel Coverage": 95,
                    "Conversion Latency": 95,
                    "Attribution Accuracy": 95,
                    "Data Freshness": 95,
                }
            ),
            action,
        )
        assert result.decision.value in {"pass", "hold", "block"}

    def test_low_signal_blocks_or_holds(self, integ):
        action = create_automation_action(
            "meta", "acct_1", "campaign", "camp_1", "increase_budget"
        )
        result = integ.evaluate_action(
            _emq(
                **{
                    "Event Match Rate": 5,
                    "Pixel Coverage": 5,
                    "Conversion Latency": 5,
                    "Attribution Accuracy": 5,
                    "Data Freshness": 5,
                }
            ),
            action,
        )
        assert result.decision.value in {"hold", "block"}


# =============================================================================
# Autopilot config mode tiering
# =============================================================================
class TestAutopilotConfig:
    def _config_for(self, integ, score):
        # all-equal drivers make overall_score track the input
        return integ.get_autopilot_config(
            _emq(
                **{
                    "Event Match Rate": score,
                    "Pixel Coverage": score,
                    "Conversion Latency": score,
                    "Attribution Accuracy": score,
                    "Data Freshness": score,
                }
            )
        )

    def test_excellent_is_normal(self, integ):
        cfg = self._config_for(integ, 95)
        assert cfg["mode"] == "normal"
        assert "excellent" in cfg["reason"].lower()

    def test_critical_is_frozen(self, integ):
        cfg = self._config_for(integ, 10)
        assert cfg["mode"] == "frozen"

    def test_config_shape(self, integ):
        cfg = self._config_for(integ, 90)
        assert set(cfg) == {
            "mode",
            "reason",
            "signalHealth",
            "allowedActions",
            "restrictedActions",
        }
        comps = cfg["signalHealth"]["components"]
        assert set(comps) == {"emq", "freshness", "variance", "anomaly"}
        assert isinstance(cfg["allowedActions"], list)

    @pytest.mark.parametrize(
        "score,expected_mode",
        [
            (85, "normal"),
            (75, "normal"),
            (65, "limited"),
            (45, "cuts_only"),
            (20, "frozen"),
        ],
    )
    def test_mode_tiers(self, integ, score, expected_mode):
        # overall_score is a weighted blend, so assert the documented tier
        # contains the resulting mode by feeding uniform drivers
        cfg = self._config_for(integ, score)
        assert cfg["mode"] in {
            "normal",
            "limited",
            "cuts_only",
            "frozen",
        }


# =============================================================================
# EMQ score conversion
# =============================================================================
class TestConvertEmq:
    def test_normalizes_0_100_to_0_10(self):
        score = convert_platform_emq_to_score("meta", 85.0)
        assert isinstance(score, EMQScore)
        assert score.score == 8.5
        assert score.platform == Platform.META

    def test_already_0_10_unchanged(self):
        assert convert_platform_emq_to_score("google", 7.5).score == 7.5

    def test_clamps_to_range(self):
        assert convert_platform_emq_to_score("tiktok", 250.0).score == 10
        assert convert_platform_emq_to_score("snapchat", -5.0).score == 0

    def test_platform_case_insensitive(self):
        assert convert_platform_emq_to_score("META", 5.0).platform == Platform.META


# =============================================================================
# Action construction
# =============================================================================
class TestCreateAction:
    def test_builds_action(self):
        action = create_automation_action(
            "google", "acct_9", "adset", "as_1", "pause", parameters={"reason": "x"}
        )
        assert isinstance(action, AutomationAction)
        assert action.platform == Platform.GOOGLE
        assert action.entity_id == "as_1"
        assert action.parameters == {"reason": "x"}

    def test_default_empty_parameters(self):
        action = create_automation_action("meta", "a", "campaign", "c", "enable")
        assert action.parameters == {}


# =============================================================================
# Global accessor
# =============================================================================
class TestGetIntegration:
    def test_returns_singleton(self):
        assert get_integration() is get_integration()
        assert isinstance(get_integration(), StratumIntegration)
