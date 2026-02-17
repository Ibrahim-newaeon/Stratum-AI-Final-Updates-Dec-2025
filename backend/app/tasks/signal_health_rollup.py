# =============================================================================
# Stratum AI - Signal Health Daily Rollup Task
# =============================================================================
"""
Celery task for daily signal health rollup.
Aggregates platform metrics and calculates health status for each tenant.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import logging

from celery import shared_task
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus
from app.analytics.logic.signal_health import signal_health, SignalHealthResult


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Thresholds for status determination
THRESHOLDS = {
    "critical": {
        "emq_score_below": 70,
        "event_loss_above": 20,
        "freshness_above": 360,
        "api_error_above": 10,
    },
    "degraded": {
        "emq_score_below": 80,
        "event_loss_above": 10,
        "freshness_above": 180,
        "api_error_above": 5,
    },
    "risk": {
        "emq_score_below": 90,
        "event_loss_above": 5,
        "freshness_above": 60,
        "api_error_above": 2,
    },
}

PLATFORMS = ["meta", "google", "tiktok", "snapchat"]


# =============================================================================
# Helper Functions
# =============================================================================

def determine_status(
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    freshness_minutes: Optional[int],
    api_error_rate: Optional[float],
) -> SignalHealthStatus:
    """
    Determine signal health status based on metrics.

    Returns the worst status among all metrics.
    """
    # Check critical thresholds
    if any([
        emq_score is not None and emq_score < THRESHOLDS["critical"]["emq_score_below"],
        event_loss_pct is not None and event_loss_pct > THRESHOLDS["critical"]["event_loss_above"],
        freshness_minutes is not None and freshness_minutes > THRESHOLDS["critical"]["freshness_above"],
        api_error_rate is not None and api_error_rate > THRESHOLDS["critical"]["api_error_above"],
    ]):
        return SignalHealthStatus.CRITICAL

    # Check degraded thresholds
    if any([
        emq_score is not None and emq_score < THRESHOLDS["degraded"]["emq_score_below"],
        event_loss_pct is not None and event_loss_pct > THRESHOLDS["degraded"]["event_loss_above"],
        freshness_minutes is not None and freshness_minutes > THRESHOLDS["degraded"]["freshness_above"],
        api_error_rate is not None and api_error_rate > THRESHOLDS["degraded"]["api_error_above"],
    ]):
        return SignalHealthStatus.DEGRADED

    # Check risk thresholds
    if any([
        emq_score is not None and emq_score < THRESHOLDS["risk"]["emq_score_below"],
        event_loss_pct is not None and event_loss_pct > THRESHOLDS["risk"]["event_loss_above"],
        freshness_minutes is not None and freshness_minutes > THRESHOLDS["risk"]["freshness_above"],
        api_error_rate is not None and api_error_rate > THRESHOLDS["risk"]["api_error_above"],
    ]):
        return SignalHealthStatus.RISK

    return SignalHealthStatus.OK


def generate_issues(
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    freshness_minutes: Optional[int],
    api_error_rate: Optional[float],
) -> List[str]:
    """Generate list of issues based on metrics."""
    issues = []

    if emq_score is not None and emq_score < 90:
        issues.append(f"EMQ score is {emq_score:.0f}% (below 90% threshold)")

    if event_loss_pct is not None and event_loss_pct > 5:
        issues.append(f"Event loss is {event_loss_pct:.1f}% (above 5% threshold)")

    if freshness_minutes is not None and freshness_minutes > 60:
        issues.append(f"Data freshness is {freshness_minutes} minutes (above 60 minute threshold)")

    if api_error_rate is not None and api_error_rate > 2:
        issues.append(f"API error rate is {api_error_rate:.1f}% (above 2% threshold)")

    return issues


def generate_actions(
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    freshness_minutes: Optional[int],
    api_error_rate: Optional[float],
    platform: str,
) -> List[str]:
    """Generate recommended actions based on metrics."""
    actions = []

    if emq_score is not None and emq_score < 90:
        actions.append(f"Review {platform} pixel/CAPI implementation")
        actions.append("Check event parameter mapping")

    if event_loss_pct is not None and event_loss_pct > 5:
        actions.append("Verify server-side event delivery")
        actions.append("Check for browser tracking blockers")

    if freshness_minutes is not None and freshness_minutes > 60:
        actions.append("Check data pipeline status")
        actions.append("Verify API connection health")

    if api_error_rate is not None and api_error_rate > 2:
        actions.append(f"Review {platform} API credentials")
        actions.append("Check rate limits and quotas")

    return actions


# =============================================================================
# Main Task
# =============================================================================

@shared_task(
    name="tasks.signal_health_rollup",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def signal_health_rollup(self, tenant_id: Optional[int] = None, target_date: Optional[str] = None):
    """
    Daily signal health rollup task.

    Collects metrics from platform connections and calculates health status.
    Can run for a specific tenant or all tenants.

    Args:
        tenant_id: Optional tenant ID to process (None = all tenants)
        target_date: Date to process in ISO format (default: yesterday)
    """
    import asyncio

    async def run_rollup():
        async with async_session_factory() as db:
            try:
                rollup_date = date.fromisoformat(target_date) if target_date else date.today() - timedelta(days=1)

                logger.info(f"Starting signal health rollup for date={rollup_date}, tenant_id={tenant_id}")

                # Get list of tenants to process
                if tenant_id:
                    tenant_ids = [tenant_id]
                else:
                    # Get all active tenants with platform connections
                    # For now, we'll use a placeholder - in production, query dim_tenant
                    from app.models.tenant import Tenant
                    result = await db.execute(
                        select(Tenant.id).where(Tenant.is_active == True)
                    )
                    tenant_ids = [row[0] for row in result.all()]

                records_created = 0

                for tid in tenant_ids:
                    for platform in PLATFORMS:
                        # Fetch metrics for this tenant/platform
                        # In production, this would query actual platform APIs or aggregated metrics
                        metrics = await fetch_platform_metrics(db, tid, platform, rollup_date)

                        if not metrics:
                            continue

                        # Calculate status
                        status = determine_status(
                            metrics.get("emq_score"),
                            metrics.get("event_loss_pct"),
                            metrics.get("freshness_minutes"),
                            metrics.get("api_error_rate"),
                        )

                        # Generate issues and actions
                        issues = generate_issues(
                            metrics.get("emq_score"),
                            metrics.get("event_loss_pct"),
                            metrics.get("freshness_minutes"),
                            metrics.get("api_error_rate"),
                        )

                        actions = generate_actions(
                            metrics.get("emq_score"),
                            metrics.get("event_loss_pct"),
                            metrics.get("freshness_minutes"),
                            metrics.get("api_error_rate"),
                            platform,
                        )

                        # Check if record already exists
                        existing = await db.execute(
                            select(FactSignalHealthDaily).where(
                                and_(
                                    FactSignalHealthDaily.tenant_id == tid,
                                    FactSignalHealthDaily.date == rollup_date,
                                    FactSignalHealthDaily.platform == platform,
                                )
                            )
                        )
                        existing_record = existing.scalar_one_or_none()

                        import json

                        if existing_record:
                            # Update existing record
                            existing_record.emq_score = metrics.get("emq_score")
                            existing_record.event_loss_pct = metrics.get("event_loss_pct")
                            existing_record.freshness_minutes = metrics.get("freshness_minutes")
                            existing_record.api_error_rate = metrics.get("api_error_rate")
                            existing_record.status = status
                            existing_record.issues = json.dumps(issues) if issues else None
                            existing_record.actions = json.dumps(actions) if actions else None
                            existing_record.updated_at = datetime.now(timezone.utc)
                        else:
                            # Create new record
                            record = FactSignalHealthDaily(
                                tenant_id=tid,
                                date=rollup_date,
                                platform=platform,
                                emq_score=metrics.get("emq_score"),
                                event_loss_pct=metrics.get("event_loss_pct"),
                                freshness_minutes=metrics.get("freshness_minutes"),
                                api_error_rate=metrics.get("api_error_rate"),
                                status=status,
                                issues=json.dumps(issues) if issues else None,
                                actions=json.dumps(actions) if actions else None,
                            )
                            db.add(record)
                            records_created += 1

                await db.commit()

                logger.info(f"Signal health rollup completed: {records_created} records created/updated")

                return {
                    "status": "success",
                    "date": rollup_date.isoformat(),
                    "records_processed": records_created,
                }

            except Exception as e:
                logger.error(f"Signal health rollup failed: {str(e)}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.get_event_loop().run_until_complete(run_rollup())


async def fetch_platform_metrics(
    db: AsyncSession,
    tenant_id: int,
    platform: str,
    target_date: date,
) -> Optional[Dict[str, Any]]:
    """
    Fetch platform metrics for signal health calculation.

    In production, this would:
    1. Query platform APIs for EMQ scores
    2. Calculate event loss from fact_events vs platform reported
    3. Check data freshness from last sync timestamp
    4. Calculate API error rate from logs

    For now, returns placeholder data if platform connection exists.
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

    # Calculate freshness from last sync
    freshness_minutes = None
    if connection.last_sync_at:
        delta = datetime.now(timezone.utc) - connection.last_sync_at.replace(tzinfo=timezone.utc)
        freshness_minutes = int(delta.total_seconds() / 60)

    # In production, these would be calculated from actual data
    # For now, return metrics based on connection health
    return {
        "emq_score": 85.0 if connection.is_healthy else 65.0,
        "event_loss_pct": 3.5 if connection.is_healthy else 15.0,
        "freshness_minutes": freshness_minutes or 30,
        "api_error_rate": 0.5 if connection.is_healthy else 8.0,
    }


# =============================================================================
# Scheduled Task Registration
# =============================================================================

@shared_task(name="tasks.schedule_signal_health_rollup")
def schedule_signal_health_rollup():
    """
    Scheduled task to trigger signal health rollup for all tenants.
    Should be scheduled to run daily at 2:00 AM UTC.
    """
    return signal_health_rollup.delay()
