"""Create Apache AGE Knowledge Graph schema

Revision ID: kg_2026_02_07
Revises:
Create Date: 2026-02-07

This migration creates the Apache AGE graph schema for Stratum's
Revenue Knowledge Graph with trust-gated automation tracking.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'kg_2026_02_07'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create Apache AGE extension and Knowledge Graph schema.

    Graph: stratum_knowledge_graph

    Vertices (Nodes):
    - Profile: CDP customer profiles
    - Account: Business accounts
    - Event: Customer events/actions
    - Signal: Data quality signals
    - TrustGate: Trust gate decisions
    - Automation: Automated actions
    - Segment: Customer segments
    - Campaign: Marketing campaigns
    - Channel: Acquisition channels
    - Revenue: Revenue events
    - Touchpoint: Customer touchpoints

    Edges (Relationships):
    - BELONGS_TO: Profile -> Segment, Profile -> Account
    - PERFORMED: Profile -> Event
    - GENERATED: Event -> Signal, Event -> Revenue
    - EVALUATED_BY: Signal -> TrustGate
    - TRIGGERED: Signal -> Automation, TrustGate -> Automation
    - BLOCKED: TrustGate -> Automation
    - PRODUCED: Automation -> Revenue
    - ATTRIBUTED_TO: Revenue -> Campaign, Profile -> Channel
    - DROVE: Campaign -> Revenue
    - RECEIVED: Profile -> Touchpoint
    - HAS_HEALTH: Signal -> HealthScore
    """

    # Enable Apache AGE extension
    op.execute("CREATE EXTENSION IF NOT EXISTS age;")
    op.execute("LOAD 'age';")
    op.execute("SET search_path = ag_catalog, '$user', public;")

    # Create the knowledge graph
    op.execute("SELECT create_graph('stratum_knowledge_graph');")

    # Create vertex labels (node types)
    vertex_labels = [
        'Profile',
        'Account',
        'Event',
        'Signal',
        'TrustGate',
        'Automation',
        'Segment',
        'Campaign',
        'Channel',
        'Revenue',
        'Touchpoint',
        'HealthScore',
    ]

    for label in vertex_labels:
        op.execute(f"""
            SELECT create_vlabel('stratum_knowledge_graph', '{label}');
        """)

    # Create edge labels (relationship types)
    edge_labels = [
        'BELONGS_TO',
        'PERFORMED',
        'GENERATED',
        'EVALUATED_BY',
        'TRIGGERED',
        'BLOCKED',
        'PRODUCED',
        'ATTRIBUTED_TO',
        'DROVE',
        'RECEIVED',
        'HAS_HEALTH',
        'MERGED_INTO',
        'LINKED_TO',
        'CONVERTED_FROM',
        'INFLUENCED',
    ]

    for label in edge_labels:
        op.execute(f"""
            SELECT create_elabel('stratum_knowledge_graph', '{label}');
        """)

    # Create indexes for common query patterns
    # Profile lookups by external_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_profile_external_id
        ON stratum_knowledge_graph."Profile" USING btree ((properties->>'external_id'));
    """)

    # Profile lookups by tenant
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_profile_tenant
        ON stratum_knowledge_graph."Profile" USING btree ((properties->>'tenant_id'));
    """)

    # Event lookups by type and timestamp
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_event_type
        ON stratum_knowledge_graph."Event" USING btree ((properties->>'event_type'));
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_event_timestamp
        ON stratum_knowledge_graph."Event" USING btree ((properties->>'timestamp'));
    """)

    # Signal lookups by health status
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_signal_status
        ON stratum_knowledge_graph."Signal" USING btree ((properties->>'status'));
    """)

    # TrustGate lookups by decision
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_trustgate_decision
        ON stratum_knowledge_graph."TrustGate" USING btree ((properties->>'decision'));
    """)

    # Revenue lookups by amount range
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_revenue_amount
        ON stratum_knowledge_graph."Revenue" USING btree (((properties->>'amount_cents')::bigint));
    """)

    # Campaign lookups by platform
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_kg_campaign_platform
        ON stratum_knowledge_graph."Campaign" USING btree ((properties->>'platform'));
    """)

    # Create helper function for tenant-isolated queries
    op.execute("""
        CREATE OR REPLACE FUNCTION kg_tenant_profiles(tenant_uuid UUID)
        RETURNS TABLE(vertex_id agtype, properties agtype)
        LANGUAGE sql
        AS $$
            SELECT * FROM cypher('stratum_knowledge_graph', $$
                MATCH (p:Profile)
                WHERE p.tenant_id = $tenant_uuid
                RETURN p
            $$, $1) AS (vertex_id agtype, properties agtype);
        $$;
    """)

    # Create materialized view for revenue attribution summary
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS kg_revenue_attribution_summary AS
        SELECT
            (r.properties->>'tenant_id')::uuid as tenant_id,
            (c.properties->>'platform')::text as platform,
            (c.properties->>'campaign_id')::text as campaign_id,
            COUNT(DISTINCT r.id) as revenue_events,
            SUM((r.properties->>'amount_cents')::bigint) as total_revenue_cents,
            COUNT(DISTINCT p.id) as unique_profiles
        FROM stratum_knowledge_graph."Revenue" r
        LEFT JOIN stratum_knowledge_graph."ATTRIBUTED_TO" attr ON r.id = attr.start_id
        LEFT JOIN stratum_knowledge_graph."Campaign" c ON attr.end_id = c.id
        LEFT JOIN stratum_knowledge_graph."Profile" p ON EXISTS (
            SELECT 1 FROM stratum_knowledge_graph."PERFORMED" perf
            JOIN stratum_knowledge_graph."Event" e ON perf.end_id = e.id
            JOIN stratum_knowledge_graph."GENERATED" gen ON e.id = gen.start_id
            WHERE gen.end_id = r.id AND perf.start_id = p.id
        )
        GROUP BY 1, 2, 3
        WITH NO DATA;
    """)


def downgrade() -> None:
    """Drop the knowledge graph and AGE extension."""

    op.execute("DROP MATERIALIZED VIEW IF EXISTS kg_revenue_attribution_summary;")
    op.execute("DROP FUNCTION IF EXISTS kg_tenant_profiles(UUID);")
    op.execute("SELECT drop_graph('stratum_knowledge_graph', true);")
    op.execute("DROP EXTENSION IF EXISTS age CASCADE;")
