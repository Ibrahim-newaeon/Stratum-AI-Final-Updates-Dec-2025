# =============================================================================
# Stratum AI - Attribution Variance Daily Rollup Task
# =============================================================================
"""
Celery task for daily attribution variance rollup.
Compares platform-reported metrics with GA4 data to identify discrepancies.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from celery import shared_task
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.trust_layer import AttributionVarianceStatus, FactAttributionVarianceDaily

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Variance thresholds for status determination
VARIANCE_THRESHOLDS = {
    "high": 30,  # >30% variance = high
    "moderate": 15,  # 15-30% = moderate
    "minor": 5,  # 5-15% = minor
    # <5% = healthy
}

PLATFORMS = ["meta", "google", "tiktok", "snapchat"]


# =============================================================================
# Helper Functions
# =============================================================================


def determine_variance_status(delta_pct: float) -> AttributionVarianceStatus:
    """
    Determine attribution variance status based on percentage difference.
    """
    abs_delta = abs(delta_pct)

    if abs_delta >= VARIANCE_THRESHOLDS["high"]:
        return AttributionVarianceStatus.HIGH_VARIANCE
    elif abs_delta >= VARIANCE_THRESHOLDS["moderate"]:
        return AttributionVarianceStatus.MODERATE_VARIANCE
    elif abs_delta >= VARIANCE_THRESHOLDS["minor"]:
        return AttributionVarianceStatus.MINOR_VARIANCE
    else:
        return AttributionVarianceStatus.HEALTHY


def calculate_confidence(
    ga4_revenue: float,
    platform_revenue: float,
    ga4_conversions: int,
    platform_conversions: int,
) -> float:
    """
    Calculate confidence score based on data volume and consistency.

    Higher confidence when:
    - Both sources have significant data volume
    - Multiple conversions to validate
    - Revenue and conversion trends align
    """
    # Base confidence from data volume
    min_revenue = min(ga4_revenue, platform_revenue)
    if min_revenue < 100:
        volume_confidence = 0.3
    elif min_revenue < 1000:
        volume_confidence = 0.6
    elif min_revenue < 10000:
        volume_confidence = 0.8
    else:
        volume_confidence = 0.95

    # Conversion count confidence
    min_conversions = min(ga4_conversions, platform_conversions)
    if min_conversions < 5:
        conversion_confidence = 0.4
    elif min_conversions < 20:
        conversion_confidence = 0.7
    elif min_conversions < 100:
        conversion_confidence = 0.85
    else:
        conversion_confidence = 0.95

    # Check if revenue and conversion trends align
    if ga4_conversions > 0 and platform_conversions > 0:
        ga4_aov = ga4_revenue / ga4_conversions
        platform_aov = platform_revenue / platform_conversions
        aov_diff = abs(ga4_aov - platform_aov) / max(ga4_aov, platform_aov, 1) * 100

        if aov_diff < 10:
            trend_confidence = 1.0
        elif aov_diff < 25:
            trend_confidence = 0.8
        else:
            trend_confidence = 0.6
    else:
        trend_confidence = 0.5

    # Weighted average
    confidence = (
        (volume_confidence * 0.4) + (conversion_confidence * 0.3) + (trend_confidence * 0.3)
    )

    return round(min(confidence, 1.0), 2)


# =============================================================================
# Main Task
# =============================================================================


@shared_task(
    name="tasks.attribution_variance_rollup",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def attribution_variance_rollup(
    self, tenant_id: Optional[int] = None, target_date: Optional[str] = None
):
    """
    Daily attribution variance rollup task.

    Compares platform-reported revenue/conversions with GA4 data.
    Can run for a specific tenant or all tenants.

    Args:
        tenant_id: Optional tenant ID to process (None = all tenants)
        target_date: Date to process in ISO format (default: yesterday)
    """
    import asyncio

    async def run_rollup():
        async with async_session_factory() as db:
            try:
                rollup_date = (
                    date.fromisoformat(target_date)
                    if target_date
                    else date.today() - timedelta(days=1)
                )

                logger.info(
                    f"Starting attribution variance rollup for date={rollup_date}, tenant_id={tenant_id}"
                )

                # Get list of tenants to process
                if tenant_id:
                    tenant_ids = [tenant_id]
                else:
                    from app.models.tenant import Tenant

                    result = await db.execute(select(Tenant.id).where(Tenant.is_active == True))
                    tenant_ids = [row[0] for row in result.all()]

                records_created = 0

                for tid in tenant_ids:
                    for platform in PLATFORMS:
                        # Fetch GA4 and platform metrics
                        metrics = await fetch_attribution_metrics(db, tid, platform, rollup_date)

                        if not metrics:
                            continue

                        # Calculate deltas
                        ga4_revenue = metrics["ga4_revenue"]
                        platform_revenue = metrics["platform_revenue"]
                        ga4_conversions = metrics["ga4_conversions"]
                        platform_conversions = metrics["platform_conversions"]

                        revenue_delta_abs = platform_revenue - ga4_revenue
                        revenue_delta_pct = (
                            (revenue_delta_abs / ga4_revenue * 100) if ga4_revenue > 0 else 0
                        )

                        conversion_delta_abs = platform_conversions - ga4_conversions
                        conversion_delta_pct = (
                            (conversion_delta_abs / ga4_conversions * 100)
                            if ga4_conversions > 0
                            else 0
                        )

                        # Determine status and confidence
                        status = determine_variance_status(revenue_delta_pct)
                        confidence = calculate_confidence(
                            ga4_revenue, platform_revenue, ga4_conversions, platform_conversions
                        )

                        # Check if record already exists
                        existing = await db.execute(
                            select(FactAttributionVarianceDaily).where(
                                and_(
                                    FactAttributionVarianceDaily.tenant_id == tid,
                                    FactAttributionVarianceDaily.date == rollup_date,
                                    FactAttributionVarianceDaily.platform == platform,
                                )
                            )
                        )
                        existing_record = existing.scalar_one_or_none()

                        if existing_record:
                            # Update existing record
                            existing_record.ga4_revenue = ga4_revenue
                            existing_record.platform_revenue = platform_revenue
                            existing_record.revenue_delta_abs = revenue_delta_abs
                            existing_record.revenue_delta_pct = revenue_delta_pct
                            existing_record.ga4_conversions = ga4_conversions
                            existing_record.platform_conversions = platform_conversions
                            existing_record.conversion_delta_abs = conversion_delta_abs
                            existing_record.conversion_delta_pct = conversion_delta_pct
                            existing_record.confidence = confidence
                            existing_record.status = status
                            existing_record.updated_at = datetime.now(UTC)
                        else:
                            # Create new record
                            record = FactAttributionVarianceDaily(
                                tenant_id=tid,
                                date=rollup_date,
                                platform=platform,
                                ga4_revenue=ga4_revenue,
                                platform_revenue=platform_revenue,
                                revenue_delta_abs=revenue_delta_abs,
                                revenue_delta_pct=revenue_delta_pct,
                                ga4_conversions=ga4_conversions,
                                platform_conversions=platform_conversions,
                                conversion_delta_abs=conversion_delta_abs,
                                conversion_delta_pct=conversion_delta_pct,
                                confidence=confidence,
                                status=status,
                            )
                            db.add(record)
                            records_created += 1

                await db.commit()

                logger.info(
                    f"Attribution variance rollup completed: {records_created} records created/updated"
                )

                return {
                    "status": "success",
                    "date": rollup_date.isoformat(),
                    "records_processed": records_created,
                }

            except Exception as e:
                logger.error(f"Attribution variance rollup failed: {e!s}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.get_event_loop().run_until_complete(run_rollup())


async def fetch_attribution_metrics(
    db: AsyncSession,
    tenant_id: int,
    platform: str,
    target_date: date,
) -> Optional[dict[str, Any]]:
    """
    Fetch attribution metrics from both GA4 and platform sources.

    In production, this would:
    1. Query fact_daily_metrics for platform-reported data
    2. Query GA4 API or fact_ga4_sessions for GA4 data
    3. Match by UTM source/medium

    For now, returns placeholder data if connections exist.
    """
    # Check if tenant has this platform connected
    from app.models.campaign_builder import TenantPlatformConnection

    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.platform == platform,
                TenantPlatformConnection.is_connected == True,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return None

    # In production, query actual data from fact tables
    # For now, return simulated metrics
    # Platform typically over-reports by 10-30% due to view-through attribution

    import random

    base_revenue = random.uniform(5000, 50000)  # noqa: S311 - simulated metrics
    base_conversions = random.randint(50, 500)  # noqa: S311

    # Simulate typical variance (platform usually higher)
    variance_factor = random.uniform(1.05, 1.35)  # noqa: S311

    return {
        "ga4_revenue": base_revenue,
        "platform_revenue": base_revenue * variance_factor,
        "ga4_conversions": base_conversions,
        "platform_conversions": int(base_conversions * variance_factor),
    }


# =============================================================================
# Scheduled Task Registration
# =============================================================================


@shared_task(name="tasks.schedule_attribution_variance_rollup")
def schedule_attribution_variance_rollup():
    """
    Scheduled task to trigger attribution variance rollup for all tenants.
    Should be scheduled to run daily at 3:00 AM UTC (after signal health).
    """
    return attribution_variance_rollup.delay()
