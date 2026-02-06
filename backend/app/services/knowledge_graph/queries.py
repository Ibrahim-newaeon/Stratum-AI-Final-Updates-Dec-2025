"""
Cypher Query Builder for Apache AGE

Provides a fluent API for building Cypher queries with tenant isolation
and revenue-focused analytics patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from .models import NodeLabel, EdgeLabel, GateDecision, SignalStatus


class AggregateFunction(str, Enum):
    """Cypher aggregate functions."""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COLLECT = "collect"


@dataclass
class CypherQueryBuilder:
    """
    Fluent builder for Cypher queries with Apache AGE.

    Example:
        query = (
            CypherQueryBuilder(tenant_id)
            .match_node("p", NodeLabel.PROFILE)
            .where("p.lifecycle_stage", "=", "customer")
            .match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
            .where("e.event_type", "=", "purchase")
            .return_fields(["p.external_id", "sum(e.revenue_cents)"])
            .order_by("sum(e.revenue_cents)", desc=True)
            .limit(100)
            .build()
        )
    """

    tenant_id: UUID
    graph_name: str = "stratum_knowledge_graph"
    _match_clauses: list[str] = field(default_factory=list)
    _where_clauses: list[str] = field(default_factory=list)
    _optional_matches: list[str] = field(default_factory=list)
    _with_clauses: list[str] = field(default_factory=list)
    _return_fields: list[str] = field(default_factory=list)
    _order_by: Optional[str] = None
    _limit: Optional[int] = None
    _skip: Optional[int] = None
    _parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Initialize mutable defaults
        if not hasattr(self, '_match_clauses') or self._match_clauses is None:
            self._match_clauses = []
        if not hasattr(self, '_where_clauses') or self._where_clauses is None:
            self._where_clauses = []
        if not hasattr(self, '_optional_matches') or self._optional_matches is None:
            self._optional_matches = []
        if not hasattr(self, '_with_clauses') or self._with_clauses is None:
            self._with_clauses = []
        if not hasattr(self, '_return_fields') or self._return_fields is None:
            self._return_fields = []
        if not hasattr(self, '_parameters') or self._parameters is None:
            self._parameters = {}

    def match_node(
        self,
        alias: str,
        label: NodeLabel,
        properties: Optional[dict[str, Any]] = None
    ) -> CypherQueryBuilder:
        """Add a MATCH clause for a node."""
        props = self._format_properties(properties) if properties else ""
        self._match_clauses.append(f"({alias}:{label.value}{props})")
        # Always filter by tenant
        self._where_clauses.append(f"{alias}.tenant_id = '{self.tenant_id}'")
        return self

    def match_edge(
        self,
        start_alias: str,
        edge_label: EdgeLabel,
        end_alias: str,
        end_label: Optional[NodeLabel] = None,
        edge_alias: Optional[str] = None,
        direction: str = "->",  # "->" or "<-" or "--"
    ) -> CypherQueryBuilder:
        """Add a MATCH clause for an edge."""
        edge_part = f"[{edge_alias or ''}:{edge_label.value}]" if edge_alias else f"[:{edge_label.value}]"
        end_part = f"({end_alias}:{end_label.value})" if end_label else f"({end_alias})"

        if direction == "->":
            pattern = f"({start_alias})-{edge_part}->{end_part}"
        elif direction == "<-":
            pattern = f"({start_alias})<-{edge_part}-{end_part}"
        else:
            pattern = f"({start_alias})-{edge_part}-{end_part}"

        self._match_clauses.append(pattern)
        return self

    def optional_match_edge(
        self,
        start_alias: str,
        edge_label: EdgeLabel,
        end_alias: str,
        end_label: Optional[NodeLabel] = None,
    ) -> CypherQueryBuilder:
        """Add an OPTIONAL MATCH clause for an edge."""
        end_part = f"({end_alias}:{end_label.value})" if end_label else f"({end_alias})"
        self._optional_matches.append(
            f"({start_alias})-[:{edge_label.value}]->{end_part}"
        )
        return self

    def where(
        self,
        field: str,
        operator: str,
        value: Any,
        param_name: Optional[str] = None
    ) -> CypherQueryBuilder:
        """Add a WHERE condition."""
        if param_name:
            self._parameters[param_name] = value
            self._where_clauses.append(f"{field} {operator} ${param_name}")
        else:
            formatted_value = self._format_value(value)
            self._where_clauses.append(f"{field} {operator} {formatted_value}")
        return self

    def where_in(self, field: str, values: list[Any]) -> CypherQueryBuilder:
        """Add a WHERE IN condition."""
        formatted = [self._format_value(v) for v in values]
        self._where_clauses.append(f"{field} IN [{', '.join(formatted)}]")
        return self

    def where_between(
        self,
        field: str,
        start: Any,
        end: Any
    ) -> CypherQueryBuilder:
        """Add a WHERE BETWEEN condition."""
        start_val = self._format_value(start)
        end_val = self._format_value(end)
        self._where_clauses.append(f"{field} >= {start_val} AND {field} <= {end_val}")
        return self

    def where_date_range(
        self,
        field: str,
        start_date: datetime,
        end_date: datetime
    ) -> CypherQueryBuilder:
        """Add a date range filter."""
        return self.where_between(
            field,
            start_date.isoformat(),
            end_date.isoformat()
        )

    def where_last_n_days(self, field: str, days: int) -> CypherQueryBuilder:
        """Filter to last N days."""
        start = datetime.utcnow() - timedelta(days=days)
        return self.where(field, ">=", start.isoformat())

    def with_clause(self, *fields: str) -> CypherQueryBuilder:
        """Add a WITH clause for query chaining."""
        self._with_clauses.append(", ".join(fields))
        return self

    def return_fields(self, fields: list[str]) -> CypherQueryBuilder:
        """Set RETURN fields."""
        self._return_fields = fields
        return self

    def return_count(self, alias: str, as_name: str = "count") -> CypherQueryBuilder:
        """Return count of nodes."""
        self._return_fields.append(f"count({alias}) AS {as_name}")
        return self

    def return_sum(
        self,
        field: str,
        as_name: str = "total"
    ) -> CypherQueryBuilder:
        """Return sum of field."""
        self._return_fields.append(f"sum({field}) AS {as_name}")
        return self

    def return_path(self, from_alias: str, to_alias: str) -> CypherQueryBuilder:
        """Return path between nodes."""
        self._return_fields.append(f"path = shortestPath(({from_alias})-[*]->({to_alias}))")
        return self

    def order_by(self, field: str, desc: bool = False) -> CypherQueryBuilder:
        """Set ORDER BY clause."""
        direction = "DESC" if desc else "ASC"
        self._order_by = f"{field} {direction}"
        return self

    def limit(self, n: int) -> CypherQueryBuilder:
        """Set LIMIT clause."""
        self._limit = n
        return self

    def skip(self, n: int) -> CypherQueryBuilder:
        """Set SKIP clause for pagination."""
        self._skip = n
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """
        Build the final Cypher query wrapped for Apache AGE.

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        # Build MATCH clause
        match_part = "MATCH " + ", ".join(self._match_clauses) if self._match_clauses else ""

        # Build OPTIONAL MATCH clauses
        optional_parts = [f"OPTIONAL MATCH {om}" for om in self._optional_matches]

        # Build WHERE clause
        where_part = "WHERE " + " AND ".join(self._where_clauses) if self._where_clauses else ""

        # Build WITH clauses
        with_parts = [f"WITH {w}" for w in self._with_clauses]

        # Build RETURN clause
        return_part = "RETURN " + ", ".join(self._return_fields) if self._return_fields else "RETURN *"

        # Build ORDER BY
        order_part = f"ORDER BY {self._order_by}" if self._order_by else ""

        # Build LIMIT/SKIP
        skip_part = f"SKIP {self._skip}" if self._skip else ""
        limit_part = f"LIMIT {self._limit}" if self._limit else ""

        # Combine all parts
        cypher_parts = [
            match_part,
            *optional_parts,
            where_part,
            *with_parts,
            return_part,
            order_part,
            skip_part,
            limit_part,
        ]
        cypher = " ".join(part for part in cypher_parts if part)

        # Wrap in AGE SQL function
        sql = f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                {cypher}
            $$) AS (result agtype);
        """

        return sql, self._parameters

    def build_create_node(self, alias: str, node_label: NodeLabel, properties: dict[str, Any]) -> str:
        """Build a CREATE node query."""
        props = self._format_properties(properties)
        cypher = f"CREATE ({alias}:{node_label.value}{props}) RETURN {alias}"
        return f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                {cypher}
            $$) AS (result agtype);
        """

    def build_merge_node(
        self,
        alias: str,
        node_label: NodeLabel,
        match_properties: dict[str, Any],
        set_properties: Optional[dict[str, Any]] = None
    ) -> str:
        """Build a MERGE node query (create if not exists)."""
        match_props = self._format_properties(match_properties)
        set_clause = ""
        if set_properties:
            set_parts = [f"{alias}.{k} = {self._format_value(v)}" for k, v in set_properties.items()]
            set_clause = f"ON CREATE SET {', '.join(set_parts)} ON MATCH SET {', '.join(set_parts)}"

        cypher = f"MERGE ({alias}:{node_label.value}{match_props}) {set_clause} RETURN {alias}"
        return f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                {cypher}
            $$) AS (result agtype);
        """

    def build_create_edge(
        self,
        start_label: NodeLabel,
        start_match: dict[str, Any],
        edge_label: EdgeLabel,
        end_label: NodeLabel,
        end_match: dict[str, Any],
        edge_properties: Optional[dict[str, Any]] = None
    ) -> str:
        """Build a CREATE edge query."""
        start_props = self._format_properties(start_match)
        end_props = self._format_properties(end_match)
        edge_props = self._format_properties(edge_properties) if edge_properties else ""

        cypher = f"""
            MATCH (a:{start_label.value}{start_props}), (b:{end_label.value}{end_props})
            CREATE (a)-[r:{edge_label.value}{edge_props}]->(b)
            RETURN r
        """
        return f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                {cypher}
            $$) AS (result agtype);
        """

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a value for Cypher."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            escaped = value.replace("'", "\\'")
            return f"'{escaped}'"
        elif isinstance(value, datetime):
            return f"'{value.isoformat()}'"
        elif isinstance(value, UUID):
            return f"'{str(value)}'"
        elif isinstance(value, Enum):
            return f"'{value.value}'"
        elif isinstance(value, (list, tuple)):
            formatted = [CypherQueryBuilder._format_value(v) for v in value]
            return f"[{', '.join(formatted)}]"
        elif isinstance(value, dict):
            parts = [f"{k}: {CypherQueryBuilder._format_value(v)}" for k, v in value.items()]
            return "{" + ", ".join(parts) + "}"
        else:
            return f"'{str(value)}'"

    @staticmethod
    def _format_properties(properties: Optional[dict[str, Any]]) -> str:
        """Format properties dict for Cypher."""
        if not properties:
            return ""
        parts = [f"{k}: {CypherQueryBuilder._format_value(v)}" for k, v in properties.items()]
        return " {" + ", ".join(parts) + "}"


# =============================================================================
# PRE-BUILT REVENUE ANALYTICS QUERIES
# =============================================================================

class RevenueAnalyticsQueries:
    """Pre-built Cypher queries for revenue analytics."""

    @staticmethod
    def revenue_by_channel(tenant_id: UUID, days: int = 30) -> tuple[str, dict]:
        """Get revenue breakdown by acquisition channel."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("r", NodeLabel.REVENUE)
            .match_edge("r", EdgeLabel.ATTRIBUTED_TO, "ch", NodeLabel.CHANNEL, direction="->")
            .where_last_n_days("r.occurred_at", days)
            .return_fields([
                "ch.name AS channel",
                "ch.channel_type AS channel_type",
                "count(r) AS transactions",
                "sum(r.amount_cents) AS revenue_cents",
                "avg(r.amount_cents) AS avg_order_cents"
            ])
            .order_by("revenue_cents", desc=True)
            .build()
        )

    @staticmethod
    def revenue_by_campaign(tenant_id: UUID, platform: Optional[str] = None, days: int = 30) -> tuple[str, dict]:
        """Get revenue breakdown by campaign."""
        builder = (
            CypherQueryBuilder(tenant_id)
            .match_node("r", NodeLabel.REVENUE)
            .match_edge("r", EdgeLabel.ATTRIBUTED_TO, "c", NodeLabel.CAMPAIGN, direction="->")
            .where_last_n_days("r.occurred_at", days)
        )
        if platform:
            builder.where("c.platform", "=", platform)

        return (
            builder
            .return_fields([
                "c.name AS campaign_name",
                "c.platform AS platform",
                "c.spend_cents AS spend_cents",
                "sum(r.amount_cents) AS revenue_cents",
                "count(r) AS conversions",
                "CASE WHEN c.spend_cents > 0 THEN sum(r.amount_cents) * 1.0 / c.spend_cents ELSE 0 END AS roas"
            ])
            .order_by("revenue_cents", desc=True)
            .limit(50)
            .build()
        )

    @staticmethod
    def customer_journey(tenant_id: UUID, profile_external_id: str) -> tuple[str, dict]:
        """Get full customer journey for a profile."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("p", NodeLabel.PROFILE, {"external_id": profile_external_id})
            .match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
            .optional_match_edge("e", EdgeLabel.GENERATED, "r", NodeLabel.REVENUE)
            .return_fields([
                "p.external_id AS profile_id",
                "p.lifecycle_stage AS lifecycle",
                "collect({event_type: e.event_type, timestamp: e.event_time, revenue: r.amount_cents}) AS journey"
            ])
            .build()
        )

    @staticmethod
    def blocked_automations(tenant_id: UUID, days: int = 7) -> tuple[str, dict]:
        """Get automations that were blocked by trust gates."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("tg", NodeLabel.TRUST_GATE, {"decision": GateDecision.BLOCK.value})
            .match_edge("tg", EdgeLabel.BLOCKED, "a", NodeLabel.AUTOMATION)
            .where_last_n_days("tg.evaluated_at", days)
            .return_fields([
                "a.action_type AS action_type",
                "a.platform AS platform",
                "tg.reason AS block_reason",
                "tg.signal_health_score AS health_score",
                "tg.evaluated_at AS blocked_at"
            ])
            .order_by("tg.evaluated_at", desc=True)
            .limit(100)
            .build()
        )

    @staticmethod
    def signal_health_impact(tenant_id: UUID, days: int = 30) -> tuple[str, dict]:
        """Analyze correlation between signal health and revenue."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("s", NodeLabel.SIGNAL)
            .match_edge("s", EdgeLabel.EVALUATED_BY, "tg", NodeLabel.TRUST_GATE)
            .match_edge("tg", EdgeLabel.TRIGGERED, "a", NodeLabel.AUTOMATION)
            .match_edge("a", EdgeLabel.PRODUCED, "r", NodeLabel.REVENUE)
            .where_last_n_days("s.measured_at", days)
            .return_fields([
                "s.status AS signal_status",
                "avg(s.score) AS avg_signal_score",
                "count(a) AS automations_executed",
                "sum(r.amount_cents) AS revenue_produced_cents"
            ])
            .order_by("avg_signal_score", desc=True)
            .build()
        )

    @staticmethod
    def segment_revenue_performance(tenant_id: UUID, days: int = 30) -> tuple[str, dict]:
        """Get revenue performance by customer segment."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("seg", NodeLabel.SEGMENT)
            .match_edge("p", EdgeLabel.BELONGS_TO, "seg", direction="<-")
            .match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
            .match_edge("e", EdgeLabel.GENERATED, "r", NodeLabel.REVENUE)
            .where_last_n_days("r.occurred_at", days)
            .return_fields([
                "seg.name AS segment_name",
                "seg.profile_count AS segment_size",
                "count(DISTINCT p) AS converting_profiles",
                "count(r) AS transactions",
                "sum(r.amount_cents) AS total_revenue_cents",
                "avg(r.amount_cents) AS avg_order_cents"
            ])
            .order_by("total_revenue_cents", desc=True)
            .build()
        )

    @staticmethod
    def multi_touch_attribution_paths(
        tenant_id: UUID,
        min_touchpoints: int = 2,
        limit: int = 20
    ) -> tuple[str, dict]:
        """Get multi-touch attribution paths to conversion."""
        # This is a more complex traversal query
        cypher = f"""
            MATCH (p:Profile {{tenant_id: '{tenant_id}'}})-[:PERFORMED]->(e:Event)-[:GENERATED]->(r:Revenue)
            MATCH path = (p)-[:RECEIVED*1..10]->(t:Touchpoint)
            WHERE t.timestamp < r.occurred_at
            WITH p, r, collect(t) AS touchpoints
            WHERE size(touchpoints) >= {min_touchpoints}
            RETURN
                p.external_id AS profile_id,
                r.amount_cents AS revenue_cents,
                [t IN touchpoints | t.channel] AS attribution_path,
                size(touchpoints) AS path_length
            ORDER BY r.amount_cents DESC
            LIMIT {limit}
        """
        sql = f"""
            SELECT * FROM cypher('stratum_knowledge_graph', $$
                {cypher}
            $$) AS (result agtype);
        """
        return sql, {}

    @staticmethod
    def rfm_segment_trends(tenant_id: UUID) -> tuple[str, dict]:
        """Get RFM segment distribution and revenue contribution."""
        return (
            CypherQueryBuilder(tenant_id)
            .match_node("p", NodeLabel.PROFILE)
            .where("p.rfm_segment", "IS NOT", None)
            .return_fields([
                "p.rfm_segment AS rfm_segment",
                "count(p) AS profile_count",
                "sum(p.total_revenue_cents) AS total_revenue_cents",
                "avg(p.rfm_score) AS avg_rfm_score",
                "avg(p.total_purchases) AS avg_purchases"
            ])
            .order_by("total_revenue_cents", desc=True)
            .build()
        )
