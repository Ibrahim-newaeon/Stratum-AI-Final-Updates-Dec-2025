# =============================================================================
# Stratum AI - User-Tenant Memberships (Multi-Account Switcher)
# =============================================================================
"""
Add user_tenant_memberships table to allow users to belong to multiple tenants
with per-tenant roles. Enables the account/workspace switcher feature.

Revision ID: 044_add_user_tenant_memberships
Revises: 043_add_tenant_revenue_monthly
Create Date: 2026-03-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers
revision = '044_add_user_tenant_memberships'
down_revision = '043_add_tenant_revenue_monthly'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_tenant_memberships',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column(
            'role',
            ENUM('superadmin', 'admin', 'manager', 'analyst', 'viewer', name='userrole', create_type=False),
            nullable=False,
            server_default='analyst',
        ),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Unique constraint: one membership per user-tenant pair
    op.create_unique_constraint(
        'uq_user_tenant_membership',
        'user_tenant_memberships',
        ['user_id', 'tenant_id'],
    )

    # Indexes for fast lookups
    op.create_index('ix_utm_user_id', 'user_tenant_memberships', ['user_id'])
    op.create_index('ix_utm_tenant_id', 'user_tenant_memberships', ['tenant_id'])
    op.create_index('ix_utm_user_active', 'user_tenant_memberships', ['user_id', 'is_active'])

    # Seed: create memberships for all existing users based on their current tenant_id
    op.execute("""
        INSERT INTO user_tenant_memberships (user_id, tenant_id, role, is_default, is_active, created_at, updated_at)
        SELECT id, tenant_id, role, true, true, NOW(), NOW()
        FROM users
        WHERE is_deleted = false
    """)


def downgrade():
    op.drop_index('ix_utm_user_active', table_name='user_tenant_memberships')
    op.drop_index('ix_utm_tenant_id', table_name='user_tenant_memberships')
    op.drop_index('ix_utm_user_id', table_name='user_tenant_memberships')
    op.drop_constraint('uq_user_tenant_membership', 'user_tenant_memberships', type_='unique')
    op.drop_table('user_tenant_memberships')
