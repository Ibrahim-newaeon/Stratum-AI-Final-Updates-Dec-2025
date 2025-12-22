"""Add PixelEventLog model for Pixel vs CAPI dedupe tracking

Revision ID: 005
Revises: 004
Create Date: 2024-12-22 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Create pixel_event_logs table (for Pixel vs CAPI dedupe comparison)
    # =========================================================================
    op.create_table(
        'pixel_event_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Event identifiers
        sa.Column('event_id', sa.String(length=100), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('event_time', sa.Integer(), nullable=False),

        # Context
        sa.Column('event_source_url', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key to tenants
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Create indexes for dedupe queries
    op.create_index('ix_pixel_event_id', 'pixel_event_logs', ['event_id'])
    op.create_index('ix_pixel_tenant_date', 'pixel_event_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_pixel_event_name', 'pixel_event_logs', ['tenant_id', 'event_name', 'created_at'])
    op.create_index('ix_pixel_event_id_tenant', 'pixel_event_logs', ['tenant_id', 'event_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_pixel_event_id_tenant', table_name='pixel_event_logs')
    op.drop_index('ix_pixel_event_name', table_name='pixel_event_logs')
    op.drop_index('ix_pixel_tenant_date', table_name='pixel_event_logs')
    op.drop_index('ix_pixel_event_id', table_name='pixel_event_logs')

    # Drop table
    op.drop_table('pixel_event_logs')
