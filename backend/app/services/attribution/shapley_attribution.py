# =============================================================================
# Stratum AI - Shapley Value Attribution Model
# =============================================================================
"""
Data-driven attribution using Shapley Values from cooperative game theory.

Shapley Values provide a fair way to distribute credit among channels based on
their marginal contribution to conversions. The method considers all possible
orderings of channels and averages the marginal contributions.

Key properties of Shapley Values:
1. Efficiency: Credits sum to total value
2. Symmetry: Equal contribution = equal credit
3. Null player: Zero contribution = zero credit
4. Additivity: Combined games preserve values
"""

import math
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import CRMContact, CRMDeal, Touchpoint

logger = get_logger(__name__)


class ShapleyValueModel:
    """
    Shapley Value model for multi-touch attribution.

    Calculates fair credit distribution based on marginal contributions
    of each channel to the overall conversion probability.
    """

    def __init__(self):
        # Coalition conversion rates: {frozenset(channels): conversion_rate}
        self.coalition_conversions: dict[frozenset, int] = defaultdict(int)
        self.coalition_totals: dict[frozenset, int] = defaultdict(int)
        # All observed channels
        self.channels: set[str] = set()
        # Journey statistics
        self.journey_count: int = 0
        self.converting_journeys: int = 0

    def add_journey(self, channels: list[str], converted: bool) -> None:
        """
        Add a customer journey to the model.

        Records the conversion outcome for this specific coalition of channels.
        """
        if not channels:
            return

        self.journey_count += 1
        if converted:
            self.converting_journeys += 1

        # Get unique channels in this journey (order doesn't matter for Shapley)
        channel_set = frozenset(set(channels))
        self.channels.update(channels)

        # Record this coalition's outcome
        self.coalition_totals[channel_set] += 1
        if converted:
            self.coalition_conversions[channel_set] += 1

    def get_coalition_value(self, coalition: frozenset) -> float:
        """
        Get the conversion rate for a specific coalition of channels.

        If we haven't observed this exact coalition, estimate from similar coalitions.
        """
        # Direct observation
        if coalition in self.coalition_totals and self.coalition_totals[coalition] > 0:
            return self.coalition_conversions[coalition] / self.coalition_totals[coalition]

        # Estimate from subsets and supersets
        if not coalition:
            return 0.0

        # Try to find similar coalitions
        similar_values = []
        for obs_coalition, total in self.coalition_totals.items():
            if total == 0:
                continue

            # Check if observed coalition is similar (subset or superset with 1 diff)
            diff = len(obs_coalition.symmetric_difference(coalition))
            if diff <= 1:
                rate = self.coalition_conversions[obs_coalition] / total
                similar_values.append(rate)

        if similar_values:
            return sum(similar_values) / len(similar_values)

        # Fallback: use overall conversion rate weighted by coalition size
        if self.journey_count > 0:
            base_rate = self.converting_journeys / self.journey_count
            # Smaller coalitions typically have lower conversion rates
            size_factor = len(coalition) / max(1, len(self.channels))
            return base_rate * size_factor

        return 0.0

    def calculate_shapley_values(self, max_channels: int = 10) -> dict[str, float]:
        """
        Calculate Shapley Values for each channel.

        For computational efficiency, uses sampling if there are many channels.

        Shapley formula:
        φ_i = Σ [|S|! (n-|S|-1)! / n!] * [v(S ∪ {i}) - v(S)]
        where S is a subset not containing i

        Args:
            max_channels: Maximum channels before using Monte Carlo sampling

        Returns:
            Dictionary of channel -> Shapley value
        """
        channels = list(self.channels)
        n = len(channels)

        if n == 0:
            return {}

        if n > max_channels:
            return self._calculate_shapley_monte_carlo(channels, samples=10000)

        shapley_values = {channel: 0.0 for channel in channels}

        # For each channel, calculate its Shapley value
        for i, channel in enumerate(channels):
            other_channels = [c for c in channels if c != channel]

            # Sum over all subsets of other channels
            for r in range(len(other_channels) + 1):
                for subset in combinations(other_channels, r):
                    subset_set = frozenset(subset)
                    with_channel = frozenset(subset) | {channel}

                    # Marginal contribution
                    v_with = self.get_coalition_value(with_channel)
                    v_without = self.get_coalition_value(subset_set)
                    marginal = v_with - v_without

                    # Shapley weight
                    s = len(subset)
                    weight = (math.factorial(s) * math.factorial(n - s - 1)) / math.factorial(n)

                    shapley_values[channel] += weight * marginal

        return shapley_values

    def _calculate_shapley_monte_carlo(
        self,
        channels: list[str],
        samples: int = 10000,
    ) -> dict[str, float]:
        """
        Monte Carlo approximation of Shapley values for large channel sets.

        Samples random permutations and averages marginal contributions.
        """
        import random

        marginal_sums = {channel: 0.0 for channel in channels}
        counts = {channel: 0 for channel in channels}

        for _ in range(samples):
            # Random permutation
            perm = channels.copy()
            random.shuffle(perm)

            # Calculate marginal contribution for each position
            current_coalition = set()
            for channel in perm:
                v_with = self.get_coalition_value(frozenset(current_coalition | {channel}))
                v_without = self.get_coalition_value(frozenset(current_coalition))

                marginal_sums[channel] += v_with - v_without
                counts[channel] += 1

                current_coalition.add(channel)

        # Average marginal contributions
        return {
            channel: marginal_sums[channel] / counts[channel] if counts[channel] > 0 else 0.0
            for channel in channels
        }

    def calculate_attribution_weights(self) -> dict[str, float]:
        """
        Calculate normalized attribution weights from Shapley values.

        Ensures weights are non-negative and sum to 1.0.
        """
        shapley_values = self.calculate_shapley_values()

        # Handle negative values (can occur due to estimation)
        min_val = min(shapley_values.values()) if shapley_values else 0
        if min_val < 0:
            # Shift to make all non-negative
            shapley_values = {k: v - min_val for k, v in shapley_values.items()}

        total = sum(shapley_values.values())
        if total == 0:
            n = len(shapley_values)
            return {k: 1.0 / n for k in shapley_values} if n > 0 else {}

        return {k: v / total for k, v in shapley_values.items()}

    def get_model_stats(self) -> dict[str, Any]:
        """Get model statistics."""
        return {
            "journey_count": self.journey_count,
            "converting_journeys": self.converting_journeys,
            "conversion_rate": (
                self.converting_journeys / self.journey_count if self.journey_count > 0 else 0
            ),
            "unique_channels": len(self.channels),
            "channels": list(self.channels),
            "unique_coalitions": len(self.coalition_totals),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to dictionary."""
        return {
            "coalition_conversions": {
                ",".join(sorted(k)): v for k, v in self.coalition_conversions.items()
            },
            "coalition_totals": {",".join(sorted(k)): v for k, v in self.coalition_totals.items()},
            "channels": list(self.channels),
            "journey_count": self.journey_count,
            "converting_journeys": self.converting_journeys,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShapleyValueModel":
        """Deserialize model from dictionary."""
        model = cls()

        for k, v in data.get("coalition_conversions", {}).items():
            key = frozenset(k.split(",")) if k else frozenset()
            model.coalition_conversions[key] = v

        for k, v in data.get("coalition_totals", {}).items():
            key = frozenset(k.split(",")) if k else frozenset()
            model.coalition_totals[key] = v

        model.channels = set(data.get("channels", []))
        model.journey_count = data.get("journey_count", 0)
        model.converting_journeys = data.get("converting_journeys", 0)
        return model


class ShapleyAttributionService:
    """
    Service for training and using Shapley Value attribution models.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def train_model(
        self,
        start_date: datetime,
        end_date: datetime,
        channel_type: str = "platform",
        include_non_converting: bool = True,
        min_journeys: int = 100,
    ) -> dict[str, Any]:
        """
        Train a Shapley Value model on historical journey data.
        """
        model = ShapleyValueModel()

        # Get converting journeys
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        for deal in deals:
            channels = await self._get_journey_channels(
                deal.contact_id,
                before_time=deal.won_at,
                channel_type=channel_type,
            )
            if channels:
                model.add_journey(channels, converted=True)

        # Include non-converting journeys
        if include_non_converting:
            non_converting = await self._get_non_converting_contacts(
                start_date, end_date, limit=len(deals) * 2
            )
            for contact_id in non_converting:
                channels = await self._get_journey_channels(
                    contact_id,
                    before_time=end_date,
                    channel_type=channel_type,
                )
                if channels:
                    model.add_journey(channels, converted=False)

        # Check minimum journeys
        if model.journey_count < min_journeys:
            return {
                "success": False,
                "error": f"Insufficient data: {model.journey_count} journeys (minimum: {min_journeys})",
                "journey_count": model.journey_count,
            }

        # Calculate Shapley values
        shapley_values = model.calculate_shapley_values()
        weights = model.calculate_attribution_weights()

        return {
            "success": True,
            "model_type": "shapley_value",
            "channel_type": channel_type,
            "training_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "stats": model.get_model_stats(),
            "shapley_values": shapley_values,
            "attribution_weights": weights,
            "model_data": model.to_dict(),
        }

    async def attribute_with_model(
        self,
        model_data: dict[str, Any],
        deal_id: UUID,
    ) -> dict[str, Any]:
        """
        Attribute a deal using a trained Shapley model.
        """
        model = ShapleyValueModel.from_dict(model_data)
        weights = model.calculate_attribution_weights()

        # Get deal
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.id == deal_id,
                    CRMDeal.tenant_id == self.tenant_id,
                )
            )
        )
        deal = deal_result.scalar_one_or_none()

        if not deal or not deal.contact_id:
            return {"success": False, "error": "deal_not_found"}

        # Get touchpoints
        touchpoints = await self._get_journey_touchpoints(
            deal.contact_id,
            before_time=deal.won_at,
        )

        if not touchpoints:
            return {"success": False, "error": "no_touchpoints"}

        revenue = deal.amount or 0
        breakdown = []

        # Get unique channels in journey
        journey_channels = {tp.source or "unknown" for tp in touchpoints}

        # Normalize weights for channels in this journey
        journey_weights = {c: weights.get(c, 0.0) for c in journey_channels}
        total = sum(journey_weights.values())
        if total > 0:
            journey_weights = {c: w / total for c, w in journey_weights.items()}

        for tp in touchpoints:
            channel = tp.source or "unknown"
            weight = journey_weights.get(channel, 0.0)

            breakdown.append(
                {
                    "touchpoint_id": str(tp.id),
                    "channel": channel,
                    "campaign_id": tp.campaign_id,
                    "event_ts": tp.event_ts.isoformat(),
                    "weight": round(weight, 4),
                    "attributed_revenue": round(revenue * weight, 2),
                }
            )

        return {
            "success": True,
            "deal_id": str(deal_id),
            "model_type": "shapley_value",
            "total_revenue": revenue,
            "touchpoint_count": len(touchpoints),
            "breakdown": breakdown,
        }

    async def _get_journey_channels(
        self,
        contact_id: UUID,
        before_time: Optional[datetime],
        channel_type: str = "platform",
    ) -> list[str]:
        """Get channel sequence for a contact's journey."""
        touchpoints = await self._get_journey_touchpoints(contact_id, before_time)

        if channel_type == "platform":
            return [tp.source or "unknown" for tp in touchpoints]
        else:
            return [tp.campaign_id or "direct" for tp in touchpoints]

    async def _get_journey_touchpoints(
        self,
        contact_id: UUID,
        before_time: Optional[datetime],
    ) -> list[Touchpoint]:
        """Get touchpoints for a contact."""
        query = select(Touchpoint).where(
            and_(
                Touchpoint.contact_id == contact_id,
                Touchpoint.tenant_id == self.tenant_id,
            )
        )

        if before_time:
            query = query.where(Touchpoint.event_ts <= before_time)

        query = query.order_by(Touchpoint.event_ts)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_non_converting_contacts(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
    ) -> list[UUID]:
        """Get contacts with touchpoints but no won deals."""
        won_contacts = (
            select(CRMDeal.contact_id)
            .where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                )
            )
            .distinct()
        )

        result = await self.db.execute(
            select(CRMContact.id)
            .where(
                and_(
                    CRMContact.tenant_id == self.tenant_id,
                    CRMContact.touch_count > 0,
                    CRMContact.first_touch_ts >= start_date,
                    CRMContact.first_touch_ts <= end_date,
                    ~CRMContact.id.in_(won_contacts),
                )
            )
            .limit(limit)
        )

        return [row[0] for row in result.fetchall()]
