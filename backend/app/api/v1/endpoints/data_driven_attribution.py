# =============================================================================
# Stratum AI - Data-Driven Attribution API Endpoints
# =============================================================================
"""
API endpoints for data-driven attribution using ML models.

Provides:
- Model training (Markov Chain, Shapley Values)
- Model comparison and validation
- Attribution using trained models
- Recommendations for model selection
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import User
from app.models.attribution import (
    ModelStatus,
    ModelTrainingRun,
    TrainedAttributionModel,
)
from app.services.attribution import (
    DataDrivenModelType,
    MarkovAttributionService,
    ModelTrainingService,
    ShapleyAttributionService,
)
from app.tenancy.deps import get_current_user, get_db, get_tenant_id

logger = get_logger(__name__)
router = APIRouter(prefix="/attribution/data-driven", tags=["data-driven-attribution"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class TrainModelRequest(BaseModel):
    """Request to train a data-driven model."""

    model_type: str = Field(
        ..., description="Model type: 'markov_chain' or 'shapley_value'"
    )
    start_date: datetime = Field(..., description="Training period start")
    end_date: datetime = Field(..., description="Training period end")
    channel_type: str = Field(
        default="platform", description="Channel type: 'platform' or 'campaign'"
    )
    include_non_converting: bool = Field(
        default=True, description="Include non-converting journeys in training"
    )
    min_journeys: int = Field(
        default=100, ge=10, description="Minimum journeys required for training"
    )
    model_name: Optional[str] = Field(
        default=None, description="Optional name for the trained model"
    )


class TrainAllModelsRequest(BaseModel):
    """Request to train all model types."""

    start_date: datetime
    end_date: datetime
    channel_type: str = "platform"
    include_non_converting: bool = True
    min_journeys: int = 100


class AttributeWithModelRequest(BaseModel):
    """Request to attribute using a trained model."""

    model_type: str
    model_data: dict
    deal_id: UUID


class BatchAttributeRequest(BaseModel):
    """Request to batch attribute multiple deals."""

    model_type: str
    model_data: dict
    deal_ids: List[UUID]


class CompareWithRuleBasedRequest(BaseModel):
    """Request to compare data-driven with rule-based attribution."""

    data_driven_weights: dict
    start_date: datetime
    end_date: datetime


class ValidateModelRequest(BaseModel):
    """Request to validate a trained model."""

    model_type: str
    model_data: dict
    validation_start: datetime
    validation_end: datetime


class ModelTrainingResponse(BaseModel):
    """Response from model training."""

    success: bool
    model_id: Optional[str] = None
    model_type: Optional[str] = None
    model_name: Optional[str] = None
    channel_type: Optional[str] = None
    training_period: Optional[dict] = None
    stats: Optional[dict] = None
    attribution_weights: Optional[dict] = None
    model_data: Optional[dict] = None
    error: Optional[str] = None


class ModelComparisonResponse(BaseModel):
    """Response from model comparison."""

    success: bool
    training_period: dict
    channel_type: str
    models: dict
    weights_comparison: dict
    consensus_weights: dict


class ModelRecommendationResponse(BaseModel):
    """Response with model recommendation."""

    recommendation: str
    recommended_model: str
    reason: str
    deals_analyzed: int
    avg_journey_length: Optional[float] = None
    minimum_required: Optional[int] = None


# =============================================================================
# Model Training Endpoints
# =============================================================================


@router.post("/train", response_model=ModelTrainingResponse)
async def train_model(
    request: TrainModelRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Train a data-driven attribution model.

    Supports:
    - **markov_chain**: Uses transition probabilities and removal effects
    - **shapley_value**: Uses game theory for fair credit distribution

    Requires sufficient historical journey data for training.
    """
    if request.model_type not in [
        DataDrivenModelType.MARKOV_CHAIN,
        DataDrivenModelType.SHAPLEY_VALUE,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_type. Must be 'markov_chain' or 'shapley_value'",
        )

    service = ModelTrainingService(db, tenant_id)
    result = await service.train_model(
        model_type=request.model_type,
        start_date=request.start_date,
        end_date=request.end_date,
        channel_type=request.channel_type,
        include_non_converting=request.include_non_converting,
        min_journeys=request.min_journeys,
        model_name=request.model_name,
        created_by_user_id=current_user.id,
    )

    return ModelTrainingResponse(**result)


@router.post("/train-all", response_model=ModelComparisonResponse)
async def train_all_models(
    request: TrainAllModelsRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Train all available model types and compare results.

    Returns attribution weights from both Markov Chain and Shapley Value models,
    along with a consensus (averaged) weight distribution.
    """
    service = ModelTrainingService(db, tenant_id)
    result = await service.train_all_models(
        start_date=request.start_date,
        end_date=request.end_date,
        channel_type=request.channel_type,
        include_non_converting=request.include_non_converting,
        min_journeys=request.min_journeys,
    )

    return ModelComparisonResponse(**result)


@router.get("/recommend", response_model=ModelRecommendationResponse)
async def get_model_recommendation(
    start_date: datetime = Query(..., description="Analysis period start"),
    end_date: datetime = Query(..., description="Analysis period end"),
    channel_type: str = Query("platform", description="Channel type"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get a recommendation for which attribution model to use.

    Analyzes journey characteristics (length, channel diversity, data volume)
    to recommend the most appropriate model type.
    """
    service = ModelTrainingService(db, tenant_id)
    result = await service.get_recommended_model(
        start_date=start_date,
        end_date=end_date,
        channel_type=channel_type,
    )

    return ModelRecommendationResponse(**result)


# =============================================================================
# Model Attribution Endpoints
# =============================================================================


@router.post("/attribute")
async def attribute_with_model(
    request: AttributeWithModelRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Attribute a deal using a trained data-driven model.

    Pass the model_data from a previous training response.
    """
    if request.model_type == DataDrivenModelType.MARKOV_CHAIN:
        service = MarkovAttributionService(db, tenant_id)
    elif request.model_type == DataDrivenModelType.SHAPLEY_VALUE:
        service = ShapleyAttributionService(db, tenant_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid model_type")

    result = await service.attribute_with_model(
        model_data=request.model_data,
        deal_id=request.deal_id,
    )

    return {"data": result}


@router.post("/batch-attribute")
async def batch_attribute_with_model(
    request: BatchAttributeRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Batch attribute multiple deals using a trained model.
    """
    if request.model_type == DataDrivenModelType.MARKOV_CHAIN:
        service = MarkovAttributionService(db, tenant_id)
    elif request.model_type == DataDrivenModelType.SHAPLEY_VALUE:
        service = ShapleyAttributionService(db, tenant_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid model_type")

    results = []
    for deal_id in request.deal_ids:
        result = await service.attribute_with_model(request.model_data, deal_id)
        results.append(result)

    successful = sum(1 for r in results if r.get("success"))

    return {
        "total": len(request.deal_ids),
        "successful": successful,
        "failed": len(request.deal_ids) - successful,
        "results": results,
    }


# =============================================================================
# Model Validation Endpoints
# =============================================================================


@router.post("/validate")
async def validate_model(
    request: ValidateModelRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a trained model on holdout data.

    Tests the model's attribution accuracy on data not used for training.
    """
    service = ModelTrainingService(db, tenant_id)
    result = await service.validate_model(
        model_data=request.model_data,
        model_type=request.model_type,
        validation_start=request.validation_start,
        validation_end=request.validation_end,
    )

    return {"data": result}


@router.post("/compare-with-rule-based")
async def compare_with_rule_based(
    request: CompareWithRuleBasedRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Compare data-driven weights with rule-based attribution models.

    Shows correlation between data-driven results and traditional models
    (first touch, last touch, linear, position-based, time decay).
    """
    service = ModelTrainingService(db, tenant_id)
    result = await service.compare_with_rule_based(
        data_driven_weights=request.data_driven_weights,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    return {"data": result}


# =============================================================================
# Model Information Endpoints
# =============================================================================


@router.get("/model-types")
async def list_model_types(
    current_user: User = Depends(get_current_user),
):
    """
    List available data-driven model types with descriptions.
    """
    return {
        "model_types": [
            {
                "value": "markov_chain",
                "name": "Markov Chain",
                "description": "Models customer journeys as state transitions. Calculates channel importance based on removal effect - how conversion probability changes when a channel is removed.",
                "best_for": "Long, complex journeys with sequential dependencies between channels.",
                "requirements": "At least 100 journeys with both converting and non-converting paths.",
                "computational_complexity": "Medium - O(n³) where n is number of channels.",
            },
            {
                "value": "shapley_value",
                "name": "Shapley Value",
                "description": "Uses game theory to fairly distribute credit among channels based on their marginal contribution to conversions across all possible orderings.",
                "best_for": "Fair credit distribution when channel order may not matter as much.",
                "requirements": "At least 100 journeys. More accurate with diverse coalition observations.",
                "computational_complexity": "High - O(2^n) exact, O(n²) with sampling.",
            },
        ]
    }


@router.get("/training-requirements")
async def get_training_requirements(
    start_date: datetime = Query(..., description="Proposed training start"),
    end_date: datetime = Query(..., description="Proposed training end"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Check if there's sufficient data for model training.

    Returns data availability and recommendations.
    """
    from sqlalchemy import and_, func, select

    from app.models.crm import CRMContact, CRMDeal, Touchpoint

    # Count won deals
    deal_count = await db.scalar(
        select(func.count(CRMDeal.id)).where(
            and_(
                CRMDeal.tenant_id == tenant_id,
                CRMDeal.is_won == True,
                CRMDeal.won_at >= start_date,
                CRMDeal.won_at <= end_date,
                CRMDeal.contact_id.isnot(None),
            )
        )
    )

    # Count touchpoints
    touchpoint_count = await db.scalar(
        select(func.count(Touchpoint.id)).where(
            and_(
                Touchpoint.tenant_id == tenant_id,
                Touchpoint.event_ts >= start_date,
                Touchpoint.event_ts <= end_date,
            )
        )
    )

    # Count unique channels
    channel_result = await db.execute(
        select(func.count(func.distinct(Touchpoint.source))).where(
            and_(
                Touchpoint.tenant_id == tenant_id,
                Touchpoint.event_ts >= start_date,
                Touchpoint.event_ts <= end_date,
            )
        )
    )
    unique_channels = channel_result.scalar() or 0

    # Assess readiness
    min_deals = 100
    is_ready = deal_count >= min_deals

    recommendations = []
    if deal_count < min_deals:
        recommendations.append(
            f"Need at least {min_deals} won deals (currently {deal_count})"
        )
    if unique_channels < 2:
        recommendations.append(
            "Need at least 2 unique channels for meaningful attribution"
        )
    if touchpoint_count < deal_count * 2:
        recommendations.append("Low touchpoint-to-deal ratio may affect model accuracy")

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "data_availability": {
            "won_deals": deal_count,
            "touchpoints": touchpoint_count,
            "unique_channels": unique_channels,
        },
        "requirements": {
            "minimum_deals": min_deals,
            "minimum_channels": 2,
        },
        "is_ready": is_ready,
        "recommendations": (
            recommendations if recommendations else ["Data sufficient for training"]
        ),
    }


# =============================================================================
# Model Registry (persisted trained models)
# =============================================================================


def _serialize_model(m: TrainedAttributionModel, *, full: bool = False) -> dict:
    """Serialize a TrainedAttributionModel to a JSON-safe dict."""
    data = {
        "id": str(m.id),
        "model_name": m.model_name,
        "model_type": getattr(m.model_type, "value", m.model_type),
        "channel_type": m.channel_type,
        "status": getattr(m.status, "value", m.status),
        "is_active": m.is_active,
        "training_start": m.training_start.isoformat() if m.training_start else None,
        "training_end": m.training_end.isoformat() if m.training_end else None,
        "journey_count": m.journey_count,
        "converting_journeys": m.converting_journeys,
        "unique_channels": m.unique_channels,
        "validation_accuracy": m.validation_accuracy,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
    if full:
        data.update(
            {
                "attribution_weights": m.attribution_weights,
                "removal_effects": m.removal_effects,
                "shapley_values": m.shapley_values,
                "baseline_conversion_rate": m.baseline_conversion_rate,
                "model_data": m.model_data,
            }
        )
    return data


async def _get_owned_model(
    db: AsyncSession, tenant_id: int, model_id: UUID
) -> TrainedAttributionModel:
    result = await db.execute(
        select(TrainedAttributionModel).where(
            TrainedAttributionModel.id == model_id,
            TrainedAttributionModel.tenant_id == tenant_id,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Trained model not found")
    return model


@router.get("/models")
async def list_trained_models(
    model_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """List trained attribution models for the tenant (newest first)."""
    query = select(TrainedAttributionModel).where(
        TrainedAttributionModel.tenant_id == tenant_id
    )
    if model_type:
        query = query.where(TrainedAttributionModel.model_type == model_type)
    if is_active is not None:
        query = query.where(TrainedAttributionModel.is_active.is_(is_active))
    if status:
        query = query.where(TrainedAttributionModel.status == status)
    query = query.order_by(TrainedAttributionModel.created_at.desc())

    result = await db.execute(query)
    models = result.scalars().all()
    return {
        "status": "success",
        "count": len(models),
        "models": [_serialize_model(m) for m in models],
    }


@router.get("/models/{model_id}")
async def get_trained_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """Get a trained model with its full weights/effects (its 'results')."""
    model = await _get_owned_model(db, tenant_id, model_id)
    return {"status": "success", "model": _serialize_model(model, full=True)}


@router.post("/models/{model_id}/activate")
async def activate_trained_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """Mark a model as the active one for its (model_type, channel_type)."""
    model = await _get_owned_model(db, tenant_id, model_id)

    # Only one active model per (model_type, channel_type) — deactivate siblings.
    siblings = await db.execute(
        select(TrainedAttributionModel).where(
            TrainedAttributionModel.tenant_id == tenant_id,
            TrainedAttributionModel.model_type == model.model_type,
            TrainedAttributionModel.channel_type == model.channel_type,
            TrainedAttributionModel.is_active.is_(True),
        )
    )
    for other in siblings.scalars().all():
        other.is_active = False

    model.is_active = True
    model.status = ModelStatus.ACTIVE
    await db.commit()
    await db.refresh(model)
    return {"status": "success", "model": _serialize_model(model)}


@router.post("/models/{model_id}/archive")
async def archive_trained_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """Archive a model, removing it from active use."""
    model = await _get_owned_model(db, tenant_id, model_id)
    model.is_active = False
    model.status = ModelStatus.ARCHIVED
    await db.commit()
    await db.refresh(model)
    return {"status": "success", "model": _serialize_model(model)}


@router.get("/training-runs")
async def list_training_runs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """List model training-run history for the tenant (newest first)."""
    result = await db.execute(
        select(ModelTrainingRun)
        .where(ModelTrainingRun.tenant_id == tenant_id)
        .order_by(ModelTrainingRun.started_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    return {
        "status": "success",
        "count": len(runs),
        "runs": [
            {
                "id": str(r.id),
                "model_id": str(r.model_id) if r.model_id else None,
                "model_type": getattr(r.model_type, "value", r.model_type),
                "channel_type": r.channel_type,
                "status": getattr(r.status, "value", r.status),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "journey_count": r.journey_count,
                "converting_journeys": r.converting_journeys,
            }
            for r in runs
        ],
    }
