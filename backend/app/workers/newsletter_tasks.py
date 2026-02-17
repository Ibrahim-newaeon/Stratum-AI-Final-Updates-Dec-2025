# =============================================================================
# Stratum AI - Newsletter Worker Tasks
# =============================================================================
"""
Celery tasks for sending newsletter campaigns.

- send_newsletter_campaign: Batch-sends emails for a campaign
- process_scheduled_campaigns: Beat-scheduled task to dispatch due campaigns
"""

import base64
import re
import time
from datetime import datetime, UTC

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, and_

logger = get_task_logger(__name__)

BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 1  # Delay between batches to avoid SMTP throttling


def _personalize_html(
    html: str,
    subscriber_email: str,
    subscriber_name: str | None,
    subscriber_company: str | None,
) -> str:
    """Replace template variables in email HTML."""
    html = html.replace("{{email}}", subscriber_email)
    html = html.replace("{{first_name}}", (subscriber_name or "").split(" ")[0] or "there")
    html = html.replace("{{full_name}}", subscriber_name or "")
    html = html.replace("{{company_name}}", subscriber_company or "")
    return html


def _inject_tracking(
    html: str,
    campaign_id: int,
    subscriber_id: int,
    api_base_url: str,
) -> str:
    """Inject open tracking pixel and rewrite links for click tracking."""
    # Open tracking pixel (before </body>)
    pixel_url = f"{api_base_url}/api/v1/newsletter/track/open/{campaign_id}/{subscriber_id}"
    pixel_tag = f'<img src="{pixel_url}" width="1" height="1" style="display:none" alt="" />'

    if "</body>" in html:
        html = html.replace("</body>", f"{pixel_tag}</body>")
    else:
        html += pixel_tag

    # Click tracking: rewrite <a href="..."> links
    def rewrite_link(match: re.Match) -> str:
        href = match.group(1)
        # Skip mailto:, tel:, and tracking URLs
        if href.startswith(("mailto:", "tel:", "#")) or "/newsletter/track/" in href:
            return match.group(0)
        from urllib.parse import quote

        tracked_url = (
            f"{api_base_url}/api/v1/newsletter/track/click/"
            f"{campaign_id}/{subscriber_id}?url={quote(href, safe='')}"
        )
        return f'href="{tracked_url}"'

    html = re.sub(r'href="([^"]+)"', rewrite_link, html)

    return html


def _add_unsubscribe_footer(
    html: str,
    unsubscribe_url: str,
) -> str:
    """Add CAN-SPAM compliant unsubscribe footer."""
    footer = f"""
    <div style="margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.1);text-align:center;font-size:12px;color:#86868b;">
        <p>You received this because you subscribed at stratumai.app</p>
        <p>&copy; {datetime.now().year} Stratum AI &bull;
        <a href="{unsubscribe_url}" style="color:#00c7be;text-decoration:underline;">Unsubscribe</a></p>
    </div>
    """

    if "</body>" in html:
        html = html.replace("</body>", f"{footer}</body>")
    else:
        html += footer

    return html


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_newsletter_campaign(self, campaign_id: int) -> dict:
    """
    Send a newsletter campaign to all matching subscribers.

    This task:
    1. Loads the campaign and validates status
    2. Queries matching subscribers
    3. Batch-sends personalized emails with tracking
    4. Updates campaign stats on completion

    Idempotent via status checks — safe to retry.
    """
    from app.core.config import settings
    from app.db.session import SyncSessionLocal
    from app.base_models import LandingPageSubscriber
    from app.models.newsletter import (
        CampaignStatus,
        NewsletterCampaign,
        NewsletterEvent,
        NewsletterEventType,
    )
    from app.services.email_service import get_email_service

    db = SyncSessionLocal()
    email_service = get_email_service()
    api_base_url = settings.frontend_url.rstrip("/")

    try:
        # Load campaign
        campaign = db.query(NewsletterCampaign).filter_by(id=campaign_id).first()
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return {"error": "Campaign not found"}

        if campaign.status not in (CampaignStatus.SENDING.value, CampaignStatus.SCHEDULED.value):
            logger.warning(f"Campaign {campaign_id} status is {campaign.status}, skipping")
            return {"error": f"Campaign status is {campaign.status}"}

        # Set status to sending
        campaign.status = CampaignStatus.SENDING.value
        if not campaign.sent_at:
            campaign.sent_at = datetime.now(UTC)
        db.commit()

        # Build subscriber query with audience filters
        query = db.query(LandingPageSubscriber).filter(
            LandingPageSubscriber.subscribed_to_newsletter == True  # noqa: E712
        )

        filters = campaign.audience_filters or {}
        if "status" in filters and filters["status"]:
            query = query.filter(LandingPageSubscriber.status.in_(filters["status"]))
        if "min_lead_score" in filters:
            query = query.filter(LandingPageSubscriber.lead_score >= filters["min_lead_score"])
        if "platforms" in filters and filters["platforms"]:
            query = query.filter(
                LandingPageSubscriber.attributed_platform.in_(filters["platforms"])
            )

        subscribers = query.all()
        total_recipients = len(subscribers)
        campaign.total_recipients = total_recipients
        db.commit()

        logger.info(f"Sending campaign {campaign_id} to {total_recipients} subscribers")

        sent_count = 0
        bounced_count = 0

        for i, subscriber in enumerate(subscribers):
            # Check if campaign was cancelled mid-send
            if i % BATCH_SIZE == 0 and i > 0:
                db.refresh(campaign)
                if campaign.status == CampaignStatus.CANCELLED.value:
                    logger.info(f"Campaign {campaign_id} was cancelled, stopping send")
                    break
                time.sleep(BATCH_DELAY_SECONDS)

            # Generate unsubscribe token & URL
            token = base64.urlsafe_b64encode(
                f"{campaign_id}:{subscriber.id}".encode()
            ).decode()
            unsubscribe_url = f"{api_base_url}/api/v1/newsletter/unsubscribe?token={token}"

            # Personalize HTML
            html = _personalize_html(
                campaign.content_html,
                subscriber.email,
                subscriber.full_name,
                subscriber.company_name,
            )

            # Inject tracking pixel + click tracking
            html = _inject_tracking(html, campaign_id, subscriber.id, api_base_url)

            # Add unsubscribe footer
            html = _add_unsubscribe_footer(html, unsubscribe_url)

            # Send email
            success = email_service.send_newsletter_email(
                to_email=subscriber.email,
                subject=campaign.subject,
                html_content=html,
                from_name=campaign.from_name,
                from_email=campaign.from_email,
                reply_to=campaign.reply_to_email,
                unsubscribe_url=unsubscribe_url,
            )

            # Record event
            event_type = NewsletterEventType.SENT.value if success else NewsletterEventType.BOUNCED.value
            event = NewsletterEvent(
                campaign_id=campaign_id,
                subscriber_id=subscriber.id,
                event_type=event_type,
            )
            db.add(event)

            if success:
                sent_count += 1
                subscriber.last_email_sent_at = datetime.now(UTC)
                subscriber.email_send_count += 1
            else:
                bounced_count += 1

            # Commit every batch
            if (i + 1) % BATCH_SIZE == 0:
                campaign.total_sent = sent_count
                campaign.total_bounced = bounced_count
                db.commit()

        # Final update
        campaign.total_sent = sent_count
        campaign.total_delivered = sent_count  # SMTP delivery = success for now
        campaign.total_bounced = bounced_count
        campaign.status = CampaignStatus.SENT.value
        campaign.completed_at = datetime.now(UTC)
        db.commit()

        logger.info(
            f"Campaign {campaign_id} completed: {sent_count} sent, {bounced_count} bounced"
        )

        return {
            "campaign_id": campaign_id,
            "total_recipients": total_recipients,
            "sent": sent_count,
            "bounced": bounced_count,
        }

    except Exception as exc:
        logger.error(f"Error sending campaign {campaign_id}: {exc}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def process_scheduled_campaigns(self) -> dict:
    """
    Beat-scheduled task: Check for campaigns due for sending.

    Runs every minute. Dispatches send_newsletter_campaign for each
    campaign where status='scheduled' and scheduled_at <= now.
    """
    from app.db.session import SyncSessionLocal
    from app.models.newsletter import CampaignStatus, NewsletterCampaign

    db = SyncSessionLocal()
    try:
        due_campaigns = (
            db.query(NewsletterCampaign)
            .filter(
                NewsletterCampaign.status == CampaignStatus.SCHEDULED.value,
                NewsletterCampaign.scheduled_at <= datetime.now(UTC),
            )
            .all()
        )

        dispatched = []
        for campaign in due_campaigns:
            campaign.status = CampaignStatus.SENDING.value
            campaign.sent_at = datetime.now(UTC)
            db.commit()

            send_newsletter_campaign.delay(campaign.id)
            dispatched.append(campaign.id)
            logger.info(f"Dispatched scheduled campaign {campaign.id}")

        return {"dispatched": dispatched, "count": len(dispatched)}

    except Exception as exc:
        logger.error(f"Error processing scheduled campaigns: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
