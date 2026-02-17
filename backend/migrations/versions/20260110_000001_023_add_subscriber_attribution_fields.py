"""Add subscriber attribution fields for CAPI

Revision ID: 023_subscriber_attribution
Revises: 022_landing_cms
Create Date: 2026-01-10 00:00:01.000000

This migration adds platform-specific click IDs, lead scoring,
and CAPI tracking fields to the landing_page_subscribers table
for full attribution and conversion tracking.

New fields:
- email_hash: SHA256 for deduplication
- phone: Contact phone number
- utm_term, utm_content: Additional UTM parameters
- landing_url: Full landing page URL
- fbclid, gclid, ttclid, sccid, fbc, fbp: Platform click IDs
- attributed_platform: Detected ad platform
- lead_score: Lead quality score (0-100)
- capi_sent, capi_results: CAPI tracking
- verified_at: Email verification timestamp
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '023_subscriber_attribution'
down_revision = '022_landing_cms'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to landing_page_subscribers table

    # Email hash for deduplication
    op.add_column('landing_page_subscribers',
        sa.Column('email_hash', sa.String(64), nullable=True)
    )

    # Phone number
    op.add_column('landing_page_subscribers',
        sa.Column('phone', sa.String(20), nullable=True)
    )

    # Additional UTM parameters
    op.add_column('landing_page_subscribers',
        sa.Column('utm_term', sa.String(100), nullable=True)
    )
    op.add_column('landing_page_subscribers',
        sa.Column('utm_content', sa.String(100), nullable=True)
    )

    # Landing URL
    op.add_column('landing_page_subscribers',
        sa.Column('landing_url', sa.String(1000), nullable=True)
    )

    # Platform-specific click IDs (CRITICAL for conversion attribution)
    op.add_column('landing_page_subscribers',
        sa.Column('fbclid', sa.String(255), nullable=True)  # Meta/Facebook
    )
    op.add_column('landing_page_subscribers',
        sa.Column('gclid', sa.String(255), nullable=True)  # Google
    )
    op.add_column('landing_page_subscribers',
        sa.Column('ttclid', sa.String(255), nullable=True)  # TikTok
    )
    op.add_column('landing_page_subscribers',
        sa.Column('sccid', sa.String(255), nullable=True)  # Snapchat
    )
    op.add_column('landing_page_subscribers',
        sa.Column('fbc', sa.String(255), nullable=True)  # Meta browser cookie
    )
    op.add_column('landing_page_subscribers',
        sa.Column('fbp', sa.String(255), nullable=True)  # Meta pixel cookie
    )

    # Detected platform
    op.add_column('landing_page_subscribers',
        sa.Column('attributed_platform', sa.String(20), nullable=True)
    )

    # Lead scoring
    op.add_column('landing_page_subscribers',
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0')
    )

    # CAPI tracking
    op.add_column('landing_page_subscribers',
        sa.Column('capi_sent', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('landing_page_subscribers',
        sa.Column('capi_results', sa.Text(), nullable=True)
    )

    # Email verification timestamp
    op.add_column('landing_page_subscribers',
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create new indexes
    op.create_index('ix_subscriber_platform', 'landing_page_subscribers', ['attributed_platform'])
    op.create_index('ix_subscriber_lead_score', 'landing_page_subscribers', ['lead_score'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('ix_subscriber_lead_score', table_name='landing_page_subscribers')
    op.drop_index('ix_subscriber_platform', table_name='landing_page_subscribers')

    # Drop new columns
    op.drop_column('landing_page_subscribers', 'verified_at')
    op.drop_column('landing_page_subscribers', 'capi_results')
    op.drop_column('landing_page_subscribers', 'capi_sent')
    op.drop_column('landing_page_subscribers', 'lead_score')
    op.drop_column('landing_page_subscribers', 'attributed_platform')
    op.drop_column('landing_page_subscribers', 'fbp')
    op.drop_column('landing_page_subscribers', 'fbc')
    op.drop_column('landing_page_subscribers', 'sccid')
    op.drop_column('landing_page_subscribers', 'ttclid')
    op.drop_column('landing_page_subscribers', 'gclid')
    op.drop_column('landing_page_subscribers', 'fbclid')
    op.drop_column('landing_page_subscribers', 'landing_url')
    op.drop_column('landing_page_subscribers', 'utm_content')
    op.drop_column('landing_page_subscribers', 'utm_term')
    op.drop_column('landing_page_subscribers', 'phone')
    op.drop_column('landing_page_subscribers', 'email_hash')
