# =============================================================================
# Stratum AI - Add superadmin to userrole enum
# =============================================================================
"""
Add 'superadmin' value to PostgreSQL userrole enum type.

The Python UserRole enum includes SUPERADMIN but the database enum
was never updated via migration. The seed_superadmin script handles this
at runtime, but a proper migration ensures consistency across environments.

Revision ID: 041_add_superadmin_to_userrole_enum
Revises: 040_add_newsletter_system
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op
from sqlalchemy import text

# revision identifiers
revision = "041_add_superadmin_to_userrole_enum"
down_revision = "040_add_newsletter_system"
branch_labels = None
depends_on = None


def upgrade():
    # Check if superadmin already exists in the enum (e.g. from seed script)
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT 1 FROM pg_enum "
        "WHERE enumtypid = 'userrole'::regtype "
        "AND enumlabel = 'superadmin'"
    ))
    if not result.fetchone():
        # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PG < 12.
        # In PG 12+ it can run inside a transaction with IF NOT EXISTS.
        # Railway uses PG 16, so this is safe.
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'superadmin' BEFORE 'admin'")


def downgrade():
    # PostgreSQL doesn't support removing enum values.
    # The 'superadmin' value will remain in the enum type.
    pass
