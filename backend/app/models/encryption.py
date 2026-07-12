# =============================================================================
# Stratum AI - Per-Tenant PII Encryption Keys [AUTH-05]
# =============================================================================
"""
Key store for per-tenant PII data-encryption keys (envelope encryption).

Each tenant gets its own random Fernet data-encryption key (DEK). The DEK is
never stored in plaintext — it is wrapped (encrypted) with a key-encryption key
(KEK) derived from the master ``settings.pii_encryption_key`` and stored here.
At runtime the wrapped DEKs are unwrapped once and held in an in-memory cache
(see ``app.core.pii_keys``) so PII encrypt/decrypt stay synchronous with no
per-call database I/O.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class TenantEncryptionKey(Base):
    """A tenant's wrapped PII data-encryption key."""

    __tablename__ = "tenant_encryption_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Fernet-wrapped DEK (base64 text). Unwrapped with the master-derived KEK.
    wrapped_dek: Mapped[str] = mapped_column(String, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
