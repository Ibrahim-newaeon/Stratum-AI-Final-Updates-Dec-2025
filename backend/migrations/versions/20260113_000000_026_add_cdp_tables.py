"""Add CDP (Customer Data Platform) tables

Revision ID: 026_cdp_tables
Revises: 026_add_autopilot_enforcement
Create Date: 2026-01-13 00:00:00.000000

Tables:
- cdp_sources: Data source configurations
- cdp_profiles: Unified customer profiles
- cdp_profile_identifiers: Identity mappings
- cdp_events: Append-only event store
- cdp_consents: Privacy consent records
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '026_cdp_tables'
down_revision = '026_add_autopilot_enforcement'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. CDP Sources - Data source configurations
    # =========================================================================
    op.create_table(
        'cdp_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Source identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),  # website, server, sgtm, import, crm
        sa.Column('source_key', sa.String(64), nullable=False),   # API key for authentication

        # Configuration
        sa.Column('config', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),

        # Metrics
        sa.Column('event_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('last_event_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'source_key', name='uq_cdp_sources_tenant_key'),
    )

    op.create_index('ix_cdp_sources_tenant', 'cdp_sources', ['tenant_id'])
    op.create_index('ix_cdp_sources_key', 'cdp_sources', ['source_key'])
    op.create_index('ix_cdp_sources_type', 'cdp_sources', ['tenant_id', 'source_type'])

    # =========================================================================
    # 2. CDP Profiles - Unified customer profiles
    # =========================================================================
    op.create_table(
        'cdp_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # External reference
        sa.Column('external_id', sa.String(255), nullable=True),

        # Timestamps
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Profile data
        sa.Column('profile_data', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('computed_traits', postgresql.JSONB(), server_default='{}', nullable=False),

        # Lifecycle
        sa.Column('lifecycle_stage', sa.String(50), server_default='anonymous', nullable=False),

        # Aggregated counters (denormalized for performance)
        sa.Column('total_events', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_sessions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_purchases', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_revenue', sa.Numeric(15, 2), server_default='0', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Partial unique index on external_id (only when not null)
    op.execute("""
        CREATE UNIQUE INDEX uq_cdp_profiles_tenant_external
        ON cdp_profiles (tenant_id, external_id)
        WHERE external_id IS NOT NULL
    """)

    op.create_index('ix_cdp_profiles_tenant', 'cdp_profiles', ['tenant_id'])
    op.create_index('ix_cdp_profiles_lifecycle', 'cdp_profiles', ['tenant_id', 'lifecycle_stage'])
    op.create_index('ix_cdp_profiles_last_seen', 'cdp_profiles', ['tenant_id', sa.text('last_seen_at DESC')])

    # =========================================================================
    # 3. CDP Profile Identifiers - Identity mappings
    # =========================================================================
    op.create_table(
        'cdp_profile_identifiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Identifier details
        sa.Column('identifier_type', sa.String(50), nullable=False),  # email, phone, device_id, anonymous_id, external_id
        sa.Column('identifier_value', sa.String(512), nullable=True),  # Original value (nullable for privacy)
        sa.Column('identifier_hash', sa.String(64), nullable=False),   # SHA256 hash

        # Metadata
        sa.Column('is_primary', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('confidence_score', sa.Numeric(3, 2), server_default='1.00', nullable=False),

        # Verification
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['cdp_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'identifier_type', 'identifier_hash', name='uq_cdp_identifiers_tenant_type_hash'),
    )

    op.create_index('ix_cdp_identifiers_tenant', 'cdp_profile_identifiers', ['tenant_id'])
    op.create_index('ix_cdp_identifiers_profile', 'cdp_profile_identifiers', ['profile_id'])
    op.create_index('ix_cdp_identifiers_lookup', 'cdp_profile_identifiers', ['tenant_id', 'identifier_type', 'identifier_hash'])
    op.create_index('ix_cdp_identifiers_hash', 'cdp_profile_identifiers', ['identifier_hash'])

    # =========================================================================
    # 4. CDP Events - Append-only event store
    # =========================================================================
    op.create_table(
        'cdp_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Event identification
        sa.Column('event_name', sa.String(255), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Deduplication
        sa.Column('idempotency_key', sa.String(128), nullable=True),

        # Event data
        sa.Column('properties', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('context', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('identifiers', postgresql.JSONB(), server_default='[]', nullable=False),

        # Processing
        sa.Column('processed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('processing_errors', postgresql.JSONB(), server_default='[]', nullable=False),

        # EMQ (Event Match Quality) - integration with Stratum signal health
        sa.Column('emq_score', sa.Numeric(5, 2), nullable=True),

        # Timestamps (no updated_at - events are immutable)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['cdp_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['cdp_sources.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_cdp_events_tenant', 'cdp_events', ['tenant_id'])
    op.create_index('ix_cdp_events_profile', 'cdp_events', ['profile_id'])
    op.create_index('ix_cdp_events_name', 'cdp_events', ['tenant_id', 'event_name'])
    op.create_index('ix_cdp_events_time', 'cdp_events', ['tenant_id', sa.text('event_time DESC')])
    op.create_index('ix_cdp_events_source', 'cdp_events', ['source_id'])
    op.create_index('ix_cdp_events_received', 'cdp_events', [sa.text('received_at DESC')])

    # Partial index for idempotency lookup (only when key is not null)
    op.execute("""
        CREATE INDEX ix_cdp_events_idempotency
        ON cdp_events (tenant_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """)

    # =========================================================================
    # 5. CDP Consents - Privacy consent tracking
    # =========================================================================
    op.create_table(
        'cdp_consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Consent details
        sa.Column('consent_type', sa.String(50), nullable=False),  # analytics, ads, email, sms, all
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),

        # Audit information
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),

        # Compliance
        sa.Column('consent_text', sa.Text(), nullable=True),
        sa.Column('consent_version', sa.String(50), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['cdp_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'profile_id', 'consent_type', name='uq_cdp_consents_profile_type'),
    )

    op.create_index('ix_cdp_consents_tenant', 'cdp_consents', ['tenant_id'])
    op.create_index('ix_cdp_consents_profile', 'cdp_consents', ['profile_id'])
    op.create_index('ix_cdp_consents_type', 'cdp_consents', ['tenant_id', 'consent_type', 'granted'])


def downgrade() -> None:
    # Drop in reverse order of creation (respect foreign keys)
    op.drop_table('cdp_consents')
    op.drop_table('cdp_events')
    op.drop_table('cdp_profile_identifiers')
    op.drop_table('cdp_profiles')
    op.drop_table('cdp_sources')
