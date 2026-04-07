"""Add CRM Integration tables (HubSpot, Attribution, Pipeline)

Revision ID: 013_add_crm_integration_tables
Revises: 012_add_ml_prediction_columns
Create Date: 2026-01-06 00:00:00.000000

This migration adds:
- crm_connections: OAuth connections to CRM providers (HubSpot, Salesforce)
- crm_contacts: Synced contacts with identity matching fields
- crm_deals: Synced deals with attribution
- touchpoints: Ad touchpoints for multi-touch attribution
- daily_pipeline_metrics: Aggregated pipeline/revenue metrics
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_crm_integration'
down_revision = '012_add_ml_prediction_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # CRM Provider Enum
    # ==========================================================================
    crm_provider = postgresql.ENUM(
        'hubspot', 'salesforce', 'pipedrive', 'zoho',
        name='crm_provider',
        create_type=False
    )
    crm_provider.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # CRM Connection Status Enum
    # ==========================================================================
    crm_connection_status = postgresql.ENUM(
        'pending', 'connected', 'expired', 'revoked', 'error',
        name='crm_connection_status',
        create_type=False
    )
    crm_connection_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Deal Stage Enum
    # ==========================================================================
    deal_stage = postgresql.ENUM(
        'lead', 'mql', 'sql', 'opportunity', 'proposal', 'negotiation', 'won', 'lost',
        name='deal_stage',
        create_type=False
    )
    deal_stage.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Attribution Model Enum
    # ==========================================================================
    attribution_model = postgresql.ENUM(
        'last_touch', 'first_touch', 'linear', 'position_based', 'time_decay', 'data_driven',
        name='attribution_model',
        create_type=False
    )
    attribution_model.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # crm_connections - OAuth connections to CRM providers
    # ==========================================================================
    op.create_table(
        'crm_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Provider details
        sa.Column('provider', crm_provider, nullable=False),
        sa.Column('provider_account_id', sa.String(255), nullable=True),
        sa.Column('provider_account_name', sa.String(255), nullable=True),

        # OAuth tokens (encrypted)
        sa.Column('access_token_enc', sa.Text(), nullable=True),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),

        # Scopes granted
        sa.Column('scopes', sa.Text(), nullable=True),

        # Connection status
        sa.Column('status', crm_connection_status, nullable=False, server_default='pending'),
        sa.Column('status_message', sa.Text(), nullable=True),

        # Sync configuration
        sa.Column('sync_contacts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_deals', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_companies', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('webhook_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('webhook_secret', sa.String(255), nullable=True),

        # Sync tracking
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(50), nullable=True),
        sa.Column('last_sync_contacts_count', sa.Integer(), server_default='0'),
        sa.Column('last_sync_deals_count', sa.Integer(), server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_crm_connections_tenant_provider', 'crm_connections', ['tenant_id', 'provider'])
    op.create_index('ix_crm_connections_status', 'crm_connections', ['status'])

    # ==========================================================================
    # crm_contacts - Synced contacts with identity matching
    # ==========================================================================
    op.create_table(
        'crm_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),

        # CRM identifiers
        sa.Column('crm_contact_id', sa.String(255), nullable=False),
        sa.Column('crm_owner_id', sa.String(255), nullable=True),

        # Identity matching (hashed for privacy)
        sa.Column('email_hash', sa.String(64), nullable=True),
        sa.Column('phone_hash', sa.String(64), nullable=True),

        # UTM parameters
        sa.Column('utm_source', sa.String(255), nullable=True),
        sa.Column('utm_medium', sa.String(255), nullable=True),
        sa.Column('utm_campaign', sa.String(255), nullable=True),
        sa.Column('utm_content', sa.String(255), nullable=True),
        sa.Column('utm_term', sa.String(255), nullable=True),

        # Click IDs
        sa.Column('gclid', sa.String(255), nullable=True),
        sa.Column('fbclid', sa.String(255), nullable=True),
        sa.Column('ttclid', sa.String(255), nullable=True),
        sa.Column('sclid', sa.String(255), nullable=True),
        sa.Column('msclkid', sa.String(255), nullable=True),

        # Visitor IDs
        sa.Column('ga_client_id', sa.String(255), nullable=True),
        sa.Column('stratum_visitor_id', sa.String(255), nullable=True),

        # Lifecycle tracking
        sa.Column('lifecycle_stage', sa.String(100), nullable=True),
        sa.Column('lead_source', sa.String(255), nullable=True),

        # Attribution (computed)
        sa.Column('first_touch_campaign_id', sa.String(255), nullable=True),
        sa.Column('last_touch_campaign_id', sa.String(255), nullable=True),
        sa.Column('first_touch_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_touch_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('touch_count', sa.Integer(), server_default='0'),

        # Stratum quality score (optional writeback)
        sa.Column('stratum_quality_score', sa.Float(), nullable=True),

        # Raw CRM data
        sa.Column('raw_properties', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('crm_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('crm_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['crm_connections.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_crm_contacts_tenant_email', 'crm_contacts', ['tenant_id', 'email_hash'])
    op.create_index('ix_crm_contacts_tenant_phone', 'crm_contacts', ['tenant_id', 'phone_hash'])
    op.create_index('ix_crm_contacts_tenant_gclid', 'crm_contacts', ['tenant_id', 'gclid'])
    op.create_index('ix_crm_contacts_tenant_fbclid', 'crm_contacts', ['tenant_id', 'fbclid'])
    op.create_index('ix_crm_contacts_crm_id', 'crm_contacts', ['connection_id', 'crm_contact_id'])
    op.create_index('ix_crm_contacts_lifecycle', 'crm_contacts', ['tenant_id', 'lifecycle_stage'])

    # ==========================================================================
    # touchpoints - Ad touchpoints for attribution
    # ==========================================================================
    op.create_table(
        'touchpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Touchpoint timing
        sa.Column('event_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),

        # Platform/source
        sa.Column('source', sa.String(50), nullable=False),

        # Campaign hierarchy
        sa.Column('account_id', sa.String(255), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('campaign_name', sa.String(500), nullable=True),
        sa.Column('adset_id', sa.String(255), nullable=True),
        sa.Column('adset_name', sa.String(500), nullable=True),
        sa.Column('ad_id', sa.String(255), nullable=True),
        sa.Column('ad_name', sa.String(500), nullable=True),

        # UTM parameters
        sa.Column('utm_source', sa.String(255), nullable=True),
        sa.Column('utm_medium', sa.String(255), nullable=True),
        sa.Column('utm_campaign', sa.String(255), nullable=True),
        sa.Column('utm_content', sa.String(255), nullable=True),
        sa.Column('utm_term', sa.String(255), nullable=True),

        # Click IDs
        sa.Column('click_id', sa.String(255), nullable=True),
        sa.Column('gclid', sa.String(255), nullable=True),
        sa.Column('fbclid', sa.String(255), nullable=True),
        sa.Column('ttclid', sa.String(255), nullable=True),
        sa.Column('sclid', sa.String(255), nullable=True),

        # Identity signals
        sa.Column('email_hash', sa.String(64), nullable=True),
        sa.Column('phone_hash', sa.String(64), nullable=True),
        sa.Column('visitor_id', sa.String(255), nullable=True),
        sa.Column('ga_client_id', sa.String(255), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),

        # Device/geo context
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('country', sa.String(10), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),

        # Landing page
        sa.Column('landing_page_url', sa.Text(), nullable=True),
        sa.Column('referrer_url', sa.Text(), nullable=True),

        # Cost
        sa.Column('cost_cents', sa.BigInteger(), nullable=True),

        # Attribution flags
        sa.Column('is_first_touch', sa.Boolean(), server_default='false'),
        sa.Column('is_last_touch', sa.Boolean(), server_default='false'),
        sa.Column('is_converting_touch', sa.Boolean(), server_default='false'),

        # Position in journey
        sa.Column('touch_position', sa.Integer(), nullable=True),
        sa.Column('total_touches', sa.Integer(), nullable=True),

        # Attribution weight
        sa.Column('attribution_weight', sa.Float(), server_default='1.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_touchpoints_tenant_contact', 'touchpoints', ['tenant_id', 'contact_id'])
    op.create_index('ix_touchpoints_tenant_event_ts', 'touchpoints', ['tenant_id', 'event_ts'])
    op.create_index('ix_touchpoints_tenant_campaign', 'touchpoints', ['tenant_id', 'campaign_id'])
    op.create_index('ix_touchpoints_email_hash', 'touchpoints', ['tenant_id', 'email_hash'])
    op.create_index('ix_touchpoints_click_ids', 'touchpoints', ['tenant_id', 'gclid', 'fbclid', 'ttclid'])
    op.create_index('ix_touchpoints_visitor', 'touchpoints', ['tenant_id', 'visitor_id'])

    # ==========================================================================
    # crm_deals - Synced deals with attribution
    # ==========================================================================
    op.create_table(
        'crm_deals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),

        # CRM identifiers
        sa.Column('crm_deal_id', sa.String(255), nullable=False),
        sa.Column('crm_pipeline_id', sa.String(255), nullable=True),
        sa.Column('crm_owner_id', sa.String(255), nullable=True),

        # Deal details
        sa.Column('deal_name', sa.String(500), nullable=True),
        sa.Column('stage', sa.String(100), nullable=True),
        sa.Column('stage_normalized', deal_stage, nullable=True),

        # Financials
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('amount_cents', sa.BigInteger(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),

        # Dates
        sa.Column('close_date', sa.Date(), nullable=True),
        sa.Column('expected_close_date', sa.Date(), nullable=True),

        # Win/Loss tracking
        sa.Column('is_won', sa.Boolean(), server_default='false'),
        sa.Column('is_closed', sa.Boolean(), server_default='false'),
        sa.Column('won_at', sa.DateTime(timezone=True), nullable=True),

        # Attribution
        sa.Column('attributed_campaign_id', sa.String(255), nullable=True),
        sa.Column('attributed_adset_id', sa.String(255), nullable=True),
        sa.Column('attributed_ad_id', sa.String(255), nullable=True),
        sa.Column('attributed_platform', sa.String(50), nullable=True),
        sa.Column('attribution_model', attribution_model, server_default='last_touch'),
        sa.Column('attribution_confidence', sa.Float(), nullable=True),
        sa.Column('attributed_touchpoint_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Raw CRM data
        sa.Column('raw_properties', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('crm_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('crm_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['crm_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['attributed_touchpoint_id'], ['touchpoints.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_crm_deals_tenant_stage', 'crm_deals', ['tenant_id', 'stage_normalized'])
    op.create_index('ix_crm_deals_tenant_won', 'crm_deals', ['tenant_id', 'is_won'])
    op.create_index('ix_crm_deals_tenant_close_date', 'crm_deals', ['tenant_id', 'close_date'])
    op.create_index('ix_crm_deals_crm_id', 'crm_deals', ['connection_id', 'crm_deal_id'])
    op.create_index('ix_crm_deals_attributed_campaign', 'crm_deals', ['tenant_id', 'attributed_campaign_id'])

    # ==========================================================================
    # daily_pipeline_metrics - Aggregated pipeline/revenue metrics
    # ==========================================================================
    op.create_table(
        'daily_pipeline_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),

        # Dimension
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),

        # Ad platform metrics
        sa.Column('spend_cents', sa.BigInteger(), server_default='0'),
        sa.Column('impressions', sa.BigInteger(), server_default='0'),
        sa.Column('clicks', sa.BigInteger(), server_default='0'),
        sa.Column('platform_conversions', sa.Integer(), server_default='0'),
        sa.Column('platform_revenue_cents', sa.BigInteger(), server_default='0'),

        # CRM pipeline metrics
        sa.Column('leads_created', sa.Integer(), server_default='0'),
        sa.Column('mqls_created', sa.Integer(), server_default='0'),
        sa.Column('sqls_created', sa.Integer(), server_default='0'),
        sa.Column('opportunities_created', sa.Integer(), server_default='0'),

        # Pipeline value
        sa.Column('pipeline_value_cents', sa.BigInteger(), server_default='0'),
        sa.Column('pipeline_deal_count', sa.Integer(), server_default='0'),

        # Won deals
        sa.Column('deals_won', sa.Integer(), server_default='0'),
        sa.Column('won_revenue_cents', sa.BigInteger(), server_default='0'),

        # Lost deals
        sa.Column('deals_lost', sa.Integer(), server_default='0'),
        sa.Column('lost_value_cents', sa.BigInteger(), server_default='0'),

        # Computed ROAS metrics
        sa.Column('platform_roas', sa.Float(), nullable=True),
        sa.Column('pipeline_roas', sa.Float(), nullable=True),
        sa.Column('won_roas', sa.Float(), nullable=True),

        # Funnel conversion rates
        sa.Column('lead_to_mql_rate', sa.Float(), nullable=True),
        sa.Column('mql_to_sql_rate', sa.Float(), nullable=True),
        sa.Column('sql_to_won_rate', sa.Float(), nullable=True),

        # CAC metrics
        sa.Column('cac_cents', sa.BigInteger(), nullable=True),

        # Time-to-close
        sa.Column('avg_time_to_close_days', sa.Float(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_daily_pipeline_metrics_tenant_date', 'daily_pipeline_metrics', ['tenant_id', 'date'])
    op.create_index('ix_daily_pipeline_metrics_tenant_platform', 'daily_pipeline_metrics', ['tenant_id', 'platform', 'date'])
    op.create_index('ix_daily_pipeline_metrics_tenant_campaign', 'daily_pipeline_metrics', ['tenant_id', 'campaign_id', 'date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('daily_pipeline_metrics')
    op.drop_table('crm_deals')
    op.drop_table('touchpoints')
    op.drop_table('crm_contacts')
    op.drop_table('crm_connections')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS attribution_model')
    op.execute('DROP TYPE IF EXISTS deal_stage')
    op.execute('DROP TYPE IF EXISTS crm_connection_status')
    op.execute('DROP TYPE IF EXISTS crm_provider')
