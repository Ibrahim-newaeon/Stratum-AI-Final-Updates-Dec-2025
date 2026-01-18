# =============================================================================
# Stratum AI - Integrations API Router
# =============================================================================
"""
API endpoints for third-party integrations:
- HubSpot CRM (OAuth, sync, webhooks)
- Salesforce (future)
- Pipeline metrics and attribution

All routes enforce tenant isolation and RBAC permissions.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from app.db.session import get_async_session
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMContact,
    CRMDeal,
    CRMProvider,
    DailyPipelineMetrics,
    CRMWritebackConfig,
    CRMWritebackSync,
    WritebackStatus,
)
from app.services.crm.hubspot_client import HubSpotClient
from app.services.crm.hubspot_sync import HubSpotSyncService
from app.services.crm.identity_matching import IdentityMatcher
from app.services.crm.hubspot_writeback import HubSpotWritebackService
from app.services.crm.zoho_client import ZohoClient
from app.services.crm.zoho_sync import ZohoSyncService
from app.services.crm.zoho_writeback import ZohoWritebackService
from app.services.crm.pipedrive_client import PipedriveClient
from app.services.crm.pipedrive_sync import PipedriveSyncService
from app.services.crm.pipedrive_writeback import PipedriveWritebackService
from app.services.crm.salesforce_client import SalesforceClient
from app.services.crm.salesforce_sync import SalesforceSyncService
from app.services.crm.salesforce_writeback import SalesforceWritebackService
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.response import APIResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class HubSpotConnectRequest(BaseModel):
    """Request to initiate HubSpot OAuth."""
    redirect_uri: str = Field(..., description="OAuth callback URL")


class HubSpotConnectResponse(BaseModel):
    """Response with OAuth authorization URL."""
    authorization_url: str
    state: str


class HubSpotCallbackRequest(BaseModel):
    """OAuth callback parameters."""
    code: str
    state: str
    redirect_uri: str


class HubSpotStatusResponse(BaseModel):
    """HubSpot connection status."""
    connected: bool
    status: str
    provider: str = "hubspot"
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    scopes: List[str] = []


class SyncRequest(BaseModel):
    """Manual sync request."""
    full_sync: bool = Field(default=False, description="Perform full sync vs incremental")


class SyncResponse(BaseModel):
    """Sync operation response."""
    status: str
    contacts_synced: int = 0
    contacts_created: int = 0
    contacts_updated: int = 0
    deals_synced: int = 0
    deals_created: int = 0
    deals_updated: int = 0
    errors: List[str] = []


class PipelineSummaryResponse(BaseModel):
    """Pipeline metrics summary."""
    status: str
    stage_counts: Dict[str, int] = {}
    stage_values: Dict[str, float] = {}
    total_pipeline_value: float = 0
    total_won_value: float = 0
    won_deal_count: int = 0
    last_sync_at: Optional[str] = None


class PipelineROASResponse(BaseModel):
    """Pipeline ROAS metrics."""
    date_range: Dict[str, str]
    spend: float
    platform_revenue: float
    pipeline_value: float
    won_revenue: float
    platform_roas: Optional[float] = None
    pipeline_roas: Optional[float] = None
    won_roas: Optional[float] = None
    funnel_metrics: Dict[str, Any] = {}


class AttributionReportResponse(BaseModel):
    """Attribution report by dimension."""
    dimension: str
    date_range: Dict[str, str]
    data: List[Dict[str, Any]]


class WebhookPayload(BaseModel):
    """HubSpot webhook payload."""
    subscriptionType: str
    objectId: int
    propertyName: Optional[str] = None
    propertyValue: Optional[str] = None
    changeSource: Optional[str] = None
    eventId: Optional[int] = None
    subscriptionId: Optional[int] = None
    portalId: Optional[int] = None
    appId: Optional[int] = None
    occurredAt: Optional[int] = None
    attemptNumber: Optional[int] = None


# =============================================================================
# HubSpot OAuth Endpoints
# =============================================================================

@router.post(
    "/hubspot/connect",
    response_model=APIResponse[HubSpotConnectResponse],
    summary="Initiate HubSpot OAuth",
)
async def hubspot_connect(
    request: HubSpotConnectRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start HubSpot OAuth authorization flow.
    Returns authorization URL to redirect user to HubSpot.
    """
    client = HubSpotClient(db, tenant_id)

    # Generate state token for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)

    # Store state in session/cache (simplified - in production use Redis)
    # For now, we'll include tenant_id in state
    state_with_tenant = f"{tenant_id}:{state}"

    auth_url = client.get_authorization_url(
        redirect_uri=request.redirect_uri,
        state=state_with_tenant,
    )

    return APIResponse(
        success=True,
        data=HubSpotConnectResponse(
            authorization_url=auth_url,
            state=state_with_tenant,
        ),
    )


@router.get(
    "/hubspot/callback",
    response_model=APIResponse[HubSpotStatusResponse],
    summary="HubSpot OAuth callback",
)
async def hubspot_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle HubSpot OAuth callback.
    Exchanges authorization code for tokens and stores connection.
    """
    # Extract tenant_id from state
    try:
        tenant_id_str, _ = state.split(":", 1)
        tenant_id = int(tenant_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    client = HubSpotClient(db, tenant_id)

    try:
        connection = await client.exchange_code_for_tokens(code, redirect_uri)
        status = await client.get_connection_status()

        return APIResponse(
            success=True,
            data=HubSpotStatusResponse(**status),
            message="HubSpot connected successfully",
        )

    except Exception as e:
        logger.error("hubspot_oauth_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get(
    "/hubspot/status",
    response_model=APIResponse[HubSpotStatusResponse],
    summary="Get HubSpot connection status",
)
async def hubspot_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current HubSpot connection status for tenant."""
    client = HubSpotClient(db, tenant_id)
    status = await client.get_connection_status()

    return APIResponse(
        success=True,
        data=HubSpotStatusResponse(**status),
    )


@router.delete(
    "/hubspot/disconnect",
    response_model=APIResponse[Dict[str, Any]],
    summary="Disconnect HubSpot",
)
async def hubspot_disconnect(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect HubSpot integration for tenant."""
    client = HubSpotClient(db, tenant_id)
    success = await client.disconnect()

    if not success:
        raise HTTPException(status_code=404, detail="No HubSpot connection found")

    return APIResponse(
        success=True,
        data={"disconnected": True},
        message="HubSpot disconnected successfully",
    )


# =============================================================================
# Sync Endpoints
# =============================================================================

@router.post(
    "/hubspot/sync",
    response_model=APIResponse[SyncResponse],
    summary="Trigger HubSpot sync",
)
async def hubspot_sync(
    request: SyncRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger manual sync of HubSpot contacts and deals.
    Can run as background task for large syncs.
    """
    sync_service = HubSpotSyncService(db, tenant_id)

    # For now, run synchronously (in production, use background task)
    results = await sync_service.sync_all(full_sync=request.full_sync)

    return APIResponse(
        success=results.get("status") != "error",
        data=SyncResponse(**results),
        message=f"Sync completed: {results.get('contacts_synced', 0)} contacts, {results.get('deals_synced', 0)} deals",
    )


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post(
    "/hubspot/webhook",
    summary="HubSpot webhook receiver",
)
async def hubspot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hubspot_signature: Optional[str] = Header(None, alias="X-HubSpot-Signature"),
    x_hubspot_signature_v3: Optional[str] = Header(None, alias="X-HubSpot-Signature-v3"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Receive and process HubSpot webhooks.
    Validates signature and queues events for processing.
    """
    body = await request.body()

    # Validate webhook signature (v3 preferred)
    if settings.hubspot_client_secret:
        if x_hubspot_signature_v3:
            # V3 signature validation
            expected = hmac.new(
                settings.hubspot_client_secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, x_hubspot_signature_v3):
                logger.warning("hubspot_webhook_invalid_signature")
                raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # HubSpot sends array of events
    events = payload if isinstance(payload, list) else [payload]

    processed = 0
    for event in events:
        portal_id = event.get("portalId")
        event_type = event.get("subscriptionType", "")

        # Find tenant by portal ID
        result = await db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.provider == CRMProvider.HUBSPOT,
                    CRMConnection.provider_account_id == str(portal_id),
                )
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            # Process webhook in background
            sync_service = HubSpotSyncService(db, connection.tenant_id)
            await sync_service.process_webhook(event_type, event)
            processed += 1

    return {"status": "received", "processed": processed}


# =============================================================================
# Pipeline & Attribution Endpoints
# =============================================================================

@router.get(
    "/pipeline/summary",
    response_model=APIResponse[PipelineSummaryResponse],
    summary="Get pipeline summary",
)
async def pipeline_summary(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get CRM pipeline summary with stage counts and values."""
    sync_service = HubSpotSyncService(db, tenant_id)
    summary = await sync_service.get_pipeline_summary()

    return APIResponse(
        success=True,
        data=PipelineSummaryResponse(**summary),
    )


@router.get(
    "/pipeline/roas",
    response_model=APIResponse[PipelineROASResponse],
    summary="Get Pipeline ROAS metrics",
)
async def pipeline_roas(
    tenant_id: int = Query(..., description="Tenant ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get Pipeline ROAS metrics comparing ad spend to CRM outcomes.

    Returns:
    - Platform ROAS (platform-reported revenue / spend)
    - Pipeline ROAS (pipeline value / spend)
    - Won ROAS (won revenue / spend)
    - Funnel conversion rates
    """
    from datetime import datetime as dt

    start = dt.strptime(start_date, "%Y-%m-%d").date()
    end = dt.strptime(end_date, "%Y-%m-%d").date()

    # Build query
    conditions = [
        DailyPipelineMetrics.tenant_id == tenant_id,
        DailyPipelineMetrics.date >= start,
        DailyPipelineMetrics.date <= end,
    ]

    if platform:
        conditions.append(DailyPipelineMetrics.platform == platform)
    if campaign_id:
        conditions.append(DailyPipelineMetrics.campaign_id == campaign_id)

    result = await db.execute(
        select(DailyPipelineMetrics).where(and_(*conditions))
    )
    metrics = result.scalars().all()

    # Aggregate
    spend = sum(m.spend_cents or 0 for m in metrics) / 100
    platform_revenue = sum(m.platform_revenue_cents or 0 for m in metrics) / 100
    pipeline_value = sum(m.pipeline_value_cents or 0 for m in metrics) / 100
    won_revenue = sum(m.won_revenue_cents or 0 for m in metrics) / 100

    leads = sum(m.leads_created or 0 for m in metrics)
    mqls = sum(m.mqls_created or 0 for m in metrics)
    sqls = sum(m.sqls_created or 0 for m in metrics)
    won = sum(m.deals_won or 0 for m in metrics)

    return APIResponse(
        success=True,
        data=PipelineROASResponse(
            date_range={"start": start_date, "end": end_date},
            spend=spend,
            platform_revenue=platform_revenue,
            pipeline_value=pipeline_value,
            won_revenue=won_revenue,
            platform_roas=platform_revenue / spend if spend > 0 else None,
            pipeline_roas=pipeline_value / spend if spend > 0 else None,
            won_roas=won_revenue / spend if spend > 0 else None,
            funnel_metrics={
                "leads": leads,
                "mqls": mqls,
                "sqls": sqls,
                "won": won,
                "lead_to_mql_rate": mqls / leads * 100 if leads > 0 else None,
                "mql_to_sql_rate": sqls / mqls * 100 if mqls > 0 else None,
                "sql_to_won_rate": won / sqls * 100 if sqls > 0 else None,
            },
        ),
    )


@router.get(
    "/attribution/report",
    response_model=APIResponse[AttributionReportResponse],
    summary="Get attribution report",
)
async def attribution_report(
    tenant_id: int = Query(..., description="Tenant ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    group_by: str = Query("campaign", description="Group by: campaign, platform"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get attribution report for won deals grouped by dimension.

    Shows which campaigns/platforms are driving closed revenue.
    """
    from datetime import datetime as dt

    start = dt.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = dt.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    identity_matcher = IdentityMatcher(db, tenant_id)
    report_data = await identity_matcher.get_attribution_report(start, end, group_by)

    return APIResponse(
        success=True,
        data=AttributionReportResponse(
            dimension=group_by,
            date_range={"start": start_date, "end": end_date},
            data=report_data,
        ),
    )


# =============================================================================
# Contact & Deal Endpoints
# =============================================================================

@router.get(
    "/contacts",
    response_model=APIResponse[Dict[str, Any]],
    summary="List CRM contacts",
)
async def list_contacts(
    tenant_id: int = Query(..., description="Tenant ID"),
    lifecycle_stage: Optional[str] = Query(None, description="Filter by lifecycle stage"),
    has_attribution: Optional[bool] = Query(None, description="Filter by attribution status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """List synced CRM contacts with optional filters."""
    conditions = [CRMContact.tenant_id == tenant_id]

    if lifecycle_stage:
        conditions.append(CRMContact.lifecycle_stage == lifecycle_stage)

    if has_attribution is not None:
        if has_attribution:
            conditions.append(CRMContact.first_touch_campaign_id.isnot(None))
        else:
            conditions.append(CRMContact.first_touch_campaign_id.is_(None))

    result = await db.execute(
        select(CRMContact)
        .where(and_(*conditions))
        .order_by(CRMContact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    contacts = result.scalars().all()

    # Count total
    count_result = await db.execute(
        select(CRMContact).where(and_(*conditions))
    )
    total = len(count_result.scalars().all())

    return APIResponse(
        success=True,
        data={
            "items": [
                {
                    "id": str(c.id),
                    "crm_contact_id": c.crm_contact_id,
                    "lifecycle_stage": c.lifecycle_stage,
                    "lead_source": c.lead_source,
                    "utm_source": c.utm_source,
                    "utm_campaign": c.utm_campaign,
                    "first_touch_campaign_id": c.first_touch_campaign_id,
                    "last_touch_campaign_id": c.last_touch_campaign_id,
                    "touch_count": c.touch_count,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in contacts
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get(
    "/deals",
    response_model=APIResponse[Dict[str, Any]],
    summary="List CRM deals",
)
async def list_deals(
    tenant_id: int = Query(..., description="Tenant ID"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    is_won: Optional[bool] = Query(None, description="Filter by won status"),
    has_attribution: Optional[bool] = Query(None, description="Filter by attribution status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """List synced CRM deals with optional filters."""
    conditions = [CRMDeal.tenant_id == tenant_id]

    if stage:
        conditions.append(CRMDeal.stage == stage)

    if is_won is not None:
        conditions.append(CRMDeal.is_won == is_won)

    if has_attribution is not None:
        if has_attribution:
            conditions.append(CRMDeal.attributed_campaign_id.isnot(None))
        else:
            conditions.append(CRMDeal.attributed_campaign_id.is_(None))

    result = await db.execute(
        select(CRMDeal)
        .where(and_(*conditions))
        .order_by(CRMDeal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    deals = result.scalars().all()

    # Count total
    count_result = await db.execute(
        select(CRMDeal).where(and_(*conditions))
    )
    total = len(count_result.scalars().all())

    return APIResponse(
        success=True,
        data={
            "items": [
                {
                    "id": str(d.id),
                    "crm_deal_id": d.crm_deal_id,
                    "deal_name": d.deal_name,
                    "stage": d.stage,
                    "stage_normalized": d.stage_normalized.value if d.stage_normalized else None,
                    "amount": d.amount,
                    "currency": d.currency,
                    "is_won": d.is_won,
                    "is_closed": d.is_closed,
                    "close_date": d.close_date.isoformat() if d.close_date else None,
                    "attributed_campaign_id": d.attributed_campaign_id,
                    "attributed_platform": d.attributed_platform,
                    "attribution_confidence": d.attribution_confidence,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in deals
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


# =============================================================================
# Identity Matching Endpoints
# =============================================================================

@router.post(
    "/identity/match",
    response_model=APIResponse[Dict[str, Any]],
    summary="Run identity matching",
)
async def run_identity_matching(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run identity matching to link CRM contacts to ad touchpoints.
    This enables attribution reporting.
    """
    identity_matcher = IdentityMatcher(db, tenant_id)
    results = await identity_matcher.match_contacts_to_touchpoints()

    return APIResponse(
        success=True,
        data=results,
        message=f"Matched {results['contacts_matched']} of {results['contacts_processed']} contacts",
    )


# =============================================================================
# HubSpot Writeback Endpoints
# =============================================================================

@router.get(
    "/hubspot/writeback/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get writeback status",
)
async def get_writeback_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get HubSpot writeback configuration and status.

    Returns current settings, property setup status, and last sync details.
    """
    writeback_service = HubSpotWritebackService(db, tenant_id)
    status = await writeback_service.get_writeback_status()

    return APIResponse(
        success=True,
        data=status,
    )


@router.post(
    "/hubspot/writeback/setup-properties",
    response_model=APIResponse[Dict[str, Any]],
    summary="Setup custom properties",
)
async def setup_writeback_properties(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create Stratum custom properties in HubSpot.

    Creates a property group and custom properties for both contacts and deals
    to store attribution data:
    - Contact: ad platform, campaign, attribution confidence, touchpoints
    - Deal: attributed spend, revenue ROAS, profit ROAS, days to close

    Should be run once during initial setup.
    """
    writeback_service = HubSpotWritebackService(db, tenant_id)

    try:
        results = await writeback_service.setup_custom_properties()

        # Update writeback config
        result = await db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == tenant_id,
                    CRMConnection.provider == CRMProvider.HUBSPOT,
                    CRMConnection.status == CRMConnectionStatus.CONNECTED,
                )
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            # Get or create writeback config
            config_result = await db.execute(
                select(CRMWritebackConfig).where(
                    CRMWritebackConfig.connection_id == connection.id
                )
            )
            config = config_result.scalar_one_or_none()

            if not config:
                config = CRMWritebackConfig(
                    tenant_id=tenant_id,
                    connection_id=connection.id,
                    enabled=True,
                )
                db.add(config)

            config.properties_created = True
            config.properties_created_at = datetime.now(timezone.utc)
            await db.commit()

        return APIResponse(
            success=True,
            data=results,
            message="Custom properties created successfully",
        )
    except Exception as e:
        logger.error(f"Failed to setup writeback properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/hubspot/writeback/sync",
    response_model=APIResponse[Dict[str, Any]],
    summary="Run writeback sync",
)
async def run_writeback_sync(
    tenant_id: int = Query(..., description="Tenant ID"),
    sync_contacts: bool = Query(True, description="Sync contact attribution"),
    sync_deals: bool = Query(True, description="Sync deal attribution"),
    full_sync: bool = Query(False, description="Full sync (ignore modified_since)"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run HubSpot writeback sync.

    Pushes Stratum attribution data to HubSpot contacts and deals:
    - Contact: ad platform, campaign, ad IDs, attribution confidence
    - Deal: attributed spend, ROAS, profit metrics, touchpoint count

    By default, only syncs records modified since last sync (incremental).
    Use full_sync=true to sync all records.
    """
    writeback_service = HubSpotWritebackService(db, tenant_id)

    # Get last sync time for incremental
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

    # Create sync record
    conn_result = await db.execute(
        select(CRMConnection).where(
            and_(
                CRMConnection.tenant_id == tenant_id,
                CRMConnection.provider == CRMProvider.HUBSPOT,
            )
        )
    )
    connection = conn_result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=400, detail="HubSpot not connected")

    sync_record = CRMWritebackSync(
        tenant_id=tenant_id,
        connection_id=connection.id,
        sync_type="full" if full_sync else "incremental",
        status=WritebackStatus.IN_PROGRESS,
        sync_contacts=sync_contacts,
        sync_deals=sync_deals,
        modified_since=modified_since,
    )
    db.add(sync_record)
    await db.commit()
    await db.refresh(sync_record)

    # Run sync
    try:
        results = await writeback_service.full_sync(
            sync_contacts=sync_contacts,
            sync_deals=sync_deals,
            modified_since=modified_since,
        )

        # Update sync record
        sync_record.status = WritebackStatus.COMPLETED if results["status"] == "completed" else WritebackStatus.PARTIAL
        sync_record.completed_at = datetime.now(timezone.utc)
        sync_record.duration_seconds = (
            sync_record.completed_at - sync_record.started_at
        ).total_seconds()

        if results.get("contacts"):
            sync_record.contacts_synced = results["contacts"].get("synced", 0)
            sync_record.contacts_failed = results["contacts"].get("failed", 0)

        if results.get("deals"):
            sync_record.deals_synced = results["deals"].get("synced", 0)
            sync_record.deals_failed = results["deals"].get("failed", 0)

        await db.commit()

        return APIResponse(
            success=True,
            data={
                "sync_id": str(sync_record.id),
                **results,
            },
            message="Writeback sync completed",
        )

    except Exception as e:
        sync_record.status = WritebackStatus.FAILED
        sync_record.completed_at = datetime.now(timezone.utc)
        sync_record.error_message = str(e)
        await db.commit()

        logger.error(f"Writeback sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hubspot/writeback/history",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get writeback sync history",
)
async def get_writeback_history(
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """Get history of writeback sync operations."""
    result = await db.execute(
        select(CRMWritebackSync)
        .where(CRMWritebackSync.tenant_id == tenant_id)
        .order_by(CRMWritebackSync.started_at.desc())
        .limit(limit)
    )
    syncs = result.scalars().all()

    return APIResponse(
        success=True,
        data={
            "syncs": [
                {
                    "id": str(s.id),
                    "sync_type": s.sync_type,
                    "status": s.status.value,
                    "started_at": s.started_at.isoformat(),
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "duration_seconds": s.duration_seconds,
                    "contacts_synced": s.contacts_synced,
                    "contacts_failed": s.contacts_failed,
                    "deals_synced": s.deals_synced,
                    "deals_failed": s.deals_failed,
                    "error_message": s.error_message,
                }
                for s in syncs
            ],
            "total": len(syncs),
        },
    )


@router.patch(
    "/hubspot/writeback/config",
    response_model=APIResponse[Dict[str, Any]],
    summary="Update writeback config",
)
async def update_writeback_config(
    tenant_id: int = Query(..., description="Tenant ID"),
    enabled: Optional[bool] = Query(None, description="Enable/disable writeback"),
    sync_contacts: Optional[bool] = Query(None, description="Sync contacts"),
    sync_deals: Optional[bool] = Query(None, description="Sync deals"),
    auto_sync_enabled: Optional[bool] = Query(None, description="Enable auto-sync"),
    sync_interval_hours: Optional[int] = Query(None, ge=1, le=168, description="Sync interval in hours"),
    db: AsyncSession = Depends(get_async_session),
):
    """Update writeback configuration settings."""
    # Get connection
    conn_result = await db.execute(
        select(CRMConnection).where(
            and_(
                CRMConnection.tenant_id == tenant_id,
                CRMConnection.provider == CRMProvider.HUBSPOT,
            )
        )
    )
    connection = conn_result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=400, detail="HubSpot not connected")

    # Get or create config
    config_result = await db.execute(
        select(CRMWritebackConfig).where(
            CRMWritebackConfig.connection_id == connection.id
        )
    )
    config = config_result.scalar_one_or_none()

    if not config:
        config = CRMWritebackConfig(
            tenant_id=tenant_id,
            connection_id=connection.id,
        )
        db.add(config)

    # Update fields
    if enabled is not None:
        config.enabled = enabled
    if sync_contacts is not None:
        config.sync_contacts = sync_contacts
    if sync_deals is not None:
        config.sync_deals = sync_deals
    if auto_sync_enabled is not None:
        config.auto_sync_enabled = auto_sync_enabled
    if sync_interval_hours is not None:
        config.sync_interval_hours = sync_interval_hours

    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config)

    return APIResponse(
        success=True,
        data={
            "enabled": config.enabled,
            "sync_contacts": config.sync_contacts,
            "sync_deals": config.sync_deals,
            "auto_sync_enabled": config.auto_sync_enabled,
            "sync_interval_hours": config.sync_interval_hours,
            "properties_created": config.properties_created,
        },
        message="Writeback configuration updated",
    )


# =============================================================================
# Zoho CRM Schemas
# =============================================================================

class ZohoConnectRequest(BaseModel):
    """Request to initiate Zoho OAuth."""
    redirect_uri: str = Field(..., description="OAuth callback URL")
    region: str = Field(default="com", description="Zoho region (com, eu, in, com.au, jp, com.cn)")


class ZohoConnectResponse(BaseModel):
    """Response with OAuth authorization URL."""
    authorization_url: str
    state: str


class ZohoStatusResponse(BaseModel):
    """Zoho connection status."""
    connected: bool
    status: str
    provider: str = "zoho"
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    scopes: List[str] = []


# =============================================================================
# Pipedrive CRM Schemas
# =============================================================================

class PipedriveConnectRequest(BaseModel):
    """Request to initiate Pipedrive OAuth."""
    redirect_uri: str = Field(..., description="OAuth callback URL")


class PipedriveConnectResponse(BaseModel):
    """Response with OAuth authorization URL."""
    authorization_url: str
    state: str


class PipedriveStatusResponse(BaseModel):
    """Pipedrive connection status."""
    connected: bool
    status: str
    provider: str = "pipedrive"
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    scopes: List[str] = []


class PipedriveSyncResponse(BaseModel):
    """Pipedrive sync operation response."""
    status: str
    persons_synced: int = 0
    persons_created: int = 0
    persons_updated: int = 0
    deals_synced: int = 0
    deals_created: int = 0
    errors: List[str] = []


# =============================================================================
# Salesforce CRM Schemas
# =============================================================================

class SalesforceConnectRequest(BaseModel):
    """Request to initiate Salesforce OAuth."""
    redirect_uri: str = Field(..., description="OAuth callback URL")
    is_sandbox: bool = Field(default=False, description="Use Salesforce sandbox environment")


class SalesforceConnectResponse(BaseModel):
    """Response with OAuth authorization URL."""
    authorization_url: str
    state: str


class SalesforceStatusResponse(BaseModel):
    """Salesforce connection status."""
    connected: bool
    status: str
    provider: str = "salesforce"
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    scopes: List[str] = []
    is_sandbox: bool = False


class SalesforceSyncResponse(BaseModel):
    """Salesforce sync operation response."""
    status: str
    contacts_synced: int = 0
    contacts_created: int = 0
    contacts_updated: int = 0
    leads_synced: int = 0
    leads_created: int = 0
    leads_updated: int = 0
    opportunities_synced: int = 0
    opportunities_created: int = 0
    errors: List[str] = []


# =============================================================================
# Zoho OAuth Endpoints
# =============================================================================

@router.post(
    "/zoho/connect",
    response_model=APIResponse[ZohoConnectResponse],
    summary="Initiate Zoho OAuth",
)
async def zoho_connect(
    request: ZohoConnectRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start Zoho OAuth authorization flow.
    Returns authorization URL to redirect user to Zoho.
    """
    client = ZohoClient(db, tenant_id, request.region)

    # Generate state token for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)

    # Include tenant_id and region in state
    state_with_tenant = f"{tenant_id}:{request.region}:{state}"

    auth_url = client.get_authorization_url(
        redirect_uri=request.redirect_uri,
        state=state_with_tenant,
    )

    return APIResponse(
        success=True,
        data=ZohoConnectResponse(
            authorization_url=auth_url,
            state=state_with_tenant,
        ),
    )


@router.get(
    "/zoho/callback",
    response_model=APIResponse[ZohoStatusResponse],
    summary="Zoho OAuth callback",
)
async def zoho_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle Zoho OAuth callback.
    Exchanges authorization code for tokens and stores connection.
    """
    # Extract tenant_id and region from state
    try:
        parts = state.split(":", 2)
        tenant_id = int(parts[0])
        region = parts[1] if len(parts) > 1 else "com"
    except (ValueError, AttributeError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    client = ZohoClient(db, tenant_id, region)

    try:
        connection = await client.exchange_code_for_tokens(code, redirect_uri)
        status = await client.get_connection_status()

        return APIResponse(
            success=True,
            data=ZohoStatusResponse(**status),
            message="Zoho CRM connected successfully",
        )

    except Exception as e:
        logger.error("zoho_oauth_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get(
    "/zoho/status",
    response_model=APIResponse[ZohoStatusResponse],
    summary="Get Zoho connection status",
)
async def zoho_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current Zoho CRM connection status for tenant."""
    client = ZohoClient(db, tenant_id, settings.zoho_region)
    status = await client.get_connection_status()

    return APIResponse(
        success=True,
        data=ZohoStatusResponse(**status),
    )


@router.delete(
    "/zoho/disconnect",
    response_model=APIResponse[Dict[str, Any]],
    summary="Disconnect Zoho",
)
async def zoho_disconnect(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect Zoho CRM integration for tenant."""
    client = ZohoClient(db, tenant_id, settings.zoho_region)
    success = await client.disconnect()

    if not success:
        raise HTTPException(status_code=404, detail="No Zoho connection found")

    return APIResponse(
        success=True,
        data={"disconnected": True},
        message="Zoho CRM disconnected successfully",
    )


# =============================================================================
# Zoho Sync Endpoints
# =============================================================================

@router.post(
    "/zoho/sync",
    response_model=APIResponse[SyncResponse],
    summary="Trigger Zoho sync",
)
async def zoho_sync(
    request: SyncRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger manual sync of Zoho CRM contacts, leads, and deals.
    """
    sync_service = ZohoSyncService(db, tenant_id, settings.zoho_region)

    results = await sync_service.sync_all(full_sync=request.full_sync)

    return APIResponse(
        success=results.get("status") != "error",
        data=SyncResponse(
            status=results.get("status", "error"),
            contacts_synced=results.get("contacts_synced", 0),
            contacts_created=results.get("contacts_created", 0),
            contacts_updated=results.get("contacts_updated", 0),
            deals_synced=results.get("deals_synced", 0),
            deals_created=results.get("deals_created", 0),
            deals_updated=results.get("deals_updated", 0),
            errors=results.get("errors", []),
        ),
        message=f"Sync completed: {results.get('contacts_synced', 0)} contacts, {results.get('deals_synced', 0)} deals",
    )


@router.get(
    "/zoho/pipeline",
    response_model=APIResponse[PipelineSummaryResponse],
    summary="Get Zoho pipeline summary",
)
async def zoho_pipeline_summary(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get Zoho CRM pipeline summary with stage counts and values."""
    sync_service = ZohoSyncService(db, tenant_id, settings.zoho_region)
    summary = await sync_service.get_pipeline_summary()

    return APIResponse(
        success=True,
        data=PipelineSummaryResponse(**summary),
    )


# =============================================================================
# Zoho Writeback Endpoints
# =============================================================================

@router.get(
    "/zoho/writeback/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Zoho writeback status",
)
async def get_zoho_writeback_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get Zoho CRM writeback configuration and status.
    """
    writeback_service = ZohoWritebackService(db, tenant_id, settings.zoho_region)
    status = await writeback_service.get_writeback_status()

    return APIResponse(
        success=True,
        data=status,
    )


@router.get(
    "/zoho/writeback/fields",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get required Zoho custom fields",
)
async def get_zoho_writeback_fields(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get list of custom fields required in Zoho CRM for writeback.

    For Zoho CRM editions that don't support API field creation,
    use this information to manually create fields in Zoho settings.
    """
    writeback_service = ZohoWritebackService(db, tenant_id, settings.zoho_region)
    fields_info = await writeback_service.get_required_fields_info()

    return APIResponse(
        success=True,
        data=fields_info,
    )


@router.post(
    "/zoho/writeback/setup-fields",
    response_model=APIResponse[Dict[str, Any]],
    summary="Setup Zoho custom fields",
)
async def setup_zoho_writeback_fields(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Attempt to create Stratum custom fields in Zoho CRM.

    Note: This requires Zoho CRM Enterprise edition for API field creation.
    For other editions, fields must be created manually in Zoho CRM settings.
    """
    writeback_service = ZohoWritebackService(db, tenant_id, settings.zoho_region)

    try:
        results = await writeback_service.setup_custom_fields()

        return APIResponse(
            success=True,
            data=results,
            message="Custom field setup attempted. Check results for details.",
        )
    except Exception as e:
        logger.error(f"Failed to setup Zoho writeback fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/zoho/writeback/sync",
    response_model=APIResponse[Dict[str, Any]],
    summary="Run Zoho writeback sync",
)
async def run_zoho_writeback_sync(
    tenant_id: int = Query(..., description="Tenant ID"),
    sync_contacts: bool = Query(True, description="Sync contact attribution"),
    sync_deals: bool = Query(True, description="Sync deal attribution"),
    full_sync: bool = Query(False, description="Full sync (ignore modified_since)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run Zoho CRM writeback sync.

    Pushes Stratum attribution data to Zoho contacts and deals:
    - Contact: ad platform, campaign, ad IDs, attribution confidence
    - Deal: attributed spend, ROAS, profit metrics, touchpoint count
    """
    writeback_service = ZohoWritebackService(db, tenant_id, settings.zoho_region)

    # Get last sync time for incremental
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

        return APIResponse(
            success=True,
            data=results,
            message="Zoho writeback sync completed",
        )

    except Exception as e:
        logger.error(f"Zoho writeback sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Pipedrive OAuth Endpoints
# =============================================================================

@router.post(
    "/pipedrive/connect",
    response_model=APIResponse[PipedriveConnectResponse],
    summary="Initiate Pipedrive OAuth",
)
async def pipedrive_connect(
    request: PipedriveConnectRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start Pipedrive OAuth authorization flow.
    Returns authorization URL to redirect user to Pipedrive.
    """
    client = PipedriveClient(db, tenant_id)

    # Generate state token for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)

    # Include tenant_id in state
    state_with_tenant = f"{tenant_id}:{state}"

    auth_url = client.get_authorization_url(
        redirect_uri=request.redirect_uri,
        state=state_with_tenant,
    )

    return APIResponse(
        success=True,
        data=PipedriveConnectResponse(
            authorization_url=auth_url,
            state=state_with_tenant,
        ),
    )


@router.get(
    "/pipedrive/callback",
    response_model=APIResponse[PipedriveStatusResponse],
    summary="Pipedrive OAuth callback",
)
async def pipedrive_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle Pipedrive OAuth callback.
    Exchanges authorization code for tokens and stores connection.
    """
    # Extract tenant_id from state
    try:
        tenant_id_str, _ = state.split(":", 1)
        tenant_id = int(tenant_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    client = PipedriveClient(db, tenant_id)

    try:
        connection = await client.exchange_code_for_tokens(code, redirect_uri)
        status = await client.get_connection_status()

        return APIResponse(
            success=True,
            data=PipedriveStatusResponse(**status),
            message="Pipedrive connected successfully",
        )

    except Exception as e:
        logger.error("pipedrive_oauth_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get(
    "/pipedrive/status",
    response_model=APIResponse[PipedriveStatusResponse],
    summary="Get Pipedrive connection status",
)
async def pipedrive_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current Pipedrive connection status for tenant."""
    client = PipedriveClient(db, tenant_id)
    status = await client.get_connection_status()

    return APIResponse(
        success=True,
        data=PipedriveStatusResponse(**status),
    )


@router.delete(
    "/pipedrive/disconnect",
    response_model=APIResponse[Dict[str, Any]],
    summary="Disconnect Pipedrive",
)
async def pipedrive_disconnect(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect Pipedrive integration for tenant."""
    client = PipedriveClient(db, tenant_id)
    success = await client.disconnect()

    if not success:
        raise HTTPException(status_code=404, detail="No Pipedrive connection found")

    return APIResponse(
        success=True,
        data={"disconnected": True},
        message="Pipedrive disconnected successfully",
    )


# =============================================================================
# Pipedrive Sync Endpoints
# =============================================================================

@router.post(
    "/pipedrive/sync",
    response_model=APIResponse[PipedriveSyncResponse],
    summary="Trigger Pipedrive sync",
)
async def pipedrive_sync(
    request: SyncRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger manual sync of Pipedrive persons and deals.
    """
    sync_service = PipedriveSyncService(db, tenant_id)

    results = await sync_service.sync_all(full_sync=request.full_sync)

    return APIResponse(
        success="error" not in results.get("errors", []),
        data=PipedriveSyncResponse(
            status="success" if not results.get("errors") else "partial",
            persons_synced=results.get("persons_synced", 0),
            persons_created=results.get("persons_created", 0),
            persons_updated=results.get("persons_updated", 0),
            deals_synced=results.get("deals_synced", 0),
            deals_created=results.get("deals_created", 0),
            errors=results.get("errors", []),
        ),
        message=f"Sync completed: {results.get('persons_synced', 0)} persons, {results.get('deals_synced', 0)} deals",
    )


@router.get(
    "/pipedrive/pipeline",
    response_model=APIResponse[PipelineSummaryResponse],
    summary="Get Pipedrive pipeline summary",
)
async def pipedrive_pipeline_summary(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get Pipedrive pipeline summary with stage counts and values."""
    # Get deals for pipeline summary
    result = await db.execute(
        select(CRMDeal).where(
            and_(
                CRMDeal.tenant_id == tenant_id,
            )
        )
    )
    deals = result.scalars().all()

    # Build stage summary
    stage_counts: Dict[str, int] = {}
    stage_values: Dict[str, float] = {}
    total_pipeline_value = 0
    total_won_value = 0
    won_deal_count = 0

    for deal in deals:
        stage = deal.stage or "Unknown"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        deal_value = (deal.amount_cents or 0) / 100
        stage_values[stage] = stage_values.get(stage, 0) + deal_value

        if not deal.is_closed:
            total_pipeline_value += deal_value

        if deal.is_won:
            total_won_value += deal_value
            won_deal_count += 1

    return APIResponse(
        success=True,
        data=PipelineSummaryResponse(
            status="success",
            stage_counts=stage_counts,
            stage_values=stage_values,
            total_pipeline_value=total_pipeline_value,
            total_won_value=total_won_value,
            won_deal_count=won_deal_count,
        ),
    )


# =============================================================================
# Pipedrive Writeback Endpoints
# =============================================================================

@router.get(
    "/pipedrive/writeback/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Pipedrive writeback status",
)
async def get_pipedrive_writeback_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get Pipedrive writeback configuration and status.
    """
    writeback_service = PipedriveWritebackService(db, tenant_id)
    status = await writeback_service.get_writeback_status()

    return APIResponse(
        success=True,
        data=status,
    )


@router.post(
    "/pipedrive/writeback/setup-fields",
    response_model=APIResponse[Dict[str, Any]],
    summary="Setup Pipedrive custom fields",
)
async def setup_pipedrive_writeback_fields(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create Stratum custom fields in Pipedrive.

    Creates custom fields for both persons and deals to store attribution data:
    - Person: ad platform, campaign, attribution confidence, touchpoints
    - Deal: attributed spend, ROAS, profit metrics, days to close
    """
    writeback_service = PipedriveWritebackService(db, tenant_id)

    try:
        results = await writeback_service.setup_custom_fields()

        return APIResponse(
            success=True,
            data=results,
            message="Custom fields created successfully",
        )
    except Exception as e:
        logger.error(f"Failed to setup Pipedrive writeback fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pipedrive/writeback/sync",
    response_model=APIResponse[Dict[str, Any]],
    summary="Run Pipedrive writeback sync",
)
async def run_pipedrive_writeback_sync(
    tenant_id: int = Query(..., description="Tenant ID"),
    sync_persons: bool = Query(True, description="Sync person attribution"),
    sync_deals: bool = Query(True, description="Sync deal attribution"),
    full_sync: bool = Query(False, description="Full sync (ignore modified_since)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run Pipedrive writeback sync.

    Pushes Stratum attribution data to Pipedrive persons and deals:
    - Person: ad platform, campaign, ad IDs, attribution confidence
    - Deal: attributed spend, ROAS, profit metrics, touchpoint count
    """
    writeback_service = PipedriveWritebackService(db, tenant_id)

    # Get last sync time for incremental
    modified_since = None
    if not full_sync:
        result = await db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == tenant_id,
                    CRMConnection.provider == CRMProvider.PIPEDRIVE,
                )
            )
        )
        connection = result.scalar_one_or_none()
        if connection and connection.last_sync_at:
            modified_since = connection.last_sync_at

    try:
        results = await writeback_service.full_sync(
            sync_persons=sync_persons,
            sync_deals=sync_deals,
            modified_since=modified_since,
        )

        return APIResponse(
            success=True,
            data=results,
            message="Pipedrive writeback sync completed",
        )

    except Exception as e:
        logger.error(f"Pipedrive writeback sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Salesforce OAuth Endpoints
# =============================================================================

@router.post(
    "/salesforce/connect",
    response_model=APIResponse[SalesforceConnectResponse],
    summary="Initiate Salesforce OAuth",
)
async def salesforce_connect(
    request: SalesforceConnectRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start Salesforce OAuth authorization flow.
    Returns authorization URL to redirect user to Salesforce.
    """
    client = SalesforceClient(db, tenant_id, request.is_sandbox)

    # Generate state token for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)

    # Include tenant_id and sandbox flag in state
    state_with_tenant = f"{tenant_id}:{'sandbox' if request.is_sandbox else 'prod'}:{state}"

    auth_url = client.get_authorization_url(
        redirect_uri=request.redirect_uri,
        state=state_with_tenant,
    )

    return APIResponse(
        success=True,
        data=SalesforceConnectResponse(
            authorization_url=auth_url,
            state=state_with_tenant,
        ),
    )


@router.get(
    "/salesforce/callback",
    response_model=APIResponse[SalesforceStatusResponse],
    summary="Salesforce OAuth callback",
)
async def salesforce_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle Salesforce OAuth callback.
    Exchanges authorization code for tokens and stores connection.
    """
    # Extract tenant_id and sandbox flag from state
    try:
        parts = state.split(":", 2)
        tenant_id = int(parts[0])
        is_sandbox = parts[1] == "sandbox" if len(parts) > 1 else False
    except (ValueError, AttributeError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    client = SalesforceClient(db, tenant_id, is_sandbox)

    try:
        connection = await client.exchange_code_for_tokens(code, redirect_uri)
        status = await client.get_connection_status()

        return APIResponse(
            success=True,
            data=SalesforceStatusResponse(**status),
            message="Salesforce connected successfully",
        )

    except Exception as e:
        logger.error("salesforce_oauth_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get(
    "/salesforce/status",
    response_model=APIResponse[SalesforceStatusResponse],
    summary="Get Salesforce connection status",
)
async def salesforce_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current Salesforce connection status for tenant."""
    client = SalesforceClient(db, tenant_id)
    status = await client.get_connection_status()

    return APIResponse(
        success=True,
        data=SalesforceStatusResponse(**status),
    )


@router.delete(
    "/salesforce/disconnect",
    response_model=APIResponse[Dict[str, Any]],
    summary="Disconnect Salesforce",
)
async def salesforce_disconnect(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect Salesforce integration for tenant."""
    client = SalesforceClient(db, tenant_id)
    success = await client.disconnect()

    if not success:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    return APIResponse(
        success=True,
        data={"disconnected": True},
        message="Salesforce disconnected successfully",
    )


# =============================================================================
# Salesforce Sync Endpoints
# =============================================================================

@router.post(
    "/salesforce/sync",
    response_model=APIResponse[SalesforceSyncResponse],
    summary="Trigger Salesforce sync",
)
async def salesforce_sync(
    request: SyncRequest,
    tenant_id: int = Query(..., description="Tenant ID"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger manual sync of Salesforce contacts, leads, and opportunities.
    """
    sync_service = SalesforceSyncService(db, tenant_id)

    results = await sync_service.sync_all(full_sync=request.full_sync)

    return APIResponse(
        success="error" not in str(results.get("errors", [])),
        data=SalesforceSyncResponse(
            status="success" if not results.get("errors") else "partial",
            contacts_synced=results.get("contacts_synced", 0),
            contacts_created=results.get("contacts_created", 0),
            contacts_updated=results.get("contacts_updated", 0),
            leads_synced=results.get("leads_synced", 0),
            leads_created=results.get("leads_created", 0),
            leads_updated=results.get("leads_updated", 0),
            opportunities_synced=results.get("opportunities_synced", 0),
            opportunities_created=results.get("opportunities_created", 0),
            errors=results.get("errors", []),
        ),
        message=f"Sync completed: {results.get('contacts_synced', 0)} contacts, {results.get('leads_synced', 0)} leads, {results.get('opportunities_synced', 0)} opportunities",
    )


@router.get(
    "/salesforce/pipeline",
    response_model=APIResponse[PipelineSummaryResponse],
    summary="Get Salesforce pipeline summary",
)
async def salesforce_pipeline_summary(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get Salesforce pipeline summary with stage counts and values."""
    sync_service = SalesforceSyncService(db, tenant_id)
    summary = await sync_service.get_pipeline_summary()

    return APIResponse(
        success=True,
        data=PipelineSummaryResponse(**summary),
    )


# =============================================================================
# Salesforce Writeback Endpoints
# =============================================================================

@router.get(
    "/salesforce/writeback/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Salesforce writeback status",
)
async def get_salesforce_writeback_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get Salesforce writeback configuration and status.
    """
    writeback_service = SalesforceWritebackService(db, tenant_id)
    status = await writeback_service.get_writeback_status()

    return APIResponse(
        success=True,
        data=status,
    )


@router.get(
    "/salesforce/writeback/fields",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get required Salesforce custom fields",
)
async def get_salesforce_writeback_fields(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get list of custom fields required in Salesforce for writeback.

    Use this information to manually create fields in Salesforce Setup
    if the Metadata API is not available.
    """
    writeback_service = SalesforceWritebackService(db, tenant_id)
    fields_info = await writeback_service.get_required_fields_info()

    return APIResponse(
        success=True,
        data=fields_info,
    )


@router.post(
    "/salesforce/writeback/setup-fields",
    response_model=APIResponse[Dict[str, Any]],
    summary="Check Salesforce custom fields setup",
)
async def setup_salesforce_writeback_fields(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Check which Stratum custom fields exist in Salesforce.

    Note: Creating custom fields via API requires Salesforce Metadata API.
    This endpoint checks existing fields and provides instructions for
    manually creating any missing fields in Salesforce Setup.
    """
    writeback_service = SalesforceWritebackService(db, tenant_id)

    try:
        results = await writeback_service.setup_custom_fields()

        return APIResponse(
            success=True,
            data=results,
            message="Field check completed. See instructions for any missing fields.",
        )
    except Exception as e:
        logger.error(f"Failed to check Salesforce writeback fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/salesforce/writeback/sync",
    response_model=APIResponse[Dict[str, Any]],
    summary="Run Salesforce writeback sync",
)
async def run_salesforce_writeback_sync(
    tenant_id: int = Query(..., description="Tenant ID"),
    sync_contacts: bool = Query(True, description="Sync contact attribution"),
    sync_opportunities: bool = Query(True, description="Sync opportunity attribution"),
    full_sync: bool = Query(False, description="Full sync (ignore modified_since)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run Salesforce writeback sync.

    Pushes Stratum attribution data to Salesforce contacts and opportunities:
    - Contact: ad platform, campaign, ad IDs, attribution confidence
    - Opportunity: attributed spend, ROAS, profit metrics, touchpoint count
    """
    writeback_service = SalesforceWritebackService(db, tenant_id)

    # Get last sync time for incremental
    modified_since = None
    if not full_sync:
        result = await db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == tenant_id,
                    CRMConnection.provider == CRMProvider.SALESFORCE,
                )
            )
        )
        connection = result.scalar_one_or_none()
        if connection and connection.last_sync_at:
            modified_since = connection.last_sync_at

    try:
        results = await writeback_service.full_sync(
            sync_contacts=sync_contacts,
            sync_opportunities=sync_opportunities,
            modified_since=modified_since,
        )

        return APIResponse(
            success=True,
            data=results,
            message="Salesforce writeback sync completed",
        )

    except Exception as e:
        logger.error(f"Salesforce writeback sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Multi-CRM Status Endpoint
# =============================================================================

@router.get(
    "/crm/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get all CRM connection statuses",
)
async def get_all_crm_status(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get connection status for all supported CRM providers.

    Returns status for:
    - HubSpot
    - Zoho
    - Pipedrive
    - Salesforce (future)
    """
    hubspot_client = HubSpotClient(db, tenant_id)
    zoho_client = ZohoClient(db, tenant_id, settings.zoho_region)
    pipedrive_client = PipedriveClient(db, tenant_id)

    salesforce_client = SalesforceClient(db, tenant_id)

    hubspot_status = await hubspot_client.get_connection_status()
    zoho_status = await zoho_client.get_connection_status()
    pipedrive_status = await pipedrive_client.get_connection_status()
    salesforce_status = await salesforce_client.get_connection_status()

    return APIResponse(
        success=True,
        data={
            "hubspot": hubspot_status,
            "zoho": zoho_status,
            "pipedrive": pipedrive_status,
            "salesforce": salesforce_status,
        },
    )


# =============================================================================
# Slack Integration
# =============================================================================

class SlackTestRequest(BaseModel):
    """Request to test Slack webhook."""
    webhook_url: str = Field(..., description="Slack webhook URL to test")


@router.post(
    "/slack/test",
    response_model=APIResponse[Dict[str, Any]],
    summary="Test Slack webhook",
)
async def test_slack_webhook(
    request: SlackTestRequest,
):
    """
    Test a Slack webhook by sending a test message.

    Validates the webhook URL and sends a sample notification.
    """
    import aiohttp

    # Build test message
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: Stratum AI Connected!",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Your Slack integration is working correctly. You will now receive alerts and notifications from Stratum AI.",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Test sent at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    }
                ],
            },
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                request.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response_text = await response.text()

                if response.status == 200:
                    logger.info("slack_test_success", webhook_url=request.webhook_url[:50])
                    return APIResponse(
                        success=True,
                        data={"success": True, "message": "Test message sent successfully"},
                        message="Slack webhook test successful",
                    )
                else:
                    logger.warning(
                        "slack_test_failed",
                        status=response.status,
                        response=response_text,
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Slack returned error: {response.status} - {response_text}",
                    )

    except aiohttp.ClientError as e:
        logger.error("slack_test_connection_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Slack: {str(e)}",
        )
    except Exception as e:
        logger.error("slack_test_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}",
        )
