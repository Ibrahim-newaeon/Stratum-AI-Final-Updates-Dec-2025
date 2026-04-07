# =============================================================================
# Stratum AI - Multiplatform Integration Module
# =============================================================================
"""
Stratum Multiplatform Integration.

Provides unified models and platform adapters for bi-directional sync
with advertising platforms (Meta, Google, TikTok, Snapchat, WhatsApp).

Key Components:
- Unified data models for cross-platform compatibility
- Platform adapters with full CRUD operations
- Signal health calculator with 4 components
- Trust gate evaluation for automation decisions
- Autopilot engine with built-in rules
- Server-side events tracking (CAPI)
- Webhook server for real-time updates
- Celery workers for data sync and automation

Module Structure:
- models: Unified data models
- core: Signal health, trust gate, autopilot
- adapters: Platform adapters (Meta, Google, TikTok, Snapchat, WhatsApp)
- workers: Celery tasks (data_sync, automation_runner)
- conversions: Conversions API clients
- events: Full-funnel server-side events
- webhooks: FastAPI webhook server
"""

# Models
# Conversions API
from app.stratum.conversions import (
    ConversionEvent,
    EventType,
    GoogleEnhancedConversions,
    MetaConversionsAPI,
    SnapchatConversionsAPI,
    TikTokEventsAPI,
    UnifiedConversionsAPI,
    UserData as ConversionUserData,
)

# Core - Autopilot
from app.stratum.core.autopilot import (
    AutopilotEngine,
    AutopilotRule,
    BudgetPacingRule,
    PerformanceScalingRule,
    RuleContext,
    RuleType,
    StatusManagementRule,
    TrustGatedAutopilot,
)

# Core - Signal Health & Trust Gate
from app.stratum.core.signal_health import SignalHealthCalculator
from app.stratum.core.trust_gate import GateDecision, TrustGate, TrustGateResult

# Full-funnel Events
from app.stratum.events import (
    EVENT_MAPPING,
    ContentItem,
    EcommerceTracker,
    GoogleEventsSender,
    MetaEventsSender,
    ServerEvent,
    SnapchatEventsSender,
    StandardEvent,
    TikTokEventsSender,
    UnifiedEventsAPI,
    UserData as EventUserData,
)

# Google Complete Integration
from app.stratum.integrations import (
    ChangeEvent,
    ChangeEventType,
    GA4MeasurementProtocol,
    GoogleAdsChangeHistory,
    GoogleAdsIntegration,
    GoogleAdsRecommendations,
    GoogleOfflineConversions,
    OfflineConversion,
)

# MCP Server
from app.stratum.mcp import (
    MCP_TOOLS,
    StratumMCPServer,
    create_mcp_server,
)
from app.stratum.models import (
    AutomationAction,
    BiddingStrategy,
    EMQScore,
    EntityStatus,
    PerformanceMetrics,
    Platform,
    SignalHealth,
    UnifiedAccount,
    UnifiedAd,
    UnifiedAdSet,
    UnifiedCampaign,
)

__all__ = [
    "EVENT_MAPPING",
    "MCP_TOOLS",
    "AutomationAction",
    "AutopilotEngine",
    "AutopilotRule",
    "BiddingStrategy",
    "BudgetPacingRule",
    "ChangeEvent",
    "ChangeEventType",
    "ContentItem",
    "ConversionEvent",
    "ConversionUserData",
    "EMQScore",
    "EcommerceTracker",
    "EntityStatus",
    # Conversions API
    "EventType",
    "EventUserData",
    "GA4MeasurementProtocol",
    "GateDecision",
    "GoogleAdsChangeHistory",
    # Google Complete Integration
    "GoogleAdsIntegration",
    "GoogleAdsRecommendations",
    "GoogleEnhancedConversions",
    "GoogleEventsSender",
    "GoogleOfflineConversions",
    "MetaConversionsAPI",
    "MetaEventsSender",
    "OfflineConversion",
    "PerformanceMetrics",
    "PerformanceScalingRule",
    # Models
    "Platform",
    "RuleContext",
    # Core - Autopilot
    "RuleType",
    "ServerEvent",
    "SignalHealth",
    # Core - Signal Health
    "SignalHealthCalculator",
    "SnapchatConversionsAPI",
    "SnapchatEventsSender",
    # Full-funnel Events
    "StandardEvent",
    "StatusManagementRule",
    # MCP Server
    "StratumMCPServer",
    "TikTokEventsAPI",
    "TikTokEventsSender",
    # Core - Trust Gate
    "TrustGate",
    "TrustGateResult",
    "TrustGatedAutopilot",
    "UnifiedAccount",
    "UnifiedAd",
    "UnifiedAdSet",
    "UnifiedCampaign",
    "UnifiedConversionsAPI",
    "UnifiedEventsAPI",
    "create_mcp_server",
]
