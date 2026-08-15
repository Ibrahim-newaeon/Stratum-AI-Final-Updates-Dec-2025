# =============================================================================
# Stratum AI - Autopilot API Router
# =============================================================================
"""
API endpoints for Autopilot features:
- Action queue management
- Approval workflow
- Action execution
"""

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.autopilot.service import ActionStatus, ActionType, AutopilotService
from app.db.session import get_async_session
from app.features.service import can_access_feature, get_tenant_features
from app.schemas.response import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant/{tenant_id}/autopilot", tags=["autopilot"])


def _dispatch_single_action(
    action_id: str,
    user_id: Optional[int],
    tenant_id: Optional[int] = None,
) -> None:
    """Dispatch execution of a single approved action to the Celery worker.

    Import is local to avoid a circular import at module load (the task module
    imports app.autopilot.service). Broker failures are swallowed so a transient
    dispatch problem never rolls back an already-committed approval — the
    every-5-min ``apply_actions_queue`` sweep is the backstop that catches it.
    """
    try:
        from app.tasks.apply_actions_queue import apply_single_action

        apply_single_action.delay(action_id, user_id, tenant_id)
    except Exception:  # pragma: no cover - defensive, backstop sweep recovers
        logger.exception(
            "Failed to dispatch apply_single_action for action %s; "
            "the scheduled sweep will retry",
            action_id,
        )


def _dispatch_rollback(
    action_id: str,
    user_id: Optional[int],
    tenant_id: Optional[int] = None,
) -> None:
    """Dispatch a rollback of an applied action to the Celery worker (TRUST-006).

    Local import to avoid a circular import at module load; broker failures are
    swallowed so a transient dispatch problem doesn't 500 an already-validated
    rollback request.
    """
    try:
        from app.tasks.apply_actions_queue import rollback_action

        rollback_action.delay(action_id, user_id, tenant_id)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to dispatch rollback_action for action %s", action_id)


def _dispatch_tenant_queue(tenant_id: int) -> None:
    """Dispatch execution of all approved actions for a tenant (used by
    approve-all). Same defensive contract as ``_dispatch_single_action``."""
    try:
        from app.tasks.apply_actions_queue import apply_actions_queue

        apply_actions_queue.delay(tenant_id=tenant_id)
    except Exception:  # pragma: no cover - defensive, backstop sweep recovers
        logger.exception(
            "Failed to dispatch apply_actions_queue for tenant %s; "
            "the scheduled sweep will retry",
            tenant_id,
        )


async def _require_not_frozen(db: AsyncSession, tenant_id: int) -> None:
    """Raise 409 when autopilot is frozen (emergency stop) for the tenant.

    Guards the execution-triggering endpoints (approve / confirm /
    approve-all) so an operator gets an explicit error instead of an action
    that is silently deferred. The apply worker enforces the same freeze
    authoritatively; this is the UX-layer echo so nothing looks "approved
    but stuck".
    """
    from app.autopilot.enforcer import AutopilotEnforcer

    if await AutopilotEnforcer(db).is_frozen(tenant_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Autopilot is frozen (emergency stop). "
                "Resume autopilot before executing actions."
            ),
        )


# =============================================================================
# Request/Response Models
# =============================================================================


class QueueActionRequest(BaseModel):
    """Request to queue a new action."""

    action_type: str = Field(..., description="Type of action")
    entity_type: str = Field(
        ..., description="Type of entity (campaign, adset, creative)"
    )
    entity_id: str = Field(..., description="Platform entity ID")
    entity_name: str = Field(..., description="Human-readable name")
    platform: str = Field(
        ..., description="Ad platform (meta, google, tiktok, snapchat)"
    )
    action_json: Dict[str, Any] = Field(..., description="Full action details")
    before_value: Optional[Dict[str, Any]] = Field(
        None, description="Current value before change"
    )


class ApproveActionsRequest(BaseModel):
    """Request to approve multiple actions."""

    action_ids: List[str] = Field(..., description="List of action UUIDs to approve")


class ApproverInfo(BaseModel):
    """User who accepted an action, for accountability display."""

    id: int
    name: Optional[str] = None
    department: Optional[str] = None


class ActionResponse(BaseModel):
    """Serialized action for API response."""

    id: str
    date: str
    action_type: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    platform: str
    action_json: Dict[str, Any]
    before_value: Optional[Dict[str, Any]]
    after_value: Optional[Dict[str, Any]]
    status: str
    created_at: str
    approved_at: Optional[str]
    applied_at: Optional[str]
    error: Optional[str]
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None
    approved_by: Optional[ApproverInfo] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _approver_info(action) -> Optional[ApproverInfo]:
    """Serialize the eager-loaded approver, if any.

    Only touches the relationship when the query eager-loaded it
    (selectinload in AutopilotService); a lazy load here would raise
    MissingGreenlet under the async session. full_name is PII-encrypted
    at rest, so decrypt for display.
    """
    from sqlalchemy import inspect as sa_inspect

    from app.core.security import decrypt_pii

    if action.approved_by_user_id is None:
        return None
    if "approved_by" in sa_inspect(action).unloaded:
        return None
    approver = action.approved_by
    if approver is None:  # user row deleted (FK is SET NULL on hard delete)
        return None

    # Cross-tenant approver (only reachable via the superadmin X-Tenant-ID
    # override): never serialize another tenant's user PII to this tenant.
    # Label it as platform staff instead of exposing name/department.
    if approver.tenant_id != action.tenant_id:
        return ApproverInfo(id=approver.id, name="Platform staff", department=None)

    name: Optional[str] = None
    if approver.full_name:
        try:
            name = decrypt_pii(approver.full_name)
        except (ValueError, TypeError):
            name = None

    return ApproverInfo(
        id=approver.id,
        name=name,
        department=approver.department,
    )


def action_to_response(action) -> ActionResponse:
    """Convert database action to API response."""
    import json

    return ActionResponse(
        id=str(action.id),
        date=action.date.isoformat(),
        action_type=action.action_type,
        entity_type=action.entity_type,
        entity_id=action.entity_id,
        entity_name=action.entity_name,
        platform=action.platform,
        action_json=json.loads(action.action_json) if action.action_json else {},
        before_value=json.loads(action.before_value) if action.before_value else None,
        after_value=json.loads(action.after_value) if action.after_value else None,
        status=action.status,
        created_at=action.created_at.isoformat() if action.created_at else None,
        approved_at=action.approved_at.isoformat() if action.approved_at else None,
        applied_at=action.applied_at.isoformat() if action.applied_at else None,
        error=action.error,
        requires_confirmation=bool(
            action.status == ActionStatus.PENDING_APPROVAL.value
            and getattr(action, "confirmation_token", None)
        ),
        confirmation_token=getattr(action, "confirmation_token", None),
        approved_by=_approver_info(action),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=APIResponse[Dict[str, Any]])
async def get_autopilot_status(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current autopilot status and configuration.

    Returns:
    - autopilot_level: Current level (0=suggest, 1=guarded, 2=approval)
    - pending_actions: Number of actions awaiting approval
    - caps: Budget/action caps for guarded mode
    - enabled: Whether autopilot is enabled
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    features = await get_tenant_features(db, tenant_id)

    service = AutopilotService(db)
    summary = await service.get_action_summary(tenant_id, days=1)

    from app.features.flags import get_autopilot_caps

    caps = get_autopilot_caps()

    return APIResponse(
        success=True,
        data={
            "autopilot_level": features.get("autopilot_level", 0),
            "autopilot_level_name": {
                0: "Suggest Only",
                1: "Guarded Auto",
                2: "Approval Required",
            }.get(features.get("autopilot_level", 0), "Unknown"),
            "pending_actions": summary["pending_approval"],
            "caps": caps,
            "enabled": features.get("autopilot_level", 0) > 0,
        },
    )


@router.get("/actions", response_model=APIResponse[Dict[str, Any]])
async def get_actions(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    status: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get actions for a tenant.

    Query params:
    - date: Filter by date
    - status: Filter by status (queued, approved, applied, failed, dismissed)
    - platform: Filter by platform
    - limit: Max results (default 50)
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    service = AutopilotService(db)
    actions = await service.get_queued_actions(
        tenant_id,
        target_date=target_date,
        status=status,
        platform=platform,
        limit=limit,
    )

    return APIResponse(
        success=True,
        data={
            "actions": [action_to_response(a).dict() for a in actions],
            "count": len(actions),
            "filters": {
                "date": target_date.isoformat() if target_date else None,
                "status": status,
                "platform": platform,
            },
        },
    )


@router.get("/actions/summary", response_model=APIResponse[Dict[str, Any]])
async def get_actions_summary(
    request: Request,
    tenant_id: int,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_async_session),
):
    """Get summary of actions over the past N days."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    service = AutopilotService(db)
    summary = await service.get_action_summary(tenant_id, days=days)

    return APIResponse(success=True, data=summary)


@router.get("/outcomes/summary", response_model=APIResponse[Dict[str, Any]])
async def get_outcomes_summary(
    request: Request,
    tenant_id: int,
    period: str = Query(default="7d", pattern="^(24h|7d|30d)$"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Aggregate the dollar value Stratum's autopilot has delivered for a
    tenant over a period. Powers the outcome-triggered upgrade nudge
    on the dashboard home (see frontend/src/components/billing/
    OutcomeNudge.tsx).

    Phase A: returns 0/0/0 for everyone because the estimator is a stub.
    Phase B: real counterfactual numbers with conservative_factor=0.5.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    from app.services.autopilot import get_outcome_summary

    summary = await get_outcome_summary(db, tenant_id, period=period)
    return APIResponse(success=True, data=summary.to_dict())


@router.post("/actions", response_model=APIResponse[Dict[str, Any]])
async def queue_action(
    request: Request,
    tenant_id: int,
    body: QueueActionRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Queue a new action.
    Actions will be auto-executed or require approval based on autopilot level.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Get current user ID from request state if available
    user_id = getattr(request.state, "user_id", None)

    service = AutopilotService(db)

    # Get autopilot level
    features = await get_tenant_features(db, tenant_id)
    autopilot_level = features.get("autopilot_level", 0)

    # Check if action can be auto-executed
    can_auto, reason = service.can_auto_execute(
        autopilot_level,
        body.action_type,
        body.action_json,
    )

    action = await service.queue_action(
        tenant_id=tenant_id,
        action_type=body.action_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        entity_name=body.entity_name,
        platform=body.platform,
        action_json=body.action_json,
        before_value=body.before_value,
        created_by_user_id=user_id,
    )

    # Auto-approve if allowed
    if can_auto:
        action = await service.approve_action(action.id, tenant_id, user_id or 0)
        # Auto-approved actions execute immediately (trust gate already passed).
        if action:
            _dispatch_single_action(str(action.id), user_id, tenant_id)

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "auto_approved": can_auto,
            "requires_approval": not can_auto,
            "reason": reason,
        },
    )


@router.post("/actions/{action_id}/approve", response_model=APIResponse[Dict[str, Any]])
async def approve_action(
    request: Request,
    tenant_id: int,
    action_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Approve a queued action for execution."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        uuid_id = UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID format")

    # Emergency stop — refuse to approve-for-execution while frozen.
    await _require_not_frozen(db, tenant_id)

    service = AutopilotService(db)
    action = await service.approve_action(uuid_id, tenant_id, user_id)

    if not action:
        raise HTTPException(
            status_code=404, detail="Action not found or already processed"
        )

    # Dispatch execution now that the action is approved and committed.
    _dispatch_single_action(str(action.id), user_id, tenant_id)

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "message": "Action approved for execution",
        },
    )


@router.post(
    "/actions/{action_id}/rollback", response_model=APIResponse[Dict[str, Any]]
)
async def rollback_applied_action(
    request: Request,
    tenant_id: int,
    action_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Roll back a previously applied autopilot action (TRUST-006).

    Dispatches the inverse action (restoring the entity's before_value). Only an
    applied, reversible action owned by the tenant can be rolled back.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        uuid_id = UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID format")

    await _require_not_frozen(db, tenant_id)

    service = AutopilotService(db)
    action = await service.get_action_by_id(uuid_id, tenant_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != ActionStatus.APPLIED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Only applied actions can be rolled back (status={action.status})",
        )

    _dispatch_rollback(str(action.id), user_id, tenant_id)
    return APIResponse(
        success=True,
        data={"action_id": str(action.id), "message": "Rollback initiated"},
    )


class ConfirmActionRequest(BaseModel):
    """Request to confirm a soft-blocked action."""

    override_reason: Optional[str] = Field(
        None, description="Why the operator is overriding the soft-block"
    )


@router.post("/actions/{action_id}/confirm", response_model=APIResponse[Dict[str, Any]])
async def confirm_soft_blocked_action(
    request: Request,
    tenant_id: int,
    action_id: str,
    body: Optional[ConfirmActionRequest] = None,
    db: AsyncSession = Depends(get_async_session),
):
    """Confirm a soft-blocked action and execute it.

    When the execution-path enforcement gate soft-blocks an approved
    action, it returns the action to PENDING_APPROVAL with a one-time
    confirmation token. This endpoint consumes that token (audit-logging
    the override), stamps the action as operator-confirmed, re-approves
    it, and dispatches execution. The gate lets the confirmed action
    through; hard-blocks remain absolute.

    If the stored token has expired, the action is re-dispatched so the
    gate re-evaluates and mints a fresh token.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        uuid_id = UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID format")

    # Emergency stop — a frozen tenant cannot override soft-blocks either.
    await _require_not_frozen(db, tenant_id)

    service = AutopilotService(db)
    action = await service.get_action_by_id(uuid_id, tenant_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.status != ActionStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail=f"Action status is {action.status}; only soft-blocked "
            "(pending_approval) actions can be confirmed",
        )

    if not action.confirmation_token:
        raise HTTPException(
            status_code=409,
            detail="Action has no pending confirmation token",
        )

    from app.autopilot.enforcer import AutopilotEnforcer

    enforcer = AutopilotEnforcer(db)
    success, error = await enforcer.confirm_action(
        tenant_id=tenant_id,
        confirmation_token=action.confirmation_token,
        user_id=user_id,
        override_reason=body.override_reason if body else None,
    )

    now = datetime.now(timezone.utc)

    if not success:
        # Expired/invalid token: clear it and re-dispatch so the gate
        # re-evaluates and mints a fresh token for the operator.
        action.confirmation_token = None
        action.status = ActionStatus.APPROVED.value
        action.error = None
        await db.commit()
        _dispatch_single_action(str(action.id), user_id, tenant_id)
        return APIResponse(
            success=False,
            data={
                "action": action_to_response(action).dict(),
                "message": (
                    f"Confirmation failed ({error}). The action was "
                    "re-submitted for enforcement evaluation; a fresh "
                    "confirmation token will be issued if it is "
                    "soft-blocked again."
                ),
            },
        )

    action.enforcement_confirmed_at = now
    action.enforcement_confirmed_by_user_id = user_id
    action.confirmation_token = None
    action.status = ActionStatus.APPROVED.value
    action.approved_by_user_id = action.approved_by_user_id or user_id
    action.approved_at = action.approved_at or now
    action.error = None
    await db.commit()
    await db.refresh(action)

    # Dispatch execution now that the override is committed.
    _dispatch_single_action(str(action.id), user_id, tenant_id)

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "message": "Override confirmed - action dispatched for execution",
        },
    )


@router.post("/actions/approve-all", response_model=APIResponse[Dict[str, Any]])
async def approve_all_actions(
    request: Request,
    tenant_id: int,
    body: Optional[ApproveActionsRequest] = None,
    db: AsyncSession = Depends(get_async_session),
):
    """Approve multiple queued actions at once."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    # Emergency stop — refuse bulk approve-for-execution while frozen.
    await _require_not_frozen(db, tenant_id)

    service = AutopilotService(db)

    action_ids = None
    if body and body.action_ids:
        try:
            action_ids = [UUID(aid) for aid in body.action_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid action ID format")

    count = await service.approve_all_queued(tenant_id, user_id, action_ids)

    # Dispatch the tenant-wide apply sweep so the just-approved actions execute.
    if count:
        _dispatch_tenant_queue(tenant_id)

    return APIResponse(
        success=True,
        data={
            "approved_count": count,
            "message": f"Approved {count} actions for execution",
        },
    )


@router.post("/actions/{action_id}/dismiss", response_model=APIResponse[Dict[str, Any]])
async def dismiss_action(
    request: Request,
    tenant_id: int,
    action_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Dismiss a queued action (won't be executed)."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        uuid_id = UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID format")

    service = AutopilotService(db)
    action = await service.dismiss_action(uuid_id, tenant_id, user_id)

    if not action:
        raise HTTPException(
            status_code=404, detail="Action not found or already processed"
        )

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "message": "Action dismissed",
        },
    )


@router.get("/actions/{action_id}", response_model=APIResponse[Dict[str, Any]])
async def get_action(
    request: Request,
    tenant_id: int,
    action_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get details of a specific action."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    try:
        uuid_id = UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID format")

    service = AutopilotService(db)
    action = await service.get_action_by_id(uuid_id, tenant_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    return APIResponse(
        success=True,
        data={"action": action_to_response(action).dict()},
    )
