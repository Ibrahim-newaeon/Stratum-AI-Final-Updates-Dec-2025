# =============================================================================
# Stratum AI - Authentication Endpoints
# =============================================================================
"""
Authentication and authorization endpoints.
Handles login, registration, token refresh, and password reset.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_pii_for_lookup,
    verify_password,
)
from app.db.session import get_async_session
from app.models import AuditAction, AuditLog, User
from app.schemas import (
    APIResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Authenticate user and return access/refresh tokens.

    Args:
        login_data: Email and password

    Returns:
        JWT tokens for authentication
    """
    # Hash email for lookup (PII is stored encrypted)
    email_hash = hash_pii_for_lookup(login_data.email.lower())

    # Find user by email hash
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        logger.warning("login_failed", email_hash=email_hash[:16])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "email": login_data.email,  # Include for convenience
        },
    )
    refresh_token = create_refresh_token(subject=user.id)

    # Log login event
    audit_log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action=AuditAction.LOGIN,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    db.add(audit_log)
    await db.commit()

    logger.info("user_logged_in", user_id=user.id, tenant_id=user.tenant_id)

    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes
        ),
        message="Login successful",
    )


@router.post("/register", response_model=APIResponse[UserResponse])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Register a new user.

    Args:
        user_data: User registration details

    Returns:
        Created user information
    """
    from app.core.security import encrypt_pii

    # Check if email already exists
    email_hash = hash_pii_for_lookup(user_data.email.lower())
    result = await db.execute(
        select(User).where(
            User.tenant_id == user_data.tenant_id,
            User.email_hash == email_hash,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user with encrypted PII
    user = User(
        tenant_id=user_data.tenant_id,
        email=encrypt_pii(user_data.email.lower()),
        email_hash=email_hash,
        password_hash=get_password_hash(user_data.password),
        full_name=encrypt_pii(user_data.full_name) if user_data.full_name else None,
        role=user_data.role,
        locale=user_data.locale,
        timezone=user_data.timezone,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("user_registered", user_id=user.id, tenant_id=user.tenant_id)

    return APIResponse(
        success=True,
        data=UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user_data.email,  # Return original email
            full_name=user_data.full_name,
            role=user.role,
            locale=user.locale,
            timezone=user.timezone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        message="Registration successful",
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Refresh access token using refresh token.

    Args:
        token_data: Refresh token

    Returns:
        New access and refresh tokens
    """
    payload = decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = int(payload["sub"])

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "tenant_id": user.tenant_id,
            "role": user.role.value,
        },
    )
    refresh_token = create_refresh_token(subject=user.id)

    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60,
        ),
        message="Token refreshed",
    )


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Log out the current user.

    In a production system, this would invalidate the refresh token.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if user_id:
        # Log logout event
        audit_log = AuditLog(
            tenant_id=tenant_id or 0,
            user_id=user_id,
            action=AuditAction.LOGOUT,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit_log)
        await db.commit()

        logger.info("user_logged_out", user_id=user_id)

    return APIResponse(success=True, message="Logged out successfully")
