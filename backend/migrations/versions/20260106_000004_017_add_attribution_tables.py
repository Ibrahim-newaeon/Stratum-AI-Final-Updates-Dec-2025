"""Add Multi-Touch Attribution tables

Revision ID: 017_add_attribution_tables
Revises: 016
Create Date: 2026-01-06 00:04:00.000000

This migration adds:
- daily_attributed_revenue: Pre-calculated attributed revenue by model
- conversion_paths: Aggregated conversion path statistics
- attribution_snapshots: Point-in-time attribution snapshots
- channel_interactions: Channel transition matrix for Sankey visualization
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_attribution'
down_revision = '016_hubspot_wb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # daily_attributed_revenue - Pre-calculated attributed revenue
    # ==========================================================================
    op.create_table(
        'daily_attributed_revenue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),

        # Attribution model
        sa.Column('attribution_model', sa.String(50), nullable=False),

        # Dimension
        sa.Column('dimension_type', sa.String(50), nullable=False),
        sa.Column('dimension_id', sa.String(255), nullable=False),
        sa.Column('dimension_name', sa.String(500), nullable=True),

        # Attribution metrics
        sa.Column('attributed_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('attributed_deals', sa.Float(), server_default='0', nullable=False),
        sa.Column('attributed_pipeline_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Touchpoint metrics
        sa.Column('touchpoint_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('first_touch_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_touch_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('assisted_count', sa.Integer(), server_default='0', nullable=False),

        # Spend
        sa.Column('spend_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Calculated ROAS
        sa.Column('attributed_roas', sa.Float(), nullable=True),

        # Unique contacts
        sa.Column('unique_contacts', sa.Integer(), server_default='0', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'tenant_id', 'date', 'attribution_model', 'dimension_type', 'dimension_id',
            name='uq_daily_attributed_rev'
        ),
    )

    op.create_index('ix_daily_attributed_rev_tenant_date', 'daily_attributed_revenue', ['tenant_id', 'date'])
    op.create_index('ix_daily_attributed_rev_model', 'daily_attributed_revenue', ['tenant_id', 'attribution_model', 'date'])
    op.create_index('ix_daily_attributed_rev_dimension', 'daily_attributed_revenue', ['tenant_id', 'dimension_type', 'dimension_id', 'date'])

    # ==========================================================================
    # conversion_paths - Aggregated path statistics
    # ==========================================================================
    op.create_table(
        'conversion_paths',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Path identifier
        sa.Column('path_hash', sa.String(64), nullable=False),
        sa.Column('path_string', sa.Text(), nullable=False),
        sa.Column('path_type', sa.String(50), nullable=False),

        # Path structure
        sa.Column('path_length', sa.Integer(), nullable=False),
        sa.Column('unique_channels', sa.Integer(), nullable=False),
        sa.Column('first_channel', sa.String(100), nullable=True),
        sa.Column('last_channel', sa.String(100), nullable=True),

        # Period
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),

        # Conversion metrics
        sa.Column('conversions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('avg_deal_size_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Time metrics
        sa.Column('avg_time_to_conversion', sa.Float(), nullable=True),
        sa.Column('min_time_to_conversion', sa.Float(), nullable=True),
        sa.Column('max_time_to_conversion', sa.Float(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'tenant_id', 'path_hash', 'path_type', 'period_start', 'period_end',
            name='uq_conversion_path'
        ),
    )

    op.create_index('ix_conversion_paths_tenant_period', 'conversion_paths', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('ix_conversion_paths_hash', 'conversion_paths', ['tenant_id', 'path_hash'])
    op.create_index('ix_conversion_paths_conversions', 'conversion_paths', ['tenant_id', 'conversions'])

    # ==========================================================================
    # attribution_snapshots - Historical comparison
    # ==========================================================================
    op.create_table(
        'attribution_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Snapshot metadata
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('snapshot_type', sa.String(50), nullable=False),
        sa.Column('attribution_model', sa.String(50), nullable=False),

        # Period covered
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),

        # Summary metrics
        sa.Column('total_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_deals', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_touchpoints', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unique_contacts', sa.Integer(), server_default='0', nullable=False),

        # Journey metrics
        sa.Column('avg_touches_per_conversion', sa.Float(), nullable=True),
        sa.Column('avg_time_to_conversion_hours', sa.Float(), nullable=True),
        sa.Column('avg_unique_channels', sa.Float(), nullable=True),

        # Top performers (JSON)
        sa.Column('top_campaigns', postgresql.JSONB(), nullable=True),
        sa.Column('top_platforms', postgresql.JSONB(), nullable=True),
        sa.Column('top_paths', postgresql.JSONB(), nullable=True),

        # Channel contribution
        sa.Column('channel_mix', postgresql.JSONB(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'tenant_id', 'snapshot_date', 'snapshot_type', 'attribution_model',
            name='uq_attribution_snapshot'
        ),
    )

    op.create_index('ix_attribution_snapshot_tenant_date', 'attribution_snapshots', ['tenant_id', 'snapshot_date'])
    op.create_index('ix_attribution_snapshot_model', 'attribution_snapshots', ['tenant_id', 'attribution_model', 'snapshot_date'])

    # ==========================================================================
    # channel_interactions - Channel transition matrix
    # ==========================================================================
    op.create_table(
        'channel_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Period
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),

        # Transition
        sa.Column('from_channel', sa.String(100), nullable=False),
        sa.Column('to_channel', sa.String(100), nullable=False),
        sa.Column('transition_type', sa.String(50), nullable=False),

        # Metrics
        sa.Column('transition_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unique_journeys', sa.Integer(), server_default='0', nullable=False),

        # Attributed revenue
        sa.Column('attributed_revenue_cents', sa.BigInteger(), server_default='0', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'tenant_id', 'period_start', 'period_end', 'from_channel', 'to_channel', 'transition_type',
            name='uq_channel_interaction'
        ),
    )

    op.create_index('ix_channel_interaction_tenant_period', 'channel_interactions', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('ix_channel_interaction_from', 'channel_interactions', ['tenant_id', 'from_channel'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('channel_interactions')
    op.drop_table('attribution_snapshots')
    op.drop_table('conversion_paths')
    op.drop_table('daily_attributed_revenue')
