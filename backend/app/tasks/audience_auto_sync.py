# =============================================================================
# Stratum AI - Audience Auto-Sync Task
# =============================================================================
"""
Celery task executing scheduled audience syncs.

PlatformAudience rows carry auto_sync / sync_interval_hours / next_sync_at,
and AudienceSyncService.sync_platform_audience advances next_sync_at on
success — but until this task existed nothing ever executed the schedule,
so ``triggered_by="schedule"`` was unreachable and audiences only synced
when a user clicked the button.

The sweep runs every 15 minutes and processes every active audience whose
next_sync_at is due. Failures are recorded per audience (the service
commits the failed job for history) and next_sync_at is pushed forward by
a backoff so a persistently failing audience does not get retried on
every sweep.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import and_, select

from app.db.session import async_session_factory
from app.models.audience_sync import PlatformAudience, SyncOperation

logger = logging.getLogger(__name__)

# On failure, retry no sooner than this instead of on the next sweep.
FAILURE_BACKOFF_HOURS = 1


@shared_task(
    name="tasks.audience_auto_sync",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def audience_auto_sync(self, platform_audience_id: str | None = None):
    """
    Execute scheduled audience syncs.

    Args:
        platform_audience_id: Optional single audience to sync (str UUID);
            None sweeps every due audience across all tenants.
    """
    import asyncio

    async def run_sweep():
        from app.db.session import dispose_stale_async_pool
        from app.services.cdp.audience_sync.service import AudienceSyncService

        # Celery tasks run asyncio.run() per invocation; drop pool
        # connections bound to a previous task's event loop first.
        await dispose_stale_async_pool()
        async with async_session_factory() as db:
            now = datetime.now(UTC)

            query = select(PlatformAudience).where(
                and_(
                    PlatformAudience.auto_sync == True,  # noqa: E712
                    PlatformAudience.is_active == True,  # noqa: E712
                    PlatformAudience.next_sync_at != None,  # noqa: E711
                    PlatformAudience.next_sync_at <= now,
                )
            )
            if platform_audience_id:
                query = query.where(PlatformAudience.id == UUID(platform_audience_id))

            result = await db.execute(query.order_by(PlatformAudience.next_sync_at))
            due = list(result.scalars().all())

            if not due:
                return {"status": "success", "synced": 0, "failed": 0}

            logger.info("audience_auto_sync: %d audience(s) due", len(due))

            synced = 0
            failed = 0
            for audience in due:
                service = AudienceSyncService(db, audience.tenant_id)
                try:
                    await service.sync_platform_audience(
                        audience.id,
                        operation=SyncOperation.UPDATE,
                        triggered_by="schedule",
                    )
                    synced += 1
                except Exception as e:
                    # The service already committed the failed job + audience
                    # status for sync history. Back off so the next sweeps
                    # don't hammer a persistently failing audience/platform.
                    failed += 1
                    logger.warning(
                        "audience_auto_sync: audience %s (tenant %s) failed: %s",
                        audience.id,
                        audience.tenant_id,
                        e,
                    )
                    audience.next_sync_at = now + timedelta(hours=FAILURE_BACKOFF_HOURS)

            await db.commit()

            logger.info(
                "audience_auto_sync completed: synced=%d failed=%d", synced, failed
            )
            return {"status": "success", "synced": synced, "failed": failed}

    return asyncio.run(run_sweep())


# =============================================================================
# Scheduled Task Registration
# =============================================================================


@shared_task(name="tasks.schedule_audience_auto_sync")
def schedule_audience_auto_sync():
    """
    Scheduled trigger for the audience auto-sync sweep.
    Runs every 15 minutes from Celery Beat.
    """
    return audience_auto_sync.delay()
