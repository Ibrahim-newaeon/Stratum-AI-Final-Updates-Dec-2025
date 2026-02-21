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

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
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


class SourceType(str, enum.Enum):
    """Types of data sources that can send events."""

    WEBSITE = "website"  # Browser pixel/JavaScript SDK
    SERVER = "server"  # Server-side API
    SGTM = "sgtm"  # Server-side Google Tag Manager
    IMPORT = "import"  # CSV/bulk import
    CRM = "crm"  # CRM sync (HubSpot, Salesforce, etc.)


class IdentifierType(str, enum.Enum):
    """Types of customer identifiers."""

    EMAIL = "email"
    PHONE = "phone"
    DEVICE_ID = "device_id"
    ANONYMOUS_ID = "anonymous_id"
    EXTERNAL_ID = "external_id"


class LifecycleStage(str, enum.Enum):
    """Customer lifecycle stages."""

    ANONYMOUS = "anonymous"  # Unknown visitor
    KNOWN = "known"  # Identified (email/phone collected)
    CUSTOMER = "customer"  # Has made a purchase
    CHURNED = "churned"  # Inactive for defined period


class ConsentType(str, enum.Enum):
    """Types of privacy consent."""

    ANALYTICS = "analytics"  # Analytics/tracking consent
    ADS = "ads"  # Advertising consent
    EMAIL = "email"  # Email marketing consent
    SMS = "sms"  # SMS marketing consent
    ALL = "all"  # Global consent (all types)


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
    source_key = Column(String(64), nullable=False)  # API key for this source

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
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

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
    identifier_value = Column(String(512), nullable=True)  # Original (can be redacted)
    identifier_hash = Column(String(64), nullable=False)  # SHA256 hash

    # Metadata
    is_primary = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Numeric(3, 2), nullable=False, default=Decimal("1.00"))

    # Verification & timestamps
    verified_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("CDPProfile", back_populates="identifiers")

    __table_args__ = (
        Index("ix_cdp_identifiers_tenant", "tenant_id"),
        Index("ix_cdp_identifiers_profile", "profile_id"),
        Index("ix_cdp_identifiers_lookup", "tenant_id", "identifier_type", "identifier_hash"),
        Index("ix_cdp_identifiers_hash", "identifier_hash"),
        UniqueConstraint(
            "tenant_id",
            "identifier_type",
            "identifier_hash",
            name="uq_cdp_identifiers_tenant_type_hash",
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
    received_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

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
            "tenant_id", "profile_id", "consent_type", name="uq_cdp_consents_tenant_profile_type"
        ),
    )

    def __repr__(self) -> str:
        status = "granted" if self.granted else "revoked"
        return f"<CDPConsent {self.consent_type}: {status}>"


# =============================================================================
# CDP Webhook Model
# =============================================================================


class WebhookEventType(str, enum.Enum):
    """Events that can trigger webhooks."""

    EVENT_RECEIVED = "event.received"
    PROFILE_CREATED = "profile.created"
    PROFILE_UPDATED = "profile.updated"
    PROFILE_MERGED = "profile.merged"
    CONSENT_UPDATED = "consent.updated"
    ALL = "all"


class IdentityLinkType(str, enum.Enum):
    """Types of identity links in the graph."""

    SAME_SESSION = "same_session"  # Identifiers seen in same session
    SAME_EVENT = "same_event"  # Identifiers sent in same event
    LOGIN = "login"  # Anonymous linked to known via login
    FORM_SUBMIT = "form_submit"  # Anonymous linked via form submission
    PURCHASE = "purchase"  # Linked during purchase
    MANUAL = "manual"  # Manually linked by admin
    INFERRED = "inferred"  # Inferred from behavior patterns


class MergeReason(str, enum.Enum):
    """Reasons for profile merges."""

    IDENTITY_MATCH = "identity_match"  # Same identifier found
    MANUAL_MERGE = "manual_merge"  # Admin merged profiles
    LOGIN_EVENT = "login_event"  # Login linked anonymous to known
    CROSS_DEVICE = "cross_device"  # Cross-device identification


class CDPWebhook(Base, TimestampMixin):
    """
    Webhook destination for CDP events.
    Allows tenants to receive real-time notifications when events occur.
    """

    __tablename__ = "cdp_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Webhook configuration
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    event_types = Column(JSONB, nullable=False, default=list)  # List of WebhookEventType values

    # Authentication
    secret_key = Column(String(64), nullable=True)  # For HMAC signature

    # State
    is_active = Column(Boolean, nullable=False, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, nullable=False, default=0)

    # Retry configuration
    max_retries = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=30)

    __table_args__ = (
        Index("ix_cdp_webhooks_tenant", "tenant_id"),
        Index("ix_cdp_webhooks_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<CDPWebhook {self.name}: {status}>"


# =============================================================================
# CDP Identity Graph Models
# =============================================================================

# Identity resolution priority (higher = stronger identity)
IDENTITY_PRIORITY = {
    "external_id": 100,  # Customer ID from client system
    "email": 80,  # Email (strong, verified)
    "phone": 70,  # Phone (strong, verified)
    "device_id": 40,  # Device fingerprint
    "anonymous_id": 10,  # Anonymous/cookie ID (weakest)
}


class CDPIdentityLink(Base):
    """
    Identity graph edge - links two identifiers that belong to the same person.

    This creates a graph where nodes are identifiers and edges represent
    relationships between them. Used for identity stitching.
    """

    __tablename__ = "cdp_identity_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source identifier (the one we're linking FROM)
    source_identifier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profile_identifiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Target identifier (the one we're linking TO)
    target_identifier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profile_identifiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link metadata
    link_type = Column(String(50), nullable=False, default=IdentityLinkType.SAME_EVENT.value)
    confidence_score = Column(Numeric(3, 2), nullable=False, default=Decimal("1.00"))

    # Evidence for the link
    evidence = Column(JSONB, nullable=False, default=dict)  # {event_id, session_id, etc.}

    # State
    is_active = Column(Boolean, nullable=False, default=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    source_identifier = relationship(
        "CDPProfileIdentifier",
        foreign_keys=[source_identifier_id],
        backref="outgoing_links",
    )
    target_identifier = relationship(
        "CDPProfileIdentifier",
        foreign_keys=[target_identifier_id],
        backref="incoming_links",
    )

    __table_args__ = (
        Index("ix_cdp_identity_links_tenant", "tenant_id"),
        Index("ix_cdp_identity_links_source", "source_identifier_id"),
        Index("ix_cdp_identity_links_target", "target_identifier_id"),
        Index("ix_cdp_identity_links_type", "tenant_id", "link_type"),
        # Prevent duplicate links
        UniqueConstraint(
            "tenant_id",
            "source_identifier_id",
            "target_identifier_id",
            name="uq_cdp_identity_links_source_target",
        ),
    )

    def __repr__(self) -> str:
        return f"<CDPIdentityLink {self.source_identifier_id} -> {self.target_identifier_id} ({self.link_type})>"


class CDPProfileMerge(Base):
    """
    Profile merge history - tracks when profiles are merged.

    When two profiles are identified as the same person, they are merged.
    This table keeps an audit trail of all merges for debugging and rollback.
    """

    __tablename__ = "cdp_profile_merges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The surviving profile (the one that remains after merge)
    surviving_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="SET NULL"),
        nullable=True,  # Nullable in case surviving profile is later deleted
        index=True,
    )

    # The merged profile (the one that was absorbed)
    merged_profile_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Merge details
    merge_reason = Column(String(50), nullable=False, default=MergeReason.IDENTITY_MATCH.value)

    # Snapshot of merged profile before merge (for potential rollback)
    merged_profile_snapshot = Column(JSONB, nullable=False, default=dict)

    # The identifier that triggered the merge
    triggering_identifier_type = Column(String(50), nullable=True)
    triggering_identifier_hash = Column(String(64), nullable=True)

    # Statistics at merge time
    merged_event_count = Column(Integer, nullable=False, default=0)
    merged_identifier_count = Column(Integer, nullable=False, default=0)

    # Merge metadata
    merged_by_user_id = Column(Integer, nullable=True)  # If manual merge
    merge_metadata = Column(JSONB, nullable=False, default=dict)

    # State
    is_rolled_back = Column(Boolean, nullable=False, default=False)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    surviving_profile = relationship("CDPProfile", foreign_keys=[surviving_profile_id])

    __table_args__ = (
        Index("ix_cdp_profile_merges_tenant", "tenant_id"),
        Index("ix_cdp_profile_merges_surviving", "surviving_profile_id"),
        Index("ix_cdp_profile_merges_merged", "merged_profile_id"),
        Index("ix_cdp_profile_merges_time", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CDPProfileMerge {self.merged_profile_id} -> {self.surviving_profile_id}>"


class CDPCanonicalIdentity(Base):
    """
    Canonical identity record - the "golden" identity for a profile.

    Each profile has one canonical identity that represents the best-known
    identity for that person. Used for identity resolution priority.
    """

    __tablename__ = "cdp_canonical_identities"

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

    # The canonical (strongest) identifier for this profile
    canonical_identifier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profile_identifiers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Canonical identity details (denormalized for performance)
    canonical_type = Column(String(50), nullable=True)  # email, phone, external_id
    canonical_value_hash = Column(String(64), nullable=True)

    # Priority score (based on identifier type)
    priority_score = Column(Integer, nullable=False, default=0)

    # Verification status
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_method = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("CDPProfile", backref="canonical_identity")
    canonical_identifier = relationship("CDPProfileIdentifier")

    __table_args__ = (
        Index("ix_cdp_canonical_tenant", "tenant_id"),
        Index("ix_cdp_canonical_profile", "profile_id"),
        # One canonical identity per profile
        UniqueConstraint("tenant_id", "profile_id", name="uq_cdp_canonical_profile"),
    )

    def __repr__(self) -> str:
        return f"<CDPCanonicalIdentity {self.profile_id}: {self.canonical_type}>"


# =============================================================================
# CDP Segment Models
# =============================================================================


class SegmentType(str, enum.Enum):
    """Types of segments."""

    STATIC = "static"  # Manually defined membership
    DYNAMIC = "dynamic"  # Rule-based, auto-updated
    COMPUTED = "computed"  # ML/algorithm-based


class SegmentStatus(str, enum.Enum):
    """Segment computation status."""

    DRAFT = "draft"  # Not yet computed
    COMPUTING = "computing"  # Currently being computed
    ACTIVE = "active"  # Ready for use
    STALE = "stale"  # Needs recomputation
    ARCHIVED = "archived"  # No longer in use


class ConditionOperator(str, enum.Enum):
    """Operators for segment conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BEFORE = "before"  # Date comparison
    AFTER = "after"  # Date comparison
    WITHIN_LAST = "within_last"  # e.g., within_last 30 days


class CDPSegment(Base, TimestampMixin):
    """
    Customer segment definition.

    Segments can be static (manual membership) or dynamic (rule-based).
    Dynamic segments are evaluated against profile data and events.
    """

    __tablename__ = "cdp_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Segment identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=True)  # URL-friendly identifier

    # Segment configuration
    segment_type = Column(String(50), nullable=False, default=SegmentType.DYNAMIC.value)
    status = Column(String(50), nullable=False, default=SegmentStatus.DRAFT.value)

    # Segment rules (JSON structure for flexible conditions)
    # Format: {"logic": "and|or", "conditions": [...], "groups": [...]}
    rules = Column(JSONB, nullable=False, default=dict)

    # Computed metadata
    profile_count = Column(Integer, nullable=False, default=0)
    last_computed_at = Column(DateTime(timezone=True), nullable=True)
    computation_duration_ms = Column(Integer, nullable=True)

    # Scheduling
    auto_refresh = Column(Boolean, nullable=False, default=True)
    refresh_interval_hours = Column(Integer, nullable=False, default=24)
    next_refresh_at = Column(DateTime(timezone=True), nullable=True)

    # Tags for organization
    tags = Column(JSONB, nullable=False, default=list)

    # Created by
    created_by_user_id = Column(Integer, nullable=True)

    # Relationships
    memberships = relationship(
        "CDPSegmentMembership",
        back_populates="segment",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_cdp_segments_tenant", "tenant_id"),
        Index("ix_cdp_segments_status", "tenant_id", "status"),
        Index("ix_cdp_segments_type", "tenant_id", "segment_type"),
        UniqueConstraint("tenant_id", "slug", name="uq_cdp_segments_slug"),
    )

    def __repr__(self) -> str:
        return f"<CDPSegment {self.name} ({self.segment_type}): {self.profile_count} profiles>"


class CDPSegmentMembership(Base):
    """
    Profile membership in a segment.

    Tracks which profiles belong to which segments.
    For dynamic segments, this is computed automatically.
    """

    __tablename__ = "cdp_segment_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Membership metadata
    added_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    removed_at = Column(DateTime(timezone=True), nullable=True)  # For tracking history
    is_active = Column(Boolean, nullable=False, default=True)

    # For static segments, track who added the profile
    added_by_user_id = Column(Integer, nullable=True)

    # Match score for ranked segments (optional)
    match_score = Column(Numeric(5, 2), nullable=True)

    # Relationships
    segment = relationship("CDPSegment", back_populates="memberships")
    profile = relationship("CDPProfile", backref="segment_memberships")

    __table_args__ = (
        Index("ix_cdp_memberships_tenant", "tenant_id"),
        Index("ix_cdp_memberships_segment", "segment_id"),
        Index("ix_cdp_memberships_profile", "profile_id"),
        Index("ix_cdp_memberships_active", "segment_id", "is_active"),
        # One active membership per profile per segment
        UniqueConstraint(
            "tenant_id", "segment_id", "profile_id", name="uq_cdp_memberships_segment_profile"
        ),
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return (
            f"<CDPSegmentMembership segment={self.segment_id} profile={self.profile_id} ({status})>"
        )


# =============================================================================
# CDP Computed Traits Models
# =============================================================================


class ComputedTraitType(str, enum.Enum):
    """Types of computed traits."""

    COUNT = "count"  # Count of events
    SUM = "sum"  # Sum of property values
    AVERAGE = "average"  # Average of property values
    MIN = "min"  # Minimum value
    MAX = "max"  # Maximum value
    FIRST = "first"  # First occurrence
    LAST = "last"  # Last occurrence
    UNIQUE_COUNT = "unique_count"  # Count of unique values
    EXISTS = "exists"  # Boolean - if event/property exists
    FORMULA = "formula"  # Custom formula


class CDPComputedTrait(Base, TimestampMixin):
    """
    Computed trait definition.

    Computed traits are derived values calculated from profile events.
    Examples: total_purchases, average_order_value, days_since_last_login
    """

    __tablename__ = "cdp_computed_traits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Trait identification
    name = Column(String(100), nullable=False)  # e.g., "total_purchases"
    display_name = Column(String(255), nullable=False)  # e.g., "Total Purchases"
    description = Column(Text, nullable=True)

    # Computation configuration
    trait_type = Column(String(50), nullable=False, default=ComputedTraitType.COUNT.value)

    # Source configuration (what events/properties to compute from)
    # Format: {"event_name": "Purchase", "property": "total", "time_window_days": 365}
    source_config = Column(JSONB, nullable=False, default=dict)

    # Output configuration
    output_type = Column(
        String(50), nullable=False, default="number"
    )  # number, string, boolean, date
    default_value = Column(String(255), nullable=True)  # Default if no data

    # State
    is_active = Column(Boolean, nullable=False, default=True)
    last_computed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_cdp_traits_tenant", "tenant_id"),
        Index("ix_cdp_traits_active", "tenant_id", "is_active"),
        UniqueConstraint("tenant_id", "name", name="uq_cdp_traits_name"),
    )

    def __repr__(self) -> str:
        return f"<CDPComputedTrait {self.name} ({self.trait_type})>"


# =============================================================================
# CDP Funnel/Journey Models
# =============================================================================


class FunnelStatus(str, enum.Enum):
    """Funnel computation status."""

    DRAFT = "draft"  # Not yet computed
    COMPUTING = "computing"  # Currently being computed
    ACTIVE = "active"  # Ready for analysis
    STALE = "stale"  # Needs recomputation
    ARCHIVED = "archived"  # No longer in use


class CDPFunnel(Base, TimestampMixin):
    """
    Funnel definition for conversion analysis.

    A funnel tracks user progression through a series of events/steps.
    Examples: Registration funnel, Purchase funnel, Onboarding flow.
    """

    __tablename__ = "cdp_funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Funnel identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=True)  # URL-friendly identifier

    # Funnel configuration
    status = Column(String(50), nullable=False, default=FunnelStatus.DRAFT.value)

    # Funnel steps (ordered list of event conditions)
    # Format: [{"step_name": "View Product", "event_name": "ProductView", "conditions": [...]}, ...]
    steps = Column(JSONB, nullable=False, default=list)

    # Analysis configuration
    conversion_window_days = Column(
        Integer, nullable=False, default=30
    )  # Max days between first and last step
    step_timeout_hours = Column(Integer, nullable=True)  # Max hours between steps (null = no limit)

    # Computed metrics (cached for performance)
    total_entered = Column(Integer, nullable=False, default=0)  # Users who completed step 1
    total_converted = Column(Integer, nullable=False, default=0)  # Users who completed all steps
    overall_conversion_rate = Column(Numeric(5, 2), nullable=True)  # Percentage 0-100

    # Step-by-step conversion data (cached)
    # Format: [{"step": 1, "name": "...", "count": N, "conversion_rate": X, "drop_off_rate": Y}, ...]
    step_metrics = Column(JSONB, nullable=False, default=list)

    # Timing
    last_computed_at = Column(DateTime(timezone=True), nullable=True)
    computation_duration_ms = Column(Integer, nullable=True)

    # Scheduling
    auto_refresh = Column(Boolean, nullable=False, default=True)
    refresh_interval_hours = Column(Integer, nullable=False, default=24)
    next_refresh_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    tags = Column(JSONB, nullable=False, default=list)
    created_by_user_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_cdp_funnels_tenant", "tenant_id"),
        Index("ix_cdp_funnels_status", "tenant_id", "status"),
        UniqueConstraint("tenant_id", "slug", name="uq_cdp_funnels_slug"),
    )

    def __repr__(self) -> str:
        return f"<CDPFunnel {self.name}: {self.total_entered} entered, {self.overall_conversion_rate}% conversion>"


class CDPFunnelEntry(Base):
    """
    Individual profile's progression through a funnel.

    Tracks each user's journey through funnel steps with timestamps.
    """

    __tablename__ = "cdp_funnel_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    funnel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_funnels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entry status
    entered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    converted_at = Column(DateTime(timezone=True), nullable=True)  # When completed all steps
    is_converted = Column(Boolean, nullable=False, default=False)

    # Current progress
    current_step = Column(Integer, nullable=False, default=1)  # 1-indexed
    completed_steps = Column(Integer, nullable=False, default=1)

    # Step completion timestamps
    # Format: {"1": "2024-01-01T...", "2": "2024-01-02T...", ...}
    step_timestamps = Column(JSONB, nullable=False, default=dict)

    # Time analysis
    total_duration_seconds = Column(Integer, nullable=True)  # Time from step 1 to final step

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    funnel = relationship("CDPFunnel", backref="entries")
    profile = relationship("CDPProfile", backref="funnel_entries")

    __table_args__ = (
        Index("ix_cdp_funnel_entries_tenant", "tenant_id"),
        Index("ix_cdp_funnel_entries_funnel", "funnel_id"),
        Index("ix_cdp_funnel_entries_profile", "profile_id"),
        Index("ix_cdp_funnel_entries_converted", "funnel_id", "is_converted"),
        # One entry per profile per funnel (for now - could support multiple journeys later)
        UniqueConstraint(
            "tenant_id", "funnel_id", "profile_id", name="uq_cdp_funnel_entries_funnel_profile"
        ),
    )
