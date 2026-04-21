# =============================================================================
# Stratum AI - Launch Readiness Tables
# =============================================================================
"""Add launch_readiness_item_state + launch_readiness_events tables.

Backs the superadmin-only Launch Readiness wizard (sequential go-live
phases with append-only audit trail).

Revision ID: 046_add_launch_readiness
Revises: 25b2d4ee6525
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "046_add_launch_readiness"
down_revision = "25b2d4ee6525"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "launch_readiness_item_state",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=100), nullable=False),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "checked_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_launch_readiness_item",
        "launch_readiness_item_state",
        ["phase_number", "item_key"],
    )
    op.create_index(
        "ix_launch_readiness_state_phase",
        "launch_readiness_item_state",
        ["phase_number"],
    )

    op.create_table(
        "launch_readiness_events",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_launch_readiness_event_phase_created",
        "launch_readiness_events",
        ["phase_number", "created_at"],
    )
    op.create_index(
        "ix_launch_readiness_event_created",
        "launch_readiness_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_launch_readiness_event_created",
        table_name="launch_readiness_events",
    )
    op.drop_index(
        "ix_launch_readiness_event_phase_created",
        table_name="launch_readiness_events",
    )
    op.drop_table("launch_readiness_events")

    op.drop_index(
        "ix_launch_readiness_state_phase",
        table_name="launch_readiness_item_state",
    )
    op.drop_constraint(
        "uq_launch_readiness_item",
        "launch_readiness_item_state",
        type_="unique",
    )
    op.drop_table("launch_readiness_item_state")
