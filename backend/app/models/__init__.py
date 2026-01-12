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

# CRM Integration models
from app.models.crm import (
    CRMProvider,
    CRMConnectionStatus,
    DealStage,
    AttributionModel,
    WritebackStatus,
    CRMConnection,
    CRMContact,
    CRMDeal,
    Touchpoint,
    DailyPipelineMetrics,
    CRMWritebackConfig,
    CRMWritebackSync,
)

# Pacing & Forecasting models
from app.models.pacing import (
    TargetPeriod,
    TargetMetric,
    AlertSeverity,
    AlertType,
    AlertStatus,
    Target,
    DailyKPI,
    PacingAlert,
    Forecast,
    PacingSummary,
)

# Profit ROAS models
from app.models.profit import (
    MarginType,
    ProductStatus,
    COGSSource,
    ProductCatalog,
    ProductMargin,
    MarginRule,
    DailyProfitMetrics,
    ProfitROASReport,
    COGSUpload,
)

# Multi-Touch Attribution models
from app.models.attribution import (
    DailyAttributedRevenue,
    ConversionPath,
    AttributionSnapshot,
    ChannelInteraction,
    DataDrivenModelType,
    ModelStatus,
    TrainedAttributionModel,
    ModelTrainingRun,
)

# Automated Reporting models
from app.models.reporting import (
    ReportType,
    ReportFormat,
    ScheduleFrequency,
    DeliveryChannel,
    ExecutionStatus,
    DeliveryStatus,
    ReportTemplate,
    ScheduledReport,
    ReportExecution,
    ReportDelivery,
    DeliveryChannelConfig,
)

# Onboarding models
from app.models.onboarding import (
    OnboardingStatus,
    OnboardingStep,
    Industry,
    MonthlyAdSpend,
    TeamSize,
    AutomationMode,
    PrimaryKPI,
    TenantOnboarding,
)

# Autopilot Enforcement models
from app.models.autopilot import (
    EnforcementMode,
    ViolationType,
    InterventionAction,
    TenantEnforcementSettings,
    TenantEnforcementRule,
    EnforcementAuditLog,
    PendingConfirmationToken,
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
]
