# =============================================================================
# Stratum AI - Campaign Management Endpoints
# =============================================================================
"""
Campaign CRUD operations and metrics retrieval.
Implements Module B: Unified Campaign Model.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import AdPlatform, Campaign, CampaignMetric, CampaignStatus
from app.schemas import (
    APIResponse,
    CampaignCreate,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignMetricResponse,
    CampaignMetricsTimeSeriesResponse,
    CampaignResponse,
    CampaignUpdate,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=APIResponse[PaginatedResponse[CampaignListResponse]])
async def list_campaigns(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: Optional[AdPlatform] = None,
    status: Optional[CampaignStatus] = None,
    search: Optional[str] = None,
    labels: Optional[List[str]] = Query(None),
):
    """
    List campaigns with filtering and pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        platform: Filter by ad platform
        status: Filter by campaign status
        search: Search by name
        labels: Filter by labels
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Build query with tenant isolation
    query = select(Campaign).where(
        Campaign.tenant_id == tenant_id,
        Campaign.is_deleted == False,
    )

    # Apply filters
    if platform:
        query = query.where(Campaign.platform == platform)
    if status:
        query = query.where(Campaign.status == status)
    if search:
        query = query.where(Campaign.name.ilike(f"%{search}%"))
    if labels:
        # PostgreSQL JSONB contains any of the labels
        for label in labels:
            query = query.where(Campaign.labels.contains([label]))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Campaign.updated_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[
                CampaignListResponse(
                    id=c.id,
                    name=c.name,
                    platform=c.platform,
                    status=c.status,
                    total_spend_cents=c.total_spend_cents,
                    impressions=c.impressions,
                    clicks=c.clicks,
                    conversions=c.conversions,
                    roas=c.roas,
                    labels=c.labels,
                    last_synced_at=c.last_synced_at,
                )
                for c in campaigns
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/{campaign_id}", response_model=APIResponse[CampaignDetailResponse])
async def get_campaign(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get detailed campaign information."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return APIResponse(
        success=True,
        data=CampaignDetailResponse(
            id=campaign.id,
            tenant_id=campaign.tenant_id,
            name=campaign.name,
            platform=campaign.platform,
            external_id=campaign.external_id,
            account_id=campaign.account_id,
            status=campaign.status,
            objective=campaign.objective,
            daily_budget_cents=campaign.daily_budget_cents,
            lifetime_budget_cents=campaign.lifetime_budget_cents,
            total_spend_cents=campaign.total_spend_cents,
            currency=campaign.currency,
            impressions=campaign.impressions,
            clicks=campaign.clicks,
            conversions=campaign.conversions,
            revenue_cents=campaign.revenue_cents,
            ctr=campaign.ctr,
            cpc_cents=campaign.cpc_cents,
            cpm_cents=campaign.cpm_cents,
            cpa_cents=campaign.cpa_cents,
            roas=campaign.roas,
            targeting_age_min=campaign.targeting_age_min,
            targeting_age_max=campaign.targeting_age_max,
            targeting_genders=campaign.targeting_genders,
            targeting_locations=campaign.targeting_locations,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            labels=campaign.labels,
            last_synced_at=campaign.last_synced_at,
            demographics_age=campaign.demographics_age,
            demographics_gender=campaign.demographics_gender,
            demographics_location=campaign.demographics_location,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        ),
    )


@router.post("", response_model=APIResponse[CampaignResponse], status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: Request,
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new campaign."""
    tenant_id = getattr(request.state, "tenant_id", None)

    # Check for duplicate
    existing = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.platform == campaign_data.platform,
            Campaign.external_id == campaign_data.external_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign with this external_id already exists",
        )

    campaign = Campaign(
        tenant_id=tenant_id,
        **campaign_data.model_dump(),
    )

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    logger.info("campaign_created", campaign_id=campaign.id, tenant_id=tenant_id)

    return APIResponse(
        success=True,
        data=CampaignResponse.model_validate(campaign),
        message="Campaign created successfully",
    )


@router.patch("/{campaign_id}", response_model=APIResponse[CampaignResponse])
async def update_campaign(
    request: Request,
    campaign_id: int,
    update_data: CampaignUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a campaign."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)

    logger.info("campaign_updated", campaign_id=campaign_id)

    return APIResponse(
        success=True,
        data=CampaignResponse.model_validate(campaign),
        message="Campaign updated successfully",
    )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Soft delete a campaign."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    campaign.soft_delete()
    await db.commit()

    logger.info("campaign_deleted", campaign_id=campaign_id)


@router.get("/{campaign_id}/metrics", response_model=APIResponse[CampaignMetricsTimeSeriesResponse])
async def get_campaign_metrics(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_async_session),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get time-series metrics for a campaign.

    Args:
        campaign_id: Campaign ID
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: today)
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Verify campaign exists and belongs to tenant
    campaign_result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    if not campaign_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Default date range
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Query metrics
    result = await db.execute(
        select(CampaignMetric)
        .where(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.tenant_id == tenant_id,
            CampaignMetric.date >= start_date,
            CampaignMetric.date <= end_date,
        )
        .order_by(CampaignMetric.date)
    )
    metrics = result.scalars().all()

    # Calculate aggregates
    total_impressions = sum(m.impressions for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_spend = sum(m.spend_cents for m in metrics)
    total_revenue = sum(m.revenue_cents for m in metrics)

    aggregated = {
        "impressions": total_impressions,
        "clicks": total_clicks,
        "conversions": total_conversions,
        "spend_cents": total_spend,
        "revenue_cents": total_revenue,
        "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
        "roas": (total_revenue / total_spend) if total_spend > 0 else 0,
    }

    return APIResponse(
        success=True,
        data=CampaignMetricsTimeSeriesResponse(
            campaign_id=campaign_id,
            date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
            metrics=[
                CampaignMetricResponse(
                    date=m.date,
                    impressions=m.impressions,
                    clicks=m.clicks,
                    conversions=m.conversions,
                    spend_cents=m.spend_cents,
                    revenue_cents=m.revenue_cents,
                    video_views=m.video_views,
                    video_completions=m.video_completions,
                )
                for m in metrics
            ],
            aggregated=aggregated,
        ),
    )


@router.post("/sync-all")
async def trigger_sync_all_campaigns(
    request: Request,
) -> APIResponse:
    """
    Trigger a manual sync for all campaigns across all platforms.
    Queues a Celery task to fetch latest data from every ad platform.
    """
    from app.workers.tasks import sync_all_campaigns

    task = sync_all_campaigns.delay()

    return APIResponse(
        success=True,
        data={"task_id": task.id},
        message="Sync all campaigns queued successfully",
    )


@router.post("/{campaign_id}/sync")
async def trigger_campaign_sync(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger a manual sync for a campaign.
    Queues a Celery task to fetch latest data from the ad platform.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Verify campaign exists
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Queue sync task
    from app.workers.tasks import sync_campaign_data

    task = sync_campaign_data.delay(tenant_id, campaign_id)

    return APIResponse(
        success=True,
        data={"task_id": task.id},
        message="Sync queued successfully",
    )
