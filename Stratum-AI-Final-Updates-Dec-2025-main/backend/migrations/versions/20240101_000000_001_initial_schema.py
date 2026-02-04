"""Initial schema for Stratum AI

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'manager', 'analyst', 'viewer')")
    op.execute("CREATE TYPE adplatform AS ENUM ('meta', 'google', 'tiktok', 'snapchat')")
    op.execute("CREATE TYPE campaignstatus AS ENUM ('draft', 'active', 'paused', 'completed', 'archived')")
    op.execute("CREATE TYPE assettype AS ENUM ('image', 'video', 'carousel', 'story', 'html5')")
    op.execute("CREATE TYPE rulestatus AS ENUM ('active', 'paused', 'draft')")
    op.execute("CREATE TYPE ruleoperator AS ENUM ('equals', 'not_equals', 'greater_than', 'less_than', 'gte', 'lte', 'contains', 'in')")
    op.execute("CREATE TYPE ruleaction AS ENUM ('apply_label', 'send_alert', 'pause_campaign', 'adjust_budget', 'notify_slack')")
    op.execute("CREATE TYPE auditaction AS ENUM ('create', 'update', 'delete', 'login', 'logout', 'export', 'anonymize')")

    # Tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('feature_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('max_users', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_campaigns', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id', name='pk_tenants'),
        sa.UniqueConstraint('slug', name='uq_tenants_slug')
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])
    op.create_index('ix_tenants_active', 'tenants', ['is_deleted', 'plan'])

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('role', postgresql.ENUM('admin', 'manager', 'analyst', 'viewer', name='userrole', create_type=False), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locale', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('consent_marketing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('consent_analytics', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('gdpr_anonymized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_users_tenant_id_tenants', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('tenant_id', 'email_hash', name='uq_user_tenant_email')
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email_hash', 'users', ['email_hash'])
    op.create_index('ix_users_tenant_active', 'users', ['tenant_id', 'is_active', 'is_deleted'])

    # Campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('platform', postgresql.ENUM('meta', 'google', 'tiktok', 'snapchat', name='adplatform', create_type=False), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('status', postgresql.ENUM('draft', 'active', 'paused', 'completed', 'archived', name='campaignstatus', create_type=False), nullable=False),
        sa.Column('objective', sa.String(length=100), nullable=True),
        sa.Column('daily_budget_cents', sa.Integer(), nullable=True),
        sa.Column('lifetime_budget_cents', sa.Integer(), nullable=True),
        sa.Column('total_spend_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revenue_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ctr', sa.Float(), nullable=True),
        sa.Column('cpc_cents', sa.Integer(), nullable=True),
        sa.Column('cpm_cents', sa.Integer(), nullable=True),
        sa.Column('cpa_cents', sa.Integer(), nullable=True),
        sa.Column('roas', sa.Float(), nullable=True),
        sa.Column('targeting_age_min', sa.Integer(), nullable=True),
        sa.Column('targeting_age_max', sa.Integer(), nullable=True),
        sa.Column('targeting_genders', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('targeting_locations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('targeting_interests', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographics_age', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographics_gender', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographics_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_campaigns_tenant_id_tenants', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_campaigns'),
        sa.UniqueConstraint('tenant_id', 'platform', 'external_id', name='uq_campaign_platform_external')
    )
    op.create_index('ix_campaigns_tenant_id', 'campaigns', ['tenant_id'])
    op.create_index('ix_campaigns_tenant_status', 'campaigns', ['tenant_id', 'status'])
    op.create_index('ix_campaigns_platform', 'campaigns', ['tenant_id', 'platform'])
    op.create_index('ix_campaigns_date_range', 'campaigns', ['tenant_id', 'start_date', 'end_date'])
    op.create_index('ix_campaigns_roas', 'campaigns', ['tenant_id', 'roas'])

    # Campaign Metrics table
    op.create_table(
        'campaign_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('spend_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revenue_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('video_views', sa.Integer(), nullable=True),
        sa.Column('video_completions', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('saves', sa.Integer(), nullable=True),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name='fk_campaign_metrics_campaign_id_campaigns', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_campaign_metrics'),
        sa.UniqueConstraint('campaign_id', 'date', name='uq_campaign_metric_date')
    )
    op.create_index('ix_campaign_metrics_tenant_id', 'campaign_metrics', ['tenant_id'])
    op.create_index('ix_campaign_metrics_date', 'campaign_metrics', ['tenant_id', 'date'])
    op.create_index('ix_campaign_metrics_campaign_date', 'campaign_metrics', ['campaign_id', 'date'])

    # Creative Assets table
    op.create_table(
        'creative_assets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('asset_type', postgresql.ENUM('image', 'video', 'carousel', 'story', 'html5', name='assettype', create_type=False), nullable=False),
        sa.Column('file_url', sa.String(length=1000), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=1000), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_format', sa.String(length=50), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('folder', sa.String(length=255), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ctr', sa.Float(), nullable=True),
        sa.Column('fatigue_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('first_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('times_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_description', sa.Text(), nullable=True),
        sa.Column('ai_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('brand_safety_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name='fk_creative_assets_campaign_id_campaigns', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_creative_assets')
    )
    op.create_index('ix_creative_assets_tenant_id', 'creative_assets', ['tenant_id'])
    op.create_index('ix_assets_tenant_type', 'creative_assets', ['tenant_id', 'asset_type'])
    op.create_index('ix_assets_fatigue', 'creative_assets', ['tenant_id', 'fatigue_score'])
    op.create_index('ix_assets_folder', 'creative_assets', ['tenant_id', 'folder'])

    # Rules table
    op.create_table(
        'rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'draft', name='rulestatus', create_type=False), nullable=False),
        sa.Column('condition_field', sa.String(length=100), nullable=False),
        sa.Column('condition_operator', postgresql.ENUM('equals', 'not_equals', 'greater_than', 'less_than', 'gte', 'lte', 'contains', 'in', name='ruleoperator', create_type=False), nullable=False),
        sa.Column('condition_value', sa.String(length=255), nullable=False),
        sa.Column('condition_duration_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('action_type', postgresql.ENUM('apply_label', 'send_alert', 'pause_campaign', 'adjust_budget', 'notify_slack', name='ruleaction', create_type=False), nullable=False),
        sa.Column('action_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('applies_to_campaigns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('applies_to_platforms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cooldown_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id', name='pk_rules')
    )
    op.create_index('ix_rules_tenant_id', 'rules', ['tenant_id'])
    op.create_index('ix_rules_tenant_status', 'rules', ['tenant_id', 'status'])
    op.create_index('ix_rules_evaluation', 'rules', ['status', 'last_evaluated_at'])

    # Rule Executions table
    op.create_table(
        'rule_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('triggered', sa.Boolean(), nullable=False),
        sa.Column('condition_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name='fk_rule_executions_campaign_id_campaigns', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], name='fk_rule_executions_rule_id_rules', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_rule_executions')
    )
    op.create_index('ix_rule_executions_tenant_id', 'rule_executions', ['tenant_id'])
    op.create_index('ix_rule_executions_rule_date', 'rule_executions', ['rule_id', 'executed_at'])
    op.create_index('ix_rule_executions_tenant_date', 'rule_executions', ['tenant_id', 'executed_at'])

    # Competitor Benchmarks table
    op.create_table(
        'competitor_benchmarks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('meta_title', sa.String(length=500), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('meta_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('social_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('estimated_traffic', sa.Integer(), nullable=True),
        sa.Column('traffic_trend', sa.String(length=20), nullable=True),
        sa.Column('top_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('paid_keywords_count', sa.Integer(), nullable=True),
        sa.Column('organic_keywords_count', sa.Integer(), nullable=True),
        sa.Column('share_of_voice', sa.Float(), nullable=True),
        sa.Column('category_rank', sa.Integer(), nullable=True),
        sa.Column('estimated_ad_spend_cents', sa.Integer(), nullable=True),
        sa.Column('detected_ad_platforms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ad_creatives_count', sa.Integer(), nullable=True),
        sa.Column('metrics_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=False, server_default='scraper'),
        sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fetch_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_competitor_benchmarks'),
        sa.UniqueConstraint('tenant_id', 'domain', name='uq_competitor_tenant_domain')
    )
    op.create_index('ix_competitor_benchmarks_tenant_id', 'competitor_benchmarks', ['tenant_id'])
    op.create_index('ix_competitors_tenant_primary', 'competitor_benchmarks', ['tenant_id', 'is_primary'])
    op.create_index('ix_competitors_sov', 'competitor_benchmarks', ['tenant_id', 'share_of_voice'])

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', postgresql.ENUM('create', 'update', 'delete', 'login', 'logout', 'export', 'anonymize', name='auditaction', create_type=False), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('http_method', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_logs_user_id_users', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_audit_logs')
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_tenant_date', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_user_date', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_action', 'audit_logs', ['tenant_id', 'action', 'created_at'])

    # ML Predictions table
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('prediction_value', sa.Float(), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=True),
        sa.Column('confidence_upper', sa.Float(), nullable=True),
        sa.Column('feature_importances', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name='fk_ml_predictions_campaign_id_campaigns', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_ml_predictions')
    )
    op.create_index('ix_ml_predictions_tenant_id', 'ml_predictions', ['tenant_id'])
    op.create_index('ix_predictions_cache', 'ml_predictions', ['model_type', 'input_hash'])
    op.create_index('ix_predictions_expiry', 'ml_predictions', ['expires_at'])

    # Notification Preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('slack_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('slack_webhook_url', sa.String(length=500), nullable=True),
        sa.Column('alert_rule_triggered', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('alert_budget_threshold', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('alert_performance_drop', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('alert_sync_failure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('report_daily', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('report_weekly', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('report_monthly', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_notification_preferences_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_notification_preferences'),
        sa.UniqueConstraint('user_id', name='uq_notification_user')
    )
    op.create_index('ix_notification_preferences_tenant_id', 'notification_preferences', ['tenant_id'])

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=10), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_api_keys_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_api_keys'),
        sa.UniqueConstraint('key_hash', name='uq_api_keys_key_hash')
    )
    op.create_index('ix_api_keys_tenant_id', 'api_keys', ['tenant_id'])
    op.create_index('ix_api_keys_hash', 'api_keys', ['key_hash'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('api_keys')
    op.drop_table('notification_preferences')
    op.drop_table('ml_predictions')
    op.drop_table('audit_logs')
    op.drop_table('competitor_benchmarks')
    op.drop_table('rule_executions')
    op.drop_table('rules')
    op.drop_table('creative_assets')
    op.drop_table('campaign_metrics')
    op.drop_table('campaigns')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enum types
    op.execute("DROP TYPE auditaction")
    op.execute("DROP TYPE ruleaction")
    op.execute("DROP TYPE ruleoperator")
    op.execute("DROP TYPE rulestatus")
    op.execute("DROP TYPE assettype")
    op.execute("DROP TYPE campaignstatus")
    op.execute("DROP TYPE adplatform")
    op.execute("DROP TYPE userrole")
