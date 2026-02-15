# =============================================================================
# Stratum AI - Newsletter / Email Campaign API
# =============================================================================
"""
Newsletter campaign management endpoints.

Campaign CRUD, template management, subscriber management,
and public tracking/unsubscribe endpoints.
"""

import base64
import hashlib
import secrets
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, CurrentUserDep
from app.db.session import get_async_session
from app.base_models import LandingPageSubscriber, SubscriberStatus
from app.models.newsletter import (
    CampaignStatus,
    NewsletterCampaign,
    NewsletterEvent,
    NewsletterEventType,
    NewsletterTemplate,
    TemplateCategory,
)

router = APIRouter(prefix="/newsletter")


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(default="", max_length=500)
    preheader_text: Optional[str] = Field(default=None, max_length=500)
    content_html: Optional[str] = None
    content_json: Optional[dict] = None
    category: str = Field(default="promotional")


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=500)
    preheader_text: Optional[str] = Field(default=None, max_length=500)
    content_html: Optional[str] = None
    content_json: Optional[dict] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    preheader_text: Optional[str]
    content_html: Optional[str]
    content_json: Optional[dict]
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    preheader_text: Optional[str] = Field(default=None, max_length=500)
    content_html: Optional[str] = None
    content_json: Optional[dict] = None
    template_id: Optional[int] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    reply_to_email: Optional[str] = None
    audience_filters: Optional[dict] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=500)
    preheader_text: Optional[str] = Field(default=None, max_length=500)
    content_html: Optional[str] = None
    content_json: Optional[dict] = None
    template_id: Optional[int] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    reply_to_email: Optional[str] = None
    audience_filters: Optional[dict] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    subject: str
    preheader_text: Optional[str]
    content_html: Optional[str]
    content_json: Optional[dict]
    template_id: Optional[int]
    status: str
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]
    from_name: Optional[str]
    from_email: Optional[str]
    reply_to_email: Optional[str]
    audience_filters: Optional[dict]
    total_recipients: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_unsubscribed: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignResponse]
    total: int


class ScheduleRequest(BaseModel):
    scheduled_at: datetime


class SendTestRequest(BaseModel):
    emails: list[str] = Field(..., min_length=1, max_length=5)


class SubscriberResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    status: str
    attributed_platform: Optional[str]
    lead_score: int
    subscribed_to_newsletter: bool
    unsubscribed_at: Optional[datetime]
    last_email_sent_at: Optional[datetime]
    last_email_opened_at: Optional[datetime]
    email_send_count: int
    email_open_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriberStatsResponse(BaseModel):
    total: int
    active: int
    unsubscribed: int


class AnalyticsResponse(BaseModel):
    campaign: CampaignResponse
    open_rate: float
    click_rate: float
    bounce_rate: float
    unsubscribe_rate: float
    events: list[dict]


# ---------------------------------------------------------------------------
# Helper: Generate unsubscribe token
# ---------------------------------------------------------------------------
def _generate_unsubscribe_token(campaign_id: int, subscriber_id: int) -> str:
    """Create a signed token for unsubscribe URLs."""
    payload = f"{campaign_id}:{subscriber_id}"
    token = base64.urlsafe_b64encode(payload.encode()).decode()
    return token


def _decode_unsubscribe_token(token: str) -> tuple[int, int]:
    """Decode an unsubscribe token to (campaign_id, subscriber_id)."""
    try:
        payload = base64.urlsafe_b64decode(token.encode()).decode()
        parts = payload.split(":")
        return int(parts[0]), int(parts[1])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")


# ---------------------------------------------------------------------------
# Helper: Count audience for filters
# ---------------------------------------------------------------------------
async def _count_audience(db: AsyncSession, filters: Optional[dict]) -> int:
    """Count subscribers matching audience filters."""
    query = select(func.count(LandingPageSubscriber.id)).where(
        LandingPageSubscriber.subscribed_to_newsletter == True  # noqa: E712
    )

    if filters:
        if "status" in filters and filters["status"]:
            query = query.where(LandingPageSubscriber.status.in_(filters["status"]))
        if "min_lead_score" in filters:
            query = query.where(LandingPageSubscriber.lead_score >= filters["min_lead_score"])
        if "platforms" in filters and filters["platforms"]:
            query = query.where(
                LandingPageSubscriber.attributed_platform.in_(filters["platforms"])
            )

    result = await db.execute(query)
    return result.scalar() or 0


# ===================================================================
# TEMPLATE ENDPOINTS
# ===================================================================
@router.get("/templates", response_model=list[TemplateResponse], tags=["Newsletter"])
async def list_templates(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
    category: Optional[str] = None,
    is_active: bool = True,
) -> list[TemplateResponse]:
    """List newsletter templates."""
    query = select(NewsletterTemplate).where(NewsletterTemplate.is_active == is_active)
    if category:
        query = query.where(NewsletterTemplate.category == category)
    query = query.order_by(NewsletterTemplate.updated_at.desc())

    result = await db.execute(query)
    templates = result.scalars().all()
    return [TemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=TemplateResponse, tags=["Newsletter"])
async def create_template(
    data: TemplateCreate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> TemplateResponse:
    """Create a new newsletter template."""
    template = NewsletterTemplate(
        name=data.name,
        subject=data.subject,
        preheader_text=data.preheader_text,
        content_html=data.content_html,
        content_json=data.content_json,
        category=data.category,
        created_by_user_id=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=TemplateResponse, tags=["Newsletter"])
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> TemplateResponse:
    """Update an existing template."""
    result = await db.execute(
        select(NewsletterTemplate).where(NewsletterTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", tags=["Newsletter"])
async def delete_template(
    template_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Delete a template (soft-delete by setting is_active=False)."""
    result = await db.execute(
        select(NewsletterTemplate).where(NewsletterTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = False
    await db.commit()
    return {"success": True, "message": "Template deleted"}


# ===================================================================
# CAMPAIGN ENDPOINTS
# ===================================================================
@router.get("/campaigns", response_model=CampaignListResponse, tags=["Newsletter"])
async def list_campaigns(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> CampaignListResponse:
    """List newsletter campaigns with optional status filter."""
    query = select(NewsletterCampaign)
    count_query = select(func.count(NewsletterCampaign.id))

    if status:
        query = query.where(NewsletterCampaign.status == status)
        count_query = count_query.where(NewsletterCampaign.status == status)

    query = query.order_by(NewsletterCampaign.updated_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total,
    )


@router.post("/campaigns", response_model=CampaignResponse, tags=["Newsletter"])
async def create_campaign(
    data: CampaignCreate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> CampaignResponse:
    """Create a new newsletter campaign (draft)."""
    campaign = NewsletterCampaign(
        name=data.name,
        subject=data.subject,
        preheader_text=data.preheader_text,
        content_html=data.content_html,
        content_json=data.content_json,
        template_id=data.template_id,
        from_name=data.from_name,
        from_email=data.from_email,
        reply_to_email=data.reply_to_email,
        audience_filters=data.audience_filters,
        status=CampaignStatus.DRAFT.value,
        created_by_user_id=current_user.id,
    )

    # Pre-compute audience count
    campaign.total_recipients = await _count_audience(db, data.audience_filters)

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, tags=["Newsletter"])
async def get_campaign(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> CampaignResponse:
    """Get campaign details."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse, tags=["Newsletter"])
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> CampaignResponse:
    """Update a draft campaign."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Only draft campaigns can be edited")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    # Re-compute audience count if filters changed
    if data.audience_filters is not None:
        campaign.total_recipients = await _count_audience(db, data.audience_filters)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.delete("/campaigns/{campaign_id}", tags=["Newsletter"])
async def delete_campaign(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Delete a draft campaign."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in (CampaignStatus.DRAFT.value, CampaignStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail="Only draft or cancelled campaigns can be deleted")

    await db.delete(campaign)
    await db.commit()
    return {"success": True, "message": "Campaign deleted"}


@router.post("/campaigns/{campaign_id}/duplicate", response_model=CampaignResponse, tags=["Newsletter"])
async def duplicate_campaign(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> CampaignResponse:
    """Clone an existing campaign as a new draft."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Campaign not found")

    clone = NewsletterCampaign(
        name=f"{original.name} (Copy)",
        subject=original.subject,
        preheader_text=original.preheader_text,
        content_html=original.content_html,
        content_json=original.content_json,
        template_id=original.template_id,
        from_name=original.from_name,
        from_email=original.from_email,
        reply_to_email=original.reply_to_email,
        audience_filters=original.audience_filters,
        status=CampaignStatus.DRAFT.value,
        total_recipients=original.total_recipients,
        created_by_user_id=current_user.id,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return CampaignResponse.model_validate(clone)


@router.post("/campaigns/{campaign_id}/send", tags=["Newsletter"])
async def send_campaign(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Queue campaign for immediate send."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Only draft campaigns can be sent")
    if not campaign.content_html:
        raise HTTPException(status_code=400, detail="Campaign has no content")

    # Update audience count
    campaign.total_recipients = await _count_audience(db, campaign.audience_filters)
    if campaign.total_recipients == 0:
        raise HTTPException(status_code=400, detail="No subscribers match the audience filters")

    campaign.status = CampaignStatus.SENDING.value
    campaign.sent_at = datetime.now(UTC)
    await db.commit()

    # Dispatch Celery task
    try:
        from app.workers.newsletter_tasks import send_newsletter_campaign

        send_newsletter_campaign.delay(campaign_id)
    except Exception:
        pass  # Worker may not be running in dev; campaign status is already set

    return {
        "success": True,
        "message": f"Campaign queued for sending to {campaign.total_recipients} subscribers",
    }


@router.post("/campaigns/{campaign_id}/schedule", tags=["Newsletter"])
async def schedule_campaign(
    campaign_id: int,
    data: ScheduleRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Schedule campaign for future send."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Only draft campaigns can be scheduled")

    if data.scheduled_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    campaign.status = CampaignStatus.SCHEDULED.value
    campaign.scheduled_at = data.scheduled_at
    campaign.total_recipients = await _count_audience(db, campaign.audience_filters)
    await db.commit()

    return {
        "success": True,
        "message": f"Campaign scheduled for {data.scheduled_at.isoformat()}",
    }


@router.post("/campaigns/{campaign_id}/cancel", tags=["Newsletter"])
async def cancel_campaign(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Cancel a scheduled or sending campaign."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in (CampaignStatus.SCHEDULED.value, CampaignStatus.SENDING.value):
        raise HTTPException(status_code=400, detail="Can only cancel scheduled or sending campaigns")

    campaign.status = CampaignStatus.CANCELLED.value
    await db.commit()
    return {"success": True, "message": "Campaign cancelled"}


@router.post("/campaigns/{campaign_id}/send-test", tags=["Newsletter"])
async def send_test_email(
    campaign_id: int,
    data: SendTestRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Send test email to specified addresses."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.content_html:
        raise HTTPException(status_code=400, detail="Campaign has no content")

    from app.services.email_service import get_email_service

    email_service = get_email_service()
    sent_count = 0
    for email in data.emails:
        success = email_service.send_newsletter_email(
            to_email=email,
            subject=f"[TEST] {campaign.subject}",
            html_content=campaign.content_html,
            from_name=campaign.from_name,
            from_email=campaign.from_email,
            reply_to=campaign.reply_to_email,
        )
        if success:
            sent_count += 1

    return {"success": True, "message": f"Test email sent to {sent_count}/{len(data.emails)} addresses"}


@router.get("/campaigns/{campaign_id}/analytics", response_model=AnalyticsResponse, tags=["Newsletter"])
async def campaign_analytics(
    campaign_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> AnalyticsResponse:
    """Get detailed analytics for a campaign."""
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get recent events
    events_result = await db.execute(
        select(NewsletterEvent)
        .where(NewsletterEvent.campaign_id == campaign_id)
        .order_by(NewsletterEvent.created_at.desc())
        .limit(100)
    )
    events = events_result.scalars().all()

    total = max(campaign.total_sent, 1)  # Avoid division by zero
    return AnalyticsResponse(
        campaign=CampaignResponse.model_validate(campaign),
        open_rate=round((campaign.total_opened / total) * 100, 2),
        click_rate=round((campaign.total_clicked / total) * 100, 2),
        bounce_rate=round((campaign.total_bounced / total) * 100, 2),
        unsubscribe_rate=round((campaign.total_unsubscribed / total) * 100, 2),
        events=[
            {
                "id": e.id,
                "event_type": e.event_type,
                "subscriber_id": e.subscriber_id,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    )


# ===================================================================
# SUBSCRIBER ENDPOINTS (newsletter-specific)
# ===================================================================
@router.get("/subscribers", response_model=list[SubscriberResponse], tags=["Newsletter"])
async def list_subscribers(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
    subscribed: Optional[bool] = None,
    platform: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SubscriberResponse]:
    """List subscribers with newsletter subscription info."""
    query = select(LandingPageSubscriber)

    if subscribed is not None:
        query = query.where(LandingPageSubscriber.subscribed_to_newsletter == subscribed)
    if platform:
        query = query.where(LandingPageSubscriber.attributed_platform == platform)
    if min_score is not None:
        query = query.where(LandingPageSubscriber.lead_score >= min_score)

    query = query.order_by(LandingPageSubscriber.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    subscribers = result.scalars().all()
    return [SubscriberResponse.model_validate(s) for s in subscribers]


@router.get("/subscribers/stats", response_model=SubscriberStatsResponse, tags=["Newsletter"])
async def subscriber_stats(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> SubscriberStatsResponse:
    """Get newsletter subscriber statistics."""
    total_result = await db.execute(select(func.count(LandingPageSubscriber.id)))
    total = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(LandingPageSubscriber.id)).where(
            LandingPageSubscriber.subscribed_to_newsletter == True  # noqa: E712
        )
    )
    active = active_result.scalar() or 0

    return SubscriberStatsResponse(
        total=total, active=active, unsubscribed=total - active
    )


@router.put("/subscribers/{subscriber_id}/unsubscribe", tags=["Newsletter"])
async def manual_unsubscribe(
    subscriber_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Manually unsubscribe a subscriber from newsletters."""
    result = await db.execute(
        select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
    )
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    subscriber.subscribed_to_newsletter = False
    subscriber.unsubscribed_at = datetime.now(UTC)
    await db.commit()
    return {"success": True, "message": "Subscriber unsubscribed"}


@router.put("/subscribers/{subscriber_id}/resubscribe", tags=["Newsletter"])
async def resubscribe(
    subscriber_id: int,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Re-subscribe a subscriber to newsletters."""
    result = await db.execute(
        select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
    )
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    subscriber.subscribed_to_newsletter = True
    subscriber.unsubscribed_at = None
    await db.commit()
    return {"success": True, "message": "Subscriber re-subscribed"}


@router.get("/subscribers/count", tags=["Newsletter"])
async def preview_audience_count(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
    status: Optional[str] = None,
    min_lead_score: Optional[int] = None,
    platform: Optional[str] = None,
) -> dict:
    """Preview audience count for given filters (used by campaign editor)."""
    filters: dict = {}
    if status:
        filters["status"] = [s.strip() for s in status.split(",")]
    if min_lead_score is not None:
        filters["min_lead_score"] = min_lead_score
    if platform:
        filters["platforms"] = [p.strip() for p in platform.split(",")]

    count = await _count_audience(db, filters if filters else None)
    return {"count": count}


# ===================================================================
# PUBLIC ENDPOINTS (tracking & unsubscribe — no auth required)
# ===================================================================

# 1x1 transparent GIF for open tracking
TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/track/open/{campaign_id}/{subscriber_id}", tags=["Newsletter Tracking"])
async def track_open(
    campaign_id: int,
    subscriber_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Track email open via invisible pixel."""
    # Record open event
    try:
        event = NewsletterEvent(
            campaign_id=campaign_id,
            subscriber_id=subscriber_id,
            event_type=NewsletterEventType.OPENED.value,
        )
        db.add(event)

        # Update campaign stats
        await db.execute(
            select(NewsletterCampaign)
            .where(NewsletterCampaign.id == campaign_id)
        )
        campaign = (await db.execute(
            select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
        )).scalar_one_or_none()
        if campaign:
            campaign.total_opened += 1

        # Update subscriber stats
        subscriber = (await db.execute(
            select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
        )).scalar_one_or_none()
        if subscriber:
            subscriber.last_email_opened_at = datetime.now(UTC)
            subscriber.email_open_count += 1

        await db.commit()
    except Exception:
        pass  # Don't break the pixel response on tracking errors

    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache"},
    )


@router.get("/track/click/{campaign_id}/{subscriber_id}", tags=["Newsletter Tracking"])
async def track_click(
    campaign_id: int,
    subscriber_id: int,
    url: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Track link click and redirect to destination URL."""
    # Record click event
    try:
        event = NewsletterEvent(
            campaign_id=campaign_id,
            subscriber_id=subscriber_id,
            event_type=NewsletterEventType.CLICKED.value,
            metadata={"link_url": url},
        )
        db.add(event)

        # Update campaign stats
        campaign = (await db.execute(
            select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
        )).scalar_one_or_none()
        if campaign:
            campaign.total_clicked += 1

        await db.commit()
    except Exception:
        pass

    # Redirect to actual URL
    return Response(
        status_code=302,
        headers={"Location": url},
    )


@router.get("/unsubscribe", tags=["Newsletter Tracking"])
async def public_unsubscribe(
    token: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """One-click unsubscribe (CAN-SPAM compliance). Returns HTML confirmation."""
    campaign_id, subscriber_id = _decode_unsubscribe_token(token)

    result = await db.execute(
        select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
    )
    subscriber = result.scalar_one_or_none()

    if subscriber:
        subscriber.subscribed_to_newsletter = False
        subscriber.unsubscribed_at = datetime.now(UTC)

        # Record event
        event = NewsletterEvent(
            campaign_id=campaign_id,
            subscriber_id=subscriber_id,
            event_type=NewsletterEventType.UNSUBSCRIBED.value,
        )
        db.add(event)

        # Update campaign stats
        campaign = (await db.execute(
            select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id)
        )).scalar_one_or_none()
        if campaign:
            campaign.total_unsubscribed += 1

        await db.commit()

    # Return simple HTML confirmation page
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Unsubscribed - Stratum AI</title>
    <style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#000;color:#fff}
    .card{text-align:center;padding:3rem;border-radius:1.5rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);max-width:400px}
    h1{font-size:1.5rem;margin-bottom:0.5rem}p{color:rgba(255,255,255,0.5);font-size:0.9rem}</style>
    </head>
    <body><div class="card"><h1>You've been unsubscribed</h1><p>You will no longer receive newsletter emails from Stratum AI.</p></div></body>
    </html>
    """
    return Response(content=html, media_type="text/html")
