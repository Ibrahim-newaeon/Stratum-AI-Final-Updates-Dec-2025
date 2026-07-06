# =============================================================================
# Stratum AI - Apply Actions Task Integration Tests
# =============================================================================
"""
Integration tests for the autopilot execution pipeline
(``tasks.apply_single_action`` / ``tasks.apply_actions_queue``).

These drive the real Celery task bodies (asyncio.run + the app's own
async_session_factory against the test database) through the full
orchestration: status validation, signal-health deferral, cap
validation, the enforcement gate (allowed / hard-block / soft-block /
confirmed override), executor dispatch, and result persistence.

The tasks open their own DB sessions on their own event loop, so unlike
the API tests these seed *committed* rows via the sync engine and clean
them up in teardown. WebSocket publishing (Redis pub/sub) is mocked;
platform execution uses the executors' mock mode.
"""

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from app.autopilot.enforcer import EnforcementMode, EnforcementResult
from app.models.trust_layer import (
    FactActionsQueue,
    FactSignalHealthDaily,
    SignalHealthStatus,
)
from app.tasks import apply_actions_queue as mod

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _dispose_task_loop_connections():
    """Discard global-engine connections pooled under the task's event loop.

    Each Celery task body here runs via ``asyncio.run()`` and uses the
    app's module-level async engine, leaving pooled asyncpg connections
    bound to a loop that closes when the task returns. The tasks defend
    themselves at entry (``_reset_async_engine``), but later tests on the
    session-scoped loop that reach the global engine (any code path that
    opens its own session instead of the DI override) would pick up a
    dead-loop connection and fail with "Future attached to a different
    loop". Dispose via the sync facade — ``close=False`` swaps the pool
    without awaiting closes across loops, so no event loop is needed.
    """
    yield
    from app.db.session import async_engine

    async_engine.sync_engine.dispose(close=False)


# =============================================================================
# Seed helpers (committed rows — the task reads via its own session)
# =============================================================================


def _allowed() -> EnforcementResult:
    return EnforcementResult(allowed=True, mode=EnforcementMode.ADVISORY)


def _hard_block() -> EnforcementResult:
    return EnforcementResult(
        allowed=False,
        mode=EnforcementMode.HARD_BLOCK,
        warnings=["budget cap exceeded"],
        violations=[{"rule": "budget_cap"}],
    )


def _soft_block(token: str = "confirm-tok-123") -> EnforcementResult:
    return EnforcementResult(
        allowed=False,
        mode=EnforcementMode.SOFT_BLOCK,
        warnings=["needs confirmation"],
        requires_confirmation=True,
        confirmation_token=token,
    )


@pytest.fixture
def seeded(sync_engine):
    """A committed tenant + factory for committed queue actions.

    Yields a dict with the tenant id and an ``add_action`` factory; every
    row created here is deleted (and the tenant removed) on teardown.
    """
    from app.base_models import Tenant, User

    session = Session(bind=sync_engine)
    tenant = Tenant(
        name="Exec Pipeline Tenant",
        slug=f"exec-pipeline-{uuid.uuid4().hex[:10]}",
    )
    session.add(tenant)
    session.commit()

    # The applied_by_user_id FK requires a real user row.
    operator = User(
        tenant_id=tenant.id,
        email=f"exec-op-{uuid.uuid4().hex[:8]}@test.local",
        email_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        password_hash="x",
    )
    session.add(operator)
    session.commit()

    created_action_ids = []
    created_health_ids = []

    def add_action(
        status: str = "approved",
        platform: str = "meta",
        action_type: str = "budget_increase",
        amount: int = 50,
        tenant_id: Optional[int] = None,
        **overrides: Any,
    ) -> uuid.UUID:
        action = FactActionsQueue(
            tenant_id=tenant_id or tenant.id,
            date=date.today(),
            action_type=action_type,
            entity_type="campaign",
            entity_id=f"cmp-{uuid.uuid4().hex[:8]}",
            entity_name="Exec Test Campaign",
            platform=platform,
            action_json=json.dumps({"amount": amount}),
            status=status,
        )
        for key, value in overrides.items():
            setattr(action, key, value)
        session.add(action)
        session.commit()
        created_action_ids.append(action.id)
        return action.id

    def add_health_row(status: SignalHealthStatus) -> None:
        row = FactSignalHealthDaily(
            tenant_id=tenant.id,
            date=datetime.now(timezone.utc).date(),
            platform="meta",
            status=status,
        )
        session.add(row)
        session.commit()
        created_health_ids.append(row.id)

    yield {
        "tenant_id": tenant.id,
        "user_id": operator.id,
        "add_action": add_action,
        "add_health_row": add_health_row,
        "session": session,
    }

    for aid in created_action_ids:
        row = session.get(FactActionsQueue, aid)
        if row is not None:
            session.delete(row)
    for hid in created_health_ids:
        row = session.get(FactSignalHealthDaily, hid)
        if row is not None:
            session.delete(row)
    session.commit()
    session.delete(session.get(User, operator.id))
    session.commit()
    session.delete(session.get(Tenant, tenant.id))
    session.commit()
    session.close()


def reload_action(session: Session, action_id: uuid.UUID) -> FactActionsQueue:
    session.expire_all()
    return session.get(FactActionsQueue, action_id)


def run_single(action_id: uuid.UUID, enforcement: EnforcementResult, user_id: int = 7):
    """Run apply_single_action with WS publishing mocked, executor mock mode
    pinned, and a fixed enforcement outcome (the enforcer itself is covered
    elsewhere)."""
    with (
        patch.object(mod, "publish_action_status_update", AsyncMock()),
        patch.object(
            mod, "enforce_before_execute", AsyncMock(return_value=enforcement)
        ),
        patch.object(mod.settings, "use_mock_ad_data", True),
    ):
        return mod.apply_single_action.apply(
            kwargs={"action_id": str(action_id), "user_id": user_id}
        ).get()


# =============================================================================
# apply_single_action
# =============================================================================


class TestApplySingleAction:
    def test_unknown_action_id_errors(self):
        with patch.object(mod, "publish_action_status_update", AsyncMock()):
            result = mod.apply_single_action.apply(
                kwargs={"action_id": str(uuid.uuid4()), "user_id": 1}
            ).get()
        assert result == {"status": "error", "error": "Action not found"}

    def test_non_approved_status_is_rejected(self, seeded):
        action_id = seeded["add_action"](status="queued")
        result = run_single(action_id, _allowed())
        assert result["status"] == "error"
        assert "expected approved" in result["error"]

    def test_happy_path_applies_and_persists(self, seeded):
        action_id = seeded["add_action"](status="approved", amount=50)

        result = run_single(action_id, _allowed(), user_id=seeded["user_id"])

        assert result == {"status": "success", "action_id": str(action_id)}
        row = reload_action(seeded["session"], action_id)
        assert row.status == "applied"
        assert row.applied_at is not None
        assert row.applied_by_user_id == seeded["user_id"]
        after = json.loads(row.after_value)
        assert after["daily_budget"] == 10050  # mock executor: 10000 + 50
        assert json.loads(row.platform_response)["status"] == "success"

    def test_cap_violation_fails_action(self, seeded):
        caps = mod.get_autopilot_caps()
        over_cap = int(caps["max_daily_budget_change"]) + 1
        action_id = seeded["add_action"](status="approved", amount=over_cap)

        result = run_single(action_id, _allowed())

        assert result["status"] == "error"
        assert "exceeds max" in result["error"]
        row = reload_action(seeded["session"], action_id)
        assert row.status == "failed"

    def test_hard_block_is_terminal_failed(self, seeded):
        action_id = seeded["add_action"](status="approved")

        result = run_single(action_id, _hard_block())

        assert result["status"] == "blocked"
        assert result["requires_confirmation"] is False
        row = reload_action(seeded["session"], action_id)
        assert row.status == "failed"
        assert "Enforcement (hard_block)" in row.error

    def test_soft_block_returns_to_pending_with_token(self, seeded):
        action_id = seeded["add_action"](status="approved")

        result = run_single(action_id, _soft_block(token="tok-abc"))

        assert result["status"] == "blocked"
        assert result["requires_confirmation"] is True
        assert result["confirmation_token"] == "tok-abc"
        row = reload_action(seeded["session"], action_id)
        assert row.status == "pending_approval"
        assert row.confirmation_token == "tok-abc"

    def test_confirmed_soft_block_override_executes(self, seeded):
        action_id = seeded["add_action"](
            status="approved",
            enforcement_confirmed_at=datetime.now(timezone.utc),
            enforcement_confirmed_by_user_id=seeded["user_id"],
        )

        result = run_single(action_id, _soft_block(), user_id=seeded["user_id"])

        assert result == {"status": "success", "action_id": str(action_id)}
        row = reload_action(seeded["session"], action_id)
        assert row.status == "applied"

    def test_degraded_signal_health_defers(self, seeded):
        seeded["add_health_row"](SignalHealthStatus.DEGRADED)
        action_id = seeded["add_action"](status="approved")

        result = run_single(action_id, _allowed())

        assert result == {"status": "error", "error": "Signal health degraded"}
        row = reload_action(seeded["session"], action_id)
        assert row.status == "approved"  # left for a later sweep

    def test_unsupported_platform_fails(self, seeded):
        action_id = seeded["add_action"](status="approved", platform="linkedin")

        result = run_single(action_id, _allowed())

        assert result["status"] == "error"
        assert "Unsupported platform" in result["error"]
        row = reload_action(seeded["session"], action_id)
        assert row.status == "failed"


# =============================================================================
# apply_actions_queue (sweep)
# =============================================================================


class TestApplyActionsQueueSweep:
    def test_sweep_applies_all_approved_for_tenant(self, seeded):
        first = seeded["add_action"](status="approved", amount=10)
        second = seeded["add_action"](
            status="approved", platform="google", action_type="pause_campaign"
        )
        ignored_queued = seeded["add_action"](status="queued")

        with (
            patch.object(mod, "publish_action_status_update", AsyncMock()),
            patch.object(
                mod, "enforce_before_execute", AsyncMock(return_value=_allowed())
            ),
            patch.object(mod.settings, "use_mock_ad_data", True),
        ):
            result = mod.apply_actions_queue.apply(
                kwargs={"tenant_id": seeded["tenant_id"]}
            ).get()

        assert result["status"] == "success"
        assert result["processed"] == 2
        assert result["failed"] == 0
        session = seeded["session"]
        assert reload_action(session, first).status == "applied"
        assert reload_action(session, second).status == "applied"
        assert reload_action(session, ignored_queued).status == "queued"

    def test_sweep_mixes_success_and_enforcement_block(self, seeded):
        allowed_id = seeded["add_action"](status="approved", amount=10)
        blocked_id = seeded["add_action"](status="approved", amount=20)

        outcomes = {str(allowed_id): _allowed(), str(blocked_id): _hard_block()}

        async def per_action(db, action, action_details):
            return outcomes[str(action.id)]

        with (
            patch.object(mod, "publish_action_status_update", AsyncMock()),
            patch.object(mod, "enforce_before_execute", per_action),
            patch.object(mod.settings, "use_mock_ad_data", True),
        ):
            result = mod.apply_actions_queue.apply(
                kwargs={"tenant_id": seeded["tenant_id"]}
            ).get()

        assert result["processed"] == 1
        assert result["failed"] == 1
        session = seeded["session"]
        assert reload_action(session, allowed_id).status == "applied"
        blocked = reload_action(session, blocked_id)
        assert blocked.status == "failed"
        assert "Enforcement" in blocked.error

    def test_sweep_with_no_approved_actions_is_noop(self, seeded):
        with patch.object(mod, "publish_action_status_update", AsyncMock()):
            result = mod.apply_actions_queue.apply(
                kwargs={"tenant_id": seeded["tenant_id"]}
            ).get()
        assert result == {"status": "success", "processed": 0, "failed": 0}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
