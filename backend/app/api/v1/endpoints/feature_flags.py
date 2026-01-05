# =============================================================================
# Stratum AI - Feature Flags API Router
# =============================================================================
"""
API endpoints for managing tenant feature flags.

Tenant routes:
- GET /api/tenant/{tenant_id}/features - Get tenant features
- PUT /api/tenant/{tenant_id}/features - Update tenant features (admin only)

Superadmin routes:
- GET /api/superadmin/tenants/{tenant_id}/features - Get any tenant's features
- PUT /api/superadmin/tenants/{tenant_id}/features - Update any tenant's features
- POST /api/superadmin/tenants/{tenant_id}/features/reset - Reset to defaults
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.features.service import FeatureFlagsService
from app.features.flags import (
    FeatureFlags,
    FeatureFlagsUpdate,
    FEATURE_CATEGORIES,
    FEATURE_DESCRIPTIONS,
)
from app.schemas.response import APIResponse


# =============================================================================
# Tenant Routes
# =============================================================================

tenant_router = APIRouter(prefix="/tenant/{tenant_id}", tags=["feature-flags"])


@tenant_router.get("/features", response_model=APIResponse[Dict[str, Any]])
async def get_tenant_features(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get feature flags for the current tenant.
    Returns merged flags (plan defaults + tenant overrides).
    """
    # Enforce tenant context
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    service = FeatureFlagsService(db)
    features = await service.get_tenant_features(tenant_id)

    return APIResponse(
        success=True,
        data={
            "features": features,
            "categories": FEATURE_CATEGORIES,
            "descriptions": FEATURE_DESCRIPTIONS,
        },
    )


@tenant_router.put("/features", response_model=APIResponse[Dict[str, Any]])
async def update_tenant_features(
    request: Request,
    tenant_id: int,
    updates: FeatureFlagsUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update feature flags for the current tenant.
    Requires tenant_admin role.
    """
    # Enforce tenant context
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Check admin role
    user_role = getattr(request.state, "user_role", None)
    if user_role not in ["superadmin", "admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Admin role required")

    user_id = getattr(request.state, "user_id", None)
    service = FeatureFlagsService(db)
    features = await service.update_tenant_features(tenant_id, updates, user_id)

    return APIResponse(
        success=True,
        data={"features": features},
        message="Features updated successfully",
    )


# =============================================================================
# Superadmin Routes
# =============================================================================

superadmin_router = APIRouter(prefix="/superadmin", tags=["superadmin-features"])


@superadmin_router.get("/tenants/{tenant_id}/features", response_model=APIResponse[Dict[str, Any]])
async def superadmin_get_tenant_features(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get feature flags for any tenant (superadmin only).
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin role required")

    service = FeatureFlagsService(db)
    features = await service.get_tenant_features(tenant_id)

    return APIResponse(
        success=True,
        data={
            "tenant_id": tenant_id,
            "features": features,
            "categories": FEATURE_CATEGORIES,
            "descriptions": FEATURE_DESCRIPTIONS,
        },
    )


@superadmin_router.put("/tenants/{tenant_id}/features", response_model=APIResponse[Dict[str, Any]])
async def superadmin_update_tenant_features(
    request: Request,
    tenant_id: int,
    updates: FeatureFlagsUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update feature flags for any tenant (superadmin only).
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin role required")

    user_id = getattr(request.state, "user_id", None)
    service = FeatureFlagsService(db)
    features = await service.update_tenant_features(tenant_id, updates, user_id)

    # TODO: Log to audit_log

    return APIResponse(
        success=True,
        data={"tenant_id": tenant_id, "features": features},
        message="Features updated successfully",
    )


@superadmin_router.post("/tenants/{tenant_id}/features/reset", response_model=APIResponse[Dict[str, Any]])
async def superadmin_reset_tenant_features(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reset tenant features to plan defaults (superadmin only).
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin role required")

    service = FeatureFlagsService(db)
    features = await service.reset_tenant_features(tenant_id)

    return APIResponse(
        success=True,
        data={"tenant_id": tenant_id, "features": features},
        message="Features reset to plan defaults",
    )


@superadmin_router.get("/feature-metadata", response_model=APIResponse[Dict[str, Any]])
async def get_feature_metadata(request: Request):
    """
    Get feature categories and descriptions for UI.
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin role required")

    return APIResponse(
        success=True,
        data={
            "categories": FEATURE_CATEGORIES,
            "descriptions": FEATURE_DESCRIPTIONS,
        },
    )


# =============================================================================
# Combined Router for API Registration
# =============================================================================

router = APIRouter()
router.include_router(tenant_router)
router.include_router(superadmin_router)
