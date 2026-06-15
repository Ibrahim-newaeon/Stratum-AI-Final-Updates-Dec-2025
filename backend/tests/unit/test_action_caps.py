# =============================================================================
# Stratum AI - Autopilot Action-Cap Validation Unit Tests
# =============================================================================
"""Unit tests for ``validate_action_caps`` in
``app.tasks.apply_actions_queue`` — the pure guard that rejects budget
actions exceeding the configured autopilot caps. ``get_autopilot_caps`` is
monkeypatched for deterministic thresholds; the Celery task body and
platform executors are out of scope here.
"""

import pytest

from app.autopilot.service import ActionType
from app.tasks import apply_actions_queue as mod
from app.tasks.apply_actions_queue import validate_action_caps

pytestmark = pytest.mark.unit

_CAPS = {
    "max_daily_budget_change": 500.0,
    "max_budget_pct_change": 30.0,
    "max_actions_per_day": 10,
}


@pytest.fixture(autouse=True)
def fixed_caps(monkeypatch):
    monkeypatch.setattr(mod, "get_autopilot_caps", lambda: dict(_CAPS))


class TestBudgetCaps:
    def test_within_caps_is_valid(self):
        ok, err = validate_action_caps(
            ActionType.BUDGET_INCREASE.value, {"amount": 100, "percentage": 10}
        )
        assert ok is True
        assert err is None

    def test_amount_over_cap_rejected(self):
        ok, err = validate_action_caps(
            ActionType.BUDGET_INCREASE.value, {"amount": 600}
        )
        assert ok is False
        assert "exceeds" in err

    def test_percentage_over_cap_rejected(self):
        ok, err = validate_action_caps(
            ActionType.BUDGET_DECREASE.value, {"percentage": 50}
        )
        assert ok is False
        assert "%" in err

    def test_absolute_value_is_used_for_decrease(self):
        # A -600 change is still |600| > 500 -> rejected.
        ok, _err = validate_action_caps(
            ActionType.BUDGET_DECREASE.value, {"amount": -600}
        )
        assert ok is False


class TestNonBudgetActions:
    def test_pause_action_is_always_valid(self):
        ok, err = validate_action_caps(ActionType.PAUSE_CAMPAIGN.value, {})
        assert ok is True
        assert err is None

    def test_budget_action_with_no_details_is_valid(self):
        # Missing amount/percentage default to 0, which is within caps.
        ok, err = validate_action_caps(ActionType.BUDGET_INCREASE.value, {})
        assert ok is True
        assert err is None
