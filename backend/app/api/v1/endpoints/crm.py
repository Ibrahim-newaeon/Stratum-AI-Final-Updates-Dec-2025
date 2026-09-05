# =============================================================================
# Stratum AI - Tenant-facing CRM endpoints
# =============================================================================
"""The CRM surface the tenant UI calls, at ``/integrations/crm``.

``frontend/src/api/crm.ts`` has always pointed here, but no route ever existed:
the integrations router mounts at ``/integrations`` and its paths are
``/contacts``, ``/deals``, ``/pipeline/summary``, ``/hubspot/*`` and
``/pipedrive/*``. Every call from the Settings > Integrations views 404'd.

Those existing routes could not simply be reused. All of them are guarded by
``require_super_admin`` and take the tenant as a ``?tenant_id=`` query
parameter — an admin-console contract, where an operator names the tenant they
are acting on. A tenant user has no business supplying a tenant id at all, and
would be rejected by the guard before the path even mattered. So this router
derives the tenant from the caller's own token and never reads one from the
request.

Rate limiting and audit are middleware-wide (``RateLimitMiddleware``,
``AuditMiddleware``), so there are no per-route decorators for either here —
the same as every other endpoint module in this package.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, get_current_user
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.schemas.crm import (
    CRMConnectionRead,
    CRMContactRead,
    CRMDealRead,
    PipelineSummaryRead,
    SyncTriggerRead,
    WritebackConfigRead,
    WritebackConfigUpdate,
)
from app.schemas.response import APIResponse, PaginatedResponse
from app.services import crm_tenant_service

router = APIRouter(prefix="/integrations/crm", tags=["crm"])
logger = get_logger(__name__)


def _page_meta(total: int, limit: int, offset: int) -> tuple[int, int]:
    """Translate limit/offset into the page numbers PaginatedResponse wants."""
    page = (offset // limit) + 1 if limit else 1
    total_pages = (total + limit - 1) // limit if limit else 0
    return page, total_pages


# -----------------------------------------------------------------------------
# Connections
# -----------------------------------------------------------------------------


@router.get(
    "/connections",
    response_model=APIResponse[list[CRMConnectionRead]],
    summary="List this tenant's CRM connections",
)
async def list_connections(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[list[CRMConnectionRead]]:
    """Every CRM connection for the authenticated tenant, newest first.

    Provider-agnostic on purpose: this is what the Integrations view calls to
    discover which CRMs are connected, so it cannot be asked to name one.
    """
    connections = await crm_tenant_service.list_connections(db, user.tenant_id)
    return APIResponse(
        success=True,
        data=[CRMConnectionRead.model_validate(c) for c in connections],
    )


@router.post(
    "/connections/{connection_id}/sync",
    response_model=APIResponse[SyncTriggerRead],
    summary="Queue a sync for one connection",
)
async def trigger_connection_sync(
    connection_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[SyncTriggerRead]:
    """Queue a CRM sync for one of this tenant's connections.

    Returns 404 for a connection this tenant does not own, deliberately not
    403: whether the id exists at all is not something to confirm.
    """
    result = await crm_tenant_service.trigger_sync(db, user.tenant_id, connection_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
        )
    return APIResponse(
        success=result["status"] in {"queued"},
        data=SyncTriggerRead(**result),
        message=result.get("message"),
    )


# -----------------------------------------------------------------------------
# Contacts and deals
# -----------------------------------------------------------------------------


@router.get(
    "/contacts",
    response_model=APIResponse[PaginatedResponse[CRMContactRead]],
    summary="List synced CRM contacts",
)
async def list_contacts(
    lifecycle_stage: Optional[str] = Query(None, description="Filter by stage"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PaginatedResponse[CRMContactRead]]:
    """A page of this tenant's synced contacts, most recently touched first.

    No email, name, phone or company is returned: ``CRMContact`` stores only
    SHA256 hashes of the identifiers, so there is no plaintext to serialise.
    """
    contacts, total = await crm_tenant_service.list_contacts(
        db, user.tenant_id, lifecycle_stage=lifecycle_stage, limit=limit, offset=offset
    )
    page, total_pages = _page_meta(total, limit, offset)
    return APIResponse(
        success=True,
        data=PaginatedResponse[CRMContactRead](
            items=[CRMContactRead.model_validate(c) for c in contacts],
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/deals",
    response_model=APIResponse[PaginatedResponse[CRMDealRead]],
    summary="List synced CRM deals",
)
async def list_deals(
    stage: Optional[str] = Query(None, description="Filter by normalized stage"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PaginatedResponse[CRMDealRead]]:
    """A page of this tenant's synced deals, newest first.

    Deal value is ``amount_cents``; the model marks the float ``amount`` column
    deprecated and unfit for calculation, so it is not exposed.
    """
    deals, total = await crm_tenant_service.list_deals(
        db, user.tenant_id, stage=stage, limit=limit, offset=offset
    )
    page, total_pages = _page_meta(total, limit, offset)
    return APIResponse(
        success=True,
        data=PaginatedResponse[CRMDealRead](
            items=[CRMDealRead.model_validate(d) for d in deals],
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
        ),
    )


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------


@router.get(
    "/pipeline/summary",
    response_model=APIResponse[PipelineSummaryRead],
    summary="Pipeline totals by stage",
)
async def pipeline_summary(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PipelineSummaryRead]:
    """Open-deal counts and values by stage, plus won totals, across providers.

    ``status`` is ``not_connected`` when the tenant has no CRM connection at
    all, which the view renders as an empty state rather than as zeroes.
    """
    summary = await crm_tenant_service.get_pipeline_summary(db, user.tenant_id)
    return APIResponse(success=True, data=PipelineSummaryRead(**summary))


# -----------------------------------------------------------------------------
# Writeback configuration
# -----------------------------------------------------------------------------


@router.get(
    "/writeback/config",
    response_model=APIResponse[Optional[WritebackConfigRead]],
    summary="Get writeback settings",
)
async def get_writeback_config(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[Optional[WritebackConfigRead]]:
    """This tenant's writeback settings.

    ``data`` is null when no config exists yet — a tenant that has connected a
    CRM but never opened the writeback tab. That is not an error, so the view
    can show defaults instead of handling a 404.
    """
    config = await crm_tenant_service.get_writeback_config(db, user.tenant_id)
    return APIResponse(
        success=True,
        data=WritebackConfigRead.model_validate(config) if config else None,
    )


@router.put(
    "/writeback/config",
    response_model=APIResponse[WritebackConfigRead],
    summary="Update writeback settings",
)
async def update_writeback_config(
    payload: WritebackConfigUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[WritebackConfigRead]:
    """Update writeback settings, creating the config row on first write.

    Only fields present in the body are changed, so sending one toggle cannot
    reset the others to their defaults. Returns 404 when the tenant has no CRM
    connection to attach the config to.
    """
    config = await crm_tenant_service.update_writeback_config(
        db, user.tenant_id, payload
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CRM connection to configure writeback for",
        )
    return APIResponse(success=True, data=WritebackConfigRead.model_validate(config))
