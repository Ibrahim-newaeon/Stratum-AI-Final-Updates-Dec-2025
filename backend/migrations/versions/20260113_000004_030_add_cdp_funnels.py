"""Add CDP funnel/journey tracking tables

Revision ID: 030_add_cdp_funnels
Revises: 029_cdp_segments
Create Date: 2026-01-13 00:00:04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = "030_add_cdp_funnels"
down_revision = "029_cdp_segments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # CDP Funnels Table
    # ==========================================================================
    op.create_table(
        "cdp_funnels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),

        # Funnel identification
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(100), nullable=True),

        # Configuration
        sa.Column("status", sa.String(50), nullable=False, default="draft"),
        sa.Column("steps", JSONB, nullable=False, server_default="[]"),

        # Analysis configuration
        sa.Column("conversion_window_days", sa.Integer(), nullable=False, default=30),
        sa.Column("step_timeout_hours", sa.Integer(), nullable=True),

        # Computed metrics (cached)
        sa.Column("total_entered", sa.Integer(), nullable=False, default=0),
        sa.Column("total_converted", sa.Integer(), nullable=False, default=0),
        sa.Column("overall_conversion_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("step_metrics", JSONB, nullable=False, server_default="[]"),

        # Timing
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computation_duration_ms", sa.Integer(), nullable=True),

        # Scheduling
        sa.Column("auto_refresh", sa.Boolean(), nullable=False, default=True),
        sa.Column("refresh_interval_hours", sa.Integer(), nullable=False, default=24),
        sa.Column("next_refresh_at", sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Indexes for funnels
    op.create_index("ix_cdp_funnels_tenant", "cdp_funnels", ["tenant_id"])
    op.create_index("ix_cdp_funnels_status", "cdp_funnels", ["tenant_id", "status"])

    # Unique constraint for slug per tenant
    op.create_unique_constraint(
        "uq_cdp_funnels_slug",
        "cdp_funnels",
        ["tenant_id", "slug"]
    )

    # ==========================================================================
    # CDP Funnel Entries Table
    # ==========================================================================
    op.create_table(
        "cdp_funnel_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("funnel_id", UUID(as_uuid=True), sa.ForeignKey("cdp_funnels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("cdp_profiles.id", ondelete="CASCADE"), nullable=False),

        # Entry status
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_converted", sa.Boolean(), nullable=False, default=False),

        # Progress tracking
        sa.Column("current_step", sa.Integer(), nullable=False, default=1),
        sa.Column("completed_steps", sa.Integer(), nullable=False, default=1),
        sa.Column("step_timestamps", JSONB, nullable=False, server_default="{}"),

        # Time analysis
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Indexes for funnel entries
    op.create_index("ix_cdp_funnel_entries_tenant", "cdp_funnel_entries", ["tenant_id"])
    op.create_index("ix_cdp_funnel_entries_funnel", "cdp_funnel_entries", ["funnel_id"])
    op.create_index("ix_cdp_funnel_entries_profile", "cdp_funnel_entries", ["profile_id"])
    op.create_index("ix_cdp_funnel_entries_converted", "cdp_funnel_entries", ["funnel_id", "is_converted"])

    # One entry per profile per funnel
    op.create_unique_constraint(
        "uq_cdp_funnel_entries_funnel_profile",
        "cdp_funnel_entries",
        ["tenant_id", "funnel_id", "profile_id"]
    )


def downgrade() -> None:
    # Drop funnel entries table
    op.drop_constraint("uq_cdp_funnel_entries_funnel_profile", "cdp_funnel_entries", type_="unique")
    op.drop_index("ix_cdp_funnel_entries_converted", table_name="cdp_funnel_entries")
    op.drop_index("ix_cdp_funnel_entries_profile", table_name="cdp_funnel_entries")
    op.drop_index("ix_cdp_funnel_entries_funnel", table_name="cdp_funnel_entries")
    op.drop_index("ix_cdp_funnel_entries_tenant", table_name="cdp_funnel_entries")
    op.drop_table("cdp_funnel_entries")

    # Drop funnels table
    op.drop_constraint("uq_cdp_funnels_slug", "cdp_funnels", type_="unique")
    op.drop_index("ix_cdp_funnels_status", table_name="cdp_funnels")
    op.drop_index("ix_cdp_funnels_tenant", table_name="cdp_funnels")
    op.drop_table("cdp_funnels")
