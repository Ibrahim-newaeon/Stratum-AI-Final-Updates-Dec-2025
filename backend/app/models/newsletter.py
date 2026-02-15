# =============================================================================
# Stratum AI - Newsletter / Email Campaign Models
# =============================================================================
"""
Database models for the newsletter email campaign system.

- NewsletterTemplate: Reusable email templates
- NewsletterCampaign: Individual campaign sends
- NewsletterEvent: Open/click/bounce tracking events
"""

from datetime import datetime, UTC
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_models import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class CampaignStatus(str, PyEnum):
    """Status of a newsletter campaign."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TemplateCategory(str, PyEnum):
    """Category of a newsletter template."""

    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    UPDATE = "update"
    ANNOUNCEMENT = "announcement"


class NewsletterEventType(str, PyEnum):
    """Type of tracking event."""

    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINED = "complained"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class NewsletterTemplate(Base):
    """
    Reusable email templates for newsletter campaigns.

    Stores both rendered HTML and TipTap JSON for editor round-tripping.
    """

    __tablename__ = "newsletter_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    # Template content
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    preheader_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # TipTap JSON

    # Metadata
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(
        String(20), default=TemplateCategory.PROMOTIONAL.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    campaigns = relationship("NewsletterCampaign", back_populates="template")

    __table_args__ = (
        Index("ix_nl_template_tenant", "tenant_id"),
        Index("ix_nl_template_category", "category"),
    )


class NewsletterCampaign(Base):
    """
    Individual newsletter email campaign.

    Holds content, audience filters, scheduling, and aggregate stats.
    """

    __tablename__ = "newsletter_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    # Campaign details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    preheader_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content (stored both as HTML and TipTap JSON for round-tripping)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Template reference (optional — campaign can be from scratch)
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("newsletter_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=CampaignStatus.DRAFT.value, nullable=False
    )

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sender overrides (falls back to system defaults if null)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    from_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reply_to_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audience filters (JSONB)
    # e.g. { "status": ["approved"], "min_lead_score": 50, "platforms": ["meta","google"] }
    audience_filters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Aggregate stats (updated by worker after send)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_bounced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_unsubscribed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Creator
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    template = relationship("NewsletterTemplate", back_populates="campaigns")
    events = relationship("NewsletterEvent", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_nl_campaign_tenant", "tenant_id"),
        Index("ix_nl_campaign_status", "status"),
        Index("ix_nl_campaign_scheduled", "status", "scheduled_at"),
    )


class NewsletterEvent(Base):
    """
    Tracking events for newsletter campaigns.

    Records opens, clicks, bounces, unsubscribes per subscriber per campaign.
    """

    __tablename__ = "newsletter_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("newsletter_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("landing_page_subscribers.id", ondelete="CASCADE"), nullable=False
    )

    # Event
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # e.g. { "link_url": "https://...", "user_agent": "...", "ip": "..." }

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    campaign = relationship("NewsletterCampaign", back_populates="events")

    __table_args__ = (
        Index("ix_nl_event_campaign", "campaign_id", "event_type"),
        Index("ix_nl_event_subscriber", "subscriber_id", "event_type"),
        Index("ix_nl_event_created", "created_at"),
    )
