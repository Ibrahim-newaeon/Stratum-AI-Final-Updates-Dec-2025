"""Add users.department for autopilot approver accountability.

The dashboard's accountability surfaces (RecentAutopilot, AutopilotPanel
action history) show which user accepted each autopilot action and that
user's department. ``fact_actions_queue`` already carries
``approved_by_user_id``; this adds the org-unit attribute on the user.

Free text, admin-managed via Team settings. Not PII, so stored in the
clear (unlike email/full_name). Nullable: existing users have no
department until an admin assigns one, and the UI renders a placeholder.

Revision ID: 057_add_user_department
Revises: 056_catchup_audit_services_drift
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "057_add_user_department"
down_revision = "056_catchup_audit_services_drift"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable column with no default: metadata-only change on PostgreSQL,
    # no table rewrite, safe on a live users table.
    op.add_column(
        "users",
        sa.Column("department", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "department")
