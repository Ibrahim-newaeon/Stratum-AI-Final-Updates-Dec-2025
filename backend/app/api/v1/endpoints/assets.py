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
    Recalculate fatigue score for an asset using comprehensive analysis.

    Fatigue Components (each 0-25 points, total 0-100):
    - Usage Factor: Based on times_used across campaigns
    - Age Factor: Days since first deployment
    - Impression Saturation: Volume relative to audience
    - Performance Decay: CTR trend analysis
    """
    from app.services.ad_fatigue_service import AdFatigueService

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

    # Use the comprehensive fatigue service
    fatigue_service = AdFatigueService()
    breakdown = fatigue_service.calculate_fatigue_score(asset)

    # Update asset
    asset.fatigue_score = breakdown.total_score
    await db.commit()
    await db.refresh(asset)

    return APIResponse(
        success=True,
        data={
            "fatigue_score": breakdown.total_score,
            "status": breakdown.status.value,
            "breakdown": {
                "usage_score": breakdown.usage_score,
                "age_score": breakdown.age_score,
                "saturation_score": breakdown.saturation_score,
                "decay_score": breakdown.decay_score,
            },
            "recommendations": breakdown.recommendations,
        },
        message="Fatigue score calculated",
    )


@router.post("/calculate-all-fatigue")
async def calculate_all_fatigue_scores(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Batch recalculate fatigue scores for all assets.
    Returns summary with assets needing attention.
    """
    from app.services.ad_fatigue_service import AdFatigueService

    tenant_id = getattr(request.state, "tenant_id", None)

    fatigue_service = AdFatigueService(db)
    summary = await fatigue_service.calculate_all_assets_fatigue(tenant_id)

    return APIResponse(
        success=True,
        data=summary,
        message=f"Calculated fatigue for {summary['total_assets']} assets",
    )


@router.get("/fatigue-summary")
async def get_fatigue_summary(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get fatigue distribution summary for dashboard widgets.
    """
    from app.services.ad_fatigue_service import FatigueStatus

    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CreativeAsset)
        .where(
            CreativeAsset.tenant_id == tenant_id,
            CreativeAsset.is_deleted == False,
        )
    )
    assets = result.scalars().all()

    # Build distribution
    distribution = {
        "fresh": {"count": 0, "label": "Fresh (0-25%)", "color": "#22c55e"},
        "healthy": {"count": 0, "label": "Healthy (26-50%)", "color": "#84cc16"},
        "watch": {"count": 0, "label": "Watch (51-70%)", "color": "#f59e0b"},
        "fatigued": {"count": 0, "label": "Fatigued (71-85%)", "color": "#f97316"},
        "critical": {"count": 0, "label": "Critical (86-100%)", "color": "#ef4444"},
    }

    for asset in assets:
        score = asset.fatigue_score
        if score <= 25:
            distribution["fresh"]["count"] += 1
        elif score <= 50:
            distribution["healthy"]["count"] += 1
        elif score <= 70:
            distribution["watch"]["count"] += 1
        elif score <= 85:
            distribution["fatigued"]["count"] += 1
        else:
            distribution["critical"]["count"] += 1

    return APIResponse(
        success=True,
        data={
            "total_assets": len(assets),
            "distribution": distribution,
            "needs_attention": distribution["fatigued"]["count"] + distribution["critical"]["count"],
        },
    )
