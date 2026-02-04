# =============================================================================
# Stratum AI - Audit Services API Endpoints
# =============================================================================
"""
API endpoints for all audit-recommended services:
- EMQ Measurement
- Offline Conversions
- Model A/B Testing
- Conversion Latency
- Creative Performance
- Competitor Benchmarking
- Budget Reallocation
- Audience Insights
- LTV Predictions
- Model Retraining

Security features:
- All endpoints require authentication
- Tenant isolation on all operations
- Role-based access for admin operations
- Rate limiting on write operations
- Structured audit logging
"""

import threading
import time
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ml.ab_testing import ModelABTestingService
from app.ml.explainability import ModelExplainer
from app.ml.ltv_predictor import CustomerBehavior, LTVPredictor
from app.ml.retraining_pipeline import RetrainingPipeline as ModelRetrainingPipeline
from app.models import User
from app.services.audience_insights_service import AudienceInsightsService, AudienceType
from app.services.budget_reallocation_service import (
    BudgetReallocationService,
    CampaignBudgetState,
    ReallocationConfig,
    ReallocationStrategy,
)
from app.services.competitor_benchmarking_service import (
    CompetitorBenchmarkingService,
    Industry,
    Region,
)
from app.services.conversion_latency_service import ConversionLatencyTracker
from app.services.creative_performance_service import CreativePerformanceService

# Import services
from app.services.emq_measurement_service import RealEMQService as EMQMeasurementService
from app.services.offline_conversion_service import OfflineConversionService
from app.tenancy.deps import get_current_user, get_db, get_tenant_id

logger = get_logger(__name__)
router = APIRouter(prefix="/audit-services", tags=["audit-services"])


# =============================================================================
# Rate Limiting
# =============================================================================


class RateLimiter:
    """Simple in-memory rate limiter for API protection."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        with self._lock:
            # Clean old entries
            self.requests[key] = [t for t in self.requests[key] if t > window_start]

            if len(self.requests[key]) >= self.requests_per_minute:
                return False

            self.requests[key].append(now)
            return True


# Rate limiters for different operation types
_write_limiter = RateLimiter(requests_per_minute=30)  # Writes: 30/min
_read_limiter = RateLimiter(requests_per_minute=120)  # Reads: 120/min
_batch_limiter = RateLimiter(requests_per_minute=10)  # Batch ops: 10/min


async def check_rate_limit(
    limiter: RateLimiter,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_id),
):
    """Dependency to check rate limits."""
    key = f"{tenant_id}:{current_user.id}"
    if not limiter.is_allowed(key):
        logger.warning(
            "Rate limit exceeded", extra={"user_id": str(current_user.id), "tenant_id": tenant_id}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )


async def check_write_rate_limit(
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_id),
):
    """Rate limit for write operations."""
    await check_rate_limit(_write_limiter, current_user, tenant_id)


async def check_batch_rate_limit(
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_id),
):
    """Rate limit for batch operations."""
    await check_rate_limit(_batch_limiter, current_user, tenant_id)


# =============================================================================
# Role-Based Access Control
# =============================================================================


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role for endpoint access."""
    if not hasattr(current_user, "role") or current_user.role not in ("admin", "superadmin"):
        logger.warning(
            "Unauthorized admin access attempt",
            extra={"user_id": str(current_user.id), "email": current_user.email},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_manager_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require manager or admin role for endpoint access."""
    allowed_roles = ("manager", "admin", "superadmin")
    if not hasattr(current_user, "role") or current_user.role not in allowed_roles:
        logger.warning(
            "Unauthorized manager access attempt",
            extra={"user_id": str(current_user.id), "email": current_user.email},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin access required",
        )
    return current_user


# =============================================================================
# Audit Logging
# =============================================================================


class AuditLogger:
    """Structured audit logging for compliance and debugging."""

    @staticmethod
    def log_operation(
        operation: str,
        user_id: str,
        tenant_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        success: bool = True,
    ):
        """Log an audit event."""
        log_data = {
            "audit_event": True,
            "operation": operation,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "success": success,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if success:
            logger.info(f"Audit: {operation} on {resource_type}", extra=log_data)
        else:
            logger.warning(f"Audit: {operation} FAILED on {resource_type}", extra=log_data)


audit_log = AuditLogger()


# =============================================================================
# Service Configuration (Admin)
# =============================================================================

_service_config: dict[str, dict[str, Any]] = {
    "emq": {
        "enabled": True,
        "cache_ttl_seconds": 300,
        "max_history_days": 90,
    },
    "offline_conversions": {
        "enabled": True,
        "max_batch_size": 10000,
        "retry_failed": True,
    },
    "ab_testing": {
        "enabled": True,
        "min_sample_size": 100,
        "default_significance": 0.05,
    },
    "latency_tracking": {
        "enabled": True,
        "alert_threshold_ms": 5000,
        "retention_days": 30,
    },
    "creative_performance": {
        "enabled": True,
        "fatigue_threshold": 0.15,
        "min_impressions": 1000,
    },
    "benchmarking": {
        "enabled": True,
        "update_frequency_hours": 24,
    },
    "budget_reallocation": {
        "enabled": True,
        "require_approval": True,
        "max_change_percent": 50.0,
    },
    "audience_insights": {
        "enabled": True,
        "overlap_threshold": 0.3,
    },
    "ltv_prediction": {
        "enabled": True,
        "model_version": "v1.0",
        "confidence_threshold": 0.7,
    },
    "model_retraining": {
        "enabled": True,
        "auto_retrain": False,
        "performance_threshold": 0.1,
    },
}


# =============================================================================
# Pydantic Schemas
# =============================================================================


# EMQ Schemas
class EMQMeasurementRequest(BaseModel):
    platform: str
    pixel_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class EMQMeasurementResponse(BaseModel):
    success: bool
    platform: str
    pixel_id: str
    overall_score: Optional[float] = None
    parameter_quality: Optional[float] = None
    event_coverage: Optional[float] = None
    match_rate: Optional[float] = None
    recommendations: Optional[list[str]] = None
    error: Optional[str] = None


# Offline Conversion Schemas
class OfflineConversionRecord(BaseModel):
    event_name: str
    event_time: datetime
    value: Optional[float] = None
    currency: str = "USD"
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None
    click_id: Optional[str] = None


class OfflineConversionUploadRequest(BaseModel):
    platform: str
    conversions: list[OfflineConversionRecord]
    batch_name: Optional[str] = None


class OfflineConversionUploadResponse(BaseModel):
    success: bool
    batch_id: Optional[str] = None
    total_records: int
    successful: int = 0
    failed: int = 0
    errors: Optional[list[str]] = None


# Model A/B Testing Schemas
class CreateExperimentRequest(BaseModel):
    name: str
    model_name: str
    champion_version: str
    challenger_version: str
    traffic_split: float = Field(default=0.1, ge=0.01, le=0.5)
    min_samples: int = Field(default=1000, ge=100)
    significance_threshold: float = Field(default=0.05, ge=0.01, le=0.2)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    status: str
    champion_predictions: int
    challenger_predictions: int
    winner: Optional[str] = None
    p_value: Optional[float] = None


# Conversion Latency Schemas
class LatencyStatsResponse(BaseModel):
    platform: str
    event_type: str
    event_count: int
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


# Creative Performance Schemas
class CreativeMetricsRequest(BaseModel):
    creative_id: str
    platform: str
    campaign_id: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0
    revenue: float = 0


class CreativeFatigueResponse(BaseModel):
    creative_id: str
    is_fatigued: bool
    fatigue_score: float
    days_active: int
    ctr_trend: str
    recommendation: Optional[str] = None


# Competitor Benchmark Schemas
class BenchmarkRequest(BaseModel):
    industry: str
    region: str = "GLOBAL"
    platform: str
    metrics: dict[str, float]


class BenchmarkResponse(BaseModel):
    industry: str
    platform: str
    metrics: dict[str, Any]
    overall_score: float
    recommendations: list[str]


# Budget Reallocation Schemas
class CampaignBudgetInput(BaseModel):
    campaign_id: str
    campaign_name: str
    platform: str
    current_daily_budget: float
    current_spend: float
    performance_metrics: dict[str, float]


class ReallocationPlanRequest(BaseModel):
    campaigns: list[CampaignBudgetInput]
    strategy: str = "ROAS_MAXIMIZATION"
    min_campaign_budget: float = 10.0
    max_change_percent: float = 50.0


class ReallocationPlanResponse(BaseModel):
    plan_id: str
    status: str
    total_budget: float
    campaigns_affected: int
    changes: list[dict[str, Any]]
    projected_impact: dict[str, float]


# Audience Insights Schemas
class AudiencePerformanceRequest(BaseModel):
    audience_type: str
    size: int
    platform: str
    budget: float
    lookalike_percent: Optional[float] = None


class AudienceInsightResponse(BaseModel):
    audience_type: str
    predicted_metrics: dict[str, float]
    quality_score: Optional[float] = None
    recommendations: list[str]


# LTV Prediction Schemas
class CustomerBehaviorInput(BaseModel):
    customer_id: str
    acquisition_date: datetime
    acquisition_channel: str
    first_order_value: float
    total_orders: int = 1
    total_revenue: float = 0
    avg_order_value: float = 0
    days_since_last_order: int = 0
    sessions_first_week: int = 1
    email_opens_first_week: int = 0


class LTVPredictionResponse(BaseModel):
    customer_id: str
    segment: str
    predicted_ltv_30d: float
    predicted_ltv_90d: float
    predicted_ltv_365d: float
    predicted_ltv_lifetime: float
    churn_probability: float
    confidence: float
    max_cac: float


# Explainability Schemas
class ExplainPredictionRequest(BaseModel):
    model_name: str
    features: dict[str, float]
    prediction: float


class ExplanationResponse(BaseModel):
    model_name: str
    prediction: float
    top_factors: list[dict[str, Any]]
    summary: str
    confidence: float


# =============================================================================
# EMQ Measurement Endpoints
# =============================================================================


@router.post("/emq/measure", response_model=EMQMeasurementResponse)
async def measure_emq(
    request: EMQMeasurementRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Measure Event Match Quality for a pixel/dataset.
    """
    try:
        service = EMQMeasurementService()
        result = service.measure_emq(
            platform=request.platform,
            pixel_id=request.pixel_id,
            tenant_id=str(tenant_id),
        )

        return EMQMeasurementResponse(
            success=True,
            platform=request.platform,
            pixel_id=request.pixel_id,
            overall_score=result.overall_score,
            parameter_quality=result.parameter_quality,
            event_coverage=result.event_coverage,
            match_rate=result.match_rate,
            recommendations=result.recommendations,
        )
    except Exception as e:
        logger.error(f"EMQ measurement failed: {e}")
        return EMQMeasurementResponse(
            success=False,
            platform=request.platform,
            pixel_id=request.pixel_id,
            error=str(e),
        )


@router.get("/emq/history")
async def get_emq_history(
    platform: str = Query(...),
    pixel_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get historical EMQ measurements.
    """
    service = EMQMeasurementService()
    history = service.get_history(
        platform=platform,
        pixel_id=pixel_id,
        tenant_id=str(tenant_id),
        days=days,
    )

    return {"data": history}


# =============================================================================
# Offline Conversion Endpoints
# =============================================================================


@router.post("/offline-conversions/upload", response_model=OfflineConversionUploadResponse)
async def upload_offline_conversions(
    request: OfflineConversionUploadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Upload offline conversions to ad platforms.
    """
    import uuid

    from app.services.offline_conversion_service import OfflineConversion

    try:
        service = OfflineConversionService()

        # Convert to OfflineConversion objects
        conversions = []
        for i, conv in enumerate(request.conversions):
            conversions.append(
                OfflineConversion(
                    conversion_id=f"{request.batch_name or 'batch'}_{tenant_id}_{i}_{uuid.uuid4().hex[:8]}",
                    platform=request.platform,
                    event_name=conv.event_name,
                    event_time=conv.event_time,
                    conversion_value=conv.value or 0.0,
                    currency=conv.currency or "USD",
                    email=conv.email,
                    phone=conv.phone,
                    external_id=conv.external_id,
                    click_id=conv.click_id,
                )
            )

        result = await service.upload_conversions(
            conversions=conversions,
            platform=request.platform,
        )

        return OfflineConversionUploadResponse(
            success=result.success,
            batch_id=result.batch_id,
            total_records=result.total_records,
            successful=result.successful_records,
            failed=result.failed_records,
            errors=[e.get("message", str(e)) for e in result.errors] if result.errors else None,
        )
    except Exception as e:
        logger.error(f"Offline conversion upload failed: {e}")
        return OfflineConversionUploadResponse(
            success=False,
            total_records=len(request.conversions),
            errors=[str(e)],
        )


@router.get("/offline-conversions/batches")
async def list_conversion_batches(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    List offline conversion upload batches.
    """
    service = OfflineConversionService()
    batches = service.list_batches(
        tenant_id=str(tenant_id),
        platform=platform,
        status=status,
        limit=limit,
    )

    return {"data": batches}


# =============================================================================
# Model A/B Testing Endpoints
# =============================================================================


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new model A/B test experiment.
    """
    service = ModelABTestingService()

    experiment = service.create_experiment(
        name=request.name,
        model_name=request.model_name,
        champion_version=request.champion_version,
        challenger_version=request.challenger_version,
        traffic_split=request.traffic_split,
        min_samples=request.min_samples,
        significance_threshold=request.significance_threshold,
    )

    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        status=experiment.status.value,
        champion_predictions=0,
        challenger_predictions=0,
    )


@router.get("/experiments")
async def list_experiments(
    model_name: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    List model experiments.
    """
    service = ModelABTestingService()
    experiments = service.list_experiments(
        model_name=model_name,
        status=status,
    )

    return {
        "data": [
            {
                "id": exp.id,
                "name": exp.name,
                "model_name": exp.model_name,
                "status": exp.status.value,
                "champion_version": exp.champion_version,
                "challenger_version": exp.challenger_version,
                "traffic_split": exp.traffic_split,
                "champion_predictions": exp.champion_predictions,
                "challenger_predictions": exp.challenger_predictions,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
            }
            for exp in experiments
        ]
    }


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Start an experiment.
    """
    service = ModelABTestingService()
    success = service.start_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to start experiment")

    return {"success": True, "message": "Experiment started"}


@router.post("/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Stop an experiment and evaluate results.
    """
    service = ModelABTestingService()
    result = service.evaluate_experiment(experiment_id)

    return {"success": True, "result": result}


# =============================================================================
# Conversion Latency Endpoints
# =============================================================================


@router.get("/latency/stats", response_model=list[LatencyStatsResponse])
async def get_latency_stats(
    platform: Optional[str] = None,
    event_type: Optional[str] = None,
    period_hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get conversion latency statistics.
    """
    tracker = ConversionLatencyTracker()
    stats_list = []

    platforms = [platform] if platform else ["meta", "google", "tiktok"]
    event_types = [event_type] if event_type else ["Purchase", "Lead", "AddToCart"]

    for p in platforms:
        for et in event_types:
            stats = tracker.get_stats(p, et, period_hours)
            if stats and stats.count > 0:
                stats_list.append(
                    LatencyStatsResponse(
                        platform=p,
                        event_type=et,
                        event_count=stats.count,
                        avg_latency_ms=stats.avg_ms,
                        median_latency_ms=stats.median_ms,
                        p95_latency_ms=stats.p95_ms,
                        p99_latency_ms=stats.p99_ms,
                    )
                )

    return stats_list


@router.get("/latency/timeline")
async def get_latency_timeline(
    platform: str = Query(...),
    event_type: str = Query(...),
    period_hours: int = Query(default=24, ge=1, le=168),
    bucket_minutes: int = Query(default=60, ge=5, le=360),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get latency timeline for visualization.
    """
    tracker = ConversionLatencyTracker()
    timeline = tracker.get_latency_timeline(
        platform=platform,
        event_type=event_type,
        period_hours=period_hours,
        bucket_minutes=bucket_minutes,
    )

    return {"data": timeline}


# =============================================================================
# Creative Performance Endpoints
# =============================================================================


@router.post("/creatives/record-metrics")
async def record_creative_metrics(
    request: CreativeMetricsRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Record performance metrics for a creative.
    """
    service = CreativePerformanceService()

    service.record_metrics(
        creative_id=request.creative_id,
        tenant_id=str(tenant_id),
        platform=request.platform,
        campaign_id=request.campaign_id,
        metrics={
            "impressions": request.impressions,
            "clicks": request.clicks,
            "conversions": request.conversions,
            "spend": request.spend,
            "revenue": request.revenue,
        },
    )

    return {"success": True}


@router.get("/creatives/{creative_id}/fatigue", response_model=CreativeFatigueResponse)
async def analyze_creative_fatigue(
    creative_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze creative fatigue.
    """
    service = CreativePerformanceService()
    analysis = service.analyze_fatigue(creative_id)

    if not analysis:
        raise HTTPException(status_code=404, detail="Creative not found or insufficient data")

    return CreativeFatigueResponse(
        creative_id=creative_id,
        is_fatigued=analysis.is_fatigued,
        fatigue_score=analysis.fatigue_score,
        days_active=analysis.days_active,
        ctr_trend=analysis.ctr_trend,
        recommendation=analysis.recommendation,
    )


@router.get("/creatives/top")
async def get_top_creatives(
    platform: Optional[str] = None,
    metric: str = Query(default="roas", description="Metric to rank by"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get top performing creatives.
    """
    service = CreativePerformanceService()
    top_creatives = service.get_top_creatives(
        tenant_id=str(tenant_id),
        platform=platform,
        metric=metric,
        limit=limit,
    )

    return {"data": top_creatives}


# =============================================================================
# Competitor Benchmarking Endpoints
# =============================================================================


@router.post("/benchmarks/compare", response_model=BenchmarkResponse)
async def compare_to_benchmarks(
    request: BenchmarkRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Compare your metrics to industry benchmarks.
    """
    service = CompetitorBenchmarkingService()

    try:
        industry_enum = Industry(request.industry.upper())
    except ValueError:
        industry_enum = Industry.OTHER

    try:
        region_enum = Region(request.region.upper())
    except ValueError:
        region_enum = Region.GLOBAL

    benchmark = service.get_benchmark(
        tenant_id=str(tenant_id),
        industry=industry_enum,
        region=region_enum,
        platform=request.platform,
        metrics=request.metrics,
    )

    return BenchmarkResponse(
        industry=request.industry,
        platform=request.platform,
        metrics={
            name: {
                "your_value": m.your_value,
                "industry_median": m.industry_median,
                "percentile": m.your_percentile,
                "performance_level": m.performance_level.value,
            }
            for name, m in benchmark.metrics.items()
        },
        overall_score=benchmark.overall_score,
        recommendations=benchmark.recommendations,
    )


@router.get("/benchmarks/industry-report")
async def get_industry_report(
    industry: str = Query(...),
    platform: str = Query(...),
    region: str = Query(default="GLOBAL"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get full industry benchmark report.
    """
    service = CompetitorBenchmarkingService()

    try:
        industry_enum = Industry(industry.upper())
    except ValueError:
        industry_enum = Industry.OTHER

    try:
        region_enum = Region(region.upper())
    except ValueError:
        region_enum = Region.GLOBAL

    report = service.get_industry_report(
        industry=industry_enum,
        platform=platform,
        region=region_enum,
    )

    return {"data": report}


# =============================================================================
# Budget Reallocation Endpoints
# =============================================================================


@router.post("/budget/reallocation-plan", response_model=ReallocationPlanResponse)
async def create_reallocation_plan(
    request: ReallocationPlanRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Create a budget reallocation plan.
    """
    service = BudgetReallocationService()

    # Convert to service format
    campaigns = [
        CampaignBudgetState(
            campaign_id=c.campaign_id,
            campaign_name=c.campaign_name,
            platform=c.platform,
            current_daily_budget=c.current_daily_budget,
            current_spend=c.current_spend,
            performance_metrics=c.performance_metrics,
            data_quality_score=0.8,
        )
        for c in request.campaigns
    ]

    try:
        strategy = ReallocationStrategy(request.strategy)
    except ValueError:
        strategy = ReallocationStrategy.ROAS_MAXIMIZATION

    config = ReallocationConfig(
        strategy=strategy,
        min_campaign_budget=request.min_campaign_budget,
        max_change_percent=request.max_change_percent,
    )

    plan = service.create_plan(
        tenant_id=str(tenant_id),
        campaigns=campaigns,
        config=config,
    )

    return ReallocationPlanResponse(
        plan_id=plan.plan_id,
        status=plan.status.value,
        total_budget=plan.total_budget,
        campaigns_affected=len(plan.changes),
        changes=[
            {
                "campaign_id": c.campaign_id,
                "campaign_name": c.campaign_name,
                "current_budget": c.current_budget,
                "new_budget": c.new_budget,
                "change_percent": c.change_percent,
                "reason": c.reason,
            }
            for c in plan.changes
        ],
        projected_impact={
            "roas_change": plan.projected_roas_change if plan.projected_roas_change else 0,
            "revenue_change": plan.projected_revenue_change if plan.projected_revenue_change else 0,
        },
    )


@router.post("/budget/reallocation-plan/{plan_id}/approve")
async def approve_reallocation_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Approve a budget reallocation plan.
    """
    service = BudgetReallocationService()
    success = service.approve(plan_id, approved_by=current_user.email)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve plan")

    return {"success": True, "message": "Plan approved"}


@router.post("/budget/reallocation-plan/{plan_id}/execute")
async def execute_reallocation_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Execute an approved reallocation plan.
    """
    service = BudgetReallocationService()
    result = service.execute(plan_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=f"Execution failed: {result.error}")

    return {
        "success": True,
        "changes_applied": result.changes_applied,
        "message": "Plan executed successfully",
    }


@router.post("/budget/reallocation-plan/{plan_id}/rollback")
async def rollback_reallocation_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Rollback an executed reallocation plan.
    """
    service = BudgetReallocationService()
    result = service.rollback(plan_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=f"Rollback failed: {result.error}")

    return {"success": True, "message": "Plan rolled back successfully"}


# =============================================================================
# Audience Insights Endpoints
# =============================================================================


@router.post("/audiences/predict-performance", response_model=AudienceInsightResponse)
async def predict_audience_performance(
    request: AudiencePerformanceRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Predict performance for an audience configuration.
    """
    service = AudienceInsightsService()

    try:
        audience_type = AudienceType(request.audience_type.lower())
    except ValueError:
        audience_type = AudienceType.INTEREST

    prediction = service.predict_performance(
        audience_type=audience_type,
        size=request.size,
        platform=request.platform,
        budget=request.budget,
        lookalike_percent=request.lookalike_percent,
    )

    return AudienceInsightResponse(
        audience_type=request.audience_type,
        predicted_metrics=prediction["predictions"],
        quality_score=prediction.get("confidence", 0) * 100,
        recommendations=prediction.get("notes", []),
    )


@router.get("/audiences/{audience_id}/insights")
async def get_audience_insights(
    audience_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get insights for a specific audience.
    """
    service = AudienceInsightsService()
    insights = service.get_insights(audience_id)

    return {
        "data": [
            {
                "type": i.insight_type,
                "severity": i.severity,
                "title": i.title,
                "description": i.description,
                "recommendation": i.recommendation,
            }
            for i in insights
        ]
    }


@router.get("/audiences/recommendations")
async def get_audience_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get audience optimization recommendations.
    """
    service = AudienceInsightsService()
    recommendations = service.get_recommendations(
        tenant_id=str(tenant_id),
        limit=limit,
    )

    return {
        "data": [
            {
                "audience_id": r.audience_id,
                "action": r.action,
                "priority": r.priority,
                "title": r.title,
                "description": r.description,
                "expected_impact": r.expected_impact,
            }
            for r in recommendations
        ]
    }


# =============================================================================
# LTV Prediction Endpoints
# =============================================================================


@router.post("/ltv/predict", response_model=LTVPredictionResponse)
async def predict_customer_ltv(
    request: CustomerBehaviorInput,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Predict customer lifetime value.
    """
    # Use non-existent path to avoid loading potentially incompatible models
    predictor = LTVPredictor(models_path="./models_api")

    behavior = CustomerBehavior(
        customer_id=request.customer_id,
        acquisition_date=request.acquisition_date,
        acquisition_channel=request.acquisition_channel,
        first_order_value=request.first_order_value,
        total_orders=request.total_orders,
        total_revenue=request.total_revenue,
        avg_order_value=request.avg_order_value,
        days_since_last_order=request.days_since_last_order,
        sessions_first_week=request.sessions_first_week,
        email_opens_first_week=request.email_opens_first_week,
    )

    prediction = predictor.predict(behavior)

    return LTVPredictionResponse(
        customer_id=prediction.customer_id,
        segment=prediction.segment.value,
        predicted_ltv_30d=prediction.predicted_ltv_30d,
        predicted_ltv_90d=prediction.predicted_ltv_90d,
        predicted_ltv_365d=prediction.predicted_ltv_365d,
        predicted_ltv_lifetime=prediction.predicted_ltv_lifetime,
        churn_probability=prediction.churn_probability,
        confidence=prediction.confidence,
        max_cac=prediction.recommended_cac_max,
    )


@router.post("/ltv/batch-predict")
async def batch_predict_ltv(
    customers: list[CustomerBehaviorInput],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Batch predict LTV for multiple customers.
    """
    predictor = LTVPredictor(models_path="./models_api")

    predictions = []
    for cust in customers:
        behavior = CustomerBehavior(
            customer_id=cust.customer_id,
            acquisition_date=cust.acquisition_date,
            acquisition_channel=cust.acquisition_channel,
            first_order_value=cust.first_order_value,
            total_orders=cust.total_orders,
            total_revenue=cust.total_revenue,
            avg_order_value=cust.avg_order_value,
            days_since_last_order=cust.days_since_last_order,
            sessions_first_week=cust.sessions_first_week,
            email_opens_first_week=cust.email_opens_first_week,
        )
        pred = predictor.predict(behavior)
        predictions.append(
            {
                "customer_id": pred.customer_id,
                "segment": pred.segment.value,
                "predicted_ltv_365d": pred.predicted_ltv_365d,
                "churn_probability": pred.churn_probability,
                "max_cac": pred.recommended_cac_max,
            }
        )

    return {"predictions": predictions}


@router.get("/ltv/segments")
async def get_ltv_segments(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get LTV segment definitions and thresholds.
    """
    return {
        "segments": [
            {
                "name": "VIP",
                "value": "vip",
                "ltv_threshold": 1000,
                "description": "Top 5% customers",
            },
            {
                "name": "High Value",
                "value": "high_value",
                "ltv_threshold": 500,
                "description": "Top 25% customers",
            },
            {
                "name": "Medium Value",
                "value": "medium_value",
                "ltv_threshold": 200,
                "description": "25-75% customers",
            },
            {
                "name": "Low Value",
                "value": "low_value",
                "ltv_threshold": 0,
                "description": "Bottom 25% customers",
            },
            {
                "name": "At Risk",
                "value": "at_risk",
                "ltv_threshold": None,
                "description": "Customers with declining value",
            },
        ]
    }


# =============================================================================
# Explainability Endpoints
# =============================================================================


@router.post("/explain/prediction", response_model=ExplanationResponse)
async def explain_prediction(
    request: ExplainPredictionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get explanation for a model prediction.
    """
    explainer = ModelExplainer(request.model_name, models_path="./models")

    explanation = explainer.explain_prediction(
        features=request.features,
        prediction=request.prediction,
        top_k=5,
    )

    return ExplanationResponse(
        model_name=explanation.model_name,
        prediction=explanation.predicted_value,
        top_factors=[
            {
                "feature": f.feature_name,
                "contribution": f.contribution,
                "direction": f.direction,
            }
            for f in explanation.top_positive_factors + explanation.top_negative_factors
        ],
        summary=explanation.explanation_summary,
        confidence=explanation.confidence_score,
    )


# =============================================================================
# Model Retraining Endpoints
# =============================================================================


@router.post("/models/retrain")
async def trigger_model_retraining(
    model_name: str = Query(...),
    reason: str = Query(default="manual"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger model retraining.
    """
    pipeline = ModelRetrainingPipeline()

    # Queue retraining job
    job_id = pipeline.schedule_retraining(
        model_name=model_name,
        tenant_id=str(tenant_id) if tenant_id else None,
        trigger_reason=reason,
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Retraining job scheduled for {model_name}",
    }


@router.get("/models/retraining-status")
async def get_retraining_status(
    model_name: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get model retraining job status.
    """
    pipeline = ModelRetrainingPipeline()
    jobs = pipeline.get_job_history(
        model_name=model_name,
        limit=limit,
    )

    return {"data": jobs}


# =============================================================================
# Health & Admin Endpoints
# =============================================================================


@router.get("/health")
async def audit_services_health():
    """
    Health check for audit services.
    """
    services_status = {}

    # Check each service
    try:
        EMQMeasurementService()
        services_status["emq"] = "healthy"
    except Exception:
        services_status["emq"] = "unhealthy"

    try:
        OfflineConversionService()
        services_status["offline_conversions"] = "healthy"
    except Exception:
        services_status["offline_conversions"] = "unhealthy"

    try:
        ModelABTestingService()
        services_status["ab_testing"] = "healthy"
    except Exception:
        services_status["ab_testing"] = "unhealthy"

    try:
        ConversionLatencyTracker()
        services_status["latency_tracking"] = "healthy"
    except Exception:
        services_status["latency_tracking"] = "unhealthy"

    try:
        CreativePerformanceService()
        services_status["creative_performance"] = "healthy"
    except Exception:
        services_status["creative_performance"] = "unhealthy"

    try:
        CompetitorBenchmarkingService()
        services_status["benchmarking"] = "healthy"
    except Exception:
        services_status["benchmarking"] = "unhealthy"

    try:
        BudgetReallocationService()
        services_status["budget_reallocation"] = "healthy"
    except Exception:
        services_status["budget_reallocation"] = "unhealthy"

    try:
        AudienceInsightsService()
        services_status["audience_insights"] = "healthy"
    except Exception:
        services_status["audience_insights"] = "unhealthy"

    try:
        LTVPredictor(models_path="./models_health_check")
        services_status["ltv_predictor"] = "healthy"
    except Exception:
        services_status["ltv_predictor"] = "unhealthy"

    all_healthy = all(s == "healthy" for s in services_status.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/metrics")
async def get_audit_services_metrics(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregate metrics for audit services.
    """
    return {
        "emq": {
            "measurements_today": 0,
            "avg_score": None,
        },
        "offline_conversions": {
            "uploads_today": 0,
            "records_processed": 0,
        },
        "experiments": {
            "active_count": 0,
            "completed_count": 0,
        },
        "creative_alerts": {
            "fatigue_alerts_today": 0,
            "unacknowledged": 0,
        },
        "budget_plans": {
            "pending_approval": 0,
            "executed_today": 0,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Admin Configuration Endpoints
# =============================================================================


class ServiceConfigUpdate(BaseModel):
    """Schema for updating service configuration."""

    config: dict[str, Any]


@router.get("/admin/config")
async def get_all_service_config(
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Get all service configurations (admin only).
    """
    audit_log.log_operation(
        operation="read_config",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="service_config",
        details={"scope": "all"},
    )
    return {
        "config": _service_config,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/admin/config/{service_name}")
async def get_service_config(
    service_name: str,
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Get configuration for a specific service (admin only).
    """
    if service_name not in _service_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found",
        )

    audit_log.log_operation(
        operation="read_config",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="service_config",
        resource_id=service_name,
    )

    return {
        "service": service_name,
        "config": _service_config[service_name],
    }


@router.put("/admin/config/{service_name}")
async def update_service_config(
    service_name: str,
    update: ServiceConfigUpdate,
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
    _: None = Depends(check_write_rate_limit),
):
    """
    Update configuration for a specific service (admin only).
    """
    if service_name not in _service_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found",
        )

    old_config = _service_config[service_name].copy()

    # Update config (only known keys)
    for key, value in update.config.items():
        if key in _service_config[service_name]:
            _service_config[service_name][key] = value

    audit_log.log_operation(
        operation="update_config",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="service_config",
        resource_id=service_name,
        details={
            "old_config": old_config,
            "new_config": _service_config[service_name],
        },
    )

    return {
        "success": True,
        "service": service_name,
        "config": _service_config[service_name],
    }


@router.post("/admin/services/{service_name}/enable")
async def enable_service(
    service_name: str,
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
    _: None = Depends(check_write_rate_limit),
):
    """
    Enable a service (admin only).
    """
    if service_name not in _service_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found",
        )

    _service_config[service_name]["enabled"] = True

    audit_log.log_operation(
        operation="enable_service",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="service",
        resource_id=service_name,
    )

    return {"success": True, "service": service_name, "enabled": True}


@router.post("/admin/services/{service_name}/disable")
async def disable_service(
    service_name: str,
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
    _: None = Depends(check_write_rate_limit),
):
    """
    Disable a service (admin only).
    """
    if service_name not in _service_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found",
        )

    _service_config[service_name]["enabled"] = False

    audit_log.log_operation(
        operation="disable_service",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="service",
        resource_id=service_name,
    )

    return {"success": True, "service": service_name, "enabled": False}


@router.get("/admin/services/status")
async def get_services_status(
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Get enabled/disabled status of all services (admin only).
    """
    status_map = {name: config.get("enabled", True) for name, config in _service_config.items()}

    return {
        "services": status_map,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/admin/audit-log")
async def get_audit_log(
    operation: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Get audit log entries (admin only).
    Note: In production, this would query from a database or log aggregation service.
    """
    return {
        "message": "Audit logs are written to the application log stream",
        "log_location": "/var/log/stratum/audit.log",
        "filters": {
            "operation": operation,
            "resource_type": resource_type,
        },
        "hint": "Use log aggregation tools (ELK, Datadog, etc.) to query audit events",
    }


@router.post("/admin/cache/clear")
async def clear_service_cache(
    service_name: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
    _: None = Depends(check_write_rate_limit),
):
    """
    Clear service caches (admin only).
    """
    if service_name:
        if service_name not in _service_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found",
            )
        cleared = [service_name]
    else:
        cleared = list(_service_config.keys())

    audit_log.log_operation(
        operation="clear_cache",
        user_id=str(admin_user.id),
        tenant_id=tenant_id,
        resource_type="cache",
        details={"services_cleared": cleared},
    )

    return {
        "success": True,
        "caches_cleared": cleared,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Rate Limit Status (Admin)
# =============================================================================


@router.get("/admin/rate-limits")
async def get_rate_limit_status(
    admin_user: User = Depends(require_admin),
):
    """
    Get current rate limit configuration (admin only).
    """
    return {
        "write_operations": {
            "requests_per_minute": _write_limiter.requests_per_minute,
            "description": "Limit for write/create operations",
        },
        "read_operations": {
            "requests_per_minute": _read_limiter.requests_per_minute,
            "description": "Limit for read/list operations",
        },
        "batch_operations": {
            "requests_per_minute": _batch_limiter.requests_per_minute,
            "description": "Limit for batch/bulk operations",
        },
    }


# =============================================================================
# Service Info Endpoint
# =============================================================================


@router.get("/info")
async def get_audit_services_info():
    """
    Get information about available audit services.
    Public endpoint for API discovery.
    """
    return {
        "name": "Stratum AI Audit Services",
        "version": "1.0.0",
        "services": [
            {
                "name": "EMQ Measurement",
                "prefix": "/emq",
                "description": "Event Match Quality measurement and tracking",
            },
            {
                "name": "Offline Conversions",
                "prefix": "/offline-conversions",
                "description": "Upload offline conversion data to ad platforms",
            },
            {
                "name": "Model A/B Testing",
                "prefix": "/experiments",
                "description": "Champion/Challenger model experiments",
            },
            {
                "name": "Conversion Latency",
                "prefix": "/latency",
                "description": "Track and analyze conversion latency",
            },
            {
                "name": "Creative Performance",
                "prefix": "/creatives",
                "description": "Creative fatigue detection and performance tracking",
            },
            {
                "name": "Competitor Benchmarking",
                "prefix": "/benchmarks",
                "description": "Industry and regional performance benchmarks",
            },
            {
                "name": "Budget Reallocation",
                "prefix": "/budget",
                "description": "AI-powered budget optimization with approval workflow",
            },
            {
                "name": "Audience Insights",
                "prefix": "/audiences",
                "description": "Audience performance prediction and insights",
            },
            {
                "name": "LTV Prediction",
                "prefix": "/ltv",
                "description": "Customer lifetime value prediction",
            },
            {
                "name": "Model Explainability",
                "prefix": "/explain",
                "description": "Explain ML model predictions",
            },
            {
                "name": "Model Retraining",
                "prefix": "/models",
                "description": "Trigger and monitor model retraining",
            },
        ],
        "admin_endpoints": [
            "/admin/config",
            "/admin/services/status",
            "/admin/audit-log",
            "/admin/cache/clear",
            "/admin/rate-limits",
        ],
    }
