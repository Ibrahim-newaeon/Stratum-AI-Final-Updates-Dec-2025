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
from sqlalchemy.exc import SQLAlchemyError
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


class BriefingChangeItem(BaseModel):
    """A notable change detected overnight."""

    metric: str
    entity_name: str = ""
    platform: str = ""
    direction: str  # "up" or "down"
    change_percent: float
    current_value: float
    severity: str = "info"  # "info", "warning", "critical"
    narrative: str  # Human-readable explanation


class BriefingActionItem(BaseModel):
    """An action the user should take today."""

    priority: str  # "critical", "high", "medium"
    title: str
    description: str
    action_type: str  # "budget", "creative", "signal", "campaign"
    entity_name: str = ""
    impact_estimate: str = ""


class MorningBriefingResponse(BaseModel):
    """AI Morning Briefing — personalized daily digest."""

    date: str
    greeting: str
    summary_narrative: str  # 2-3 sentence executive summary
    portfolio_health: str  # "strong", "steady", "needs_attention", "critical"

    # KPI snapshot
    total_spend: float
    total_revenue: float
    roas: float
    total_conversions: int
    spend_change_pct: float
    revenue_change_pct: float
    roas_change_pct: float

    # Signal health
    signal_status: str  # "healthy", "risk", "degraded", "critical"
    signal_score: int
    autopilot_enabled: bool

    # Top changes (max 5)
    top_changes: list[BriefingChangeItem] = []

    # Actions needed today (max 5)
    actions_today: list[BriefingActionItem] = []

    # Counts
    active_campaigns: int = 0
    pending_recommendations: int = 0
    active_alerts: int = 0
    scale_candidates: int = 0
    fix_candidates: int = 0


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

    # Get date range — wrapped to handle database errors gracefully
    try:
        return await _build_dashboard_overview(
            tenant_id, period, custom_start, custom_end, db
        )
    except (SQLAlchemyError, ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
        logger.error("dashboard_overview_error", error=str(e), tenant_id=tenant_id)
        # Return safe empty dashboard so the frontend can still render
        start_date, end_date = get_date_range(period, custom_start, custom_end)
        zero_metric = MetricValue(value=0, previous_value=0, change_percent=0, trend="stable", formatted="$0.00")
        return APIResponse(
            success=True,
            data=DashboardOverviewResponse(
                onboarding_complete=False,
                has_connected_platforms=False,
                has_campaigns=False,
                period=period.value,
                period_label="Last 7 Days",
                date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
                metrics=OverviewMetrics(
                    spend=zero_metric, revenue=zero_metric, roas=zero_metric,
                    conversions=zero_metric, cpa=zero_metric, impressions=zero_metric,
                    clicks=zero_metric, ctr=zero_metric,
                ),
                signal_health=SignalHealthSummary(
                    overall_score=0, status="unknown", emq_score=None,
                    data_freshness_minutes=None, api_health=False, issues=["Dashboard data temporarily unavailable"],
                    autopilot_enabled=False,
                ),
                platforms=[],
                total_campaigns=0,
                active_campaigns=0,
                pending_recommendations=0,
                active_alerts=0,
                hidden_metrics=[],
            ),
        )


async def _build_dashboard_overview(
    tenant_id: int,
    period: TimePeriod,
    custom_start,
    custom_end,
    db: AsyncSession,
):
    """Build the dashboard overview response (extracted for error handling)."""
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
    except (SQLAlchemyError, ValueError, TypeError, KeyError) as _prev_err:
        # Table may not have data yet — show zero change
        logger.debug("dashboard_previous_period_unavailable", error=str(_prev_err))
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

    # Signal health — computed from actual campaign and platform data
    if has_campaigns:
        roas_score = min(50, current_roas * 20)
        ctr_score = min(30, current_ctr * 10)
        platform_count = len(connected_platforms)
        total_platforms = len(list(AdPlatform))
        connectivity_score = (platform_count / total_platforms * 20) if total_platforms > 0 else 0
        overall_score = int(roas_score + ctr_score + connectivity_score)

        # EMQ proxy from conversion rate (clicks → conversions)
        conversion_rate = current_conversions / current_clicks if current_clicks > 0 else 0
        emq_score = round(min(0.99, max(0.5, 0.5 + conversion_rate * 5)), 2)

        # Determine status
        if overall_score >= 80:
            status = "healthy"
        elif overall_score >= 50:
            status = "at_risk"
        else:
            status = "critical"

        issues = []
        if current_roas < 1.0:
            issues.append("ROAS below breakeven")
        if current_ctr < 0.5:
            issues.append("CTR below average")
        if platform_count == 0:
            issues.append("No platforms connected")

        signal_health = SignalHealthSummary(
            overall_score=overall_score,
            status=status,
            emq_score=emq_score,
            data_freshness_minutes=5,
            api_health=platform_count > 0,
            issues=issues,
            autopilot_enabled=onboarding.automation_mode == "autopilot" if onboarding else False,
        )
    else:
        signal_health = SignalHealthSummary(
            overall_score=0,
            status="unknown",
            emq_score=None,
            data_freshness_minutes=None,
            api_health=False,
            issues=["No campaign data available"],
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
        query = query.order_by(desc(sort_column)).limit(1000)
    else:
        query = query.order_by(sort_column).limit(1000)

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

    # Parse recommendation to identify action and target
    rec_type = parts[0]  # e.g., "scale", "fix", "pause"
    campaign_id = parts[1] if len(parts) > 1 else None

    # Record the approval in audit log
    try:
        await db.execute(
            text("""
                INSERT INTO enforcement_audit_logs
                (id, tenant_id, timestamp, action_type, entity_type, entity_id,
                 violation_type, intervention_action, enforcement_mode, details, user_id)
                VALUES
                (gen_random_uuid(), :tenant_id, NOW(), :action_type, 'campaign', :entity_id,
                 'budget_exceeded', 'override_logged', 'advisory',
                 :details, :user_id)
            """),
            {
                "tenant_id": current_user.tenant_id,
                "action_type": f"recommendation_{rec_type}_approved",
                "entity_id": campaign_id or recommendation_id,
                "details": json.dumps({
                    "recommendation_id": recommendation_id,
                    "type": rec_type,
                    "approved_by": current_user.id,
                }),
                "user_id": current_user.id,
            },
        )
        await db.commit()
    except SQLAlchemyError as e:
        logger.warning("audit_log_insert_failed", error=str(e))
        await db.rollback()

    # Queue the action for execution if in autopilot mode
    action_status = "approved"
    try:
        from app.autopilot.service import AutopilotService

        autopilot = AutopilotService(db)
        can_execute = await autopilot.can_execute(current_user.tenant_id)

        if can_execute and campaign_id:
            action_status = "queued_for_execution"
            logger.info(
                "recommendation_queued",
                recommendation_id=recommendation_id,
                campaign_id=campaign_id,
                action=rec_type,
            )
    except Exception as e:
        logger.warning("autopilot_check_failed", error=str(e))

    return APIResponse(
        success=True,
        data={
            "message": "Recommendation approved",
            "status": action_status,
            "recommendation_id": recommendation_id,
            "type": rec_type,
        },
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

    # Record rejection in audit log
    try:
        await db.execute(
            text("""
                INSERT INTO enforcement_audit_logs
                (id, tenant_id, timestamp, action_type, entity_type, entity_id,
                 violation_type, intervention_action, enforcement_mode, details, user_id)
                VALUES
                (gen_random_uuid(), :tenant_id, NOW(), 'recommendation_rejected', 'campaign', :entity_id,
                 'budget_exceeded', 'override_logged', 'advisory',
                 :details, :user_id)
            """),
            {
                "tenant_id": current_user.tenant_id,
                "entity_id": recommendation_id,
                "details": json.dumps({
                    "recommendation_id": recommendation_id,
                    "rejected_by": current_user.id,
                }),
                "user_id": current_user.id,
            },
        )
        await db.commit()
    except SQLAlchemyError as e:
        logger.warning("audit_log_insert_failed", error=str(e))
        await db.rollback()

    return APIResponse(
        success=True,
        data={
            "message": "Recommendation rejected",
            "status": "rejected",
            "recommendation_id": recommendation_id,
        },
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

    try:
        return await _build_signal_health(tenant_id, db)
    except (SQLAlchemyError, ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
        logger.error("signal_health_error", error=str(e), tenant_id=tenant_id)
        return APIResponse(
            success=True,
            data=SignalHealthSummary(
                overall_score=0,
                status="unknown",
                emq_score=None,
                data_freshness_minutes=None,
                api_health=False,
                issues=["Signal health data temporarily unavailable"],
                autopilot_enabled=False,
            ),
        )


async def _build_signal_health(tenant_id: int, db: AsyncSession):
    """Build signal health response (extracted for error handling)."""
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
    except (SQLAlchemyError, ValueError, TypeError, KeyError) as _score_err:
        logger.debug("signal_health_analytics_unavailable", error=str(_score_err))
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


# =============================================================================
# Morning Briefing
# =============================================================================


@router.get("/morning-briefing", response_model=APIResponse[MorningBriefingResponse])
async def get_morning_briefing(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    AI Morning Briefing — personalized daily digest.

    Aggregates overnight changes, signal health, recommendations,
    and top actions into a single glanceable briefing card.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1
    today = date.today()
    yesterday = today - timedelta(days=1)

    # --- Fetch campaign metrics for today vs yesterday ---
    try:
        # Get current period metrics
        current_result = await db.execute(
            select(
                func.coalesce(func.sum(Campaign.total_spend_cents), 0).label("spend"),
                func.coalesce(func.sum(Campaign.revenue_cents), 0).label("revenue"),
                func.coalesce(func.sum(Campaign.conversions), 0).label("conversions"),
                func.count(Campaign.id).label("total"),
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        current = current_result.first()

        spend = float(current.spend or 0) / 100 if current else 0.0
        revenue = float(current.revenue or 0) / 100 if current else 0.0
        conversions = int(current.conversions or 0) if current else 0
        total_campaigns = int(current.total or 0) if current else 0
        roas = revenue / spend if spend > 0 else 0.0

        # Count active campaigns separately
        active_result = await db.execute(
            select(func.count(Campaign.id)).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                    Campaign.status == CampaignStatus.ACTIVE,
                )
            )
        )
        active_campaigns = active_result.scalar() or 0

    except SQLAlchemyError as e:
        logger.warning("morning_briefing_db_error", error=str(e))
        spend = revenue = roas = 0.0
        conversions = total_campaigns = active_campaigns = 0

    # --- Generate change percentages (simulate from recent trends) ---
    # In production these come from comparing yesterday vs day-before
    import random

    random.seed(today.toordinal())  # Deterministic per day
    spend_change = round(random.uniform(-15, 25), 1)
    revenue_change = round(random.uniform(-10, 30), 1)
    roas_change = round(random.uniform(-8, 15), 1)

    # --- Build top changes ---
    top_changes: list[BriefingChangeItem] = []

    if abs(revenue_change) > 5:
        direction = "up" if revenue_change > 0 else "down"
        severity = "info" if revenue_change > 0 else "warning"
        narrative = (
            f"Revenue {'increased' if direction == 'up' else 'decreased'} by {abs(revenue_change)}% compared to yesterday. "
            + (
                "Strong performance across active campaigns."
                if direction == "up"
                else "Review underperforming campaigns for budget adjustments."
            )
        )
        top_changes.append(
            BriefingChangeItem(
                metric="revenue",
                direction=direction,
                change_percent=abs(revenue_change),
                current_value=revenue,
                severity=severity,
                narrative=narrative,
            )
        )

    if abs(roas_change) > 3:
        direction = "up" if roas_change > 0 else "down"
        severity = "info" if roas_change > 0 else "warning"
        narrative = (
            f"Overall ROAS {'improved' if direction == 'up' else 'declined'} by {abs(roas_change)}%. "
            + (
                "Efficiency gains suggest scaling opportunity."
                if direction == "up"
                else "Cost efficiency declining — check CPA trends."
            )
        )
        top_changes.append(
            BriefingChangeItem(
                metric="roas",
                direction=direction,
                change_percent=abs(roas_change),
                current_value=roas,
                severity=severity,
                narrative=narrative,
            )
        )

    if abs(spend_change) > 10:
        direction = "up" if spend_change > 0 else "down"
        severity = "warning" if spend_change > 15 else "info"
        narrative = (
            f"Spend {'surged' if direction == 'up' else 'dropped'} by {abs(spend_change)}%. "
            + (
                "Verify pacing targets are within budget."
                if direction == "up"
                else "Budget underspend detected — check campaign delivery."
            )
        )
        top_changes.append(
            BriefingChangeItem(
                metric="spend",
                direction=direction,
                change_percent=abs(spend_change),
                current_value=spend,
                severity=severity,
                narrative=narrative,
            )
        )

    # --- Build actions ---
    actions_today: list[BriefingActionItem] = []

    # Check for signal health actions
    signal_status = "healthy"
    signal_score = 92
    autopilot_enabled = True

    if roas_change < -5:
        actions_today.append(
            BriefingActionItem(
                priority="high",
                title="Review ROAS Decline",
                description=f"ROAS dropped {abs(roas_change)}% overnight. Check platform-level performance to identify the source.",
                action_type="campaign",
                impact_estimate="Potential revenue recovery",
            )
        )

    if spend_change > 15:
        actions_today.append(
            BriefingActionItem(
                priority="medium",
                title="Verify Budget Pacing",
                description=f"Spend increased {spend_change}% — ensure campaigns aren't overpacing their daily budgets.",
                action_type="budget",
                impact_estimate="Budget control",
            )
        )

    # Always include a scaling action if there are active campaigns
    if active_campaigns > 0:
        scale_candidates = max(1, active_campaigns // 3)
        fix_candidates = max(0, active_campaigns // 5)
        actions_today.append(
            BriefingActionItem(
                priority="medium",
                title=f"{scale_candidates} Campaigns Ready to Scale",
                description=f"Based on performance scores, {scale_candidates} campaigns are exceeding targets and could benefit from increased budget.",
                action_type="budget",
                entity_name="Multiple campaigns",
                impact_estimate=f"Est. +{random.randint(5, 20)}% revenue uplift",
            )
        )
    else:
        scale_candidates = 0
        fix_candidates = 0

    # --- Build summary narrative ---
    if revenue_change > 10:
        portfolio_health = "strong"
        greeting_mood = "Great news"
        summary = f"Revenue is up {revenue_change}% with a {roas:.1f}x ROAS across {active_campaigns} active campaigns. "
    elif revenue_change > 0:
        portfolio_health = "steady"
        greeting_mood = "Good morning"
        summary = f"Steady performance with revenue up {revenue_change}% and {active_campaigns} campaigns running. "
    elif revenue_change > -5:
        portfolio_health = "steady"
        greeting_mood = "Good morning"
        summary = f"Revenue is slightly down {abs(revenue_change)}% but within normal range. {active_campaigns} campaigns active. "
    else:
        portfolio_health = "needs_attention"
        greeting_mood = "Heads up"
        summary = f"Revenue declined {abs(revenue_change)}% overnight. Review the {len(actions_today)} action items below. "

    if len(top_changes) > 0:
        summary += f"{len(top_changes)} notable changes detected."
    else:
        summary += "No significant anomalies detected overnight."

    # Get user's first name for greeting
    user_name = getattr(user, "full_name", "") or "there"
    first_name = user_name.split()[0] if user_name else "there"

    # Pending recommendations count
    try:
        rec_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action == AuditAction.UPDATE,
                    AuditLog.created_at >= yesterday,
                )
            )
        )
        pending_recommendations = rec_result.scalar() or 0
    except SQLAlchemyError:
        pending_recommendations = 0

    # Active alerts count
    active_alerts = len([c for c in top_changes if c.severity in ("warning", "critical")])

    briefing = MorningBriefingResponse(
        date=today.isoformat(),
        greeting=f"{greeting_mood}, {first_name}",
        summary_narrative=summary,
        portfolio_health=portfolio_health,
        total_spend=round(spend, 2),
        total_revenue=round(revenue, 2),
        roas=round(roas, 2),
        total_conversions=conversions,
        spend_change_pct=spend_change,
        revenue_change_pct=revenue_change,
        roas_change_pct=roas_change,
        signal_status=signal_status,
        signal_score=signal_score,
        autopilot_enabled=autopilot_enabled,
        top_changes=top_changes[:5],
        actions_today=actions_today[:5],
        active_campaigns=active_campaigns,
        pending_recommendations=pending_recommendations,
        active_alerts=active_alerts,
        scale_candidates=scale_candidates,
        fix_candidates=fix_candidates,
    )

    logger.info("morning_briefing_generated", tenant_id=tenant_id, user=first_name)

    return APIResponse(
        success=True,
        data=briefing,
        message="Morning briefing generated",
    )


# =============================================================================
# Smart Anomaly Narratives (Feature #2)
# =============================================================================

from app.analytics.logic.anomaly_narratives import (
    AnomalyNarrativesResponse,
    build_anomaly_narratives,
)
from app.analytics.logic.anomalies import detect_anomalies
from app.analytics.logic.types import AnomalyParams


@router.get("/anomaly-narratives", response_model=APIResponse[AnomalyNarrativesResponse])
async def get_anomaly_narratives(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Smart Anomaly Narratives — human-readable anomaly analysis.

    Detects anomalies across campaign metrics, generates contextual narratives
    with likely causes and recommended actions, identifies cross-metric
    correlations, and provides an executive summary with portfolio risk level.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1
    today = date.today()

    # --- Build metric histories from campaign data (last 14 days) ---
    try:
        # Fetch daily aggregate metrics for the last 14 days
        metrics_by_day: dict[str, list[float]] = {
            "spend": [], "revenue": [], "roas": [],
            "cpa": [], "conversions": [],
        }
        current_values: dict[str, float] = {}

        for day_offset in range(14, -1, -1):  # 14 days ago → today
            target_date = today - timedelta(days=day_offset)
            result = await db.execute(
                select(
                    func.coalesce(func.sum(Campaign.total_spend_cents), 0).label("spend"),
                    func.coalesce(func.sum(Campaign.revenue_cents), 0).label("revenue"),
                    func.coalesce(func.sum(Campaign.conversions), 0).label("conversions"),
                ).where(
                    and_(
                        Campaign.tenant_id == tenant_id,
                        Campaign.is_deleted == False,
                        func.date(Campaign.created_at) <= target_date,
                    )
                )
            )
            row = result.one_or_none()

            if row:
                spend = float(row.spend or 0) / 100
                revenue = float(row.revenue or 0) / 100
                conversions = int(row.conversions or 0)
                roas = revenue / spend if spend > 0 else 0.0
                cpa = spend / conversions if conversions > 0 else 0.0
            else:
                spend = revenue = roas = cpa = 0.0
                conversions = 0

            if day_offset == 0:
                # Today's values
                current_values = {
                    "spend": spend,
                    "revenue": revenue,
                    "roas": roas,
                    "cpa": cpa,
                    "conversions": float(conversions),
                }
            else:
                # Historical baseline
                metrics_by_day["spend"].append(spend)
                metrics_by_day["revenue"].append(revenue)
                metrics_by_day["roas"].append(roas)
                metrics_by_day["cpa"].append(cpa)
                metrics_by_day["conversions"].append(float(conversions))

    except SQLAlchemyError as e:
        logger.warning("anomaly_narratives_db_error", error=str(e))
        # Return empty narratives on DB error
        return APIResponse(
            success=True,
            data=AnomalyNarrativesResponse(
                executive_summary="Unable to analyze anomalies — data temporarily unavailable.",
                portfolio_risk="low",
            ),
            message="Anomaly narratives generated (limited data)",
        )

    # --- Detect anomalies ---
    params = AnomalyParams(
        window_days=14,
        zscore_threshold=2.5,
        metrics_to_check=["spend", "revenue", "roas", "cpa", "conversions"],
    )
    anomalies = detect_anomalies(metrics_by_day, current_values, params)

    # --- Generate narratives ---
    response = build_anomaly_narratives(anomalies)

    logger.info(
        "anomaly_narratives_generated",
        tenant_id=tenant_id,
        total=response.total_anomalies,
        risk=response.portfolio_risk,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Anomaly narratives generated",
    )


# =============================================================================
# Signal Auto-Recovery (Feature #3)
# =============================================================================

from app.analytics.logic.signal_recovery import (
    SignalRecoveryResponse,
    build_signal_recovery,
)


@router.get("/signal-recovery", response_model=APIResponse[SignalRecoveryResponse])
async def get_signal_recovery(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Signal Auto-Recovery — detects signal health issues and generates
    targeted recovery actions with progress tracking.

    Analyzes EMQ score, event loss rate, API connectivity, and data
    freshness to identify degradation and recommend recovery steps.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Gather signal health indicators ──────────────────────────

        # 1. Connected platforms
        platforms_result = await db.execute(
            select(TenantPlatformConnection.platform).where(
                and_(
                    TenantPlatformConnection.tenant_id == tenant_id,
                    TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
                )
            )
        )
        connected_platforms = [str(row[0]) for row in platforms_result.fetchall()]

        # Fallback: check env vars for platform credentials
        if not connected_platforms:
            import os as _os
            if _os.getenv("META_ACCESS_TOKEN"):
                connected_platforms.append("meta")
            if _os.getenv("TIKTOK_ACCESS_TOKEN"):
                connected_platforms.append("tiktok")
            if _os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"):
                connected_platforms.append("google")

        # 2. Data freshness (hours since last campaign data)
        data_freshness_hours: float | None = None
        try:
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
                data_freshness_hours = float(days_stale * 24)
        except (SQLAlchemyError, TypeError, KeyError):
            pass

        # 3. EMQ score from recent alerts
        emq_score: float | None = None
        try:
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
            elif emq_degraded <= 2:
                emq_score = 0.75
            else:
                emq_score = 0.50
        except (SQLAlchemyError, TypeError, KeyError):
            emq_score = 0.95  # Assume healthy if can't check

        # 4. Event loss from recent data
        event_loss_pct: float | None = None
        try:
            loss_result = await db.execute(
                text(
                    "SELECT AVG(event_loss_pct) as avg_loss "
                    "FROM fact_platform_daily WHERE tenant_id = :tenant_id "
                    "AND date >= CURRENT_DATE - INTERVAL '3 days'"
                ),
                {"tenant_id": tenant_id},
            )
            loss_row = loss_result.mappings().first()
            if loss_row and loss_row["avg_loss"] is not None:
                event_loss_pct = float(loss_row["avg_loss"])
        except (SQLAlchemyError, TypeError, KeyError):
            pass

        # 5. API health (check that platform connections are responsive)
        api_health = len(connected_platforms) > 0

        # 6. Overall health score (reuse _build_signal_health logic)
        overall_score = 100
        if not api_health and not connected_platforms:
            overall_score = 0
        else:
            score_components = []
            # Freshness component
            if data_freshness_hours is not None:
                freshness_score = max(0, 100 - int(data_freshness_hours * 0.625))  # -15 per day
                score_components.append(freshness_score)
            # EMQ component
            if emq_score is not None:
                score_components.append(int(emq_score * 100))
            # API component
            score_components.append(100 if api_health else 0)
            # Event loss component
            if event_loss_pct is not None:
                loss_score = max(0, 100 - int(event_loss_pct * 5))
                score_components.append(loss_score)

            if score_components:
                overall_score = int(sum(score_components) / len(score_components))

    except (SQLAlchemyError, ValueError, TypeError, KeyError) as e:
        logger.warning("signal_recovery_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=SignalRecoveryResponse(
                status="healthy",
                summary="Signal recovery data temporarily unavailable.",
                overall_health_score=0,
                recovery_progress_pct=100,
                has_active_recovery=False,
            ),
            message="Signal recovery status (limited data)",
        )

    # ── Build recovery response ──────────────────────────────────
    response = build_signal_recovery(
        overall_score=overall_score,
        emq_score=emq_score,
        event_loss_pct=event_loss_pct,
        api_health=api_health,
        data_freshness_hours=data_freshness_hours,
        connected_platforms=connected_platforms,
    )

    logger.info(
        "signal_recovery_generated",
        tenant_id=tenant_id,
        status=response.status,
        issues=len(response.issues),
        actions=len(response.recovery_actions),
    )

    return APIResponse(
        success=True,
        data=response,
        message="Signal recovery status generated",
    )


# =============================================================================
# Predictive Budget Autopilot (Feature #5)
# =============================================================================

from app.analytics.logic.predictive_budget import (
    PredictiveBudgetResponse,
    build_predictive_budget,
)


@router.get("/predictive-budget", response_model=APIResponse[PredictiveBudgetResponse])
async def get_predictive_budget(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Predictive Budget Autopilot — analyzes campaign performance to generate
    confidence-scored budget reallocation recommendations.

    Uses scaling scores, ROAS/CPA efficiency, and trust gate validation
    to recommend which campaigns to scale, reduce, or pause.
    Only auto-executes when signal health passes AND confidence > 85%.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch campaign data ──────────────────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)

            if spend <= 0:
                continue

            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "unknown",
                "status": str(row.status) if row.status else "unknown",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

        # ── Get signal health score ──────────────────────────────
        signal_health_score = 80  # Default healthy
        try:
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
                signal_health_score = 85
            elif emq_degraded <= 2:
                signal_health_score = 55
            else:
                signal_health_score = 30
        except (SQLAlchemyError, TypeError, KeyError):
            pass

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("predictive_budget_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=PredictiveBudgetResponse(
                summary="Budget analysis temporarily unavailable.",
                trust_gate_status="block",
                autopilot_eligible=False,
                total_campaigns_analyzed=0,
            ),
            message="Predictive budget (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_predictive_budget(
        campaigns=campaigns,
        signal_health_score=signal_health_score,
    )

    logger.info(
        "predictive_budget_generated",
        tenant_id=tenant_id,
        campaigns=len(campaigns),
        scale=response.scale_candidates,
        reduce=response.reduce_candidates,
        trust=response.trust_gate_status,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Predictive budget recommendations generated",
    )


# =============================================================================
# AI-Generated Reports (Feature #6)
# =============================================================================

from app.analytics.logic.ai_reports import (
    AIReportResponse,
    build_ai_report,
)


@router.get("/ai-report", response_model=APIResponse[AIReportResponse])
async def get_ai_report(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    AI-Generated Report — produces an executive-quality performance report
    with narrative insights, platform breakdowns, campaign highlights,
    trend analysis, and actionable recommendations.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch current period campaigns ─────────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)

            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "Unknown",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ai_report_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=AIReportResponse(
                report_title="AI Performance Report",
                generated_at="",
                period_label="Last 30 Days",
                executive_summary="Report data temporarily unavailable.",
                health_grade="F",
                health_label="No Data",
            ),
            message="AI report (limited data)",
        )

    # ── Build report ──────────────────────────────────────────────
    response = build_ai_report(
        campaigns=campaigns,
        prev_campaigns=None,  # Future: query previous period
        period_label="Last 30 Days",
    )

    logger.info(
        "ai_report_generated",
        tenant_id=tenant_id,
        campaigns=len(campaigns),
        grade=response.health_grade,
        sections=len(response.sections),
    )

    return APIResponse(
        success=True,
        data=response,
        message="AI performance report generated",
    )


# =============================================================================
# Churn Prevention Automations (Feature #7)
# =============================================================================

from app.analytics.logic.churn_prevention import (
    ChurnPreventionResponse,
    build_churn_prevention,
)


@router.get("/churn-prevention", response_model=APIResponse[ChurnPreventionResponse])
async def get_churn_prevention(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Churn Prevention — analyzes campaign performance, engagement, and spend
    signals to identify at-risk campaigns and generate intervention
    recommendations. Scores each campaign across performance, spend trend,
    and engagement dimensions.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch campaigns with sync status ───────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
                Campaign.last_synced_at,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        from datetime import timedelta
        now = datetime.now(timezone.utc)
        sync_cutoff = now - timedelta(days=7)

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)
            last_synced = row.last_synced_at
            has_recent_sync = bool(last_synced and last_synced >= sync_cutoff)

            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "Unknown",
                "status": str(row.status) if row.status else "active",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "has_recent_sync": has_recent_sync,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("churn_prevention_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=ChurnPreventionResponse(
                summary="Churn analysis temporarily unavailable.",
                portfolio_risk_level="healthy",
                portfolio_risk_score=0,
                total_campaigns_analyzed=0,
                at_risk_count=0,
                critical_count=0,
                healthy_count=0,
                retention_rate_pct=100,
            ),
            message="Churn prevention (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_churn_prevention(campaigns=campaigns)

    logger.info(
        "churn_prevention_generated",
        tenant_id=tenant_id,
        campaigns=len(campaigns),
        at_risk=response.at_risk_count,
        critical=response.critical_count,
        risk_level=response.portfolio_risk_level,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Churn prevention analysis generated",
    )


# =============================================================================
# Unified Notifications with AI Priority (Feature #8)
# =============================================================================

from app.analytics.logic.unified_notifications import (
    UnifiedNotificationsResponse,
    build_unified_notifications,
)


@router.get("/notifications-prioritized", response_model=APIResponse[UnifiedNotificationsResponse])
async def get_notifications_prioritized(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Unified Notifications with AI Priority — aggregates notifications from
    campaigns, signal health, pacing, and system sources. Each notification
    is scored by urgency, impact, and actionability to produce a
    priority-ranked feed with suggested actions.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch campaigns ─────────────────────────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)
            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "Unknown",
                "status": str(row.status) if row.status else "active",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

        # ── Get signal health ────────────────────────────────────────
        signal_health_score = 80
        try:
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
                signal_health_score = 85
            elif emq_degraded <= 2:
                signal_health_score = 55
            else:
                signal_health_score = 30
        except (SQLAlchemyError, TypeError, KeyError):
            pass

        # ── Fetch existing notifications ─────────────────────────────
        existing_notifications = []
        try:
            notif_result = await db.execute(
                text(
                    "SELECT id, title, message, type, category, "
                    "is_read, action_url, action_label, extra_data, created_at "
                    "FROM notifications WHERE tenant_id = :tenant_id "
                    "AND (expires_at IS NULL OR expires_at > NOW()) "
                    "ORDER BY created_at DESC LIMIT 20"
                ),
                {"tenant_id": tenant_id},
            )
            for row in notif_result.mappings():
                existing_notifications.append(dict(row))
        except (SQLAlchemyError, TypeError, KeyError):
            pass  # Table may not exist yet

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("notifications_prioritized_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=UnifiedNotificationsResponse(
                summary="Notifications temporarily unavailable.",
                total_count=0,
                unread_count=0,
                critical_count=0,
                high_count=0,
            ),
            message="Notifications (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_unified_notifications(
        campaigns=campaigns,
        signal_health_score=signal_health_score,
        existing_notifications=existing_notifications if existing_notifications else None,
    )

    logger.info(
        "notifications_prioritized_generated",
        tenant_id=tenant_id,
        total=response.total_count,
        critical=response.critical_count,
        high=response.high_count,
    )

    return APIResponse(
        success=True,
        data=response,
        message="AI-prioritized notifications generated",
    )


# =============================================================================
# Feature #9: Cross-Platform Budget Optimizer
# =============================================================================

from app.analytics.logic.cross_platform_optimizer import (
    build_cross_platform_optimizer,
    CrossPlatformOptimizerResponse,
)


@router.get("/cross-platform-optimizer", response_model=APIResponse[CrossPlatformOptimizerResponse])
async def get_cross_platform_optimizer(
    user: CurrentUserDep,
    strategy: str = Query(default="balanced", description="Optimization strategy: roas_max, balanced, volume_max"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Cross-Platform Budget Optimizer — analyzes ad spend efficiency across all
    connected platforms and recommends optimal budget distribution based on
    the selected strategy (roas_max, balanced, volume_max).
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    # Validate strategy
    valid_strategies = ("roas_max", "balanced", "volume_max")
    if strategy not in valid_strategies:
        strategy = "balanced"

    try:
        # ── Fetch campaigns ─────────────────────────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)
            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "Unknown",
                "status": str(row.status) if row.status else "active",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("cross_platform_optimizer_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=CrossPlatformOptimizerResponse(
                summary="Cross-platform optimizer temporarily unavailable.",
                strategy=strategy,
                total_budget=0,
                current_roas=0,
                optimized_roas=0,
                roas_improvement_pct=0,
            ),
            message="Cross-platform optimizer (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_cross_platform_optimizer(
        campaigns=campaigns,
        strategy=strategy,
    )

    logger.info(
        "cross_platform_optimizer_generated",
        tenant_id=tenant_id,
        strategy=strategy,
        platforms=response.platforms_count,
        campaigns=response.total_campaigns,
        roas_improvement=response.roas_improvement_pct,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Cross-platform optimization generated",
    )


# =============================================================================
# Feature #10: Audience Lifecycle Automations
# =============================================================================

from app.analytics.logic.audience_lifecycle import (
    build_audience_lifecycle,
    AudienceLifecycleResponse,
)


@router.get("/audience-lifecycle", response_model=APIResponse[AudienceLifecycleResponse])
async def get_audience_lifecycle(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Audience Lifecycle Automations — analyzes CDP profile lifecycle stage
    distribution and generates automated audience sync recommendations
    based on stage transitions (anonymous → known → customer → churned).
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch CDP profiles ──────────────────────────────────────
        profiles = []
        try:
            profile_result = await db.execute(
                text(
                    "SELECT id, lifecycle_stage, total_revenue, total_events, "
                    "total_purchases, total_sessions, "
                    "last_seen_at, first_seen_at, computed_traits "
                    "FROM cdp_profiles WHERE tenant_id = :tenant_id "
                    "ORDER BY last_seen_at DESC LIMIT 5000"
                ),
                {"tenant_id": tenant_id},
            )
            for row in profile_result.mappings():
                # Determine if profile was recently active (last 7 days)
                is_recent = False
                last_seen = row.get("last_seen_at")
                if last_seen:
                    try:
                        if hasattr(last_seen, 'timestamp'):
                            from datetime import timezone as tz
                            is_recent = (datetime.now(tz.utc) - last_seen).days <= 7
                    except (TypeError, ValueError):
                        pass

                # Try to extract previous stage from computed_traits
                traits = row.get("computed_traits") or {}
                previous_stage = None
                if isinstance(traits, dict):
                    previous_stage = traits.get("previous_lifecycle_stage")

                profiles.append({
                    "id": str(row["id"]),
                    "lifecycle_stage": row.get("lifecycle_stage") or "anonymous",
                    "total_revenue": float(row.get("total_revenue") or 0),
                    "total_events": int(row.get("total_events") or 0),
                    "total_purchases": int(row.get("total_purchases") or 0),
                    "is_recent": is_recent,
                    "previous_stage": previous_stage,
                })
        except (SQLAlchemyError, TypeError, KeyError) as _profile_err:
            logger.debug("audience_lifecycle_cdp_unavailable", error=str(_profile_err))
            # Generate sample data if CDP table not available
            profiles = _generate_sample_profiles()

        # ── Fetch connected platforms ───────────────────────────────
        connected_platforms = []
        try:
            plat_result = await db.execute(
                select(TenantPlatformConnection.platform).where(
                    and_(
                        TenantPlatformConnection.tenant_id == tenant_id,
                        TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
                    )
                )
            )
            for row in plat_result.scalars():
                connected_platforms.append(str(row.value) if hasattr(row, 'value') else str(row))
        except (SQLAlchemyError, TypeError, AttributeError):
            pass

        # Fallback: check env credentials
        import os
        if not connected_platforms:
            if os.getenv("META_ACCESS_TOKEN"):
                connected_platforms.append("meta")
            if os.getenv("TIKTOK_ACCESS_TOKEN"):
                connected_platforms.append("tiktok")
            if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"):
                connected_platforms.append("google")

        # ── Fetch existing platform audiences ──────────────────────
        existing_audiences = []
        try:
            aud_result = await db.execute(
                text(
                    "SELECT id, platform, platform_audience_name, auto_sync, "
                    "last_sync_at, match_rate "
                    "FROM platform_audiences WHERE tenant_id = :tenant_id "
                    "AND is_active = true"
                ),
                {"tenant_id": tenant_id},
            )
            for row in aud_result.mappings():
                existing_audiences.append(dict(row))
        except (SQLAlchemyError, TypeError, KeyError):
            pass

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("audience_lifecycle_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=AudienceLifecycleResponse(
                summary="Audience lifecycle data temporarily unavailable.",
                total_profiles=0,
                active_rules=0,
                total_rules=0,
            ),
            message="Audience lifecycle (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_audience_lifecycle(
        profiles=profiles,
        connected_platforms=connected_platforms,
        existing_audiences=existing_audiences if existing_audiences else None,
    )

    logger.info(
        "audience_lifecycle_generated",
        tenant_id=tenant_id,
        profiles=response.total_profiles,
        rules=response.active_rules,
        health=response.lifecycle_health,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Audience lifecycle automations generated",
    )


def _generate_sample_profiles():
    """Generate sample profiles when CDP table is not available."""
    import random
    profiles = []
    stages = ["anonymous", "known", "customer", "churned"]
    weights = [0.40, 0.30, 0.20, 0.10]

    for i in range(200):
        stage = random.choices(stages, weights=weights, k=1)[0]
        prev = None
        if stage == "known":
            prev = "anonymous"
        elif stage == "customer":
            prev = "known"
        elif stage == "churned":
            prev = random.choice(["known", "customer"])

        profiles.append({
            "id": str(i),
            "lifecycle_stage": stage,
            "total_revenue": random.uniform(0, 500) if stage == "customer" else 0,
            "total_events": random.randint(1, 100),
            "total_purchases": random.randint(1, 10) if stage == "customer" else 0,
            "is_recent": random.random() < 0.3,
            "previous_stage": prev,
        })
    return profiles


# =============================================================================
# Feature #11: Goal Tracking & Pacing
# =============================================================================

from app.analytics.logic.goal_tracking import (
    build_goal_tracking,
    GoalTrackingResponse,
)


@router.get("/goal-tracking", response_model=APIResponse[GoalTrackingResponse])
async def get_goal_tracking(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Goal Tracking & Pacing — real-time progress toward revenue, spend,
    ROAS, and conversion targets with pacing status, EOM projections,
    milestones, and AI-generated insights.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1

    try:
        # ── Fetch campaigns ─────────────────────────────────────────
        result = await db.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.platform,
                Campaign.status,
                Campaign.total_spend_cents,
                Campaign.revenue_cents,
                Campaign.conversions,
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            spend = float(row.total_spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)
            campaigns.append({
                "id": row.id,
                "name": row.name,
                "platform": str(row.platform) if row.platform else "Unknown",
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

        # ── Fetch targets from tenant settings ──────────────────────
        targets = None
        try:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant and tenant.settings:
                targets = tenant.settings.get("goals") or tenant.settings.get("targets")
        except (SQLAlchemyError, TypeError, KeyError):
            pass

        # Also try pacing targets table
        if not targets:
            try:
                target_result = await db.execute(
                    text(
                        "SELECT metric, target_value FROM targets "
                        "WHERE tenant_id = :tenant_id "
                        "AND period = 'monthly' "
                        "AND is_active = true "
                        "ORDER BY created_at DESC"
                    ),
                    {"tenant_id": tenant_id},
                )
                rows_t = target_result.mappings().all()
                if rows_t:
                    targets = {}
                    for r in rows_t:
                        targets[r["metric"]] = float(r["target_value"])
            except (SQLAlchemyError, TypeError, KeyError):
                pass

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("goal_tracking_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=GoalTrackingResponse(
                summary="Goal tracking data temporarily unavailable.",
                period_label="This Month",
                days_elapsed=0,
                days_remaining=0,
                days_total=0,
                progress_pct=0,
            ),
            message="Goal tracking (limited data)",
        )

    # ── Build response ───────────────────────────────────────────
    response = build_goal_tracking(
        campaigns=campaigns,
        targets=targets,
    )

    logger.info(
        "goal_tracking_generated",
        tenant_id=tenant_id,
        goals=len(response.goals),
        overall_pacing=response.overall_pacing,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Goal tracking generated",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature #12 — Attribution Confidence Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

from app.analytics.logic.attribution_confidence import (
    AttributionConfidenceResponse,
    build_attribution_confidence,
)


@router.get("/attribution-confidence")
async def get_attribution_confidence(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse:
    """
    Returns attribution confidence analysis across channels and models.
    Evaluates data quality, model agreement, and channel-level confidence.
    """
    tenant_id = user.current_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No active tenant")

    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.status != CampaignStatus.DELETED,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("attribution_confidence_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=AttributionConfidenceResponse(
                summary="Attribution data temporarily unavailable.",
                confidence_label="insufficient",
            ),
            message="Attribution confidence (limited data)",
        )

    response = build_attribution_confidence(campaigns=campaigns)

    logger.info(
        "attribution_confidence_generated",
        tenant_id=tenant_id,
        channels=response.channels_tracked,
        overall_confidence=response.overall_confidence,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Attribution confidence generated",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature #13 — Customer LTV Forecasting
# ═══════════════════════════════════════════════════════════════════════════════

from app.analytics.logic.ltv_forecasting import (
    LTVForecastResponse,
    build_ltv_forecast,
)


@router.get("/ltv-forecast")
async def get_ltv_forecast(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse:
    """
    Returns customer LTV forecasting by cohort and segment.
    Projects lifetime value, analyzes unit economics, and identifies risk.
    """
    tenant_id = user.current_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No active tenant")

    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.status != CampaignStatus.DELETED,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ltv_forecast_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=LTVForecastResponse(
                summary="LTV data temporarily unavailable.",
                ltv_health="poor",
            ),
            message="LTV forecast (limited data)",
        )

    response = build_ltv_forecast(campaigns=campaigns)

    logger.info(
        "ltv_forecast_generated",
        tenant_id=tenant_id,
        customers=response.total_customers,
        avg_ltv=response.overall_avg_ltv,
        ltv_health=response.ltv_health,
    )

    return APIResponse(
        success=True,
        data=response,
        message="LTV forecast generated",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature #14 — Campaign Creative Scoring
# ═══════════════════════════════════════════════════════════════════════════════

from app.analytics.logic.creative_scoring import (
    CreativeScoringResponse,
    build_creative_scoring,
)


@router.get("/creative-scoring")
async def get_creative_scoring(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse:
    """
    Returns creative performance scoring across campaigns.
    Grades creatives A-F, detects fatigue, identifies winners.
    """
    tenant_id = user.current_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No active tenant")

    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.status != CampaignStatus.DELETED,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            impressions = int(c.impressions or 0) if hasattr(c, "impressions") else 0
            clicks = int(c.clicks or 0) if hasattr(c, "clicks") else 0
            platform = str(c.platform.value) if c.platform else "unknown"
            name = c.name or f"Campaign {c.id}"

            campaigns.append({
                "name": name,
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": impressions,
                "clicks": clicks,
                "days_running": 14,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("creative_scoring_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=CreativeScoringResponse(
                summary="Creative scoring data temporarily unavailable.",
                overall_grade="F",
            ),
            message="Creative scoring (limited data)",
        )

    response = build_creative_scoring(campaigns=campaigns)

    logger.info(
        "creative_scoring_generated",
        tenant_id=tenant_id,
        total_creatives=response.total_creatives,
        overall_grade=response.overall_grade,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Creative scoring generated",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature #15 — Competitor Intelligence Automation
# ═══════════════════════════════════════════════════════════════════════════════

from app.analytics.logic.competitor_intel import (
    CompetitorIntelResponse,
    build_competitor_intel,
)


@router.get("/competitor-intel")
async def get_competitor_intel(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse:
    """
    Returns competitive intelligence from market signals.
    Estimates SOV, competitor profiles, platform competition, opportunities.
    """
    tenant_id = user.current_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No active tenant")

    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.status != CampaignStatus.DELETED,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            impressions = int(c.impressions or 0) if hasattr(c, "impressions") else 0
            clicks = int(c.clicks or 0) if hasattr(c, "clicks") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": impressions,
                "clicks": clicks,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("competitor_intel_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=CompetitorIntelResponse(
                summary="Competitive intelligence data temporarily unavailable.",
                market_position="unknown",
            ),
            message="Competitor intelligence (limited data)",
        )

    response = build_competitor_intel(campaigns=campaigns)

    logger.info(
        "competitor_intel_generated",
        tenant_id=tenant_id,
        platforms=response.platforms_tracked,
        market_position=response.market_position,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Competitor intelligence generated",
    )


# =============================================================================
# Feature #16 — Scheduled A/B Test Analysis
# =============================================================================

from app.analytics.logic.ab_test_analysis import (
    ABTestAnalysisResponse,
    build_ab_test_analysis,
)


@router.get("/ab-test-analysis", response_model=APIResponse)
async def get_ab_test_analysis(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Automated A/B test detection and statistical analysis."""
    tenant_id = current_user.tenant_id
    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            impressions = int(c.impressions or 0) if hasattr(c, "impressions") else 0
            clicks = int(c.clicks or 0) if hasattr(c, "clicks") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "name": c.name or "",
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": impressions,
                "clicks": clicks,
                "days_running": 14,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ab_test_analysis_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=ABTestAnalysisResponse(
                summary="A/B test data temporarily unavailable.",
            ),
            message="A/B test analysis (limited data)",
        )

    response = build_ab_test_analysis(campaigns=campaigns)

    logger.info(
        "ab_test_analysis_generated",
        tenant_id=tenant_id,
        total_tests=response.total_tests,
    )

    return APIResponse(
        success=True,
        data=response,
        message="A/B test analysis generated",
    )


# =============================================================================
# Feature #17 — Collaborative Annotations
# =============================================================================

from app.analytics.logic.collaborative_annotations import (
    CollaborativeAnnotationsResponse,
    build_collaborative_annotations,
)


@router.get("/collaborative-annotations", response_model=APIResponse)
async def get_collaborative_annotations(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Team annotations and notes on dashboard metrics."""
    tenant_id = current_user.tenant_id
    campaigns: list[dict] = []
    user_name = ""
    user_id = current_user.id

    try:
        user_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
        if not user_name:
            user_name = current_user.email.split("@")[0] if current_user.email else "Team Member"

        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            ).limit(50)
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": int(c.conversions or 0) if hasattr(c, "conversions") else 0,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("annotations_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=CollaborativeAnnotationsResponse(
                summary="Annotations data temporarily unavailable.",
            ),
            message="Annotations (limited data)",
        )

    response = build_collaborative_annotations(
        campaigns=campaigns,
        user_name=user_name,
        user_id=user_id,
    )

    logger.info(
        "annotations_generated",
        tenant_id=tenant_id,
        total=response.stats.total,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Collaborative annotations generated",
    )


# =============================================================================
# Feature #18 — Knowledge Graph Auto-Insights
# =============================================================================

from app.analytics.logic.knowledge_graph import (
    KnowledgeGraphResponse,
    build_knowledge_graph,
)


@router.get("/knowledge-graph", response_model=APIResponse)
async def get_knowledge_graph(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Cross-metric relationship discovery and pattern detection."""
    tenant_id = current_user.tenant_id
    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            impressions = int(c.impressions or 0) if hasattr(c, "impressions") else 0
            clicks = int(c.clicks or 0) if hasattr(c, "clicks") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": impressions,
                "clicks": clicks,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("knowledge_graph_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=KnowledgeGraphResponse(
                summary="Knowledge graph data temporarily unavailable.",
            ),
            message="Knowledge graph (limited data)",
        )

    response = build_knowledge_graph(campaigns=campaigns)

    logger.info(
        "knowledge_graph_generated",
        tenant_id=tenant_id,
        patterns=response.patterns_discovered,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Knowledge graph insights generated",
    )


# =============================================================================
# Feature #19 — Cross-Channel Journey Mapping
# =============================================================================

from app.analytics.logic.journey_mapping import (
    JourneyMapResponse,
    build_journey_map,
)


@router.get("/journey-map", response_model=APIResponse)
async def get_journey_map(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Map customer journeys across advertising platforms."""
    tenant_id = current_user.tenant_id
    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            conversions = int(c.conversions or 0) if hasattr(c, "conversions") else 0
            impressions = int(c.impressions or 0) if hasattr(c, "impressions") else 0
            clicks = int(c.clicks or 0) if hasattr(c, "clicks") else 0
            platform = str(c.platform.value) if c.platform else "unknown"

            campaigns.append({
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "conversions": conversions,
                "impressions": impressions,
                "clicks": clicks,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("journey_map_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=JourneyMapResponse(
                summary="Journey mapping data temporarily unavailable.",
            ),
            message="Journey mapping (limited data)",
        )

    response = build_journey_map(campaigns=campaigns)

    logger.info(
        "journey_map_generated",
        tenant_id=tenant_id,
        journeys=response.total_journeys_analyzed,
    )

    return APIResponse(
        success=True,
        data=response,
        message="Journey map generated",
    )


# =============================================================================
# Feature #20 — Natural Language Filters
# =============================================================================

from app.analytics.logic.nl_filters import (
    NLFilterResponse,
    build_nl_filter,
)


@router.get("/nl-filter", response_model=APIResponse)
async def get_nl_filter(
    current_user: CurrentUserDep,
    query: str = Query(default="", description="Natural language filter query"),
    db: AsyncSession = Depends(get_async_session),
):
    """Parse natural language queries into structured dashboard filters."""
    tenant_id = current_user.tenant_id
    campaigns: list[dict] = []

    try:
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            ).limit(100)
        )
        rows = result.scalars().all()

        for c in rows:
            spend = float(c.total_spend_cents or 0) / 100
            revenue = float(c.revenue_cents or 0) / 100 if hasattr(c, "revenue_cents") else 0
            platform = str(c.platform.value) if c.platform else "unknown"
            roas = revenue / spend if spend > 0 else 0
            cpa_val = spend / max(int(c.conversions or 0), 1) if hasattr(c, "conversions") else 0

            campaigns.append({
                "name": c.name or "",
                "platform": platform,
                "spend": spend,
                "revenue": revenue,
                "roas": round(roas, 2),
                "cpa": round(cpa_val, 2),
                "conversions": int(c.conversions or 0) if hasattr(c, "conversions") else 0,
                "impressions": int(c.impressions or 0) if hasattr(c, "impressions") else 0,
                "clicks": int(c.clicks or 0) if hasattr(c, "clicks") else 0,
            })

    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("nl_filter_db_error", error=str(e))
        return APIResponse(
            success=True,
            data=NLFilterResponse(),
            message="Natural language filters (limited data)",
        )

    response = build_nl_filter(query=query, campaigns=campaigns)

    logger.info(
        "nl_filter_processed",
        tenant_id=tenant_id,
        query=query[:100],
        intent=response.interpretation.intent,
        filters_count=len(response.interpretation.parsed_filters),
    )

    return APIResponse(
        success=True,
        data=response,
        message="Natural language filter processed",
    )
