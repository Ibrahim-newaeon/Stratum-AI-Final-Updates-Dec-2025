# =============================================================================
# Stratum AI - RFM Customer Segmentation
# =============================================================================
"""
RFM (Recency, Frequency, Monetary) based customer segmentation.

Provides more granular segmentation than simple LTV thresholds
by considering customer behavior patterns.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class RFMSegment(str, Enum):
    """
    RFM-based customer segments for more granular targeting.

    Based on Recency (R), Frequency (F), and Monetary (M) scoring.
    Each dimension is scored 1-5 (5 being best).
    """

    CHAMPIONS = "champions"  # R=5, F=5, M=5 - Best customers
    LOYAL_CUSTOMERS = "loyal"  # R=4-5, F=3-5, M=4-5
    POTENTIAL_LOYALISTS = "potential"  # R=4-5, F=1-3, M=1-3
    NEW_CUSTOMERS = "new"  # R=5, F=1, M=1-3
    PROMISING = "promising"  # R=4, F=1, M=1-2
    NEED_ATTENTION = "need_attention"  # R=3, F=2-3, M=2-3
    ABOUT_TO_SLEEP = "about_to_sleep"  # R=2-3, F=1-2, M=1-2
    AT_RISK = "at_risk"  # R=1-2, F=3-5, M=3-5
    CANT_LOSE = "cant_lose"  # R=1, F=4-5, M=4-5
    HIBERNATING = "hibernating"  # R=1-2, F=1-2, M=1-2
    LOST = "lost"  # R=1, F=1, M=1


@dataclass
class RFMScore:
    """RFM scoring result for a customer."""

    customer_id: str
    recency_days: int
    frequency: int
    monetary: float

    recency_score: int  # 1-5
    frequency_score: int  # 1-5
    monetary_score: int  # 1-5

    rfm_score: str  # e.g., "555" for best customer
    rfm_segment: RFMSegment

    # Composite scores
    rfm_composite: float  # Weighted average
    percentile_rank: float  # Overall percentile


@dataclass
class CustomerRFMData:
    """Customer data for RFM analysis."""

    customer_id: str
    days_since_last_order: int
    total_orders: int
    total_revenue: float
    first_order_date: Optional[datetime] = None
    last_order_date: Optional[datetime] = None


class RFMSegmenter:
    """
    RFM-based customer segmentation.

    Provides more granular segmentation than simple LTV thresholds
    by considering customer behavior patterns.

    Usage:
        segmenter = RFMSegmenter()
        segmenter.fit(customers)  # Calibrate quintiles
        score = segmenter.score_customer(customer)
        results = segmenter.segment_customers(customers)
    """

    # Segment mapping based on RFM score patterns
    SEGMENT_MAPPING = {
        # Champions: Recent, frequent, high spenders
        (5, 5, 5): RFMSegment.CHAMPIONS,
        (5, 5, 4): RFMSegment.CHAMPIONS,
        (5, 4, 5): RFMSegment.CHAMPIONS,
        (4, 5, 5): RFMSegment.CHAMPIONS,
        # Loyal Customers: Good across all dimensions
        (5, 4, 4): RFMSegment.LOYAL_CUSTOMERS,
        (4, 4, 5): RFMSegment.LOYAL_CUSTOMERS,
        (4, 4, 4): RFMSegment.LOYAL_CUSTOMERS,
        (4, 5, 4): RFMSegment.LOYAL_CUSTOMERS,
        (5, 3, 5): RFMSegment.LOYAL_CUSTOMERS,
        (4, 3, 5): RFMSegment.LOYAL_CUSTOMERS,
        # Potential Loyalists: Recent but lower frequency/monetary
        (5, 3, 3): RFMSegment.POTENTIAL_LOYALISTS,
        (5, 2, 3): RFMSegment.POTENTIAL_LOYALISTS,
        (5, 3, 2): RFMSegment.POTENTIAL_LOYALISTS,
        (4, 3, 3): RFMSegment.POTENTIAL_LOYALISTS,
        (5, 2, 2): RFMSegment.POTENTIAL_LOYALISTS,
        # New Customers: Very recent, first purchase
        (5, 1, 3): RFMSegment.NEW_CUSTOMERS,
        (5, 1, 2): RFMSegment.NEW_CUSTOMERS,
        (5, 1, 1): RFMSegment.NEW_CUSTOMERS,
        # Promising: Fairly recent, low engagement
        (4, 1, 2): RFMSegment.PROMISING,
        (4, 1, 1): RFMSegment.PROMISING,
        (4, 2, 1): RFMSegment.PROMISING,
        # Need Attention: Average across dimensions
        (3, 3, 3): RFMSegment.NEED_ATTENTION,
        (3, 2, 3): RFMSegment.NEED_ATTENTION,
        (3, 3, 2): RFMSegment.NEED_ATTENTION,
        (3, 2, 2): RFMSegment.NEED_ATTENTION,
        # About to Sleep: Declining engagement
        (2, 2, 2): RFMSegment.ABOUT_TO_SLEEP,
        (2, 2, 1): RFMSegment.ABOUT_TO_SLEEP,
        (2, 1, 2): RFMSegment.ABOUT_TO_SLEEP,
        (3, 1, 2): RFMSegment.ABOUT_TO_SLEEP,
        (3, 1, 1): RFMSegment.ABOUT_TO_SLEEP,
        # At Risk: Were good customers, now inactive
        (2, 4, 4): RFMSegment.AT_RISK,
        (2, 4, 3): RFMSegment.AT_RISK,
        (2, 3, 4): RFMSegment.AT_RISK,
        (2, 3, 3): RFMSegment.AT_RISK,
        (1, 3, 4): RFMSegment.AT_RISK,
        (1, 4, 3): RFMSegment.AT_RISK,
        # Can't Lose: High value but churning
        (1, 5, 5): RFMSegment.CANT_LOSE,
        (1, 5, 4): RFMSegment.CANT_LOSE,
        (1, 4, 5): RFMSegment.CANT_LOSE,
        (1, 4, 4): RFMSegment.CANT_LOSE,
        (2, 5, 5): RFMSegment.CANT_LOSE,
        (2, 5, 4): RFMSegment.CANT_LOSE,
        # Hibernating: Inactive, low value
        (2, 1, 1): RFMSegment.HIBERNATING,
        (1, 2, 2): RFMSegment.HIBERNATING,
        (1, 2, 1): RFMSegment.HIBERNATING,
        (1, 1, 2): RFMSegment.HIBERNATING,
        # Lost: Completely inactive
        (1, 1, 1): RFMSegment.LOST,
    }

    # Marketing recommendations per segment
    SEGMENT_ACTIONS = {
        RFMSegment.CHAMPIONS: "Reward with loyalty program, early access, referral program",
        RFMSegment.LOYAL_CUSTOMERS: "Upsell premium products, ask for reviews",
        RFMSegment.POTENTIAL_LOYALISTS: "Offer membership, cross-sell related products",
        RFMSegment.NEW_CUSTOMERS: "Onboarding sequence, product education, first-purchase discount",
        RFMSegment.PROMISING: "Create brand awareness, offer free trials",
        RFMSegment.NEED_ATTENTION: "Limited-time offers, personalized recommendations",
        RFMSegment.ABOUT_TO_SLEEP: "Win-back campaign, share valuable content",
        RFMSegment.AT_RISK: "Send personalized re-engagement, offer renewal discounts",
        RFMSegment.CANT_LOSE: "Win-back urgently, highest priority outreach, surveys",
        RFMSegment.HIBERNATING: "Offer deep discounts, reconnect with new products",
        RFMSegment.LOST: "Revive with aggressive discounts or remove from active list",
    }

    def __init__(
        self,
        recency_weight: float = 0.35,
        frequency_weight: float = 0.35,
        monetary_weight: float = 0.30,
    ):
        """
        Initialize RFM segmenter.

        Args:
            recency_weight: Weight for recency in composite score
            frequency_weight: Weight for frequency in composite score
            monetary_weight: Weight for monetary in composite score
        """
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight
        self.monetary_weight = monetary_weight

        # Quintile boundaries (will be calculated from data)
        self.recency_quintiles: list[float] = []
        self.frequency_quintiles: list[float] = []
        self.monetary_quintiles: list[float] = []
        self._is_fitted = False

    def fit(self, customers: list[CustomerRFMData]) -> "RFMSegmenter":
        """
        Calculate quintile boundaries from customer data.

        This should be called before scoring to calibrate thresholds
        based on your actual customer distribution.
        """
        if not customers:
            logger.warning("No customers provided for RFM fitting")
            return self

        recency_values = [c.days_since_last_order for c in customers]
        frequency_values = [c.total_orders for c in customers]
        monetary_values = [c.total_revenue for c in customers]

        # Calculate quintiles (20th, 40th, 60th, 80th percentiles)
        self.recency_quintiles = [float(np.percentile(recency_values, p)) for p in [20, 40, 60, 80]]
        self.frequency_quintiles = [
            float(np.percentile(frequency_values, p)) for p in [20, 40, 60, 80]
        ]
        self.monetary_quintiles = [
            float(np.percentile(monetary_values, p)) for p in [20, 40, 60, 80]
        ]

        self._is_fitted = True
        logger.info(
            "RFM segmenter fitted",
            customers=len(customers),
            recency_q=self.recency_quintiles,
            frequency_q=self.frequency_quintiles,
            monetary_q=self.monetary_quintiles,
        )

        return self

    def _score_value(
        self,
        value: float,
        quintiles: list[float],
        reverse: bool = False,
    ) -> int:
        """
        Score a value from 1-5 based on quintiles.

        Args:
            value: The value to score
            quintiles: List of 4 quintile boundaries
            reverse: If True, lower values get higher scores (for recency)
        """
        if not quintiles:
            # Default scoring if not fitted
            return 3

        score = 5
        for i, threshold in enumerate(quintiles):
            if value <= threshold:
                score = i + 1
                break

        if reverse:
            score = 6 - score  # Invert: 1->5, 2->4, etc.

        return score

    def score_customer(self, customer: CustomerRFMData) -> RFMScore:
        """
        Calculate RFM score for a single customer.

        Args:
            customer: Customer data with recency, frequency, monetary values

        Returns:
            RFMScore with individual scores and segment assignment
        """
        # Calculate individual scores
        r_score = self._score_value(
            customer.days_since_last_order,
            self.recency_quintiles,
            reverse=True,  # Lower recency (more recent) = better
        )
        f_score = self._score_value(
            customer.total_orders,
            self.frequency_quintiles,
        )
        m_score = self._score_value(
            customer.total_revenue,
            self.monetary_quintiles,
        )

        # RFM string (e.g., "555" for best customer)
        rfm_str = f"{r_score}{f_score}{m_score}"

        # Get segment
        segment = self._get_segment(r_score, f_score, m_score)

        # Calculate composite score (weighted average)
        composite = (
            r_score * self.recency_weight
            + f_score * self.frequency_weight
            + m_score * self.monetary_weight
        )

        # Percentile rank (0-100)
        percentile = (composite - 1) / 4 * 100  # Normalize to 0-100

        return RFMScore(
            customer_id=customer.customer_id,
            recency_days=customer.days_since_last_order,
            frequency=customer.total_orders,
            monetary=customer.total_revenue,
            recency_score=r_score,
            frequency_score=f_score,
            monetary_score=m_score,
            rfm_score=rfm_str,
            rfm_segment=segment,
            rfm_composite=round(composite, 2),
            percentile_rank=round(percentile, 1),
        )

    def _get_segment(self, r: int, f: int, m: int) -> RFMSegment:
        """Determine segment from RFM scores using mapping and rules."""
        # Try exact match first
        if (r, f, m) in self.SEGMENT_MAPPING:
            return self.SEGMENT_MAPPING[(r, f, m)]

        # Fall back to rules-based assignment
        avg_score = (r + f + m) / 3

        if r >= 4 and f >= 4 and m >= 4:
            return RFMSegment.CHAMPIONS
        elif r >= 4 and (f >= 3 or m >= 4):
            return RFMSegment.LOYAL_CUSTOMERS
        elif r >= 4:
            return RFMSegment.POTENTIAL_LOYALISTS
        elif r == 5 and f == 1:
            return RFMSegment.NEW_CUSTOMERS
        elif r <= 2 and f >= 4:
            return RFMSegment.CANT_LOSE
        elif r <= 2 and f >= 3:
            return RFMSegment.AT_RISK
        elif r <= 2 and avg_score < 2:
            return RFMSegment.LOST
        elif r <= 2:
            return RFMSegment.HIBERNATING
        elif avg_score >= 3:
            return RFMSegment.NEED_ATTENTION
        else:
            return RFMSegment.ABOUT_TO_SLEEP

    def segment_customers(
        self,
        customers: list[CustomerRFMData],
        auto_fit: bool = True,
    ) -> dict[str, Any]:
        """
        Segment all customers and return distribution with actionable insights.

        Args:
            customers: List of customer data
            auto_fit: If True, automatically fit quintiles if not already done

        Returns:
            Dict with segment distribution, statistics, and recommendations
        """
        if not customers:
            return {"error": "No customers provided", "segments": {}}

        # Fit quintiles if not already done
        if auto_fit and not self._is_fitted:
            self.fit(customers)

        scores = [self.score_customer(c) for c in customers]

        # Group by segment
        segments: dict[RFMSegment, list[RFMScore]] = {}
        for score in scores:
            if score.rfm_segment not in segments:
                segments[score.rfm_segment] = []
            segments[score.rfm_segment].append(score)

        # Build results with actionable recommendations
        segment_insights = {}
        for segment, segment_scores in segments.items():
            avg_monetary = sum(s.monetary for s in segment_scores) / len(segment_scores)
            avg_frequency = sum(s.frequency for s in segment_scores) / len(segment_scores)
            avg_recency = sum(s.recency_days for s in segment_scores) / len(segment_scores)
            total_value = sum(s.monetary for s in segment_scores)

            segment_insights[segment.value] = {
                "count": len(segment_scores),
                "percent": round(len(segment_scores) / len(customers) * 100, 1),
                "avg_monetary": round(avg_monetary, 2),
                "avg_frequency": round(avg_frequency, 1),
                "avg_recency_days": round(avg_recency, 0),
                "total_value": round(total_value, 2),
                "value_share_percent": round(
                    total_value / sum(c.total_revenue for c in customers) * 100, 1
                )
                if sum(c.total_revenue for c in customers) > 0
                else 0,
                "avg_rfm_composite": round(
                    sum(s.rfm_composite for s in segment_scores) / len(segment_scores), 2
                ),
                "recommended_action": self.SEGMENT_ACTIONS.get(segment, "Analyze further"),
            }

        # Sort segments by value share
        sorted_segments = dict(
            sorted(
                segment_insights.items(),
                key=lambda x: x[1]["total_value"],
                reverse=True,
            )
        )

        return {
            "total_customers": len(customers),
            "total_revenue": round(sum(c.total_revenue for c in customers), 2),
            "segments": sorted_segments,
            "quintile_thresholds": {
                "recency_days": self.recency_quintiles,
                "frequency": self.frequency_quintiles,
                "monetary": self.monetary_quintiles,
            },
            "segment_count": len(segments),
        }

    def get_segment_customers(
        self,
        customers: list[CustomerRFMData],
        segment: RFMSegment,
    ) -> list[RFMScore]:
        """
        Get all customers in a specific segment.

        Useful for targeted marketing campaigns.
        """
        if not self._is_fitted:
            self.fit(customers)

        return [
            self.score_customer(c)
            for c in customers
            if self.score_customer(c).rfm_segment == segment
        ]

    def get_high_value_at_risk(
        self,
        customers: list[CustomerRFMData],
    ) -> list[RFMScore]:
        """
        Get high-value customers who are at risk of churning.

        These are priority targets for retention campaigns.
        """
        at_risk_segments = {
            RFMSegment.AT_RISK,
            RFMSegment.CANT_LOSE,
            RFMSegment.ABOUT_TO_SLEEP,
        }

        if not self._is_fitted:
            self.fit(customers)

        return [
            self.score_customer(c)
            for c in customers
            if self.score_customer(c).rfm_segment in at_risk_segments
        ]


# Singleton instance
rfm_segmenter = RFMSegmenter()


# =============================================================================
# Convenience Functions
# =============================================================================


def segment_customers_rfm(
    customers: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convenience function to segment customers using RFM analysis.

    Args:
        customers: List of customer dicts with:
            - customer_id
            - days_since_last_order
            - total_orders
            - total_revenue

    Returns:
        Segmentation results with recommendations
    """
    customer_data = [
        CustomerRFMData(
            customer_id=c["customer_id"],
            days_since_last_order=c.get("days_since_last_order", 0),
            total_orders=c.get("total_orders", 1),
            total_revenue=c.get("total_revenue", 0),
        )
        for c in customers
    ]

    segmenter = RFMSegmenter()
    return segmenter.segment_customers(customer_data)


def get_customer_rfm_score(
    customer_id: str,
    days_since_last_order: int,
    total_orders: int,
    total_revenue: float,
) -> dict[str, Any]:
    """
    Get RFM score for a single customer.

    Note: Uses default quintiles if segmenter hasn't been fitted.
    For accurate scoring, fit the segmenter with your customer base first.
    """
    customer = CustomerRFMData(
        customer_id=customer_id,
        days_since_last_order=days_since_last_order,
        total_orders=total_orders,
        total_revenue=total_revenue,
    )

    score = rfm_segmenter.score_customer(customer)

    return {
        "customer_id": score.customer_id,
        "rfm_score": score.rfm_score,
        "segment": score.rfm_segment.value,
        "scores": {
            "recency": score.recency_score,
            "frequency": score.frequency_score,
            "monetary": score.monetary_score,
        },
        "composite_score": score.rfm_composite,
        "percentile_rank": score.percentile_rank,
        "recommended_action": RFMSegmenter.SEGMENT_ACTIONS.get(
            score.rfm_segment, "Analyze further"
        ),
    }


# =============================================================================
# Segment Transition Tracking
# =============================================================================


@dataclass
class SegmentTransition:
    """A customer's transition between segments."""

    customer_id: str
    from_segment: RFMSegment
    to_segment: RFMSegment
    transition_date: datetime
    days_in_previous_segment: int
    monetary_change: float
    frequency_change: int


class SegmentTransitionTracker:
    """
    Track how customers move between RFM segments over time.

    Enables:
    - Identifying at-risk customers before they churn
    - Measuring campaign effectiveness on segment movement
    - Predicting future segment transitions
    """

    # Transition sentiment: positive, negative, neutral
    TRANSITION_SENTIMENT = {
        (RFMSegment.LOST, RFMSegment.HIBERNATING): "positive",
        (RFMSegment.HIBERNATING, RFMSegment.ABOUT_TO_SLEEP): "positive",
        (RFMSegment.ABOUT_TO_SLEEP, RFMSegment.NEED_ATTENTION): "positive",
        (RFMSegment.NEED_ATTENTION, RFMSegment.PROMISING): "positive",
        (RFMSegment.PROMISING, RFMSegment.NEW_CUSTOMERS): "positive",
        (RFMSegment.NEW_CUSTOMERS, RFMSegment.POTENTIAL_LOYALISTS): "positive",
        (RFMSegment.POTENTIAL_LOYALISTS, RFMSegment.LOYAL_CUSTOMERS): "positive",
        (RFMSegment.LOYAL_CUSTOMERS, RFMSegment.CHAMPIONS): "positive",
        (RFMSegment.AT_RISK, RFMSegment.NEED_ATTENTION): "positive",
        (RFMSegment.CANT_LOSE, RFMSegment.LOYAL_CUSTOMERS): "positive",
        # Negative transitions
        (RFMSegment.CHAMPIONS, RFMSegment.LOYAL_CUSTOMERS): "negative",
        (RFMSegment.LOYAL_CUSTOMERS, RFMSegment.AT_RISK): "negative",
        (RFMSegment.AT_RISK, RFMSegment.CANT_LOSE): "negative",
        (RFMSegment.CANT_LOSE, RFMSegment.LOST): "negative",
        (RFMSegment.POTENTIAL_LOYALISTS, RFMSegment.ABOUT_TO_SLEEP): "negative",
        (RFMSegment.NEW_CUSTOMERS, RFMSegment.LOST): "negative",
    }

    def __init__(self):
        self.transition_history: list[SegmentTransition] = []
        self.customer_segment_history: dict[str, list[tuple[datetime, RFMSegment]]] = {}

    def record_snapshot(
        self,
        snapshot_date: datetime,
        customer_scores: list[RFMScore],
    ) -> list[SegmentTransition]:
        """
        Record a snapshot of customer segments and detect transitions.

        Call this periodically (e.g., weekly) to track segment movements.
        """
        transitions = []

        for score in customer_scores:
            customer_id = score.customer_id
            current_segment = score.rfm_segment

            # Check for transition
            if customer_id in self.customer_segment_history:
                history = self.customer_segment_history[customer_id]
                if history:
                    last_date, last_segment = history[-1]

                    if last_segment != current_segment:
                        transition = SegmentTransition(
                            customer_id=customer_id,
                            from_segment=last_segment,
                            to_segment=current_segment,
                            transition_date=snapshot_date,
                            days_in_previous_segment=(snapshot_date - last_date).days,
                            monetary_change=0,  # Would be calculated from full data
                            frequency_change=0,
                        )
                        transitions.append(transition)
                        self.transition_history.append(transition)

            # Update history
            if customer_id not in self.customer_segment_history:
                self.customer_segment_history[customer_id] = []
            self.customer_segment_history[customer_id].append((snapshot_date, current_segment))

        return transitions

    def get_transition_matrix(self) -> dict[str, dict[str, int]]:
        """
        Get transition counts between segments.

        Returns a matrix showing how many customers moved from each segment to each other.
        """
        matrix: dict[str, dict[str, int]] = {}

        for segment in RFMSegment:
            matrix[segment.value] = {s.value: 0 for s in RFMSegment}

        for transition in self.transition_history:
            from_seg = transition.from_segment.value
            to_seg = transition.to_segment.value
            matrix[from_seg][to_seg] += 1

        return matrix

    def get_transition_probabilities(self) -> dict[str, dict[str, float]]:
        """Get probability matrix for segment transitions."""
        counts = self.get_transition_matrix()
        probs: dict[str, dict[str, float]] = {}

        for from_seg, to_counts in counts.items():
            total = sum(to_counts.values())
            if total > 0:
                probs[from_seg] = {to_seg: count / total for to_seg, count in to_counts.items()}
            else:
                probs[from_seg] = {to_seg: 0 for to_seg in to_counts}

        return probs

    def get_at_risk_customers(
        self,
        customer_scores: list[RFMScore],
        lookback_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Identify customers likely to transition to worse segments.

        Uses historical transition patterns to predict at-risk customers.
        """
        probs = self.get_transition_probabilities()
        at_risk = []

        for score in customer_scores:
            segment = score.rfm_segment.value
            if segment not in probs:
                continue

            # Calculate risk of negative transition
            negative_prob = 0
            for to_seg, prob in probs[segment].items():
                transition_key = (score.rfm_segment, RFMSegment(to_seg))
                sentiment = self.TRANSITION_SENTIMENT.get(transition_key, "neutral")
                if sentiment == "negative":
                    negative_prob += prob

            if negative_prob > 0.3:  # >30% chance of negative transition
                at_risk.append(
                    {
                        "customer_id": score.customer_id,
                        "current_segment": segment,
                        "churn_risk": round(negative_prob, 2),
                        "rfm_score": score.rfm_score,
                        "recommended_action": RFMSegmenter.SEGMENT_ACTIONS.get(
                            score.rfm_segment, "Engage proactively"
                        ),
                    }
                )

        return sorted(at_risk, key=lambda x: x["churn_risk"], reverse=True)

    def analyze_campaign_impact(
        self,
        campaign_start: datetime,
        campaign_end: datetime,
        target_segment: RFMSegment,
    ) -> dict[str, Any]:
        """
        Analyze how a campaign impacted segment transitions.

        Returns metrics on segment movement during campaign period.
        """
        relevant_transitions = [
            t
            for t in self.transition_history
            if campaign_start <= t.transition_date <= campaign_end
            and t.from_segment == target_segment
        ]

        positive = sum(
            1
            for t in relevant_transitions
            if self.TRANSITION_SENTIMENT.get((t.from_segment, t.to_segment)) == "positive"
        )
        negative = sum(
            1
            for t in relevant_transitions
            if self.TRANSITION_SENTIMENT.get((t.from_segment, t.to_segment)) == "negative"
        )
        neutral = len(relevant_transitions) - positive - negative

        return {
            "campaign_period": {
                "start": campaign_start.isoformat(),
                "end": campaign_end.isoformat(),
            },
            "target_segment": target_segment.value,
            "total_transitions": len(relevant_transitions),
            "positive_transitions": positive,
            "negative_transitions": negative,
            "neutral_transitions": neutral,
            "net_positive_rate": (positive - negative) / len(relevant_transitions)
            if relevant_transitions
            else 0,
        }


# =============================================================================
# Customer Lifetime Value Integration
# =============================================================================


@dataclass
class CustomerCLV:
    """Customer Lifetime Value calculation result."""

    customer_id: str
    rfm_segment: RFMSegment
    historical_value: float
    predicted_clv: float
    clv_confidence: float
    expected_lifetime_months: int
    monthly_expected_value: float
    acquisition_cost: Optional[float] = None
    clv_to_cac_ratio: Optional[float] = None


class CLVPredictor:
    """
    Predict Customer Lifetime Value using RFM segmentation.

    Combines RFM segments with historical purchase patterns
    to predict future customer value.
    """

    # Expected retention rates by segment
    SEGMENT_RETENTION_RATES = {
        RFMSegment.CHAMPIONS: 0.95,
        RFMSegment.LOYAL_CUSTOMERS: 0.85,
        RFMSegment.POTENTIAL_LOYALISTS: 0.70,
        RFMSegment.NEW_CUSTOMERS: 0.40,
        RFMSegment.PROMISING: 0.50,
        RFMSegment.NEED_ATTENTION: 0.60,
        RFMSegment.ABOUT_TO_SLEEP: 0.30,
        RFMSegment.AT_RISK: 0.25,
        RFMSegment.CANT_LOSE: 0.35,
        RFMSegment.HIBERNATING: 0.15,
        RFMSegment.LOST: 0.05,
    }

    # Average order multiplier by segment
    SEGMENT_ORDER_MULTIPLIERS = {
        RFMSegment.CHAMPIONS: 1.5,
        RFMSegment.LOYAL_CUSTOMERS: 1.2,
        RFMSegment.POTENTIAL_LOYALISTS: 1.0,
        RFMSegment.NEW_CUSTOMERS: 0.8,
        RFMSegment.PROMISING: 0.7,
        RFMSegment.NEED_ATTENTION: 0.9,
        RFMSegment.ABOUT_TO_SLEEP: 0.6,
        RFMSegment.AT_RISK: 0.8,
        RFMSegment.CANT_LOSE: 1.1,
        RFMSegment.HIBERNATING: 0.4,
        RFMSegment.LOST: 0.2,
    }

    def __init__(
        self,
        discount_rate: float = 0.10,  # 10% annual discount rate
        prediction_horizon_months: int = 24,
    ):
        self.discount_rate = discount_rate
        self.prediction_horizon_months = prediction_horizon_months
        self.monthly_discount = (1 + discount_rate) ** (1 / 12) - 1

    def predict_clv(
        self,
        customer: CustomerRFMData,
        rfm_score: RFMScore,
        acquisition_cost: Optional[float] = None,
    ) -> CustomerCLV:
        """
        Predict lifetime value for a customer.

        Uses segment-based retention rates and historical behavior
        to project future value.
        """
        segment = rfm_score.rfm_segment
        retention_rate = self.SEGMENT_RETENTION_RATES.get(segment, 0.5)
        order_multiplier = self.SEGMENT_ORDER_MULTIPLIERS.get(segment, 1.0)

        # Calculate historical metrics
        months_as_customer = (
            max(1, customer.days_since_last_order / 30) if customer.first_order_date else 12
        )
        avg_monthly_value = customer.total_revenue / months_as_customer
        avg_order_value = customer.total_revenue / max(1, customer.total_orders)

        # Project future value using geometric series
        # CLV = Σ (retention^t * monthly_value) / (1 + discount)^t
        predicted_clv = 0
        for month in range(1, self.prediction_horizon_months + 1):
            survival_prob = retention_rate**month
            expected_value = avg_monthly_value * order_multiplier * survival_prob
            discounted_value = expected_value / ((1 + self.monthly_discount) ** month)
            predicted_clv += discounted_value

        # Estimate expected lifetime
        if retention_rate > 0 and retention_rate < 1:
            expected_lifetime = int(1 / (1 - retention_rate))
        else:
            expected_lifetime = self.prediction_horizon_months

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(customer, rfm_score)

        # Calculate CLV:CAC ratio if acquisition cost provided
        clv_cac_ratio = None
        if acquisition_cost and acquisition_cost > 0:
            clv_cac_ratio = (customer.total_revenue + predicted_clv) / acquisition_cost

        return CustomerCLV(
            customer_id=customer.customer_id,
            rfm_segment=segment,
            historical_value=customer.total_revenue,
            predicted_clv=round(predicted_clv, 2),
            clv_confidence=round(confidence, 2),
            expected_lifetime_months=expected_lifetime,
            monthly_expected_value=round(avg_monthly_value * order_multiplier, 2),
            acquisition_cost=acquisition_cost,
            clv_to_cac_ratio=round(clv_cac_ratio, 2) if clv_cac_ratio else None,
        )

    def _calculate_confidence(
        self,
        customer: CustomerRFMData,
        score: RFMScore,
    ) -> float:
        """Calculate confidence in CLV prediction."""
        confidence = 0.5

        # More orders = higher confidence
        if customer.total_orders >= 10:
            confidence += 0.2
        elif customer.total_orders >= 5:
            confidence += 0.1

        # Longer history = higher confidence
        if customer.first_order_date:
            days_as_customer = (datetime.now(UTC) - customer.first_order_date).days
            if days_as_customer >= 365:
                confidence += 0.15
            elif days_as_customer >= 180:
                confidence += 0.1

        # Higher RFM composite = more predictable behavior
        if score.rfm_composite >= 4:
            confidence += 0.1

        return min(0.95, confidence)

    def segment_clv_summary(
        self,
        customers: list[CustomerRFMData],
        scores: list[RFMScore],
    ) -> dict[str, Any]:
        """
        Get CLV summary by segment.

        Returns aggregate CLV metrics for each segment.
        """
        segment_data: dict[RFMSegment, list[CustomerCLV]] = {}

        for customer, score in zip(customers, scores, strict=False):
            clv = self.predict_clv(customer, score)
            if clv.rfm_segment not in segment_data:
                segment_data[clv.rfm_segment] = []
            segment_data[clv.rfm_segment].append(clv)

        summary = {}
        for segment, clvs in segment_data.items():
            total_historical = sum(c.historical_value for c in clvs)
            total_predicted = sum(c.predicted_clv for c in clvs)
            avg_clv = total_predicted / len(clvs) if clvs else 0
            avg_lifetime = sum(c.expected_lifetime_months for c in clvs) / len(clvs) if clvs else 0

            summary[segment.value] = {
                "customer_count": len(clvs),
                "total_historical_value": round(total_historical, 2),
                "total_predicted_clv": round(total_predicted, 2),
                "avg_predicted_clv": round(avg_clv, 2),
                "avg_expected_lifetime_months": round(avg_lifetime, 1),
                "total_portfolio_value": round(total_historical + total_predicted, 2),
            }

        return {
            "segments": summary,
            "total_portfolio_clv": round(
                sum(s["total_portfolio_value"] for s in summary.values()), 2
            ),
        }


# Singleton instances
segment_tracker = SegmentTransitionTracker()
clv_predictor = CLVPredictor()
