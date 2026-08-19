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

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import CompetitorBenchmark
from app.schemas import (
    APIResponse,
    CompetitorCreate,
    CompetitorResponse,
    CompetitorScanRequest,
    CompetitorUpdate,
    PaginatedResponse,
)

logger = get_logger(__name__)


async def require_competitor_intel_enabled() -> None:
    """
    Gate Competitor Intelligence behind a feature flag.

    Defaults on. The flag was held shut because the refresh worker fabricated
    spend/impressions/CTR with random.randint; ``_apply_scan_result`` was
    rewritten to write honest nulls instead, and this surface now serves only
    what the scanner can actually source — site metadata, social links, and
    the Meta Ad Library active-ad count and platforms.

    Kept wired so a deployment can turn the surface off (FEATURE_COMPETITOR_
    INTEL=false) without a code change.
    """
    if not settings.feature_competitor_intel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Competitor Intelligence is not enabled on this deployment.",
        )


router = APIRouter(dependencies=[Depends(require_competitor_intel_enabled)])


@router.get("", response_model=APIResponse[List[CompetitorResponse]])
async def list_competitors(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    is_primary: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of records to return"
    ),
):
    """List tracked competitors."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(CompetitorBenchmark).where(
        CompetitorBenchmark.tenant_id == tenant_id,
    )

    if is_primary is not None:
        query = query.where(CompetitorBenchmark.is_primary == is_primary)

    # Ordered by observed Ad Library activity, then domain for stability.
    # This used to order by share_of_voice, a column no code path writes, so
    # every row sorted by NULL — arbitrary order presented as a ranking.
    query = query.order_by(
        CompetitorBenchmark.ad_creatives_count.desc().nullslast(),
        CompetitorBenchmark.domain.asc(),
    )
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    competitors = result.scalars().all()

    return APIResponse(
        success=True,
        data=[CompetitorResponse.model_validate(c) for c in competitors],
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


@router.post(
    "",
    response_model=APIResponse[CompetitorResponse],
    status_code=status.HTTP_201_CREATED,
)
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

    logger.info(
        "competitor_added", competitor_id=competitor.id, domain=competitor.domain
    )

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


@router.post("/scan")
async def scan_competitor_preview(
    request: Request,
    payload: CompetitorScanRequest,
):
    """
    Scan a domain and report what we can actually source about it.

    Runs the same scanner the refresh worker uses — website scrape for social
    links and meta tags, plus a Meta Ad Library lookup when a Graph token is
    configured — and returns the raw result without persisting anything. Used
    by the add-competitor flow to show, before saving, exactly which of the
    two sources answered.

    Nothing here is estimated. Where the Ad Library query cannot run the
    result carries ``ad_library.error`` and a manual ``search_url``, rather
    than an ad count of zero.
    """
    from app.services.competitor_scraper import scan_competitor

    tenant_id = getattr(request.state, "tenant_id", None)

    try:
        result = await scan_competitor(
            domain=payload.domain,
            name=payload.name or payload.domain,
            country=payload.country,
            fb_page_name=payload.fb_page_name,
            access_token=settings.meta_access_token,
        )
    except Exception as exc:
        logger.warning(
            "competitor_scan_failed",
            tenant_id=tenant_id,
            domain=payload.domain,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the competitor's site or the Ad Library.",
        ) from exc

    return APIResponse(success=True, data=result)
