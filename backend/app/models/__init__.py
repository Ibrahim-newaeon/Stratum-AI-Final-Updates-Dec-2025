# =============================================================================
# Stratum AI - Models Package
# =============================================================================
# Re-exports all models for backwards compatibility

# Base models (formerly models.py)
from app.base_models import (
    AdPlatform,
    APIKey,
    AssetType,
    AuditAction,
    AuditLog,
    Campaign,
    CampaignMetric,
    CampaignStatus,
    CompetitorBenchmark,
    CreativeAsset,
    MLPrediction,
    NotificationPreference,
    Rule,
    RuleAction,
    RuleExecution,
    RuleOperator,
    RuleStatus,
    # Models
    Tenant,
    User,
    # Enums
    UserRole,
    WhatsAppContact,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppMessageDirection,
    WhatsAppMessageStatus,
    WhatsAppOptInStatus,
    WhatsAppTemplate,
    WhatsAppTemplateCategory,
    WhatsAppTemplateStatus,
)

# Multi-Touch Attribution models
from app.models.attribution import (
    AttributionSnapshot,
    ChannelInteraction,
    ConversionPath,
    DailyAttributedRevenue,
    DataDrivenModelType,
    ModelStatus,
    ModelTrainingRun,
    TrainedAttributionModel,
)

# Audience Sync models
from app.models.audience_sync import (
    AudienceSyncCredential,
    AudienceSyncJob,
    AudienceType,
    PlatformAudience,
    SyncOperation,
    SyncPlatform,
    SyncStatus,
)

# Autopilot Enforcement models
from app.models.autopilot import (
    EnforcementAuditLog,
    EnforcementMode,
    InterventionAction,
    PendingConfirmationToken,
    TenantEnforcementRule,
    TenantEnforcementSettings,
    ViolationType,
)

# Client Entity models (Agency model)
from app.models.client import (
    Client,
    ClientAssignment,
    ClientRequest,
    ClientRequestStatus,
    ClientRequestType,
)

# Campaign Builder models
from app.models.campaign_builder import (
    CampaignDraft,
    CampaignPublishLog,
    ConnectionStatus,
    DraftStatus,
    PublishResult,
    TenantAdAccount,
    TenantPlatformConnection,
)

# CDP (Customer Data Platform) models
from app.models.cdp import (
    CDPConsent,
    CDPEvent,
    CDPProfile,
    CDPProfileIdentifier,
    CDPSource,
    ConsentType,
    IdentifierType,
    LifecycleStage,
    SourceType,
)

# CMS (Content Management System) models
from app.models.cms import (
    CMSAuthor,
    CMSCategory,
    CMSContactSubmission,
    CMSContentType,
    CMSPage,
    CMSPageStatus,
    CMSPost,
    CMSPostStatus,
    CMSTag,
)

# CRM Integration models
from app.models.crm import (
    AttributionModel,
    CRMConnection,
    CRMConnectionStatus,
    CRMContact,
    CRMDeal,
    CRMProvider,
    CRMWritebackConfig,
    CRMWritebackSync,
    DailyPipelineMetrics,
    DealStage,
    Touchpoint,
    WritebackStatus,
)

# Onboarding models
from app.models.onboarding import (
    AutomationMode,
    Industry,
    MonthlyAdSpend,
    OnboardingStatus,
    OnboardingStep,
    PrimaryKPI,
    TeamSize,
    TenantOnboarding,
)

# Pacing & Forecasting models
from app.models.pacing import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    DailyKPI,
    Forecast,
    PacingAlert,
    PacingSummary,
    Target,
    TargetMetric,
    TargetPeriod,
)

# Profit ROAS models
from app.models.profit import (
    COGSSource,
    COGSUpload,
    DailyProfitMetrics,
    MarginRule,
    MarginType,
    ProductCatalog,
    ProductMargin,
    ProductStatus,
    ProfitROASReport,
)

# Automated Reporting models
from app.models.reporting import (
    DeliveryChannel,
    DeliveryChannelConfig,
    DeliveryStatus,
    ExecutionStatus,
    ReportDelivery,
    ReportExecution,
    ReportFormat,
    ReportTemplate,
    ReportType,
    ScheduledReport,
    ScheduleFrequency,
)

# Settings models (Webhooks, Notifications, Changelog, Slack)
from app.models.settings import (
    ChangelogEntry,
    ChangelogReadStatus,
    ChangelogType,
    Notification,
    NotificationCategory,
    NotificationType,
    SlackIntegration,
    Webhook,
    WebhookDelivery,
    WebhookEventType,
    WebhookStatus,
)

# Trust Layer models
from app.models.trust_layer import (
    AttributionVarianceStatus,
    FactActionsQueue,
    FactAttributionVarianceDaily,
    FactSignalHealthDaily,
    SignalHealthStatus,
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
    # CRM Integration
    "CRMProvider",
    "CRMConnectionStatus",
    "DealStage",
    "AttributionModel",
    "WritebackStatus",
    "CRMConnection",
    "CRMContact",
    "CRMDeal",
    "Touchpoint",
    "DailyPipelineMetrics",
    "CRMWritebackConfig",
    "CRMWritebackSync",
    # Pacing & Forecasting
    "TargetPeriod",
    "TargetMetric",
    "AlertSeverity",
    "AlertType",
    "AlertStatus",
    "Target",
    "DailyKPI",
    "PacingAlert",
    "Forecast",
    "PacingSummary",
    # Profit ROAS
    "MarginType",
    "ProductStatus",
    "COGSSource",
    "ProductCatalog",
    "ProductMargin",
    "MarginRule",
    "DailyProfitMetrics",
    "ProfitROASReport",
    "COGSUpload",
    # Multi-Touch Attribution
    "DailyAttributedRevenue",
    "ConversionPath",
    "AttributionSnapshot",
    "ChannelInteraction",
    # Data-Driven Attribution
    "DataDrivenModelType",
    "ModelStatus",
    "TrainedAttributionModel",
    "ModelTrainingRun",
    # Automated Reporting
    "ReportType",
    "ReportFormat",
    "ScheduleFrequency",
    "DeliveryChannel",
    "ExecutionStatus",
    "DeliveryStatus",
    "ReportTemplate",
    "ScheduledReport",
    "ReportExecution",
    "ReportDelivery",
    "DeliveryChannelConfig",
    # Onboarding
    "OnboardingStatus",
    "OnboardingStep",
    "Industry",
    "MonthlyAdSpend",
    "TeamSize",
    "AutomationMode",
    "PrimaryKPI",
    "TenantOnboarding",
    # Autopilot Enforcement
    "EnforcementMode",
    "ViolationType",
    "InterventionAction",
    "TenantEnforcementSettings",
    "TenantEnforcementRule",
    "EnforcementAuditLog",
    "PendingConfirmationToken",
    # CDP (Customer Data Platform)
    "SourceType",
    "IdentifierType",
    "LifecycleStage",
    "ConsentType",
    "CDPSource",
    "CDPProfile",
    "CDPProfileIdentifier",
    "CDPEvent",
    "CDPConsent",
    # Audience Sync
    "SyncPlatform",
    "SyncStatus",
    "SyncOperation",
    "AudienceType",
    "PlatformAudience",
    "AudienceSyncJob",
    "AudienceSyncCredential",
    # Settings (Webhooks, Notifications, Changelog, Slack)
    "WebhookStatus",
    "WebhookEventType",
    "NotificationType",
    "NotificationCategory",
    "ChangelogType",
    "Webhook",
    "WebhookDelivery",
    "Notification",
    "ChangelogEntry",
    "ChangelogReadStatus",
    "SlackIntegration",
    # Client Entity (Agency model)
    "Client",
    "ClientAssignment",
    "ClientRequest",
    "ClientRequestStatus",
    "ClientRequestType",
    # CMS (Content Management System)
    "CMSPostStatus",
    "CMSContentType",
    "CMSPageStatus",
    "CMSCategory",
    "CMSTag",
    "CMSAuthor",
    "CMSPost",
    "CMSPage",
    "CMSContactSubmission",
]
