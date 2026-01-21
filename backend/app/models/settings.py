# =============================================================================
# Stratum AI - Settings Models (Webhooks, Notifications, Changelog)
# =============================================================================
"""
Models for tenant settings features:
- Webhooks: Outbound event notifications
- Notifications: In-app notification system
- Changelog: Product updates and release notes
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, TenantMixin


# =============================================================================
# Enums
# =============================================================================

class WebhookStatus(str, Enum):
    """Webhook endpoint status."""
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"  # Too many failures


class WebhookEventType(str, Enum):
    """Available webhook event types."""
    CAMPAIGN_UPDATED = "campaign.updated"
    CAMPAIGN_PAUSED = "campaign.paused"
    ALERT_TRIGGERED = "alert.triggered"
    BUDGET_DEPLETED = "budget.depleted"
    SYNC_COMPLETED = "sync.completed"
    ANOMALY_DETECTED = "anomaly.detected"
    TRUST_GATE_PASS = "trust_gate.pass"
    TRUST_GATE_HOLD = "trust_gate.hold"
    TRUST_GATE_BLOCK = "trust_gate.block"


class NotificationType(str, Enum):
    """In-app notification types."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ALERT = "alert"


class NotificationCategory(str, Enum):
    """Notification categories for filtering."""
    SYSTEM = "system"
    CAMPAIGN = "campaign"
    TRUST_GATE = "trust_gate"
    BILLING = "billing"
    SECURITY = "security"
    INTEGRATION = "integration"


class ChangelogType(str, Enum):
    """Changelog entry types."""
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    FIX = "fix"
    SECURITY = "security"
    DEPRECATION = "deprecation"


# =============================================================================
# Webhook Models
# =============================================================================

class Webhook(Base, TimestampMixin, TenantMixin):
    """
    Webhook endpoint configuration for outbound event notifications.
    """
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Endpoint configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # For HMAC signing

    # Event subscriptions (list of WebhookEventType values)
    events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Status and health
    status: Mapped[WebhookStatus] = mapped_column(
        SQLEnum(WebhookStatus, name="webhook_status"),
        default=WebhookStatus.ACTIVE,
        nullable=False,
    )
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Headers to include in requests
    headers: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)

    # Relationships
    deliveries: Mapped[List["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_webhooks_tenant_status", "tenant_id", "status"),
    )


class WebhookDelivery(Base, TimestampMixin):
    """
    Log of webhook delivery attempts.
    """
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Delivery status
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_created", "webhook_id", "created_at"),
    )


# =============================================================================
# Notification Models
# =============================================================================

class Notification(Base, TimestampMixin, TenantMixin):
    """
    In-app notifications for users.
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # Null = broadcast to all tenant users

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, name="notification_type"),
        default=NotificationType.INFO,
        nullable=False,
    )
    category: Mapped[NotificationCategory] = mapped_column(
        SQLEnum(NotificationCategory, name="notification_category"),
        default=NotificationCategory.SYSTEM,
        nullable=False,
    )

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Action link (optional)
    action_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    action_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_tenant_created", "tenant_id", "created_at"),
    )


# =============================================================================
# Changelog Models
# =============================================================================

class ChangelogEntry(Base, TimestampMixin):
    """
    Product changelog / What's New entries.
    Global (not tenant-specific).
    """
    __tablename__ = "changelog_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Version info
    version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "1.2.0"

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    type: Mapped[ChangelogType] = mapped_column(
        SQLEnum(ChangelogType, name="changelog_type"),
        default=ChangelogType.FEATURE,
        nullable=False,
    )

    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Rich content
    image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    docs_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Tags for filtering
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    __table_args__ = (
        Index("ix_changelog_published", "is_published", "published_at"),
    )


class ChangelogReadStatus(Base, TimestampMixin):
    """
    Tracks which changelog entries a user has seen.
    """
    __tablename__ = "changelog_read_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    changelog_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("changelog_entries.id", ondelete="CASCADE"), nullable=False
    )

    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_changelog_read_user", "user_id", "changelog_id", unique=True),
    )


# =============================================================================
# Slack Integration Settings
# =============================================================================

class SlackIntegration(Base, TimestampMixin, TenantMixin):
    """
    Slack workspace integration settings per tenant.
    """
    __tablename__ = "slack_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Webhook URL (encrypted)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Channel configuration
    channel_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # What to notify
    notify_trust_gate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_anomalies: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_signal_health: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_test_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("ix_slack_integrations_tenant", "tenant_id", unique=True),
    )
