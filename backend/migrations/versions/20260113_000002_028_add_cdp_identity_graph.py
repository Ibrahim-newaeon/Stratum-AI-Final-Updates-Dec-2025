"""Add CDP identity graph tables

Revision ID: 028_cdp_identity_graph
Revises: 027_cdp_webhooks
Create Date: 2026-01-13 20:00:00.000000

Tables:
- cdp_identity_links: Identity graph edges between identifiers
- cdp_profile_merges: Profile merge history for auditing
- cdp_canonical_identities: Golden identity for each profile
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '028_cdp_identity_graph'
down_revision = '027_cdp_webhooks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # CDP Identity Links - Graph edges between identifiers
    # =========================================================================
    op.create_table(
        'cdp_identity_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Source and target identifiers
        sa.Column('source_identifier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_identifier_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Link metadata
        sa.Column('link_type', sa.String(50), nullable=False, server_default='same_event'),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=False, server_default='1.00'),

        # Evidence for the link
        sa.Column('evidence', postgresql.JSONB(), server_default='{}', nullable=False),

        # State
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_identifier_id'], ['cdp_profile_identifiers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_identifier_id'], ['cdp_profile_identifiers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'source_identifier_id', 'target_identifier_id', name='uq_cdp_identity_links_source_target'),
    )

    # Indexes for identity links
    op.create_index('ix_cdp_identity_links_tenant', 'cdp_identity_links', ['tenant_id'])
    op.create_index('ix_cdp_identity_links_source', 'cdp_identity_links', ['source_identifier_id'])
    op.create_index('ix_cdp_identity_links_target', 'cdp_identity_links', ['target_identifier_id'])
    op.create_index('ix_cdp_identity_links_type', 'cdp_identity_links', ['tenant_id', 'link_type'])

    # =========================================================================
    # CDP Profile Merges - Merge history for auditing
    # =========================================================================
    op.create_table(
        'cdp_profile_merges',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Surviving profile (the one that remains)
        sa.Column('surviving_profile_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Merged profile ID (kept even after deletion)
        sa.Column('merged_profile_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Merge details
        sa.Column('merge_reason', sa.String(50), nullable=False, server_default='identity_match'),

        # Snapshot of merged profile before merge
        sa.Column('merged_profile_snapshot', postgresql.JSONB(), server_default='{}', nullable=False),

        # Triggering identifier
        sa.Column('triggering_identifier_type', sa.String(50), nullable=True),
        sa.Column('triggering_identifier_hash', sa.String(64), nullable=True),

        # Statistics at merge time
        sa.Column('merged_event_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('merged_identifier_count', sa.Integer(), server_default='0', nullable=False),

        # Merge metadata
        sa.Column('merged_by_user_id', sa.Integer(), nullable=True),
        sa.Column('merge_metadata', postgresql.JSONB(), server_default='{}', nullable=False),

        # State
        sa.Column('is_rolled_back', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('rolled_back_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['surviving_profile_id'], ['cdp_profiles.id'], ondelete='SET NULL'),
    )

    # Indexes for profile merges
    op.create_index('ix_cdp_profile_merges_tenant', 'cdp_profile_merges', ['tenant_id'])
    op.create_index('ix_cdp_profile_merges_surviving', 'cdp_profile_merges', ['surviving_profile_id'])
    op.create_index('ix_cdp_profile_merges_merged', 'cdp_profile_merges', ['merged_profile_id'])
    op.create_index('ix_cdp_profile_merges_time', 'cdp_profile_merges', ['tenant_id', 'created_at'])

    # =========================================================================
    # CDP Canonical Identities - Golden identity per profile
    # =========================================================================
    op.create_table(
        'cdp_canonical_identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Canonical identifier
        sa.Column('canonical_identifier_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Canonical identity details (denormalized)
        sa.Column('canonical_type', sa.String(50), nullable=True),
        sa.Column('canonical_value_hash', sa.String(64), nullable=True),

        # Priority score
        sa.Column('priority_score', sa.Integer(), server_default='0', nullable=False),

        # Verification status
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_method', sa.String(50), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['cdp_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['canonical_identifier_id'], ['cdp_profile_identifiers.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'profile_id', name='uq_cdp_canonical_profile'),
    )

    # Indexes for canonical identities
    op.create_index('ix_cdp_canonical_tenant', 'cdp_canonical_identities', ['tenant_id'])
    op.create_index('ix_cdp_canonical_profile', 'cdp_canonical_identities', ['profile_id'])


def downgrade() -> None:
    op.drop_table('cdp_canonical_identities')
    op.drop_table('cdp_profile_merges')
    op.drop_table('cdp_identity_links')
