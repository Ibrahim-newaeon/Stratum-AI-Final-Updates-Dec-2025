# =============================================================================
# Stratum AI - Authentication Endpoints
# =============================================================================
"""
Authentication and authorization endpoints.
Handles login, registration, token refresh, password reset, and WhatsApp verification.
"""

import random
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.logging import get_logger
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_pii,
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
from app.services.email_service import get_email_service
from app.services.whatsapp_client import (
    get_whatsapp_client,
    is_whatsapp_configured,
    WhatsAppAPIError,
    WhatsAppNotConfiguredError,
)

logger = get_logger(__name__)
router = APIRouter()

# Redis connection for OTP storage
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_PREFIX = "whatsapp_otp:"
PASSWORD_RESET_PREFIX = "password_reset:"
PASSWORD_RESET_EXPIRY_SECONDS = 3600  # 1 hour
EMAIL_VERIFICATION_PREFIX = "email_verify:"
EMAIL_VERIFICATION_EXPIRY_SECONDS = 86400  # 24 hours


# Pydantic schemas for forgot-password / reset-password
class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""
    email: str = Field(..., description="Email address associated with the account")
    delivery_method: Optional[str] = Field(
        default="email",
        description="Delivery method: 'email' or 'whatsapp'",
    )
    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number for WhatsApp delivery (required if delivery_method is 'whatsapp')",
    )


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset."""
    success: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token."""
    token: str = Field(..., min_length=1, description="Password reset token")
    password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class ResetPasswordResponse(BaseModel):
    """Response after resetting password."""
    success: bool
    message: str


class VerifyEmailRequest(BaseModel):
    """Request to verify email with token."""
    token: str = Field(..., min_length=1, description="Email verification token")


class VerifyEmailResponse(BaseModel):
    """Response after verifying email."""
    success: bool
    message: str


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: str = Field(..., description="Email address to resend verification to")


class ResendVerificationResponse(BaseModel):
    """Response after resending verification."""
    success: bool
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
    """Generate a cryptographically secure random numeric OTP code."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


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
    # Fail fast if WhatsApp is not configured
    if not is_whatsapp_configured():
        logger.error("WhatsApp OTP requested but WhatsApp credentials are not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp messaging is not configured. Please contact your administrator.",
        )

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
            # Send authentication template with OTP code
            # Uses the Meta-approved "stratum_verify_code" authentication template
            # which auto-generates: "<code> is your verification code."
            await whatsapp_client.send_template_message(
                recipient_phone=phone_number.replace('+', ''),  # Remove + for API
                template_name="stratum_verify_code",  # Approved auth template
                language_code="en",
                components=[
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": otp_code}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {"type": "text", "text": otp_code}
                        ]
                    }
                ]
            )
            logger.info(f"WhatsApp OTP sent to {phone_number[:6]}***")
        except WhatsAppNotConfiguredError:
            logger.error(
                "WhatsApp credentials not configured. OTP was stored in Redis "
                "but could not be delivered. Set WHATSAPP_PHONE_NUMBER_ID and "
                "WHATSAPP_ACCESS_TOKEN in your environment."
            )
        except WhatsAppAPIError as e:
            logger.error(
                f"WhatsApp API error sending OTP to {phone_number[:6]}***: "
                f"{e.message} (code={e.error_code}, subcode={e.error_subcode})"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp OTP: {e}", exc_info=True)

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
        verification_token = secrets.token_urlsafe(32)
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
            # NOTE: email intentionally excluded from JWT to prevent PII leakage
            # JWTs are base64-encoded (not encrypted) and visible in request headers
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
# Forgot Password
# =============================================================================


@router.post("/forgot-password", response_model=APIResponse[ForgotPasswordResponse])
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Request a password reset link.

    Generates a secure token, stores it in Redis, and sends a reset link
    via email (or WhatsApp if requested). Always returns success to prevent
    email enumeration attacks.
    """
    email = request_data.email.lower().strip()
    email_hash = hash_pii_for_lookup(email)

    # Look up user by email hash
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    # Always return success even if user not found (prevent email enumeration)
    if not user:
        logger.info("password_reset_requested_unknown_email", email_hash=email_hash[:16])
        return APIResponse(
            success=True,
            data=ForgotPasswordResponse(
                success=True,
                message="If an account with that email exists, a password reset link has been sent.",
            ),
            message="Password reset requested",
        )

    # Generate secure reset token
    reset_token = secrets.token_urlsafe(48)

    # Store token in Redis with user ID mapping
    try:
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{reset_token}"
        await redis_client.setex(
            token_key,
            PASSWORD_RESET_EXPIRY_SECONDS,
            str(user.id),
        )
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis error storing reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reset link. Please try again.",
        )

    # Determine user's display name for the email
    user_name = ""
    if user.full_name:
        try:
            user_name = decrypt_pii(user.full_name)
        except Exception:
            user_name = "there"

    # Send reset link (in background to not block response)
    delivery_method = request_data.delivery_method or "email"

    if delivery_method == "whatsapp" and request_data.phone_number:
        # Send via WhatsApp
        async def send_whatsapp_reset():
            try:
                if not is_whatsapp_configured():
                    logger.warning("WhatsApp not configured for password reset delivery")
                    return
                whatsapp_client = get_whatsapp_client()
                reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
                await whatsapp_client.send_text_message(
                    recipient_phone=request_data.phone_number.replace('+', ''),
                    message=f"Your Stratum AI password reset link:\n{reset_url}\n\nThis link expires in 1 hour.",
                )
                logger.info("password_reset_whatsapp_sent", user_id=user.id)
            except Exception as e:
                logger.error(f"Failed to send WhatsApp reset: {e}")

        background_tasks.add_task(send_whatsapp_reset)
    else:
        # Send via email (default)
        async def send_reset_email():
            try:
                email_service = get_email_service()
                email_service.send_password_reset_email(
                    to_email=email,
                    token=reset_token,
                    user_name=user_name,
                )
                logger.info("password_reset_email_sent", user_id=user.id)
            except Exception as e:
                logger.error(f"Failed to send reset email: {e}")

        background_tasks.add_task(send_reset_email)

    logger.info("password_reset_requested", user_id=user.id, method=delivery_method)

    return APIResponse(
        success=True,
        data=ForgotPasswordResponse(
            success=True,
            message="If an account with that email exists, a password reset link has been sent.",
        ),
        message="Password reset requested",
    )


# =============================================================================
# Reset Password
# =============================================================================


@router.post("/reset-password", response_model=APIResponse[ResetPasswordResponse])
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reset password using a valid reset token.

    Validates the token from Redis, updates the user's password hash,
    and invalidates the token.
    """
    token = request_data.token.strip()

    # Look up token in Redis
    try:
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{token}"
        user_id_str = await redis_client.get(token_key)

        if not user_id_str:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token. Please request a new password reset.",
            )

        # Invalidate the token immediately (one-time use)
        await redis_client.delete(token_key)
        await redis_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis error validating reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate reset token. Please try again.",
        )

    # Find the user
    user_id = int(user_id_str)
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
            detail="User account not found.",
        )

    # Update password hash
    user.password_hash = get_password_hash(request_data.password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("password_reset_completed", user_id=user.id)

    return APIResponse(
        success=True,
        data=ResetPasswordResponse(
            success=True,
            message="Password has been reset successfully. You can now log in with your new password.",
        ),
        message="Password reset successful",
    )


# =============================================================================
# Verify Email
# =============================================================================


@router.post("/verify-email", response_model=APIResponse[VerifyEmailResponse])
async def verify_email(
    request_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Verify a user's email address using the verification token.

    Validates the token from Redis and marks the user as verified.
    """
    token = request_data.token.strip()

    # Look up token in Redis
    try:
        redis_client = await get_redis_client()
        token_key = f"{EMAIL_VERIFICATION_PREFIX}{token}"
        user_id_str = await redis_client.get(token_key)

        if not user_id_str:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token. Please request a new verification email.",
            )

        # Invalidate the token
        await redis_client.delete(token_key)
        await redis_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis error validating verification token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email. Please try again.",
        )

    # Find and update user
    user_id = int(user_id_str)
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
            detail="User account not found.",
        )

    if user.is_verified:
        return APIResponse(
            success=True,
            data=VerifyEmailResponse(
                success=True,
                message="Email is already verified.",
            ),
            message="Already verified",
        )

    user.is_verified = True
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Send welcome email in background
    user_name = ""
    if user.full_name:
        try:
            user_name = decrypt_pii(user.full_name)
        except Exception:
            user_name = "there"

    try:
        # Decrypt the original email for sending the welcome message
        original_email = decrypt_pii(user.email) if user.email else None
        if original_email:
            email_service = get_email_service()
            email_service.send_welcome_email(
                to_email=original_email,
                user_name=user_name,
            )
    except Exception as e:
        logger.warning(f"Failed to send welcome email: {e}")

    logger.info("email_verified", user_id=user.id)

    return APIResponse(
        success=True,
        data=VerifyEmailResponse(
            success=True,
            message="Email verified successfully. Welcome to Stratum AI!",
        ),
        message="Email verified",
    )


# =============================================================================
# Resend Verification Email
# =============================================================================


@router.post("/resend-verification", response_model=APIResponse[ResendVerificationResponse])
async def resend_verification(
    request_data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Resend verification email to the user.

    Generates a new verification token and sends a verification email.
    Always returns success to prevent email enumeration.
    """
    email = request_data.email.lower().strip()
    email_hash = hash_pii_for_lookup(email)

    # Look up user
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    # Always return success (prevent enumeration)
    if not user:
        logger.info("resend_verification_unknown_email", email_hash=email_hash[:16])
        return APIResponse(
            success=True,
            data=ResendVerificationResponse(
                success=True,
                message="If an account with that email exists, a verification email has been sent.",
            ),
            message="Verification email requested",
        )

    if user.is_verified:
        return APIResponse(
            success=True,
            data=ResendVerificationResponse(
                success=True,
                message="Email is already verified. You can log in.",
            ),
            message="Already verified",
        )

    # Generate verification token
    verification_token = secrets.token_urlsafe(48)

    # Store in Redis
    try:
        redis_client = await get_redis_client()
        token_key = f"{EMAIL_VERIFICATION_PREFIX}{verification_token}"
        await redis_client.setex(
            token_key,
            EMAIL_VERIFICATION_EXPIRY_SECONDS,
            str(user.id),
        )
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis error storing verification token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification email. Please try again.",
        )

    # Get display name
    user_name = ""
    if user.full_name:
        try:
            user_name = decrypt_pii(user.full_name)
        except Exception:
            user_name = "there"

    # Send email in background
    async def send_verification():
        try:
            email_service = get_email_service()
            email_service.send_verification_email(
                to_email=email,
                token=verification_token,
                user_name=user_name,
            )
            logger.info("verification_email_resent", user_id=user.id)
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")

    background_tasks.add_task(send_verification)

    logger.info("resend_verification_requested", user_id=user.id)

    return APIResponse(
        success=True,
        data=ResendVerificationResponse(
            success=True,
            message="If an account with that email exists, a verification email has been sent.",
        ),
        message="Verification email sent",
    )
