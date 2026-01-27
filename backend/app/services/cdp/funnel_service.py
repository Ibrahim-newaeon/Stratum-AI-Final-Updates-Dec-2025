# =============================================================================
# Stratum AI - CDP Funnel Service
# =============================================================================
"""
Funnel analysis service for CDP.

Provides functionality for:
- Funnel definition and CRUD
- Funnel computation (step-by-step conversion analysis)
- Profile journey tracking
- Conversion rate analytics
"""

import re
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cdp import (
    CDPEvent,
    CDPFunnel,
    CDPFunnelEntry,
    CDPProfile,
    FunnelStatus,
)

logger = structlog.get_logger()


class FunnelStepEvaluator:
    """
    Evaluates funnel step conditions against profile events.
    """

    async def check_step_completion(
        self,
        profile_id: UUID,
        step: dict[str, Any],
        events: list[CDPEvent],
        after_time: Optional[datetime] = None,
        before_time: Optional[datetime] = None,
    ) -> tuple[bool, Optional[datetime]]:
        """
        Check if a profile completed a funnel step.

        Returns:
            (completed: bool, completion_time: Optional[datetime])
        """
        event_name = step.get("event_name")
        conditions = step.get("conditions", [])

        for event in events:
            # Check event name matches
            if event.event_name != event_name:
                continue

            # Check time bounds
            if after_time and event.event_time <= after_time:
                continue
            if before_time and event.event_time >= before_time:
                continue

            # Check additional conditions
            if self._check_conditions(event, conditions):
                return True, event.event_time

        return False, None

    def _check_conditions(self, event: CDPEvent, conditions: list[dict]) -> bool:
        """Check if event matches all conditions."""
        if not conditions:
            return True

        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "equals")
            value = condition.get("value")

            # Get field value from event properties
            actual_value = self._get_field_value(event, field)

            if not self._evaluate_condition(actual_value, operator, value):
                return False

        return True

    def _get_field_value(self, event: CDPEvent, field: str) -> Any:
        """Extract field value from event."""
        if field.startswith("properties."):
            prop_name = field[11:]
            return event.properties.get(prop_name)
        elif field.startswith("context."):
            ctx_name = field[8:]
            return event.context.get(ctx_name)
        elif field == "event_name":
            return event.event_name
        return None

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single condition."""
        if actual is None:
            return operator in ("is_null", "not_equals")

        operators = {
            "equals": lambda a, e: a == e,
            "not_equals": lambda a, e: a != e,
            "contains": lambda a, e: str(e) in str(a),
            "not_contains": lambda a, e: str(e) not in str(a),
            "greater_than": lambda a, e: float(a) > float(e),
            "less_than": lambda a, e: float(a) < float(e),
            "greater_or_equal": lambda a, e: float(a) >= float(e),
            "less_or_equal": lambda a, e: float(a) <= float(e),
            "in": lambda a, e: a in (e if isinstance(e, list) else [e]),
            "not_in": lambda a, e: a not in (e if isinstance(e, list) else [e]),
            "is_null": lambda a, e: a is None,
            "is_not_null": lambda a, e: a is not None,
        }

        evaluator = operators.get(operator, lambda a, e: a == e)
        try:
            return evaluator(actual, expected)
        except (TypeError, ValueError):
            return False


class FunnelService:
    """
    Service for managing CDP funnels and computing conversion analytics.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.evaluator = FunnelStepEvaluator()

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    async def create_funnel(
        self,
        name: str,
        steps: list[dict[str, Any]],
        description: Optional[str] = None,
        conversion_window_days: int = 30,
        step_timeout_hours: Optional[int] = None,
        auto_refresh: bool = True,
        refresh_interval_hours: int = 24,
        tags: Optional[list[str]] = None,
        created_by_user_id: Optional[int] = None,
    ) -> CDPFunnel:
        """Create a new funnel definition."""
        # Generate slug from name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

        # Ensure slug is unique
        existing = await self.db.execute(
            select(CDPFunnel).where(
                CDPFunnel.tenant_id == self.tenant_id,
                CDPFunnel.slug == slug,
            )
        )
        if existing.scalar_one_or_none():
            slug = f"{slug}-{int(time.time())}"

        funnel = CDPFunnel(
            tenant_id=self.tenant_id,
            name=name,
            description=description,
            slug=slug,
            steps=steps,
            status=FunnelStatus.DRAFT.value,
            conversion_window_days=conversion_window_days,
            step_timeout_hours=step_timeout_hours,
            auto_refresh=auto_refresh,
            refresh_interval_hours=refresh_interval_hours,
            tags=tags or [],
            created_by_user_id=created_by_user_id,
        )

        self.db.add(funnel)
        await self.db.flush()

        logger.info(
            "cdp_funnel_created",
            funnel_id=str(funnel.id),
            name=name,
            steps_count=len(steps),
            tenant_id=self.tenant_id,
        )

        return funnel

    async def get_funnel(self, funnel_id: UUID) -> Optional[CDPFunnel]:
        """Get a funnel by ID."""
        result = await self.db.execute(
            select(CDPFunnel).where(
                CDPFunnel.id == funnel_id,
                CDPFunnel.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_funnels(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CDPFunnel], int]:
        """List all funnels for tenant."""
        query = select(CDPFunnel).where(CDPFunnel.tenant_id == self.tenant_id)

        if status:
            query = query.where(CDPFunnel.status == status)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CDPFunnel.id)).where(CDPFunnel.tenant_id == self.tenant_id)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(CDPFunnel.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def update_funnel(
        self,
        funnel_id: UUID,
        **updates,
    ) -> Optional[CDPFunnel]:
        """Update a funnel definition."""
        funnel = await self.get_funnel(funnel_id)
        if not funnel:
            return None

        allowed_fields = {
            "name",
            "description",
            "steps",
            "conversion_window_days",
            "step_timeout_hours",
            "auto_refresh",
            "refresh_interval_hours",
            "tags",
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(funnel, field, value)

        # Mark as stale if steps changed
        if "steps" in updates:
            funnel.status = FunnelStatus.STALE.value

        await self.db.flush()
        return funnel

    async def delete_funnel(self, funnel_id: UUID) -> bool:
        """Delete a funnel and all its entries."""
        funnel = await self.get_funnel(funnel_id)
        if not funnel:
            return False

        # Delete all entries first
        await self.db.execute(
            delete(CDPFunnelEntry).where(
                CDPFunnelEntry.funnel_id == funnel_id,
                CDPFunnelEntry.tenant_id == self.tenant_id,
            )
        )

        # Delete funnel
        await self.db.delete(funnel)
        await self.db.flush()

        logger.info(
            "cdp_funnel_deleted",
            funnel_id=str(funnel_id),
            tenant_id=self.tenant_id,
        )

        return True

    # -------------------------------------------------------------------------
    # Funnel Computation
    # -------------------------------------------------------------------------

    async def compute_funnel(
        self,
        funnel_id: UUID,
        batch_size: int = 500,
    ) -> dict[str, Any]:
        """
        Compute funnel metrics by analyzing all profiles.

        This is a potentially expensive operation that:
        1. Iterates through all profiles
        2. Checks each profile's events against funnel steps
        3. Creates/updates funnel entries
        4. Calculates step-by-step conversion metrics
        """
        start_time = time.time()

        funnel = await self.get_funnel(funnel_id)
        if not funnel:
            raise ValueError(f"Funnel {funnel_id} not found")

        # Update status to computing
        funnel.status = FunnelStatus.COMPUTING.value
        await self.db.flush()

        steps = funnel.steps
        if not steps:
            raise ValueError("Funnel has no steps defined")

        # Clear existing entries
        await self.db.execute(
            delete(CDPFunnelEntry).where(
                CDPFunnelEntry.funnel_id == funnel_id,
                CDPFunnelEntry.tenant_id == self.tenant_id,
            )
        )

        # Initialize step counters
        step_counts = {i: 0 for i in range(1, len(steps) + 1)}
        total_entered = 0
        total_converted = 0

        # Process profiles in batches
        offset = 0
        while True:
            result = await self.db.execute(
                select(CDPProfile)
                .where(CDPProfile.tenant_id == self.tenant_id)
                .options(selectinload(CDPProfile.events))
                .limit(batch_size)
                .offset(offset)
            )
            profiles = list(result.scalars().all())

            if not profiles:
                break

            for profile in profiles:
                entry = await self._process_profile_funnel(profile, funnel, steps)

                if entry:
                    total_entered += 1
                    step_counts[1] += 1

                    for step_num in range(2, entry.completed_steps + 1):
                        step_counts[step_num] += 1

                    if entry.is_converted:
                        total_converted += 1

            offset += batch_size

        # Calculate step metrics
        step_metrics = []
        for i, step in enumerate(steps, 1):
            count = step_counts[i]
            prev_count = step_counts.get(i - 1, total_entered) if i > 1 else total_entered

            conversion_rate = (count / total_entered * 100) if total_entered > 0 else 0
            drop_off_rate = ((prev_count - count) / prev_count * 100) if prev_count > 0 else 0

            step_metrics.append(
                {
                    "step": i,
                    "name": step.get("step_name", step.get("event_name", f"Step {i}")),
                    "event_name": step.get("event_name"),
                    "count": count,
                    "conversion_rate": round(conversion_rate, 2),
                    "drop_off_rate": round(drop_off_rate, 2),
                    "drop_off_count": prev_count - count if i > 1 else 0,
                }
            )

        # Update funnel metrics
        overall_rate = (total_converted / total_entered * 100) if total_entered > 0 else 0

        funnel.total_entered = total_entered
        funnel.total_converted = total_converted
        funnel.overall_conversion_rate = Decimal(str(round(overall_rate, 2)))
        funnel.step_metrics = step_metrics
        funnel.status = FunnelStatus.ACTIVE.value
        funnel.last_computed_at = datetime.now(UTC)
        funnel.computation_duration_ms = int((time.time() - start_time) * 1000)

        if funnel.auto_refresh:
            funnel.next_refresh_at = datetime.now(UTC) + timedelta(
                hours=funnel.refresh_interval_hours
            )

        await self.db.flush()

        logger.info(
            "cdp_funnel_computed",
            funnel_id=str(funnel_id),
            total_entered=total_entered,
            total_converted=total_converted,
            overall_conversion_rate=overall_rate,
            duration_ms=funnel.computation_duration_ms,
            tenant_id=self.tenant_id,
        )

        return {
            "funnel_id": str(funnel_id),
            "total_entered": total_entered,
            "total_converted": total_converted,
            "overall_conversion_rate": round(overall_rate, 2),
            "step_metrics": step_metrics,
            "computation_duration_ms": funnel.computation_duration_ms,
        }

    async def _process_profile_funnel(
        self,
        profile: CDPProfile,
        funnel: CDPFunnel,
        steps: list[dict],
    ) -> Optional[CDPFunnelEntry]:
        """
        Process a single profile through the funnel.

        Returns a funnel entry if the profile completed at least step 1.
        """
        # Get all events for this profile (ordered by time)
        events = sorted(list(profile.events), key=lambda e: e.event_time)

        if not events:
            return None

        # Check step 1
        step1 = steps[0]
        completed_step1, step1_time = await self.evaluator.check_step_completion(
            profile.id, step1, events
        )

        if not completed_step1:
            return None

        # Create funnel entry
        entry = CDPFunnelEntry(
            tenant_id=self.tenant_id,
            funnel_id=funnel.id,
            profile_id=profile.id,
            entered_at=step1_time,
            current_step=1,
            completed_steps=1,
            step_timestamps={"1": step1_time.isoformat()},
        )

        # Check subsequent steps
        last_step_time = step1_time
        conversion_deadline = step1_time + timedelta(days=funnel.conversion_window_days)

        for i, step in enumerate(steps[1:], start=2):
            # Check step timeout
            min_time = last_step_time
            max_time = conversion_deadline

            if funnel.step_timeout_hours:
                step_deadline = last_step_time + timedelta(hours=funnel.step_timeout_hours)
                max_time = min(max_time, step_deadline)

            completed, step_time = await self.evaluator.check_step_completion(
                profile.id,
                step,
                events,
                after_time=min_time,
                before_time=max_time,
            )

            if not completed:
                break

            entry.current_step = i
            entry.completed_steps = i
            entry.step_timestamps[str(i)] = step_time.isoformat()
            last_step_time = step_time

        # Check if fully converted
        if entry.completed_steps == len(steps):
            entry.is_converted = True
            entry.converted_at = last_step_time
            entry.total_duration_seconds = int((last_step_time - step1_time).total_seconds())

        self.db.add(entry)
        return entry

    # -------------------------------------------------------------------------
    # Analytics Queries
    # -------------------------------------------------------------------------

    async def get_funnel_analysis(
        self,
        funnel_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Get detailed funnel analysis with time-based filtering.
        """
        funnel = await self.get_funnel(funnel_id)
        if not funnel:
            raise ValueError(f"Funnel {funnel_id} not found")

        # Build query for entries
        query = select(CDPFunnelEntry).where(
            CDPFunnelEntry.funnel_id == funnel_id,
            CDPFunnelEntry.tenant_id == self.tenant_id,
        )

        if start_date:
            query = query.where(CDPFunnelEntry.entered_at >= start_date)
        if end_date:
            query = query.where(CDPFunnelEntry.entered_at <= end_date)

        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        # Calculate metrics
        total_entered = len(entries)
        converted_entries = [e for e in entries if e.is_converted]
        total_converted = len(converted_entries)

        # Step-by-step analysis
        step_counts = {i: 0 for i in range(1, len(funnel.steps) + 1)}
        for entry in entries:
            for step_num in range(1, entry.completed_steps + 1):
                step_counts[step_num] += 1

        step_analysis = []
        for i, step in enumerate(funnel.steps, 1):
            count = step_counts[i]
            prev_count = step_counts.get(i - 1, total_entered) if i > 1 else total_entered

            step_analysis.append(
                {
                    "step": i,
                    "name": step.get("step_name", step.get("event_name", f"Step {i}")),
                    "event_name": step.get("event_name"),
                    "count": count,
                    "conversion_rate_from_start": round(
                        (count / total_entered * 100) if total_entered > 0 else 0, 2
                    ),
                    "conversion_rate_from_prev": round(
                        (count / prev_count * 100) if prev_count > 0 else 0, 2
                    ),
                    "drop_off_count": prev_count - count if i > 1 else 0,
                }
            )

        # Time analysis for converted users
        avg_duration = None
        if converted_entries:
            durations = [
                e.total_duration_seconds for e in converted_entries if e.total_duration_seconds
            ]
            if durations:
                avg_duration = sum(durations) / len(durations)

        return {
            "funnel_id": str(funnel_id),
            "funnel_name": funnel.name,
            "total_entered": total_entered,
            "total_converted": total_converted,
            "overall_conversion_rate": round(
                (total_converted / total_entered * 100) if total_entered > 0 else 0, 2
            ),
            "step_analysis": step_analysis,
            "avg_conversion_time_seconds": round(avg_duration, 0) if avg_duration else None,
            "analysis_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    async def get_profile_funnel_journey(
        self,
        profile_id: UUID,
        funnel_id: Optional[UUID] = None,
    ) -> list[dict[str, Any]]:
        """
        Get a profile's journey through funnels.
        """
        query = select(CDPFunnelEntry).where(
            CDPFunnelEntry.profile_id == profile_id,
            CDPFunnelEntry.tenant_id == self.tenant_id,
        )

        if funnel_id:
            query = query.where(CDPFunnelEntry.funnel_id == funnel_id)

        result = await self.db.execute(query.options(selectinload(CDPFunnelEntry.funnel)))
        entries = list(result.scalars().all())

        journeys = []
        for entry in entries:
            journeys.append(
                {
                    "funnel_id": str(entry.funnel_id),
                    "funnel_name": entry.funnel.name if entry.funnel else None,
                    "entered_at": entry.entered_at.isoformat(),
                    "converted_at": entry.converted_at.isoformat() if entry.converted_at else None,
                    "is_converted": entry.is_converted,
                    "current_step": entry.current_step,
                    "completed_steps": entry.completed_steps,
                    "total_steps": len(entry.funnel.steps) if entry.funnel else None,
                    "step_timestamps": entry.step_timestamps,
                    "total_duration_seconds": entry.total_duration_seconds,
                }
            )

        return journeys

    async def get_funnel_drop_off_profiles(
        self,
        funnel_id: UUID,
        at_step: int,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CDPProfile], int]:
        """
        Get profiles that dropped off at a specific step.
        """
        # Get entries that stopped at this step
        query = select(CDPFunnelEntry).where(
            CDPFunnelEntry.funnel_id == funnel_id,
            CDPFunnelEntry.tenant_id == self.tenant_id,
            CDPFunnelEntry.completed_steps == at_step,
            CDPFunnelEntry.is_converted == False,
        )

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CDPFunnelEntry.id)).where(
                CDPFunnelEntry.funnel_id == funnel_id,
                CDPFunnelEntry.tenant_id == self.tenant_id,
                CDPFunnelEntry.completed_steps == at_step,
                CDPFunnelEntry.is_converted == False,
            )
        )
        total = count_result.scalar() or 0

        # Get paginated entries with profiles
        result = await self.db.execute(
            query.options(selectinload(CDPFunnelEntry.profile)).limit(limit).offset(offset)
        )
        entries = list(result.scalars().all())

        profiles = [e.profile for e in entries if e.profile]
        return profiles, total
