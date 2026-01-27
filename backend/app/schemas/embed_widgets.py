# =============================================================================
# Stratum AI - Embed Widget Schemas
# =============================================================================
"""
Pydantic schemas for embed widget API requests and responses.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

# =============================================================================
# Enums
# =============================================================================


class WidgetType(str, Enum):
    SIGNAL_HEALTH = "signal_health"
    ROAS_DISPLAY = "roas_display"
    CAMPAIGN_PERFORMANCE = "campaign_performance"
    TRUST_GATE_STATUS = "trust_gate_status"
    SPEND_TRACKER = "spend_tracker"
    ANOMALY_ALERT = "anomaly_alert"


class WidgetSize(str, Enum):
    BADGE = "badge"
    COMPACT = "compact"
    STANDARD = "standard"
    LARGE = "large"
    CUSTOM = "custom"


class BrandingLevel(str, Enum):
    FULL = "full"
    MINIMAL = "minimal"
    NONE = "none"


class TokenStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


# =============================================================================
# Domain Whitelist Schemas
# =============================================================================


class DomainWhitelistCreate(BaseModel):
    """Create a new whitelisted domain."""

    domain_pattern: str = Field(
        ...,
        description="Domain pattern (e.g., 'dashboard.client.com' or '*.client.com')",
        min_length=3,
        max_length=255,
    )
    description: Optional[str] = None

    @validator("domain_pattern")
    def validate_domain_pattern(cls, v):
        # Allow wildcards like *.domain.com
        pattern = r"^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(pattern, v):
            raise ValueError("Invalid domain pattern")
        return v.lower()


class DomainWhitelistResponse(BaseModel):
    """Domain whitelist entry response."""

    id: UUID
    domain_pattern: str
    is_verified: bool
    is_active: bool
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Widget Schemas
# =============================================================================


class WidgetDataScope(BaseModel):
    """Scope configuration for widget data access."""

    campaigns: Optional[list[str]] = Field(default=None, description="Specific campaign IDs")
    ad_accounts: Optional[list[str]] = Field(default=None, description="Specific ad account IDs")
    date_range_days: int = Field(default=30, ge=1, le=365, description="Data lookback period")


class WidgetCustomBranding(BaseModel):
    """Custom branding options (Enterprise only)."""

    custom_logo_url: Optional[str] = Field(default=None, max_length=512)
    custom_accent_color: Optional[str] = Field(default=None, regex=r"^#[0-9A-Fa-f]{6}$")
    custom_background_color: Optional[str] = Field(default=None, regex=r"^#[0-9A-Fa-f]{6}$")
    custom_text_color: Optional[str] = Field(default=None, regex=r"^#[0-9A-Fa-f]{6}$")


class WidgetCreate(BaseModel):
    """Create a new embed widget."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    widget_type: WidgetType
    widget_size: WidgetSize = WidgetSize.STANDARD

    # Custom dimensions
    custom_width: Optional[int] = Field(default=None, ge=100, le=1200)
    custom_height: Optional[int] = Field(default=None, ge=50, le=800)

    # Data scope
    data_scope: Optional[WidgetDataScope] = None

    # Refresh interval
    refresh_interval_seconds: int = Field(default=300, ge=60, le=3600)

    # Custom branding (Enterprise only - validated at service layer)
    custom_branding: Optional[WidgetCustomBranding] = None

    @validator("custom_width", "custom_height", always=True)
    def validate_custom_dimensions(cls, v, values):
        if values.get("widget_size") == WidgetSize.CUSTOM and v is None:
            raise ValueError("Custom dimensions required when widget_size is 'custom'")
        return v


class WidgetUpdate(BaseModel):
    """Update an existing widget."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    widget_size: Optional[WidgetSize] = None
    custom_width: Optional[int] = Field(default=None, ge=100, le=1200)
    custom_height: Optional[int] = Field(default=None, ge=50, le=800)
    data_scope: Optional[WidgetDataScope] = None
    refresh_interval_seconds: Optional[int] = Field(default=None, ge=60, le=3600)
    custom_branding: Optional[WidgetCustomBranding] = None
    is_active: Optional[bool] = None


class WidgetResponse(BaseModel):
    """Widget configuration response."""

    id: UUID
    name: str
    description: Optional[str]
    widget_type: WidgetType
    widget_size: WidgetSize
    custom_width: Optional[int]
    custom_height: Optional[int]
    branding_level: BrandingLevel
    data_scope: dict[str, Any]
    refresh_interval_seconds: int
    is_active: bool
    total_views: int
    created_at: datetime
    updated_at: datetime

    # Custom branding (only for Enterprise)
    custom_logo_url: Optional[str] = None
    custom_accent_color: Optional[str] = None
    custom_background_color: Optional[str] = None
    custom_text_color: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Token Schemas
# =============================================================================


class TokenCreate(BaseModel):
    """Create a new embed token for a widget."""

    allowed_domains: list[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Domains where this token can be used",
    )
    expires_in_days: int = Field(default=30, ge=1, le=365)

    @validator("allowed_domains", each_item=True)
    def validate_domains(cls, v):
        pattern = r"^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid domain: {v}")
        return v.lower()


class TokenCreateResponse(BaseModel):
    """Response after creating a token (includes the actual token once)."""

    id: UUID
    token: str  # Only returned once at creation!
    refresh_token: str  # Only returned once at creation!
    token_prefix: str
    allowed_domains: list[str]
    expires_at: datetime
    rate_limit_per_minute: int

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token information response (without actual token)."""

    id: UUID
    token_prefix: str
    allowed_domains: list[str]
    status: TokenStatus
    expires_at: datetime
    last_used_at: Optional[datetime]
    total_requests: int
    total_errors: int
    created_at: datetime

    class Config:
        from_attributes = True


class TokenRefresh(BaseModel):
    """Refresh an embed token."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Response after refreshing a token."""

    token: str
    refresh_token: str
    expires_at: datetime


# =============================================================================
# Widget Data Schemas (for embed endpoint responses)
# =============================================================================


class SignalHealthData(BaseModel):
    """Data for signal health widget."""

    overall_score: int = Field(..., ge=0, le=100)
    status: str  # healthy, degraded, unhealthy
    platforms: dict[str, int]  # platform -> score
    last_updated: datetime


class ROASData(BaseModel):
    """Data for ROAS display widget."""

    blended_roas: float
    trend: str  # up, down, stable
    trend_percentage: float
    period: str
    last_updated: datetime


class TrustGateData(BaseModel):
    """Data for trust gate status widget."""

    status: str  # pass, hold, block
    signal_health: int
    automation_mode: str
    pending_actions: int
    last_updated: datetime


class SpendTrackerData(BaseModel):
    """Data for spend tracker widget."""

    total_spend: float
    budget: Optional[float]
    utilization_percentage: Optional[float]
    currency: str
    period: str
    last_updated: datetime


class AnomalyAlertData(BaseModel):
    """Data for anomaly alert widget."""

    has_anomalies: bool
    anomaly_count: int
    severity: str  # none, low, medium, high
    most_recent: Optional[str]
    last_updated: datetime


class CampaignPerformanceData(BaseModel):
    """Data for campaign performance widget."""

    campaigns: list[dict[str, Any]]
    total_campaigns: int
    top_performer: Optional[str]
    last_updated: datetime


# =============================================================================
# Embed Code Response
# =============================================================================


class EmbedCodeResponse(BaseModel):
    """Generated embed code for a widget."""

    widget_id: UUID
    iframe_code: str
    script_code: str
    preview_url: str
    documentation_url: str


# =============================================================================
# Widget Render Request (from embed endpoint)
# =============================================================================


class WidgetRenderRequest(BaseModel):
    """Request to render widget data (validated from token)."""

    token: str
    origin: str


class WidgetRenderResponse(BaseModel):
    """Rendered widget data response."""

    widget_type: WidgetType
    branding_level: BrandingLevel
    data: dict[str, Any]
    config: dict[str, Any]
    signature: str  # HMAC signature for data integrity
    expires_at: datetime
