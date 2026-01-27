# =============================================================================
# Stratum AI - Feature Flags System
# =============================================================================
"""
Multi-tenant feature flag system for gating USP features by plan/tenant.

Feature Flags:
- signal_health: Trust layer signal health monitoring
- attribution_variance: Trust layer attribution variance tracking
- ai_recommendations: Intelligence layer recommendations
- anomaly_alerts: Intelligence layer anomaly detection alerts
- creative_fatigue: Intelligence layer creative fatigue detection
- campaign_builder: Execution layer campaign builder
- autopilot_level: Execution layer automation level (0-2)
- superadmin_profitability: Platform owner profitability views
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AutopilotLevel(int, Enum):
    """Autopilot automation levels."""

    SUGGEST_ONLY = 0  # No automatic writes, only suggestions
    GUARDED_AUTO = 1  # Safe actions within caps, requires signal health OK
    APPROVAL_REQUIRED = 2  # All actions require approval before execution


class PlanTier(str, Enum):
    """Subscription plan tiers."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


# =============================================================================
# Default Feature Flags by Plan
# =============================================================================

DEFAULT_FEATURES_BY_PLAN: dict[str, dict[str, Any]] = {
    PlanTier.FREE: {
        "signal_health": False,
        "attribution_variance": False,
        "ai_recommendations": False,
        "anomaly_alerts": False,
        "creative_fatigue": False,
        "campaign_builder": False,
        "autopilot_level": AutopilotLevel.SUGGEST_ONLY,
        "superadmin_profitability": False,
        "max_campaigns": 5,
        "max_users": 2,
        "data_retention_days": 30,
    },
    PlanTier.STARTER: {
        "signal_health": True,
        "attribution_variance": False,
        "ai_recommendations": True,
        "anomaly_alerts": True,
        "creative_fatigue": False,
        "campaign_builder": False,
        "autopilot_level": AutopilotLevel.SUGGEST_ONLY,
        "superadmin_profitability": False,
        "max_campaigns": 20,
        "max_users": 5,
        "data_retention_days": 90,
        # CDP Enhancements
        "rfm_analysis": True,
        "funnel_builder": False,
        "computed_traits": False,
        "consent_management": False,
        "realtime_streaming": False,
        "predictive_churn": False,
        # Trust Engine
        "signal_health_history": True,
        "trust_audit_logs": False,
        "custom_autopilot_rules": False,
        "action_dry_run": False,
        # Integrations
        "slack_notifications": True,
        "crm_salesforce": False,
        "crm_pipedrive": False,
        "linkedin_leadgen": False,
        # Dashboard
        "dashboard_export": True,
        "dashboard_customization": False,
        "custom_reports": False,
    },
    PlanTier.PROFESSIONAL: {
        "signal_health": True,
        "attribution_variance": True,
        "ai_recommendations": True,
        "anomaly_alerts": True,
        "creative_fatigue": True,
        "campaign_builder": True,
        "autopilot_level": AutopilotLevel.GUARDED_AUTO,
        "superadmin_profitability": False,
        "max_campaigns": 100,
        "max_users": 20,
        "data_retention_days": 365,
        # CDP Enhancements
        "rfm_analysis": True,
        "funnel_builder": True,
        "computed_traits": True,
        "consent_management": False,
        "realtime_streaming": False,
        "predictive_churn": False,
        # Trust Engine
        "signal_health_history": True,
        "trust_audit_logs": True,
        "custom_autopilot_rules": False,
        "action_dry_run": True,
        # Integrations
        "slack_notifications": True,
        "crm_salesforce": False,
        "crm_pipedrive": True,
        "linkedin_leadgen": False,
        # Dashboard
        "dashboard_export": True,
        "dashboard_customization": False,
        "custom_reports": False,
    },
    PlanTier.ENTERPRISE: {
        "signal_health": True,
        "attribution_variance": True,
        "ai_recommendations": True,
        "anomaly_alerts": True,
        "creative_fatigue": True,
        "campaign_builder": True,
        "autopilot_level": AutopilotLevel.APPROVAL_REQUIRED,
        "superadmin_profitability": True,
        "max_campaigns": -1,  # Unlimited
        "max_users": -1,  # Unlimited
        "data_retention_days": -1,  # Unlimited
        # CDP Enhancements
        "rfm_analysis": True,
        "funnel_builder": True,
        "computed_traits": True,
        "consent_management": True,
        "realtime_streaming": True,
        "predictive_churn": True,
        # Trust Engine
        "signal_health_history": True,
        "trust_audit_logs": True,
        "custom_autopilot_rules": True,
        "action_dry_run": True,
        # Integrations
        "slack_notifications": True,
        "crm_salesforce": True,
        "crm_pipedrive": True,
        "linkedin_leadgen": True,
        # Dashboard
        "dashboard_export": True,
        "dashboard_customization": True,
        "custom_reports": True,
    },
    PlanTier.CUSTOM: {
        # Custom plans inherit enterprise defaults, overridden per tenant
        "signal_health": True,
        "attribution_variance": True,
        "ai_recommendations": True,
        "anomaly_alerts": True,
        "creative_fatigue": True,
        "campaign_builder": True,
        "autopilot_level": AutopilotLevel.APPROVAL_REQUIRED,
        "superadmin_profitability": True,
        "max_campaigns": -1,
        "max_users": -1,
        "data_retention_days": -1,
        # CDP Enhancements
        "rfm_analysis": True,
        "funnel_builder": True,
        "computed_traits": True,
        "consent_management": True,
        "realtime_streaming": True,
        "predictive_churn": True,
        # Trust Engine
        "signal_health_history": True,
        "trust_audit_logs": True,
        "custom_autopilot_rules": True,
        "action_dry_run": True,
        # Integrations
        "slack_notifications": True,
        "crm_salesforce": True,
        "crm_pipedrive": True,
        "linkedin_leadgen": True,
        # Dashboard
        "dashboard_export": True,
        "dashboard_customization": True,
        "custom_reports": True,
    },
}


# =============================================================================
# Feature Flag Models
# =============================================================================


class FeatureFlags(BaseModel):
    """Complete feature flags configuration for a tenant."""

    # Trust Layer
    signal_health: bool = Field(default=False, description="Signal health monitoring")
    attribution_variance: bool = Field(default=False, description="Attribution variance tracking")

    # Intelligence Layer
    ai_recommendations: bool = Field(default=False, description="AI-powered recommendations")
    anomaly_alerts: bool = Field(default=True, description="Anomaly detection alerts")
    creative_fatigue: bool = Field(default=False, description="Creative fatigue detection")

    # Execution Layer
    campaign_builder: bool = Field(default=False, description="Campaign builder access")
    autopilot_level: int = Field(default=0, ge=0, le=2, description="Autopilot automation level")

    # Platform
    superadmin_profitability: bool = Field(
        default=False, description="Superadmin profitability views"
    )

    # Limits
    max_campaigns: int = Field(default=20, description="Maximum number of campaigns")
    max_users: int = Field(default=5, description="Maximum number of users")
    data_retention_days: int = Field(default=90, description="Data retention in days")

    # CDP Enhancements
    rfm_analysis: bool = Field(default=False, description="RFM analysis dashboard")
    funnel_builder: bool = Field(default=False, description="Conversion funnel builder")
    computed_traits: bool = Field(default=False, description="Computed traits UI")
    consent_management: bool = Field(default=False, description="Privacy consent management")
    realtime_streaming: bool = Field(default=False, description="Real-time event streaming")
    predictive_churn: bool = Field(default=False, description="Predictive churn modeling")

    # Trust Engine
    signal_health_history: bool = Field(default=False, description="Signal health history tracking")
    trust_audit_logs: bool = Field(default=False, description="Trust gate audit logging")
    custom_autopilot_rules: bool = Field(default=False, description="Custom autopilot rules")
    action_dry_run: bool = Field(default=False, description="Action dry-run mode")

    # Integrations
    slack_notifications: bool = Field(default=False, description="Slack notification integration")
    crm_salesforce: bool = Field(default=False, description="Salesforce CRM integration")
    crm_pipedrive: bool = Field(default=False, description="Pipedrive CRM integration")
    linkedin_leadgen: bool = Field(default=False, description="LinkedIn Lead Gen integration")

    # Dashboard
    dashboard_export: bool = Field(default=False, description="Dashboard export functionality")
    dashboard_customization: bool = Field(default=False, description="Dashboard customization")
    custom_reports: bool = Field(default=False, description="Custom report builder")

    class Config:
        use_enum_values = True


class FeatureFlagsUpdate(BaseModel):
    """Request model for updating feature flags."""

    signal_health: Optional[bool] = None
    attribution_variance: Optional[bool] = None
    ai_recommendations: Optional[bool] = None
    anomaly_alerts: Optional[bool] = None
    creative_fatigue: Optional[bool] = None
    campaign_builder: Optional[bool] = None
    autopilot_level: Optional[int] = Field(default=None, ge=0, le=2)
    superadmin_profitability: Optional[bool] = None
    max_campaigns: Optional[int] = None
    max_users: Optional[int] = None
    data_retention_days: Optional[int] = None
    # CDP Enhancements
    rfm_analysis: Optional[bool] = None
    funnel_builder: Optional[bool] = None
    computed_traits: Optional[bool] = None
    consent_management: Optional[bool] = None
    realtime_streaming: Optional[bool] = None
    predictive_churn: Optional[bool] = None
    # Trust Engine
    signal_health_history: Optional[bool] = None
    trust_audit_logs: Optional[bool] = None
    custom_autopilot_rules: Optional[bool] = None
    action_dry_run: Optional[bool] = None
    # Integrations
    slack_notifications: Optional[bool] = None
    crm_salesforce: Optional[bool] = None
    crm_pipedrive: Optional[bool] = None
    linkedin_leadgen: Optional[bool] = None
    # Dashboard
    dashboard_export: Optional[bool] = None
    dashboard_customization: Optional[bool] = None
    custom_reports: Optional[bool] = None


# =============================================================================
# Feature Flag Helpers
# =============================================================================


def get_default_features(plan: str) -> dict[str, Any]:
    """
    Get default feature flags for a plan tier.

    Args:
        plan: Plan tier name (free, starter, professional, enterprise, custom)

    Returns:
        Dict of default feature flags
    """
    plan_lower = plan.lower()
    if plan_lower in DEFAULT_FEATURES_BY_PLAN:
        return DEFAULT_FEATURES_BY_PLAN[plan_lower].copy()
    # Default to starter if unknown plan
    return DEFAULT_FEATURES_BY_PLAN[PlanTier.STARTER].copy()


def merge_features(defaults: dict[str, Any], overrides: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Merge default features with tenant-specific overrides.

    Args:
        defaults: Default feature flags from plan
        overrides: Tenant-specific overrides (from feature_flags jsonb)

    Returns:
        Merged feature flags
    """
    if not overrides:
        return defaults.copy()

    merged = defaults.copy()
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged


def can(features: dict[str, Any], feature_name: str) -> bool:
    """
    Check if a feature is enabled.

    Args:
        features: Feature flags dict
        feature_name: Name of feature to check

    Returns:
        True if feature is enabled
    """
    value = features.get(feature_name)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    return bool(value)


def get_autopilot_caps() -> dict[str, Any]:
    """
    Get default caps for autopilot actions.

    Returns:
        Dict with cap values:
        - max_daily_budget_change: Max absolute budget change per day
        - max_budget_pct_change: Max percentage budget change per action
        - max_actions_per_day: Max automated actions per day
    """
    return {
        "max_daily_budget_change": 500.0,  # Max $500 per day
        "max_budget_pct_change": 30.0,  # Max 30% change per action
        "max_actions_per_day": 10,  # Max 10 automated actions per day
    }


def get_autopilot_level(features: dict[str, Any]) -> AutopilotLevel:
    """
    Get the autopilot level from features.

    Args:
        features: Feature flags dict

    Returns:
        AutopilotLevel enum value
    """
    level = features.get("autopilot_level", 0)
    try:
        return AutopilotLevel(level)
    except ValueError:
        return AutopilotLevel.SUGGEST_ONLY


def is_autopilot_blocked(features: dict[str, Any], signal_health_status: str) -> bool:
    """
    Check if autopilot should be blocked due to signal health.

    Args:
        features: Feature flags dict
        signal_health_status: Current signal health status (healthy/risk/degraded/critical)

    Returns:
        True if autopilot should be blocked
    """
    autopilot_level = get_autopilot_level(features)

    # Suggest-only never auto-executes, so not "blocked"
    if autopilot_level == AutopilotLevel.SUGGEST_ONLY:
        return False

    # Block if signal health is degraded or critical
    if signal_health_status in ["degraded", "critical"]:
        return True

    return False


def validate_action_within_caps(
    features: dict[str, Any],
    action_type: str,
    change_pct: float,
) -> tuple[bool, Optional[str]]:
    """
    Validate if an action is within allowed caps.

    Default caps:
    - Budget increase: max 30% per day
    - Budget decrease: max 20% per day

    Args:
        features: Feature flags dict
        action_type: Type of action (budget_increase, budget_decrease)
        change_pct: Percentage change

    Returns:
        Tuple of (is_valid, error_message)
    """
    max_increase = features.get("max_budget_increase_pct", 30.0)
    max_decrease = features.get("max_budget_decrease_pct", 20.0)

    if action_type == "budget_increase" and change_pct > max_increase:
        return False, f"Budget increase {change_pct:.1f}% exceeds max {max_increase}%"

    if action_type == "budget_decrease" and change_pct > max_decrease:
        return False, f"Budget decrease {change_pct:.1f}% exceeds max {max_decrease}%"

    return True, None


# =============================================================================
# Feature Categories (for UI grouping)
# =============================================================================

FEATURE_CATEGORIES = {
    "trust_layer": {
        "name": "Trust Layer",
        "description": "Data quality and transparency features",
        "features": [
            "signal_health",
            "attribution_variance",
            "signal_health_history",
            "trust_audit_logs",
            "action_dry_run",
        ],
    },
    "intelligence_layer": {
        "name": "Intelligence Layer",
        "description": "AI-powered insights and recommendations",
        "features": [
            "ai_recommendations",
            "anomaly_alerts",
            "creative_fatigue",
            "predictive_churn",
        ],
    },
    "execution_layer": {
        "name": "Execution Layer",
        "description": "Campaign building and automation",
        "features": ["campaign_builder", "autopilot_level", "custom_autopilot_rules"],
    },
    "cdp": {
        "name": "Customer Data Platform",
        "description": "CDP features for customer analytics",
        "features": [
            "rfm_analysis",
            "funnel_builder",
            "computed_traits",
            "consent_management",
            "realtime_streaming",
        ],
    },
    "integrations": {
        "name": "Integrations",
        "description": "Third-party platform integrations",
        "features": ["slack_notifications", "crm_salesforce", "crm_pipedrive", "linkedin_leadgen"],
    },
    "dashboard": {
        "name": "Dashboard & Reports",
        "description": "Dashboard customization and reporting",
        "features": ["dashboard_export", "dashboard_customization", "custom_reports"],
    },
    "platform": {
        "name": "Platform Features",
        "description": "Platform-level features",
        "features": ["superadmin_profitability"],
    },
    "limits": {
        "name": "Usage Limits",
        "description": "Account usage limits",
        "features": ["max_campaigns", "max_users", "data_retention_days"],
    },
}


FEATURE_DESCRIPTIONS = {
    "signal_health": "Monitor data quality with EMQ scores and event loss tracking",
    "attribution_variance": "Track differences between platform and GA4 attribution",
    "ai_recommendations": "Get AI-powered recommendations for campaign optimization",
    "anomaly_alerts": "Receive alerts when metrics show unusual patterns",
    "creative_fatigue": "Detect when creatives are losing effectiveness",
    "campaign_builder": "Create and publish campaigns directly from Stratum AI",
    "autopilot_level": "Automation level: 0=Suggest, 1=Auto with caps, 2=Approval required",
    "superadmin_profitability": "Access platform-wide profitability and usage analytics",
    "max_campaigns": "Maximum number of active campaigns",
    "max_users": "Maximum number of team members",
    "data_retention_days": "How long historical data is kept",
    # CDP Enhancements
    "rfm_analysis": "RFM customer segmentation and analysis dashboard",
    "funnel_builder": "Build and analyze conversion funnels",
    "computed_traits": "Define and manage computed profile traits",
    "consent_management": "Privacy consent and GDPR/CCPA compliance management",
    "realtime_streaming": "Real-time event streaming and processing",
    "predictive_churn": "ML-powered customer churn prediction",
    # Trust Engine
    "signal_health_history": "Historical signal health tracking and trends",
    "trust_audit_logs": "Audit logs for trust gate decisions",
    "custom_autopilot_rules": "Create custom autopilot rules and conditions",
    "action_dry_run": "Test automation actions without execution",
    # Integrations
    "slack_notifications": "Send alerts and notifications to Slack",
    "crm_salesforce": "Salesforce CRM data sync and enrichment",
    "crm_pipedrive": "Pipedrive CRM data sync and enrichment",
    "linkedin_leadgen": "LinkedIn Lead Gen form integration",
    # Dashboard
    "dashboard_export": "Export dashboard data to CSV/JSON",
    "dashboard_customization": "Customize dashboard layout and widgets",
    "custom_reports": "Build custom reports with drag-and-drop",
}
