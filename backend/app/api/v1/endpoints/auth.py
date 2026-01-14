# =============================================================================
# Stratum AI - Authentication Endpoints
# =============================================================================
"""
Authentication and authorization endpoints.
Handles login, registration, token refresh, password reset, and WhatsApp verification.
"""

import random
import string
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.logging import get_logger
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_pii,
    decrypt_pii,
    get_password_hash,
    hash_pii_for_lookup,
    verify_password,
)
from app.db.session import get_async_session
from app.models import AuditAction, AuditLog, User, UserRole, Tenant
from app.schemas import (
    APIResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.whatsapp_client import get_whatsapp_client, WhatsAppAPIError
from app.services.email_service import get_email_service
from app.auth.deps import (
    generate_verification_token,
    generate_password_reset_token,
    CurrentUserDep,
)

logger = get_logger(__name__)
router = APIRouter()

# Redis connection for OTP and token storage
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_PREFIX = "whatsapp_otp:"
EMAIL_VERIFY_PREFIX = "email_verify:"
PASSWORD_RESET_PREFIX = "password_reset:"


# =============================================================================
# Additional Schemas for Auth Endpoints
# =============================================================================
class SignupRequest(BaseModel):
    """Self-service signup request (creates new tenant)."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    company_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class SignupResponse(BaseModel):
    """Signup response."""

    user_id: int
    email: str
    message: str
    verification_required: bool = True


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str = Field(..., min_length=32, max_length=64)


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    token: str = Field(..., min_length=32, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request (when logged in)."""

    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Pydantic schemas for WhatsApp OTP
class SendOTPRequest(BaseModel):
    """Request to send WhatsApp OTP."""
    phone_number: str = Field(..., description="Phone number with country code (e.g., +1234567890)")


class SendOTPResponse(BaseModel):
    """Response after sending OTP."""
    message: str
    expires_in: int = OTP_EXPIRY_SECONDS


class VerifyOTPRequest(BaseModel):
    """Request to verify WhatsApp OTP."""
    phone_number: str = Field(..., description="Phone number that received OTP")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class VerifyOTPResponse(BaseModel):
    """Response after verifying OTP."""
    verified: bool
    verification_token: Optional[str] = None  # Token to use during registration


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


async def get_redis_client() -> redis.Redis:
    """Get Redis client for OTP storage."""
    return redis.from_url(settings.redis_url, decode_responses=True)


@router.post("/whatsapp/send-otp", response_model=APIResponse[SendOTPResponse])
async def send_whatsapp_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a WhatsApp OTP verification code to the specified phone number.

    The OTP is valid for 5 minutes and must be verified before registration.
    """
    phone_number = request.phone_number.strip()

    # Normalize phone number (ensure it starts with +)
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    # Generate OTP
    otp_code = generate_otp()

    # Store OTP in Redis with expiry
    try:
        redis_client = await get_redis_client()
        otp_key = f"{OTP_PREFIX}{phone_number}"
        await redis_client.setex(otp_key, OTP_EXPIRY_SECONDS, otp_code)
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis error storing OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send OTP via WhatsApp (in background to not block response)
    async def send_whatsapp_message():
        try:
            whatsapp_client = get_whatsapp_client()
            # Send template message with OTP
            # Note: You need to create an approved WhatsApp template for OTP
            await whatsapp_client.send_template_message(
                recipient_phone=phone_number.replace('+', ''),  # Remove + for API
                template_name="verification_code",  # Must be pre-approved template
                language_code="en",
                components=[
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": otp_code}
                        ]
                    }
                ]
            )
            logger.info(f"WhatsApp OTP sent to {phone_number[:6]}***")
        except WhatsAppAPIError as e:
            logger.error(f"WhatsApp API error sending OTP: {e.message}")
        except Exception as e:
            logger.error(f"Error sending WhatsApp OTP: {e}")

    background_tasks.add_task(send_whatsapp_message)

    logger.info(f"OTP generated for phone {phone_number[:6]}***")

    return APIResponse(
        success=True,
        data=SendOTPResponse(
            message="Verification code sent to your WhatsApp",
            expires_in=OTP_EXPIRY_SECONDS,
        ),
        message="OTP sent successfully",
    )


@router.post("/whatsapp/verify-otp", response_model=APIResponse[VerifyOTPResponse])
async def verify_whatsapp_otp(request: VerifyOTPRequest):
    """
    Verify the WhatsApp OTP code.

    Returns a verification token that must be included during registration.
    """
    phone_number = request.phone_number.strip()

    # Normalize phone number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    try:
        redis_client = await get_redis_client()
        otp_key = f"{OTP_PREFIX}{phone_number}"
        stored_otp = await redis_client.get(otp_key)

        if not stored_otp:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new code.",
            )

        if stored_otp != request.otp_code:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code. Please try again.",
            )

        # OTP is valid - delete it and create verification token
        await redis_client.delete(otp_key)

        # Create a verification token (valid for 30 minutes)
        verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        verification_key = f"phone_verified:{phone_number}"
        await redis_client.setex(verification_key, 1800, verification_token)  # 30 min expiry

        await redis_client.close()

        logger.info(f"OTP verified for phone {phone_number[:6]}***")

        return APIResponse(
            success=True,
            data=VerifyOTPResponse(
                verified=True,
                verification_token=verification_token,
            ),
            message="Phone number verified successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify code",
        )


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


# =============================================================================
# Self-Service Signup (Creates Tenant + User)
# =============================================================================
@router.post("/signup", response_model=APIResponse[SignupResponse])
async def signup(
    signup_data: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Self-service signup that creates a new tenant and admin user.

    - Creates a new tenant (organization) with the company name
    - Creates the first user as tenant admin
    - Sends email verification link
    - User must verify email before full access

    Args:
        signup_data: Email, password, name, company details

    Returns:
        User ID and verification message
    """
    email_lower = signup_data.email.lower()
    email_hash = hash_pii_for_lookup(email_lower)

    # Check if email already exists (across all tenants for now)
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create tenant slug from company name
    slug = signup_data.company_name.lower()
    slug = "".join(c if c.isalnum() else "-" for c in slug)
    slug = "-".join(filter(None, slug.split("-")))  # Remove empty parts

    # Ensure slug uniqueness
    base_slug = slug[:80]  # Leave room for suffix
    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create tenant
    tenant = Tenant(
        name=signup_data.company_name,
        slug=slug,
        plan="free",
        settings={},
        feature_flags={},
    )
    db.add(tenant)
    await db.flush()  # Get tenant ID

    # Create user as tenant admin
    user = User(
        tenant_id=tenant.id,
        email=encrypt_pii(email_lower),
        email_hash=email_hash,
        password_hash=get_password_hash(signup_data.password),
        full_name=encrypt_pii(signup_data.full_name),
        phone=encrypt_pii(signup_data.phone) if signup_data.phone else None,
        role=UserRole.ADMIN,  # First user is admin
        is_active=True,
        is_verified=False,  # Requires email verification
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate verification token and store in Redis
    verification_token = generate_verification_token()
    try:
        redis_client = await get_redis_client()
        token_key = f"{EMAIL_VERIFY_PREFIX}{verification_token}"
        token_data = f"{user.id}:{email_lower}"
        expiry_seconds = settings.email_verification_expire_hours * 3600
        await redis_client.setex(token_key, expiry_seconds, token_data)
        await redis_client.close()
    except Exception as e:
        logger.error("Redis error storing verification token", error=str(e))
        # Continue anyway - user can request resend

    # Send verification email in background
    async def send_verification():
        try:
            email_service = get_email_service()
            email_service.send_verification_email(
                to_email=email_lower,
                token=verification_token,
                user_name=signup_data.full_name,
            )
        except Exception as e:
            logger.error("Error sending verification email", error=str(e))

    background_tasks.add_task(send_verification)

    logger.info(
        "user_signed_up",
        user_id=user.id,
        tenant_id=tenant.id,
    )

    return APIResponse(
        success=True,
        data=SignupResponse(
            user_id=user.id,
            email=email_lower,
            message="Account created. Please check your email to verify your account.",
            verification_required=True,
        ),
        message="Signup successful",
    )


# =============================================================================
# Email Verification Endpoints
# =============================================================================
@router.post("/verify-email", response_model=APIResponse[MessageResponse])
async def verify_email(
    verify_data: VerifyEmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Verify user email address using the token from verification email.

    Args:
        verify_data: Verification token

    Returns:
        Success message
    """
    try:
        redis_client = await get_redis_client()
        token_key = f"{EMAIL_VERIFY_PREFIX}{verify_data.token}"
        token_data = await redis_client.get(token_key)

        if not token_data:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Parse user ID and email from token data
        user_id_str, email = token_data.split(":", 1)
        user_id = int(user_id_str)

        # Delete token (single use)
        await redis_client.delete(token_key)
        await redis_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error verifying email token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed",
        )

    # Get user and verify
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_verified:
        return APIResponse(
            success=True,
            data=MessageResponse(message="Email already verified"),
            message="Email already verified",
        )

    # Mark user as verified
    user.is_verified = True
    await db.commit()

    # Send welcome email in background
    async def send_welcome():
        try:
            email_service = get_email_service()
            full_name = decrypt_pii(user.full_name) if user.full_name else None
            email_service.send_welcome_email(
                to_email=email,
                user_name=full_name,
            )
        except Exception as e:
            logger.error("Error sending welcome email", error=str(e))

    background_tasks.add_task(send_welcome)

    logger.info("email_verified", user_id=user.id)

    return APIResponse(
        success=True,
        data=MessageResponse(message="Email verified successfully"),
        message="Email verified",
    )


@router.post("/resend-verification", response_model=APIResponse[MessageResponse])
async def resend_verification(
    resend_data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Resend email verification link.

    Args:
        resend_data: Email address

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    email_lower = resend_data.email.lower()
    email_hash = hash_pii_for_lookup(email_lower)

    # Find user
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    success_response = APIResponse(
        success=True,
        data=MessageResponse(message="If the email exists, a verification link has been sent"),
        message="Verification email sent",
    )

    if not user:
        return success_response

    if user.is_verified:
        return success_response

    # Generate new verification token
    verification_token = generate_verification_token()
    try:
        redis_client = await get_redis_client()
        token_key = f"{EMAIL_VERIFY_PREFIX}{verification_token}"
        token_data = f"{user.id}:{email_lower}"
        expiry_seconds = settings.email_verification_expire_hours * 3600
        await redis_client.setex(token_key, expiry_seconds, token_data)
        await redis_client.close()
    except Exception as e:
        logger.error("Redis error storing verification token", error=str(e))
        return success_response

    # Send verification email
    async def send_verification():
        try:
            email_service = get_email_service()
            full_name = decrypt_pii(user.full_name) if user.full_name else None
            email_service.send_verification_email(
                to_email=email_lower,
                token=verification_token,
                user_name=full_name,
            )
        except Exception as e:
            logger.error("Error sending verification email", error=str(e))

    background_tasks.add_task(send_verification)

    logger.info("verification_email_resent", user_id=user.id)

    return success_response


# =============================================================================
# Password Reset Endpoints
# =============================================================================
@router.post("/forgot-password", response_model=APIResponse[MessageResponse])
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Request password reset email.

    Args:
        forgot_data: Email address

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    email_lower = forgot_data.email.lower()
    email_hash = hash_pii_for_lookup(email_lower)

    # Always return success to prevent email enumeration
    success_response = APIResponse(
        success=True,
        data=MessageResponse(message="If the email exists, a password reset link has been sent"),
        message="Password reset email sent",
    )

    # Find user
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return success_response

    # Generate password reset token
    reset_token = generate_password_reset_token()
    try:
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{reset_token}"
        token_data = f"{user.id}:{email_lower}"
        expiry_seconds = settings.password_reset_expire_hours * 3600
        await redis_client.setex(token_key, expiry_seconds, token_data)
        await redis_client.close()
    except Exception as e:
        logger.error("Redis error storing reset token", error=str(e))
        return success_response

    # Send reset email
    async def send_reset_email():
        try:
            email_service = get_email_service()
            full_name = decrypt_pii(user.full_name) if user.full_name else None
            email_service.send_password_reset_email(
                to_email=email_lower,
                token=reset_token,
                user_name=full_name,
            )
        except Exception as e:
            logger.error("Error sending reset email", error=str(e))

    background_tasks.add_task(send_reset_email)

    logger.info("password_reset_requested", user_id=user.id)

    return success_response


@router.post("/reset-password", response_model=APIResponse[MessageResponse])
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reset password using token from reset email.

    Args:
        reset_data: Reset token and new password

    Returns:
        Success message
    """
    try:
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{reset_data.token}"
        token_data = await redis_client.get(token_key)

        if not token_data:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Parse user ID from token data
        user_id_str, _ = token_data.split(":", 1)
        user_id = int(user_id_str)

        # Delete token (single use)
        await redis_client.delete(token_key)
        await redis_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error verifying reset token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )

    # Get user and update password
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    await db.commit()

    logger.info("password_reset_completed", user_id=user.id)

    return APIResponse(
        success=True,
        data=MessageResponse(message="Password reset successfully"),
        message="Password reset successful",
    )


@router.post("/change-password", response_model=APIResponse[MessageResponse])
async def change_password(
    change_data: ChangePasswordRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Change password for authenticated user.

    Requires current password for verification.

    Args:
        change_data: Current and new password
        current_user: Authenticated user

    Returns:
        Success message
    """
    # Verify current password
    if not verify_password(change_data.current_password, current_user.user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.user.password_hash = get_password_hash(change_data.new_password)
    await db.commit()

    logger.info("password_changed", user_id=current_user.id)

    return APIResponse(
        success=True,
        data=MessageResponse(message="Password changed successfully"),
        message="Password changed",
    )


# =============================================================================
# Current User Endpoint
# =============================================================================
@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: CurrentUserDep):
    """
    Get current authenticated user profile.

    Args:
        current_user: Authenticated user from JWT

    Returns:
        User profile information
    """
    return APIResponse(
        success=True,
        data=UserResponse(
            id=current_user.id,
            tenant_id=current_user.tenant_id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            locale=current_user.user.locale,
            timezone=current_user.user.timezone,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            last_login_at=current_user.user.last_login_at,
            avatar_url=current_user.user.avatar_url,
            created_at=current_user.user.created_at,
            updated_at=current_user.user.updated_at,
        ),
        message="User profile retrieved",
    )
