# =============================================================================
# Stratum AI - Predictive Audience Insights Service
# =============================================================================
"""
Service for predictive audience analysis and targeting recommendations.

Provides:
- Audience performance prediction
- Lookalike quality scoring
- Audience overlap detection
- Targeting recommendations
- Audience expansion suggestions
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics
import math

from app.core.logging import get_logger

logger = get_logger(__name__)


class AudienceType(str, Enum):
    """Types of audiences."""
    CUSTOM = "custom"
    LOOKALIKE = "lookalike"
    INTEREST = "interest"
    BEHAVIORAL = "behavioral"
    DEMOGRAPHIC = "demographic"
    RETARGETING = "retargeting"
    BROAD = "broad"
    FIRST_PARTY = "first_party"


class AudienceQuality(str, Enum):
    """Quality rating for audiences."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    UNKNOWN = "unknown"


class ExpansionPotential(str, Enum):
    """Potential for audience expansion."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SATURATED = "saturated"


@dataclass
class AudienceMetrics:
    """Performance metrics for an audience."""
    reach: int = 0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0

    # Calculated
    ctr: float = 0.0
    cvr: float = 0.0
    roas: float = 0.0
    cpm: float = 0.0
    cpa: float = 0.0

    # Saturation metrics
    frequency: float = 0.0  # avg impressions per user
    unique_reach_percent: float = 0.0

    def calculate_derived(self):
        """Calculate derived metrics."""
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
            self.cpm = (self.spend / self.impressions) * 1000
        if self.clicks > 0:
            self.cvr = (self.conversions / self.clicks) * 100
        if self.spend > 0:
            self.roas = self.revenue / self.spend
        if self.conversions > 0:
            self.cpa = self.spend / self.conversions
        if self.reach > 0:
            self.frequency = self.impressions / self.reach
            self.unique_reach_percent = (self.reach / self.impressions) * 100 if self.impressions else 0


@dataclass
class Audience:
    """Represents an audience for analysis."""
    audience_id: str
    tenant_id: str
    platform: str
    name: str
    audience_type: AudienceType
    size: int  # Estimated audience size
    source_audience_id: Optional[str] = None  # For lookalikes

    # Configuration
    lookalike_percent: Optional[float] = None  # 1-10% for lookalikes
    interest_categories: List[str] = field(default_factory=list)
    demographics: Dict[str, Any] = field(default_factory=dict)

    # Performance
    metrics: AudienceMetrics = field(default_factory=AudienceMetrics)

    # Analysis results
    quality: AudienceQuality = AudienceQuality.UNKNOWN
    quality_score: float = 0.0  # 0-100
    expansion_potential: ExpansionPotential = ExpansionPotential.MEDIUM
    predicted_roas: float = 0.0
    confidence: float = 0.0


@dataclass
class AudienceOverlap:
    """Overlap between two audiences."""
    audience_id_1: str
    audience_id_2: str
    overlap_percent: float  # Percentage of audience_1 that overlaps with audience_2
    overlap_size: int
    recommendation: str


@dataclass
class AudienceInsight:
    """Insight about an audience."""
    audience_id: str
    insight_type: str  # performance, saturation, expansion, targeting
    severity: str  # info, warning, critical
    title: str
    description: str
    recommendation: str
    expected_impact: Optional[str] = None


@dataclass
class AudienceRecommendation:
    """Recommendation for audience optimization."""
    audience_id: Optional[str]
    action: str  # expand, narrow, pause, test, create_lookalike
    priority: str  # high, medium, low
    title: str
    description: str
    expected_impact: Dict[str, float]


class AudienceInsightsService:
    """
    Service for predictive audience insights.

    Usage:
        service = AudienceInsightsService()

        # Analyze an audience
        analysis = service.analyze_audience(audience)

        # Get insights
        insights = service.get_insights(audience_id)

        # Get expansion recommendations
        recommendations = service.get_recommendations(tenant_id)

        # Predict performance
        prediction = service.predict_performance(audience_config)
    """

    def __init__(self):
        self._audiences: Dict[str, Audience] = {}
        self._by_tenant: Dict[str, List[str]] = {}

    def register_audience(
        self,
        audience_id: str,
        tenant_id: str,
        platform: str,
        name: str,
        audience_type: AudienceType,
        size: int,
        **kwargs,
    ) -> Audience:
        """Register an audience for tracking."""
        audience = Audience(
            audience_id=audience_id,
            tenant_id=tenant_id,
            platform=platform,
            name=name,
            audience_type=audience_type,
            size=size,
            **kwargs,
        )

        self._audiences[audience_id] = audience

        if tenant_id not in self._by_tenant:
            self._by_tenant[tenant_id] = []
        self._by_tenant[tenant_id].append(audience_id)

        return audience

    def update_metrics(
        self,
        audience_id: str,
        metrics: AudienceMetrics,
    ):
        """Update audience performance metrics."""
        audience = self._audiences.get(audience_id)
        if not audience:
            return

        metrics.calculate_derived()
        audience.metrics = metrics

        # Re-analyze audience
        self._analyze_audience(audience)

    def _analyze_audience(self, audience: Audience):
        """Analyze audience quality and potential."""
        metrics = audience.metrics

        # Calculate quality score
        quality_score = 0

        # ROAS contribution (40%)
        if metrics.roas > 0:
            roas_score = min(metrics.roas / 3.0, 1.0) * 40
            quality_score += roas_score

        # CVR contribution (25%)
        if metrics.cvr > 0:
            cvr_score = min(metrics.cvr / 5.0, 1.0) * 25
            quality_score += cvr_score

        # CTR contribution (20%)
        if metrics.ctr > 0:
            ctr_score = min(metrics.ctr / 2.0, 1.0) * 20
            quality_score += ctr_score

        # Efficiency contribution (15%)
        if metrics.cpa > 0:
            cpa_score = min(50.0 / metrics.cpa, 1.0) * 15
            quality_score += cpa_score

        audience.quality_score = round(quality_score, 1)

        # Determine quality level
        if quality_score >= 80:
            audience.quality = AudienceQuality.EXCELLENT
        elif quality_score >= 60:
            audience.quality = AudienceQuality.GOOD
        elif quality_score >= 40:
            audience.quality = AudienceQuality.MODERATE
        else:
            audience.quality = AudienceQuality.POOR

        # Analyze expansion potential
        audience.expansion_potential = self._analyze_expansion_potential(audience)

        # Predict ROAS
        audience.predicted_roas = self._predict_audience_roas(audience)
        audience.confidence = self._calculate_confidence(audience)

    def _analyze_expansion_potential(self, audience: Audience) -> ExpansionPotential:
        """Analyze whether audience can be expanded."""
        metrics = audience.metrics

        # Check saturation via frequency
        if metrics.frequency > 10:
            return ExpansionPotential.SATURATED
        elif metrics.frequency > 5:
            return ExpansionPotential.LOW

        # Check reach vs size
        if audience.size > 0 and metrics.reach > 0:
            penetration = metrics.reach / audience.size
            if penetration > 0.5:
                return ExpansionPotential.LOW
            elif penetration > 0.2:
                return ExpansionPotential.MEDIUM
            else:
                return ExpansionPotential.HIGH

        # Default based on audience type
        if audience.audience_type == AudienceType.RETARGETING:
            return ExpansionPotential.LOW
        elif audience.audience_type == AudienceType.LOOKALIKE:
            if audience.lookalike_percent and audience.lookalike_percent < 5:
                return ExpansionPotential.HIGH
            else:
                return ExpansionPotential.MEDIUM
        elif audience.audience_type == AudienceType.BROAD:
            return ExpansionPotential.HIGH
        else:
            return ExpansionPotential.MEDIUM

    def _predict_audience_roas(self, audience: Audience) -> float:
        """Predict expected ROAS for an audience."""
        # Base prediction on current performance
        current_roas = audience.metrics.roas if audience.metrics.roas > 0 else 1.0

        # Adjust based on audience type
        type_multipliers = {
            AudienceType.RETARGETING: 1.3,
            AudienceType.CUSTOM: 1.2,
            AudienceType.LOOKALIKE: 1.1,
            AudienceType.FIRST_PARTY: 1.15,
            AudienceType.INTEREST: 0.95,
            AudienceType.BEHAVIORAL: 1.0,
            AudienceType.DEMOGRAPHIC: 0.85,
            AudienceType.BROAD: 0.8,
        }

        multiplier = type_multipliers.get(audience.audience_type, 1.0)

        # Adjust for saturation
        if audience.expansion_potential == ExpansionPotential.SATURATED:
            multiplier *= 0.85
        elif audience.expansion_potential == ExpansionPotential.LOW:
            multiplier *= 0.95

        # Adjust for lookalike quality
        if audience.audience_type == AudienceType.LOOKALIKE and audience.lookalike_percent:
            # Tighter lookalikes perform better
            if audience.lookalike_percent <= 1:
                multiplier *= 1.15
            elif audience.lookalike_percent <= 3:
                multiplier *= 1.05
            elif audience.lookalike_percent >= 7:
                multiplier *= 0.9

        return round(current_roas * multiplier, 2)

    def _calculate_confidence(self, audience: Audience) -> float:
        """Calculate confidence in predictions."""
        metrics = audience.metrics

        # Base confidence on data volume
        if metrics.conversions >= 100:
            conversion_confidence = 1.0
        elif metrics.conversions >= 30:
            conversion_confidence = 0.8
        elif metrics.conversions >= 10:
            conversion_confidence = 0.6
        else:
            conversion_confidence = 0.3

        # Adjust for spend
        if metrics.spend >= 1000:
            spend_confidence = 1.0
        elif metrics.spend >= 500:
            spend_confidence = 0.85
        elif metrics.spend >= 100:
            spend_confidence = 0.7
        else:
            spend_confidence = 0.5

        return round((conversion_confidence * 0.6 + spend_confidence * 0.4), 2)

    def get_insights(self, audience_id: str) -> List[AudienceInsight]:
        """Get insights for an audience."""
        audience = self._audiences.get(audience_id)
        if not audience:
            return []

        insights = []
        metrics = audience.metrics

        # Saturation insight
        if metrics.frequency > 8:
            insights.append(AudienceInsight(
                audience_id=audience_id,
                insight_type="saturation",
                severity="critical",
                title="High Frequency Detected",
                description=f"Average frequency of {metrics.frequency:.1f} indicates audience fatigue",
                recommendation="Consider expanding audience or rotating creatives",
                expected_impact="Could improve CTR by 15-25%",
            ))
        elif metrics.frequency > 5:
            insights.append(AudienceInsight(
                audience_id=audience_id,
                insight_type="saturation",
                severity="warning",
                title="Moderate Frequency",
                description=f"Frequency of {metrics.frequency:.1f} approaching saturation levels",
                recommendation="Monitor performance and prepare expansion options",
            ))

        # Performance insights
        if audience.quality == AudienceQuality.EXCELLENT:
            insights.append(AudienceInsight(
                audience_id=audience_id,
                insight_type="performance",
                severity="info",
                title="Top Performing Audience",
                description=f"This audience has a quality score of {audience.quality_score}",
                recommendation="Consider increasing budget allocation and creating lookalikes",
                expected_impact="Potential for 20%+ more conversions",
            ))
        elif audience.quality == AudienceQuality.POOR:
            insights.append(AudienceInsight(
                audience_id=audience_id,
                insight_type="performance",
                severity="critical",
                title="Underperforming Audience",
                description=f"Quality score of {audience.quality_score} is below threshold",
                recommendation="Review targeting criteria or pause audience",
            ))

        # Expansion insights
        if audience.expansion_potential == ExpansionPotential.HIGH:
            insights.append(AudienceInsight(
                audience_id=audience_id,
                insight_type="expansion",
                severity="info",
                title="High Expansion Potential",
                description="This audience can support increased budget",
                recommendation="Test 20-30% budget increase gradually",
            ))

        # Lookalike insights
        if audience.audience_type == AudienceType.LOOKALIKE:
            if audience.lookalike_percent and audience.lookalike_percent > 5:
                insights.append(AudienceInsight(
                    audience_id=audience_id,
                    insight_type="targeting",
                    severity="warning",
                    title="Wide Lookalike Range",
                    description=f"{audience.lookalike_percent}% lookalike may include lower-quality users",
                    recommendation="Test tighter 1-3% lookalike for better conversion rates",
                ))

        return insights

    def get_recommendations(
        self,
        tenant_id: str,
        limit: int = 10,
    ) -> List[AudienceRecommendation]:
        """Get audience recommendations for a tenant."""
        audience_ids = self._by_tenant.get(tenant_id, [])
        audiences = [self._audiences[aid] for aid in audience_ids if aid in self._audiences]

        recommendations = []

        # Find top performers for lookalike creation
        top_performers = sorted(
            [a for a in audiences if a.quality_score > 60],
            key=lambda a: a.quality_score,
            reverse=True
        )[:3]

        for audience in top_performers:
            if audience.audience_type in [AudienceType.CUSTOM, AudienceType.FIRST_PARTY]:
                recommendations.append(AudienceRecommendation(
                    audience_id=audience.audience_id,
                    action="create_lookalike",
                    priority="high",
                    title=f"Create Lookalike from {audience.name}",
                    description=f"High-performing audience (score: {audience.quality_score}) is ideal for lookalike creation",
                    expected_impact={
                        "estimated_roas": audience.predicted_roas * 0.9,
                        "reach_multiplier": 10,
                    },
                ))

        # Find underperformers to pause
        poor_performers = [a for a in audiences if a.quality == AudienceQuality.POOR]
        for audience in poor_performers[:2]:
            recommendations.append(AudienceRecommendation(
                audience_id=audience.audience_id,
                action="pause",
                priority="high",
                title=f"Consider Pausing {audience.name}",
                description=f"Low quality score ({audience.quality_score}) with ROAS of {audience.metrics.roas:.2f}",
                expected_impact={
                    "budget_saved": audience.metrics.spend * 0.5,
                    "efficiency_gain": 15,
                },
            ))

        # Find expansion opportunities
        expansion_candidates = [
            a for a in audiences
            if a.expansion_potential == ExpansionPotential.HIGH
            and a.quality_score >= 50
        ]
        for audience in expansion_candidates[:2]:
            recommendations.append(AudienceRecommendation(
                audience_id=audience.audience_id,
                action="expand",
                priority="medium",
                title=f"Expand {audience.name}",
                description=f"Low saturation with good performance supports budget increase",
                expected_impact={
                    "additional_conversions": audience.metrics.conversions * 0.3,
                    "expected_roas": audience.predicted_roas,
                },
            ))

        # General recommendations
        if not recommendations:
            recommendations.append(AudienceRecommendation(
                audience_id=None,
                action="test",
                priority="medium",
                title="Test New Audience Types",
                description="Consider testing interest-based or behavioral audiences",
                expected_impact={},
            ))

        return recommendations[:limit]

    def predict_performance(
        self,
        audience_type: AudienceType,
        size: int,
        platform: str,
        budget: float,
        lookalike_percent: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict performance for a new audience configuration.

        Args:
            audience_type: Type of audience
            size: Estimated audience size
            platform: Ad platform
            budget: Planned daily budget
            lookalike_percent: For lookalikes, the percentage

        Returns:
            Dict with predicted metrics
        """
        # Base CPM estimates by platform
        platform_cpms = {
            "meta": 12.0,
            "google": 15.0,
            "tiktok": 8.0,
            "snapchat": 10.0,
        }

        # Base CTR estimates by audience type
        type_ctrs = {
            AudienceType.RETARGETING: 3.0,
            AudienceType.CUSTOM: 2.5,
            AudienceType.LOOKALIKE: 2.0,
            AudienceType.FIRST_PARTY: 2.8,
            AudienceType.INTEREST: 1.5,
            AudienceType.BEHAVIORAL: 1.8,
            AudienceType.DEMOGRAPHIC: 1.2,
            AudienceType.BROAD: 1.0,
        }

        # Base CVR estimates
        type_cvrs = {
            AudienceType.RETARGETING: 5.0,
            AudienceType.CUSTOM: 4.0,
            AudienceType.LOOKALIKE: 3.0,
            AudienceType.FIRST_PARTY: 4.5,
            AudienceType.INTEREST: 2.0,
            AudienceType.BEHAVIORAL: 2.5,
            AudienceType.DEMOGRAPHIC: 1.5,
            AudienceType.BROAD: 1.2,
        }

        cpm = platform_cpms.get(platform, 12.0)
        ctr = type_ctrs.get(audience_type, 1.5)
        cvr = type_cvrs.get(audience_type, 2.0)

        # Adjust for lookalike quality
        if audience_type == AudienceType.LOOKALIKE and lookalike_percent:
            if lookalike_percent <= 1:
                ctr *= 1.2
                cvr *= 1.3
            elif lookalike_percent <= 3:
                ctr *= 1.1
                cvr *= 1.15
            elif lookalike_percent >= 7:
                ctr *= 0.9
                cvr *= 0.85

        # Calculate predictions
        impressions = (budget / cpm) * 1000
        clicks = impressions * (ctr / 100)
        conversions = clicks * (cvr / 100)

        # Estimate AOV (average order value) by platform
        aov = 80 if platform == "meta" else 100 if platform == "google" else 60
        revenue = conversions * aov

        roas = revenue / budget if budget > 0 else 0
        cpa = budget / conversions if conversions > 0 else 0

        # Calculate reach (assuming 3-5 frequency over period)
        avg_frequency = 4
        reach = int(impressions / avg_frequency)

        return {
            "audience_type": audience_type.value,
            "platform": platform,
            "budget": budget,
            "predictions": {
                "impressions": int(impressions),
                "reach": min(reach, size),
                "clicks": int(clicks),
                "conversions": int(conversions),
                "revenue": round(revenue, 2),
                "roas": round(roas, 2),
                "cpa": round(cpa, 2),
                "ctr": round(ctr, 2),
                "cvr": round(cvr, 2),
            },
            "confidence": 0.7 if size > 100000 else 0.5,
            "notes": [
                f"Based on {platform} average performance for {audience_type.value} audiences",
                "Actual results may vary based on creative quality and competition",
            ],
        }

    def detect_overlap(
        self,
        audience_ids: List[str],
    ) -> List[AudienceOverlap]:
        """Detect overlap between audiences."""
        overlaps = []

        for i, aid1 in enumerate(audience_ids):
            for aid2 in audience_ids[i+1:]:
                audience1 = self._audiences.get(aid1)
                audience2 = self._audiences.get(aid2)

                if not audience1 or not audience2:
                    continue

                # Estimate overlap based on audience types and sizes
                overlap_percent = self._estimate_overlap(audience1, audience2)
                overlap_size = int(min(audience1.size, audience2.size) * overlap_percent / 100)

                if overlap_percent > 20:
                    recommendation = "Consider combining audiences or excluding one from the other"
                elif overlap_percent > 10:
                    recommendation = "Monitor for frequency issues across these audiences"
                else:
                    recommendation = "Low overlap - safe to run simultaneously"

                overlaps.append(AudienceOverlap(
                    audience_id_1=aid1,
                    audience_id_2=aid2,
                    overlap_percent=round(overlap_percent, 1),
                    overlap_size=overlap_size,
                    recommendation=recommendation,
                ))

        return overlaps

    def _estimate_overlap(self, audience1: Audience, audience2: Audience) -> float:
        """Estimate overlap between two audiences."""
        # Same type = higher overlap
        if audience1.audience_type == audience2.audience_type:
            base_overlap = 30

            # Retargeting audiences from same source = very high overlap
            if audience1.audience_type == AudienceType.RETARGETING:
                return 60

            # Lookalikes from same source = high overlap
            if audience1.audience_type == AudienceType.LOOKALIKE:
                if audience1.source_audience_id == audience2.source_audience_id:
                    return 50
                return 25

        # Similar types
        similar_pairs = [
            (AudienceType.INTEREST, AudienceType.BEHAVIORAL),
            (AudienceType.CUSTOM, AudienceType.FIRST_PARTY),
            (AudienceType.DEMOGRAPHIC, AudienceType.BROAD),
        ]

        for pair in similar_pairs:
            if {audience1.audience_type, audience2.audience_type} == set(pair):
                return 25

        # Retargeting vs others = some overlap
        if AudienceType.RETARGETING in [audience1.audience_type, audience2.audience_type]:
            return 15

        # Default
        return 10

    def get_audience(self, audience_id: str) -> Optional[Audience]:
        """Get an audience by ID."""
        return self._audiences.get(audience_id)

    def get_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get summary of audiences for a tenant."""
        audience_ids = self._by_tenant.get(tenant_id, [])
        audiences = [self._audiences[aid] for aid in audience_ids if aid in self._audiences]

        by_type = {}
        by_quality = {}
        total_spend = 0
        total_revenue = 0

        for audience in audiences:
            # By type
            t = audience.audience_type.value
            by_type[t] = by_type.get(t, 0) + 1

            # By quality
            q = audience.quality.value
            by_quality[q] = by_quality.get(q, 0) + 1

            total_spend += audience.metrics.spend
            total_revenue += audience.metrics.revenue

        return {
            "total_audiences": len(audiences),
            "by_type": by_type,
            "by_quality": by_quality,
            "total_spend": round(total_spend, 2),
            "total_revenue": round(total_revenue, 2),
            "overall_roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
        }


# Singleton instance
audience_service = AudienceInsightsService()


# =============================================================================
# Convenience Functions
# =============================================================================

def predict_audience_performance(
    audience_type: str,
    size: int,
    platform: str,
    budget: float,
    lookalike_percent: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Predict performance for an audience configuration.

    Returns:
        Dict with predicted metrics
    """
    try:
        type_enum = AudienceType(audience_type.lower())
    except ValueError:
        type_enum = AudienceType.INTEREST

    return audience_service.predict_performance(
        audience_type=type_enum,
        size=size,
        platform=platform,
        budget=budget,
        lookalike_percent=lookalike_percent,
    )


def get_audience_recommendations(tenant_id: str) -> List[Dict[str, Any]]:
    """Get audience recommendations for a tenant."""
    recommendations = audience_service.get_recommendations(tenant_id)

    return [
        {
            "audience_id": r.audience_id,
            "action": r.action,
            "priority": r.priority,
            "title": r.title,
            "description": r.description,
            "expected_impact": r.expected_impact,
        }
        for r in recommendations
    ]


# =============================================================================
# Advanced Audience Insights Features (P2 Enhancement)
# =============================================================================

@dataclass
class AudienceLTVPrediction:
    """LTV prediction for an audience segment."""
    audience_id: str
    predicted_avg_ltv: float
    ltv_range_low: float
    ltv_range_high: float
    confidence: float
    value_tier: str  # low, medium, high, premium
    recommended_cac_limit: float


@dataclass
class AudienceDecayPrediction:
    """Prediction of audience performance decay."""
    audience_id: str
    current_performance_score: float
    predicted_score_30d: float
    predicted_score_60d: float
    predicted_score_90d: float
    decay_rate: float  # % per month
    time_to_refresh_days: int
    factors: List[str]


@dataclass
class AudienceCluster:
    """Cluster of similar audiences."""
    cluster_id: str
    cluster_name: str
    audiences: List[str]
    common_traits: List[str]
    avg_performance: Dict[str, float]
    recommendation: str


class AudienceLTVPredictor:
    """
    Predicts LTV for audience segments.

    Estimates:
    - Average customer LTV for audience
    - LTV distribution
    - Recommended CAC limits
    """

    # LTV multipliers by audience type
    LTV_MULTIPLIERS = {
        AudienceType.FIRST_PARTY: 1.5,
        AudienceType.LOOKALIKE: 1.0,
        AudienceType.INTEREST: 0.7,
        AudienceType.BEHAVIORAL: 0.9,
        AudienceType.RETARGETING: 1.8,
        AudienceType.CUSTOM: 1.2,
    }

    def __init__(self):
        self._baseline_ltv: Dict[str, float] = {}

    def set_baseline_ltv(self, tenant_id: str, baseline: float):
        """Set baseline LTV for a tenant."""
        self._baseline_ltv[tenant_id] = baseline

    def predict(
        self,
        audience_id: str,
        audience_type: AudienceType,
        tenant_id: str,
        historical_performance: Optional[Dict[str, float]] = None,
    ) -> AudienceLTVPrediction:
        """Predict LTV for an audience."""
        baseline = self._baseline_ltv.get(tenant_id, 100)

        # Apply type multiplier
        multiplier = self.LTV_MULTIPLIERS.get(audience_type, 1.0)
        base_ltv = baseline * multiplier

        # Adjust based on historical performance
        if historical_performance:
            roas = historical_performance.get("roas", 2)
            cvr = historical_performance.get("conversion_rate", 0.02)

            # Higher ROAS/CVR suggests better quality customers
            perf_multiplier = 0.8 + (min(roas, 5) / 5) * 0.3 + (min(cvr, 0.1) / 0.1) * 0.2
            base_ltv *= perf_multiplier

        predicted_ltv = round(base_ltv, 2)

        # Calculate range
        variance = 0.3 if audience_type in [AudienceType.LOOKALIKE, AudienceType.INTEREST] else 0.2
        ltv_low = round(predicted_ltv * (1 - variance), 2)
        ltv_high = round(predicted_ltv * (1 + variance), 2)

        # Determine value tier
        if predicted_ltv >= baseline * 1.5:
            value_tier = "premium"
        elif predicted_ltv >= baseline:
            value_tier = "high"
        elif predicted_ltv >= baseline * 0.5:
            value_tier = "medium"
        else:
            value_tier = "low"

        # Calculate confidence
        confidence = 0.7 if historical_performance else 0.5

        # Recommended CAC
        recommended_cac = round(predicted_ltv / 3, 2)  # LTV:CAC ratio of 3:1

        return AudienceLTVPrediction(
            audience_id=audience_id,
            predicted_avg_ltv=predicted_ltv,
            ltv_range_low=ltv_low,
            ltv_range_high=ltv_high,
            confidence=confidence,
            value_tier=value_tier,
            recommended_cac_limit=recommended_cac,
        )


class AudienceDecayPredictor:
    """
    Predicts audience performance decay over time.

    Factors:
    - Audience fatigue
    - Saturation
    - Market changes
    - Competition
    """

    # Base decay rates by audience type (% per month)
    BASE_DECAY_RATES = {
        AudienceType.FIRST_PARTY: 0.02,  # 2% per month
        AudienceType.LOOKALIKE: 0.05,
        AudienceType.INTEREST: 0.08,
        AudienceType.BEHAVIORAL: 0.06,
        AudienceType.RETARGETING: 0.10,  # Higher decay for retargeting
        AudienceType.CUSTOM: 0.04,
    }

    def __init__(self):
        self._performance_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def record_performance(self, audience_id: str, score: float):
        """Record audience performance for decay tracking."""
        if audience_id not in self._performance_history:
            self._performance_history[audience_id] = []

        self._performance_history[audience_id].append((
            datetime.now(timezone.utc),
            score,
        ))

        # Keep last 180 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        self._performance_history[audience_id] = [
            (t, s) for t, s in self._performance_history[audience_id] if t > cutoff
        ]

    def predict(
        self,
        audience_id: str,
        audience_type: AudienceType,
        current_score: float,
        audience_age_days: int,
    ) -> AudienceDecayPrediction:
        """Predict audience decay."""
        base_decay = self.BASE_DECAY_RATES.get(audience_type, 0.05)

        # Adjust decay based on historical data
        history = self._performance_history.get(audience_id, [])
        if len(history) >= 3:
            scores = [s for _, s in sorted(history)]
            if scores[0] > 0:
                observed_decay = (scores[0] - scores[-1]) / scores[0] / max(1, len(scores))
                decay_rate = (base_decay + observed_decay) / 2
            else:
                decay_rate = base_decay
        else:
            decay_rate = base_decay

        # Older audiences decay faster
        age_multiplier = 1 + (audience_age_days / 365) * 0.5
        adjusted_decay = decay_rate * age_multiplier

        # Predict future scores
        score_30d = current_score * (1 - adjusted_decay)
        score_60d = current_score * (1 - adjusted_decay * 2)
        score_90d = current_score * (1 - adjusted_decay * 3)

        # Determine time to refresh (when score drops below 50% of current)
        if adjusted_decay > 0:
            time_to_refresh = int(0.5 / adjusted_decay * 30)
        else:
            time_to_refresh = 365

        # Identify factors
        factors = []
        if audience_type == AudienceType.RETARGETING:
            factors.append("Retargeting audiences decay faster due to user fatigue")
        if audience_age_days > 90:
            factors.append(f"Audience is {audience_age_days} days old - consider refresh")
        if adjusted_decay > 0.08:
            factors.append("High decay rate detected - monitor closely")
        if not factors:
            factors.append("Normal decay pattern")

        return AudienceDecayPrediction(
            audience_id=audience_id,
            current_performance_score=round(current_score, 2),
            predicted_score_30d=round(max(0, score_30d), 2),
            predicted_score_60d=round(max(0, score_60d), 2),
            predicted_score_90d=round(max(0, score_90d), 2),
            decay_rate=round(adjusted_decay * 100, 2),
            time_to_refresh_days=time_to_refresh,
            factors=factors,
        )


class AudienceClusterAnalyzer:
    """
    Clusters audiences by similarity.

    Groups audiences based on:
    - Performance patterns
    - Demographic signals
    - Behavioral traits
    """

    def __init__(self):
        self._audience_features: Dict[str, Dict[str, float]] = {}

    def record_audience_features(
        self,
        audience_id: str,
        features: Dict[str, float],
    ):
        """Record features for an audience."""
        self._audience_features[audience_id] = features

    def cluster_audiences(
        self,
        audience_ids: List[str],
        n_clusters: int = 4,
    ) -> List[AudienceCluster]:
        """Cluster audiences into groups."""
        if len(audience_ids) < n_clusters:
            n_clusters = len(audience_ids)

        if n_clusters < 2:
            return []

        # Get features for all audiences
        audiences_with_features = [
            (aid, self._audience_features.get(aid, {}))
            for aid in audience_ids
            if aid in self._audience_features
        ]

        if len(audiences_with_features) < n_clusters:
            return []

        # Simple k-means-style clustering
        # In production, would use sklearn or similar
        clusters: Dict[int, List[str]] = {i: [] for i in range(n_clusters)}

        # Initial assignment based on performance buckets
        sorted_audiences = sorted(
            audiences_with_features,
            key=lambda x: x[1].get("roas", 0),
        )

        bucket_size = len(sorted_audiences) // n_clusters
        for i, (aid, _) in enumerate(sorted_audiences):
            cluster_idx = min(i // max(1, bucket_size), n_clusters - 1)
            clusters[cluster_idx].append(aid)

        # Create cluster objects
        result = []
        cluster_names = ["Low Performers", "Below Average", "Above Average", "Top Performers"]

        for cluster_idx, audience_list in clusters.items():
            if not audience_list:
                continue

            # Calculate cluster stats
            cluster_features = [
                self._audience_features[aid]
                for aid in audience_list
                if aid in self._audience_features
            ]

            avg_performance = {}
            if cluster_features:
                for key in cluster_features[0]:
                    values = [f.get(key, 0) for f in cluster_features]
                    avg_performance[key] = round(statistics.mean(values), 3)

            # Identify common traits
            common_traits = self._identify_common_traits(cluster_features)

            # Generate recommendation
            recommendation = self._generate_cluster_recommendation(
                cluster_idx, n_clusters, avg_performance
            )

            result.append(AudienceCluster(
                cluster_id=f"cluster_{cluster_idx}",
                cluster_name=cluster_names[cluster_idx] if cluster_idx < len(cluster_names) else f"Cluster {cluster_idx + 1}",
                audiences=audience_list,
                common_traits=common_traits,
                avg_performance=avg_performance,
                recommendation=recommendation,
            ))

        return result

    def _identify_common_traits(
        self,
        features: List[Dict[str, float]],
    ) -> List[str]:
        """Identify common traits in cluster."""
        if not features:
            return []

        traits = []

        # Check for high/low patterns
        avg_roas = statistics.mean([f.get("roas", 0) for f in features])
        avg_ctr = statistics.mean([f.get("ctr", 0) for f in features])
        avg_cvr = statistics.mean([f.get("conversion_rate", 0) for f in features])

        if avg_roas > 3:
            traits.append("High ROAS performers")
        elif avg_roas < 1.5:
            traits.append("Below-target ROAS")

        if avg_ctr > 2:
            traits.append("Strong engagement")
        elif avg_ctr < 0.5:
            traits.append("Low engagement")

        if avg_cvr > 0.03:
            traits.append("High conversion intent")

        if not traits:
            traits.append("Mixed performance patterns")

        return traits

    def _generate_cluster_recommendation(
        self,
        cluster_idx: int,
        n_clusters: int,
        performance: Dict[str, float],
    ) -> str:
        """Generate recommendation for cluster."""
        if cluster_idx >= n_clusters - 1:  # Top cluster
            return "Scale budget for these top-performing audiences"
        elif cluster_idx == 0:  # Bottom cluster
            return "Review and potentially pause low performers"
        elif performance.get("roas", 0) > 2:
            return "Good performers - test incremental budget increases"
        else:
            return "Monitor closely - optimize targeting before scaling"

    def find_similar_audiences(
        self,
        target_audience_id: str,
        candidate_ids: List[str],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find audiences similar to target."""
        target_features = self._audience_features.get(target_audience_id)
        if not target_features:
            return []

        similarities = []

        for aid in candidate_ids:
            if aid == target_audience_id:
                continue

            features = self._audience_features.get(aid)
            if not features:
                continue

            # Calculate similarity
            similarity = self._calculate_similarity(target_features, features)
            similarities.append({
                "audience_id": aid,
                "similarity_score": round(similarity, 3),
                "features": features,
            })

        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similarities[:top_n]

    def _calculate_similarity(
        self,
        features_a: Dict[str, float],
        features_b: Dict[str, float],
    ) -> float:
        """Calculate similarity between feature sets."""
        common_keys = set(features_a.keys()) & set(features_b.keys())
        if not common_keys:
            return 0

        total_sim = 0
        for key in common_keys:
            val_a = features_a[key]
            val_b = features_b[key]
            max_val = max(abs(val_a), abs(val_b), 1)
            diff = abs(val_a - val_b) / max_val
            total_sim += 1 - min(diff, 1)

        return total_sim / len(common_keys)


# Singleton instances for P2 enhancements
audience_ltv_predictor = AudienceLTVPredictor()
audience_decay_predictor = AudienceDecayPredictor()
audience_cluster_analyzer = AudienceClusterAnalyzer()
