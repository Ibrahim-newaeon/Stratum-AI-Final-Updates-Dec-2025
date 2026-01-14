"""Add CDP audience sync tables

Revision ID: 031_cdp_audience_sync
Revises: 030_cdp_funnels
Create Date: 2026-01-14 00:00:00.000000

Tables:
- platform_audiences: CDP segment to ad platform audience mapping
- audience_sync_jobs: Sync job execution records
- audience_sync_credentials: Platform credentials for sync
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '031_cdp_audience_sync'
down_revision = '030_cdp_funnels'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # Platform Audiences - Links CDP segments to ad platform audiences
    # =========================================================================
    op.create_table(
        'platform_audiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Link to CDP segment
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Platform details
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_audience_id', sa.String(255), nullable=True),
        sa.Column('platform_audience_name', sa.String(255), nullable=False),

        # Ad account linkage
        sa.Column('ad_account_id', sa.String(255), nullable=False),

        # Audience configuration
        sa.Column('audience_type', sa.String(50), server_default='customer_list', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Sync settings
        sa.Column('auto_sync', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('sync_interval_hours', sa.Integer(), server_default='24', nullable=False),
        sa.Column('next_sync_at', sa.DateTime(timezone=True), nullable=True),

        # Status tracking
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(50), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),

        # Audience size on platform
        sa.Column('platform_size', sa.BigInteger(), nullable=True),
        sa.Column('matched_size', sa.BigInteger(), nullable=True),
        sa.Column('match_rate', sa.Numeric(5, 2), nullable=True),

        # Platform-specific configuration
        sa.Column('platform_config', postgresql.JSONB(), server_default='{}', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['segment_id'], ['cdp_segments.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'segment_id', 'platform', 'ad_account_id', name='uq_platform_audiences_segment_platform_account'),
    )

    # Indexes for platform_audiences
    op.create_index('ix_platform_audiences_tenant', 'platform_audiences', ['tenant_id'])
    op.create_index('ix_platform_audiences_segment', 'platform_audiences', ['segment_id'])
    op.create_index('ix_platform_audiences_platform', 'platform_audiences', ['tenant_id', 'platform'])
    op.create_index('ix_platform_audiences_account', 'platform_audiences', ['tenant_id', 'ad_account_id'])

    # =========================================================================
    # Audience Sync Jobs - Tracks sync job executions
    # =========================================================================
    op.create_table(
        'audience_sync_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Link to platform audience
        sa.Column('platform_audience_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Job details
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),

        # Metrics
        sa.Column('profiles_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('profiles_sent', sa.Integer(), server_default='0', nullable=False),
        sa.Column('profiles_added', sa.Integer(), server_default='0', nullable=False),
        sa.Column('profiles_removed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('profiles_failed', sa.Integer(), server_default='0', nullable=False),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), server_default='{}', nullable=False),

        # Platform response
        sa.Column('platform_response', postgresql.JSONB(), server_default='{}', nullable=False),

        # Triggered by
        sa.Column('triggered_by', sa.String(50), nullable=True),
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['platform_audience_id'], ['platform_audiences.id'], ondelete='CASCADE'),
    )

    # Indexes for audience_sync_jobs
    op.create_index('ix_audience_sync_jobs_tenant', 'audience_sync_jobs', ['tenant_id'])
    op.create_index('ix_audience_sync_jobs_audience', 'audience_sync_jobs', ['platform_audience_id'])
    op.create_index('ix_audience_sync_jobs_status', 'audience_sync_jobs', ['tenant_id', 'status'])
    op.create_index('ix_audience_sync_jobs_created', 'audience_sync_jobs', ['created_at'])

    # =========================================================================
    # Audience Sync Credentials - Platform credentials for sync
    # =========================================================================
    op.create_table(
        'audience_sync_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Platform and account
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('ad_account_id', sa.String(255), nullable=False),
        sa.Column('ad_account_name', sa.String(255), nullable=True),

        # Credentials (encrypted in production)
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),

        # Platform-specific IDs
        sa.Column('business_id', sa.String(255), nullable=True),
        sa.Column('customer_id', sa.String(255), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),

        # Additional config
        sa.Column('config', postgresql.JSONB(), server_default='{}', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'platform', 'ad_account_id', name='uq_audience_sync_creds_tenant_platform_account'),
    )

    # Indexes for audience_sync_credentials
    op.create_index('ix_audience_sync_creds_tenant', 'audience_sync_credentials', ['tenant_id'])
    op.create_index('ix_audience_sync_creds_platform', 'audience_sync_credentials', ['tenant_id', 'platform'])


def downgrade() -> None:
    op.drop_table('audience_sync_credentials')
    op.drop_table('audience_sync_jobs')
    op.drop_table('platform_audiences')
