"""
Knowledge Graph Insights Engine

Detects problems by analyzing the knowledge graph and suggests
actionable solutions based on graph traversal patterns.

This is the "why" engine - it explains what's happening and what to do about it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .service import KnowledgeGraphService

logger = logging.getLogger(__name__)


def _days_ago_iso(days: int) -> str:
    """The ISO-8601 instant ``days`` before now, for use as a Cypher literal.

    AGE implements neither ``datetime()`` nor ``duration()`` -- a query calling
    them fails with ``function datetime does not exist``. Timestamps enter the
    graph as ISO strings (``GraphNode.to_cypher_properties`` calls
    ``isoformat()``), and ISO-8601 in a fixed offset sorts lexicographically,
    so a string comparison against a cutoff computed here is exact.
    """
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


class ProblemSeverity(str, Enum):
    """Severity levels for detected problems."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action needed soon
    MEDIUM = "medium"  # Should investigate
    LOW = "low"  # Informational


class ProblemCategory(str, Enum):
    """Categories of problems the engine can detect."""

    REVENUE_DECLINE = "revenue_decline"
    AUTOMATION_BLOCKED = "automation_blocked"
    SIGNAL_DEGRADED = "signal_degraded"
    SEGMENT_UNDERPERFORMING = "segment_underperforming"
    ATTRIBUTION_GAP = "attribution_gap"
    IDENTITY_FRAGMENTATION = "identity_fragmentation"
    TRUST_GATE_BOTTLENECK = "trust_gate_bottleneck"
    CHANNEL_INEFFICIENCY = "channel_inefficiency"


@dataclass
class Solution:
    """A suggested solution for a detected problem."""

    title: str
    description: str
    action_type: str  # "investigate", "adjust", "fix", "monitor"
    priority: int  # 1 = highest
    steps: list[str] = field(default_factory=list)
    affected_entities: list[dict[str, Any]] = field(default_factory=list)
    estimated_impact: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class Problem:
    """A detected problem with context and solutions."""

    id: str
    category: ProblemCategory
    severity: ProblemSeverity
    title: str
    description: str
    detected_at: datetime

    # Graph context
    root_cause_path: list[dict[str, Any]] = field(default_factory=list)
    affected_nodes: list[dict[str, Any]] = field(default_factory=list)

    # Metrics
    metrics: dict[str, Any] = field(default_factory=dict)

    # Solutions
    solutions: list[Solution] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
            "root_cause_path": self.root_cause_path,
            "affected_nodes": self.affected_nodes,
            "metrics": self.metrics,
            "solutions": [
                {
                    "title": s.title,
                    "description": s.description,
                    "action_type": s.action_type,
                    "priority": s.priority,
                    "steps": s.steps,
                    "affected_entities": s.affected_entities,
                    "estimated_impact": s.estimated_impact,
                    "auto_fixable": s.auto_fixable,
                }
                for s in self.solutions
            ],
        }


class KnowledgeGraphInsightsEngine:
    """
    Analyzes the Knowledge Graph to detect problems and suggest solutions.

    Uses graph traversal to:
    1. Detect anomalies and performance issues
    2. Trace root causes through relationships
    3. Generate actionable solutions

    Usage:
        engine = KnowledgeGraphInsightsEngine(session)
        problems = await engine.detect_all_problems(tenant_id)

        for problem in problems:
            print(f"{problem.severity}: {problem.title}")
            for solution in problem.solutions:
                print(f"  -> {solution.title}")
    """

    # Thresholds for problem detection
    REVENUE_DECLINE_THRESHOLD = 0.15  # 15% decline triggers alert
    BLOCK_RATE_THRESHOLD = 0.30  # 30% block rate is concerning
    SIGNAL_HEALTH_THRESHOLD = 70  # Below 70 is degraded
    SEGMENT_DECLINE_THRESHOLD = 0.20  # 20% segment revenue decline

    def __init__(self, session: AsyncSession):
        self.session = session
        self.kg = KnowledgeGraphService(session)

    async def detect_all_problems(self, tenant_id: int, days: int = 7) -> list[Problem]:
        """
        Run all problem detection algorithms and return sorted by severity.

        Args:
            tenant_id: Tenant ID
            days: Lookback period for analysis

        Returns:
            List of Problems sorted by severity (critical first)
        """
        problems = []

        # Run all detectors
        detectors = [
            self._detect_revenue_decline,
            self._detect_blocked_automations,
            self._detect_signal_degradation,
            self._detect_segment_issues,
            self._detect_trust_gate_bottlenecks,
            self._detect_channel_inefficiency,
        ]

        for detector in detectors:
            try:
                detected = await detector(tenant_id, days)
                if detected:
                    problems.extend(
                        detected if isinstance(detected, list) else [detected]
                    )
            except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
                logger.error(f"Problem detector {detector.__name__} failed: {e}")

        # Sort by severity
        severity_order = {
            ProblemSeverity.CRITICAL: 0,
            ProblemSeverity.HIGH: 1,
            ProblemSeverity.MEDIUM: 2,
            ProblemSeverity.LOW: 3,
        }
        problems.sort(key=lambda p: severity_order[p.severity])

        return problems

    async def _detect_revenue_decline(
        self, tenant_id: int, days: int
    ) -> Optional[Problem]:
        """Detect significant revenue decline and trace the cause."""

        # Query revenue trends. Three things here are AGE's constraints rather
        # than choices, and all three failed when this first ran against a live
        # graph:
        #
        # * ``reduce()`` is openCypher, not AGE -- it raises a syntax error at
        #   the ``|``. The two totals come from UNWIND + sum() instead.
        # * ``ORDER BY`` cannot see an alias produced by an aggregating WITH
        #   ("could not find rte for date"), so the ordering gets a WITH of its
        #   own to project the aliases forward first.
        # * UNWIND of an empty list yields no rows, which would drop the whole
        #   result when a tenant has fewer than ``days`` distinct dates. The
        #   ``+ [0]`` keeps each slice non-empty and cannot change a sum.
        cypher = f"""
            MATCH (r:Revenue {{tenant_id: '{tenant_id}'}})
            WITH r.occurred_at AS date, sum(r.amount_cents) AS daily_revenue
            WITH date, daily_revenue
            ORDER BY date DESC
            LIMIT {days * 2}
            WITH collect(daily_revenue) AS data
            WITH data[0..{days}] + [0] AS recent, data[{days}..] + [0] AS previous
            UNWIND recent AS recent_day
            WITH previous, sum(recent_day) AS recent_total
            UNWIND previous AS previous_day
            WITH recent_total, sum(previous_day) AS previous_total
            RETURN {{recent_total: recent_total, previous_total: previous_total,
                    change_pct: CASE WHEN previous_total > 0
                                     THEN (recent_total - previous_total) * 1.0 / previous_total
                                     ELSE 0 END}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)
            if not results:
                return None

            data = results[0] if results else {}
            change_pct = data.get("change_pct", 0)

            if change_pct < -self.REVENUE_DECLINE_THRESHOLD:
                # Revenue declined - trace the cause
                root_cause = await self._trace_revenue_decline_cause(tenant_id, days)

                return Problem(
                    id=f"rev_decline_{tenant_id}_{datetime.now(tz=UTC).strftime('%Y%m%d')}",
                    category=ProblemCategory.REVENUE_DECLINE,
                    severity=(
                        ProblemSeverity.CRITICAL
                        if change_pct < -0.30
                        else ProblemSeverity.HIGH
                    ),
                    title=f"Revenue Declined {abs(change_pct)*100:.1f}% This Week",
                    description=f"Revenue dropped from ${data.get('previous_total', 0)/100:,.0f} to ${data.get('recent_total', 0)/100:,.0f} compared to the previous period.",
                    detected_at=datetime.now(tz=UTC),
                    root_cause_path=root_cause.get("path", []),
                    affected_nodes=root_cause.get("affected", []),
                    metrics={
                        "previous_revenue_cents": data.get("previous_total", 0),
                        "current_revenue_cents": data.get("recent_total", 0),
                        "change_percent": change_pct * 100,
                    },
                    solutions=self._generate_revenue_solutions(root_cause),
                )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Revenue decline detection failed: {e}")

        return None

    async def _trace_revenue_decline_cause(
        self, tenant_id: int, days: int
    ) -> dict[str, Any]:
        """Trace through the graph to find why revenue declined."""

        causes = {"path": [], "affected": []}

        # Check if campaigns are underperforming
        campaign_query = f"""
            MATCH (c:Campaign {{tenant_id: '{tenant_id}'}})-[drove:DROVE]->(r:Revenue)
            WHERE r.occurred_at >= '{_days_ago_iso(days)}'
            WITH c, sum(r.amount_cents) AS revenue
            WITH c, revenue
            ORDER BY revenue DESC
            LIMIT 5
            RETURN {{campaign: c.name, platform: c.platform,
                    spend: c.spend_cents, revenue: revenue,
                    roas: CASE WHEN c.spend_cents > 0
                               THEN revenue * 1.0 / c.spend_cents ELSE 0 END}} AS result
        """
        campaigns = await self.kg.execute_cypher(campaign_query)

        # Check for blocked automations
        blocked_query = f"""
            MATCH (tg:TrustGate {{tenant_id: '{tenant_id}', decision: 'block'}})-[blk:BLOCKED]->(a:Automation)
            WHERE tg.evaluated_at >= '{_days_ago_iso(days)}'
            RETURN {{blocked_count: count(a),
                    action_types: collect(DISTINCT a.action_type)[0..5],
                    avg_health: avg(tg.signal_health_score)}} AS result
        """
        blocked = await self.kg.execute_cypher(blocked_query)

        # Check signal health
        signal_query = f"""
            MATCH (s:Signal {{tenant_id: '{tenant_id}'}})
            WHERE s.measured_at >= '{_days_ago_iso(days)}'
            RETURN {{source: s.source, avg_score: avg(s.score),
                    statuses: collect(DISTINCT s.status)}} AS result
        """
        signals = await self.kg.execute_cypher(signal_query)

        # Build cause chain
        if blocked and blocked[0].get("blocked_count", 0) > 5:
            causes["path"].append(
                {
                    "node": "TrustGate",
                    "finding": f"{blocked[0]['blocked_count']} automations blocked",
                    "detail": f"Avg signal health: {blocked[0].get('avg_health', 0):.1f}%",
                }
            )

        if signals:
            degraded = [
                s
                for s in signals
                if s.get("avg_score", 100) < self.SIGNAL_HEALTH_THRESHOLD
            ]
            if degraded:
                causes["path"].append(
                    {
                        "node": "Signal",
                        "finding": f"{len(degraded)} signal sources degraded",
                        "detail": f"Sources: {', '.join(s.get('source', 'unknown') for s in degraded[:3])}",
                    }
                )

        if campaigns:
            low_roas = [c for c in campaigns if c.get("roas", 0) < 1.0]
            if low_roas:
                causes["path"].append(
                    {
                        "node": "Campaign",
                        "finding": f"{len(low_roas)} campaigns with ROAS < 1.0",
                        "detail": f"Campaigns: {', '.join(c.get('campaign', 'unknown') for c in low_roas[:3])}",
                    }
                )
                causes["affected"].extend(low_roas)

        return causes

    def _generate_revenue_solutions(self, root_cause: dict[str, Any]) -> list[Solution]:
        """Generate solutions based on revenue decline root cause."""
        solutions = []

        path = root_cause.get("path", [])

        # Check if trust gate is blocking
        trust_gate_issue = next((p for p in path if p.get("node") == "TrustGate"), None)
        if trust_gate_issue:
            solutions.append(
                Solution(
                    title="Investigate Blocked Automations",
                    description="Multiple automations were blocked by Trust Gate due to low signal health.",
                    action_type="investigate",
                    priority=1,
                    steps=[
                        "Go to Trust Engine > Audit Log",
                        "Review blocked automations from the past 7 days",
                        "Check which signals are causing the blocks",
                        "Verify pixel/API implementations for degraded signals",
                    ],
                    estimated_impact="Unblocking could restore 20-40% of optimization capacity",
                    auto_fixable=False,
                )
            )

        # Check if signals are degraded
        signal_issue = next((p for p in path if p.get("node") == "Signal"), None)
        if signal_issue:
            solutions.append(
                Solution(
                    title="Fix Degraded Signal Sources",
                    description="One or more data signals are below healthy thresholds.",
                    action_type="fix",
                    priority=1,
                    steps=[
                        "Go to Trust Engine > Signal Health",
                        "Identify sources with score below 70",
                        "For EMQ issues: Check pixel implementation and event parameters",
                        "For freshness issues: Verify data pipeline is running",
                        "For variance issues: Audit attribution settings",
                    ],
                    estimated_impact="Healthy signals enable full automation",
                    auto_fixable=False,
                )
            )

        # Check campaign performance
        campaign_issue = next((p for p in path if p.get("node") == "Campaign"), None)
        if campaign_issue:
            affected = root_cause.get("affected", [])
            solutions.append(
                Solution(
                    title="Optimize Underperforming Campaigns",
                    description=f"{len(affected)} campaigns have ROAS below 1.0.",
                    action_type="adjust",
                    priority=2,
                    steps=[
                        "Review creative fatigue scores",
                        "Check audience overlap between campaigns",
                        "Consider pausing campaigns with ROAS < 0.5 for 48 hours",
                        "Reallocate budget to top performers",
                    ],
                    affected_entities=affected[:5],
                    estimated_impact="Proper allocation could improve overall ROAS by 15-25%",
                    auto_fixable=True,
                )
            )

        # Default solution if no specific cause found
        if not solutions:
            solutions.append(
                Solution(
                    title="Review Customer Journey Paths",
                    description="Analyze the Knowledge Graph to find conversion bottlenecks.",
                    action_type="investigate",
                    priority=2,
                    steps=[
                        "Go to Knowledge Graph > Customer Journeys",
                        "Compare converting vs non-converting paths",
                        "Identify drop-off points in the funnel",
                        "Check if specific segments are underperforming",
                    ],
                    estimated_impact="Journey optimization can improve conversion by 10-20%",
                    auto_fixable=False,
                )
            )

        return solutions

    async def _detect_blocked_automations(
        self, tenant_id: int, days: int
    ) -> Optional[Problem]:
        """Detect high automation block rate."""

        cypher = f"""
            MATCH (tg:TrustGate {{tenant_id: '{tenant_id}'}})
            WHERE tg.evaluated_at >= '{_days_ago_iso(days)}'
            WITH
                count(CASE WHEN tg.decision = 'block' THEN 1 END) AS blocked,
                count(CASE WHEN tg.decision = 'pass' THEN 1 END) AS passed,
                count(tg) AS total
            RETURN {{blocked: blocked, passed: passed, total: total,
                    block_rate: CASE WHEN total > 0
                                     THEN blocked * 1.0 / total ELSE 0 END}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)
            if not results:
                return None

            data = results[0]
            block_rate = data.get("block_rate", 0)

            if block_rate > self.BLOCK_RATE_THRESHOLD and data.get("total", 0) > 10:
                # Get details on what's being blocked
                detail_query = f"""
                    MATCH (tg:TrustGate {{tenant_id: '{tenant_id}', decision: 'block'}})-[blk:BLOCKED]->(a:Automation)
                    WHERE tg.evaluated_at >= '{_days_ago_iso(days)}'
                    WITH a.action_type AS action_type, a.platform AS platform,
                         count(*) AS action_count,
                         avg(tg.signal_health_score) AS avg_health
                    WITH action_type, platform, action_count, avg_health
                    ORDER BY action_count DESC
                    LIMIT 5
                    RETURN {{action_type: action_type, platform: platform,
                            count: action_count, avg_health: avg_health}} AS result
                """
                details = await self.kg.execute_cypher(detail_query)

                return Problem(
                    id=f"block_rate_{tenant_id}_{datetime.now(tz=UTC).strftime('%Y%m%d')}",
                    category=ProblemCategory.AUTOMATION_BLOCKED,
                    severity=(
                        ProblemSeverity.HIGH
                        if block_rate > 0.50
                        else ProblemSeverity.MEDIUM
                    ),
                    title=f"{block_rate*100:.0f}% of Automations Being Blocked",
                    description=f"{data.get('blocked', 0)} out of {data.get('total', 0)} automation attempts were blocked by Trust Gate.",
                    detected_at=datetime.now(tz=UTC),
                    affected_nodes=details or [],
                    metrics={
                        "blocked_count": data.get("blocked", 0),
                        "passed_count": data.get("passed", 0),
                        "total_count": data.get("total", 0),
                        "block_rate": block_rate * 100,
                    },
                    solutions=[
                        Solution(
                            title="Review Signal Health Dashboard",
                            description="Blocked automations indicate signal quality issues.",
                            action_type="investigate",
                            priority=1,
                            steps=[
                                "Open Trust Engine > Signal Health",
                                "Identify signals below 70% health",
                                "Check EMQ, freshness, and variance scores",
                                "Fix underlying data quality issues",
                            ],
                            estimated_impact="Fixing signals could reduce block rate by 50%+",
                        ),
                        Solution(
                            title="Adjust Trust Gate Thresholds (Caution)",
                            description="If data quality is actually fine, thresholds may be too strict.",
                            action_type="adjust",
                            priority=3,
                            steps=[
                                "Review recent automation outcomes",
                                "If blocked automations would have been correct, consider lowering thresholds",
                                "Go to Settings > Trust Engine > Thresholds",
                                "Decrease in small increments (5% at a time)",
                            ],
                            estimated_impact="Lower thresholds increase automation but add risk",
                            auto_fixable=False,
                        ),
                    ],
                )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Blocked automation detection failed: {e}")

        return None

    async def _detect_signal_degradation(
        self, tenant_id: int, days: int
    ) -> list[Problem]:
        """Detect degraded signals and identify affected areas."""

        problems = []

        cypher = f"""
            MATCH (s:Signal {{tenant_id: '{tenant_id}'}})
            WHERE s.measured_at >= '{_days_ago_iso(days)}'
            WITH s.source AS source, s.platform AS platform,
                 avg(s.score) AS avg_score,
                 min(s.score) AS min_score,
                 collect(DISTINCT s.status) AS statuses
            WHERE avg_score < {self.SIGNAL_HEALTH_THRESHOLD}
            RETURN {{source: source, platform: platform, avg_score: avg_score,
                    min_score: min_score, statuses: statuses}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)

            for signal in results or []:
                severity = (
                    ProblemSeverity.CRITICAL
                    if signal.get("avg_score", 0) < 40
                    else ProblemSeverity.MEDIUM
                )

                problems.append(
                    Problem(
                        id=f"signal_{signal.get('source')}_{tenant_id}",
                        category=ProblemCategory.SIGNAL_DEGRADED,
                        severity=severity,
                        title=f"Signal Degraded: {signal.get('source', 'Unknown')}",
                        description=f"Average health score is {signal.get('avg_score', 0):.1f}%, below the {self.SIGNAL_HEALTH_THRESHOLD}% threshold.",
                        detected_at=datetime.now(tz=UTC),
                        metrics={
                            "source": signal.get("source"),
                            "platform": signal.get("platform"),
                            "avg_score": signal.get("avg_score"),
                            "min_score": signal.get("min_score"),
                        },
                        solutions=[
                            Solution(
                                title=f"Fix {signal.get('source', 'Signal')} Data Quality",
                                description="This signal is preventing automations from executing.",
                                action_type="fix",
                                priority=1,
                                steps=self._get_signal_fix_steps(signal.get("source")),
                                estimated_impact="Restoring this signal enables related automations",
                            ),
                        ],
                    )
                )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Signal degradation detection failed: {e}")

        return problems

    def _get_signal_fix_steps(self, source: Optional[str]) -> list[str]:
        """Get specific fix steps based on signal source."""
        source = (source or "").lower()

        if "emq" in source or "pixel" in source:
            return [
                "Check pixel installation on all pages",
                "Verify event parameters are being sent correctly",
                "Test events using platform's event debugger",
                "Ensure server-side events have proper user data",
            ]
        elif "freshness" in source:
            return [
                "Check data pipeline status",
                "Verify scheduled jobs are running",
                "Check for API rate limiting",
                "Review error logs for failed syncs",
            ]
        elif "variance" in source:
            return [
                "Compare platform reporting with GA4",
                "Check attribution window settings",
                "Verify conversion tracking setup",
                "Look for duplicate conversions",
            ]
        else:
            return [
                "Review signal configuration",
                "Check data source connectivity",
                "Verify API credentials are valid",
                "Contact support if issue persists",
            ]

    async def _detect_segment_issues(self, tenant_id: int, days: int) -> list[Problem]:
        """Detect underperforming segments."""

        problems = []

        # Query segment performance
        cypher = f"""
            MATCH (seg:Segment {{tenant_id: '{tenant_id}'}})<-[member:BELONGS_TO]-(p:Profile)
                  -[perf:PERFORMED]->(e:Event)-[gen:GENERATED]->(r:Revenue)
            WHERE r.occurred_at >= '{_days_ago_iso(days)}'
            WITH seg, count(DISTINCT p) AS converting_profiles,
                 sum(r.amount_cents) AS revenue, seg.profile_count AS total_profiles
            WHERE total_profiles > 10
            WITH seg, total_profiles, converting_profiles, revenue
            ORDER BY revenue DESC
            RETURN {{segment: seg.name, segment_id: seg.external_id,
                    total_profiles: total_profiles,
                    converting_profiles: converting_profiles, revenue: revenue,
                    conversion_rate: converting_profiles * 1.0 / total_profiles}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)

            if results and len(results) >= 2:
                # Compare segments - find underperformers
                avg_conversion = sum(
                    r.get("conversion_rate", 0) for r in results
                ) / len(results)

                for segment in results:
                    conv_rate = segment.get("conversion_rate", 0)
                    if (
                        conv_rate < avg_conversion * 0.5
                        and segment.get("total_profiles", 0) > 50
                    ):
                        problems.append(
                            Problem(
                                id=f"segment_{segment.get('segment_id')}_{tenant_id}",
                                category=ProblemCategory.SEGMENT_UNDERPERFORMING,
                                severity=ProblemSeverity.MEDIUM,
                                title=f"Segment Underperforming: {segment.get('segment', 'Unknown')}",
                                description=f"Conversion rate ({conv_rate*100:.1f}%) is less than half the average ({avg_conversion*100:.1f}%).",
                                detected_at=datetime.now(tz=UTC),
                                metrics={
                                    "segment_name": segment.get("segment"),
                                    "total_profiles": segment.get("total_profiles"),
                                    "converting_profiles": segment.get(
                                        "converting_profiles"
                                    ),
                                    "revenue_cents": segment.get("revenue"),
                                    "conversion_rate": conv_rate * 100,
                                    "avg_conversion_rate": avg_conversion * 100,
                                },
                                solutions=[
                                    Solution(
                                        title="Review Segment Definition",
                                        description="The segment criteria may be too broad or misaligned.",
                                        action_type="investigate",
                                        priority=2,
                                        steps=[
                                            "Go to CDP > Segments > "
                                            + segment.get("segment", ""),
                                            "Review segment conditions",
                                            "Check if profiles match intended audience",
                                            "Consider splitting into more specific segments",
                                        ],
                                    ),
                                    Solution(
                                        title="Exclude from High-Value Campaigns",
                                        description="Stop spending on this segment until issues are resolved.",
                                        action_type="adjust",
                                        priority=1,
                                        steps=[
                                            "Pause audience sync for this segment",
                                            "Or add as exclusion in ad platforms",
                                            "Monitor for 7 days after changes",
                                        ],
                                        auto_fixable=True,
                                    ),
                                ],
                            )
                        )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Segment issue detection failed: {e}")

        return problems

    async def _detect_trust_gate_bottlenecks(
        self, tenant_id: int, days: int
    ) -> Optional[Problem]:
        """Detect if Trust Gate is consistently blocking specific action types."""

        cypher = f"""
            MATCH (tg:TrustGate {{tenant_id: '{tenant_id}'}})-[blk:BLOCKED]->(a:Automation)
            WHERE tg.evaluated_at >= '{_days_ago_iso(days)}'
            WITH a.action_type AS action_type, count(*) AS blocked_count,
                 avg(tg.signal_health_score) AS avg_health_at_block
            WHERE blocked_count >= 5
            WITH action_type, blocked_count, avg_health_at_block
            ORDER BY blocked_count DESC
            LIMIT 3
            RETURN {{action_type: action_type, blocked_count: blocked_count,
                    avg_health_at_block: avg_health_at_block}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)

            if results and len(results) > 0:
                top_blocked = results[0]

                return Problem(
                    id=f"bottleneck_{top_blocked.get('action_type')}_{tenant_id}",
                    category=ProblemCategory.TRUST_GATE_BOTTLENECK,
                    severity=ProblemSeverity.MEDIUM,
                    title=f"Trust Gate Bottleneck: {top_blocked.get('action_type', 'Unknown')}",
                    description=f"'{top_blocked.get('action_type')}' action blocked {top_blocked.get('blocked_count')} times at avg health {top_blocked.get('avg_health_at_block', 0):.1f}%.",
                    detected_at=datetime.now(tz=UTC),
                    affected_nodes=results,
                    metrics={
                        "action_type": top_blocked.get("action_type"),
                        "blocked_count": top_blocked.get("blocked_count"),
                        "avg_health_at_block": top_blocked.get("avg_health_at_block"),
                    },
                    solutions=[
                        Solution(
                            title="Review Action Risk Level",
                            description="This action may be classified as higher risk than necessary.",
                            action_type="adjust",
                            priority=2,
                            steps=[
                                "Go to Settings > Trust Engine > Action Risk Levels",
                                f"Find '{top_blocked.get('action_type')}' action",
                                "Consider if 'standard' risk level is appropriate",
                                "Lower risk level reduces required health threshold",
                            ],
                        ),
                    ],
                )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Trust gate bottleneck detection failed: {e}")

        return None

    async def _detect_channel_inefficiency(
        self, tenant_id: int, days: int
    ) -> Optional[Problem]:
        """Detect channels with poor ROI."""

        # Reads the Channel rollup rather than traversing ATTRIBUTED_TO to
        # per-event Revenue, which cannot be populated — daily_attributed_
        # revenue is a period aggregate with no conversion id. `days` is not a
        # filter here; the node carries its own rollup window (window_days).
        cypher = f"""
            MATCH (ch:Channel {{tenant_id: '{tenant_id}'}})
            WITH ch
            ORDER BY ch.total_revenue_cents DESC
            RETURN {{channel: ch.name, type: ch.channel_type,
                    revenue: ch.total_revenue_cents,
                    conversions: ch.total_conversions,
                    avg_order: CASE WHEN ch.total_conversions > 0
                                    THEN ch.total_revenue_cents / ch.total_conversions
                                    ELSE 0 END}} AS result
        """

        try:
            results = await self.kg.execute_cypher(cypher)

            if results and len(results) >= 2:
                total_revenue = sum(r.get("revenue", 0) for r in results)

                # Find channels with high share but low efficiency
                for channel in results:
                    share = (
                        channel.get("revenue", 0) / total_revenue
                        if total_revenue > 0
                        else 0
                    )
                    avg_order = channel.get("avg_order", 0)
                    overall_avg = total_revenue / sum(
                        r.get("conversions", 1) for r in results
                    )

                    if share > 0.2 and avg_order < overall_avg * 0.5:
                        return Problem(
                            id=f"channel_{channel.get('channel')}_{tenant_id}",
                            category=ProblemCategory.CHANNEL_INEFFICIENCY,
                            severity=ProblemSeverity.MEDIUM,
                            title=f"Channel Inefficiency: {channel.get('channel', 'Unknown')}",
                            description=f"This channel has {share*100:.0f}% of revenue but avg order value is {avg_order/100:.0f} vs overall {overall_avg/100:.0f}.",
                            detected_at=datetime.now(tz=UTC),
                            metrics={
                                "channel": channel.get("channel"),
                                "revenue_share": share * 100,
                                "avg_order_cents": avg_order,
                                "overall_avg_order_cents": overall_avg,
                            },
                            solutions=[
                                Solution(
                                    title="Optimize Channel Targeting",
                                    description="Focus on higher-value audiences within this channel.",
                                    action_type="adjust",
                                    priority=2,
                                    steps=[
                                        "Review audience targeting for this channel",
                                        "Create lookalike from high-AOV customers",
                                        "Test value-based bidding strategies",
                                        "Consider excluding low-value segments",
                                    ],
                                ),
                            ],
                        )
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OSError) as e:
            logger.error(f"Channel inefficiency detection failed: {e}")

        return None

    async def get_problem_details(
        self, tenant_id: int, problem_id: str
    ) -> Optional[Problem]:
        """
        Get detailed information about a specific problem.

        Includes extended graph traversal for root cause analysis.
        """
        # Re-run detection to get fresh data
        all_problems = await self.detect_all_problems(tenant_id)
        return next((p for p in all_problems if p.id == problem_id), None)

    async def get_health_summary(self, tenant_id: int) -> dict[str, Any]:
        """
        Get overall health summary based on Knowledge Graph analysis.

        Returns:
            Health summary with score and problem counts
        """
        problems = await self.detect_all_problems(tenant_id)

        # Calculate health score (100 - penalty for problems)
        penalty = 0
        for p in problems:
            if p.severity == ProblemSeverity.CRITICAL:
                penalty += 25
            elif p.severity == ProblemSeverity.HIGH:
                penalty += 15
            elif p.severity == ProblemSeverity.MEDIUM:
                penalty += 8
            else:
                penalty += 3

        health_score = max(0, 100 - penalty)

        return {
            "health_score": health_score,
            "status": (
                "healthy"
                if health_score >= 80
                else "degraded" if health_score >= 50 else "critical"
            ),
            "problem_counts": {
                "critical": len(
                    [p for p in problems if p.severity == ProblemSeverity.CRITICAL]
                ),
                "high": len(
                    [p for p in problems if p.severity == ProblemSeverity.HIGH]
                ),
                "medium": len(
                    [p for p in problems if p.severity == ProblemSeverity.MEDIUM]
                ),
                "low": len([p for p in problems if p.severity == ProblemSeverity.LOW]),
            },
            "total_problems": len(problems),
            "top_problem": problems[0].to_dict() if problems else None,
        }
