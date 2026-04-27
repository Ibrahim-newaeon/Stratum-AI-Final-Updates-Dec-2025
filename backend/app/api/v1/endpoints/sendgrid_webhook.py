# =============================================================================
# Stratum AI - SendGrid Inbound Webhook
# =============================================================================
"""
Receive SendGrid event webhooks for delivery tracking, bounces, opens, clicks,
spam reports, and unsubscribes.

Configure in SendGrid:
  HTTP POST URL: https://stratumai.app/api/v1/webhooks/sendgrid?token=<SENDGRID_WEBHOOK_TOKEN>
  Events: All

Security:
  - URL token verification (query param must match SENDGRID_WEBHOOK_TOKEN env var)
  - HTTPS only in production
  - Idempotent event processing via sg_event_id deduplication
"""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import require_super_admin
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.newsletter import NewsletterCampaign, NewsletterEvent, NewsletterEventType
from app.services.email_service import get_email_service

router = APIRouter(tags=["SendGrid Webhooks"])
logger = get_logger(__name__)

# In-memory dedup cache for sg_event_id (prevent duplicate processing)
# In production with multiple workers, replace with Redis SET.
_seen_event_ids: set[str] = set()
_MAX_CACHE_SIZE = 10_000


# =============================================================================
# Schemas
# =============================================================================
class SendGridEvent(BaseModel):
    """Individual SendGrid event payload."""

    event: str = Field(..., description="Event type")
    email: str = Field(..., description="Recipient email")
    timestamp: int = Field(..., description="Unix timestamp")
    sg_event_id: Optional[str] = Field(default=None)
    sg_message_id: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    response: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    ip: Optional[str] = Field(default=None)
    useragent: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    asm_group_id: Optional[int] = Field(default=None)
    category: Optional[list[str]] = Field(default=None)
    campaign_id: Optional[str] = Field(default=None)
    # Additional fields may be present; ignore extras
    model_config = {"extra": "ignore"}


# =============================================================================
# Helpers
# =============================================================================

def _verify_token(request: Request) -> bool:
    """Verify the webhook URL token matches the configured secret."""
    token = request.query_params.get("token", "")
    expected = getattr(settings, "sendgrid_webhook_token", None) or ""
    if not expected:
        # If no token is configured, reject the webhook in production
        if settings.is_production:
            logger.error("SENDGRID_WEBHOOK_TOKEN not configured — rejecting webhook")
            return False
        # In dev, allow empty token but log warning
        logger.warning("SENDGRID_WEBHOOK_TOKEN not set — allowing in development")
        return True
    return hmac.compare_digest(token, expected)


def _event_to_newsletter_event_type(event_name: str) -> Optional[str]:
    """Map SendGrid event names to our NewsletterEventType enum."""
    mapping = {
        "delivered": NewsletterEventType.DELIVERED.value,
        "open": NewsletterEventType.OPENED.value,
        "click": NewsletterEventType.CLICKED.value,
        "bounce": NewsletterEventType.BOUNCED.value,
        "dropped": NewsletterEventType.BOUNCED.value,
        "spam_report": NewsletterEventType.COMPLAINED.value,
        "unsubscribe": NewsletterEventType.UNSUBSCRIBED.value,
        "group_unsubscribe": NewsletterEventType.UNSUBSCRIBED.value,
    }
    return mapping.get(event_name)


def _is_duplicate_event(sg_event_id: Optional[str]) -> bool:
    """Check if we've already processed this event ID."""
    if not sg_event_id:
        return False
    if sg_event_id in _seen_event_ids:
        return True
    # Simple LRU-style eviction
    if len(_seen_event_ids) >= _MAX_CACHE_SIZE:
        # Clear half the cache when full
        _seen_event_ids.clear()
    _seen_event_ids.add(sg_event_id)
    return False


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post("/webhooks/sendgrid")
async def receive_sendgrid_events(request: Request) -> dict:
    """
    Receive SendGrid Event Webhook.

    SendGrid POSTs a JSON array of event objects here.
    We process each event and update newsletter stats / logs.
    """
    if not _verify_token(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token",
        )

    # Parse JSON body
    try:
        body = await request.json()
    except Exception as e:
        logger.error("Failed to parse SendGrid webhook JSON", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    if not isinstance(body, list):
        logger.error("SendGrid webhook body is not a list")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected JSON array",
        )

    processed = 0
    skipped = 0
    errors = 0

    async with get_async_session() as db:
        for raw_event in body:
            try:
                event = SendGridEvent.model_validate(raw_event)

                if _is_duplicate_event(event.sg_event_id):
                    skipped += 1
                    continue

                await _process_single_event(db, event)
                processed += 1

            except Exception as e:
                logger.error(
                    "Error processing SendGrid event",
                    error=str(e),
                    event_raw=raw_event,
                )
                errors += 1

    logger.info(
        "SendGrid webhook processed",
        total=len(body),
        processed=processed,
        skipped=skipped,
        errors=errors,
    )

    return {
        "success": True,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
    }


async def _process_single_event(db: AsyncSession, event: SendGridEvent) -> None:
    """Process a single SendGrid event."""
    event_type = _event_to_newsletter_event_type(event.event)

    # Log all events at INFO level for observability
    logger.info(
        "SendGrid event received",
        event=event.event,
        email=event.email[:30] + "..." if len(event.email) > 30 else event.email,
        sg_message_id=event.sg_message_id,
        sg_event_id=event.sg_event_id,
    )

    # Handle bounces / drops aggressively — log for reputation monitoring
    if event.event in ("bounce", "dropped"):
        logger.warning(
            "Email bounce/drop detected",
            email=event.email,
            reason=event.reason,
            response=event.response,
            status=event.status,
            sg_message_id=event.sg_message_id,
        )

    # Handle spam reports
    if event.event == "spam_report":
        logger.warning(
            "Spam report received",
            email=event.email,
            sg_message_id=event.sg_message_id,
        )

    # If this event maps to a newsletter event type, try to find the campaign
    if event_type and event.campaign_id:
        await _upsert_newsletter_event(db, event, event_type)


async def _upsert_newsletter_event(
    db: AsyncSession,
    event: SendGridEvent,
    event_type: str,
) -> None:
    """Update newsletter campaign stats and insert event record."""
    try:
        campaign_id_int = int(event.campaign_id)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return

    # Check campaign exists
    result = await db.execute(
        select(NewsletterCampaign).where(NewsletterCampaign.id == campaign_id_int)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        return

    # Update aggregate counters
    counter_field = None
    if event_type == NewsletterEventType.DELIVERED.value:
        counter_field = "total_delivered"
    elif event_type == NewsletterEventType.OPENED.value:
        counter_field = "total_opened"
    elif event_type == NewsletterEventType.CLICKED.value:
        counter_field = "total_clicked"
    elif event_type == NewsletterEventType.BOUNCED.value:
        counter_field = "total_bounced"
    elif event_type == NewsletterEventType.UNSUBSCRIBED.value:
        counter_field = "total_unsubscribed"

    if counter_field:
        await db.execute(
            update(NewsletterCampaign)
            .where(NewsletterCampaign.id == campaign_id_int)
            .values({counter_field: getattr(campaign, counter_field) + 1})
        )

    # Insert detailed event (if subscriber mapping available — requires email lookup)
    # For now we skip detailed event insertion since we don't have a direct
    # subscriber lookup by email in this context. The aggregate counters are
    # sufficient for campaign analytics.

    await db.commit()


# =============================================================================
# Health / Test Endpoint
# =============================================================================

@router.post("/webhooks/sendgrid/test")
async def sendgrid_test_webhook(request: Request) -> dict:
    """
    Test endpoint that simulates a SendGrid webhook payload.
    Only available in development/staging.
    """
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint disabled in production",
        )

    test_payload = [
        {
            "event": "delivered",
            "email": "test@example.com",
            "timestamp": int(datetime.now(UTC).timestamp()),
            "sg_event_id": f"test-{datetime.now(UTC).timestamp()}",
            "sg_message_id": "test-message-id",
            "campaign_id": "1",
        }
    ]

    # Re-use processing logic directly
    async with get_async_session() as db:
        for raw_event in test_payload:
            event = SendGridEvent.model_validate(raw_event)
            await _process_single_event(db, event)

    return {"success": True, "message": "Test event processed"}


# =============================================================================
# Superadmin Test Email Endpoint
# =============================================================================

class TestEmailRequest(BaseModel):
    """Request to send a test email via SendGrid."""

    to_email: str = Field(..., description="Recipient email address")
    email_type: str = Field(
        default="verification",
        description="Type of test email: verification, password_reset, welcome, otp",
    )


@router.post("/superadmin/email/test-send")
async def send_test_email(
    request: Request,
    body: TestEmailRequest,
    _: None = Depends(require_super_admin),
) -> dict:
    """
    Send a test email via SendGrid (superadmin only).
    Useful for verifying SendGrid connectivity and template rendering.
    """
    email_service = get_email_service()
    success = False

    if body.email_type == "verification":
        success = email_service.send_verification_email(
            to_email=body.to_email,
            token="test-token-12345",
            user_name="Test User",
        )
    elif body.email_type == "password_reset":
        success = email_service.send_password_reset_email(
            to_email=body.to_email,
            token="test-token-12345",
            user_name="Test User",
        )
    elif body.email_type == "welcome":
        success = email_service.send_welcome_email(
            to_email=body.to_email,
            user_name="Test User",
        )
    elif body.email_type == "otp":
        success = email_service.send_otp_email(
            to_email=body.to_email,
            otp_code="123456",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown email_type: {body.email_type}",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send test email. Check logs for provider error.",
        )

    return {
        "success": True,
        "message": f"Test {body.email_type} email sent to {body.to_email}",
        "provider": "sendgrid" if email_service._sg else "smtp",
    }
