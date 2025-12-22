# =============================================================================
# Stratum AI - Schemas Package
# =============================================================================
"""
Pydantic schemas for API request/response validation.
Re-exports all schemas from submodules for backwards compatibility.
"""

# Import everything from base schemas (original schemas.py content)
from app.schemas.base import (
    # Generic Response
    APIResponse,
    PaginatedResponse,
    DataT,
    # Base Schemas
    BaseSchema,
    TimestampMixin,
    # Auth Schemas
    TokenPayload,
    TokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
    # Tenant Schemas
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    # User Schemas
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfileResponse,
    TenantSignUp,
    TenantSignUpResponse,
    # Campaign Schemas
    CampaignBase,
    CampaignCreate,
    CampaignUpdate,
    CampaignMetricsUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignMetricResponse,
    CampaignMetricsTimeSeriesResponse,
    # Creative Asset Schemas
    CreativeAssetBase,
    CreativeAssetCreate,
    CreativeAssetUpdate,
    CreativeAssetResponse,
    # Rule Schemas
    RuleCondition,
    RuleActionConfig,
    RuleBase,
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleExecutionResponse,
    # Competitor Schemas
    CompetitorBase,
    CompetitorCreate,
    CompetitorUpdate,
    CompetitorResponse,
    CompetitorShareOfVoiceResponse,
    # ML / Simulator Schemas
    SimulationRequest,
    SimulationResponse,
    ROASForecastRequest,
    ROASForecastResponse,
    ConversionPredictionRequest,
    ConversionPredictionResponse,
    # Audit Log Schemas
    AuditLogResponse,
    AuditLogFilter,
    # GDPR Schemas
    GDPRExportRequest,
    GDPRAnonymizeRequest,
    GDPRAnonymizeResponse,
    # Health & Status Schemas
    HealthResponse,
    SyncStatusResponse,
    # Dashboard / Analytics Schemas
    KPITileResponse,
    DemographicsResponse,
    HeatmapDataResponse,
    # Notification Schemas
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    # WebSocket / SSE Schemas
    RealtimeEvent,
)

# Meta CAPI schemas
from app.schemas.meta_capi import (
    MetaUserIn,
    MetaCustomDataIn,
    MetaCapiCollectIn,
    MetaCapiCollectOut,
)

__all__ = [
    # Generic Response
    "APIResponse",
    "PaginatedResponse",
    "DataT",
    # Base Schemas
    "BaseSchema",
    "TimestampMixin",
    # Auth Schemas
    "TokenPayload",
    "TokenResponse",
    "LoginRequest",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "PasswordResetResponse",
    # Tenant Schemas
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    # User Schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfileResponse",
    "TenantSignUp",
    "TenantSignUpResponse",
    # Campaign Schemas
    "CampaignBase",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignMetricsUpdate",
    "CampaignResponse",
    "CampaignDetailResponse",
    "CampaignListResponse",
    "CampaignMetricResponse",
    "CampaignMetricsTimeSeriesResponse",
    # Creative Asset Schemas
    "CreativeAssetBase",
    "CreativeAssetCreate",
    "CreativeAssetUpdate",
    "CreativeAssetResponse",
    # Rule Schemas
    "RuleCondition",
    "RuleActionConfig",
    "RuleBase",
    "RuleCreate",
    "RuleUpdate",
    "RuleResponse",
    "RuleExecutionResponse",
    # Competitor Schemas
    "CompetitorBase",
    "CompetitorCreate",
    "CompetitorUpdate",
    "CompetitorResponse",
    "CompetitorShareOfVoiceResponse",
    # ML / Simulator Schemas
    "SimulationRequest",
    "SimulationResponse",
    "ROASForecastRequest",
    "ROASForecastResponse",
    "ConversionPredictionRequest",
    "ConversionPredictionResponse",
    # Audit Log Schemas
    "AuditLogResponse",
    "AuditLogFilter",
    # GDPR Schemas
    "GDPRExportRequest",
    "GDPRAnonymizeRequest",
    "GDPRAnonymizeResponse",
    # Health & Status Schemas
    "HealthResponse",
    "SyncStatusResponse",
    # Dashboard / Analytics Schemas
    "KPITileResponse",
    "DemographicsResponse",
    "HeatmapDataResponse",
    # Notification Schemas
    "NotificationPreferenceUpdate",
    "NotificationPreferenceResponse",
    # WebSocket / SSE Schemas
    "RealtimeEvent",
    # Meta CAPI Schemas
    "MetaUserIn",
    "MetaCustomDataIn",
    "MetaCapiCollectIn",
    "MetaCapiCollectOut",
]
