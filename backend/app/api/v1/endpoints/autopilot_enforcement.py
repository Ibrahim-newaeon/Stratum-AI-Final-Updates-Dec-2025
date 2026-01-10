# =============================================================================
# Stratum AI - Autopilot Enforcement API Router
# =============================================================================
"""
API endpoints for Autopilot Enforcement features:
- Enforcement settings management
- Action enforcement checks
- Soft-block confirmation workflow
- Kill switch control
- Intervention audit log
"""

from datetime import date
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_async_session
from app.autopilot.enforcer import (
    AutopilotEnforcer,
    EnforcementMode,
    EnforcementSettings,
    EnforcementRule,
    ViolationType,
)
from app.schemas.response import APIResponse


router = APIRouter(prefix="/tenant/{tenant_id}/autopilot/enforcement", tags=["autopilot-enforcement"])


# =============================================================================
# Request/Response Models
# =============================================================================

class EnforcementSettingsRequest(BaseModel):
    """Request to update enforcement settings."""
    enforcement_enabled: Optional[bool] = Field(None, description="Kill switch - enable/disable enforcement")
    default_mode: Optional[str] = Field(None, description="Default enforcement mode: advisory, soft_block, hard_block")
    max_daily_budget: Optional[float] = Field(None, description="Maximum daily budget across all campaigns")
    max_campaign_budget: Optional[float] = Field(None, description="Maximum budget per campaign")
    budget_increase_limit_pct: Optional[float] = Field(None, description="Maximum budget increase percentage")
    min_roas_threshold: Optional[float] = Field(None, description="Minimum ROAS threshold")
    roas_lookback_days: Optional[int] = Field(None, description="Days to look back for ROAS calculation")
    max_budget_changes_per_day: Optional[int] = Field(None, description="Maximum budget changes per day")
    min_hours_between_changes: Optional[int] = Field(None, description="Minimum hours between changes")


class EnforcementCheckRequest(BaseModel):
    """Request to check enforcement for a proposed action."""
    action_type: str = Field(..., description="Type of action (budget_increase, budget_decrease, etc.)")
    entity_type: str = Field(..., description="Entity type (campaign, adset, creative)")
    entity_id: str = Field(..., description="Platform entity ID")
    proposed_value: Dict[str, Any] = Field(..., description="Proposed new value")
    current_value: Optional[Dict[str, Any]] = Field(None, description="Current value")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Current performance metrics")


class ConfirmActionRequest(BaseModel):
    """Request to confirm a soft-blocked action."""
    confirmation_token: str = Field(..., description="Token from enforcement check")
    override_reason: Optional[str] = Field(None, description="Reason for override")


class AddRuleRequest(BaseModel):
    """Request to add a custom enforcement rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_type: str = Field(..., description="Type of rule (budget_exceeded, roas_below_threshold, etc.)")
    threshold_value: float = Field(..., description="Threshold value for the rule")
    enforcement_mode: str = Field("advisory", description="Enforcement mode for this rule")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    description: Optional[str] = Field(None, description="Human-readable description")


class KillSwitchRequest(BaseModel):
    """Request to toggle kill switch."""
    enabled: bool = Field(..., description="Enable (true) or disable (false) enforcement")
    reason: Optional[str] = Field(None, description="Reason for change")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/settings", response_model=APIResponse[Dict[str, Any]])
async def get_enforcement_settings(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current enforcement settings for tenant.

    Returns full enforcement configuration including:
    - enforcement_enabled (kill switch status)
    - default_mode (advisory/soft_block/hard_block)
    - Budget thresholds
    - ROAS thresholds
    - Frequency limits
    - Custom rules
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    enforcer = AutopilotEnforcer(db)
    settings = await enforcer.get_settings(tenant_id)

    return APIResponse(
        success=True,
        data={
            "settings": {
                "enforcement_enabled": settings.enforcement_enabled,
                "default_mode": settings.default_mode.value if isinstance(settings.default_mode, EnforcementMode) else settings.default_mode,
                "max_daily_budget": settings.max_daily_budget,
                "max_campaign_budget": settings.max_campaign_budget,
                "budget_increase_limit_pct": settings.budget_increase_limit_pct,
                "min_roas_threshold": settings.min_roas_threshold,
                "roas_lookback_days": settings.roas_lookback_days,
                "max_budget_changes_per_day": settings.max_budget_changes_per_day,
                "min_hours_between_changes": settings.min_hours_between_changes,
                "rules": [r.dict() for r in settings.rules],
            },
            "modes": {
                "advisory": "Warn only, no blocking",
                "soft_block": "Warn + require confirmation to proceed",
                "hard_block": "Prevent action via API, log override attempts",
            },
        },
    )


@router.put("/settings", response_model=APIResponse[Dict[str, Any]])
async def update_enforcement_settings(
    request: Request,
    tenant_id: int,
    body: EnforcementSettingsRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update enforcement settings for tenant.

    Requires admin role.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    # Build updates dict from non-None values
    updates = {}
    if body.enforcement_enabled is not None:
        updates["enforcement_enabled"] = body.enforcement_enabled
    if body.default_mode is not None:
        try:
            updates["default_mode"] = EnforcementMode(body.default_mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {body.default_mode}")
    if body.max_daily_budget is not None:
        updates["max_daily_budget"] = body.max_daily_budget
    if body.max_campaign_budget is not None:
        updates["max_campaign_budget"] = body.max_campaign_budget
    if body.budget_increase_limit_pct is not None:
        updates["budget_increase_limit_pct"] = body.budget_increase_limit_pct
    if body.min_roas_threshold is not None:
        updates["min_roas_threshold"] = body.min_roas_threshold
    if body.roas_lookback_days is not None:
        updates["roas_lookback_days"] = body.roas_lookback_days
    if body.max_budget_changes_per_day is not None:
        updates["max_budget_changes_per_day"] = body.max_budget_changes_per_day
    if body.min_hours_between_changes is not None:
        updates["min_hours_between_changes"] = body.min_hours_between_changes

    enforcer = AutopilotEnforcer(db)
    settings = await enforcer.update_settings(tenant_id, updates)

    return APIResponse(
        success=True,
        data={
            "message": "Settings updated successfully",
            "settings": {
                "enforcement_enabled": settings.enforcement_enabled,
                "default_mode": settings.default_mode.value if isinstance(settings.default_mode, EnforcementMode) else settings.default_mode,
                "max_daily_budget": settings.max_daily_budget,
                "max_campaign_budget": settings.max_campaign_budget,
                "budget_increase_limit_pct": settings.budget_increase_limit_pct,
                "min_roas_threshold": settings.min_roas_threshold,
            },
        },
    )


@router.post("/check", response_model=APIResponse[Dict[str, Any]])
async def check_enforcement(
    request: Request,
    tenant_id: int,
    body: EnforcementCheckRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Check if a proposed action is allowed under enforcement rules.

    Returns:
    - allowed: Whether the action is permitted
    - mode: Enforcement mode that applied
    - violations: List of rule violations (if any)
    - warnings: Human-readable warning messages
    - requires_confirmation: Whether soft-block confirmation is needed
    - confirmation_token: Token to use for confirmation (if soft-blocked)
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    enforcer = AutopilotEnforcer(db)
    result = await enforcer.check_action(
        tenant_id=tenant_id,
        action_type=body.action_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        proposed_value=body.proposed_value,
        current_value=body.current_value,
        metrics=body.metrics,
    )

    return APIResponse(
        success=True,
        data=result.to_dict(),
    )


@router.post("/confirm", response_model=APIResponse[Dict[str, Any]])
async def confirm_soft_blocked_action(
    request: Request,
    tenant_id: int,
    body: ConfirmActionRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Confirm a soft-blocked action to proceed.

    Requires the confirmation_token from the enforcement check response.
    Override reason is logged for audit purposes.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    enforcer = AutopilotEnforcer(db)
    success, error = await enforcer.confirm_action(
        tenant_id=tenant_id,
        confirmation_token=body.confirmation_token,
        user_id=user_id,
        override_reason=body.override_reason,
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return APIResponse(
        success=True,
        data={
            "message": "Action confirmed - you may now proceed",
            "override_logged": True,
        },
    )


@router.post("/kill-switch", response_model=APIResponse[Dict[str, Any]])
async def toggle_kill_switch(
    request: Request,
    tenant_id: int,
    body: KillSwitchRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Enable or disable enforcement for the entire tenant.

    This is a kill switch that immediately stops all enforcement checks.
    All changes are logged for audit purposes.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    enforcer = AutopilotEnforcer(db)
    settings = await enforcer.set_kill_switch(
        tenant_id=tenant_id,
        enabled=body.enabled,
        user_id=user_id,
        reason=body.reason,
    )

    status = "enabled" if settings.enforcement_enabled else "disabled"

    return APIResponse(
        success=True,
        data={
            "message": f"Enforcement {status} for tenant",
            "enforcement_enabled": settings.enforcement_enabled,
            "changed_by_user_id": user_id,
        },
    )


@router.get("/audit-log", response_model=APIResponse[Dict[str, Any]])
async def get_intervention_audit_log(
    request: Request,
    tenant_id: int,
    days: int = Query(default=30, ge=1, le=90),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get audit log of all enforcement interventions.

    Returns history of:
    - Blocked actions
    - Warnings issued
    - Override confirmations
    - Kill switch changes
    - Auto-pause events
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    enforcer = AutopilotEnforcer(db)
    logs = await enforcer.get_intervention_log(tenant_id, days=days, limit=limit)

    return APIResponse(
        success=True,
        data={
            "logs": logs,
            "count": len(logs),
            "filters": {
                "days": days,
                "limit": limit,
            },
        },
    )


@router.post("/rules", response_model=APIResponse[Dict[str, Any]])
async def add_custom_rule(
    request: Request,
    tenant_id: int,
    body: AddRuleRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Add a custom enforcement rule.

    Custom rules allow fine-grained control over specific thresholds
    and can have different enforcement modes than the default.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    # Validate rule type
    try:
        rule_type = ViolationType(body.rule_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rule type: {body.rule_type}. Valid types: {[v.value for v in ViolationType]}",
        )

    # Validate enforcement mode
    try:
        mode = EnforcementMode(body.enforcement_mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid enforcement mode: {body.enforcement_mode}. Valid modes: advisory, soft_block, hard_block",
        )

    rule = EnforcementRule(
        rule_id=body.rule_id,
        rule_type=rule_type,
        threshold_value=body.threshold_value,
        enforcement_mode=mode,
        enabled=body.enabled,
        description=body.description,
    )

    enforcer = AutopilotEnforcer(db)
    settings = await enforcer.get_settings(tenant_id)
    settings.rules.append(rule)
    await enforcer.update_settings(tenant_id, {"rules": settings.rules})

    return APIResponse(
        success=True,
        data={
            "message": f"Rule '{body.rule_id}' added successfully",
            "rule": rule.dict(),
        },
    )


@router.delete("/rules/{rule_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_custom_rule(
    request: Request,
    tenant_id: int,
    rule_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a custom enforcement rule."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    enforcer = AutopilotEnforcer(db)
    settings = await enforcer.get_settings(tenant_id)

    original_count = len(settings.rules)
    settings.rules = [r for r in settings.rules if r.rule_id != rule_id]

    if len(settings.rules) == original_count:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    await enforcer.update_settings(tenant_id, {"rules": settings.rules})

    return APIResponse(
        success=True,
        data={
            "message": f"Rule '{rule_id}' deleted successfully",
        },
    )
