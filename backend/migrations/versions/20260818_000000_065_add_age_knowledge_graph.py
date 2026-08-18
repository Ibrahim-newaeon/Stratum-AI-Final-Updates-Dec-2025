"""Provision Apache AGE and create the Stratum knowledge graph.

The knowledge graph was shelved behind ``feature_knowledge_graph`` because the
AGE extension was not provisioned: every query in
app/services/knowledge_graph/service.py runs real Cypher through
``cypher('stratum_knowledge_graph', $$ ... $$)``, so without AGE each route
500s. The router returns 503 instead, which is why the flag exists.

Installing the extension alone is not enough. ``cypher()`` addresses a *named*
graph, and that name is a schema AGE creates on demand — so the graph and its
vertex/edge labels have to exist before a single query resolves. This migration
creates all three: extension, graph, labels.

Requires the custom database image (backend/Dockerfile.postgres), which layers
AGE onto pgvector/pgvector:pg16. Against the stock image ``CREATE EXTENSION
age`` fails here rather than at runtime, which is the intended place to find out.

Idempotent throughout. ``create_graph`` and ``create_vlabel`` have no IF NOT
EXISTS form, so each is guarded on the catalog object it produces — a schema for
the graph, a table per label — via to_regnamespace/to_regclass. That is stable
across AGE versions in a way that reading ag_catalog's own columns is not.

Deliberately NOT ported from the never-applied draft at
alembic/versions/2026_02_07_knowledge_graph_age.py: eight expression indexes
over ``properties->>'...'``, a kg_tenant_profiles helper, and a
kg_revenue_attribution_summary materialized view. No application code
references any of them, the indexes depend on agtype's ``->>`` being IMMUTABLE
(it is not marked so), and the helper's body nests $$ inside a $$-quoted
function, which does not parse. They were three ways for this migration to fail
while adding nothing the feature needs on a graph that starts empty. Indexes
belong in a later, measured change once the sync service has populated it.

Revision ID: 065_add_age_knowledge_graph
Revises: 064_widen_cdp_identifier_value
"""

from alembic import op

revision = "065_add_age_knowledge_graph"
down_revision = "064_widen_cdp_identifier_value"
branch_labels = None
depends_on = None


GRAPH_NAME = "stratum_knowledge_graph"

# Mirrors NodeLabel / EdgeLabel in app/services/knowledge_graph/models.py. A
# label missing here is not a degraded query, it is an error on first write:
# AGE rejects MATCH and CREATE against a label the graph does not know.
VERTEX_LABELS = [
    "Profile",
    "Account",
    "Event",
    "Signal",
    "TrustGate",
    "Automation",
    "Segment",
    "Campaign",
    "Channel",
    "Revenue",
    "Touchpoint",
    "HealthScore",
]

EDGE_LABELS = [
    "BELONGS_TO",
    "PERFORMED",
    "GENERATED",
    "EVALUATED_BY",
    "TRIGGERED",
    "BLOCKED",
    "PRODUCED",
    "ATTRIBUTED_TO",
    "DROVE",
    "RECEIVED",
    "HAS_HEALTH",
    "MERGED_INTO",
    "LINKED_TO",
    "CONVERTED_FROM",
    "INFLUENCED",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS age")

    # AGE installs planner and parse hooks when its library loads, and the
    # hooks must be in place before a statement using them is parsed. Function
    # calls below are schema-qualified, so this is belt-and-braces for the
    # session rather than strictly required by them.
    op.execute("LOAD 'age'")

    # create_graph builds a schema named after the graph; its absence is the
    # cheapest correct existence check.
    op.execute(f"""
        DO $do$
        BEGIN
            IF to_regnamespace('{GRAPH_NAME}') IS NULL THEN
                PERFORM ag_catalog.create_graph('{GRAPH_NAME}');
            END IF;
        END
        $do$;
        """)

    # create_vlabel/create_elabel each build one table inside the graph schema.
    for label in VERTEX_LABELS:
        op.execute(f"""
            DO $do$
            BEGIN
                IF to_regclass('{GRAPH_NAME}."{label}"') IS NULL THEN
                    PERFORM ag_catalog.create_vlabel('{GRAPH_NAME}', '{label}');
                END IF;
            END
            $do$;
            """)

    for label in EDGE_LABELS:
        op.execute(f"""
            DO $do$
            BEGIN
                IF to_regclass('{GRAPH_NAME}."{label}"') IS NULL THEN
                    PERFORM ag_catalog.create_elabel('{GRAPH_NAME}', '{label}');
                END IF;
            END
            $do$;
            """)


def downgrade() -> None:
    # drop_graph(..., cascade => true) removes the schema and every label table
    # with it, so the labels need no separate teardown. Guarded because
    # drop_graph raises rather than no-ops on an absent graph.
    op.execute("LOAD 'age'")
    op.execute(f"""
        DO $do$
        BEGIN
            IF to_regnamespace('{GRAPH_NAME}') IS NOT NULL THEN
                PERFORM ag_catalog.drop_graph('{GRAPH_NAME}', true);
            END IF;
        END
        $do$;
        """)
    op.execute("DROP EXTENSION IF EXISTS age CASCADE")
