"""widen api_keys.key_prefix from VARCHAR(10) to VARCHAR(32)

The generated key prefix ``strat_live_`` is 11 characters, which overflowed
the original ``VARCHAR(10)`` column and caused API-key creation/regeneration
to fail with a StringDataRightTruncation error. Widen the column so live
keys can be stored. Increasing a varchar length limit in PostgreSQL is a
metadata-only change (no table rewrite, no long lock).

Revision ID: 053_widen_api_key_prefix
Revises: 052_add_push_tables
Create Date: 2026-06-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "053_widen_api_key_prefix"
down_revision = "052_add_push_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "api_keys",
        "key_prefix",
        existing_type=sa.String(length=10),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Narrowing back to VARCHAR(10) would truncate existing prefixes; only
    # safe if no longer-than-10 values exist. Postgres will reject the
    # change otherwise, which is the desired guard.
    op.alter_column(
        "api_keys",
        "key_prefix",
        existing_type=sa.String(length=32),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
