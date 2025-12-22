# =============================================================================
# Stratum AI - Plan Configuration
# =============================================================================
"""
Subscription plan definitions with feature limits and pricing.
"""

from datetime import timedelta
from typing import Dict, Any

# Trial duration
TRIAL_DURATION_DAYS = 14

# Plan definitions
PLANS: Dict[str, Dict[str, Any]] = {
    "trial": {
        "name": "Trial",
        "price_monthly": 0,
        "price_yearly": 0,
        "duration_days": TRIAL_DURATION_DAYS,
        "limits": {
            "max_users": 3,
            "max_campaigns": 10,
            "max_ad_platforms": 5,  # All platforms during trial
            "max_automation_rules": 5,
            "max_competitors": 3,
            "data_retention_days": 30,
        },
        "features": {
            "ai_predictions": "full",  # full, advanced, basic, none
            "competitor_tracking": True,
            "whatsapp_alerts": True,
            "api_access": False,
            "custom_reports": True,
            "white_label": False,
            "priority_support": False,
            "dedicated_support": False,
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 49,
        "price_yearly": 470,  # ~20% discount
        "duration_days": None,  # Ongoing subscription
        "limits": {
            "max_users": 5,
            "max_campaigns": 25,
            "max_ad_platforms": 2,
            "max_automation_rules": 10,
            "max_competitors": 5,
            "data_retention_days": 90,
        },
        "features": {
            "ai_predictions": "basic",
            "competitor_tracking": True,
            "whatsapp_alerts": True,
            "api_access": False,
            "custom_reports": False,
            "white_label": False,
            "priority_support": False,
            "dedicated_support": False,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 199,
        "price_yearly": 1910,  # ~20% discount
        "duration_days": None,
        "limits": {
            "max_users": 15,
            "max_campaigns": 100,
            "max_ad_platforms": 5,
            "max_automation_rules": 50,
            "max_competitors": 20,
            "data_retention_days": 365,
        },
        "features": {
            "ai_predictions": "advanced",
            "competitor_tracking": True,
            "whatsapp_alerts": True,
            "api_access": True,
            "custom_reports": True,
            "white_label": False,
            "priority_support": True,
            "dedicated_support": False,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": None,  # Custom pricing
        "price_yearly": None,
        "duration_days": None,
        "limits": {
            "max_users": -1,  # Unlimited
            "max_campaigns": -1,
            "max_ad_platforms": -1,
            "max_automation_rules": -1,
            "max_competitors": -1,
            "data_retention_days": -1,  # Unlimited
        },
        "features": {
            "ai_predictions": "full",
            "competitor_tracking": True,
            "whatsapp_alerts": True,
            "api_access": True,
            "custom_reports": True,
            "white_label": True,
            "priority_support": True,
            "dedicated_support": True,
        },
    },
}


def get_plan_config(plan_name: str) -> Dict[str, Any]:
    """Get configuration for a specific plan."""
    return PLANS.get(plan_name, PLANS["trial"])


def get_plan_limit(plan_name: str, limit_key: str) -> int:
    """Get a specific limit for a plan. Returns -1 for unlimited."""
    plan = get_plan_config(plan_name)
    return plan.get("limits", {}).get(limit_key, 0)


def has_feature(plan_name: str, feature_key: str) -> bool:
    """Check if a plan has a specific feature enabled."""
    plan = get_plan_config(plan_name)
    feature_value = plan.get("features", {}).get(feature_key, False)
    # Handle boolean and string values
    if isinstance(feature_value, bool):
        return feature_value
    return feature_value not in [None, "none", False]


def get_trial_expiry():
    """Get the expiry datetime for a new trial."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc) + timedelta(days=TRIAL_DURATION_DAYS)


def is_plan_expired(plan: str, plan_expires_at) -> bool:
    """Check if a plan/trial has expired."""
    if plan == "trial" and plan_expires_at:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > plan_expires_at
    return False


# Plan upgrade paths
UPGRADE_PATHS = {
    "trial": ["starter", "professional", "enterprise"],
    "starter": ["professional", "enterprise"],
    "professional": ["enterprise"],
    "enterprise": [],
}


def can_upgrade_to(current_plan: str, target_plan: str) -> bool:
    """Check if upgrade from current to target plan is allowed."""
    return target_plan in UPGRADE_PATHS.get(current_plan, [])
