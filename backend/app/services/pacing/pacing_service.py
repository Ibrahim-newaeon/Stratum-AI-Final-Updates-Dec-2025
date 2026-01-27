# =============================================================================
# Stratum AI - Pacing Service
# =============================================================================
"""
Pacing service for calculating target progress and projections.

Features:
- MTD actual vs target calculations
- Pacing percentage and completion tracking
- EOM projections with confidence intervals
- Gap analysis and daily needed calculations
- Pacing summary snapshots
"""

from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.pacing import (
    DailyKPI,
    PacingSummary,
    Target,
    TargetMetric,
    TargetPeriod,
)
from app.services.pacing.forecasting import ForecastingService

logger = get_logger(__name__)


class PacingService:
    """
    Service for calculating pacing metrics and projections.

    Provides:
    - Real-time pacing calculations
    - Target progress tracking
    - EOM projections using forecasting service
    - Pacing summary snapshots
    """

    # Pacing thresholds
    ON_TRACK_MIN = 0.9  # Within 90% of expected pace
    ON_TRACK_MAX = 1.1  # Within 110% of expected pace
    AT_RISK_MIN = 0.75  # Between 75-90% or 110-125%
    AT_RISK_MAX = 1.25

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.forecasting = ForecastingService(db, tenant_id)

    async def get_target_pacing(
        self,
        target_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Calculate pacing for a specific target.

        Args:
            target_id: Target UUID
            as_of_date: Date to calculate pacing for (default: today)

        Returns:
            Pacing metrics including MTD, projections, and status
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Load target
        result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.id == target_id,
                    Target.tenant_id == self.tenant_id,
                )
            )
        )
        target = result.scalar_one_or_none()

        if not target:
            return {"status": "error", "message": "Target not found"}

        if not target.is_active:
            return {"status": "error", "message": "Target is inactive"}

        # Calculate period metrics
        period_days = (target.period_end - target.period_start).days + 1
        days_elapsed = max(0, (as_of_date - target.period_start).days + 1)
        days_remaining = max(0, (target.period_end - as_of_date).days)

        # Handle dates outside period
        if as_of_date < target.period_start:
            return {
                "status": "not_started",
                "message": "Target period has not started",
                "target_id": str(target.id),
                "period_start": target.period_start.isoformat(),
            }

        if as_of_date > target.period_end:
            return {
                "status": "ended",
                "message": "Target period has ended",
                "target_id": str(target.id),
                "period_end": target.period_end.isoformat(),
            }

        # Get MTD actual
        mtd_actual = await self._get_mtd_actual(
            target.metric_type,
            target.platform,
            target.campaign_id,
            target.period_start,
            as_of_date,
        )

        # Calculate expected (pro-rated target)
        progress_pct = days_elapsed / period_days
        mtd_expected = target.target_value * progress_pct

        # Pacing percentage
        pacing_pct = (mtd_actual / mtd_expected * 100) if mtd_expected > 0 else 0
        completion_pct = (mtd_actual / target.target_value * 100) if target.target_value > 0 else 0

        # Get forecast for remaining period
        projected_eom = mtd_actual
        projected_lower = mtd_actual
        projected_upper = mtd_actual

        if days_remaining > 0:
            forecast = await self.forecasting.forecast_metric(
                target.metric_type,
                forecast_days=days_remaining,
                platform=target.platform,
                campaign_id=target.campaign_id,
                as_of_date=as_of_date,
            )

            if forecast.get("status") == "success":
                remaining_forecast = sum(
                    f["point_forecast"] for f in forecast.get("daily_forecasts", [])
                )
                remaining_lower = sum(f["lower_bound"] for f in forecast.get("daily_forecasts", []))
                remaining_upper = sum(f["upper_bound"] for f in forecast.get("daily_forecasts", []))

                projected_eom = mtd_actual + remaining_forecast
                projected_lower = mtd_actual + remaining_lower
                projected_upper = mtd_actual + remaining_upper
            else:
                # Fallback: linear projection
                daily_avg = mtd_actual / days_elapsed if days_elapsed > 0 else 0
                remaining_forecast = daily_avg * days_remaining
                projected_eom = mtd_actual + remaining_forecast
                projected_lower = projected_eom * 0.8
                projected_upper = projected_eom * 1.2

        # Gap analysis
        gap_to_target = target.target_value - projected_eom
        gap_pct = (gap_to_target / target.target_value * 100) if target.target_value > 0 else 0

        # Daily metrics
        daily_average = mtd_actual / days_elapsed if days_elapsed > 0 else 0
        daily_needed = (
            (target.target_value - mtd_actual) / days_remaining if days_remaining > 0 else 0
        )

        # Status determination
        pacing_ratio = pacing_pct / 100
        on_track = self.ON_TRACK_MIN <= pacing_ratio <= self.ON_TRACK_MAX
        at_risk = not on_track and (self.AT_RISK_MIN <= pacing_ratio <= self.AT_RISK_MAX)
        will_miss = pacing_ratio < self.AT_RISK_MIN or pacing_ratio > self.AT_RISK_MAX

        # Determine if projected to miss
        projection_gap_pct = abs(gap_pct)
        will_miss = will_miss or projection_gap_pct > target.critical_threshold_pct
        at_risk = at_risk or (
            target.warning_threshold_pct < projection_gap_pct <= target.critical_threshold_pct
        )

        return {
            "status": "success",
            "target_id": str(target.id),
            "target_name": target.name,
            "metric_type": target.metric_type.value,
            "as_of_date": as_of_date.isoformat(),
            "period": {
                "type": target.period_type.value,
                "start": target.period_start.isoformat(),
                "end": target.period_end.isoformat(),
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "days_total": period_days,
                "progress_pct": round(progress_pct * 100, 1),
            },
            "scope": {
                "platform": target.platform,
                "campaign_id": target.campaign_id,
            },
            "target_value": target.target_value,
            "mtd": {
                "actual": round(mtd_actual, 2),
                "expected": round(mtd_expected, 2),
                "gap": round(mtd_actual - mtd_expected, 2),
            },
            "pacing": {
                "pct": round(pacing_pct, 1),
                "completion_pct": round(completion_pct, 1),
            },
            "projection": {
                "eom": round(projected_eom, 2),
                "lower": round(projected_lower, 2),
                "upper": round(projected_upper, 2),
            },
            "gap_analysis": {
                "gap_to_target": round(gap_to_target, 2),
                "gap_pct": round(gap_pct, 1),
            },
            "daily": {
                "average": round(daily_average, 2),
                "needed": round(daily_needed, 2),
            },
            "status_flags": {
                "on_track": on_track,
                "at_risk": at_risk,
                "will_miss": will_miss,
            },
            "thresholds": {
                "warning_pct": target.warning_threshold_pct,
                "critical_pct": target.critical_threshold_pct,
            },
        }

    async def get_all_targets_pacing(
        self,
        as_of_date: Optional[date] = None,
        metric_type: Optional[TargetMetric] = None,
        platform: Optional[str] = None,
        active_only: bool = True,
    ) -> dict[str, Any]:
        """
        Get pacing for all targets.

        Args:
            as_of_date: Date to calculate pacing for
            metric_type: Optional filter by metric type
            platform: Optional filter by platform
            active_only: Only include active targets

        Returns:
            List of pacing results for all matching targets
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Build query
        conditions = [Target.tenant_id == self.tenant_id]

        if active_only:
            conditions.append(Target.is_active == True)

        if metric_type:
            conditions.append(Target.metric_type == metric_type)

        if platform:
            conditions.append(Target.platform == platform)

        # Filter to targets that include current date
        conditions.append(Target.period_start <= as_of_date)
        conditions.append(Target.period_end >= as_of_date)

        result = await self.db.execute(select(Target).where(and_(*conditions)))
        targets = result.scalars().all()

        # Calculate pacing for each target
        pacing_results = []
        summary = {
            "on_track": 0,
            "at_risk": 0,
            "will_miss": 0,
            "total": len(targets),
        }

        for target in targets:
            pacing = await self.get_target_pacing(target.id, as_of_date)
            pacing_results.append(pacing)

            if pacing.get("status") == "success":
                flags = pacing.get("status_flags", {})
                if flags.get("will_miss"):
                    summary["will_miss"] += 1
                elif flags.get("at_risk"):
                    summary["at_risk"] += 1
                elif flags.get("on_track"):
                    summary["on_track"] += 1

        return {
            "status": "success",
            "as_of_date": as_of_date.isoformat(),
            "summary": summary,
            "targets": pacing_results,
        }

    async def create_pacing_snapshot(
        self,
        target_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> Optional[PacingSummary]:
        """
        Create a pacing summary snapshot for a target.

        Args:
            target_id: Target UUID
            as_of_date: Date for snapshot

        Returns:
            Created PacingSummary or None if failed
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get current pacing
        pacing = await self.get_target_pacing(target_id, as_of_date)

        if pacing.get("status") != "success":
            logger.warning(
                f"Cannot create snapshot for target {target_id}: {pacing.get('message')}"
            )
            return None

        # Check for existing snapshot
        result = await self.db.execute(
            select(PacingSummary).where(
                and_(
                    PacingSummary.target_id == target_id,
                    PacingSummary.snapshot_date == as_of_date,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing snapshot
            existing.period_start = date.fromisoformat(pacing["period"]["start"])
            existing.period_end = date.fromisoformat(pacing["period"]["end"])
            existing.days_elapsed = pacing["period"]["days_elapsed"]
            existing.days_remaining = pacing["period"]["days_remaining"]
            existing.days_total = pacing["period"]["days_total"]
            existing.target_value = pacing["target_value"]
            existing.mtd_actual = pacing["mtd"]["actual"]
            existing.mtd_expected = pacing["mtd"]["expected"]
            existing.pacing_pct = pacing["pacing"]["pct"]
            existing.completion_pct = pacing["pacing"]["completion_pct"]
            existing.projected_eom = pacing["projection"]["eom"]
            existing.projected_eom_lower = pacing["projection"]["lower"]
            existing.projected_eom_upper = pacing["projection"]["upper"]
            existing.gap_to_target = pacing["gap_analysis"]["gap_to_target"]
            existing.gap_pct = pacing["gap_analysis"]["gap_pct"]
            existing.daily_needed = pacing["daily"]["needed"]
            existing.daily_average = pacing["daily"]["average"]
            existing.on_track = pacing["status_flags"]["on_track"]
            existing.at_risk = pacing["status_flags"]["at_risk"]
            existing.will_miss = pacing["status_flags"]["will_miss"]
            existing.updated_at = datetime.utcnow()

            await self.db.commit()
            return existing

        # Create new snapshot
        summary = PacingSummary(
            tenant_id=self.tenant_id,
            target_id=target_id,
            snapshot_date=as_of_date,
            period_start=date.fromisoformat(pacing["period"]["start"]),
            period_end=date.fromisoformat(pacing["period"]["end"]),
            days_elapsed=pacing["period"]["days_elapsed"],
            days_remaining=pacing["period"]["days_remaining"],
            days_total=pacing["period"]["days_total"],
            target_value=pacing["target_value"],
            mtd_actual=pacing["mtd"]["actual"],
            mtd_expected=pacing["mtd"]["expected"],
            pacing_pct=pacing["pacing"]["pct"],
            completion_pct=pacing["pacing"]["completion_pct"],
            projected_eom=pacing["projection"]["eom"],
            projected_eom_lower=pacing["projection"]["lower"],
            projected_eom_upper=pacing["projection"]["upper"],
            gap_to_target=pacing["gap_analysis"]["gap_to_target"],
            gap_pct=pacing["gap_analysis"]["gap_pct"],
            daily_needed=pacing["daily"]["needed"],
            daily_average=pacing["daily"]["average"],
            on_track=pacing["status_flags"]["on_track"],
            at_risk=pacing["status_flags"]["at_risk"],
            will_miss=pacing["status_flags"]["will_miss"],
        )

        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)

        return summary

    async def create_all_snapshots(
        self,
        as_of_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Create pacing snapshots for all active targets.

        Args:
            as_of_date: Date for snapshots

        Returns:
            Summary of created snapshots
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get all active targets
        result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.tenant_id == self.tenant_id,
                    Target.is_active == True,
                    Target.period_start <= as_of_date,
                    Target.period_end >= as_of_date,
                )
            )
        )
        targets = result.scalars().all()

        created = 0
        failed = 0

        for target in targets:
            snapshot = await self.create_pacing_snapshot(target.id, as_of_date)
            if snapshot:
                created += 1
            else:
                failed += 1

        return {
            "status": "success",
            "as_of_date": as_of_date.isoformat(),
            "targets_processed": len(targets),
            "snapshots_created": created,
            "snapshots_failed": failed,
        }

    async def get_pacing_history(
        self,
        target_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """
        Get historical pacing snapshots for a target.

        Args:
            target_id: Target UUID
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of historical pacing snapshots
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        result = await self.db.execute(
            select(PacingSummary)
            .where(
                and_(
                    PacingSummary.target_id == target_id,
                    PacingSummary.snapshot_date >= start_date,
                    PacingSummary.snapshot_date <= end_date,
                )
            )
            .order_by(PacingSummary.snapshot_date)
        )
        snapshots = result.scalars().all()

        return [
            {
                "date": s.snapshot_date.isoformat(),
                "mtd_actual": s.mtd_actual,
                "mtd_expected": s.mtd_expected,
                "pacing_pct": s.pacing_pct,
                "completion_pct": s.completion_pct,
                "projected_eom": s.projected_eom,
                "gap_to_target": s.gap_to_target,
                "on_track": s.on_track,
                "at_risk": s.at_risk,
                "will_miss": s.will_miss,
            }
            for s in snapshots
        ]

    async def _get_mtd_actual(
        self,
        metric: TargetMetric,
        platform: Optional[str],
        campaign_id: Optional[str],
        period_start: date,
        as_of_date: date,
    ) -> float:
        """Get month-to-date actual for a metric."""
        conditions = [
            DailyKPI.tenant_id == self.tenant_id,
            DailyKPI.date >= period_start,
            DailyKPI.date <= as_of_date,
        ]

        if platform:
            conditions.append(DailyKPI.platform == platform)
        else:
            conditions.append(DailyKPI.platform.is_(None))

        if campaign_id:
            conditions.append(DailyKPI.campaign_id == campaign_id)
        else:
            conditions.append(DailyKPI.campaign_id.is_(None))

        result = await self.db.execute(select(DailyKPI).where(and_(*conditions)))
        records = result.scalars().all()

        total = 0.0
        for r in records:
            value = self._get_metric_value(r, metric)
            if value is not None:
                total += value

        return total

    def _get_metric_value(self, record: DailyKPI, metric: TargetMetric) -> Optional[float]:
        """Extract metric value from DailyKPI record."""
        if metric == TargetMetric.SPEND:
            return (record.spend_cents or 0) / 100
        elif metric == TargetMetric.REVENUE:
            return (record.revenue_cents or 0) / 100
        elif metric == TargetMetric.ROAS:
            return record.roas
        elif metric == TargetMetric.CONVERSIONS:
            return record.conversions
        elif metric == TargetMetric.LEADS:
            return record.leads + record.crm_leads
        elif metric == TargetMetric.PIPELINE_VALUE:
            return (record.crm_pipeline_cents or 0) / 100
        elif metric == TargetMetric.WON_REVENUE:
            return (record.crm_won_revenue_cents or 0) / 100
        elif metric == TargetMetric.CPA:
            return (record.cpa_cents or 0) / 100
        elif metric == TargetMetric.CPL:
            return (record.cpl_cents or 0) / 100
        return None


# =============================================================================
# Target CRUD Operations
# =============================================================================


class TargetService:
    """Service for managing targets (CRUD operations)."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def create_target(
        self,
        name: str,
        metric_type: TargetMetric,
        target_value: float,
        period_start: date,
        period_end: date,
        period_type: TargetPeriod = TargetPeriod.MONTHLY,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        description: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        warning_threshold_pct: float = 10.0,
        critical_threshold_pct: float = 20.0,
        created_by_user_id: Optional[int] = None,
    ) -> Target:
        """Create a new target."""
        # Convert monetary values to cents if applicable
        target_value_cents = None
        if metric_type in [
            TargetMetric.SPEND,
            TargetMetric.REVENUE,
            TargetMetric.PIPELINE_VALUE,
            TargetMetric.WON_REVENUE,
        ]:
            target_value_cents = int(target_value * 100)

        target = Target(
            tenant_id=self.tenant_id,
            name=name,
            description=description,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            platform=platform,
            campaign_id=campaign_id,
            metric_type=metric_type,
            target_value=target_value,
            target_value_cents=target_value_cents,
            min_value=min_value,
            max_value=max_value,
            warning_threshold_pct=warning_threshold_pct,
            critical_threshold_pct=critical_threshold_pct,
            created_by_user_id=created_by_user_id,
        )

        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)

        logger.info(f"Created target {target.id}: {name} ({metric_type.value})")
        return target

    async def get_target(self, target_id: UUID) -> Optional[Target]:
        """Get a target by ID."""
        result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.id == target_id,
                    Target.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_targets(
        self,
        active_only: bool = True,
        metric_type: Optional[TargetMetric] = None,
        platform: Optional[str] = None,
        period_type: Optional[TargetPeriod] = None,
    ) -> list[Target]:
        """List targets with optional filters."""
        conditions = [Target.tenant_id == self.tenant_id]

        if active_only:
            conditions.append(Target.is_active == True)

        if metric_type:
            conditions.append(Target.metric_type == metric_type)

        if platform:
            conditions.append(Target.platform == platform)

        if period_type:
            conditions.append(Target.period_type == period_type)

        result = await self.db.execute(
            select(Target).where(and_(*conditions)).order_by(Target.period_start.desc())
        )
        return list(result.scalars().all())

    async def update_target(
        self,
        target_id: UUID,
        **kwargs,
    ) -> Optional[Target]:
        """Update a target."""
        target = await self.get_target(target_id)
        if not target:
            return None

        # Update allowed fields
        allowed_fields = [
            "name",
            "description",
            "target_value",
            "min_value",
            "max_value",
            "warning_threshold_pct",
            "critical_threshold_pct",
            "is_active",
            "notify_slack",
            "notify_email",
            "notify_whatsapp",
            "notification_recipients",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(target, field, value)

        # Update target_value_cents if target_value changed
        if "target_value" in kwargs:
            if target.metric_type in [
                TargetMetric.SPEND,
                TargetMetric.REVENUE,
                TargetMetric.PIPELINE_VALUE,
                TargetMetric.WON_REVENUE,
            ]:
                target.target_value_cents = int(target.target_value * 100)

        target.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(target)

        return target

    async def delete_target(self, target_id: UUID) -> bool:
        """Delete a target (soft delete by setting inactive)."""
        target = await self.get_target(target_id)
        if not target:
            return False

        target.is_active = False
        target.updated_at = datetime.utcnow()
        await self.db.commit()

        return True

    async def get_current_targets(
        self,
        metric_type: Optional[TargetMetric] = None,
        platform: Optional[str] = None,
    ) -> list[Target]:
        """Get targets that are currently active (period includes today)."""
        today = date.today()

        conditions = [
            Target.tenant_id == self.tenant_id,
            Target.is_active == True,
            Target.period_start <= today,
            Target.period_end >= today,
        ]

        if metric_type:
            conditions.append(Target.metric_type == metric_type)

        if platform:
            conditions.append(Target.platform == platform)

        result = await self.db.execute(select(Target).where(and_(*conditions)))
        return list(result.scalars().all())
