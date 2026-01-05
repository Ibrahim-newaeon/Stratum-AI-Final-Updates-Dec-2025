# =============================================================================
# Stratum AI - Digital Asset Management Endpoints
# =============================================================================
"""
Creative asset management for DAM functionality.
Implements Module B: Digital Asset Management.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import AssetType, CreativeAsset
from app.schemas import (
    APIResponse,
    CreativeAssetCreate,
    CreativeAssetResponse,
    CreativeAssetUpdate,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=APIResponse[PaginatedResponse[CreativeAssetResponse]])
async def list_assets(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[AssetType] = None,
    folder: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    min_fatigue_score: Optional[float] = None,
    max_fatigue_score: Optional[float] = None,
):
    """
    List creative assets with filtering.

    Args:
        asset_type: Filter by asset type
        folder: Filter by folder
        tags: Filter by tags
        min_fatigue_score: Minimum fatigue score
        max_fatigue_score: Maximum fatigue score
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(CreativeAsset).where(
        CreativeAsset.tenant_id == tenant_id,
        CreativeAsset.is_deleted == False,
    )

    if asset_type:
        query = query.where(CreativeAsset.asset_type == asset_type)
    if folder:
        query = query.where(CreativeAsset.folder == folder)
    if tags:
        for tag in tags:
            query = query.where(CreativeAsset.tags.contains([tag]))
    if min_fatigue_score is not None:
        query = query.where(CreativeAsset.fatigue_score >= min_fatigue_score)
    if max_fatigue_score is not None:
        query = query.where(CreativeAsset.fatigue_score <= max_fatigue_score)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(CreativeAsset.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    assets = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[CreativeAssetResponse.model_validate(a) for a in assets],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/folders")
async def list_folders(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get list of unique folders."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset.folder)
        .where(
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
            CreativeAsset.folder.isnot(None),
        )
        .distinct()
    )
    folders = [row[0] for row in result.all()]

    return APIResponse(success=True, data=folders)


@router.get("/fatigued", response_model=APIResponse[List[CreativeAssetResponse]])
async def get_fatigued_assets(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    threshold: float = Query(70.0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get assets with high fatigue scores.
    Useful for identifying creatives that need refreshing.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset)
        .where(
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
            CreativeAsset.fatigue_score >= threshold,
        )
        .order_by(CreativeAsset.fatigue_score.desc())
        .limit(limit)
    )
    assets = result.scalars().all()

    return APIResponse(
        success=True,
        data=[CreativeAssetResponse.model_validate(a) for a in assets],
    )


@router.get("/{asset_id}", response_model=APIResponse[CreativeAssetResponse])
async def get_asset(
    request: Request,
    asset_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get asset details."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return APIResponse(
        success=True,
        data=CreativeAssetResponse.model_validate(asset),
    )


@router.post("", response_model=APIResponse[CreativeAssetResponse], status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: Request,
    asset_data: CreativeAssetCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new creative asset."""
    tenant_id = getattr(request.state, "tenant_id", None)

    asset = CreativeAsset(
        tenant_id=tenant_id,
        **asset_data.model_dump(),
    )

    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    logger.info("asset_created", asset_id=asset.id, tenant_id=tenant_id)

    return APIResponse(
        success=True,
        data=CreativeAssetResponse.model_validate(asset),
        message="Asset created successfully",
    )


@router.patch("/{asset_id}", response_model=APIResponse[CreativeAssetResponse])
async def update_asset(
    request: Request,
    asset_id: int,
    update_data: CreativeAssetUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update an asset."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)

    return APIResponse(
        success=True,
        data=CreativeAssetResponse.model_validate(asset),
        message="Asset updated successfully",
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    request: Request,
    asset_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Soft delete an asset."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    asset.soft_delete()
    await db.commit()

    logger.info("asset_deleted", asset_id=asset_id)


@router.post("/{asset_id}/calculate-fatigue")
async def calculate_fatigue_score(
    request: Request,
    asset_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Recalculate fatigue score for an asset.

    Fatigue is calculated based on:
    - Times used
    - Time since first use
    - CTR trend (if decreasing)
    - Impressions volume
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.tenant_id == tenant_id,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Calculate fatigue score
    from datetime import datetime, timezone, timedelta

    base_score = 0.0

    # Factor 1: Times used (max 30 points)
    if asset.times_used > 0:
        base_score += min(30, asset.times_used * 3)

    # Factor 2: Age since first use (max 30 points)
    if asset.first_used_at:
        days_active = (datetime.now(timezone.utc) - asset.first_used_at).days
        base_score += min(30, days_active * 0.5)

    # Factor 3: High impression volume (max 20 points)
    if asset.impressions > 100000:
        base_score += min(20, (asset.impressions / 100000) * 5)

    # Factor 4: CTR below threshold (max 20 points)
    if asset.ctr and asset.ctr < 1.0:
        base_score += 20 - (asset.ctr * 10)

    asset.fatigue_score = min(100, base_score)
    await db.commit()
    await db.refresh(asset)

    return APIResponse(
        success=True,
        data={"fatigue_score": asset.fatigue_score},
        message="Fatigue score calculated",
    )
