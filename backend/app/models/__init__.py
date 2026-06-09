# =============================================================================
# Stratum AI - Models Package
# =============================================================================
# Re-exports all models for backwards compatibility

# Base models (formerly models.py)
from app.base_models import (  # Enums; Models
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
    Tenant,
    User,
    UserRole,
    UserTenantMembership,
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

# Autopilot Enforcement models
from app.models.autopilot import (
    EnforcementAuditLog,
)
from app.models.autopilot import EnforcementMode as AutopilotEnforcementMode
from app.models.autopilot import InterventionAction as AutopilotInterventionAction
from app.models.autopilot import (
    PendingConfirmationToken,
    TenantEnforcementRule,
    TenantEnforcementSettings,
)
from app.models.autopilot import ViolationType as AutopilotViolationType

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

# Client (Agency → Brand) models
from app.models.client import (
    Client,
    ClientAssignment,
    ClientRequest,
    ClientRequestStatus,
    ClientRequestType,
)
from app.models.copilot_doc import CopilotDocChunk

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

# EMQ fix-playbook progress
from app.models.emq_playbook import EmqPlaybookItemState

# Launch Readiness (Go-Live wizard)
from app.models.launch_readiness import (
    LaunchReadinessEvent,
    LaunchReadinessItemState,
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

# Trust Layer models
from app.models.trust_layer import (
    AttributionVarianceStatus,
    FactActionsQueue,
    FactAttributionVarianceDaily,
    FactSignalHealthDaily,
    SignalHealthStatus,
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
    "CopilotDocChunk",
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
    "EmqPlaybookItemState",
    "EnforcementAuditLog",
    "ExecutionStatus",
    "FactActionsQueue",
    "FactAttributionVarianceDaily",
    "FactSignalHealthDaily",
    "Forecast",
    # Launch Readiness (Go-Live wizard)
    "LaunchReadinessEvent",
    "LaunchReadinessItemState",
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
