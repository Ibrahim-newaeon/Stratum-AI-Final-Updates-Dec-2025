# =============================================================================
# Stratum AI - Custom SQLAlchemy Column Types
# =============================================================================
"""
Reusable column types.

`EncryptedString` transparently encrypts a text column at rest with Fernet,
using the same `encrypt_pii`/`decrypt_pii` helpers the app uses for PII.
"""

from typing import Optional

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.security import decrypt_pii, encrypt_pii


class EncryptedString(TypeDecorator):
    """
    A ``String`` column transparently encrypted at rest with Fernet.

    Encrypts on write, decrypts on read. Rows written before encryption was
    introduced are returned as-is (they fail to decrypt) and get re-encrypted
    on their next write — so **no data migration is required** and the
    underlying column stays ``VARCHAR``.

    **Uses the global key, not a per-tenant one, and cannot do otherwise.**
    A ``TypeDecorator`` is handed the bare value, never the row, so there is no
    way to reach ``tenant_id`` from here. Everything else that stores a secret
    now passes the owning tenant to ``encrypt_pii`` (AUTH-05); this type is the
    one place that structurally can't.

    Only ``SlackIntegration.webhook_url`` uses it today, so the exposure is one
    low-sensitivity column. Do **not** reach for this type for access tokens,
    refresh tokens, or user PII — those have tenant-aware call sites and should
    use them. Making this tenant-aware means moving to explicit
    ``set_x``/``get_x`` accessors on the model (as ``AudienceSyncCredential``
    does) rather than a column type.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_pii(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        try:
            return decrypt_pii(value)
        except ValueError:
            # Legacy row stored as plaintext before encryption was added.
            # Return it as-is; it becomes ciphertext on the next write.
            return value
