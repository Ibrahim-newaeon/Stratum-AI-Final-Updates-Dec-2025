# =============================================================================
# Stratum AI - CDP Computed Traits Service
# =============================================================================
"""
Computed Traits service for CDP profile enrichment.

This service handles:
- Computed trait definitions (count, sum, average, min, max, etc.)
- Trait computation for individual profiles
- Batch trait computation
- RFM (Recency, Frequency, Monetary) analysis
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdp import (
    CDPProfile,
    CDPEvent,
    CDPComputedTrait,
    ComputedTraitType,
)

logger = structlog.get_logger()


class ComputedTraitsService:
    """
    Service for computing and managing profile traits.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # Trait Definition CRUD
    # =========================================================================

    async def create_trait(
        self,
        name: str,
        display_name: str,
        trait_type: str,
        source_config: Dict[str, Any],
        description: Optional[str] = None,
        output_type: str = "number",
        default_value: Optional[str] = None,
    ) -> CDPComputedTrait:
        """Create a new computed trait definition."""
        trait = CDPComputedTrait(
            tenant_id=self.tenant_id,
            name=name,
            display_name=display_name,
            description=description,
            trait_type=trait_type,
            source_config=source_config,
            output_type=output_type,
            default_value=default_value,
        )
        self.db.add(trait)
        await self.db.flush()

        logger.info(
            "cdp_computed_trait_created",
            tenant_id=self.tenant_id,
            trait_name=name,
            trait_type=trait_type,
        )

        return trait

    async def get_trait(self, trait_id: UUID) -> Optional[CDPComputedTrait]:
        """Get a trait by ID."""
        result = await self.db.execute(
            select(CDPComputedTrait)
            .where(
                CDPComputedTrait.id == trait_id,
                CDPComputedTrait.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_trait_by_name(self, name: str) -> Optional[CDPComputedTrait]:
        """Get a trait by name."""
        result = await self.db.execute(
            select(CDPComputedTrait)
            .where(
                CDPComputedTrait.name == name,
                CDPComputedTrait.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_traits(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CDPComputedTrait], int]:
        """List computed traits."""
        query = select(CDPComputedTrait).where(
            CDPComputedTrait.tenant_id == self.tenant_id
        )

        if active_only:
            query = query.where(CDPComputedTrait.is_active == True)

        # Get count
        count_result = await self.db.execute(
            select(func.count(CDPComputedTrait.id))
            .where(CDPComputedTrait.tenant_id == self.tenant_id)
        )
        total = count_result.scalar() or 0

        # Get traits
        result = await self.db.execute(
            query.order_by(CDPComputedTrait.name)
            .offset(offset)
            .limit(limit)
        )
        traits = list(result.scalars().all())

        return traits, total

    async def delete_trait(self, trait_id: UUID) -> bool:
        """Delete a computed trait."""
        trait = await self.get_trait(trait_id)
        if not trait:
            return False

        await self.db.delete(trait)
        await self.db.flush()

        logger.info(
            "cdp_computed_trait_deleted",
            tenant_id=self.tenant_id,
            trait_id=str(trait_id),
        )

        return True

    # =========================================================================
    # Trait Computation
    # =========================================================================

    async def compute_trait_for_profile(
        self,
        profile: CDPProfile,
        trait: CDPComputedTrait,
    ) -> Any:
        """
        Compute a single trait value for a profile.

        Returns the computed value.
        """
        config = trait.source_config or {}
        event_name = config.get("event_name")
        property_name = config.get("property")
        time_window_days = config.get("time_window_days")

        # Build event query
        query = select(CDPEvent).where(
            CDPEvent.tenant_id == self.tenant_id,
            CDPEvent.profile_id == profile.id,
        )

        if event_name:
            query = query.where(CDPEvent.event_name == event_name)

        if time_window_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=time_window_days)
            query = query.where(CDPEvent.event_time >= cutoff)

        result = await self.db.execute(query.order_by(CDPEvent.event_time.desc()))
        events = result.scalars().all()

        # Compute based on trait type
        trait_type = trait.trait_type

        if trait_type == ComputedTraitType.COUNT.value:
            return len(events)

        elif trait_type == ComputedTraitType.SUM.value:
            if not property_name:
                return 0
            total = sum(
                float(e.properties.get(property_name, 0))
                for e in events
                if e.properties.get(property_name) is not None
            )
            return total

        elif trait_type == ComputedTraitType.AVERAGE.value:
            if not property_name or not events:
                return None
            values = [
                float(e.properties.get(property_name, 0))
                for e in events
                if e.properties.get(property_name) is not None
            ]
            return sum(values) / len(values) if values else None

        elif trait_type == ComputedTraitType.MIN.value:
            if not property_name or not events:
                return None
            values = [
                float(e.properties.get(property_name, 0))
                for e in events
                if e.properties.get(property_name) is not None
            ]
            return min(values) if values else None

        elif trait_type == ComputedTraitType.MAX.value:
            if not property_name or not events:
                return None
            values = [
                float(e.properties.get(property_name, 0))
                for e in events
                if e.properties.get(property_name) is not None
            ]
            return max(values) if values else None

        elif trait_type == ComputedTraitType.FIRST.value:
            if events:
                last_event = events[-1]  # Oldest event
                if property_name:
                    return last_event.properties.get(property_name)
                return last_event.event_time.isoformat()
            return None

        elif trait_type == ComputedTraitType.LAST.value:
            if events:
                first_event = events[0]  # Most recent event
                if property_name:
                    return first_event.properties.get(property_name)
                return first_event.event_time.isoformat()
            return None

        elif trait_type == ComputedTraitType.UNIQUE_COUNT.value:
            if not property_name:
                return 0
            unique_values = set(
                e.properties.get(property_name)
                for e in events
                if e.properties.get(property_name) is not None
            )
            return len(unique_values)

        elif trait_type == ComputedTraitType.EXISTS.value:
            return len(events) > 0

        return trait.default_value

    async def compute_all_traits_for_profile(
        self,
        profile: CDPProfile,
    ) -> Dict[str, Any]:
        """
        Compute all active traits for a profile and update computed_traits.

        Returns the updated computed_traits dict.
        """
        traits, _ = await self.list_traits(active_only=True)

        computed = profile.computed_traits or {}

        for trait in traits:
            try:
                value = await self.compute_trait_for_profile(profile, trait)
                computed[trait.name] = value
            except Exception as e:
                logger.warning(
                    "cdp_trait_computation_error",
                    trait_name=trait.name,
                    profile_id=str(profile.id),
                    error=str(e),
                )

        # Update profile
        profile.computed_traits = computed
        await self.db.flush()

        return computed

    async def compute_traits_batch(
        self,
        batch_size: int = 500,
    ) -> Tuple[int, int]:
        """
        Compute all traits for all profiles in batches.

        Returns: (profiles_processed, errors)
        """
        traits, _ = await self.list_traits(active_only=True)
        if not traits:
            return 0, 0

        processed = 0
        errors = 0
        offset = 0

        while True:
            result = await self.db.execute(
                select(CDPProfile)
                .where(CDPProfile.tenant_id == self.tenant_id)
                .offset(offset)
                .limit(batch_size)
            )
            profiles = result.scalars().all()

            if not profiles:
                break

            for profile in profiles:
                try:
                    await self.compute_all_traits_for_profile(profile)
                    processed += 1
                except Exception as e:
                    errors += 1
                    logger.error(
                        "cdp_batch_trait_error",
                        profile_id=str(profile.id),
                        error=str(e),
                    )

            offset += batch_size
            await self.db.flush()

        # Update last_computed_at for all traits
        for trait in traits:
            trait.last_computed_at = datetime.now(timezone.utc)

        await self.db.flush()

        logger.info(
            "cdp_traits_batch_computed",
            tenant_id=self.tenant_id,
            profiles_processed=processed,
            errors=errors,
        )

        return processed, errors


class RFMAnalysisService:
    """
    RFM (Recency, Frequency, Monetary) Analysis service.

    Calculates customer value scores based on:
    - Recency: How recently did they purchase?
    - Frequency: How often do they purchase?
    - Monetary: How much do they spend?
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def calculate_rfm_for_profile(
        self,
        profile: CDPProfile,
        purchase_event_name: str = "Purchase",
        revenue_property: str = "total",
        analysis_window_days: int = 365,
    ) -> Dict[str, Any]:
        """
        Calculate RFM scores for a single profile.

        Returns:
        {
            "recency_days": int,
            "frequency": int,
            "monetary": float,
            "recency_score": int (1-5),
            "frequency_score": int (1-5),
            "monetary_score": int (1-5),
            "rfm_score": int (combined 1-5),
            "rfm_segment": str
        }
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=analysis_window_days)

        # Get purchase events
        result = await self.db.execute(
            select(CDPEvent)
            .where(
                CDPEvent.tenant_id == self.tenant_id,
                CDPEvent.profile_id == profile.id,
                CDPEvent.event_name == purchase_event_name,
                CDPEvent.event_time >= cutoff,
            )
            .order_by(CDPEvent.event_time.desc())
        )
        purchases = result.scalars().all()

        # Calculate raw RFM values
        if purchases:
            last_purchase = purchases[0]
            recency_days = (datetime.now(timezone.utc) - last_purchase.event_time).days
            frequency = len(purchases)
            monetary = sum(
                float(p.properties.get(revenue_property, 0))
                for p in purchases
                if p.properties.get(revenue_property) is not None
            )
        else:
            recency_days = analysis_window_days
            frequency = 0
            monetary = 0.0

        # Calculate scores (1-5, using quintiles)
        # For now, use simple thresholds; in production, use actual distribution
        recency_score = self._score_recency(recency_days)
        frequency_score = self._score_frequency(frequency)
        monetary_score = self._score_monetary(monetary)

        # Combined RFM score (average, weighted equally)
        rfm_score = round((recency_score + frequency_score + monetary_score) / 3)

        # Determine segment
        rfm_segment = self._determine_segment(recency_score, frequency_score, monetary_score)

        return {
            "recency_days": recency_days,
            "frequency": frequency,
            "monetary": round(monetary, 2),
            "recency_score": recency_score,
            "frequency_score": frequency_score,
            "monetary_score": monetary_score,
            "rfm_score": rfm_score,
            "rfm_segment": rfm_segment,
            "analysis_window_days": analysis_window_days,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _score_recency(self, days: int) -> int:
        """Score recency (lower days = higher score)."""
        if days <= 7:
            return 5
        elif days <= 30:
            return 4
        elif days <= 90:
            return 3
        elif days <= 180:
            return 2
        else:
            return 1

    def _score_frequency(self, count: int) -> int:
        """Score frequency (higher count = higher score)."""
        if count >= 20:
            return 5
        elif count >= 10:
            return 4
        elif count >= 5:
            return 3
        elif count >= 2:
            return 2
        elif count >= 1:
            return 1
        else:
            return 1

    def _score_monetary(self, amount: float) -> int:
        """Score monetary value (higher amount = higher score)."""
        if amount >= 1000:
            return 5
        elif amount >= 500:
            return 4
        elif amount >= 200:
            return 3
        elif amount >= 50:
            return 2
        else:
            return 1

    def _determine_segment(self, r: int, f: int, m: int) -> str:
        """Determine customer segment based on RFM scores."""
        avg = (r + f + m) / 3

        # Champions: High R, F, M
        if r >= 4 and f >= 4 and m >= 4:
            return "champions"

        # Loyal Customers: High F, moderate to high R and M
        if f >= 4 and r >= 3:
            return "loyal_customers"

        # Potential Loyalists: Recent, moderate frequency
        if r >= 4 and f >= 2 and f < 4:
            return "potential_loyalists"

        # New Customers: Very recent, low frequency
        if r >= 4 and f <= 2:
            return "new_customers"

        # Promising: Recent but low spend
        if r >= 3 and f >= 2 and m <= 2:
            return "promising"

        # Need Attention: Moderate everything, slipping
        if r >= 2 and r <= 3 and f >= 2 and f <= 3:
            return "need_attention"

        # About to Sleep: Low recency, was active
        if r <= 2 and f >= 2:
            return "about_to_sleep"

        # At Risk: Low recency, high value previously
        if r <= 2 and (f >= 4 or m >= 4):
            return "at_risk"

        # Cannot Lose: Very low recency but high historical value
        if r == 1 and (f >= 4 and m >= 4):
            return "cannot_lose"

        # Hibernating: Very low engagement
        if r <= 2 and f <= 2:
            return "hibernating"

        # Lost: No recent activity, low historical
        if r == 1 and f <= 2 and m <= 2:
            return "lost"

        return "other"

    async def calculate_rfm_batch(
        self,
        purchase_event_name: str = "Purchase",
        revenue_property: str = "total",
        analysis_window_days: int = 365,
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """
        Calculate RFM for all profiles and store in computed_traits.

        Returns summary statistics.
        """
        processed = 0
        segment_counts: Dict[str, int] = {}
        offset = 0

        while True:
            result = await self.db.execute(
                select(CDPProfile)
                .where(CDPProfile.tenant_id == self.tenant_id)
                .offset(offset)
                .limit(batch_size)
            )
            profiles = result.scalars().all()

            if not profiles:
                break

            for profile in profiles:
                try:
                    rfm = await self.calculate_rfm_for_profile(
                        profile,
                        purchase_event_name,
                        revenue_property,
                        analysis_window_days,
                    )

                    # Store in computed_traits
                    traits = profile.computed_traits or {}
                    traits["rfm_recency_days"] = rfm["recency_days"]
                    traits["rfm_frequency"] = rfm["frequency"]
                    traits["rfm_monetary"] = rfm["monetary"]
                    traits["rfm_score"] = rfm["rfm_score"]
                    traits["rfm_segment"] = rfm["rfm_segment"]
                    traits["rfm_calculated_at"] = rfm["calculated_at"]
                    profile.computed_traits = traits

                    # Track segment
                    segment = rfm["rfm_segment"]
                    segment_counts[segment] = segment_counts.get(segment, 0) + 1
                    processed += 1

                except Exception as e:
                    logger.error(
                        "cdp_rfm_calculation_error",
                        profile_id=str(profile.id),
                        error=str(e),
                    )

            offset += batch_size
            await self.db.flush()

        logger.info(
            "cdp_rfm_batch_completed",
            tenant_id=self.tenant_id,
            profiles_processed=processed,
            segment_counts=segment_counts,
        )

        return {
            "profiles_processed": processed,
            "segment_distribution": segment_counts,
            "analysis_window_days": analysis_window_days,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_rfm_summary(self) -> Dict[str, Any]:
        """
        Get RFM distribution summary for the tenant.
        """
        result = await self.db.execute(
            select(CDPProfile)
            .where(CDPProfile.tenant_id == self.tenant_id)
        )
        profiles = result.scalars().all()

        segment_counts: Dict[str, int] = {}
        total_profiles = 0
        profiles_with_rfm = 0

        for profile in profiles:
            total_profiles += 1
            traits = profile.computed_traits or {}
            segment = traits.get("rfm_segment")
            if segment:
                profiles_with_rfm += 1
                segment_counts[segment] = segment_counts.get(segment, 0) + 1

        return {
            "total_profiles": total_profiles,
            "profiles_with_rfm": profiles_with_rfm,
            "segment_distribution": segment_counts,
            "coverage_pct": round(profiles_with_rfm / total_profiles * 100, 1) if total_profiles > 0 else 0,
        }
