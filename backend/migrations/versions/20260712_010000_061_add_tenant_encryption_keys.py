"""Add per-tenant PII encryption key store (AUTH-05).

Envelope encryption: each tenant gets a random data-encryption key (DEK),
stored wrapped by a master-derived key-encryption key. Enables per-tenant PII
key isolation without a big-bang re-encryption (dual-read rollout).

Revision ID: 061_add_tenant_encryption_keys
Revises: 060_add_fk_indexes
"""

import sqlalchemy as sa

from alembic import op

revision = "061_add_tenant_encryption_keys"
down_revision = "060_add_fk_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_encryption_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("wrapped_dek", sa.String(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_encryption_keys_tenant_id"),
    )
    op.create_index(
        "ix_tenant_encryption_keys_tenant_id",
        "tenant_encryption_keys",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_encryption_keys_tenant_id", table_name="tenant_encryption_keys"
    )
    op.drop_table("tenant_encryption_keys")
