"""
Stratum AI: Data Sync Workers
=============================

Celery tasks for synchronizing data from all advertising platforms.
These workers run on a schedule to keep Stratum's data fresh and
maintain up-to-date signal health calculations.

Architecture
------------

    +------------------+      +------------------+
    |  Celery Beat     |------|  Redis Broker    |
    |  (Scheduler)     |      |                  |
    +------------------+      +---------+--------+
                                        |
                         +--------------+-------------+
                         |                            |
                    +----v----+              +--------v---+
                    | Worker 1|              | Worker 2   |
                    | (Meta)  |              | (Google)   |
                    +----+----+              +------+-----+
                         |                          |
                         +-----------+--------------+
                                     |
                               +-----v-----+
                               | Database  |
                               | (Results) |
                               +-----------+

Task Types
----------

1. **Sync Tasks**: Pull data from platforms (campaigns, metrics, EMQ)
2. **Health Tasks**: Calculate signal health scores
3. **Alert Tasks**: Send notifications for degraded/critical states
4. **Cleanup Tasks**: Purge old data, maintain storage

Schedule
--------

Default schedule (configurable):
- Full sync: Every 15 minutes
- Metrics update: Every 5 minutes
- EMQ refresh: Every 6 hours
- Health calculation: Every 15 minutes (after sync)
- Weekly digest: Every Monday 9 AM

Usage
-----

Start the worker:
    celery -A app.stratum.workers.data_sync worker --loglevel=info

Start the beat scheduler:
    celery -A app.stratum.workers.data_sync beat --loglevel=info

Or combined:
    celery -A app.stratum.workers.data_sync worker --beat --loglevel=info
"""

import asyncio
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

# Celery imports (with fallback for when Celery isn't installed)
try:
    from celery import Celery, shared_task
    from celery.schedules import crontab

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    # Mock decorator for when Celery isn't available
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


from app.stratum.core.signal_health import SignalHealthCalculator
from app.stratum.models import EMQScore, PerformanceMetrics, Platform

logger = logging.getLogger("stratum.workers.data_sync")


# Celery app configuration
if CELERY_AVAILABLE:
    app = Celery("stratum", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minute timeout
        worker_prefetch_multiplier=1,  # One task at a time per worker
    )

    # Beat schedule for periodic tasks
    app.conf.beat_schedule = {
        "sync-all-platforms-every-15-min": {
            "task": "app.stratum.workers.data_sync.sync_all_platforms",
            "schedule": timedelta(minutes=15),
        },
        "update-metrics-every-5-min": {
            "task": "app.stratum.workers.data_sync.update_metrics_all",
            "schedule": timedelta(minutes=5),
        },
        "refresh-emq-every-6-hours": {
            "task": "app.stratum.workers.data_sync.refresh_emq_all",
            "schedule": timedelta(hours=6),
        },
        "calculate-signal-health-every-15-min": {
            "task": "app.stratum.workers.data_sync.calculate_all_signal_health",
            "schedule": timedelta(minutes=15),
        },
        "send-weekly-digest-monday-9am": {
            "task": "app.stratum.workers.data_sync.send_weekly_digest",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
        },
    }
else:
    app = None


def async_task(func):
    """
    Decorator to run async functions in Celery tasks.

    Celery doesn't natively support async, so we need to
    run the async code in an event loop.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            loop.close()

    return wrapper


# ============================================================================
# DATA SYNC TASKS
# ============================================================================


@shared_task(bind=True, max_retries=3)
@async_task
async def sync_platform_data(
    self, platform: str, account_ids: list[str], credentials: dict[str, Any]
) -> dict[str, Any]:
    """
    Sync all data from a single platform.

    This is the main sync task that pulls campaigns, ad sets, ads,
    and current metrics from a platform.

    Args:
        platform: Platform identifier (meta, google, tiktok, snapchat)
        account_ids: List of account IDs to sync
        credentials: Platform credentials

    Returns:
        Sync results including counts and any errors
    """
    from app.stratum.adapters.registry import get_adapter

    platform_enum = Platform(platform)
    results = {
        "platform": platform,
        "accounts_synced": 0,
        "campaigns_synced": 0,
        "adsets_synced": 0,
        "ads_synced": 0,
        "errors": [],
    }

    try:
        adapter = await get_adapter(platform_enum, credentials)

        for account_id in account_ids:
            try:
                # Sync campaigns
                campaigns = await adapter.get_campaigns(account_id)
                results["campaigns_synced"] += len(campaigns)

                # Sync ad sets for each campaign
                for campaign in campaigns:
                    adsets = await adapter.get_adsets(account_id, campaign_id=campaign.campaign_id)
                    results["adsets_synced"] += len(adsets)

                    # Sync ads for each ad set
                    for adset in adsets:
                        ads = await adapter.get_ads(account_id, adset_id=adset.adset_id)
                        results["ads_synced"] += len(ads)

                results["accounts_synced"] += 1
                logger.info(f"Synced {platform} account {account_id}")

            except Exception as e:
                error_msg = f"Error syncing account {account_id}: {e!s}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        await adapter.cleanup()

    except Exception as e:
        logger.error(f"Failed to initialize {platform} adapter: {e}")
        results["errors"].append(str(e))
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds

    return results


@shared_task(bind=True)
@async_task
async def sync_all_platforms(self) -> dict[str, Any]:
    """
    Sync data from all configured platforms.

    This is the main scheduled sync task that runs every 15 minutes.
    It reads platform configuration and dispatches individual sync tasks.
    """
    import yaml

    results = {"started_at": datetime.utcnow().isoformat(), "platforms": {}}

    try:
        # Load configuration
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yaml not found")
        return {"error": "Configuration file not found"}

    platforms = ["meta", "google", "tiktok", "snapchat"]

    for platform in platforms:
        platform_config = config.get(platform, {})
        if not platform_config.get("enabled", False):
            results["platforms"][platform] = {"status": "disabled"}
            continue

        # Get account IDs (would normally come from database)
        account_ids = platform_config.get("account_ids", [])
        if not account_ids:
            results["platforms"][platform] = {"status": "no_accounts"}
            continue

        # Dispatch sync task
        try:
            task_result = await sync_platform_data(platform, account_ids, platform_config)
            results["platforms"][platform] = task_result
        except Exception as e:
            results["platforms"][platform] = {"status": "error", "error": str(e)}

    results["completed_at"] = datetime.utcnow().isoformat()
    return results


# ============================================================================
# METRICS UPDATE TASKS
# ============================================================================


@shared_task(bind=True)
@async_task
async def update_metrics(
    self,
    platform: str,
    account_id: str,
    entity_type: str,
    entity_ids: list[str],
    credentials: dict[str, Any],
    lookback_days: int = 1,
) -> dict[str, Any]:
    """
    Update performance metrics for specific entities.

    This is a more targeted update than full sync - just grabs
    the latest metrics for specified campaigns/ad sets.
    """
    from app.stratum.adapters.registry import get_adapter

    platform_enum = Platform(platform)
    results = {
        "platform": platform,
        "account_id": account_id,
        "entity_type": entity_type,
        "entities_updated": 0,
        "metrics": {},
    }

    try:
        adapter = await get_adapter(platform_enum, credentials)

        date_end = datetime.utcnow()
        date_start = date_end - timedelta(days=lookback_days)

        metrics = await adapter.get_metrics(
            account_id=account_id,
            entity_type=entity_type,
            entity_ids=entity_ids,
            date_start=date_start,
            date_end=date_end,
        )

        results["entities_updated"] = len(metrics)
        results["metrics"] = {
            entity_id: {
                "impressions": m.impressions,
                "clicks": m.clicks,
                "spend": m.spend,
                "conversions": m.conversions,
                "cpa": m.cpa,
                "roas": m.roas,
            }
            for entity_id, m in metrics.items()
        }

        await adapter.cleanup()

    except Exception as e:
        logger.error(f"Failed to update metrics: {e}")
        results["error"] = str(e)

    return results


@shared_task
@async_task
async def update_metrics_all() -> dict[str, Any]:
    """
    Update metrics for all active campaigns across platforms.

    Runs every 5 minutes to keep metrics fresh for the signal
    health calculator.
    """
    # This would normally query the database for active campaigns
    # and dispatch update_metrics tasks for each

    logger.info("Starting metrics update for all platforms")

    # Placeholder implementation
    results = {
        "started_at": datetime.utcnow().isoformat(),
        "status": "completed",
        "note": "Implement database query for active campaigns",
    }

    return results


# ============================================================================
# EMQ REFRESH TASKS
# ============================================================================


@shared_task(bind=True)
@async_task
async def refresh_emq(
    self, platform: str, account_id: str, credentials: dict[str, Any]
) -> dict[str, Any]:
    """
    Refresh EMQ scores for an account.

    EMQ data doesn't change as frequently as metrics, so we only
    refresh every 6 hours.
    """
    from app.stratum.adapters.registry import get_adapter

    platform_enum = Platform(platform)
    results = {"platform": platform, "account_id": account_id, "emq_scores": []}

    try:
        adapter = await get_adapter(platform_enum, credentials)

        emq_scores = await adapter.get_emq_scores(account_id)

        results["emq_scores"] = [
            {
                "event_name": emq.event_name,
                "score": emq.score,
                "last_updated": emq.last_updated.isoformat() if emq.last_updated else None,
            }
            for emq in emq_scores
        ]

        await adapter.cleanup()

        logger.info(f"Refreshed {len(emq_scores)} EMQ scores for {platform} {account_id}")

    except Exception as e:
        logger.error(f"Failed to refresh EMQ: {e}")
        results["error"] = str(e)

    return results


@shared_task
@async_task
async def refresh_emq_all() -> dict[str, Any]:
    """
    Refresh EMQ scores for all accounts across platforms.

    Runs every 6 hours as EMQ data is relatively stable.
    """
    logger.info("Starting EMQ refresh for all platforms")

    results = {"started_at": datetime.utcnow().isoformat(), "status": "completed"}

    return results


# ============================================================================
# SIGNAL HEALTH TASKS
# ============================================================================


@shared_task
def calculate_signal_health(
    platform: str,
    account_id: str,
    emq_scores: list[dict[str, Any]],
    recent_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate signal health for a single account.

    Takes pre-fetched EMQ and metrics data and computes the
    signal health score.
    """
    calculator = SignalHealthCalculator()

    # Convert dicts back to models
    emq_list = [
        EMQScore(platform=Platform(platform), event_name=e["event_name"], score=e["score"])
        for e in emq_scores
    ]

    metrics_list = [
        PerformanceMetrics(
            impressions=m.get("impressions"),
            clicks=m.get("clicks"),
            spend=m.get("spend"),
            conversions=m.get("conversions"),
            cpa=m.get("cpa"),
            date_start=datetime.fromisoformat(m["date_start"]) if m.get("date_start") else None,
            date_end=datetime.fromisoformat(m["date_end"]) if m.get("date_end") else None,
        )
        for m in recent_metrics
    ]

    health = calculator.calculate(
        platform=Platform(platform),
        account_id=account_id,
        emq_scores=emq_list,
        recent_metrics=metrics_list,
    )

    return {
        "platform": platform,
        "account_id": account_id,
        "score": health.score,
        "emq_score": health.emq_score,
        "freshness_score": health.freshness_score,
        "variance_score": health.variance_score,
        "anomaly_score": health.anomaly_score,
        "is_healthy": health.is_healthy,
        "is_degraded": health.is_degraded,
        "is_critical": health.is_critical,
        "autopilot_allowed": health.autopilot_allowed,
        "issues": health.issues,
        "recommendations": health.recommendations,
        "calculated_at": datetime.utcnow().isoformat(),
    }


@shared_task
@async_task
async def calculate_all_signal_health() -> dict[str, Any]:
    """
    Calculate signal health for all accounts.

    Runs every 15 minutes after the sync completes.
    """
    logger.info("Calculating signal health for all accounts")

    results = {
        "started_at": datetime.utcnow().isoformat(),
        "accounts_processed": 0,
        "healthy": 0,
        "degraded": 0,
        "critical": 0,
    }

    # This would normally:
    # 1. Query database for all accounts
    # 2. Get latest EMQ and metrics for each
    # 3. Calculate signal health
    # 4. Store results and trigger alerts if needed

    return results


# ============================================================================
# ALERT TASKS
# ============================================================================


@shared_task
def send_signal_health_alert(
    account_id: str,
    platform: str,
    health_data: dict[str, Any],
    alert_type: str,  # "degraded" or "critical"
) -> dict[str, Any]:
    """
    Send an alert for degraded or critical signal health.

    This would typically integrate with Slack, email, or other
    notification systems.
    """
    logger.warning(
        f"SIGNAL HEALTH ALERT [{alert_type.upper()}]: "
        f"{platform} account {account_id} - Score: {health_data.get('score')}"
    )

    # Placeholder for notification integration
    # Could integrate with:
    # - Slack webhooks
    # - SendGrid/Mailgun for email
    # - Twilio for SMS
    # - PagerDuty for critical alerts

    return {
        "alert_sent": True,
        "alert_type": alert_type,
        "account_id": account_id,
        "platform": platform,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task
def send_weekly_digest() -> dict[str, Any]:
    """
    Send weekly performance and signal health digest.

    Runs every Monday at 9 AM.
    """
    logger.info("Generating weekly digest")

    # This would compile weekly stats and send to stakeholders

    return {"status": "sent", "sent_at": datetime.utcnow().isoformat()}


# ============================================================================
# CLEANUP TASKS
# ============================================================================


@shared_task
def cleanup_old_data(days_to_keep: int = 90) -> dict[str, Any]:
    """
    Remove old sync data to manage storage.

    Keeps the last N days of historical data.
    """
    logger.info(f"Cleaning up data older than {days_to_keep} days")

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    # This would delete old records from the database

    return {"cutoff_date": cutoff_date.isoformat(), "status": "completed"}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_task_status(task_id: str) -> dict[str, Any]:
    """Get the status of a Celery task by ID."""
    if not CELERY_AVAILABLE or not app:
        return {"error": "Celery not available"}

    result = app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


def trigger_immediate_sync(platform: str, account_id: str) -> str:
    """
    Trigger an immediate sync for a specific account.

    Returns the task ID for tracking.
    """
    if not CELERY_AVAILABLE:
        logger.error("Celery not available")
        return ""

    # Would normally load credentials from database
    task = sync_platform_data.delay(platform, [account_id], {})
    return task.id
