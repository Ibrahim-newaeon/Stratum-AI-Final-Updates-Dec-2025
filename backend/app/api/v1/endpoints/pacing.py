# =============================================================================
# Stratum AI - Pacing & Forecasting API Endpoints
# =============================================================================
"""
API endpoints for targets, pacing, and forecasting.

Endpoints:
- Targets: CRUD operations for spend/revenue/ROAS targets
- Pacing: Real-time pacing calculations and projections
- Forecasts: EWMA-based metric forecasting
- Alerts: Pacing alert management
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import User
from app.models.pacing import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    TargetMetric,
    TargetPeriod,
)
from app.services.pacing import (
    ForecastingService,
    PacingAlertService,
    PacingService,
    TargetService,
)
from app.tenancy.deps import get_current_user, get_db

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class TargetCreate(BaseModel):
    """Schema for creating a new target."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metric_type: TargetMetric
    target_value: float = Field(..., gt=0)
    period_type: TargetPeriod = TargetPeriod.MONTHLY
    period_start: date
    period_end: date
    platform: Optional[str] = None
    campaign_id: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    warning_threshold_pct: float = Field(default=10.0, ge=0, le=100)
    critical_threshold_pct: float = Field(default=20.0, ge=0, le=100)
    notify_slack: bool = True
    notify_email: bool = True
    notify_whatsapp: bool = False
    notification_recipients: Optional[list[str]] = None


class TargetUpdate(BaseModel):
    """Schema for updating a target."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_value: Optional[float] = Field(None, gt=0)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    warning_threshold_pct: Optional[float] = Field(None, ge=0, le=100)
    critical_threshold_pct: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    notify_slack: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    notification_recipients: Optional[list[str]] = None


class TargetResponse(BaseModel):
    """Response schema for a target."""

    id: UUID
    name: str
    description: Optional[str]
    metric_type: str
    target_value: float
    period_type: str
    period_start: date
    period_end: date
    platform: Optional[str]
    campaign_id: Optional[str]
    min_value: Optional[float]
    max_value: Optional[float]
    warning_threshold_pct: float
    critical_threshold_pct: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ForecastRequest(BaseModel):
    """Request schema for forecasting."""

    metric_type: TargetMetric
    forecast_days: int = Field(default=30, ge=1, le=90)
    platform: Optional[str] = None
    campaign_id: Optional[str] = None
    as_of_date: Optional[date] = None


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    pass


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""

    resolution_notes: Optional[str] = None


class AlertDismiss(BaseModel):
    """Schema for dismissing an alert."""

    reason: Optional[str] = None


# =============================================================================
# Target Endpoints
# =============================================================================


@router.post("/targets", response_model=dict[str, Any])
async def create_target(
    target_data: TargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Create a new target.

    Targets define goals for metrics like spend, revenue, or ROAS
    over a specific period (monthly, quarterly, etc.).
    """
    service = TargetService(db, current_user.tenant_id)

    target = await service.create_target(
        name=target_data.name,
        description=target_data.description,
        metric_type=target_data.metric_type,
        target_value=target_data.target_value,
        period_type=target_data.period_type,
        period_start=target_data.period_start,
        period_end=target_data.period_end,
        platform=target_data.platform,
        campaign_id=target_data.campaign_id,
        min_value=target_data.min_value,
        max_value=target_data.max_value,
        warning_threshold_pct=target_data.warning_threshold_pct,
        critical_threshold_pct=target_data.critical_threshold_pct,
        created_by_user_id=current_user.id,
    )

    return {
        "status": "success",
        "message": "Target created successfully",
        "target": {
            "id": str(target.id),
            "name": target.name,
            "metric_type": target.metric_type.value,
            "target_value": target.target_value,
            "period_start": target.period_start.isoformat(),
            "period_end": target.period_end.isoformat(),
        },
    }


@router.get("/targets", response_model=dict[str, Any])
async def list_targets(
    active_only: bool = Query(True, description="Only show active targets"),
    metric_type: Optional[TargetMetric] = Query(None, description="Filter by metric type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    period_type: Optional[TargetPeriod] = Query(None, description="Filter by period type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all targets with optional filters."""
    service = TargetService(db, current_user.tenant_id)

    targets = await service.list_targets(
        active_only=active_only,
        metric_type=metric_type,
        platform=platform,
        period_type=period_type,
    )

    return {
        "status": "success",
        "count": len(targets),
        "targets": [
            {
                "id": str(t.id),
                "name": t.name,
                "metric_type": t.metric_type.value,
                "target_value": t.target_value,
                "period_type": t.period_type.value,
                "period_start": t.period_start.isoformat(),
                "period_end": t.period_end.isoformat(),
                "platform": t.platform,
                "campaign_id": t.campaign_id,
                "is_active": t.is_active,
            }
            for t in targets
        ],
    }


@router.get("/targets/{target_id}", response_model=dict[str, Any])
async def get_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific target by ID."""
    service = TargetService(db, current_user.tenant_id)
    target = await service.get_target(target_id)

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    return {
        "status": "success",
        "target": {
            "id": str(target.id),
            "name": target.name,
            "description": target.description,
            "metric_type": target.metric_type.value,
            "target_value": target.target_value,
            "target_value_cents": target.target_value_cents,
            "period_type": target.period_type.value,
            "period_start": target.period_start.isoformat(),
            "period_end": target.period_end.isoformat(),
            "platform": target.platform,
            "campaign_id": target.campaign_id,
            "min_value": target.min_value,
            "max_value": target.max_value,
            "warning_threshold_pct": target.warning_threshold_pct,
            "critical_threshold_pct": target.critical_threshold_pct,
            "is_active": target.is_active,
            "notify_slack": target.notify_slack,
            "notify_email": target.notify_email,
            "notify_whatsapp": target.notify_whatsapp,
            "notification_recipients": target.notification_recipients,
            "created_at": target.created_at.isoformat(),
            "updated_at": target.updated_at.isoformat(),
        },
    }


@router.patch("/targets/{target_id}", response_model=dict[str, Any])
async def update_target(
    target_id: UUID,
    target_data: TargetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a target."""
    service = TargetService(db, current_user.tenant_id)

    target = await service.update_target(
        target_id,
        **target_data.model_dump(exclude_unset=True),
    )

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    return {
        "status": "success",
        "message": "Target updated successfully",
        "target": {
            "id": str(target.id),
            "name": target.name,
            "target_value": target.target_value,
            "is_active": target.is_active,
        },
    }


@router.delete("/targets/{target_id}", response_model=dict[str, Any])
async def delete_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete (deactivate) a target."""
    service = TargetService(db, current_user.tenant_id)
    success = await service.delete_target(target_id)

    if not success:
        raise HTTPException(status_code=404, detail="Target not found")

    return {
        "status": "success",
        "message": "Target deleted successfully",
    }


# =============================================================================
# Pacing Endpoints
# =============================================================================


@router.get("/pacing/target/{target_id}", response_model=dict[str, Any])
async def get_target_pacing(
    target_id: UUID,
    as_of_date: Optional[date] = Query(None, description="Date to calculate pacing for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get pacing metrics for a specific target.

    Returns MTD actual vs expected, pacing percentage, EOM projections,
    and status flags (on_track, at_risk, will_miss).
    """
    service = PacingService(db, current_user.tenant_id)
    pacing = await service.get_target_pacing(target_id, as_of_date)

    if pacing.get("status") == "error":
        raise HTTPException(status_code=404, detail=pacing.get("message"))

    return pacing


@router.get("/pacing/all", response_model=dict[str, Any])
async def get_all_pacing(
    as_of_date: Optional[date] = Query(None, description="Date to calculate pacing for"),
    metric_type: Optional[TargetMetric] = Query(None, description="Filter by metric type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get pacing for all active targets.

    Returns a summary of targets on track, at risk, and will miss,
    along with individual pacing details for each target.
    """
    service = PacingService(db, current_user.tenant_id)
    return await service.get_all_targets_pacing(
        as_of_date=as_of_date,
        metric_type=metric_type,
        platform=platform,
    )


@router.get("/pacing/history/{target_id}", response_model=dict[str, Any])
async def get_pacing_history(
    target_id: UUID,
    start_date: Optional[date] = Query(None, description="Start of date range"),
    end_date: Optional[date] = Query(None, description="End of date range"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get historical pacing snapshots for a target.

    Returns daily pacing snapshots for trend analysis.
    """
    service = PacingService(db, current_user.tenant_id)
    history = await service.get_pacing_history(target_id, start_date, end_date)

    return {
        "status": "success",
        "target_id": str(target_id),
        "count": len(history),
        "history": history,
    }


@router.post("/pacing/snapshot", response_model=dict[str, Any])
async def create_pacing_snapshots(
    as_of_date: Optional[date] = Query(None, description="Date for snapshots"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Create pacing snapshots for all active targets.

    Used for historical trend tracking. Should be run daily via cron.
    """
    service = PacingService(db, current_user.tenant_id)
    return await service.create_all_snapshots(as_of_date)


# =============================================================================
# Forecast Endpoints
# =============================================================================


@router.post("/forecast", response_model=dict[str, Any])
async def create_forecast(
    request: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a forecast for a metric.

    Uses EWMA (Exponentially Weighted Moving Average) with day-of-week
    seasonality adjustment. Returns daily point forecasts with confidence
    intervals.
    """
    service = ForecastingService(db, current_user.tenant_id)

    forecast = await service.forecast_metric(
        metric=request.metric_type,
        forecast_days=request.forecast_days,
        platform=request.platform,
        campaign_id=request.campaign_id,
        as_of_date=request.as_of_date,
    )

    return forecast


@router.get("/forecast/eom", response_model=dict[str, Any])
async def get_eom_forecast(
    metric_type: TargetMetric = Query(..., description="Metric to forecast"),
    platform: Optional[str] = Query(None, description="Platform filter"),
    campaign_id: Optional[str] = Query(None, description="Campaign filter"),
    month: Optional[date] = Query(None, description="Month to forecast (default: current)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get end-of-month forecast for a metric.

    Returns MTD actual, remaining forecast, and projected EOM value
    with confidence intervals.
    """
    service = ForecastingService(db, current_user.tenant_id)

    return await service.forecast_eom(
        metric=metric_type,
        platform=platform,
        campaign_id=campaign_id,
        month=month,
    )


# =============================================================================
# Alert Endpoints
# =============================================================================


@router.get("/alerts", response_model=dict[str, Any])
async def get_alerts(
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by type"),
    target_id: Optional[UUID] = Query(None, description="Filter by target"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get alerts with optional filters."""
    service = PacingAlertService(db, current_user.tenant_id)

    # Currently returns active alerts for all status filters.
    # Non-active status filtering (resolved, dismissed) can be added
    # when PacingAlertService supports those query modes.
    alerts = await service.get_active_alerts(
        target_id=target_id,
        severity=severity,
        alert_type=alert_type,
    )

    return {
        "status": "success",
        "count": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "target_id": str(a.target_id) if a.target_id else None,
                "alert_type": a.alert_type.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "title": a.title,
                "message": a.message,
                "pacing_date": a.pacing_date.isoformat(),
                "current_value": a.current_value,
                "target_value": a.target_value,
                "projected_value": a.projected_value,
                "deviation_pct": a.deviation_pct,
                "days_remaining": a.days_remaining,
                "platform": a.platform,
                "campaign_id": a.campaign_id,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


@router.get("/alerts/summary", response_model=dict[str, Any])
async def get_alert_summary(
    start_date: Optional[date] = Query(None, description="Start of period"),
    end_date: Optional[date] = Query(None, description="End of period"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get alert summary statistics for a time period."""
    service = PacingAlertService(db, current_user.tenant_id)
    return await service.get_alert_summary(start_date, end_date)


@router.post("/alerts/check", response_model=dict[str, Any])
async def check_all_alerts(
    as_of_date: Optional[date] = Query(None, description="Date to check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check all targets for alert conditions.

    Creates new alerts for any targets that are underpacing, overpacing,
    or at risk of missing their targets.
    """
    service = PacingAlertService(db, current_user.tenant_id)
    return await service.check_all_targets(as_of_date)


@router.post("/alerts/{alert_id}/acknowledge", response_model=dict[str, Any])
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Acknowledge an alert."""
    service = PacingAlertService(db, current_user.tenant_id)
    alert = await service.acknowledge_alert(alert_id, current_user.id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "status": "success",
        "message": "Alert acknowledged",
        "alert_id": str(alert.id),
    }


@router.post("/alerts/{alert_id}/resolve", response_model=dict[str, Any])
async def resolve_alert(
    alert_id: UUID,
    request: AlertResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Resolve an alert."""
    service = PacingAlertService(db, current_user.tenant_id)
    alert = await service.resolve_alert(
        alert_id,
        current_user.id,
        request.resolution_notes,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "status": "success",
        "message": "Alert resolved",
        "alert_id": str(alert.id),
    }


@router.post("/alerts/{alert_id}/dismiss", response_model=dict[str, Any])
async def dismiss_alert(
    alert_id: UUID,
    request: AlertDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Dismiss an alert (false positive or not actionable)."""
    service = PacingAlertService(db, current_user.tenant_id)
    alert = await service.dismiss_alert(
        alert_id,
        current_user.id,
        request.reason,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "status": "success",
        "message": "Alert dismissed",
        "alert_id": str(alert.id),
    }


@router.post("/alerts/check-cliff/{target_id}", response_model=dict[str, Any])
async def check_pacing_cliff(
    target_id: UUID,
    lookback_days: int = Query(7, ge=3, le=30, description="Days to look back"),
    drop_threshold_pct: float = Query(30.0, ge=10, le=90, description="Drop threshold %"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check for sudden performance drops (pacing cliff).

    Compares recent day to lookback average and creates alert if
    drop exceeds threshold.
    """
    service = PacingAlertService(db, current_user.tenant_id)
    alert = await service.check_pacing_cliff(
        target_id,
        lookback_days=lookback_days,
        drop_threshold_pct=drop_threshold_pct,
    )

    if alert:
        return {
            "status": "cliff_detected",
            "alert_id": str(alert.id),
            "message": alert.message,
        }

    return {
        "status": "no_cliff",
        "message": "No significant performance drop detected",
    }
