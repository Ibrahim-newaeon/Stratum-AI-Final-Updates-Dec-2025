# =============================================================================
# Stratum AI - CDP Pydantic Schemas
# =============================================================================
"""
Pydantic schemas for CDP API request/response validation.

Schemas:
- Event ingestion (single + batch)
- Profile responses
- Source management
- Consent handling
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# Base Configuration
# =============================================================================

class CDPBaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# =============================================================================
# Identifier Schemas
# =============================================================================

class IdentifierInput(BaseModel):
    """Single identifier in an event."""
    type: str = Field(..., description="Identifier type: email, phone, device_id, anonymous_id, external_id")
    value: str = Field(..., min_length=1, max_length=512, description="Identifier value")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"email", "phone", "device_id", "anonymous_id", "external_id"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid identifier type. Allowed: {allowed}")
        return v.lower()


class IdentifierResponse(CDPBaseSchema):
    """Identifier in API responses."""
    id: UUID
    identifier_type: str
    identifier_value: Optional[str] = None
    identifier_hash: str
    is_primary: bool
    confidence_score: Decimal
    verified_at: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime


# =============================================================================
# Event Schemas
# =============================================================================

class EventContext(BaseModel):
    """Context data for an event (device, geo, campaign info)."""
    user_agent: Optional[str] = Field(None, max_length=1024)
    ip: Optional[str] = Field(None, max_length=45)
    locale: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    screen: Optional[Dict[str, int]] = None
    campaign: Optional[Dict[str, str]] = None


class EventConsent(BaseModel):
    """Consent flags sent with event."""
    analytics: Optional[bool] = None
    ads: Optional[bool] = None
    email: Optional[bool] = None
    sms: Optional[bool] = None


class EventInput(BaseModel):
    """Single event for ingestion."""
    event_name: str = Field(..., min_length=1, max_length=255, description="Event name (e.g., PageView, Purchase)")
    event_time: datetime = Field(..., description="When the event occurred (ISO8601)")
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Unique key for deduplication")

    identifiers: List[IdentifierInput] = Field(..., min_length=1, description="At least one identifier required")

    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event-specific properties")
    context: Optional[EventContext] = Field(default=None, description="Device, geo, campaign context")
    consent: Optional[EventConsent] = Field(default=None, description="Consent flags")

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        # Allow alphanumeric, spaces, underscores, dashes
        import re
        if not re.match(r"^[\w\s\-]+$", v):
            raise ValueError("Event name can only contain letters, numbers, spaces, underscores, and dashes")
        return v


class EventBatchInput(BaseModel):
    """Batch of events for ingestion."""
    events: List[EventInput] = Field(..., min_length=1, max_length=1000, description="Events to ingest (max 1000)")


class EventIngestResult(BaseModel):
    """Result for a single event ingestion."""
    event_id: Optional[UUID] = None
    status: str  # "accepted", "rejected", "duplicate"
    profile_id: Optional[UUID] = None
    error: Optional[str] = None


class EventBatchResponse(BaseModel):
    """Response for batch event ingestion."""
    accepted: int
    rejected: int
    duplicates: int
    results: List[EventIngestResult]


class EventResponse(CDPBaseSchema):
    """Event in API responses."""
    id: UUID
    event_name: str
    event_time: datetime
    received_at: datetime
    properties: Dict[str, Any]
    context: Dict[str, Any]
    emq_score: Optional[Decimal] = None
    processed: bool


# =============================================================================
# Profile Schemas
# =============================================================================

class ProfileResponse(CDPBaseSchema):
    """Full profile response with identifiers and metadata."""
    id: UUID
    tenant_id: int
    external_id: Optional[str] = None

    first_seen_at: datetime
    last_seen_at: datetime

    profile_data: Dict[str, Any]
    computed_traits: Dict[str, Any]

    lifecycle_stage: str

    total_events: int
    total_sessions: int
    total_purchases: int
    total_revenue: Decimal

    identifiers: List[IdentifierResponse] = []

    created_at: datetime
    updated_at: datetime


class ProfileListResponse(BaseModel):
    """Paginated list of profiles."""
    profiles: List[ProfileResponse]
    total: int
    page: int
    page_size: int


class ProfileLookupParams(BaseModel):
    """Parameters for profile lookup by identifier."""
    identifier_type: str = Field(..., description="Type of identifier (email, phone, etc.)")
    identifier_value: str = Field(..., description="Value to look up")


# =============================================================================
# Source Schemas
# =============================================================================

class SourceCreate(BaseModel):
    """Create a new data source."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable source name")
    source_type: str = Field(..., description="Source type: website, server, sgtm, import, crm")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Source-specific configuration")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"website", "server", "sgtm", "import", "crm"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid source type. Allowed: {allowed}")
        return v.lower()


class SourceResponse(CDPBaseSchema):
    """Data source in API responses."""
    id: UUID
    name: str
    source_type: str
    source_key: str
    config: Dict[str, Any]
    is_active: bool
    event_count: int
    last_event_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SourceListResponse(BaseModel):
    """List of data sources."""
    sources: List[SourceResponse]
    total: int


# =============================================================================
# Consent Schemas
# =============================================================================

class ConsentUpdate(BaseModel):
    """Update consent for a profile."""
    consent_type: str = Field(..., description="Consent type: analytics, ads, email, sms, all")
    granted: bool = Field(..., description="Whether consent is granted")
    source: Optional[str] = Field(None, description="Where consent was collected")
    consent_text: Optional[str] = Field(None, description="Legal text shown to user")
    consent_version: Optional[str] = Field(None, description="Version of consent form")

    @field_validator("consent_type")
    @classmethod
    def validate_consent_type(cls, v: str) -> str:
        allowed = {"analytics", "ads", "email", "sms", "all"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid consent type. Allowed: {allowed}")
        return v.lower()


class ConsentResponse(CDPBaseSchema):
    """Consent record in API responses."""
    id: UUID
    consent_type: str
    granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    source: Optional[str] = None
    consent_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# EMQ (Event Match Quality) Schemas
# =============================================================================

class EMQScoreResponse(BaseModel):
    """EMQ score breakdown for an event or batch."""
    overall_score: Decimal = Field(..., description="Overall EMQ score (0-100)")
    identifier_quality: Decimal = Field(..., description="Score for identifier quality (0-40)")
    data_completeness: Decimal = Field(..., description="Score for data completeness (0-25)")
    timeliness: Decimal = Field(..., description="Score for event timeliness (0-20)")
    context_richness: Decimal = Field(..., description="Score for context data (0-15)")


# =============================================================================
# API Response Wrappers
# =============================================================================

class CDPAPIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# Webhook Schemas
# =============================================================================

class WebhookCreate(BaseModel):
    """Create a new webhook destination."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable webhook name")
    url: str = Field(..., min_length=1, max_length=2048, description="Webhook destination URL (HTTPS)")
    event_types: List[str] = Field(
        ...,
        min_length=1,
        description="Event types to trigger on: event.received, profile.created, profile.updated, profile.merged, consent.updated, all"
    )
    max_retries: int = Field(3, ge=0, le=10, description="Max retry attempts on failure")
    timeout_seconds: int = Field(30, ge=5, le=120, description="Request timeout in seconds")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("https://", "http://localhost")):
            raise ValueError("Webhook URL must use HTTPS (http://localhost allowed for testing)")
        return v

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: List[str]) -> List[str]:
        allowed = {"event.received", "profile.created", "profile.updated", "profile.merged", "consent.updated", "all"}
        for event_type in v:
            if event_type not in allowed:
                raise ValueError(f"Invalid event type '{event_type}'. Allowed: {allowed}")
        return v


class WebhookUpdate(BaseModel):
    """Update an existing webhook."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, min_length=1, max_length=2048)
    event_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=120)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(("https://", "http://localhost")):
            raise ValueError("Webhook URL must use HTTPS (http://localhost allowed for testing)")
        return v

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        allowed = {"event.received", "profile.created", "profile.updated", "profile.merged", "consent.updated", "all"}
        for event_type in v:
            if event_type not in allowed:
                raise ValueError(f"Invalid event type '{event_type}'. Allowed: {allowed}")
        return v


class WebhookResponse(CDPBaseSchema):
    """Webhook in API responses."""
    id: UUID
    name: str
    url: str
    event_types: List[str]
    secret_key: Optional[str] = None  # Only returned on create
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    failure_count: int
    max_retries: int
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    """List of webhooks."""
    webhooks: List[WebhookResponse]
    total: int


class WebhookTestResult(BaseModel):
    """Result of webhook test request."""
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
