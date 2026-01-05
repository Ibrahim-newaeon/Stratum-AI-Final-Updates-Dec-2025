# =============================================================================
# Stratum AI - Database Models
# =============================================================================
"""
Complete SQLAlchemy models for the Stratum AI platform.
Implements multi-tenancy, soft delete, and audit capabilities.

Models:
- Tenant: Organization/company entity
- User: User accounts with roles
- Campaign: Unified campaign model across ad platforms
- CreativeAsset: Digital Asset Management (DAM)
- Rule: Automation rules engine
- CompetitorBenchmark: Competitor intelligence data
- AuditLog: Security and compliance audit trail
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin


# =============================================================================
# Enums
# =============================================================================
class UserRole(str, PyEnum):
    """User roles for access control."""

    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class AdPlatform(str, PyEnum):
    """Supported advertising platforms."""

    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
    LINKEDIN = "linkedin"


class CampaignStatus(str, PyEnum):
    """Campaign lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AssetType(str, PyEnum):
    """Creative asset types."""

    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"
    HTML5 = "html5"


class RuleStatus(str, PyEnum):
    """Automation rule status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DRAFT = "draft"


class RuleOperator(str, PyEnum):
    """Rule condition operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    IN = "in"


class RuleAction(str, PyEnum):
    """Rule action types."""

    APPLY_LABEL = "apply_label"
    SEND_ALERT = "send_alert"
    PAUSE_CAMPAIGN = "pause_campaign"
    ADJUST_BUDGET = "adjust_budget"
    NOTIFY_SLACK = "notify_slack"
    NOTIFY_WHATSAPP = "notify_whatsapp"


class AuditAction(str, PyEnum):
    """Audit log action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    ANONYMIZE = "anonymize"


# =============================================================================
# Tenant Model (Multi-tenancy Root)
# =============================================================================
class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    """
    Organization/Company entity.
    All other entities belong to a tenant for multi-tenancy isolation.
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Subscription & Billing
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    feature_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Limits
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_campaigns: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="tenant", foreign_keys="[User.tenant_id]"
    )
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="tenant", foreign_keys="[Campaign.tenant_id]"
    )
    assets: Mapped[List["CreativeAsset"]] = relationship(
        "CreativeAsset", back_populates="tenant", foreign_keys="[CreativeAsset.tenant_id]"
    )
    rules: Mapped[List["Rule"]] = relationship(
        "Rule", back_populates="tenant", foreign_keys="[Rule.tenant_id]"
    )
    competitors: Mapped[List["CompetitorBenchmark"]] = relationship(
        "CompetitorBenchmark", back_populates="tenant", foreign_keys="[CompetitorBenchmark.tenant_id]"
    )

    # Trust Layer relationships (lazy import to avoid circular imports)
    signal_health_records: Mapped[List["FactSignalHealthDaily"]] = relationship(
        "FactSignalHealthDaily", back_populates="tenant", foreign_keys="[FactSignalHealthDaily.tenant_id]"
    )
    attribution_variance_records: Mapped[List["FactAttributionVarianceDaily"]] = relationship(
        "FactAttributionVarianceDaily", back_populates="tenant", foreign_keys="[FactAttributionVarianceDaily.tenant_id]"
    )
    actions_queue: Mapped[List["FactActionsQueue"]] = relationship(
        "FactActionsQueue", back_populates="tenant", foreign_keys="[FactActionsQueue.tenant_id]"
    )

    # Campaign Builder relationships
    platform_connections: Mapped[List["TenantPlatformConnection"]] = relationship(
        "TenantPlatformConnection", back_populates="tenant", foreign_keys="[TenantPlatformConnection.tenant_id]"
    )
    ad_accounts: Mapped[List["TenantAdAccount"]] = relationship(
        "TenantAdAccount", back_populates="tenant", foreign_keys="[TenantAdAccount.tenant_id]"
    )
    campaign_drafts: Mapped[List["CampaignDraft"]] = relationship(
        "CampaignDraft", back_populates="tenant", foreign_keys="[CampaignDraft.tenant_id]"
    )
    publish_logs: Mapped[List["CampaignPublishLog"]] = relationship(
        "CampaignPublishLog", back_populates="tenant", foreign_keys="[CampaignPublishLog.tenant_id]"
    )

    __table_args__ = (
        Index("ix_tenants_slug", "slug"),
        Index("ix_tenants_active", "is_deleted", "plan"),
    )


# =============================================================================
# User Model
# =============================================================================
class User(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """
    User accounts with role-based access control.
    PII fields (email, full_name) are encrypted at rest.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted
    email_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # For lookups
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile (PII - encrypted)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Role & Permissions
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.ANALYST, nullable=False
    )
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Preferences
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # GDPR Compliance
    consent_marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_analytics: Mapped[bool] = mapped_column(Boolean, default=True)
    gdpr_anonymized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email_hash", name="uq_user_tenant_email"),
        Index("ix_users_email_hash", "email_hash"),
        Index("ix_users_tenant_active", "tenant_id", "is_active", "is_deleted"),
    )


# =============================================================================
# Campaign Model (Unified across Ad Platforms)
# =============================================================================
class Campaign(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """
    Unified campaign model that normalizes data from Meta, Google, TikTok, Snapchat.
    Provides a single view across all advertising platforms.
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Platform Reference
    platform: Mapped[AdPlatform] = mapped_column(
        Enum(AdPlatform, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    external_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Platform's campaign ID
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Campaign Info
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, values_callable=lambda x: [e.value for e in x]),
        default=CampaignStatus.DRAFT, nullable=False
    )
    objective: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Budget & Spend (stored in cents to avoid floating point issues)
    daily_budget_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lifetime_budget_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_spend_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Performance Metrics (Aggregated)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Computed Metrics (stored for query performance)
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Click-through rate
    cpc_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Cost per click
    cpm_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Cost per mille
    cpa_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Cost per acquisition
    roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Return on ad spend

    # Targeting (Denormalized for analytics)
    targeting_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    targeting_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    targeting_genders: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    targeting_locations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    targeting_interests: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Demographics Breakdown (for heatmaps)
    demographics_age: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    demographics_gender: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    demographics_location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Scheduling
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)

    # Labels for organization
    labels: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Raw platform data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Sync metadata
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="campaigns")
    metrics: Mapped[List["CampaignMetric"]] = relationship(
        "CampaignMetric", back_populates="campaign", cascade="all, delete-orphan"
    )
    assets: Mapped[List["CreativeAsset"]] = relationship(
        "CreativeAsset", back_populates="campaign"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "platform", "external_id", name="uq_campaign_platform_external"
        ),
        Index("ix_campaigns_tenant_status", "tenant_id", "status"),
        Index("ix_campaigns_platform", "tenant_id", "platform"),
        Index("ix_campaigns_date_range", "tenant_id", "start_date", "end_date"),
        Index("ix_campaigns_roas", "tenant_id", "roas"),
    )

    def calculate_metrics(self) -> None:
        """Recalculate derived metrics."""
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
            self.cpm_cents = int((self.total_spend_cents / self.impressions) * 1000)

        if self.clicks > 0:
            self.cpc_cents = int(self.total_spend_cents / self.clicks)

        if self.conversions > 0:
            self.cpa_cents = int(self.total_spend_cents / self.conversions)

        if self.total_spend_cents > 0:
            self.roas = self.revenue_cents / self.total_spend_cents


# =============================================================================
# Campaign Metrics (Time Series)
# =============================================================================
class CampaignMetric(Base, TenantMixin):
    """
    Daily time-series metrics for campaigns.
    Used for trend analysis and forecasting.
    """

    __tablename__ = "campaign_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Daily Metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spend_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Engagement
    video_views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_completions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Demographics snapshot
    demographics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "date", name="uq_campaign_metric_date"
        ),
        Index("ix_campaign_metrics_date", "tenant_id", "date"),
        Index("ix_campaign_metrics_campaign_date", "campaign_id", "date"),
    )


# =============================================================================
# Creative Asset (Digital Asset Management)
# =============================================================================
class CreativeAsset(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """
    Digital Asset Management for ad creatives.
    Tracks images, videos, and their performance across campaigns.
    """

    __tablename__ = "creative_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )

    # Asset Info
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # File Metadata
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Organization
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Performance Metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Creative Fatigue Analysis
    fatigue_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )  # 0-100 scale
    first_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # AI-Generated Metadata
    ai_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    brand_safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="assets")
    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="assets"
    )

    __table_args__ = (
        Index("ix_assets_tenant_type", "tenant_id", "asset_type"),
        Index("ix_assets_fatigue", "tenant_id", "fatigue_score"),
        Index("ix_assets_folder", "tenant_id", "folder"),
    )


# =============================================================================
# Automation Rule (Rules Engine - Module C)
# =============================================================================
class Rule(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """
    IFTTT-style automation rules for campaign management.
    Evaluated periodically by Celery workers.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Rule Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RuleStatus] = mapped_column(
        Enum(RuleStatus), default=RuleStatus.DRAFT, nullable=False
    )

    # Condition (IF)
    condition_field: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., 'roas', 'ctr', 'spend'
    condition_operator: Mapped[RuleOperator] = mapped_column(
        Enum(RuleOperator), nullable=False
    )
    condition_value: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Stored as string, parsed based on field type
    condition_duration_hours: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
    )  # Time window

    # Action (THEN)
    action_type: Mapped[RuleAction] = mapped_column(Enum(RuleAction), nullable=False)
    action_config: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # Action-specific config

    # Scope
    applies_to_campaigns: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # Specific campaign IDs or null for all
    applies_to_platforms: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # Specific platforms or null for all

    # Execution
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trigger_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cooldown (prevent rapid-fire triggers)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="rules")
    executions: Mapped[List["RuleExecution"]] = relationship(
        "RuleExecution", back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_rules_tenant_status", "tenant_id", "status"),
        Index("ix_rules_evaluation", "status", "last_evaluated_at"),
    )


class RuleExecution(Base, TenantMixin):
    """
    Log of rule executions for audit and debugging.
    """

    __tablename__ = "rule_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )

    # Execution Details
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    condition_result: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # What was evaluated
    action_result: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # What action was taken
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule", back_populates="executions")

    __table_args__ = (
        Index("ix_rule_executions_rule_date", "rule_id", "executed_at"),
        Index("ix_rule_executions_tenant_date", "tenant_id", "executed_at"),
    )


# =============================================================================
# Competitor Benchmark (Module D)
# =============================================================================
class CompetitorBenchmark(Base, TimestampMixin, TenantMixin):
    """
    Competitor intelligence and market benchmark data.
    Stores scraped metadata and API-sourced market data.
    """

    __tablename__ = "competitor_benchmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Competitor Info
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Primary competitor flag

    # Scraped Metadata (Safe)
    meta_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    social_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Market Intelligence (from APIs like SerpApi/DataForSEO)
    estimated_traffic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    traffic_trend: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # 'up', 'down', 'stable'
    top_keywords: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    paid_keywords_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organic_keywords_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Share of Voice (calculated)
    share_of_voice: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ad Intelligence
    estimated_ad_spend_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detected_ad_platforms: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    ad_creatives_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Historical snapshots
    metrics_history: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # Array of timestamped snapshots

    # Data Source
    data_source: Mapped[str] = mapped_column(
        String(50), default="scraper", nullable=False
    )
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetch_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="competitors")

    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_competitor_tenant_domain"),
        Index("ix_competitors_tenant_primary", "tenant_id", "is_primary"),
        Index("ix_competitors_sov", "tenant_id", "share_of_voice"),
    )


# =============================================================================
# Audit Log (Module F - Security & Governance)
# =============================================================================
class AuditLog(Base):
    """
    Comprehensive audit trail for security and compliance.
    Records all state-changing operations.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Action Details
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Change Tracking
    old_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    changed_fields: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_tenant_date", "tenant_id", "created_at"),
        Index("ix_audit_user_date", "user_id", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
        Index("ix_audit_action", "tenant_id", "action", "created_at"),
    )


# =============================================================================
# ML Predictions Cache
# =============================================================================
class MLPrediction(Base, TenantMixin):
    """
    Cache for ML model predictions to avoid redundant computations.
    """

    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True
    )

    # Prediction Info
    prediction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'portfolio_analysis', 'roas_alerts', 'campaign_prediction'
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # 'roas_forecast', 'conversion_predictor'
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)
    input_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # Hash of input features

    # Input/Output Data (for complex predictions)
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    prediction_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Simple Prediction Result (for single-value predictions)
    prediction_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feature_importances: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    predicted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_predictions_cache", "model_type", "input_hash"),
        Index("ix_predictions_type", "tenant_id", "prediction_type"),
        Index("ix_predictions_expiry", "expires_at"),
    )


# =============================================================================
# Notification Preferences
# =============================================================================
class NotificationPreference(Base, TenantMixin):
    """
    User notification preferences for alerts and reports.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Alert Types
    alert_rule_triggered: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_budget_threshold: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_performance_drop: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_sync_failure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Reports
    report_daily: Mapped[bool] = mapped_column(Boolean, default=False)
    report_weekly: Mapped[bool] = mapped_column(Boolean, default=True)
    report_monthly: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("user_id", name="uq_notification_user"),)


# =============================================================================
# API Key Management
# =============================================================================
class APIKey(Base, TimestampMixin, TenantMixin):
    """
    API keys for programmatic access.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )  # SHA256 hash
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # For identification

    # Permissions
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_api_keys_hash", "key_hash"),)


# =============================================================================
# WhatsApp Integration Models (Module G)
# =============================================================================
class WhatsAppOptInStatus(str, PyEnum):
    """WhatsApp contact opt-in status."""
    PENDING = "pending"
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"


class WhatsAppMessageDirection(str, PyEnum):
    """WhatsApp message direction."""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class WhatsAppMessageStatus(str, PyEnum):
    """WhatsApp message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsAppTemplateStatus(str, PyEnum):
    """WhatsApp template approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAUSED = "paused"


class WhatsAppTemplateCategory(str, PyEnum):
    """WhatsApp template categories."""
    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class WhatsAppContact(Base, TimestampMixin, TenantMixin):
    """
    WhatsApp contact management with opt-in tracking.
    Required for WhatsApp Business API compliance.
    """

    __tablename__ = "whatsapp_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Contact Info (E.164 format)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    verification_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Opt-in Status (REQUIRED for WhatsApp Business)
    opt_in_status: Mapped[WhatsAppOptInStatus] = mapped_column(
        Enum(WhatsAppOptInStatus, values_callable=lambda x: [e.value for e in x]),
        default=WhatsAppOptInStatus.PENDING, nullable=False
    )
    opt_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opt_out_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opt_in_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # web_form, sms, qr_code, manual

    # WhatsApp Profile (from API)
    wa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    profile_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Preferences
    notification_types: Mapped[list] = mapped_column(
        JSONB, default=["alerts", "reports", "digests"], nullable=False
    )
    quiet_hours: Mapped[dict] = mapped_column(
        JSONB, default={"enabled": False, "start": "22:00", "end": "08:00"}, nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User")
    messages: Mapped[List["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage", back_populates="contact", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["WhatsAppConversation"]] = relationship(
        "WhatsAppConversation", back_populates="contact", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_wa_contacts_tenant_phone", "tenant_id", "phone_number"),
        Index("ix_wa_contacts_user", "user_id"),
        Index("ix_wa_contacts_opt_in", "tenant_id", "opt_in_status"),
    )


class WhatsAppTemplate(Base, TimestampMixin, TenantMixin):
    """
    WhatsApp message templates (require Meta approval).
    """

    __tablename__ = "whatsapp_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Template Info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    category: Mapped[WhatsAppTemplateCategory] = mapped_column(
        Enum(WhatsAppTemplateCategory, values_callable=lambda x: [e.value for e in x]), nullable=False
    )

    # Template Content
    header_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # NONE, TEXT, IMAGE, VIDEO, DOCUMENT
    header_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    footer_text: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    # Variables/Parameters
    header_variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    body_variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Buttons (Optional)
    buttons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Meta Approval Status
    meta_template_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[WhatsAppTemplateStatus] = mapped_column(
        Enum(WhatsAppTemplateStatus, values_callable=lambda x: [e.value for e in x]), default=WhatsAppTemplateStatus.PENDING, nullable=False
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Usage Tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    messages: Mapped[List["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage", back_populates="template"
    )

    __table_args__ = (
        Index("ix_wa_templates_tenant_status", "tenant_id", "status"),
        Index("ix_wa_templates_name", "tenant_id", "name"),
    )


class WhatsAppMessage(Base, TenantMixin):
    """
    WhatsApp message tracking and delivery status.
    """

    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("whatsapp_contacts.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("whatsapp_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Message Details
    direction: Mapped[WhatsAppMessageDirection] = mapped_column(
        Enum(WhatsAppMessageDirection, values_callable=lambda x: [e.value for e in x]), default=WhatsAppMessageDirection.OUTBOUND, nullable=False
    )
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # template, text, image, document, interactive

    # Content
    template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    template_variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # WhatsApp API Response
    wamid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipient_wa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status Tracking
    status: Mapped[WhatsAppMessageStatus] = mapped_column(
        Enum(WhatsAppMessageStatus, values_callable=lambda x: [e.value for e in x]), default=WhatsAppMessageStatus.PENDING, nullable=False
    )
    status_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Error Handling
    error_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    contact: Mapped["WhatsAppContact"] = relationship(
        "WhatsAppContact", back_populates="messages"
    )
    template: Mapped[Optional["WhatsAppTemplate"]] = relationship(
        "WhatsAppTemplate", back_populates="messages"
    )

    __table_args__ = (
        Index("ix_wa_messages_contact", "contact_id", "created_at"),
        Index("ix_wa_messages_status", "tenant_id", "status"),
        Index("ix_wa_messages_wamid", "wamid"),
    )


class WhatsAppConversation(Base, TenantMixin):
    """
    WhatsApp conversation windows (24-hour pricing model).
    """

    __tablename__ = "whatsapp_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("whatsapp_contacts.id", ondelete="CASCADE"), nullable=False
    )

    # Conversation Window
    conversation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origin_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # business_initiated, user_initiated

    # Pricing Category
    pricing_category: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # service, utility, authentication, marketing

    # Window Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # 24 hours from start

    # Stats
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    contact: Mapped["WhatsAppContact"] = relationship(
        "WhatsAppContact", back_populates="conversations"
    )

    __table_args__ = (
        Index("ix_wa_conversations_contact", "contact_id"),
        Index("ix_wa_conversations_active", "tenant_id", "is_active", "expires_at"),
    )
