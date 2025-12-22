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
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_pii_for_lookup,
    verify_password,
    verify_password_reset_token,
)
from app.db.session import get_async_session
from app.models import AuditAction, AuditLog, Tenant, User, UserRole
from app.schemas import (
    APIResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TenantResponse,
    TenantSignUp,
    TenantSignUpResponse,
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


@router.post("/signup", response_model=APIResponse[TenantSignUpResponse])
async def signup(
    signup_data: TenantSignUp,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Self-service tenant sign-up.
    Creates a new tenant and admin user in one step.

    Args:
        signup_data: Company name, admin email, password, and full name

    Returns:
        Created tenant, user, and JWT tokens
    """
    import re
    from app.core.security import encrypt_pii

    # Generate slug from company name
    slug = re.sub(r"[^a-z0-9]+", "-", signup_data.company_name.lower()).strip("-")

    # Ensure slug uniqueness
    base_slug = slug
    counter = 1
    while True:
        result = await db.execute(select(Tenant).where(Tenant.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Check if email already exists globally
    email_hash = hash_pii_for_lookup(signup_data.email.lower())
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please login or use a different email.",
        )

    # Import plan configuration
    from app.core.plans import get_plan_config, get_trial_expiry, TRIAL_DURATION_DAYS

    # Get trial plan limits
    trial_config = get_plan_config("trial")
    trial_limits = trial_config["limits"]

    # Create tenant with trial plan (14-day trial)
    tenant = Tenant(
        name=signup_data.company_name,
        slug=slug,
        plan="trial",
        plan_expires_at=get_trial_expiry(),
        max_users=trial_limits["max_users"],
        max_campaigns=trial_limits["max_campaigns"],
        settings={
            "trial_started_at": datetime.now(timezone.utc).isoformat(),
            "trial_duration_days": TRIAL_DURATION_DAYS,
        },
        feature_flags=trial_config["features"],
    )

    db.add(tenant)
    await db.flush()  # Get tenant ID without committing

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=encrypt_pii(signup_data.email.lower()),
        email_hash=email_hash,
        password_hash=get_password_hash(signup_data.password),
        full_name=encrypt_pii(signup_data.full_name),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=False,
        locale="en",
        timezone="UTC",
    )

    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "tenant_id": tenant.id,
            "role": user.role.value,
        },
    )
    refresh_token = create_refresh_token(subject=user.id)

    logger.info(
        "tenant_signup",
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        user_id=user.id,
    )

    return APIResponse(
        success=True,
        data=TenantSignUpResponse(
            tenant=TenantResponse(
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
            user=UserResponse(
                id=user.id,
                tenant_id=user.tenant_id,
                email=signup_data.email,
                full_name=signup_data.full_name,
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
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        message="Sign-up successful! Welcome to Stratum AI.",
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


@router.post("/forgot-password", response_model=APIResponse[PasswordResetResponse])
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Request a password reset email.

    For security, always returns success even if email doesn't exist.
    This prevents email enumeration attacks.

    Args:
        request_data: Email address for password reset

    Returns:
        Success message (regardless of whether email exists)
    """
    email_hash = hash_pii_for_lookup(request_data.email.lower())

    # Find user by email hash
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    email_sent = False
    if user:
        # Generate password reset token
        reset_token = create_password_reset_token(request_data.email.lower())

        # Send password reset email
        from app.services.email_service import send_password_reset_email
        from app.core.security import decrypt_pii

        user_name = None
        if user.full_name:
            try:
                user_name = decrypt_pii(user.full_name)
            except Exception:
                pass

        email_sent = await send_password_reset_email(
            to_email=request_data.email.lower(),
            reset_token=reset_token,
            user_name=user_name,
        )

        logger.info(
            "password_reset_requested",
            user_id=user.id,
            tenant_id=user.tenant_id,
            email_sent=email_sent,
        )

        # Log audit event
        audit_log = AuditLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action=AuditAction.UPDATE,
            resource_type="password_reset",
            resource_id=str(user.id),
        )
        db.add(audit_log)
        await db.commit()

    # Always return success to prevent email enumeration
    return APIResponse(
        success=True,
        data=PasswordResetResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            email_sent=email_sent,
        ),
    )


@router.post("/reset-password", response_model=APIResponse[PasswordResetResponse])
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reset password using a valid reset token.

    Args:
        request_data: Reset token and new password

    Returns:
        Success or error message
    """
    # Verify the reset token
    email = verify_password_reset_token(request_data.token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # Find user by email hash
    email_hash = hash_pii_for_lookup(email.lower())
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # Update password
    user.password_hash = get_password_hash(request_data.new_password)
    user.is_active = True  # Reactivate if was deactivated

    # Log audit event
    audit_log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action=AuditAction.UPDATE,
        resource_type="password",
        resource_id=str(user.id),
    )
    db.add(audit_log)
    await db.commit()

    logger.info("password_reset_completed", user_id=user.id, tenant_id=user.tenant_id)

    return APIResponse(
        success=True,
        data=PasswordResetResponse(
            message="Password has been reset successfully. You can now log in with your new password.",
            email_sent=False,
        ),
    )
