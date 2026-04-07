"""Add CDP webhooks table

Revision ID: 027_cdp_webhooks
Revises: 026_cdp_tables
Create Date: 2026-01-13 19:00:00.000000

Tables:
- cdp_webhooks: Webhook destinations for CDP events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '027_cdp_webhooks'
down_revision = '026_cdp_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # CDP Webhooks - Webhook destinations for CDP events
    # =========================================================================
    op.create_table(
        'cdp_webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Webhook configuration
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('event_types', postgresql.JSONB(), server_default='[]', nullable=False),

        # Authentication
        sa.Column('secret_key', sa.String(64), nullable=True),  # For HMAC signature

        # State
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_count', sa.Integer(), server_default='0', nullable=False),

        # Retry configuration
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), server_default='30', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Indexes
    op.create_index('ix_cdp_webhooks_tenant', 'cdp_webhooks', ['tenant_id'])
    op.create_index('ix_cdp_webhooks_active', 'cdp_webhooks', ['tenant_id', 'is_active'])


def downgrade() -> None:
    op.drop_table('cdp_webhooks')
