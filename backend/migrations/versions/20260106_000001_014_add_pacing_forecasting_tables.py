# =============================================================================
# Stratum AI - Migration: Add Pacing & Forecasting Tables
# =============================================================================
"""
Add pacing and forecasting tables.

Revision ID: 014_add_pacing_forecasting
Revises: 013_add_crm_integration_tables
Create Date: 2026-01-06

Tables:
- targets: Monthly/quarterly targets for spend, revenue, ROAS
- daily_kpis: Materialized daily KPIs for fast pacing queries
- pacing_alerts: Alert records for pacing issues
- forecasts: Stored forecasts for trend analysis
- pacing_summaries: Pacing summary snapshots
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '014_add_pacing_forecasting'
down_revision = '013_add_crm_integration_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE target_period AS ENUM ('monthly', 'quarterly', 'yearly', 'custom');
    """)

    op.execute("""
        CREATE TYPE target_metric AS ENUM (
            'spend', 'revenue', 'roas', 'conversions', 'leads',
            'pipeline_value', 'won_revenue', 'cpa', 'cpl'
        );
    """)

    op.execute("""
        CREATE TYPE alert_severity AS ENUM ('info', 'warning', 'critical');
    """)

    op.execute("""
        CREATE TYPE alert_type AS ENUM (
            'underpacing_spend', 'overpacing_spend', 'roas_below_target',
            'conversions_below_target', 'revenue_below_target',
            'pipeline_below_target', 'pacing_cliff', 'budget_exhaustion'
        );
    """)

    op.execute("""
        CREATE TYPE alert_status AS ENUM ('active', 'acknowledged', 'resolved', 'dismissed');
    """)

    # Create targets table
    op.create_table(
        'targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Target identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Period
        sa.Column('period_type', postgresql.ENUM('monthly', 'quarterly', 'yearly', 'custom', name='target_period', create_type=False), nullable=False, server_default='monthly'),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('adset_id', sa.String(255), nullable=True),

        # Target metrics
        sa.Column('metric_type', postgresql.ENUM('spend', 'revenue', 'roas', 'conversions', 'leads', 'pipeline_value', 'won_revenue', 'cpa', 'cpl', name='target_metric', create_type=False), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('target_value_cents', sa.BigInteger(), nullable=True),

        # Bounds
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),

        # Alert thresholds
        sa.Column('warning_threshold_pct', sa.Float(), server_default='10.0'),
        sa.Column('critical_threshold_pct', sa.Float(), server_default='20.0'),

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),

        # Notification settings
        sa.Column('notify_slack', sa.Boolean(), server_default='true'),
        sa.Column('notify_email', sa.Boolean(), server_default='true'),
        sa.Column('notify_whatsapp', sa.Boolean(), server_default='false'),
        sa.Column('notification_recipients', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Constraints
        sa.UniqueConstraint('tenant_id', 'period_start', 'period_end', 'metric_type', 'platform', 'campaign_id', name='uq_target_scope'),
    )

    op.create_index('ix_targets_tenant_period', 'targets', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('ix_targets_tenant_metric', 'targets', ['tenant_id', 'metric_type'])
    op.create_index('ix_targets_tenant_active', 'targets', ['tenant_id', 'is_active'])

    # Create daily_kpis table
    op.create_table(
        'daily_kpis',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('account_id', sa.String(255), nullable=True),

        # Spend metrics
        sa.Column('spend_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('budget_cents', sa.BigInteger(), nullable=True),

        # Traffic metrics
        sa.Column('impressions', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('clicks', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('ctr', sa.Float(), nullable=True),

        # Cost metrics
        sa.Column('cpm_cents', sa.BigInteger(), nullable=True),
        sa.Column('cpc_cents', sa.BigInteger(), nullable=True),
        sa.Column('cpa_cents', sa.BigInteger(), nullable=True),
        sa.Column('cpl_cents', sa.BigInteger(), nullable=True),

        # Conversion metrics
        sa.Column('conversions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('leads', sa.Integer(), server_default='0', nullable=False),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=False),

        # Revenue metrics
        sa.Column('revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('roas', sa.Float(), nullable=True),

        # CRM metrics
        sa.Column('crm_leads', sa.Integer(), server_default='0', nullable=False),
        sa.Column('crm_mqls', sa.Integer(), server_default='0', nullable=False),
        sa.Column('crm_sqls', sa.Integer(), server_default='0', nullable=False),
        sa.Column('crm_opportunities', sa.Integer(), server_default='0', nullable=False),
        sa.Column('crm_deals_won', sa.Integer(), server_default='0', nullable=False),
        sa.Column('crm_pipeline_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('crm_won_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Computed CRM ROAS
        sa.Column('pipeline_roas', sa.Float(), nullable=True),
        sa.Column('won_roas', sa.Float(), nullable=True),

        # Quality metrics
        sa.Column('frequency', sa.Float(), nullable=True),
        sa.Column('emq_score', sa.Float(), nullable=True),

        # Day of week
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('is_weekend', sa.Boolean(), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('tenant_id', 'date', 'platform', 'campaign_id', name='uq_daily_kpi_scope'),
    )

    op.create_index('ix_daily_kpis_tenant_date', 'daily_kpis', ['tenant_id', 'date'])
    op.create_index('ix_daily_kpis_tenant_platform_date', 'daily_kpis', ['tenant_id', 'platform', 'date'])
    op.create_index('ix_daily_kpis_tenant_campaign_date', 'daily_kpis', ['tenant_id', 'campaign_id', 'date'])

    # Create pacing_alerts table
    op.create_table(
        'pacing_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('targets.id', ondelete='CASCADE'), nullable=True),

        # Alert details
        sa.Column('alert_type', postgresql.ENUM('underpacing_spend', 'overpacing_spend', 'roas_below_target', 'conversions_below_target', 'revenue_below_target', 'pipeline_below_target', 'pacing_cliff', 'budget_exhaustion', name='alert_type', create_type=False), nullable=False),
        sa.Column('severity', postgresql.ENUM('info', 'warning', 'critical', name='alert_severity', create_type=False), nullable=False, server_default='warning'),
        sa.Column('status', postgresql.ENUM('active', 'acknowledged', 'resolved', 'dismissed', name='alert_status', create_type=False), nullable=False, server_default='active'),

        # Alert message
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),

        # Metrics at time of alert
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('projected_value', sa.Float(), nullable=True),
        sa.Column('deviation_pct', sa.Float(), nullable=True),

        # Pacing context
        sa.Column('pacing_date', sa.Date(), nullable=False),
        sa.Column('days_remaining', sa.Integer(), nullable=True),
        sa.Column('mtd_actual', sa.Float(), nullable=True),
        sa.Column('mtd_expected', sa.Float(), nullable=True),
        sa.Column('projected_eom', sa.Float(), nullable=True),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),

        # Resolution
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),

        # Notification tracking
        sa.Column('notifications_sent', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_pacing_alerts_tenant_status', 'pacing_alerts', ['tenant_id', 'status'])
    op.create_index('ix_pacing_alerts_tenant_date', 'pacing_alerts', ['tenant_id', 'pacing_date'])
    op.create_index('ix_pacing_alerts_tenant_type', 'pacing_alerts', ['tenant_id', 'alert_type'])
    op.create_index('ix_pacing_alerts_target', 'pacing_alerts', ['target_id'])

    # Create forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Forecast metadata
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('forecast_for_date', sa.Date(), nullable=False),
        sa.Column('forecast_type', sa.String(50), nullable=False),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),

        # Metric being forecasted
        sa.Column('metric_type', postgresql.ENUM('spend', 'revenue', 'roas', 'conversions', 'leads', 'pipeline_value', 'won_revenue', 'cpa', 'cpl', name='target_metric', create_type=False), nullable=False),

        # Forecast values
        sa.Column('forecasted_value', sa.Float(), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=True),
        sa.Column('confidence_upper', sa.Float(), nullable=True),
        sa.Column('confidence_level', sa.Float(), server_default='0.9'),

        # Model info
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('model_params', postgresql.JSONB(), nullable=True),

        # Accuracy tracking
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('error', sa.Float(), nullable=True),
        sa.Column('error_pct', sa.Float(), nullable=True),
        sa.Column('mape', sa.Float(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_forecasts_tenant_date', 'forecasts', ['tenant_id', 'forecast_date'])
    op.create_index('ix_forecasts_tenant_for_date', 'forecasts', ['tenant_id', 'forecast_for_date'])
    op.create_index('ix_forecasts_tenant_metric', 'forecasts', ['tenant_id', 'metric_type'])

    # Create pacing_summaries table
    op.create_table(
        'pacing_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('targets.id', ondelete='CASCADE'), nullable=False),

        # Snapshot date
        sa.Column('snapshot_date', sa.Date(), nullable=False),

        # Period info
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('days_elapsed', sa.Integer(), nullable=False),
        sa.Column('days_remaining', sa.Integer(), nullable=False),
        sa.Column('days_total', sa.Integer(), nullable=False),

        # Progress
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('mtd_actual', sa.Float(), nullable=False),
        sa.Column('mtd_expected', sa.Float(), nullable=False),

        # Pacing metrics
        sa.Column('pacing_pct', sa.Float(), nullable=False),
        sa.Column('completion_pct', sa.Float(), nullable=False),

        # Projections
        sa.Column('projected_eom', sa.Float(), nullable=True),
        sa.Column('projected_eom_lower', sa.Float(), nullable=True),
        sa.Column('projected_eom_upper', sa.Float(), nullable=True),

        # Gap analysis
        sa.Column('gap_to_target', sa.Float(), nullable=True),
        sa.Column('gap_pct', sa.Float(), nullable=True),

        # Daily metrics
        sa.Column('daily_needed', sa.Float(), nullable=True),
        sa.Column('daily_average', sa.Float(), nullable=True),

        # Status flags
        sa.Column('on_track', sa.Boolean(), nullable=False),
        sa.Column('at_risk', sa.Boolean(), nullable=False),
        sa.Column('will_miss', sa.Boolean(), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('target_id', 'snapshot_date', name='uq_pacing_summary_target_date'),
    )

    op.create_index('ix_pacing_summaries_tenant_date', 'pacing_summaries', ['tenant_id', 'snapshot_date'])
    op.create_index('ix_pacing_summaries_target', 'pacing_summaries', ['target_id', 'snapshot_date'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('pacing_summaries')
    op.drop_table('forecasts')
    op.drop_table('pacing_alerts')
    op.drop_table('daily_kpis')
    op.drop_table('targets')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS alert_status')
    op.execute('DROP TYPE IF EXISTS alert_type')
    op.execute('DROP TYPE IF EXISTS alert_severity')
    op.execute('DROP TYPE IF EXISTS target_metric')
    op.execute('DROP TYPE IF EXISTS target_period')
