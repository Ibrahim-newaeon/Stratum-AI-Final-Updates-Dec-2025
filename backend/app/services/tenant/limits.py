# =============================================================================
# Stratum AI - Tenant Limit Enforcement Service
# =============================================================================
"""
Service for enforcing tenant resource limits based on subscription tier.

Enforces limits on:
- Number of users
- Number of ad accounts
- Number of segments
- Number of automations
- API rate limits
- Audience sync platforms
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import Campaign, Tenant, User
from app.core.logging import get_logger
from app.core.tiers import SubscriptionTier, TierLimits, get_tier_limits

logger = get_logger(__name__)


class LimitType(str, Enum):
    """Types of limits that can be checked."""

    USERS = "users"
    AD_ACCOUNTS = "ad_accounts"
    SEGMENTS = "segments"
    AUTOMATIONS = "automations"
    AUDIENCE_SYNC_PLATFORMS = "audience_sync_platforms"
    API_REQUESTS = "api_requests"


@dataclass
class LimitCheckResult:
    """Result of a limit check."""

    allowed: bool
    current_count: int
    max_allowed: int
    limit_type: LimitType
    message: Optional[str] = None


class TenantLimitService:
    """
    Service for checking and enforcing tenant resource limits.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_limits(self, tenant_id: int) -> TierLimits:
        """Get the limits for a tenant based on their tier."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Map plan names to subscription tiers (handles 'free' -> 'starter')
        plan_mapping = {
            "free": SubscriptionTier.STARTER,
            "starter": SubscriptionTier.STARTER,
            "professional": SubscriptionTier.PROFESSIONAL,
            "enterprise": SubscriptionTier.ENTERPRISE,
        }
        tier = plan_mapping.get(tenant.plan.lower(), SubscriptionTier.STARTER)
        return get_tier_limits(tier)

    async def check_user_limit(self, tenant_id: int) -> LimitCheckResult:
        """Check if tenant can add more users."""
        limits = await self.get_tenant_limits(tenant_id)

        # Count current active users
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.tenant_id == tenant_id)
            .where(User.is_deleted == False)
            .where(User.is_active == True)
        )
        current_count = result.scalar() or 0

        allowed = current_count < limits.max_users
        return LimitCheckResult(
            allowed=allowed,
            current_count=current_count,
            max_allowed=limits.max_users,
            limit_type=LimitType.USERS,
            message=None
            if allowed
            else f"User limit reached ({limits.max_users}). Upgrade to add more users.",
        )

    async def check_ad_account_limit(self, tenant_id: int) -> LimitCheckResult:
        """Check if tenant can connect more ad accounts."""
        limits = await self.get_tenant_limits(tenant_id)

        # Count unique ad accounts across campaigns
        result = await self.db.execute(
            select(func.count(func.distinct(Campaign.account_id)))
            .where(Campaign.tenant_id == tenant_id)
            .where(Campaign.is_deleted == False)
        )
        current_count = result.scalar() or 0

        allowed = current_count < limits.max_ad_accounts
        return LimitCheckResult(
            allowed=allowed,
            current_count=current_count,
            max_allowed=limits.max_ad_accounts,
            limit_type=LimitType.AD_ACCOUNTS,
            message=None
            if allowed
            else f"Ad account limit reached ({limits.max_ad_accounts}). Upgrade for more accounts.",
        )

    async def check_segment_limit(self, tenant_id: int) -> LimitCheckResult:
        """Check if tenant can create more segments."""
        limits = await self.get_tenant_limits(tenant_id)

        # Import here to avoid circular imports
        from app.models.cdp import CDPSegment

        result = await self.db.execute(
            select(func.count(CDPSegment.id)).where(CDPSegment.tenant_id == tenant_id)
        )
        current_count = result.scalar() or 0

        allowed = current_count < limits.max_segments
        return LimitCheckResult(
            allowed=allowed,
            current_count=current_count,
            max_allowed=limits.max_segments,
            limit_type=LimitType.SEGMENTS,
            message=None
            if allowed
            else f"Segment limit reached ({limits.max_segments}). Upgrade for more segments.",
        )

    async def check_automation_limit(self, tenant_id: int) -> LimitCheckResult:
        """Check if tenant can create more automations/rules."""
        limits = await self.get_tenant_limits(tenant_id)

        from app.base_models import Rule

        result = await self.db.execute(
            select(func.count(Rule.id))
            .where(Rule.tenant_id == tenant_id)
            .where(Rule.is_deleted == False)
        )
        current_count = result.scalar() or 0

        allowed = current_count < limits.max_automations
        return LimitCheckResult(
            allowed=allowed,
            current_count=current_count,
            max_allowed=limits.max_automations,
            limit_type=LimitType.AUTOMATIONS,
            message=None
            if allowed
            else f"Automation limit reached ({limits.max_automations}). Upgrade for more.",
        )

    async def check_audience_sync_platforms(self, tenant_id: int) -> LimitCheckResult:
        """Check how many audience sync platforms tenant can use."""
        limits = await self.get_tenant_limits(tenant_id)

        from app.models.audience_sync import PlatformAudience

        # Count distinct platforms used
        result = await self.db.execute(
            select(func.count(func.distinct(PlatformAudience.platform))).where(
                PlatformAudience.tenant_id == tenant_id
            )
        )
        current_count = result.scalar() or 0

        allowed = current_count < limits.max_audience_sync_platforms
        return LimitCheckResult(
            allowed=allowed,
            current_count=current_count,
            max_allowed=limits.max_audience_sync_platforms,
            limit_type=LimitType.AUDIENCE_SYNC_PLATFORMS,
            message=None
            if allowed
            else f"Platform limit reached ({limits.max_audience_sync_platforms}). Upgrade for more platforms.",
        )

    async def get_usage_summary(self, tenant_id: int) -> dict:
        """Get a summary of tenant's resource usage vs limits."""
        limits = await self.get_tenant_limits(tenant_id)

        users = await self.check_user_limit(tenant_id)
        ad_accounts = await self.check_ad_account_limit(tenant_id)
        segments = await self.check_segment_limit(tenant_id)
        automations = await self.check_automation_limit(tenant_id)
        platforms = await self.check_audience_sync_platforms(tenant_id)

        return {
            "users": {
                "current": users.current_count,
                "max": users.max_allowed,
                "percentage": (users.current_count / users.max_allowed * 100)
                if users.max_allowed > 0
                else 0,
            },
            "ad_accounts": {
                "current": ad_accounts.current_count,
                "max": ad_accounts.max_allowed,
                "percentage": (ad_accounts.current_count / ad_accounts.max_allowed * 100)
                if ad_accounts.max_allowed > 0
                else 0,
            },
            "segments": {
                "current": segments.current_count,
                "max": segments.max_allowed,
                "percentage": (segments.current_count / segments.max_allowed * 100)
                if segments.max_allowed > 0
                else 0,
            },
            "automations": {
                "current": automations.current_count,
                "max": automations.max_allowed,
                "percentage": (automations.current_count / automations.max_allowed * 100)
                if automations.max_allowed > 0
                else 0,
            },
            "audience_sync_platforms": {
                "current": platforms.current_count,
                "max": platforms.max_allowed,
                "percentage": (platforms.current_count / platforms.max_allowed * 100)
                if platforms.max_allowed > 0
                else 0,
            },
            "api_rate_limit_per_minute": limits.api_rate_limit_per_minute,
            "data_retention_days": limits.data_retention_days,
        }


async def check_tenant_limit(
    db: AsyncSession,
    tenant_id: int,
    limit_type: LimitType,
    raise_on_exceeded: bool = True,
) -> LimitCheckResult:
    """
    Convenience function to check a specific limit.

    Args:
        db: Database session
        tenant_id: Tenant to check
        limit_type: Type of limit to check
        raise_on_exceeded: If True, raises HTTPException when limit exceeded

    Returns:
        LimitCheckResult

    Raises:
        HTTPException: If limit exceeded and raise_on_exceeded is True
    """
    service = TenantLimitService(db)

    check_methods = {
        LimitType.USERS: service.check_user_limit,
        LimitType.AD_ACCOUNTS: service.check_ad_account_limit,
        LimitType.SEGMENTS: service.check_segment_limit,
        LimitType.AUTOMATIONS: service.check_automation_limit,
        LimitType.AUDIENCE_SYNC_PLATFORMS: service.check_audience_sync_platforms,
    }

    if limit_type not in check_methods:
        raise ValueError(f"Unknown limit type: {limit_type}")

    result = await check_methods[limit_type](tenant_id)

    if not result.allowed and raise_on_exceeded:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "limit_exceeded",
                "limit_type": limit_type.value,
                "current": result.current_count,
                "max": result.max_allowed,
                "message": result.message,
                "upgrade_url": "/settings/billing",
            },
        )

    return result


# FastAPI dependency for limit checking
class LimitChecker:
    """
    FastAPI dependency for checking tenant limits.

    Usage:
        @router.post("/users")
        async def create_user(
            limit_ok: bool = Depends(LimitChecker(LimitType.USERS))
        ):
            ...
    """

    def __init__(self, limit_type: LimitType):
        self.limit_type = limit_type

    async def __call__(
        self,
        request: Request,
        db: AsyncSession,
    ) -> bool:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant context required",
            )

        result = await check_tenant_limit(
            db=db,
            tenant_id=tenant_id,
            limit_type=self.limit_type,
            raise_on_exceeded=True,
        )

        return result.allowed
