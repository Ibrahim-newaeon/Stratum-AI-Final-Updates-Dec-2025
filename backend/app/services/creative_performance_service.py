# =============================================================================
# Stratum AI - Creative Performance Tracking Service
# =============================================================================
"""
Service for tracking and analyzing creative performance across platforms.

Provides:
- Creative-level performance metrics (ROAS, CTR, CVR, etc.)
- Creative fatigue detection
- A/B test support for creatives
- Asset-level analysis (images, videos, copy)
- Cross-platform creative performance comparison
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class CreativeType(str, Enum):
    """Types of creative assets."""

    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    COLLECTION = "collection"
    STORIES = "stories"
    REELS = "reels"
    TEXT_ONLY = "text_only"
    DYNAMIC = "dynamic"


class CreativeStatus(str, Enum):
    """Status of a creative."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    FATIGUED = "fatigued"  # Performance declining
    WINNER = "winner"  # Top performer
    LOSER = "loser"  # Underperforming


class FatigueLevel(str, Enum):
    """Level of creative fatigue."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CreativeMetrics:
    """Performance metrics for a creative."""

    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0

    # Calculated metrics
    ctr: float = 0.0
    cvr: float = 0.0
    roas: float = 0.0
    cpc: float = 0.0
    cpm: float = 0.0
    cpa: float = 0.0

    # Engagement metrics (platform-specific)
    video_views: int = 0
    video_completions: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    saves: int = 0

    # Video metrics
    avg_watch_time_seconds: float = 0.0
    video_completion_rate: float = 0.0

    def calculate_derived(self):
        """Calculate derived metrics."""
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
            self.cpm = (self.spend / self.impressions) * 1000
        if self.clicks > 0:
            self.cvr = (self.conversions / self.clicks) * 100
            self.cpc = self.spend / self.clicks
        if self.spend > 0:
            self.roas = self.revenue / self.spend
        if self.conversions > 0:
            self.cpa = self.spend / self.conversions
        if self.video_views > 0:
            self.video_completion_rate = (self.video_completions / self.video_views) * 100


@dataclass
class DailyCreativeMetrics:
    """Daily snapshot of creative metrics."""

    date: datetime
    metrics: CreativeMetrics


@dataclass
class Creative:
    """Represents a creative asset."""

    creative_id: str
    tenant_id: str
    platform: str
    campaign_id: str
    ad_set_id: Optional[str] = None

    # Creative metadata
    name: str = ""
    creative_type: CreativeType = CreativeType.IMAGE
    status: CreativeStatus = CreativeStatus.ACTIVE

    # Asset information
    asset_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    headline: Optional[str] = None
    body_text: Optional[str] = None
    cta_type: Optional[str] = None

    # Video-specific
    video_duration_seconds: Optional[float] = None

    # Tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    first_impression_at: Optional[datetime] = None
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Performance
    lifetime_metrics: CreativeMetrics = field(default_factory=CreativeMetrics)
    daily_metrics: list[DailyCreativeMetrics] = field(default_factory=list)

    # Fatigue tracking
    fatigue_level: FatigueLevel = FatigueLevel.NONE
    fatigue_score: float = 0.0  # 0-100, higher = more fatigued
    days_active: int = 0

    # A/B testing
    test_group: Optional[str] = None  # For creative A/B tests


@dataclass
class CreativeFatigueAnalysis:
    """Analysis of creative fatigue."""

    creative_id: str
    fatigue_level: FatigueLevel
    fatigue_score: float
    indicators: list[str]
    recommendation: str
    trend_data: dict[str, list[float]]


@dataclass
class CreativeComparison:
    """Comparison between creatives."""

    creative_ids: list[str]
    winner_id: Optional[str]
    metrics_comparison: dict[str, dict[str, float]]
    statistical_significance: bool
    confidence_level: float


class CreativePerformanceService:
    """
    Service for tracking and analyzing creative performance.

    Usage:
        service = CreativePerformanceService()

        # Record creative metrics
        service.record_metrics(
            creative_id="creative_123",
            tenant_id="tenant_1",
            platform="meta",
            campaign_id="campaign_456",
            metrics=CreativeMetrics(
                impressions=10000,
                clicks=500,
                conversions=25,
                spend=1000.0,
                revenue=2500.0,
            )
        )

        # Check for fatigue
        fatigue = service.analyze_fatigue("creative_123")

        # Compare creatives
        comparison = service.compare_creatives(["creative_123", "creative_456"])
    """

    def __init__(self):
        self._creatives: dict[str, Creative] = {}
        self._by_campaign: dict[str, list[str]] = defaultdict(list)
        self._by_tenant: dict[str, list[str]] = defaultdict(list)
        self._by_platform: dict[str, list[str]] = defaultdict(list)

    def register_creative(
        self,
        creative_id: str,
        tenant_id: str,
        platform: str,
        campaign_id: str,
        creative_type: CreativeType = CreativeType.IMAGE,
        name: str = "",
        **kwargs,
    ) -> Creative:
        """
        Register a new creative for tracking.

        Args:
            creative_id: Unique creative identifier
            tenant_id: Tenant ID
            platform: Platform name
            campaign_id: Parent campaign ID
            creative_type: Type of creative
            name: Creative name
            **kwargs: Additional creative attributes

        Returns:
            The registered creative
        """
        creative = Creative(
            creative_id=creative_id,
            tenant_id=tenant_id,
            platform=platform,
            campaign_id=campaign_id,
            creative_type=creative_type,
            name=name,
            **kwargs,
        )

        self._creatives[creative_id] = creative
        self._by_campaign[campaign_id].append(creative_id)
        self._by_tenant[tenant_id].append(creative_id)
        self._by_platform[platform].append(creative_id)

        logger.info(f"Registered creative: {creative_id} ({name})")

        return creative

    def record_metrics(
        self,
        creative_id: str,
        tenant_id: str,
        platform: str,
        campaign_id: str,
        metrics: CreativeMetrics,
        date: Optional[datetime] = None,
        creative_type: CreativeType = CreativeType.IMAGE,
        name: str = "",
    ):
        """
        Record metrics for a creative.

        Will create the creative if it doesn't exist.
        """
        # Get or create creative
        if creative_id not in self._creatives:
            self.register_creative(
                creative_id=creative_id,
                tenant_id=tenant_id,
                platform=platform,
                campaign_id=campaign_id,
                creative_type=creative_type,
                name=name,
            )

        creative = self._creatives[creative_id]

        # Calculate derived metrics
        metrics.calculate_derived()

        # Update lifetime metrics
        lifetime = creative.lifetime_metrics
        lifetime.impressions += metrics.impressions
        lifetime.clicks += metrics.clicks
        lifetime.conversions += metrics.conversions
        lifetime.spend += metrics.spend
        lifetime.revenue += metrics.revenue
        lifetime.video_views += metrics.video_views
        lifetime.video_completions += metrics.video_completions
        lifetime.likes += metrics.likes
        lifetime.shares += metrics.shares
        lifetime.comments += metrics.comments
        lifetime.saves += metrics.saves
        lifetime.calculate_derived()

        # Record daily metrics
        metric_date = date or datetime.now(UTC)
        creative.daily_metrics.append(
            DailyCreativeMetrics(
                date=metric_date,
                metrics=metrics,
            )
        )

        # Update tracking dates
        if creative.first_impression_at is None and metrics.impressions > 0:
            creative.first_impression_at = metric_date
        creative.last_updated_at = datetime.now(UTC)

        # Update days active
        if creative.first_impression_at:
            creative.days_active = (metric_date - creative.first_impression_at).days + 1

        # Check for fatigue
        self._update_fatigue(creative)

    def _update_fatigue(self, creative: Creative):
        """Update fatigue analysis for a creative."""
        if len(creative.daily_metrics) < 7:
            # Need at least 7 days of data
            creative.fatigue_level = FatigueLevel.NONE
            creative.fatigue_score = 0.0
            return

        # Get last 14 days of data, split into two weeks
        recent = (
            creative.daily_metrics[-14:]
            if len(creative.daily_metrics) >= 14
            else creative.daily_metrics
        )
        mid = len(recent) // 2

        first_half = recent[:mid]
        second_half = recent[mid:]

        if not first_half or not second_half:
            return

        # Calculate average CTR and ROAS for each half
        first_ctrs = [d.metrics.ctr for d in first_half if d.metrics.ctr > 0]
        second_ctrs = [d.metrics.ctr for d in second_half if d.metrics.ctr > 0]
        first_roas = [d.metrics.roas for d in first_half if d.metrics.roas > 0]
        second_roas = [d.metrics.roas for d in second_half if d.metrics.roas > 0]

        # Calculate decline percentages
        fatigue_indicators = []
        fatigue_score = 0.0

        if first_ctrs and second_ctrs:
            avg_first_ctr = statistics.mean(first_ctrs)
            avg_second_ctr = statistics.mean(second_ctrs)
            if avg_first_ctr > 0:
                ctr_decline = ((avg_first_ctr - avg_second_ctr) / avg_first_ctr) * 100
                if ctr_decline > 10:
                    fatigue_indicators.append(f"CTR declined {ctr_decline:.1f}%")
                    fatigue_score += min(ctr_decline, 30)

        if first_roas and second_roas:
            avg_first_roas = statistics.mean(first_roas)
            avg_second_roas = statistics.mean(second_roas)
            if avg_first_roas > 0:
                roas_decline = ((avg_first_roas - avg_second_roas) / avg_first_roas) * 100
                if roas_decline > 10:
                    fatigue_indicators.append(f"ROAS declined {roas_decline:.1f}%")
                    fatigue_score += min(roas_decline, 40)

        # Factor in days active (older creatives fatigue more)
        if creative.days_active > 30:
            age_factor = min((creative.days_active - 30) / 30, 1.0) * 20
            fatigue_score += age_factor
            if age_factor > 10:
                fatigue_indicators.append(f"Creative age: {creative.days_active} days")

        # Determine fatigue level
        creative.fatigue_score = min(fatigue_score, 100)

        if fatigue_score < 10:
            creative.fatigue_level = FatigueLevel.NONE
        elif fatigue_score < 30:
            creative.fatigue_level = FatigueLevel.LOW
        elif fatigue_score < 50:
            creative.fatigue_level = FatigueLevel.MEDIUM
        elif fatigue_score < 75:
            creative.fatigue_level = FatigueLevel.HIGH
        else:
            creative.fatigue_level = FatigueLevel.CRITICAL

        # Update status if critically fatigued
        if creative.fatigue_level == FatigueLevel.CRITICAL:
            creative.status = CreativeStatus.FATIGUED

    def analyze_fatigue(self, creative_id: str) -> Optional[CreativeFatigueAnalysis]:
        """
        Get detailed fatigue analysis for a creative.

        Returns:
            Fatigue analysis with indicators and recommendations
        """
        creative = self._creatives.get(creative_id)
        if not creative:
            return None

        indicators = []
        recommendation = "No action needed"

        # Build trend data
        trend_data: dict[str, list[float]] = {
            "ctr": [],
            "roas": [],
            "cpm": [],
        }

        for daily in creative.daily_metrics[-30:]:  # Last 30 days
            trend_data["ctr"].append(daily.metrics.ctr)
            trend_data["roas"].append(daily.metrics.roas)
            trend_data["cpm"].append(daily.metrics.cpm)

        # Generate indicators
        if creative.fatigue_score > 0:
            if len(creative.daily_metrics) >= 7:
                recent_ctrs = [d.metrics.ctr for d in creative.daily_metrics[-7:]]
                if recent_ctrs and max(recent_ctrs) > 0:
                    ctr_variance = statistics.variance(recent_ctrs) if len(recent_ctrs) > 1 else 0
                    if ctr_variance > statistics.mean(recent_ctrs) * 0.5:
                        indicators.append("High CTR variance indicates audience saturation")

            if creative.days_active > 60:
                indicators.append(f"Creative has been running for {creative.days_active} days")

            if creative.lifetime_metrics.cpm > 0:
                indicators.append(f"Current CPM: ${creative.lifetime_metrics.cpm:.2f}")

        # Generate recommendation
        if creative.fatigue_level == FatigueLevel.CRITICAL:
            recommendation = "Pause creative immediately and replace with fresh creative"
        elif creative.fatigue_level == FatigueLevel.HIGH:
            recommendation = "Plan creative refresh within 1 week"
        elif creative.fatigue_level == FatigueLevel.MEDIUM:
            recommendation = "Monitor closely, consider A/B testing new variants"
        elif creative.fatigue_level == FatigueLevel.LOW:
            recommendation = "Continue monitoring, prepare backup creatives"

        return CreativeFatigueAnalysis(
            creative_id=creative_id,
            fatigue_level=creative.fatigue_level,
            fatigue_score=creative.fatigue_score,
            indicators=indicators,
            recommendation=recommendation,
            trend_data=trend_data,
        )

    def compare_creatives(
        self,
        creative_ids: list[str],
        metric: str = "roas",
        period_days: int = 7,
    ) -> Optional[CreativeComparison]:
        """
        Compare performance between creatives.

        Args:
            creative_ids: List of creative IDs to compare
            metric: Primary metric to compare (roas, ctr, cvr)
            period_days: Number of days to analyze

        Returns:
            Comparison result with winner and statistical significance
        """
        if len(creative_ids) < 2:
            return None

        creatives = [self._creatives.get(cid) for cid in creative_ids]
        if not all(creatives):
            return None

        cutoff = datetime.now(UTC) - timedelta(days=period_days)

        metrics_comparison: dict[str, dict[str, float]] = {}
        metric_values: dict[str, list[float]] = {}

        for creative in creatives:
            # Get recent daily metrics
            recent_metrics = [d.metrics for d in creative.daily_metrics if d.date >= cutoff]

            if not recent_metrics:
                continue

            # Calculate averages
            avg_roas = statistics.mean([m.roas for m in recent_metrics]) if recent_metrics else 0
            avg_ctr = statistics.mean([m.ctr for m in recent_metrics]) if recent_metrics else 0
            avg_cvr = statistics.mean([m.cvr for m in recent_metrics]) if recent_metrics else 0
            avg_cpa = (
                statistics.mean([m.cpa for m in recent_metrics if m.cpa > 0])
                if recent_metrics
                else 0
            )
            total_spend = sum(m.spend for m in recent_metrics)
            total_conversions = sum(m.conversions for m in recent_metrics)

            metrics_comparison[creative.creative_id] = {
                "roas": round(avg_roas, 2),
                "ctr": round(avg_ctr, 2),
                "cvr": round(avg_cvr, 2),
                "cpa": round(avg_cpa, 2),
                "spend": round(total_spend, 2),
                "conversions": total_conversions,
            }

            # Collect values for statistical test
            metric_values[creative.creative_id] = [getattr(m, metric, 0) for m in recent_metrics]

        # Determine winner
        winner_id = None
        if metrics_comparison:
            if metric in ["roas", "ctr", "cvr"]:  # Higher is better
                winner_id = max(
                    metrics_comparison.keys(), key=lambda k: metrics_comparison[k].get(metric, 0)
                )
            else:  # Lower is better (cpa)
                winner_id = min(
                    metrics_comparison.keys(),
                    key=lambda k: metrics_comparison[k].get(metric, float("inf")),
                )

        # Statistical significance (simple t-test between top 2)
        significance = False
        confidence = 0.0

        if len(metric_values) >= 2:
            sorted_ids = sorted(
                metric_values.keys(),
                key=lambda k: statistics.mean(metric_values[k]) if metric_values[k] else 0,
                reverse=True,
            )

            if len(sorted_ids) >= 2:
                vals1 = metric_values[sorted_ids[0]]
                vals2 = metric_values[sorted_ids[1]]

                if len(vals1) >= 5 and len(vals2) >= 5:
                    from scipy import stats

                    try:
                        _, p_value = stats.ttest_ind(vals1, vals2)
                        significance = p_value < 0.05
                        confidence = (1 - p_value) * 100 if p_value else 0
                    except Exception:
                        pass

        return CreativeComparison(
            creative_ids=creative_ids,
            winner_id=winner_id,
            metrics_comparison=metrics_comparison,
            statistical_significance=significance,
            confidence_level=round(confidence, 1),
        )

    def get_top_creatives(
        self,
        tenant_id: Optional[str] = None,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        metric: str = "roas",
        limit: int = 10,
        period_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get top performing creatives.

        Args:
            tenant_id: Filter by tenant
            platform: Filter by platform
            campaign_id: Filter by campaign
            metric: Ranking metric
            limit: Number of results
            period_days: Analysis period

        Returns:
            List of top creatives with metrics
        """
        cutoff = datetime.now(UTC) - timedelta(days=period_days)

        # Filter creatives
        creatives = list(self._creatives.values())

        if tenant_id:
            creatives = [c for c in creatives if c.tenant_id == tenant_id]
        if platform:
            creatives = [c for c in creatives if c.platform == platform]
        if campaign_id:
            creatives = [c for c in creatives if c.campaign_id == campaign_id]

        # Calculate period metrics
        results = []
        for creative in creatives:
            recent = [d for d in creative.daily_metrics if d.date >= cutoff]
            if not recent:
                continue

            total_spend = sum(d.metrics.spend for d in recent)
            total_revenue = sum(d.metrics.revenue for d in recent)
            total_impressions = sum(d.metrics.impressions for d in recent)
            total_clicks = sum(d.metrics.clicks for d in recent)
            total_conversions = sum(d.metrics.conversions for d in recent)

            period_roas = total_revenue / total_spend if total_spend > 0 else 0
            period_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            period_cvr = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

            results.append(
                {
                    "creative_id": creative.creative_id,
                    "name": creative.name,
                    "platform": creative.platform,
                    "campaign_id": creative.campaign_id,
                    "creative_type": creative.creative_type.value,
                    "status": creative.status.value,
                    "fatigue_level": creative.fatigue_level.value,
                    "days_active": creative.days_active,
                    "metrics": {
                        "roas": round(period_roas, 2),
                        "ctr": round(period_ctr, 2),
                        "cvr": round(period_cvr, 2),
                        "spend": round(total_spend, 2),
                        "revenue": round(total_revenue, 2),
                        "impressions": total_impressions,
                        "clicks": total_clicks,
                        "conversions": total_conversions,
                    },
                }
            )

        # Sort by metric
        reverse = metric in ["roas", "ctr", "cvr", "conversions", "revenue"]
        results.sort(key=lambda x: x["metrics"].get(metric, 0), reverse=reverse)

        return results[:limit]

    def get_creative(self, creative_id: str) -> Optional[Creative]:
        """Get a creative by ID."""
        return self._creatives.get(creative_id)

    def get_creatives_for_campaign(self, campaign_id: str) -> list[Creative]:
        """Get all creatives for a campaign."""
        creative_ids = self._by_campaign.get(campaign_id, [])
        return [self._creatives[cid] for cid in creative_ids if cid in self._creatives]

    def get_fatigued_creatives(
        self,
        tenant_id: Optional[str] = None,
        min_fatigue_level: FatigueLevel = FatigueLevel.MEDIUM,
    ) -> list[dict[str, Any]]:
        """Get creatives that need attention due to fatigue."""
        fatigue_order = [
            FatigueLevel.NONE,
            FatigueLevel.LOW,
            FatigueLevel.MEDIUM,
            FatigueLevel.HIGH,
            FatigueLevel.CRITICAL,
        ]
        min_index = fatigue_order.index(min_fatigue_level)

        creatives = list(self._creatives.values())
        if tenant_id:
            creatives = [c for c in creatives if c.tenant_id == tenant_id]

        fatigued = []
        for creative in creatives:
            if fatigue_order.index(creative.fatigue_level) >= min_index:
                analysis = self.analyze_fatigue(creative.creative_id)
                fatigued.append(
                    {
                        "creative_id": creative.creative_id,
                        "name": creative.name,
                        "platform": creative.platform,
                        "campaign_id": creative.campaign_id,
                        "fatigue_level": creative.fatigue_level.value,
                        "fatigue_score": creative.fatigue_score,
                        "days_active": creative.days_active,
                        "recommendation": analysis.recommendation if analysis else "",
                        "lifetime_roas": round(creative.lifetime_metrics.roas, 2),
                    }
                )

        # Sort by fatigue score descending
        fatigued.sort(key=lambda x: x["fatigue_score"], reverse=True)

        return fatigued

    def get_creative_type_performance(
        self,
        tenant_id: Optional[str] = None,
        platform: Optional[str] = None,
        period_days: int = 30,
    ) -> dict[str, dict[str, float]]:
        """
        Get performance breakdown by creative type.

        Useful for understanding which creative formats work best.
        """
        cutoff = datetime.now(UTC) - timedelta(days=period_days)

        creatives = list(self._creatives.values())
        if tenant_id:
            creatives = [c for c in creatives if c.tenant_id == tenant_id]
        if platform:
            creatives = [c for c in creatives if c.platform == platform]

        by_type: dict[str, dict[str, float]] = {}

        for creative_type in CreativeType:
            type_creatives = [c for c in creatives if c.creative_type == creative_type]

            if not type_creatives:
                continue

            total_spend = 0
            total_revenue = 0
            total_impressions = 0
            total_clicks = 0
            total_conversions = 0

            for creative in type_creatives:
                recent = [d for d in creative.daily_metrics if d.date >= cutoff]
                for d in recent:
                    total_spend += d.metrics.spend
                    total_revenue += d.metrics.revenue
                    total_impressions += d.metrics.impressions
                    total_clicks += d.metrics.clicks
                    total_conversions += d.metrics.conversions

            by_type[creative_type.value] = {
                "creative_count": len(type_creatives),
                "roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
                "ctr": round((total_clicks / total_impressions * 100), 2)
                if total_impressions > 0
                else 0,
                "cvr": round((total_conversions / total_clicks * 100), 2)
                if total_clicks > 0
                else 0,
                "total_spend": round(total_spend, 2),
                "total_revenue": round(total_revenue, 2),
            }

        return by_type

    def get_summary(
        self,
        tenant_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get summary of creative performance."""
        creatives = list(self._creatives.values())
        if tenant_id:
            creatives = [c for c in creatives if c.tenant_id == tenant_id]

        by_status = defaultdict(int)
        by_fatigue = defaultdict(int)
        by_platform = defaultdict(int)

        for creative in creatives:
            by_status[creative.status.value] += 1
            by_fatigue[creative.fatigue_level.value] += 1
            by_platform[creative.platform] += 1

        return {
            "total_creatives": len(creatives),
            "by_status": dict(by_status),
            "by_fatigue_level": dict(by_fatigue),
            "by_platform": dict(by_platform),
            "needs_attention": len(
                [
                    c
                    for c in creatives
                    if c.fatigue_level in [FatigueLevel.HIGH, FatigueLevel.CRITICAL]
                ]
            ),
        }


# Singleton instance
creative_service = CreativePerformanceService()


# =============================================================================
# Convenience Functions
# =============================================================================


def record_creative_metrics(
    creative_id: str,
    tenant_id: str,
    platform: str,
    campaign_id: str,
    impressions: int = 0,
    clicks: int = 0,
    conversions: int = 0,
    spend: float = 0.0,
    revenue: float = 0.0,
    **kwargs,
):
    """
    Convenience function to record creative metrics.

    Usage:
        record_creative_metrics(
            creative_id="creative_123",
            tenant_id="tenant_1",
            platform="meta",
            campaign_id="campaign_456",
            impressions=10000,
            clicks=500,
            conversions=25,
            spend=1000.0,
            revenue=2500.0,
        )
    """
    metrics = CreativeMetrics(
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        spend=spend,
        revenue=revenue,
        **kwargs,
    )

    creative_service.record_metrics(
        creative_id=creative_id,
        tenant_id=tenant_id,
        platform=platform,
        campaign_id=campaign_id,
        metrics=metrics,
    )


def get_fatigued_creatives_for_tenant(tenant_id: str) -> list[dict[str, Any]]:
    """Get fatigued creatives for a tenant."""
    return creative_service.get_fatigued_creatives(tenant_id=tenant_id)


def get_top_performing_creatives(
    tenant_id: str,
    platform: Optional[str] = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get top performing creatives for a tenant."""
    return creative_service.get_top_creatives(
        tenant_id=tenant_id,
        platform=platform,
        limit=limit,
    )


# =============================================================================
# Advanced Creative Performance Analytics (P0 Enhancement)
# =============================================================================


@dataclass
class CreativeElement:
    """Individual element of a creative."""

    element_type: str  # headline, body, cta, image, video
    content: str
    position: Optional[str] = None


@dataclass
class CreativeElementAnalysis:
    """Analysis of creative element performance."""

    element_type: str
    top_performers: list[dict[str, Any]]
    worst_performers: list[dict[str, Any]]
    recommendations: list[str]


@dataclass
class CreativeLifecyclePrediction:
    """Prediction of creative lifecycle."""

    creative_id: str
    current_phase: str  # learning, growth, maturity, decline, fatigue
    days_in_phase: int
    predicted_phase_change_days: int
    predicted_next_phase: str
    confidence: float
    factors: list[str]


@dataclass
class CrossPlatformCreativeInsight:
    """Insight from cross-platform creative analysis."""

    insight_type: str
    platforms: list[str]
    description: str
    actionable_recommendation: str
    potential_impact: str


class CreativeElementAnalyzer:
    """
    Analyzes individual creative elements (headlines, CTAs, etc).

    Identifies:
    - Which headlines perform best
    - Optimal CTA variations
    - Image/video effectiveness patterns
    """

    def __init__(self):
        self._element_performance: dict[str, dict[str, list[dict[str, float]]]] = {}

    def record_element_performance(
        self,
        creative_id: str,
        element: CreativeElement,
        metrics: CreativeMetrics,
    ):
        """Record performance for a creative element."""
        key = f"{element.element_type}:{element.content[:50]}"

        if element.element_type not in self._element_performance:
            self._element_performance[element.element_type] = {}

        if key not in self._element_performance[element.element_type]:
            self._element_performance[element.element_type][key] = []

        self._element_performance[element.element_type][key].append(
            {
                "creative_id": creative_id,
                "ctr": metrics.ctr,
                "conversion_rate": metrics.conversion_rate,
                "roas": metrics.roas,
                "impressions": metrics.impressions,
            }
        )

    def analyze_element_type(
        self,
        element_type: str,
        min_impressions: int = 1000,
    ) -> CreativeElementAnalysis:
        """Analyze performance of an element type."""
        type_data = self._element_performance.get(element_type, {})

        if not type_data:
            return CreativeElementAnalysis(
                element_type=element_type,
                top_performers=[],
                worst_performers=[],
                recommendations=["Insufficient data for analysis"],
            )

        # Calculate aggregate metrics per element
        element_scores = []
        for element_key, performances in type_data.items():
            total_impressions = sum(p["impressions"] for p in performances)
            if total_impressions < min_impressions:
                continue

            avg_ctr = statistics.mean([p["ctr"] for p in performances])
            avg_cvr = statistics.mean([p["conversion_rate"] for p in performances])
            avg_roas = statistics.mean([p["roas"] for p in performances if p["roas"] > 0])

            # Composite score
            score = avg_ctr * 0.3 + avg_cvr * 0.4 + min(avg_roas / 10, 3) * 0.3

            element_scores.append(
                {
                    "element": element_key.split(":", 1)[1] if ":" in element_key else element_key,
                    "avg_ctr": round(avg_ctr, 2),
                    "avg_conversion_rate": round(avg_cvr, 2),
                    "avg_roas": round(avg_roas, 2),
                    "impressions": total_impressions,
                    "score": round(score, 3),
                }
            )

        # Sort by score
        element_scores.sort(key=lambda x: x["score"], reverse=True)

        top_performers = element_scores[:5]
        worst_performers = element_scores[-5:] if len(element_scores) > 5 else []

        # Generate recommendations
        recommendations = self._generate_element_recommendations(
            element_type, top_performers, worst_performers
        )

        return CreativeElementAnalysis(
            element_type=element_type,
            top_performers=top_performers,
            worst_performers=worst_performers,
            recommendations=recommendations,
        )

    def _generate_element_recommendations(
        self,
        element_type: str,
        top: list[dict],
        worst: list[dict],
    ) -> list[str]:
        """Generate recommendations based on element analysis."""
        recommendations = []

        if not top:
            return ["Collect more data to analyze element performance"]

        if element_type == "headline":
            # Analyze headline patterns
            top_lengths = [len(e["element"]) for e in top]
            avg_top_length = statistics.mean(top_lengths) if top_lengths else 0
            recommendations.append(
                f"Optimal headline length appears to be ~{int(avg_top_length)} characters"
            )

            # Check for patterns in top performers
            if any("?" in e["element"] for e in top):
                recommendations.append("Questions in headlines tend to perform well")

        elif element_type == "cta":
            # Analyze CTA patterns
            top_ctas = [e["element"].lower() for e in top]
            if any("now" in cta for cta in top_ctas):
                recommendations.append("Urgency words like 'Now' improve CTA performance")
            if any("free" in cta for cta in top_ctas):
                recommendations.append("'Free' in CTAs drives higher engagement")

        elif element_type == "body":
            recommendations.append("Test shorter vs longer body copy variations")

        if worst:
            avg_worst_score = statistics.mean([w["score"] for w in worst])
            avg_top_score = statistics.mean([t["score"] for t in top])
            if avg_top_score > avg_worst_score * 2:
                recommendations.append(
                    f"Consider pausing low performers - top elements score {avg_top_score/avg_worst_score:.1f}x better"
                )

        return recommendations


class CreativeLifecyclePredictor:
    """
    Predicts creative lifecycle phases and transitions.

    Phases:
    - Learning: Initial data collection (0-3 days)
    - Growth: Performance improving (3-14 days)
    - Maturity: Stable performance (14-30 days)
    - Decline: Performance dropping (30+ days)
    - Fatigue: Severe degradation
    """

    PHASE_THRESHOLDS = {
        "learning": {"min_days": 0, "max_days": 3, "min_impressions": 0},
        "growth": {"min_days": 3, "max_days": 14, "ctr_trend": "increasing"},
        "maturity": {"min_days": 14, "max_days": 45, "ctr_trend": "stable"},
        "decline": {"min_days": 30, "ctr_drop_pct": 10},
        "fatigue": {"ctr_drop_pct": 30},
    }

    def __init__(self):
        self._creative_history: dict[str, list[tuple[datetime, CreativeMetrics]]] = {}

    def record_metrics(self, creative_id: str, metrics: CreativeMetrics):
        """Record metrics for lifecycle tracking."""
        if creative_id not in self._creative_history:
            self._creative_history[creative_id] = []

        self._creative_history[creative_id].append(
            (
                datetime.now(UTC),
                metrics,
            )
        )

        # Keep last 90 days
        cutoff = datetime.now(UTC) - timedelta(days=90)
        self._creative_history[creative_id] = [
            (t, m) for t, m in self._creative_history[creative_id] if t > cutoff
        ]

    def predict(self, creative_id: str) -> CreativeLifecyclePrediction:
        """Predict lifecycle phase for a creative."""
        history = self._creative_history.get(creative_id, [])

        if not history:
            return CreativeLifecyclePrediction(
                creative_id=creative_id,
                current_phase="unknown",
                days_in_phase=0,
                predicted_phase_change_days=0,
                predicted_next_phase="learning",
                confidence=0.0,
                factors=["No historical data available"],
            )

        # Calculate creative age
        first_date = min(t for t, _ in history)
        age_days = (datetime.now(UTC) - first_date).days

        # Get recent and historical CTR
        recent_metrics = [m for t, m in history[-7:]]
        older_metrics = [m for t, m in history[:-7]] if len(history) > 7 else []

        current_ctr = statistics.mean([m.ctr for m in recent_metrics]) if recent_metrics else 0
        historical_ctr = (
            statistics.mean([m.ctr for m in older_metrics]) if older_metrics else current_ctr
        )

        # Determine current phase
        current_phase, factors = self._determine_phase(
            age_days, current_ctr, historical_ctr, recent_metrics
        )

        # Predict next phase
        next_phase, change_days, confidence = self._predict_transition(
            current_phase, age_days, current_ctr, historical_ctr
        )

        # Calculate days in current phase
        days_in_phase = self._calculate_days_in_phase(history, current_phase)

        return CreativeLifecyclePrediction(
            creative_id=creative_id,
            current_phase=current_phase,
            days_in_phase=days_in_phase,
            predicted_phase_change_days=change_days,
            predicted_next_phase=next_phase,
            confidence=round(confidence, 2),
            factors=factors,
        )

    def _determine_phase(
        self,
        age_days: int,
        current_ctr: float,
        historical_ctr: float,
        recent_metrics: list[CreativeMetrics],
    ) -> tuple[str, list[str]]:
        """Determine current lifecycle phase."""
        factors = []

        if age_days <= 3:
            return "learning", ["Creative is new, in learning phase"]

        # Calculate CTR change
        ctr_change_pct = (
            ((current_ctr - historical_ctr) / historical_ctr * 100) if historical_ctr > 0 else 0
        )

        if ctr_change_pct <= -30:
            factors.append(f"CTR dropped {abs(ctr_change_pct):.1f}% - severe fatigue")
            return "fatigue", factors

        if ctr_change_pct <= -10:
            factors.append(f"CTR declining by {abs(ctr_change_pct):.1f}%")
            return "decline", factors

        if age_days <= 14 and ctr_change_pct > 0:
            factors.append("Performance improving during growth phase")
            return "growth", factors

        if abs(ctr_change_pct) <= 10:
            factors.append("Performance stable")
            return "maturity", factors

        factors.append("Transitional performance pattern")
        return "maturity", factors

    def _predict_transition(
        self,
        current_phase: str,
        age_days: int,
        current_ctr: float,
        historical_ctr: float,
    ) -> tuple[str, int, float]:
        """Predict when phase will change and to what."""
        transitions = {
            "learning": ("growth", 3 - age_days, 0.9),
            "growth": ("maturity", max(7, 14 - age_days), 0.8),
            "maturity": ("decline", max(14, 45 - age_days), 0.6),
            "decline": ("fatigue", 14, 0.7),
            "fatigue": ("fatigue", 0, 0.9),  # Terminal state
        }

        return transitions.get(current_phase, ("unknown", 0, 0.5))

    def _calculate_days_in_phase(
        self,
        history: list[tuple[datetime, CreativeMetrics]],
        current_phase: str,
    ) -> int:
        """Calculate how many days in current phase."""
        # Simplified: assume phase started at certain age thresholds
        if not history:
            return 0

        first_date = min(t for t, _ in history)
        age = (datetime.now(UTC) - first_date).days

        phase_starts = {
            "learning": 0,
            "growth": 3,
            "maturity": 14,
            "decline": 30,
            "fatigue": 45,
        }

        phase_start = phase_starts.get(current_phase, 0)
        return max(0, age - phase_start)


class CrossPlatformCreativeAnalyzer:
    """
    Analyzes creative performance across multiple platforms.

    Identifies:
    - Platform-specific performance patterns
    - Creatives that work universally vs platform-specific
    - Optimization opportunities
    """

    def __init__(self, service: CreativePerformanceService):
        self.service = service

    def analyze_creative_across_platforms(
        self,
        creative_name: str,
        tenant_id: str,
    ) -> list[CrossPlatformCreativeInsight]:
        """Analyze a creative's performance across platforms."""
        insights = []

        # Get performance data for this creative across platforms
        platform_performance = {}

        for creative_id, record in self.service._creative_data.items():
            if record.tenant_id != tenant_id:
                continue

            # Simple name matching (in production, use creative asset matching)
            if creative_id.startswith(creative_name) or creative_name in creative_id:
                latest = record.metrics_history[-1] if record.metrics_history else None
                if latest:
                    platform_performance[record.platform] = {
                        "creative_id": creative_id,
                        "ctr": latest.ctr,
                        "conversion_rate": latest.conversion_rate,
                        "roas": latest.roas,
                        "spend": latest.spend,
                    }

        if len(platform_performance) < 2:
            return [
                CrossPlatformCreativeInsight(
                    insight_type="insufficient_data",
                    platforms=list(platform_performance.keys()),
                    description="Creative only found on one platform",
                    actionable_recommendation="Consider expanding to more platforms",
                    potential_impact="Medium - diversification reduces risk",
                )
            ]

        # Compare performance across platforms
        platforms = list(platform_performance.keys())
        performances = list(platform_performance.values())

        # Find best and worst performing platforms
        best_platform = max(platform_performance.items(), key=lambda x: x[1]["roas"])
        worst_platform = min(platform_performance.items(), key=lambda x: x[1]["roas"])

        if best_platform[1]["roas"] > worst_platform[1]["roas"] * 2:
            insights.append(
                CrossPlatformCreativeInsight(
                    insight_type="performance_gap",
                    platforms=[best_platform[0], worst_platform[0]],
                    description=f"{best_platform[0]} outperforms {worst_platform[0]} by {best_platform[1]['roas']/worst_platform[1]['roas']:.1f}x ROAS",
                    actionable_recommendation=f"Consider reallocating budget from {worst_platform[0]} to {best_platform[0]}",
                    potential_impact="High - significant ROAS improvement potential",
                )
            )

        # Check for universal performers
        avg_roas = statistics.mean([p["roas"] for p in performances if p["roas"] > 0])
        if all(p["roas"] >= avg_roas * 0.8 for p in performances if p["roas"] > 0):
            insights.append(
                CrossPlatformCreativeInsight(
                    insight_type="universal_performer",
                    platforms=platforms,
                    description="This creative performs consistently across all platforms",
                    actionable_recommendation="Scale budget across all platforms",
                    potential_impact="High - proven cross-platform effectiveness",
                )
            )

        # Check for platform-specific optimization
        for platform, perf in platform_performance.items():
            if perf["ctr"] > 0 and perf["conversion_rate"] < avg_roas * 0.5:
                insights.append(
                    CrossPlatformCreativeInsight(
                        insight_type="conversion_opportunity",
                        platforms=[platform],
                        description=f"High CTR but low conversion on {platform}",
                        actionable_recommendation=f"Optimize landing page or targeting for {platform}",
                        potential_impact="Medium - improve conversion rate to match engagement",
                    )
                )

        if not insights:
            insights.append(
                CrossPlatformCreativeInsight(
                    insight_type="balanced_performance",
                    platforms=platforms,
                    description="Creative performs similarly across platforms",
                    actionable_recommendation="Maintain current allocation, test new variations",
                    potential_impact="Low - already optimized",
                )
            )

        return insights

    def get_platform_creative_recommendations(
        self,
        tenant_id: str,
    ) -> dict[str, list[str]]:
        """Get creative recommendations per platform."""
        recommendations = {}

        # Analyze each platform
        platforms_data: dict[str, list[CreativeMetrics]] = {}

        for creative_id, record in self.service._creative_data.items():
            if record.tenant_id != tenant_id:
                continue

            if record.platform not in platforms_data:
                platforms_data[record.platform] = []

            if record.metrics_history:
                platforms_data[record.platform].append(record.metrics_history[-1])

        for platform, metrics_list in platforms_data.items():
            platform_recs = []

            if not metrics_list:
                platform_recs.append("No active creatives - launch test campaigns")
            else:
                avg_ctr = statistics.mean([m.ctr for m in metrics_list])
                avg_roas = statistics.mean([m.roas for m in metrics_list if m.roas > 0])

                # Platform-specific recommendations
                if platform == "meta":
                    if avg_ctr < 1.0:
                        platform_recs.append("Test more engaging headlines and images")
                    if avg_roas < 2.0:
                        platform_recs.append("Review audience targeting for better quality")

                elif platform == "google":
                    if avg_ctr < 3.0:
                        platform_recs.append("Improve ad relevance and keyword alignment")

                elif platform == "tiktok":
                    if avg_ctr < 2.0:
                        platform_recs.append("Try more native, authentic creative styles")

                if not platform_recs:
                    platform_recs.append("Performance is strong - continue current strategy")

            recommendations[platform] = platform_recs

        return recommendations


# Singleton instances for P0 enhancements
creative_element_analyzer = CreativeElementAnalyzer()
creative_lifecycle_predictor = CreativeLifecyclePredictor()
cross_platform_creative_analyzer = CrossPlatformCreativeAnalyzer(creative_service)
