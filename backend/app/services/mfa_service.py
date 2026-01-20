# =============================================================================
# Stratum AI - Multi-Factor Authentication (MFA/2FA) Service
# =============================================================================
"""
Two-Factor Authentication using TOTP (Time-based One-Time Password).

Features:
- TOTP secret generation and QR code creation
- TOTP verification with rate limiting
- Backup codes generation and validation
- Account lockout protection
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional, List, Tuple

import pyotp
import qrcode
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import encrypt_pii, decrypt_pii

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# TOTP Configuration
TOTP_ISSUER = "Stratum AI"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # seconds
TOTP_VALID_WINDOW = 1  # Allow 1 step before/after for clock drift

# Rate Limiting
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Backup Codes
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TOTPSetupData:
    """Data for setting up TOTP."""
    secret: str
    provisioning_uri: str
    qr_code_base64: str


@dataclass
class MFAStatus:
    """Current MFA status for a user."""
    enabled: bool
    verified_at: Optional[datetime]
    backup_codes_remaining: int
    is_locked: bool
    lockout_until: Optional[datetime]


# =============================================================================
# TOTP Functions
# =============================================================================

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """
    Generate TOTP provisioning URI for authenticator apps.

    Args:
        secret: TOTP secret key
        email: User's email for identification

    Returns:
        otpauth:// URI for authenticator apps
    """
    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL,
    )
    return totp.provisioning_uri(
        name=email,
        issuer_name=TOTP_ISSUER,
    )


def generate_qr_code(uri: str) -> str:
    """
    Generate QR code image as base64 string.

    Args:
        uri: TOTP provisioning URI

    Returns:
        Base64-encoded PNG image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a TOTP code.

    Args:
        secret: TOTP secret key
        code: 6-digit code from authenticator

    Returns:
        True if code is valid
    """
    if not secret or not code:
        return False

    # Remove spaces and ensure it's digits only
    code = code.replace(" ", "").strip()
    if not code.isdigit() or len(code) != TOTP_DIGITS:
        return False

    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL,
    )

    return totp.verify(code, valid_window=TOTP_VALID_WINDOW)


# =============================================================================
# Backup Codes Functions
# =============================================================================

def generate_backup_codes() -> List[str]:
    """
    Generate a set of backup codes.

    Returns:
        List of backup codes (plaintext)
    """
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        # Generate random alphanumeric code
        code = secrets.token_hex(BACKUP_CODE_LENGTH // 2).upper()
        # Format as XXXX-XXXX
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage."""
    # Normalize: remove dashes, uppercase
    normalized = code.replace("-", "").upper()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify_backup_code(code: str, hashed_codes: List[str]) -> Tuple[bool, Optional[int]]:
    """
    Verify a backup code against stored hashes.

    Args:
        code: Backup code to verify
        hashed_codes: List of hashed backup codes

    Returns:
        Tuple of (is_valid, index_of_code)
    """
    if not code or not hashed_codes:
        return False, None

    code_hash = hash_backup_code(code)

    for i, stored_hash in enumerate(hashed_codes):
        if stored_hash and secrets.compare_digest(code_hash, stored_hash):
            return True, i

    return False, None


# =============================================================================
# MFA Service Class
# =============================================================================

class MFAService:
    """Service for managing user MFA."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_mfa_status(self, user_id: int) -> MFAStatus:
        """Get current MFA status for a user."""
        from app.base_models import User

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Count remaining backup codes
        backup_codes_remaining = 0
        if user.backup_codes and "codes" in user.backup_codes:
            backup_codes_remaining = sum(
                1 for code in user.backup_codes["codes"] if code is not None
            )

        # Check lockout
        is_locked = False
        lockout_until = user.totp_lockout_until
        if lockout_until:
            if datetime.now(timezone.utc) < lockout_until:
                is_locked = True
            else:
                # Lockout expired, clear it
                lockout_until = None

        return MFAStatus(
            enabled=user.totp_enabled,
            verified_at=user.totp_verified_at,
            backup_codes_remaining=backup_codes_remaining,
            is_locked=is_locked,
            lockout_until=lockout_until,
        )

    async def initiate_setup(self, user_id: int, email: str) -> TOTPSetupData:
        """
        Start MFA setup process.

        Generates a new TOTP secret and returns setup data including QR code.
        The secret is stored but MFA is not enabled until verified.

        Args:
            user_id: User ID
            email: User's email for authenticator app

        Returns:
            TOTPSetupData with secret, URI, and QR code
        """
        from app.base_models import User

        # Generate new secret
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, email)
        qr_base64 = generate_qr_code(uri)

        # Encrypt and store secret (but don't enable yet)
        encrypted_secret = encrypt_pii(secret)

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                totp_secret=encrypted_secret,
                totp_enabled=False,  # Not enabled until verified
            )
        )
        await self.db.commit()

        logger.info("mfa_setup_initiated", user_id=user_id)

        return TOTPSetupData(
            secret=secret,
            provisioning_uri=uri,
            qr_code_base64=qr_base64,
        )

    async def verify_and_enable(
        self,
        user_id: int,
        code: str,
    ) -> Tuple[bool, List[str]]:
        """
        Verify TOTP code and enable MFA.

        Args:
            user_id: User ID
            code: TOTP code from authenticator

        Returns:
            Tuple of (success, backup_codes)
            backup_codes is empty list if verification failed
        """
        from app.base_models import User

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.totp_secret:
            raise ValueError("MFA setup not initiated")

        if user.totp_enabled:
            raise ValueError("MFA is already enabled")

        # Decrypt and verify
        secret = decrypt_pii(user.totp_secret)

        if not verify_totp(secret, code):
            logger.warning("mfa_verification_failed", user_id=user_id)
            return False, []

        # Generate backup codes
        backup_codes = generate_backup_codes()
        hashed_codes = [hash_backup_code(c) for c in backup_codes]

        # Enable MFA
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                totp_enabled=True,
                totp_verified_at=now,
                backup_codes={"codes": hashed_codes},
                failed_totp_attempts=0,
                totp_lockout_until=None,
            )
        )
        await self.db.commit()

        logger.info("mfa_enabled", user_id=user_id)

        return True, backup_codes

    async def disable(self, user_id: int, code: str) -> bool:
        """
        Disable MFA for a user.

        Requires valid TOTP code or backup code for security.

        Args:
            user_id: User ID
            code: TOTP code or backup code

        Returns:
            True if disabled successfully
        """
        from app.base_models import User

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.totp_enabled:
            raise ValueError("MFA is not enabled")

        # Verify code (TOTP or backup)
        is_valid = await self._verify_code(user, code)

        if not is_valid:
            logger.warning("mfa_disable_failed_invalid_code", user_id=user_id)
            return False

        # Disable MFA
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                totp_secret=None,
                totp_enabled=False,
                totp_verified_at=None,
                backup_codes=None,
                failed_totp_attempts=0,
                totp_lockout_until=None,
            )
        )
        await self.db.commit()

        logger.info("mfa_disabled", user_id=user_id)

        return True

    async def verify_code(self, user_id: int, code: str) -> Tuple[bool, str]:
        """
        Verify a TOTP or backup code during login.

        Args:
            user_id: User ID
            code: TOTP code or backup code

        Returns:
            Tuple of (is_valid, message)
        """
        from app.base_models import User

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        if not user.totp_enabled:
            return True, "MFA not enabled"

        # Check lockout
        if user.totp_lockout_until:
            if datetime.now(timezone.utc) < user.totp_lockout_until:
                remaining = (user.totp_lockout_until - datetime.now(timezone.utc)).seconds // 60
                return False, f"Account locked. Try again in {remaining} minutes."

        # Verify code
        is_valid = await self._verify_code(user, code)

        if is_valid:
            # Reset failed attempts
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    failed_totp_attempts=0,
                    totp_lockout_until=None,
                )
            )
            await self.db.commit()
            return True, "Code verified"
        else:
            # Increment failed attempts
            new_attempts = user.failed_totp_attempts + 1
            lockout_until = None

            if new_attempts >= MAX_FAILED_ATTEMPTS:
                lockout_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                logger.warning("mfa_account_locked", user_id=user_id)

            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    failed_totp_attempts=new_attempts,
                    totp_lockout_until=lockout_until,
                )
            )
            await self.db.commit()

            if lockout_until:
                return False, f"Too many failed attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes."

            remaining = MAX_FAILED_ATTEMPTS - new_attempts
            return False, f"Invalid code. {remaining} attempts remaining."

    async def regenerate_backup_codes(self, user_id: int, code: str) -> Tuple[bool, List[str]]:
        """
        Regenerate backup codes (requires valid TOTP code).

        Args:
            user_id: User ID
            code: Current TOTP code for verification

        Returns:
            Tuple of (success, new_backup_codes)
        """
        from app.base_models import User

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.totp_enabled:
            raise ValueError("MFA is not enabled")

        # Verify TOTP code (not backup code)
        secret = decrypt_pii(user.totp_secret)
        if not verify_totp(secret, code):
            return False, []

        # Generate new backup codes
        backup_codes = generate_backup_codes()
        hashed_codes = [hash_backup_code(c) for c in backup_codes]

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(backup_codes={"codes": hashed_codes})
        )
        await self.db.commit()

        logger.info("mfa_backup_codes_regenerated", user_id=user_id)

        return True, backup_codes

    async def _verify_code(self, user, code: str) -> bool:
        """
        Internal method to verify TOTP or backup code.

        Args:
            user: User model instance
            code: TOTP code or backup code

        Returns:
            True if code is valid
        """
        # Try TOTP first
        if user.totp_secret:
            secret = decrypt_pii(user.totp_secret)
            if verify_totp(secret, code):
                return True

        # Try backup code
        if user.backup_codes and "codes" in user.backup_codes:
            is_valid, index = verify_backup_code(code, user.backup_codes["codes"])
            if is_valid and index is not None:
                # Mark backup code as used
                codes = user.backup_codes["codes"].copy()
                codes[index] = None  # Mark as used

                await self.db.execute(
                    update(type(user))
                    .where(type(user).id == user.id)
                    .values(backup_codes={"codes": codes})
                )
                await self.db.commit()

                logger.info("mfa_backup_code_used", user_id=user.id, code_index=index)
                return True

        return False


# =============================================================================
# Convenience Functions
# =============================================================================

async def check_mfa_required(db: AsyncSession, user_id: int) -> bool:
    """Check if MFA verification is required for login."""
    from app.base_models import User

    result = await db.execute(
        select(User.totp_enabled).where(User.id == user_id)
    )
    totp_enabled = result.scalar_one_or_none()

    return bool(totp_enabled)


async def is_user_locked(db: AsyncSession, user_id: int) -> Tuple[bool, Optional[datetime]]:
    """Check if user is locked out from MFA attempts."""
    from app.base_models import User

    result = await db.execute(
        select(User.totp_lockout_until).where(User.id == user_id)
    )
    lockout_until = result.scalar_one_or_none()

    if lockout_until and datetime.now(timezone.utc) < lockout_until:
        return True, lockout_until

    return False, None
