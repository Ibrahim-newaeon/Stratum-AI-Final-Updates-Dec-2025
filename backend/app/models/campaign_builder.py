# =============================================================================
# Stratum AI - Campaign Builder Models
# =============================================================================
"""
Database models for the Campaign Builder feature:
- TenantPlatformConnection: OAuth tokens and connection metadata per tenant
- TenantAdAccount: Ad accounts enabled for use by tenant
- CampaignDraft: Campaign drafts with approval workflow
- CampaignPublishLog: Audit trail for publish attempts
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, ForeignKey,
    Numeric, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.db.base_class import Base


# =============================================================================
# Enums
# =============================================================================

class AdPlatform(str, enum.Enum):
    """Supported advertising platforms."""
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"


class ConnectionStatus(str, enum.Enum):
    """Platform connection status."""
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class DraftStatus(str, enum.Enum):
    """Campaign draft status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishResult(str, enum.Enum):
    """Publish attempt result."""
    SUCCESS = "success"
    FAILURE = "failure"


# =============================================================================
# Models
# =============================================================================

class TenantPlatformConnection(Base):
    """
    Stores OAuth tokens and connection metadata per tenant.
    One record per (tenant, platform) pair.
    """
    __tablename__ = "tenant_platform_connection"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default=ConnectionStatus.DISCONNECTED.value)

    # Token storage (encrypted in production)
    token_ref = Column(Text, nullable=True)  # Reference to encrypted token in secrets manager
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # OAuth metadata
    scopes = Column(JSONB, nullable=True, default=list)
    granted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="platform_connections")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])
    ad_accounts = relationship("TenantAdAccount", back_populates="connection", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", name="uq_tenant_platform_connection"),
        Index("ix_tenant_platform_connection_tenant_platform", "tenant_id", "platform"),
    )


class TenantAdAccount(Base):
    """
    Ad accounts that tenant has enabled for use in Stratum AI.
    Synced from platform after OAuth authorization.
    """
    __tablename__ = "tenant_ad_account"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("tenant_platform_connection.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)

    # Platform identifiers
    platform_account_id = Column(String(255), nullable=False)  # e.g., act_123456789
    name = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=True)

    # Account configuration
    currency = Column(String(10), nullable=False, default="USD")
    timezone = Column(String(100), nullable=False, default="UTC")
    is_enabled = Column(Boolean, default=False, nullable=False)

    # Budget controls
    daily_budget_cap = Column(Numeric(precision=12, scale=2), nullable=True)
    monthly_budget_cap = Column(Numeric(precision=12, scale=2), nullable=True)

    # Platform permissions and metadata
    permissions_json = Column(JSONB, nullable=True, default=dict)
    account_status = Column(String(50), nullable=True)  # active, disabled, etc.

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="ad_accounts")
    connection = relationship("TenantPlatformConnection", back_populates="ad_accounts")
    campaign_drafts = relationship("CampaignDraft", back_populates="ad_account")

    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", "platform_account_id", name="uq_tenant_ad_account"),
        Index("ix_tenant_ad_account_enabled", "tenant_id", "is_enabled"),
    )


class CampaignDraft(Base):
    """
    Stores campaign drafts with approval workflow.
    Draft JSON is platform-agnostic, converted at publish time.
    """
    __tablename__ = "campaign_draft"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    ad_account_id = Column(UUID(as_uuid=True), ForeignKey("tenant_ad_account.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(50), nullable=False)

    # Draft identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=DraftStatus.DRAFT.value)

    # Campaign configuration (canonical JSON format)
    draft_json = Column(JSONB, nullable=False, default=dict)

    # Workflow tracking
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejected_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Published campaign reference
    platform_campaign_id = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="campaign_drafts")
    ad_account = relationship("TenantAdAccount", back_populates="campaign_drafts")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id])
    publish_logs = relationship("CampaignPublishLog", back_populates="draft", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_campaign_draft_tenant_status", "tenant_id", "status"),
        Index("ix_campaign_draft_platform", "tenant_id", "platform"),
    )


class CampaignPublishLog(Base):
    """
    Audit trail for campaign publish attempts.
    Records request/response for debugging and compliance.
    """
    __tablename__ = "campaign_publish_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("campaign_draft.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(50), nullable=False)
    platform_account_id = Column(String(255), nullable=False)

    # Actor
    published_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Event timing
    event_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Request/Response (for debugging)
    request_json = Column(JSONB, nullable=True)
    response_json = Column(JSONB, nullable=True)

    # Result
    result_status = Column(String(50), nullable=False)
    platform_campaign_id = Column(String(255), nullable=True)  # If successful

    # Error details
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="publish_logs")
    draft = relationship("CampaignDraft", back_populates="publish_logs")
    published_by = relationship("User", foreign_keys=[published_by_user_id])

    __table_args__ = (
        Index("ix_campaign_publish_log_tenant_time", "tenant_id", "event_time"),
        Index("ix_campaign_publish_log_draft", "draft_id"),
    )
