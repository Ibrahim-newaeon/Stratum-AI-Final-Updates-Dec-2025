# =============================================================================
# Stratum AI - CDP Segment Service
# =============================================================================
"""
Segment builder and evaluation service for CDP.

This service handles:
- Segment creation and management
- Rule-based segment evaluation
- Profile membership computation
- Batch segment refresh
"""

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cdp import (
    CDPProfile,
    CDPEvent,
    CDPSegment,
    CDPSegmentMembership,
    SegmentType,
    SegmentStatus,
)

logger = structlog.get_logger()


class SegmentEvaluator:
    """
    Evaluates segment rules against profile data.

    Rule Format:
    {
        "logic": "and" | "or",
        "conditions": [
            {
                "field": "profile.lifecycle_stage" | "profile.total_purchases" | "event.PageView.count" | "trait.ltv",
                "operator": "equals" | "greater_than" | etc.,
                "value": "customer" | 100 | etc.
            }
        ],
        "groups": [  # Nested groups for complex logic
            {
                "logic": "or",
                "conditions": [...]
            }
        ]
    }
    """

    PROFILE_FIELDS = {
        "lifecycle_stage",
        "total_events",
        "total_sessions",
        "total_purchases",
        "total_revenue",
        "first_seen_at",
        "last_seen_at",
        "external_id",
    }

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def evaluate_profile(
        self,
        profile: CDPProfile,
        rules: Dict,
        profile_events: Optional[List[CDPEvent]] = None,
    ) -> Tuple[bool, Optional[float]]:
        """
        Evaluate if a profile matches segment rules.

        Returns: (matches: bool, score: Optional[float])
        """
        if not rules or not rules.get("conditions") and not rules.get("groups"):
            return False, None

        logic = rules.get("logic", "and").lower()
        conditions = rules.get("conditions", [])
        groups = rules.get("groups", [])

        results = []
        scores = []

        # Evaluate individual conditions
        for condition in conditions:
            matches, score = await self._evaluate_condition(
                profile, condition, profile_events
            )
            results.append(matches)
            if score is not None:
                scores.append(score)

        # Evaluate nested groups recursively
        for group in groups:
            matches, score = await self.evaluate_profile(profile, group, profile_events)
            results.append(matches)
            if score is not None:
                scores.append(score)

        if not results:
            return False, None

        # Apply logic
        if logic == "and":
            final_match = all(results)
        else:  # or
            final_match = any(results)

        # Calculate average score
        avg_score = sum(scores) / len(scores) if scores else None

        return final_match, avg_score

    async def _evaluate_condition(
        self,
        profile: CDPProfile,
        condition: Dict,
        profile_events: Optional[List[CDPEvent]] = None,
    ) -> Tuple[bool, Optional[float]]:
        """Evaluate a single condition against a profile."""
        field = condition.get("field", "")
        operator = condition.get("operator", "")
        value = condition.get("value")

        # Parse field path (e.g., "profile.lifecycle_stage", "event.PageView.count")
        field_parts = field.split(".")

        if len(field_parts) < 2:
            return False, None

        field_type = field_parts[0].lower()

        try:
            if field_type == "profile":
                actual_value = self._get_profile_value(profile, field_parts[1])
            elif field_type == "trait":
                actual_value = self._get_trait_value(profile, field_parts[1])
            elif field_type == "identifier":
                actual_value = await self._get_identifier_value(profile, field_parts[1])
            elif field_type == "event":
                actual_value = await self._get_event_value(
                    profile, field_parts[1:], profile_events
                )
            elif field_type == "data":
                actual_value = self._get_profile_data_value(profile, field_parts[1:])
            else:
                return False, None

            return self._compare_values(actual_value, operator, value)

        except Exception as e:
            logger.warning(
                "cdp_segment_condition_error",
                field=field,
                operator=operator,
                error=str(e),
            )
            return False, None

    def _get_profile_value(self, profile: CDPProfile, field: str) -> Any:
        """Get a value from profile standard fields."""
        if field not in self.PROFILE_FIELDS:
            return None

        value = getattr(profile, field, None)

        # Convert Decimal to float for comparison
        if isinstance(value, Decimal):
            return float(value)

        return value

    def _get_trait_value(self, profile: CDPProfile, trait_name: str) -> Any:
        """Get a value from profile computed_traits."""
        traits = profile.computed_traits or {}
        return traits.get(trait_name)

    def _get_profile_data_value(self, profile: CDPProfile, path: List[str]) -> Any:
        """Get a nested value from profile_data JSON."""
        data = profile.profile_data or {}
        for key in path:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data

    async def _get_identifier_value(
        self, profile: CDPProfile, identifier_type: str
    ) -> Any:
        """Check if profile has a specific identifier type."""
        if profile.identifiers:
            for ident in profile.identifiers:
                if ident.identifier_type == identifier_type:
                    return True
        return False

    async def _get_event_value(
        self,
        profile: CDPProfile,
        path: List[str],
        profile_events: Optional[List[CDPEvent]] = None,
    ) -> Any:
        """
        Get event-based values.

        Supports:
        - event.{event_name}.count - Count of events
        - event.{event_name}.exists - Boolean if event exists
        - event.{event_name}.last - Date of last event
        - event.{event_name}.first - Date of first event
        - event.{event_name}.property.{prop_name} - Last property value
        """
        if len(path) < 2:
            return None

        event_name = path[0]
        aggregation = path[1].lower()

        # Fetch events if not provided
        if profile_events is None:
            result = await self.db.execute(
                select(CDPEvent)
                .where(
                    CDPEvent.tenant_id == self.tenant_id,
                    CDPEvent.profile_id == profile.id,
                    CDPEvent.event_name == event_name,
                )
                .order_by(CDPEvent.event_time.desc())
                .limit(1000)
            )
            profile_events = result.scalars().all()
        else:
            profile_events = [e for e in profile_events if e.event_name == event_name]

        if aggregation == "count":
            return len(profile_events)
        elif aggregation == "exists":
            return len(profile_events) > 0
        elif aggregation == "last" and profile_events:
            return profile_events[0].event_time
        elif aggregation == "first" and profile_events:
            return profile_events[-1].event_time
        elif aggregation == "property" and len(path) > 2 and profile_events:
            prop_name = path[2]
            return profile_events[0].properties.get(prop_name)

        return None

    def _compare_values(
        self, actual: Any, operator: str, expected: Any
    ) -> Tuple[bool, Optional[float]]:
        """Compare actual value against expected using operator."""
        if actual is None and operator not in ["is_null", "is_not_null"]:
            return False, None

        op = operator.lower()

        try:
            if op == "equals":
                result = actual == expected
            elif op == "not_equals":
                result = actual != expected
            elif op == "contains":
                result = str(expected).lower() in str(actual).lower()
            elif op == "not_contains":
                result = str(expected).lower() not in str(actual).lower()
            elif op == "starts_with":
                result = str(actual).lower().startswith(str(expected).lower())
            elif op == "ends_with":
                result = str(actual).lower().endswith(str(expected).lower())
            elif op == "greater_than":
                result = float(actual) > float(expected)
            elif op == "less_than":
                result = float(actual) < float(expected)
            elif op == "greater_or_equal":
                result = float(actual) >= float(expected)
            elif op == "less_or_equal":
                result = float(actual) <= float(expected)
            elif op == "between":
                if isinstance(expected, list) and len(expected) == 2:
                    result = float(expected[0]) <= float(actual) <= float(expected[1])
                else:
                    result = False
            elif op == "in":
                if isinstance(expected, list):
                    result = actual in expected
                else:
                    result = False
            elif op == "not_in":
                if isinstance(expected, list):
                    result = actual not in expected
                else:
                    result = True
            elif op == "is_null":
                result = actual is None
            elif op == "is_not_null":
                result = actual is not None
            elif op == "before":
                actual_dt = self._parse_datetime(actual)
                expected_dt = self._parse_datetime(expected)
                result = actual_dt < expected_dt if actual_dt and expected_dt else False
            elif op == "after":
                actual_dt = self._parse_datetime(actual)
                expected_dt = self._parse_datetime(expected)
                result = actual_dt > expected_dt if actual_dt and expected_dt else False
            elif op == "within_last":
                # expected is number of days
                actual_dt = self._parse_datetime(actual)
                if actual_dt:
                    cutoff = datetime.now(timezone.utc) - timedelta(days=int(expected))
                    result = actual_dt >= cutoff
                else:
                    result = False
            else:
                result = False

            # Calculate confidence score (1.0 for exact match)
            score = 1.0 if result else 0.0

            return result, score

        except (ValueError, TypeError) as e:
            logger.warning(
                "cdp_segment_comparison_error",
                actual=actual,
                operator=operator,
                expected=expected,
                error=str(e),
            )
            return False, None

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse a value as datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


class SegmentService:
    """
    Service for managing CDP segments.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.evaluator = SegmentEvaluator(db, tenant_id)

    # =========================================================================
    # Segment CRUD
    # =========================================================================

    async def create_segment(
        self,
        name: str,
        rules: Dict,
        segment_type: str = SegmentType.DYNAMIC.value,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_refresh: bool = True,
        refresh_interval_hours: int = 24,
        created_by_user_id: Optional[int] = None,
    ) -> CDPSegment:
        """Create a new segment."""
        # Generate slug from name
        slug = self._generate_slug(name)

        segment = CDPSegment(
            tenant_id=self.tenant_id,
            name=name,
            slug=slug,
            description=description,
            segment_type=segment_type,
            status=SegmentStatus.DRAFT.value,
            rules=rules,
            tags=tags or [],
            auto_refresh=auto_refresh,
            refresh_interval_hours=refresh_interval_hours,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(segment)
        await self.db.flush()

        logger.info(
            "cdp_segment_created",
            tenant_id=self.tenant_id,
            segment_id=str(segment.id),
            segment_name=name,
            segment_type=segment_type,
        )

        return segment

    async def get_segment(self, segment_id: UUID) -> Optional[CDPSegment]:
        """Get a segment by ID."""
        result = await self.db.execute(
            select(CDPSegment)
            .where(
                CDPSegment.id == segment_id,
                CDPSegment.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_segments(
        self,
        status: Optional[str] = None,
        segment_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CDPSegment], int]:
        """List segments with optional filtering."""
        query = select(CDPSegment).where(CDPSegment.tenant_id == self.tenant_id)

        if status:
            query = query.where(CDPSegment.status == status)
        if segment_type:
            query = query.where(CDPSegment.segment_type == segment_type)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CDPSegment.id)).where(CDPSegment.tenant_id == self.tenant_id)
        )
        total = count_result.scalar() or 0

        # Get segments
        result = await self.db.execute(
            query.order_by(CDPSegment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        segments = list(result.scalars().all())

        return segments, total

    async def update_segment(
        self,
        segment_id: UUID,
        **updates,
    ) -> Optional[CDPSegment]:
        """Update segment fields."""
        segment = await self.get_segment(segment_id)
        if not segment:
            return None

        for field, value in updates.items():
            if hasattr(segment, field):
                setattr(segment, field, value)

        # If rules changed, mark as stale
        if "rules" in updates:
            segment.status = SegmentStatus.STALE.value

        await self.db.flush()

        logger.info(
            "cdp_segment_updated",
            tenant_id=self.tenant_id,
            segment_id=str(segment_id),
            updates=list(updates.keys()),
        )

        return segment

    async def delete_segment(self, segment_id: UUID) -> bool:
        """Delete a segment and its memberships."""
        segment = await self.get_segment(segment_id)
        if not segment:
            return False

        await self.db.delete(segment)
        await self.db.flush()

        logger.info(
            "cdp_segment_deleted",
            tenant_id=self.tenant_id,
            segment_id=str(segment_id),
        )

        return True

    # =========================================================================
    # Segment Computation
    # =========================================================================

    async def compute_segment(
        self,
        segment_id: UUID,
        batch_size: int = 1000,
    ) -> Tuple[int, int]:
        """
        Compute segment membership for all profiles.

        Returns: (added_count, removed_count)
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            return 0, 0

        start_time = datetime.now(timezone.utc)
        segment.status = SegmentStatus.COMPUTING.value
        await self.db.flush()

        added_count = 0
        removed_count = 0
        offset = 0

        try:
            while True:
                # Fetch batch of profiles
                result = await self.db.execute(
                    select(CDPProfile)
                    .where(CDPProfile.tenant_id == self.tenant_id)
                    .options(selectinload(CDPProfile.identifiers))
                    .offset(offset)
                    .limit(batch_size)
                )
                profiles = result.scalars().all()

                if not profiles:
                    break

                for profile in profiles:
                    matches, score = await self.evaluator.evaluate_profile(
                        profile, segment.rules
                    )

                    # Check current membership
                    membership_result = await self.db.execute(
                        select(CDPSegmentMembership)
                        .where(
                            CDPSegmentMembership.segment_id == segment_id,
                            CDPSegmentMembership.profile_id == profile.id,
                        )
                    )
                    existing = membership_result.scalar_one_or_none()

                    if matches:
                        if not existing:
                            # Add to segment
                            membership = CDPSegmentMembership(
                                tenant_id=self.tenant_id,
                                segment_id=segment_id,
                                profile_id=profile.id,
                                match_score=Decimal(str(score)) if score else None,
                            )
                            self.db.add(membership)
                            added_count += 1
                        elif not existing.is_active:
                            # Re-activate membership
                            existing.is_active = True
                            existing.removed_at = None
                            existing.match_score = Decimal(str(score)) if score else None
                            added_count += 1
                    else:
                        if existing and existing.is_active:
                            # Remove from segment
                            existing.is_active = False
                            existing.removed_at = datetime.now(timezone.utc)
                            removed_count += 1

                offset += batch_size
                await self.db.flush()

            # Update segment metadata
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            # Get final count
            count_result = await self.db.execute(
                select(func.count(CDPSegmentMembership.id))
                .where(
                    CDPSegmentMembership.segment_id == segment_id,
                    CDPSegmentMembership.is_active == True,
                )
            )
            profile_count = count_result.scalar() or 0

            segment.status = SegmentStatus.ACTIVE.value
            segment.profile_count = profile_count
            segment.last_computed_at = datetime.now(timezone.utc)
            segment.computation_duration_ms = duration_ms

            if segment.auto_refresh:
                segment.next_refresh_at = datetime.now(timezone.utc) + timedelta(
                    hours=segment.refresh_interval_hours
                )

            await self.db.flush()

            logger.info(
                "cdp_segment_computed",
                tenant_id=self.tenant_id,
                segment_id=str(segment_id),
                profile_count=profile_count,
                added=added_count,
                removed=removed_count,
                duration_ms=duration_ms,
            )

            return added_count, removed_count

        except Exception as e:
            segment.status = SegmentStatus.STALE.value
            await self.db.flush()
            logger.error(
                "cdp_segment_computation_error",
                tenant_id=self.tenant_id,
                segment_id=str(segment_id),
                error=str(e),
            )
            raise

    async def preview_segment(
        self,
        rules: Dict,
        limit: int = 100,
    ) -> Tuple[int, List[CDPProfile]]:
        """
        Preview segment membership without saving.

        Returns: (estimated_count, sample_profiles)
        """
        matching_profiles = []
        total_checked = 0
        offset = 0
        batch_size = 500

        # Sample profiles to estimate total
        while len(matching_profiles) < limit and total_checked < 10000:
            result = await self.db.execute(
                select(CDPProfile)
                .where(CDPProfile.tenant_id == self.tenant_id)
                .options(selectinload(CDPProfile.identifiers))
                .offset(offset)
                .limit(batch_size)
            )
            profiles = result.scalars().all()

            if not profiles:
                break

            for profile in profiles:
                matches, _ = await self.evaluator.evaluate_profile(profile, rules)
                if matches:
                    matching_profiles.append(profile)
                    if len(matching_profiles) >= limit:
                        break

            total_checked += len(profiles)
            offset += batch_size

        # Estimate total count
        if total_checked > 0:
            match_rate = len(matching_profiles) / total_checked

            # Get total profile count
            count_result = await self.db.execute(
                select(func.count(CDPProfile.id))
                .where(CDPProfile.tenant_id == self.tenant_id)
            )
            total_profiles = count_result.scalar() or 0
            estimated_count = int(total_profiles * match_rate)
        else:
            estimated_count = 0

        return estimated_count, matching_profiles[:limit]

    # =========================================================================
    # Membership Management
    # =========================================================================

    async def get_segment_profiles(
        self,
        segment_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CDPProfile], int]:
        """Get profiles in a segment."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(CDPSegmentMembership.id))
            .where(
                CDPSegmentMembership.segment_id == segment_id,
                CDPSegmentMembership.is_active == True,
            )
        )
        total = count_result.scalar() or 0

        # Get profiles
        result = await self.db.execute(
            select(CDPProfile)
            .join(CDPSegmentMembership)
            .where(
                CDPSegmentMembership.segment_id == segment_id,
                CDPSegmentMembership.is_active == True,
            )
            .options(selectinload(CDPProfile.identifiers))
            .offset(offset)
            .limit(limit)
        )
        profiles = list(result.scalars().all())

        return profiles, total

    async def add_profile_to_segment(
        self,
        segment_id: UUID,
        profile_id: UUID,
        added_by_user_id: Optional[int] = None,
    ) -> bool:
        """Manually add a profile to a static segment."""
        segment = await self.get_segment(segment_id)
        if not segment or segment.segment_type != SegmentType.STATIC.value:
            return False

        # Check if already member
        existing_result = await self.db.execute(
            select(CDPSegmentMembership)
            .where(
                CDPSegmentMembership.segment_id == segment_id,
                CDPSegmentMembership.profile_id == profile_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.removed_at = None
                existing.added_by_user_id = added_by_user_id
                segment.profile_count += 1
            return True

        membership = CDPSegmentMembership(
            tenant_id=self.tenant_id,
            segment_id=segment_id,
            profile_id=profile_id,
            added_by_user_id=added_by_user_id,
        )
        self.db.add(membership)
        segment.profile_count += 1
        await self.db.flush()

        return True

    async def remove_profile_from_segment(
        self,
        segment_id: UUID,
        profile_id: UUID,
    ) -> bool:
        """Remove a profile from a segment."""
        segment = await self.get_segment(segment_id)
        if not segment:
            return False

        result = await self.db.execute(
            select(CDPSegmentMembership)
            .where(
                CDPSegmentMembership.segment_id == segment_id,
                CDPSegmentMembership.profile_id == profile_id,
                CDPSegmentMembership.is_active == True,
            )
        )
        membership = result.scalar_one_or_none()

        if membership:
            membership.is_active = False
            membership.removed_at = datetime.now(timezone.utc)
            segment.profile_count = max(0, segment.profile_count - 1)
            await self.db.flush()
            return True

        return False

    async def get_profile_segments(
        self,
        profile_id: UUID,
    ) -> List[CDPSegment]:
        """Get all segments a profile belongs to."""
        result = await self.db.execute(
            select(CDPSegment)
            .join(CDPSegmentMembership)
            .where(
                CDPSegmentMembership.profile_id == profile_id,
                CDPSegmentMembership.is_active == True,
                CDPSegment.tenant_id == self.tenant_id,
            )
        )
        return list(result.scalars().all())

    # =========================================================================
    # Helpers
    # =========================================================================

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug)
        slug = slug.strip("-")
        return slug[:100]
