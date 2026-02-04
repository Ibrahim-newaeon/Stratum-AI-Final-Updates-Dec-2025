"""Add autopilot enforcement tables

Revision ID: 020_autopilot_enforcement
Revises: 020_audit_services
Create Date: 2026-01-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '020_autopilot_enforcement'
down_revision = '020_audit_services'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enforcement Settings table - tenant-level enforcement configuration
    op.create_table(
        'autopilot_enforcement_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('enforcement_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('default_mode', sa.String(20), server_default='advisory', nullable=False),

        # Budget thresholds
        sa.Column('max_daily_budget', sa.Float(), nullable=True),
        sa.Column('max_campaign_budget', sa.Float(), nullable=True),
        sa.Column('budget_increase_limit_pct', sa.Float(), server_default='30.0', nullable=False),

        # ROAS thresholds
        sa.Column('min_roas_threshold', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('roas_lookback_days', sa.Integer(), server_default='7', nullable=False),

        # Frequency settings
        sa.Column('max_budget_changes_per_day', sa.Integer(), server_default='5', nullable=False),
        sa.Column('min_hours_between_changes', sa.Integer(), server_default='4', nullable=False),

        # Custom rules (JSON array)
        sa.Column('custom_rules', postgresql.JSONB(), server_default='[]', nullable=False),

        # Notification settings
        sa.Column('notify_on_block', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notify_on_override', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notification_channels', postgresql.JSONB(), server_default='["email"]', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    op.create_index(
        'ix_autopilot_enforcement_settings_tenant_id',
        'autopilot_enforcement_settings',
        ['tenant_id'],
        unique=True,
    )

    # Enforcement Intervention Log table - audit log for all enforcement actions
    op.create_table(
        'autopilot_intervention_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Action details
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=True),

        # Violation details
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('violation_message', sa.Text(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),

        # Intervention details
        sa.Column('intervention_action', sa.String(50), nullable=False),
        sa.Column('enforcement_mode', sa.String(20), nullable=False),

        # User override info
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('confirmation_token', sa.String(255), nullable=True),

        # Additional context
        sa.Column('details', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('proposed_value', postgresql.JSONB(), nullable=True),
        sa.Column('current_value', postgresql.JSONB(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index(
        'ix_autopilot_intervention_log_tenant_timestamp',
        'autopilot_intervention_log',
        ['tenant_id', 'timestamp'],
    )

    op.create_index(
        'ix_autopilot_intervention_log_entity',
        'autopilot_intervention_log',
        ['tenant_id', 'entity_type', 'entity_id'],
    )

    op.create_index(
        'ix_autopilot_intervention_log_violation_type',
        'autopilot_intervention_log',
        ['tenant_id', 'violation_type'],
    )

    # Pending Confirmations table - for soft_block confirmations
    op.create_table(
        'autopilot_pending_confirmations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('confirmation_token', sa.String(255), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('violations', postgresql.JSONB(), nullable=False),
        sa.Column('proposed_value', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_by_user_id', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['confirmed_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index(
        'ix_autopilot_pending_confirmations_token',
        'autopilot_pending_confirmations',
        ['confirmation_token'],
        unique=True,
    )

    op.create_index(
        'ix_autopilot_pending_confirmations_tenant',
        'autopilot_pending_confirmations',
        ['tenant_id', 'expires_at'],
    )


def downgrade() -> None:
    op.drop_table('autopilot_pending_confirmations')
    op.drop_table('autopilot_intervention_log')
    op.drop_table('autopilot_enforcement_settings')
