# =============================================================================
# Stratum AI - Feature Flags Service
# =============================================================================
"""
Service layer for managing tenant feature flags.
Handles fetching, updating, and caching of feature configurations.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.flags import (
    FEATURE_CATEGORIES,
    FEATURE_DESCRIPTIONS,
    FeatureFlags,
    FeatureFlagsUpdate,
    get_default_features,
    merge_features,
)
from app.models import Tenant


class FeatureFlagsService:
    """Service for managing tenant feature flags."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_features(self, tenant_id: int) -> dict[str, Any]:
        """
        Get complete feature flags for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Merged feature flags (defaults + overrides)
        """
        result = await self.db.execute(
            select(Tenant.plan, Tenant.feature_flags).where(Tenant.id == tenant_id)
        )
        row = result.first()

        if not row:
            # Return starter defaults if tenant not found
            return get_default_features("starter")

        plan, overrides = row
        defaults = get_default_features(plan or "starter")
        return merge_features(defaults, overrides)

    async def get_feature_flags_model(self, tenant_id: int) -> FeatureFlags:
        """
        Get feature flags as a validated Pydantic model.

        Args:
            tenant_id: Tenant ID

        Returns:
            FeatureFlags model
        """
        features = await self.get_tenant_features(tenant_id)
        return FeatureFlags(**features)

    async def update_tenant_features(
        self,
        tenant_id: int,
        updates: FeatureFlagsUpdate,
        updated_by_user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Update tenant feature flags (merge with existing overrides).

        Args:
            tenant_id: Tenant ID
            updates: Feature flag updates
            updated_by_user_id: ID of user making the update

        Returns:
            Updated feature flags
        """
        # Get current overrides
        result = await self.db.execute(select(Tenant.feature_flags).where(Tenant.id == tenant_id))
        current_overrides = result.scalar_one_or_none() or {}

        # Merge updates
        update_dict = updates.model_dump(exclude_unset=True)
        new_overrides = {**current_overrides, **update_dict}

        # Update tenant
        await self.db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                feature_flags=new_overrides,
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.commit()

        # Return merged features
        return await self.get_tenant_features(tenant_id)

    async def reset_tenant_features(self, tenant_id: int) -> dict[str, Any]:
        """
        Reset tenant features to plan defaults.

        Args:
            tenant_id: Tenant ID

        Returns:
            Default feature flags for tenant's plan
        """
        await self.db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                feature_flags={},
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.commit()

        return await self.get_tenant_features(tenant_id)

    async def can(self, tenant_id: int, feature_name: str) -> bool:
        """
        Check if a feature is enabled for a tenant.

        Args:
            tenant_id: Tenant ID
            feature_name: Feature name to check

        Returns:
            True if feature is enabled
        """
        features = await self.get_tenant_features(tenant_id)
        value = features.get(feature_name)

        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value > 0
        return bool(value)

    def get_feature_categories(self) -> dict[str, Any]:
        """Get feature categories for UI grouping."""
        return FEATURE_CATEGORIES

    def get_feature_descriptions(self) -> dict[str, str]:
        """Get feature descriptions for UI display."""
        return FEATURE_DESCRIPTIONS


async def get_tenant_features(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    """
    Convenience function to get tenant features.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Feature flags dict
    """
    service = FeatureFlagsService(db)
    return await service.get_tenant_features(tenant_id)


async def can_access_feature(db: AsyncSession, tenant_id: int, feature: str) -> bool:
    """
    Convenience function to check feature access.

    Args:
        db: Database session
        tenant_id: Tenant ID
        feature: Feature name

    Returns:
        True if feature is enabled
    """
    service = FeatureFlagsService(db)
    return await service.can(tenant_id, feature)
