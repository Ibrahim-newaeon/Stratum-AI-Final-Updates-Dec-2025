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
    UserTenantMembership,
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

# Client (Agency → Brand) models
from app.models.client import (
    ClientRequestStatus,
    ClientRequestType,
    Client,
    ClientAssignment,
    ClientRequest,
)

# Autopilot Enforcement models
from app.models.autopilot import (
    EnforcementMode as AutopilotEnforcementMode,
    ViolationType as AutopilotViolationType,
    InterventionAction as AutopilotInterventionAction,
    TenantEnforcementSettings,
    TenantEnforcementRule,
    EnforcementAuditLog,
    PendingConfirmationToken,
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

__all__ = [
    "APIKey",
    "AdPlatform",
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "AssetType",
    "AttributionModel",
    "AttributionSnapshot",
    "AttributionVarianceStatus",
    "AuditAction",
    "AuditLog",
    # Autopilot Enforcement
    "AutopilotEnforcementMode",
    "AutopilotInterventionAction",
    "AutopilotViolationType",
    "COGSSource",
    "COGSUpload",
    "CRMConnection",
    "CRMConnectionStatus",
    "CRMContact",
    "CRMDeal",
    # CRM Integration
    "CRMProvider",
    "CRMWritebackConfig",
    "CRMWritebackSync",
    "Campaign",
    "CampaignDraft",
    "CampaignMetric",
    "CampaignPublishLog",
    "CampaignStatus",
    "ChannelInteraction",
    "Client",
    "ClientAssignment",
    "ClientRequest",
    # Client (Agency → Brand)
    "ClientRequestStatus",
    "ClientRequestType",
    "CompetitorBenchmark",
    "ConnectionStatus",
    "ConversionPath",
    "CreativeAsset",
    # Multi-Touch Attribution
    "DailyAttributedRevenue",
    "DailyKPI",
    "DailyPipelineMetrics",
    "DailyProfitMetrics",
    # Data-Driven Attribution
    "DataDrivenModelType",
    "DealStage",
    "DeliveryChannel",
    "DeliveryChannelConfig",
    "DeliveryStatus",
    "DraftStatus",
    "EnforcementAuditLog",
    "ExecutionStatus",
    "FactActionsQueue",
    "FactAttributionVarianceDaily",
    "FactSignalHealthDaily",
    "Forecast",
    "MLPrediction",
    "MarginRule",
    # Profit ROAS
    "MarginType",
    "ModelStatus",
    "ModelTrainingRun",
    "NotificationPreference",
    "PacingAlert",
    "PacingSummary",
    "PendingConfirmationToken",
    "ProductCatalog",
    "ProductMargin",
    "ProductStatus",
    "ProfitROASReport",
    "PublishResult",
    "ReportDelivery",
    "ReportExecution",
    "ReportFormat",
    "ReportTemplate",
    # Automated Reporting
    "ReportType",
    "Rule",
    "RuleAction",
    "RuleExecution",
    "RuleOperator",
    "RuleStatus",
    "ScheduleFrequency",
    "ScheduledReport",
    "SignalHealthStatus",
    "Target",
    "TargetMetric",
    # Pacing & Forecasting
    "TargetPeriod",
    # Models
    "Tenant",
    "TenantAdAccount",
    "TenantEnforcementRule",
    "TenantEnforcementSettings",
    "TenantPlatformConnection",
    "Touchpoint",
    "TrainedAttributionModel",
    "User",
    # Enums
    "UserRole",
    "UserTenantMembership",
    "WhatsAppContact",
    "WhatsAppConversation",
    "WhatsAppMessage",
    "WhatsAppMessageDirection",
    "WhatsAppMessageStatus",
    "WhatsAppOptInStatus",
    "WhatsAppTemplate",
    "WhatsAppTemplateCategory",
    "WhatsAppTemplateStatus",
    "WritebackStatus",
]
