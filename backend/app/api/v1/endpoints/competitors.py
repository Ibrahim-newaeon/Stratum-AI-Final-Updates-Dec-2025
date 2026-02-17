# =============================================================================
# Stratum AI - Competitor Intelligence Endpoints
# =============================================================================
"""
Competitor benchmarking and market intelligence.
Implements Module D: Competitor Intelligence.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import CompetitorBenchmark
from app.schemas import (
    APIResponse,
    CompetitorCreate,
    CompetitorResponse,
    CompetitorShareOfVoiceResponse,
    CompetitorUpdate,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=APIResponse[List[CompetitorResponse]])
async def list_competitors(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    is_primary: Optional[bool] = None,
):
    """List tracked competitors."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(CompetitorBenchmark).where(
        CompetitorBenchmark.tenant_id == tenant_id,
    )

    if is_primary is not None:
        query = query.where(CompetitorBenchmark.is_primary == is_primary)

    query = query.order_by(CompetitorBenchmark.share_of_voice.desc().nullslast())

    result = await db.execute(query)
    competitors = result.scalars().all()

    return APIResponse(
        success=True,
        data=[CompetitorResponse.model_validate(c) for c in competitors],
    )


@router.get("/share-of-voice", response_model=APIResponse[CompetitorShareOfVoiceResponse])
async def get_share_of_voice(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get share of voice comparison across all tracked competitors.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark)
        .where(CompetitorBenchmark.tenant_id == tenant_id)
        .order_by(CompetitorBenchmark.share_of_voice.desc().nullslast())
    )
    competitors = result.scalars().all()

    total_traffic = sum(c.estimated_traffic or 0 for c in competitors)

    comparison = [
        {
            "domain": c.domain,
            "name": c.name,
            "share_of_voice": c.share_of_voice,
            "estimated_traffic": c.estimated_traffic,
            "traffic_trend": c.traffic_trend,
            "is_primary": c.is_primary,
        }
        for c in competitors
    ]

    return APIResponse(
        success=True,
        data=CompetitorShareOfVoiceResponse(
            competitors=comparison,
            total_market=total_traffic,
            date_range={
                "start": "calculated_dynamically",
                "end": datetime.now(timezone.utc).date().isoformat(),
            },
        ),
    )


@router.get("/{competitor_id}", response_model=APIResponse[CompetitorResponse])
async def get_competitor(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get detailed competitor information."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.id == competitor_id,
            CompetitorBenchmark.tenant_id == tenant_id,
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    return APIResponse(
        success=True,
        data=CompetitorResponse.model_validate(competitor),
    )


@router.post("", response_model=APIResponse[CompetitorResponse], status_code=status.HTTP_201_CREATED)
async def add_competitor(
    request: Request,
    competitor_data: CompetitorCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Add a new competitor to track."""
    tenant_id = getattr(request.state, "tenant_id", None)

    # Check for duplicate domain
    existing = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.tenant_id == tenant_id,
            CompetitorBenchmark.domain == competitor_data.domain.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Competitor domain already tracked",
        )

    competitor = CompetitorBenchmark(
        tenant_id=tenant_id,
        domain=competitor_data.domain.lower(),
        name=competitor_data.name,
        is_primary=competitor_data.is_primary,
    )

    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)

    # Queue initial data fetch
    from app.workers.tasks import fetch_competitor_data

    fetch_competitor_data.delay(tenant_id, competitor.id)

    logger.info("competitor_added", competitor_id=competitor.id, domain=competitor.domain)

    return APIResponse(
        success=True,
        data=CompetitorResponse.model_validate(competitor),
        message="Competitor added. Data will be fetched shortly.",
    )


@router.patch("/{competitor_id}", response_model=APIResponse[CompetitorResponse])
async def update_competitor(
    request: Request,
    competitor_id: int,
    update_data: CompetitorUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update competitor details."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.id == competitor_id,
            CompetitorBenchmark.tenant_id == tenant_id,
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(competitor, field, value)

    await db.commit()
    await db.refresh(competitor)

    return APIResponse(
        success=True,
        data=CompetitorResponse.model_validate(competitor),
        message="Competitor updated",
    )


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_competitor(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a competitor from tracking."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.id == competitor_id,
            CompetitorBenchmark.tenant_id == tenant_id,
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    await db.delete(competitor)
    await db.commit()

    logger.info("competitor_removed", competitor_id=competitor_id)


@router.post("/{competitor_id}/refresh")
async def refresh_competitor_data(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger a manual refresh of competitor data.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.id == competitor_id,
            CompetitorBenchmark.tenant_id == tenant_id,
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    # Queue refresh task
    from app.workers.tasks import fetch_competitor_data

    task = fetch_competitor_data.delay(tenant_id, competitor_id)

    return APIResponse(
        success=True,
        data={"task_id": task.id},
        message="Refresh queued",
    )


@router.get("/{competitor_id}/keywords")
async def get_competitor_keywords(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_async_session),
    keyword_type: str = Query("all", pattern="^(all|paid|organic)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get top keywords for a competitor.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(CompetitorBenchmark).where(
            CompetitorBenchmark.id == competitor_id,
            CompetitorBenchmark.tenant_id == tenant_id,
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    keywords = competitor.top_keywords or []

    # Filter by type if specified
    if keyword_type != "all":
        keywords = [k for k in keywords if k.get("type") == keyword_type]

    return APIResponse(
        success=True,
        data={
            "domain": competitor.domain,
            "keywords": keywords[:limit],
            "total_paid": competitor.paid_keywords_count,
            "total_organic": competitor.organic_keywords_count,
        },
    )
