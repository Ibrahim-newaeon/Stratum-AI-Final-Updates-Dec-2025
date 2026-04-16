# =============================================================================
# Stratum AI - Authentication Endpoints
# =============================================================================
"""
Authentication and authorization endpoints.
Handles login, registration, token refresh, password reset, and WhatsApp verification.
"""

import hmac
import secrets
import re
import string
from datetime import datetime, timezone, timedelta
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.logging import get_logger
from app.core.config import settings
from app.core.security import (
    blacklist_token,
    check_login_rate_limit,
    clear_login_attempts,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_pii,
    get_password_hash,
    hash_pii_for_lookup,
    record_failed_login,
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
EMAIL_OTP_PREFIX = "email_otp:"
SIGNUP_VERIFY_PREFIX = "signup_verify:"
SIGNUP_VERIFY_EXPIRY_SECONDS = 1800  # 30 minutes


# Pydantic schemas for forgot-password / reset-password
class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr = Field(..., description="Email address associated with the account")
    delivery_method: Literal["email", "whatsapp"] = Field(
        default="email",
        description="Delivery method for reset code",
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


# Email OTP schemas
class SendEmailOTPRequest(BaseModel):
    """Request to send email OTP."""
    email: str = Field(..., description="Email address to send OTP to")


class SendEmailOTPResponse(BaseModel):
    """Response after sending email OTP."""
    message: str
    expires_in: int = OTP_EXPIRY_SECONDS


class VerifyEmailOTPRequest(BaseModel):
    """Request to verify email OTP."""
    email: str = Field(..., description="Email that received OTP")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class VerifyEmailOTPResponse(BaseModel):
    """Response after verifying email OTP."""
    verified: bool
    verification_token: Optional[str] = None


# Public registration schema (auto-creates tenant with free tier)
class RegisterRequest(BaseModel):
    """Public registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = None
    company_website: Optional[str] = None
    verification_token: str = Field(..., min_length=1, description="Token from email or WhatsApp verification")

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

    # Normalize phone number: strip spaces, dashes, parentheses, dots
    phone_number = re.sub(r'[\s\-\(\)\.]+', '', request.phone_number.strip())

    # Ensure it starts with +
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    # Validate E.164 phone number format
    if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Use E.164 format (e.g., +1234567890).",
        )

    # Generate OTP
    otp_code = generate_otp()

    # Store OTP in Redis with expiry
    try:
        redis_client = await get_redis_client()
        otp_key = f"{OTP_PREFIX}{phone_number}"
        await redis_client.setex(otp_key, OTP_EXPIRY_SECONDS, otp_code)
        await redis_client.close()
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_store_otp_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send OTP via WhatsApp (in background to not block response)
    async def send_whatsapp_message() -> None:
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
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error("whatsapp_otp_send_failed", error=str(e))

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
    # Normalize phone number: strip spaces, dashes, parentheses, dots
    phone_number = re.sub(r'[\s\-\(\)\.]+', '', request.phone_number.strip())

    # Ensure it starts with +
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format.",
        )

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

        if not hmac.compare_digest(str(stored_otp), str(request.otp_code)):
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
        # Store for register endpoint validation
        await redis_client.setex(
            f"{SIGNUP_VERIFY_PREFIX}{verification_token}",
            SIGNUP_VERIFY_EXPIRY_SECONDS,
            f"phone:{phone_number}",
        )

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
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_verify_otp_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify code",
        )


@router.post("/email/send-otp", response_model=APIResponse[SendEmailOTPResponse])
async def send_email_otp(
    request: SendEmailOTPRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send an email OTP verification code for signup.

    The OTP is valid for 5 minutes and must be verified before registration.
    """
    email = request.email.lower().strip()

    # Basic email format validation
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    # Generate OTP
    otp_code = generate_otp()

    # Store OTP in Redis with expiry
    try:
        redis_client = await get_redis_client()
        otp_key = f"{EMAIL_OTP_PREFIX}{email}"
        await redis_client.setex(otp_key, OTP_EXPIRY_SECONDS, otp_code)
        await redis_client.close()
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_store_email_otp_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send OTP via email in background
    async def send_otp_email_bg() -> None:
        try:
            email_service = get_email_service()
            email_service.send_otp_email(to_email=email, otp_code=otp_code)
            logger.info(f"Email OTP sent to {email[:6]}***")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error("email_otp_send_failed", error=str(e))

    background_tasks.add_task(send_otp_email_bg)

    logger.info(f"Email OTP generated for {email[:6]}***")

    return APIResponse(
        success=True,
        data=SendEmailOTPResponse(
            message="Verification code sent to your email",
            expires_in=OTP_EXPIRY_SECONDS,
        ),
        message="OTP sent successfully",
    )


@router.post("/email/verify-otp", response_model=APIResponse[VerifyEmailOTPResponse])
async def verify_email_otp(request: VerifyEmailOTPRequest):
    """
    Verify the email OTP code.

    Returns a verification token that must be included during registration.
    """
    email = request.email.lower().strip()

    try:
        redis_client = await get_redis_client()
        otp_key = f"{EMAIL_OTP_PREFIX}{email}"
        stored_otp = await redis_client.get(otp_key)

        if not stored_otp:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new code.",
            )

        if not hmac.compare_digest(str(stored_otp), str(request.otp_code)):
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code. Please try again.",
            )

        # OTP is valid - delete it and create verification token
        await redis_client.delete(otp_key)

        # Create a verification token (valid for 30 minutes)
        verification_token = secrets.token_urlsafe(32)
        # Store for register endpoint validation
        await redis_client.setex(
            f"{SIGNUP_VERIFY_PREFIX}{verification_token}",
            SIGNUP_VERIFY_EXPIRY_SECONDS,
            f"email:{email}",
        )

        await redis_client.close()

        logger.info(f"Email OTP verified for {email[:6]}***")

        return APIResponse(
            success=True,
            data=VerifyEmailOTPResponse(
                verified=True,
                verification_token=verification_token,
            ),
            message="Email verified successfully",
        )

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_verify_email_otp_failed", error=str(e))
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

    # Check rate limiting / account lockout
    try:
        is_allowed, lockout_remaining = await check_login_rate_limit(email_hash)
        if not is_allowed:
            logger.warning("login_locked_out", email_hash=email_hash[:16], lockout_remaining=lockout_remaining)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {lockout_remaining} seconds.",
                headers={"Retry-After": str(lockout_remaining)},
            )
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, OSError) as exc:
        # Graceful degradation: allow login when Redis is unavailable.
        # Rate limiting is best-effort; password verification is the real gate.
        logger.warning("redis_unavailable_rate_limit_check", error=str(exc))

    # Find user(s) by email hash
    # Note: email_hash is unique per tenant, so the same email may exist
    # across multiple tenants. We match by password to find the correct user.
    result = await db.execute(
        select(User).where(
            User.email_hash == email_hash,
            User.is_deleted == False,
            User.is_active == True,
        )
    )
    candidates = result.scalars().all()

    user = None
    for candidate in candidates:
        if verify_password(login_data.password, candidate.password_hash):
            user = candidate
            break

    if not user:
        # Record failed attempt
        try:
            await record_failed_login(email_hash)
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("redis_unavailable_record_failed_login", error=str(exc))
        logger.warning("login_failed", email_hash=email_hash[:16])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Clear failed attempts on successful login
    try:
        await clear_login_attempts(email_hash)
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning("redis_unavailable_clear_login_attempts", error=str(exc))

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "cms_role": user.cms_role,
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

    # Fetch available tenants for multi-account switcher
    from app.models import UserTenantMembership, Tenant as TenantModel
    membership_result = await db.execute(
        select(UserTenantMembership, TenantModel)
        .join(TenantModel, UserTenantMembership.tenant_id == TenantModel.id)
        .where(
            UserTenantMembership.user_id == user.id,
            UserTenantMembership.is_active == True,
            TenantModel.is_deleted == False,
        )
        .order_by(UserTenantMembership.is_default.desc(), TenantModel.name)
    )
    membership_rows = membership_result.all()
    available_tenants = [
        {
            "tenant_id": t.id,
            "tenant_name": t.name,
            "tenant_slug": t.slug,
            "tenant_plan": t.plan,
            "role": m.role.value if hasattr(m.role, 'value') else str(m.role),
            "is_default": m.is_default,
            "is_active": m.is_active,
        }
        for m, t in membership_rows
    ]

    return APIResponse(
        success=True,
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60,  # 30 minutes
            "available_tenants": available_tenants,
        },
        message="Login successful",
    )


@router.post("/register", response_model=APIResponse[UserResponse])
async def register(
    request_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Register a new user with verified identity.

    Requires a verification_token from email or WhatsApp OTP verification.
    Auto-creates a tenant with free tier for new signups.
    """
    from app.core.security import encrypt_pii
    from app.models import Tenant, UserTenantMembership
    from app.base_models import UserRole

    # 1. Validate verification token from Redis
    try:
        redis_client = await get_redis_client()
        verify_key = f"{SIGNUP_VERIFY_PREFIX}{request_data.verification_token}"
        verified_data = await redis_client.get(verify_key)

        if not verified_data:
            await redis_client.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification. Please verify your email or phone first.",
            )

        # Consume the token (one-time use)
        await redis_client.delete(verify_key)
        await redis_client.close()
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_validate_signup_token_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate verification. Please try again.",
        )

    # 2. Check if email already exists (globally)
    email_lower = request_data.email.lower()
    email_hash = hash_pii_for_lookup(email_lower)
    result = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    existing = result.scalars().first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 3. Auto-create tenant with free tier
    slug_base = re.sub(r'[^a-z0-9]+', '-', email_lower.split('@')[0]).strip('-')
    slug = f"{slug_base}-{secrets.token_hex(4)}"
    tenant_name = f"{request_data.full_name}'s Workspace" if request_data.full_name else f"{slug_base}'s Workspace"

    tenant = Tenant(
        name=tenant_name,
        slug=slug,
        plan="free",
        status="active",
        billing_email=email_lower,
    )
    db.add(tenant)
    await db.flush()  # Get tenant.id without committing

    # 4. Create user with encrypted PII (verified = True since they passed OTP)
    user = User(
        tenant_id=tenant.id,
        email=encrypt_pii(email_lower),
        email_hash=email_hash,
        password_hash=get_password_hash(request_data.password),
        full_name=encrypt_pii(request_data.full_name) if request_data.full_name else None,
        role=UserRole.ADMIN,
        is_verified=True,
    )
    db.add(user)
    await db.flush()  # Get user.id

    # 5. Create tenant membership (admin, default tenant)
    membership = UserTenantMembership(
        user_id=user.id,
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
        is_default=True,
        is_active=True,
    )
    db.add(membership)

    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)

    # 6. Send welcome email in background
    user_name = request_data.full_name or ""
    async def send_welcome() -> None:
        try:
            email_service = get_email_service()
            email_service.send_welcome_email(to_email=email_lower, user_name=user_name)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning("welcome_email_send_failed", error=str(e))

    background_tasks.add_task(send_welcome)

    logger.info(
        "user_registered",
        user_id=user.id,
        tenant_id=tenant.id,
        plan="free",
    )

    return APIResponse(
        success=True,
        data=UserResponse(
            id=user.id,
            tenant_id=tenant.id,
            email=request_data.email,  # Return original email
            full_name=request_data.full_name,
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
        message="Registration successful. Free tier activated.",
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
            "cms_role": user.cms_role,
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

    Blacklists the current access token in Redis so it cannot be reused.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    # Blacklist the access token so it cannot be reused
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload:
            try:
                await blacklist_token(token, payload)
            except (ConnectionError, TimeoutError, OSError) as exc:
                logger.warning("redis_unavailable_token_blacklist", error=str(exc))
                # Token will expire naturally via JWT exp claim

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
# Multi-Tenant Switcher
# =============================================================================


@router.get("/tenants", response_model=APIResponse[list])
async def list_my_tenants(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    List all tenants the current user has access to.
    Returns tenant info with the user's role in each tenant.
    """
    from app.models import Tenant, UserTenantMembership

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    result = await db.execute(
        select(UserTenantMembership, Tenant)
        .join(Tenant, UserTenantMembership.tenant_id == Tenant.id)
        .where(
            UserTenantMembership.user_id == user_id,
            UserTenantMembership.is_active == True,
            Tenant.is_deleted == False,
        )
        .order_by(UserTenantMembership.is_default.desc(), Tenant.name)
    )
    rows = result.all()

    tenants = []
    for membership, tenant in rows:
        tenants.append({
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "tenant_slug": tenant.slug,
            "tenant_plan": tenant.plan,
            "role": membership.role.value if hasattr(membership.role, 'value') else str(membership.role),
            "is_default": membership.is_default,
            "is_active": membership.is_active,
        })

    return APIResponse(
        success=True,
        data=tenants,
        message=f"Found {len(tenants)} tenant(s)",
    )


@router.post("/switch-tenant", response_model=APIResponse)
async def switch_tenant(
    request: Request,
    switch_data: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Switch active tenant context. Issues new JWT tokens scoped to the target tenant.
    The user must have an active membership in the target tenant.
    """
    from app.models import Tenant, UserTenantMembership

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    target_tenant_id = switch_data.get("tenant_id")
    if not target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )

    # Verify user has active membership in target tenant
    result = await db.execute(
        select(UserTenantMembership, Tenant)
        .join(Tenant, UserTenantMembership.tenant_id == Tenant.id)
        .where(
            UserTenantMembership.user_id == user_id,
            UserTenantMembership.tenant_id == target_tenant_id,
            UserTenantMembership.is_active == True,
            Tenant.is_deleted == False,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this tenant",
        )

    membership, tenant = row

    # Get the user to access cms_role
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Use the role from the membership for the target tenant
    target_role = membership.role.value if hasattr(membership.role, 'value') else str(membership.role)

    # Issue new tokens scoped to the target tenant
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "tenant_id": tenant.id,
            "role": target_role,
            "cms_role": user.cms_role,
        },
    )
    refresh_token = create_refresh_token(subject=user.id)

    # Audit log the switch
    audit_log = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action=AuditAction.LOGIN,
        resource_type="tenant_switch",
        resource_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
        new_value={"switched_from": getattr(request.state, "tenant_id", None)},
    )
    db.add(audit_log)
    await db.commit()

    logger.info(
        "tenant_switched",
        user_id=user.id,
        from_tenant=getattr(request.state, "tenant_id", None),
        to_tenant=tenant.id,
    )

    return APIResponse(
        success=True,
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "role": target_role,
        },
        message=f"Switched to {tenant.name}",
    )


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

    # Store hashed token in Redis to prevent token theft if Redis is exposed
    try:
        import hashlib
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{token_hash}"
        await redis_client.setex(
            token_key,
            PASSWORD_RESET_EXPIRY_SECONDS,
            str(user.id),
        )
        await redis_client.close()
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_store_reset_token_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reset link. Please try again.",
        )

    # Determine user's display name for the email
    user_name = ""
    if user.full_name:
        try:
            user_name = decrypt_pii(user.full_name)
        except (ValueError, TypeError, UnicodeDecodeError):
            user_name = "there"

    # Send reset link (in background to not block response)
    delivery_method = request_data.delivery_method or "email"

    if delivery_method == "whatsapp" and request_data.phone_number:
        # Send via WhatsApp
        async def send_whatsapp_reset() -> None:
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
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error("whatsapp_reset_send_failed", error=str(e))

        background_tasks.add_task(send_whatsapp_reset)
    else:
        # Send via email (default)
        async def send_reset_email() -> None:
            try:
                email_service = get_email_service()
                email_service.send_password_reset_email(
                    to_email=email,
                    token=reset_token,
                    user_name=user_name,
                )
                logger.info("password_reset_email_sent", user_id=user.id)
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error("reset_email_send_failed", error=str(e))

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

    # Look up hashed token in Redis
    try:
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        redis_client = await get_redis_client()
        token_key = f"{PASSWORD_RESET_PREFIX}{token_hash}"
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
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_validate_reset_token_failed", error=str(e))
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
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_validate_verification_token_failed", error=str(e))
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
        except (ValueError, TypeError, UnicodeDecodeError):
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
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.warning("welcome_email_send_failed", error=str(e))

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
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("redis_store_verification_token_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification email. Please try again.",
        )

    # Get display name
    user_name = ""
    if user.full_name:
        try:
            user_name = decrypt_pii(user.full_name)
        except (ValueError, TypeError, UnicodeDecodeError):
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
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error("verification_email_send_failed", error=str(e))

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
