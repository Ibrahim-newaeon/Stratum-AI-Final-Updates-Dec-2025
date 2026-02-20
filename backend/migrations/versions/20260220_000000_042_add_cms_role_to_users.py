# =============================================================================
# Stratum AI - Add cms_role column to users table
# =============================================================================
"""
Add cms_role column to users table for CMS RBAC.

Adds a nullable String(30) column for CMS-specific roles (super_admin, admin,
editor_in_chief, editor, author, contributor, reviewer, viewer).

Seeds existing superadmin users with cms_role = 'super_admin'.

Revision ID: 042_add_cms_role_to_users
Revises: 041_add_superadmin_to_userrole_enum
Create Date: 2026-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "042_add_cms_role_to_users"
down_revision = "041_add_superadmin_to_userrole_enum"
branch_labels = None
depends_on = None


def upgrade():
    # Add cms_role column (nullable, no default)
    op.add_column(
        "users",
        sa.Column("cms_role", sa.String(30), nullable=True),
    )

    # Add index for cms_role lookups
    op.create_index("ix_users_cms_role", "users", ["cms_role"])

    # Seed: grant super_admin CMS role to existing superadmin users
    op.execute(
        "UPDATE users SET cms_role = 'super_admin' "
        "WHERE role = 'superadmin' AND is_deleted = false"
    )


def downgrade():
    # Drop index first
    op.drop_index("ix_users_cms_role", table_name="users")

    # Drop column
    op.drop_column("users", "cms_role")
