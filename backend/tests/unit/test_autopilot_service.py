# =============================================================================
# Stratum AI - Autopilot Service Unit Tests
# =============================================================================
"""
Unit tests for AutopilotService and recommendation-to-action mapping.

All database access goes through a mocked AsyncSession -- no Postgres,
Redis, or network connections are required. The trust-gate check inside
``queue_action`` is driven by monkeypatching
``SignalHealthService.get_signal_health``.
"""

import json
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.autopilot.service import (
    SAFE_ACTIONS,
    ActionStatus,
    ActionType,
    AutopilotService,
    process_recommendations_to_actions,
)
from app.features.flags import AutopilotLevel, get_autopilot_caps
from app.models.trust_layer import FactActionsQueue

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers & Fixtures
# =============================================================================


def _make_db(execute_results: Optional[List[Any]] = None) -> MagicMock:
    """Build a mock AsyncSession.

    ``add`` is synchronous on AsyncSession, so it is a plain MagicMock;
    ``execute``/``commit``/``refresh`` are AsyncMocks. When
    ``execute_results`` is given, each call to ``execute`` consumes the
    next stubbed result object.
    """
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    if execute_results is None:
        db.execute = AsyncMock(return_value=MagicMock())
    else:
        db.execute = AsyncMock(side_effect=list(execute_results))
    return db


def _scalars_all(values: List[Any]) -> MagicMock:
    """Result stub for ``result.scalars().all()``."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _scalar_one_or_none(value: Any) -> MagicMock:
    """Result stub for ``result.scalar_one_or_none()``."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _iter_rows(rows: List[Any]) -> MagicMock:
    """Result stub for direct row iteration (``for row in result``)."""
    result = MagicMock()
    result.__iter__.return_value = iter(rows)
    return result


def _make_action(status: str = "queued", **overrides: Any) -> FactActionsQueue:
    """Construct an in-memory FactActionsQueue row (no DB needed)."""
    action = FactActionsQueue(
        tenant_id=1,
        date=date.today(),
        action_type="budget_decrease",
        entity_type="campaign",
        entity_id="camp_123",
        entity_name="Campaign 123",
        platform="meta",
        action_json=json.dumps({"amount": -50}),
        status=status,
    )
    action.id = uuid4()
    for key, value in overrides.items():
        setattr(action, key, value)
    return action


@pytest.fixture
def db() -> MagicMock:
    """Mock AsyncSession with default execute behaviour."""
    return _make_db()


@pytest.fixture
def service(db: MagicMock) -> AutopilotService:
    """AutopilotService bound to the mock session."""
    return AutopilotService(db=db)


@pytest.fixture
def stub_signal_health(monkeypatch: pytest.MonkeyPatch):
    """Stub SignalHealthService.get_signal_health to a given status."""

    def _stub(status: Optional[str]) -> AsyncMock:
        payload: Dict[str, Any] = {} if status is None else {"status": status}
        mock = AsyncMock(return_value=payload)
        monkeypatch.setattr(
            "app.quality.trust_layer_service.SignalHealthService.get_signal_health",
            mock,
        )
        return mock

    return _stub


# =============================================================================
# Test queue_action (Trust Gate)
# =============================================================================


class TestQueueAction:
    """Tests for the trust-gated queue_action() workflow."""

    @pytest.mark.asyncio
    async def test_critical_signal_blocks_action(self, service, db, stub_signal_health):
        """Critical signal health raises and never persists the action."""
        stub_signal_health("critical")

        with pytest.raises(ValueError, match="critical"):
            await service.queue_action(
                tenant_id=1,
                action_type="budget_increase",
                entity_type="campaign",
                entity_id="camp_123",
                entity_name="Campaign 123",
                platform="meta",
                action_json={"amount": 100},
            )

        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_degraded_signal_requires_approval(
        self, service, db, stub_signal_health
    ):
        """Degraded signal health queues the action as pending_approval."""
        stub_signal_health("degraded")

        action = await service.queue_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            entity_name="Campaign 123",
            platform="meta",
            action_json={"amount": 100},
            before_value={"budget": 500},
            created_by_user_id=9,
        )

        assert action.status == ActionStatus.PENDING_APPROVAL.value
        assert action.before_value == json.dumps({"budget": 500})
        assert action.created_by_user_id == 9
        assert db.add.call_args.args[0] is action
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(action)

    @pytest.mark.asyncio
    async def test_healthy_signal_queues_action(self, service, db, stub_signal_health):
        """Healthy signal health queues the action normally."""
        stub_signal_health("ok")

        action = await service.queue_action(
            tenant_id=1,
            action_type="budget_decrease",
            entity_type="adset",
            entity_id="adset_5",
            entity_name="Adset 5",
            platform="google",
            action_json={"amount": -25},
        )

        assert action.status == ActionStatus.QUEUED.value
        assert action.before_value is None
        assert action.action_json == json.dumps({"amount": -25})
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_signal_status_queues_action(
        self, service, db, stub_signal_health
    ):
        """Missing signal status defaults to the healthy path."""
        stub_signal_health(None)

        action = await service.queue_action(
            tenant_id=1,
            action_type="pause_creative",
            entity_type="creative",
            entity_id="cr_1",
            entity_name="Creative 1",
            platform="tiktok",
            action_json={},
        )

        assert action.status == ActionStatus.QUEUED.value


# =============================================================================
# Test Read Paths
# =============================================================================


class TestReadPaths:
    """Tests for get_queued_actions() and get_action_by_id()."""

    @pytest.mark.asyncio
    async def test_get_queued_actions_with_all_filters(self):
        """All optional filters are applied and rows are returned as a list."""
        expected = [_make_action(), _make_action()]
        db = _make_db([_scalars_all(expected)])
        service = AutopilotService(db=db)

        actions = await service.get_queued_actions(
            tenant_id=1,
            target_date=date.today(),
            status=ActionStatus.QUEUED.value,
            platform="meta",
            limit=10,
        )

        assert actions == expected
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_queued_actions_without_filters(self):
        """Filters are optional; the base tenant query still runs."""
        db = _make_db([_scalars_all([])])
        service = AutopilotService(db=db)

        actions = await service.get_queued_actions(tenant_id=1)

        assert actions == []

    @pytest.mark.asyncio
    async def test_get_action_by_id_found(self):
        """A matching action row is returned."""
        action = _make_action()
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        found = await service.get_action_by_id(action.id, tenant_id=1)

        assert found is action

    @pytest.mark.asyncio
    async def test_get_action_by_id_missing(self):
        """A miss returns None."""
        db = _make_db([_scalar_one_or_none(None)])
        service = AutopilotService(db=db)

        assert await service.get_action_by_id(uuid4(), tenant_id=1) is None


# =============================================================================
# Test Approval Workflow
# =============================================================================


class TestApprovalWorkflow:
    """Tests for approve_action(), approve_all_queued(), dismiss_action()."""

    @pytest.mark.asyncio
    async def test_approve_queued_action(self):
        """A queued action transitions to approved with an audit stamp."""
        action = _make_action(status=ActionStatus.QUEUED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        approved = await service.approve_action(action.id, tenant_id=1, user_id=5)

        assert approved is action
        assert approved.status == ActionStatus.APPROVED.value
        assert approved.approved_by_user_id == 5
        assert approved.approved_at.tzinfo is not None
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(action)

    @pytest.mark.asyncio
    async def test_approve_missing_action_returns_none(self):
        """Approving a nonexistent action is a no-op returning None."""
        db = _make_db([_scalar_one_or_none(None)])
        service = AutopilotService(db=db)

        result = await service.approve_action(uuid4(), tenant_id=1, user_id=5)

        assert result is None
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_non_queued_action_returns_none(self):
        """Only queued actions can be approved."""
        action = _make_action(status=ActionStatus.APPLIED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        result = await service.approve_action(action.id, tenant_id=1, user_id=5)

        assert result is None
        assert action.status == ActionStatus.APPLIED.value
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_all_queued_returns_rowcount(self):
        """Bulk approval commits and reports the affected row count."""
        db = _make_db([MagicMock(rowcount=3)])
        service = AutopilotService(db=db)

        count = await service.approve_all_queued(tenant_id=1, user_id=5)

        assert count == 3
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_all_queued_with_explicit_ids(self):
        """Bulk approval can be scoped to specific action IDs."""
        db = _make_db([MagicMock(rowcount=2)])
        service = AutopilotService(db=db)

        count = await service.approve_all_queued(
            tenant_id=1, user_id=5, action_ids=[uuid4(), uuid4()]
        )

        assert count == 2

    @pytest.mark.asyncio
    async def test_dismiss_queued_action(self):
        """A queued action can be dismissed."""
        action = _make_action(status=ActionStatus.QUEUED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        dismissed = await service.dismiss_action(action.id, tenant_id=1, user_id=5)

        assert dismissed is action
        assert dismissed.status == ActionStatus.DISMISSED.value
        assert dismissed.approved_by_user_id == 5
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dismiss_pending_approval_action(self):
        """A pending-approval (soft-blocked) action can also be dismissed."""
        action = _make_action(status=ActionStatus.PENDING_APPROVAL.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        dismissed = await service.dismiss_action(action.id, tenant_id=1, user_id=5)

        assert dismissed is action
        assert dismissed.status == ActionStatus.DISMISSED.value

    @pytest.mark.asyncio
    async def test_dismiss_applied_action_returns_none(self):
        """An already-applied action cannot be dismissed."""
        action = _make_action(status=ActionStatus.APPLIED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        result = await service.dismiss_action(action.id, tenant_id=1, user_id=5)

        assert result is None
        assert action.status == ActionStatus.APPLIED.value

    @pytest.mark.asyncio
    async def test_dismiss_missing_action_returns_none(self):
        """Dismissing a nonexistent action returns None."""
        db = _make_db([_scalar_one_or_none(None)])
        service = AutopilotService(db=db)

        assert await service.dismiss_action(uuid4(), tenant_id=1, user_id=5) is None


# =============================================================================
# Test Execution Result Recording
# =============================================================================


class TestExecutionResults:
    """Tests for mark_applied() and mark_failed()."""

    @pytest.mark.asyncio
    async def test_mark_applied_records_result(self):
        """mark_applied stamps status, actor, and serialized payloads."""
        action = _make_action(status=ActionStatus.APPROVED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        applied = await service.mark_applied(
            action_id=action.id,
            after_value={"budget": 120},
            platform_response={"id": "fb_1", "ok": True},
            user_id=5,
        )

        assert applied is action
        assert applied.status == ActionStatus.APPLIED.value
        assert applied.applied_by_user_id == 5
        assert applied.applied_at.tzinfo is not None
        assert applied.after_value == json.dumps({"budget": 120})
        assert applied.platform_response == json.dumps({"id": "fb_1", "ok": True})
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_applied_missing_action_returns_none(self):
        """mark_applied on a nonexistent action returns None."""
        db = _make_db([_scalar_one_or_none(None)])
        service = AutopilotService(db=db)

        result = await service.mark_applied(
            action_id=uuid4(),
            after_value={},
            platform_response={},
        )

        assert result is None
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_mark_failed_records_error(self):
        """mark_failed stamps status, error, and optional platform response."""
        action = _make_action(status=ActionStatus.APPROVED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        failed = await service.mark_failed(
            action_id=action.id,
            error="rate limited",
            platform_response={"code": 429},
        )

        assert failed is action
        assert failed.status == ActionStatus.FAILED.value
        assert failed.error == "rate limited"
        assert failed.platform_response == json.dumps({"code": 429})
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_failed_without_platform_response(self):
        """platform_response stays untouched when not supplied."""
        action = _make_action(status=ActionStatus.APPROVED.value)
        db = _make_db([_scalar_one_or_none(action)])
        service = AutopilotService(db=db)

        failed = await service.mark_failed(action_id=action.id, error="timeout")

        assert failed.error == "timeout"
        assert failed.platform_response is None

    @pytest.mark.asyncio
    async def test_mark_failed_missing_action_returns_none(self):
        """mark_failed on a nonexistent action returns None."""
        db = _make_db([_scalar_one_or_none(None)])
        service = AutopilotService(db=db)

        assert await service.mark_failed(action_id=uuid4(), error="x") is None


# =============================================================================
# Test Action Summary
# =============================================================================


class TestActionSummary:
    """Tests for get_action_summary() aggregation."""

    @pytest.mark.asyncio
    async def test_summary_aggregates_counts_and_success_rate(self):
        """Status/type/platform counts roll up with a correct success rate."""
        status_rows = [
            SimpleNamespace(status="applied", count=3),
            SimpleNamespace(status="failed", count=1),
            SimpleNamespace(status="queued", count=2),
        ]
        type_rows = [SimpleNamespace(action_type="budget_decrease", count=6)]
        platform_rows = [SimpleNamespace(platform="meta", count=6)]
        db = _make_db(
            [_iter_rows(status_rows), _iter_rows(type_rows), _iter_rows(platform_rows)]
        )
        service = AutopilotService(db=db)

        summary = await service.get_action_summary(tenant_id=1, days=7)

        assert summary["days"] == 7
        assert summary["start_date"] == (date.today() - timedelta(days=7)).isoformat()
        assert summary["status_counts"] == {"applied": 3, "failed": 1, "queued": 2}
        assert summary["type_counts"] == {"budget_decrease": 6}
        assert summary["platform_counts"] == {"meta": 6}
        assert summary["total"] == 6
        assert summary["pending_approval"] == 2
        # 3 applied / (3 applied + 1 failed) = 75%
        assert summary["success_rate"] == pytest.approx(75.0)

    @pytest.mark.asyncio
    async def test_summary_empty_avoids_division_by_zero(self):
        """No actions at all yields a 0% success rate, not a ZeroDivisionError."""
        db = _make_db([_iter_rows([]), _iter_rows([]), _iter_rows([])])
        service = AutopilotService(db=db)

        summary = await service.get_action_summary(tenant_id=1, days=30)

        assert summary["total"] == 0
        assert summary["pending_approval"] == 0
        assert summary["success_rate"] == 0.0


# =============================================================================
# Test can_auto_execute
# =============================================================================


class TestCanAutoExecute:
    """Tests for the pure can_auto_execute() gate across autopilot levels."""

    @pytest.fixture
    def gate(self) -> AutopilotService:
        """Service instance; can_auto_execute never touches the session."""
        return AutopilotService(db=MagicMock())

    def test_suggest_only_never_executes(self, gate: AutopilotService) -> None:
        """Level 0 always defers to suggestions."""
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.SUGGEST_ONLY, "budget_decrease", {"amount": -10}
        )
        assert allowed is False
        assert "suggest-only" in reason

    def test_approval_required_never_executes(self, gate: AutopilotService) -> None:
        """Level 2 requires approval for everything."""
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.APPROVAL_REQUIRED, "budget_decrease", {"amount": -10}
        )
        assert allowed is False
        assert "Approval required" in reason

    def test_guarded_auto_blocks_unsafe_action(self, gate: AutopilotService) -> None:
        """budget_increase is not in SAFE_ACTIONS and needs approval."""
        assert ActionType.BUDGET_INCREASE not in SAFE_ACTIONS
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO, "budget_increase", {"amount": 10}
        )
        assert allowed is False
        assert "requires approval" in reason

    def test_guarded_auto_rejects_unknown_action_type(
        self, gate: AutopilotService
    ) -> None:
        """Unrecognized action types are rejected outright."""
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO, "resurrect_campaign", {}
        )
        assert allowed is False
        assert "Unknown action type" in reason

    def test_guarded_auto_enforces_amount_cap(self, gate: AutopilotService) -> None:
        """Absolute budget changes above the dollar cap are blocked."""
        caps = get_autopilot_caps()
        over_cap = caps["max_daily_budget_change"] + 100
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO,
            "budget_decrease",
            {"amount": -over_cap, "percentage": 5},
        )
        assert allowed is False
        assert str(caps["max_daily_budget_change"]) in reason

    def test_guarded_auto_enforces_percentage_cap(self, gate: AutopilotService) -> None:
        """Percentage budget changes above the percent cap are blocked."""
        caps = get_autopilot_caps()
        over_cap = caps["max_budget_pct_change"] + 10
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO,
            "budget_decrease",
            {"amount": -10, "percentage": over_cap},
        )
        assert allowed is False
        assert str(caps["max_budget_pct_change"]) in reason

    def test_guarded_auto_allows_safe_budget_change_within_caps(
        self, gate: AutopilotService
    ) -> None:
        """A safe budget action within both caps auto-executes."""
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO,
            "budget_decrease",
            {"amount": -100, "percentage": 10},
        )
        assert allowed is True
        assert reason is None

    def test_guarded_auto_allows_safe_non_budget_action(
        self, gate: AutopilotService
    ) -> None:
        """Safe non-budget actions (pause_adset) skip the cap checks."""
        allowed, reason = gate.can_auto_execute(
            AutopilotLevel.GUARDED_AUTO, "pause_adset", {}
        )
        assert allowed is True
        assert reason is None

    def test_unknown_level_is_blocked(self, gate: AutopilotService) -> None:
        """An unrecognized autopilot level never executes."""
        allowed, reason = gate.can_auto_execute(99, "budget_decrease", {})
        assert allowed is False
        assert "Unknown autopilot level" in reason


# =============================================================================
# Test process_recommendations_to_actions
# =============================================================================


class TestProcessRecommendations:
    """Tests for the pure recommendations-to-actions mapper."""

    def test_empty_input_yields_no_actions(self) -> None:
        """Empty recommendations produce an empty action list."""
        assert process_recommendations_to_actions({}, AutopilotLevel.GUARDED_AUTO) == []

    def test_budget_actions_are_mapped(self) -> None:
        """increase/decrease actions map to budget_* queue items; others skip."""
        recommendations = {
            "actions": [
                {
                    "type": "increase",
                    "entity_id": "camp_1",
                    "entity_name": "Campaign 1",
                    "amount": 50,
                    "reason": "scaling winner",
                },
                {
                    "type": "decrease",
                    "entity_id": "camp_2",
                    "entity_name": "Campaign 2",
                    "amount": -30,
                    "reason": "underperforming",
                },
                {"type": "pause", "entity_id": "camp_3"},
            ]
        }

        actions = process_recommendations_to_actions(
            recommendations, AutopilotLevel.GUARDED_AUTO
        )

        assert len(actions) == 2
        assert actions[0]["action_type"] == "budget_increase"
        assert actions[0]["entity_type"] == "campaign"
        assert actions[0]["entity_id"] == "camp_1"
        assert actions[0]["action_json"] == {"amount": 50, "reason": "scaling winner"}
        # GUARDED_AUTO (1) < APPROVAL_REQUIRED (2)
        assert actions[0]["requires_approval"] is False
        assert actions[1]["action_type"] == "budget_decrease"

    def test_recommendations_are_mapped(self) -> None:
        """creative_refresh and fix_campaign recommendations become actions."""
        recommendations = {
            "recommendations": [
                {
                    "type": "creative_refresh",
                    "entity_id": "cr_1",
                    "entity_name": "Creative 1",
                    "description": "Fatigued creative",
                    "expected_impact": {"fatigue_score": 82},
                },
                {
                    "type": "fix_campaign",
                    "entity_id": "camp_9",
                    "entity_name": "Campaign 9",
                    "description": "Underperforming",
                    "expected_impact": {"scaling_score": 12},
                    "action_params": {"recommendations": ["lower budget"]},
                },
                {"type": "unknown_rec", "entity_id": "x"},
            ]
        }

        actions = process_recommendations_to_actions(
            recommendations, AutopilotLevel.APPROVAL_REQUIRED
        )

        assert len(actions) == 2
        refresh, fix = actions
        assert refresh["action_type"] == ActionType.PAUSE_CREATIVE.value
        assert refresh["entity_type"] == "creative"
        assert refresh["action_json"]["fatigue_score"] == 82
        assert refresh["requires_approval"] is True
        assert fix["action_type"] == ActionType.BUDGET_DECREASE.value
        assert fix["entity_type"] == "campaign"
        assert fix["action_json"]["scaling_score"] == 12
        assert fix["action_json"]["recommendations"] == ["lower budget"]
        assert fix["requires_approval"] is True

    def test_mixed_payload_maps_everything(self) -> None:
        """Budget actions and recommendations combine in one pass."""
        recommendations = {
            "actions": [
                {
                    "type": "increase",
                    "entity_id": "camp_1",
                    "entity_name": "Campaign 1",
                    "amount": 20,
                    "reason": "scale",
                }
            ],
            "recommendations": [
                {
                    "type": "creative_refresh",
                    "entity_id": "cr_2",
                    "entity_name": "Creative 2",
                    "description": "Refresh",
                    "expected_impact": {},
                }
            ],
        }

        actions = process_recommendations_to_actions(
            recommendations, AutopilotLevel.SUGGEST_ONLY
        )

        assert [a["action_type"] for a in actions] == [
            "budget_increase",
            ActionType.PAUSE_CREATIVE.value,
        ]
