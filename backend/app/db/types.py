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
