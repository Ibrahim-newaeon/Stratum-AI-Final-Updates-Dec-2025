# =============================================================================
# Stratum AI - Attribution API Endpoints
# =============================================================================
"""
Multi-Touch Attribution (MTA) API endpoints.

Provides attribution calculations, journey analysis, and conversion path insights.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.deps import get_current_user, get_db, get_tenant_id
from app.core.logging import get_logger
from app.models import User, AttributionModel
from app.services.attribution import (
    AttributionService,
    AttributionCalculator,
    JourneyService,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/attribution", tags=["attribution"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class AttributeDealRequest(BaseModel):
    """Request to attribute a single deal."""
    deal_id: UUID
    model: AttributionModel = AttributionModel.LAST_TOUCH
    half_life_days: float = Field(default=7.0, ge=1, le=90)


class BatchAttributeRequest(BaseModel):
    """Request to batch attribute deals."""
    model: AttributionModel = AttributionModel.LAST_TOUCH
    deal_ids: Optional[List[UUID]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AttributionResponse(BaseModel):
    """Attribution calculation response."""
    success: bool
    deal_id: Optional[str] = None
    model: Optional[str] = None
    touchpoint_count: Optional[int] = None
    total_revenue: Optional[float] = None
    confidence: Optional[float] = None
    breakdown: Optional[List[dict]] = None
    error: Optional[str] = None


class BatchAttributionResponse(BaseModel):
    """Batch attribution response."""
    total: int
    attributed: int
    failed: int
    errors: List[dict]


class ModelComparisonResponse(BaseModel):
    """Attribution model comparison response."""
    start_date: str
    end_date: str
    deals_analyzed: int
    total_revenue: float
    models: dict


class JourneyResponse(BaseModel):
    """Contact journey response."""
    success: bool
    contact_id: Optional[str] = None
    path: Optional[str] = None
    touch_count: Optional[int] = None
    timeline: Optional[List[dict]] = None
    deals: Optional[List[dict]] = None
    metrics: Optional[dict] = None
    error: Optional[str] = None


class ConversionPathResponse(BaseModel):
    """Top conversion paths response."""
    path: str
    conversions: int
    total_revenue: float
    avg_revenue: float
    avg_touches: float
    avg_time_to_conversion_hours: Optional[float]
    avg_unique_channels: float


class ChannelTransitionsResponse(BaseModel):
    """Channel transitions (Sankey) response."""
    nodes: List[dict]
    links: List[dict]
    total_transitions: int
    unique_paths: int


class AssistedConversionsResponse(BaseModel):
    """Assisted conversions response."""
    key: str
    name: str
    last_touch_conversions: int
    last_touch_revenue: float
    assisted_conversions: int
    assisted_revenue: float
    total_conversions: int
    total_revenue: float
    total_touches: int
    assist_ratio: float


# =============================================================================
# Attribution Endpoints
# =============================================================================

@router.post("/deals/attribute", response_model=AttributionResponse)
async def attribute_deal(
    request: AttributeDealRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate attribution for a single deal.

    Applies the specified attribution model and returns the full breakdown
    of credit assigned to each touchpoint.
    """
    service = AttributionService(db, tenant_id)
    result = await service.attribute_deal(
        deal_id=request.deal_id,
        model=request.model,
        half_life_days=request.half_life_days,
    )

    return AttributionResponse(**result)


@router.post("/deals/batch-attribute", response_model=BatchAttributionResponse)
async def batch_attribute_deals(
    request: BatchAttributeRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Batch attribute multiple deals.

    If deal_ids not provided, attributes all unattributed won deals in the date range.
    """
    service = AttributionService(db, tenant_id)
    result = await service.batch_attribute_deals(
        model=request.model,
        deal_ids=request.deal_ids,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    return BatchAttributionResponse(**result)


@router.get("/models/compare", response_model=ModelComparisonResponse)
async def compare_attribution_models(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    models: Optional[str] = Query(
        None,
        description="Comma-separated list of models to compare (first_touch,last_touch,linear,position_based,time_decay)"
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Compare attribution results across different models.

    Shows how attributed revenue differs by campaign/platform
    when using different attribution models.
    """
    # Parse models
    model_list = None
    if models:
        model_list = [
            AttributionModel(m.strip())
            for m in models.split(",")
            if m.strip() in [e.value for e in AttributionModel]
        ]

    service = AttributionService(db, tenant_id)
    result = await service.compare_attribution_models(
        start_date=start_date,
        end_date=end_date,
        models=model_list,
    )

    return ModelComparisonResponse(**result)


@router.get("/summary")
async def get_attribution_summary(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    model: AttributionModel = Query(AttributionModel.LAST_TOUCH, description="Attribution model"),
    group_by: str = Query("platform", description="Grouping: platform, campaign, adset, day"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get attribution summary grouped by dimension.

    Returns attributed revenue and deal count by platform, campaign, etc.
    """
    service = AttributionService(db, tenant_id)
    result = await service.get_attribution_summary(
        start_date=start_date,
        end_date=end_date,
        model=model,
        group_by=group_by,
    )

    return {"data": result}


@router.get("/campaigns/{campaign_id}")
async def get_campaign_attribution(
    campaign_id: str,
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    model: AttributionModel = Query(AttributionModel.LAST_TOUCH, description="Attribution model"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get attribution details for a specific campaign.
    """
    service = AttributionService(db, tenant_id)
    result = await service.get_campaign_attribution(
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
        model=model,
    )

    return {"data": result}


# =============================================================================
# Journey Endpoints
# =============================================================================

@router.get("/journeys/contact/{contact_id}", response_model=JourneyResponse)
async def get_contact_journey(
    contact_id: UUID,
    include_deals: bool = Query(True, description="Include deal information"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete journey for a single contact.

    Returns timeline of touchpoints and deals with full attribution details.
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_contact_journey(
        contact_id=contact_id,
        include_deals=include_deals,
    )

    return JourneyResponse(**result)


@router.get("/journeys/conversion-paths", response_model=List[ConversionPathResponse])
async def get_top_conversion_paths(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    limit: int = Query(20, ge=1, le=100, description="Max paths to return"),
    min_conversions: int = Query(2, ge=1, description="Minimum conversions for path"),
    path_by: str = Query("platform", description="Group path by: platform or campaign"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get most common paths that lead to conversions.

    Shows which channel sequences most frequently result in won deals.
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_top_conversion_paths(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        min_conversions=min_conversions,
        path_by=path_by,
    )

    return [ConversionPathResponse(**path) for path in result]


@router.get("/journeys/channel-transitions", response_model=ChannelTransitionsResponse)
async def get_channel_transitions(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    min_transitions: int = Query(5, ge=1, description="Minimum transitions to include"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get channel transition data for Sankey diagram visualization.

    Shows how users move between channels during their journey.
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_channel_transitions(
        start_date=start_date,
        end_date=end_date,
        min_transitions=min_transitions,
    )

    return ChannelTransitionsResponse(**result)


@router.get("/journeys/metrics")
async def get_journey_metrics(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregate journey metrics for the tenant.

    Includes average touches, time to conversion, channel usage.
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_journey_metrics(
        start_date=start_date,
        end_date=end_date,
    )

    return {"data": result}


@router.get("/journeys/assisted-conversions", response_model=List[AssistedConversionsResponse])
async def get_assisted_conversions(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    group_by: str = Query("platform", description="Group by: platform or campaign"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get assisted conversion metrics.

    Shows which channels/campaigns assist conversions (not last touch)
    vs. which directly convert (last touch).
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_assisted_conversions(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
    )

    return [AssistedConversionsResponse(**item) for item in result]


@router.get("/journeys/time-lag")
async def get_time_lag_report(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get time lag analysis between first touch and conversion.

    Shows distribution of how long it takes users to convert.
    """
    service = JourneyService(db, tenant_id)
    result = await service.get_time_lag_report(
        start_date=start_date,
        end_date=end_date,
    )

    return {"data": result}


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/models")
async def list_attribution_models(
    current_user: User = Depends(get_current_user),
):
    """
    List available attribution models with descriptions.
    """
    models = [
        {
            "value": "first_touch",
            "name": "First Touch",
            "description": "100% credit to the first interaction that introduced the customer to your brand.",
            "best_for": "Understanding which channels drive awareness and bring new leads.",
        },
        {
            "value": "last_touch",
            "name": "Last Touch",
            "description": "100% credit to the last interaction before conversion.",
            "best_for": "Identifying which channels are best at closing deals.",
        },
        {
            "value": "linear",
            "name": "Linear",
            "description": "Equal credit distributed across all touchpoints in the journey.",
            "best_for": "Valuing all touchpoints equally when every interaction matters.",
        },
        {
            "value": "position_based",
            "name": "Position-Based (U-Shaped)",
            "description": "40% to first touch, 40% to last touch, 20% distributed among middle touchpoints.",
            "best_for": "Balancing value between awareness (first) and closing (last) touchpoints.",
        },
        {
            "value": "time_decay",
            "name": "Time Decay",
            "description": "More credit to touchpoints closer to conversion, with exponential decay.",
            "best_for": "Short sales cycles where recent interactions are most influential.",
        },
        {
            "value": "data_driven",
            "name": "Data-Driven",
            "description": "Machine learning-based attribution using your actual conversion data.",
            "best_for": "High-volume accounts with sufficient conversion data for modeling.",
        },
    ]

    return {"models": models}


@router.post("/calculate-weights")
async def calculate_weights_preview(
    model: AttributionModel = Query(..., description="Attribution model"),
    touchpoint_count: int = Query(..., ge=1, le=50, description="Number of touchpoints"),
    current_user: User = Depends(get_current_user),
):
    """
    Preview attribution weights for a given model and touchpoint count.

    Useful for understanding how different models distribute credit.
    """
    weights = AttributionCalculator.get_weights(
        model=model,
        touchpoint_count=touchpoint_count,
    )

    return {
        "model": model.value,
        "touchpoint_count": touchpoint_count,
        "weights": [round(w, 4) for w in weights],
        "positions": [
            {
                "position": i + 1,
                "weight": round(w, 4),
                "percentage": f"{round(w * 100, 1)}%",
            }
            for i, w in enumerate(weights)
        ],
    }
