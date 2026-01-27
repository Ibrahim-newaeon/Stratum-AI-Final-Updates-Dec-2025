# =============================================================================
# Stratum AI - Subscription API Endpoints
# =============================================================================
"""
API endpoints for subscription status and management.

These endpoints allow users to check their subscription status,
view expiry warnings, and access billing information.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.subscription import (
    EXPIRY_WARNING_DAYS,
    GRACE_PERIOD_DAYS,
    SubscriptionStatus,
    get_expiry_warning_message,
    get_subscription_info,
)
from app.core.tiers import TIER_PRICING, SubscriptionTier

router = APIRouter(prefix="/subscription", tags=["subscription"])


# =============================================================================
# Response Models
# =============================================================================


class SubscriptionStatusResponse(BaseModel):
    """Response model for subscription status."""

    tenant_id: int
    plan: str
    tier: str
    status: str
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    days_in_grace: Optional[int]
    is_access_restricted: bool
    restriction_reason: Optional[str]
    warning_message: Optional[str]
    pricing: Optional[dict]

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": 1,
                "plan": "professional",
                "tier": "professional",
                "status": "expiring_soon",
                "expires_at": "2024-02-01T00:00:00Z",
                "days_until_expiry": 7,
                "days_in_grace": None,
                "is_access_restricted": False,
                "restriction_reason": None,
                "warning_message": "Your subscription expires in 7 days. Renew now to avoid interruption.",
                "pricing": {"name": "Professional", "price": 999, "currency": "USD"},
            }
        }


class SubscriptionConfigResponse(BaseModel):
    """Response model for subscription configuration."""

    grace_period_days: int
    expiry_warning_days: int
    available_plans: list


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(request: Request):
    """
    Get current subscription status for the authenticated tenant.

    Returns:
        - Plan and tier information
        - Subscription status (active, expiring_soon, grace_period, expired)
        - Days until expiry or days in grace period
        - Warning messages if applicable
        - Whether access is restricted

    This endpoint is always accessible (even with expired subscription)
    so users can check their status and renew.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    info = await get_subscription_info(tenant_id)
    warning_message = get_expiry_warning_message(info)

    # Get pricing info for current tier
    pricing = TIER_PRICING.get(info.tier, {})

    return SubscriptionStatusResponse(
        tenant_id=info.tenant_id,
        plan=info.plan,
        tier=info.tier.value,
        status=info.status.value,
        expires_at=info.expires_at.isoformat() if info.expires_at else None,
        days_until_expiry=info.days_until_expiry,
        days_in_grace=info.days_in_grace,
        is_access_restricted=info.is_access_restricted,
        restriction_reason=info.restriction_reason,
        warning_message=warning_message,
        pricing=pricing,
    )


@router.get("/config", response_model=SubscriptionConfigResponse)
async def get_subscription_config():
    """
    Get subscription configuration constants.

    Returns:
        - Grace period duration
        - Warning threshold for expiry
        - Available plans with pricing
    """
    plans = []
    for tier in [
        SubscriptionTier.STARTER,
        SubscriptionTier.PROFESSIONAL,
        SubscriptionTier.ENTERPRISE,
    ]:
        pricing = TIER_PRICING.get(tier, {})
        plans.append(
            {
                "tier": tier.value,
                **pricing,
            }
        )

    return SubscriptionConfigResponse(
        grace_period_days=GRACE_PERIOD_DAYS,
        expiry_warning_days=EXPIRY_WARNING_DAYS,
        available_plans=plans,
    )


@router.get("/check")
async def check_subscription_valid(request: Request):
    """
    Quick check if subscription is valid for access.

    Returns:
        - valid: bool - whether access should be allowed
        - status: str - current subscription status
        - message: str - explanation if not valid

    Use this for quick client-side checks before attempting
    operations that require valid subscription.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    info = await get_subscription_info(tenant_id)

    return {
        "valid": not info.is_access_restricted,
        "status": info.status.value,
        "message": info.restriction_reason
        if info.is_access_restricted
        else "Subscription is active",
        "tier": info.tier.value,
    }


@router.get("/warnings")
async def get_subscription_warnings(request: Request):
    """
    Get any active warnings about the subscription.

    Returns a list of warnings that should be displayed to the user.
    Empty list if no warnings.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    info = await get_subscription_info(tenant_id)
    warnings = []

    if info.status == SubscriptionStatus.EXPIRING_SOON:
        warnings.append(
            {
                "type": "expiring_soon",
                "severity": "warning",
                "title": "Subscription Expiring Soon",
                "message": f"Your subscription expires in {info.days_until_expiry} days.",
                "action": {
                    "label": "Renew Now",
                    "url": "/settings/billing",
                },
            }
        )

    elif info.status == SubscriptionStatus.GRACE_PERIOD:
        remaining = GRACE_PERIOD_DAYS - (info.days_in_grace or 0)
        warnings.append(
            {
                "type": "grace_period",
                "severity": "error",
                "title": "Subscription Expired",
                "message": f"Your subscription has expired. You have {remaining} days to renew before access is restricted.",
                "action": {
                    "label": "Renew Immediately",
                    "url": "/settings/billing",
                },
            }
        )

    elif info.status == SubscriptionStatus.EXPIRED:
        warnings.append(
            {
                "type": "expired",
                "severity": "critical",
                "title": "Access Restricted",
                "message": "Your subscription has expired. Please renew to restore access.",
                "action": {
                    "label": "Renew Subscription",
                    "url": "/settings/billing",
                },
            }
        )

    return {
        "warnings": warnings,
        "count": len(warnings),
    }


@router.get("/usage-summary")
async def get_subscription_usage_summary(request: Request):
    """
    Get a summary of subscription usage vs limits.

    Combines subscription status with resource usage information.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Get subscription info
    info = await get_subscription_info(tenant_id)

    # Get usage from tenant limits service
    from app.db.session import get_async_session
    from app.services.tenant.limits import TenantLimitService

    async for db in get_async_session():
        limit_service = TenantLimitService(db)
        try:
            usage = await limit_service.get_usage_summary(tenant_id)
        except Exception:
            usage = {}
        break

    return {
        "subscription": info.to_dict(),
        "usage": usage,
        "warning_message": get_expiry_warning_message(info),
    }
