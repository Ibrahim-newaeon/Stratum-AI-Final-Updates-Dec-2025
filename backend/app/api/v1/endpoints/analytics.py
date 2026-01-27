# =============================================================================
# Stratum AI - Analytics & Dashboard Endpoints
# =============================================================================
"""
Analytics endpoints for dashboard data and KPI calculations.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import AdPlatform, Campaign, CampaignMetric, CampaignStatus
from app.schemas import (
    APIResponse,
    DemographicsResponse,
    HeatmapDataResponse,
    KPITileResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/kpis")
async def get_kpi_tiles(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    period: str = Query("30d", pattern="^(today|7d|30d|90d)$"),
):
    """
    Get KPI tiles for the dashboard overview.

    Returns key metrics with trends.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Determine date ranges
    today = date.today()
    if period == "today":
        start_date = today
        prev_start = today - timedelta(days=1)
        prev_end = today - timedelta(days=1)
    elif period == "7d":
        start_date = today - timedelta(days=7)
        prev_start = today - timedelta(days=14)
        prev_end = today - timedelta(days=8)
    elif period == "30d":
        start_date = today - timedelta(days=30)
        prev_start = today - timedelta(days=60)
        prev_end = today - timedelta(days=31)
    else:  # 90d
        start_date = today - timedelta(days=90)
        prev_start = today - timedelta(days=180)
        prev_end = today - timedelta(days=91)

    # Current period metrics
    current_result = await db.execute(
        select(
            func.sum(CampaignMetric.spend_cents).label("spend"),
            func.sum(CampaignMetric.revenue_cents).label("revenue"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.clicks).label("clicks"),
            func.sum(CampaignMetric.conversions).label("conversions"),
        ).where(
            CampaignMetric.tenant_id == tenant_id,
            CampaignMetric.date >= start_date,
            CampaignMetric.date <= today,
        )
    )
    current = current_result.one()

    # Previous period metrics
    prev_result = await db.execute(
        select(
            func.sum(CampaignMetric.spend_cents).label("spend"),
            func.sum(CampaignMetric.revenue_cents).label("revenue"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.clicks).label("clicks"),
            func.sum(CampaignMetric.conversions).label("conversions"),
        ).where(
            CampaignMetric.tenant_id == tenant_id,
            CampaignMetric.date >= prev_start,
            CampaignMetric.date <= prev_end,
        )
    )
    prev = prev_result.one()

    def calc_change(current_val, prev_val):
        if not prev_val or prev_val == 0:
            return None
        return ((current_val or 0) - prev_val) / prev_val * 100

    def get_trend(change):
        if change is None:
            return "stable"
        return "up" if change > 0 else "down" if change < 0 else "stable"

    # Calculate derived metrics
    current_spend = (current.spend or 0) / 100
    prev_spend = (prev.spend or 0) / 100
    current_revenue = (current.revenue or 0) / 100
    prev_revenue = (prev.revenue or 0) / 100
    current_roas = current_revenue / current_spend if current_spend > 0 else 0
    prev_roas = prev_revenue / prev_spend if prev_spend > 0 else 0
    current_ctr = ((current.clicks or 0) / (current.impressions or 1)) * 100
    prev_ctr = ((prev.clicks or 0) / (prev.impressions or 1)) * 100

    kpis = [
        KPITileResponse(
            metric="spend",
            value=current_spend,
            previous_value=prev_spend,
            change_percent=calc_change(current_spend, prev_spend),
            trend=get_trend(calc_change(current_spend, prev_spend)),
            period=period,
        ),
        KPITileResponse(
            metric="revenue",
            value=current_revenue,
            previous_value=prev_revenue,
            change_percent=calc_change(current_revenue, prev_revenue),
            trend=get_trend(calc_change(current_revenue, prev_revenue)),
            period=period,
        ),
        KPITileResponse(
            metric="roas",
            value=round(current_roas, 2),
            previous_value=round(prev_roas, 2),
            change_percent=calc_change(current_roas, prev_roas),
            trend=get_trend(calc_change(current_roas, prev_roas)),
            period=period,
        ),
        KPITileResponse(
            metric="impressions",
            value=current.impressions or 0,
            previous_value=prev.impressions or 0,
            change_percent=calc_change(current.impressions, prev.impressions),
            trend=get_trend(calc_change(current.impressions, prev.impressions)),
            period=period,
        ),
        KPITileResponse(
            metric="clicks",
            value=current.clicks or 0,
            previous_value=prev.clicks or 0,
            change_percent=calc_change(current.clicks, prev.clicks),
            trend=get_trend(calc_change(current.clicks, prev.clicks)),
            period=period,
        ),
        KPITileResponse(
            metric="conversions",
            value=current.conversions or 0,
            previous_value=prev.conversions or 0,
            change_percent=calc_change(current.conversions, prev.conversions),
            trend=get_trend(calc_change(current.conversions, prev.conversions)),
            period=period,
        ),
        KPITileResponse(
            metric="ctr",
            value=round(current_ctr, 2),
            previous_value=round(prev_ctr, 2),
            change_percent=calc_change(current_ctr, prev_ctr),
            trend=get_trend(calc_change(current_ctr, prev_ctr)),
            period=period,
        ),
    ]

    return APIResponse(success=True, data=kpis)


@router.get("/demographics", response_model=APIResponse[DemographicsResponse])
async def get_demographics(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    campaign_id: Optional[int] = None,
    platform: Optional[AdPlatform] = None,
):
    """
    Get demographic breakdown for campaigns.

    Used for age/gender stacked bar charts.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(Campaign).where(
        Campaign.tenant_id == tenant_id,
        Campaign.is_deleted == False,
    )

    if campaign_id:
        query = query.where(Campaign.id == campaign_id)
    if platform:
        query = query.where(Campaign.platform == platform)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    # Aggregate demographics
    age_data = {}
    gender_data = {}
    location_data = {}

    for campaign in campaigns:
        if campaign.demographics_age:
            for age_range, metrics in campaign.demographics_age.items():
                if age_range not in age_data:
                    age_data[age_range] = {
                        "impressions": 0,
                        "clicks": 0,
                        "conversions": 0,
                        "spend_cents": 0,
                    }
                for metric, value in metrics.items():
                    age_data[age_range][metric] = age_data[age_range].get(metric, 0) + value

        if campaign.demographics_gender:
            for gender, metrics in campaign.demographics_gender.items():
                if gender not in gender_data:
                    gender_data[gender] = {
                        "impressions": 0,
                        "clicks": 0,
                        "conversions": 0,
                        "spend_cents": 0,
                    }
                for metric, value in metrics.items():
                    gender_data[gender][metric] = gender_data[gender].get(metric, 0) + value

        if campaign.demographics_location:
            for location, metrics in campaign.demographics_location.items():
                if location not in location_data:
                    location_data[location] = {"impressions": 0, "clicks": 0, "conversions": 0}
                for metric, value in metrics.items():
                    location_data[location][metric] = location_data[location].get(metric, 0) + value

    # Format for response
    age_breakdown = [{"range": k, **v} for k, v in sorted(age_data.items())]

    gender_breakdown = [{"gender": k, **v} for k, v in gender_data.items()]

    location_breakdown = [
        {"location": k, **v}
        for k, v in sorted(
            location_data.items(), key=lambda x: x[1].get("impressions", 0), reverse=True
        )[:20]
    ]

    return APIResponse(
        success=True,
        data=DemographicsResponse(
            age_breakdown=age_breakdown,
            gender_breakdown=gender_breakdown,
            location_breakdown=location_breakdown,
        ),
    )


@router.get("/heatmap", response_model=APIResponse[HeatmapDataResponse])
async def get_location_heatmap(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    aggregation: str = Query("country", pattern="^(country|state|city)$"),
    metric: str = Query("impressions", pattern="^(impressions|clicks|conversions|spend)$"),
):
    """
    Get location-based heatmap data.

    Returns coordinates and weights for map visualization.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaigns = result.scalars().all()

    # Aggregate location data
    location_metrics = {}

    for campaign in campaigns:
        if campaign.demographics_location:
            for location_key, metrics in campaign.demographics_location.items():
                if location_key not in location_metrics:
                    location_metrics[location_key] = {
                        "impressions": 0,
                        "clicks": 0,
                        "conversions": 0,
                        "spend": 0,
                    }
                location_metrics[location_key]["impressions"] += metrics.get("impressions", 0)
                location_metrics[location_key]["clicks"] += metrics.get("clicks", 0)
                location_metrics[location_key]["conversions"] += metrics.get("conversions", 0)
                location_metrics[location_key]["spend"] += metrics.get("spend_cents", 0)

    # Convert to heatmap points (using mock coordinates for demo)
    # In production, this would use a geocoding service
    from app.services.mock_client import LOCATION_COORDINATES

    points = []
    for location, metrics in location_metrics.items():
        coords = LOCATION_COORDINATES.get(location, {"lat": 0, "lng": 0})
        weight = metrics.get(metric, 0)
        if weight > 0:
            points.append(
                {
                    "location": location,
                    "lat": coords["lat"],
                    "lng": coords["lng"],
                    "weight": weight,
                    **metrics,
                }
            )

    # Sort by weight and limit
    points.sort(key=lambda x: x["weight"], reverse=True)
    points = points[:100]

    # Calculate bounds
    if points:
        lats = [p["lat"] for p in points]
        lngs = [p["lng"] for p in points]
        bounds = {
            "ne": {"lat": max(lats), "lng": max(lngs)},
            "sw": {"lat": min(lats), "lng": min(lngs)},
        }
    else:
        bounds = {
            "ne": {"lat": 90, "lng": 180},
            "sw": {"lat": -90, "lng": -180},
        }

    return APIResponse(
        success=True,
        data=HeatmapDataResponse(
            points=points,
            bounds=bounds,
            aggregation=aggregation,
        ),
    )


@router.get("/platform-breakdown")
async def get_platform_breakdown(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get performance breakdown by ad platform.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(
            Campaign.platform,
            func.sum(Campaign.total_spend_cents).label("spend"),
            func.sum(Campaign.revenue_cents).label("revenue"),
            func.sum(Campaign.impressions).label("impressions"),
            func.sum(Campaign.clicks).label("clicks"),
            func.sum(Campaign.conversions).label("conversions"),
            func.count(Campaign.id).label("campaign_count"),
        )
        .where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
        .group_by(Campaign.platform)
    )
    rows = result.all()

    breakdown = []
    for row in rows:
        spend = (row.spend or 0) / 100
        revenue = (row.revenue or 0) / 100
        roas = revenue / spend if spend > 0 else 0
        ctr = ((row.clicks or 0) / (row.impressions or 1)) * 100

        breakdown.append(
            {
                "platform": row.platform.value,
                "spend": spend,
                "revenue": revenue,
                "roas": round(roas, 2),
                "impressions": row.impressions or 0,
                "clicks": row.clicks or 0,
                "conversions": row.conversions or 0,
                "ctr": round(ctr, 2),
                "campaign_count": row.campaign_count,
            }
        )

    return APIResponse(success=True, data=breakdown)


@router.get("/trends")
async def get_performance_trends(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    days: int = Query(30, ge=7, le=90),
    metric: str = Query("spend", pattern="^(spend|revenue|impressions|clicks|conversions|roas)$"),
):
    """
    Get daily performance trends for a specified metric.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            CampaignMetric.date,
            func.sum(CampaignMetric.spend_cents).label("spend"),
            func.sum(CampaignMetric.revenue_cents).label("revenue"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.clicks).label("clicks"),
            func.sum(CampaignMetric.conversions).label("conversions"),
        )
        .where(
            CampaignMetric.tenant_id == tenant_id,
            CampaignMetric.date >= start_date,
        )
        .group_by(CampaignMetric.date)
        .order_by(CampaignMetric.date)
    )
    rows = result.all()

    trends = []
    for row in rows:
        spend = (row.spend or 0) / 100
        revenue = (row.revenue or 0) / 100
        roas = revenue / spend if spend > 0 else 0

        value = {
            "spend": spend,
            "revenue": revenue,
            "impressions": row.impressions or 0,
            "clicks": row.clicks or 0,
            "conversions": row.conversions or 0,
            "roas": round(roas, 2),
        }.get(metric, 0)

        trends.append(
            {
                "date": row.date.isoformat(),
                "value": value,
            }
        )

    return APIResponse(success=True, data={"metric": metric, "trends": trends})


@router.get("/tenant-overview")
async def get_tenant_overview(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get analytics overview for all tenants (superadmin view).
    Returns ROAS, EMQ, status, and key metrics per tenant.
    """
    from app.models import Tenant, UserRole

    user_role = getattr(request.state, "role", None)

    # Only superadmin can see all tenants
    if user_role != UserRole.ADMIN.value:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Get all active tenants
    tenant_result = await db.execute(select(Tenant).where(Tenant.is_deleted == False))
    tenants = tenant_result.scalars().all()

    tenant_analytics = []

    for tenant in tenants:
        # Get aggregate metrics for this tenant
        metrics_result = await db.execute(
            select(
                func.sum(CampaignMetric.spend_cents).label("spend"),
                func.sum(CampaignMetric.revenue_cents).label("revenue"),
                func.sum(CampaignMetric.conversions).label("conversions"),
                func.sum(CampaignMetric.clicks).label("clicks"),
                func.sum(CampaignMetric.impressions).label("impressions"),
            ).where(
                CampaignMetric.tenant_id == tenant.id,
                CampaignMetric.date >= date.today() - timedelta(days=30),
            )
        )
        metrics = metrics_result.one()

        # Calculate ROAS
        spend = (metrics.spend or 0) / 100
        revenue = (metrics.revenue or 0) / 100
        roas = round(revenue / spend, 2) if spend > 0 else 0

        # Calculate EMQ (Event Match Quality) - simulated based on conversion rate
        # In production, this would come from platform CAPI data
        conversions = metrics.conversions or 0
        clicks = metrics.clicks or 0
        emq = min(95, max(50, int(70 + (conversions / max(clicks, 1)) * 100))) if clicks > 0 else 75

        # Determine status based on ROAS trend
        if roas >= 4.0:
            status = "scaling"
        elif roas >= 2.5:
            status = "stable"
        else:
            status = "at_risk"

        tenant_analytics.append(
            {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "plan": tenant.plan,
                "roas": roas,
                "emq": emq,
                "status": status,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": metrics.impressions or 0,
            }
        )

    # Sort by revenue descending
    tenant_analytics.sort(key=lambda x: x["revenue"], reverse=True)

    return APIResponse(success=True, data=tenant_analytics)


@router.get("/executive-summary")
async def get_executive_summary(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get executive summary for superadmin dashboard.
    Aggregated metrics across all tenants.
    """
    from app.models import Tenant, UserRole

    user_role = getattr(request.state, "role", None)

    # Only superadmin can see executive summary
    if user_role != UserRole.ADMIN.value:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    today = date.today()
    start_30d = today - timedelta(days=30)
    prev_start = today - timedelta(days=60)
    prev_end = today - timedelta(days=31)

    # Current period - all tenants
    current_result = await db.execute(
        select(
            func.sum(CampaignMetric.spend_cents).label("spend"),
            func.sum(CampaignMetric.revenue_cents).label("revenue"),
            func.sum(CampaignMetric.conversions).label("conversions"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.clicks).label("clicks"),
        ).where(
            CampaignMetric.date >= start_30d,
            CampaignMetric.date <= today,
        )
    )
    current = current_result.one()

    # Previous period
    prev_result = await db.execute(
        select(
            func.sum(CampaignMetric.spend_cents).label("spend"),
            func.sum(CampaignMetric.revenue_cents).label("revenue"),
            func.sum(CampaignMetric.conversions).label("conversions"),
        ).where(
            CampaignMetric.date >= prev_start,
            CampaignMetric.date <= prev_end,
        )
    )
    prev = prev_result.one()

    # Get tenant counts
    tenant_count = await db.execute(select(func.count(Tenant.id)).where(Tenant.is_deleted == False))
    total_tenants = tenant_count.scalar()

    # Get campaign counts
    campaign_count = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.is_deleted == False,
            Campaign.status == CampaignStatus.ACTIVE,
        )
    )
    active_campaigns = campaign_count.scalar()

    # Calculate metrics
    current_spend = (current.spend or 0) / 100
    current_revenue = (current.revenue or 0) / 100
    prev_spend = (prev.spend or 0) / 100
    prev_revenue = (prev.revenue or 0) / 100

    current_roas = current_revenue / current_spend if current_spend > 0 else 0
    prev_roas = prev_revenue / prev_spend if prev_spend > 0 else 0

    def calc_change(curr, previous):
        if not previous or previous == 0:
            return 0
        return round(((curr - previous) / previous) * 100, 1)

    return APIResponse(
        success=True,
        data={
            "total_revenue": current_revenue,
            "revenue_change": calc_change(current_revenue, prev_revenue),
            "total_spend": current_spend,
            "spend_change": calc_change(current_spend, prev_spend),
            "platform_roas": round(current_roas, 2),
            "roas_change": calc_change(current_roas, prev_roas),
            "total_tenants": total_tenants,
            "active_campaigns": active_campaigns,
            "total_conversions": current.conversions or 0,
            "conversions_change": calc_change(current.conversions or 0, prev.conversions or 0),
            "total_impressions": current.impressions or 0,
            "period": "30d",
        },
    )
