# =============================================================================
# Stratum AI - WhatsApp Messaging Tasks
# =============================================================================
"""
Background tasks for WhatsApp Business API messaging.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import (
    WhatsAppContact,
    WhatsAppMessage,
    WhatsAppMessageStatus,
    WhatsAppTemplate,
)

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_whatsapp_message(
    self,
    tenant_id: int,
    message_id: int,
    contact_phone: Optional[str] = None,
    message_type: Optional[str] = None,
    template_name: Optional[str] = None,
    template_variables: Optional[dict] = None,
    content: Optional[str] = None,
    media_url: Optional[str] = None,
):
    """
    Send a WhatsApp message that the API layer has already persisted.

    The send endpoint creates the ``WhatsAppMessage`` row (status PENDING) and
    dispatches this task with its ``message_id``; the task loads that row,
    sends it via the Graph API, and records the result. It does NOT create a
    new message (that would double-write and diverged the kwargs/columns).

    Args:
        tenant_id: Tenant ID for isolation.
        message_id: Existing WhatsAppMessage row to send.
        contact_phone: Recipient E.164 number (falls back to the contact row).
        message_type: "template" or "text" (falls back to the row's value).
        template_name / template_variables / content / media_url: send payload,
            each falling back to the persisted row when not supplied.
    """
    logger.info(f"Sending WhatsApp message {message_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        message = db.get(WhatsAppMessage, message_id)
        if message is None or message.tenant_id != tenant_id:
            logger.error(
                f"WhatsApp message {message_id} not found for tenant {tenant_id}"
            )
            return {"status": "message_not_found"}

        # Resolve recipient phone (prefer the passed value, else the contact row).
        phone = contact_phone
        if not phone and message.contact_id:
            contact = db.get(WhatsAppContact, message.contact_id)
            phone = contact.phone_number if contact else None
        if not phone:
            message.status = WhatsAppMessageStatus.FAILED
            message.error_message = "No recipient phone number"
            db.commit()
            return {"status": "no_recipient"}

        m_type = message_type or message.message_type
        tmpl_name = template_name or message.template_name
        tmpl_vars = (
            template_variables
            if template_variables is not None
            else message.template_variables
        )
        body = content or message.content
        media = media_url or message.media_url

        try:
            wamid = _send_via_client(
                db=db,
                tenant_id=tenant_id,
                phone=phone,
                message_type=m_type,
                template_name=tmpl_name,
                template_variables=tmpl_vars,
                content=body,
                media_url=media,
            )

            message.wamid = wamid
            message.status = WhatsAppMessageStatus.SENT
            message.sent_at = datetime.now(UTC)
            db.commit()

            logger.info(f"WhatsApp message {message_id} sent: {wamid}")
            return {"status": "sent", "message_id": message_id, "wamid": wamid}

        except Exception as e:
            message.status = WhatsAppMessageStatus.FAILED
            message.error_message = str(e)[:500]
            db.commit()
            logger.error(f"WhatsApp send failed for message {message_id}: {e}")
            raise


# Explicit name: this module was split out of the old app/workers/tasks.py;
# without it the auto-generated name gains the submodule segment and the
# beat schedule's task reference silently dispatches to nothing.
@shared_task(name="app.workers.tasks.process_scheduled_whatsapp_messages")
def process_scheduled_whatsapp_messages():
    """
    Process scheduled WhatsApp messages.
    Scheduled every minute by Celery beat.
    """
    logger.info("Processing scheduled WhatsApp messages")

    with SyncSessionLocal() as db:
        now = datetime.now(UTC)

        # Get pending scheduled messages
        messages = (
            db.execute(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.status == WhatsAppMessageStatus.PENDING,
                    WhatsAppMessage.scheduled_at <= now,
                    WhatsAppMessage.scheduled_at.isnot(None),
                )
            )
            .scalars()
            .all()
        )

        task_count = 0
        for message in messages:
            send_whatsapp_message.delay(
                tenant_id=message.tenant_id,
                message_id=message.id,
                contact_phone=message.contact.phone_number if message.contact else None,
                message_type=message.message_type,
                template_name=message.template_name,
                template_variables=message.template_variables,
                content=message.content,
                media_url=message.media_url,
            )
            task_count += 1

    logger.info(f"Queued {task_count} scheduled WhatsApp messages")
    return {"queued": task_count}


# Explicit name so the endpoint's ``from app.workers.tasks import
# send_whatsapp_broadcast`` (which previously ImportError'd — the task never
# existed) resolves and dispatches correctly.
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="app.workers.tasks.send_whatsapp_broadcast",
)
def send_whatsapp_broadcast(
    self,
    tenant_id: int,
    template_name: str,
    template_variables: Optional[dict] = None,
    contact_ids: Optional[list] = None,
):
    """
    Fan a template broadcast out to per-contact sends.

    The broadcast endpoint already created one PENDING ``WhatsAppMessage`` per
    opted-in contact; this task finds each and dispatches ``send_whatsapp_message``
    so every message goes through the same single-send path (status tracking,
    retries, wamid capture).
    """
    contact_ids = contact_ids or []
    dispatched = 0

    with SyncSessionLocal() as db:
        for contact_id in contact_ids:
            message = (
                db.execute(
                    select(WhatsAppMessage)
                    .where(
                        WhatsAppMessage.tenant_id == tenant_id,
                        WhatsAppMessage.contact_id == contact_id,
                        WhatsAppMessage.template_name == template_name,
                        WhatsAppMessage.status == WhatsAppMessageStatus.PENDING,
                    )
                    .order_by(WhatsAppMessage.id.desc())
                )
                .scalars()
                .first()
            )
            if message is None:
                logger.warning(
                    f"Broadcast: no pending message for contact {contact_id}"
                )
                continue

            contact = db.get(WhatsAppContact, contact_id)
            send_whatsapp_message.delay(
                tenant_id=tenant_id,
                message_id=message.id,
                contact_phone=contact.phone_number if contact else None,
                message_type="template",
                template_name=template_name,
                template_variables=template_variables,
            )
            dispatched += 1

    logger.info(f"Broadcast dispatched {dispatched} of {len(contact_ids)} messages")
    return {"dispatched": dispatched, "requested": len(contact_ids)}


def _build_template_components(
    template: WhatsAppTemplate,
    variables: Optional[dict],
    media_url: Optional[str],
) -> list:
    """Build WhatsApp template components from variables."""
    components = []

    if media_url and template.header_type in ("image", "video", "document"):
        components.append(
            {
                "type": "header",
                "parameters": [{"type": template.header_type, "url": media_url}],
            }
        )

    if variables:
        body_params = [{"type": "text", "text": str(v)} for v in variables.values()]
        if body_params:
            components.append({"type": "body", "parameters": body_params})

    return components


def _extract_wamid(result: Any) -> Optional[str]:
    """Pull the WhatsApp message id (wamid) out of a Graph API send response."""
    if not isinstance(result, dict):
        return None
    if result.get("message_id"):
        return result["message_id"]
    messages = result.get("messages") or []
    if messages:
        return messages[0].get("id")
    return None


def _send_via_client(
    *,
    db,
    tenant_id: int,
    phone: str,
    message_type: Optional[str],
    template_name: Optional[str],
    template_variables: Optional[dict],
    content: Optional[str],
    media_url: Optional[str],
) -> Optional[str]:
    """Send one message through the Graph client and return its wamid.

    Template sends (the only ones valid outside the 24h window) are preferred
    when a template name is present; otherwise a plain text send is used. The
    client is pure HTTP, so ``asyncio.run`` from this sync task is safe.
    """
    from app.services.whatsapp_client import get_whatsapp_client

    client = get_whatsapp_client()

    if template_name:
        template = db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.tenant_id == tenant_id,
                WhatsAppTemplate.name == template_name,
            )
        ).scalar_one_or_none()
        language = template.language if template else "en"
        components = (
            _build_template_components(template, template_variables, media_url)
            if template
            else None
        )
        result = asyncio.run(
            client.send_template_message(
                recipient_phone=phone,
                template_name=template_name,
                language_code=language,
                components=components,
            )
        )
    else:
        result = asyncio.run(
            client.send_text_message(recipient_phone=phone, text=content or "")
        )

    return _extract_wamid(result)
