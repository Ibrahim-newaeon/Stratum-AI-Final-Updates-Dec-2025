"""Add CapiQaLog model for EMQ tracking and data quality dashboard

Revision ID: 004
Revises: 003
Create Date: 2024-12-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Create capi_qa_logs table (source of truth for EMQ dashboard)
    # =========================================================================
    op.create_table(
        'capi_qa_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Event identifiers
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('event_time', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=100), nullable=False),
        sa.Column('action_source', sa.String(length=50), nullable=False, server_default='website'),

        # Platform identifiers
        sa.Column('pixel_id', sa.String(length=50), nullable=True),
        sa.Column('dataset_id', sa.String(length=50), nullable=True),
        sa.Column('platform', sa.String(length=20), nullable=False, server_default='meta'),

        # Identifier presence flags (for Match Coverage Score calculation)
        sa.Column('has_em', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_ph', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_external_id', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_fbp', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_fbc', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_ip', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_ua', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_fn', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_ln', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_ct', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_country', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_zp', sa.Boolean(), nullable=False, server_default='false'),

        # Match coverage score (0-100, weighted based on identifier presence)
        sa.Column('match_coverage_score', sa.Float(), nullable=False, server_default='0.0'),

        # Meta API response tracking
        sa.Column('meta_trace_id', sa.String(length=100), nullable=True),
        sa.Column('meta_success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('meta_error_code', sa.Integer(), nullable=True),
        sa.Column('meta_error_message', sa.Text(), nullable=True),
        sa.Column('meta_events_received', sa.Integer(), nullable=False, server_default='0'),

        # Raw payloads for debugging
        sa.Column('request_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key to tenants
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Create indexes for dashboard queries
    op.create_index('ix_capi_qa_tenant_date', 'capi_qa_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_capi_qa_event_name', 'capi_qa_logs', ['tenant_id', 'event_name', 'created_at'])
    op.create_index('ix_capi_qa_platform', 'capi_qa_logs', ['tenant_id', 'platform', 'created_at'])
    op.create_index('ix_capi_qa_event_id', 'capi_qa_logs', ['event_id'])
    op.create_index('ix_capi_qa_success', 'capi_qa_logs', ['tenant_id', 'meta_success', 'created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_capi_qa_success', table_name='capi_qa_logs')
    op.drop_index('ix_capi_qa_event_id', table_name='capi_qa_logs')
    op.drop_index('ix_capi_qa_platform', table_name='capi_qa_logs')
    op.drop_index('ix_capi_qa_event_name', table_name='capi_qa_logs')
    op.drop_index('ix_capi_qa_tenant_date', table_name='capi_qa_logs')

    # Drop table
    op.drop_table('capi_qa_logs')
