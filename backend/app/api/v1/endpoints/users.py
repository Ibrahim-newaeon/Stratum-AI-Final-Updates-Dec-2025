# =============================================================================
# Stratum AI - User Management Endpoints
# =============================================================================
"""
User profile and management endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decrypt_pii, encrypt_pii, get_password_hash
from app.db.session import get_async_session
from app.models import User
from app.schemas import APIResponse, UserProfileResponse, UserResponse, UserUpdate

logger = get_logger(__name__)
router = APIRouter()


@router.get("/me", response_model=APIResponse[UserProfileResponse])
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get the current authenticated user's profile."""
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Decrypt PII for response
    return APIResponse(
        success=True,
        data=UserProfileResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=decrypt_pii(user.email),
            full_name=decrypt_pii(user.full_name) if user.full_name else None,
            phone=decrypt_pii(user.phone) if user.phone else None,
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            preferences=user.preferences,
            consent_marketing=user.consent_marketing,
            consent_analytics=user.consent_analytics,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.patch("/me", response_model=APIResponse[UserProfileResponse])
async def update_current_user(
    request: Request,
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update the current user's profile."""
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    # Encrypt PII fields
    if "full_name" in update_dict and update_dict["full_name"]:
        update_dict["full_name"] = encrypt_pii(update_dict["full_name"])
    if "phone" in update_dict and update_dict["phone"]:
        update_dict["phone"] = encrypt_pii(update_dict["phone"])

    for field, value in update_dict.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return APIResponse(
        success=True,
        data=UserProfileResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=decrypt_pii(user.email),
            full_name=decrypt_pii(user.full_name) if user.full_name else None,
            phone=decrypt_pii(user.phone) if user.phone else None,
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            preferences=user.preferences,
            consent_marketing=user.consent_marketing,
            consent_analytics=user.consent_analytics,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        message="Profile updated successfully",
    )


@router.get("", response_model=APIResponse[List[UserResponse]])
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = 0,
    limit: int = 50,
):
    """
    List all users in the tenant.
    Requires admin or manager role.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id, User.is_deleted == False)
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            UserResponse(
                id=u.id,
                tenant_id=u.tenant_id,
                email=decrypt_pii(u.email),
                full_name=decrypt_pii(u.full_name) if u.full_name else None,
                role=u.role,
                locale=u.locale,
                timezone=u.timezone,
                is_active=u.is_active,
                is_verified=u.is_verified,
                last_login_at=u.last_login_at,
                avatar_url=u.avatar_url,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            for u in users
        ],
    )
