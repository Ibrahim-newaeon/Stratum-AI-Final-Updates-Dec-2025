# =============================================================================
# Stratum AI - Pipeline Monitoring Tasks
# =============================================================================
"""
Background tasks for pipeline health checks and monitoring.
"""

from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import Campaign, Tenant
from app.workers.locks import with_distributed_lock

logger = get_task_logger(__name__)


@shared_task
@with_distributed_lock(timeout=600)
def check_pipeline_health():
    """
    Check health of data pipelines and sync jobs.
    Scheduled every 15 minutes by Celery beat.
    """
    logger.info("Checking pipeline health")

    issues = []

    with SyncSessionLocal() as db:
        # Check for stale campaigns (not synced in 2+ hours)
        stale_threshold = datetime.now(UTC) - timedelta(hours=2)

        stale_campaigns = (
            db.execute(
                select(Campaign).where(
                    Campaign.is_deleted == False,
                    Campaign.status == "active",
                    Campaign.last_synced_at < stale_threshold,
                )
            )
            .scalars()
            .all()
        )

        if stale_campaigns:
            issues.append(
                {
                    "type": "stale_campaigns",
                    "count": len(stale_campaigns),
                    "campaign_ids": [c.id for c in stale_campaigns[:10]],
                }
            )

        # Check for sync errors
        error_campaigns = (
            db.execute(
                select(Campaign).where(
                    Campaign.is_deleted == False,
                    Campaign.sync_error.isnot(None),
                )
            )
            .scalars()
            .all()
        )

        if error_campaigns:
            issues.append(
                {
                    "type": "sync_errors",
                    "count": len(error_campaigns),
                    "errors": [{"id": c.id, "error": c.sync_error} for c in error_campaigns[:5]],
                }
            )

        # Check Redis connectivity
        try:
            import redis

            redis_client = redis.from_url(settings.redis_url)
            redis_client.ping()
            redis_status = "healthy"
        except (ConnectionError, TimeoutError, OSError) as e:
            redis_status = f"unhealthy: {e!s}"
            logger.warning("Redis health check failed: %s", e)
            issues.append(
                {
                    "type": "redis_connection",
                    "status": redis_status,
                }
            )

        # Check database health
        try:
            # Note: This is async, so we check differently in sync context
            db.execute(select(func.count(Tenant.id)))
            db_status = "healthy"
        except (ConnectionError, TimeoutError, OSError) as e:
            db_status = f"unhealthy: {e!s}"
            logger.warning("Database health check failed: %s", e)
            issues.append(
                {
                    "type": "database_connection",
                    "status": db_status,
                }
            )

    # Publish health status
    health_status = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "degraded" if issues else "healthy",
        "issues": issues,
        "redis": redis_status,
        "database": db_status,
    }

    # Alert if issues found — escalate to external alerting
    if issues:
        logger.warning(f"Pipeline health issues detected: {issues}")
        # Publish to monitoring channel
        try:
            import json

            import redis

            redis_client = redis.from_url(settings.redis_url)
            redis_client.publish("monitoring:pipeline_health", json.dumps(health_status))
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Failed to publish pipeline health to Redis: %s", e)

        # Escalate to Sentry/external alerting for critical issues
        critical_types = {"redis_connection", "database_connection"}
        critical_issues = [i for i in issues if i["type"] in critical_types]
        if critical_issues:
            logger.error(
                "CRITICAL pipeline health failure — escalating: %s",
                critical_issues,
            )
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"Pipeline health CRITICAL: {[i['type'] for i in critical_issues]}",
                    level="error",
                )
            except (ImportError, Exception) as e:
                logger.warning("Sentry escalation unavailable: %s", e)

        # Escalate webhook if configured
        alert_webhook = getattr(settings, "alert_webhook_url", None)
        if alert_webhook:
            try:
                import json
                import urllib.request
                req = urllib.request.Request(
                    alert_webhook,
                    data=json.dumps(health_status).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                logger.warning("Webhook escalation failed: %s", e)

    logger.info(f"Pipeline health check complete: {health_status['status']}")
    return health_status
