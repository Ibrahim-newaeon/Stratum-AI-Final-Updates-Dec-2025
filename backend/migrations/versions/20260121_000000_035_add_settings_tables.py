"""Add settings tables (webhooks, notifications, changelog, slack)

Revision ID: 035_add_settings_tables
Revises: 034_add_rls_coverage_gaps
Create Date: 2026-01-21 00:00:00.000000

Tables:
- webhooks: Outbound webhook endpoint configuration
- webhook_deliveries: Webhook delivery attempt logs
- notifications: In-app notification system
- changelog_entries: Product changelog/release notes
- changelog_read_status: User read status for changelog entries
- slack_integrations: Slack workspace integration settings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '035_add_settings_tables'
down_revision = "034_add_rls_coverage_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # Webhook Status Enum
    # =========================================================================
    webhook_status = postgresql.ENUM('active', 'paused', 'failed', name='webhook_status', create_type=False)
    webhook_status.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Notification Type Enum
    # =========================================================================
    notification_type = postgresql.ENUM('info', 'warning', 'error', 'success', 'alert', name='notification_type', create_type=False)
    notification_type.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Notification Category Enum
    # =========================================================================
    notification_category = postgresql.ENUM('system', 'campaign', 'trust_gate', 'billing', 'security', 'integration', name='notification_category', create_type=False)
    notification_category.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Changelog Type Enum
    # =========================================================================
    changelog_type = postgresql.ENUM('feature', 'improvement', 'fix', 'security', 'deprecation', name='changelog_type', create_type=False)
    changelog_type.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Webhooks - Outbound webhook endpoint configuration
    # =========================================================================
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Endpoint configuration
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('secret', sa.String(255), nullable=True),

        # Event subscriptions (list of event types)
        sa.Column('events', postgresql.JSONB(), server_default='[]', nullable=False),

        # Status and health
        sa.Column('status', sa.Enum('active', 'paused', 'failed', name='webhook_status'), server_default='active', nullable=False),
        sa.Column('failure_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_reason', sa.Text(), nullable=True),

        # Custom headers
        sa.Column('headers', postgresql.JSONB(), server_default='{}', nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_webhooks_tenant_status', 'webhooks', ['tenant_id', 'status'])

    # =========================================================================
    # Webhook Deliveries - Delivery attempt logs
    # =========================================================================
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),

        # Event details
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),

        # Delivery status
        sa.Column('success', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timing
        sa.Column('duration_ms', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_webhook_deliveries_webhook_created', 'webhook_deliveries', ['webhook_id', 'created_at'])

    # =========================================================================
    # Notifications - In-app notification system
    # =========================================================================
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),  # Null = broadcast

        # Content
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),

        # Classification
        sa.Column('type', sa.Enum('info', 'warning', 'error', 'success', 'alert', name='notification_type'), server_default='info', nullable=False),
        sa.Column('category', sa.Enum('system', 'campaign', 'trust_gate', 'billing', 'security', 'integration', name='notification_category'), server_default='system', nullable=False),

        # Status
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),

        # Action link
        sa.Column('action_url', sa.String(2048), nullable=True),
        sa.Column('action_label', sa.String(100), nullable=True),

        # Extra data (metadata is reserved in SQLAlchemy)
        sa.Column('extra_data', postgresql.JSONB(), server_default='{}', nullable=True),

        # Expiration
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_notifications_user_unread', 'notifications', ['user_id', 'is_read'])
    op.create_index('ix_notifications_tenant_created', 'notifications', ['tenant_id', 'created_at'])

    # =========================================================================
    # Changelog Entries - Product changelog/release notes
    # =========================================================================
    op.create_table(
        'changelog_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # Version info
        sa.Column('version', sa.String(50), nullable=False),

        # Content
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),

        # Classification
        sa.Column('type', sa.Enum('feature', 'improvement', 'fix', 'security', 'deprecation', name='changelog_type'), server_default='feature', nullable=False),

        # Publishing
        sa.Column('is_published', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),

        # Rich content
        sa.Column('image_url', sa.String(2048), nullable=True),
        sa.Column('video_url', sa.String(2048), nullable=True),
        sa.Column('docs_url', sa.String(2048), nullable=True),

        # Tags
        sa.Column('tags', postgresql.JSONB(), server_default='[]', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_changelog_published', 'changelog_entries', ['is_published', 'published_at'])

    # =========================================================================
    # Changelog Read Status - User read tracking
    # =========================================================================
    op.create_table(
        'changelog_read_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('changelog_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changelog_id'], ['changelog_entries.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_changelog_read_user', 'changelog_read_status', ['user_id', 'changelog_id'], unique=True)

    # =========================================================================
    # Slack Integrations - Slack workspace settings per tenant
    # =========================================================================
    op.create_table(
        'slack_integrations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Webhook URL
        sa.Column('webhook_url', sa.String(2048), nullable=False),

        # Channel configuration
        sa.Column('channel_name', sa.String(100), nullable=True),

        # Notification preferences
        sa.Column('notify_trust_gate', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notify_anomalies', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notify_signal_health', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('notify_daily_summary', sa.Boolean(), server_default='true', nullable=False),

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_test_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_test_success', sa.Boolean(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_slack_integrations_tenant', 'slack_integrations', ['tenant_id'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table('slack_integrations')
    op.drop_table('changelog_read_status')
    op.drop_table('changelog_entries')
    op.drop_table('notifications')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS changelog_type')
    op.execute('DROP TYPE IF EXISTS notification_category')
    op.execute('DROP TYPE IF EXISTS notification_type')
    op.execute('DROP TYPE IF EXISTS webhook_status')
