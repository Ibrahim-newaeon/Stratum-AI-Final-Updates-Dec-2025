# =============================================================================
# Stratum AI - Super Admin & Multi-Tenant Subscription System
# =============================================================================
"""
Add Super Admin dashboard and subscription management tables.

Based on Multi_Tenant_and_Super_Admin_Spec.md requirements:
- Extended tenant fields (MRR, status, connectors)
- Subscription plans catalog
- Usage tracking
- Audit logging

Revision ID: 009
Revises: 008
Create Date: 2024-12-23 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Extend Tenants Table
    # =========================================================================
    op.add_column('tenants', sa.Column('status', sa.String(20), default='active', nullable=False, server_default='active'))
    op.add_column('tenants', sa.Column('mrr_cents', sa.Integer, default=0, nullable=False, server_default='0'))
    op.add_column('tenants', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('billing_email', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('billing_address', postgresql.JSONB, nullable=True))
    op.add_column('tenants', sa.Column('vat_number', sa.String(50), nullable=True))
    op.add_column('tenants', sa.Column('timezone', sa.String(50), default='UTC', server_default='UTC'))
    op.add_column('tenants', sa.Column('currency', sa.String(3), default='USD', server_default='USD'))
    op.add_column('tenants', sa.Column('max_connectors', sa.Integer, default=3, server_default='3'))
    op.add_column('tenants', sa.Column('max_refresh_frequency_mins', sa.Integer, default=60, server_default='60'))
    op.add_column('tenants', sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('last_admin_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('onboarding_completed', sa.Boolean, default=False, server_default='false'))
    op.add_column('tenants', sa.Column('churn_risk_score', sa.Float, nullable=True))
    op.add_column('tenants', sa.Column('health_score', sa.Float, nullable=True))

    # =========================================================================
    # Subscription Plans Catalog
    # =========================================================================
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.String(50), primary_key=True),  # e.g., 'starter_monthly'
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),  # free/starter/professional/enterprise
        sa.Column('billing_period', sa.String(20), nullable=False),  # monthly/yearly
        sa.Column('price_cents', sa.Integer, nullable=False, default=0),
        sa.Column('currency', sa.String(3), default='USD'),

        # Limits
        sa.Column('max_users', sa.Integer, nullable=False, default=5),
        sa.Column('max_campaigns', sa.Integer, nullable=False, default=50),
        sa.Column('max_connectors', sa.Integer, nullable=False, default=3),
        sa.Column('max_refresh_frequency_mins', sa.Integer, nullable=False, default=60),

        # Features
        sa.Column('features', postgresql.JSONB, default=dict),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('sort_order', sa.Integer, default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed plans
    op.execute("""
        INSERT INTO subscription_plans (id, name, display_name, tier, billing_period, price_cents, max_users, max_campaigns, max_connectors, max_refresh_frequency_mins, features, sort_order) VALUES
        ('free', 'Free', 'Free Plan', 'free', 'monthly', 0, 5, 10, 2, 1440, '{"analytics": true, "ai_insights": false, "api_access": false, "white_label": false, "sso": false}', 1),
        ('starter_monthly', 'Starter Monthly', 'Starter', 'starter', 'monthly', 9900, 10, 50, 3, 60, '{"analytics": true, "ai_insights": true, "api_access": false, "white_label": false, "sso": false}', 2),
        ('starter_yearly', 'Starter Yearly', 'Starter (Annual)', 'starter', 'yearly', 99900, 10, 50, 3, 60, '{"analytics": true, "ai_insights": true, "api_access": false, "white_label": false, "sso": false}', 3),
        ('professional_monthly', 'Professional Monthly', 'Professional', 'professional', 'monthly', 29900, 25, 200, 5, 30, '{"analytics": true, "ai_insights": true, "api_access": true, "white_label": false, "sso": false}', 4),
        ('professional_yearly', 'Professional Yearly', 'Professional (Annual)', 'professional', 'yearly', 299900, 25, 200, 5, 30, '{"analytics": true, "ai_insights": true, "api_access": true, "white_label": false, "sso": false}', 5),
        ('enterprise_monthly', 'Enterprise Monthly', 'Enterprise', 'enterprise', 'monthly', 99900, 100, 1000, 10, 15, '{"analytics": true, "ai_insights": true, "api_access": true, "white_label": true, "sso": true}', 6),
        ('enterprise_yearly', 'Enterprise Yearly', 'Enterprise (Annual)', 'enterprise', 'yearly', 999900, 100, 1000, 10, 15, '{"analytics": true, "ai_insights": true, "api_access": true, "white_label": true, "sso": true}', 7)
        ON CONFLICT (id) DO NOTHING
    """)

    # =========================================================================
    # Subscriptions (History)
    # =========================================================================
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('plan_id', sa.String(50), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='active'),  # active/cancelled/past_due/trialing
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean, default=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),

        # Stripe/Payment
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),

        # Discounts
        sa.Column('discount_percent', sa.Float, default=0),
        sa.Column('discount_reason', sa.String(255), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_subscriptions_tenant', 'subscriptions', ['tenant_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])

    # =========================================================================
    # Usage Tracking (Daily)
    # =========================================================================
    op.create_table(
        'tenant_usage_daily',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),

        # Usage metrics
        sa.Column('active_users', sa.Integer, default=0),
        sa.Column('api_calls', sa.Integer, default=0),
        sa.Column('campaigns_active', sa.Integer, default=0),
        sa.Column('connectors_used', sa.Integer, default=0),
        sa.Column('data_ingested_mb', sa.Float, default=0),
        sa.Column('events_processed', sa.Integer, default=0),

        # Health metrics
        sa.Column('emq_score_avg', sa.Float, nullable=True),
        sa.Column('event_loss_pct', sa.Float, nullable=True),
        sa.Column('api_errors', sa.Integer, default=0),

        # Engagement
        sa.Column('logins', sa.Integer, default=0),
        sa.Column('session_minutes', sa.Integer, default=0),
        sa.Column('actions_taken', sa.Integer, default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_tenant_usage_daily_tenant_date', 'tenant_usage_daily', ['tenant_id', 'date'])

    # =========================================================================
    # Platform Connectors
    # =========================================================================
    op.create_table(
        'platform_connectors',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),  # meta/google/tiktok/snap/ga4
        sa.Column('account_id', sa.String(100), nullable=True),
        sa.Column('account_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), default='connected'),  # connected/disconnected/error
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('credentials_encrypted', postgresql.BYTEA, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_platform_connectors_tenant', 'platform_connectors', ['tenant_id'])

    # =========================================================================
    # Audit Log - Skip if already exists (created in migration 001)
    # =========================================================================
    # Note: audit_logs table is created in migration 001. We only add
    # missing columns needed for superadmin functionality if they don't exist.
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'audit_logs')"
    ))
    audit_logs_exists = result.scalar()

    if not audit_logs_exists:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('tenant_id', sa.Integer, nullable=True),
            sa.Column('user_id', sa.Integer, nullable=True),
            sa.Column('user_email', sa.String(255), nullable=True),
            sa.Column('action', sa.String(100), nullable=False),
            sa.Column('resource_type', sa.String(50), nullable=True),
            sa.Column('resource_id', sa.String(100), nullable=True),
            sa.Column('details', postgresql.JSONB, nullable=True),
            sa.Column('ip_address', sa.String(50), nullable=True),
            sa.Column('user_agent', sa.String(500), nullable=True),
            sa.Column('success', sa.Boolean, default=True),
            sa.Column('error_message', sa.Text, nullable=True),
        )
        op.create_index('ix_audit_logs_tenant_timestamp', 'audit_logs', ['tenant_id', 'timestamp'])
        op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
        op.create_index('ix_audit_logs_user', 'audit_logs', ['user_id'])

    # =========================================================================
    # Invoices
    # =========================================================================
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('subscription_id', sa.Integer, sa.ForeignKey('subscriptions.id'), nullable=True),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),  # draft/pending/paid/overdue/cancelled
        sa.Column('amount_cents', sa.Integer, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('tax_cents', sa.Integer, default=0),
        sa.Column('total_cents', sa.Integer, nullable=False),

        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),

        # Stripe
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True),

        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_invoices_tenant', 'invoices', ['tenant_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])

    # =========================================================================
    # System Health Metrics
    # =========================================================================
    op.create_table(
        'system_health_hourly',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),

        # Pipeline health
        sa.Column('pipeline_success_rate', sa.Float),
        sa.Column('pipeline_jobs_total', sa.Integer, default=0),
        sa.Column('pipeline_jobs_failed', sa.Integer, default=0),

        # API health
        sa.Column('api_requests', sa.Integer, default=0),
        sa.Column('api_errors', sa.Integer, default=0),
        sa.Column('api_latency_p50_ms', sa.Float),
        sa.Column('api_latency_p99_ms', sa.Float),

        # Platform API health
        sa.Column('meta_api_success_rate', sa.Float),
        sa.Column('google_api_success_rate', sa.Float),
        sa.Column('tiktok_api_success_rate', sa.Float),
        sa.Column('snap_api_success_rate', sa.Float),

        # Queue health
        sa.Column('queue_depth', sa.Integer, default=0),
        sa.Column('queue_latency_ms', sa.Float),

        # Resources
        sa.Column('cpu_percent', sa.Float),
        sa.Column('memory_percent', sa.Float),
        sa.Column('disk_percent', sa.Float),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_system_health_hourly_timestamp', 'system_health_hourly', ['timestamp'])


def downgrade():
    op.drop_table('system_health_hourly')
    op.drop_table('invoices')
    # Note: audit_logs is NOT dropped here since it was created in migration 001
    # and should only be dropped by that migration's downgrade
    op.drop_table('platform_connectors')
    op.drop_table('tenant_usage_daily')
    op.drop_table('subscriptions')
    op.drop_table('subscription_plans')

    # Remove added columns from tenants
    op.drop_column('tenants', 'health_score')
    op.drop_column('tenants', 'churn_risk_score')
    op.drop_column('tenants', 'onboarding_completed')
    op.drop_column('tenants', 'last_admin_login_at')
    op.drop_column('tenants', 'last_activity_at')
    op.drop_column('tenants', 'max_refresh_frequency_mins')
    op.drop_column('tenants', 'max_connectors')
    op.drop_column('tenants', 'currency')
    op.drop_column('tenants', 'timezone')
    op.drop_column('tenants', 'vat_number')
    op.drop_column('tenants', 'billing_address')
    op.drop_column('tenants', 'billing_email')
    op.drop_column('tenants', 'trial_ends_at')
    op.drop_column('tenants', 'mrr_cents')
    op.drop_column('tenants', 'status')
