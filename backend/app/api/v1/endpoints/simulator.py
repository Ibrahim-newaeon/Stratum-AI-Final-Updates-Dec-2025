# =============================================================================
# Stratum AI - ML Simulator Endpoints
# =============================================================================
"""
What-If Simulator and ML prediction endpoints.
Implements Module A: Intelligence Engine.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign
from app.schemas import (
    APIResponse,
    ConversionPredictionRequest,
    ConversionPredictionResponse,
    ROASForecastRequest,
    ROASForecastResponse,
    SimulationRequest,
    SimulationResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=APIResponse[SimulationResponse])
async def simulate_budget_change(
    request: Request,
    simulation: SimulationRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    What-If Simulator: Predict outcomes based on budget changes.

    Uses the hybrid ML strategy:
    - ML_PROVIDER=local: Uses scikit-learn models
    - ML_PROVIDER=vertex: Uses Google Vertex AI
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Get campaign data if specified
    campaign_data = None
    if simulation.campaign_id:
        result = await db.execute(
            select(Campaign).where(
                Campaign.id == simulation.campaign_id,
                Campaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        campaign_data = {
            "current_spend": campaign.total_spend_cents / 100,
            "impressions": campaign.impressions,
            "clicks": campaign.clicks,
            "conversions": campaign.conversions,
            "revenue": campaign.revenue_cents / 100,
            "ctr": campaign.ctr,
            "roas": campaign.roas,
        }
    else:
        # Use aggregated tenant data for portfolio simulation
        result = await db.execute(
            select(Campaign).where(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        )
        campaigns = result.scalars().all()

        total_spend = sum(c.total_spend_cents for c in campaigns) / 100
        total_revenue = sum(c.revenue_cents for c in campaigns) / 100
        total_impressions = sum(c.impressions for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        total_conversions = sum(c.conversions for c in campaigns)

        campaign_data = {
            "current_spend": total_spend,
            "impressions": total_impressions,
            "clicks": total_clicks,
            "conversions": total_conversions,
            "revenue": total_revenue,
            "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
            "roas": (total_revenue / total_spend) if total_spend > 0 else 0,
        }

    # Run prediction using the ML service
    from app.ml.simulator import WhatIfSimulator

    simulator = WhatIfSimulator()

    prediction = await simulator.predict_budget_impact(
        current_metrics=campaign_data,
        budget_change_percent=simulation.budget_change_percent,
        days_ahead=simulation.days_ahead,
        include_confidence=simulation.include_confidence_interval,
    )

    return APIResponse(
        success=True,
        data=SimulationResponse(
            campaign_id=simulation.campaign_id,
            current_metrics=campaign_data,
            predicted_metrics=prediction["predicted_metrics"],
            budget_change_percent=simulation.budget_change_percent,
            confidence_interval=prediction.get("confidence_interval"),
            feature_importances=prediction.get("feature_importances"),
            model_version=prediction["model_version"],
        ),
    )


@router.post("/forecast/roas", response_model=APIResponse[ROASForecastResponse])
async def forecast_roas(
    request: Request,
    forecast_request: ROASForecastRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    ROAS Forecasting: Predict future ROAS trends.

    Uses historical data to forecast ROAS for the specified period.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Get campaigns to forecast
    query = select(Campaign).where(
        Campaign.tenant_id == tenant_id,
        Campaign.is_deleted == False,
    )

    if forecast_request.campaign_ids:
        query = query.where(Campaign.id.in_(forecast_request.campaign_ids))

    result = await db.execute(query)
    campaigns = result.scalars().all()

    if not campaigns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No campaigns found",
        )

    # Get historical metrics for forecasting
    from app.ml.forecaster import ROASForecaster

    forecaster = ROASForecaster()

    forecasts = await forecaster.forecast(
        campaigns=campaigns,
        days_ahead=forecast_request.days_ahead,
        granularity=forecast_request.granularity,
        tenant_id=tenant_id,
        db=db,
    )

    return APIResponse(
        success=True,
        data=ROASForecastResponse(
            forecasts=forecasts["predictions"],
            model_version=forecasts["model_version"],
            generated_at=datetime.now(timezone.utc),
        ),
    )


@router.post("/predict/conversions", response_model=APIResponse[ConversionPredictionResponse])
async def predict_conversions(
    request: Request,
    prediction_request: ConversionPredictionRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Conversion Prediction: Predict expected conversions based on features.

    Can be used to estimate conversions for different targeting scenarios.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Verify campaign exists
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == prediction_request.campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    from app.ml.conversion_predictor import ConversionPredictor

    predictor = ConversionPredictor()

    # Merge campaign features with custom features
    features = {
        "impressions": campaign.impressions,
        "clicks": campaign.clicks,
        "spend": campaign.total_spend_cents / 100,
        "ctr": campaign.ctr or 0,
        "platform": campaign.platform.value,
        **prediction_request.features,
    }

    prediction = await predictor.predict(features)

    return APIResponse(
        success=True,
        data=ConversionPredictionResponse(
            campaign_id=prediction_request.campaign_id,
            predicted_conversions=prediction["value"],
            predicted_conversion_rate=prediction["conversion_rate"],
            confidence=prediction["confidence"],
            factors=prediction["contributing_factors"],
        ),
    )


@router.get("/models/status")
async def get_model_status():
    """
    Get status of ML models.

    Returns information about loaded models and their versions.
    """
    from app.ml.inference import ModelRegistry

    registry = ModelRegistry()

    return APIResponse(
        success=True,
        data={
            "ml_provider": settings.ml_provider,
            "models": registry.get_model_info(),
            "is_healthy": registry.health_check(),
        },
    )
