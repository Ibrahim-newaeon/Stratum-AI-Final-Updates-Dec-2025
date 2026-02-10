# =============================================================================
# Stratum AI - Client Schemas
# =============================================================================
"""
Pydantic schemas for Client CRUD, assignments, and portal invitations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# =============================================================================
# Client Schemas
# =============================================================================
class ClientCreate(BaseModel):
    """Schema for creating a new client."""

    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    logo_url: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    currency: str = Field(default="USD", max_length=3)
    timezone: str = Field(default="UTC", max_length=50)
    monthly_budget_cents: Optional[int] = Field(None, ge=0)
    target_roas: Optional[float] = Field(None, ge=0)
    target_cpa_cents: Optional[int] = Field(None, ge=0)
    target_ctr: Optional[float] = Field(None, ge=0, le=100)
    budget_alert_threshold: float = Field(default=0.9, ge=0, le=1)
    roas_alert_threshold: Optional[float] = Field(None, ge=0)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    settings: Optional[dict] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is lowercase and URL-safe."""
        return v.lower().strip()


class ClientUpdate(BaseModel):
    """Schema for updating a client. All fields optional."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    logo_url: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    currency: Optional[str] = Field(None, max_length=3)
    timezone: Optional[str] = Field(None, max_length=50)
    monthly_budget_cents: Optional[int] = Field(None, ge=0)
    target_roas: Optional[float] = Field(None, ge=0)
    target_cpa_cents: Optional[int] = Field(None, ge=0)
    target_ctr: Optional[float] = Field(None, ge=0, le=100)
    budget_alert_threshold: Optional[float] = Field(None, ge=0, le=1)
    roas_alert_threshold: Optional[float] = Field(None, ge=0)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ClientResponse(BaseModel):
    """Schema for client detail response."""

    id: int
    tenant_id: int
    name: str
    slug: str
    logo_url: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    currency: str
    timezone: str
    monthly_budget_cents: Optional[int] = None
    target_roas: Optional[float] = None
    target_cpa_cents: Optional[int] = None
    target_ctr: Optional[float] = None
    budget_alert_threshold: float
    roas_alert_threshold: Optional[float] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    settings: dict = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields populated at query time
    total_campaigns: Optional[int] = None
    total_spend_cents: Optional[int] = None
    assigned_users: Optional[list[int]] = None

    model_config = ConfigDict(from_attributes=True)


class ClientListResponse(BaseModel):
    """Lightweight schema for client list items."""

    id: int
    tenant_id: int
    name: str
    slug: str
    industry: Optional[str] = None
    currency: str
    is_active: bool
    monthly_budget_cents: Optional[int] = None
    target_roas: Optional[float] = None
    created_at: datetime

    # Computed
    total_campaigns: Optional[int] = None
    total_spend_cents: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ClientSummaryResponse(BaseModel):
    """Aggregated KPI summary across all campaigns for a client."""

    client_id: int
    client_name: str
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_spend_cents: int = 0
    total_revenue_cents: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    avg_roas: Optional[float] = None
    avg_ctr: Optional[float] = None
    avg_cpa_cents: Optional[int] = None
    monthly_budget_cents: Optional[int] = None
    budget_utilization: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Client Assignment Schemas
# =============================================================================
class ClientAssignmentCreate(BaseModel):
    """Schema for assigning a user to a client."""

    user_id: int
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True)


class ClientAssignmentResponse(BaseModel):
    """Schema for client assignment detail."""

    id: int
    user_id: int
    client_id: int
    assigned_by: Optional[int] = None
    is_primary: bool
    created_at: datetime

    # Populated at query time
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Portal Invitation Schema
# =============================================================================
class ClientPortalInvite(BaseModel):
    """Schema for inviting a client portal user (VIEWER role)."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    client_id: int

    model_config = ConfigDict(from_attributes=True)
