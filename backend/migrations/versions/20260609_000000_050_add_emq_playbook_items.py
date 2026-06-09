"""Add emq_playbook_item_state table.

Persists user-driven workflow state (status / owner) for the deterministically
generated EMQ fix-playbook items, keyed by a stable (tenant_id, item_key).

Revision ID: 050_add_emq_playbook_items
Revises: 049_copilot_doc_chunks
Create Date: 2026-06-09 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "050_add_emq_playbook_items"
down_revision = "049_copilot_doc_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emq_playbook_item_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "item_key", name="uq_emq_playbook_item"),
    )
    op.create_index(
        "ix_emq_playbook_state_tenant", "emq_playbook_item_state", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_emq_playbook_state_tenant", table_name="emq_playbook_item_state")
    op.drop_table("emq_playbook_item_state")
