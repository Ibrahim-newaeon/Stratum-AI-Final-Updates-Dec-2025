# =============================================================================
# Stratum AI - Cost Allocation Tracking
# =============================================================================
"""
Add cost allocation tracking tables.

Based on Multi_Tenant_and_Super_Admin_Spec.md Section 4.2:
- fact_cost_allocation_daily: Per-tenant cost breakdown
- Tracks warehouse, API, and compute costs

Revision ID: 010
Revises: 009
Create Date: 2024-12-23 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Cost Allocation Daily
    # =========================================================================
    op.create_table(
        'fact_cost_allocation_daily',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),

        # Warehouse costs
        sa.Column('warehouse_storage_gb', sa.Float, default=0),
        sa.Column('warehouse_storage_cost_usd', sa.Float, default=0),
        sa.Column('warehouse_query_cost_usd', sa.Float, default=0),
        sa.Column('warehouse_total_cost_usd', sa.Float, default=0),

        # API costs (platform API calls)
        sa.Column('meta_api_calls', sa.Integer, default=0),
        sa.Column('google_api_calls', sa.Integer, default=0),
        sa.Column('tiktok_api_calls', sa.Integer, default=0),
        sa.Column('snap_api_calls', sa.Integer, default=0),
        sa.Column('api_total_cost_usd', sa.Float, default=0),

        # Compute costs
        sa.Column('compute_hours', sa.Float, default=0),
        sa.Column('compute_cost_usd', sa.Float, default=0),

        # ML/AI costs
        sa.Column('ml_predictions', sa.Integer, default=0),
        sa.Column('ml_cost_usd', sa.Float, default=0),

        # Totals
        sa.Column('total_cost_usd', sa.Float, default=0),
        sa.Column('mrr_usd', sa.Float, default=0),
        sa.Column('gross_margin_pct', sa.Float, default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_cost_allocation_daily_tenant_date', 'fact_cost_allocation_daily', ['tenant_id', 'date'])
    op.create_index('ix_cost_allocation_daily_date', 'fact_cost_allocation_daily', ['date'])

    # =========================================================================
    # Platform API Rate Limits Tracking
    # =========================================================================
    op.create_table(
        'platform_rate_limits',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),  # meta/google/tiktok/snap
        sa.Column('endpoint', sa.String(100), nullable=True),

        # Rate limit status
        sa.Column('limit_total', sa.Integer, nullable=True),
        sa.Column('limit_remaining', sa.Integer, nullable=True),
        sa.Column('limit_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_throttled', sa.Boolean, default=False),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_platform_rate_limits_tenant', 'platform_rate_limits', ['tenant_id', 'platform'])

    # =========================================================================
    # Feature Usage Tracking
    # =========================================================================
    op.create_table(
        'feature_usage',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),

        # Feature usage counts
        sa.Column('dashboard_views', sa.Integer, default=0),
        sa.Column('campaign_edits', sa.Integer, default=0),
        sa.Column('rule_executions', sa.Integer, default=0),
        sa.Column('report_exports', sa.Integer, default=0),
        sa.Column('ai_insights_generated', sa.Integer, default=0),
        sa.Column('api_calls_made', sa.Integer, default=0),
        sa.Column('whatsapp_messages', sa.Integer, default=0),

        # Time spent
        sa.Column('session_seconds', sa.Integer, default=0),
        sa.Column('unique_users', sa.Integer, default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_feature_usage_tenant_date', 'feature_usage', ['tenant_id', 'date'])


def downgrade():
    op.drop_table('feature_usage')
    op.drop_table('platform_rate_limits')
    op.drop_table('fact_cost_allocation_daily')
