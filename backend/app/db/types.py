# =============================================================================
# Stratum AI - Custom SQLAlchemy Column Types
# =============================================================================
"""
Reusable column types.

`EncryptedString` and `EncryptedText` transparently encrypt a column at rest
with Fernet, using the same `encrypt_pii`/`decrypt_pii` helpers the app uses for
PII. They differ only in the underlying SQL type: `VARCHAR(n)` versus `TEXT`.
"""

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator

from app.core.security import decrypt_pii, encrypt_pii


class _EncryptedMixin:
    """Shared Fernet bind/result handling for the encrypted column types.

    **Uses the global key, not a per-tenant one, and cannot do otherwise.**
    A ``TypeDecorator`` is handed the bare value, never the row, so there is no
    way to reach ``tenant_id`` from here.

    Prefer a tenant-aware call site (``encrypt_pii(value, tenant_id)``, as
    ``AudienceSyncCredential`` does with explicit ``set_x``/``get_x`` accessors)
    whenever the row *has* a tenant. Reach for these types only when it
    structurally does not. Do not use them for access or refresh tokens: those
    all hang off tenant-scoped rows and have tenant-aware call sites already.

    Current uses, both deliberate:

    - ``SlackIntegration.webhook_url`` — one low-sensitivity column.
    - ``CMSContactSubmission`` PII (2026-08-17) — the public marketing contact
      form. That table has no ``tenant_id`` at all: submissions belong to
      Stratum, not to a tenant, so there is no key to derive per-tenant and the
      global key is the only option available.

    Rows written before encryption was introduced are returned as-is (they fail
    to decrypt) and get re-encrypted on their next write, so adding the type to
    an existing column needs no data migration. Note the limit of that: a row
    whose encrypted columns are never rewritten stays plaintext forever. It is
    only a clean migration path for columns that get updated, or for a table
    that is empty when the type is introduced.

    Widening the column IS required, though. Measure rather than estimate: a
    bare Fernet token is ~1.4x the plaintext, but ``encrypt_pii`` here produces
    about **2.2x** (255 chars -> 560, 50 -> 220, 45 -> 188). A ``VARCHAR`` sized
    to the input limit will reject the longest legitimate value on insert.
    """

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


class EncryptedString(_EncryptedMixin, TypeDecorator):
    """A ``VARCHAR`` column transparently encrypted at rest with Fernet.

    See ``_EncryptedMixin`` for the key-scoping caveat and sizing rule.
    """

    impl = String


class EncryptedText(_EncryptedMixin, TypeDecorator):
    """A ``TEXT`` column transparently encrypted at rest with Fernet.

    Use this for unbounded free text (a message body) so the column keeps its
    ``TEXT`` type instead of becoming a ``VARCHAR`` wide enough to guess at.
    """

    impl = Text
