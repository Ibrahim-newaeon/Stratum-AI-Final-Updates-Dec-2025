# =============================================================================
# Stratum AI - Analytics Warehouse Schema Migration
# =============================================================================
"""
Add analytics warehouse tables for AI-powered insights.

Based on Data_Schema_Events_and_Tables.md and schema.sql from the
claude_code_analytics_docs_pack.

Revision ID: 008
Revises: 002
Create Date: 2024-12-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '008'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Dimension Tables
    # =========================================================================

    # dim_platform - Advertising platforms
    op.create_table(
        'dim_platform',
        sa.Column('platform', sa.String(20), primary_key=True),
        sa.Column('platform_name', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed platform data
    op.execute("""
        INSERT INTO dim_platform (platform, platform_name) VALUES
        ('meta', 'Meta Ads'),
        ('google', 'Google Ads'),
        ('tiktok', 'TikTok Ads'),
        ('snap', 'Snapchat Ads'),
        ('linkedin', 'LinkedIn Ads')
        ON CONFLICT (platform) DO NOTHING
    """)

    # dim_creative - Creative asset dimensions
    op.create_table(
        'dim_creative',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('creative_id', sa.String(100), nullable=False),
        sa.Column('creative_name', sa.String(255)),
        sa.Column('format', sa.String(50)),  # video/static/ugc
        sa.Column('hook_tag', sa.String(100)),
        sa.Column('created_time', sa.DateTime(timezone=True)),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('platform', 'creative_id', 'tenant_id', name='uq_dim_creative'),
    )
    op.create_index('ix_dim_creative_tenant', 'dim_creative', ['tenant_id'])

    # =========================================================================
    # Fact Tables
    # =========================================================================

    # fact_platform_daily - Platform-reported KPIs (daily)
    op.create_table(
        'fact_platform_daily',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('account_id', sa.String(100)),
        sa.Column('campaign_id', sa.String(100)),
        sa.Column('adgroup_id', sa.String(100)),
        sa.Column('ad_id', sa.String(100)),
        sa.Column('creative_id', sa.String(100)),

        # Core metrics
        sa.Column('spend', sa.Float, default=0),
        sa.Column('impressions', sa.BigInteger, default=0),
        sa.Column('clicks', sa.BigInteger, default=0),
        sa.Column('conversions', sa.BigInteger, default=0),
        sa.Column('revenue', sa.Float, default=0),

        # Computed metrics
        sa.Column('ctr', sa.Float),
        sa.Column('cvr', sa.Float),
        sa.Column('cpm', sa.Float),
        sa.Column('cpc', sa.Float),
        sa.Column('cpa', sa.Float),
        sa.Column('roas', sa.Float),
        sa.Column('frequency', sa.Float),

        # Metadata
        sa.Column('reporting_window', sa.String(50)),  # e.g., "1d_click_1d_view"
        sa.Column('ingestion_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_fact_platform_daily_date', 'fact_platform_daily', ['date', 'tenant_id'])
    op.create_index('ix_fact_platform_daily_campaign', 'fact_platform_daily', ['campaign_id', 'date'])

    # fact_ga4_daily - GA4 aligned KPIs (daily)
    op.create_table(
        'fact_ga4_daily',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('account_id', sa.String(100)),
        sa.Column('source_platform', sa.String(20)),  # inferred meta/google/tiktok/snap
        sa.Column('utm_campaign', sa.String(255)),
        sa.Column('utm_content', sa.String(255)),
        sa.Column('gclid', sa.String(255)),
        sa.Column('fbclid', sa.String(255)),

        # GA4 metrics
        sa.Column('sessions', sa.BigInteger, default=0),
        sa.Column('add_to_cart', sa.BigInteger, default=0),
        sa.Column('begin_checkout', sa.BigInteger, default=0),
        sa.Column('purchases', sa.BigInteger, default=0),
        sa.Column('revenue', sa.Float, default=0),
        sa.Column('leads', sa.BigInteger, default=0),

        sa.Column('ingestion_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_fact_ga4_daily_date', 'fact_ga4_daily', ['date', 'tenant_id'])

    # fact_creative_daily - Creative metrics + computed fatigue
    op.create_table(
        'fact_creative_daily',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('account_id', sa.String(100)),
        sa.Column('campaign_id', sa.String(100)),
        sa.Column('ad_id', sa.String(100)),
        sa.Column('creative_id', sa.String(100)),

        # Core metrics
        sa.Column('spend', sa.Float, default=0),
        sa.Column('impressions', sa.BigInteger, default=0),
        sa.Column('clicks', sa.BigInteger, default=0),
        sa.Column('conversions', sa.BigInteger, default=0),
        sa.Column('revenue', sa.Float, default=0),

        # Computed metrics
        sa.Column('ctr', sa.Float),
        sa.Column('cvr', sa.Float),
        sa.Column('cpa', sa.Float),
        sa.Column('roas', sa.Float),
        sa.Column('frequency', sa.Float),

        # Fatigue tracking
        sa.Column('fatigue_score', sa.Float),  # 0..1
        sa.Column('fatigue_state', sa.String(20)),  # healthy/watch/refresh

        sa.Column('ingestion_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_fact_creative_daily_date', 'fact_creative_daily', ['date', 'tenant_id'])
    op.create_index('ix_fact_creative_daily_creative', 'fact_creative_daily', ['creative_id', 'date'])

    # fact_alerts - Anomalies + system alerts
    op.create_table(
        'fact_alerts',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('platform', sa.String(20)),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('account_id', sa.String(100)),

        # Alert info
        sa.Column('alert_type', sa.String(50), nullable=False),  # roas_alert, emq_degraded, anomaly
        sa.Column('severity', sa.String(20), nullable=False),  # low/medium/high/critical
        sa.Column('entity_level', sa.String(50)),  # campaign/adset/ad/creative
        sa.Column('entity_id', sa.String(100)),

        # Alert details
        sa.Column('metric', sa.String(50)),
        sa.Column('current_value', sa.Float),
        sa.Column('baseline_value', sa.Float),
        sa.Column('zscore', sa.Float),
        sa.Column('message', sa.Text),

        # Resolution
        sa.Column('resolved', sa.Boolean, default=False),
        sa.Column('resolved_time', sa.DateTime(timezone=True)),
        sa.Column('resolved_by', sa.String(100)),
        sa.Column('acknowledged', sa.Boolean, default=False),
        sa.Column('acknowledged_time', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_fact_alerts_tenant_date', 'fact_alerts', ['tenant_id', 'date'])
    op.create_index('ix_fact_alerts_unresolved', 'fact_alerts', ['tenant_id', 'resolved'])

    # fact_scaling_scores - Daily scaling scores for entities
    op.create_table(
        'fact_scaling_scores',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('platform', sa.String(20)),
        sa.Column('entity_level', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('entity_name', sa.String(255)),

        # Score details
        sa.Column('score', sa.Float, nullable=False),  # -1 to +1
        sa.Column('action', sa.String(20)),  # scale/watch/fix/pause
        sa.Column('roas_delta', sa.Float),
        sa.Column('cpa_delta', sa.Float),
        sa.Column('cvr_delta', sa.Float),
        sa.Column('ctr_delta', sa.Float),
        sa.Column('freq_penalty', sa.Float),
        sa.Column('emq_penalty', sa.Float),
        sa.Column('vol_penalty', sa.Float),

        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_fact_scaling_scores_date', 'fact_scaling_scores', ['date', 'tenant_id'])
    op.create_index('ix_fact_scaling_scores_entity', 'fact_scaling_scores', ['entity_id', 'date'])

    # fact_budget_actions - Budget reallocation actions
    op.create_table(
        'fact_budget_actions',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('entity_name', sa.String(255)),

        sa.Column('action', sa.String(30)),  # increase_budget / decrease_budget
        sa.Column('amount', sa.Float),
        sa.Column('current_spend', sa.Float),
        sa.Column('scaling_score', sa.Float),
        sa.Column('reason', sa.Text),

        # Execution tracking
        sa.Column('status', sa.String(20), default='pending'),  # pending/executed/cancelled
        sa.Column('executed_at', sa.DateTime(timezone=True)),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_fact_budget_actions_date', 'fact_budget_actions', ['date', 'tenant_id'])


def downgrade():
    op.drop_table('fact_budget_actions')
    op.drop_table('fact_scaling_scores')
    op.drop_table('fact_alerts')
    op.drop_table('fact_creative_daily')
    op.drop_table('fact_ga4_daily')
    op.drop_table('fact_platform_daily')
    op.drop_table('dim_creative')
    op.drop_table('dim_platform')
