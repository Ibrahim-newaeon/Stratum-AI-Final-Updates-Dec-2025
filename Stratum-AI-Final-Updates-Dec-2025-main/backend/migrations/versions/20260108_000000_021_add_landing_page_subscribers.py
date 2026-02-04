"""Add landing page subscribers table

Revision ID: 021_landing_subscribers
Revises: 20260107_000001
Create Date: 2026-01-08 00:00:00.000000

This migration adds the landing_page_subscribers table for collecting
email signups from landing pages for superadmin review.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '021_landing_subscribers'
down_revision = '20260107_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create landing_page_subscribers table
    op.create_table(
        'landing_page_subscribers',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),

        # Contact Information
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),

        # Source tracking
        sa.Column('source_page', sa.String(50), nullable=False, server_default='landing'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('referrer_url', sa.String(500), nullable=True),

        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),

        # Admin notes
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),

        # Conversion tracking
        sa.Column('converted_to_tenant_id', sa.Integer(), nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['converted_to_tenant_id'], ['tenants.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('ix_subscriber_email', 'landing_page_subscribers', ['email'])
    op.create_index('ix_subscriber_status', 'landing_page_subscribers', ['status', 'created_at'])
    op.create_index('ix_subscriber_source', 'landing_page_subscribers', ['source_page', 'language'])


def downgrade() -> None:
    op.drop_index('ix_subscriber_source', table_name='landing_page_subscribers')
    op.drop_index('ix_subscriber_status', table_name='landing_page_subscribers')
    op.drop_index('ix_subscriber_email', table_name='landing_page_subscribers')
    op.drop_table('landing_page_subscribers')
