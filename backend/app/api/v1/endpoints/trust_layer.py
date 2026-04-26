# =============================================================================
# Stratum AI - Trust Layer API Router
# =============================================================================
"""
API endpoints for Trust Layer features:
- Signal health monitoring
- Attribution variance tracking
- Trust banners and status
"""

from datetime import date
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus
from app.quality.trust_layer_service import SignalHealthService, AttributionVarianceService
from app.features.service import can_access_feature
from app.schemas.response import APIResponse


router = APIRouter(prefix="/tenant/{tenant_id}", tags=["trust-layer"])


# =============================================================================
# Signal Health Endpoints
# =============================================================================

@router.get("/signal-health", response_model=APIResponse[Dict[str, Any]])
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
            status_code=403,
            detail="Signal health feature is not enabled for this tenant"
        ).limit(1000)

    service = SignalHealthService(db)
    data = await service.get_signal_health(tenant_id, target_date)

    return APIResponse(success=True, data=data)


@router.get("/signal-health/history", response_model=APIResponse[Dict[str, Any]])
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

    if not await can_access_feature(db, tenant_id, "signal_health"):
        raise HTTPException(status_code=403, detail="Feature not enabled")

    # For now, return empty history - will be populated by rollup tasks
    return APIResponse(
        success=True,
        data={
            "days": days,
            "platform": platform,
            "history": [],
            "message": "History will be available after daily rollup runs",
        },
    )


# =============================================================================
# Account-Level Signal Health Endpoints
# =============================================================================

@router.get("/signal-health/by-account", response_model=APIResponse[Dict[str, Any]])
async def get_signal_health_by_account(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get signal health breakdown by ad account.

    Returns per-account signal health metrics grouped by platform and account_id.
    Useful for identifying which specific ad accounts have degraded signals.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "signal_health"):
        raise HTTPException(status_code=403, detail="Signal health feature is not enabled")

    if target_date is None:
        target_date = date.today()

    # Query signal health records grouped by platform + account_id
    conditions = [
        FactSignalHealthDaily.tenant_id == tenant_id,
        FactSignalHealthDaily.date == target_date,
        FactSignalHealthDaily.account_id.isnot(None),
    ]
    if platform:
        conditions.append(FactSignalHealthDaily.platform == platform)

    result = await db.execute(
        select(FactSignalHealthDaily).where(*conditions).order_by(
            FactSignalHealthDaily.platform,
            FactSignalHealthDaily.account_id,
        ).limit(1000)
    )
    records = result.scalars().all()

    # Enrich with account names from TenantAdAccount
    from app.models.campaign_builder import TenantAdAccount
    account_names_result = await db.execute(
        select(
            TenantAdAccount.platform_account_id,
            TenantAdAccount.name,
            TenantAdAccount.business_name,
        ).where(TenantAdAccount.tenant_id == tenant_id)
    )
    account_lookup = {
        row.platform_account_id: {
            "name": row.name,
            "business_name": row.business_name,
        }
        for row in account_names_result.all()
    }

    # Build response
    accounts: List[Dict[str, Any]] = []
    status_counts = {"ok": 0, "risk": 0, "degraded": 0, "critical": 0}

    for record in records:
        account_info = account_lookup.get(record.account_id, {})
        status_val = record.status.value if hasattr(record.status, 'value') else str(record.status)
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

        accounts.append({
            "platform": record.platform,
            "account_id": record.account_id,
            "account_name": account_info.get("name", record.account_id),
            "business_name": account_info.get("business_name"),
            "status": status_val,
            "emq_score": record.emq_score,
            "event_loss_pct": record.event_loss_pct,
            "freshness_minutes": record.freshness_minutes,
            "api_error_rate": record.api_error_rate,
            "issues": record.issues,
            "actions": record.actions,
            "notes": record.notes,
        })

    # Determine overall status
    if status_counts["critical"] > 0:
        overall_status = "critical"
    elif status_counts["degraded"] > 0:
        overall_status = "degraded"
    elif status_counts["risk"] > 0:
        overall_status = "risk"
    else:
        overall_status = "ok"

    return APIResponse(
        success=True,
        data={
            "date": target_date.isoformat(),
            "overall_status": overall_status,
            "status_counts": status_counts,
            "total_accounts": len(accounts),
            "accounts": accounts,
        },
    )


# =============================================================================
# Attribution Variance Endpoints
# =============================================================================

@router.get("/attribution-variance", response_model=APIResponse[Dict[str, Any]])
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
            status_code=403,
            detail="Attribution variance feature is not enabled for this tenant"
        )

    service = AttributionVarianceService(db)
    data = await service.get_attribution_variance(tenant_id, target_date)

    return APIResponse(success=True, data=data)


# =============================================================================
# Combined Trust Status Endpoint
# =============================================================================

@router.get("/trust-status", response_model=APIResponse[Dict[str, Any]])
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
        "date": (target_date or date.today()).isoformat(),
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
