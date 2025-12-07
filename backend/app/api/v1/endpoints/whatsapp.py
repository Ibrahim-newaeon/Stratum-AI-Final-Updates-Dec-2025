# =============================================================================
# Stratum AI - WhatsApp Integration Endpoints
# =============================================================================
"""
WhatsApp Business API integration endpoints.
Implements Module G: WhatsApp Messaging.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import (
    WhatsAppContact,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppMessageStatus,
    WhatsAppOptInStatus,
    WhatsAppTemplate,
    WhatsAppTemplateCategory,
    WhatsAppTemplateStatus,
)
from app.schemas import APIResponse, PaginatedResponse

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Schemas for WhatsApp
# =============================================================================
class WhatsAppContactCreate(BaseModel):
    phone_number: str = Field(..., description="Phone number in E.164 format")
    country_code: str = Field(..., max_length=5)
    display_name: Optional[str] = None
    opt_in_method: str = Field(default="web_form")


class WhatsAppContactResponse(BaseModel):
    id: int
    phone_number: str
    country_code: str
    display_name: Optional[str]
    is_verified: bool
    opt_in_status: str
    wa_id: Optional[str]
    profile_name: Optional[str]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WhatsAppTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    language: str = Field(default="en", max_length=10)
    category: WhatsAppTemplateCategory
    header_type: Optional[str] = None
    header_content: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = Field(None, max_length=60)
    header_variables: List[str] = []
    body_variables: List[str] = []
    buttons: List[dict] = []


class WhatsAppTemplateResponse(BaseModel):
    id: int
    name: str
    language: str
    category: str
    body_text: str
    status: str
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class WhatsAppMessageSend(BaseModel):
    contact_id: int
    message_type: str = Field(..., description="template, text, image, document")
    template_name: Optional[str] = None
    template_variables: dict = {}
    content: Optional[str] = None
    media_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class WhatsAppMessageResponse(BaseModel):
    id: int
    contact_id: int
    direction: str
    message_type: str
    status: str
    content: Optional[str]
    template_name: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WhatsAppConversationResponse(BaseModel):
    id: int
    contact_id: int
    origin_type: str
    pricing_category: Optional[str]
    started_at: datetime
    expires_at: datetime
    message_count: int
    is_active: bool

    class Config:
        from_attributes = True


# =============================================================================
# Contact Endpoints
# =============================================================================
@router.get("/contacts", response_model=APIResponse[PaginatedResponse[WhatsAppContactResponse]])
async def list_contacts(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    opt_in_status: Optional[WhatsAppOptInStatus] = None,
    search: Optional[str] = None,
):
    """List WhatsApp contacts with filtering and pagination."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(WhatsAppContact).where(
        WhatsAppContact.tenant_id == tenant_id,
        WhatsAppContact.is_active == True,
    )

    if opt_in_status:
        query = query.where(WhatsAppContact.opt_in_status == opt_in_status)
    if search:
        query = query.where(
            (WhatsAppContact.phone_number.ilike(f"%{search}%")) |
            (WhatsAppContact.display_name.ilike(f"%{search}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(WhatsAppContact.created_at.desc())

    result = await db.execute(query)
    contacts = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[WhatsAppContactResponse.model_validate(c) for c in contacts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.post("/contacts", response_model=APIResponse[WhatsAppContactResponse])
async def create_contact(
    request: Request,
    contact_data: WhatsAppContactCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Add a new WhatsApp contact."""
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    # Check for duplicate phone number
    existing = await db.execute(
        select(WhatsAppContact).where(
            WhatsAppContact.tenant_id == tenant_id,
            WhatsAppContact.phone_number == contact_data.phone_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this phone number already exists",
        )

    contact = WhatsAppContact(
        tenant_id=tenant_id,
        user_id=user_id,
        phone_number=contact_data.phone_number,
        country_code=contact_data.country_code,
        display_name=contact_data.display_name,
        opt_in_method=contact_data.opt_in_method,
    )

    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    logger.info(f"Created WhatsApp contact {contact.id} for tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=WhatsAppContactResponse.model_validate(contact),
        message="Contact created successfully",
    )


@router.post("/contacts/{contact_id}/verify", response_model=APIResponse)
async def verify_contact(
    request: Request,
    contact_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Send verification code to contact."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(WhatsAppContact).where(
            WhatsAppContact.id == contact_id,
            WhatsAppContact.tenant_id == tenant_id,
        )
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Generate 6-digit verification code
    import secrets
    verification_code = str(secrets.randbelow(900000) + 100000)

    contact.verification_code = verification_code
    contact.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    await db.commit()

    # TODO: Send verification code via WhatsApp API
    logger.info(f"Verification code generated for contact {contact_id}")

    return APIResponse(
        success=True,
        message="Verification code sent",
    )


@router.post("/contacts/{contact_id}/opt-in", response_model=APIResponse[WhatsAppContactResponse])
async def opt_in_contact(
    request: Request,
    contact_id: int,
    method: str = Query(default="web_form"),
    db: AsyncSession = Depends(get_async_session),
):
    """Opt-in a contact for WhatsApp messages."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(WhatsAppContact).where(
            WhatsAppContact.id == contact_id,
            WhatsAppContact.tenant_id == tenant_id,
        )
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.opt_in_status = WhatsAppOptInStatus.OPTED_IN
    contact.opt_in_at = datetime.now(timezone.utc)
    contact.opt_in_method = method

    await db.commit()
    await db.refresh(contact)

    logger.info(f"Contact {contact_id} opted in via {method}")

    return APIResponse(
        success=True,
        data=WhatsAppContactResponse.model_validate(contact),
        message="Contact opted in successfully",
    )


@router.post("/contacts/{contact_id}/opt-out", response_model=APIResponse)
async def opt_out_contact(
    request: Request,
    contact_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Opt-out a contact from WhatsApp messages."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(WhatsAppContact).where(
            WhatsAppContact.id == contact_id,
            WhatsAppContact.tenant_id == tenant_id,
        )
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.opt_in_status = WhatsAppOptInStatus.OPTED_OUT
    contact.opt_out_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(f"Contact {contact_id} opted out")

    return APIResponse(success=True, message="Contact opted out successfully")


# =============================================================================
# Template Endpoints
# =============================================================================
@router.get("/templates", response_model=APIResponse[PaginatedResponse[WhatsAppTemplateResponse]])
async def list_templates(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[WhatsAppTemplateStatus] = None,
    category: Optional[WhatsAppTemplateCategory] = None,
):
    """List WhatsApp message templates."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(WhatsAppTemplate).where(WhatsAppTemplate.tenant_id == tenant_id)

    if status:
        query = query.where(WhatsAppTemplate.status == status)
    if category:
        query = query.where(WhatsAppTemplate.category == category)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(WhatsAppTemplate.created_at.desc())

    result = await db.execute(query)
    templates = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[WhatsAppTemplateResponse.model_validate(t) for t in templates],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.post("/templates", response_model=APIResponse[WhatsAppTemplateResponse])
async def create_template(
    request: Request,
    template_data: WhatsAppTemplateCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new message template (will be submitted to Meta for approval)."""
    tenant_id = getattr(request.state, "tenant_id", None)

    template = WhatsAppTemplate(
        tenant_id=tenant_id,
        name=template_data.name,
        language=template_data.language,
        category=template_data.category,
        header_type=template_data.header_type,
        header_content=template_data.header_content,
        body_text=template_data.body_text,
        footer_text=template_data.footer_text,
        header_variables=template_data.header_variables,
        body_variables=template_data.body_variables,
        buttons=template_data.buttons,
        status=WhatsAppTemplateStatus.PENDING,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    # TODO: Submit to Meta Business Manager API for approval
    logger.info(f"Created WhatsApp template {template.id} for tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=WhatsAppTemplateResponse.model_validate(template),
        message="Template created and submitted for approval",
    )


# =============================================================================
# Message Endpoints
# =============================================================================
@router.post("/messages/send", response_model=APIResponse[WhatsAppMessageResponse])
async def send_message(
    request: Request,
    message_data: WhatsAppMessageSend,
    db: AsyncSession = Depends(get_async_session),
):
    """Queue a WhatsApp message for sending."""
    tenant_id = getattr(request.state, "tenant_id", None)

    # Verify contact exists and is opted in
    contact_result = await db.execute(
        select(WhatsAppContact).where(
            WhatsAppContact.id == message_data.contact_id,
            WhatsAppContact.tenant_id == tenant_id,
        )
    )
    contact = contact_result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.opt_in_status != WhatsAppOptInStatus.OPTED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact has not opted in to receive messages",
        )

    # Create message record
    message = WhatsAppMessage(
        tenant_id=tenant_id,
        contact_id=message_data.contact_id,
        message_type=message_data.message_type,
        template_name=message_data.template_name,
        template_variables=message_data.template_variables,
        content=message_data.content,
        media_url=message_data.media_url,
        scheduled_at=message_data.scheduled_at,
        status=WhatsAppMessageStatus.PENDING,
    )

    db.add(message)

    # Update contact stats
    contact.message_count += 1
    contact.last_message_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)

    # TODO: Queue for async sending via Celery worker
    logger.info(f"Queued WhatsApp message {message.id} for contact {contact.id}")

    return APIResponse(
        success=True,
        data=WhatsAppMessageResponse.model_validate(message),
        message="Message queued for sending",
    )


@router.get("/messages", response_model=APIResponse[PaginatedResponse[WhatsAppMessageResponse]])
async def list_messages(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    contact_id: Optional[int] = None,
    status: Optional[WhatsAppMessageStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List WhatsApp messages with filtering."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(WhatsAppMessage).where(WhatsAppMessage.tenant_id == tenant_id)

    if contact_id:
        query = query.where(WhatsAppMessage.contact_id == contact_id)
    if status:
        query = query.where(WhatsAppMessage.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(WhatsAppMessage.created_at.desc())

    result = await db.execute(query)
    messages = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[WhatsAppMessageResponse.model_validate(m) for m in messages],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/messages/{message_id}", response_model=APIResponse[WhatsAppMessageResponse])
async def get_message(
    request: Request,
    message_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get message details and delivery status."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(WhatsAppMessage).where(
            WhatsAppMessage.id == message_id,
            WhatsAppMessage.tenant_id == tenant_id,
        )
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return APIResponse(
        success=True,
        data=WhatsAppMessageResponse.model_validate(message),
    )


# =============================================================================
# Webhook Endpoint
# =============================================================================
@router.post("/webhooks/status")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Webhook endpoint for WhatsApp status updates from Meta."""
    # TODO: Verify webhook signature from Meta
    body = await request.json()

    # Process status updates
    if "entry" in body:
        for entry in body["entry"]:
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    statuses = change.get("value", {}).get("statuses", [])
                    for status_update in statuses:
                        wamid = status_update.get("id")
                        new_status = status_update.get("status")
                        timestamp = status_update.get("timestamp")

                        # Update message status
                        result = await db.execute(
                            select(WhatsAppMessage).where(WhatsAppMessage.wamid == wamid)
                        )
                        message = result.scalar_one_or_none()

                        if message:
                            message.status = new_status
                            ts = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)

                            if new_status == "sent":
                                message.sent_at = ts
                            elif new_status == "delivered":
                                message.delivered_at = ts
                            elif new_status == "read":
                                message.read_at = ts

                            # Update status history
                            history = message.status_history or []
                            history.append({"status": new_status, "timestamp": ts.isoformat()})
                            message.status_history = history

                            await db.commit()
                            logger.info(f"Updated message {wamid} status to {new_status}")

    return {"status": "received"}


@router.get("/webhooks/verify")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
):
    """Verify webhook subscription from Meta."""
    from app.core.config import settings

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified")
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


# =============================================================================
# Conversation Endpoints
# =============================================================================
@router.get("/conversations", response_model=APIResponse[PaginatedResponse[WhatsAppConversationResponse]])
async def list_conversations(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    contact_id: Optional[int] = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List WhatsApp conversations (24-hour windows)."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(WhatsAppConversation).where(WhatsAppConversation.tenant_id == tenant_id)

    if contact_id:
        query = query.where(WhatsAppConversation.contact_id == contact_id)
    if active_only:
        query = query.where(
            WhatsAppConversation.is_active == True,
            WhatsAppConversation.expires_at > datetime.now(timezone.utc),
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(WhatsAppConversation.started_at.desc())

    result = await db.execute(query)
    conversations = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[WhatsAppConversationResponse.model_validate(c) for c in conversations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )
