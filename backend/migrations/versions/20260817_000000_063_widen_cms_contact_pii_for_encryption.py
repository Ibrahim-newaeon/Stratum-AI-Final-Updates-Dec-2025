"""Widen cms_contact_submissions PII columns for Fernet ciphertext.

The contact form's identifiable fields are now encrypted at rest via
EncryptedString / EncryptedText (app/db/types.py). The columns were sized to the
ContactSubmit schema's own input limits, so they would reject the longest
legitimate submission on insert.

Widths come from measuring this codebase's encrypt_pii, not from the size of a
bare Fernet token: 255 chars -> 560, 50 -> 220, 45 -> 188, i.e. ~2.2x rather than
~1.4x. The new widths carry margin on top of that.

`message` is untouched: it is TEXT and uses EncryptedText, so it needs no width.
`source_page` and `user_agent` are untouched because they stay plaintext —
neither is a personal identifier.

Production safety: increasing a VARCHAR's length is metadata-only on PostgreSQL
9.2+ (no table rewrite, no data validation pass), taking only a brief ACCESS
EXCLUSIVE lock. Safe to run online.

No data backfill. cms_contact_submissions held 0 rows in production when this
was written, so there is no plaintext to convert. That matters: EncryptedString
returns undecryptable values as-is and re-encrypts them on the next write, but
these rows are only ever updated on their is_read / is_spam flags, so existing
plaintext PII would never have been rewritten. If this migration is ever applied
to a database that does have rows, they stay readable and stay plaintext, and
converting them needs a separate backfill.

Revision ID: 063_widen_cms_contact_pii
Revises: 062_add_sync_job_profiles_suppressed
"""

import sqlalchemy as sa

from alembic import op

revision = "063_widen_cms_contact_pii"
down_revision = "062_add_sync_job_profiles_suppressed"
branch_labels = None
depends_on = None

# column -> (old length, new length)
_WIDENED = {
    "name": (255, 1024),
    "email": (255, 1024),
    "company": (255, 1024),
    "subject": (255, 1024),
    "phone": (50, 512),
    "ip_address": (45, 512),
}

_NULLABLE = {"company", "subject", "phone", "ip_address"}


def upgrade() -> None:
    for column, (_old, new) in _WIDENED.items():
        op.alter_column(
            "cms_contact_submissions",
            column,
            existing_type=sa.String(length=_old),
            type_=sa.String(length=new),
            existing_nullable=column in _NULLABLE,
        )


def downgrade() -> None:
    # Narrowing DOES rewrite the table and will fail outright if any stored
    # ciphertext is longer than the old limit — which is the normal case once
    # rows exist, since that is the whole reason for widening. Downgrading is
    # only safe on an empty table, or after decrypting back to plaintext.
    for column, (old, new) in _WIDENED.items():
        op.alter_column(
            "cms_contact_submissions",
            column,
            existing_type=sa.String(length=new),
            type_=sa.String(length=old),
            existing_nullable=column in _NULLABLE,
        )
