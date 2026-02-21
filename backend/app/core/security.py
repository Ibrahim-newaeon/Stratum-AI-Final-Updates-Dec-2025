# =============================================================================
# Stratum AI - Security Module
# =============================================================================
"""
Security utilities including JWT handling, password hashing, and PII encryption.
Implements GDPR-compliant encryption for sensitive data.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject (usually user_id) to encode
        expires_delta: Optional custom expiration time
        additional_claims: Additional JWT claims to include

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject (usually user_id) to encode
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),  # Unique token ID for revocation
    }

    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# =============================================================================
# PII Encryption (GDPR Compliance)
# =============================================================================

def _get_pii_salt() -> bytes:
    """Return the salt used for PII key derivation."""
    return b"stratum_ai_pii_salt_v1"


def _get_fernet_key() -> bytes:
    """
    Derive a Fernet-compatible key from the encryption key setting.
    Uses PBKDF2 for key derivation.
    """
    # Use a fixed salt for deterministic key derivation
    # In production, consider using a per-tenant salt stored securely
    salt = _get_pii_salt()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    key = base64.urlsafe_b64encode(
        kdf.derive(settings.pii_encryption_key.encode())
    )
    return key


def encrypt_pii(plaintext: str) -> str:
    """
    Encrypt PII data using Fernet symmetric encryption.

    Args:
        plaintext: The sensitive data to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ""

    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_pii(ciphertext: str) -> str:
    """
    Decrypt PII data.

    Falls back to returning the raw value if decryption fails (e.g. the data
    was stored in plaintext or encrypted with a different key).

    Args:
        ciphertext: The encrypted data to decrypt

    Returns:
        Decrypted plaintext string
    """
    if not ciphertext:
        return ""

    try:
        fernet = Fernet(_get_fernet_key())
        decrypted = fernet.decrypt(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise  # Tampered or wrong-key data must raise
    except Exception:
        # Data may be stored in plaintext or encrypted with a different key
        return ciphertext


def hash_pii_for_lookup(value: str) -> str:
    """
    Create a deterministic hash of PII for lookup purposes.
    This allows searching encrypted data without decryption.

    Args:
        value: The PII value to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    salted = f"{settings.pii_encryption_key}:{value}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def anonymize_pii(value: str) -> str:
    """
    Anonymize PII data for GDPR "Right to be Forgotten".
    Replaces the value with a non-reversible anonymized version.

    Args:
        value: The PII value to anonymize

    Returns:
        Anonymized string
    """
    # Generate a random anonymized ID
    random_suffix = secrets.token_hex(8)
    return f"ANONYMIZED_{random_suffix}"


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"sk_{'live' if settings.is_production else 'test'}_{secrets.token_urlsafe(32)}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash using constant-time comparison."""
    import hmac
    computed_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return hmac.compare_digest(computed_hash, stored_hash)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


# =============================================================================
# Permission Decorator
# =============================================================================

def require_permission(permission: str):
    """
    Dependency factory that checks if the current user has the required permission.

    Args:
        permission: The permission string to check (e.g., "CAMPAIGN_APPROVE")

    Returns:
        A FastAPI dependency that validates the permission
    """
    from fastapi import Depends, HTTPException, Request

    async def permission_checker(request: Request):
        # Get user permissions from request state (set by auth middleware)
        user_permissions = getattr(request.state, "permissions", [])
        user_role = getattr(request.state, "role", None)

        # Superadmins have all permissions
        if user_role == "superadmin":
            return True

        # Check if user has the required permission
        if permission not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required"
            )

        return True

    return Depends(permission_checker)
