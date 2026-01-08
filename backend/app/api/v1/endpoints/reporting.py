# =============================================================================
# Stratum AI - Automated Reporting API Endpoints
# =============================================================================
"""
API endpoints for automated report generation and scheduling.

Endpoints:
- Templates: CRUD operations for report templates
- Schedules: Create and manage scheduled reports
- Executions: Generate reports and view history
- Delivery: Manage delivery channels and retry failed deliveries
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.deps import get_current_user, get_db
from app.core.logging import get_logger
from app.models import User
from app.models.reporting import (
    ReportType,
    ReportFormat,
    ScheduleFrequency,
    DeliveryChannel,
    ExecutionStatus,
)
from app.services.reporting import (
    ReportGenerator,
    ReportScheduler,
    DeliveryService,
)

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================

# -------------------------------------------------------------------------
# Template Schemas
# -------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    """Schema for creating a report template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    report_type: ReportType
    config: Dict[str, Any] = Field(default_factory=dict)
    default_format: ReportFormat = ReportFormat.PDF
    available_formats: List[str] = Field(default=["pdf", "csv"])
    template_html: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None


class TemplateUpdate(BaseModel):
    """Schema for updating a report template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    default_format: Optional[ReportFormat] = None
    available_formats: Optional[List[str]] = None
    template_html: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Response schema for a report template."""
    id: UUID
    name: str
    description: Optional[str]
    report_type: str
    config: Dict[str, Any]
    default_format: str
    available_formats: List[str]
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Schedule Schemas
# -------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    """Schema for creating a scheduled report."""
    template_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    frequency: ScheduleFrequency
    timezone: str = "UTC"
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=-1, le=31)
    hour: int = Field(default=8, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    cron_expression: Optional[str] = None
    format_override: Optional[ReportFormat] = None
    config_override: Optional[Dict[str, Any]] = None
    date_range_type: str = "last_30_days"
    delivery_channels: List[str] = Field(default=["email"])
    delivery_config: Dict[str, Any] = Field(default_factory=dict)


class ScheduleUpdate(BaseModel):
    """Schema for updating a scheduled report."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    frequency: Optional[ScheduleFrequency] = None
    timezone: Optional[str] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=-1, le=31)
    hour: Optional[int] = Field(None, ge=0, le=23)
    minute: Optional[int] = Field(None, ge=0, le=59)
    cron_expression: Optional[str] = None
    format_override: Optional[ReportFormat] = None
    config_override: Optional[Dict[str, Any]] = None
    date_range_type: Optional[str] = None
    delivery_channels: Optional[List[str]] = None
    delivery_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Response schema for a scheduled report."""
    id: UUID
    template_id: UUID
    name: str
    description: Optional[str]
    frequency: str
    timezone: str
    day_of_week: Optional[int]
    day_of_month: Optional[int]
    hour: int
    minute: int
    cron_expression: Optional[str]
    format_override: Optional[str]
    date_range_type: str
    delivery_channels: List[str]
    is_active: bool
    is_paused: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    run_count: int
    failure_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Execution Schemas
# -------------------------------------------------------------------------

class GenerateReportRequest(BaseModel):
    """Schema for generating a report on-demand."""
    template_id: UUID
    start_date: date
    end_date: date
    format: ReportFormat = ReportFormat.PDF
    config_override: Optional[Dict[str, Any]] = None
    deliver_to: Optional[List[str]] = None  # Channel names
    delivery_config: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    """Response schema for a report execution."""
    id: UUID
    template_id: Optional[UUID]
    schedule_id: Optional[UUID]
    execution_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    report_type: str
    format: str
    date_range_start: date
    date_range_end: date
    file_url: Optional[str]
    file_size_bytes: Optional[int]
    row_count: Optional[int]
    metrics_summary: Optional[Dict[str, Any]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Delivery Schemas
# -------------------------------------------------------------------------

class DeliveryChannelConfigCreate(BaseModel):
    """Schema for configuring a delivery channel."""
    channel: DeliveryChannel
    name: str = Field(..., min_length=1, max_length=255)
    config: Dict[str, Any]


class DeliveryStatusResponse(BaseModel):
    """Response schema for delivery status."""
    id: str
    channel: str
    recipient: str
    status: str
    sent_at: Optional[str]
    error: Optional[str]
    retry_count: int


# =============================================================================
# Template Endpoints
# =============================================================================

@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new report template."""
    from app.models.reporting import ReportTemplate

    template = ReportTemplate(
        tenant_id=current_user.tenant_id,
        name=data.name,
        description=data.description,
        report_type=data.report_type,
        config=data.config,
        default_format=data.default_format,
        available_formats=data.available_formats,
        template_html=data.template_html,
        chart_config=data.chart_config,
        created_by_user_id=current_user.id,
        last_modified_by_user_id=current_user.id,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    report_type: Optional[ReportType] = None,
    is_active: bool = True,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List report templates."""
    from sqlalchemy import select, and_
    from app.models.reporting import ReportTemplate

    conditions = [
        ReportTemplate.tenant_id == current_user.tenant_id,
        ReportTemplate.is_active == is_active,
    ]

    if report_type:
        conditions.append(ReportTemplate.report_type == report_type)

    query = (
        select(ReportTemplate)
        .where(and_(*conditions))
        .order_by(ReportTemplate.name)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get a specific report template."""
    from app.models.reporting import ReportTemplate

    template = await db.get(ReportTemplate, template_id)
    if not template or template.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update a report template."""
    from app.models.reporting import ReportTemplate

    template = await db.get(ReportTemplate, template_id)
    if not template or template.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system templates")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.last_modified_by_user_id = current_user.id

    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a report template."""
    from app.models.reporting import ReportTemplate

    template = await db.get(ReportTemplate, template_id)
    if not template or template.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")

    await db.delete(template)
    await db.commit()

    return {"status": "deleted"}


# =============================================================================
# Schedule Endpoints
# =============================================================================

@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    try:
        schedule = await scheduler.create_schedule(
            template_id=data.template_id,
            name=data.name,
            frequency=data.frequency,
            delivery_config=data.delivery_config,
            description=data.description,
            timezone=data.timezone,
            day_of_week=data.day_of_week,
            day_of_month=data.day_of_month,
            hour=data.hour,
            minute=data.minute,
            cron_expression=data.cron_expression,
            format_override=data.format_override,
            config_override=data.config_override,
            date_range_type=data.date_range_type,
            delivery_channels=data.delivery_channels,
            created_by_user_id=current_user.id,
        )
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    is_active: Optional[bool] = None,
    template_id: Optional[UUID] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List scheduled reports."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    schedules, total = await scheduler.list_schedules(
        is_active=is_active,
        template_id=template_id,
        limit=limit,
        offset=offset,
    )

    return schedules


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get a specific scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    schedule = await scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update a scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    try:
        update_data = data.model_dump(exclude_unset=True)
        schedule = await scheduler.update_schedule(schedule_id, **update_data)
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/schedules/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Pause a scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    try:
        schedule = await scheduler.pause_schedule(schedule_id)
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/schedules/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Resume a paused scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    try:
        schedule = await scheduler.resume_schedule(schedule_id)
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/schedules/{schedule_id}/run-now", response_model=ExecutionResponse)
async def run_schedule_now(
    schedule_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Manually trigger a scheduled report to run immediately."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    try:
        execution = await scheduler.run_now(schedule_id, current_user.id)
        return execution
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    deleted = await scheduler.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"status": "deleted"}


@router.get("/schedules/{schedule_id}/history", response_model=List[ExecutionResponse])
async def get_schedule_history(
    schedule_id: UUID,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get execution history for a scheduled report."""
    scheduler = ReportScheduler(db, current_user.tenant_id)

    # Verify schedule exists
    schedule = await scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    executions = await scheduler.get_execution_history(schedule_id, limit)
    return executions


# =============================================================================
# Report Generation Endpoints
# =============================================================================

@router.post("/generate", response_model=ExecutionResponse)
async def generate_report(
    data: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Generate a report on-demand."""
    generator = ReportGenerator(db, current_user.tenant_id)

    try:
        result = await generator.generate_report(
            template_id=data.template_id,
            start_date=data.start_date,
            end_date=data.end_date,
            format=data.format,
            config_override=data.config_override,
            triggered_by_user_id=current_user.id,
            execution_type="manual",
        )

        # Optionally deliver the report
        if data.deliver_to and data.delivery_config:
            delivery_service = DeliveryService(db, current_user.tenant_id)
            await delivery_service.deliver_report(
                execution_id=result["execution_id"],
                channels=data.deliver_to,
                delivery_config=data.delivery_config,
            )

        # Get execution record
        from app.models.reporting import ReportExecution
        execution = await db.get(ReportExecution, result["execution_id"])
        return execution

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions", response_model=List[ExecutionResponse])
async def list_executions(
    status: Optional[ExecutionStatus] = None,
    report_type: Optional[ReportType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List report executions."""
    from sqlalchemy import select, and_
    from app.models.reporting import ReportExecution

    conditions = [ReportExecution.tenant_id == current_user.tenant_id]

    if status:
        conditions.append(ReportExecution.status == status)
    if report_type:
        conditions.append(ReportExecution.report_type == report_type)
    if start_date:
        conditions.append(ReportExecution.started_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        conditions.append(ReportExecution.started_at <= datetime.combine(end_date, datetime.max.time()))

    query = (
        select(ReportExecution)
        .where(and_(*conditions))
        .order_by(ReportExecution.started_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get a specific report execution."""
    from app.models.reporting import ReportExecution

    execution = await db.get(ReportExecution, execution_id)
    if not execution or execution.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@router.get("/executions/{execution_id}/download")
async def download_report(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get download URL for a generated report."""
    from app.models.reporting import ReportExecution

    execution = await db.get(ReportExecution, execution_id)
    if not execution or execution.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status != ExecutionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report not ready for download")

    if not execution.file_url:
        raise HTTPException(status_code=404, detail="Report file not available")

    return {
        "download_url": execution.file_url,
        "expires_at": execution.file_url_expires_at.isoformat() if execution.file_url_expires_at else None,
        "format": execution.format.value,
        "file_size_bytes": execution.file_size_bytes,
    }


# =============================================================================
# Delivery Endpoints
# =============================================================================

@router.get("/executions/{execution_id}/deliveries", response_model=List[DeliveryStatusResponse])
async def get_delivery_status(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get delivery status for a report execution."""
    delivery_service = DeliveryService(db, current_user.tenant_id)

    # Verify execution exists
    from app.models.reporting import ReportExecution
    execution = await db.get(ReportExecution, execution_id)
    if not execution or execution.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    deliveries = await delivery_service.get_delivery_status(execution_id)
    return deliveries


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Retry a failed delivery."""
    delivery_service = DeliveryService(db, current_user.tenant_id)

    try:
        result = await delivery_service.retry_delivery(delivery_id)
        return {
            "success": result.get("success"),
            "error": result.get("error"),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Report Type Info Endpoint
# =============================================================================

@router.get("/report-types")
async def get_report_types(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get available report types and their configurations."""
    return {
        "report_types": [
            {
                "type": "campaign_performance",
                "name": "Campaign Performance",
                "description": "Detailed campaign metrics including spend, revenue, and ROI",
                "default_metrics": ["spend", "revenue", "roas", "conversions", "ctr", "cpc"],
                "available_dimensions": ["campaign", "platform", "date", "ad_set", "ad"],
            },
            {
                "type": "attribution_summary",
                "name": "Attribution Summary",
                "description": "Multi-touch attribution analysis across channels",
                "default_metrics": ["attributed_revenue", "touchpoints", "conversion_paths"],
                "available_models": ["first_touch", "last_touch", "linear", "position_based", "time_decay"],
            },
            {
                "type": "pacing_status",
                "name": "Pacing Status",
                "description": "Target pacing and forecasting report",
                "default_metrics": ["target_value", "actual_value", "pacing_pct", "projected_value"],
                "available_dimensions": ["target", "metric_type", "platform"],
            },
            {
                "type": "profit_roas",
                "name": "Profit & ROAS",
                "description": "Profitability analysis with COGS deduction",
                "default_metrics": ["revenue", "cogs", "gross_profit", "net_profit", "profit_margin", "true_roas"],
                "available_dimensions": ["campaign", "platform", "product_category"],
            },
            {
                "type": "pipeline_metrics",
                "name": "Pipeline Metrics",
                "description": "CRM pipeline and deal tracking",
                "default_metrics": ["deals_created", "deals_won", "deal_value", "conversion_rate"],
                "available_dimensions": ["stage", "source", "owner"],
            },
            {
                "type": "executive_summary",
                "name": "Executive Summary",
                "description": "High-level overview of all key metrics",
                "sections": ["overview", "performance", "trends", "recommendations"],
            },
        ],
        "formats": [f.value for f in ReportFormat],
        "frequencies": [f.value for f in ScheduleFrequency],
        "delivery_channels": [c.value for c in DeliveryChannel],
        "date_range_types": [
            "yesterday",
            "last_7_days",
            "last_30_days",
            "last_month",
            "month_to_date",
            "quarter_to_date",
            "year_to_date",
            "custom",
        ],
    }
