# =============================================================================
# Stratum AI - Autopilot API Router
# =============================================================================
"""
API endpoints for Autopilot features:
- Action queue management
- Approval workflow
- Action execution
"""

from datetime import UTC, date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.autopilot.service import AutopilotService
from app.db.session import get_async_session
from app.features.service import can_access_feature, get_tenant_features
from app.models.trust_layer import TrustGateAuditLog
from app.schemas.response import APIResponse

router = APIRouter(prefix="/tenant/{tenant_id}/autopilot", tags=["autopilot"])


# =============================================================================
# Request/Response Models
# =============================================================================


class QueueActionRequest(BaseModel):
    """Request to queue a new action."""

    action_type: str = Field(..., description="Type of action")
    entity_type: str = Field(..., description="Type of entity (campaign, adset, creative)")
    entity_id: str = Field(..., description="Platform entity ID")
    entity_name: str = Field(..., description="Human-readable name")
    platform: str = Field(..., description="Ad platform (meta, google, tiktok, snapchat)")
    action_json: dict[str, Any] = Field(..., description="Full action details")
    before_value: Optional[dict[str, Any]] = Field(None, description="Current value before change")


class ApproveActionsRequest(BaseModel):
    """Request to approve multiple actions."""

    action_ids: list[str] = Field(..., description="List of action UUIDs to approve")


class ActionResponse(BaseModel):
    """Serialized action for API response."""

    id: str
    date: str
    action_type: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    platform: str
    action_json: dict[str, Any]
    before_value: Optional[dict[str, Any]]
    after_value: Optional[dict[str, Any]]
    status: str
    created_at: str
    approved_at: Optional[str]
    applied_at: Optional[str]
    error: Optional[str]


# =============================================================================
# Helper Functions
# =============================================================================


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
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=APIResponse[dict[str, Any]])
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


@router.get("/actions", response_model=APIResponse[dict[str, Any]])
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


@router.get("/actions/summary", response_model=APIResponse[dict[str, Any]])
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


@router.post("/actions", response_model=APIResponse[dict[str, Any]])
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

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "auto_approved": can_auto,
            "requires_approval": not can_auto,
            "reason": reason,
        },
    )


@router.post("/actions/{action_id}/approve", response_model=APIResponse[dict[str, Any]])
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

    service = AutopilotService(db)
    action = await service.approve_action(uuid_id, tenant_id, user_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found or already processed")

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "message": "Action approved for execution",
        },
    )


@router.post("/actions/approve-all", response_model=APIResponse[dict[str, Any]])
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

    service = AutopilotService(db)

    action_ids = None
    if body and body.action_ids:
        try:
            action_ids = [UUID(aid) for aid in body.action_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid action ID format")

    count = await service.approve_all_queued(tenant_id, user_id, action_ids)

    return APIResponse(
        success=True,
        data={
            "approved_count": count,
            "message": f"Approved {count} actions for execution",
        },
    )


@router.post("/actions/{action_id}/dismiss", response_model=APIResponse[dict[str, Any]])
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
        raise HTTPException(status_code=404, detail="Action not found or already processed")

    return APIResponse(
        success=True,
        data={
            "action": action_to_response(action).dict(),
            "message": "Action dismissed",
        },
    )


@router.get("/actions/{action_id}", response_model=APIResponse[dict[str, Any]])
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


# =============================================================================
# Dry-Run Mode
# =============================================================================


class DryRunRequest(BaseModel):
    """Request to simulate an action in dry-run mode."""

    action_type: str = Field(..., description="Type of action")
    entity_type: str = Field(..., description="Type of entity (campaign, adset, creative)")
    entity_id: str = Field(..., description="Platform entity ID")
    entity_name: Optional[str] = Field(None, description="Human-readable name")
    platform: str = Field(..., description="Ad platform (meta, google, tiktok, snapchat)")
    action_json: dict[str, Any] = Field(..., description="Full action details")


class DryRunResult(BaseModel):
    """Result of a dry-run simulation."""

    would_execute: bool
    decision_type: str  # execute, hold, block
    signal_health_score: Optional[float]
    signal_health_status: Optional[str]
    gate_passed: bool
    gate_reasons: list[str]
    healthy_threshold: float
    degraded_threshold: float
    action_preview: dict[str, Any]
    warnings: list[str]


@router.post("/actions/dry-run", response_model=APIResponse[dict[str, Any]])
async def dry_run_action(
    request: Request,
    tenant_id: int,
    body: DryRunRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Simulate an action without executing it (dry-run mode).

    This endpoint allows testing automation rules before applying them.
    It evaluates:
    - Signal health and trust gate status
    - Autopilot level and caps
    - Action validity

    The result is logged to the trust gate audit log with is_dry_run=True.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "action_dry_run"):
        raise HTTPException(status_code=403, detail="Action dry-run feature not enabled")

    user_id = getattr(request.state, "user_id", None)

    # Get tenant features and autopilot level
    features = await get_tenant_features(db, tenant_id)
    autopilot_level = features.get("autopilot_level", 0)

    # Get signal health
    from app.quality.trust_layer_service import SignalHealthService

    signal_service = SignalHealthService(db)
    signal_data = await signal_service.get_signal_health(tenant_id)

    # Determine thresholds
    healthy_threshold = 70.0
    degraded_threshold = 40.0

    # Calculate effective signal health score
    signal_score = None
    signal_status = signal_data.get("status", "no_data")

    # Get EMQ from cards if available
    for card in signal_data.get("cards", []):
        if "EMQ" in card.get("title", ""):
            try:
                signal_score = float(card.get("value", "0").rstrip("%"))
            except (ValueError, AttributeError):
                pass

    # Evaluate trust gate
    gate_passed = True
    gate_reasons = []
    decision_type = "execute"
    warnings = []

    # Check signal health
    if signal_status in ["degraded", "critical"]:
        gate_passed = False
        decision_type = "block"
        gate_reasons.append(f"Signal health is {signal_status}")
    elif signal_status == "risk":
        decision_type = "hold"
        gate_reasons.append("Signal health is at risk")
        warnings.append("Action will be held for review due to signal health")

    if signal_score is not None:
        if signal_score < degraded_threshold:
            gate_passed = False
            decision_type = "block"
            gate_reasons.append(
                f"EMQ score {signal_score:.1f}% is below degraded threshold ({degraded_threshold}%)"
            )
        elif signal_score < healthy_threshold:
            if decision_type != "block":
                decision_type = "hold"
            gate_reasons.append(
                f"EMQ score {signal_score:.1f}% is below healthy threshold ({healthy_threshold}%)"
            )
            warnings.append("Consider improving data quality before executing")

    # Check autopilot level
    service = AutopilotService(db)
    can_auto, auto_reason = service.can_auto_execute(
        autopilot_level,
        body.action_type,
        body.action_json,
    )

    if not can_auto:
        if decision_type == "execute":
            decision_type = "hold"
        gate_reasons.append(f"Autopilot check: {auto_reason}")

    # Prepare action preview
    action_preview = {
        "action_type": body.action_type,
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "entity_name": body.entity_name,
        "platform": body.platform,
        "details": body.action_json,
    }

    # Log to audit trail
    import json
    from datetime import datetime

    audit_log = TrustGateAuditLog(
        tenant_id=tenant_id,
        decision_type=decision_type,
        action_type=body.action_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        entity_name=body.entity_name,
        platform=body.platform,
        signal_health_score=signal_score,
        signal_health_status=signal_status,
        gate_passed=1 if gate_passed else 0,
        gate_reason=json.dumps(gate_reasons),
        healthy_threshold=healthy_threshold,
        degraded_threshold=degraded_threshold,
        is_dry_run=1,
        action_payload=json.dumps(body.action_json),
        triggered_by_user_id=user_id,
        triggered_by_system=0,
        created_at=datetime.now(UTC),
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    result = DryRunResult(
        would_execute=gate_passed and decision_type == "execute",
        decision_type=decision_type,
        signal_health_score=signal_score,
        signal_health_status=signal_status,
        gate_passed=gate_passed,
        gate_reasons=gate_reasons,
        healthy_threshold=healthy_threshold,
        degraded_threshold=degraded_threshold,
        action_preview=action_preview,
        warnings=warnings,
    )

    return APIResponse(
        success=True,
        data={
            **result.dict(),
            "audit_log_id": str(audit_log.id),
            "message": "Dry-run simulation completed. No changes were made.",
        },
    )
