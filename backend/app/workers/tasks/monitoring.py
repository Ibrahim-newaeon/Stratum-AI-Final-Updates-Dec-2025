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


def post_alert_webhook(url: str | None, payload: dict) -> bool:
    """POST a P0 operational alert to the configured on-call webhook (MON-002).

    No-op (returns False) when no URL is configured or the URL fails SSRF
    validation (non-http scheme, or resolves to a private/link-local/loopback
    address — e.g. the cloud metadata endpoint). Best-effort: never raises, so
    alerting can't take down the monitoring task itself.
    """
    from app.core.ssrf import is_safe_outbound_url

    if not url:
        return False
    if not is_safe_outbound_url(url):
        logger.warning("Ignoring alert_webhook_url: failed SSRF validation")
        return False
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # nosec B310 — scheme validated to http(s) above; URL is operator config.
        urllib.request.urlopen(req, timeout=5)  # nosec B310
        return True
    except Exception as e:  # noqa: BLE001 - alerting must never break monitoring
        logger.warning("Webhook escalation failed: %s", e)
        return False


# Celery has no HTTP endpoint, so Railway can't health-probe the worker/beat
# directly. Instead the worker writes a heartbeat to Redis every minute and the
# API reports liveness from it (INF-003).
WORKER_HEARTBEAT_KEY = "stratum:worker:heartbeat"
WORKER_HEARTBEAT_TTL = 300  # seconds; key self-expires if the worker dies
WORKER_ALIVE_MAX_AGE = 180  # consider the worker alive if seen in the last 3 min


@shared_task(name="app.workers.tasks.worker_heartbeat")
def worker_heartbeat() -> dict:
    """Write a liveness heartbeat (current epoch seconds) to Redis.

    Beat-scheduled every minute. If the worker/beat process dies, the key stops
    refreshing and expires, so worker_is_alive() flips to False.
    """
    import redis

    ts = datetime.now(UTC).timestamp()
    try:
        client = redis.from_url(settings.redis_url)
        client.set(WORKER_HEARTBEAT_KEY, str(ts), ex=WORKER_HEARTBEAT_TTL)
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.warning("worker_heartbeat_write_failed: %s", e)
    return {"heartbeat": ts}


def worker_last_heartbeat() -> "float | None":
    """Return the epoch-seconds of the last worker heartbeat, or None."""
    import redis

    try:
        client = redis.from_url(settings.redis_url)
        raw = client.get(WORKER_HEARTBEAT_KEY)
        if raw is None:
            return None
        return float(raw)
    except (ConnectionError, TimeoutError, OSError, ValueError):
        return None


def worker_is_alive(max_age_seconds: int = WORKER_ALIVE_MAX_AGE) -> bool:
    """True if the worker wrote a heartbeat within max_age_seconds."""
    last = worker_last_heartbeat()
    if last is None:
        return False
    return (datetime.now(UTC).timestamp() - last) <= max_age_seconds


# Explicit name: this module was split out of the old app/workers/tasks.py;
# without it the auto-generated name gains the submodule segment and the
# beat schedule's task reference silently dispatches to nothing.
@shared_task(name="app.workers.tasks.check_pipeline_health")
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
                    "errors": [
                        {"id": c.id, "error": c.sync_error} for c in error_campaigns[:5]
                    ],
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
            redis_client.publish(
                "monitoring:pipeline_health", json.dumps(health_status)
            )
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

        # Escalate to the configured on-call webhook (MON-002)
        if critical_issues:
            post_alert_webhook(settings.alert_webhook_url, health_status)

    logger.info(f"Pipeline health check complete: {health_status['status']}")
    return health_status
