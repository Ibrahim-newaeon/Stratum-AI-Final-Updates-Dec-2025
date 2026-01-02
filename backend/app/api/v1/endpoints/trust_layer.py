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
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
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
        )

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
