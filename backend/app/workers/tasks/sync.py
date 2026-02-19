# =============================================================================
# Stratum AI - Data Synchronization Tasks
# =============================================================================
"""
Background tasks for syncing campaign data from ad platforms.

Security: Beat-scheduled tasks use distributed locks to prevent
duplicate execution across multiple Celery workers.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import Campaign, CampaignMetric, Tenant
from app.workers.locks import with_distributed_lock
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def sync_campaign_data(self, tenant_id: int, campaign_id: int):
    """
    Sync data for a specific campaign from its ad platform.

    Idempotent: Safe to retry without side effects.
    """
    logger.info(f"Syncing campaign {campaign_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        campaign = db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not campaign:
            logger.warning(f"Campaign {campaign_id} not found")
            return {"status": "not_found"}

        try:
            # Use mock client for development
            if settings.use_mock_ad_data:
                from app.services.mock_client import MockAdNetwork, MockAdNetworkManager

                manager = MockAdNetworkManager(tenant_id)
                network = MockAdNetwork(seed=tenant_id)

                end_date = datetime.now(UTC).date()
                start_date = campaign.start_date or (end_date - timedelta(days=30))

                time_series = network.generate_time_series(
                    campaign.external_id,
                    start_date,
                    end_date,
                    campaign.__dict__,
                )

                # Update daily metrics
                for day_data in time_series:
                    existing = db.execute(
                        select(CampaignMetric).where(
                            CampaignMetric.campaign_id == campaign_id,
                            CampaignMetric.date == day_data["date"],
                        )
                    ).scalar_one_or_none()

                    if existing:
                        for key, value in day_data.items():
                            if key != "date" and hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        metric = CampaignMetric(
                            tenant_id=tenant_id,
                            campaign_id=campaign_id,
                            date=day_data["date"],
                            impressions=day_data["impressions"],
                            clicks=day_data["clicks"],
                            conversions=day_data["conversions"],
                            spend_cents=day_data["spend_cents"],
                            revenue_cents=day_data["revenue_cents"],
                            video_views=day_data.get("video_views"),
                            video_completions=day_data.get("video_completions"),
                        )
                        db.add(metric)

                # Update campaign aggregates
                campaign.calculate_metrics()
                campaign.last_synced_at = datetime.now(UTC)
                campaign.sync_error = None

            db.commit()

            # Publish real-time event
            publish_event(
                tenant_id,
                "sync_complete",
                {
                    "campaign_id": campaign_id,
                    "campaign_name": campaign.name,
                },
            )

            logger.info(f"Campaign {campaign_id} synced successfully")
            return {"status": "success", "campaign_id": campaign_id}

        except Exception as e:
            campaign.sync_error = str(e)
            db.commit()
            raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=2,
)
def sync_platform_campaigns(self, tenant_id: int, platform: str):
    """
    Sync all campaigns for a tenant+platform using the real orchestrator.

    This calls the async PlatformSyncOrchestrator which handles token
    management, API calls, and campaign/metric upserts.
    """
    from app.base_models import AdPlatform
    from app.db.session import async_session_context
    from app.services.sync.orchestrator import PlatformSyncOrchestrator

    logger.info(f"Syncing {platform} campaigns for tenant {tenant_id}")

    async def _do_sync():
        async with async_session_context() as db:
            orchestrator = PlatformSyncOrchestrator(db)
            return await orchestrator.sync_platform(
                tenant_id=tenant_id,
                platform=AdPlatform(platform),
            )

    result = _run_async(_do_sync())

    if result.errors:
        logger.warning(
            f"Sync {platform} tenant {tenant_id}: "
            f"{result.campaigns_synced} campaigns, {result.metrics_upserted} metrics, "
            f"{len(result.errors)} errors: {result.errors}"
        )
    else:
        logger.info(
            f"Sync {platform} tenant {tenant_id}: "
            f"{result.campaigns_synced} campaigns, {result.metrics_upserted} metrics "
            f"in {result.duration_seconds}s"
        )

    return {
        "status": "success" if not result.errors else "partial",
        "platform": platform,
        "tenant_id": tenant_id,
        "campaigns_synced": result.campaigns_synced,
        "metrics_upserted": result.metrics_upserted,
        "errors": result.errors,
    }


@shared_task
@with_distributed_lock(timeout=3600)  # 1 hour lock timeout
def sync_all_campaigns():
    """
    Sync all active campaigns across all tenants.
    Scheduled hourly by Celery beat.

    Uses distributed lock to prevent duplicate execution across workers.

    When use_mock_ad_data is True, dispatches per-campaign mock sync tasks.
    When False, dispatches per-tenant+platform orchestrator sync tasks
    that call real ad platform APIs.
    """
    logger.info("Starting sync for all campaigns")

    with SyncSessionLocal() as db:
        tenant_ids = db.execute(
            select(Tenant.id).where(Tenant.is_deleted == False)
        ).scalars().all()

        task_count = 0

        if settings.use_mock_ad_data:
            # Mock mode: sync individual campaigns with generated data
            for tid in tenant_ids:
                campaign_ids = db.execute(
                    select(Campaign.id).where(
                        Campaign.tenant_id == tid,
                        Campaign.is_deleted == False,
                    )
                ).scalars().all()

                for cid in campaign_ids:
                    sync_campaign_data.delay(tid, cid)
                    task_count += 1

                db.expire_all()

            logger.info(f"Queued {task_count} mock campaign sync tasks")
        else:
            # Real mode: use orchestrator per tenant+platform
            from app.base_models import AdPlatform

            platforms = [AdPlatform.META, AdPlatform.TIKTOK, AdPlatform.SNAPCHAT]
            for tid in tenant_ids:
                for platform in platforms:
                    sync_platform_campaigns.delay(tid, platform.value)
                    task_count += 1

            logger.info(f"Queued {task_count} platform sync tasks")

    return {"tasks_queued": task_count}
