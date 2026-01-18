# =============================================================================
# Stratum AI - CRM Sync Celery Tasks
# =============================================================================
"""
Background tasks for CRM data synchronization.

Supports:
- HubSpot CRM
- Zoho CRM

Tasks:
- Scheduled sync of contacts and deals
- Writeback of attribution data
- Identity matching
"""

import asyncio
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SyncSessionLocal, async_session_maker
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMProvider,
    CRMWritebackConfig,
    CRMWritebackSync,
    WritebackStatus,
)

logger = get_task_logger(__name__)


def async_task(func):
    """
    Decorator to run async functions in Celery tasks.
    Celery doesn't natively support async, so we run in an event loop.
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


# =============================================================================
# HubSpot Sync Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3)
@async_task
async def sync_hubspot_data(
    self,
    tenant_id: int,
    full_sync: bool = False,
) -> Dict[str, Any]:
    """
    Sync contacts and deals from HubSpot CRM.

    Args:
        tenant_id: Tenant ID to sync
        full_sync: If True, sync all records. Otherwise, incremental sync.

    Returns:
        Sync results with counts
    """
    from app.services.crm.hubspot_sync import HubSpotSyncService

    logger.info(f"Starting HubSpot sync for tenant {tenant_id}")

    async with async_session_maker() as db:
        sync_service = HubSpotSyncService(db, tenant_id)

        try:
            results = await sync_service.sync_all(full_sync=full_sync)

            logger.info(
                f"HubSpot sync completed for tenant {tenant_id}: "
                f"{results.get('contacts_synced', 0)} contacts, "
                f"{results.get('deals_synced', 0)} deals"
            )

            return results

        except Exception as e:
            logger.error(f"HubSpot sync failed for tenant {tenant_id}: {e}")
            raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=3)
@async_task
async def writeback_hubspot_attribution(
    self,
    tenant_id: int,
    sync_contacts: bool = True,
    sync_deals: bool = True,
    full_sync: bool = False,
) -> Dict[str, Any]:
    """
    Write attribution data back to HubSpot CRM.

    Args:
        tenant_id: Tenant ID
        sync_contacts: Whether to sync contacts
        sync_deals: Whether to sync deals
        full_sync: If True, sync all records

    Returns:
        Writeback results
    """
    from app.services.crm.hubspot_writeback import HubSpotWritebackService

    logger.info(f"Starting HubSpot writeback for tenant {tenant_id}")

    async with async_session_maker() as db:
        writeback_service = HubSpotWritebackService(db, tenant_id)

        # Get modified_since for incremental sync
        modified_since = None
        if not full_sync:
            result = await db.execute(
                select(CRMWritebackConfig).where(
                    CRMWritebackConfig.tenant_id == tenant_id
                )
            )
            config = result.scalar_one_or_none()
            if config and config.last_sync_at:
                modified_since = config.last_sync_at

        try:
            results = await writeback_service.full_sync(
                sync_contacts=sync_contacts,
                sync_deals=sync_deals,
                modified_since=modified_since,
            )

            logger.info(f"HubSpot writeback completed for tenant {tenant_id}")
            return results

        except Exception as e:
            logger.error(f"HubSpot writeback failed for tenant {tenant_id}: {e}")
            raise self.retry(exc=e, countdown=60 * 5)


# =============================================================================
# Zoho CRM Sync Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3)
@async_task
async def sync_zoho_data(
    self,
    tenant_id: int,
    full_sync: bool = False,
    region: str = "com",
) -> Dict[str, Any]:
    """
    Sync contacts, leads, and deals from Zoho CRM.

    Args:
        tenant_id: Tenant ID to sync
        full_sync: If True, sync all records. Otherwise, incremental sync.
        region: Zoho region (com, eu, in, com.au, jp, com.cn)

    Returns:
        Sync results with counts
    """
    from app.services.crm.zoho_sync import ZohoSyncService

    logger.info(f"Starting Zoho CRM sync for tenant {tenant_id}")

    async with async_session_maker() as db:
        sync_service = ZohoSyncService(db, tenant_id, region)

        try:
            results = await sync_service.sync_all(full_sync=full_sync)

            logger.info(
                f"Zoho sync completed for tenant {tenant_id}: "
                f"{results.get('contacts_synced', 0)} contacts, "
                f"{results.get('deals_synced', 0)} deals"
            )

            return results

        except Exception as e:
            logger.error(f"Zoho sync failed for tenant {tenant_id}: {e}")
            raise self.retry(exc=e, countdown=60 * 5)


@shared_task(bind=True, max_retries=3)
@async_task
async def writeback_zoho_attribution(
    self,
    tenant_id: int,
    sync_contacts: bool = True,
    sync_deals: bool = True,
    full_sync: bool = False,
    region: str = "com",
) -> Dict[str, Any]:
    """
    Write attribution data back to Zoho CRM.

    Args:
        tenant_id: Tenant ID
        sync_contacts: Whether to sync contacts
        sync_deals: Whether to sync deals
        full_sync: If True, sync all records
        region: Zoho region

    Returns:
        Writeback results
    """
    from app.services.crm.zoho_writeback import ZohoWritebackService

    logger.info(f"Starting Zoho writeback for tenant {tenant_id}")

    async with async_session_maker() as db:
        writeback_service = ZohoWritebackService(db, tenant_id, region)

        # Get modified_since for incremental sync
        modified_since = None
        if not full_sync:
            result = await db.execute(
                select(CRMConnection).where(
                    and_(
                        CRMConnection.tenant_id == tenant_id,
                        CRMConnection.provider == CRMProvider.ZOHO,
                    )
                )
            )
            connection = result.scalar_one_or_none()
            if connection and connection.last_sync_at:
                modified_since = connection.last_sync_at

        try:
            results = await writeback_service.full_sync(
                sync_contacts=sync_contacts,
                sync_deals=sync_deals,
                modified_since=modified_since,
            )

            logger.info(f"Zoho writeback completed for tenant {tenant_id}")
            return results

        except Exception as e:
            logger.error(f"Zoho writeback failed for tenant {tenant_id}: {e}")
            raise self.retry(exc=e, countdown=60 * 5)


# =============================================================================
# Scheduled Sync Tasks
# =============================================================================

@shared_task
@async_task
async def sync_all_crm_connections() -> Dict[str, Any]:
    """
    Sync all active CRM connections across all tenants.

    This is the main scheduled sync task that runs periodically.
    """
    logger.info("Starting scheduled CRM sync for all connections")

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "hubspot": {"synced": 0, "failed": 0},
        "zoho": {"synced": 0, "failed": 0},
    }

    async with async_session_maker() as db:
        # Get all active CRM connections
        result = await db.execute(
            select(CRMConnection).where(
                CRMConnection.status == CRMConnectionStatus.CONNECTED
            )
        )
        connections = result.scalars().all()

        for connection in connections:
            try:
                if connection.provider == CRMProvider.HUBSPOT:
                    # Dispatch HubSpot sync task
                    sync_hubspot_data.delay(connection.tenant_id, full_sync=False)
                    results["hubspot"]["synced"] += 1

                elif connection.provider == CRMProvider.ZOHO:
                    # Dispatch Zoho sync task
                    sync_zoho_data.delay(
                        connection.tenant_id,
                        full_sync=False,
                        region=settings.zoho_region,
                    )
                    results["zoho"]["synced"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to dispatch sync for {connection.provider.value} "
                    f"tenant {connection.tenant_id}: {e}"
                )
                if connection.provider == CRMProvider.HUBSPOT:
                    results["hubspot"]["failed"] += 1
                elif connection.provider == CRMProvider.ZOHO:
                    results["zoho"]["failed"] += 1

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"CRM sync dispatch complete: {results}")

    return results


@shared_task
@async_task
async def run_scheduled_writebacks() -> Dict[str, Any]:
    """
    Run scheduled writeback syncs for all configured connections.

    Checks writeback configs for auto_sync_enabled and runs if due.
    """
    logger.info("Checking for scheduled CRM writebacks")

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "writebacks_triggered": 0,
    }

    async with async_session_maker() as db:
        # Get all writeback configs with auto_sync enabled
        result = await db.execute(
            select(CRMWritebackConfig).where(
                and_(
                    CRMWritebackConfig.enabled == True,
                    CRMWritebackConfig.auto_sync_enabled == True,
                )
            )
        )
        configs = result.scalars().all()

        now = datetime.now(timezone.utc)

        for config in configs:
            # Check if writeback is due
            if config.next_sync_at and config.next_sync_at > now:
                continue

            try:
                # Get connection to determine provider
                conn_result = await db.execute(
                    select(CRMConnection).where(
                        CRMConnection.id == config.connection_id
                    )
                )
                connection = conn_result.scalar_one_or_none()

                if not connection:
                    continue

                if connection.provider == CRMProvider.HUBSPOT:
                    writeback_hubspot_attribution.delay(
                        config.tenant_id,
                        sync_contacts=config.sync_contacts,
                        sync_deals=config.sync_deals,
                    )
                elif connection.provider == CRMProvider.ZOHO:
                    writeback_zoho_attribution.delay(
                        config.tenant_id,
                        sync_contacts=config.sync_contacts,
                        sync_deals=config.sync_deals,
                        region=settings.zoho_region,
                    )

                # Update next sync time
                config.next_sync_at = now + timedelta(hours=config.sync_interval_hours)
                results["writebacks_triggered"] += 1

            except Exception as e:
                logger.error(f"Failed to trigger writeback for config {config.id}: {e}")

        await db.commit()

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Writeback scheduling complete: {results}")

    return results


# =============================================================================
# Identity Matching Task
# =============================================================================

@shared_task(bind=True, max_retries=3)
@async_task
async def run_identity_matching(
    self,
    tenant_id: int,
) -> Dict[str, Any]:
    """
    Run identity matching for a tenant to link CRM contacts to ad touchpoints.

    Args:
        tenant_id: Tenant ID

    Returns:
        Matching results
    """
    from app.services.crm.identity_matching import IdentityMatcher

    logger.info(f"Running identity matching for tenant {tenant_id}")

    async with async_session_maker() as db:
        identity_matcher = IdentityMatcher(db, tenant_id)

        try:
            results = await identity_matcher.match_contacts_to_touchpoints()

            logger.info(
                f"Identity matching completed for tenant {tenant_id}: "
                f"matched {results.get('contacts_matched', 0)} of "
                f"{results.get('contacts_processed', 0)} contacts"
            )

            return results

        except Exception as e:
            logger.error(f"Identity matching failed for tenant {tenant_id}: {e}")
            raise self.retry(exc=e, countdown=60 * 2)


# =============================================================================
# Celery Beat Schedule Configuration
# =============================================================================

# These schedules can be added to the main Celery app configuration
CRM_BEAT_SCHEDULE = {
    'sync-all-crm-hourly': {
        'task': 'app.workers.crm_sync_tasks.sync_all_crm_connections',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'crm_sync'},
    },
    'run-writebacks-every-6-hours': {
        'task': 'app.workers.crm_sync_tasks.run_scheduled_writebacks',
        'schedule': timedelta(hours=6),
        'options': {'queue': 'crm_sync'},
    },
}
