# =============================================================================
# Stratum AI - Superadmin Analytics API
# =============================================================================
"""
API endpoints for Superadmin analytics and profitability views.
Provides cross-tenant insights and platform health monitoring.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_async_session
from app.models.trust_layer import FactSignalHealthDaily, FactActionsQueue
from app.schemas.response import APIResponse


router = APIRouter(prefix="/superadmin", tags=["superadmin-analytics"])


# =============================================================================
# Platform Overview
# =============================================================================

@router.get("/platform-overview", response_model=APIResponse[Dict[str, Any]])
async def get_platform_overview(
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get platform-wide overview metrics.

    Returns:
    - total_tenants: Total number of tenants
    - active_tenants: Tenants with recent activity
    - total_actions: Total autopilot actions
    - success_rate: Action success rate
    - signal_health_summary: Aggregated signal health
    """
    # Verify superadmin role
    if not getattr(request.state, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Superadmin access required")

    start_date = date.today() - timedelta(days=days)

    # Count distinct tenants with signal health data
    tenant_count_query = select(
        func.count(func.distinct(FactSignalHealthDaily.tenant_id))
    ).where(FactSignalHealthDaily.date >= start_date)
    tenant_count_result = await db.execute(tenant_count_query)
    active_tenants = tenant_count_result.scalar() or 0

    # Actions summary
    actions_query = select(
        func.count(FactActionsQueue.id).label("total"),
        func.sum(
            func.case(
                (FactActionsQueue.status == "applied", 1),
                else_=0
            )
        ).label("applied"),
        func.sum(
            func.case(
                (FactActionsQueue.status == "failed", 1),
                else_=0
            )
        ).label("failed"),
    ).where(FactActionsQueue.date >= start_date)
    actions_result = await db.execute(actions_query)
    actions_row = actions_result.first()

    total_actions = actions_row.total or 0
    applied_actions = actions_row.applied or 0
    failed_actions = actions_row.failed or 0
    success_rate = (applied_actions / (applied_actions + failed_actions) * 100) if (applied_actions + failed_actions) > 0 else 100

    # Signal health by status
    health_query = select(
        FactSignalHealthDaily.status,
        func.count(FactSignalHealthDaily.id).label("count"),
    ).where(
        FactSignalHealthDaily.date >= start_date
    ).group_by(FactSignalHealthDaily.status)
    health_result = await db.execute(health_query)
    health_summary = {row.status.value: row.count for row in health_result}

    # Platform breakdown
    platform_query = select(
        FactSignalHealthDaily.platform,
        func.count(FactSignalHealthDaily.id).label("count"),
        func.avg(FactSignalHealthDaily.emq_score).label("avg_emq"),
    ).where(
        FactSignalHealthDaily.date >= start_date
    ).group_by(FactSignalHealthDaily.platform)
    platform_result = await db.execute(platform_query)
    platform_breakdown = [
        {
            "platform": row.platform,
            "record_count": row.count,
            "avg_emq": round(row.avg_emq, 1) if row.avg_emq else None,
        }
        for row in platform_result
    ]

    return APIResponse(
        success=True,
        data={
            "period_days": days,
            "start_date": start_date.isoformat(),
            "active_tenants": active_tenants,
            "total_actions": total_actions,
            "applied_actions": applied_actions,
            "failed_actions": failed_actions,
            "success_rate": round(success_rate, 1),
            "signal_health_summary": health_summary,
            "platform_breakdown": platform_breakdown,
        },
    )


# =============================================================================
# Tenant Profitability
# =============================================================================

@router.get("/tenant-profitability", response_model=APIResponse[Dict[str, Any]])
async def get_tenant_profitability(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get tenant profitability metrics.

    Returns profitability analysis per tenant including:
    - Revenue metrics
    - Action efficiency
    - Signal health score
    """
    if not getattr(request.state, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Superadmin access required")

    start_date = date.today() - timedelta(days=days)

    # Tenant activity summary
    tenant_query = select(
        FactActionsQueue.tenant_id,
        func.count(FactActionsQueue.id).label("total_actions"),
        func.sum(
            func.case(
                (FactActionsQueue.status == "applied", 1),
                else_=0
            )
        ).label("applied_actions"),
        func.count(func.distinct(FactActionsQueue.date)).label("active_days"),
    ).where(
        FactActionsQueue.date >= start_date
    ).group_by(FactActionsQueue.tenant_id)
    tenant_result = await db.execute(tenant_query)

    # Signal health averages per tenant
    health_query = select(
        FactSignalHealthDaily.tenant_id,
        func.avg(FactSignalHealthDaily.emq_score).label("avg_emq"),
        func.avg(FactSignalHealthDaily.event_loss_pct).label("avg_event_loss"),
    ).where(
        FactSignalHealthDaily.date >= start_date
    ).group_by(FactSignalHealthDaily.tenant_id)
    health_result = await db.execute(health_query)
    health_map = {row.tenant_id: {"avg_emq": row.avg_emq, "avg_event_loss": row.avg_event_loss} for row in health_result}

    tenants = []
    for row in tenant_result:
        health = health_map.get(row.tenant_id, {})
        efficiency = (row.applied_actions / row.total_actions * 100) if row.total_actions > 0 else 0

        tenants.append({
            "tenant_id": row.tenant_id,
            "total_actions": row.total_actions,
            "applied_actions": row.applied_actions,
            "active_days": row.active_days,
            "action_efficiency": round(efficiency, 1),
            "avg_emq_score": round(health.get("avg_emq") or 0, 1),
            "avg_event_loss": round(health.get("avg_event_loss") or 0, 2),
            "health_score": calculate_health_score(health.get("avg_emq"), health.get("avg_event_loss")),
        })

    # Sort by health score descending
    tenants.sort(key=lambda x: x["health_score"], reverse=True)

    return APIResponse(
        success=True,
        data={
            "period_days": days,
            "start_date": start_date.isoformat(),
            "tenants": tenants,
            "total_tenants": len(tenants),
        },
    )


def calculate_health_score(avg_emq: Optional[float], avg_event_loss: Optional[float]) -> float:
    """Calculate a composite health score from EMQ and event loss."""
    if avg_emq is None and avg_event_loss is None:
        return 0

    score = 0
    if avg_emq is not None:
        score += avg_emq * 0.7  # EMQ weighted 70%
    if avg_event_loss is not None:
        score += (100 - avg_event_loss) * 0.3  # Inverse event loss weighted 30%

    return round(score, 1)


# =============================================================================
# Signal Health Trends
# =============================================================================

@router.get("/signal-health-trends", response_model=APIResponse[Dict[str, Any]])
async def get_signal_health_trends(
    request: Request,
    days: int = Query(default=14, ge=1, le=30),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get platform-wide signal health trends.

    Returns daily aggregates of signal health metrics.
    """
    if not getattr(request.state, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Superadmin access required")

    start_date = date.today() - timedelta(days=days)

    # Daily averages
    daily_query = select(
        FactSignalHealthDaily.date,
        func.avg(FactSignalHealthDaily.emq_score).label("avg_emq"),
        func.avg(FactSignalHealthDaily.event_loss_pct).label("avg_event_loss"),
        func.avg(FactSignalHealthDaily.freshness_minutes).label("avg_freshness"),
        func.avg(FactSignalHealthDaily.api_error_rate).label("avg_api_errors"),
        func.count(FactSignalHealthDaily.id).label("record_count"),
    ).where(
        FactSignalHealthDaily.date >= start_date
    ).group_by(FactSignalHealthDaily.date).order_by(FactSignalHealthDaily.date)

    daily_result = await db.execute(daily_query)

    trends = [
        {
            "date": row.date.isoformat(),
            "avg_emq": round(row.avg_emq, 1) if row.avg_emq else None,
            "avg_event_loss": round(row.avg_event_loss, 2) if row.avg_event_loss else None,
            "avg_freshness_minutes": round(row.avg_freshness, 0) if row.avg_freshness else None,
            "avg_api_error_rate": round(row.avg_api_errors, 2) if row.avg_api_errors else None,
            "record_count": row.record_count,
        }
        for row in daily_result
    ]

    # Calculate trend direction
    if len(trends) >= 2:
        first_half = trends[:len(trends)//2]
        second_half = trends[len(trends)//2:]

        first_avg_emq = sum(t["avg_emq"] for t in first_half if t["avg_emq"]) / len(first_half) if first_half else 0
        second_avg_emq = sum(t["avg_emq"] for t in second_half if t["avg_emq"]) / len(second_half) if second_half else 0

        trend_direction = "improving" if second_avg_emq > first_avg_emq else "declining" if second_avg_emq < first_avg_emq else "stable"
    else:
        trend_direction = "insufficient_data"

    return APIResponse(
        success=True,
        data={
            "period_days": days,
            "trends": trends,
            "trend_direction": trend_direction,
        },
    )


# =============================================================================
# Actions Analytics
# =============================================================================

@router.get("/actions-analytics", response_model=APIResponse[Dict[str, Any]])
async def get_actions_analytics(
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get platform-wide autopilot actions analytics.

    Returns action type breakdown, status distribution, and daily trends.
    """
    if not getattr(request.state, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Superadmin access required")

    start_date = date.today() - timedelta(days=days)

    # Action type breakdown
    type_query = select(
        FactActionsQueue.action_type,
        func.count(FactActionsQueue.id).label("count"),
    ).where(
        FactActionsQueue.date >= start_date
    ).group_by(FactActionsQueue.action_type)
    type_result = await db.execute(type_query)
    type_breakdown = {row.action_type: row.count for row in type_result}

    # Status breakdown
    status_query = select(
        FactActionsQueue.status,
        func.count(FactActionsQueue.id).label("count"),
    ).where(
        FactActionsQueue.date >= start_date
    ).group_by(FactActionsQueue.status)
    status_result = await db.execute(status_query)
    status_breakdown = {row.status: row.count for row in status_result}

    # Platform breakdown
    platform_query = select(
        FactActionsQueue.platform,
        func.count(FactActionsQueue.id).label("count"),
    ).where(
        FactActionsQueue.date >= start_date
    ).group_by(FactActionsQueue.platform)
    platform_result = await db.execute(platform_query)
    platform_breakdown = {row.platform: row.count for row in platform_result}

    # Daily action counts
    daily_query = select(
        FactActionsQueue.date,
        func.count(FactActionsQueue.id).label("count"),
    ).where(
        FactActionsQueue.date >= start_date
    ).group_by(FactActionsQueue.date).order_by(FactActionsQueue.date)
    daily_result = await db.execute(daily_query)
    daily_counts = [{"date": row.date.isoformat(), "count": row.count} for row in daily_result]

    total = sum(status_breakdown.values())

    return APIResponse(
        success=True,
        data={
            "period_days": days,
            "total_actions": total,
            "type_breakdown": type_breakdown,
            "status_breakdown": status_breakdown,
            "platform_breakdown": platform_breakdown,
            "daily_counts": daily_counts,
        },
    )
