# =============================================================================
# Stratum AI - Feature Gate System
# =============================================================================
"""
Feature gating middleware and decorators for tier-based access control.

Usage:
    @router.get("/predictive-churn")
    @require_feature(Feature.PREDICTIVE_CHURN)
    async def get_churn_prediction(...):
        ...

    # Or as a dependency
    @router.get("/churn")
    async def get_churn(
        _: None = Depends(FeatureGate(Feature.PREDICTIVE_CHURN))
    ):
        ...
"""

from functools import wraps
from typing import Callable, List, Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.tiers import (
    Feature,
    SubscriptionTier,
    has_feature,
    get_tier_limit,
    tier_at_least,
    TIER_FEATURES,
)


class FeatureNotAvailableError(HTTPException):
    """Exception raised when a feature is not available for the current tier."""

    def __init__(self, feature: Feature, current_tier: SubscriptionTier):
        required_tier = get_required_tier(feature)
        detail = {
            "error": "feature_not_available",
            "feature": feature.value,
            "current_tier": current_tier.value,
            "required_tier": required_tier.value if required_tier else "enterprise",
            "message": f"The '{feature.value}' feature requires {required_tier.value if required_tier else 'Enterprise'} tier or higher.",
            "upgrade_url": "/settings/billing",
        }
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class LimitExceededError(HTTPException):
    """Exception raised when a tier limit is exceeded."""

    def __init__(self, limit_name: str, current_value: int, max_value: int, tier: SubscriptionTier):
        detail = {
            "error": "limit_exceeded",
            "limit": limit_name,
            "current": current_value,
            "maximum": max_value,
            "tier": tier.value,
            "message": f"You have reached the {limit_name} limit ({max_value}) for the {tier.value} tier.",
            "upgrade_url": "/settings/billing",
        }
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_required_tier(feature: Feature) -> Optional[SubscriptionTier]:
    """Get the minimum tier required for a feature."""
    for tier in [SubscriptionTier.STARTER, SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]:
        if feature in TIER_FEATURES.get(tier, set()):
            return tier
    return None


def get_current_tier() -> SubscriptionTier:
    """
    Get the current subscription tier from settings.

    In a real implementation, this would check:
    1. The tenant's subscription from database
    2. Or the SUBSCRIPTION_TIER environment variable
    """
    tier_value = getattr(settings, 'subscription_tier', 'enterprise')
    try:
        return SubscriptionTier(tier_value.lower())
    except ValueError:
        return SubscriptionTier.ENTERPRISE


class FeatureGate:
    """
    FastAPI dependency for feature gating.

    Usage:
        @router.get("/churn")
        async def get_churn(
            _: None = Depends(FeatureGate(Feature.PREDICTIVE_CHURN))
        ):
            ...
    """

    def __init__(self, feature: Feature):
        self.feature = feature

    async def __call__(self, request: Request) -> None:
        current_tier = get_current_tier()

        if not has_feature(current_tier, self.feature):
            raise FeatureNotAvailableError(self.feature, current_tier)


class TierGate:
    """
    FastAPI dependency for tier-level gating.

    Usage:
        @router.get("/enterprise-only")
        async def enterprise_endpoint(
            _: None = Depends(TierGate(SubscriptionTier.ENTERPRISE))
        ):
            ...
    """

    def __init__(self, minimum_tier: SubscriptionTier):
        self.minimum_tier = minimum_tier

    async def __call__(self, request: Request) -> None:
        current_tier = get_current_tier()

        if not tier_at_least(current_tier, self.minimum_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tier_required",
                    "current_tier": current_tier.value,
                    "required_tier": self.minimum_tier.value,
                    "message": f"This feature requires {self.minimum_tier.value} tier or higher.",
                    "upgrade_url": "/settings/billing",
                }
            )


class LimitChecker:
    """
    FastAPI dependency for checking tier limits.

    Usage:
        @router.post("/ad-accounts")
        async def create_ad_account(
            limit_check: dict = Depends(LimitChecker("max_ad_accounts", get_current_count))
        ):
            ...
    """

    def __init__(self, limit_name: str, get_current_count: Callable):
        self.limit_name = limit_name
        self.get_current_count = get_current_count

    async def __call__(self, request: Request) -> dict:
        current_tier = get_current_tier()
        max_value = get_tier_limit(current_tier, self.limit_name)
        current_value = await self.get_current_count(request)

        if current_value >= max_value:
            raise LimitExceededError(
                self.limit_name,
                current_value,
                max_value,
                current_tier
            )

        return {
            "current": current_value,
            "maximum": max_value,
            "remaining": max_value - current_value,
        }


def require_feature(feature: Feature):
    """
    Decorator for gating endpoints by feature.

    Usage:
        @router.get("/predictive-churn")
        @require_feature(Feature.PREDICTIVE_CHURN)
        async def get_churn_prediction(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_tier = get_current_tier()

            if not has_feature(current_tier, feature):
                raise FeatureNotAvailableError(feature, current_tier)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_tier(minimum_tier: SubscriptionTier):
    """
    Decorator for gating endpoints by minimum tier.

    Usage:
        @router.get("/enterprise-dashboard")
        @require_tier(SubscriptionTier.ENTERPRISE)
        async def enterprise_dashboard(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_tier = get_current_tier()

            if not tier_at_least(current_tier, minimum_tier):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "tier_required",
                        "current_tier": current_tier.value,
                        "required_tier": minimum_tier.value,
                        "message": f"This feature requires {minimum_tier.value} tier or higher.",
                    }
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Utility Functions
# =============================================================================

def check_feature(feature: Feature) -> bool:
    """Quick check if current tier has a feature."""
    return has_feature(get_current_tier(), feature)


def check_limit(limit_name: str, current_count: int) -> bool:
    """Quick check if current count is within limit."""
    max_value = get_tier_limit(get_current_tier(), limit_name)
    return current_count < max_value


def get_tier_features_response() -> dict:
    """Get current tier info for API response."""
    tier = get_current_tier()
    from app.core.tiers import get_tier_info, TIER_PRICING

    info = get_tier_info(tier)
    pricing = TIER_PRICING.get(tier, {})

    return {
        **info,
        "pricing": pricing,
    }
