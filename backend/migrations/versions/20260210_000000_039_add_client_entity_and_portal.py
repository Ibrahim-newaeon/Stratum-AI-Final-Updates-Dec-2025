# =============================================================================
# Stratum AI - Client Entity & Portal Migration
# =============================================================================
"""
Add client entity, assignments, requests, and portal fields.

Creates:
- clients table (brand entity for agency model)
- client_assignments table (user ↔ client junction)
- client_requests table (portal workflow, v2 placeholder)
- client_id + user_type columns on users table
- client_id column on campaigns table

Revision ID: 039_add_client_entity_and_portal
Revises: 038_add_user_is_protected
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = "039_add_client_entity_and_portal"
down_revision = "038_add_user_is_protected"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create client tables and add client scope columns."""

    # 1. Create clients table
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("timezone", sa.String(50), server_default="UTC", nullable=False),
        sa.Column("monthly_budget_cents", sa.Integer(), nullable=True),
        sa.Column("target_roas", sa.Float(), nullable=True),
        sa.Column("target_cpa_cents", sa.Integer(), nullable=True),
        sa.Column("target_ctr", sa.Float(), nullable=True),
        sa.Column("budget_alert_threshold", sa.Float(), server_default="0.9", nullable=False),
        sa.Column("roas_alert_threshold", sa.Float(), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # SoftDeleteMixin
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_clients"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_clients_tenant_id_tenants", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_client_tenant_slug"),
    )
    op.create_index("ix_clients_tenant_active", "clients", ["tenant_id", "is_active"])
    op.create_index("ix_clients_tenant_name", "clients", ["tenant_id", "name"])
    op.create_index("ix_clients_tenant_id", "clients", ["tenant_id"])

    # 2. Create client_assignments table
    op.create_table(
        "client_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_client_assignments"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_client_assignments_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_client_assignments_client_id_clients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], name="fk_client_assignments_assigned_by_users", ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_user_client_assignment"),
    )
    op.create_index("ix_client_assignments_user", "client_assignments", ["user_id"])
    op.create_index("ix_client_assignments_client", "client_assignments", ["client_id"])

    # 3. Create client_requests table (v2 placeholder)
    op.create_table(
        "client_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column(
            "request_type",
            sa.Enum(
                "pause_campaign", "resume_campaign", "adjust_budget",
                "change_targeting", "new_campaign", "other",
                name="clientrequesttype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_entity_type", sa.String(50), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("requested_changes", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "rejected", "executed", "cancelled",
                name="clientrequeststatus",
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_client_requests"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_client_requests_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_client_requests_client_id_clients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_client_requests_requested_by_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_client_requests_reviewed_by_users", ondelete="SET NULL"),
    )
    op.create_index("ix_client_requests_client_status", "client_requests", ["client_id", "status"])
    op.create_index("ix_client_requests_status", "client_requests", ["status", "created_at"])
    op.create_index("ix_client_requests_tenant", "client_requests", ["tenant_id"])

    # 4. Add client_id + user_type columns to users table
    op.add_column("users", sa.Column("client_id", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("user_type", sa.String(20), server_default="agency", nullable=False),
    )
    op.create_foreign_key(
        "fk_users_client_id_clients",
        "users",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_client", "users", ["client_id"])

    # 5. Add client_id column to campaigns table
    op.add_column("campaigns", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_campaigns_client_id_clients",
        "campaigns",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_campaigns_client", "campaigns", ["client_id"])


def downgrade() -> None:
    """Reverse all changes."""

    # 5. Remove client_id from campaigns
    op.drop_index("ix_campaigns_client", table_name="campaigns")
    op.drop_constraint("fk_campaigns_client_id_clients", "campaigns", type_="foreignkey")
    op.drop_column("campaigns", "client_id")

    # 4. Remove client_id + user_type from users
    op.drop_index("ix_users_client", table_name="users")
    op.drop_constraint("fk_users_client_id_clients", "users", type_="foreignkey")
    op.drop_column("users", "user_type")
    op.drop_column("users", "client_id")

    # 3. Drop client_requests
    op.drop_index("ix_client_requests_tenant", table_name="client_requests")
    op.drop_index("ix_client_requests_status", table_name="client_requests")
    op.drop_index("ix_client_requests_client_status", table_name="client_requests")
    op.drop_table("client_requests")
    op.execute("DROP TYPE IF EXISTS clientrequeststatus")
    op.execute("DROP TYPE IF EXISTS clientrequesttype")

    # 2. Drop client_assignments
    op.drop_index("ix_client_assignments_client", table_name="client_assignments")
    op.drop_index("ix_client_assignments_user", table_name="client_assignments")
    op.drop_table("client_assignments")

    # 1. Drop clients
    op.drop_index("ix_clients_tenant_id", table_name="clients")
    op.drop_index("ix_clients_tenant_name", table_name="clients")
    op.drop_index("ix_clients_tenant_active", table_name="clients")
    op.drop_table("clients")
