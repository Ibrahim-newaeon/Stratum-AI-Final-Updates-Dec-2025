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
            "linkedin": 25.0,
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
