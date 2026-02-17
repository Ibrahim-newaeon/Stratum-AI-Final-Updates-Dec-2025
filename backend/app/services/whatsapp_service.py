# =============================================================================
# Stratum AI - WhatsApp Service
# =============================================================================
"""
WhatsApp Business API service layer for contact management,
template handling, and message operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models import (
    WhatsAppContact,
    WhatsAppTemplate,
    WhatsAppMessage,
    WhatsAppConversation,
    WhatsAppOptInStatus,
    WhatsAppMessageStatus,
)


class WhatsAppService:
    """Service for WhatsApp messaging operations."""

    # -------------------------------------------------------------------------
    # Contact Operations
    # -------------------------------------------------------------------------

    @staticmethod
    async def get_contacts(
        db: AsyncSession,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        opt_in_status: Optional[str] = None,
    ) -> List[WhatsAppContact]:
        """Get tenant's WhatsApp contacts with optional filtering."""
        query = select(WhatsAppContact).where(
            WhatsAppContact.tenant_id == tenant_id
        )
        if opt_in_status:
            query = query.where(WhatsAppContact.opt_in_status == opt_in_status)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_contact_by_id(
        db: AsyncSession, contact_id: int, tenant_id: int
    ) -> Optional[WhatsAppContact]:
        """Get a specific contact by ID."""
        result = await db.execute(
            select(WhatsAppContact).where(
                WhatsAppContact.id == contact_id,
                WhatsAppContact.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_contact_by_phone(
        db: AsyncSession, phone_number: str, tenant_id: int
    ) -> Optional[WhatsAppContact]:
        """Get a contact by phone number."""
        result = await db.execute(
            select(WhatsAppContact).where(
                WhatsAppContact.phone_number == phone_number,
                WhatsAppContact.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_contact(
        db: AsyncSession, contact_data: Dict[str, Any]
    ) -> WhatsAppContact:
        """Add a new WhatsApp contact."""
        contact = WhatsAppContact(**contact_data)
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def verify_contact(
        db: AsyncSession, contact_id: int, tenant_id: int
    ) -> bool:
        """Mark contact as verified (phone number confirmed)."""
        contact = await WhatsAppService.get_contact_by_id(db, contact_id, tenant_id)
        if contact:
            contact.is_verified = True
            contact.verified_at = datetime.utcnow()
            await db.commit()
            return True
        return False

    @staticmethod
    async def opt_in_contact(
        db: AsyncSession,
        contact_id: int,
        tenant_id: int,
        method: str = "web_form",
    ) -> bool:
        """Opt-in a contact for WhatsApp messages."""
        contact = await WhatsAppService.get_contact_by_id(db, contact_id, tenant_id)
        if contact:
            contact.opt_in_status = WhatsAppOptInStatus.OPTED_IN
            contact.opt_in_at = datetime.utcnow()
            contact.opt_in_method = method
            await db.commit()
            return True
        return False

    @staticmethod
    async def opt_out_contact(
        db: AsyncSession, contact_id: int, tenant_id: int
    ) -> bool:
        """Opt-out a contact from WhatsApp messages."""
        contact = await WhatsAppService.get_contact_by_id(db, contact_id, tenant_id)
        if contact:
            contact.opt_in_status = WhatsAppOptInStatus.OPTED_OUT
            contact.opt_out_at = datetime.utcnow()
            await db.commit()
            return True
        return False

    # -------------------------------------------------------------------------
    # Template Operations
    # -------------------------------------------------------------------------

    @staticmethod
    async def get_templates(
        db: AsyncSession,
        tenant_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[WhatsAppTemplate]:
        """Get WhatsApp message templates with optional filtering."""
        query = select(WhatsAppTemplate).where(
            WhatsAppTemplate.tenant_id == tenant_id
        )
        if status:
            query = query.where(WhatsAppTemplate.status == status)
        if category:
            query = query.where(WhatsAppTemplate.category == category)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_template_by_id(
        db: AsyncSession, template_id: int, tenant_id: int
    ) -> Optional[WhatsAppTemplate]:
        """Get a specific template by ID."""
        result = await db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.id == template_id,
                WhatsAppTemplate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_template_by_name(
        db: AsyncSession, name: str, tenant_id: int
    ) -> Optional[WhatsAppTemplate]:
        """Get a template by name."""
        result = await db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.name == name,
                WhatsAppTemplate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_template(
        db: AsyncSession, template_data: Dict[str, Any]
    ) -> WhatsAppTemplate:
        """Create a new message template."""
        template = WhatsAppTemplate(**template_data)
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    @staticmethod
    async def update_template_status(
        db: AsyncSession,
        template_id: int,
        tenant_id: int,
        status: str,
        meta_template_id: Optional[str] = None,
    ) -> bool:
        """Update template status (after Meta approval/rejection)."""
        template = await WhatsAppService.get_template_by_id(
            db, template_id, tenant_id
        )
        if template:
            template.status = status
            if meta_template_id:
                template.meta_template_id = meta_template_id
            await db.commit()
            return True
        return False

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------

    @staticmethod
    async def send_message(
        db: AsyncSession, message_data: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Queue a WhatsApp message for sending."""
        message = WhatsAppMessage(
            **message_data, status=WhatsAppMessageStatus.PENDING
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        # Message will be picked up by Celery worker for async sending
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        tenant_id: int,
        contact_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WhatsAppMessage]:
        """Get messages with optional filtering."""
        query = select(WhatsAppMessage).where(
            WhatsAppMessage.tenant_id == tenant_id
        )
        if contact_id:
            query = query.where(WhatsAppMessage.contact_id == contact_id)
        if conversation_id:
            query = query.where(
                WhatsAppMessage.conversation_id == conversation_id
            )
        query = query.order_by(WhatsAppMessage.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_message_by_id(
        db: AsyncSession, message_id: int, tenant_id: int
    ) -> Optional[WhatsAppMessage]:
        """Get a specific message by ID."""
        result = await db.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.id == message_id,
                WhatsAppMessage.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_message_by_wamid(
        db: AsyncSession, wamid: str
    ) -> Optional[WhatsAppMessage]:
        """Get a message by WhatsApp Message ID."""
        result = await db.execute(
            select(WhatsAppMessage).where(WhatsAppMessage.wamid == wamid)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_message_status(
        db: AsyncSession,
        wamid: str,
        status: str,
        timestamp: datetime,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update message status from webhook callback."""
        message = await WhatsAppService.get_message_by_wamid(db, wamid)
        if message:
            message.status = status

            # Update timestamp based on status
            if status == WhatsAppMessageStatus.SENT:
                message.sent_at = timestamp
            elif status == WhatsAppMessageStatus.DELIVERED:
                message.delivered_at = timestamp
            elif status == WhatsAppMessageStatus.READ:
                message.read_at = timestamp
            elif status == WhatsAppMessageStatus.FAILED:
                message.error_code = error_code
                message.error_message = error_message

            # Append to status history
            status_history = message.status_history or []
            status_history.append({
                "status": status,
                "timestamp": timestamp.isoformat(),
                "error_code": error_code,
                "error_message": error_message,
            })
            message.status_history = status_history

            await db.commit()
            return True
        return False

    # -------------------------------------------------------------------------
    # Conversation Operations
    # -------------------------------------------------------------------------

    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession,
        tenant_id: int,
        contact_id: int,
    ) -> WhatsAppConversation:
        """Get active conversation or create a new one."""
        # Look for active conversation (within 24-hour window)
        result = await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.tenant_id == tenant_id,
                WhatsAppConversation.contact_id == contact_id,
                WhatsAppConversation.is_active == True,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            # Create new conversation
            conversation = WhatsAppConversation(
                tenant_id=tenant_id,
                contact_id=contact_id,
                started_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        return conversation

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        tenant_id: int,
        contact_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WhatsAppConversation]:
        """Get conversations with optional filtering."""
        query = select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == tenant_id
        )
        if contact_id:
            query = query.where(WhatsAppConversation.contact_id == contact_id)
        if is_active is not None:
            query = query.where(WhatsAppConversation.is_active == is_active)
        query = query.order_by(WhatsAppConversation.started_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def close_conversation(
        db: AsyncSession, conversation_id: int, tenant_id: int
    ) -> bool:
        """Close an active conversation."""
        result = await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conversation_id,
                WhatsAppConversation.tenant_id == tenant_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.is_active = False
            conversation.ended_at = datetime.utcnow()
            await db.commit()
            return True
        return False
