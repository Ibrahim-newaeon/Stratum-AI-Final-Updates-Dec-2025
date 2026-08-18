# =============================================================================
# Stratum AI - Celery Application Configuration
# =============================================================================
"""
Celery application setup with Redis broker and result backend.
Includes beat schedule for periodic tasks.
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "stratum_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks",
        "app.workers.campaign_builder_tasks",
        # Autopilot execution pipeline — applies approved actions to platforms.
        # Without this the @shared_task defs are never registered, so approved
        # actions are never dispatched or executed.
        "app.tasks.apply_actions_queue",
        # Trust Engine signal-health rollup — populates FactSignalHealthDaily,
        # which feeds the trust gate, the dashboard trust layer, and the
        # execution-path signal-health check. Same registration gap as the
        # autopilot pipeline: without this the tasks were never registered.
        "app.tasks.signal_health_rollup",
        # Attribution-variance rollup — populates FactAttributionVarianceDaily.
        # Same registration gap as its sibling rollups: the task + its scheduler
        # existed but were in neither `include` nor the beat schedule, so the
        # variance table was never populated (CRM/ATTR orphaned-task fix).
        "app.tasks.attribution_variance_rollup",
        # Audience auto-sync sweep — executes PlatformAudience schedules
        # (auto_sync/next_sync_at). Without this, audiences only sync when
        # a user clicks the button and triggered_by="schedule" is dead code.
        "app.tasks.audience_auto_sync",
        # Newsletter send/schedule tasks. Without this the worker never
        # registers send_newsletter_campaign, so the send endpoint's .delay()
        # dispatched to an unregistered task and silently did nothing.
        "app.workers.newsletter_tasks",
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
    # NOTE: "evaluate-active-rules" and "refresh-competitor-data" are NOT in
    # this static schedule — they are gated behind feature flags below (the
    # rules task crashes on a schema mismatch and the competitor task
    # fabricates benchmarks, so both are shelved off for launch).
    # Sync campaign data every hour
    "sync-all-campaigns": {
        "task": "app.workers.tasks.sync_all_campaigns",
        "schedule": crontab(minute=0),
        "options": {"queue": "sync"},
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
    # Worker liveness heartbeat every minute (INF-003) — Railway can't HTTP-probe
    # the worker, so the API reports its liveness from this Redis heartbeat.
    "worker-heartbeat": {
        "task": "app.workers.tasks.worker_heartbeat",
        "schedule": crontab(minute="*"),
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
    # Apply approved autopilot actions every 5 minutes. This is a backstop:
    # the approve endpoint dispatches apply_single_action directly, but this
    # sweep guarantees any approved action still gets executed even if a
    # direct dispatch was missed (e.g. broker hiccup at approval time).
    "apply-approved-autopilot-actions": {
        "task": "tasks.schedule_apply_actions_queue",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "default"},
    },
    # Daily signal-health rollup at 02:00 UTC — aggregates yesterday's
    # platform metrics into FactSignalHealthDaily for every live tenant.
    # This table is what the trust gate, the dashboard trust layer, and
    # the autopilot execution-path health check all read; without the
    # rollup they see permanent no_data.
    "signal-health-daily-rollup": {
        "task": "tasks.schedule_signal_health_rollup",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
    # Daily attribution-variance rollup at 02:15 UTC — aggregates yesterday's
    # platform-vs-GA attribution variance into FactAttributionVarianceDaily.
    # Offset from the signal-health rollup so they don't contend. Was orphaned
    # (defined but never scheduled), so the table stayed empty (CRM/ATTR).
    "attribution-variance-daily-rollup": {
        "task": "tasks.schedule_attribution_variance_rollup",
        "schedule": crontab(hour=2, minute=15),
        "options": {"queue": "default"},
    },
    # Audience auto-sync sweep every 15 minutes — executes due
    # PlatformAudience schedules (auto_sync + next_sync_at <= now) with
    # triggered_by="schedule". next_sync_at granularity is hours, so a
    # 15-minute sweep keeps syncs within ~15 min of their due time.
    "audience-auto-sync-sweep": {
        "task": "tasks.schedule_audience_auto_sync",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "sync"},
    },
}


# ---------------------------------------------------------------------------
# Opt-in periodic tasks
# ---------------------------------------------------------------------------
# The campaign-builder connector tasks exist but were never registered on the
# beat schedule (orphaned). They sync ad accounts, refresh OAuth tokens, and
# health-check connectors — all of which hit live platform APIs, so they are
# gated behind a default-off flag. Set ENABLE_CAMPAIGN_BUILDER_BEAT=true once
# connectors/credentials are configured.
if settings.enable_campaign_builder_beat:
    celery_app.conf.beat_schedule.update(
        {
            "sync-all-ad-accounts": {
                "task": "app.workers.campaign_builder_tasks.sync_all_ad_accounts",
                "schedule": crontab(hour=2, minute=0),
                "options": {"queue": "sync"},
            },
            "refresh-expiring-tokens": {
                "task": "app.workers.campaign_builder_tasks.refresh_expiring_tokens",
                "schedule": crontab(hour="*/6"),
                "options": {"queue": "default"},
            },
            "connector-health-check": {
                "task": "app.workers.campaign_builder_tasks.connector_health_check",
                "schedule": crontab(minute="*/30"),
                "options": {"queue": "default"},
            },
        }
    )

# Newsletter scheduled-send sweep — every minute, dispatches campaigns whose
# scheduled_at has arrived. Sends live email, so gated off by default; the
# manual send endpoint works regardless (the task module is always in the
# include above). Set ENABLE_NEWSLETTER_BEAT=true to enable scheduled sends.
if settings.enable_newsletter_beat:
    celery_app.conf.beat_schedule["process-scheduled-newsletters"] = {
        "task": "app.workers.newsletter_tasks.process_scheduled_campaigns",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    }

# Scheduled since ff6823ca reconciled the evaluator with the flat
# ``condition_field/operator/value`` schema (it previously read a non-existent
# ``rule.conditions`` and raised AttributeError on every 15-minute tick).
# Set FEATURE_AUTOMATION_RULES=false to disable.
if settings.feature_automation_rules:
    celery_app.conf.beat_schedule["evaluate-active-rules"] = {
        "task": "app.workers.tasks.evaluate_all_rules",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "rules"},
    }

# The competitor refresh worker fabricates estimated spend/impressions/CTR with
# random.randint (no real ad-intelligence source is wired), so it would write
# fake benchmarks that surface on /competitors. Gated off until a real source
# lands. Set FEATURE_COMPETITOR_INTEL=true to re-enable.
if settings.feature_competitor_intel:
    celery_app.conf.beat_schedule["refresh-competitor-data"] = {
        "task": "app.workers.tasks.refresh_all_competitors",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "intel"},
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
    dl_logger.error("Task %s[%s] permanently failed: %s", self.name, task_id, exc)

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
# Per-tenant PII DEK-cache bootstrap [AUTH-05]
# ---------------------------------------------------------------------------
@worker_process_init.connect
def _init_worker_pii_dek_cache(**_kwargs):
    """Preload the per-tenant DEK cache in each prefork worker child.

    The API preloads DEKs in its FastAPI lifespan (``app.main``); worker
    processes get the same bootstrap here, or any task that decrypts
    DEK-encrypted PII would fail with an empty cache. Never raises — on a
    key-store hiccup the worker starts anyway and affected tenants fall
    back to the legacy global-derived key (dual-read).

    The cache is a point-in-time snapshot per child: tenants provisioned
    after this fires are missing until the child is recycled
    (``--max-tasks-per-child`` bounds that window). Acceptable today — no
    worker code decrypts user PII yet; refresh-on-miss is future work.
    """
    import asyncio
    import logging

    logger = logging.getLogger("celery.pii_keys")

    async def _bootstrap() -> dict:
        from app.core import pii_keys
        from app.db import session as db_session

        # Fresh event loop: drop any pooled connections bound to another
        # loop (same guard every task coroutine uses), and dispose again on
        # the way out so task loops start clean.
        await db_session.dispose_stale_async_pool()
        try:
            async with db_session.async_session_factory() as db:
                return await pii_keys.initialize_pii_keys(db)
        finally:
            await db_session.async_engine.dispose()

    try:
        result = asyncio.run(_bootstrap())
        logger.info(
            "worker_pii_keys_ready loaded=%s provisioned=%s",
            result.get("loaded"),
            result.get("provisioned"),
        )
    except Exception as exc:
        # Include the type: e.g. fernet.InvalidToken has an EMPTY str(), which
        # would otherwise log a blank reason (bit us: a worker missing
        # PII_ENCRYPTION_KEY logged nothing actionable).
        logger.warning("worker_pii_keys_init_failed: %s: %s", type(exc).__name__, exc)


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
