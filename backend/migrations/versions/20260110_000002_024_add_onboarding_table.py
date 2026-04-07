"""Add tenant_onboarding table

Revision ID: 024_add_onboarding
Revises: 023_add_subscriber_attribution_fields
Create Date: 2026-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024_add_onboarding'
down_revision = '023_subscriber_attribution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tenant_onboarding table."""
    op.create_table(
        'tenant_onboarding',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Overall status
        sa.Column('status', sa.String(50), nullable=False, server_default='not_started'),
        sa.Column('current_step', sa.String(50), nullable=False, server_default='business_profile'),
        sa.Column('completed_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Step 1: Business Profile
        sa.Column('industry', sa.String(50), nullable=True),
        sa.Column('industry_other', sa.String(255), nullable=True),
        sa.Column('monthly_ad_spend', sa.String(50), nullable=True),
        sa.Column('team_size', sa.String(50), nullable=True),
        sa.Column('company_website', sa.String(500), nullable=True),
        sa.Column('target_markets', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Step 2: Platform Selection
        sa.Column('selected_platforms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Step 3: Goals Setup
        sa.Column('primary_kpi', sa.String(50), nullable=True),
        sa.Column('target_roas', sa.Float(), nullable=True),
        sa.Column('target_cpa_cents', sa.Integer(), nullable=True),
        sa.Column('monthly_budget_cents', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(100), nullable=False, server_default='UTC'),

        # Step 4: Automation Preferences
        sa.Column('automation_mode', sa.String(50), nullable=True),
        sa.Column('auto_pause_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_scale_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_email', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_slack', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_whatsapp', sa.Boolean(), nullable=False, server_default='false'),

        # Step 5: Trust Gate Configuration
        sa.Column('trust_threshold_autopilot', sa.Integer(), nullable=False, server_default='70'),
        sa.Column('trust_threshold_alert', sa.Integer(), nullable=False, server_default='40'),
        sa.Column('require_approval_above', sa.Integer(), nullable=True),
        sa.Column('max_daily_actions', sa.Integer(), nullable=False, server_default='10'),

        # Additional preferences (flexible JSON)
        sa.Column('additional_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Timestamps
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # User who completed onboarding
        sa.Column('completed_by_user_id', sa.Integer(), nullable=True),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['users.id'], ondelete='SET NULL'),

        # Unique constraint
        sa.UniqueConstraint('tenant_id', name='uq_tenant_onboarding_tenant_id'),
    )

    # Create indexes
    op.create_index('ix_tenant_onboarding_tenant_id', 'tenant_onboarding', ['tenant_id'])
    op.create_index('ix_tenant_onboarding_status', 'tenant_onboarding', ['status'])


def downgrade() -> None:
    """Drop tenant_onboarding table."""
    op.drop_index('ix_tenant_onboarding_status', table_name='tenant_onboarding')
    op.drop_index('ix_tenant_onboarding_tenant_id', table_name='tenant_onboarding')
    op.drop_table('tenant_onboarding')
