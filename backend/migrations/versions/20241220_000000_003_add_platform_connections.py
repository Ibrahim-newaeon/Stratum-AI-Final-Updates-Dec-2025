"""Add PlatformConnection model for persistent credential storage

Revision ID: 003
Revises: 002
Create Date: 2024-12-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Create ConnectionStatus enum
    # =========================================================================
    op.execute("CREATE TYPE connectionstatus AS ENUM ('connected', 'disconnected', 'error', 'pending')")

    # =========================================================================
    # Create platform_connections table
    # =========================================================================
    op.create_table(
        'platform_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Platform identification
        sa.Column('platform', postgresql.ENUM('meta', 'google', 'tiktok', 'snapchat', 'linkedin', name='adplatform', create_type=False), nullable=False),

        # Connection status
        sa.Column('status', postgresql.ENUM('connected', 'disconnected', 'error', 'pending', name='connectionstatus', create_type=False), nullable=False, server_default='pending'),

        # Encrypted credentials
        sa.Column('credentials_encrypted', sa.Text(), nullable=False),

        # Platform-specific account info
        sa.Column('account_id', sa.String(length=255), nullable=True),
        sa.Column('account_name', sa.String(length=255), nullable=True),

        # Connection metadata
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),

        # Sync configuration
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=False, server_default='60'),

        # Additional settings
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key to tenants
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),

        # Unique constraint: one connection per platform per tenant
        sa.UniqueConstraint('tenant_id', 'platform', name='uq_tenant_platform'),
    )

    # Create indexes
    op.create_index('ix_platform_connections_tenant', 'platform_connections', ['tenant_id'])
    op.create_index('ix_platform_connections_status', 'platform_connections', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_platform_connections_status', table_name='platform_connections')
    op.drop_index('ix_platform_connections_tenant', table_name='platform_connections')

    # Drop table
    op.drop_table('platform_connections')

    # Drop enum
    op.execute("DROP TYPE connectionstatus")
