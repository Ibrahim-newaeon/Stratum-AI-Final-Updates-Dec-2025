# =============================================================================
# Stratum AI - Audience Sync Models
# =============================================================================
"""
Database models for CDP audience sync to ad platforms.

Tracks sync jobs, platform audiences, and sync history for:
- Meta Custom Audiences
- Google Customer Match
- TikTok Custom Audiences
- Snapchat Audience Match
"""

import enum
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base, TimestampMixin

# =============================================================================
# Enums
# =============================================================================


class SyncPlatform(str, enum.Enum):
    """Supported ad platforms for audience sync."""

    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"


class SyncStatus(str, enum.Enum):
    """Status of audience sync job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some records failed


class SyncOperation(str, enum.Enum):
    """Type of sync operation."""

    CREATE = "create"  # Create new audience
    UPDATE = "update"  # Update existing audience (add/remove users)
    REPLACE = "replace"  # Replace entire audience
    DELETE = "delete"  # Delete audience from platform


class AudienceType(str, enum.Enum):
    """Type of audience on platform."""

    CUSTOMER_LIST = "customer_list"
    LOOKALIKE = "lookalike"
    WEBSITE = "website"
    APP = "app"


# =============================================================================
# Platform Audience Model
# =============================================================================


class PlatformAudience(Base, TimestampMixin):
    """
    Tracks audiences created on ad platforms from CDP segments.
    Links CDP segments to their corresponding platform audiences.
    """

    __tablename__ = "platform_audiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to CDP segment
    segment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform details
    platform = Column(String(50), nullable=False)  # meta, google, tiktok, snapchat
    platform_audience_id = Column(String(255), nullable=True)  # ID on the platform
    platform_audience_name = Column(String(255), nullable=False)

    # Ad account linkage
    ad_account_id = Column(String(255), nullable=False)  # Platform ad account ID

    # Audience configuration
    audience_type = Column(String(50), nullable=False, default=AudienceType.CUSTOMER_LIST.value)
    description = Column(Text, nullable=True)

    # Sync settings
    auto_sync = Column(Boolean, nullable=False, default=True)
    sync_interval_hours = Column(Integer, nullable=False, default=24)
    next_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    is_active = Column(Boolean, nullable=False, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_error = Column(Text, nullable=True)

    # Audience size on platform
    platform_size = Column(BigInteger, nullable=True)
    matched_size = Column(BigInteger, nullable=True)  # Size after platform matching
    match_rate = Column(Numeric(5, 2), nullable=True)  # Percentage matched

    # Configuration for platform-specific settings
    platform_config = Column(JSONB, nullable=False, default=dict)

    # Relationships
    segment = relationship("CDPSegment", backref="platform_audiences")
    sync_jobs = relationship(
        "AudienceSyncJob",
        back_populates="platform_audience",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_platform_audiences_tenant", "tenant_id"),
        Index("ix_platform_audiences_segment", "segment_id"),
        Index("ix_platform_audiences_platform", "tenant_id", "platform"),
        Index("ix_platform_audiences_account", "tenant_id", "ad_account_id"),
        UniqueConstraint(
            "tenant_id",
            "segment_id",
            "platform",
            "ad_account_id",
            name="uq_platform_audiences_segment_platform_account",
        ),
    )

    def __repr__(self) -> str:
        return f"<PlatformAudience {self.platform}: {self.platform_audience_name}>"


# =============================================================================
# Audience Sync Job Model
# =============================================================================


class AudienceSyncJob(Base, TimestampMixin):
    """
    Individual sync job execution record.
    Tracks each sync operation with detailed status and metrics.
    """

    __tablename__ = "audience_sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to platform audience
    platform_audience_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_audiences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job details
    operation = Column(String(50), nullable=False)  # create, update, replace, delete
    status = Column(String(50), nullable=False, default=SyncStatus.PENDING.value)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Metrics
    profiles_total = Column(Integer, nullable=False, default=0)
    profiles_sent = Column(Integer, nullable=False, default=0)
    profiles_added = Column(Integer, nullable=False, default=0)
    profiles_removed = Column(Integer, nullable=False, default=0)
    profiles_failed = Column(Integer, nullable=False, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=False, default=dict)

    # Platform response
    platform_response = Column(JSONB, nullable=False, default=dict)

    # Triggered by
    triggered_by = Column(String(50), nullable=True)  # "auto", "manual", "segment_update"
    triggered_by_user_id = Column(Integer, nullable=True)

    # Relationships
    platform_audience = relationship("PlatformAudience", back_populates="sync_jobs")

    __table_args__ = (
        Index("ix_audience_sync_jobs_tenant", "tenant_id"),
        Index("ix_audience_sync_jobs_audience", "platform_audience_id"),
        Index("ix_audience_sync_jobs_status", "tenant_id", "status"),
        Index("ix_audience_sync_jobs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AudienceSyncJob {self.operation} ({self.status}): {self.profiles_sent} profiles>"


# =============================================================================
# Platform Credentials Model (for storing OAuth tokens)
# =============================================================================


class AudienceSyncCredential(Base, TimestampMixin):
    """
    Stores platform-specific credentials for audience sync.
    Links to ad accounts for each platform.

    Security: OAuth tokens are encrypted at rest using Fernet encryption.
    Use the set_access_token() and get_access_token() methods to handle
    encryption/decryption automatically.
    """

    __tablename__ = "audience_sync_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform and account
    platform = Column(String(50), nullable=False)
    ad_account_id = Column(String(255), nullable=False)
    ad_account_name = Column(String(255), nullable=True)

    # Credentials (ENCRYPTED - never store plaintext tokens)
    # Use set_access_token()/get_access_token() methods for encryption
    _access_token_encrypted = Column("access_token", Text, nullable=True)
    _refresh_token_encrypted = Column("refresh_token", Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    def set_access_token(self, token: str | None) -> None:
        """Encrypt and store access token."""
        if token is None:
            self._access_token_encrypted = None
        else:
            from app.core.security import encrypt_pii
            self._access_token_encrypted = encrypt_pii(token)

    def get_access_token(self) -> str | None:
        """Decrypt and return access token."""
        if self._access_token_encrypted is None:
            return None
        from app.core.security import decrypt_pii
        return decrypt_pii(self._access_token_encrypted)

    def set_refresh_token(self, token: str | None) -> None:
        """Encrypt and store refresh token."""
        if token is None:
            self._refresh_token_encrypted = None
        else:
            from app.core.security import encrypt_pii
            self._refresh_token_encrypted = encrypt_pii(token)

    def get_refresh_token(self) -> str | None:
        """Decrypt and return refresh token."""
        if self._refresh_token_encrypted is None:
            return None
        from app.core.security import decrypt_pii
        return decrypt_pii(self._refresh_token_encrypted)

    # Properties for backward compatibility
    @property
    def access_token(self) -> str | None:
        """Get decrypted access token (backward compat)."""
        return self.get_access_token()

    @access_token.setter
    def access_token(self, value: str | None) -> None:
        """Set encrypted access token (backward compat)."""
        self.set_access_token(value)

    @property
    def refresh_token(self) -> str | None:
        """Get decrypted refresh token (backward compat)."""
        return self.get_refresh_token()

    @refresh_token.setter
    def refresh_token(self, value: str | None) -> None:
        """Set encrypted refresh token (backward compat)."""
        self.set_refresh_token(value)

    # Platform-specific IDs
    business_id = Column(String(255), nullable=True)  # Meta Business Manager ID
    customer_id = Column(String(255), nullable=True)  # Google Ads Customer ID

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Additional config
    config = Column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_audience_sync_creds_tenant", "tenant_id"),
        Index("ix_audience_sync_creds_platform", "tenant_id", "platform"),
        UniqueConstraint(
            "tenant_id",
            "platform",
            "ad_account_id",
            name="uq_audience_sync_creds_tenant_platform_account",
        ),
    )

    def __repr__(self) -> str:
        return f"<AudienceSyncCredential {self.platform}: {self.ad_account_id}>"
