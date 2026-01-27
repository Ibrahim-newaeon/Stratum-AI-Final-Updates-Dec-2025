# =============================================================================
# Stratum AI - CDP EMQ Aggregator Service
# =============================================================================
"""
CDP EMQ Aggregator Service for Trust Engine Integration.

This service aggregates CDP Event Match Quality scores and provides them
to the Signal Health Calculator for inclusion in Trust Gate decisions.

The CDP EMQ score represents the quality of first-party data collection:
- Higher scores indicate better identity resolution
- Lower scores may indicate tracking gaps or data quality issues
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdp import CDPConsent, CDPEvent, CDPProfile

logger = logging.getLogger("stratum.cdp_emq")


class CDPEMQAggregator:
    """
    Aggregates CDP EMQ scores for integration with Trust Engine.

    This service provides:
    1. Daily aggregate EMQ scores per tenant
    2. EMQ trend analysis over time
    3. Profile quality metrics
    4. Integration with Signal Health calculation
    """

    # Thresholds for EMQ interpretation
    EXCELLENT_THRESHOLD = 85.0
    HEALTHY_THRESHOLD = 70.0
    DEGRADED_THRESHOLD = 50.0

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_aggregate_emq(
        self,
        tenant_id: int,
        target_date: Optional[date] = None,
        lookback_days: int = 7,
    ) -> dict[str, Any]:
        """
        Get aggregated CDP EMQ score for a tenant.

        Args:
            tenant_id: Tenant identifier
            target_date: Date to calculate for (default: today)
            lookback_days: Days to include in average

        Returns:
            Dict with aggregate EMQ data:
            - aggregate_score: Overall CDP EMQ (0-100)
            - event_count: Total events in period
            - profile_count: Active profiles
            - avg_score: Average event EMQ
            - issues: List of detected issues
        """
        if target_date is None:
            target_date = date.today()

        start_date = target_date - timedelta(days=lookback_days)

        # Get EMQ statistics for the period
        result = await self.db.execute(
            select(
                func.count(CDPEvent.id).label("event_count"),
                func.avg(CDPEvent.emq_score).label("avg_emq"),
                func.min(CDPEvent.emq_score).label("min_emq"),
                func.max(CDPEvent.emq_score).label("max_emq"),
                func.stddev(CDPEvent.emq_score).label("std_emq"),
            ).where(
                and_(
                    CDPEvent.tenant_id == tenant_id,
                    func.date(CDPEvent.received_at) >= start_date,
                    func.date(CDPEvent.received_at) <= target_date,
                    CDPEvent.emq_score.isnot(None),
                )
            )
        )
        stats = result.one()

        # Get profile count
        profile_result = await self.db.execute(
            select(func.count(CDPProfile.id)).where(CDPProfile.tenant_id == tenant_id)
        )
        profile_count = profile_result.scalar() or 0

        # Get recent event count (last 24h)
        recent_result = await self.db.execute(
            select(func.count(CDPEvent.id)).where(
                and_(
                    CDPEvent.tenant_id == tenant_id,
                    CDPEvent.received_at >= datetime.now(UTC) - timedelta(hours=24),
                )
            )
        )
        recent_event_count = recent_result.scalar() or 0

        # Calculate aggregate score and issues
        issues = []
        event_count = stats.event_count or 0
        avg_emq = float(stats.avg_emq or 0)
        min_emq = float(stats.min_emq or 0)
        std_emq = float(stats.std_emq or 0)

        # Determine aggregate score
        if event_count == 0:
            # No CDP events - use default score with warning
            aggregate_score = 75.0
            issues.append("No CDP events in analysis period - using default EMQ")
        else:
            aggregate_score = avg_emq

            # Check for issues
            if avg_emq < self.HEALTHY_THRESHOLD:
                issues.append(
                    f"CDP EMQ below target: {avg_emq:.1f} (target: {self.HEALTHY_THRESHOLD}+)"
                )

            if min_emq < self.DEGRADED_THRESHOLD:
                issues.append(f"Low-quality events detected: min EMQ {min_emq:.1f}")

            if std_emq > 20:
                issues.append(f"High EMQ variance: {std_emq:.1f} - inconsistent data quality")

            if recent_event_count == 0:
                issues.append("No CDP events in last 24 hours - data may be stale")

        return {
            "aggregate_score": round(aggregate_score, 1),
            "event_count": event_count,
            "profile_count": profile_count,
            "recent_event_count": recent_event_count,
            "avg_score": round(avg_emq, 1),
            "min_score": round(min_emq, 1),
            "max_score": round(float(stats.max_emq or 0), 1),
            "std_score": round(std_emq, 1),
            "lookback_days": lookback_days,
            "issues": issues,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    async def get_emq_trend(
        self,
        tenant_id: int,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get daily EMQ trend for a tenant.

        Args:
            tenant_id: Tenant identifier
            days: Number of days to retrieve

        Returns:
            List of daily EMQ records with date, score, event_count
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(CDPEvent.received_at).label("event_date"),
                func.count(CDPEvent.id).label("event_count"),
                func.avg(CDPEvent.emq_score).label("avg_emq"),
            )
            .where(
                and_(
                    CDPEvent.tenant_id == tenant_id,
                    func.date(CDPEvent.received_at) >= start_date,
                    func.date(CDPEvent.received_at) <= end_date,
                    CDPEvent.emq_score.isnot(None),
                )
            )
            .group_by(func.date(CDPEvent.received_at))
            .order_by(func.date(CDPEvent.received_at))
        )

        return [
            {
                "date": str(row.event_date),
                "event_count": row.event_count,
                "avg_emq": round(float(row.avg_emq or 0), 1),
            }
            for row in result.all()
        ]

    async def get_profile_quality_breakdown(
        self,
        tenant_id: int,
    ) -> dict[str, Any]:
        """
        Get profile quality breakdown by lifecycle stage.

        Returns distribution of profiles and their quality indicators.
        """
        result = await self.db.execute(
            select(
                CDPProfile.lifecycle_stage,
                func.count(CDPProfile.id).label("count"),
                func.avg(CDPProfile.total_events).label("avg_events"),
            )
            .where(CDPProfile.tenant_id == tenant_id)
            .group_by(CDPProfile.lifecycle_stage)
        )

        stages = {}
        total = 0
        for row in result.all():
            stages[row.lifecycle_stage] = {
                "count": row.count,
                "avg_events": round(float(row.avg_events or 0), 1),
            }
            total += row.count

        # Calculate percentages
        for stage in stages:
            stages[stage]["percentage"] = round(
                (stages[stage]["count"] / total * 100) if total > 0 else 0, 1
            )

        # Calculate identity resolution rate (known + customer profiles)
        known_count = stages.get("known", {}).get("count", 0)
        customer_count = stages.get("customer", {}).get("count", 0)
        identified_count = known_count + customer_count
        resolution_rate = (identified_count / total * 100) if total > 0 else 0

        return {
            "total_profiles": total,
            "stages": stages,
            "identity_resolution_rate": round(resolution_rate, 1),
        }

    async def get_consent_metrics(
        self,
        tenant_id: int,
    ) -> dict[str, Any]:
        """
        Get consent compliance metrics.

        Returns:
        - consent_rate: Percentage of profiles with any consent granted
        - consent_by_type: Breakdown by consent type
        """
        # Get total profiles
        total_result = await self.db.execute(
            select(func.count(CDPProfile.id)).where(CDPProfile.tenant_id == tenant_id)
        )
        total_profiles = total_result.scalar() or 0

        if total_profiles == 0:
            return {
                "consent_rate": 0,
                "profiles_with_consent": 0,
                "total_profiles": 0,
                "consent_by_type": {},
            }

        # Get profiles with at least one consent granted
        profiles_with_consent_result = await self.db.execute(
            select(func.count(func.distinct(CDPConsent.profile_id))).where(
                and_(
                    CDPConsent.tenant_id == tenant_id,
                    CDPConsent.granted == True,
                )
            )
        )
        profiles_with_consent = profiles_with_consent_result.scalar() or 0

        # Get consent breakdown by type
        consent_by_type_result = await self.db.execute(
            select(
                CDPConsent.consent_type,
                func.count(CDPConsent.id).label("count"),
                func.sum(func.cast(CDPConsent.granted, Integer)).label("granted_count"),
            )
            .where(CDPConsent.tenant_id == tenant_id)
            .group_by(CDPConsent.consent_type)
        )

        consent_by_type = {}
        for row in consent_by_type_result.all():
            consent_by_type[row.consent_type] = {
                "total": row.count,
                "granted": row.granted_count or 0,
                "rate": round((row.granted_count or 0) / row.count * 100, 1)
                if row.count > 0
                else 0,
            }

        consent_rate = (profiles_with_consent / total_profiles * 100) if total_profiles > 0 else 0

        return {
            "consent_rate": round(consent_rate, 1),
            "profiles_with_consent": profiles_with_consent,
            "total_profiles": total_profiles,
            "consent_by_type": consent_by_type,
        }

    def calculate_cdp_contribution(
        self,
        aggregate_emq: float,
        identity_resolution_rate: float,
        recent_event_count: int,
        consent_rate: float = 0.0,
    ) -> tuple[float, list[str]]:
        """
        Calculate CDP's contribution to overall signal health.

        Combines:
        - Aggregate EMQ (50% weight)
        - Identity resolution rate (25% weight)
        - Data recency (15% weight)
        - Consent compliance (10% weight)

        Args:
            aggregate_emq: Average CDP EMQ score (0-100)
            identity_resolution_rate: Percentage of identified profiles
            recent_event_count: Events in last 24h
            consent_rate: Percentage of profiles with consent

        Returns:
            Tuple of (cdp_score, issues)
        """
        issues = []

        # EMQ component (50%)
        emq_component = aggregate_emq * 0.50

        # Identity resolution component (25%)
        # Scale: 0-20% = low, 20-50% = moderate, 50%+ = good
        if identity_resolution_rate >= 50:
            resolution_score = 100
        elif identity_resolution_rate >= 20:
            resolution_score = 50 + (identity_resolution_rate - 20) * (50 / 30)
        else:
            resolution_score = identity_resolution_rate * (50 / 20)
            issues.append(f"Low identity resolution: {identity_resolution_rate:.1f}%")

        resolution_component = resolution_score * 0.25

        # Recency component (15%)
        # Any events = good, no events = penalty
        if recent_event_count > 100:
            recency_score = 100
        elif recent_event_count > 0:
            recency_score = 70 + (recent_event_count / 100) * 30
        else:
            recency_score = 40
            issues.append("No recent CDP events - data may be stale")

        recency_component = recency_score * 0.15

        # Consent compliance component (10%)
        # Scale: 0-30% = low, 30-70% = moderate, 70%+ = good
        if consent_rate >= 70:
            consent_score = 100
        elif consent_rate >= 30:
            consent_score = 50 + (consent_rate - 30) * (50 / 40)
        else:
            consent_score = consent_rate * (50 / 30)
            if consent_rate < 20:
                issues.append(f"Low consent rate: {consent_rate:.1f}% - may limit data activation")

        consent_component = consent_score * 0.10

        # Calculate total CDP score
        cdp_score = emq_component + resolution_component + recency_component + consent_component

        return round(cdp_score, 1), issues


async def get_cdp_emq_for_signal_health(
    db: AsyncSession,
    tenant_id: int,
    target_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Convenience function to get CDP EMQ data for Signal Health Calculator.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        target_date: Date to calculate for

    Returns:
        Dict with cdp_score and issues ready for SignalHealth integration
    """
    aggregator = CDPEMQAggregator(db)

    # Get aggregate EMQ
    emq_data = await aggregator.get_aggregate_emq(tenant_id, target_date)

    # Get profile quality
    profile_data = await aggregator.get_profile_quality_breakdown(tenant_id)

    # Get consent metrics
    consent_data = await aggregator.get_consent_metrics(tenant_id)

    # Calculate CDP contribution (now includes consent)
    cdp_score, issues = aggregator.calculate_cdp_contribution(
        aggregate_emq=emq_data["aggregate_score"],
        identity_resolution_rate=profile_data["identity_resolution_rate"],
        recent_event_count=emq_data["recent_event_count"],
        consent_rate=consent_data["consent_rate"],
    )

    # Combine issues
    all_issues = emq_data["issues"] + issues

    return {
        "cdp_score": cdp_score,
        "aggregate_emq": emq_data["aggregate_score"],
        "event_count": emq_data["event_count"],
        "profile_count": emq_data["profile_count"],
        "identity_resolution_rate": profile_data["identity_resolution_rate"],
        "consent_rate": consent_data["consent_rate"],
        "consent_by_type": consent_data["consent_by_type"],
        "issues": all_issues,
        "profile_stages": profile_data["stages"],
    }
