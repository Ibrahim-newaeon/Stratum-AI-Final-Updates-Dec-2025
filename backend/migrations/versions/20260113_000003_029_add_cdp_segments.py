"""Add CDP segments and computed traits tables

Revision ID: 029_cdp_segments
Revises: 028_cdp_identity_graph
Create Date: 2026-01-13 21:00:00.000000

Tables:
- cdp_segments: Customer segment definitions
- cdp_segment_memberships: Profile membership in segments
- cdp_computed_traits: Computed trait definitions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '029_cdp_segments'
down_revision = '028_cdp_identity_graph'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # CDP Segments - Customer segment definitions
    # =========================================================================
    op.create_table(
        'cdp_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Segment identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(100), nullable=True),

        # Segment configuration
        sa.Column('segment_type', sa.String(50), server_default='dynamic', nullable=False),
        sa.Column('status', sa.String(50), server_default='draft', nullable=False),

        # Rules (JSON)
        sa.Column('rules', postgresql.JSONB(), server_default='{}', nullable=False),

        # Computed metadata
        sa.Column('profile_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('computation_duration_ms', sa.Integer(), nullable=True),

        # Scheduling
        sa.Column('auto_refresh', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('refresh_interval_hours', sa.Integer(), server_default='24', nullable=False),
        sa.Column('next_refresh_at', sa.DateTime(timezone=True), nullable=True),

        # Tags
        sa.Column('tags', postgresql.JSONB(), server_default='[]', nullable=False),

        # Created by
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'slug', name='uq_cdp_segments_slug'),
    )

    # Indexes for segments
    op.create_index('ix_cdp_segments_tenant', 'cdp_segments', ['tenant_id'])
    op.create_index('ix_cdp_segments_status', 'cdp_segments', ['tenant_id', 'status'])
    op.create_index('ix_cdp_segments_type', 'cdp_segments', ['tenant_id', 'segment_type'])

    # =========================================================================
    # CDP Segment Memberships - Profile membership in segments
    # =========================================================================
    op.create_table(
        'cdp_segment_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Membership metadata
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),

        # For static segments
        sa.Column('added_by_user_id', sa.Integer(), nullable=True),

        # Match score
        sa.Column('match_score', sa.Numeric(5, 2), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['segment_id'], ['cdp_segments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['cdp_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'segment_id', 'profile_id', name='uq_cdp_memberships_segment_profile'),
    )

    # Indexes for memberships
    op.create_index('ix_cdp_memberships_tenant', 'cdp_segment_memberships', ['tenant_id'])
    op.create_index('ix_cdp_memberships_segment', 'cdp_segment_memberships', ['segment_id'])
    op.create_index('ix_cdp_memberships_profile', 'cdp_segment_memberships', ['profile_id'])
    op.create_index('ix_cdp_memberships_active', 'cdp_segment_memberships', ['segment_id', 'is_active'])

    # =========================================================================
    # CDP Computed Traits - Computed trait definitions
    # =========================================================================
    op.create_table(
        'cdp_computed_traits',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Trait identification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Computation configuration
        sa.Column('trait_type', sa.String(50), server_default='count', nullable=False),
        sa.Column('source_config', postgresql.JSONB(), server_default='{}', nullable=False),

        # Output configuration
        sa.Column('output_type', sa.String(50), server_default='number', nullable=False),
        sa.Column('default_value', sa.String(255), nullable=True),

        # State
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_computed_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_cdp_traits_name'),
    )

    # Indexes for computed traits
    op.create_index('ix_cdp_traits_tenant', 'cdp_computed_traits', ['tenant_id'])
    op.create_index('ix_cdp_traits_active', 'cdp_computed_traits', ['tenant_id', 'is_active'])


def downgrade() -> None:
    op.drop_table('cdp_computed_traits')
    op.drop_table('cdp_segment_memberships')
    op.drop_table('cdp_segments')
