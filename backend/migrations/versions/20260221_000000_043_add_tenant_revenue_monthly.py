# =============================================================================
# Stratum AI - Tenant Revenue Monthly Snapshots
# =============================================================================
"""
Add tenant_revenue_monthly table for tracking MRR/ARR growth, churn,
and revenue metrics over time. Required by the SuperAdmin dashboard
for revenue analytics (growth, NRR, logo churn, revenue churn).

Revision ID: 043
Revises: 042
Create Date: 2026-02-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Tenant Revenue Monthly Snapshots
    # =========================================================================
    op.create_table(
        'tenant_revenue_monthly',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('month', sa.Date, nullable=False),  # first day of month

        # Revenue metrics (all in cents to avoid floating point)
        sa.Column('mrr_cents', sa.Integer, nullable=False, default=0),
        sa.Column('arr_cents', sa.Integer, nullable=False, default=0),

        # Changes from previous month
        sa.Column('new_revenue_cents', sa.Integer, default=0),       # new subscriptions
        sa.Column('expansion_cents', sa.Integer, default=0),         # upgrades
        sa.Column('contraction_cents', sa.Integer, default=0),       # downgrades
        sa.Column('churned_revenue_cents', sa.Integer, default=0),   # cancellations

        # Derived metrics
        sa.Column('gross_margin_pct', sa.Float, nullable=True),      # gross margin %
        sa.Column('nrr_pct', sa.Float, nullable=True),               # net revenue retention %
        sa.Column('logo_churn_pct', sa.Float, nullable=True),        # % of tenants lost
        sa.Column('revenue_churn_pct', sa.Float, nullable=True),     # % of revenue lost
        sa.Column('trial_conversion_pct', sa.Float, nullable=True),  # trial → paid %

        # Tenant counts at snapshot time
        sa.Column('total_tenants', sa.Integer, default=0),
        sa.Column('active_tenants', sa.Integer, default=0),
        sa.Column('churned_tenants', sa.Integer, default=0),
        sa.Column('trial_tenants', sa.Integer, default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_tenant_revenue_monthly_tenant_month',
        'tenant_revenue_monthly',
        ['tenant_id', 'month'],
        unique=True,
    )
    op.create_index(
        'ix_tenant_revenue_monthly_month',
        'tenant_revenue_monthly',
        ['month'],
    )


def downgrade():
    op.drop_table('tenant_revenue_monthly')
