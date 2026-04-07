# =============================================================================
# Stratum AI - Protected User Field Migration
# =============================================================================
"""
Add is_protected field to users table for root admin protection.

Protected users cannot be:
- Deleted by other admins
- Demoted to a lower role
- Deactivated by other admins

This is used for the CMS root admin account.

Revision ID: 038_add_user_is_protected
Revises: 037_add_cms_2026_workflow
Create Date: 2026-01-23
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "038_add_user_is_protected"
down_revision = "037_add_cms_2026_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_protected field to users table."""

    # Add is_protected flag
    op.add_column(
        "users",
        sa.Column(
            "is_protected",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Protected users cannot be deleted or demoted by other admins",
        ),
    )

    # Add index for protected users (useful for admin queries)
    op.create_index(
        "ix_users_is_protected",
        "users",
        ["is_protected"],
        postgresql_where=sa.text("is_protected = true"),
    )


def downgrade() -> None:
    """Remove is_protected field from users table."""

    # Drop index
    op.drop_index("ix_users_is_protected", table_name="users")

    # Drop column
    op.drop_column("users", "is_protected")
