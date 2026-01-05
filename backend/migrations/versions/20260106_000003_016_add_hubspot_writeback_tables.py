"""Add HubSpot Writeback tables

Revision ID: 016_add_hubspot_writeback_tables
Revises: 015
Create Date: 2026-01-06 00:03:00.000000

This migration adds:
- writeback_status enum for tracking sync operation status
- crm_writeback_configs: Configuration for CRM writeback operations
- crm_writeback_syncs: History of writeback sync operations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_add_hubspot_writeback_tables'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Writeback Status Enum
    # ==========================================================================
    writeback_status = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'failed', 'partial',
        name='writeback_status',
        create_type=False
    )
    writeback_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # crm_writeback_configs - Configuration for CRM writeback operations
    # ==========================================================================
    op.create_table(
        'crm_writeback_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Writeback toggles
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sync_contacts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_deals', sa.Boolean(), nullable=False, server_default='true'),

        # Sync schedule
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sync_interval_hours', sa.Integer(), nullable=False, server_default='24'),

        # What to sync
        sa.Column('sync_attribution', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_profit_metrics', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_touchpoint_count', sa.Boolean(), nullable=False, server_default='true'),

        # Property setup status
        sa.Column('properties_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('properties_created_at', sa.DateTime(timezone=True), nullable=True),

        # Last sync tracking
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', writeback_status, nullable=True),
        sa.Column('last_sync_contacts', sa.Integer(), nullable=True),
        sa.Column('last_sync_deals', sa.Integer(), nullable=True),
        sa.Column('last_sync_errors', sa.Integer(), nullable=True),

        # Next scheduled sync
        sa.Column('next_sync_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['crm_connections.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('connection_id', name='uq_writeback_config_connection'),
    )

    op.create_index('ix_writeback_config_tenant', 'crm_writeback_configs', ['tenant_id'])
    op.create_index('ix_writeback_config_next_sync', 'crm_writeback_configs', ['next_sync_at'],
                    postgresql_where=sa.text('auto_sync_enabled = true'))

    # ==========================================================================
    # crm_writeback_syncs - History of writeback sync operations
    # ==========================================================================
    op.create_table(
        'crm_writeback_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Sync details
        sa.Column('sync_type', sa.String(50), nullable=False),  # full, incremental, manual, scheduled
        sa.Column('status', writeback_status, nullable=False, server_default='pending'),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),

        # Scope
        sa.Column('sync_contacts', sa.Boolean(), server_default='true'),
        sa.Column('sync_deals', sa.Boolean(), server_default='true'),
        sa.Column('modified_since', sa.DateTime(timezone=True), nullable=True),

        # Results
        sa.Column('contacts_processed', sa.Integer(), server_default='0'),
        sa.Column('contacts_synced', sa.Integer(), server_default='0'),
        sa.Column('contacts_failed', sa.Integer(), server_default='0'),
        sa.Column('deals_processed', sa.Integer(), server_default='0'),
        sa.Column('deals_synced', sa.Integer(), server_default='0'),
        sa.Column('deals_failed', sa.Integer(), server_default='0'),

        # Error details
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),

        # Triggered by
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['crm_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_writeback_sync_tenant_date', 'crm_writeback_syncs', ['tenant_id', 'started_at'])
    op.create_index('ix_writeback_sync_status', 'crm_writeback_syncs', ['tenant_id', 'status'])
    op.create_index('ix_writeback_sync_connection', 'crm_writeback_syncs', ['connection_id', 'started_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('crm_writeback_syncs')
    op.drop_table('crm_writeback_configs')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS writeback_status')
