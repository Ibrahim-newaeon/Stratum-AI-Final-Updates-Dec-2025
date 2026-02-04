# =============================================================================
# Stratum AI - Trust Layer API Router
# =============================================================================
"""
API endpoints for Trust Layer features:
- Signal health monitoring
- Attribution variance tracking
- Trust banners and status
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.features.service import can_access_feature
from app.models.trust_layer import SignalHealthHistory, TrustGateAuditLog
from app.quality.trust_layer_service import AttributionVarianceService, SignalHealthService
from app.schemas.response import APIResponse

router = APIRouter(prefix="/tenant/{tenant_id}", tags=["trust-layer"])


# =============================================================================
# Signal Health Endpoints
# =============================================================================


@router.get("/signal-health", response_model=APIResponse[dict[str, Any]])
async def get_signal_health(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get signal health status and metrics for the tenant.

    Returns:
    - status: Overall health status (ok/risk/degraded/critical)
    - automation_blocked: Whether automation should be blocked
    - cards: Metric summary cards
    - platform_rows: Per-platform breakdown
    - banners: Trust banners to display
    """
    # Enforce tenant context
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Check feature flag
    if not await can_access_feature(db, tenant_id, "signal_health"):
        raise HTTPException(
            status_code=403, detail="Signal health feature is not enabled for this tenant"
        )

    service = SignalHealthService(db)
    data = await service.get_signal_health(tenant_id, target_date)

    return APIResponse(success=True, data=data)


@router.get("/signal-health/history", response_model=APIResponse[dict[str, Any]])
async def get_signal_health_history(
    request: Request,
    tenant_id: int,
    days: int = Query(default=7, ge=1, le=30),
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get signal health history for the past N days.
    Useful for trend analysis and reporting.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "signal_health_history"):
        raise HTTPException(status_code=403, detail="Signal health history feature not enabled")

    # Calculate date range
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days)

    # Query history records
    result = await db.execute(
        select(SignalHealthHistory)
        .where(
            and_(
                SignalHealthHistory.tenant_id == tenant_id,
                SignalHealthHistory.date >= start_date,
                SignalHealthHistory.date <= end_date,
            )
        )
        .order_by(desc(SignalHealthHistory.date))
    )
    records = result.scalars().all()

    # Format history data
    history = [
        {
            "date": record.date.isoformat(),
            "overall_score": record.overall_score,
            "status": record.status.value if hasattr(record.status, "value") else record.status,
            "emq_score_avg": record.emq_score_avg,
            "event_loss_pct_avg": record.event_loss_pct_avg,
            "freshness_minutes_avg": record.freshness_minutes_avg,
            "api_error_rate_avg": record.api_error_rate_avg,
            "platforms_ok": record.platforms_ok,
            "platforms_risk": record.platforms_risk,
            "platforms_degraded": record.platforms_degraded,
            "platforms_critical": record.platforms_critical,
            "automation_blocked": bool(record.automation_blocked),
        }
        for record in records
    ]

    return APIResponse(
        success=True,
        data={
            "days": days,
            "platform": platform,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "history": history,
            "total_records": len(history),
        },
    )


# =============================================================================
# Attribution Variance Endpoints
# =============================================================================


@router.get("/attribution-variance", response_model=APIResponse[dict[str, Any]])
async def get_attribution_variance(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get attribution variance between platform and GA4.

    Returns:
    - status: Variance status (healthy/minor/moderate/high)
    - overall_revenue_variance_pct: Overall revenue variance percentage
    - cards: Summary metric cards
    - platform_rows: Per-platform breakdown
    - banners: Attribution variance banners
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "attribution_variance"):
        raise HTTPException(
            status_code=403, detail="Attribution variance feature is not enabled for this tenant"
        )

    service = AttributionVarianceService(db)
    data = await service.get_attribution_variance(tenant_id, target_date)

    return APIResponse(success=True, data=data)


# =============================================================================
# Combined Trust Status Endpoint
# =============================================================================


@router.get("/trust-status", response_model=APIResponse[dict[str, Any]])
async def get_trust_status(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get combined trust status including signal health and attribution variance.
    This is the main endpoint for the Trust Layer banner/status.

    Returns:
    - overall_status: Combined trust status
    - automation_allowed: Whether automation can proceed
    - signal_health: Signal health summary (if enabled)
    - attribution_variance: Attribution variance summary (if enabled)
    - banners: Combined banners to display
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = {
        "date": (target_date or datetime.now(UTC).date()).isoformat(),
        "overall_status": "ok",
        "automation_allowed": True,
        "signal_health": None,
        "attribution_variance": None,
        "banners": [],
    }

    # Get signal health if enabled
    if await can_access_feature(db, tenant_id, "signal_health"):
        service = SignalHealthService(db)
        signal_data = await service.get_signal_health(tenant_id, target_date)
        result["signal_health"] = signal_data

        if signal_data["status"] in ["degraded", "critical"]:
            result["overall_status"] = signal_data["status"]
            result["automation_allowed"] = False
            result["banners"].extend(signal_data["banners"])
        elif signal_data["status"] == "risk" and result["overall_status"] == "ok":
            result["overall_status"] = "risk"
            result["banners"].extend(signal_data["banners"])

    # Get attribution variance if enabled
    if await can_access_feature(db, tenant_id, "attribution_variance"):
        service = AttributionVarianceService(db)
        attr_data = await service.get_attribution_variance(tenant_id, target_date)
        result["attribution_variance"] = attr_data

        # Add attribution banners (don't block automation for attribution issues)
        result["banners"].extend(attr_data["banners"])

    return APIResponse(success=True, data=result)


# =============================================================================
# Trust Gate Audit Log Endpoints
# =============================================================================


@router.get("/trust-gate/audit-logs", response_model=APIResponse[dict[str, Any]])
async def get_trust_gate_audit_logs(
    request: Request,
    tenant_id: int,
    days: int = Query(default=7, ge=1, le=30),
    decision_type: Optional[str] = Query(
        None, description="Filter by decision: execute, hold, block"
    ),
    entity_type: Optional[str] = Query(
        None, description="Filter by entity: campaign, adset, creative"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get trust gate audit logs for the tenant.

    Returns history of all trust gate decisions including:
    - Decision type (execute, hold, block)
    - Signal health at decision time
    - Action details
    - Gate evaluation reasons
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "trust_audit_logs"):
        raise HTTPException(status_code=403, detail="Trust audit logs feature not enabled")

    # Build query conditions
    from datetime import datetime

    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    conditions = [
        TrustGateAuditLog.tenant_id == tenant_id,
        TrustGateAuditLog.created_at >= start_date,
        TrustGateAuditLog.created_at <= end_date,
    ]

    if decision_type:
        conditions.append(TrustGateAuditLog.decision_type == decision_type)
    if entity_type:
        conditions.append(TrustGateAuditLog.entity_type == entity_type)

    # Get total count
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(TrustGateAuditLog.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # Get paginated records
    result = await db.execute(
        select(TrustGateAuditLog)
        .where(and_(*conditions))
        .order_by(desc(TrustGateAuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    records = result.scalars().all()

    # Format logs
    import json

    logs = []
    for record in records:
        logs.append(
            {
                "id": str(record.id),
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "decision_type": record.decision_type,
                "action_type": record.action_type,
                "entity_type": record.entity_type,
                "entity_id": record.entity_id,
                "entity_name": record.entity_name,
                "platform": record.platform,
                "signal_health_score": record.signal_health_score,
                "signal_health_status": record.signal_health_status,
                "gate_passed": bool(record.gate_passed),
                "gate_reason": json.loads(record.gate_reason) if record.gate_reason else None,
                "is_dry_run": bool(record.is_dry_run),
                "healthy_threshold": record.healthy_threshold,
                "degraded_threshold": record.degraded_threshold,
                "triggered_by_system": bool(record.triggered_by_system),
            }
        )

    # Compute summary stats
    execute_count = sum(1 for log in logs if log["decision_type"] == "execute")
    hold_count = sum(1 for log in logs if log["decision_type"] == "hold")
    block_count = sum(1 for log in logs if log["decision_type"] == "block")

    return APIResponse(
        success=True,
        data={
            "logs": logs,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(logs) < total,
            },
            "summary": {
                "total_decisions": len(logs),
                "executed": execute_count,
                "held": hold_count,
                "blocked": block_count,
                "pass_rate": execute_count / len(logs) * 100 if logs else 0,
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        },
    )


@router.get("/trust-gate/audit-logs/{log_id}", response_model=APIResponse[dict[str, Any]])
async def get_trust_gate_audit_log_detail(
    request: Request,
    tenant_id: int,
    log_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed information about a specific trust gate decision.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "trust_audit_logs"):
        raise HTTPException(status_code=403, detail="Trust audit logs feature not enabled")

    from uuid import UUID

    try:
        log_uuid = UUID(log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log ID format")

    result = await db.execute(
        select(TrustGateAuditLog).where(
            and_(
                TrustGateAuditLog.id == log_uuid,
                TrustGateAuditLog.tenant_id == tenant_id,
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Audit log not found")

    import json

    return APIResponse(
        success=True,
        data={
            "id": str(record.id),
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "decision_type": record.decision_type,
            "action_type": record.action_type,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "entity_name": record.entity_name,
            "platform": record.platform,
            "signal_health_score": record.signal_health_score,
            "signal_health_status": record.signal_health_status,
            "gate_passed": bool(record.gate_passed),
            "gate_reason": json.loads(record.gate_reason) if record.gate_reason else None,
            "healthy_threshold": record.healthy_threshold,
            "degraded_threshold": record.degraded_threshold,
            "is_dry_run": bool(record.is_dry_run),
            "action_payload": json.loads(record.action_payload) if record.action_payload else None,
            "action_result": json.loads(record.action_result) if record.action_result else None,
            "triggered_by_system": bool(record.triggered_by_system),
            "triggered_by_user_id": record.triggered_by_user_id,
        },
    )
