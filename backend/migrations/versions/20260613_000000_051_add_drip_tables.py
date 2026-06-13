"""Add drip_sequences and drip_execution_logs tables.

Persists drip (email sequence) campaigns and their execution logs, replacing
the former per-process in-memory store in the drip-campaigns endpoint, which
lost data on restart and was invisible across API workers.

Identifiers keep the legacy ``drip_<hex>`` / ``exec_<hex>`` string format, so
the table primary keys are VARCHAR rather than UUID.

Revision ID: 051_add_drip_tables
Revises: 050_add_emq_playbook_items
Create Date: 2026-06-13 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "051_add_drip_tables"
down_revision = "050_add_emq_playbook_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drip_sequences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column(
            "trigger_config",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column(
            "nodes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "edges", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "active_recipient_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "revenue_attributed_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_drip_sequences_tenant_id", "drip_sequences", ["tenant_id"])
    op.create_index(
        "ix_drip_sequences_created_by_user_id", "drip_sequences", ["created_by_user_id"]
    )
    op.create_index(
        "ix_drip_sequence_tenant_status", "drip_sequences", ["tenant_id", "status"]
    )

    op.create_table(
        "drip_execution_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.String(length=64), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sequence_id"], ["drip_sequences.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_drip_execution_logs_tenant_id", "drip_execution_logs", ["tenant_id"]
    )
    op.create_index(
        "ix_drip_execution_logs_sequence_id", "drip_execution_logs", ["sequence_id"]
    )
    op.create_index(
        "ix_drip_exec_sequence", "drip_execution_logs", ["sequence_id", "sent_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_drip_exec_sequence", table_name="drip_execution_logs")
    op.drop_index(
        "ix_drip_execution_logs_sequence_id", table_name="drip_execution_logs"
    )
    op.drop_index("ix_drip_execution_logs_tenant_id", table_name="drip_execution_logs")
    op.drop_table("drip_execution_logs")

    op.drop_index("ix_drip_sequence_tenant_status", table_name="drip_sequences")
    op.drop_index("ix_drip_sequences_created_by_user_id", table_name="drip_sequences")
    op.drop_index("ix_drip_sequences_tenant_id", table_name="drip_sequences")
    op.drop_table("drip_sequences")
