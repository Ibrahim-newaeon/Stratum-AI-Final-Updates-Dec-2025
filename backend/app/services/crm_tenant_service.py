# =============================================================================
# Stratum AI - Tenant-scoped CRM service
# =============================================================================
"""Read and mutate a single tenant's CRM data.

The superadmin surface in ``api/v1/endpoints/integrations.py`` reaches CRM data
through the provider-specific services (``HubSpotSyncService`` and friends),
which is right for provider operations — connect, disconnect, webhook. It is
wrong for the tenant views, which ask provider-agnostic questions: "what are my
connections", "what are my deals". Answering those through a provider service
would mean picking a provider first, which is exactly the thing the caller does
not know.

So every function here filters on ``tenant_id`` and nothing else identifies the
row set. ``tenant_id`` is always the first positional argument after the
session, is always supplied by the route from the authenticated user, and is
never accepted from a request body.

Mutations are not audited here: ``AuditMiddleware`` records every successful
state-changing request globally, which is how the rest of this codebase does it.
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMContact,
    CRMDeal,
    CRMProvider,
    CRMWritebackConfig,
    DealStage,
)
from app.schemas.crm import WritebackConfigUpdate

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Connections
# -----------------------------------------------------------------------------


async def list_connections(db: AsyncSession, tenant_id: int) -> list[CRMConnection]:
    """Every CRM connection belonging to this tenant, newest first."""
    result = await db.execute(
        select(CRMConnection)
        .where(CRMConnection.tenant_id == tenant_id)
        .order_by(CRMConnection.created_at.desc())
    )
    return list(result.scalars().all())


async def get_connection(
    db: AsyncSession, tenant_id: int, connection_id: UUID
) -> Optional[CRMConnection]:
    """One connection, or None.

    The tenant filter sits in the WHERE clause rather than in a check after the
    lookup: a connection belonging to another tenant must be indistinguishable
    from one that does not exist, so the route can answer 404 either way
    without leaking that the id is real.
    """
    result = await db.execute(
        select(CRMConnection).where(
            CRMConnection.tenant_id == tenant_id,
            CRMConnection.id == connection_id,
        )
    )
    return result.scalar_one_or_none()


# -----------------------------------------------------------------------------
# Contacts and deals
# -----------------------------------------------------------------------------


async def list_contacts(
    db: AsyncSession,
    tenant_id: int,
    *,
    lifecycle_stage: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CRMContact], int]:
    """A page of contacts plus the total matching count."""
    conditions = [CRMContact.tenant_id == tenant_id]
    if lifecycle_stage:
        conditions.append(CRMContact.lifecycle_stage == lifecycle_stage)

    total = await db.scalar(
        select(func.count()).select_from(CRMContact).where(*conditions)
    )
    result = await db.execute(
        select(CRMContact)
        .where(*conditions)
        .order_by(CRMContact.last_touch_ts.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


async def list_deals(
    db: AsyncSession,
    tenant_id: int,
    *,
    stage: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CRMDeal], int]:
    """A page of deals plus the total matching count."""
    conditions = [CRMDeal.tenant_id == tenant_id]
    if stage:
        conditions.append(CRMDeal.stage_normalized == stage)

    total = await db.scalar(
        select(func.count()).select_from(CRMDeal).where(*conditions)
    )
    result = await db.execute(
        select(CRMDeal)
        .where(*conditions)
        .order_by(CRMDeal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------


async def get_pipeline_summary(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    """Deal counts and values by stage, across every provider.

    Grouped in one query per axis rather than one per stage: the equivalent on
    HubSpotSyncService issues a SELECT for each member of DealStage and loads
    every matching row into Python to sum it, which is a query per stage plus
    the whole deal table in memory.

    Values are summed from ``amount_cents`` and divided once at the end, so the
    arithmetic stays in integers until it is presented.
    """
    connection_count = await db.scalar(
        select(func.count())
        .select_from(CRMConnection)
        .where(CRMConnection.tenant_id == tenant_id)
    )
    if not connection_count:
        return {"status": "not_connected"}

    open_rows = await db.execute(
        select(
            CRMDeal.stage_normalized,
            func.count(CRMDeal.id),
            func.coalesce(func.sum(CRMDeal.amount_cents), 0),
        )
        .where(
            CRMDeal.tenant_id == tenant_id,
            CRMDeal.is_closed.is_(False),
        )
        .group_by(CRMDeal.stage_normalized)
    )

    stage_counts = {stage.value: 0 for stage in DealStage}
    stage_values = {stage.value: 0.0 for stage in DealStage}
    total_pipeline_cents = 0
    for stage, count, value_cents in open_rows:
        if stage is None:
            continue
        key = stage.value if hasattr(stage, "value") else str(stage)
        stage_counts[key] = int(count)
        stage_values[key] = int(value_cents) / 100
        total_pipeline_cents += int(value_cents)

    won_count, won_cents = (
        await db.execute(
            select(
                func.count(CRMDeal.id),
                func.coalesce(func.sum(CRMDeal.amount_cents), 0),
            ).where(
                CRMDeal.tenant_id == tenant_id,
                CRMDeal.is_won.is_(True),
            )
        )
    ).one()

    last_sync_at = await db.scalar(
        select(func.max(CRMConnection.last_sync_at)).where(
            CRMConnection.tenant_id == tenant_id
        )
    )

    return {
        "status": "ok",
        "stage_counts": stage_counts,
        "stage_values": stage_values,
        "total_pipeline_value": total_pipeline_cents / 100,
        "total_won_value": int(won_cents) / 100,
        "won_deal_count": int(won_count),
        "last_sync_at": last_sync_at.isoformat() if last_sync_at else None,
    }


# -----------------------------------------------------------------------------
# Writeback configuration
# -----------------------------------------------------------------------------


async def get_writeback_config(
    db: AsyncSession, tenant_id: int
) -> Optional[CRMWritebackConfig]:
    """This tenant's writeback config, or None if it has never been created."""
    result = await db.execute(
        select(CRMWritebackConfig).where(CRMWritebackConfig.tenant_id == tenant_id)
    )
    return result.scalars().first()


async def update_writeback_config(
    db: AsyncSession,
    tenant_id: int,
    payload: WritebackConfigUpdate,
) -> Optional[CRMWritebackConfig]:
    """Apply the supplied writeback settings.

    Returns None when the tenant has no config row and no connection to hang
    one off, which the route turns into a 404 — creating a config for a tenant
    with no CRM would produce a row that nothing can ever sync.

    ``exclude_unset`` means an absent field is left alone rather than reset to
    its default, so a client sending one toggle cannot silently clear the rest.
    """
    config = await get_writeback_config(db, tenant_id)

    if config is None:
        connection = (
            (
                await db.execute(
                    select(CRMConnection)
                    .where(CRMConnection.tenant_id == tenant_id)
                    .order_by(CRMConnection.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if connection is None:
            return None
        config = CRMWritebackConfig(tenant_id=tenant_id, connection_id=connection.id)
        db.add(config)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


# -----------------------------------------------------------------------------
# Sync
# -----------------------------------------------------------------------------


async def trigger_sync(
    db: AsyncSession, tenant_id: int, connection_id: UUID
) -> Optional[dict[str, Any]]:
    """Queue a sync for one connection.

    Dispatched to Celery rather than awaited inline. The superadmin
    ``/integrations/{provider}/sync`` routes call ``sync_all()`` in the request
    and hold the connection open for the length of a full CRM pull; a tenant
    clicking a button in the UI should not.

    Returns None if the connection does not belong to this tenant.
    """
    connection = await get_connection(db, tenant_id, connection_id)
    if connection is None:
        return None

    if connection.status != CRMConnectionStatus.CONNECTED:
        return {
            "connection_id": connection.id,
            "provider": connection.provider.value,
            "status": "not_connected",
            "message": "Connection is not active; reconnect before syncing.",
        }

    # Imported here, not at module scope: app.workers.crm_sync_tasks imports the
    # Celery app, and importing it from a service pulls the worker's whole task
    # graph into the API process at startup.
    from app.workers.crm_sync_tasks import sync_hubspot_data, sync_pipedrive_data

    dispatch = {
        CRMProvider.HUBSPOT: sync_hubspot_data,
        CRMProvider.PIPEDRIVE: sync_pipedrive_data,
    }.get(connection.provider)

    if dispatch is None:
        return {
            "connection_id": connection.id,
            "provider": connection.provider.value,
            "status": "unsupported",
            "message": f"No sync task for provider {connection.provider.value}.",
        }

    dispatch.delay(tenant_id, full_sync=False)
    logger.info(
        "crm_sync_queued",
        tenant_id=tenant_id,
        connection_id=str(connection.id),
        provider=connection.provider.value,
    )

    return {
        "connection_id": connection.id,
        "provider": connection.provider.value,
        "status": "queued",
        "message": "Sync queued.",
    }
