# =============================================================================
# Stratum AI - Report Scheduling Service
# =============================================================================
"""
Handles scheduling and automatic execution of reports.

Features:
- Cron-based scheduling
- Next run time calculation
- Frequency-based scheduling (daily, weekly, monthly, etc.)
- Timezone-aware scheduling
- Automatic retry on failure
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reporting import (
    ExecutionStatus,
    ReportExecution,
    ReportFormat,
    ReportTemplate,
    ScheduledReport,
    ScheduleFrequency,
)
from app.services.reporting.delivery import DeliveryService
from app.services.reporting.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


# =============================================================================
# Cron Parser (Simple Implementation)
# =============================================================================


class CronParser:
    """
    Simple cron expression parser for custom schedules.

    Format: minute hour day_of_month month day_of_week
    Supports: *, specific values, ranges (1-5), steps (*/5)
    """

    @staticmethod
    def parse_field(field: str, min_val: int, max_val: int) -> list[int]:
        """Parse a single cron field into a list of valid values."""
        if field == "*":
            return list(range(min_val, max_val + 1))

        values = set()

        for part in field.split(","):
            if "/" in part:
                # Step values: */5 or 1-10/2
                base, step = part.split("/")
                step = int(step)
                if base == "*":
                    start, end = min_val, max_val
                elif "-" in base:
                    start, end = map(int, base.split("-"))
                else:
                    start = int(base)
                    end = max_val
                values.update(range(start, end + 1, step))
            elif "-" in part:
                # Range: 1-5
                start, end = map(int, part.split("-"))
                values.update(range(start, end + 1))
            else:
                # Single value
                values.add(int(part))

        return sorted(v for v in values if min_val <= v <= max_val)

    @classmethod
    def parse(cls, expression: str) -> dict[str, list[int]]:
        """
        Parse a cron expression.

        Returns dict with keys: minute, hour, day, month, weekday
        """
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        return {
            "minute": cls.parse_field(parts[0], 0, 59),
            "hour": cls.parse_field(parts[1], 0, 23),
            "day": cls.parse_field(parts[2], 1, 31),
            "month": cls.parse_field(parts[3], 1, 12),
            "weekday": cls.parse_field(parts[4], 0, 6),  # 0=Sunday
        }

    @classmethod
    def get_next_run(cls, expression: str, after: datetime) -> datetime:
        """Calculate the next run time after a given datetime."""
        parsed = cls.parse(expression)

        # Start from the next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search for next valid time (max 1 year ahead)
        max_iterations = 525600  # minutes in a year

        for _ in range(max_iterations):
            if (
                current.month in parsed["month"]
                and current.day in parsed["day"]
                and current.weekday() in [d % 7 for d in parsed["weekday"]]
                and current.hour in parsed["hour"]
                and current.minute in parsed["minute"]
            ):
                return current
            current += timedelta(minutes=1)

        raise ValueError(f"Could not find next run time for: {expression}")


# =============================================================================
# Report Scheduler
# =============================================================================


class ReportScheduler:
    """
    Manages scheduled report execution.

    Responsibilities:
    - Calculate next run times
    - Execute due reports
    - Handle retries and failures
    - Manage schedule lifecycle
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.report_generator = ReportGenerator(db, tenant_id)
        self.delivery_service = DeliveryService(db, tenant_id)

    # -------------------------------------------------------------------------
    # Schedule Management
    # -------------------------------------------------------------------------

    async def create_schedule(
        self,
        template_id: UUID,
        name: str,
        frequency: ScheduleFrequency,
        delivery_config: dict[str, Any],
        *,
        description: Optional[str] = None,
        timezone: str = "UTC",
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        hour: int = 8,
        minute: int = 0,
        cron_expression: Optional[str] = None,
        format_override: Optional[ReportFormat] = None,
        config_override: Optional[dict[str, Any]] = None,
        date_range_type: str = "last_30_days",
        delivery_channels: list[str] = None,
        created_by_user_id: Optional[int] = None,
    ) -> ScheduledReport:
        """Create a new scheduled report."""

        # Validate template exists
        template = await self.db.get(ReportTemplate, template_id)
        if not template or template.tenant_id != self.tenant_id:
            raise ValueError(f"Template not found: {template_id}")

        # Create schedule
        schedule = ScheduledReport(
            tenant_id=self.tenant_id,
            template_id=template_id,
            name=name,
            description=description,
            frequency=frequency,
            timezone=timezone,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            hour=hour,
            minute=minute,
            cron_expression=cron_expression,
            format_override=format_override,
            config_override=config_override,
            date_range_type=date_range_type,
            delivery_channels=delivery_channels or ["email"],
            delivery_config=delivery_config,
            created_by_user_id=created_by_user_id,
        )

        # Calculate initial next run time
        schedule.next_run_at = self.calculate_next_run(schedule)

        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(
            f"Created schedule {schedule.id} for template {template_id}, next run: {schedule.next_run_at}"
        )

        return schedule

    async def update_schedule(self, schedule_id: UUID, **updates) -> ScheduledReport:
        """Update an existing schedule."""
        schedule = await self.db.get(ScheduledReport, schedule_id)
        if not schedule or schedule.tenant_id != self.tenant_id:
            raise ValueError(f"Schedule not found: {schedule_id}")

        # Apply updates
        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        # Recalculate next run if schedule timing changed
        timing_fields = {
            "frequency",
            "day_of_week",
            "day_of_month",
            "hour",
            "minute",
            "cron_expression",
            "timezone",
        }
        if timing_fields & set(updates.keys()):
            schedule.next_run_at = self.calculate_next_run(schedule)

        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    async def pause_schedule(self, schedule_id: UUID) -> ScheduledReport:
        """Pause a schedule."""
        return await self.update_schedule(schedule_id, is_paused=True)

    async def resume_schedule(self, schedule_id: UUID) -> ScheduledReport:
        """Resume a paused schedule."""
        schedule = await self.db.get(ScheduledReport, schedule_id)
        if not schedule or schedule.tenant_id != self.tenant_id:
            raise ValueError(f"Schedule not found: {schedule_id}")

        schedule.is_paused = False
        schedule.next_run_at = self.calculate_next_run(schedule)

        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a schedule."""
        schedule = await self.db.get(ScheduledReport, schedule_id)
        if not schedule or schedule.tenant_id != self.tenant_id:
            return False

        await self.db.delete(schedule)
        await self.db.commit()

        return True

    # -------------------------------------------------------------------------
    # Next Run Calculation
    # -------------------------------------------------------------------------

    def calculate_next_run(
        self,
        schedule: ScheduledReport,
        after: Optional[datetime] = None,
    ) -> datetime:
        """Calculate the next run time for a schedule."""
        if after is None:
            after = datetime.utcnow()

        tz = ZoneInfo(schedule.timezone)
        local_now = after.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)

        if schedule.frequency == ScheduleFrequency.CUSTOM and schedule.cron_expression:
            # Use cron expression
            next_run = CronParser.get_next_run(schedule.cron_expression, local_now)
        else:
            # Calculate based on frequency
            next_run = self._calculate_frequency_next_run(schedule, local_now)

        # Convert back to UTC
        return next_run.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    def _calculate_frequency_next_run(
        self,
        schedule: ScheduledReport,
        local_now: datetime,
    ) -> datetime:
        """Calculate next run based on frequency setting."""
        target_time = time(schedule.hour, schedule.minute)
        tz = local_now.tzinfo

        # Start with today at the target time
        today_run = datetime.combine(local_now.date(), target_time).replace(tzinfo=tz)

        if schedule.frequency == ScheduleFrequency.DAILY:
            if local_now < today_run:
                return today_run
            return today_run + timedelta(days=1)

        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            target_day = schedule.day_of_week or 0  # Default Monday
            days_ahead = target_day - local_now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and local_now >= today_run):
                days_ahead += 7
            return datetime.combine(
                local_now.date() + timedelta(days=days_ahead), target_time
            ).replace(tzinfo=tz)

        elif schedule.frequency == ScheduleFrequency.BIWEEKLY:
            target_day = schedule.day_of_week or 0
            days_ahead = target_day - local_now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and local_now >= today_run):
                days_ahead += 14
            elif days_ahead >= 7:
                days_ahead -= 7
            return datetime.combine(
                local_now.date() + timedelta(days=days_ahead), target_time
            ).replace(tzinfo=tz)

        elif schedule.frequency == ScheduleFrequency.MONTHLY:
            target_day = schedule.day_of_month or 1

            # Handle last day of month (-1)
            if target_day == -1:
                next_month = local_now.replace(day=28) + timedelta(days=4)
                target_date = next_month - timedelta(days=next_month.day)
            else:
                # Try this month first
                try:
                    target_date = local_now.replace(day=target_day)
                except ValueError:
                    # Day doesn't exist this month (e.g., Feb 30)
                    next_month = local_now.replace(day=28) + timedelta(days=4)
                    target_date = next_month.replace(day=1) - timedelta(days=1)

            target_datetime = datetime.combine(target_date.date(), target_time).replace(tzinfo=tz)

            if local_now >= target_datetime:
                # Move to next month
                next_month = local_now.replace(day=28) + timedelta(days=4)
                if target_day == -1:
                    following_month = next_month.replace(day=28) + timedelta(days=4)
                    target_date = following_month - timedelta(days=following_month.day)
                else:
                    try:
                        target_date = next_month.replace(day=target_day)
                    except ValueError:
                        target_date = (next_month.replace(day=28) + timedelta(days=4)).replace(
                            day=1
                        ) - timedelta(days=1)
                target_datetime = datetime.combine(target_date.date(), target_time).replace(
                    tzinfo=tz
                )

            return target_datetime

        elif schedule.frequency == ScheduleFrequency.QUARTERLY:
            current_quarter = (local_now.month - 1) // 3
            quarter_start_months = [1, 4, 7, 10]

            # First day of next quarter
            next_quarter = (current_quarter + 1) % 4
            next_quarter_month = quarter_start_months[next_quarter]
            next_quarter_year = (
                local_now.year if next_quarter > current_quarter else local_now.year + 1
            )

            target_day = schedule.day_of_month or 1
            try:
                target_date = date(next_quarter_year, next_quarter_month, target_day)
            except ValueError:
                # Invalid day for month
                target_date = date(next_quarter_year, next_quarter_month, 1)

            return datetime.combine(target_date, target_time).replace(tzinfo=tz)

        # Default: tomorrow
        return today_run + timedelta(days=1)

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def get_due_schedules(
        self,
        limit: int = 50,
    ) -> list[ScheduledReport]:
        """Get schedules that are due for execution."""
        now = datetime.utcnow()

        query = (
            select(ScheduledReport)
            .options(selectinload(ScheduledReport.template))
            .where(
                and_(
                    ScheduledReport.tenant_id == self.tenant_id,
                    ScheduledReport.is_active == True,
                    ScheduledReport.is_paused == False,
                    ScheduledReport.next_run_at <= now,
                )
            )
            .order_by(ScheduledReport.next_run_at)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def execute_schedule(
        self,
        schedule: ScheduledReport,
        triggered_by_user_id: Optional[int] = None,
    ) -> ReportExecution:
        """Execute a scheduled report."""
        logger.info(f"Executing schedule {schedule.id}: {schedule.name}")

        # Determine date range
        from app.services.reporting.report_generator import ReportGenerator

        start_date, end_date = ReportGenerator.parse_date_range(
            schedule.date_range_type, datetime.utcnow().date()
        )

        # Determine format
        report_format = schedule.format_override or schedule.template.default_format

        # Merge config
        config = {**schedule.template.config}
        if schedule.config_override:
            config.update(schedule.config_override)

        try:
            # Generate report
            execution_result = await self.report_generator.generate_report(
                template_id=schedule.template_id,
                start_date=start_date,
                end_date=end_date,
                format=report_format,
                config_override=config,
                triggered_by_user_id=triggered_by_user_id,
                schedule_id=schedule.id,
                execution_type="scheduled",
            )

            execution_id = execution_result["execution_id"]

            # Deliver report
            await self.delivery_service.deliver_report(
                execution_id=execution_id,
                channels=schedule.delivery_channels,
                delivery_config=schedule.delivery_config,
            )

            # Update schedule
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = ExecutionStatus.COMPLETED
            schedule.run_count += 1
            schedule.next_run_at = self.calculate_next_run(schedule)

            await self.db.commit()

            # Get execution record
            execution = await self.db.get(ReportExecution, execution_id)

            logger.info(f"Schedule {schedule.id} completed successfully")

            return execution

        except Exception as e:
            logger.error(f"Schedule {schedule.id} failed: {e!s}")

            # Update schedule with failure
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = ExecutionStatus.FAILED
            schedule.failure_count += 1
            schedule.next_run_at = self.calculate_next_run(schedule)

            await self.db.commit()

            raise

    async def run_now(
        self,
        schedule_id: UUID,
        triggered_by_user_id: Optional[int] = None,
    ) -> ReportExecution:
        """Manually trigger a scheduled report to run immediately."""
        schedule = await self.db.get(
            ScheduledReport, schedule_id, options=[selectinload(ScheduledReport.template)]
        )
        if not schedule or schedule.tenant_id != self.tenant_id:
            raise ValueError(f"Schedule not found: {schedule_id}")

        return await self.execute_schedule(schedule, triggered_by_user_id)

    # -------------------------------------------------------------------------
    # Background Processing
    # -------------------------------------------------------------------------

    async def process_due_schedules(self) -> dict[str, Any]:
        """Process all due schedules. Called by background worker."""
        due_schedules = await self.get_due_schedules()

        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "errors": [],
        }

        for schedule in due_schedules:
            try:
                await self.execute_schedule(schedule)
                results["succeeded"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "schedule_id": str(schedule.id),
                        "name": schedule.name,
                        "error": str(e),
                    }
                )
            results["processed"] += 1

        return results

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    async def get_schedule(self, schedule_id: UUID) -> Optional[ScheduledReport]:
        """Get a schedule by ID."""
        schedule = await self.db.get(
            ScheduledReport, schedule_id, options=[selectinload(ScheduledReport.template)]
        )
        if schedule and schedule.tenant_id == self.tenant_id:
            return schedule
        return None

    async def list_schedules(
        self,
        *,
        is_active: Optional[bool] = None,
        template_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ScheduledReport], int]:
        """List schedules with filtering."""
        conditions = [ScheduledReport.tenant_id == self.tenant_id]

        if is_active is not None:
            conditions.append(ScheduledReport.is_active == is_active)
        if template_id:
            conditions.append(ScheduledReport.template_id == template_id)

        # Count query
        count_query = select(ScheduledReport).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Data query
        query = (
            select(ScheduledReport)
            .options(selectinload(ScheduledReport.template))
            .where(and_(*conditions))
            .order_by(ScheduledReport.next_run_at)
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        schedules = result.scalars().all()

        return schedules, total

    async def get_execution_history(
        self,
        schedule_id: UUID,
        limit: int = 20,
    ) -> list[ReportExecution]:
        """Get execution history for a schedule."""
        query = (
            select(ReportExecution)
            .where(
                and_(
                    ReportExecution.tenant_id == self.tenant_id,
                    ReportExecution.schedule_id == schedule_id,
                )
            )
            .order_by(ReportExecution.started_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()


# =============================================================================
# Scheduler Worker (Background Task)
# =============================================================================


class SchedulerWorker:
    """
    Background worker that processes scheduled reports.

    Run this in a separate process or as a Celery task.
    """

    def __init__(self, db_session_factory, check_interval: int = 60):
        self.db_session_factory = db_session_factory
        self.check_interval = check_interval
        self._running = False

    async def start(self):
        """Start the scheduler worker."""
        self._running = True
        logger.info("Scheduler worker started")

        while self._running:
            try:
                await self._process_all_tenants()
            except Exception as e:
                logger.error(f"Scheduler worker error: {e!s}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the scheduler worker."""
        self._running = False
        logger.info("Scheduler worker stopped")

    async def _process_all_tenants(self):
        """Process schedules for all tenants."""
        async with self.db_session_factory() as db:
            # Get all tenant IDs with active schedules
            query = (
                select(ScheduledReport.tenant_id)
                .where(
                    and_(
                        ScheduledReport.is_active == True,
                        ScheduledReport.is_paused == False,
                        ScheduledReport.next_run_at <= datetime.utcnow(),
                    )
                )
                .distinct()
            )

            result = await db.execute(query)
            tenant_ids = result.scalars().all()

        for tenant_id in tenant_ids:
            async with self.db_session_factory() as db:
                scheduler = ReportScheduler(db, tenant_id)
                results = await scheduler.process_due_schedules()

                if results["processed"] > 0:
                    logger.info(
                        f"Tenant {tenant_id}: processed {results['processed']} schedules, "
                        f"{results['succeeded']} succeeded, {results['failed']} failed"
                    )
