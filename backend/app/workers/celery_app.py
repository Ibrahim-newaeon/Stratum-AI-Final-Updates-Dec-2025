# =============================================================================
# Stratum AI - Celery Application Configuration
# =============================================================================
"""
Celery application setup with Redis broker and result backend.
Includes beat schedule for periodic tasks.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "stratum_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes (for reliability)
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for memory efficiency
    worker_concurrency=4,

    # Result settings
    result_expires=86400,  # Results expire after 24 hours

    # Dead letter queue — tasks that exhaust all retries are routed here
    # instead of being silently discarded.  A dedicated consumer (or manual
    # inspection via Flower / CLI) can replay or investigate failures.
    task_default_queue="default",
    task_queues={
        "default": {},
        "sync": {},
        "rules": {},
        "intel": {},
        "ml": {},
        "dead_letter": {},
    },

    # Task routing
    task_routes={
        "app.workers.tasks.sync_campaign_data": {"queue": "sync"},
        "app.workers.tasks.evaluate_rules": {"queue": "rules"},
        "app.workers.tasks.fetch_competitor_data": {"queue": "intel"},
        "app.workers.tasks.generate_forecast": {"queue": "ml"},
    },

    # Task time limits
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit (for graceful shutdown)
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Evaluate rules every 15 minutes
    "evaluate-active-rules": {
        "task": "app.workers.tasks.evaluate_all_rules",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "rules"},
    },

    # Sync campaign data every hour
    "sync-all-campaigns": {
        "task": "app.workers.tasks.sync_all_campaigns",
        "schedule": crontab(minute=0),
        "options": {"queue": "sync"},
    },

    # Refresh competitor data every 6 hours
    "refresh-competitor-data": {
        "task": "app.workers.tasks.refresh_all_competitors",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "intel"},
    },

    # Generate daily forecasts at 6 AM UTC
    "generate-daily-forecasts": {
        "task": "app.workers.tasks.generate_daily_forecasts",
        "schedule": crontab(minute=0, hour=6),
        "options": {"queue": "ml"},
    },

    # Calculate creative fatigue scores daily at 3 AM UTC
    "calculate-fatigue-scores": {
        "task": "app.workers.tasks.calculate_all_fatigue_scores",
        "schedule": crontab(minute=0, hour=3),
        "options": {"queue": "default"},
    },

    # Process audit log queue every minute
    "process-audit-logs": {
        "task": "app.workers.tasks.process_audit_log_queue",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },

    # Cost allocation daily at 2 AM UTC
    "calculate-cost-allocation": {
        "task": "app.workers.tasks.calculate_cost_allocation",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "default"},
    },

    # Usage rollup daily at 1 AM UTC
    "calculate-usage-rollup": {
        "task": "app.workers.tasks.calculate_usage_rollup",
        "schedule": crontab(minute=0, hour=1),
        "options": {"queue": "default"},
    },

    # Pipeline health check hourly
    "check-pipeline-health": {
        "task": "app.workers.tasks.check_pipeline_health",
        "schedule": crontab(minute=30),
        "options": {"queue": "default"},
    },

    # Daily scoring at 4 AM UTC
    "calculate-daily-scores": {
        "task": "app.workers.tasks.calculate_daily_scores",
        "schedule": crontab(minute=0, hour=4),
        "options": {"queue": "default"},
    },

    # Live predictions every 30 minutes
    "run-all-predictions": {
        "task": "app.workers.tasks.run_all_tenant_predictions",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "ml"},
    },

    # Process scheduled WhatsApp messages every minute
    "process-scheduled-whatsapp": {
        "task": "app.workers.tasks.process_scheduled_whatsapp_messages",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },
}


# ---------------------------------------------------------------------------
# Dead-letter callback — routes permanently failed tasks to the DLQ
# ---------------------------------------------------------------------------
def _on_task_failure(self, exc, task_id, args, kwargs, einfo):
    """Called when a task exhausts all retries.  Publishes metadata to the
    dead_letter queue so failures are never silently lost."""
    import json
    import logging

    dl_logger = logging.getLogger("celery.dead_letter")
    dl_logger.error(
        "Task %s[%s] permanently failed: %s", self.name, task_id, exc
    )

    try:
        celery_app.send_task(
            "dead_letter_sink",
            queue="dead_letter",
            kwargs={
                "original_task": self.name,
                "task_id": task_id,
                "args": json.dumps(args, default=str),
                "kwargs": json.dumps(kwargs, default=str),
                "exception": str(exc),
                "traceback": str(einfo) if einfo else None,
            },
        )
    except Exception:
        dl_logger.exception("Could not publish to dead_letter queue")


# ---------------------------------------------------------------------------
# Task decorators for common patterns
# ---------------------------------------------------------------------------
def retriable_task(**kwargs):
    """Decorator for tasks with exponential backoff retry."""
    default_kwargs = {
        "bind": True,
        "autoretry_for": (Exception,),
        "retry_backoff": True,
        "retry_backoff_max": 600,
        "retry_jitter": True,
        "max_retries": 3,
        "on_failure": _on_task_failure,
    }
    default_kwargs.update(kwargs)
    return celery_app.task(**default_kwargs)


def idempotent_task(**kwargs):
    """Decorator for idempotent tasks (safe to retry)."""
    kwargs.setdefault("acks_late", True)
    kwargs.setdefault("reject_on_worker_lost", True)
    kwargs.setdefault("on_failure", _on_task_failure)
    return celery_app.task(**kwargs)


# Sink task that simply stores DLQ entries (logged for now; can be extended
# to persist to a database table for dashboard visibility).
@celery_app.task(name="dead_letter_sink", queue="dead_letter", ignore_result=True)
def dead_letter_sink(**payload):
    """Store dead-letter entries.  Override this task to write to a DB table."""
    import logging
    logging.getLogger("celery.dead_letter").warning(
        "Dead letter received: task=%s id=%s error=%s",
        payload.get("original_task"),
        payload.get("task_id"),
        payload.get("exception"),
    )
