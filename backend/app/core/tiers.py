# =============================================================================
# Stratum AI - Subscription Tier Configuration
# =============================================================================
"""
Defines subscription tiers and their feature access.

Tiers:
- STARTER: Basic features for small teams ($499/mo)
- PROFESSIONAL: Advanced features for growing teams ($999/mo)
- ENTERPRISE: Full features for large organizations (Custom)
"""

import enum
from typing import Dict, List, Set
from functools import wraps

from fastapi import HTTPException, status


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Tier hierarchy (higher index = more features)
TIER_HIERARCHY = [
    SubscriptionTier.STARTER,
    SubscriptionTier.PROFESSIONAL,
    SubscriptionTier.ENTERPRISE,
]


class Feature(str, enum.Enum):
    """All gated features in the platform."""

    # === STARTER FEATURES ===
    # Ad Account Management
    AD_ACCOUNTS_BASIC = "ad_accounts_basic"  # Up to 5 accounts

    # Signal Health
    SIGNAL_HEALTH_MONITORING = "signal_health_monitoring"
    ANOMALY_DETECTION = "anomaly_detection"

    # CDP Basic
    CDP_PROFILES = "cdp_profiles"
    CDP_EVENTS = "cdp_events"
    RFM_ANALYSIS = "rfm_analysis"

    # Reporting
    DASHBOARD_EXPORTS = "dashboard_exports"

    # Notifications
    SLACK_NOTIFICATIONS = "slack_notifications"
    EMAIL_NOTIFICATIONS = "email_notifications"

    # === PROFESSIONAL FEATURES ===
    # Ad Account Management
    AD_ACCOUNTS_EXTENDED = "ad_accounts_extended"  # Up to 15 accounts

    # CDP Advanced
    FUNNEL_BUILDER = "funnel_builder"
    COMPUTED_TRAITS = "computed_traits"
    SEGMENT_BUILDER = "segment_builder"

    # Trust Engine
    TRUST_GATE_AUDIT_LOGS = "trust_gate_audit_logs"
    ACTION_DRY_RUN = "action_dry_run"

    # CRM Integration
    PIPEDRIVE_INTEGRATION = "pipedrive_integration"
    HUBSPOT_INTEGRATION = "hubspot_integration"

    # Audience Sync
    AUDIENCE_SYNC_BASIC = "audience_sync_basic"  # 2 platforms

    # === ENTERPRISE FEATURES ===
    # Ad Account Management
    AD_ACCOUNTS_UNLIMITED = "ad_accounts_unlimited"

    # Advanced Analytics
    PREDICTIVE_CHURN = "predictive_churn"
    CUSTOM_AUTOPILOT_RULES = "custom_autopilot_rules"
    CUSTOM_REPORT_BUILDER = "custom_report_builder"
    WHAT_IF_SIMULATOR = "what_if_simulator"

    # CRM Advanced
    SALESFORCE_INTEGRATION = "salesforce_integration"
    ZOHO_INTEGRATION = "zoho_integration"
    CRM_WRITEBACK = "crm_writeback"

    # Compliance
    CONSENT_MANAGEMENT = "consent_management"
    GDPR_TOOLS = "gdpr_tools"
    AUDIT_EXPORT = "audit_export"

    # Audience Sync Advanced
    AUDIENCE_SYNC_ALL = "audience_sync_all"  # All 4 platforms

    # Identity
    IDENTITY_GRAPH = "identity_graph"

    # API
    API_ACCESS = "api_access"
    WEBHOOKS = "webhooks"

    # Embed Widgets
    EMBED_WIDGETS_BASIC = "embed_widgets_basic"      # Starter: with full branding
    EMBED_WIDGETS_MINIMAL = "embed_widgets_minimal"  # Professional: minimal branding
    EMBED_WIDGETS_WHITELABEL = "embed_widgets_whitelabel"  # Enterprise: no branding


# Feature sets per tier
TIER_FEATURES: Dict[SubscriptionTier, Set[Feature]] = {
    SubscriptionTier.STARTER: {
        # Core
        Feature.AD_ACCOUNTS_BASIC,
        Feature.SIGNAL_HEALTH_MONITORING,
        Feature.ANOMALY_DETECTION,
        # CDP
        Feature.CDP_PROFILES,
        Feature.CDP_EVENTS,
        Feature.RFM_ANALYSIS,
        # Reporting
        Feature.DASHBOARD_EXPORTS,
        # Notifications
        Feature.SLACK_NOTIFICATIONS,
        Feature.EMAIL_NOTIFICATIONS,
        # Embed Widgets (with full branding)
        Feature.EMBED_WIDGETS_BASIC,
    },

    SubscriptionTier.PROFESSIONAL: {
        # All Starter features (inherited)
        Feature.AD_ACCOUNTS_BASIC,
        Feature.SIGNAL_HEALTH_MONITORING,
        Feature.ANOMALY_DETECTION,
        Feature.CDP_PROFILES,
        Feature.CDP_EVENTS,
        Feature.RFM_ANALYSIS,
        Feature.DASHBOARD_EXPORTS,
        Feature.SLACK_NOTIFICATIONS,
        Feature.EMAIL_NOTIFICATIONS,
        # Professional features
        Feature.AD_ACCOUNTS_EXTENDED,
        Feature.FUNNEL_BUILDER,
        Feature.COMPUTED_TRAITS,
        Feature.SEGMENT_BUILDER,
        Feature.TRUST_GATE_AUDIT_LOGS,
        Feature.ACTION_DRY_RUN,
        Feature.PIPEDRIVE_INTEGRATION,
        Feature.HUBSPOT_INTEGRATION,
        Feature.AUDIENCE_SYNC_BASIC,
        # Embed Widgets (with minimal branding)
        Feature.EMBED_WIDGETS_BASIC,
        Feature.EMBED_WIDGETS_MINIMAL,
    },

    SubscriptionTier.ENTERPRISE: {
        # All features
        Feature.AD_ACCOUNTS_BASIC,
        Feature.SIGNAL_HEALTH_MONITORING,
        Feature.ANOMALY_DETECTION,
        Feature.CDP_PROFILES,
        Feature.CDP_EVENTS,
        Feature.RFM_ANALYSIS,
        Feature.DASHBOARD_EXPORTS,
        Feature.SLACK_NOTIFICATIONS,
        Feature.EMAIL_NOTIFICATIONS,
        Feature.AD_ACCOUNTS_EXTENDED,
        Feature.FUNNEL_BUILDER,
        Feature.COMPUTED_TRAITS,
        Feature.SEGMENT_BUILDER,
        Feature.TRUST_GATE_AUDIT_LOGS,
        Feature.ACTION_DRY_RUN,
        Feature.PIPEDRIVE_INTEGRATION,
        Feature.HUBSPOT_INTEGRATION,
        Feature.AUDIENCE_SYNC_BASIC,
        # Enterprise only
        Feature.AD_ACCOUNTS_UNLIMITED,
        Feature.PREDICTIVE_CHURN,
        Feature.CUSTOM_AUTOPILOT_RULES,
        Feature.CUSTOM_REPORT_BUILDER,
        Feature.WHAT_IF_SIMULATOR,
        Feature.SALESFORCE_INTEGRATION,
        Feature.ZOHO_INTEGRATION,
        Feature.CRM_WRITEBACK,
        Feature.CONSENT_MANAGEMENT,
        Feature.GDPR_TOOLS,
        Feature.AUDIT_EXPORT,
        Feature.AUDIENCE_SYNC_ALL,
        Feature.IDENTITY_GRAPH,
        Feature.API_ACCESS,
        Feature.WEBHOOKS,
        # Embed Widgets (white-label, no branding)
        Feature.EMBED_WIDGETS_BASIC,
        Feature.EMBED_WIDGETS_MINIMAL,
        Feature.EMBED_WIDGETS_WHITELABEL,
    },
}


# Tier limits
TIER_LIMITS: Dict[SubscriptionTier, Dict[str, int]] = {
    SubscriptionTier.STARTER: {
        "max_ad_accounts": 5,
        "max_users": 3,
        "max_segments": 10,
        "max_automations": 5,
        "max_audience_sync_platforms": 0,
        "api_rate_limit_per_minute": 60,
        "data_retention_days": 90,
        "max_embed_widgets": 3,
        "max_embed_domains": 2,
    },
    SubscriptionTier.PROFESSIONAL: {
        "max_ad_accounts": 15,
        "max_users": 10,
        "max_segments": 50,
        "max_automations": 25,
        "max_audience_sync_platforms": 2,
        "api_rate_limit_per_minute": 300,
        "data_retention_days": 365,
        "max_embed_widgets": 10,
        "max_embed_domains": 10,
    },
    SubscriptionTier.ENTERPRISE: {
        "max_ad_accounts": 999999,  # Unlimited
        "max_users": 999999,
        "max_segments": 999999,
        "max_automations": 999999,
        "max_audience_sync_platforms": 4,
        "api_rate_limit_per_minute": 1000,
        "data_retention_days": 730,  # 2 years
        "max_embed_widgets": 999999,  # Unlimited
        "max_embed_domains": 999999,  # Unlimited
    },
}


def has_feature(tier: SubscriptionTier, feature: Feature) -> bool:
    """Check if a tier has access to a specific feature."""
    return feature in TIER_FEATURES.get(tier, set())


def get_tier_limit(tier: SubscriptionTier, limit_name: str) -> int:
    """Get a specific limit for a tier."""
    return TIER_LIMITS.get(tier, {}).get(limit_name, 0)


def tier_at_least(tier: SubscriptionTier, minimum: SubscriptionTier) -> bool:
    """Check if tier is at least the minimum required tier."""
    tier_index = TIER_HIERARCHY.index(tier)
    min_index = TIER_HIERARCHY.index(minimum)
    return tier_index >= min_index


def get_available_features(tier: SubscriptionTier) -> List[str]:
    """Get list of available feature names for a tier."""
    return [f.value for f in TIER_FEATURES.get(tier, set())]


def get_tier_info(tier: SubscriptionTier) -> Dict:
    """Get complete tier information."""
    return {
        "tier": tier.value,
        "features": get_available_features(tier),
        "limits": TIER_LIMITS.get(tier, {}),
    }


# =============================================================================
# Tier Pricing Info (for display)
# =============================================================================

TIER_PRICING = {
    SubscriptionTier.STARTER: {
        "name": "Starter",
        "price": 499,
        "currency": "USD",
        "billing_period": "monthly",
        "ad_spend_limit": 100000,
        "description": "For teams scaling their ad operations",
    },
    SubscriptionTier.PROFESSIONAL: {
        "name": "Professional",
        "price": 999,
        "currency": "USD",
        "billing_period": "monthly",
        "ad_spend_limit": 500000,
        "description": "For growing marketing teams",
    },
    SubscriptionTier.ENTERPRISE: {
        "name": "Enterprise",
        "price": None,  # Custom
        "currency": "USD",
        "billing_period": "monthly",
        "ad_spend_limit": None,  # Unlimited
        "description": "For large organizations",
    },
}
