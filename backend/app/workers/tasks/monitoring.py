# =============================================================================
# Stratum AI - Pipeline Monitoring Tasks
# =============================================================================
"""
Background tasks for pipeline health checks and monitoring.
"""

from datetime import datetime, timedelta, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, func

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import Campaign, CampaignMetric, Tenant
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task
def check_pipeline_health():
    """
    Check health of data pipelines and sync jobs.
    Scheduled every 15 minutes by Celery beat.
    """
    logger.info("Checking pipeline health")

    issues = []

    with SyncSessionLocal() as db:
        # Check for stale campaigns (not synced in 2+ hours)
        stale_threshold = datetime.now(timezone.utc) - timedelta(hours=2)

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
                    "errors": [
                        {"id": c.id, "error": c.sync_error}
                        for c in error_campaigns[:5]
                    ],
                }
            )

        # Check Redis connectivity
        try:
            import redis

            redis_client = redis.from_url(settings.redis_url)
            redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
            issues.append(
                {
                    "type": "redis_connection",
                    "status": redis_status,
                }
            )

        # Check database health
        try:
            from app.db.session import check_database_health

            # Note: This is async, so we check differently in sync context
            db.execute(select(func.count(Tenant.id)))
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            issues.append(
                {
                    "type": "database_connection",
                    "status": db_status,
                }
            )

    # Publish health status
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "degraded" if issues else "healthy",
        "issues": issues,
        "redis": redis_status,
        "database": db_status,
    }

    # Alert if issues found
    if issues:
        logger.warning(f"Pipeline health issues detected: {issues}")
        # Publish to monitoring channel
        try:
            import redis
            import json

            redis_client = redis.from_url(settings.redis_url)
            redis_client.publish("monitoring:pipeline_health", json.dumps(health_status))
        except Exception:
            pass

    logger.info(f"Pipeline health check complete: {health_status['status']}")
    return health_status
