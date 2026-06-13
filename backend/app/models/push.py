# =============================================================================
# Stratum AI - Push Notification Models
# =============================================================================
"""SQLAlchemy models for web-push notifications.

Persists device subscriptions and sent-notification records so that data
survives process restarts and is shared across API workers — replacing the
former per-process in-memory store, which lost subscriptions on restart and
was invisible across workers.

Identifiers retain the legacy ``sub_<hex>`` / ``notif_<hex>`` string format,
so the API contract is unchanged.
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


def generate_subscription_id() -> str:
    """Generate a push-subscription identifier (legacy ``sub_<hex>`` format)."""
    return f"sub_{secrets.token_hex(8)}"


def generate_notification_id() -> str:
    """Generate a push-notification identifier (legacy ``notif_<hex>`` format)."""
    return f"notif_{secrets.token_hex(8)}"


class PushSubscription(Base):
    """A browser/device registration for web-push notifications."""

    __tablename__ = "push_subscriptions"

    id = Column(String(64), primary_key=True, default=generate_subscription_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint = Column(Text, nullable=False)
    keys = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    user_agent = Column(Text, nullable=True)
    platform = Column(String(20), nullable=False, default="web", server_default="web")
    is_active = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    last_active_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_push_subscription_tenant_active", "tenant_id", "is_active"),
    )


class PushNotificationLog(Base):
    """A record of a sent push-notification batch."""

    __tablename__ = "push_notification_log"

    id = Column(String(64), primary_key=True, default=generate_notification_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    tag = Column(String(255), nullable=True)
    sent_count = Column(Integer, nullable=False, default=0, server_default="0")
    delivered_count = Column(Integer, nullable=False, default=0, server_default="0")
    failed_count = Column(Integer, nullable=False, default=0, server_default="0")
    target_type = Column(
        String(20), nullable=False, default="all", server_default="all"
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_push_notif_tenant_created", "tenant_id", "created_at"),)
