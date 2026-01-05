"""Add Automated Reporting tables

Revision ID: 019_add_automated_reporting_tables
Revises: 018_add_data_driven_attribution_tables
Create Date: 2026-01-06 00:06:00.000000

This migration adds:
- report_type enum
- report_format enum
- schedule_frequency enum
- delivery_channel enum
- execution_status enum
- delivery_status enum
- report_templates: Configurable report definitions
- scheduled_reports: Report scheduling configuration
- report_executions: History of report runs
- report_deliveries: Delivery tracking per channel
- delivery_channel_configs: Tenant-level channel configuration
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '019_add_automated_reporting_tables'
down_revision = '018_add_data_driven_attribution_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Report Type Enum
    # ==========================================================================
    report_type = postgresql.ENUM(
        'campaign_performance', 'attribution_summary', 'pacing_status',
        'profit_roas', 'pipeline_metrics', 'executive_summary', 'custom',
        name='report_type',
        create_type=False
    )
    report_type.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Report Format Enum
    # ==========================================================================
    report_format = postgresql.ENUM(
        'pdf', 'csv', 'excel', 'json', 'html',
        name='report_format',
        create_type=False
    )
    report_format.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Schedule Frequency Enum
    # ==========================================================================
    schedule_frequency = postgresql.ENUM(
        'daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'custom',
        name='schedule_frequency',
        create_type=False
    )
    schedule_frequency.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Delivery Channel Enum
    # ==========================================================================
    delivery_channel = postgresql.ENUM(
        'email', 'slack', 'teams', 'webhook', 's3',
        name='delivery_channel',
        create_type=False
    )
    delivery_channel.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Execution Status Enum
    # ==========================================================================
    execution_status = postgresql.ENUM(
        'pending', 'running', 'completed', 'failed', 'cancelled',
        name='execution_status',
        create_type=False
    )
    execution_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Delivery Status Enum
    # ==========================================================================
    delivery_status = postgresql.ENUM(
        'pending', 'sent', 'delivered', 'failed', 'bounced',
        name='delivery_status',
        create_type=False
    )
    delivery_status.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # report_templates - Configurable report definitions
    # ==========================================================================
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Template identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', report_type, nullable=False),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),

        # Configuration
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),

        # Output settings
        sa.Column('default_format', report_format, nullable=False, server_default="'pdf'"),
        sa.Column('available_formats', postgresql.ARRAY(sa.String()), nullable=False, server_default="'{pdf,csv}'"),

        # Styling
        sa.Column('template_html', sa.Text(), nullable=True),
        sa.Column('chart_config', postgresql.JSONB(), nullable=True),

        # Metadata
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('last_modified_by_user_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['last_modified_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_report_template_name'),
    )

    op.create_index('ix_report_template_tenant', 'report_templates', ['tenant_id'])
    op.create_index('ix_report_template_type', 'report_templates', ['tenant_id', 'report_type'])

    # ==========================================================================
    # scheduled_reports - Report scheduling configuration
    # ==========================================================================
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Schedule identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false'),

        # Schedule configuration
        sa.Column('frequency', schedule_frequency, nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default="'UTC'"),

        # Schedule timing
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('day_of_month', sa.Integer(), nullable=True),
        sa.Column('hour', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('minute', sa.Integer(), nullable=False, server_default='0'),

        # Report configuration overrides
        sa.Column('format_override', report_format, nullable=True),
        sa.Column('config_override', postgresql.JSONB(), nullable=True),

        # Date range
        sa.Column('date_range_type', sa.String(50), nullable=False, server_default="'last_30_days'"),

        # Delivery configuration
        sa.Column('delivery_channels', postgresql.ARRAY(sa.String()), nullable=False, server_default="'{email}'"),
        sa.Column('delivery_config', postgresql.JSONB(), nullable=False, server_default='{}'),

        # Execution tracking
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', execution_status, nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),

        # Metadata
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_scheduled_report_tenant', 'scheduled_reports', ['tenant_id'])
    op.create_index('ix_scheduled_report_template', 'scheduled_reports', ['template_id'])
    op.create_index(
        'ix_scheduled_report_next_run',
        'scheduled_reports',
        ['next_run_at'],
        postgresql_where=sa.text("is_active = true AND is_paused = false")
    )

    # ==========================================================================
    # report_executions - History of report runs
    # ==========================================================================
    op.create_table(
        'report_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Execution details
        sa.Column('execution_type', sa.String(50), nullable=False),
        sa.Column('status', execution_status, nullable=False, server_default="'pending'"),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),

        # Report parameters
        sa.Column('report_type', report_type, nullable=False),
        sa.Column('format', report_format, nullable=False),
        sa.Column('date_range_start', sa.Date(), nullable=False),
        sa.Column('date_range_end', sa.Date(), nullable=False),
        sa.Column('config_used', postgresql.JSONB(), nullable=True),

        # Output
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('file_url', sa.Text(), nullable=True),
        sa.Column('file_url_expires_at', sa.DateTime(timezone=True), nullable=True),

        # Report data summary
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('metrics_summary', postgresql.JSONB(), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),

        # Triggered by
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schedule_id'], ['scheduled_reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_report_execution_tenant', 'report_executions', ['tenant_id', 'started_at'])
    op.create_index('ix_report_execution_status', 'report_executions', ['tenant_id', 'status'])
    op.create_index('ix_report_execution_schedule', 'report_executions', ['schedule_id'])

    # ==========================================================================
    # report_deliveries - Delivery tracking per channel
    # ==========================================================================
    op.create_table(
        'report_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Delivery details
        sa.Column('channel', delivery_channel, nullable=False),
        sa.Column('status', delivery_status, nullable=False, server_default="'pending'"),

        # Recipient info
        sa.Column('recipient', sa.String(500), nullable=False),
        sa.Column('recipient_type', sa.String(50), nullable=True),

        # Timing
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),

        # Delivery metadata
        sa.Column('message_id', sa.String(255), nullable=True),
        sa.Column('delivery_response', postgresql.JSONB(), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['execution_id'], ['report_executions.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_report_delivery_execution', 'report_deliveries', ['execution_id'])
    op.create_index('ix_report_delivery_status', 'report_deliveries', ['tenant_id', 'status'])
    op.create_index('ix_report_delivery_channel', 'report_deliveries', ['tenant_id', 'channel'])

    # ==========================================================================
    # delivery_channel_configs - Tenant-level channel configuration
    # ==========================================================================
    op.create_table(
        'delivery_channel_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Channel
        sa.Column('channel', delivery_channel, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),

        # Configuration (encrypted sensitive data)
        sa.Column('config', postgresql.JSONB(), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'channel', 'name', name='uq_delivery_config'),
    )

    op.create_index('ix_delivery_config_tenant', 'delivery_channel_configs', ['tenant_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('delivery_channel_configs')
    op.drop_table('report_deliveries')
    op.drop_table('report_executions')
    op.drop_table('scheduled_reports')
    op.drop_table('report_templates')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS delivery_status')
    op.execute('DROP TYPE IF EXISTS execution_status')
    op.execute('DROP TYPE IF EXISTS delivery_channel')
    op.execute('DROP TYPE IF EXISTS schedule_frequency')
    op.execute('DROP TYPE IF EXISTS report_format')
    op.execute('DROP TYPE IF EXISTS report_type')
