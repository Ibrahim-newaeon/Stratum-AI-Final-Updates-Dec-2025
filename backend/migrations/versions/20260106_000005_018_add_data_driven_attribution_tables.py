"""Add Data-Driven Attribution tables

Revision ID: 018_add_data_driven_attribution_tables
Revises: 017
Create Date: 2026-01-06 00:05:00.000000

This migration adds:
- data_driven_model_type enum
- model_status enum
- trained_attribution_models: Stored ML attribution models
- model_training_runs: Training history and audit log
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_dd_attribution'
down_revision = '017_attribution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Data-Driven Model Type Enum
    # ==========================================================================
    data_driven_model_type = postgresql.ENUM(
        'markov_chain', 'shapley_value',
        name='data_driven_model_type',
        create_type=False
    )
    data_driven_model_type.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Model Status Enum
    # ==========================================================================
    model_status = postgresql.ENUM(
        'training', 'active', 'archived', 'failed',
        name='model_status',
        create_type=False
    )
    model_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # trained_attribution_models - Stored ML models
    # ==========================================================================
    op.create_table(
        'trained_attribution_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Model identification
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('model_type', data_driven_model_type, nullable=False),
        sa.Column('channel_type', sa.String(50), nullable=False),

        # Status
        sa.Column('status', model_status, nullable=False, server_default='training'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),

        # Training period
        sa.Column('training_start', sa.Date(), nullable=False),
        sa.Column('training_end', sa.Date(), nullable=False),

        # Training statistics
        sa.Column('journey_count', sa.Integer(), nullable=True),
        sa.Column('converting_journeys', sa.Integer(), nullable=True),
        sa.Column('unique_channels', sa.Integer(), nullable=True),

        # Model results
        sa.Column('attribution_weights', postgresql.JSONB(), nullable=True),
        sa.Column('model_data', postgresql.JSONB(), nullable=True),

        # Markov Chain specific
        sa.Column('removal_effects', postgresql.JSONB(), nullable=True),
        sa.Column('baseline_conversion_rate', sa.Float(), nullable=True),

        # Shapley Value specific
        sa.Column('shapley_values', postgresql.JSONB(), nullable=True),

        # Validation metrics
        sa.Column('validation_accuracy', sa.Float(), nullable=True),
        sa.Column('validation_period_start', sa.Date(), nullable=True),
        sa.Column('validation_period_end', sa.Date(), nullable=True),

        # Metadata
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_trained_model_tenant', 'trained_attribution_models', ['tenant_id'])
    op.create_index('ix_trained_model_active', 'trained_attribution_models', ['tenant_id', 'is_active'])
    op.create_index('ix_trained_model_type', 'trained_attribution_models', ['tenant_id', 'model_type'])

    # ==========================================================================
    # model_training_runs - Training history
    # ==========================================================================
    op.create_table(
        'model_training_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Run details
        sa.Column('model_type', data_driven_model_type, nullable=False),
        sa.Column('channel_type', sa.String(50), nullable=False),
        sa.Column('status', model_status, nullable=False, server_default='training'),

        # Training period
        sa.Column('training_start', sa.Date(), nullable=False),
        sa.Column('training_end', sa.Date(), nullable=False),

        # Configuration
        sa.Column('include_non_converting', sa.Boolean(), server_default='true'),
        sa.Column('min_journeys', sa.Integer(), server_default='100'),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),

        # Results
        sa.Column('journey_count', sa.Integer(), nullable=True),
        sa.Column('converting_journeys', sa.Integer(), nullable=True),
        sa.Column('unique_channels', sa.Integer(), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),

        # Triggered by
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['trained_attribution_models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_training_run_tenant', 'model_training_runs', ['tenant_id', 'started_at'])
    op.create_index('ix_training_run_status', 'model_training_runs', ['tenant_id', 'status'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('model_training_runs')
    op.drop_table('trained_attribution_models')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS model_status')
    op.execute('DROP TYPE IF EXISTS data_driven_model_type')
