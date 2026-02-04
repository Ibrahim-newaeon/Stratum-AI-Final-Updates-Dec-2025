# =============================================================================
# Stratum AI - Landing Page CMS Endpoints
# =============================================================================
"""
Landing Page CMS endpoints for multi-language content management
and subscriber collection from marketing campaign landing pages.

Features:
- Full UTM tracking (source, medium, campaign, term, content)
- Platform-specific click IDs (fbclid, gclid, ttclid, sccid)
- Lead scoring based on data completeness
- Platform attribution detection
- CAPI integration for conversion feedback to ad platforms
- Admin endpoints for subscriber management
"""

import csv
import hashlib
import io
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.base_models import LandingPageSubscriber, SubscriberStatus
from app.db.session import get_async_session

logger = logging.getLogger("stratum.landing_cms")

router = APIRouter(prefix="/landing-cms")

# =============================================================================
# Configuration
# =============================================================================
ADMIN_API_KEY = os.getenv("STRATUM_ADMIN_API_KEY", "change_me_in_production")


# =============================================================================
# Authentication
# =============================================================================
security = HTTPBearer(auto_error=False)


async def verify_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    """Verify admin API token for protected endpoints."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


# =============================================================================
# Schemas
# =============================================================================
class SubscriberCreate(BaseModel):
    """Schema for creating a new landing page subscriber from marketing campaigns."""

    # Contact Information
    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")

    # Source tracking
    source_page: str = Field("landing", max_length=50, description="Source page identifier")
    language: str = Field("en", max_length=10, description="Language code")

    # UTM tracking (works for all platforms)
    utm_source: Optional[str] = Field(
        None, max_length=100, description="UTM source (facebook, google, tiktok, snapchat)"
    )
    utm_medium: Optional[str] = Field(
        None, max_length=100, description="UTM medium (cpc, cpm, social)"
    )
    utm_campaign: Optional[str] = Field(None, max_length=100, description="UTM campaign name")
    utm_term: Optional[str] = Field(None, max_length=100, description="UTM term (keyword)")
    utm_content: Optional[str] = Field(
        None, max_length=100, description="UTM content (ad variation)"
    )
    referrer_url: Optional[str] = Field(None, max_length=500)
    landing_url: Optional[str] = Field(
        None, max_length=1000, description="Landing page URL with params"
    )

    # Platform-specific click IDs (CRITICAL for conversion attribution)
    fbclid: Optional[str] = Field(None, max_length=255, description="Meta/Facebook click ID")
    gclid: Optional[str] = Field(None, max_length=255, description="Google click ID")
    ttclid: Optional[str] = Field(None, max_length=255, description="TikTok click ID")
    sccid: Optional[str] = Field(None, max_length=255, description="Snapchat click ID (ScCid)")

    # Meta browser/cookie IDs
    fbc: Optional[str] = Field(None, max_length=255, description="Meta browser cookie (fb.1.xxx)")
    fbp: Optional[str] = Field(None, max_length=255, description="Meta pixel cookie (_fbp)")


class SubscriberResponse(BaseModel):
    """Response after successful subscription."""

    success: bool
    message: str
    subscriber_id: Optional[int] = None
    lead_score: Optional[int] = None
    attributed_platform: Optional[str] = None


class SubscriberListItem(BaseModel):
    """Subscriber item for list responses."""

    id: int
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    phone: Optional[str]
    source_page: str
    language: str
    status: str
    lead_score: int
    attributed_platform: Optional[str]
    utm_source: Optional[str]
    utm_campaign: Optional[str]
    capi_sent: bool
    created_at: datetime


class SubscriberStats(BaseModel):
    """Statistics about subscribers."""

    total_subscribers: int
    subscribers_today: int
    subscribers_this_week: int
    subscribers_this_month: int
    by_status: dict[str, int]
    by_platform: dict[str, int]
    by_utm_source: dict[str, int]
    by_language: dict[str, int]
    average_lead_score: float
    capi_sent_count: int


# =============================================================================
# Helper Functions
# =============================================================================
def hash_email(email: str) -> str:
    """Hash email for deduplication."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def detect_platform(
    fbclid: Optional[str] = None,
    gclid: Optional[str] = None,
    ttclid: Optional[str] = None,
    sccid: Optional[str] = None,
    fbc: Optional[str] = None,
    utm_source: Optional[str] = None,
) -> str:
    """
    Detect which ad platform the lead came from based on click IDs and UTM.

    Priority: Click ID > UTM Source > Organic
    """
    # Check click IDs first (most reliable)
    if fbclid or fbc:
        return "meta"
    if gclid:
        return "google"
    if ttclid:
        return "tiktok"
    if sccid:
        return "snapchat"

    # Fall back to UTM source
    utm_src = (utm_source or "").lower()
    if utm_src in ("facebook", "fb", "instagram", "ig", "meta"):
        return "meta"
    if utm_src in ("google", "gads", "youtube", "yt"):
        return "google"
    if utm_src in ("tiktok", "tt"):
        return "tiktok"
    if utm_src in ("snapchat", "snap", "sc"):
        return "snapchat"

    return "organic"


def calculate_lead_score(
    full_name: Optional[str] = None,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    has_click_id: bool = False,
    has_utm: bool = False,
) -> int:
    """
    Calculate lead quality score (0-100) based on data completeness.

    Higher score = more valuable lead = better for lookalike audiences.
    """
    score = 20  # Email is required, so baseline

    if full_name:
        score += 15
    if company_name:
        score += 20  # Indicates B2B intent
    if phone:
        score += 25  # High value for follow-up
    if has_click_id:
        score += 10  # Better attribution
    if has_utm:
        score += 10  # Trackable

    return min(score, 100)


async def send_conversion_to_platforms(subscriber_id: int, platform: str) -> dict[str, Any]:
    """
    Send 'Lead' conversion event to ad platforms via CAPI.

    This runs as a background task after the subscriber is created.
    """
    results = {}

    try:
        async with get_async_session() as session:
            result = await session.execute(
                select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
            )
            subscriber = result.scalar_one_or_none()

            if not subscriber:
                return {"error": "Subscriber not found"}

            # Try to import and use the events API
            try:
                from app.services.capi.platform_connectors import (
                    MetaCAPIConnector,
                    SnapchatCAPIConnector,
                    TikTokCAPIConnector,
                )

                # Build user data
                user_data = {
                    "email": subscriber.email,
                    "phone": subscriber.phone,
                    "external_id": str(subscriber.id),
                    "fbc": subscriber.fbc or subscriber.fbclid,
                    "fbp": subscriber.fbp,
                    "client_ip_address": subscriber.ip_address,
                    "client_user_agent": subscriber.user_agent,
                }

                # Send to appropriate platform
                if platform == "meta":
                    pixel_id = os.getenv("META_PIXEL_ID")
                    access_token = os.getenv("META_ACCESS_TOKEN")
                    if pixel_id and access_token:
                        connector = MetaCAPIConnector(pixel_id, access_token)
                        result = await connector.send_lead_event(
                            user_data=user_data,
                            event_source_url=subscriber.landing_url,
                            custom_data={
                                "lead_type": "landing_page_signup",
                                "utm_source": subscriber.utm_source,
                                "utm_campaign": subscriber.utm_campaign,
                            },
                        )
                        results["meta"] = result

                elif platform == "tiktok":
                    pixel_id = os.getenv("TIKTOK_PIXEL_ID")
                    access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
                    if pixel_id and access_token:
                        connector = TikTokCAPIConnector(pixel_id, access_token)
                        result = await connector.send_lead_event(
                            user_data=user_data,
                            event_source_url=subscriber.landing_url,
                        )
                        results["tiktok"] = result

                elif platform == "snapchat":
                    pixel_id = os.getenv("SNAPCHAT_PIXEL_ID")
                    access_token = os.getenv("SNAPCHAT_ACCESS_TOKEN")
                    if pixel_id and access_token:
                        connector = SnapchatCAPIConnector(pixel_id, access_token)
                        result = await connector.send_lead_event(
                            user_data=user_data,
                            event_source_url=subscriber.landing_url,
                        )
                        results["snapchat"] = result

                # Update subscriber with CAPI results
                subscriber.capi_sent = True
                subscriber.capi_results = json.dumps(results)
                subscriber.updated_at = datetime.now(UTC)
                await session.commit()

                logger.info(f"CAPI sent for lead {subscriber_id}: {results}")

            except ImportError:
                logger.warning("CAPI connectors not available, skipping conversion send")
                results["error"] = "CAPI connectors not available"

    except Exception as e:
        logger.error(f"CAPI error for subscriber {subscriber_id}: {e}")
        results["error"] = str(e)

    return results


# =============================================================================
# Public Endpoints (No Authentication Required)
# =============================================================================
@router.get("/health")
async def landing_cms_health():
    """Health check for Landing CMS module."""
    return {"status": "healthy", "module": "landing_cms"}


@router.post("/subscribe", response_model=SubscriberResponse)
async def create_subscriber(
    subscriber_data: SubscriberCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle new lead signup from marketing campaign landing page.

    This endpoint:
    1. Stores the lead with full attribution (UTM + click IDs)
    2. Detects which ad platform drove the lead
    3. Calculates lead quality score
    4. Sends conversion event to ad platforms (CAPI) in background
    5. Returns success response immediately

    Click ID Parameters (captured from URL):
    - fbclid: Meta/Facebook
    - gclid: Google Ads
    - ttclid: TikTok
    - sccid/ScCid: Snapchat
    """
    async with get_async_session() as session:
        # Check if email already exists
        existing = await session.execute(
            select(LandingPageSubscriber).where(
                LandingPageSubscriber.email == subscriber_data.email.lower()
            )
        )
        if existing.scalar_one_or_none():
            # Don't reveal that email exists (privacy)
            return SubscriberResponse(
                success=True,
                message="Thank you for your interest! We'll be in touch soon.",
            )

        # Get client IP and user agent
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]

        # Detect platform
        attributed_platform = detect_platform(
            fbclid=subscriber_data.fbclid,
            gclid=subscriber_data.gclid,
            ttclid=subscriber_data.ttclid,
            sccid=subscriber_data.sccid,
            fbc=subscriber_data.fbc,
            utm_source=subscriber_data.utm_source,
        )

        # Calculate lead score
        has_click_id = any(
            [
                subscriber_data.fbclid,
                subscriber_data.gclid,
                subscriber_data.ttclid,
                subscriber_data.sccid,
            ]
        )
        has_utm = bool(subscriber_data.utm_source and subscriber_data.utm_campaign)
        lead_score = calculate_lead_score(
            full_name=subscriber_data.full_name,
            company_name=subscriber_data.company_name,
            phone=subscriber_data.phone,
            has_click_id=has_click_id,
            has_utm=has_utm,
        )

        # Create new subscriber
        subscriber = LandingPageSubscriber(
            email=subscriber_data.email.lower(),
            email_hash=hash_email(subscriber_data.email),
            full_name=subscriber_data.full_name,
            company_name=subscriber_data.company_name,
            phone=subscriber_data.phone,
            source_page=subscriber_data.source_page,
            language=subscriber_data.language,
            # UTM tracking
            utm_source=subscriber_data.utm_source,
            utm_medium=subscriber_data.utm_medium,
            utm_campaign=subscriber_data.utm_campaign,
            utm_term=subscriber_data.utm_term,
            utm_content=subscriber_data.utm_content,
            referrer_url=subscriber_data.referrer_url,
            landing_url=subscriber_data.landing_url,
            # Platform click IDs
            fbclid=subscriber_data.fbclid,
            gclid=subscriber_data.gclid,
            ttclid=subscriber_data.ttclid,
            sccid=subscriber_data.sccid,
            fbc=subscriber_data.fbc,
            fbp=subscriber_data.fbp,
            # Derived fields
            attributed_platform=attributed_platform,
            lead_score=lead_score,
            # Status and metadata
            status=SubscriberStatus.PENDING.value,
            ip_address=client_ip,
            user_agent=user_agent,
            capi_sent=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        try:
            session.add(subscriber)
            await session.commit()
            await session.refresh(subscriber)

            logger.info(
                f"New lead: {subscriber_data.email} | "
                f"Platform: {attributed_platform} | "
                f"Campaign: {subscriber_data.utm_campaign} | "
                f"Score: {lead_score}"
            )

            # Send CAPI conversion in background (if not organic)
            if attributed_platform != "organic":
                background_tasks.add_task(
                    send_conversion_to_platforms, subscriber.id, attributed_platform
                )

            return SubscriberResponse(
                success=True,
                message="Thank you for signing up! Check your email frequently - we'll send your access credentials soon.",
                subscriber_id=subscriber.id,
                lead_score=lead_score,
                attributed_platform=attributed_platform,
            )
        except IntegrityError:
            await session.rollback()
            # Email already exists (race condition)
            return SubscriberResponse(
                success=True,
                message="Thank you for your interest! We'll be in touch soon.",
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating subscriber: {e}")
            raise HTTPException(
                status_code=500,
                detail="An error occurred while processing your request. Please try again.",
            )


# Alias endpoint for /lead (same as /subscribe)
@router.post("/lead", response_model=SubscriberResponse)
async def capture_lead(
    subscriber_data: SubscriberCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Alias for /subscribe - capture lead from marketing campaign."""
    return await create_subscriber(subscriber_data, request, background_tasks)


# =============================================================================
# Admin Endpoints (Require Authentication)
# =============================================================================
@router.get("/subscribers")
async def list_subscribers(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: bool = Depends(verify_admin_token),
):
    """
    List all subscribers (admin only).

    Requires Authorization header with admin API key.
    """
    async with get_async_session() as session:
        query = select(LandingPageSubscriber)

        if status:
            query = query.where(LandingPageSubscriber.status == status)
        if platform:
            query = query.where(LandingPageSubscriber.attributed_platform == platform)

        query = query.order_by(LandingPageSubscriber.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        subscribers = result.scalars().all()

        return {
            "subscribers": [
                SubscriberListItem(
                    id=s.id,
                    email=s.email,
                    full_name=s.full_name,
                    company_name=s.company_name,
                    phone=s.phone,
                    source_page=s.source_page,
                    language=s.language,
                    status=s.status,
                    lead_score=s.lead_score,
                    attributed_platform=s.attributed_platform,
                    utm_source=s.utm_source,
                    utm_campaign=s.utm_campaign,
                    capi_sent=s.capi_sent,
                    created_at=s.created_at,
                ).dict()
                for s in subscribers
            ],
            "total": len(subscribers),
            "limit": limit,
            "offset": offset,
        }


@router.get("/stats", response_model=SubscriberStats)
async def get_stats(_: bool = Depends(verify_admin_token)):
    """
    Get subscriber statistics (admin only).

    Returns counts by status, platform, UTM source, etc.
    """
    async with get_async_session() as session:
        # Get all subscribers for calculations
        result = await session.execute(select(LandingPageSubscriber))
        subscribers = result.scalars().all()

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        # Initialize counters
        today_count = 0
        week_count = 0
        month_count = 0
        by_status: dict[str, int] = {}
        by_platform: dict[str, int] = {}
        by_utm_source: dict[str, int] = {}
        by_language: dict[str, int] = {}
        total_lead_score = 0
        capi_sent_count = 0

        for s in subscribers:
            # Time-based counts
            if s.created_at >= today_start:
                today_count += 1
            if s.created_at >= week_start:
                week_count += 1
            if s.created_at >= month_start:
                month_count += 1

            # By status
            by_status[s.status] = by_status.get(s.status, 0) + 1

            # By platform
            platform = s.attributed_platform or "unknown"
            by_platform[platform] = by_platform.get(platform, 0) + 1

            # By UTM source
            utm_src = s.utm_source or "direct"
            by_utm_source[utm_src] = by_utm_source.get(utm_src, 0) + 1

            # By language
            by_language[s.language] = by_language.get(s.language, 0) + 1

            # Lead score
            total_lead_score += s.lead_score

            # CAPI
            if s.capi_sent:
                capi_sent_count += 1

        total = len(subscribers)
        avg_lead_score = (total_lead_score / total) if total > 0 else 0.0

        return SubscriberStats(
            total_subscribers=total,
            subscribers_today=today_count,
            subscribers_this_week=week_count,
            subscribers_this_month=month_count,
            by_status=by_status,
            by_platform=by_platform,
            by_utm_source=by_utm_source,
            by_language=by_language,
            average_lead_score=round(avg_lead_score, 2),
            capi_sent_count=capi_sent_count,
        )


@router.post("/export")
async def export_subscribers(
    format: str = Query("csv", pattern="^(csv|json)$"),
    _: bool = Depends(verify_admin_token),
):
    """
    Export subscribers as CSV or JSON (admin only).
    """
    async with get_async_session() as session:
        result = await session.execute(
            select(LandingPageSubscriber).order_by(LandingPageSubscriber.created_at.desc())
        )
        subscribers = result.scalars().all()

        if format == "json":
            return {
                "subscribers": [
                    {
                        "id": s.id,
                        "email": s.email,
                        "full_name": s.full_name,
                        "company_name": s.company_name,
                        "phone": s.phone,
                        "source_page": s.source_page,
                        "language": s.language,
                        "status": s.status,
                        "lead_score": s.lead_score,
                        "attributed_platform": s.attributed_platform,
                        "utm_source": s.utm_source,
                        "utm_medium": s.utm_medium,
                        "utm_campaign": s.utm_campaign,
                        "utm_term": s.utm_term,
                        "utm_content": s.utm_content,
                        "fbclid": s.fbclid,
                        "gclid": s.gclid,
                        "ttclid": s.ttclid,
                        "sccid": s.sccid,
                        "capi_sent": s.capi_sent,
                        "referrer_url": s.referrer_url,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in subscribers
                ],
                "exported_at": datetime.now(UTC).isoformat(),
                "total": len(subscribers),
            }

        # CSV export
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "id",
                "email",
                "full_name",
                "company_name",
                "phone",
                "status",
                "lead_score",
                "attributed_platform",
                "source_page",
                "language",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "fbclid",
                "gclid",
                "ttclid",
                "sccid",
                "capi_sent",
                "referrer_url",
                "created_at",
            ]
        )

        # Data rows
        for s in subscribers:
            writer.writerow(
                [
                    s.id,
                    s.email,
                    s.full_name,
                    s.company_name,
                    s.phone,
                    s.status,
                    s.lead_score,
                    s.attributed_platform,
                    s.source_page,
                    s.language,
                    s.utm_source,
                    s.utm_medium,
                    s.utm_campaign,
                    s.utm_term,
                    s.utm_content,
                    s.fbclid,
                    s.gclid,
                    s.ttclid,
                    s.sccid,
                    s.capi_sent,
                    s.referrer_url,
                    s.created_at.isoformat(),
                ]
            )

        csv_content = output.getvalue()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=subscribers_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
            },
        )


@router.put("/subscribers/{subscriber_id}/status")
async def update_subscriber_status(
    subscriber_id: int,
    status: str,
    _: bool = Depends(verify_admin_token),
):
    """
    Update subscriber status (admin only).

    Valid statuses: pending, verified, active, rejected, converted
    """
    valid_statuses = ["pending", "verified", "active", "rejected", "converted"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    async with get_async_session() as session:
        result = await session.execute(
            select(LandingPageSubscriber).where(LandingPageSubscriber.id == subscriber_id)
        )
        subscriber = result.scalar_one_or_none()

        if not subscriber:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        subscriber.status = status
        subscriber.updated_at = datetime.now(UTC)

        if status == "verified":
            subscriber.verified_at = datetime.now(UTC)
        elif status == "converted":
            subscriber.converted_at = datetime.now(UTC)

        await session.commit()

        return {"success": True, "subscriber_id": subscriber_id, "new_status": status}
