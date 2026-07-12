# =============================================================================
# Stratum AI - Per-Tenant PII Key Management [AUTH-05]
# =============================================================================
"""
Envelope encryption for per-tenant PII keys.

Each tenant has a random Fernet data-encryption key (DEK). DEKs are wrapped
(encrypted) with a key-encryption key (KEK) derived from the master
``settings.pii_encryption_key`` and persisted in ``tenant_encryption_keys``.
At runtime the unwrapped DEKs live in an in-memory cache so PII
encrypt/decrypt stay synchronous with no per-call DB I/O (the codebase forbids
blocking the event loop). The cache is populated at startup
(``initialize_pii_keys``) and refreshed whenever a tenant is provisioned
(``ensure_tenant_dek``).

Rollout is dual-read (see ``app.core.security``): new writes use the per-tenant
DEK; existing ciphertext still decrypts via the legacy global-derived key, so
no mass re-encryption is required.
"""

import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# tenant_id -> DEK (a Fernet key: url-safe base64 bytes). Process-local; safe
# because it holds only in-memory copies already derivable from the DB + master
# key. Never logged or serialized.
_DEK_CACHE: dict[int, bytes] = {}

# Distinct from the PII derivation salt in security.py so the KEK and the legacy
# per-tenant PII keys never collide.
_KEK_SALT = b"stratum_ai_kek_salt_v1"


def _kek() -> Fernet:
    """Key-encryption key derived from the master secret; wraps per-tenant DEKs."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KEK_SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.pii_encryption_key.encode()))
    return Fernet(key)


def wrap_dek(dek: bytes) -> str:
    """Encrypt a DEK with the KEK for storage. Returns base64 text."""
    return _kek().encrypt(dek).decode("utf-8")


def unwrap_dek(wrapped: str) -> bytes:
    """Decrypt a stored wrapped DEK back to a usable Fernet key."""
    return _kek().decrypt(wrapped.encode("utf-8"))


def get_cached_dek(tenant_id: Optional[int]) -> Optional[bytes]:
    """Return the tenant's DEK from the in-memory cache, or None if absent.

    None means "fall back to the legacy global-derived key" — never an error.
    """
    if tenant_id is None:
        return None
    return _DEK_CACHE.get(tenant_id)


def cache_size() -> int:
    """Number of tenant DEKs currently cached (diagnostics)."""
    return len(_DEK_CACHE)


def _clear_cache() -> None:
    """Test hook: drop all cached DEKs."""
    _DEK_CACHE.clear()


async def ensure_tenant_dek(tenant_id: int, db: AsyncSession) -> bytes:
    """Return the tenant's DEK, provisioning + persisting one if absent.

    Populates the cache. Safe against a concurrent provisioner via the unique
    constraint on ``tenant_id`` — on a race we re-read the winning row. The
    caller is responsible for committing the surrounding transaction.
    """
    cached = _DEK_CACHE.get(tenant_id)
    if cached is not None:
        return cached

    from sqlalchemy import select

    from app.models.encryption import TenantEncryptionKey

    row = (
        await db.execute(
            select(TenantEncryptionKey).where(
                TenantEncryptionKey.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        dek = unwrap_dek(row.wrapped_dek)
        _DEK_CACHE[tenant_id] = dek
        return dek

    dek = Fernet.generate_key()
    db.add(
        TenantEncryptionKey(
            tenant_id=tenant_id, wrapped_dek=wrap_dek(dek), key_version=1
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        # Another request provisioned it first — roll back our insert and adopt
        # the persisted DEK so both callers agree on one key for the tenant.
        await db.rollback()
        row = (
            await db.execute(
                select(TenantEncryptionKey).where(
                    TenantEncryptionKey.tenant_id == tenant_id
                )
            )
        ).scalar_one()
        dek = unwrap_dek(row.wrapped_dek)
        _DEK_CACHE[tenant_id] = dek
        return dek

    _DEK_CACHE[tenant_id] = dek
    logger.info("pii_dek_provisioned", tenant_id=tenant_id)
    return dek


async def load_all_tenant_deks(db: AsyncSession) -> int:
    """Unwrap every stored DEK into the cache. Returns the number loaded."""
    from sqlalchemy import select

    from app.models.encryption import TenantEncryptionKey

    rows = (await db.execute(select(TenantEncryptionKey))).scalars().all()
    for row in rows:
        try:
            _DEK_CACHE[row.tenant_id] = unwrap_dek(row.wrapped_dek)
        except InvalidToken:
            # A DEK we can't unwrap (master key changed?) — skip it; that tenant
            # falls back to the legacy global key rather than crashing startup.
            logger.error("pii_dek_unwrap_failed", tenant_id=row.tenant_id)
    return len(rows)


async def initialize_pii_keys(db: AsyncSession) -> dict:
    """Startup hook: cache all DEKs, provisioning one for any tenant lacking it.

    Never raises — a key-store hiccup must not block app startup; affected
    tenants simply fall back to the legacy global-derived key (dual-read).
    Returns ``{"loaded": int, "provisioned": int}``.
    """
    from sqlalchemy import select

    from app.base_models import Tenant

    loaded = await load_all_tenant_deks(db)

    tenant_ids = (await db.execute(select(Tenant.id))).scalars().all()
    provisioned = 0
    for tid in tenant_ids:
        if tid not in _DEK_CACHE:
            await ensure_tenant_dek(tid, db)
            provisioned += 1
    if provisioned:
        await db.commit()

    logger.info("pii_keys_initialized", loaded=loaded, provisioned=provisioned)
    return {"loaded": loaded, "provisioned": provisioned}
