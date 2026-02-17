# =============================================================================
# Stratum AI - Analytics AI Endpoints
# =============================================================================
"""
API endpoints for AI-powered analytics.
Provides recommendations, scoring, and insights based on the Analytics Design System.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CreativeAsset
from app.schemas import APIResponse

from app.analytics.logic.types import (
    EntityMetrics,
    BaselineMetrics,
    EntityLevel,
    Platform,
    ScoringParams,
    FatigueParams,
    AnomalyParams,
    SignalHealthParams,
)
from app.analytics.logic.scoring import scaling_score, batch_scaling_scores
from app.analytics.logic.fatigue import creative_fatigue, batch_creative_fatigue
from app.analytics.logic.anomalies import detect_anomalies
from app.analytics.logic.signal_health import signal_health, auto_resolve
from app.analytics.logic.attribution import attribution_variance, get_attribution_health
from app.analytics.logic.budget import reallocate_budget, summarize_reallocation
from app.analytics.logic.recommend import generate_recommendations, RecommendationsEngine

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================
class ScalingScoreRequest(BaseModel):
    entity_id: str
    entity_name: str
    platform: str = "meta"

    # Today's metrics
    spend: float
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    ctr: float = 0
    cvr: float = 0
    cpa: float = 0
    roas: float = 0
    frequency: Optional[float] = None
    emq_score: Optional[float] = None

    # Baseline metrics (last 7 days average)
    baseline_spend: float
    baseline_impressions: int
    baseline_clicks: int
    baseline_conversions: int
    baseline_revenue: float
    baseline_ctr: float = 0
    baseline_cvr: float = 0
    baseline_cpa: float = 0
    baseline_roas: float = 0


class FatigueScoreRequest(BaseModel):
    creative_id: str
    creative_name: str

    # Today's metrics
    ctr: float
    roas: float
    cpa: float
    frequency: Optional[float] = None

    # Baseline metrics
    baseline_ctr: float
    baseline_roas: float
    baseline_cpa: float


class AnomalyDetectionRequest(BaseModel):
    metrics_history: dict[str, List[float]]
    current_values: dict[str, float]


class SignalHealthRequest(BaseModel):
    emq_score: Optional[float] = None
    event_loss_pct: Optional[float] = None
    api_health: bool = True


# =============================================================================
# Endpoints
# =============================================================================
@router.post("/scoring/scale", response_model=APIResponse)
async def calculate_scaling_score(
    request: ScalingScoreRequest,
):
    """
    Calculate scaling score for a single entity.

    Returns a score from -1 to +1:
    - >= +0.25: scale candidate
    - -0.25 to +0.25: stable/watch
    - <= -0.25: fix or pause candidate
    """
    # Build EntityMetrics
    today = EntityMetrics(
        entity_id=request.entity_id,
        entity_name=request.entity_name,
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform(request.platform),
        date=datetime.now(timezone.utc),
        spend=request.spend,
        impressions=request.impressions,
        clicks=request.clicks,
        conversions=request.conversions,
        revenue=request.revenue,
        ctr=request.ctr or (request.clicks / max(request.impressions, 1) * 100),
        cvr=request.cvr or (request.conversions / max(request.clicks, 1) * 100),
        cpa=request.cpa or (request.spend / max(request.conversions, 1)),
        roas=request.roas or (request.revenue / max(request.spend, 1)),
        frequency=request.frequency,
        emq_score=request.emq_score,
    )

    # Build BaselineMetrics
    baseline = BaselineMetrics(
        spend=request.baseline_spend,
        impressions=request.baseline_impressions,
        clicks=request.baseline_clicks,
        conversions=request.baseline_conversions,
        revenue=request.baseline_revenue,
        ctr=request.baseline_ctr,
        cvr=request.baseline_cvr,
        cpa=request.baseline_cpa,
        roas=request.baseline_roas,
    )

    # Calculate score
    result = scaling_score(today, baseline)

    return APIResponse(
        success=True,
        data=result.dict(),
    )


@router.post("/scoring/fatigue", response_model=APIResponse)
async def calculate_fatigue_score(
    request: FatigueScoreRequest,
):
    """
    Calculate creative fatigue score.

    Returns a score from 0 to 1:
    - >= 0.65: refresh creative (new hook/visual)
    - 0.45 to 0.65: watch, rotate variants
    - < 0.45: healthy
    """
    # Build EntityMetrics for creative
    today = EntityMetrics(
        entity_id=request.creative_id,
        entity_name=request.creative_name,
        entity_level=EntityLevel.CREATIVE,
        platform=Platform.META,
        date=datetime.now(timezone.utc),
        ctr=request.ctr,
        roas=request.roas,
        cpa=request.cpa,
        frequency=request.frequency,
    )

    # Build BaselineMetrics
    baseline = BaselineMetrics(
        ctr=request.baseline_ctr,
        roas=request.baseline_roas,
        cpa=request.baseline_cpa,
    )

    # Calculate fatigue
    result = creative_fatigue(today, baseline)

    return APIResponse(
        success=True,
        data=result.dict(),
    )


@router.post("/anomalies/detect", response_model=APIResponse)
async def detect_metric_anomalies(
    request: AnomalyDetectionRequest,
):
    """
    Detect anomalies in metrics using Z-score analysis.

    Returns anomalies with Z-scores >= 2.5 (configurable).
    """
    anomalies = detect_anomalies(
        request.metrics_history,
        request.current_values,
    )

    return APIResponse(
        success=True,
        data={
            "anomalies": [a.dict() for a in anomalies],
            "anomaly_count": len([a for a in anomalies if a.is_anomaly]),
            "has_critical": any(a.severity.value == "critical" for a in anomalies),
        },
    )


@router.post("/health/signal", response_model=APIResponse)
async def check_signal_health(
    request: SignalHealthRequest,
):
    """
    Check EMQ/signal health status.

    Returns:
    - healthy: All signals good
    - risk: Some signals below target
    - degraded: Significant data quality issues
    - critical: API down or severe issues
    """
    result = signal_health(
        request.emq_score,
        request.event_loss_pct,
        request.api_health,
    )

    # Get auto-resolve actions
    resolve_result = auto_resolve(result)

    return APIResponse(
        success=True,
        data={
            "health": result.dict(),
            "auto_resolve": resolve_result,
        },
    )


@router.get("/recommendations", response_model=APIResponse)
async def get_ai_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
):
    """
    Get AI-powered recommendations for the tenant's campaigns.

    Returns:
    - Recommendations (prioritized actions)
    - Budget actions (reallocation suggestions)
    - Alerts (anomalies and issues)
    - Insights (opportunities)
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get campaigns
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaigns = result.scalars().all()

    if not campaigns:
        return APIResponse(
            success=True,
            data={
                "recommendations": [],
                "actions": [],
                "alerts": [],
                "insights": [],
                "message": "No campaigns found",
            },
        )

    # Build entity metrics from campaigns
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

        # Use same values for baseline (in real scenario, fetch historical data)
        baselines[str(c.id)] = BaselineMetrics(
            spend=spend * 0.9,  # Simulate 10% higher spend vs baseline
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
    recommendations = engine.generate_recommendations(
        entities_today=entities_today,
        baselines=baselines,
        current_spends=current_spends,
        api_health=True,
    )

    return APIResponse(
        success=True,
        data=recommendations,
    )


@router.get("/kpis", response_model=APIResponse)
async def get_analytics_kpis(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get analytics KPIs summary for the dashboard.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get campaigns
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaigns = result.scalars().all()

    if not campaigns:
        return APIResponse(
            success=True,
            data={
                "total_spend": 0,
                "total_revenue": 0,
                "portfolio_roas": 0,
                "campaign_count": 0,
            },
        )

    # Calculate KPIs
    total_spend = sum(c.total_spend_cents / 100 if c.total_spend_cents else 0 for c in campaigns)
    total_revenue = sum(c.revenue_cents / 100 if c.revenue_cents else 0 for c in campaigns)
    total_impressions = sum(c.impressions or 0 for c in campaigns)
    total_clicks = sum(c.clicks or 0 for c in campaigns)
    total_conversions = sum(c.conversions or 0 for c in campaigns)

    portfolio_roas = total_revenue / total_spend if total_spend > 0 else 0
    avg_ctr = sum(c.ctr or 0 for c in campaigns) / len(campaigns) if campaigns else 0
    avg_cpa = total_spend / total_conversions if total_conversions > 0 else 0

    return APIResponse(
        success=True,
        data={
            "total_spend": round(total_spend, 2),
            "total_revenue": round(total_revenue, 2),
            "portfolio_roas": round(portfolio_roas, 2),
            "campaign_count": len(campaigns),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "avg_ctr": round(avg_ctr, 2),
            "avg_cpa": round(avg_cpa, 2),
        },
    )
