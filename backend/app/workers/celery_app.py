# =============================================================================
# Stratum AI - Celery Application Configuration
# =============================================================================
"""
Celery application setup with Redis broker and result backend.
Includes beat schedule for periodic tasks.

Security: All beat-scheduled tasks use distributed locks to prevent
duplicate execution across multiple workers.
"""

import functools
import logging
from contextlib import contextmanager
from typing import Any, Callable

import redis
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger("stratum.workers.celery")


# =============================================================================
# Distributed Lock for Beat-Scheduled Tasks
# =============================================================================


class DistributedLock:
    """
    Redis-based distributed lock to prevent duplicate task execution.

    When multiple Celery workers are running with beat scheduler,
    this lock ensures only one worker executes a scheduled task.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis_client = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url)
        return self._redis_client

    @contextmanager
    def acquire(self, lock_name: str, timeout: int = 3600, blocking: bool = False):
        """
        Acquire a distributed lock.

        Args:
            lock_name: Unique name for the lock (usually task name)
            timeout: Lock expiration in seconds (default 1 hour)
            blocking: Whether to wait for lock (default False - return immediately)

        Yields:
            bool: True if lock was acquired, False otherwise
        """
        lock_key = f"celery:lock:{lock_name}"
        lock = self.redis_client.lock(lock_key, timeout=timeout, blocking=blocking)

        acquired = False
        try:
            acquired = lock.acquire(blocking=blocking)
            yield acquired
        finally:
            if acquired:
                try:
                    lock.release()
                except redis.exceptions.LockNotOwnedError:
                    # Lock expired or was released by another process
                    logger.warning(f"Lock {lock_name} was not owned when releasing")


# Global lock instance
_distributed_lock = DistributedLock()


def with_distributed_lock(
    lock_name: str = None,
    timeout: int = 3600,
    skip_if_locked: bool = True
) -> Callable:
    """
    Decorator to ensure only one instance of a task runs across all workers.

    Args:
        lock_name: Name of the lock (defaults to task name)
        timeout: Lock timeout in seconds (default 1 hour)
        skip_if_locked: If True, skip task silently when locked. If False, raise exception.

    Usage:
        @celery_app.task
        @with_distributed_lock(timeout=1800)
        def my_scheduled_task():
            # Only one worker will execute this
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = lock_name or f"{func.__module__}.{func.__name__}"
            with _distributed_lock.acquire(name, timeout=timeout) as acquired:
                if not acquired:
                    if skip_if_locked:
                        logger.info(
                            f"Task {name} skipped - already running on another worker"
                        )
                        return {"status": "skipped", "reason": "lock_held"}
                    else:
                        raise RuntimeError(f"Could not acquire lock for task {name}")
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Create Celery app
celery_app = Celery(
    "stratum_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.sync",
        "app.workers.tasks.rules",
        "app.workers.tasks.competitors",
        "app.workers.tasks.forecast",
        "app.workers.tasks.creative",
        "app.workers.tasks.audit",
        "app.workers.tasks.whatsapp",
        "app.workers.tasks.ml",
        "app.workers.tasks.billing",
        "app.workers.tasks.monitoring",
        "app.workers.tasks.scores",
        "app.workers.tasks.cdp",
        "app.workers.tasks.cms",
    ],
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
    # Task routing (organized by domain module)
    task_routes={
        # Sync tasks
        "app.workers.tasks.sync.sync_campaign_data": {"queue": "sync"},
        "app.workers.tasks.sync.sync_all_campaigns": {"queue": "sync"},
        # Rules tasks
        "app.workers.tasks.rules.evaluate_rules": {"queue": "rules"},
        "app.workers.tasks.rules.evaluate_all_rules": {"queue": "rules"},
        # Competitor tasks
        "app.workers.tasks.competitors.fetch_competitor_data": {"queue": "intel"},
        "app.workers.tasks.competitors.refresh_all_competitors": {"queue": "intel"},
        # ML tasks
        "app.workers.tasks.ml.*": {"queue": "ml"},
        "app.workers.tasks.forecast.*": {"queue": "ml"},
        # CDP tasks
        "app.workers.tasks.cdp.*": {"queue": "cdp"},
        # CMS tasks
        "app.workers.tasks.cms.*": {"queue": "default"},
        # WhatsApp tasks
        "app.workers.tasks.whatsapp.*": {"queue": "default"},
    },
    # Task time limits
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit (for graceful shutdown)
)

# Beat schedule for periodic tasks (using new modular task paths)
celery_app.conf.beat_schedule = {
    # ==========================================================================
    # Rules Engine Tasks
    # ==========================================================================
    "evaluate-active-rules": {
        "task": "app.workers.tasks.rules.evaluate_all_rules",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "rules"},
    },
    # ==========================================================================
    # Data Sync Tasks
    # ==========================================================================
    "sync-all-campaigns": {
        "task": "app.workers.tasks.sync.sync_all_campaigns",
        "schedule": crontab(minute=0),
        "options": {"queue": "sync"},
    },
    # ==========================================================================
    # Competitor Intelligence Tasks
    # ==========================================================================
    "refresh-competitor-data": {
        "task": "app.workers.tasks.competitors.refresh_all_competitors",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "intel"},
    },
    # ==========================================================================
    # ML & Forecasting Tasks
    # ==========================================================================
    "generate-daily-forecasts": {
        "task": "app.workers.tasks.forecast.generate_daily_forecasts",
        "schedule": crontab(minute=0, hour=6),
        "options": {"queue": "ml"},
    },
    "run-all-predictions": {
        "task": "app.workers.tasks.ml.run_all_tenant_predictions",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "ml"},
    },
    # ==========================================================================
    # Creative & Scoring Tasks
    # ==========================================================================
    "calculate-fatigue-scores": {
        "task": "app.workers.tasks.creative.calculate_all_fatigue_scores",
        "schedule": crontab(minute=0, hour=3),
        "options": {"queue": "default"},
    },
    "calculate-daily-scores": {
        "task": "app.workers.tasks.scores.calculate_daily_scores",
        "schedule": crontab(minute=0, hour=4),
        "options": {"queue": "default"},
    },
    # ==========================================================================
    # Audit & Monitoring Tasks
    # ==========================================================================
    "process-audit-logs": {
        "task": "app.workers.tasks.audit.process_audit_log_queue",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },
    "check-pipeline-health": {
        "task": "app.workers.tasks.monitoring.check_pipeline_health",
        "schedule": crontab(minute=30),
        "options": {"queue": "default"},
    },
    # ==========================================================================
    # Billing & Usage Tasks
    # ==========================================================================
    "calculate-cost-allocation": {
        "task": "app.workers.tasks.billing.calculate_cost_allocation",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "default"},
    },
    "calculate-usage-rollup": {
        "task": "app.workers.tasks.billing.calculate_usage_rollup",
        "schedule": crontab(minute=0, hour=1),
        "options": {"queue": "default"},
    },
    # ==========================================================================
    # WhatsApp Tasks
    # ==========================================================================
    "process-scheduled-whatsapp": {
        "task": "app.workers.tasks.whatsapp.process_scheduled_whatsapp_messages",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },
    # ==========================================================================
    # CDP (Customer Data Platform) Tasks
    # ==========================================================================
    "compute-cdp-segments": {
        "task": "app.workers.tasks.cdp.compute_all_cdp_segments",
        "schedule": crontab(minute=0),
        "options": {"queue": "cdp"},
    },
    "compute-cdp-funnels": {
        "task": "app.workers.tasks.cdp.compute_all_cdp_funnels",
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"queue": "cdp"},
    },
    # ==========================================================================
    # CMS (Content Management System) Tasks
    # ==========================================================================
    "publish-scheduled-cms-posts": {
        "task": "app.workers.tasks.cms.publish_scheduled_cms_posts",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },
}


# Task decorators for common patterns
def retriable_task(**kwargs):
    """Decorator for tasks with exponential backoff retry."""
    default_kwargs = {
        "bind": True,
        "autoretry_for": (Exception,),
        "retry_backoff": True,
        "retry_backoff_max": 600,
        "retry_jitter": True,
        "max_retries": 3,
    }
    default_kwargs.update(kwargs)
    return celery_app.task(**default_kwargs)


def idempotent_task(**kwargs):
    """Decorator for idempotent tasks (safe to retry)."""
    kwargs.setdefault("acks_late", True)
    kwargs.setdefault("reject_on_worker_lost", True)
    return celery_app.task(**kwargs)
