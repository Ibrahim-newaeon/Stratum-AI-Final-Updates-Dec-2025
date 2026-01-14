# =============================================================================
# Stratum AI - Audience Sync API Endpoints
# =============================================================================
"""
REST API endpoints for CDP audience sync to ad platforms.

Provides endpoints for:
- Creating/managing platform audiences
- Triggering manual syncs
- Viewing sync history
- Managing platform credentials
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.tenancy.deps import get_tenant_id
from app.auth.deps import get_current_user
from app.models import User
from app.models.audience_sync import SyncPlatform, SyncOperation, SyncStatus
from app.services.cdp.audience_sync import AudienceSyncService

router = APIRouter(prefix="/cdp/audience-sync", tags=["CDP Audience Sync"])


# =============================================================================
# Schemas
# =============================================================================

class PlatformAudienceCreate(BaseModel):
    """Schema for creating a platform audience."""
    segment_id: UUID = Field(..., description="CDP segment ID to sync")
    platform: str = Field(..., description="Platform: meta, google, tiktok, snapchat")
    ad_account_id: str = Field(..., description="Platform ad account ID")
    audience_name: str = Field(..., description="Name for the audience on the platform")
    description: Optional[str] = Field(None, description="Audience description")
    auto_sync: bool = Field(True, description="Enable automatic sync")
    sync_interval_hours: int = Field(24, ge=1, le=168, description="Auto-sync interval in hours")


class PlatformAudienceResponse(BaseModel):
    """Response schema for platform audience."""
    id: UUID
    segment_id: UUID
    platform: str
    platform_audience_id: Optional[str]
    platform_audience_name: str
    ad_account_id: str
    description: Optional[str]
    auto_sync: bool
    sync_interval_hours: int
    is_active: bool
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    platform_size: Optional[int]
    matched_size: Optional[int]
    match_rate: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncJobResponse(BaseModel):
    """Response schema for sync job."""
    id: UUID
    platform_audience_id: UUID
    operation: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    profiles_total: int
    profiles_sent: int
    profiles_added: int
    profiles_removed: int
    profiles_failed: int
    error_message: Optional[str]
    triggered_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TriggerSyncRequest(BaseModel):
    """Request schema for triggering a sync."""
    operation: str = Field("update", description="Operation: update, replace")


class ConnectedPlatformResponse(BaseModel):
    """Response schema for connected platform."""
    platform: str
    ad_accounts: List[Dict[str, str]]


class PlatformAudienceListResponse(BaseModel):
    """Response schema for listing platform audiences."""
    audiences: List[PlatformAudienceResponse]
    total: int


class SyncHistoryResponse(BaseModel):
    """Response schema for sync history."""
    jobs: List[SyncJobResponse]


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/platforms",
    response_model=List[ConnectedPlatformResponse],
    summary="Get connected platforms",
    description="List all platforms with active credentials for audience sync.",
)
async def get_connected_platforms(
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
) -> List[ConnectedPlatformResponse]:
    """Get list of platforms with active credentials."""
    service = AudienceSyncService(db, tenant_id)
    platforms = await service.get_connected_platforms()
    return [ConnectedPlatformResponse(**p) for p in platforms]


@router.get(
    "/audiences",
    response_model=PlatformAudienceListResponse,
    summary="List platform audiences",
    description="List all platform audiences with optional filtering.",
)
async def list_platform_audiences(
    segment_id: Optional[UUID] = Query(None, description="Filter by segment ID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
) -> PlatformAudienceListResponse:
    """List platform audiences."""
    service = AudienceSyncService(db, tenant_id)
    audiences, total = await service.list_platform_audiences(
        segment_id=segment_id,
        platform=platform,
        limit=limit,
        offset=offset,
    )
    return PlatformAudienceListResponse(
        audiences=[PlatformAudienceResponse.model_validate(a) for a in audiences],
        total=total,
    )


@router.post(
    "/audiences",
    response_model=PlatformAudienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create platform audience",
    description="Create a new platform audience linked to a CDP segment.",
)
async def create_platform_audience(
    request: PlatformAudienceCreate,
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> PlatformAudienceResponse:
    """Create a platform audience and sync initial users."""
    # Validate platform
    if request.platform not in [p.value for p in SyncPlatform]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Supported: {[p.value for p in SyncPlatform]}",
        )

    service = AudienceSyncService(db, tenant_id)

    try:
        platform_audience, sync_job = await service.create_platform_audience(
            segment_id=request.segment_id,
            platform=request.platform,
            ad_account_id=request.ad_account_id,
            audience_name=request.audience_name,
            description=request.description,
            auto_sync=request.auto_sync,
            sync_interval_hours=request.sync_interval_hours,
        )
        await db.commit()
        return PlatformAudienceResponse.model_validate(platform_audience)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create platform audience: {str(e)}",
        )


@router.get(
    "/audiences/{audience_id}",
    response_model=PlatformAudienceResponse,
    summary="Get platform audience",
    description="Get details of a specific platform audience.",
)
async def get_platform_audience(
    audience_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
) -> PlatformAudienceResponse:
    """Get platform audience details."""
    service = AudienceSyncService(db, tenant_id)
    audiences, _ = await service.list_platform_audiences(limit=1, offset=0)

    # Query directly
    from sqlalchemy import select
    from app.models.audience_sync import PlatformAudience

    result = await db.execute(
        select(PlatformAudience).where(
            PlatformAudience.id == audience_id,
            PlatformAudience.tenant_id == tenant_id,
        )
    )
    audience = result.scalar_one_or_none()

    if not audience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform audience not found",
        )

    return PlatformAudienceResponse.model_validate(audience)


@router.post(
    "/audiences/{audience_id}/sync",
    response_model=SyncJobResponse,
    summary="Trigger sync",
    description="Manually trigger a sync for a platform audience.",
)
async def trigger_sync(
    audience_id: UUID,
    request: TriggerSyncRequest,
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> SyncJobResponse:
    """Trigger a manual sync."""
    # Map operation string to enum
    operation_map = {
        "update": SyncOperation.UPDATE,
        "replace": SyncOperation.REPLACE,
    }
    operation = operation_map.get(request.operation)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operation. Supported: update, replace",
        )

    service = AudienceSyncService(db, tenant_id)

    try:
        sync_job = await service.sync_platform_audience(
            platform_audience_id=audience_id,
            operation=operation,
            triggered_by="manual",
            triggered_by_user_id=current_user.id,
        )
        await db.commit()
        return SyncJobResponse.model_validate(sync_job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get(
    "/audiences/{audience_id}/history",
    response_model=SyncHistoryResponse,
    summary="Get sync history",
    description="Get sync job history for a platform audience.",
)
async def get_sync_history(
    audience_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
) -> SyncHistoryResponse:
    """Get sync history."""
    service = AudienceSyncService(db, tenant_id)
    jobs = await service.get_sync_history(audience_id, limit=limit)
    return SyncHistoryResponse(
        jobs=[SyncJobResponse.model_validate(j) for j in jobs]
    )


@router.delete(
    "/audiences/{audience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete platform audience",
    description="Delete a platform audience mapping.",
)
async def delete_platform_audience(
    audience_id: UUID,
    delete_from_platform: bool = Query(True, description="Also delete from ad platform"),
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Delete a platform audience."""
    service = AudienceSyncService(db, tenant_id)

    success = await service.delete_platform_audience(
        platform_audience_id=audience_id,
        delete_from_platform=delete_from_platform,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform audience not found",
        )

    await db.commit()


# =============================================================================
# Segment Sync Endpoints (Convenience)
# =============================================================================

@router.get(
    "/segments/{segment_id}/audiences",
    response_model=PlatformAudienceListResponse,
    summary="Get segment audiences",
    description="List all platform audiences for a specific segment.",
)
async def get_segment_audiences(
    segment_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
) -> PlatformAudienceListResponse:
    """Get all platform audiences for a segment."""
    service = AudienceSyncService(db, tenant_id)
    audiences, total = await service.list_platform_audiences(
        segment_id=segment_id,
        limit=100,
        offset=0,
    )
    return PlatformAudienceListResponse(
        audiences=[PlatformAudienceResponse.model_validate(a) for a in audiences],
        total=total,
    )


@router.post(
    "/segments/{segment_id}/sync-all",
    response_model=List[SyncJobResponse],
    summary="Sync segment to all platforms",
    description="Trigger sync for all platform audiences linked to a segment.",
)
async def sync_segment_to_all_platforms(
    segment_id: UUID,
    operation: str = Query("update", description="Operation: update, replace"),
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> List[SyncJobResponse]:
    """Sync a segment to all connected platforms."""
    operation_map = {
        "update": SyncOperation.UPDATE,
        "replace": SyncOperation.REPLACE,
    }
    sync_operation = operation_map.get(operation)
    if not sync_operation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation",
        )

    service = AudienceSyncService(db, tenant_id)

    # Get all platform audiences for this segment
    audiences, _ = await service.list_platform_audiences(
        segment_id=segment_id,
        limit=100,
    )

    if not audiences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No platform audiences found for this segment",
        )

    # Trigger sync for each
    jobs = []
    errors = []

    for audience in audiences:
        try:
            job = await service.sync_platform_audience(
                platform_audience_id=audience.id,
                operation=sync_operation,
                triggered_by="manual",
                triggered_by_user_id=current_user.id,
            )
            jobs.append(job)
        except Exception as e:
            errors.append({
                "platform": audience.platform,
                "error": str(e),
            })

    await db.commit()

    return [SyncJobResponse.model_validate(j) for j in jobs]
