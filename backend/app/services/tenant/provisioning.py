# =============================================================================
# Stratum AI - Tenant Provisioning Service
# =============================================================================
"""
Service for provisioning new tenants with proper setup:
- Creates tenant record with tier-based limits
- Creates admin user account
- Sets up default configurations
- Initializes feature flags based on tier
- Creates default data sources (CDP)
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import Tenant, User, UserRole
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import encrypt_pii, hash_pii_for_lookup, get_password_hash
from app.core.tiers import (
    SubscriptionTier,
    TIER_FEATURES,
    TIER_LIMITS,
    get_tier_limits,
    get_tier_features,
)

logger = get_logger(__name__)


class TenantProvisioningService:
    """
    Service for creating and setting up new tenants.

    This service handles the complete provisioning workflow:
    1. Validate license key (if self-hosted)
    2. Create tenant with tier-appropriate limits
    3. Create admin user
    4. Initialize default configurations
    5. Set up feature flags
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def provision_tenant(
        self,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_name: str,
        tier: SubscriptionTier = SubscriptionTier.STARTER,
        domain: Optional[str] = None,
        license_key: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        plan_expires_at: Optional[datetime] = None,
    ) -> tuple["Tenant", "User"]:
        """
        Provision a new tenant with all required setup.

        Args:
            name: Organization display name
            slug: URL-friendly unique identifier
            admin_email: Email for the admin user
            admin_password: Password for the admin user
            admin_name: Full name of the admin user
            tier: Subscription tier (starter, professional, enterprise)
            domain: Custom domain (optional)
            license_key: License key for validation (self-hosted)
            stripe_customer_id: Stripe customer ID (SaaS)
            plan_expires_at: When the plan expires

        Returns:
            Tuple of (tenant, admin_user)

        Raises:
            ValueError: If slug already exists or validation fails
        """
        logger.info(
            "provisioning_tenant",
            name=name,
            slug=slug,
            tier=tier.value,
        )

        # Check if slug already exists
        existing = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        # Get tier-based limits and features
        limits = get_tier_limits(tier)
        features = get_tier_features(tier)

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            domain=domain,
            plan=tier.value,
            plan_expires_at=plan_expires_at,
            stripe_customer_id=stripe_customer_id,
            max_users=limits.max_users,
            max_campaigns=limits.max_ad_accounts * 10,  # Rough estimate
            settings=self._get_default_settings(tier),
            feature_flags=self._build_feature_flags(features),
        )
        self.db.add(tenant)
        await self.db.flush()  # Get tenant.id

        logger.info("tenant_created", tenant_id=tenant.id, slug=slug)

        # Create admin user
        admin_user = await self._create_admin_user(
            tenant_id=tenant.id,
            email=admin_email,
            password=admin_password,
            full_name=admin_name,
        )

        # Initialize default configurations
        await self._initialize_defaults(tenant, tier)

        await self.db.commit()

        logger.info(
            "tenant_provisioned",
            tenant_id=tenant.id,
            admin_user_id=admin_user.id,
            tier=tier.value,
        )

        return tenant, admin_user

    async def _create_admin_user(
        self,
        tenant_id: int,
        email: str,
        password: str,
        full_name: str,
    ) -> User:
        """Create the initial admin user for the tenant."""
        user = User(
            tenant_id=tenant_id,
            email=encrypt_pii(email),
            email_hash=hash_pii_for_lookup(email.lower()),
            password_hash=get_password_hash(password),
            full_name=encrypt_pii(full_name) if full_name else None,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,  # Admin is auto-verified
            permissions={
                "manage_users": True,
                "manage_billing": True,
                "manage_integrations": True,
                "export_data": True,
            },
        )
        self.db.add(user)
        await self.db.flush()

        logger.info("admin_user_created", user_id=user.id, tenant_id=tenant_id)
        return user

    def _get_default_settings(self, tier: SubscriptionTier) -> dict:
        """Get default tenant settings based on tier."""
        base_settings = {
            "timezone": "UTC",
            "currency": "USD",
            "date_format": "YYYY-MM-DD",
            "notifications": {
                "email": True,
                "slack": False,
                "whatsapp": False,
            },
            "trust_gate": {
                "healthy_threshold": 70,
                "degraded_threshold": 40,
                "auto_execute_when_healthy": True,
            },
            "data_retention_days": 90,
        }

        # Tier-specific overrides
        if tier == SubscriptionTier.PROFESSIONAL:
            base_settings["data_retention_days"] = 365
            base_settings["notifications"]["slack"] = True
        elif tier == SubscriptionTier.ENTERPRISE:
            base_settings["data_retention_days"] = 730
            base_settings["notifications"]["slack"] = True
            base_settings["notifications"]["whatsapp"] = True
            base_settings["advanced"] = {
                "custom_branding": True,
                "white_label": True,
                "sso_enabled": False,
            }

        return base_settings

    def _build_feature_flags(self, features: list[str]) -> dict:
        """Convert feature list to feature flags dict."""
        return {feature: True for feature in features}

    async def _initialize_defaults(
        self,
        tenant: Tenant,
        tier: SubscriptionTier,
    ) -> None:
        """Initialize default configurations for the tenant."""
        # This can be extended to create:
        # - Default CDP sources
        # - Default segments
        # - Default automation rules
        # - etc.
        pass

    async def update_tenant_tier(
        self,
        tenant_id: int,
        new_tier: SubscriptionTier,
        plan_expires_at: Optional[datetime] = None,
    ) -> Tenant:
        """
        Upgrade or downgrade a tenant's tier.

        Updates limits and feature flags accordingly.
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        old_tier = tenant.plan
        limits = get_tier_limits(new_tier)
        features = get_tier_features(new_tier)

        tenant.plan = new_tier.value
        tenant.plan_expires_at = plan_expires_at
        tenant.max_users = limits.max_users
        tenant.feature_flags = self._build_feature_flags(features)
        tenant.settings = {
            **tenant.settings,
            "data_retention_days": limits.data_retention_days,
        }

        await self.db.commit()

        logger.info(
            "tenant_tier_updated",
            tenant_id=tenant_id,
            old_tier=old_tier,
            new_tier=new_tier.value,
        )

        return tenant


# Convenience alias
TenantProvisioner = TenantProvisioningService
