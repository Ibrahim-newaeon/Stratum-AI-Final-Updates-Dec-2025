# =============================================================================
# Stratum AI - Models Package
# =============================================================================
# Re-exports all models for backwards compatibility

# Base models (formerly models.py)
from app.base_models import (
    # Enums
    UserRole,
    AdPlatform,
    CampaignStatus,
    AssetType,
    RuleStatus,
    RuleOperator,
    RuleAction,
    AuditAction,
    WhatsAppOptInStatus,
    WhatsAppMessageDirection,
    WhatsAppMessageStatus,
    WhatsAppTemplateStatus,
    WhatsAppTemplateCategory,
    # Models
    Tenant,
    User,
    Campaign,
    CampaignMetric,
    CreativeAsset,
    Rule,
    RuleExecution,
    CompetitorBenchmark,
    AuditLog,
    MLPrediction,
    NotificationPreference,
    APIKey,
    WhatsAppContact,
    WhatsAppTemplate,
    WhatsAppMessage,
    WhatsAppConversation,
)

# Trust Layer models
from app.models.trust_layer import (
    SignalHealthStatus,
    AttributionVarianceStatus,
    FactSignalHealthDaily,
    FactAttributionVarianceDaily,
    FactActionsQueue,
)

# Campaign Builder models
from app.models.campaign_builder import (
    ConnectionStatus,
    DraftStatus,
    PublishResult,
    TenantPlatformConnection,
    TenantAdAccount,
    CampaignDraft,
    CampaignPublishLog,
)

__all__ = [
    # Enums
    "UserRole",
    "AdPlatform",
    "CampaignStatus",
    "AssetType",
    "RuleStatus",
    "RuleOperator",
    "RuleAction",
    "AuditAction",
    "WhatsAppOptInStatus",
    "WhatsAppMessageDirection",
    "WhatsAppMessageStatus",
    "WhatsAppTemplateStatus",
    "WhatsAppTemplateCategory",
    "SignalHealthStatus",
    "AttributionVarianceStatus",
    "ConnectionStatus",
    "DraftStatus",
    "PublishResult",
    # Models
    "Tenant",
    "User",
    "Campaign",
    "CampaignMetric",
    "CreativeAsset",
    "Rule",
    "RuleExecution",
    "CompetitorBenchmark",
    "AuditLog",
    "MLPrediction",
    "NotificationPreference",
    "APIKey",
    "WhatsAppContact",
    "WhatsAppTemplate",
    "WhatsAppMessage",
    "WhatsAppConversation",
    "FactSignalHealthDaily",
    "FactAttributionVarianceDaily",
    "FactActionsQueue",
    "TenantPlatformConnection",
    "TenantAdAccount",
    "CampaignDraft",
    "CampaignPublishLog",
]
