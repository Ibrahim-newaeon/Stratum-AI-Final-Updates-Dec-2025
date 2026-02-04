# =============================================================================
# Stratum AI - Markov Chain Attribution Model
# =============================================================================
"""
Data-driven attribution using Markov Chain models.

Calculates channel contribution based on:
1. Transition probabilities between channels
2. Removal effect (what happens when a channel is removed)
3. Conversion probability from each state

This provides a mathematically sound way to attribute credit
based on actual customer behavior patterns.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import CRMDeal, Touchpoint

logger = get_logger(__name__)


# Special states in the Markov chain
STATE_START = "__start__"
STATE_CONVERSION = "__conversion__"
STATE_NULL = "__null__"  # Non-conversion


class MarkovChainModel:
    """
    Markov Chain model for attribution.

    Models the customer journey as a sequence of states (channels),
    with transition probabilities between states.
    """

    def __init__(self):
        # Transition counts: {from_state: {to_state: count}}
        self.transition_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # Total transitions from each state
        self.state_totals: dict[str, int] = defaultdict(int)
        # All observed channels
        self.channels: set[str] = set()
        # Number of journeys used for training
        self.journey_count: int = 0
        self.converting_journeys: int = 0
        self.non_converting_journeys: int = 0

    def add_journey(self, channels: list[str], converted: bool) -> None:
        """
        Add a customer journey to the model.

        Args:
            channels: List of channel touchpoints in order
            converted: Whether the journey resulted in a conversion
        """
        if not channels:
            return

        self.journey_count += 1
        if converted:
            self.converting_journeys += 1
        else:
            self.non_converting_journeys += 1

        # Add all channels to the set
        self.channels.update(channels)

        # Build state sequence: start -> channels -> end_state
        states = [STATE_START] + channels
        end_state = STATE_CONVERSION if converted else STATE_NULL
        states.append(end_state)

        # Count transitions
        for i in range(len(states) - 1):
            from_state = states[i]
            to_state = states[i + 1]
            self.transition_counts[from_state][to_state] += 1
            self.state_totals[from_state] += 1

    def get_transition_probability(self, from_state: str, to_state: str) -> float:
        """Get probability of transitioning from one state to another."""
        total = self.state_totals.get(from_state, 0)
        if total == 0:
            return 0.0
        count = self.transition_counts.get(from_state, {}).get(to_state, 0)
        return count / total

    def get_transition_matrix(self) -> dict[str, dict[str, float]]:
        """Get the full transition probability matrix."""
        matrix = {}
        all_states = list(self.channels) + [STATE_START, STATE_CONVERSION, STATE_NULL]

        for from_state in all_states:
            matrix[from_state] = {}
            for to_state in all_states:
                matrix[from_state][to_state] = self.get_transition_probability(from_state, to_state)

        return matrix

    def calculate_conversion_probability(
        self,
        excluded_channel: Optional[str] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> float:
        """
        Calculate overall conversion probability using absorption probabilities.

        If excluded_channel is provided, calculates probability without that channel.
        Uses iterative method to solve the system of equations.
        """
        # Build list of transient states (channels + start)
        transient_states = [STATE_START] + [c for c in self.channels if c != excluded_channel]

        # Initialize conversion probabilities
        conv_prob = {state: 0.0 for state in transient_states}

        # Iteratively update until convergence
        for iteration in range(max_iterations):
            new_conv_prob = {}
            max_change = 0.0

            for state in transient_states:
                # P(conversion from state) = P(direct conversion) + sum(P(transition) * P(conversion from next))
                prob = self.get_transition_probability(state, STATE_CONVERSION)

                for next_state in transient_states:
                    if next_state != state:
                        trans_prob = self.get_transition_probability(state, next_state)
                        prob += trans_prob * conv_prob.get(next_state, 0.0)

                new_conv_prob[state] = prob
                max_change = max(max_change, abs(prob - conv_prob.get(state, 0.0)))

            conv_prob = new_conv_prob

            if max_change < tolerance:
                break

        return conv_prob.get(STATE_START, 0.0)

    def calculate_removal_effects(self) -> dict[str, float]:
        """
        Calculate the removal effect for each channel.

        Removal effect = (baseline_conversion - conversion_without_channel) / baseline_conversion

        Higher values indicate more important channels.
        """
        # Baseline conversion probability (with all channels)
        baseline = self.calculate_conversion_probability()

        if baseline == 0:
            return {channel: 0.0 for channel in self.channels}

        removal_effects = {}
        for channel in self.channels:
            # Conversion probability without this channel
            prob_without = self.calculate_conversion_probability(excluded_channel=channel)
            # Removal effect
            effect = (baseline - prob_without) / baseline
            removal_effects[channel] = max(0.0, effect)  # Ensure non-negative

        return removal_effects

    def calculate_attribution_weights(self) -> dict[str, float]:
        """
        Calculate attribution weights based on removal effects.

        Normalizes removal effects to sum to 1.0.
        """
        removal_effects = self.calculate_removal_effects()

        total_effect = sum(removal_effects.values())
        if total_effect == 0:
            # Equal distribution if no effects
            n = len(self.channels)
            return {channel: 1.0 / n for channel in self.channels} if n > 0 else {}

        return {channel: effect / total_effect for channel, effect in removal_effects.items()}

    def get_model_stats(self) -> dict[str, Any]:
        """Get model statistics."""
        return {
            "journey_count": self.journey_count,
            "converting_journeys": self.converting_journeys,
            "non_converting_journeys": self.non_converting_journeys,
            "conversion_rate": (
                self.converting_journeys / self.journey_count if self.journey_count > 0 else 0
            ),
            "unique_channels": len(self.channels),
            "channels": list(self.channels),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to dictionary."""
        return {
            "transition_counts": {k: dict(v) for k, v in self.transition_counts.items()},
            "state_totals": dict(self.state_totals),
            "channels": list(self.channels),
            "journey_count": self.journey_count,
            "converting_journeys": self.converting_journeys,
            "non_converting_journeys": self.non_converting_journeys,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarkovChainModel":
        """Deserialize model from dictionary."""
        model = cls()
        model.transition_counts = defaultdict(
            lambda: defaultdict(int),
            {k: defaultdict(int, v) for k, v in data.get("transition_counts", {}).items()},
        )
        model.state_totals = defaultdict(int, data.get("state_totals", {}))
        model.channels = set(data.get("channels", []))
        model.journey_count = data.get("journey_count", 0)
        model.converting_journeys = data.get("converting_journeys", 0)
        model.non_converting_journeys = data.get("non_converting_journeys", 0)
        return model


class MarkovAttributionService:
    """
    Service for training and using Markov Chain attribution models.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def train_model(
        self,
        start_date: datetime,
        end_date: datetime,
        channel_type: str = "platform",  # platform or campaign
        include_non_converting: bool = True,
        min_journeys: int = 100,
    ) -> dict[str, Any]:
        """
        Train a Markov Chain model on historical journey data.

        Args:
            start_date: Start of training period
            end_date: End of training period
            channel_type: What to use as channels (platform or campaign)
            include_non_converting: Include journeys that didn't convert
            min_journeys: Minimum journeys required for training

        Returns:
            Training results with model statistics
        """
        model = MarkovChainModel()

        # Get converting journeys (won deals with touchpoints)
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

        # Optionally include non-converting journeys
        if include_non_converting:
            # Get contacts without won deals in the period
            non_converting = await self._get_non_converting_contacts(
                start_date,
                end_date,
                limit=len(deals) * 2,  # Sample 2x converting
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

        # Calculate attribution weights
        weights = model.calculate_attribution_weights()
        removal_effects = model.calculate_removal_effects()
        transition_matrix = model.get_transition_matrix()

        return {
            "success": True,
            "model_type": "markov_chain",
            "channel_type": channel_type,
            "training_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "stats": model.get_model_stats(),
            "attribution_weights": weights,
            "removal_effects": removal_effects,
            "baseline_conversion_rate": model.calculate_conversion_probability(),
            "model_data": model.to_dict(),
        }

    async def attribute_with_model(
        self,
        model_data: dict[str, Any],
        deal_id: UUID,
    ) -> dict[str, Any]:
        """
        Attribute a deal using a trained Markov model.

        Args:
            model_data: Serialized model data
            deal_id: Deal to attribute

        Returns:
            Attribution breakdown
        """
        model = MarkovChainModel.from_dict(model_data)
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

        # Get journey
        touchpoints = await self._get_journey_touchpoints(
            deal.contact_id,
            before_time=deal.won_at,
        )

        if not touchpoints:
            return {"success": False, "error": "no_touchpoints"}

        # Calculate attributed revenue per touchpoint
        revenue = deal.amount or 0
        breakdown = []

        for tp in touchpoints:
            channel = tp.source or "unknown"
            weight = weights.get(channel, 0.0)

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
            "model_type": "markov_chain",
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
        from app.models.crm import CRMContact

        # Subquery for contacts with won deals
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

        # Get contacts with touchpoints but not in won_contacts
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
