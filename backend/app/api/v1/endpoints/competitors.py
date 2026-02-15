# =============================================================================
# Stratum AI - Competitor Intelligence Endpoints
# =============================================================================
"""
Competitor benchmarking and market intelligence.
Implements Module D: Competitor Intelligence.
"""

import os
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
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
)

logger = get_logger(__name__)
router = APIRouter()


# ── Scan request / response schemas ──────────────────────────────────────────
class CompetitorScanRequest(BaseModel):
    """Request body for scanning a competitor."""

    domain: str = Field(..., min_length=3, max_length=255, description="Competitor website domain")
    name: str = Field(..., min_length=1, max_length=255, description="Competitor name for ad library search")
    country: str = Field(default="SA", max_length=10, description="ISO country code")


class CompetitorScanResponse(BaseModel):
    """Response from a competitor scan."""

    domain: str
    social_links: dict
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    fb_page_name: Optional[str] = None
    ig_account_name: Optional[str] = None
    ad_library: dict
    scanned_at: str
    scrape_error: Optional[str] = None


@router.get("", response_model=APIResponse[list[CompetitorResponse]])
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
                "end": datetime.now(UTC).date().isoformat(),
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


@router.post(
    "", response_model=APIResponse[CompetitorResponse], status_code=status.HTTP_201_CREATED
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


# ── Competitor Scan: Scrape website + Meta Ad Library ─────────────────────────


@router.post("/scan", response_model=APIResponse[CompetitorScanResponse])
async def scan_competitor_endpoint(
    request: Request,
    scan_request: CompetitorScanRequest,
):
    """
    Scan a competitor: scrape their website for social links (FB, IG, etc.)
    and search Meta Ad Library for their active ads.

    Returns social_links and ad_library results.
    """
    from app.services.competitor_scraper import scan_competitor

    # Use the platform META_ACCESS_TOKEN for Ad Library API
    access_token = os.environ.get("META_ACCESS_TOKEN")

    scan_result = await scan_competitor(
        domain=scan_request.domain,
        name=scan_request.name,
        country=scan_request.country,
        access_token=access_token,
    )

    return APIResponse(
        success=True,
        data=scan_result,
        message="Competitor scan complete",
    )


@router.post("/{competitor_id}/scan", response_model=APIResponse[CompetitorScanResponse])
async def scan_existing_competitor(
    request: Request,
    competitor_id: int,
    country: str = Query("SA", max_length=10),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Scan an existing tracked competitor: scrape their website for social links
    and search Meta Ad Library, then update the DB record.
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

    from app.services.competitor_scraper import scan_competitor

    access_token = os.environ.get("META_ACCESS_TOKEN")

    scan_result = await scan_competitor(
        domain=competitor.domain,
        name=competitor.name or competitor.domain,
        country=country,
        access_token=access_token,
    )

    # Update the competitor record with scraped data
    if scan_result.get("social_links"):
        competitor.social_links = scan_result["social_links"]
    if scan_result.get("meta_title"):
        competitor.meta_title = scan_result["meta_title"]
    if scan_result.get("meta_description"):
        competitor.meta_description = scan_result["meta_description"]

    ad_library = scan_result.get("ad_library", {})
    if ad_library.get("has_ads"):
        competitor.ad_creatives_count = ad_library.get("ad_count", 0)
        competitor.detected_ad_platforms = ad_library.get("ads", [{}])[0].get("platforms") if ad_library.get("ads") else None

    competitor.last_fetched_at = datetime.now(UTC)
    competitor.data_source = "scraper"

    # Append to metrics history
    history = competitor.metrics_history or []
    history.append({
        "timestamp": datetime.now(UTC).isoformat(),
        "social_links": scan_result.get("social_links"),
        "ad_library": {
            "has_ads": ad_library.get("has_ads"),
            "ad_count": ad_library.get("ad_count"),
        },
    })
    competitor.metrics_history = history[-50:]  # Keep last 50 snapshots

    await db.commit()
    await db.refresh(competitor)

    logger.info(
        "competitor_scanned",
        competitor_id=competitor_id,
        has_ads=ad_library.get("has_ads"),
    )

    return APIResponse(
        success=True,
        data=scan_result,
        message="Competitor scanned and updated",
    )
