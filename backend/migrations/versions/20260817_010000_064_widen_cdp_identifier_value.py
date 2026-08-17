"""Widen cdp_profile_identifiers.identifier_value for tenant-keyed ciphertext.

The raw identifier (email address, phone number) is now encrypted at rest under
the owning row's tenant key [CDP-04]. app/schemas/cdp.py caps
IdentifierInput.value at 512 characters and encrypt_pii here produces ~2.2x the
plaintext, so the existing VARCHAR(512) would reject the longest legitimate
identifier on insert.

The column KEEPS its name. The model maps it privately as
_identifier_value_encrypted so the public `identifier_value` can be a decrypting
property, which means this is a widening, not a rename — no data moves.

Production safety: increasing a VARCHAR's length is metadata-only on PostgreSQL
9.2+ (no table rewrite, no validation scan), taking only a brief ACCESS EXCLUSIVE
lock. Safe to run online on a large cdp_profile_identifiers table.

No data backfill, and unlike migration 063 this table is NOT empty in general.
Existing rows stay plaintext and stay readable: the property's decrypt fails with
ValueError and returns the stored value as-is. They are re-encrypted only if
something rewrites them, and nothing does — identifier rows are touched to bump
last_seen_at, which does not go through set_identifier_value. Converting the
existing rows therefore needs a deliberate backfill that reads each row, calls
set_identifier_value, and commits per tenant. Tracked separately; this migration
only makes the column able to hold ciphertext so new writes are protected.

Revision ID: 064_widen_cdp_identifier_value
Revises: 063_widen_cms_contact_pii
"""

import sqlalchemy as sa

from alembic import op

revision = "064_widen_cdp_identifier_value"
down_revision = "063_widen_cms_contact_pii"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "cdp_profile_identifiers",
        "identifier_value",
        existing_type=sa.String(length=512),
        type_=sa.String(length=2048),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Narrowing rewrites the table and fails outright if any stored ciphertext
    # exceeds 512 characters — the normal case for any identifier written after
    # the upgrade. Only safe on a table whose values are all still plaintext.
    op.alter_column(
        "cdp_profile_identifiers",
        "identifier_value",
        existing_type=sa.String(length=2048),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
