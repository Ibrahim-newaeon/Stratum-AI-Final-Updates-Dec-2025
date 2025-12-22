"""Add EMQ One-Click Fix System tables

Revision ID: 007
Revises: 006
Create Date: 2024-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenant_tracking_configs table
    op.create_table(
        "tenant_tracking_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pixel_id", sa.String(80), nullable=True),
        sa.Column("dataset_id", sa.String(80), nullable=True),
        sa.Column("measurement_id", sa.String(80), nullable=True),
        sa.Column("normalization_policy", sa.String(20), nullable=False, server_default="v1"),
        sa.Column("dedupe_mode", sa.String(20), nullable=False, server_default="capi_only"),
        sa.Column("retry_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("backoff_seconds", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
    )

    # Unique index for tenant + platform
    op.create_index(
        "ix_tracking_cfg_tenant_platform",
        "tenant_tracking_configs",
        ["tenant_id", "platform"],
        unique=True,
    )

    # Create fix_runs table
    op.create_table(
        "fix_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("issue_code", sa.String(80), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("applied_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("before_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
    )

    # Index for querying fix runs
    op.create_index(
        "ix_fix_runs_tenant_platform_date",
        "fix_runs",
        ["tenant_id", "platform", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_fix_runs_tenant_platform_date", table_name="fix_runs")
    op.drop_table("fix_runs")
    op.drop_index("ix_tracking_cfg_tenant_platform", table_name="tenant_tracking_configs")
    op.drop_table("tenant_tracking_configs")
