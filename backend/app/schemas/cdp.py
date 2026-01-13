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


# =============================================================================
# Identity Graph Schemas
# =============================================================================

class IdentityLinkResponse(CDPBaseSchema):
    """Identity link (graph edge) in API responses."""
    id: UUID
    source_identifier_id: UUID
    target_identifier_id: UUID
    link_type: str
    confidence_score: Decimal
    is_active: bool
    evidence: Dict[str, Any] = {}
    verified_at: Optional[datetime] = None
    created_at: datetime


class IdentityGraphNode(BaseModel):
    """Node in identity graph (represents an identifier)."""
    id: str
    type: str
    hash: str  # Truncated hash for display
    is_primary: bool
    priority: int


class IdentityGraphEdge(BaseModel):
    """Edge in identity graph (represents a link)."""
    source: str
    target: str
    type: str
    confidence: float


class IdentityGraphResponse(BaseModel):
    """Complete identity graph for a profile."""
    profile_id: UUID
    nodes: List[IdentityGraphNode]
    edges: List[IdentityGraphEdge]
    total_identifiers: int
    total_links: int


class ProfileMergeRequest(BaseModel):
    """Request to manually merge two profiles."""
    source_profile_id: UUID = Field(..., description="Profile to be merged (will be deleted)")
    target_profile_id: UUID = Field(..., description="Profile to keep (will receive data)")
    reason: Optional[str] = Field("manual_merge", description="Reason for merge")


class ProfileMergeResponse(CDPBaseSchema):
    """Profile merge result in API responses."""
    id: UUID
    surviving_profile_id: Optional[UUID]
    merged_profile_id: UUID
    merge_reason: str
    merged_event_count: int
    merged_identifier_count: int
    is_rolled_back: bool
    created_at: datetime


class ProfileMergeHistoryResponse(BaseModel):
    """List of profile merges."""
    merges: List[ProfileMergeResponse]
    total: int


class CanonicalIdentityResponse(CDPBaseSchema):
    """Canonical identity for a profile."""
    id: UUID
    profile_id: UUID
    canonical_type: Optional[str]
    canonical_value_hash: Optional[str]
    priority_score: int
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Segment Schemas
# =============================================================================

class SegmentCondition(BaseModel):
    """Single condition in segment rules."""
    field: str = Field(..., description="Field path: profile.lifecycle_stage, event.PageView.count, trait.ltv")
    operator: str = Field(..., description="Comparison operator: equals, greater_than, contains, etc.")
    value: Any = Field(..., description="Value to compare against")


class SegmentRules(BaseModel):
    """Segment rules definition."""
    logic: str = Field("and", description="Logic operator: and, or")
    conditions: List[SegmentCondition] = Field(default_factory=list)
    groups: Optional[List["SegmentRules"]] = Field(default=None, description="Nested rule groups")


class SegmentCreate(BaseModel):
    """Create a new segment."""
    name: str = Field(..., min_length=1, max_length=255, description="Segment name")
    description: Optional[str] = Field(None, max_length=1000)
    segment_type: str = Field("dynamic", description="Segment type: static, dynamic, computed")
    rules: SegmentRules = Field(..., description="Segment rules/conditions")
    tags: Optional[List[str]] = Field(default_factory=list)
    auto_refresh: bool = Field(True, description="Auto-refresh segment membership")
    refresh_interval_hours: int = Field(24, ge=1, le=168, description="Hours between refreshes")

    @field_validator("segment_type")
    @classmethod
    def validate_segment_type(cls, v: str) -> str:
        allowed = {"static", "dynamic", "computed"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid segment type. Allowed: {allowed}")
        return v.lower()


class SegmentUpdate(BaseModel):
    """Update a segment."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rules: Optional[SegmentRules] = None
    tags: Optional[List[str]] = None
    auto_refresh: Optional[bool] = None
    refresh_interval_hours: Optional[int] = Field(None, ge=1, le=168)


class SegmentResponse(CDPBaseSchema):
    """Segment in API responses."""
    id: UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    segment_type: str
    status: str
    rules: Dict[str, Any]
    profile_count: int
    last_computed_at: Optional[datetime]
    computation_duration_ms: Optional[int]
    auto_refresh: bool
    refresh_interval_hours: int
    next_refresh_at: Optional[datetime]
    tags: List[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class SegmentListResponse(BaseModel):
    """List of segments."""
    segments: List[SegmentResponse]
    total: int


class SegmentPreviewRequest(BaseModel):
    """Request to preview segment membership."""
    rules: SegmentRules
    limit: int = Field(100, ge=1, le=500)


class SegmentPreviewResponse(BaseModel):
    """Preview of segment membership."""
    estimated_count: int
    sample_profiles: List[ProfileResponse]


class SegmentMembershipResponse(BaseModel):
    """Profile membership in a segment."""
    profile_id: UUID
    segment_id: UUID
    added_at: datetime
    is_active: bool
    match_score: Optional[float]


class SegmentProfilesResponse(BaseModel):
    """Profiles in a segment."""
    profiles: List[ProfileResponse]
    total: int


class ProfileSegmentsResponse(BaseModel):
    """Segments a profile belongs to."""
    segments: List[SegmentResponse]


# =============================================================================
# Profile Deletion (GDPR) Schemas
# =============================================================================

class ProfileDeletionRequest(BaseModel):
    """Request to delete a profile (GDPR right to erasure)."""
    profile_id: UUID
    reason: Optional[str] = Field(None, description="Reason for deletion")
    delete_events: bool = Field(True, description="Also delete all events")
    requester_email: Optional[str] = Field(None, description="Email of person requesting deletion")


class ProfileDeletionResponse(BaseModel):
    """Response after profile deletion."""
    profile_id: UUID
    deleted: bool
    events_deleted: int
    identifiers_deleted: int
    consents_deleted: int
    segment_memberships_deleted: int
    deletion_timestamp: datetime


# =============================================================================
# Computed Traits Schemas
# =============================================================================

class ComputedTraitSourceConfig(BaseModel):
    """Source configuration for computed traits."""
    event_name: Optional[str] = Field(None, description="Event name to compute from")
    property: Optional[str] = Field(None, description="Property to aggregate")
    time_window_days: Optional[int] = Field(None, ge=1, le=3650, description="Time window in days")


class ComputedTraitCreate(BaseModel):
    """Create a computed trait."""
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trait_type: str = Field(..., description="count, sum, average, min, max, first, last, unique_count, exists")
    source_config: ComputedTraitSourceConfig
    output_type: str = Field("number", description="number, string, boolean, date")
    default_value: Optional[str] = None

    @field_validator("trait_type")
    @classmethod
    def validate_trait_type(cls, v: str) -> str:
        allowed = {"count", "sum", "average", "min", "max", "first", "last", "unique_count", "exists", "formula"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid trait type. Allowed: {allowed}")
        return v.lower()


class ComputedTraitResponse(CDPBaseSchema):
    """Computed trait in API responses."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    trait_type: str
    source_config: Dict[str, Any]
    output_type: str
    default_value: Optional[str]
    is_active: bool
    last_computed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ComputedTraitListResponse(BaseModel):
    """List of computed traits."""
    traits: List[ComputedTraitResponse]
    total: int


class ComputeTraitsResponse(BaseModel):
    """Response after computing traits."""
    profiles_processed: int
    errors: int


# =============================================================================
# RFM Analysis Schemas
# =============================================================================

class RFMConfig(BaseModel):
    """Configuration for RFM analysis."""
    purchase_event_name: str = Field("Purchase", description="Event name for purchases")
    revenue_property: str = Field("total", description="Property containing revenue")
    analysis_window_days: int = Field(365, ge=30, le=1095, description="Analysis window in days")


class RFMScores(BaseModel):
    """RFM scores for a profile."""
    recency_days: int
    frequency: int
    monetary: float
    recency_score: int = Field(..., ge=1, le=5)
    frequency_score: int = Field(..., ge=1, le=5)
    monetary_score: int = Field(..., ge=1, le=5)
    rfm_score: int = Field(..., ge=1, le=5)
    rfm_segment: str
    analysis_window_days: int
    calculated_at: str


class RFMBatchResponse(BaseModel):
    """Response after batch RFM calculation."""
    profiles_processed: int
    segment_distribution: Dict[str, int]
    analysis_window_days: int
    calculated_at: str


class RFMSummaryResponse(BaseModel):
    """RFM summary for tenant."""
    total_profiles: int
    profiles_with_rfm: int
    segment_distribution: Dict[str, int]
    coverage_pct: float


# =============================================================================
# Funnel/Journey Schemas
# =============================================================================

class FunnelStepCondition(BaseModel):
    """Condition for funnel step matching."""
    field: str = Field(..., description="Field path: properties.category, context.campaign")
    operator: str = Field("equals", description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class FunnelStep(BaseModel):
    """Single step in a funnel definition."""
    step_name: str = Field(..., min_length=1, max_length=255, description="Display name for the step")
    event_name: str = Field(..., min_length=1, max_length=255, description="Event name to match")
    conditions: Optional[List[FunnelStepCondition]] = Field(
        default_factory=list,
        description="Additional conditions for step completion"
    )


class FunnelCreate(BaseModel):
    """Create a new funnel."""
    name: str = Field(..., min_length=1, max_length=255, description="Funnel name")
    description: Optional[str] = Field(None, max_length=1000)
    steps: List[FunnelStep] = Field(..., min_length=2, max_length=20, description="Funnel steps (2-20 steps)")
    conversion_window_days: int = Field(30, ge=1, le=365, description="Max days to complete funnel")
    step_timeout_hours: Optional[int] = Field(None, ge=1, le=720, description="Max hours between steps")
    auto_refresh: bool = Field(True, description="Auto-refresh funnel metrics")
    refresh_interval_hours: int = Field(24, ge=1, le=168, description="Hours between refreshes")
    tags: Optional[List[str]] = Field(default_factory=list)


class FunnelUpdate(BaseModel):
    """Update a funnel."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    steps: Optional[List[FunnelStep]] = Field(None, min_length=2, max_length=20)
    conversion_window_days: Optional[int] = Field(None, ge=1, le=365)
    step_timeout_hours: Optional[int] = Field(None, ge=1, le=720)
    auto_refresh: Optional[bool] = None
    refresh_interval_hours: Optional[int] = Field(None, ge=1, le=168)
    tags: Optional[List[str]] = None


class FunnelStepMetrics(BaseModel):
    """Metrics for a single funnel step."""
    step: int
    name: str
    event_name: str
    count: int
    conversion_rate: float = Field(..., description="Conversion rate from funnel start (%)")
    drop_off_rate: float = Field(..., description="Drop-off rate from previous step (%)")
    drop_off_count: int = Field(0, description="Number of profiles that dropped off")


class FunnelResponse(CDPBaseSchema):
    """Funnel in API responses."""
    id: UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    status: str
    steps: List[Dict[str, Any]]
    conversion_window_days: int
    step_timeout_hours: Optional[int]
    total_entered: int
    total_converted: int
    overall_conversion_rate: Optional[Decimal]
    step_metrics: List[Dict[str, Any]]
    last_computed_at: Optional[datetime]
    computation_duration_ms: Optional[int]
    auto_refresh: bool
    refresh_interval_hours: int
    next_refresh_at: Optional[datetime]
    tags: List[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class FunnelListResponse(BaseModel):
    """List of funnels."""
    funnels: List[FunnelResponse]
    total: int


class FunnelComputeResponse(BaseModel):
    """Response after computing funnel metrics."""
    funnel_id: str
    total_entered: int
    total_converted: int
    overall_conversion_rate: float
    step_metrics: List[FunnelStepMetrics]
    computation_duration_ms: int


class FunnelAnalysisRequest(BaseModel):
    """Request for funnel analysis with date filtering."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class FunnelStepAnalysis(BaseModel):
    """Detailed analysis for a funnel step."""
    step: int
    name: str
    event_name: str
    count: int
    conversion_rate_from_start: float
    conversion_rate_from_prev: float
    drop_off_count: int


class FunnelAnalysisResponse(BaseModel):
    """Detailed funnel analysis response."""
    funnel_id: str
    funnel_name: str
    total_entered: int
    total_converted: int
    overall_conversion_rate: float
    step_analysis: List[FunnelStepAnalysis]
    avg_conversion_time_seconds: Optional[float]
    analysis_period: Dict[str, Optional[str]]


class ProfileFunnelJourney(BaseModel):
    """A profile's journey through a funnel."""
    funnel_id: str
    funnel_name: Optional[str]
    entered_at: str
    converted_at: Optional[str]
    is_converted: bool
    current_step: int
    completed_steps: int
    total_steps: Optional[int]
    step_timestamps: Dict[str, str]
    total_duration_seconds: Optional[int]


class ProfileFunnelJourneysResponse(BaseModel):
    """List of a profile's funnel journeys."""
    profile_id: str
    journeys: List[ProfileFunnelJourney]


class FunnelDropOffResponse(BaseModel):
    """Profiles that dropped off at a specific funnel step."""
    funnel_id: str
    step: int
    profiles: List[ProfileResponse]
    total: int
