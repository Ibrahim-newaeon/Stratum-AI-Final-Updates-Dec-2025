# =============================================================================
# Stratum AI - Tier/Subscription API Endpoints
# =============================================================================
"""
API endpoints for subscription tier information and feature access.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.core.tiers import (
    Feature,
    SubscriptionTier,
    has_feature,
    get_tier_limit,
    get_available_features,
    get_tier_info,
    TIER_FEATURES,
    TIER_LIMITS,
    TIER_PRICING,
)
from app.core.feature_gate import (
    get_current_tier,
    get_tier_features_response,
    check_feature,
)

router = APIRouter(prefix="/tier", tags=["tier"])


@router.get("/current")
async def get_current_tier_info():
    """
    Get current subscription tier and available features.

    Returns tier name, features, limits, and pricing info.
    """
    return get_tier_features_response()


@router.get("/features")
async def get_tier_features():
    """
    Get list of all features available for current tier.
    """
    tier = get_current_tier()
    return {
        "tier": tier.value,
        "features": get_available_features(tier),
    }


@router.get("/features/{feature_name}")
async def check_feature_access(feature_name: str):
    """
    Check if a specific feature is available.

    Returns:
        available: bool - whether feature is accessible
        feature: str - feature name
        tier: str - current tier
        required_tier: str - minimum tier needed (if not available)
    """
    tier = get_current_tier()

    try:
        feature = Feature(feature_name)
        available = has_feature(tier, feature)

        # Find required tier
        required_tier = None
        if not available:
            for t in [SubscriptionTier.STARTER, SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]:
                if feature in TIER_FEATURES.get(t, set()):
                    required_tier = t.value
                    break

        return {
            "available": available,
            "feature": feature_name,
            "tier": tier.value,
            "required_tier": required_tier,
        }
    except ValueError:
        return {
            "available": False,
            "feature": feature_name,
            "tier": tier.value,
            "error": "Unknown feature",
        }


@router.get("/limits")
async def get_tier_limits():
    """
    Get all limits for current tier.
    """
    tier = get_current_tier()
    return {
        "tier": tier.value,
        "limits": TIER_LIMITS.get(tier, {}),
    }


@router.get("/limits/{limit_name}")
async def get_specific_limit(limit_name: str):
    """
    Get a specific limit value for current tier.
    """
    tier = get_current_tier()
    limit_value = get_tier_limit(tier, limit_name)

    return {
        "tier": tier.value,
        "limit": limit_name,
        "value": limit_value,
    }


@router.get("/all")
async def get_all_tiers():
    """
    Get information about all available tiers.
    Useful for displaying upgrade options.
    """
    current_tier = get_current_tier()

    tiers = []
    for tier in [SubscriptionTier.STARTER, SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]:
        info = get_tier_info(tier)
        pricing = TIER_PRICING.get(tier, {})
        tiers.append({
            **info,
            "pricing": pricing,
            "is_current": tier == current_tier,
        })

    return {
        "current_tier": current_tier.value,
        "tiers": tiers,
    }


@router.get("/compare")
async def compare_tiers():
    """
    Compare features across all tiers.
    Returns a matrix of features by tier.
    """
    all_features = list(Feature)

    comparison = {}
    for feature in all_features:
        comparison[feature.value] = {
            "starter": has_feature(SubscriptionTier.STARTER, feature),
            "professional": has_feature(SubscriptionTier.PROFESSIONAL, feature),
            "enterprise": has_feature(SubscriptionTier.ENTERPRISE, feature),
        }

    return {
        "features": comparison,
        "limits": {
            "starter": TIER_LIMITS.get(SubscriptionTier.STARTER, {}),
            "professional": TIER_LIMITS.get(SubscriptionTier.PROFESSIONAL, {}),
            "enterprise": TIER_LIMITS.get(SubscriptionTier.ENTERPRISE, {}),
        },
    }
