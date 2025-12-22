# =============================================================================
# Stratum AI - Ad Fatigue Analysis Service
# =============================================================================
"""
Comprehensive ad fatigue calculation engine.
Analyzes creative performance degradation over time to identify
assets that need refreshing.

Fatigue Score Components (0-100 scale):
- Usage Factor (0-25): Based on times_used and campaign count
- Age Factor (0-25): Days since first deployment
- Impression Saturation (0-25): Volume relative to audience size
- Performance Decay (0-25): CTR/engagement trend decline

Higher score = More fatigued = Needs refresh
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreativeAsset, Campaign
from app.core.logging import get_logger

logger = get_logger(__name__)


class FatigueStatus(str, Enum):
    """Fatigue status classification."""
    FRESH = "fresh"        # 0-25: New or recently refreshed
    HEALTHY = "healthy"    # 26-50: Performing well
    WATCH = "watch"        # 51-70: Monitor closely
    FATIGUED = "fatigued"  # 71-85: Needs attention
    CRITICAL = "critical"  # 86-100: Immediate action needed


@dataclass
class FatigueBreakdown:
    """Detailed breakdown of fatigue score components."""
    usage_score: float
    age_score: float
    saturation_score: float
    decay_score: float
    total_score: float
    status: FatigueStatus
    recommendations: List[str]


@dataclass
class AssetPerformanceHistory:
    """Historical performance data for decay analysis."""
    date: datetime
    impressions: int
    clicks: int
    ctr: float
    conversions: Optional[int] = None


class AdFatigueService:
    """
    Service for calculating and managing ad creative fatigue.

    Fatigue indicates when an ad creative has been seen too often
    by the target audience and performance is declining.
    """

    # Configuration thresholds
    USAGE_WEIGHT = 0.25
    AGE_WEIGHT = 0.25
    SATURATION_WEIGHT = 0.25
    DECAY_WEIGHT = 0.25

    # Usage thresholds
    MAX_OPTIMAL_USES = 10  # Beyond this, fatigue increases
    CRITICAL_USES = 25     # Above this, high fatigue

    # Age thresholds (days)
    FRESH_DAYS = 7
    HEALTHY_DAYS = 30
    WATCH_DAYS = 60
    FATIGUED_DAYS = 90

    # Impression saturation thresholds
    LOW_SATURATION = 100_000
    MEDIUM_SATURATION = 500_000
    HIGH_SATURATION = 1_000_000
    CRITICAL_SATURATION = 2_000_000

    # CTR decay thresholds
    HEALTHY_CTR = 2.0
    WATCH_CTR = 1.5
    LOW_CTR = 1.0
    CRITICAL_CTR = 0.5

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    def calculate_fatigue_score(
        self,
        asset: CreativeAsset,
        historical_ctr: Optional[List[float]] = None,
        audience_size: Optional[int] = None,
    ) -> FatigueBreakdown:
        """
        Calculate comprehensive fatigue score for an asset.

        Args:
            asset: The creative asset to analyze
            historical_ctr: List of CTR values over time (oldest to newest)
            audience_size: Target audience size for saturation calculation

        Returns:
            FatigueBreakdown with detailed scoring
        """
        # 1. Usage Factor (0-25)
        usage_score = self._calculate_usage_score(asset.times_used)

        # 2. Age Factor (0-25)
        age_score = self._calculate_age_score(asset.first_used_at)

        # 3. Impression Saturation (0-25)
        saturation_score = self._calculate_saturation_score(
            asset.impressions,
            audience_size
        )

        # 4. Performance Decay (0-25)
        decay_score = self._calculate_decay_score(
            asset.ctr,
            historical_ctr
        )

        # Calculate total score
        total_score = (
            usage_score * self.USAGE_WEIGHT +
            age_score * self.AGE_WEIGHT +
            saturation_score * self.SATURATION_WEIGHT +
            decay_score * self.DECAY_WEIGHT
        ) * 100  # Scale to 0-100

        total_score = min(100, max(0, total_score))

        # Determine status
        status = self._get_fatigue_status(total_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            usage_score, age_score, saturation_score, decay_score, status
        )

        return FatigueBreakdown(
            usage_score=round(usage_score * 25, 1),
            age_score=round(age_score * 25, 1),
            saturation_score=round(saturation_score * 25, 1),
            decay_score=round(decay_score * 25, 1),
            total_score=round(total_score, 1),
            status=status,
            recommendations=recommendations,
        )

    def _calculate_usage_score(self, times_used: int) -> float:
        """
        Calculate fatigue from usage frequency.
        Score from 0 (unused) to 1 (heavily used).
        """
        if times_used <= 0:
            return 0.0
        elif times_used <= self.MAX_OPTIMAL_USES:
            return times_used / self.MAX_OPTIMAL_USES * 0.4
        elif times_used <= self.CRITICAL_USES:
            return 0.4 + ((times_used - self.MAX_OPTIMAL_USES) /
                         (self.CRITICAL_USES - self.MAX_OPTIMAL_USES) * 0.4)
        else:
            return min(1.0, 0.8 + (times_used - self.CRITICAL_USES) * 0.02)

    def _calculate_age_score(self, first_used_at: Optional[datetime]) -> float:
        """
        Calculate fatigue based on asset age.
        Score from 0 (new) to 1 (old).
        """
        if not first_used_at:
            return 0.0

        now = datetime.now(timezone.utc)
        days_active = (now - first_used_at).days

        if days_active <= self.FRESH_DAYS:
            return days_active / self.FRESH_DAYS * 0.1
        elif days_active <= self.HEALTHY_DAYS:
            return 0.1 + ((days_active - self.FRESH_DAYS) /
                         (self.HEALTHY_DAYS - self.FRESH_DAYS) * 0.2)
        elif days_active <= self.WATCH_DAYS:
            return 0.3 + ((days_active - self.HEALTHY_DAYS) /
                         (self.WATCH_DAYS - self.HEALTHY_DAYS) * 0.3)
        elif days_active <= self.FATIGUED_DAYS:
            return 0.6 + ((days_active - self.WATCH_DAYS) /
                         (self.FATIGUED_DAYS - self.WATCH_DAYS) * 0.3)
        else:
            return min(1.0, 0.9 + (days_active - self.FATIGUED_DAYS) * 0.001)

    def _calculate_saturation_score(
        self,
        impressions: int,
        audience_size: Optional[int] = None
    ) -> float:
        """
        Calculate impression saturation fatigue.
        Uses frequency estimation if audience size is known.
        """
        if impressions <= 0:
            return 0.0

        # If we have audience size, calculate frequency
        if audience_size and audience_size > 0:
            frequency = impressions / audience_size
            # Optimal frequency is 3-7, beyond 10 is over-saturation
            if frequency <= 3:
                return frequency / 3 * 0.2
            elif frequency <= 7:
                return 0.2 + ((frequency - 3) / 4 * 0.3)
            elif frequency <= 10:
                return 0.5 + ((frequency - 7) / 3 * 0.3)
            else:
                return min(1.0, 0.8 + (frequency - 10) * 0.02)

        # Fallback to absolute impressions
        if impressions <= self.LOW_SATURATION:
            return impressions / self.LOW_SATURATION * 0.2
        elif impressions <= self.MEDIUM_SATURATION:
            return 0.2 + ((impressions - self.LOW_SATURATION) /
                         (self.MEDIUM_SATURATION - self.LOW_SATURATION) * 0.3)
        elif impressions <= self.HIGH_SATURATION:
            return 0.5 + ((impressions - self.MEDIUM_SATURATION) /
                         (self.HIGH_SATURATION - self.MEDIUM_SATURATION) * 0.3)
        else:
            return min(1.0, 0.8 + (impressions - self.HIGH_SATURATION) /
                      self.CRITICAL_SATURATION * 0.2)

    def _calculate_decay_score(
        self,
        current_ctr: Optional[float],
        historical_ctr: Optional[List[float]] = None
    ) -> float:
        """
        Calculate performance decay fatigue.
        Measures CTR decline over time.
        """
        if current_ctr is None:
            return 0.0

        base_score = 0.0

        # Score based on absolute CTR level
        if current_ctr >= self.HEALTHY_CTR:
            base_score = 0.1
        elif current_ctr >= self.WATCH_CTR:
            base_score = 0.3
        elif current_ctr >= self.LOW_CTR:
            base_score = 0.5
        elif current_ctr >= self.CRITICAL_CTR:
            base_score = 0.7
        else:
            base_score = 0.9

        # If we have historical data, check for decay trend
        if historical_ctr and len(historical_ctr) >= 3:
            # Calculate trend using simple linear regression slope
            avg_early = sum(historical_ctr[:len(historical_ctr)//2]) / (len(historical_ctr)//2)
            avg_late = sum(historical_ctr[len(historical_ctr)//2:]) / (len(historical_ctr) - len(historical_ctr)//2)

            if avg_early > 0:
                decay_rate = (avg_early - avg_late) / avg_early
                # Significant decay adds to score
                if decay_rate > 0.3:  # 30%+ decline
                    base_score = min(1.0, base_score + 0.2)
                elif decay_rate > 0.2:  # 20%+ decline
                    base_score = min(1.0, base_score + 0.1)

        return base_score

    def _get_fatigue_status(self, score: float) -> FatigueStatus:
        """Map score to fatigue status."""
        if score <= 25:
            return FatigueStatus.FRESH
        elif score <= 50:
            return FatigueStatus.HEALTHY
        elif score <= 70:
            return FatigueStatus.WATCH
        elif score <= 85:
            return FatigueStatus.FATIGUED
        else:
            return FatigueStatus.CRITICAL

    def _generate_recommendations(
        self,
        usage_score: float,
        age_score: float,
        saturation_score: float,
        decay_score: float,
        status: FatigueStatus
    ) -> List[str]:
        """Generate actionable recommendations based on fatigue analysis."""
        recommendations = []

        if status in [FatigueStatus.FRESH, FatigueStatus.HEALTHY]:
            recommendations.append("Creative performing well - continue monitoring")
            return recommendations

        # High usage recommendations
        if usage_score > 0.6:
            recommendations.append("Reduce ad frequency - create new variations")
            recommendations.append("Consider audience segmentation to spread exposure")

        # Age-based recommendations
        if age_score > 0.6:
            recommendations.append("Creative aging - schedule refresh within 2 weeks")
            recommendations.append("Test new creative concepts against this asset")

        # Saturation recommendations
        if saturation_score > 0.6:
            recommendations.append("High impression volume - expand to new audiences")
            recommendations.append("Consider exclusion of frequent viewers")

        # Performance decay recommendations
        if decay_score > 0.6:
            recommendations.append("CTR declining - update creative messaging")
            recommendations.append("A/B test new visuals and copy")
            recommendations.append("Review targeting - audience may have shifted")

        if status == FatigueStatus.CRITICAL:
            recommendations.insert(0, "⚠️ URGENT: Replace this creative immediately")

        return recommendations

    async def calculate_all_assets_fatigue(
        self,
        tenant_id: str
    ) -> Dict[str, any]:
        """
        Calculate fatigue for all assets in a tenant.
        Useful for batch processing and dashboard views.
        """
        if not self.db:
            raise ValueError("Database session required for batch operations")

        result = await self.db.execute(
            select(CreativeAsset)
            .where(
                CreativeAsset.tenant_id == tenant_id,
                CreativeAsset.is_deleted == False
            )
        )
        assets = result.scalars().all()

        summary = {
            "total_assets": len(assets),
            "by_status": {
                FatigueStatus.FRESH.value: 0,
                FatigueStatus.HEALTHY.value: 0,
                FatigueStatus.WATCH.value: 0,
                FatigueStatus.FATIGUED.value: 0,
                FatigueStatus.CRITICAL.value: 0,
            },
            "assets_needing_attention": [],
            "avg_fatigue_score": 0.0,
        }

        total_score = 0.0

        for asset in assets:
            breakdown = self.calculate_fatigue_score(asset)

            # Update asset in DB
            asset.fatigue_score = breakdown.total_score

            # Update summary
            summary["by_status"][breakdown.status.value] += 1
            total_score += breakdown.total_score

            if breakdown.status in [FatigueStatus.FATIGUED, FatigueStatus.CRITICAL]:
                summary["assets_needing_attention"].append({
                    "id": asset.id,
                    "name": asset.name,
                    "score": breakdown.total_score,
                    "status": breakdown.status.value,
                    "recommendations": breakdown.recommendations[:2],  # Top 2 recs
                })

        if assets:
            summary["avg_fatigue_score"] = round(total_score / len(assets), 1)

        await self.db.commit()

        logger.info(
            "fatigue_batch_calculated",
            tenant_id=tenant_id,
            total_assets=len(assets),
            avg_score=summary["avg_fatigue_score"],
            critical_count=summary["by_status"][FatigueStatus.CRITICAL.value],
        )

        return summary

    @staticmethod
    def get_fatigue_color(score: float) -> str:
        """Get color code for fatigue score visualization."""
        if score <= 25:
            return "#22c55e"  # Green - Fresh
        elif score <= 50:
            return "#84cc16"  # Lime - Healthy
        elif score <= 70:
            return "#f59e0b"  # Amber - Watch
        elif score <= 85:
            return "#f97316"  # Orange - Fatigued
        else:
            return "#ef4444"  # Red - Critical
