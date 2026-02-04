"""Add CAPI delivery logging and DLQ tables (P0 Gap Fix)

Revision ID: 20260107_000001
Revises: 020_autopilot_enforcement
Create Date: 2026-01-07

This migration adds tables for:
- CAPI delivery logging (persistent audit trail)
- Dead Letter Queue (failed event recovery)
- Deduplication persistence (cross-process dedupe)
- Daily aggregated stats (dashboard optimization)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260107_000001'
down_revision = '020_autopilot_enforcement'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # CAPI Delivery Logs - Persistent audit trail
    # ==========================================================================
    op.create_table(
        'capi_delivery_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=True),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivery_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(255), nullable=True),
        sa.Column('platform_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_data_hash', sa.String(64), nullable=True),
        sa.Column('event_value_cents', sa.BigInteger(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for capi_delivery_logs
    op.create_index('ix_capi_delivery_tenant_time', 'capi_delivery_logs', ['tenant_id', 'delivery_time'])
    op.create_index('ix_capi_delivery_platform', 'capi_delivery_logs', ['tenant_id', 'platform', 'delivery_time'])
    op.create_index('ix_capi_delivery_status', 'capi_delivery_logs', ['tenant_id', 'status', 'delivery_time'])
    op.create_index('ix_capi_delivery_event_id', 'capi_delivery_logs', ['tenant_id', 'platform', 'event_id'])

    # ==========================================================================
    # Dead Letter Queue - Failed event recovery
    # ==========================================================================
    op.create_table(
        'capi_dead_letter_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=True),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=False),
        sa.Column('failure_category', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('platform_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('first_failure_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for capi_dead_letter_queue
    op.create_index('ix_dlq_pending', 'capi_dead_letter_queue', ['tenant_id', 'status', 'last_failure_at'])
    op.create_index('ix_dlq_platform', 'capi_dead_letter_queue', ['tenant_id', 'platform', 'status'])
    op.create_index('ix_dlq_category', 'capi_dead_letter_queue', ['tenant_id', 'failure_category', 'first_failure_at'])

    # ==========================================================================
    # Event Deduplication Records - Persistent cross-process dedupe
    # ==========================================================================
    op.create_table(
        'capi_event_dedupe',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('dedupe_key', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=True),
        sa.Column('event_value_cents', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for capi_event_dedupe
    op.create_index('ix_dedupe_key', 'capi_event_dedupe', ['tenant_id', 'dedupe_key'], unique=True)
    op.create_index('ix_dedupe_expires', 'capi_event_dedupe', ['expires_at'])

    # ==========================================================================
    # Daily Delivery Stats - Aggregated metrics for dashboards
    # ==========================================================================
    op.create_table(
        'capi_delivery_daily_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('total_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retried_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deduplicated_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate_pct', sa.Float(), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('p50_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('p99_latency_ms', sa.Float(), nullable=True),
        sa.Column('max_latency_ms', sa.Float(), nullable=True),
        sa.Column('total_value_cents', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('avg_value_cents', sa.Integer(), nullable=True),
        sa.Column('error_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for capi_delivery_daily_stats
    op.create_index('ix_delivery_stats_date', 'capi_delivery_daily_stats', ['tenant_id', 'date', 'platform'])
    op.create_index('ix_delivery_stats_unique', 'capi_delivery_daily_stats', ['tenant_id', 'date', 'platform'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_delivery_stats_unique', table_name='capi_delivery_daily_stats')
    op.drop_index('ix_delivery_stats_date', table_name='capi_delivery_daily_stats')
    op.drop_table('capi_delivery_daily_stats')

    op.drop_index('ix_dedupe_expires', table_name='capi_event_dedupe')
    op.drop_index('ix_dedupe_key', table_name='capi_event_dedupe')
    op.drop_table('capi_event_dedupe')

    op.drop_index('ix_dlq_category', table_name='capi_dead_letter_queue')
    op.drop_index('ix_dlq_platform', table_name='capi_dead_letter_queue')
    op.drop_index('ix_dlq_pending', table_name='capi_dead_letter_queue')
    op.drop_table('capi_dead_letter_queue')

    op.drop_index('ix_capi_delivery_event_id', table_name='capi_delivery_logs')
    op.drop_index('ix_capi_delivery_status', table_name='capi_delivery_logs')
    op.drop_index('ix_capi_delivery_platform', table_name='capi_delivery_logs')
    op.drop_index('ix_capi_delivery_tenant_time', table_name='capi_delivery_logs')
    op.drop_table('capi_delivery_logs')
