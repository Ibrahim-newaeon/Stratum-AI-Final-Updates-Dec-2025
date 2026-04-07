# =============================================================================
# Stratum AI - Embed Widget Models
# =============================================================================
"""
Database models for embeddable widgets with tier-based branding.

Security Features:
- Domain-bound tokens (only work on whitelisted domains)
- Short-lived tokens with refresh rotation
- Read-only scoped permissions
- Signed data payloads
- Rate limiting per token

Tier Alignment:
- Starter: Widgets with full Stratum branding
- Professional: Smaller branding, more widget types
- Enterprise: White-label (no branding), custom domains
"""

import enum
import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base, TimestampMixin

# =============================================================================
# Enums
# =============================================================================


class WidgetType(str, enum.Enum):
    """Types of embeddable widgets."""

    SIGNAL_HEALTH = "signal_health"  # Signal health badge/gauge
    ROAS_DISPLAY = "roas_display"  # ROAS metric display
    CAMPAIGN_PERFORMANCE = "campaign_performance"  # Mini campaign table
    TRUST_GATE_STATUS = "trust_gate_status"  # Trust gate indicator
    SPEND_TRACKER = "spend_tracker"  # Ad spend tracker
    ANOMALY_ALERT = "anomaly_alert"  # Anomaly alert badge


class WidgetSize(str, enum.Enum):
    """Widget size presets."""

    BADGE = "badge"  # Small badge (120x40)
    COMPACT = "compact"  # Compact card (200x100)
    STANDARD = "standard"  # Standard card (300x200)
    LARGE = "large"  # Large card (400x300)
    CUSTOM = "custom"  # Custom dimensions


class BrandingLevel(str, enum.Enum):
    """Branding visibility levels by tier."""

    FULL = "full"  # Starter: Full Stratum branding
    MINIMAL = "minimal"  # Professional: Small "Powered by Stratum"
    NONE = "none"  # Enterprise: No branding (white-label)


class TokenStatus(str, enum.Enum):
    """Embed token status."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


# =============================================================================
# Widget Configuration Model
# =============================================================================


class EmbedWidget(Base, TimestampMixin):
    """
    Widget configuration for embedding on external sites.
    Each widget has its own access token and domain restrictions.
    """

    __tablename__ = "embed_widgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Widget identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Widget type and configuration
    widget_type = Column(String(50), nullable=False)
    widget_size = Column(String(50), nullable=False, default=WidgetSize.STANDARD.value)

    # Custom dimensions (for CUSTOM size)
    custom_width = Column(Integer, nullable=True)
    custom_height = Column(Integer, nullable=True)

    # Branding level (determined by tier)
    branding_level = Column(String(50), nullable=False, default=BrandingLevel.FULL.value)

    # Custom branding (Enterprise only)
    custom_logo_url = Column(String(512), nullable=True)
    custom_accent_color = Column(String(7), nullable=True)  # Hex color
    custom_background_color = Column(String(7), nullable=True)
    custom_text_color = Column(String(7), nullable=True)

    # Data source configuration
    # Scope limits what data the widget can access
    data_scope = Column(JSONB, nullable=False, default=dict)
    # e.g., {"campaigns": ["camp_123"], "ad_accounts": ["acc_456"]}

    # Refresh interval (how often widget refreshes data)
    refresh_interval_seconds = Column(Integer, nullable=False, default=300)  # 5 min default

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Analytics
    total_views = Column(BigInteger, nullable=False, default=0)
    total_unique_domains = Column(Integer, nullable=False, default=0)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tokens = relationship(
        "EmbedToken",
        back_populates="widget",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_embed_widgets_tenant", "tenant_id"),
        Index("ix_embed_widgets_type", "tenant_id", "widget_type"),
        Index("ix_embed_widgets_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<EmbedWidget {self.name} ({self.widget_type})>"


# =============================================================================
# Embed Token Model
# =============================================================================


class EmbedToken(Base, TimestampMixin):
    """
    Secure, domain-bound embed tokens.

    Security measures:
    - Token is hashed before storage (we only store hash)
    - Domain binding prevents token theft
    - Short expiration with refresh rotation
    - Read-only access only
    """

    __tablename__ = "embed_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to widget
    widget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("embed_widgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token identification
    token_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    token_hash = Column(String(64), nullable=False)  # SHA-256 hash of full token

    # Domain binding (CRITICAL for security)
    allowed_domains = Column(ARRAY(String(255)), nullable=False)
    # e.g., ["dashboard.client.com", "*.client.com"]

    # Token lifecycle
    status = Column(String(50), nullable=False, default=TokenStatus.ACTIVE.value)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Refresh token (for rotation)
    refresh_token_hash = Column(String(64), nullable=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    current_minute_requests = Column(Integer, nullable=False, default=0)
    current_minute_start = Column(DateTime(timezone=True), nullable=True)

    # Usage analytics
    total_requests = Column(BigInteger, nullable=False, default=0)
    total_errors = Column(BigInteger, nullable=False, default=0)

    # Security: track last known origins
    last_origin = Column(String(512), nullable=True)
    suspicious_activity = Column(Boolean, nullable=False, default=False)

    # Relationships
    widget = relationship("EmbedWidget", back_populates="tokens")

    __table_args__ = (
        Index("ix_embed_tokens_tenant", "tenant_id"),
        Index("ix_embed_tokens_widget", "widget_id"),
        Index("ix_embed_tokens_prefix", "token_prefix"),
        Index("ix_embed_tokens_hash", "token_hash"),
        Index("ix_embed_tokens_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<EmbedToken {self.token_prefix}... ({self.status})>"

    @staticmethod
    def generate_token() -> tuple[str, str, str]:
        """
        Generate a new embed token.

        Returns:
            tuple: (full_token, token_prefix, token_hash)
        """
        # Generate a secure random token
        # Format: stm_embed_{random_32_chars}
        random_part = secrets.token_urlsafe(32)
        full_token = f"stm_embed_{random_part}"

        # Get prefix for identification
        token_prefix = full_token[:16]

        # Hash the token for storage
        token_hash = hashlib.sha256(full_token.encode()).hexdigest()

        return full_token, token_prefix, token_hash

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for comparison."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def generate_refresh_token() -> tuple[str, str]:
        """
        Generate a refresh token.

        Returns:
            tuple: (refresh_token, refresh_token_hash)
        """
        refresh_token = secrets.token_urlsafe(32)
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        return refresh_token, refresh_hash


# =============================================================================
# Domain Whitelist Model
# =============================================================================


class EmbedDomainWhitelist(Base, TimestampMixin):
    """
    Pre-approved domains for embed widgets.
    Enterprise tier can add unlimited domains.
    """

    __tablename__ = "embed_domain_whitelist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Domain pattern (supports wildcards)
    domain_pattern = Column(String(255), nullable=False)
    # e.g., "dashboard.client.com" or "*.client.com"

    # Verification status
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(64), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Notes
    description = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_embed_domain_whitelist_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id", "domain_pattern", name="uq_embed_domain_whitelist_tenant_domain"
        ),
    )

    def __repr__(self) -> str:
        return f"<EmbedDomainWhitelist {self.domain_pattern}>"


# =============================================================================
# Widget View Log (for analytics)
# =============================================================================


class EmbedWidgetView(Base):
    """
    Anonymized view log for widget analytics.
    Does not store PII, only aggregated metrics.
    """

    __tablename__ = "embed_widget_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, nullable=False, index=True)
    widget_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # View details (anonymized)
    view_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    origin_domain = Column(String(255), nullable=True)

    # Geo (country-level only)
    country_code = Column(String(2), nullable=True)

    # Device category
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet

    __table_args__ = (
        Index("ix_embed_widget_views_tenant_date", "tenant_id", "view_date"),
        Index("ix_embed_widget_views_widget_date", "widget_id", "view_date"),
    )
