"""Add USP Layer tables (Trust Layer, Actions Queue)

Revision ID: 011_add_usp_layer_tables
Revises: 010
Create Date: 2026-01-02 00:00:00.000000

This migration adds:
- fact_signal_health_daily: Daily signal health metrics per tenant/platform
- fact_attribution_variance_daily: Daily attribution variance (Platform vs GA4)
- fact_actions_queue: Autopilot action queue with approval workflow
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_add_usp_layer_tables'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Signal Health Status Enum
    # ==========================================================================
    signal_health_status = postgresql.ENUM(
        'ok', 'risk', 'degraded', 'critical',
        name='signal_health_status',
        create_type=False
    )
    signal_health_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Attribution Variance Status Enum
    # ==========================================================================
    attribution_variance_status = postgresql.ENUM(
        'healthy', 'minor_variance', 'moderate_variance', 'high_variance',
        name='attribution_variance_status',
        create_type=False
    )
    attribution_variance_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # fact_signal_health_daily
    # ==========================================================================
    op.create_table(
        'fact_signal_health_daily',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('account_id', sa.String(255), nullable=True),

        # Signal health metrics
        sa.Column('emq_score', sa.Float(), nullable=True),
        sa.Column('event_loss_pct', sa.Float(), nullable=True),
        sa.Column('freshness_minutes', sa.Integer(), nullable=True),
        sa.Column('api_error_rate', sa.Float(), nullable=True),

        # Computed status
        sa.Column('status', signal_health_status, nullable=False, server_default='ok'),

        # Additional context
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('issues', sa.Text(), nullable=True),  # JSON array
        sa.Column('actions', sa.Text(), nullable=True),  # JSON array

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Indexes for signal_health_daily
    op.create_index('ix_fact_signal_health_daily_tenant_date', 'fact_signal_health_daily', ['tenant_id', 'date'])
    op.create_index('ix_fact_signal_health_daily_tenant_platform', 'fact_signal_health_daily', ['tenant_id', 'platform'])
    op.create_index('ix_fact_signal_health_daily_status', 'fact_signal_health_daily', ['tenant_id', 'status'])

    # Unique constraint per tenant/date/platform
    op.create_unique_constraint(
        'uq_fact_signal_health_daily_tenant_date_platform',
        'fact_signal_health_daily',
        ['tenant_id', 'date', 'platform', 'account_id']
    )

    # ==========================================================================
    # fact_attribution_variance_daily
    # ==========================================================================
    op.create_table(
        'fact_attribution_variance_daily',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),

        # Revenue comparison
        sa.Column('ga4_revenue', sa.Float(), nullable=False, server_default='0'),
        sa.Column('platform_revenue', sa.Float(), nullable=False, server_default='0'),
        sa.Column('revenue_delta_abs', sa.Float(), nullable=False, server_default='0'),
        sa.Column('revenue_delta_pct', sa.Float(), nullable=False, server_default='0'),

        # Conversion comparison
        sa.Column('ga4_conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('platform_conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversion_delta_abs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversion_delta_pct', sa.Float(), nullable=False, server_default='0'),

        # Confidence and status
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', attribution_variance_status, nullable=False, server_default='healthy'),

        # Additional context
        sa.Column('notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Indexes for attribution_variance_daily
    op.create_index('ix_fact_attribution_variance_daily_tenant_date', 'fact_attribution_variance_daily', ['tenant_id', 'date'])
    op.create_index('ix_fact_attribution_variance_daily_tenant_platform', 'fact_attribution_variance_daily', ['tenant_id', 'platform'])

    # Unique constraint per tenant/date/platform
    op.create_unique_constraint(
        'uq_fact_attribution_variance_daily_tenant_date_platform',
        'fact_attribution_variance_daily',
        ['tenant_id', 'date', 'platform']
    )

    # ==========================================================================
    # fact_actions_queue
    # ==========================================================================
    op.create_table(
        'fact_actions_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),

        # Action details
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('entity_name', sa.String(255), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),

        # Action payload
        sa.Column('action_json', sa.Text(), nullable=False),

        # Before/after values for audit
        sa.Column('before_value', sa.Text(), nullable=True),
        sa.Column('after_value', sa.Text(), nullable=True),

        # Workflow status
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),

        # Actors
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('applied_by_user_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),

        # Result
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('platform_response', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['applied_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Indexes for actions_queue
    op.create_index('ix_fact_actions_queue_tenant_date', 'fact_actions_queue', ['tenant_id', 'date'])
    op.create_index('ix_fact_actions_queue_status', 'fact_actions_queue', ['tenant_id', 'status'])
    op.create_index('ix_fact_actions_queue_platform', 'fact_actions_queue', ['tenant_id', 'platform'])

    # ==========================================================================
    # Add feature_flags column to tenant table if not exists
    # ==========================================================================
    # Check if column exists and add if not
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'tenants' AND column_name = 'feature_flags'
            ) THEN
                ALTER TABLE tenants ADD COLUMN feature_flags JSONB DEFAULT '{}';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # Add relationship columns to tenant table for Trust Layer
    # ==========================================================================
    # These are handled by SQLAlchemy relationships, no column additions needed


def downgrade() -> None:
    # Drop tables
    op.drop_table('fact_actions_queue')
    op.drop_table('fact_attribution_variance_daily')
    op.drop_table('fact_signal_health_daily')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS attribution_variance_status')
    op.execute('DROP TYPE IF EXISTS signal_health_status')
