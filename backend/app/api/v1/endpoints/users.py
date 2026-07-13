# =============================================================================
# Stratum AI - User Management Endpoints
# =============================================================================
"""
User profile and management endpoints.
"""

import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import (
    decrypt_pii,
    encrypt_pii,
    get_password_hash,
    hash_pii_for_lookup,
    looks_like_pii_ciphertext,
)
from app.db.session import get_async_session
from app.models import Tenant, User, UserRole
from app.schemas import APIResponse, UserProfileResponse, UserResponse, UserUpdate
from app.services.email_service import get_email_service


class InviteUserRequest(BaseModel):
    """Request schema for inviting a new user."""

    email: EmailStr
    full_name: Optional[str] = None
    role: str = Field(default="user", description="User role: admin, manager, user")
    department: Optional[str] = Field(None, max_length=100)


def _safe_decrypt(value: Optional[str], tenant_id: Optional[int]) -> Optional[str]:
    """Decrypt PII; fail CLOSED for ciphertext, echo only legacy plaintext.

    Undecryptable *ciphertext* (key drift, corruption) returns ``None`` —
    encrypted blobs must never leak into API responses. A value that does
    not look like ``encrypt_pii`` output is a genuine pre-encryption
    plaintext row and is returned as-is so it still displays.
    """
    if not value:
        return None
    try:
        return decrypt_pii(value, tenant_id)
    except (ValueError, TypeError, KeyError, OSError):
        return None if looks_like_pii_ciphertext(value) else value


class UpdateUserRequest(BaseModel):
    """Request schema for admin updating a user."""

    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    department: Optional[str] = Field(None, max_length=100)


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
            email=_safe_decrypt(user.email, user.tenant_id) or "",
            full_name=_safe_decrypt(user.full_name, user.tenant_id),
            phone=_safe_decrypt(user.phone, user.tenant_id),
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            cms_role=user.cms_role,
            department=user.department,
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

    # Handle preferences merging (don't overwrite, merge)
    if "preferences" in update_dict and update_dict["preferences"]:
        existing_prefs = user.preferences or {}
        merged = {**existing_prefs, **update_dict["preferences"]}
        update_dict["preferences"] = merged

    # Encrypt PII fields
    if "full_name" in update_dict and update_dict["full_name"]:
        update_dict["full_name"] = encrypt_pii(update_dict["full_name"], user.tenant_id)
    if "phone" in update_dict and update_dict["phone"]:
        update_dict["phone"] = encrypt_pii(update_dict["phone"], user.tenant_id)

    for field, value in update_dict.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()

    return APIResponse(
        success=True,
        data=UserProfileResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=_safe_decrypt(user.email, user.tenant_id) or "",
            full_name=_safe_decrypt(user.full_name, user.tenant_id),
            phone=_safe_decrypt(user.phone, user.tenant_id),
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            cms_role=user.cms_role,
            department=user.department,
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
    requester_role = getattr(request.state, "role", None)

    # Enforce role-based access control
    if requester_role not in ["admin", "manager", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can list users",
        )

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
                email=_safe_decrypt(u.email, u.tenant_id) or "",
                full_name=(
                    _safe_decrypt(u.full_name, u.tenant_id) if u.full_name else None
                ),
                role=u.role,
                locale=u.locale,
                timezone=u.timezone,
                is_active=u.is_active,
                is_verified=u.is_verified,
                last_login_at=u.last_login_at,
                avatar_url=u.avatar_url,
                department=u.department,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            for u in users
        ],
    )


@router.post("/invite", response_model=APIResponse[UserResponse])
async def invite_user(
    request: Request,
    invite_data: InviteUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Invite a new user to the tenant.
    Requires admin role.
    Sends an invitation email with a link to set their password.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    requester_role = getattr(request.state, "role", None)
    requester_id = getattr(request.state, "user_id", None)

    # Only admins can invite users
    if requester_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can invite users",
        )

    # Check if email already exists
    email_hash = hash_pii_for_lookup(invite_data.email.lower())
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email_hash == email_hash,
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user and existing_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Tier-limit gate — raises 402 with structured upgrade payload
    # when the tenant's max_users ceiling is hit (see services/
    # tenant/limits.py + frontend UpgradePromptProvider listener).
    # Skipped when refreshing a pending invite: that user already
    # counts against the ceiling, and a lost email must be resendable.
    from app.services.tenant.limits import LimitType, check_tenant_limit

    if tenant_id and existing_user is None:
        await check_tenant_limit(db, tenant_id, LimitType.USERS, raise_on_exceeded=True)

    # Map role string to enum
    role_map = {
        "admin": UserRole.ADMIN,
        "manager": UserRole.MANAGER,
        "analyst": UserRole.ANALYST,
        "viewer": UserRole.VIEWER,
        "user": UserRole.ANALYST,
    }
    user_role = role_map.get(invite_data.role.lower(), UserRole.ANALYST)

    # Create user with temporary password (will need to set password on first login)
    temp_password = secrets.token_urlsafe(16)

    if existing_user:
        # Invited before but never accepted — refresh the pending invite
        # (new token + email) instead of dead-ending on "already exists".
        user = existing_user
        user.role = user_role
        if "department" in invite_data.model_fields_set:
            user.department = invite_data.department
        if invite_data.full_name:
            user.full_name = encrypt_pii(invite_data.full_name, user.tenant_id)
    else:
        user = User(
            tenant_id=tenant_id,
            email=encrypt_pii(invite_data.email.lower(), tenant_id),
            email_hash=email_hash,
            password_hash=get_password_hash(temp_password),
            full_name=(
                encrypt_pii(invite_data.full_name, tenant_id)
                if invite_data.full_name
                else None
            ),
            role=user_role,
            department=invite_data.department,
            is_active=True,
            is_verified=False,  # Verified when the invite is accepted
        )
        db.add(user)

    await db.flush()  # assign user.id; commit only after the token is stored

    # Generate the invite token and persist it (hashed) in Redis so
    # POST /auth/accept-invite can redeem it. Stored BEFORE the commit:
    # if Redis is down we roll the user back rather than creating an
    # account whose invitation link can never work.
    invite_token = secrets.token_urlsafe(32)

    try:
        import hashlib

        from app.api.v1.endpoints.auth import (
            INVITE_TOKEN_EXPIRY_SECONDS,
            INVITE_TOKEN_PREFIX,
            get_redis_client,
        )

        token_hash = hashlib.sha256(invite_token.encode()).hexdigest()
        redis_client = await get_redis_client()
        await redis_client.setex(
            f"{INVITE_TOKEN_PREFIX}{token_hash}",
            INVITE_TOKEN_EXPIRY_SECONDS,
            str(user.id),
        )
        await redis_client.close()
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_store_invite_token_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate invitation link. Please try again.",
        )

    await db.commit()

    # Get inviter name and tenant name for the email
    inviter_name = "An administrator"
    tenant_name = "your organization"

    try:
        # Get inviter's name
        if requester_id:
            inviter_result = await db.execute(
                select(User).where(User.id == requester_id)
            )
            inviter = inviter_result.scalar_one_or_none()
            if inviter and inviter.full_name:
                inviter_name = (
                    _safe_decrypt(inviter.full_name, inviter.tenant_id)
                    or "An administrator"
                )

        # Get tenant name
        if tenant_id:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                tenant_name = tenant.name
    except (ValueError, TypeError, KeyError, OSError) as e:
        logger.warning("fetch_inviter_tenant_details_failed", error=str(e))

    # Send invite email in background
    def send_invite_email():
        try:
            email_service = get_email_service()
            email_service.send_user_invite_email(
                to_email=invite_data.email,
                inviter_name=inviter_name,
                tenant_name=tenant_name,
                invite_token=invite_token,
                role=invite_data.role,
            )
            logger.info(f"Invite email sent to {invite_data.email}")
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
            logger.error(
                "send_invite_email_failed", email=invite_data.email, error=str(e)
            )

    background_tasks.add_task(send_invite_email)

    logger.info(f"Invited user {user.id} to tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=invite_data.email,
            full_name=invite_data.full_name,
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            department=user.department,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        message="User invited successfully",
    )


@router.patch("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    request: Request,
    user_id: int,
    update_data: UpdateUserRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update a user's details.
    Requires admin role.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    requester_role = getattr(request.state, "role", None)

    # Only admins can update other users
    if requester_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update users",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    if update_data.full_name is not None:
        user.full_name = (
            encrypt_pii(update_data.full_name, user.tenant_id)
            if update_data.full_name
            else None
        )

    if update_data.role is not None:
        role_map = {
            "admin": UserRole.ADMIN,
            "manager": UserRole.MANAGER,
            "analyst": UserRole.ANALYST,
            "viewer": UserRole.VIEWER,
            "user": UserRole.ANALYST,
        }
        user.role = role_map.get(update_data.role.lower(), user.role)

    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    # model_fields_set so an explicit null clears the department
    if "department" in update_data.model_fields_set:
        user.department = update_data.department

    await db.commit()

    logger.info(f"Updated user {user_id} in tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=_safe_decrypt(user.email, user.tenant_id) or "",
            full_name=(
                _safe_decrypt(user.full_name, user.tenant_id)
                if user.full_name
                else None
            ),
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            department=user.department,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        message="User updated successfully",
    )


@router.delete("/{user_id}", response_model=APIResponse)
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Remove a user from the tenant (soft delete).
    Requires admin role.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    requester_id = getattr(request.state, "user_id", None)
    requester_role = getattr(request.state, "role", None)

    # Only admins can delete users
    if requester_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove users",
        )

    # Cannot delete yourself
    if user_id == requester_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Soft delete
    user.is_deleted = True
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(f"Deleted user {user_id} from tenant {tenant_id}")

    return APIResponse(
        success=True,
        message="User removed successfully",
    )
