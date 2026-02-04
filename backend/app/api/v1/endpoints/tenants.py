# =============================================================================
# Stratum AI - Tenant Management Endpoints
# =============================================================================
"""
Tenant (Organization) management endpoints.
Provides CRUD operations for multi-tenant administration.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Tenant, User, UserRole
from app.schemas import (
    APIResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


def require_admin(request: Request) -> int:
    """Verify user has admin role."""
    user_role = getattr(request.state, "role", None)
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if user_role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user_id


@router.get("", response_model=APIResponse[list[TenantResponse]])
async def list_tenants(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
):
    """
    List all tenants.
    Requires admin role for full list, otherwise returns only user's tenant.
    """
    user_role = getattr(request.state, "role", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(Tenant).where(Tenant.is_deleted == False)

    # Non-admin users can only see their own tenant
    if user_role != UserRole.ADMIN.value:
        query = query.where(Tenant.id == tenant_id)

    # Search filter
    if search:
        query = query.where((Tenant.name.ilike(f"%{search}%")) | (Tenant.slug.ilike(f"%{search}%")))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    tenants = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            TenantResponse(
                id=t.id,
                name=t.name,
                slug=t.slug,
                domain=t.domain,
                plan=t.plan,
                plan_expires_at=t.plan_expires_at,
                max_users=t.max_users,
                max_campaigns=t.max_campaigns,
                settings=t.settings or {},
                feature_flags=t.feature_flags or {},
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tenants
        ],
    )


@router.get("/current", response_model=APIResponse[TenantResponse])
async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get the current user's tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
    )


@router.get("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def get_tenant(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific tenant by ID."""
    user_role = getattr(request.state, "role", None)
    user_tenant_id = getattr(request.state, "tenant_id", None)

    # Non-admin can only view their own tenant
    if user_role != UserRole.ADMIN.value and tenant_id != user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
    )


@router.post("", response_model=APIResponse[TenantResponse], status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: Request,
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a new tenant.
    Requires admin role.
    """
    require_admin(request)

    # Check for duplicate slug
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_data.slug))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists",
        )

    # Set plan limits based on plan type
    plan_limits = {
        "free": {"max_users": 5, "max_campaigns": 10},
        "starter": {"max_users": 10, "max_campaigns": 50},
        "professional": {"max_users": 25, "max_campaigns": 200},
        "enterprise": {"max_users": 100, "max_campaigns": 1000},
    }

    limits = plan_limits.get(tenant_data.plan, plan_limits["free"])

    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        domain=tenant_data.domain,
        plan=tenant_data.plan,
        max_users=limits["max_users"],
        max_campaigns=limits["max_campaigns"],
        settings={},
        feature_flags={},
    )

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant created: {tenant.slug} (ID: {tenant.id})")

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
        message="Tenant created successfully",
    )


@router.patch("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def update_tenant(
    request: Request,
    tenant_id: int,
    update_data: TenantUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update a tenant.
    Admin can update any tenant, managers can update their own tenant.
    """
    user_role = getattr(request.state, "role", None)
    user_tenant_id = getattr(request.state, "tenant_id", None)

    # Check permissions
    if user_role not in [UserRole.ADMIN.value, UserRole.MANAGER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager access required",
        )

    # Non-admin can only update their own tenant
    if user_role != UserRole.ADMIN.value and tenant_id != user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant updated: {tenant.slug} (ID: {tenant.id})")

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
        message="Tenant updated successfully",
    )


@router.delete("/{tenant_id}", response_model=APIResponse[None])
async def delete_tenant(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Soft delete a tenant.
    Requires admin role.
    """
    require_admin(request)

    user_tenant_id = getattr(request.state, "tenant_id", None)

    # Prevent self-deletion
    if tenant_id == user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own tenant",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Soft delete
    tenant.is_deleted = True
    await db.commit()

    logger.info(f"Tenant deleted: {tenant.slug} (ID: {tenant.id})")

    return APIResponse(
        success=True,
        message="Tenant deleted successfully",
    )


@router.get("/{tenant_id}/users", response_model=APIResponse[dict])
async def get_tenant_users(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get users count and list for a tenant.
    """
    user_role = getattr(request.state, "role", None)
    user_tenant_id = getattr(request.state, "tenant_id", None)

    # Non-admin can only view their own tenant
    if user_role != UserRole.ADMIN.value and tenant_id != user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Get user count
    count_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id, User.is_deleted == False)
    )
    user_count = count_result.scalar()

    return APIResponse(
        success=True,
        data={
            "tenant_id": tenant_id,
            "user_count": user_count,
            "max_users": tenant.max_users,
            "slots_available": tenant.max_users - user_count,
        },
    )


@router.patch("/{tenant_id}/plan", response_model=APIResponse[TenantResponse])
async def update_tenant_plan(
    request: Request,
    tenant_id: int,
    plan: str = Query(..., regex="^(free|starter|professional|enterprise)$"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update tenant subscription plan.
    Requires admin role.
    """
    require_admin(request)

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Update plan and limits
    plan_limits = {
        "free": {"max_users": 5, "max_campaigns": 10},
        "starter": {"max_users": 10, "max_campaigns": 50},
        "professional": {"max_users": 25, "max_campaigns": 200},
        "enterprise": {"max_users": 100, "max_campaigns": 1000},
    }

    limits = plan_limits[plan]
    tenant.plan = plan
    tenant.max_users = limits["max_users"]
    tenant.max_campaigns = limits["max_campaigns"]

    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant plan updated: {tenant.slug} -> {plan}")

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
        message=f"Plan updated to {plan}",
    )


@router.patch("/{tenant_id}/features", response_model=APIResponse[TenantResponse])
async def update_tenant_features(
    request: Request,
    tenant_id: int,
    feature_flags: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update tenant feature flags.
    Requires admin role.
    """
    require_admin(request)

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Merge feature flags
    current_flags = tenant.feature_flags or {}
    current_flags.update(feature_flags)
    tenant.feature_flags = current_flags

    await db.commit()
    await db.refresh(tenant)

    logger.info(f"Tenant features updated: {tenant.slug}")

    return APIResponse(
        success=True,
        data=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan,
            plan_expires_at=tenant.plan_expires_at,
            max_users=tenant.max_users,
            max_campaigns=tenant.max_campaigns,
            settings=tenant.settings or {},
            feature_flags=tenant.feature_flags or {},
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        ),
        message="Feature flags updated",
    )
