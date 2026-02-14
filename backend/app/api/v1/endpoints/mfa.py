# =============================================================================
# Stratum AI - MFA (Two-Factor Authentication) API Endpoints
# =============================================================================
"""
Two-Factor Authentication endpoints for managing TOTP-based 2FA.

Endpoints:
- GET /mfa/status - Get current MFA status
- POST /mfa/setup - Initiate MFA setup (returns QR code)
- POST /mfa/verify - Verify code and enable MFA
- POST /mfa/disable - Disable MFA (requires valid code)
- POST /mfa/backup-codes - Regenerate backup codes
- POST /mfa/validate - Validate code during login
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.base_models import User
from app.core.logging import get_logger
from app.db.session import get_async_session as get_db
from app.services.mfa_service import MFAService, check_mfa_required, is_user_locked

logger = get_logger(__name__)
router = APIRouter(prefix="/mfa", tags=["MFA"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class MFAStatusResponse(BaseModel):
    """MFA status response."""

    enabled: bool
    verified_at: Optional[str] = None
    backup_codes_remaining: int
    is_locked: bool
    lockout_until: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "verified_at": "2024-01-15T10:30:00Z",
                "backup_codes_remaining": 8,
                "is_locked": False,
                "lockout_until": None,
            }
        }


class MFASetupResponse(BaseModel):
    """MFA setup response with QR code."""

    secret: str = Field(..., description="TOTP secret (for manual entry)")
    provisioning_uri: str = Field(..., description="otpauth:// URI")
    qr_code_base64: str = Field(..., description="QR code as base64 PNG")

    class Config:
        json_schema_extra = {
            "example": {
                "secret": "JBSWY3DPEHPK3PXP",
                "provisioning_uri": "otpauth://totp/Stratum%20AI:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Stratum%20AI",
                "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
            }
        }


class MFAVerifyRequest(BaseModel):
    """Request to verify TOTP code."""

    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code")

    class Config:
        json_schema_extra = {"example": {"code": "123456"}}


class MFAVerifyResponse(BaseModel):
    """Response after enabling MFA."""

    success: bool
    message: str
    backup_codes: list[str] = Field(
        default_factory=list, description="Backup codes (only shown once)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "MFA enabled successfully",
                "backup_codes": ["ABCD-1234", "EFGH-5678", "IJKL-9012"],
            }
        }


class MFADisableRequest(BaseModel):
    """Request to disable MFA."""

    code: str = Field(..., description="TOTP code or backup code")

    class Config:
        json_schema_extra = {"example": {"code": "123456"}}


class MFAValidateRequest(BaseModel):
    """Request to validate code during login."""

    user_id: int = Field(..., description="User ID from login step 1")
    code: str = Field(..., description="TOTP code or backup code")

    class Config:
        json_schema_extra = {"example": {"user_id": 123, "code": "123456"}}


class MFAValidateResponse(BaseModel):
    """Response from code validation."""

    valid: bool
    message: str

    class Config:
        json_schema_extra = {"example": {"valid": True, "message": "Code verified"}}


class BackupCodesResponse(BaseModel):
    """Response with new backup codes."""

    success: bool
    message: str
    backup_codes: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Backup codes regenerated",
                "backup_codes": ["ABCD-1234", "EFGH-5678"],
            }
        }


class MFARequiredResponse(BaseModel):
    """Response indicating MFA is required."""

    mfa_required: bool
    is_locked: bool = False
    lockout_until: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MFAStatusResponse:
    """
    Get current MFA status for the authenticated user.

    Returns whether MFA is enabled, backup codes remaining, and lockout status.
    """
    service = MFAService(db)

    try:
        status = await service.get_mfa_status(current_user.id)

        return MFAStatusResponse(
            enabled=status.enabled,
            verified_at=status.verified_at.isoformat() if status.verified_at else None,
            backup_codes_remaining=status.backup_codes_remaining,
            is_locked=status.is_locked,
            lockout_until=status.lockout_until.isoformat() if status.lockout_until else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/setup", response_model=MFASetupResponse)
async def initiate_mfa_setup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MFASetupResponse:
    """
    Initiate MFA setup for the authenticated user.

    Returns a TOTP secret and QR code for scanning with an authenticator app.
    The user must verify a code using POST /mfa/verify to complete setup.

    **Important:** The secret is only shown once. If the user loses it before
    completing setup, they must restart the setup process.
    """
    service = MFAService(db)

    try:
        # Check if MFA is already enabled
        status = await service.get_mfa_status(current_user.id)
        if status.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled. Disable it first to reconfigure.",
            )

        setup_data = await service.initiate_setup(current_user.id, current_user.email)

        logger.info("mfa_setup_initiated", user_id=current_user.id)

        return MFASetupResponse(
            secret=setup_data.secret,
            provisioning_uri=setup_data.provisioning_uri,
            qr_code_base64=setup_data.qr_code_base64,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_and_enable_mfa(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MFAVerifyResponse:
    """
    Verify TOTP code and enable MFA.

    This completes the MFA setup process. The user must provide a valid code
    from their authenticator app to prove they have successfully configured it.

    **Important:** Backup codes are returned only once. The user should store
    them securely as they can be used to recover account access if they lose
    their authenticator device.
    """
    service = MFAService(db)

    try:
        success, backup_codes = await service.verify_and_enable(current_user.id, request.code)

        if success:
            logger.info("mfa_enabled", user_id=current_user.id)
            return MFAVerifyResponse(
                success=True,
                message="MFA enabled successfully. Store your backup codes securely.",
                backup_codes=backup_codes,
            )
        else:
            return MFAVerifyResponse(
                success=False,
                message="Invalid verification code. Please try again.",
                backup_codes=[],
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/disable", response_model=MFAVerifyResponse)
async def disable_mfa(
    request: MFADisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MFAVerifyResponse:
    """
    Disable MFA for the authenticated user.

    Requires a valid TOTP code or backup code for security.
    After disabling, the user will no longer need to provide a second factor
    during login.
    """
    service = MFAService(db)

    try:
        success = await service.disable(current_user.id, request.code)

        if success:
            logger.info("mfa_disabled", user_id=current_user.id)
            return MFAVerifyResponse(
                success=True,
                message="MFA has been disabled.",
                backup_codes=[],
            )
        else:
            return MFAVerifyResponse(
                success=False,
                message="Invalid code. MFA was not disabled.",
                backup_codes=[],
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/backup-codes", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BackupCodesResponse:
    """
    Regenerate backup codes.

    Requires a valid TOTP code (not a backup code) for security.
    This invalidates all existing backup codes and generates new ones.

    **Important:** New backup codes are shown only once. Store them securely.
    """
    service = MFAService(db)

    try:
        success, backup_codes = await service.regenerate_backup_codes(current_user.id, request.code)

        if success:
            logger.info("mfa_backup_codes_regenerated", user_id=current_user.id)
            return BackupCodesResponse(
                success=True,
                message="Backup codes regenerated. Store them securely.",
                backup_codes=backup_codes,
            )
        else:
            return BackupCodesResponse(
                success=False,
                message="Invalid TOTP code. Backup codes not regenerated.",
                backup_codes=[],
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/validate", response_model=MFAValidateResponse)
async def validate_mfa_code(
    request: MFAValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> MFAValidateResponse:
    """
    Validate MFA code during login flow.

    This endpoint is called after successful password authentication when
    MFA is enabled for the user. It verifies the TOTP or backup code.

    **Note:** This endpoint does not require authentication as it's part
    of the login flow. The user_id comes from the first authentication step.

    Rate limiting: After 5 failed attempts, the account is locked for 15 minutes.
    """
    service = MFAService(db)

    # Check if user is locked
    is_locked, lockout_until = await is_user_locked(db, request.user_id)
    if is_locked:
        import time as _time

        remaining = (lockout_until.timestamp() - _time.time()) // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked due to too many failed attempts. Try again in {int(remaining)} minutes.",
        )

    # Verify the code
    valid, message = await service.verify_code(request.user_id, request.code)

    if valid:
        logger.info("mfa_validation_success", user_id=request.user_id)
    else:
        logger.warning("mfa_validation_failed", user_id=request.user_id, message=message)

    return MFAValidateResponse(
        valid=valid,
        message=message,
    )


@router.get("/check/{user_id}", response_model=MFARequiredResponse)
async def check_mfa_required_for_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> MFARequiredResponse:
    """
    Check if MFA is required for a user during login.

    This is called after successful password authentication to determine
    if a second factor is needed.

    **Note:** This endpoint does not require authentication as it's part
    of the login flow.
    """
    mfa_required = await check_mfa_required(db, user_id)

    if mfa_required:
        is_locked, lockout_until = await is_user_locked(db, user_id)
        return MFARequiredResponse(
            mfa_required=True,
            is_locked=is_locked,
            lockout_until=lockout_until.isoformat() if lockout_until else None,
        )

    return MFARequiredResponse(
        mfa_required=False,
        is_locked=False,
        lockout_until=None,
    )
