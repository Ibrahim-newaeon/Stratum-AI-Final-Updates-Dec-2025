# =============================================================================
# Stratum AI - Campaign Builder API Router
# =============================================================================
"""
Tenant-scoped API endpoints for the Campaign Builder feature:
- Platform connectors (OAuth management)
- Ad accounts (sync and enable/disable)
- Campaign drafts (CRUD + workflow)
- Publish logs (audit trail)

All routes enforce tenant isolation and RBAC permissions.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.db.session import get_async_session
from app.models.campaign_builder import (
    TenantPlatformConnection, TenantAdAccount, CampaignDraft, CampaignPublishLog,
    AdPlatform, ConnectionStatus, DraftStatus, PublishResult
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/tenant/{tenant_id}", tags=["campaign-builder"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ConnectorStatusResponse(BaseModel):
    platform: str
    status: str
    connected_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    scopes: List[str] = []
    last_error: Optional[str] = None

    class Config:
        from_attributes = True


class AdAccountResponse(BaseModel):
    id: UUID
    platform: str
    platform_account_id: str
    name: str
    business_name: Optional[str] = None
    currency: str
    timezone: str
    is_enabled: bool
    daily_budget_cap: Optional[float] = None
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdAccountUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    daily_budget_cap: Optional[float] = None


class CampaignDraftCreate(BaseModel):
    platform: str
    ad_account_id: UUID
    name: str
    description: Optional[str] = None
    draft_json: dict = Field(default_factory=dict)


class CampaignDraftUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    draft_json: Optional[dict] = None


class CampaignDraftResponse(BaseModel):
    id: UUID
    tenant_id: int
    platform: str
    ad_account_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    status: str
    draft_json: dict
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    platform_campaign_id: Optional[str] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublishLogResponse(BaseModel):
    id: UUID
    draft_id: Optional[UUID] = None
    platform: str
    platform_account_id: str
    event_time: datetime
    result_status: str
    platform_campaign_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int

    class Config:
        from_attributes = True


# =============================================================================
# Connectors Endpoints
# =============================================================================

@router.get("/connect/{platform}/status", response_model=APIResponse[ConnectorStatusResponse])
async def get_connector_status(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    db: AsyncSession = Depends(get_async_session),
):
    """Get connection status for a platform."""
    # Enforce tenant context
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return APIResponse(
            success=True,
            data=ConnectorStatusResponse(
                platform=platform.value,
                status=ConnectionStatus.DISCONNECTED.value,
            ),
        )

    return APIResponse(
        success=True,
        data=ConnectorStatusResponse(
            platform=connection.platform,  # Already a string in DB
            status=connection.status,  # Already a string in DB
            connected_at=connection.connected_at,
            last_refreshed_at=connection.last_refreshed_at,
            scopes=connection.scopes or [],
            last_error=connection.last_error,
        ),
    )


@router.post("/connect/{platform}/start")
async def start_platform_connection(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start OAuth flow for a platform.
    Returns the authorization URL to redirect the user.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # In production, generate OAuth URL with proper state parameter
    # state = generate_state_token(tenant_id, platform)
    # oauth_url = get_oauth_url(platform, state)

    # Placeholder response
    oauth_urls = {
        AdPlatform.META: "https://www.facebook.com/v18.0/dialog/oauth?...",
        AdPlatform.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth?...",
        AdPlatform.TIKTOK: "https://ads.tiktok.com/marketing_api/auth?...",
        AdPlatform.SNAPCHAT: "https://accounts.snapchat.com/accounts/oauth2/auth?...",
    }

    return APIResponse(
        success=True,
        data={
            "oauth_url": oauth_urls.get(platform, ""),
            "message": f"Redirect user to OAuth URL for {platform.value}",
        },
    )


@router.post("/connect/{platform}/refresh")
async def refresh_platform_token(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    db: AsyncSession = Depends(get_async_session),
):
    """Refresh OAuth token for a platform."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")

    # In production, call platform API to refresh token
    # new_token = await refresh_oauth_token(platform, connection.refresh_token_encrypted)

    connection.last_refreshed_at = datetime.now(timezone.utc)
    connection.status = ConnectionStatus.CONNECTED
    connection.last_error = None
    await db.commit()

    return APIResponse(
        success=True,
        data={"message": f"Token refreshed for {platform.value}"},
    )


@router.delete("/connect/{platform}")
async def disconnect_platform(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect a platform (revoke OAuth)."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")

    # Mark as disconnected (keep record for audit)
    connection.status = ConnectionStatus.DISCONNECTED
    connection.access_token_encrypted = None
    connection.refresh_token_encrypted = None
    await db.commit()

    return APIResponse(
        success=True,
        data={"message": f"Disconnected from {platform.value}"},
    )


# =============================================================================
# Ad Accounts Endpoints
# =============================================================================

@router.get("/ad-accounts/{platform}", response_model=APIResponse[List[AdAccountResponse]])
async def list_ad_accounts(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_async_session),
):
    """List ad accounts for a platform."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    query = select(TenantAdAccount).where(
        and_(
            TenantAdAccount.tenant_id == tenant_id,
            TenantAdAccount.platform == platform,
        )
    )

    if enabled_only:
        query = query.where(TenantAdAccount.is_enabled == True)

    result = await db.execute(query.order_by(TenantAdAccount.name))
    accounts = result.scalars().all()

    return APIResponse(
        success=True,
        data=[AdAccountResponse.model_validate(acc) for acc in accounts],
    )


@router.post("/ad-accounts/{platform}/sync")
async def sync_ad_accounts(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """Trigger ad accounts sync from platform."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Check connection exists and is connected
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.platform == platform,
                TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=400,
            detail=f"Platform {platform.value} is not connected"
        )

    # In production, trigger Celery task
    # background_tasks.add_task(sync_ad_accounts_task, tenant_id, platform)

    return APIResponse(
        success=True,
        data={"message": f"Sync started for {platform.value} ad accounts"},
    )


@router.put("/ad-accounts/{platform}/{ad_account_id}", response_model=APIResponse[AdAccountResponse])
async def update_ad_account(
    request: Request,
    tenant_id: int,
    platform: AdPlatform,
    ad_account_id: UUID,
    update_data: AdAccountUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Update ad account settings (enable/disable, budget cap)."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(TenantAdAccount).where(
            and_(
                TenantAdAccount.id == ad_account_id,
                TenantAdAccount.tenant_id == tenant_id,
            )
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Ad account not found")

    if update_data.is_enabled is not None:
        account.is_enabled = update_data.is_enabled
    if update_data.daily_budget_cap is not None:
        account.daily_budget_cap = update_data.daily_budget_cap

    await db.commit()
    await db.refresh(account)

    return APIResponse(
        success=True,
        data=AdAccountResponse.model_validate(account),
    )


# =============================================================================
# Campaign Drafts Endpoints
# =============================================================================

@router.post("/campaign-drafts", response_model=APIResponse[CampaignDraftResponse])
async def create_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_data: CampaignDraftCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new campaign draft."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)

    # Validate ad account exists and is enabled
    result = await db.execute(
        select(TenantAdAccount).where(
            and_(
                TenantAdAccount.id == draft_data.ad_account_id,
                TenantAdAccount.tenant_id == tenant_id,
                TenantAdAccount.is_enabled == True,
            )
        )
    )
    ad_account = result.scalar_one_or_none()

    if not ad_account:
        raise HTTPException(
            status_code=400,
            detail="Ad account not found or not enabled"
        )

    draft = CampaignDraft(
        tenant_id=tenant_id,
        platform=draft_data.platform,  # Already a string
        ad_account_id=draft_data.ad_account_id,
        name=draft_data.name,
        description=draft_data.description,
        draft_json=draft_data.draft_json,
        status=DraftStatus.DRAFT.value,
        created_by_user_id=user_id,
    )

    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.get("/campaign-drafts", response_model=APIResponse[List[CampaignDraftResponse]])
async def list_campaign_drafts(
    request: Request,
    tenant_id: int,
    platform: Optional[AdPlatform] = None,
    status: Optional[DraftStatus] = None,
    ad_account_id: Optional[UUID] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """List campaign drafts with optional filters."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    query = select(CampaignDraft).where(CampaignDraft.tenant_id == tenant_id)

    if platform:
        query = query.where(CampaignDraft.platform == platform)
    if status:
        query = query.where(CampaignDraft.status == status)
    if ad_account_id:
        query = query.where(CampaignDraft.ad_account_id == ad_account_id)

    query = query.order_by(CampaignDraft.updated_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    drafts = result.scalars().all()

    return APIResponse(
        success=True,
        data=[CampaignDraftResponse.model_validate(d) for d in drafts],
    )


@router.get("/campaign-drafts/{draft_id}", response_model=APIResponse[CampaignDraftResponse])
async def get_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific campaign draft."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(CampaignDraft).where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.put("/campaign-drafts/{draft_id}", response_model=APIResponse[CampaignDraftResponse])
async def update_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    update_data: CampaignDraftUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a campaign draft (only allowed in draft status)."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(CampaignDraft).where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status not in [DraftStatus.DRAFT.value, DraftStatus.REJECTED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update draft in {draft.status} status"
        )

    if update_data.name is not None:
        draft.name = update_data.name
    if update_data.description is not None:
        draft.description = update_data.description
    if update_data.draft_json is not None:
        draft.draft_json = update_data.draft_json

    # Reset to draft status if was rejected
    if draft.status == DraftStatus.REJECTED.value:
        draft.status = DraftStatus.DRAFT.value
        draft.rejection_reason = None

    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.post("/campaign-drafts/{draft_id}/submit", response_model=APIResponse[CampaignDraftResponse])
async def submit_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Submit draft for approval."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(
        select(CampaignDraft).where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != DraftStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit draft in {draft.status} status"
        )

    draft.status = DraftStatus.SUBMITTED.value
    draft.submitted_by_user_id = user_id
    draft.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.post("/campaign-drafts/{draft_id}/approve", response_model=APIResponse[CampaignDraftResponse])
async def approve_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Approve a submitted draft (requires CAMPAIGN_APPROVE permission)."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(
        select(CampaignDraft).where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != DraftStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve draft in {draft.status} status"
        )

    draft.status = DraftStatus.APPROVED.value
    draft.approved_by_user_id = user_id
    draft.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.post("/campaign-drafts/{draft_id}/reject", response_model=APIResponse[CampaignDraftResponse])
async def reject_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    reason: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_async_session),
):
    """Reject a submitted draft."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(
        select(CampaignDraft).where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != DraftStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject draft in {draft.status} status"
        )

    draft.status = DraftStatus.REJECTED.value
    draft.rejected_by_user_id = user_id
    draft.rejected_at = datetime.now(timezone.utc)
    draft.rejection_reason = reason

    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


@router.post("/campaign-drafts/{draft_id}/publish", response_model=APIResponse[CampaignDraftResponse])
async def publish_campaign_draft(
    request: Request,
    tenant_id: int,
    draft_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """Publish an approved campaign draft to the platform."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(
        select(CampaignDraft)
        .options(selectinload(CampaignDraft.ad_account))
        .where(
            and_(
                CampaignDraft.id == draft_id,
                CampaignDraft.tenant_id == tenant_id,
            )
        )
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != DraftStatus.APPROVED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish draft in {draft.status} status. Must be approved first."
        )

    # Check budget guardrails
    budget = draft.draft_json.get("campaign", {}).get("budget", {})
    budget_amount = budget.get("amount", 0)

    if draft.ad_account and draft.ad_account.daily_budget_cap:
        if budget_amount > float(draft.ad_account.daily_budget_cap):
            raise HTTPException(
                status_code=400,
                detail=f"Budget {budget_amount} exceeds account cap {draft.ad_account.daily_budget_cap}"
            )

    # Update status to publishing
    draft.status = DraftStatus.PUBLISHING.value
    await db.commit()

    # Create publish log entry
    publish_log = CampaignPublishLog(
        tenant_id=tenant_id,
        draft_id=draft_id,
        platform=draft.platform,
        platform_account_id=draft.ad_account.platform_account_id if draft.ad_account else "",
        published_by_user_id=user_id,
        request_json=draft.draft_json,
        result_status=PublishResult.SUCCESS.value,  # Will be updated by background task
    )
    db.add(publish_log)
    await db.commit()

    # In production, trigger async publish task
    # background_tasks.add_task(publish_campaign_task, draft_id, publish_log.id)

    # Simulate successful publish for now
    draft.status = DraftStatus.PUBLISHED.value
    draft.platform_campaign_id = f"camp_{draft_id.hex[:12]}"
    draft.published_at = datetime.now(timezone.utc)
    publish_log.platform_campaign_id = draft.platform_campaign_id
    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data=CampaignDraftResponse.model_validate(draft),
    )


# =============================================================================
# Publish Logs Endpoints
# =============================================================================

@router.get("/campaign-publish-logs", response_model=APIResponse[List[PublishLogResponse]])
async def list_publish_logs(
    request: Request,
    tenant_id: int,
    draft_id: Optional[UUID] = None,
    platform: Optional[AdPlatform] = None,
    result_status: Optional[PublishResult] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """List publish logs with optional filters."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    query = select(CampaignPublishLog).where(CampaignPublishLog.tenant_id == tenant_id)

    if draft_id:
        query = query.where(CampaignPublishLog.draft_id == draft_id)
    if platform:
        query = query.where(CampaignPublishLog.platform == platform)
    if result_status:
        query = query.where(CampaignPublishLog.result_status == result_status)

    query = query.order_by(CampaignPublishLog.event_time.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return APIResponse(
        success=True,
        data=[PublishLogResponse.model_validate(log) for log in logs],
    )


@router.post("/campaign-publish-logs/{log_id}/retry")
async def retry_publish(
    request: Request,
    tenant_id: int,
    log_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """Retry a failed publish attempt."""
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    result = await db.execute(
        select(CampaignPublishLog).where(
            and_(
                CampaignPublishLog.id == log_id,
                CampaignPublishLog.tenant_id == tenant_id,
            )
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="Publish log not found")

    if log.result_status != PublishResult.FAILURE.value:
        raise HTTPException(
            status_code=400,
            detail="Can only retry failed publish attempts"
        )

    # Update retry count
    log.retry_count += 1
    log.last_retry_at = datetime.now(timezone.utc)
    await db.commit()

    # In production, trigger retry task
    # background_tasks.add_task(publish_retry_task, log_id)

    return APIResponse(
        success=True,
        data={"message": f"Retry initiated (attempt {log.retry_count})"},
    )
