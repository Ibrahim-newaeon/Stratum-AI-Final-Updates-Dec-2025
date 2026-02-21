# =============================================================================
# Stratum AI - Dashboard API Endpoints
# =============================================================================
"""
Unified dashboard API for the main application dashboard.

Provides consolidated endpoints for:
- Overview metrics (spend, revenue, ROAS, conversions)
- Campaign performance summary
- Signal health status
- AI recommendations with approve/reject
- Recent activity and alerts
- Platform breakdown

All data is scoped to the authenticated user's tenant.
"""

import csv
import json
import os
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUserDep, VerifiedUserDep
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import (
    AdPlatform,
    AuditAction,
    AuditLog,
    Campaign,
    CampaignStatus,
    Tenant,
)
from app.models.campaign_builder import ConnectionStatus, TenantPlatformConnection
from app.models.onboarding import OnboardingStatus, TenantOnboarding
from app.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# =============================================================================
# Enums
# =============================================================================


class TimePeriod(str, Enum):
    """Dashboard time period options."""

    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


class TrendDirection(str, Enum):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class RecommendationType(str, Enum):
    """Types of AI recommendations."""

    SCALE = "scale"
    WATCH = "watch"
    FIX = "fix"
    PAUSE = "pause"


class RecommendationStatus(str, Enum):
    """Recommendation action status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


# =============================================================================
# Pydantic Schemas
# =============================================================================


class MetricValue(BaseModel):
    """A metric with value, change, and trend."""

    value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    trend: TrendDirection = TrendDirection.STABLE
    formatted: str = ""  # Formatted display value


class OverviewMetrics(BaseModel):
    """Key performance metrics for dashboard overview."""

    spend: MetricValue
    revenue: MetricValue
    roas: MetricValue
    conversions: MetricValue
    cpa: MetricValue
    impressions: MetricValue
    clicks: MetricValue
    ctr: MetricValue


class SignalHealthSummary(BaseModel):
    """Signal health status for trust gate."""

    overall_score: int = Field(ge=0, le=100)
    status: str  # healthy, degraded, critical
    emq_score: Optional[float] = None
    data_freshness_minutes: Optional[int] = None
    api_health: bool = True
    issues: list[str] = []
    autopilot_enabled: bool = False


class PlatformSummary(BaseModel):
    """Performance summary for a single platform."""

    platform: str
    status: str  # connected, disconnected, error
    spend: float = 0
    revenue: float = 0
    roas: Optional[float] = None
    campaigns_count: int = 0
    last_synced_at: Optional[datetime] = None


class CampaignSummaryItem(BaseModel):
    """Summary of a campaign for dashboard listing."""

    id: int
    name: str
    platform: str
    status: str
    spend: float = 0
    revenue: float = 0
    roas: Optional[float] = None
    conversions: int = 0
    trend: TrendDirection = TrendDirection.STABLE
    scaling_score: Optional[float] = None
    recommendation: Optional[str] = None


class RecommendationItem(BaseModel):
    """AI recommendation for action."""

    id: str
    type: RecommendationType
    entity_type: str  # campaign, adset, ad
    entity_id: int
    entity_name: str
    platform: str
    title: str
    description: str
    impact_estimate: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: datetime


class ActivityItem(BaseModel):
    """Recent activity/event item."""

    id: int
    type: str  # action, alert, system
    title: str
    description: Optional[str] = None
    severity: Optional[str] = None  # info, warning, error, success
    timestamp: datetime
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class QuickAction(BaseModel):
    """Quick action button for dashboard."""

    id: str
    label: str
    icon: str
    action: str  # route or action identifier
    count: Optional[int] = None  # Badge count if applicable


class DashboardOverviewResponse(BaseModel):
    """Complete dashboard overview response."""

    # Account status
    onboarding_complete: bool = False
    has_connected_platforms: bool = False
    has_campaigns: bool = False

    # Time period
    period: str
    period_label: str
    date_range: dict[str, str]

    # Core metrics
    metrics: OverviewMetrics

    # Signal health
    signal_health: SignalHealthSummary

    # Platform breakdown
    platforms: list[PlatformSummary] = []

    # Quick stats
    total_campaigns: int = 0
    active_campaigns: int = 0
    pending_recommendations: int = 0
    active_alerts: int = 0

    # Metric visibility settings
    hidden_metrics: list[str] = []


class CampaignPerformanceResponse(BaseModel):
    """Campaign performance list response."""

    campaigns: list[CampaignSummaryItem]
    total: int
    page: int
    page_size: int
    sort_by: str
    sort_order: str


class RecommendationsResponse(BaseModel):
    """Recommendations list response."""

    recommendations: list[RecommendationItem]
    total: int
    by_type: dict[str, int]


class ActivityFeedResponse(BaseModel):
    """Activity feed response."""

    activities: list[ActivityItem]
    total: int
    has_more: bool


class QuickActionsResponse(BaseModel):
    """Quick actions for dashboard."""

    actions: list[QuickAction]


class ExportFormat(str, Enum):
    """Export format options."""

    CSV = "csv"
    JSON = "json"


class DashboardExportRequest(BaseModel):
    """Dashboard export request."""

    format: ExportFormat = ExportFormat.CSV
    period: TimePeriod = TimePeriod.LAST_30_DAYS
    include_campaigns: bool = True
    include_metrics: bool = True
    include_recommendations: bool = True


# =============================================================================
# Helper Functions
# =============================================================================


def get_date_range(
    period: TimePeriod,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> tuple[date, date]:
    """Get start and end dates for a time period."""
    today = datetime.now(UTC).date()

    if period == TimePeriod.CUSTOM and custom_start and custom_end:
        return custom_start, custom_end
    elif period == TimePeriod.TODAY:
        return today, today
    elif period == TimePeriod.YESTERDAY:
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == TimePeriod.LAST_7_DAYS:
        return today - timedelta(days=6), today
    elif period == TimePeriod.LAST_30_DAYS:
        return today - timedelta(days=29), today
    elif period == TimePeriod.LAST_90_DAYS:
        return today - timedelta(days=89), today
    elif period == TimePeriod.THIS_MONTH:
        return today.replace(day=1), today
    elif period == TimePeriod.LAST_MONTH:
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    else:
        return today - timedelta(days=6), today


def get_previous_period(start: date, end: date) -> tuple[date, date]:
    """Get the previous period for comparison."""
    period_length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)
    return prev_start, prev_end


def calculate_change(current: float, previous: float) -> tuple[float, TrendDirection]:
    """Calculate percentage change and trend direction."""
    if previous == 0:
        if current > 0:
            return 100.0, TrendDirection.UP
        return 0.0, TrendDirection.STABLE

    change = ((current - previous) / previous) * 100

    if change > 1:
        trend = TrendDirection.UP
    elif change < -1:
        trend = TrendDirection.DOWN
    else:
        trend = TrendDirection.STABLE

    return round(change, 1), trend


def format_currency(value: float, currency: str = "USD") -> str:
    """Format value as currency."""
    if value >= 1000000:
        return f"${value/1000000:.1f}M"
    elif value >= 1000:
        return f"${value/1000:.1f}K"
    else:
        return f"${value:.2f}"


def format_number(value: float) -> str:
    """Format large numbers with K/M suffix."""
    if value >= 1000000:
        return f"{value/1000000:.1f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    else:
        return f"{value:.0f}"


def format_percentage(value: float) -> str:
    """Format as percentage."""
    return f"{value:.2f}%"


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/overview", response_model=APIResponse[DashboardOverviewResponse])
async def get_dashboard_overview(
    current_user: CurrentUserDep,
    period: TimePeriod = Query(default=TimePeriod.LAST_7_DAYS),
    custom_start: Optional[date] = Query(default=None, alias="start_date", description="Custom range start (YYYY-MM-DD)"),
    custom_end: Optional[date] = Query(default=None, alias="end_date", description="Custom range end (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get the main dashboard overview.

    Returns key metrics, signal health, platform breakdown, and quick stats.
    Pass period=custom with start_date and end_date for custom date ranges.
    """
    tenant_id = current_user.tenant_id

    # Get date range
    start_date, end_date = get_date_range(period, custom_start, custom_end)
    prev_start, prev_end = get_previous_period(start_date, end_date)

    # Check onboarding status
    onboarding_result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant_id)
    )
    onboarding = onboarding_result.scalar_one_or_none()
    onboarding_complete = bool(onboarding and onboarding.status == OnboardingStatus.COMPLETED)

    # Get connected platforms
    platforms_result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
            )
        )
    )
    connected_platforms = platforms_result.scalars().all()
    # Also check env-var credentials as fallback
    has_env_creds = bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("TIKTOK_ACCESS_TOKEN"))
    has_connected_platforms = len(connected_platforms) > 0 or has_env_creds

    # Get campaigns and aggregate metrics
    campaigns_result = await db.execute(
        select(Campaign).where(
            and_(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        )
    )
    campaigns = campaigns_result.scalars().all()
    has_campaigns = len(campaigns) > 0

    # Aggregate current period metrics from CampaignMetric (time-series) for
    # the selected date range instead of summing all-time Campaign totals.
    from app.models import CampaignMetric

    period_agg_result = await db.execute(
        select(
            func.coalesce(func.sum(CampaignMetric.spend_cents), 0).label("spend"),
            func.coalesce(func.sum(CampaignMetric.revenue_cents), 0).label("revenue"),
            func.coalesce(func.sum(CampaignMetric.conversions), 0).label("conversions"),
            func.coalesce(func.sum(CampaignMetric.impressions), 0).label("impressions"),
            func.coalesce(func.sum(CampaignMetric.clicks), 0).label("clicks"),
        ).where(
            and_(
                CampaignMetric.tenant_id == tenant_id,
                CampaignMetric.date >= start_date,
                CampaignMetric.date <= end_date,
            )
        )
    )
    period_agg = period_agg_result.one()

    current_spend = (period_agg.spend or 0) / 100
    current_revenue = (period_agg.revenue or 0) / 100
    current_conversions = int(period_agg.conversions or 0)
    current_impressions = int(period_agg.impressions or 0)
    current_clicks = int(period_agg.clicks or 0)

    # Calculate derived metrics
    current_roas = current_revenue / current_spend if current_spend > 0 else 0
    current_cpa = current_spend / current_conversions if current_conversions > 0 else 0
    current_ctr = (current_clicks / current_impressions * 100) if current_impressions > 0 else 0

    # Query previous period from fact_platform_daily for real comparisons
    try:
        prev_result = await db.execute(
            text(
                "SELECT COALESCE(SUM(spend), 0) as spend, "
                "COALESCE(SUM(revenue), 0) as revenue, "
                "COALESCE(SUM(conversions), 0) as conversions, "
                "COALESCE(SUM(impressions), 0) as impressions, "
                "COALESCE(SUM(clicks), 0) as clicks "
                "FROM fact_platform_daily "
                "WHERE tenant_id = :tenant_id AND date BETWEEN :start AND :end"
            ),
            {"tenant_id": tenant_id, "start": prev_start, "end": prev_end},
        )
        prev_row = prev_result.mappings().first()
        if prev_row and prev_row["spend"] > 0:
            prev_spend = float(prev_row["spend"])
            prev_revenue = float(prev_row["revenue"])
            prev_conversions = int(prev_row["conversions"])
            prev_impressions = int(prev_row["impressions"])
            prev_clicks = int(prev_row["clicks"])
        else:
            # No historical data yet — show zero change
            prev_spend = current_spend
            prev_revenue = current_revenue
            prev_conversions = current_conversions
            prev_impressions = current_impressions
            prev_clicks = current_clicks
    except Exception:
        # Table may not have data yet — show zero change
        prev_spend = current_spend
        prev_revenue = current_revenue
        prev_conversions = current_conversions
        prev_impressions = current_impressions
        prev_clicks = current_clicks

    prev_roas = prev_revenue / prev_spend if prev_spend > 0 else 0
    prev_cpa = prev_spend / prev_conversions if prev_conversions > 0 else 0
    prev_ctr = (prev_clicks / prev_impressions * 100) if prev_impressions > 0 else 0

    # Build metrics with changes
    def build_metric(current: float, previous: float, formatter=format_currency) -> MetricValue:
        change, trend = calculate_change(current, previous)
        return MetricValue(
            value=current,
            previous_value=previous,
            change_percent=change,
            trend=trend,
            formatted=formatter(current),
        )

    metrics = OverviewMetrics(
        spend=build_metric(current_spend, prev_spend),
        revenue=build_metric(current_revenue, prev_revenue),
        roas=build_metric(current_roas, prev_roas, lambda v: f"{v:.2f}x"),
        conversions=build_metric(current_conversions, prev_conversions, format_number),
        cpa=build_metric(current_cpa, prev_cpa),
        impressions=build_metric(current_impressions, prev_impressions, format_number),
        clicks=build_metric(current_clicks, prev_clicks, format_number),
        ctr=build_metric(current_ctr, prev_ctr, format_percentage),
    )

    # Signal health (mock for now, integrate with trust layer)
    signal_health = SignalHealthSummary(
        overall_score=85 if has_campaigns else 0,
        status="healthy" if has_campaigns else "unknown",
        emq_score=0.92 if has_campaigns else None,
        data_freshness_minutes=5 if has_campaigns else None,
        api_health=True,
        issues=[],
        autopilot_enabled=onboarding.automation_mode == "autopilot" if onboarding else False,
    )

    # Platform breakdown
    platforms_summary = []
    for platform in AdPlatform:
        connection = next((c for c in connected_platforms if c.platform == platform), None)

        platform_campaigns = [c for c in campaigns if c.platform == platform]
        platform_spend = sum(c.total_spend_cents or 0 for c in platform_campaigns) / 100
        platform_revenue = sum(c.revenue_cents or 0 for c in platform_campaigns) / 100

        # Check env-var credentials for platform status
        env_connected = False
        if platform == AdPlatform.META and os.getenv("META_ACCESS_TOKEN"):
            env_connected = True
        elif platform == AdPlatform.TIKTOK and os.getenv("TIKTOK_ACCESS_TOKEN"):
            env_connected = True

        platforms_summary.append(
            PlatformSummary(
                platform=platform.value,
                status="connected" if (connection or env_connected) else "disconnected",
                spend=platform_spend,
                revenue=platform_revenue,
                roas=platform_revenue / platform_spend if platform_spend > 0 else None,
                campaigns_count=len(platform_campaigns),
                last_synced_at=connection.last_refreshed_at if connection else None,
            )
        )

    # Campaign stats
    active_campaigns = len([c for c in campaigns if c.status == CampaignStatus.ACTIVE])

    # Load tenant's hidden_metrics setting
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    hidden_metrics = (tenant.settings or {}).get("hidden_metrics", []) if tenant else []

    # Period label
    period_labels = {
        TimePeriod.TODAY: "Today",
        TimePeriod.YESTERDAY: "Yesterday",
        TimePeriod.LAST_7_DAYS: "Last 7 Days",
        TimePeriod.LAST_30_DAYS: "Last 30 Days",
        TimePeriod.LAST_90_DAYS: "Last 90 Days",
        TimePeriod.THIS_MONTH: "This Month",
        TimePeriod.LAST_MONTH: "Last Month",
        TimePeriod.CUSTOM: f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}",
    }

    return APIResponse(
        success=True,
        data=DashboardOverviewResponse(
            onboarding_complete=onboarding_complete,
            has_connected_platforms=has_connected_platforms,
            has_campaigns=has_campaigns,
            period=period.value,
            period_label=period_labels.get(period, "Last 7 Days"),
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            metrics=metrics,
            signal_health=signal_health,
            platforms=platforms_summary,
            total_campaigns=len(campaigns),
            active_campaigns=active_campaigns,
            pending_recommendations=0,
            active_alerts=0,
            hidden_metrics=hidden_metrics,
        ),
    )


@router.get("/campaigns", response_model=APIResponse[CampaignPerformanceResponse])
async def get_campaign_performance(
    current_user: CurrentUserDep,
    period: TimePeriod = Query(default=TimePeriod.LAST_7_DAYS),
    custom_start: Optional[date] = Query(default=None, alias="start_date"),
    custom_end: Optional[date] = Query(default=None, alias="end_date"),
    platform: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query(default="spend"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get campaign performance for dashboard.

    Returns paginated list of campaigns with key metrics and recommendations.
    """
    tenant_id = current_user.tenant_id

    # Build query
    query = select(Campaign).where(
        and_(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )

    # Apply filters
    if platform:
        try:
            platform_enum = AdPlatform(platform.lower())
            query = query.where(Campaign.platform == platform_enum)
        except ValueError:
            pass

    if status_filter:
        try:
            status_enum = CampaignStatus(status_filter.lower())
            query = query.where(Campaign.status == status_enum)
        except ValueError:
            pass

    # Apply sorting
    sort_column = getattr(Campaign, sort_by, Campaign.total_spend_cents)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    # Build response
    campaign_items = []
    for c in campaigns:
        spend = (c.total_spend_cents or 0) / 100
        revenue = (c.revenue_cents or 0) / 100

        # Determine recommendation based on ROAS
        roas = revenue / spend if spend > 0 else 0
        if roas >= 3:
            recommendation = "scale"
            scaling_score = 0.8
        elif roas >= 1.5:
            recommendation = "watch"
            scaling_score = 0.2
        elif roas > 0:
            recommendation = "fix"
            scaling_score = -0.3
        else:
            recommendation = None
            scaling_score = None

        campaign_items.append(
            CampaignSummaryItem(
                id=c.id,
                name=c.name,
                platform=c.platform.value,
                status=c.status.value,
                spend=spend,
                revenue=revenue,
                roas=roas if spend > 0 else None,
                conversions=c.conversions or 0,
                trend=TrendDirection.UP if roas >= 2 else TrendDirection.STABLE,
                scaling_score=scaling_score,
                recommendation=recommendation,
            )
        )

    return APIResponse(
        success=True,
        data=CampaignPerformanceResponse(
            campaigns=campaign_items,
            total=total,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@router.get("/recommendations", response_model=APIResponse[RecommendationsResponse])
async def get_recommendations(
    current_user: VerifiedUserDep,
    type_filter: Optional[RecommendationType] = Query(None, alias="type"),
    status_filter: Optional[RecommendationStatus] = Query(None, alias="status"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get AI recommendations for the dashboard.

    Returns prioritized recommendations for campaigns that need attention.
    """
    tenant_id = current_user.tenant_id

    # Get campaigns to generate recommendations
    result = await db.execute(
        select(Campaign)
        .where(
            and_(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
                Campaign.status == CampaignStatus.ACTIVE,
            )
        )
        .limit(50)
    )
    campaigns = result.scalars().all()

    # Generate recommendations based on campaign performance
    recommendations = []
    by_type = {t.value: 0 for t in RecommendationType}

    for c in campaigns:
        spend = (c.total_spend_cents or 0) / 100
        revenue = (c.revenue_cents or 0) / 100
        roas = revenue / spend if spend > 0 else 0

        # Determine recommendation type
        if roas >= 3:
            rec_type = RecommendationType.SCALE
            title = f"Scale {c.name}"
            description = (
                f"ROAS of {roas:.2f}x exceeds target. Consider increasing budget by 20-30%."
            )
            confidence = 0.85
            impact = f"+${spend * 0.25:.0f} potential revenue"
        elif roas < 1:
            rec_type = RecommendationType.FIX
            title = f"Fix {c.name}"
            description = f"ROAS of {roas:.2f}x is below breakeven. Review targeting and creatives."
            confidence = 0.75
            impact = f"Save ${spend * 0.3:.0f} in wasted spend"
        elif roas < 1.5:
            rec_type = RecommendationType.WATCH
            title = f"Watch {c.name}"
            description = f"ROAS of {roas:.2f}x is marginal. Monitor for 24-48 hours."
            confidence = 0.65
            impact = None
        else:
            continue  # Skip stable campaigns

        # Apply filters
        if type_filter and rec_type != type_filter:
            continue

        by_type[rec_type.value] += 1

        recommendations.append(
            RecommendationItem(
                id=f"rec_{c.id}_{rec_type.value}",
                type=rec_type,
                entity_type="campaign",
                entity_id=c.id,
                entity_name=c.name,
                platform=c.platform.value,
                title=title,
                description=description,
                impact_estimate=impact,
                confidence=confidence,
                status=RecommendationStatus.PENDING,
                created_at=datetime.now(UTC),
            )
        )

    # Sort by confidence and limit
    recommendations.sort(key=lambda r: r.confidence, reverse=True)
    recommendations = recommendations[:limit]

    return APIResponse(
        success=True,
        data=RecommendationsResponse(
            recommendations=recommendations,
            total=len(recommendations),
            by_type=by_type,
        ),
    )


@router.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Approve a recommendation for execution.

    In autopilot mode, this queues the action for automatic execution.
    In manual/assisted mode, this marks it as approved.
    """
    # Parse recommendation ID to get campaign and type
    parts = recommendation_id.split("_")
    if len(parts) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recommendation ID"
        )

    logger.info(
        "recommendation_approved",
        recommendation_id=recommendation_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return APIResponse(
        success=True,
        data={"message": "Recommendation approved", "status": "approved"},
    )


@router.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reject a recommendation.
    """
    logger.info(
        "recommendation_rejected",
        recommendation_id=recommendation_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return APIResponse(
        success=True,
        data={"message": "Recommendation rejected", "status": "rejected"},
    )


@router.get("/activity", response_model=APIResponse[ActivityFeedResponse])
async def get_activity_feed(
    current_user: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get recent activity feed for the dashboard.

    Returns recent actions, alerts, and system events.
    """
    tenant_id = current_user.tenant_id

    # Get audit logs for activity
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit + 1)  # Get one extra to check has_more
    )
    logs = result.scalars().all()

    has_more = len(logs) > limit
    logs = logs[:limit]

    # Build activity items
    activities = []
    for log in logs:
        # Determine activity type and severity
        if log.action in [AuditAction.LOGIN, AuditAction.LOGOUT]:
            activity_type = "auth"
            severity = "info"
            title = "User logged in" if log.action == AuditAction.LOGIN else "User logged out"
        elif log.action == AuditAction.CREATE:
            activity_type = "action"
            severity = "success"
            title = f"Created {log.resource_type}"
        elif log.action == AuditAction.UPDATE:
            activity_type = "action"
            severity = "info"
            title = f"Updated {log.resource_type}"
        elif log.action == AuditAction.DELETE:
            activity_type = "action"
            severity = "warning"
            title = f"Deleted {log.resource_type}"
        else:
            activity_type = "system"
            severity = "info"
            title = f"{log.action.value.title()} {log.resource_type}"

        activities.append(
            ActivityItem(
                id=log.id,
                type=activity_type,
                title=title,
                description=None,
                severity=severity,
                timestamp=log.created_at,
                entity_type=log.resource_type,
                entity_id=log.resource_id,
            )
        )

    # Get total count
    count_result = await db.execute(select(func.count()).where(AuditLog.tenant_id == tenant_id))
    total = count_result.scalar() or 0

    return APIResponse(
        success=True,
        data=ActivityFeedResponse(
            activities=activities,
            total=total,
            has_more=has_more,
        ),
    )


@router.get("/quick-actions", response_model=APIResponse[QuickActionsResponse])
async def get_quick_actions(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get quick action buttons for the dashboard.

    Returns contextual actions based on the current state.
    """
    tenant_id = current_user.tenant_id

    actions = []

    # Check onboarding status
    onboarding_result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant_id)
    )
    onboarding = onboarding_result.scalar_one_or_none()

    if not onboarding or onboarding.status != OnboardingStatus.COMPLETED:
        actions.append(
            QuickAction(
                id="complete_onboarding",
                label="Complete Setup",
                icon="settings",
                action="/dashboard/onboarding",
            )
        )

    # Check for connected platforms
    platforms_result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
            )
        )
    )
    connected = platforms_result.scalars().all()

    has_env_platform = bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("TIKTOK_ACCESS_TOKEN"))
    if len(connected) == 0 and not has_env_platform:
        actions.append(
            QuickAction(
                id="connect_platform",
                label="Connect Platform",
                icon="link",
                action="/dashboard/campaigns/connect",
            )
        )

    # Check for campaigns
    campaigns_result = await db.execute(
        select(func.count()).where(
            and_(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        )
    )
    campaign_count = campaigns_result.scalar() or 0

    if campaign_count == 0 and len(connected) > 0:
        actions.append(
            QuickAction(
                id="sync_campaigns",
                label="Sync Campaigns",
                icon="refresh",
                action="/dashboard/campaigns",
            )
        )

    # Standard actions
    actions.extend(
        [
            QuickAction(
                id="create_campaign",
                label="New Campaign",
                icon="plus",
                action="/dashboard/campaigns",
            ),
            QuickAction(
                id="view_reports",
                label="Reports",
                icon="chart",
                action="/dashboard/custom-reports",
            ),
            QuickAction(
                id="manage_rules",
                label="Automation",
                icon="zap",
                action="/dashboard/rules",
            ),
        ]
    )

    return APIResponse(
        success=True,
        data=QuickActionsResponse(actions=actions),
    )


@router.get("/signal-health", response_model=APIResponse[SignalHealthSummary])
async def get_signal_health(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed signal health status.

    Returns the current trust gate status including EMQ, data freshness,
    and any issues that may affect autopilot.
    """
    tenant_id = current_user.tenant_id

    # Get onboarding settings for thresholds
    onboarding_result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant_id)
    )
    onboarding = onboarding_result.scalar_one_or_none()

    # Get connected platforms count
    platforms_result = await db.execute(
        select(func.count()).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
            )
        )
    )
    connected_count = platforms_result.scalar() or 0

    # Check if platforms are available via env vars (fallback)
    has_env_credentials = bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("TIKTOK_ACCESS_TOKEN"))

    # Also check if campaigns exist (synced via env credentials)
    campaign_count_result = await db.execute(
        select(func.count()).where(
            and_(Campaign.tenant_id == tenant_id, Campaign.is_deleted == False)
        )
    )
    has_campaigns = (campaign_count_result.scalar() or 0) > 0

    # Signal health based on actual platform connectivity and data state
    if connected_count == 0 and not has_env_credentials and not has_campaigns:
        return APIResponse(
            success=True,
            data=SignalHealthSummary(
                overall_score=0,
                status="unknown",
                emq_score=None,
                data_freshness_minutes=None,
                api_health=True,
                issues=["No platforms connected"],
                autopilot_enabled=False,
            ),
        )

    # Compute signal health from real data
    issues: list[str] = []
    overall_score = 0
    emq_score: float | None = None
    data_freshness: int | None = None

    try:
        # Check data freshness from fact_platform_daily
        freshness_result = await db.execute(
            text(
                "SELECT MAX(date) as latest_date "
                "FROM fact_platform_daily WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
        latest_row = freshness_result.mappings().first()
        latest_date = latest_row["latest_date"] if latest_row else None

        if latest_date:
            days_stale = (datetime.now(UTC).date() - latest_date).days
            data_freshness = days_stale * 24 * 60  # Convert to minutes
            freshness_score = max(0, 100 - (days_stale * 15))  # -15 per day stale
        else:
            freshness_score = 0
            issues.append("No historical data synced yet")

        # Check EMQ from fact_alerts (emq_degraded alerts)
        emq_result = await db.execute(
            text(
                "SELECT COUNT(*) as degraded_count "
                "FROM fact_alerts WHERE tenant_id = :tenant_id "
                "AND alert_type = 'emq_degraded' "
                "AND (resolved = false OR resolved IS NULL) "
                "AND date >= CURRENT_DATE - INTERVAL '7 days'"
            ),
            {"tenant_id": tenant_id},
        )
        emq_row = emq_result.mappings().first()
        emq_degraded = emq_row["degraded_count"] if emq_row else 0

        if emq_degraded == 0:
            emq_score = 0.95
            emq_component = 95
        elif emq_degraded <= 2:
            emq_score = 0.75
            emq_component = 75
            issues.append(f"{emq_degraded} EMQ degradation alerts active")
        else:
            emq_score = 0.50
            emq_component = 50
            issues.append(f"{emq_degraded} EMQ degradation alerts active")

        # Platform connectivity score
        connectivity_score = 100 if (connected_count > 0 or has_env_credentials) else 0

        # Weighted overall score
        overall_score = int(
            freshness_score * 0.4 + emq_component * 0.35 + connectivity_score * 0.25
        )
    except Exception:
        # If analytics tables aren't populated yet, derive from connectivity
        if connected_count > 0 or has_env_credentials:
            overall_score = 75
            if has_campaigns:
                overall_score = 80
        else:
            overall_score = 0
            issues.append("Signal health data not yet available")

    # Check thresholds
    autopilot_threshold = onboarding.trust_threshold_autopilot if onboarding else 70
    alert_threshold = onboarding.trust_threshold_alert if onboarding else 40

    if overall_score < alert_threshold:
        status = "critical"
        issues.append("Signal health below critical threshold")
    elif overall_score < autopilot_threshold:
        status = "degraded"
        issues.append("Signal health below autopilot threshold")
    else:
        status = "healthy"

    autopilot_enabled = bool(
        onboarding
        and onboarding.automation_mode == "autopilot"
        and overall_score >= autopilot_threshold
    )

    return APIResponse(
        success=True,
        data=SignalHealthSummary(
            overall_score=overall_score,
            status=status,
            emq_score=emq_score,
            data_freshness_minutes=data_freshness,
            api_health=True,
            issues=issues,
            autopilot_enabled=autopilot_enabled,
        ),
    )


@router.post("/export")
async def export_dashboard(
    request: DashboardExportRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Export dashboard data as CSV or JSON.

    Returns a file download with campaigns, metrics, and recommendations.
    """
    tenant_id = current_user.tenant_id

    # Get date range
    start_date, end_date = get_date_range(request.period)

    # Get campaigns with their metrics filtered by the selected date range
    campaigns_result = await db.execute(
        select(Campaign).where(
            and_(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        )
    )
    campaigns = campaigns_result.scalars().all()

    # Aggregate metrics from CampaignMetric (time-series) within the date range
    # This ensures exports reflect the selected period, not all-time totals
    from app.base_models import CampaignMetric

    period_metrics_result = await db.execute(
        select(
            CampaignMetric.campaign_id,
            func.sum(CampaignMetric.spend_cents).label("spend_cents"),
            func.sum(CampaignMetric.revenue_cents).label("revenue_cents"),
            func.sum(CampaignMetric.conversions).label("conversions"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.clicks).label("clicks"),
        ).where(
            and_(
                CampaignMetric.tenant_id == tenant_id,
                CampaignMetric.date >= start_date,
                CampaignMetric.date <= end_date,
            )
        ).group_by(CampaignMetric.campaign_id)
    )
    period_metrics_by_campaign = {
        row.campaign_id: row for row in period_metrics_result.mappings().all()
    }

    # Build export data
    export_data = {
        "export_date": datetime.now(UTC).isoformat(),
        "period": request.period.value,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    }

    # Add metrics summary — use period-filtered data from CampaignMetric
    if request.include_metrics:
        total_spend_cents = sum(
            (m.get("spend_cents") or 0) for m in period_metrics_by_campaign.values()
        )
        total_revenue_cents = sum(
            (m.get("revenue_cents") or 0) for m in period_metrics_by_campaign.values()
        )
        total_conversions = sum(
            (m.get("conversions") or 0) for m in period_metrics_by_campaign.values()
        )
        total_impressions = sum(
            (m.get("impressions") or 0) for m in period_metrics_by_campaign.values()
        )
        total_clicks = sum(
            (m.get("clicks") or 0) for m in period_metrics_by_campaign.values()
        )

        # Convert cents to dollars at the end to avoid floating point accumulation
        total_spend = total_spend_cents / 100
        total_revenue = total_revenue_cents / 100

        export_data["metrics"] = {
            "total_spend": round(total_spend, 2),
            "total_revenue": round(total_revenue, 2),
            "roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
            "conversions": total_conversions,
            "cpa": round(total_spend / total_conversions, 2) if total_conversions > 0 else 0,
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0,
        }

    # Add campaigns — use period-filtered metrics, not all-time totals
    if request.include_campaigns:
        export_data["campaigns"] = []
        for c in campaigns:
            pm = period_metrics_by_campaign.get(c.id)
            c_spend_cents = (pm.get("spend_cents") or 0) if pm else 0
            c_revenue_cents = (pm.get("revenue_cents") or 0) if pm else 0
            c_spend = c_spend_cents / 100
            c_revenue = c_revenue_cents / 100

            export_data["campaigns"].append({
                "id": c.id,
                "name": c.name,
                "platform": c.platform.value,
                "status": c.status.value,
                "spend": round(c_spend, 2),
                "revenue": round(c_revenue, 2),
                "conversions": (pm.get("conversions") or 0) if pm else 0,
                "impressions": (pm.get("impressions") or 0) if pm else 0,
                "clicks": (pm.get("clicks") or 0) if pm else 0,
                "roas": round(c_revenue / c_spend, 2) if c_spend > 0 else 0,
            })

    # Add recommendations (mock for demo)
    if request.include_recommendations:
        recommendations = []
        for c in campaigns:
            spend = (c.total_spend_cents or 0) / 100
            revenue = (c.revenue_cents or 0) / 100
            roas = revenue / spend if spend > 0 else 0

            if roas >= 3:
                recommendations.append(
                    {
                        "campaign": c.name,
                        "type": "scale",
                        "description": f"Scale budget by 20-30% - ROAS {roas:.2f}x",
                    }
                )
            elif roas < 1 and spend > 0:
                recommendations.append(
                    {
                        "campaign": c.name,
                        "type": "fix",
                        "description": f"Review targeting - ROAS {roas:.2f}x below breakeven",
                    }
                )

        export_data["recommendations"] = recommendations

    # Generate response based on format
    if request.format == ExportFormat.CSV:
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write metrics header
        if request.include_metrics:
            writer.writerow(["=== METRICS SUMMARY ==="])
            writer.writerow(["Metric", "Value"])
            for key, value in export_data.get("metrics", {}).items():
                if isinstance(value, float):
                    writer.writerow([key, f"{value:.2f}"])
                else:
                    writer.writerow([key, value])
            writer.writerow([])

        # Write campaigns
        if request.include_campaigns and export_data.get("campaigns"):
            writer.writerow(["=== CAMPAIGNS ==="])
            headers = [
                "ID",
                "Name",
                "Platform",
                "Status",
                "Spend",
                "Revenue",
                "ROAS",
                "Conversions",
                "Impressions",
                "Clicks",
            ]
            writer.writerow(headers)
            for campaign in export_data["campaigns"]:
                writer.writerow(
                    [
                        campaign["id"],
                        campaign["name"],
                        campaign["platform"],
                        campaign["status"],
                        f"${campaign['spend']:.2f}",
                        f"${campaign['revenue']:.2f}",
                        f"{campaign['roas']:.2f}x",
                        campaign["conversions"],
                        campaign["impressions"],
                        campaign["clicks"],
                    ]
                )
            writer.writerow([])

        # Write recommendations
        if request.include_recommendations and export_data.get("recommendations"):
            writer.writerow(["=== RECOMMENDATIONS ==="])
            writer.writerow(["Campaign", "Type", "Description"])
            for rec in export_data["recommendations"]:
                writer.writerow([rec["campaign"], rec["type"], rec["description"]])

        output.seek(0)
        filename = f"stratum-dashboard-export-{datetime.now(UTC).date().isoformat()}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    else:
        # JSON format
        filename = f"stratum-dashboard-export-{datetime.now(UTC).date().isoformat()}.json"

        return StreamingResponse(
            iter([json.dumps(export_data, indent=2, default=str)]),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# =============================================================================
# Metric Visibility Settings
# =============================================================================


class MetricVisibilityRequest(BaseModel):
    """Request to update metric visibility."""

    hidden_metrics: list[str] = Field(
        ...,
        description="List of metric keys to hide (e.g. ['cpc', 'cpm', 'cpv'])",
    )


class MetricVisibilityResponse(BaseModel):
    """Current metric visibility settings."""

    hidden_metrics: list[str] = []
    available_metrics: list[dict[str, str]] = []


AVAILABLE_METRICS = [
    {"key": "cpc", "label": "Cost per Click (CPC)"},
    {"key": "cpm", "label": "Cost per 1K Impressions (CPM)"},
    {"key": "cpv", "label": "Cost per View (CPV)"},
    {"key": "cpa", "label": "Cost per Acquisition (CPA)"},
    {"key": "spend", "label": "Total Spend"},
    {"key": "roas", "label": "Return on Ad Spend (ROAS)"},
    {"key": "ctr", "label": "Click-Through Rate (CTR)"},
    {"key": "impressions", "label": "Impressions"},
    {"key": "clicks", "label": "Clicks"},
    {"key": "conversions", "label": "Conversions"},
    {"key": "revenue", "label": "Revenue"},
]


@router.get("/settings/metric-visibility", response_model=APIResponse[MetricVisibilityResponse])
async def get_metric_visibility(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Get current metric visibility settings for the tenant."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    hidden = (tenant.settings or {}).get("hidden_metrics", []) if tenant else []

    return APIResponse(
        success=True,
        data=MetricVisibilityResponse(
            hidden_metrics=hidden,
            available_metrics=AVAILABLE_METRICS,
        ),
    )


@router.patch("/settings/metric-visibility", response_model=APIResponse[MetricVisibilityResponse])
async def update_metric_visibility(
    request_data: MetricVisibilityRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update which metrics are hidden on the dashboard.

    Accepts a list of metric keys to hide. Pass an empty list to show all.
    Valid keys: cpc, cpm, cpv, cpa, spend, roas, ctr, impressions, clicks, conversions, revenue
    """
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Validate metric keys
    valid_keys = {m["key"] for m in AVAILABLE_METRICS}
    invalid = [k for k in request_data.hidden_metrics if k not in valid_keys]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric keys: {invalid}",
        )

    # Update tenant settings JSONB
    current_settings = dict(tenant.settings or {})
    current_settings["hidden_metrics"] = request_data.hidden_metrics
    tenant.settings = current_settings

    await db.commit()

    logger.info(
        "metric_visibility_updated",
        tenant_id=current_user.tenant_id,
        hidden=request_data.hidden_metrics,
    )

    return APIResponse(
        success=True,
        data=MetricVisibilityResponse(
            hidden_metrics=request_data.hidden_metrics,
            available_metrics=AVAILABLE_METRICS,
        ),
        message="Metric visibility updated",
    )
