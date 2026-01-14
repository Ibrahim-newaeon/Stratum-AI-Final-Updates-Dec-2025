# =============================================================================
# Stratum AI - Live Predictions API
# =============================================================================
"""
API endpoints for live predictions, ROAS optimization, and alerts.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.ml.roas_optimizer import ROASOptimizer
from app.models import Campaign, MLPrediction
from app.schemas import APIResponse
from app.workers.tasks import run_live_predictions

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Confidence Calculation
# =============================================================================
def _calculate_prediction_confidence(
    campaign_data: list,
    analysis: dict,
) -> float:
    """
    Calculate model-derived confidence score based on data quality.

    Factors considered:
    - Number of campaigns (more data = higher confidence)
    - Data completeness (campaigns with ROAS, spend, revenue)
    - Variance in campaign performance (lower variance = higher confidence)

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not campaign_data:
        return 0.0

    # Base confidence from sample size (more campaigns = more reliable)
    # 1 campaign = 0.3, 5 campaigns = 0.5, 10+ campaigns = 0.6
    n_campaigns = len(campaign_data)
    sample_confidence = min(0.6, 0.3 + (n_campaigns / 20))

    # Data completeness score
    complete_count = sum(
        1 for c in campaign_data
        if c.get("spend", 0) > 0 and c.get("revenue", 0) > 0 and c.get("roas", 0) > 0
    )
    completeness_ratio = complete_count / n_campaigns if n_campaigns > 0 else 0
    completeness_confidence = completeness_ratio * 0.2

    # Variance penalty - high variance in ROAS indicates less predictable outcomes
    roas_values = [c.get("roas", 0) for c in campaign_data if c.get("roas", 0) > 0]
    if len(roas_values) >= 2:
        mean_roas = sum(roas_values) / len(roas_values)
        variance = sum((r - mean_roas) ** 2 for r in roas_values) / len(roas_values)
        # Normalize variance penalty (high variance = lower confidence)
        variance_penalty = min(0.2, variance / 10)
        variance_confidence = 0.2 - variance_penalty
    else:
        variance_confidence = 0.1  # Low confidence if not enough data points

    # Total confidence (capped at 0.95 - never claim 100% confidence)
    total_confidence = min(0.95, sample_confidence + completeness_confidence + variance_confidence)

    return round(total_confidence, 2)


# =============================================================================
# Schemas
# =============================================================================
class CampaignAnalysis(BaseModel):
    campaign_id: int
    campaign_name: str
    platform: str
    health_score: float
    status: str
    current_roas: float
    optimal_budget: Optional[dict]
    recommendations: List[dict]


class PortfolioAnalysis(BaseModel):
    total_spend: float
    total_revenue: float
    portfolio_roas: float
    campaign_count: int
    avg_health_score: float
    potential_uplift: dict
    budget_reallocation: List[dict]


class PredictionAlert(BaseModel):
    campaign_id: int
    campaign_name: str
    type: str
    severity: str
    message: str
    recommendation: str


class LivePredictionResponse(BaseModel):
    portfolio: PortfolioAnalysis
    campaigns: List[CampaignAnalysis]
    alerts: List[PredictionAlert]
    generated_at: str


# =============================================================================
# Endpoints
# =============================================================================
@router.get("/live", response_model=APIResponse)
async def get_live_predictions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    refresh: bool = Query(False, description="Force refresh predictions"),
):
    """
    Get live predictions for the tenant's campaigns.

    Returns:
    - Portfolio-level analysis with ROAS and potential uplift
    - Per-campaign health scores and recommendations
    - Active alerts for underperforming campaigns
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Check for cached predictions (less than 30 mins old)
    if not refresh:
        result = await db.execute(
            select(MLPrediction)
            .where(
                MLPrediction.tenant_id == tenant_id,
                MLPrediction.prediction_type == "portfolio_analysis",
                MLPrediction.created_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
            )
            .order_by(desc(MLPrediction.created_at))
            .limit(1)
        )
        cached = result.scalar_one_or_none()

        if cached:
            return APIResponse(
                success=True,
                data={
                    "prediction": cached.prediction_result,
                    "cached": True,
                    "generated_at": cached.created_at.isoformat(),
                },
            )

    # Generate fresh predictions
    campaigns_result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaigns = campaigns_result.scalars().all()

    if not campaigns:
        return APIResponse(
            success=True,
            data={
                "prediction": None,
                "message": "No campaigns found",
            },
        )

    # Convert to dict format
    campaign_data = []
    for c in campaigns:
        campaign_data.append({
            "id": c.id,
            "name": c.name,
            "platform": c.platform.value if c.platform else "meta",
            "spend": c.total_spend_cents / 100 if c.total_spend_cents else 0,
            "revenue": c.revenue_cents / 100 if c.revenue_cents else 0,
            "roas": c.roas or 0,
            "impressions": c.impressions or 0,
            "clicks": c.clicks or 0,
            "conversions": c.conversions or 0,
            "ctr": c.ctr or 0,
            "daily_budget": c.daily_budget_cents / 100 if c.daily_budget_cents else 0,
        })

    # Run analysis
    optimizer = ROASOptimizer()
    analysis = await optimizer.analyze_portfolio(campaign_data)

    # Generate alerts
    alerts = []
    for camp in analysis.get("campaign_analyses", []):
        if camp["health_score"] < 40:
            alerts.append({
                "campaign_id": camp["campaign_id"],
                "campaign_name": camp["campaign_name"],
                "type": "low_health",
                "severity": "critical" if camp["health_score"] < 20 else "high",
                "message": f"Campaign health score is {camp['health_score']}%",
                "recommendation": "Review recommendations and take action",
            })

    # Store prediction
    prediction_record = MLPrediction(
        tenant_id=tenant_id,
        prediction_type="portfolio_analysis",
        input_data={"campaign_count": len(campaigns)},
        prediction_result=analysis,
        confidence_score=_calculate_prediction_confidence(campaign_data, analysis),
        model_version="roas_optimizer_v1.0",
    )
    db.add(prediction_record)
    await db.commit()

    return APIResponse(
        success=True,
        data={
            "prediction": analysis,
            "alerts": alerts,
            "cached": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/campaign/{campaign_id}", response_model=APIResponse)
async def get_campaign_prediction(
    campaign_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed predictions and recommendations for a specific campaign.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get campaign
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Prepare campaign data
    campaign_data = {
        "id": campaign.id,
        "name": campaign.name,
        "platform": campaign.platform.value if campaign.platform else "meta",
        "spend": campaign.total_spend_cents / 100 if campaign.total_spend_cents else 0,
        "revenue": campaign.revenue_cents / 100 if campaign.revenue_cents else 0,
        "roas": campaign.roas or 0,
        "impressions": campaign.impressions or 0,
        "clicks": campaign.clicks or 0,
        "conversions": campaign.conversions or 0,
        "ctr": campaign.ctr or 0,
        "daily_budget": campaign.daily_budget_cents / 100 if campaign.daily_budget_cents else 0,
    }

    # Run analysis
    optimizer = ROASOptimizer()
    analysis = await optimizer.analyze_campaign(campaign_data)

    return APIResponse(
        success=True,
        data=analysis,
    )


@router.get("/alerts", response_model=APIResponse)
async def get_prediction_alerts(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    limit: int = Query(50, le=100),
):
    """
    Get prediction-based alerts for campaigns.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get recent alerts from predictions
    result = await db.execute(
        select(MLPrediction)
        .where(
            MLPrediction.tenant_id == tenant_id,
            MLPrediction.prediction_type == "roas_alerts",
        )
        .order_by(desc(MLPrediction.created_at))
        .limit(1)
    )
    alert_record = result.scalar_one_or_none()

    if not alert_record:
        # Generate alerts on-demand
        campaigns_result = await db.execute(
            select(Campaign).where(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        )
        campaigns = campaigns_result.scalars().all()

        alerts = []
        for campaign in campaigns:
            # Check for ROAS below threshold
            if campaign.roas and campaign.roas < 1.0:
                alerts.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "type": "low_roas",
                    "severity": "critical" if campaign.roas < 0.5 else "high",
                    "message": f"ROAS is {campaign.roas:.2f}x - below break-even",
                    "recommendation": "Consider pausing or reducing budget",
                })

            # Check for high ROAS - scaling opportunity
            if campaign.roas and campaign.roas > 3.0:
                alerts.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "type": "scaling_opportunity",
                    "severity": "info",
                    "message": f"ROAS is {campaign.roas:.2f}x - excellent performance",
                    "recommendation": "Consider increasing budget by 20-30%",
                })

        alert_data = {"alerts": alerts, "generated_at": datetime.now(timezone.utc).isoformat()}
    else:
        alert_data = alert_record.prediction_result
        alert_data["generated_at"] = alert_record.created_at.isoformat()

    # Filter by severity if specified
    if severity and "alerts" in alert_data:
        alert_data["alerts"] = [
            a for a in alert_data["alerts"]
            if a.get("severity") == severity
        ]

    return APIResponse(
        success=True,
        data=alert_data,
    )


@router.post("/refresh", response_model=APIResponse)
async def trigger_prediction_refresh(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger a refresh of live predictions for the tenant.
    Queues a background task.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Queue prediction task
    task = run_live_predictions.delay(tenant_id)

    return APIResponse(
        success=True,
        data={
            "message": "Prediction refresh queued",
            "task_id": task.id,
        },
    )


@router.get("/optimize/budget", response_model=APIResponse)
async def get_budget_optimization(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get budget optimization recommendations across all campaigns.
    Returns suggested budget reallocation for maximum ROAS.
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
            data={"message": "No campaigns to optimize"},
        )

    # Prepare data
    campaign_data = []
    for c in campaigns:
        campaign_data.append({
            "id": c.id,
            "name": c.name,
            "platform": c.platform.value if c.platform else "meta",
            "spend": c.total_spend_cents / 100 if c.total_spend_cents else 0,
            "revenue": c.revenue_cents / 100 if c.revenue_cents else 0,
            "roas": c.roas or 0,
        })

    # Run analysis
    optimizer = ROASOptimizer()
    analysis = await optimizer.analyze_portfolio(campaign_data)

    return APIResponse(
        success=True,
        data={
            "budget_reallocation": analysis.get("budget_reallocation", []),
            "potential_uplift": analysis.get("potential_uplift", {}),
            "top_performers": analysis.get("top_performers", []),
            "bottom_performers": analysis.get("bottom_performers", []),
        },
    )


@router.get("/scenarios/{campaign_id}", response_model=APIResponse)
async def get_budget_scenarios(
    campaign_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get budget change scenarios for a campaign.
    Shows predicted ROAS and revenue at different budget levels.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get campaign
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Prepare data
    campaign_data = {
        "id": campaign.id,
        "name": campaign.name,
        "spend": campaign.total_spend_cents / 100 if campaign.total_spend_cents else 0,
        "revenue": campaign.revenue_cents / 100 if campaign.revenue_cents else 0,
        "roas": campaign.roas or 0,
    }

    # Run analysis
    optimizer = ROASOptimizer()
    analysis = await optimizer.analyze_campaign(campaign_data)

    return APIResponse(
        success=True,
        data={
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "current_metrics": analysis.get("current_metrics"),
            "optimal_budget": analysis.get("optimal_budget"),
            "budget_scenarios": analysis.get("budget_scenarios", []),
        },
    )
