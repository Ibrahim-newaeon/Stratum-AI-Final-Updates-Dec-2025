# =============================================================================
# Stratum AI - CDP (Customer Data Platform) Database Models
# =============================================================================
"""
Database models for the Stratum CDP module.

Models:
- CDPSource: Data source configurations (pixel, server, SGTM, etc.)
- CDPProfile: Unified customer profiles
- CDPProfileIdentifier: Identity mappings (email, phone, device)
- CDPEvent: Append-only event store
- CDPConsent: Privacy consent records

All models are multi-tenant with tenant_id column.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey,
    Index, Enum as SQLEnum, Boolean, BigInteger, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


# =============================================================================
# Enums
# =============================================================================

class SourceType(str, enum.Enum):
    """Types of data sources that can send events."""
    WEBSITE = "website"   # Browser pixel/JavaScript SDK
    SERVER = "server"     # Server-side API
    SGTM = "sgtm"         # Server-side Google Tag Manager
    IMPORT = "import"     # CSV/bulk import
    CRM = "crm"           # CRM sync (HubSpot, Salesforce, etc.)


class IdentifierType(str, enum.Enum):
    """Types of customer identifiers."""
    EMAIL = "email"
    PHONE = "phone"
    DEVICE_ID = "device_id"
    ANONYMOUS_ID = "anonymous_id"
    EXTERNAL_ID = "external_id"


class LifecycleStage(str, enum.Enum):
    """Customer lifecycle stages."""
    ANONYMOUS = "anonymous"   # Unknown visitor
    KNOWN = "known"           # Identified (email/phone collected)
    CUSTOMER = "customer"     # Has made a purchase
    CHURNED = "churned"       # Inactive for defined period


class ConsentType(str, enum.Enum):
    """Types of privacy consent."""
    ANALYTICS = "analytics"   # Analytics/tracking consent
    ADS = "ads"               # Advertising consent
    EMAIL = "email"           # Email marketing consent
    SMS = "sms"               # SMS marketing consent
    ALL = "all"               # Global consent (all types)


# =============================================================================
# CDP Source Model
# =============================================================================

class CDPSource(Base, TimestampMixin):
    """
    Data source configuration for CDP event ingestion.
    Each source has a unique API key for authentication.
    """
    __tablename__ = "cdp_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source identification
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # Using string for flexibility
    source_key = Column(String(64), nullable=False)   # API key for this source

    # Configuration (JSON for flexibility)
    config = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)

    # Metrics
    event_count = Column(BigInteger, nullable=False, default=0)
    last_event_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    events = relationship("CDPEvent", back_populates="source", lazy="dynamic")

    __table_args__ = (
        Index("ix_cdp_sources_tenant", "tenant_id"),
        Index("ix_cdp_sources_key", "source_key"),
        Index("ix_cdp_sources_type", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return f"<CDPSource {self.name} ({self.source_type})>"


# =============================================================================
# CDP Profile Model
# =============================================================================

class CDPProfile(Base, TimestampMixin):
    """
    Unified customer profile. One row per unique customer.
    Aggregates data from multiple identifiers and events.
    """
    __tablename__ = "cdp_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External reference (client's customer ID)
    external_id = Column(String(255), nullable=True)

    # Activity timestamps
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Flexible profile data
    profile_data = Column(JSONB, nullable=False, default=dict)
    computed_traits = Column(JSONB, nullable=False, default=dict)

    # Lifecycle
    lifecycle_stage = Column(String(50), nullable=False, default=LifecycleStage.ANONYMOUS.value)

    # Aggregated counters (denormalized for performance)
    total_events = Column(Integer, nullable=False, default=0)
    total_sessions = Column(Integer, nullable=False, default=0)
    total_purchases = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))

    # Relationships
    identifiers = relationship(
        "CDPProfileIdentifier",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events = relationship("CDPEvent", back_populates="profile", lazy="dynamic")
    consents = relationship(
        "CDPConsent",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_cdp_profiles_tenant", "tenant_id"),
        Index("ix_cdp_profiles_lifecycle", "tenant_id", "lifecycle_stage"),
    )

    def __repr__(self) -> str:
        return f"<CDPProfile {self.id} ({self.lifecycle_stage})>"

    def get_primary_email(self) -> Optional[str]:
        """Get the primary email identifier for this profile."""
        for identifier in self.identifiers:
            if identifier.identifier_type == IdentifierType.EMAIL.value and identifier.is_primary:
                return identifier.identifier_value
        # Fallback to any email
        for identifier in self.identifiers:
            if identifier.identifier_type == IdentifierType.EMAIL.value:
                return identifier.identifier_value
        return None

    def has_consent(self, consent_type: str) -> bool:
        """Check if profile has granted a specific consent type."""
        for consent in self.consents:
            if consent.consent_type == consent_type and consent.granted:
                return True
        return False


# =============================================================================
# CDP Profile Identifier Model
# =============================================================================

class CDPProfileIdentifier(Base):
    """
    Identity mapping - links identifiers (email, phone, device) to profiles.
    Identifiers are hashed for privacy.
    """
    __tablename__ = "cdp_profile_identifiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identifier details
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(String(512), nullable=True)   # Original (can be redacted)
    identifier_hash = Column(String(64), nullable=False)    # SHA256 hash

    # Metadata
    is_primary = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Numeric(3, 2), nullable=False, default=Decimal("1.00"))

    # Verification & timestamps
    verified_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    profile = relationship("CDPProfile", back_populates="identifiers")

    __table_args__ = (
        Index("ix_cdp_identifiers_tenant", "tenant_id"),
        Index("ix_cdp_identifiers_profile", "profile_id"),
        Index("ix_cdp_identifiers_lookup", "tenant_id", "identifier_type", "identifier_hash"),
        Index("ix_cdp_identifiers_hash", "identifier_hash"),
        UniqueConstraint(
            "tenant_id", "identifier_type", "identifier_hash",
            name="uq_cdp_identifiers_tenant_type_hash"
        ),
    )

    def __repr__(self) -> str:
        return f"<CDPProfileIdentifier {self.identifier_type}: {self.identifier_hash[:8]}...>"


# =============================================================================
# CDP Event Model
# =============================================================================

class CDPEvent(Base):
    """
    Append-only event store. Events are never updated or deleted.
    Each event is linked to a profile (if identifiable) and a source.
    """
    __tablename__ = "cdp_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event identification
    event_name = Column(String(255), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Deduplication
    idempotency_key = Column(String(128), nullable=True)

    # Event data
    properties = Column(JSONB, nullable=False, default=dict)
    context = Column(JSONB, nullable=False, default=dict)
    identifiers = Column(JSONB, nullable=False, default=list)

    # Processing status
    processed = Column(Boolean, nullable=False, default=False)
    processing_errors = Column(JSONB, nullable=False, default=list)

    # EMQ (Event Match Quality) - integration with Stratum signal health
    emq_score = Column(Numeric(5, 2), nullable=True)

    # Timestamp (no updated_at - events are immutable)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    profile = relationship("CDPProfile", back_populates="events")
    source = relationship("CDPSource", back_populates="events")

    __table_args__ = (
        Index("ix_cdp_events_tenant", "tenant_id"),
        Index("ix_cdp_events_profile", "profile_id"),
        Index("ix_cdp_events_name", "tenant_id", "event_name"),
        Index("ix_cdp_events_source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<CDPEvent {self.event_name} at {self.event_time}>"


# =============================================================================
# CDP Consent Model
# =============================================================================

class CDPConsent(Base, TimestampMixin):
    """
    Privacy consent tracking per profile per consent type.
    Maintains audit trail for compliance (GDPR, PDPL, etc.).
    """
    __tablename__ = "cdp_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Consent details
    consent_type = Column(String(50), nullable=False)
    granted = Column(Boolean, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Audit information
    source = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Compliance
    consent_text = Column(Text, nullable=True)
    consent_version = Column(String(50), nullable=True)

    # Relationships
    profile = relationship("CDPProfile", back_populates="consents")

    __table_args__ = (
        Index("ix_cdp_consents_tenant", "tenant_id"),
        Index("ix_cdp_consents_profile", "profile_id"),
        Index("ix_cdp_consents_type", "tenant_id", "consent_type", "granted"),
        UniqueConstraint(
            "tenant_id", "profile_id", "consent_type",
            name="uq_cdp_consents_tenant_profile_type"
        ),
    )

    def __repr__(self) -> str:
        status = "granted" if self.granted else "revoked"
        return f"<CDPConsent {self.consent_type}: {status}>"
