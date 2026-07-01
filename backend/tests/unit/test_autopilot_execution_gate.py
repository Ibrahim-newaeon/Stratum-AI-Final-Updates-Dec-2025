# =============================================================================
# Stratum AI - Autopilot Execution Enforcement-Gate Unit Tests
# =============================================================================
"""Unit tests for the enforcement gate in the autopilot execution path
(``enforce_before_execute`` and ``_enforcement_block_status`` in
``app.tasks.apply_actions_queue``).

These lock in the seam that gives the ``AutopilotEnforcer`` the final say
before an already-approved action is executed: hard-blocks become terminal
FAILED, soft-blocks return to PENDING_APPROVAL for confirmation, and the
enforcer is called with values derived from the queued action. The enforcer
itself is faked so the test needs no database — the Celery task body and
platform executors are out of scope here.
"""

import json

import pytest

from app.autopilot.enforcer import EnforcementMode, EnforcementResult
from app.autopilot.service import ActionStatus
from app.tasks import apply_actions_queue as mod

pytestmark = pytest.mark.unit


class _FakeAction:
    """Minimal stand-in for a FactActionsQueue row."""

    tenant_id = 7
    action_type = "budget_increase"
    entity_type = "campaign"
    entity_id = "camp-123"
    before_value = json.dumps({"daily_budget": 100})


@pytest.fixture
def capture_check(monkeypatch):
    """Patch AutopilotEnforcer so check_action records its kwargs and returns
    a caller-supplied result."""
    captured = {}
    result_box = {}

    class _FakeEnforcer:
        def __init__(self, db):
            captured["db"] = db

        async def check_action(self, **kwargs):
            captured.update(kwargs)
            return result_box["result"]

    # enforce_before_execute imports AutopilotEnforcer from app.autopilot.enforcer
    import app.autopilot.enforcer as enf

    monkeypatch.setattr(enf, "AutopilotEnforcer", _FakeEnforcer)
    return captured, result_box


class TestBlockStatusMapping:
    def test_hard_block_is_terminal_failed(self):
        res = EnforcementResult(
            allowed=False,
            mode=EnforcementMode.HARD_BLOCK,
            requires_confirmation=False,
        )
        assert mod._enforcement_block_status(res) == ActionStatus.FAILED.value

    def test_soft_block_returns_to_pending_approval(self):
        res = EnforcementResult(
            allowed=False,
            mode=EnforcementMode.SOFT_BLOCK,
            requires_confirmation=True,
        )
        assert mod._enforcement_block_status(res) == ActionStatus.PENDING_APPROVAL.value


class TestEnforceBeforeExecute:
    @pytest.mark.asyncio
    async def test_forwards_action_fields_to_enforcer(self, capture_check):
        captured, result_box = capture_check
        result_box["result"] = EnforcementResult(
            allowed=True, mode=EnforcementMode.ADVISORY
        )

        action_details = {"amount": 50, "metrics": {"roas": 0.4}}
        out = await mod.enforce_before_execute("SESSION", _FakeAction(), action_details)

        assert out.allowed is True
        assert captured["tenant_id"] == 7
        assert captured["action_type"] == "budget_increase"
        assert captured["entity_id"] == "camp-123"
        # proposed_value is the parsed action_json
        assert captured["proposed_value"] == action_details
        # current_value is parsed from before_value
        assert captured["current_value"] == {"daily_budget": 100}
        # metrics are lifted out of action_details for the ROAS rule
        assert captured["metrics"] == {"roas": 0.4}

    @pytest.mark.asyncio
    async def test_disallowed_result_is_returned_unchanged(self, capture_check):
        _captured, result_box = capture_check
        blocked = EnforcementResult(
            allowed=False,
            mode=EnforcementMode.HARD_BLOCK,
            warnings=["ROAS below threshold"],
        )
        result_box["result"] = blocked

        out = await mod.enforce_before_execute("SESSION", _FakeAction(), {})

        assert out.allowed is False
        assert out.warnings == ["ROAS below threshold"]

    @pytest.mark.asyncio
    async def test_malformed_before_value_degrades_to_none(self, capture_check):
        captured, result_box = capture_check
        result_box["result"] = EnforcementResult(
            allowed=True, mode=EnforcementMode.ADVISORY
        )

        action = _FakeAction()
        action.before_value = "{not valid json"
        await mod.enforce_before_execute("SESSION", action, {"amount": 1})

        assert captured["current_value"] is None
