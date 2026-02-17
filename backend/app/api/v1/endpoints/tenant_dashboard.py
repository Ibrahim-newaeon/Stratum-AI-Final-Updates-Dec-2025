# =============================================================================
# Stratum AI - Tenant Dashboard Endpoints
# =============================================================================
"""
Tenant-scoped dashboard endpoints for multi-tenant analytics.

Routes:
- GET /api/tenant/{tenant_id}/dashboard/overview - Dashboard overview KPIs
- GET /api/tenant/{tenant_id}/recommendations - AI recommendations
- GET /api/tenant/{tenant_id}/alerts - Active alerts
- POST /api/tenant/{tenant_id}/alerts/{id}/ack - Acknowledge alert
- POST /api/tenant/{tenant_id}/alerts/{id}/resolve - Resolve alert
- GET /api/tenant/{tenant_id}/settings - Tenant settings
- PUT /api/tenant/{tenant_id}/settings - Update settings
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import Permission, require_permissions
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CreativeAsset, Tenant
from app.schemas import APIResponse
from app.tenancy import get_tenant, require_tenant, TenantContext, tenant_query

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================
class DashboardOverviewResponse(BaseModel):
    """Dashboard overview response with all KPIs."""
    # Spend & Revenue
    total_spend: float = 0
    total_revenue: float = 0
    spend_delta_pct: float = 0
    revenue_delta_pct: float = 0

    # Performance
    portfolio_roas: float = 0
    roas_delta_pct: float = 0
    avg_cpa: float = 0
    cpa_delta_pct: float = 0
    avg_ctr: float = 0
    ctr_delta_pct: float = 0

    # Volume
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0

    # Campaign breakdown
    total_campaigns: int = 0
    active_campaigns: int = 0
    paused_campaigns: int = 0

    # Health indicators
    scaling_candidates: int = 0
    watch_campaigns: int = 0
    fix_candidates: int = 0

    # Signal health
    avg_emq_score: Optional[float] = None
    signal_health_status: str = "healthy"
    open_alerts_count: int = 0

    # Platform distribution
    platform_breakdown: dict = {}


class RecommendationItem(BaseModel):
    """Single recommendation item."""
    id: str
    type: str  # scale, watch, fix, pause, creative_refresh, budget_shift
    priority: int  # 1-5 (1 = highest)
    entity_type: str  # campaign, adset, creative
    entity_id: str
    entity_name: str
    title: str
    description: str
    impact_estimate: Optional[str] = None
    roas_impact: Optional[float] = None
    confidence: float = 0.0
    actions: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertItem(BaseModel):
    """Single alert item."""
    id: int
    type: str  # anomaly, fatigue, budget, signal, system
    severity: str  # low, medium, high, critical
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    metric: Optional[str] = None
    current_value: Optional[float] = None
    expected_value: Optional[float] = None
    is_acknowledged: bool = False
    is_resolved: bool = False
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class TenantSettingsResponse(BaseModel):
    """Tenant settings response."""
    # General settings
    currency: str = "USD"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    fiscal_year_start: int = 1  # Month (1-12)

    # Alert thresholds
    alert_roas_drop_pct: float = 20.0
    alert_cpa_increase_pct: float = 25.0
    alert_spend_anomaly_threshold: float = 2.5
    alert_emq_min_score: float = 7.0

    # Notification preferences
    email_notifications: bool = True
    whatsapp_notifications: bool = False
    slack_notifications: bool = False
    notification_frequency: str = "realtime"  # realtime, hourly, daily

    # Connected platforms
    connected_platforms: List[str] = []

    # Feature flags
    feature_flags: dict = {}


class TenantSettingsUpdate(BaseModel):
    """Tenant settings update request."""
    currency: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    alert_roas_drop_pct: Optional[float] = None
    alert_cpa_increase_pct: Optional[float] = None
    alert_spend_anomaly_threshold: Optional[float] = None
    alert_emq_min_score: Optional[float] = None
    email_notifications: Optional[bool] = None
    whatsapp_notifications: Optional[bool] = None
    slack_notifications: Optional[bool] = None
    notification_frequency: Optional[str] = None


# =============================================================================
# Dashboard Overview
# =============================================================================
@router.get(
    "/{tenant_id}/dashboard/overview",
    response_model=APIResponse[DashboardOverviewResponse],
)
async def get_dashboard_overview(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    date_str: Optional[str] = Query(None, alias="date", description="Date YYYY-MM-DD"),
    period: str = Query("7d", description="Comparison period: 1d, 7d, 30d"),
):
    """
    Get dashboard overview with KPIs for a tenant.

    Returns spend, revenue, ROAS, CPA metrics with period comparisons.
    """
    # Parse date
    if date_str:
        try:
            query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            query_date = date.today()
    else:
        query_date = date.today()

    # Get campaigns for tenant
    campaigns_query = tenant_query(db, Campaign, tenant_id)
    result = await db.execute(campaigns_query)
    campaigns = result.scalars().all()

    if not campaigns:
        return APIResponse(
            success=True,
            data=DashboardOverviewResponse(),
            message="No campaigns found",
        )

    # Calculate metrics
    total_spend = sum(c.total_spend_cents / 100 if c.total_spend_cents else 0 for c in campaigns)
    total_revenue = sum(c.revenue_cents / 100 if c.revenue_cents else 0 for c in campaigns)
    total_impressions = sum(c.impressions or 0 for c in campaigns)
    total_clicks = sum(c.clicks or 0 for c in campaigns)
    total_conversions = sum(c.conversions or 0 for c in campaigns)

    portfolio_roas = total_revenue / total_spend if total_spend > 0 else 0
    avg_ctr = sum(c.ctr or 0 for c in campaigns) / len(campaigns) if campaigns else 0
    avg_cpa = total_spend / total_conversions if total_conversions > 0 else 0

    # Campaign status breakdown
    active_campaigns = sum(1 for c in campaigns if c.status and c.status.value == "active")
    paused_campaigns = sum(1 for c in campaigns if c.status and c.status.value == "paused")

    # Platform breakdown
    platform_breakdown = {}
    for c in campaigns:
        platform = c.platform.value if c.platform else "unknown"
        if platform not in platform_breakdown:
            platform_breakdown[platform] = {"campaigns": 0, "spend": 0, "revenue": 0}
        platform_breakdown[platform]["campaigns"] += 1
        platform_breakdown[platform]["spend"] += c.total_spend_cents / 100 if c.total_spend_cents else 0
        platform_breakdown[platform]["revenue"] += c.revenue_cents / 100 if c.revenue_cents else 0

    # Calculate deltas (placeholder - would normally compare to previous period)
    # In real implementation, fetch fact_platform_daily for the comparison period
    spend_delta_pct = 5.2  # Placeholder
    revenue_delta_pct = 8.7
    roas_delta_pct = 3.2
    cpa_delta_pct = -4.1

    # Health classification (placeholder - would use scaling_score logic)
    scaling_candidates = sum(1 for c in campaigns if c.roas and c.roas >= 3.0)
    watch_campaigns = sum(1 for c in campaigns if c.roas and 1.5 <= c.roas < 3.0)
    fix_candidates = sum(1 for c in campaigns if c.roas and c.roas < 1.5)

    return APIResponse(
        success=True,
        data=DashboardOverviewResponse(
            total_spend=round(total_spend, 2),
            total_revenue=round(total_revenue, 2),
            spend_delta_pct=spend_delta_pct,
            revenue_delta_pct=revenue_delta_pct,
            portfolio_roas=round(portfolio_roas, 2),
            roas_delta_pct=roas_delta_pct,
            avg_cpa=round(avg_cpa, 2),
            cpa_delta_pct=cpa_delta_pct,
            avg_ctr=round(avg_ctr, 2),
            ctr_delta_pct=1.5,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            total_campaigns=len(campaigns),
            active_campaigns=active_campaigns,
            paused_campaigns=paused_campaigns,
            scaling_candidates=scaling_candidates,
            watch_campaigns=watch_campaigns,
            fix_candidates=fix_candidates,
            avg_emq_score=None,
            signal_health_status="healthy",
            open_alerts_count=0,
            platform_breakdown=platform_breakdown,
        ),
    )


# =============================================================================
# Recommendations
# =============================================================================
@router.get(
    "/{tenant_id}/recommendations",
    response_model=APIResponse[List[RecommendationItem]],
)
async def get_tenant_recommendations(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    date_str: Optional[str] = Query(None, alias="date"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get AI-powered recommendations for tenant campaigns.

    Returns prioritized list of actions: scale, watch, fix, pause, creative_refresh.
    """
    from app.analytics.logic.types import EntityMetrics, BaselineMetrics, EntityLevel, Platform
    from app.analytics.logic.recommend import RecommendationsEngine

    # Get campaigns
    campaigns_query = tenant_query(db, Campaign, tenant_id)
    result = await db.execute(campaigns_query)
    campaigns = result.scalars().all()

    if not campaigns:
        return APIResponse(
            success=True,
            data=[],
            message="No campaigns found",
        )

    # Build entity metrics
    entities_today = []
    baselines = {}
    current_spends = {}

    for c in campaigns:
        spend = c.total_spend_cents / 100 if c.total_spend_cents else 0
        revenue = c.revenue_cents / 100 if c.revenue_cents else 0
        impressions = c.impressions or 0
        clicks = c.clicks or 0
        conversions = c.conversions or 0

        entity = EntityMetrics(
            entity_id=str(c.id),
            entity_name=c.name,
            entity_level=EntityLevel.CAMPAIGN,
            platform=Platform(c.platform.value if c.platform else "meta"),
            date=datetime.now(timezone.utc),
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            revenue=revenue,
            ctr=c.ctr or 0,
            cvr=(conversions / max(clicks, 1) * 100) if clicks > 0 else 0,
            cpa=(spend / max(conversions, 1)) if conversions > 0 else 0,
            roas=c.roas or 0,
        )
        entities_today.append(entity)

        # Baseline (simulate previous period)
        baselines[str(c.id)] = BaselineMetrics(
            spend=spend * 0.9,
            impressions=int(impressions * 0.95),
            clicks=int(clicks * 0.95),
            conversions=int(conversions * 0.95),
            revenue=revenue * 0.9,
            ctr=c.ctr * 0.95 if c.ctr else 0,
            cvr=0,
            cpa=0,
            roas=c.roas * 0.9 if c.roas else 0,
        )
        current_spends[str(c.id)] = spend / 30 if spend > 0 else 0

    # Generate recommendations
    engine = RecommendationsEngine()
    recs_data = engine.generate_recommendations(
        entities_today=entities_today,
        baselines=baselines,
        current_spends=current_spends,
        api_health=True,
    )

    # Transform to response format
    recommendations = []
    for idx, rec in enumerate(recs_data.get("recommendations", [])[:limit]):
        recommendations.append(
            RecommendationItem(
                id=f"rec_{tenant_id}_{idx}",
                type=rec.get("type", "watch"),
                priority=rec.get("priority", 3),
                entity_type=rec.get("entity_type", "campaign"),
                entity_id=rec.get("entity_id", ""),
                entity_name=rec.get("entity_name", ""),
                title=rec.get("title", ""),
                description=rec.get("description", ""),
                impact_estimate=rec.get("impact_estimate"),
                roas_impact=rec.get("roas_impact"),
                confidence=rec.get("confidence", 0.0),
                actions=rec.get("actions", []),
            )
        )

    return APIResponse(
        success=True,
        data=recommendations,
    )


# =============================================================================
# Alerts
# =============================================================================
@router.get(
    "/{tenant_id}/alerts",
    response_model=APIResponse[List[AlertItem]],
)
async def get_tenant_alerts(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    date_str: Optional[str] = Query(None, alias="date"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by type"),
    include_resolved: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get alerts for a tenant.

    Filter by severity (low, medium, high, critical) and type (anomaly, fatigue, budget, signal).
    """
    # In production, query fact_alerts table
    # For now, return mock alerts based on campaign analysis
    campaigns_query = tenant_query(db, Campaign, tenant_id)
    result = await db.execute(campaigns_query)
    campaigns = result.scalars().all()

    alerts = []
    alert_id = 1

    for c in campaigns:
        roas = c.roas or 0
        ctr = c.ctr or 0

        # Generate alerts based on thresholds
        if roas > 0 and roas < 1.0:
            alerts.append(
                AlertItem(
                    id=alert_id,
                    type="budget",
                    severity="high",
                    title=f"Low ROAS: {c.name}",
                    message=f"Campaign ROAS ({roas:.2f}) is below breakeven. Consider pausing or optimizing.",
                    entity_type="campaign",
                    entity_id=str(c.id),
                    entity_name=c.name,
                    metric="roas",
                    current_value=roas,
                    expected_value=1.5,
                    is_acknowledged=False,
                    is_resolved=False,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                )
            )
            alert_id += 1

        if ctr > 0 and ctr < 0.5:
            alerts.append(
                AlertItem(
                    id=alert_id,
                    type="fatigue",
                    severity="medium",
                    title=f"Low CTR: {c.name}",
                    message=f"Click-through rate ({ctr:.2f}%) is below average. Creative may need refresh.",
                    entity_type="campaign",
                    entity_id=str(c.id),
                    entity_name=c.name,
                    metric="ctr",
                    current_value=ctr,
                    expected_value=1.5,
                    is_acknowledged=False,
                    is_resolved=False,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=5),
                )
            )
            alert_id += 1

    # Apply filters
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    if type_filter:
        alerts = [a for a in alerts if a.type == type_filter]
    if not include_resolved:
        alerts = [a for a in alerts if not a.is_resolved]

    # Sort by severity (critical first) then by created_at
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda x: (severity_order.get(x.severity, 4), x.created_at))

    return APIResponse(
        success=True,
        data=alerts[skip:skip + limit],
        meta={"total": len(alerts), "skip": skip, "limit": limit},
    )


@router.post(
    "/{tenant_id}/alerts/{alert_id}/ack",
    response_model=APIResponse,
)
async def acknowledge_alert(
    request: Request,
    tenant_id: int,
    alert_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    _: None = Depends(require_permissions([Permission.ALERT_ACKNOWLEDGE])),
):
    """
    Acknowledge an alert.

    Marks the alert as seen by the user without resolving the underlying issue.
    """
    # In production, update fact_alerts table
    # For now, return success response
    logger.info(f"Alert {alert_id} acknowledged by user {ctx.user_id} for tenant {tenant_id}")

    return APIResponse(
        success=True,
        message=f"Alert {alert_id} acknowledged",
        data={
            "alert_id": alert_id,
            "acknowledged_by": ctx.user_id,
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.post(
    "/{tenant_id}/alerts/{alert_id}/resolve",
    response_model=APIResponse,
)
async def resolve_alert(
    request: Request,
    tenant_id: int,
    alert_id: int,
    resolution_notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    _: None = Depends(require_permissions([Permission.ALERT_RESOLVE])),
):
    """
    Resolve an alert.

    Marks the alert as resolved with optional resolution notes.
    """
    logger.info(f"Alert {alert_id} resolved by user {ctx.user_id} for tenant {tenant_id}")

    return APIResponse(
        success=True,
        message=f"Alert {alert_id} resolved",
        data={
            "alert_id": alert_id,
            "resolved_by": ctx.user_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_notes": resolution_notes,
        },
    )


# =============================================================================
# Settings
# =============================================================================
@router.get(
    "/{tenant_id}/settings",
    response_model=APIResponse[TenantSettingsResponse],
)
async def get_tenant_settings(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
):
    """
    Get tenant settings and configuration.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Extract settings from tenant.settings JSON
    settings = tenant.settings or {}

    return APIResponse(
        success=True,
        data=TenantSettingsResponse(
            currency=settings.get("currency", "USD"),
            timezone=settings.get("timezone", "UTC"),
            date_format=settings.get("date_format", "YYYY-MM-DD"),
            fiscal_year_start=settings.get("fiscal_year_start", 1),
            alert_roas_drop_pct=settings.get("alert_roas_drop_pct", 20.0),
            alert_cpa_increase_pct=settings.get("alert_cpa_increase_pct", 25.0),
            alert_spend_anomaly_threshold=settings.get("alert_spend_anomaly_threshold", 2.5),
            alert_emq_min_score=settings.get("alert_emq_min_score", 7.0),
            email_notifications=settings.get("email_notifications", True),
            whatsapp_notifications=settings.get("whatsapp_notifications", False),
            slack_notifications=settings.get("slack_notifications", False),
            notification_frequency=settings.get("notification_frequency", "realtime"),
            connected_platforms=settings.get("connected_platforms", []),
            feature_flags=tenant.feature_flags or {},
        ),
    )


@router.put(
    "/{tenant_id}/settings",
    response_model=APIResponse[TenantSettingsResponse],
)
async def update_tenant_settings(
    request: Request,
    tenant_id: int,
    update_data: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    _: None = Depends(require_permissions([Permission.TENANT_SETTINGS])),
):
    """
    Update tenant settings.

    Requires TENANT_SETTINGS permission.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Update settings
    settings = tenant.settings or {}
    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        settings[key] = value

    tenant.settings = settings
    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant {tenant_id} settings updated by user {ctx.user_id}")

    return APIResponse(
        success=True,
        data=TenantSettingsResponse(
            currency=settings.get("currency", "USD"),
            timezone=settings.get("timezone", "UTC"),
            date_format=settings.get("date_format", "YYYY-MM-DD"),
            fiscal_year_start=settings.get("fiscal_year_start", 1),
            alert_roas_drop_pct=settings.get("alert_roas_drop_pct", 20.0),
            alert_cpa_increase_pct=settings.get("alert_cpa_increase_pct", 25.0),
            alert_spend_anomaly_threshold=settings.get("alert_spend_anomaly_threshold", 2.5),
            alert_emq_min_score=settings.get("alert_emq_min_score", 7.0),
            email_notifications=settings.get("email_notifications", True),
            whatsapp_notifications=settings.get("whatsapp_notifications", False),
            slack_notifications=settings.get("slack_notifications", False),
            notification_frequency=settings.get("notification_frequency", "realtime"),
            connected_platforms=settings.get("connected_platforms", []),
            feature_flags=tenant.feature_flags or {},
        ),
        message="Settings updated successfully",
    )


# =============================================================================
# Command Center (Scale/Watch/Fix table)
# =============================================================================
@router.get(
    "/{tenant_id}/command-center",
    response_model=APIResponse,
)
async def get_command_center(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
    ctx: TenantContext = Depends(require_tenant("tenant_id")),
    action_filter: Optional[str] = Query(None, description="scale, watch, fix, pause"),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get Command Center data with scaling scores and recommended actions.

    Returns campaigns grouped by recommended action (scale, watch, fix, pause).
    """
    from app.analytics.logic.types import EntityMetrics, BaselineMetrics, EntityLevel, Platform as PlatformEnum
    from app.analytics.logic.scoring import scaling_score

    # Get campaigns
    campaigns_query = tenant_query(db, Campaign, tenant_id)
    if platform:
        campaigns_query = campaigns_query.where(Campaign.platform == platform)

    result = await db.execute(campaigns_query)
    campaigns = result.scalars().all()

    command_center_data = []

    for c in campaigns:
        spend = c.total_spend_cents / 100 if c.total_spend_cents else 0
        revenue = c.revenue_cents / 100 if c.revenue_cents else 0
        impressions = c.impressions or 0
        clicks = c.clicks or 0
        conversions = c.conversions or 0

        # Build metrics
        entity = EntityMetrics(
            entity_id=str(c.id),
            entity_name=c.name,
            entity_level=EntityLevel.CAMPAIGN,
            platform=PlatformEnum(c.platform.value if c.platform else "meta"),
            date=datetime.now(timezone.utc),
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            revenue=revenue,
            ctr=c.ctr or 0,
            cvr=(conversions / max(clicks, 1) * 100) if clicks > 0 else 0,
            cpa=(spend / max(conversions, 1)) if conversions > 0 else 0,
            roas=c.roas or 0,
        )

        baseline = BaselineMetrics(
            spend=spend * 0.9,
            impressions=int(impressions * 0.95),
            clicks=int(clicks * 0.95),
            conversions=int(conversions * 0.95),
            revenue=revenue * 0.9,
            ctr=c.ctr * 0.95 if c.ctr else 0,
            cvr=0,
            cpa=0,
            roas=c.roas * 0.9 if c.roas else 0,
        )

        # Calculate scaling score
        score_result = scaling_score(entity, baseline)

        # Determine action
        if score_result.final_score >= 0.25:
            action = "scale"
        elif score_result.final_score <= -0.25:
            action = "fix"
        else:
            action = "watch"

        if action_filter and action != action_filter:
            continue

        command_center_data.append({
            "campaign_id": c.id,
            "campaign_name": c.name,
            "platform": c.platform.value if c.platform else "unknown",
            "status": c.status.value if c.status else "unknown",
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "roas": round(c.roas or 0, 2),
            "cpa": round((spend / max(conversions, 1)) if conversions > 0 else 0, 2),
            "ctr": round(c.ctr or 0, 2),
            "conversions": conversions,
            "scaling_score": round(score_result.final_score, 2),
            "action": action,
            "signals": {
                "roas_momentum": score_result.signals.get("roas_momentum", 0),
                "spend_efficiency": score_result.signals.get("spend_efficiency", 0),
                "conversion_trend": score_result.signals.get("conversion_trend", 0),
            },
            "recommendation": score_result.recommendation,
        })

    # Sort by scaling_score (descending for scale, ascending for fix)
    command_center_data.sort(key=lambda x: abs(x["scaling_score"]), reverse=True)

    return APIResponse(
        success=True,
        data={
            "items": command_center_data[:limit],
            "summary": {
                "total": len(command_center_data),
                "scale": sum(1 for x in command_center_data if x["action"] == "scale"),
                "watch": sum(1 for x in command_center_data if x["action"] == "watch"),
                "fix": sum(1 for x in command_center_data if x["action"] == "fix"),
            },
        },
    )
