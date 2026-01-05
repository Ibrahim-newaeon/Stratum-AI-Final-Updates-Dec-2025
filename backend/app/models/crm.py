# =============================================================================
# Stratum AI - CRM Integration Database Models
# =============================================================================
"""
Database models for CRM integrations (HubSpot, Salesforce, etc.).

Models:
- CRMConnection: OAuth connections to CRM providers
- CRMContact: Synced contacts with identity matching
- CRMDeal: Synced deals with attribution
- Touchpoint: Ad touchpoints for attribution tracking
- DailyPipelineMetrics: Aggregated pipeline/revenue metrics
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Float, Text, ForeignKey,
    Index, Enum as SQLEnum, Boolean, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


# =============================================================================
# Enums
# =============================================================================

class CRMProvider(str, enum.Enum):
    """Supported CRM providers."""
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    PIPEDRIVE = "pipedrive"
    ZOHO = "zoho"


class CRMConnectionStatus(str, enum.Enum):
    """CRM connection status."""
    PENDING = "pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class DealStage(str, enum.Enum):
    """Standard deal stages for pipeline tracking."""
    LEAD = "lead"
    MQL = "mql"  # Marketing Qualified Lead
    SQL = "sql"  # Sales Qualified Lead
    OPPORTUNITY = "opportunity"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class AttributionModel(str, enum.Enum):
    """Attribution models for touchpoint credit."""
    LAST_TOUCH = "last_touch"
    FIRST_TOUCH = "first_touch"
    LINEAR = "linear"
    POSITION_BASED = "position_based"  # 40% first, 40% last, 20% middle
    TIME_DECAY = "time_decay"
    DATA_DRIVEN = "data_driven"


# =============================================================================
# CRM Connection Model
# =============================================================================

class CRMConnection(Base):
    """
    OAuth connections to CRM providers (per tenant).
    Stores encrypted tokens for secure API access.
    """
    __tablename__ = "crm_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Provider details
    provider = Column(SQLEnum(CRMProvider), nullable=False)
    provider_account_id = Column(String(255), nullable=True)  # HubSpot portal ID, etc.
    provider_account_name = Column(String(255), nullable=True)

    # OAuth tokens (encrypted)
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Scopes granted
    scopes = Column(Text, nullable=True)  # Comma-separated scopes

    # Connection status
    status = Column(SQLEnum(CRMConnectionStatus), nullable=False, default=CRMConnectionStatus.PENDING)
    status_message = Column(Text, nullable=True)

    # Sync configuration
    sync_contacts = Column(Boolean, default=True, nullable=False)
    sync_deals = Column(Boolean, default=True, nullable=False)
    sync_companies = Column(Boolean, default=False, nullable=False)
    webhook_enabled = Column(Boolean, default=False, nullable=False)
    webhook_secret = Column(String(255), nullable=True)

    # Sync tracking
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # success, partial, failed
    last_sync_contacts_count = Column(Integer, default=0)
    last_sync_deals_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    contacts = relationship("CRMContact", back_populates="connection", cascade="all, delete-orphan")
    deals = relationship("CRMDeal", back_populates="connection", cascade="all, delete-orphan")
    writeback_config = relationship("CRMWritebackConfig", back_populates="connection", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_crm_connections_tenant_provider", "tenant_id", "provider"),
        Index("ix_crm_connections_status", "status"),
    )


# =============================================================================
# CRM Contact Model
# =============================================================================

class CRMContact(Base):
    """
    Synced contacts from CRM with identity matching fields.
    Links ad touchpoints to CRM contacts for attribution.
    """
    __tablename__ = "crm_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("crm_connections.id", ondelete="CASCADE"), nullable=False)

    # CRM identifiers
    crm_contact_id = Column(String(255), nullable=False)  # HubSpot contact ID
    crm_owner_id = Column(String(255), nullable=True)  # Sales rep owner

    # Identity matching (hashed for privacy)
    email_hash = Column(String(64), nullable=True)  # SHA256 lowercase trimmed
    phone_hash = Column(String(64), nullable=True)

    # UTM parameters (captured at conversion)
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)

    # Click IDs
    gclid = Column(String(255), nullable=True)  # Google
    fbclid = Column(String(255), nullable=True)  # Meta
    ttclid = Column(String(255), nullable=True)  # TikTok
    sclid = Column(String(255), nullable=True)  # Snapchat
    msclkid = Column(String(255), nullable=True)  # Microsoft

    # Visitor IDs
    ga_client_id = Column(String(255), nullable=True)
    stratum_visitor_id = Column(String(255), nullable=True)

    # Lifecycle tracking
    lifecycle_stage = Column(String(100), nullable=True)  # lead, mql, sql, customer, etc.
    lead_source = Column(String(255), nullable=True)

    # Attribution (computed)
    first_touch_campaign_id = Column(String(255), nullable=True)
    last_touch_campaign_id = Column(String(255), nullable=True)
    first_touch_ts = Column(DateTime(timezone=True), nullable=True)
    last_touch_ts = Column(DateTime(timezone=True), nullable=True)
    touch_count = Column(Integer, default=0)

    # Stratum quality score (optional writeback)
    stratum_quality_score = Column(Float, nullable=True)

    # Raw CRM data (JSON for flexibility)
    raw_properties = Column(JSONB, nullable=True)

    # Timestamps
    crm_created_at = Column(DateTime(timezone=True), nullable=True)
    crm_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    connection = relationship("CRMConnection", back_populates="contacts")
    deals = relationship("CRMDeal", back_populates="contact")
    touchpoints = relationship("Touchpoint", back_populates="contact")

    __table_args__ = (
        Index("ix_crm_contacts_tenant_email", "tenant_id", "email_hash"),
        Index("ix_crm_contacts_tenant_phone", "tenant_id", "phone_hash"),
        Index("ix_crm_contacts_tenant_gclid", "tenant_id", "gclid"),
        Index("ix_crm_contacts_tenant_fbclid", "tenant_id", "fbclid"),
        Index("ix_crm_contacts_crm_id", "connection_id", "crm_contact_id"),
        Index("ix_crm_contacts_lifecycle", "tenant_id", "lifecycle_stage"),
    )


# =============================================================================
# CRM Deal Model
# =============================================================================

class CRMDeal(Base):
    """
    Synced deals from CRM with revenue attribution.
    Enables Pipeline ROAS and Won ROAS calculations.
    """
    __tablename__ = "crm_deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("crm_connections.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)

    # CRM identifiers
    crm_deal_id = Column(String(255), nullable=False)
    crm_pipeline_id = Column(String(255), nullable=True)
    crm_owner_id = Column(String(255), nullable=True)

    # Deal details
    deal_name = Column(String(500), nullable=True)
    stage = Column(String(100), nullable=True)  # Raw stage from CRM
    stage_normalized = Column(SQLEnum(DealStage), nullable=True)  # Normalized stage

    # Financials
    amount = Column(Float, nullable=True)  # Deal value
    amount_cents = Column(BigInteger, nullable=True)  # Deal value in cents
    currency = Column(String(10), default="USD", nullable=False)

    # Dates
    close_date = Column(Date, nullable=True)
    expected_close_date = Column(Date, nullable=True)

    # Win/Loss tracking
    is_won = Column(Boolean, default=False, nullable=False)
    is_closed = Column(Boolean, default=False, nullable=False)
    won_at = Column(DateTime(timezone=True), nullable=True)

    # Attribution
    attributed_campaign_id = Column(String(255), nullable=True)
    attributed_adset_id = Column(String(255), nullable=True)
    attributed_ad_id = Column(String(255), nullable=True)
    attributed_platform = Column(String(50), nullable=True)  # meta, google, etc.
    attribution_model = Column(SQLEnum(AttributionModel), default=AttributionModel.LAST_TOUCH)
    attribution_confidence = Column(Float, nullable=True)  # 0-1

    # Attribution touchpoint link
    attributed_touchpoint_id = Column(UUID(as_uuid=True), ForeignKey("touchpoints.id", ondelete="SET NULL"), nullable=True)

    # Raw CRM data
    raw_properties = Column(JSONB, nullable=True)

    # Timestamps
    crm_created_at = Column(DateTime(timezone=True), nullable=True)
    crm_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    connection = relationship("CRMConnection", back_populates="deals")
    contact = relationship("CRMContact", back_populates="deals")
    attributed_touchpoint = relationship("Touchpoint", foreign_keys=[attributed_touchpoint_id])

    __table_args__ = (
        Index("ix_crm_deals_tenant_stage", "tenant_id", "stage_normalized"),
        Index("ix_crm_deals_tenant_won", "tenant_id", "is_won"),
        Index("ix_crm_deals_tenant_close_date", "tenant_id", "close_date"),
        Index("ix_crm_deals_crm_id", "connection_id", "crm_deal_id"),
        Index("ix_crm_deals_attributed_campaign", "tenant_id", "attributed_campaign_id"),
    )


# =============================================================================
# Touchpoint Model
# =============================================================================

class Touchpoint(Base):
    """
    Ad touchpoints for multi-touch attribution.
    Captures every ad interaction that can be linked to a conversion.
    """
    __tablename__ = "touchpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Contact link (if matched)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)

    # Touchpoint timing
    event_ts = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(50), nullable=False)  # click, view, impression, conversion

    # Platform/source
    source = Column(String(50), nullable=False)  # meta, google, tiktok, snapchat

    # Campaign hierarchy
    account_id = Column(String(255), nullable=True)
    campaign_id = Column(String(255), nullable=True)
    campaign_name = Column(String(500), nullable=True)
    adset_id = Column(String(255), nullable=True)
    adset_name = Column(String(500), nullable=True)
    ad_id = Column(String(255), nullable=True)
    ad_name = Column(String(500), nullable=True)

    # UTM parameters
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)

    # Click IDs
    click_id = Column(String(255), nullable=True)  # Generic click ID
    gclid = Column(String(255), nullable=True)
    fbclid = Column(String(255), nullable=True)
    ttclid = Column(String(255), nullable=True)
    sclid = Column(String(255), nullable=True)

    # Identity signals
    email_hash = Column(String(64), nullable=True)
    phone_hash = Column(String(64), nullable=True)
    visitor_id = Column(String(255), nullable=True)
    ga_client_id = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)

    # Device/geo context
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    country = Column(String(10), nullable=True)
    region = Column(String(100), nullable=True)

    # Landing page
    landing_page_url = Column(Text, nullable=True)
    referrer_url = Column(Text, nullable=True)

    # Cost (if available at touchpoint level)
    cost_cents = Column(BigInteger, nullable=True)

    # Attribution flags
    is_first_touch = Column(Boolean, default=False)
    is_last_touch = Column(Boolean, default=False)
    is_converting_touch = Column(Boolean, default=False)

    # Position in journey (1-based)
    touch_position = Column(Integer, nullable=True)
    total_touches = Column(Integer, nullable=True)

    # Attribution weight (for multi-touch models)
    attribution_weight = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    contact = relationship("CRMContact", back_populates="touchpoints")

    __table_args__ = (
        Index("ix_touchpoints_tenant_contact", "tenant_id", "contact_id"),
        Index("ix_touchpoints_tenant_event_ts", "tenant_id", "event_ts"),
        Index("ix_touchpoints_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_touchpoints_email_hash", "tenant_id", "email_hash"),
        Index("ix_touchpoints_click_ids", "tenant_id", "gclid", "fbclid", "ttclid"),
        Index("ix_touchpoints_visitor", "tenant_id", "visitor_id"),
    )


# =============================================================================
# Daily Pipeline Metrics (Aggregated)
# =============================================================================

class DailyPipelineMetrics(Base):
    """
    Aggregated daily metrics combining ad spend with CRM pipeline data.
    Enables Pipeline ROAS and Won ROAS calculations.
    """
    __tablename__ = "daily_pipeline_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Dimension (optional granularity)
    platform = Column(String(50), nullable=True)  # meta, google, etc. (null = all)
    campaign_id = Column(String(255), nullable=True)  # (null = all)

    # Ad platform metrics
    spend_cents = Column(BigInteger, default=0, nullable=False)
    impressions = Column(BigInteger, default=0, nullable=False)
    clicks = Column(BigInteger, default=0, nullable=False)
    platform_conversions = Column(Integer, default=0, nullable=False)
    platform_revenue_cents = Column(BigInteger, default=0, nullable=False)

    # CRM pipeline metrics
    leads_created = Column(Integer, default=0, nullable=False)
    mqls_created = Column(Integer, default=0, nullable=False)
    sqls_created = Column(Integer, default=0, nullable=False)
    opportunities_created = Column(Integer, default=0, nullable=False)

    # Pipeline value (all open deals)
    pipeline_value_cents = Column(BigInteger, default=0, nullable=False)
    pipeline_deal_count = Column(Integer, default=0, nullable=False)

    # Won deals
    deals_won = Column(Integer, default=0, nullable=False)
    won_revenue_cents = Column(BigInteger, default=0, nullable=False)

    # Lost deals
    deals_lost = Column(Integer, default=0, nullable=False)
    lost_value_cents = Column(BigInteger, default=0, nullable=False)

    # Computed ROAS metrics
    platform_roas = Column(Float, nullable=True)  # platform_revenue / spend
    pipeline_roas = Column(Float, nullable=True)  # pipeline_value / spend
    won_roas = Column(Float, nullable=True)  # won_revenue / spend

    # Funnel conversion rates
    lead_to_mql_rate = Column(Float, nullable=True)
    mql_to_sql_rate = Column(Float, nullable=True)
    sql_to_won_rate = Column(Float, nullable=True)

    # CAC metrics
    cac_cents = Column(BigInteger, nullable=True)  # spend / deals_won

    # Time-to-close (average days)
    avg_time_to_close_days = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_daily_pipeline_metrics_tenant_date", "tenant_id", "date"),
        Index("ix_daily_pipeline_metrics_tenant_platform", "tenant_id", "platform", "date"),
        Index("ix_daily_pipeline_metrics_tenant_campaign", "tenant_id", "campaign_id", "date"),
    )


# =============================================================================
# Writeback Status Enum
# =============================================================================

class WritebackStatus(str, enum.Enum):
    """Writeback operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# =============================================================================
# CRM Writeback Configuration
# =============================================================================

class CRMWritebackConfig(Base):
    """
    Configuration for CRM writeback operations.
    Controls what data is pushed back to the CRM.
    """
    __tablename__ = "crm_writeback_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("crm_connections.id", ondelete="CASCADE"), nullable=False)

    # Writeback toggles
    enabled = Column(Boolean, default=False, nullable=False)
    sync_contacts = Column(Boolean, default=True, nullable=False)
    sync_deals = Column(Boolean, default=True, nullable=False)

    # Sync schedule
    auto_sync_enabled = Column(Boolean, default=False, nullable=False)
    sync_interval_hours = Column(Integer, default=24, nullable=False)  # Default: daily

    # What to sync
    sync_attribution = Column(Boolean, default=True, nullable=False)
    sync_profit_metrics = Column(Boolean, default=True, nullable=False)
    sync_touchpoint_count = Column(Boolean, default=True, nullable=False)

    # Property setup status
    properties_created = Column(Boolean, default=False, nullable=False)
    properties_created_at = Column(DateTime(timezone=True), nullable=True)

    # Last sync tracking
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(SQLEnum(WritebackStatus), nullable=True)
    last_sync_contacts = Column(Integer, nullable=True)
    last_sync_deals = Column(Integer, nullable=True)
    last_sync_errors = Column(Integer, nullable=True)

    # Next scheduled sync
    next_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    connection = relationship("CRMConnection", back_populates="writeback_config")

    __table_args__ = (
        Index("ix_writeback_config_tenant", "tenant_id"),
    )


# =============================================================================
# CRM Writeback Sync History
# =============================================================================

class CRMWritebackSync(Base):
    """
    History of CRM writeback sync operations.
    Tracks each sync run for auditing and troubleshooting.
    """
    __tablename__ = "crm_writeback_syncs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("crm_connections.id", ondelete="CASCADE"), nullable=False)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # full, incremental, manual, scheduled
    status = Column(SQLEnum(WritebackStatus), nullable=False, default=WritebackStatus.PENDING)

    # Timing
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Scope
    sync_contacts = Column(Boolean, default=True)
    sync_deals = Column(Boolean, default=True)
    modified_since = Column(DateTime(timezone=True), nullable=True)

    # Results
    contacts_processed = Column(Integer, default=0)
    contacts_synced = Column(Integer, default=0)
    contacts_failed = Column(Integer, default=0)
    deals_processed = Column(Integer, default=0)
    deals_synced = Column(Integer, default=0)
    deals_failed = Column(Integer, default=0)

    # Error details
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Triggered by
    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    connection = relationship("CRMConnection")
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])

    __table_args__ = (
        Index("ix_writeback_sync_tenant_date", "tenant_id", "started_at"),
        Index("ix_writeback_sync_status", "tenant_id", "status"),
    )
