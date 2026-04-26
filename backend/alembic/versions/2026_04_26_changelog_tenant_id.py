"""Add tenant_id to changelog_entries

Revision ID: changelog_tenant_2026_04_26
Revises: kg_2026_02_07
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'changelog_tenant_2026_04_26'
down_revision = 'kg_2026_02_07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tenant_id column (nullable for backward compatibility)
    op.add_column(
        'changelog_entries',
        sa.Column('tenant_id', sa.Integer(), nullable=True)
    )
    # Create index for tenant-scoped queries
    op.create_index(
        'ix_changelog_entries_tenant_id',
        'changelog_entries',
        ['tenant_id'],
        unique=False
    )
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_changelog_entries_tenant_id_tenants',
        'changelog_entries',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_changelog_entries_tenant_id_tenants', 'changelog_entries', type_='foreignkey')
    op.drop_index('ix_changelog_entries_tenant_id', table_name='changelog_entries')
    op.drop_column('changelog_entries', 'tenant_id')
