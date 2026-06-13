"""Add push_subscriptions and push_notification_log tables.

Persists web-push device subscriptions and sent-notification records,
replacing the former per-process in-memory store in the push-notifications
endpoint, which lost subscriptions on restart and was invisible across
API workers.

Identifiers keep the legacy ``sub_<hex>`` / ``notif_<hex>`` string format,
so the table primary keys are VARCHAR rather than UUID.

Revision ID: 052_add_push_tables
Revises: 051_add_drip_tables
Create Date: 2026-06-13 01:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "052_add_push_tables"
down_revision = "051_add_drip_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column(
            "keys", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "platform", sa.String(length=20), nullable=False, server_default="web"
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_push_subscriptions_tenant_id", "push_subscriptions", ["tenant_id"]
    )
    op.create_index(
        "ix_push_subscription_tenant_active",
        "push_subscriptions",
        ["tenant_id", "is_active"],
    )

    op.create_table(
        "push_notification_log",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("tag", sa.String(length=255), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "target_type", sa.String(length=20), nullable=False, server_default="all"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_push_notification_log_tenant_id", "push_notification_log", ["tenant_id"]
    )
    op.create_index(
        "ix_push_notif_tenant_created",
        "push_notification_log",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_push_notif_tenant_created", table_name="push_notification_log")
    op.drop_index(
        "ix_push_notification_log_tenant_id", table_name="push_notification_log"
    )
    op.drop_table("push_notification_log")

    op.drop_index("ix_push_subscription_tenant_active", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_tenant_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
