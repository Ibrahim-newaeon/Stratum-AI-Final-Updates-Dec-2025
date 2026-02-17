# =============================================================================
# Stratum AI - Pydantic Schemas
# =============================================================================
"""
Pydantic models for API request/response validation.
Implements strict type validation with comprehensive field constraints.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.models import (
    AdPlatform,
    AssetType,
    AuditAction,
    CampaignStatus,
    RuleAction,
    RuleOperator,
    RuleStatus,
    UserRole,
)


# =============================================================================
# Generic Response Wrapper
# =============================================================================
DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper."""

    success: bool = True
    data: Optional[DataT] = None
    message: Optional[str] = None
    errors: Optional[List[dict]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated list response."""

    items: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Base Schemas
# =============================================================================
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampMixin(BaseModel):
    """Timestamp fields mixin."""

    created_at: datetime
    updated_at: datetime


# =============================================================================
# Auth Schemas
# =============================================================================
class TokenPayload(BaseSchema):
    """JWT token payload."""

    sub: str
    exp: datetime
    type: str
    tenant_id: Optional[int] = None
    role: Optional[str] = None


class TokenResponse(BaseSchema):
    """Authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseSchema):
    """Login request body."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseSchema):
    """Token refresh request."""

    refresh_token: str


# =============================================================================
# Tenant Schemas
# =============================================================================
class TenantBase(BaseSchema):
    """Base tenant fields."""

    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    domain: Optional[str] = Field(None, max_length=255)


class TenantCreate(TenantBase):
    """Tenant creation request."""

    plan: str = Field(default="free", max_length=50)


class TenantUpdate(BaseSchema):
    """Tenant update request."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    settings: Optional[dict] = None
    feature_flags: Optional[dict] = None


class TenantResponse(TenantBase, TimestampMixin):
    """Tenant response."""

    id: int
    plan: str
    plan_expires_at: Optional[datetime]
    max_users: int
    max_campaigns: int
    settings: dict
    feature_flags: dict


# =============================================================================
# User Schemas
# =============================================================================
class UserBase(BaseSchema):
    """Base user fields."""

    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.ANALYST
    locale: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)


class UserCreate(UserBase):
    """User creation request."""

    password: str = Field(..., min_length=8, max_length=128)
    tenant_id: int

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """User update request."""

    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[HttpUrl] = None
    locale: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    preferences: Optional[dict] = None


class UserResponse(UserBase, TimestampMixin):
    """User response (excludes sensitive fields)."""

    id: int
    tenant_id: int
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    avatar_url: Optional[str]


class UserProfileResponse(UserResponse):
    """Extended user profile response."""

    phone: Optional[str]
    preferences: dict
    consent_marketing: bool
    consent_analytics: bool


# =============================================================================
# Campaign Schemas
# =============================================================================
class CampaignBase(BaseSchema):
    """Base campaign fields."""

    name: str = Field(..., min_length=1, max_length=500)
    platform: AdPlatform
    status: CampaignStatus = CampaignStatus.DRAFT
    objective: Optional[str] = Field(None, max_length=100)


class CampaignCreate(CampaignBase):
    """Campaign creation request."""

    external_id: str = Field(..., max_length=255)
    account_id: str = Field(..., max_length=255)
    daily_budget_cents: Optional[int] = Field(None, ge=0)
    lifetime_budget_cents: Optional[int] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    targeting_age_min: Optional[int] = Field(None, ge=13, le=100)
    targeting_age_max: Optional[int] = Field(None, ge=13, le=100)
    targeting_genders: Optional[List[str]] = None
    targeting_locations: Optional[List[dict]] = None
    targeting_interests: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_dates(self):
        """Ensure end_date is after start_date."""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="after")
    def validate_age_range(self):
        """Ensure age_max >= age_min."""
        if self.targeting_age_min and self.targeting_age_max:
            if self.targeting_age_max < self.targeting_age_min:
                raise ValueError("targeting_age_max must be >= targeting_age_min")
        return self


class CampaignUpdate(BaseSchema):
    """Campaign update request."""

    name: Optional[str] = Field(None, max_length=500)
    status: Optional[CampaignStatus] = None
    daily_budget_cents: Optional[int] = Field(None, ge=0)
    lifetime_budget_cents: Optional[int] = Field(None, ge=0)
    labels: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignMetricsUpdate(BaseSchema):
    """Campaign metrics sync update."""

    impressions: int = Field(..., ge=0)
    clicks: int = Field(..., ge=0)
    conversions: int = Field(..., ge=0)
    spend_cents: int = Field(..., ge=0)
    revenue_cents: int = Field(..., ge=0)


class CampaignResponse(CampaignBase, TimestampMixin):
    """Campaign response."""

    id: int
    tenant_id: int
    external_id: str
    account_id: str

    # Budget
    daily_budget_cents: Optional[int]
    lifetime_budget_cents: Optional[int]
    total_spend_cents: int
    currency: str

    # Metrics
    impressions: int
    clicks: int
    conversions: int
    revenue_cents: int

    # Computed Metrics
    ctr: Optional[float]
    cpc_cents: Optional[int]
    cpm_cents: Optional[int]
    cpa_cents: Optional[int]
    roas: Optional[float]

    # Targeting
    targeting_age_min: Optional[int]
    targeting_age_max: Optional[int]
    targeting_genders: Optional[List[str]]
    targeting_locations: Optional[List[dict]]

    # Dates
    start_date: Optional[date]
    end_date: Optional[date]
    labels: List[str]
    last_synced_at: Optional[datetime]


class CampaignDetailResponse(CampaignResponse):
    """Detailed campaign response with demographics."""

    demographics_age: Optional[dict]
    demographics_gender: Optional[dict]
    demographics_location: Optional[dict]


class CampaignListResponse(BaseSchema):
    """Campaign list item (lighter response)."""

    id: int
    name: str
    platform: AdPlatform
    status: CampaignStatus
    total_spend_cents: int
    impressions: int
    clicks: int
    conversions: int
    roas: Optional[float]
    labels: List[str]
    last_synced_at: Optional[datetime]


# =============================================================================
# Campaign Metrics (Time Series) Schemas
# =============================================================================
class CampaignMetricResponse(BaseSchema):
    """Daily campaign metric response."""

    date: date
    impressions: int
    clicks: int
    conversions: int
    spend_cents: int
    revenue_cents: int
    video_views: Optional[int]
    video_completions: Optional[int]


class CampaignMetricsTimeSeriesResponse(BaseSchema):
    """Time series metrics response."""

    campaign_id: int
    date_range: dict  # {"start": date, "end": date}
    metrics: List[CampaignMetricResponse]
    aggregated: dict  # Summary stats


# =============================================================================
# Creative Asset Schemas
# =============================================================================
class CreativeAssetBase(BaseSchema):
    """Base creative asset fields."""

    name: str = Field(..., min_length=1, max_length=500)
    asset_type: AssetType
    tags: List[str] = Field(default_factory=list)
    folder: Optional[str] = Field(None, max_length=255)


class CreativeAssetCreate(CreativeAssetBase):
    """Creative asset creation request."""

    file_url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    campaign_id: Optional[int] = None
    file_size_bytes: Optional[int] = Field(None, ge=0)
    file_format: Optional[str] = Field(None, max_length=50)
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    duration_seconds: Optional[float] = Field(None, ge=0)


class CreativeAssetUpdate(BaseSchema):
    """Creative asset update request."""

    name: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None
    folder: Optional[str] = Field(None, max_length=255)
    campaign_id: Optional[int] = None


class CreativeAssetResponse(CreativeAssetBase, TimestampMixin):
    """Creative asset response."""

    id: int
    tenant_id: int
    campaign_id: Optional[int]
    file_url: str
    thumbnail_url: Optional[str]

    # File metadata
    file_size_bytes: Optional[int]
    file_format: Optional[str]
    width: Optional[int]
    height: Optional[int]
    duration_seconds: Optional[float]

    # Performance
    impressions: int
    clicks: int
    ctr: Optional[float]

    # Fatigue
    fatigue_score: float
    first_used_at: Optional[datetime]
    times_used: int

    # AI metadata
    ai_description: Optional[str]
    ai_tags: Optional[List[str]]
    brand_safety_score: Optional[float]


# =============================================================================
# Rule Schemas (Automation Engine - Module C)
# =============================================================================
class RuleCondition(BaseSchema):
    """Rule condition specification."""

    field: str = Field(..., max_length=100)
    operator: RuleOperator
    value: str = Field(..., max_length=255)
    duration_hours: int = Field(default=24, ge=1, le=720)


class RuleActionConfig(BaseSchema):
    """Rule action configuration."""

    action_type: RuleAction
    config: dict = Field(default_factory=dict)


class RuleBase(BaseSchema):
    """Base rule fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: RuleStatus = RuleStatus.DRAFT


class RuleCreate(RuleBase):
    """Rule creation request."""

    condition_field: str = Field(..., max_length=100)
    condition_operator: RuleOperator
    condition_value: str = Field(..., max_length=255)
    condition_duration_hours: int = Field(default=24, ge=1, le=720)
    action_type: RuleAction
    action_config: dict = Field(default_factory=dict)
    applies_to_campaigns: Optional[List[int]] = None
    applies_to_platforms: Optional[List[AdPlatform]] = None
    cooldown_hours: int = Field(default=24, ge=1, le=168)


class RuleUpdate(BaseSchema):
    """Rule update request."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[RuleStatus] = None
    condition_field: Optional[str] = Field(None, max_length=100)
    condition_operator: Optional[RuleOperator] = None
    condition_value: Optional[str] = Field(None, max_length=255)
    condition_duration_hours: Optional[int] = Field(None, ge=1, le=720)
    action_type: Optional[RuleAction] = None
    action_config: Optional[dict] = None
    applies_to_campaigns: Optional[List[int]] = None
    applies_to_platforms: Optional[List[AdPlatform]] = None
    cooldown_hours: Optional[int] = Field(None, ge=1, le=168)


class RuleResponse(RuleBase, TimestampMixin):
    """Rule response."""

    id: int
    tenant_id: int
    condition_field: str
    condition_operator: RuleOperator
    condition_value: str
    condition_duration_hours: int
    action_type: RuleAction
    action_config: dict
    applies_to_campaigns: Optional[List[int]]
    applies_to_platforms: Optional[List[str]]
    cooldown_hours: int
    last_evaluated_at: Optional[datetime]
    last_triggered_at: Optional[datetime]
    trigger_count: int


class RuleExecutionResponse(BaseSchema):
    """Rule execution log response."""

    id: int
    rule_id: int
    campaign_id: Optional[int]
    executed_at: datetime
    triggered: bool
    condition_result: dict
    action_result: Optional[dict]
    error: Optional[str]


# =============================================================================
# Competitor Benchmark Schemas (Module D)
# =============================================================================
class CompetitorBase(BaseSchema):
    """Base competitor fields."""

    domain: str = Field(..., min_length=3, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    is_primary: bool = False
    fb_page_name: Optional[str] = Field(None, max_length=255, description="Facebook page name for direct Ads Library search")


class CompetitorCreate(CompetitorBase):
    """Competitor creation request."""

    pass


class CompetitorUpdate(BaseSchema):
    """Competitor update request."""

    name: Optional[str] = Field(None, max_length=255)
    is_primary: Optional[bool] = None


class CompetitorResponse(CompetitorBase, TimestampMixin):
    """Competitor benchmark response."""

    id: int
    tenant_id: int

    # Scraped metadata
    meta_title: Optional[str]
    meta_description: Optional[str]
    meta_keywords: Optional[List[str]]
    social_links: Optional[dict]

    # Market intelligence
    estimated_traffic: Optional[int]
    traffic_trend: Optional[str]
    top_keywords: Optional[List[dict]]
    paid_keywords_count: Optional[int]
    organic_keywords_count: Optional[int]

    # Share of voice
    share_of_voice: Optional[float]
    category_rank: Optional[int]

    # Ad intelligence
    estimated_ad_spend_cents: Optional[int]
    detected_ad_platforms: Optional[List[str]]
    ad_creatives_count: Optional[int]

    # Metadata
    data_source: str
    last_fetched_at: Optional[datetime]
    fetch_error: Optional[str]


class CompetitorShareOfVoiceResponse(BaseSchema):
    """Share of voice comparison response."""

    competitors: List[dict]  # [{domain, share, trend}]
    total_market: int
    date_range: dict


# =============================================================================
# ML / Simulator Schemas (Module A)
# =============================================================================
class SimulationRequest(BaseSchema):
    """What-If simulator request."""

    campaign_id: Optional[int] = None
    budget_change_percent: float = Field(..., ge=-100, le=1000)
    days_ahead: int = Field(default=30, ge=1, le=365)
    include_confidence_interval: bool = True


class SimulationResponse(BaseSchema):
    """What-If simulator response."""

    campaign_id: Optional[int]
    current_metrics: dict
    predicted_metrics: dict
    budget_change_percent: float
    confidence_interval: Optional[dict]  # {"lower": float, "upper": float}
    feature_importances: Optional[dict]
    model_version: str


class ROASForecastRequest(BaseSchema):
    """ROAS forecasting request."""

    campaign_ids: Optional[List[int]] = None
    days_ahead: int = Field(default=30, ge=1, le=365)
    granularity: str = Field(default="daily", pattern=r"^(daily|weekly|monthly)$")


class ROASForecastResponse(BaseSchema):
    """ROAS forecasting response."""

    forecasts: List[dict]  # [{date, predicted_roas, confidence_lower, confidence_upper}]
    model_version: str
    generated_at: datetime


class ConversionPredictionRequest(BaseSchema):
    """Conversion prediction request."""

    campaign_id: int
    features: dict  # Custom feature values for prediction


class ConversionPredictionResponse(BaseSchema):
    """Conversion prediction response."""

    campaign_id: int
    predicted_conversions: float
    predicted_conversion_rate: float
    confidence: float
    factors: List[dict]  # Contributing factors


# =============================================================================
# Audit Log Schemas (Module F)
# =============================================================================
class AuditLogResponse(BaseSchema):
    """Audit log entry response."""

    id: int
    tenant_id: int
    user_id: Optional[int]
    action: AuditAction
    resource_type: str
    resource_id: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    changed_fields: Optional[List[str]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    endpoint: Optional[str]
    http_method: Optional[str]
    created_at: datetime


class AuditLogFilter(BaseSchema):
    """Audit log query filters."""

    user_id: Optional[int] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# =============================================================================
# GDPR Compliance Schemas
# =============================================================================
class GDPRExportRequest(BaseSchema):
    """GDPR data export request."""

    user_id: int
    include_audit_logs: bool = True
    include_campaigns: bool = True
    format: str = Field(default="json", pattern=r"^(json|csv)$")


class GDPRAnonymizeRequest(BaseSchema):
    """GDPR anonymization (right to be forgotten) request."""

    user_id: int
    confirmation: str = Field(..., pattern=r"^CONFIRM_DELETE$")


class GDPRAnonymizeResponse(BaseSchema):
    """GDPR anonymization response."""

    user_id: int
    anonymized_at: datetime
    tables_affected: List[str]
    records_modified: int


# =============================================================================
# Health & Status Schemas
# =============================================================================
class HealthResponse(BaseSchema):
    """Health check response."""

    status: str
    version: str
    environment: str
    database: str
    redis: str
    uptime_seconds: float


class SyncStatusResponse(BaseSchema):
    """Data sync status response."""

    platform: AdPlatform
    last_sync_at: Optional[datetime]
    next_sync_at: Optional[datetime]
    status: str  # 'idle', 'syncing', 'error'
    error_message: Optional[str]
    records_synced: int


# =============================================================================
# Dashboard / Analytics Schemas
# =============================================================================
class KPITileResponse(BaseSchema):
    """KPI tile data for dashboard."""

    metric: str
    value: float
    previous_value: Optional[float]
    change_percent: Optional[float]
    trend: str  # 'up', 'down', 'stable'
    period: str  # 'today', '7d', '30d'


class DemographicsResponse(BaseSchema):
    """Demographics breakdown response."""

    age_breakdown: List[dict]  # [{range: "18-24", impressions: 1000, ...}]
    gender_breakdown: List[dict]  # [{gender: "male", impressions: 500, ...}]
    location_breakdown: List[dict]  # [{country: "US", state: "CA", ...}]


class HeatmapDataResponse(BaseSchema):
    """Location heatmap data response."""

    points: List[dict]  # [{lat, lng, weight, ...}]
    bounds: dict  # {"ne": {lat, lng}, "sw": {lat, lng}}
    aggregation: str  # 'country', 'state', 'city'


# =============================================================================
# Notification Schemas
# =============================================================================
class NotificationPreferenceUpdate(BaseSchema):
    """Notification preference update request."""

    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    slack_webhook_url: Optional[str] = Field(None, max_length=500)
    alert_rule_triggered: Optional[bool] = None
    alert_budget_threshold: Optional[bool] = None
    alert_performance_drop: Optional[bool] = None
    alert_sync_failure: Optional[bool] = None
    report_daily: Optional[bool] = None
    report_weekly: Optional[bool] = None
    report_monthly: Optional[bool] = None


class NotificationPreferenceResponse(BaseSchema):
    """Notification preference response."""

    id: int
    user_id: int
    email_enabled: bool
    slack_enabled: bool
    slack_webhook_url: Optional[str]
    alert_rule_triggered: bool
    alert_budget_threshold: bool
    alert_performance_drop: bool
    alert_sync_failure: bool
    report_daily: bool
    report_weekly: bool
    report_monthly: bool


# =============================================================================
# WebSocket / SSE Schemas
# =============================================================================
class RealtimeEvent(BaseSchema):
    """Real-time event payload for SSE/WebSocket."""

    event_type: str  # 'sync_complete', 'rule_triggered', 'metric_update'
    payload: dict
    timestamp: datetime
    tenant_id: int
