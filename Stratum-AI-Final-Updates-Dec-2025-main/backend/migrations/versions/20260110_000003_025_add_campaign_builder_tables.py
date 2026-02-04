"""Add campaign_builder tables

Revision ID: 025_campaign_builder
Revises: 024_add_onboarding
Create Date: 2026-01-10

Tables:
- tenant_platform_connection: OAuth tokens and connection metadata
- tenant_ad_account: Ad accounts enabled per tenant
- campaign_draft: Campaign drafts with approval workflow
- campaign_publish_log: Audit trail for publish attempts
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '025_campaign_builder'
down_revision = '024_add_onboarding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create campaign builder tables."""

    # 1. tenant_platform_connection
    op.create_table(
        'tenant_platform_connection',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='disconnected'),

        # Token storage
        sa.Column('token_ref', sa.Text(), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),

        # OAuth metadata
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('granted_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Error tracking
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), server_default='0'),
    )

    op.create_unique_constraint('uq_tenant_platform_connection', 'tenant_platform_connection', ['tenant_id', 'platform'])
    op.create_index('ix_tenant_platform_connection_tenant_platform', 'tenant_platform_connection', ['tenant_id', 'platform'])

    # 2. tenant_ad_account
    op.create_table(
        'tenant_ad_account',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant_platform_connection.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),

        # Platform identifiers
        sa.Column('platform_account_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('business_name', sa.String(255), nullable=True),

        # Account configuration
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(100), nullable=False, server_default='UTC'),
        sa.Column('is_enabled', sa.Boolean(), server_default='false', nullable=False),

        # Budget controls
        sa.Column('daily_budget_cap', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('monthly_budget_cap', sa.Numeric(precision=12, scale=2), nullable=True),

        # Platform permissions and metadata
        sa.Column('permissions_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('account_status', sa.String(50), nullable=True),

        # Sync tracking
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_unique_constraint('uq_tenant_ad_account', 'tenant_ad_account', ['tenant_id', 'platform', 'platform_account_id'])
    op.create_index('ix_tenant_ad_account_enabled', 'tenant_ad_account', ['tenant_id', 'is_enabled'])

    # 3. campaign_draft
    op.create_table(
        'campaign_draft',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('ad_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant_ad_account.id', ondelete='SET NULL'), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),

        # Draft identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),

        # Campaign configuration (canonical JSON format)
        sa.Column('draft_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Workflow tracking
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('submitted_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rejected_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),

        # Published campaign reference
        sa.Column('platform_campaign_id', sa.String(255), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_campaign_draft_tenant_status', 'campaign_draft', ['tenant_id', 'status'])
    op.create_index('ix_campaign_draft_platform', 'campaign_draft', ['tenant_id', 'platform'])

    # 4. campaign_publish_log
    op.create_table(
        'campaign_publish_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('draft_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaign_draft.id', ondelete='SET NULL'), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_account_id', sa.String(255), nullable=False),

        # Actor
        sa.Column('published_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Event timing
        sa.Column('event_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Request/Response (for debugging)
        sa.Column('request_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Result
        sa.Column('result_status', sa.String(50), nullable=False),
        sa.Column('platform_campaign_id', sa.String(255), nullable=True),

        # Error details
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Retry tracking
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_campaign_publish_log_tenant_time', 'campaign_publish_log', ['tenant_id', 'event_time'])
    op.create_index('ix_campaign_publish_log_draft', 'campaign_publish_log', ['draft_id'])


def downgrade() -> None:
    """Drop campaign builder tables."""
    op.drop_index('ix_campaign_publish_log_draft', table_name='campaign_publish_log')
    op.drop_index('ix_campaign_publish_log_tenant_time', table_name='campaign_publish_log')
    op.drop_table('campaign_publish_log')

    op.drop_index('ix_campaign_draft_platform', table_name='campaign_draft')
    op.drop_index('ix_campaign_draft_tenant_status', table_name='campaign_draft')
    op.drop_table('campaign_draft')

    op.drop_index('ix_tenant_ad_account_enabled', table_name='tenant_ad_account')
    op.drop_constraint('uq_tenant_ad_account', 'tenant_ad_account', type_='unique')
    op.drop_table('tenant_ad_account')

    op.drop_index('ix_tenant_platform_connection_tenant_platform', table_name='tenant_platform_connection')
    op.drop_constraint('uq_tenant_platform_connection', 'tenant_platform_connection', type_='unique')
    op.drop_table('tenant_platform_connection')
