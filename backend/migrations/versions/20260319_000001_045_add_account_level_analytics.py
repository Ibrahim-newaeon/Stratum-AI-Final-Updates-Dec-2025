# =============================================================================
# Stratum AI - Account-Level Analytics Enhancement
# =============================================================================
"""
Enhance cross-account reporting, account-level pacing, and account-level
signal health tracking.

Changes:
1. Add index on campaigns.account_id for account-level aggregation
2. Add account_id to targets table for account-level budget targets
3. Update DailyKPI unique constraint to include account_id
4. Add indexes on FactSignalHealthDaily.account_id
5. Add account_id to pacing_alerts and forecasts tables

Revision ID: 045_add_account_level_analytics
Revises: 044_add_user_tenant_memberships
Create Date: 2026-03-19 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '045_add_account_level_analytics'
down_revision = '044_add_user_tenant_memberships'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # 1. Campaign table: Add index on account_id for cross-account reporting
    # =========================================================================
    op.create_index(
        'ix_campaigns_tenant_account',
        'campaigns',
        ['tenant_id', 'account_id'],
    )
    op.create_index(
        'ix_campaigns_tenant_platform_account',
        'campaigns',
        ['tenant_id', 'platform', 'account_id'],
    )

    # =========================================================================
    # 2. Target table: Add account_id column for account-level targets
    # =========================================================================
    op.add_column('targets', sa.Column('account_id', sa.String(255), nullable=True))

    # Drop old unique constraint and create new one including account_id
    op.drop_constraint('uq_target_scope', 'targets', type_='unique')
    op.create_unique_constraint(
        'uq_target_scope',
        'targets',
        ['tenant_id', 'period_start', 'period_end', 'metric_type', 'platform', 'account_id', 'campaign_id'],
    )
    op.create_index('ix_targets_tenant_account', 'targets', ['tenant_id', 'account_id'])

    # =========================================================================
    # 3. DailyKPI table: Update unique constraint to include account_id
    # =========================================================================
    op.drop_constraint('uq_daily_kpi_scope', 'daily_kpis', type_='unique')
    op.create_unique_constraint(
        'uq_daily_kpi_scope',
        'daily_kpis',
        ['tenant_id', 'date', 'platform', 'account_id', 'campaign_id'],
    )
    op.create_index(
        'ix_daily_kpis_tenant_account_date',
        'daily_kpis',
        ['tenant_id', 'account_id', 'date'],
    )
    op.create_index(
        'ix_daily_kpis_tenant_platform_account_date',
        'daily_kpis',
        ['tenant_id', 'platform', 'account_id', 'date'],
    )

    # =========================================================================
    # 4. FactSignalHealthDaily: Add index on account_id
    # =========================================================================
    op.create_index(
        'ix_fact_signal_health_daily_tenant_account',
        'fact_signal_health_daily',
        ['tenant_id', 'account_id'],
    )
    op.create_index(
        'ix_fact_signal_health_daily_tenant_platform_account',
        'fact_signal_health_daily',
        ['tenant_id', 'platform', 'account_id'],
    )

    # =========================================================================
    # 5. PacingAlerts: Add account_id for account-level alerts
    # =========================================================================
    op.add_column('pacing_alerts', sa.Column('account_id', sa.String(255), nullable=True))
    op.create_index(
        'ix_pacing_alerts_tenant_account',
        'pacing_alerts',
        ['tenant_id', 'account_id'],
    )

    # =========================================================================
    # 6. Forecasts: Add account_id for account-level forecasting
    # =========================================================================
    op.add_column('forecasts', sa.Column('account_id', sa.String(255), nullable=True))
    op.create_index(
        'ix_forecasts_tenant_account',
        'forecasts',
        ['tenant_id', 'account_id'],
    )


def downgrade():
    # Forecasts
    op.drop_index('ix_forecasts_tenant_account', table_name='forecasts')
    op.drop_column('forecasts', 'account_id')

    # PacingAlerts
    op.drop_index('ix_pacing_alerts_tenant_account', table_name='pacing_alerts')
    op.drop_column('pacing_alerts', 'account_id')

    # FactSignalHealthDaily
    op.drop_index('ix_fact_signal_health_daily_tenant_platform_account', table_name='fact_signal_health_daily')
    op.drop_index('ix_fact_signal_health_daily_tenant_account', table_name='fact_signal_health_daily')

    # DailyKPI
    op.drop_index('ix_daily_kpis_tenant_platform_account_date', table_name='daily_kpis')
    op.drop_index('ix_daily_kpis_tenant_account_date', table_name='daily_kpis')
    op.drop_constraint('uq_daily_kpi_scope', 'daily_kpis', type_='unique')
    op.create_unique_constraint(
        'uq_daily_kpi_scope',
        'daily_kpis',
        ['tenant_id', 'date', 'platform', 'campaign_id'],
    )

    # Targets
    op.drop_index('ix_targets_tenant_account', table_name='targets')
    op.drop_constraint('uq_target_scope', 'targets', type_='unique')
    op.create_unique_constraint(
        'uq_target_scope',
        'targets',
        ['tenant_id', 'period_start', 'period_end', 'metric_type', 'platform', 'campaign_id'],
    )
    op.drop_column('targets', 'account_id')

    # Campaigns
    op.drop_index('ix_campaigns_tenant_platform_account', table_name='campaigns')
    op.drop_index('ix_campaigns_tenant_account', table_name='campaigns')
