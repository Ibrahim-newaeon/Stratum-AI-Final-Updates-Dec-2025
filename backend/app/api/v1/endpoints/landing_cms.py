# =============================================================================
# Stratum AI - Landing Page CMS Endpoints
# =============================================================================
"""
Landing Page CMS endpoints for multi-language content management
and subscriber collection from landing pages.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_async_session
from app.base_models import LandingPageSubscriber, SubscriberStatus

router = APIRouter(prefix="/landing-cms")


# =============================================================================
# Schemas
# =============================================================================
class SubscriberCreate(BaseModel):
    """Schema for creating a new landing page subscriber."""

    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    source_page: str = Field("landing", max_length=50, description="Source page identifier")
    language: str = Field("en", max_length=10, description="Language code")
    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=100)
    referrer_url: Optional[str] = Field(None, max_length=500)


class SubscriberResponse(BaseModel):
    """Response after successful subscription."""

    success: bool
    message: str
    subscriber_id: Optional[int] = None


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
):
    """
    Register a new subscriber from the landing page.

    This endpoint is public and does not require authentication.
    It collects email signups for superadmin review.
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

        # Create new subscriber
        subscriber = LandingPageSubscriber(
            email=subscriber_data.email.lower(),
            full_name=subscriber_data.full_name,
            company_name=subscriber_data.company_name,
            source_page=subscriber_data.source_page,
            language=subscriber_data.language,
            utm_source=subscriber_data.utm_source,
            utm_medium=subscriber_data.utm_medium,
            utm_campaign=subscriber_data.utm_campaign,
            referrer_url=subscriber_data.referrer_url,
            status=SubscriberStatus.PENDING.value,
            ip_address=client_ip,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        try:
            session.add(subscriber)
            await session.commit()
            await session.refresh(subscriber)

            return SubscriberResponse(
                success=True,
                message="Thank you for signing up! Check your email frequently - we'll send your access credentials soon.",
                subscriber_id=subscriber.id,
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
            raise HTTPException(
                status_code=500,
                detail="An error occurred while processing your request. Please try again."
            )
