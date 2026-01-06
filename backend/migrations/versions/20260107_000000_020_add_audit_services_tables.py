"""Add audit services tables

Revision ID: 020_audit_services
Revises: 019_automated_reporting
Create Date: 2026-01-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '020_audit_services'
down_revision = '019_automated_reporting'
branch_labels = None
depends_on = None


def upgrade():
    # EMQ Measurements
    op.create_table(
        'emq_measurements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('pixel_id', sa.String(255), nullable=False),
        sa.Column('measurement_date', sa.Date(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('parameter_quality', sa.Float(), nullable=True),
        sa.Column('deduplication_quality', sa.Float(), nullable=True),
        sa.Column('event_coverage', sa.Float(), nullable=True),
        sa.Column('events_received', sa.Integer(), default=0, nullable=False),
        sa.Column('events_matched', sa.Integer(), default=0, nullable=False),
        sa.Column('events_attributed', sa.Integer(), default=0, nullable=False),
        sa.Column('email_match_rate', sa.Float(), nullable=True),
        sa.Column('phone_match_rate', sa.Float(), nullable=True),
        sa.Column('combined_match_rate', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emq_tenant_date', 'emq_measurements', ['tenant_id', 'measurement_date'])
    op.create_index('ix_emq_platform', 'emq_measurements', ['tenant_id', 'platform', 'pixel_id'])

    # Offline Conversion Batches
    op.create_table(
        'offline_conversion_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('batch_name', sa.String(255), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('upload_type', sa.String(50), nullable=False),
        sa.Column('total_records', sa.Integer(), default=0, nullable=False),
        sa.Column('successful_records', sa.Integer(), default=0, nullable=False),
        sa.Column('failed_records', sa.Integer(), default=0, nullable=False),
        sa.Column('duplicate_records', sa.Integer(), default=0, nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('platform_batch_id', sa.String(255), nullable=True),
        sa.Column('platform_response', postgresql.JSONB(), nullable=True),
        sa.Column('source_file', sa.String(500), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_offline_batch_tenant', 'offline_conversion_batches', ['tenant_id', 'created_at'])
    op.create_index('ix_offline_batch_status', 'offline_conversion_batches', ['tenant_id', 'status'])

    # Offline Conversions
    op.create_table(
        'offline_conversions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value_cents', sa.BigInteger(), nullable=True),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('email_hash', sa.String(64), nullable=True),
        sa.Column('phone_hash', sa.String(64), nullable=True),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('click_id', sa.String(255), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_event_id', sa.String(255), nullable=True),
        sa.Column('uploaded', sa.Boolean(), default=False, nullable=False),
        sa.Column('upload_attempts', sa.Integer(), default=0, nullable=False),
        sa.Column('last_upload_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['batch_id'], ['offline_conversion_batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_offline_conv_tenant', 'offline_conversions', ['tenant_id', 'event_time'])
    op.create_index('ix_offline_conv_batch', 'offline_conversions', ['batch_id'])
    op.create_index('ix_offline_conv_uploaded', 'offline_conversions', ['tenant_id', 'uploaded'])

    # Model Experiments
    op.create_table(
        'model_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('champion_version', sa.String(50), nullable=False),
        sa.Column('challenger_version', sa.String(50), nullable=False),
        sa.Column('traffic_split', sa.Float(), default=0.1, nullable=False),
        sa.Column('status', sa.String(20), default='draft', nullable=False),
        sa.Column('min_samples', sa.Integer(), default=1000, nullable=False),
        sa.Column('significance_threshold', sa.Float(), default=0.05, nullable=False),
        sa.Column('primary_metric', sa.String(50), default='mae', nullable=False),
        sa.Column('champion_predictions', sa.Integer(), default=0, nullable=False),
        sa.Column('challenger_predictions', sa.Integer(), default=0, nullable=False),
        sa.Column('champion_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('challenger_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('winner', sa.String(20), nullable=True),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('effect_size', sa.Float(), nullable=True),
        sa.Column('confidence_interval', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_exp_tenant', 'model_experiments', ['tenant_id'])
    op.create_index('ix_model_exp_status', 'model_experiments', ['tenant_id', 'status'])
    op.create_index('ix_model_exp_model', 'model_experiments', ['tenant_id', 'model_name'])

    # Experiment Predictions
    op.create_table(
        'experiment_predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('variant', sa.String(20), nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['model_experiments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_exp_pred_experiment', 'experiment_predictions', ['experiment_id'])
    op.create_index('ix_exp_pred_variant', 'experiment_predictions', ['experiment_id', 'variant'])

    # Conversion Latencies
    op.create_table(
        'conversion_latencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conv_latency_tenant', 'conversion_latencies', ['tenant_id', 'event_time'])
    op.create_index('ix_conv_latency_platform', 'conversion_latencies', ['tenant_id', 'platform', 'event_type'])

    # Conversion Latency Stats
    op.create_table(
        'conversion_latency_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('period_date', sa.Date(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_count', sa.Integer(), default=0, nullable=False),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('median_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('p99_latency_ms', sa.Float(), nullable=True),
        sa.Column('min_latency_ms', sa.Integer(), nullable=True),
        sa.Column('max_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_latency_stats_tenant', 'conversion_latency_stats', ['tenant_id', 'period_date'])

    # Creatives
    op.create_table(
        'creatives',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('name', sa.String(500), nullable=True),
        sa.Column('creative_type', sa.String(50), nullable=True),
        sa.Column('asset_url', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_creative_tenant', 'creatives', ['tenant_id'])
    op.create_index('ix_creative_external', 'creatives', ['tenant_id', 'platform', 'external_id'])

    # Creative Performance
    op.create_table(
        'creative_performance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creative_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('impressions', sa.Integer(), default=0, nullable=False),
        sa.Column('clicks', sa.Integer(), default=0, nullable=False),
        sa.Column('conversions', sa.Integer(), default=0, nullable=False),
        sa.Column('spend_cents', sa.BigInteger(), default=0, nullable=False),
        sa.Column('revenue_cents', sa.BigInteger(), default=0, nullable=False),
        sa.Column('ctr', sa.Float(), nullable=True),
        sa.Column('cvr', sa.Float(), nullable=True),
        sa.Column('cpc_cents', sa.Integer(), nullable=True),
        sa.Column('cpm_cents', sa.Integer(), nullable=True),
        sa.Column('roas', sa.Float(), nullable=True),
        sa.Column('video_views', sa.Integer(), default=0, nullable=False),
        sa.Column('video_completions', sa.Integer(), default=0, nullable=False),
        sa.Column('engagements', sa.Integer(), default=0, nullable=False),
        sa.Column('shares', sa.Integer(), default=0, nullable=False),
        sa.Column('frequency', sa.Float(), nullable=True),
        sa.Column('reach', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['creative_id'], ['creatives.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_creative_perf_tenant', 'creative_performance', ['tenant_id', 'date'])
    op.create_index('ix_creative_perf_creative', 'creative_performance', ['creative_id', 'date'])

    # Creative Fatigue Alerts
    op.create_table(
        'creative_fatigue_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creative_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('current_ctr', sa.Float(), nullable=True),
        sa.Column('baseline_ctr', sa.Float(), nullable=True),
        sa.Column('ctr_decline_percent', sa.Float(), nullable=True),
        sa.Column('current_frequency', sa.Float(), nullable=True),
        sa.Column('days_active', sa.Integer(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), default=False, nullable=False),
        sa.Column('acknowledged_by_user_id', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['creative_id'], ['creatives.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['acknowledged_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fatigue_alert_tenant', 'creative_fatigue_alerts', ['tenant_id', 'created_at'])
    op.create_index('ix_fatigue_alert_creative', 'creative_fatigue_alerts', ['creative_id'])

    # Competitor Benchmarks
    op.create_table(
        'competitor_benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('industry', sa.String(100), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('your_metrics', postgresql.JSONB(), nullable=False),
        sa.Column('industry_metrics', postgresql.JSONB(), nullable=False),
        sa.Column('percentile_rankings', postgresql.JSONB(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('metrics_above_median', sa.Integer(), default=0, nullable=False),
        sa.Column('metrics_below_median', sa.Integer(), default=0, nullable=False),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_benchmark_tenant', 'competitor_benchmarks', ['tenant_id', 'date'])
    op.create_index('ix_benchmark_industry', 'competitor_benchmarks', ['tenant_id', 'industry', 'platform'])

    # Budget Reallocation Plans
    op.create_table(
        'budget_reallocation_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('total_current_budget_cents', sa.BigInteger(), nullable=False),
        sa.Column('total_new_budget_cents', sa.BigInteger(), nullable=False),
        sa.Column('campaigns_affected', sa.Integer(), default=0, nullable=False),
        sa.Column('projected_roas_change', sa.Float(), nullable=True),
        sa.Column('projected_spend_change', sa.Float(), nullable=True),
        sa.Column('projected_revenue_change', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), default='proposed', nullable=False),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rolled_back_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_realloc_plan_tenant', 'budget_reallocation_plans', ['tenant_id', 'created_at'])
    op.create_index('ix_realloc_plan_status', 'budget_reallocation_plans', ['tenant_id', 'status'])

    # Budget Reallocation Changes
    op.create_table(
        'budget_reallocation_changes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', sa.String(255), nullable=False),
        sa.Column('campaign_name', sa.String(500), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('current_budget_cents', sa.BigInteger(), nullable=False),
        sa.Column('new_budget_cents', sa.BigInteger(), nullable=False),
        sa.Column('change_percent', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('performance_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('executed', sa.Boolean(), default=False, nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['budget_reallocation_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_realloc_change_plan', 'budget_reallocation_changes', ['plan_id'])

    # Audience Records
    op.create_table(
        'audience_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('audience_type', sa.String(50), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('lookalike_percent', sa.Float(), nullable=True),
        sa.Column('source_audience_id', sa.String(255), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('expansion_potential', sa.String(20), nullable=True),
        sa.Column('current_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('historical_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('avg_ltv', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audience_tenant', 'audience_records', ['tenant_id'])
    op.create_index('ix_audience_external', 'audience_records', ['tenant_id', 'platform', 'external_id'])

    # Audience Overlaps
    op.create_table(
        'audience_overlaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('audience_id_1', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audience_id_2', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('overlap_percent', sa.Float(), nullable=False),
        sa.Column('overlap_size', sa.Integer(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audience_id_1'], ['audience_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audience_id_2'], ['audience_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_overlap_tenant', 'audience_overlaps', ['tenant_id'])
    op.create_index('ix_overlap_audiences', 'audience_overlaps', ['audience_id_1', 'audience_id_2'])

    # Customer LTV Predictions
    op.create_table(
        'customer_ltv_predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.String(255), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('acquisition_date', sa.Date(), nullable=True),
        sa.Column('acquisition_channel', sa.String(100), nullable=True),
        sa.Column('total_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('total_revenue_cents', sa.BigInteger(), default=0, nullable=False),
        sa.Column('avg_order_value_cents', sa.Integer(), nullable=True),
        sa.Column('days_since_last_order', sa.Integer(), nullable=True),
        sa.Column('predicted_ltv_30d_cents', sa.BigInteger(), nullable=True),
        sa.Column('predicted_ltv_90d_cents', sa.BigInteger(), nullable=True),
        sa.Column('predicted_ltv_365d_cents', sa.BigInteger(), nullable=True),
        sa.Column('predicted_ltv_lifetime_cents', sa.BigInteger(), nullable=True),
        sa.Column('segment', sa.String(20), nullable=True),
        sa.Column('churn_probability', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('max_cac_cents', sa.Integer(), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ltv_pred_tenant', 'customer_ltv_predictions', ['tenant_id', 'predicted_at'])
    op.create_index('ix_ltv_pred_customer', 'customer_ltv_predictions', ['tenant_id', 'customer_id'])
    op.create_index('ix_ltv_pred_segment', 'customer_ltv_predictions', ['tenant_id', 'segment'])

    # LTV Cohort Analyses
    op.create_table(
        'ltv_cohort_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('cohort_month', sa.String(7), nullable=False),
        sa.Column('customer_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_revenue_cents', sa.BigInteger(), default=0, nullable=False),
        sa.Column('avg_ltv_cents', sa.BigInteger(), nullable=True),
        sa.Column('median_ltv_cents', sa.BigInteger(), nullable=True),
        sa.Column('ltv_p90_cents', sa.BigInteger(), nullable=True),
        sa.Column('avg_orders', sa.Float(), nullable=True),
        sa.Column('avg_retention_days', sa.Float(), nullable=True),
        sa.Column('segment_distribution', postgresql.JSONB(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ltv_cohort_tenant', 'ltv_cohort_analyses', ['tenant_id'])

    # Model Retraining Jobs
    op.create_table(
        'model_retraining_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('trigger_reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('training_start_date', sa.Date(), nullable=True),
        sa.Column('training_end_date', sa.Date(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('old_version', sa.String(50), nullable=True),
        sa.Column('new_version', sa.String(50), nullable=True),
        sa.Column('old_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('new_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('improvement', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_retrain_job_tenant', 'model_retraining_jobs', ['tenant_id', 'created_at'])
    op.create_index('ix_retrain_job_model', 'model_retraining_jobs', ['model_name', 'created_at'])
    op.create_index('ix_retrain_job_status', 'model_retraining_jobs', ['status'])


def downgrade():
    op.drop_table('model_retraining_jobs')
    op.drop_table('ltv_cohort_analyses')
    op.drop_table('customer_ltv_predictions')
    op.drop_table('audience_overlaps')
    op.drop_table('audience_records')
    op.drop_table('budget_reallocation_changes')
    op.drop_table('budget_reallocation_plans')
    op.drop_table('competitor_benchmarks')
    op.drop_table('creative_fatigue_alerts')
    op.drop_table('creative_performance')
    op.drop_table('creatives')
    op.drop_table('conversion_latency_stats')
    op.drop_table('conversion_latencies')
    op.drop_table('experiment_predictions')
    op.drop_table('model_experiments')
    op.drop_table('offline_conversions')
    op.drop_table('offline_conversion_batches')
    op.drop_table('emq_measurements')
