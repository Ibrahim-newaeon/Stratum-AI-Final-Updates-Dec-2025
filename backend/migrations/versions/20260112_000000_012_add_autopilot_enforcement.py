"""Add autopilot enforcement tables

Revision ID: 012_add_autopilot_enforcement
Revises: 011_add_usp_layer_tables
Create Date: 2026-01-12 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_add_autopilot_enforcement'
down_revision = '025_campaign_builder'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    enforcement_mode_enum = postgresql.ENUM(
        'advisory', 'soft_block', 'hard_block',
        name='enforcement_mode',
        create_type=False,
    )
    violation_type_enum = postgresql.ENUM(
        'budget_exceeded', 'roas_below_threshold', 'daily_spend_limit',
        'campaign_pause_required', 'frequency_cap_exceeded',
        name='violation_type',
        create_type=False,
    )
    intervention_action_enum = postgresql.ENUM(
        'warned', 'blocked', 'auto_paused', 'override_logged',
        'notification_sent', 'kill_switch_changed',
        name='intervention_action',
        create_type=False,
    )

    # Create enum types in PostgreSQL
    op.execute("CREATE TYPE enforcement_mode AS ENUM ('advisory', 'soft_block', 'hard_block')")
    op.execute("CREATE TYPE violation_type AS ENUM ('budget_exceeded', 'roas_below_threshold', 'daily_spend_limit', 'campaign_pause_required', 'frequency_cap_exceeded')")
    op.execute("CREATE TYPE intervention_action AS ENUM ('warned', 'blocked', 'auto_paused', 'override_logged', 'notification_sent', 'kill_switch_changed')")

    # Create tenant_enforcement_settings table
    op.create_table(
        'tenant_enforcement_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('enforcement_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_mode', enforcement_mode_enum, nullable=False, server_default='advisory'),
        sa.Column('max_daily_budget', sa.Float(), nullable=True),
        sa.Column('max_campaign_budget', sa.Float(), nullable=True),
        sa.Column('budget_increase_limit_pct', sa.Float(), nullable=False, server_default='30.0'),
        sa.Column('min_roas_threshold', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('roas_lookback_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('max_budget_changes_per_day', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('min_hours_between_changes', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index('ix_tenant_enforcement_settings_tenant_id', 'tenant_enforcement_settings', ['tenant_id'])

    # Create tenant_enforcement_rules table
    op.create_table(
        'tenant_enforcement_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('settings_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('rule_type', violation_type_enum, nullable=False),
        sa.Column('threshold_value', sa.Float(), nullable=False),
        sa.Column('enforcement_mode', enforcement_mode_enum, nullable=False, server_default='advisory'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['settings_id'], ['tenant_enforcement_settings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'rule_id', name='uq_tenant_rule_id'),
    )
    op.create_index('ix_tenant_enforcement_rules_tenant_id', 'tenant_enforcement_rules', ['tenant_id'])
    op.create_index('ix_tenant_enforcement_rules_settings_id', 'tenant_enforcement_rules', ['settings_id'])

    # Create enforcement_audit_logs table
    op.create_table(
        'enforcement_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('violation_type', violation_type_enum, nullable=False),
        sa.Column('intervention_action', intervention_action_enum, nullable=False),
        sa.Column('enforcement_mode', enforcement_mode_enum, nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_enforcement_audit_logs_tenant_id', 'enforcement_audit_logs', ['tenant_id'])
    op.create_index('ix_enforcement_audit_logs_timestamp', 'enforcement_audit_logs', ['timestamp'])
    op.create_index('ix_enforcement_audit_logs_action_type', 'enforcement_audit_logs', ['action_type'])

    # Create pending_confirmation_tokens table
    op.create_table(
        'pending_confirmation_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('violations', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_pending_confirmation_tokens_token', 'pending_confirmation_tokens', ['token'])
    op.create_index('ix_pending_confirmation_tokens_tenant_id', 'pending_confirmation_tokens', ['tenant_id'])
    op.create_index('ix_pending_confirmation_tokens_expires_at', 'pending_confirmation_tokens', ['expires_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('pending_confirmation_tokens')
    op.drop_table('enforcement_audit_logs')
    op.drop_table('tenant_enforcement_rules')
    op.drop_table('tenant_enforcement_settings')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS intervention_action")
    op.execute("DROP TYPE IF EXISTS violation_type")
    op.execute("DROP TYPE IF EXISTS enforcement_mode")
