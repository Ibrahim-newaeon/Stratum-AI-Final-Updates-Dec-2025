# =============================================================================
# Stratum AI - Subscription Management
# =============================================================================
"""
Subscription status checking and expiry enforcement.

This module handles:
- Subscription status determination (active, grace period, expired)
- Grace period logic (7 days after expiry)
- Feature access based on subscription status
- Expiry warnings for upcoming renewals
"""

import enum
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from app.core.tiers import SubscriptionTier

# =============================================================================
# Configuration
# =============================================================================

# Grace period after subscription expiry (days)
GRACE_PERIOD_DAYS = 7

# Warning threshold for upcoming expiry (days)
EXPIRY_WARNING_DAYS = 14

# Plans that never expire (free tier)
NON_EXPIRING_PLANS = {"free"}


# =============================================================================
# Subscription Status
# =============================================================================


class SubscriptionStatus(str, enum.Enum):
    """Subscription status levels."""

    ACTIVE = "active"  # Subscription is active and valid
    EXPIRING_SOON = "expiring_soon"  # Active but expiring within warning period
    GRACE_PERIOD = "grace_period"  # Expired but within grace period
    EXPIRED = "expired"  # Fully expired, access restricted
    CANCELLED = "cancelled"  # Manually cancelled
    FREE = "free"  # Free tier (never expires)


@dataclass
class SubscriptionInfo:
    """Complete subscription information for a tenant."""

    tenant_id: int
    plan: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    expires_at: Optional[datetime]
    days_until_expiry: Optional[int]
    days_in_grace: Optional[int]
    is_access_restricted: bool
    restriction_reason: Optional[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan,
            "tier": self.tier.value,
            "status": self.status.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "days_until_expiry": self.days_until_expiry,
            "days_in_grace": self.days_in_grace,
            "is_access_restricted": self.is_access_restricted,
            "restriction_reason": self.restriction_reason,
        }


# =============================================================================
# Status Checking Functions
# =============================================================================


def calculate_subscription_status(
    plan: str,
    plan_expires_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> tuple[SubscriptionStatus, Optional[int], Optional[int]]:
    """
    Calculate subscription status based on plan and expiry date.

    Args:
        plan: The tenant's plan name
        plan_expires_at: When the plan expires (None = never)
        now: Current time (defaults to UTC now)

    Returns:
        Tuple of (status, days_until_expiry, days_in_grace)
    """
    if now is None:
        now = datetime.now(UTC)

    # Free plans never expire
    if plan.lower() in NON_EXPIRING_PLANS:
        return SubscriptionStatus.FREE, None, None

    # No expiry date set = active (lifetime or misconfigured)
    if plan_expires_at is None:
        return SubscriptionStatus.ACTIVE, None, None

    # Ensure timezone awareness
    if plan_expires_at.tzinfo is None:
        plan_expires_at = plan_expires_at.replace(tzinfo=UTC)

    # Calculate time difference
    time_diff = plan_expires_at - now
    days_until_expiry = time_diff.days

    if days_until_expiry > EXPIRY_WARNING_DAYS:
        # Active and not expiring soon
        return SubscriptionStatus.ACTIVE, days_until_expiry, None

    elif days_until_expiry > 0:
        # Active but expiring soon
        return SubscriptionStatus.EXPIRING_SOON, days_until_expiry, None

    elif days_until_expiry >= -GRACE_PERIOD_DAYS:
        # In grace period
        days_in_grace = abs(days_until_expiry)
        return SubscriptionStatus.GRACE_PERIOD, 0, days_in_grace

    else:
        # Fully expired
        days_in_grace = abs(days_until_expiry)
        return SubscriptionStatus.EXPIRED, 0, days_in_grace


def is_subscription_valid(status: SubscriptionStatus) -> bool:
    """Check if subscription status allows full access."""
    return status in {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.EXPIRING_SOON,
        SubscriptionStatus.FREE,
    }


def is_access_allowed(status: SubscriptionStatus, allow_grace: bool = True) -> bool:
    """
    Check if access should be allowed based on subscription status.

    Args:
        status: Current subscription status
        allow_grace: Whether to allow access during grace period

    Returns:
        True if access should be allowed
    """
    valid_statuses = {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.EXPIRING_SOON,
        SubscriptionStatus.FREE,
    }

    if allow_grace:
        valid_statuses.add(SubscriptionStatus.GRACE_PERIOD)

    return status in valid_statuses


# =============================================================================
# Database Functions
# =============================================================================


async def get_subscription_info(tenant_id: int) -> SubscriptionInfo:
    """
    Get complete subscription information for a tenant.

    Args:
        tenant_id: The tenant ID

    Returns:
        SubscriptionInfo with all subscription details
    """
    from app.base_models import Tenant
    from app.core.feature_gate import get_tenant_tier
    from app.db.session import get_async_session

    async for db in get_async_session():
        result = await db.execute(
            select(Tenant.plan, Tenant.plan_expires_at).where(
                Tenant.id == tenant_id, Tenant.is_deleted == False
            )
        )
        row = result.one_or_none()

        if not row:
            # Tenant not found - return expired status
            return SubscriptionInfo(
                tenant_id=tenant_id,
                plan="unknown",
                tier=SubscriptionTier.STARTER,
                status=SubscriptionStatus.EXPIRED,
                expires_at=None,
                days_until_expiry=None,
                days_in_grace=None,
                is_access_restricted=True,
                restriction_reason="Tenant not found",
            )

        plan, plan_expires_at = row

        # Get tier
        tier = await get_tenant_tier(tenant_id)

        # Calculate status
        status, days_until_expiry, days_in_grace = calculate_subscription_status(
            plan, plan_expires_at
        )

        # Determine access restriction
        is_restricted = not is_access_allowed(status, allow_grace=True)
        restriction_reason = None

        if status == SubscriptionStatus.EXPIRED:
            restriction_reason = (
                f"Subscription expired {days_in_grace} days ago. Please renew to restore access."
            )
        elif status == SubscriptionStatus.GRACE_PERIOD:
            remaining_grace = GRACE_PERIOD_DAYS - (days_in_grace or 0)
            restriction_reason = (
                f"Subscription expired. {remaining_grace} days remaining in grace period."
            )
        elif status == SubscriptionStatus.CANCELLED:
            restriction_reason = "Subscription has been cancelled."

        return SubscriptionInfo(
            tenant_id=tenant_id,
            plan=plan,
            tier=tier,
            status=status,
            expires_at=plan_expires_at,
            days_until_expiry=days_until_expiry,
            days_in_grace=days_in_grace,
            is_access_restricted=is_restricted,
            restriction_reason=restriction_reason,
        )


async def check_subscription_valid(
    tenant_id: int, raise_on_invalid: bool = True
) -> SubscriptionInfo:
    """
    Check if a tenant's subscription is valid for access.

    Args:
        tenant_id: The tenant ID
        raise_on_invalid: If True, raises HTTPException when invalid

    Returns:
        SubscriptionInfo

    Raises:
        HTTPException: If subscription is invalid and raise_on_invalid is True
    """
    info = await get_subscription_info(tenant_id)

    if info.is_access_restricted and raise_on_invalid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "subscription_expired",
                "status": info.status.value,
                "message": info.restriction_reason or "Subscription has expired",
                "days_in_grace": info.days_in_grace,
                "renew_url": "/settings/billing",
            },
        )

    return info


# =============================================================================
# FastAPI Dependencies
# =============================================================================


class SubscriptionRequired:
    """
    FastAPI dependency that requires a valid subscription.

    Usage:
        @router.get("/premium-feature")
        async def premium_feature(
            sub: SubscriptionInfo = Depends(SubscriptionRequired())
        ):
            ...
    """

    def __init__(self, allow_grace: bool = True):
        """
        Args:
            allow_grace: If True, allows access during grace period
        """
        self.allow_grace = allow_grace

    async def __call__(self, request: Request) -> SubscriptionInfo:
        tenant_id = getattr(request.state, "tenant_id", None)

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        info = await get_subscription_info(tenant_id)

        # Check if access should be allowed
        if not is_access_allowed(info.status, self.allow_grace):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "subscription_expired",
                    "status": info.status.value,
                    "message": info.restriction_reason or "Subscription has expired",
                    "days_in_grace": info.days_in_grace,
                    "renew_url": "/settings/billing",
                },
            )

        # Store in request state for downstream use
        request.state.subscription_info = info

        return info


class SubscriptionWarning:
    """
    FastAPI dependency that adds subscription warnings to response.

    Doesn't block access, but adds warning headers for expiring subscriptions.

    Usage:
        @router.get("/data")
        async def get_data(
            sub: SubscriptionInfo = Depends(SubscriptionWarning())
        ):
            ...
    """

    async def __call__(self, request: Request) -> Optional[SubscriptionInfo]:
        tenant_id = getattr(request.state, "tenant_id", None)

        if not tenant_id:
            return None

        info = await get_subscription_info(tenant_id)

        # Store in request state
        request.state.subscription_info = info

        return info


async def get_subscription_dependency(request: Request) -> Optional[SubscriptionInfo]:
    """
    Simple dependency to get subscription info without blocking.

    Usage:
        @router.get("/status")
        async def get_status(
            sub: Optional[SubscriptionInfo] = Depends(get_subscription_dependency)
        ):
            ...
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        return None

    return await get_subscription_info(tenant_id)


# =============================================================================
# Utility Functions
# =============================================================================


def get_expiry_warning_message(info: SubscriptionInfo) -> Optional[str]:
    """Get a warning message for expiring/expired subscriptions."""
    if info.status == SubscriptionStatus.EXPIRING_SOON:
        return f"Your subscription expires in {info.days_until_expiry} days. Renew now to avoid interruption."

    elif info.status == SubscriptionStatus.GRACE_PERIOD:
        remaining = GRACE_PERIOD_DAYS - (info.days_in_grace or 0)
        return f"Your subscription has expired. You have {remaining} days to renew before access is restricted."

    elif info.status == SubscriptionStatus.EXPIRED:
        return "Your subscription has expired. Please renew to restore full access."

    return None


def calculate_next_billing_date(
    current_expiry: Optional[datetime],
    billing_period: str = "monthly",
) -> datetime:
    """Calculate the next billing date based on billing period."""
    base_date = current_expiry or datetime.now(UTC)

    if billing_period == "yearly":
        return base_date + timedelta(days=365)
    elif billing_period == "quarterly":
        return base_date + timedelta(days=90)
    else:  # monthly
        return base_date + timedelta(days=30)
