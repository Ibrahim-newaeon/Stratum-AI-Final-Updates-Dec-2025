"""
Knowledge Graph Service

Main service for interacting with the Stratum Knowledge Graph.
Provides high-level APIs for graph operations and revenue analytics.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Result, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    EdgeLabel,
    GraphEdge,
    GraphNode,
    NodeLabel,
)
from .queries import CypherQueryBuilder, RevenueAnalyticsQueries

logger = logging.getLogger(__name__)


def summarise_journey(raw: dict[str, Any]) -> dict[str, Any]:
    """Expand the journey query's three fields into the nine the API returns.

    ``CustomerJourneyResponse`` promises totals, a first/last seen range and a
    duration; the Cypher returns ``profile_id``, ``lifecycle`` and a list of
    events. Everything else is derivable from that list, and was previously
    left at the response model's defaults -- a profile with one purchase and
    5000 cents of revenue was reported as having zero of each.

    ``total_revenue`` is in cents, matching ``Revenue.amount_cents`` and every
    other knowledge-graph surface. ``stage_transitions`` stays empty: the graph
    records no lifecycle history, and an invented one would read as real.
    """
    journey = raw.get("journey") or []
    # OPTIONAL MATCH makes collect() yield one all-null row rather than an
    # empty list, so entries are counted by having an event_type, not by length.
    events = [entry for entry in journey if entry and entry.get("event_type")]

    timestamps = sorted(
        entry["timestamp"] for entry in events if entry.get("timestamp")
    )
    first_seen = timestamps[0] if timestamps else None
    last_seen = timestamps[-1] if timestamps else None

    duration_days: Optional[float] = None
    if first_seen and last_seen and first_seen != last_seen:
        try:
            span = datetime.fromisoformat(last_seen) - datetime.fromisoformat(first_seen)
            duration_days = round(span.total_seconds() / 86400, 2)
        except ValueError:
            # Timestamps are whatever was written to the graph; an unparseable
            # one costs the duration, not the rest of the summary.
            duration_days = None

    return {
        "profile_id": raw.get("profile_id"),
        "lifecycle_stage": raw.get("lifecycle"),
        "first_seen_at": first_seen,
        "last_seen_at": last_seen,
        "total_events": len(events),
        "total_revenue": float(sum(entry.get("revenue") or 0 for entry in events)),
        "touchpoints": events,
        "stage_transitions": [],
        "journey_duration_days": duration_days,
    }



class KnowledgeGraphService:
    """
    Service for managing the Stratum Knowledge Graph.

    Provides:
    - CRUD operations for graph nodes and edges
    - Revenue attribution queries
    - Trust gate decision tracing
    - Customer journey analysis
    - Integration with CDP and Trust Engine

    Usage:
        async with get_db_session() as session:
            kg = KnowledgeGraphService(session)

            # Create a profile node
            profile = ProfileNode(
                tenant_id=tenant_id,
                external_id=profile_id,
                lifecycle_stage=LifecycleStage.CUSTOMER
            )
            await kg.create_node(profile)

            # Query revenue attribution
            results = await kg.get_revenue_by_channel(tenant_id, days=30)
    """

    GRAPH_NAME = "stratum_knowledge_graph"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_graph(self, query: str) -> Result:
        """Run one AGE statement with the session prepared for Cypher.

        Two things must already be true of the session before a
        ``cypher(...)`` statement will even parse:

        * AGE's library must be loaded. It installs the parse hooks the Cypher
          syntax depends on, and Postgres' own on-demand loading is too late —
          that happens at first function call, after the statement has been
          parsed.
        * ``ag_catalog`` must be on the search_path. Both ``cypher`` and the
          ``agtype`` return type live there, and nothing else in the
          application puts it on the path.

        Deliberately scoped to this service rather than to the engine. A
        connect-level listener would push every pooled connection through
        ``LOAD``, so a database without AGE would fail the entire application
        instead of the knowledge-graph routes that actually depend on it.

        ``search_path`` is set LOCAL so it expires with the transaction rather
        than following the connection back into the pool. ``LOAD`` has no LOCAL
        form, but a loaded library on a pooled connection is inert.
        """
        await self.session.execute(text("LOAD 'age'"))
        await self.session.execute(
            text('SET LOCAL search_path = ag_catalog, "$user", public')
        )
        return await self.session.execute(text(query))

    # =========================================================================
    # NODE OPERATIONS
    # =========================================================================

    async def create_node(self, node: GraphNode) -> dict[str, Any]:
        """
        Create a new node in the knowledge graph.

        Args:
            node: GraphNode instance (ProfileNode, EventNode, etc.)

        Returns:
            Created node properties from the graph
        """
        properties = node.to_cypher_properties()
        label = node.label

        query = CypherQueryBuilder(node.tenant_id).build_create_node(
            alias="n", node_label=NodeLabel(label), properties=properties
        )

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return self._parse_agtype(row[0])
        return {}

    async def merge_node(
        self, node: GraphNode, match_fields: list[str] = None
    ) -> dict[str, Any]:
        """
        Merge (upsert) a node - create if not exists, update if exists.

        Args:
            node: GraphNode instance
            match_fields: Fields to match on (default: tenant_id, external_id)

        Returns:
            Merged node properties
        """
        match_fields = match_fields or ["tenant_id", "external_id"]
        properties = node.to_cypher_properties()

        match_props = {k: properties[k] for k in match_fields if k in properties}
        set_props = {k: v for k, v in properties.items() if k not in match_fields}

        query = CypherQueryBuilder(node.tenant_id).build_merge_node(
            alias="n",
            node_label=NodeLabel(node.label),
            match_properties=match_props,
            set_properties=set_props,
        )

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return self._parse_agtype(row[0])
        return {}

    async def get_node(
        self, tenant_id: int, label: NodeLabel, external_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get a node by its external ID.

        Args:
            tenant_id: Tenant ID
            label: Node label (Profile, Event, etc.)
            external_id: External system ID

        Returns:
            Node properties or None if not found
        """
        query, _params = (
            CypherQueryBuilder(tenant_id)
            .match_node("n", label, {"external_id": external_id})
            .return_fields(["n"])
            .limit(1)
            .build()
        )

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return self._parse_agtype(row[0])
        return None

    async def delete_node(
        self, tenant_id: int, label: NodeLabel, external_id: str
    ) -> bool:
        """
        Delete a node and its relationships.

        Args:
            tenant_id: Tenant ID
            label: Node label
            external_id: External system ID

        Returns:
            True if deleted, False if not found
        """
        cypher = f"""
            MATCH (n:{label.value} {{tenant_id: '{tenant_id}', external_id: '{external_id}'}})
            DETACH DELETE n
            RETURN {{deleted: count(n)}} AS result
        """
        query = f"""
            SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                {cypher}
            $$) AS (result agtype);
        """

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            deleted = self._parse_agtype(row[0])
            return deleted.get("deleted", 0) > 0
        return False

    # =========================================================================
    # EDGE OPERATIONS
    # =========================================================================

    async def create_edge(
        self,
        edge: GraphEdge,
        start_label: NodeLabel,
        start_external_id: str,
        end_label: NodeLabel,
        end_external_id: str,
    ) -> dict[str, Any]:
        """
        Create an edge between two nodes.

        Args:
            edge: GraphEdge instance
            start_label: Label of source node
            start_external_id: External ID of source node
            end_label: Label of target node
            end_external_id: External ID of target node

        Returns:
            Created edge properties
        """
        query = CypherQueryBuilder(edge.tenant_id).build_create_edge(
            start_label=start_label,
            start_match={
                "tenant_id": str(edge.tenant_id),
                "external_id": start_external_id,
            },
            edge_label=edge.label,
            end_label=end_label,
            end_match={
                "tenant_id": str(edge.tenant_id),
                "external_id": end_external_id,
            },
            edge_properties=edge.to_cypher_properties(),
        )

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return self._parse_agtype(row[0])
        return {}

    async def get_edges(
        self,
        tenant_id: int,
        start_label: NodeLabel,
        start_external_id: str,
        edge_label: Optional[EdgeLabel] = None,
    ) -> list[dict[str, Any]]:
        """
        Get all edges from a node.

        Args:
            tenant_id: Tenant ID
            start_label: Source node label
            start_external_id: Source node external ID
            edge_label: Optional filter by edge type

        Returns:
            List of edge and target node properties
        """
        edge_filter = f":{edge_label.value}" if edge_label else ""

        cypher = f"""
            MATCH (n:{start_label.value} {{tenant_id: '{tenant_id}', external_id: '{start_external_id}'}})
                  -[r{edge_filter}]->(m)
            RETURN {{relationship: type(r), edge_props: properties(r),
                    target_labels: labels(m), target_props: properties(m)}} AS result
        """
        query = f"""
            SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                {cypher}
            $$) AS (result agtype);
        """

        result = await self._execute_graph(query)
        edges = []
        for row in result:
            edges.append(self._parse_agtype(row[0]))
        return edges

    # =========================================================================
    # REVENUE ANALYTICS
    # =========================================================================

    async def get_revenue_by_channel(
        self, tenant_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get revenue breakdown by acquisition channel.

        Args:
            tenant_id: Tenant ID
            days: Lookback period in days

        Returns:
            List of channel revenue data
        """
        query, _params = RevenueAnalyticsQueries.revenue_by_channel(tenant_id, days)
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def get_revenue_by_campaign(
        self, tenant_id: int, platform: Optional[str] = None, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get revenue breakdown by campaign.

        Args:
            tenant_id: Tenant ID
            platform: Optional platform filter (meta, google, etc.)
            days: Lookback period in days

        Returns:
            List of campaign revenue data with ROAS
        """
        query, _params = RevenueAnalyticsQueries.revenue_by_campaign(
            tenant_id, platform, days
        )
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def get_customer_journey(
        self, tenant_id: int, profile_external_id: str
    ) -> dict[str, Any]:
        """
        Get complete customer journey for a profile.

        Args:
            tenant_id: Tenant ID
            profile_external_id: Profile's external ID

        Returns:
            Journey data with events and revenue
        """
        query, _params = RevenueAnalyticsQueries.customer_journey(
            tenant_id, profile_external_id
        )
        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return summarise_journey(self._parse_agtype(row[0]))
        return {}

    async def get_segment_revenue_performance(
        self, tenant_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get revenue performance by customer segment.

        Args:
            tenant_id: Tenant ID
            days: Lookback period in days

        Returns:
            List of segment performance data
        """
        query, _params = RevenueAnalyticsQueries.segment_revenue_performance(
            tenant_id, days
        )
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def get_rfm_segment_distribution(
        self, tenant_id: int
    ) -> list[dict[str, Any]]:
        """
        Get RFM segment distribution and revenue contribution.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of RFM segment data
        """
        query, _params = RevenueAnalyticsQueries.rfm_segment_trends(tenant_id)
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    # =========================================================================
    # TRUST ENGINE ANALYTICS
    # =========================================================================

    async def get_blocked_automations(
        self, tenant_id: int, days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Get automations that were blocked by trust gates.

        Args:
            tenant_id: Tenant ID
            days: Lookback period in days

        Returns:
            List of blocked automation data with reasons
        """
        query, _params = RevenueAnalyticsQueries.blocked_automations(tenant_id, days)
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def get_signal_health_impact(
        self, tenant_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Analyze correlation between signal health and revenue.

        Args:
            tenant_id: Tenant ID
            days: Lookback period in days

        Returns:
            Signal health vs revenue correlation data
        """
        query, _params = RevenueAnalyticsQueries.signal_health_impact(tenant_id, days)
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def trace_automation_decision(
        self, tenant_id: int, automation_external_id: str
    ) -> dict[str, Any]:
        """
        Trace the full decision path for an automation.

        Shows: Signal -> TrustGate -> Automation -> Outcome

        Args:
            tenant_id: Tenant ID
            automation_external_id: Automation's external ID

        Returns:
            Full decision trace with all related nodes
        """
        cypher = f"""
            MATCH (a:Automation {{tenant_id: '{tenant_id}', external_id: '{automation_external_id}'}})
            OPTIONAL MATCH (s:Signal)-[ev:EVALUATED_BY]->(tg:TrustGate)-[decision:TRIGGERED|BLOCKED]->(a)
            OPTIONAL MATCH (a)-[prod:PRODUCED]->(r:Revenue)
            RETURN {{
                automation: properties(a),
                signals: collect(DISTINCT properties(s)),
                trust_gate: properties(tg),
                decision_type: type(decision),
                revenue_produced: collect(DISTINCT properties(r))
            }} AS trace
        """
        query = f"""
            SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                {cypher}
            $$) AS (result agtype);
        """

        result = await self._execute_graph(query)
        row = result.fetchone()

        if row:
            return self._parse_agtype(row[0])
        return {}

    # =========================================================================
    # ATTRIBUTION ANALYTICS
    # =========================================================================

    async def get_multi_touch_paths(
        self, tenant_id: int, min_touchpoints: int = 2, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Get multi-touch attribution paths to conversion.

        Args:
            tenant_id: Tenant ID
            min_touchpoints: Minimum touchpoints in path
            limit: Maximum results

        Returns:
            List of attribution paths with revenue
        """
        query, _params = RevenueAnalyticsQueries.multi_touch_attribution_paths(
            tenant_id, min_touchpoints, limit
        )
        result = await self._execute_graph(query)

        return [self._parse_agtype(row[0]) for row in result]

    async def get_channel_transition_matrix(
        self, tenant_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get channel-to-channel transition probabilities for Markov attribution.

        Args:
            tenant_id: Tenant ID
            days: Lookback period

        Returns:
            List of channel transitions with counts

        Note:
            The pair is ordered but no longer capped at seven days. AGE has no
            interval arithmetic, and the timestamps are ISO-8601 strings, so
            ``t1.timestamp + duration({days: 7})`` cannot be expressed -- it
            failed with ``function duration does not exist``. Every later
            touchpoint for the same profile now counts as a transition, which
            widens the window rather than narrowing it. Restoring the cap needs
            a numeric timestamp on Touchpoint to compare against.
        """
        cypher = f"""
            MATCH (p:Profile {{tenant_id: '{tenant_id}'}})-[r1:RECEIVED]->(t1:Touchpoint)
            MATCH (p)-[r2:RECEIVED]->(t2:Touchpoint)
            WHERE t2.timestamp > t1.timestamp
            WITH t1.channel AS from_channel, t2.channel AS to_channel, count(*) AS transitions
            WITH from_channel, to_channel, transitions
            ORDER BY transitions DESC
            LIMIT 100
            RETURN {{from_channel: from_channel, to_channel: to_channel,
                    transitions: transitions}} AS result
        """
        query = f"""
            SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                {cypher}
            $$) AS (result agtype);
        """

        result = await self._execute_graph(query)
        return [self._parse_agtype(row[0]) for row in result]

    # =========================================================================
    # GRAPH STATISTICS
    # =========================================================================

    async def get_graph_stats(self, tenant_id: int) -> dict[str, Any]:
        """
        Get overall graph statistics for a tenant.

        Returns:
            Node and edge counts by type
        """
        stats = {}

        # Count each node type
        for label in NodeLabel:
            cypher = f"""
                MATCH (n:{label.value} {{tenant_id: '{tenant_id}'}})
                RETURN {{node_count: count(n)}} AS result
            """
            query = f"""
                SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                    {cypher}
                $$) AS (result agtype);
            """
            result = await self._execute_graph(query)
            row = result.fetchone()
            if row:
                data = self._parse_agtype(row[0])
                stats[f"{label.value.lower()}_count"] = data.get("node_count", 0)

        # Count edges
        for edge in EdgeLabel:
            cypher = f"""
                MATCH ()-[r:{edge.value}]->()
                WHERE r.tenant_id = '{tenant_id}'
                RETURN {{edge_count: count(r)}} AS result
            """
            query = f"""
                SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                    {cypher}
                $$) AS (result agtype);
            """
            result = await self._execute_graph(query)
            row = result.fetchone()
            if row:
                data = self._parse_agtype(row[0])
                stats[f"{edge.value.lower()}_edges"] = data.get("edge_count", 0)

        return stats

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    @staticmethod
    def _parse_agtype(value: Any) -> Any:
        """Parse Apache AGE agtype to Python dict."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                # AGE returns JSON-like strings
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        if isinstance(value, dict):
            return value
        return value

    async def execute_cypher(
        self, cypher: str, tenant_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Execute a raw Cypher query.

        WARNING: Use with caution. Prefer typed methods.

        Args:
            cypher: Raw Cypher query
            tenant_id: Optional tenant ID for logging

        Returns:
            List of result rows
        """
        logger.info(f"Executing raw Cypher for tenant {tenant_id}: {cypher[:100]}...")

        query = f"""
            SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                {cypher}
            $$) AS (result agtype);
        """

        result = await self._execute_graph(query)
        return [self._parse_agtype(row[0]) for row in result]

    async def health_check(self) -> bool:
        """
        Check if the knowledge graph is accessible.

        Returns:
            True if graph is healthy
        """
        try:
            query = f"""
                SELECT * FROM cypher('{self.GRAPH_NAME}', $$
                    RETURN {{health: 1}} AS result
                $$) AS (result agtype);
            """
            result = await self._execute_graph(query)
            row = result.fetchone()
            return row is not None
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error("knowledge_graph_health_check_failed", error=str(e))
            return False
