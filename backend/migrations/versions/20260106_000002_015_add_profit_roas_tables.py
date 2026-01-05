# =============================================================================
# Stratum AI - Migration: Add Profit ROAS Tables
# =============================================================================
"""
Add Profit ROAS tables.

Revision ID: 015_add_profit_roas_tables
Revises: 014_add_pacing_forecasting
Create Date: 2026-01-06

Tables:
- product_catalog: Product definitions with SKU, category
- product_margins: COGS and margin data per product (time-series)
- margin_rules: Default margin rules by category/platform
- daily_profit_metrics: Daily profit calculations per campaign/product
- profit_roas_reports: Aggregated profit ROAS reports
- cogs_uploads: History of COGS data uploads
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '015_add_profit_roas_tables'
down_revision = '014_add_pacing_forecasting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE margin_type AS ENUM ('fixed_amount', 'percentage', 'tiered');
    """)

    op.execute("""
        CREATE TYPE product_status AS ENUM ('active', 'inactive', 'discontinued');
    """)

    op.execute("""
        CREATE TYPE cogs_source AS ENUM (
            'manual', 'csv_upload', 'api_sync', 'erp_integration', 'shopify', 'woocommerce'
        );
    """)

    # Create product_catalog table
    op.create_table(
        'product_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Product identification
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Categorization
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('subcategory', sa.String(255), nullable=True),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('product_type', sa.String(100), nullable=True),

        # Pricing
        sa.Column('base_price_cents', sa.BigInteger(), nullable=True),
        sa.Column('currency', sa.String(3), server_default='USD', nullable=False),

        # Status
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'discontinued', name='product_status', create_type=False), server_default='active', nullable=False),

        # External IDs
        sa.Column('external_ids', postgresql.JSONB(), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('tenant_id', 'sku', name='uq_product_sku'),
    )

    op.create_index('ix_product_catalog_tenant_sku', 'product_catalog', ['tenant_id', 'sku'])
    op.create_index('ix_product_catalog_tenant_category', 'product_catalog', ['tenant_id', 'category'])

    # Create product_margins table
    op.create_table(
        'product_margins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('product_catalog.id', ondelete='CASCADE'), nullable=False),

        # Effective period
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),

        # COGS data
        sa.Column('cogs_cents', sa.BigInteger(), nullable=True),
        sa.Column('cogs_percentage', sa.Float(), nullable=True),

        # Margin data
        sa.Column('margin_type', postgresql.ENUM('fixed_amount', 'percentage', 'tiered', name='margin_type', create_type=False), server_default='fixed_amount', nullable=False),
        sa.Column('margin_cents', sa.BigInteger(), nullable=True),
        sa.Column('margin_percentage', sa.Float(), nullable=True),

        # Additional costs
        sa.Column('shipping_cost_cents', sa.BigInteger(), server_default='0'),
        sa.Column('handling_cost_cents', sa.BigInteger(), server_default='0'),
        sa.Column('platform_fee_cents', sa.BigInteger(), server_default='0'),
        sa.Column('payment_processing_cents', sa.BigInteger(), server_default='0'),
        sa.Column('total_cogs_cents', sa.BigInteger(), nullable=True),

        # Source tracking
        sa.Column('source', postgresql.ENUM('manual', 'csv_upload', 'api_sync', 'erp_integration', 'shopify', 'woocommerce', name='cogs_source', create_type=False), server_default='manual', nullable=False),
        sa.Column('source_reference', sa.String(255), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_index('ix_product_margins_product_date', 'product_margins', ['product_id', 'effective_date'])
    op.create_index('ix_product_margins_tenant_date', 'product_margins', ['tenant_id', 'effective_date'])

    # Create margin_rules table
    op.create_table(
        'margin_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Rule identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Rule scope
        sa.Column('priority', sa.Integer(), server_default='100', nullable=False),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('subcategory', sa.String(255), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),

        # Margin specification
        sa.Column('margin_type', postgresql.ENUM('fixed_amount', 'percentage', 'tiered', name='margin_type', create_type=False), server_default='percentage', nullable=False),
        sa.Column('default_margin_percentage', sa.Float(), nullable=True),
        sa.Column('default_cogs_percentage', sa.Float(), nullable=True),
        sa.Column('tiered_config', postgresql.JSONB(), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_margin_rules_tenant_priority', 'margin_rules', ['tenant_id', 'priority'])
    op.create_index('ix_margin_rules_tenant_category', 'margin_rules', ['tenant_id', 'category'])

    # Create daily_profit_metrics table
    op.create_table(
        'daily_profit_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('adset_id', sa.String(255), nullable=True),
        sa.Column('ad_id', sa.String(255), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('product_catalog.id', ondelete='SET NULL'), nullable=True),

        # Revenue metrics
        sa.Column('units_sold', sa.Integer(), server_default='0', nullable=False),
        sa.Column('gross_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('net_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('average_order_value_cents', sa.BigInteger(), nullable=True),

        # Cost metrics
        sa.Column('total_cogs_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('product_cogs_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('shipping_costs_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('platform_fees_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('payment_fees_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Ad spend
        sa.Column('ad_spend_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Profit calculations
        sa.Column('gross_profit_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('contribution_margin_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('net_profit_cents', sa.BigInteger(), server_default='0', nullable=False),

        # ROAS metrics
        sa.Column('revenue_roas', sa.Float(), nullable=True),
        sa.Column('gross_profit_roas', sa.Float(), nullable=True),
        sa.Column('contribution_roas', sa.Float(), nullable=True),
        sa.Column('net_profit_roas', sa.Float(), nullable=True),

        # Margin percentages
        sa.Column('gross_margin_pct', sa.Float(), nullable=True),
        sa.Column('contribution_margin_pct', sa.Float(), nullable=True),
        sa.Column('net_margin_pct', sa.Float(), nullable=True),

        # Data quality
        sa.Column('cogs_source', postgresql.ENUM('manual', 'csv_upload', 'api_sync', 'erp_integration', 'shopify', 'woocommerce', name='cogs_source', create_type=False), nullable=True),
        sa.Column('margin_rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('margin_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_estimated', sa.Boolean(), server_default='false', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('tenant_id', 'date', 'platform', 'campaign_id', 'product_id', name='uq_daily_profit_scope'),
    )

    op.create_index('ix_daily_profit_tenant_date', 'daily_profit_metrics', ['tenant_id', 'date'])
    op.create_index('ix_daily_profit_tenant_campaign', 'daily_profit_metrics', ['tenant_id', 'campaign_id', 'date'])
    op.create_index('ix_daily_profit_tenant_product', 'daily_profit_metrics', ['tenant_id', 'product_id', 'date'])

    # Create profit_roas_reports table
    op.create_table(
        'profit_roas_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Report period
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),

        # Scope
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),

        # Aggregated metrics
        sa.Column('total_units', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_cogs_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_ad_spend_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_gross_profit_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_net_profit_cents', sa.BigInteger(), server_default='0', nullable=False),

        # ROAS metrics
        sa.Column('revenue_roas', sa.Float(), nullable=True),
        sa.Column('gross_profit_roas', sa.Float(), nullable=True),
        sa.Column('net_profit_roas', sa.Float(), nullable=True),

        # Margin metrics
        sa.Column('avg_gross_margin_pct', sa.Float(), nullable=True),
        sa.Column('avg_net_margin_pct', sa.Float(), nullable=True),

        # Breakeven analysis
        sa.Column('breakeven_roas', sa.Float(), nullable=True),
        sa.Column('above_breakeven', sa.Boolean(), nullable=True),

        # Comparison to target
        sa.Column('target_profit_roas', sa.Float(), nullable=True),
        sa.Column('vs_target_pct', sa.Float(), nullable=True),

        # Data quality
        sa.Column('products_with_cogs', sa.Integer(), server_default='0'),
        sa.Column('products_estimated', sa.Integer(), server_default='0'),
        sa.Column('data_completeness_pct', sa.Float(), nullable=True),

        # Report metadata
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('generated_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_index('ix_profit_reports_tenant_period', 'profit_roas_reports', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('ix_profit_reports_tenant_type', 'profit_roas_reports', ['tenant_id', 'report_type'])

    # Create cogs_uploads table
    op.create_table(
        'cogs_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Upload metadata
        sa.Column('filename', sa.String(500), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('source', postgresql.ENUM('manual', 'csv_upload', 'api_sync', 'erp_integration', 'shopify', 'woocommerce', name='cogs_source', create_type=False), nullable=False),

        # Processing results
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('rows_processed', sa.Integer(), server_default='0'),
        sa.Column('rows_succeeded', sa.Integer(), server_default='0'),
        sa.Column('rows_failed', sa.Integer(), server_default='0'),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),

        # Affected date range
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('products_updated', sa.Integer(), server_default='0'),

        # Timestamps
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uploaded_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_index('ix_cogs_uploads_tenant_date', 'cogs_uploads', ['tenant_id', 'uploaded_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('cogs_uploads')
    op.drop_table('profit_roas_reports')
    op.drop_table('daily_profit_metrics')
    op.drop_table('margin_rules')
    op.drop_table('product_margins')
    op.drop_table('product_catalog')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS cogs_source')
    op.execute('DROP TYPE IF EXISTS product_status')
    op.execute('DROP TYPE IF EXISTS margin_type')
