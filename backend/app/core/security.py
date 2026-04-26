# =============================================================================
# Stratum AI - Security Module
# =============================================================================
"""
Security utilities including JWT handling, password hashing, and PII encryption.
Implements GDPR-compliant encryption for sensitive data.
"""

import asyncio
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt
from jwt.exceptions import PyJWTError as JWTError
from passlib.context import CryptContext

from app.core.config import settings

import redis.asyncio as aioredis

# Shared Redis connection pool — avoids creating a new connection per call
_redis_pool: aioredis.Redis | None = None
_redis_pool_lock: asyncio.Lock | None = None


def _get_redis_lock() -> asyncio.Lock:
    """Lazily create the asyncio lock (must be created inside a running loop)."""
    global _redis_pool_lock
    if _redis_pool_lock is None:
        _redis_pool_lock = asyncio.Lock()
    return _redis_pool_lock


async def get_redis_pool() -> aioredis.Redis:
    """Return a shared Redis connection pool for security operations."""
    global _redis_pool
    if _redis_pool is not None:
        return _redis_pool

    async with _get_redis_lock():
        # Double-check after acquiring the lock
        if _redis_pool is None:
            _redis_pool = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
            )
    return _redis_pool

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_for_bcrypt(password: str) -> str:
    """Truncate password to 72 bytes (bcrypt max) without splitting multi-byte chars."""
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(_truncate_for_bcrypt(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return pwd_context.hash(_truncate_for_bcrypt(password))


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
    except (JWTError, jwt.DecodeError, jwt.ExpiredSignatureError):
        return None


# =============================================================================
# PII Encryption (GDPR Compliance)
# =============================================================================

def _get_pii_salt(tenant_id: int | None = None) -> bytes:
    """Return the salt used for PII key derivation.

    Uses a per-tenant salt when tenant_id is provided, derived from
    the master encryption key and tenant identifier to prevent
    cross-tenant rainbow table attacks.
    """
    base_salt = b"stratum_ai_pii_salt_v2"
    if tenant_id is not None:
        return hashlib.sha256(base_salt + str(tenant_id).encode()).digest()
    return base_salt


def _get_fernet_key(tenant_id: int | None = None) -> bytes:
    """
    Derive a Fernet-compatible key from the encryption key setting.
    Uses PBKDF2 for key derivation.
    """
    # Use a fixed salt for deterministic key derivation
    # In production, consider using a per-tenant salt stored securely
    salt = _get_pii_salt(tenant_id)

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


def encrypt_pii(plaintext: str, tenant_id: int | None = None) -> str:
    """
    Encrypt PII data using Fernet symmetric encryption.

    Args:
        plaintext: The sensitive data to encrypt
        tenant_id: Optional tenant ID for per-tenant key derivation

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ""

    fernet = Fernet(_get_fernet_key(tenant_id))
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_pii(ciphertext: str, tenant_id: int | None = None) -> str:
    """
    Decrypt PII data.

    Falls back to returning the raw value if decryption fails (e.g. the data
    was stored in plaintext or encrypted with a different key).

    Args:
        ciphertext: The encrypted data to decrypt
        tenant_id: Optional tenant ID for per-tenant key derivation

    Returns:
        Decrypted plaintext string
    """
    if not ciphertext:
        return ""

    try:
        fernet = Fernet(_get_fernet_key(tenant_id))
        decrypted = fernet.decrypt(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))
        return decrypted.decode("utf-8")
    except (InvalidToken, Exception) as exc:
        # Never silently return ciphertext as plaintext — that leaks encrypted
        # data into contexts that expect decrypted values (logs, API responses).
        raise ValueError(
            f"PII decryption failed: {type(exc).__name__}. "
            "Data may be corrupted or encrypted with a different key."
        ) from exc


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
# JWT Token Blacklist (Redis-backed)
# =============================================================================

TOKEN_BLACKLIST_PREFIX = "token_blacklist:"


async def blacklist_token(token: str, payload: dict[str, Any]) -> None:
    """
    Add a JWT token to the Redis blacklist.

    The entry expires when the token itself would expire, so Redis
    automatically cleans up stale entries.

    Args:
        token: The raw JWT string
        payload: Decoded token payload (must contain 'exp')
    """
    exp = payload.get("exp")
    if not exp:
        return

    ttl = int(exp - datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        return  # Already expired

    jti = payload.get("jti", token[-32:])  # Use jti if present, else token suffix
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    client = await get_redis_pool()
    await client.setex(key, ttl, "1")


async def is_token_blacklisted(payload: dict[str, Any], token: str) -> bool:
    """
    Check whether a token has been blacklisted.

    Args:
        payload: Decoded token payload
        token: The raw JWT string

    Returns:
        True if the token is blacklisted

    Raises:
        ConnectionError: If Redis is unreachable (callers should handle gracefully)
        TimeoutError: If Redis operation times out
    """
    jti = payload.get("jti", token[-32:])
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    try:
        client = await get_redis_pool()
        return await client.exists(key) == 1
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise ConnectionError(
            f"Redis unavailable during token blacklist check: {type(exc).__name__}"
        ) from exc


# =============================================================================
# Login Rate Limiting (Redis-backed)
# =============================================================================

LOGIN_ATTEMPT_PREFIX = "login_attempts:"
LOGIN_LOCKOUT_PREFIX = "login_lockout:"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 300  # 5 minutes
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


async def check_login_rate_limit(email_hash: str) -> tuple[bool, int]:
    """
    Check if login attempts for this email hash are rate-limited.

    Returns:
        Tuple of (is_allowed, remaining_lockout_seconds)
    """
    client = await get_redis_pool()
    lockout_key = f"{LOGIN_LOCKOUT_PREFIX}{email_hash}"
    lockout_ttl = await client.ttl(lockout_key)
    if lockout_ttl > 0:
        return False, lockout_ttl
    return True, 0


async def record_failed_login(email_hash: str) -> int:
    """
    Record a failed login attempt. Returns the current attempt count.
    If MAX_LOGIN_ATTEMPTS is reached, sets a lockout.
    """
    client = await get_redis_pool()
    key = f"{LOGIN_ATTEMPT_PREFIX}{email_hash}"
    attempts = await client.incr(key)
    if attempts == 1:
        await client.expire(key, LOGIN_ATTEMPT_WINDOW_SECONDS)

    if attempts >= MAX_LOGIN_ATTEMPTS:
        lockout_key = f"{LOGIN_LOCKOUT_PREFIX}{email_hash}"
        await client.setex(lockout_key, LOGIN_LOCKOUT_SECONDS, "1")
        await client.delete(key)

    return attempts


async def clear_login_attempts(email_hash: str) -> None:
    """Clear failed login attempts after successful login."""
    client = await get_redis_pool()
    await client.delete(f"{LOGIN_ATTEMPT_PREFIX}{email_hash}")


# =============================================================================
# Permission Decorator
# =============================================================================

def require_permission(permission: str) -> Any:
    """
    Dependency factory that checks if the current user has the required permission.

    Args:
        permission: The permission string to check (e.g., "CAMPAIGN_APPROVE")

    Returns:
        A FastAPI dependency that validates the permission
    """
    from fastapi import Depends, HTTPException, Request

    async def permission_checker(request: Request) -> bool:
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
