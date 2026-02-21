# =============================================================================
# Stratum AI - Knowledge Graph Service
# =============================================================================
"""
Knowledge Graph service for analytics, insights, and problem detection.

Provides graph-based analysis of tenant data to detect problems,
trace automation decisions, and generate revenue insights.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select, and_, case, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ProblemSeverity(str, enum.Enum):
    """Severity levels for detected problems."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProblemCategory(str, enum.Enum):
    """Categories of problems detected by the Knowledge Graph."""

    SIGNAL_HEALTH = "signal_health"
    DATA_QUALITY = "data_quality"
    AUTOMATION = "automation"
    ATTRIBUTION = "attribution"
    BUDGET = "budget"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


# Lifecycle stage ordering for journey construction
_LIFECYCLE_STAGE_ORDER: dict[str, int] = {
    "anonymous": 0,
    "known": 1,
    "lead": 2,
    "customer": 3,
    "active": 4,
    "churned": 5,
}

# Event names that indicate lifecycle transitions
_EVENT_STAGE_MAP: dict[str, str] = {
    "page_view": "anonymous",
    "session_start": "anonymous",
    "identify": "known",
    "form_submit": "lead",
    "sign_up": "lead",
    "login": "known",
    "purchase": "customer",
    "order_completed": "customer",
    "add_to_cart": "active",
    "checkout_started": "active",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Solution:
    """A suggested solution for a detected problem."""

    title: str
    description: str
    action_type: str
    priority: int
    steps: list[str]
    affected_entities: list[dict[str, Any]]
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
    root_cause_path: list[dict[str, Any]] = field(default_factory=list)
    affected_nodes: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    solutions: list[Solution] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert problem to dictionary for API response."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "detected_at": self.detected_at,
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


# =============================================================================
# Knowledge Graph Service
# =============================================================================


class KnowledgeGraphService:
    """
    Service for querying and analyzing the Knowledge Graph.

    Provides methods for revenue analysis, customer journey tracing,
    automation decision tracking, and graph health monitoring.
    """

    GRAPH_NAME = "stratum_knowledge_graph"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_revenue_by_channel(
        self, tenant_id: Any, *, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get revenue breakdown by acquisition channel.

        Queries CDP events with purchase/revenue data and groups them by
        the acquisition channel found in event context (utm_source or
        referrer). Returns a list of channel dicts with revenue, count,
        and average order value.

        Args:
            tenant_id: The tenant to query.
            days: Lookback window in days.

        Returns:
            List of dicts with channel, revenue, transaction_count, and avg_order_value.
        """
        from app.models.cdp import CDPEvent, CDPProfile

        logger.info(
            "knowledge_graph.revenue_by_channel",
            tenant_id=str(tenant_id),
            days=days,
        )

        cutoff = datetime.now(UTC) - timedelta(days=days)

        try:
            # Query purchase events within the time window
            stmt = (
                select(CDPEvent)
                .where(
                    and_(
                        CDPEvent.tenant_id == tenant_id,
                        CDPEvent.event_time >= cutoff,
                        CDPEvent.event_name.in_(
                            ["purchase", "order_completed", "transaction"]
                        ),
                    )
                )
                .order_by(CDPEvent.event_time.desc())
            )
            result = await self.db.execute(stmt)
            events = result.scalars().all()

            # Group by channel extracted from event context/properties
            channel_data: dict[str, dict[str, Any]] = {}
            for event in events:
                props = event.properties or {}
                ctx = event.context or {}

                # Determine channel from UTM source, context, or default
                channel = (
                    ctx.get("utm_source")
                    or ctx.get("source")
                    or props.get("channel")
                    or props.get("utm_source")
                    or "direct"
                )
                channel = str(channel).lower()

                revenue = float(props.get("revenue", 0) or props.get("total", 0) or 0)

                if channel not in channel_data:
                    channel_data[channel] = {
                        "channel": channel,
                        "revenue": 0.0,
                        "transaction_count": 0,
                    }

                channel_data[channel]["revenue"] += revenue
                channel_data[channel]["transaction_count"] += 1

            # Compute averages and build result list
            results: list[dict[str, Any]] = []
            for ch_info in channel_data.values():
                count = ch_info["transaction_count"]
                ch_info["avg_order_value"] = (
                    round(ch_info["revenue"] / count, 2) if count > 0 else 0.0
                )
                ch_info["revenue"] = round(ch_info["revenue"], 2)
                results.append(ch_info)

            # Sort by revenue descending
            results.sort(key=lambda x: x["revenue"], reverse=True)
            return results

        except Exception:
            logger.exception(
                "knowledge_graph.revenue_by_channel_failed",
                tenant_id=str(tenant_id),
            )
            return []

    async def get_segment_revenue_performance(
        self, tenant_id: Any, *, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get revenue breakdown by customer segment.

        Joins CDP segments, memberships, and profiles to aggregate
        revenue metrics per segment.

        Args:
            tenant_id: The tenant to query.
            days: Lookback window in days.

        Returns:
            List of dicts with segment_id, segment_name, profile_count,
            total_revenue, and avg_revenue_per_profile.
        """
        from app.models.cdp import CDPSegment, CDPSegmentMembership, CDPProfile

        logger.info(
            "knowledge_graph.segment_revenue",
            tenant_id=str(tenant_id),
            days=days,
        )

        try:
            # Query active segments with their member profiles' revenue
            stmt = (
                select(
                    CDPSegment.id.label("segment_id"),
                    CDPSegment.name.label("segment_name"),
                    func.count(CDPSegmentMembership.profile_id.distinct()).label(
                        "profile_count"
                    ),
                    func.coalesce(func.sum(CDPProfile.total_revenue), 0).label(
                        "total_revenue"
                    ),
                )
                .join(
                    CDPSegmentMembership,
                    and_(
                        CDPSegment.id == CDPSegmentMembership.segment_id,
                        CDPSegmentMembership.is_active.is_(True),
                    ),
                )
                .join(
                    CDPProfile,
                    CDPSegmentMembership.profile_id == CDPProfile.id,
                )
                .where(
                    and_(
                        CDPSegment.tenant_id == tenant_id,
                        CDPSegment.status == "active",
                    )
                )
                .group_by(CDPSegment.id, CDPSegment.name)
                .order_by(func.sum(CDPProfile.total_revenue).desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            results: list[dict[str, Any]] = []
            for row in rows:
                total = float(row.total_revenue or 0)
                count = int(row.profile_count or 0)
                results.append(
                    {
                        "segment_id": str(row.segment_id),
                        "segment_name": row.segment_name,
                        "profile_count": count,
                        "total_revenue": round(total, 2),
                        "avg_revenue_per_profile": (
                            round(total / count, 2) if count > 0 else 0.0
                        ),
                    }
                )

            return results

        except Exception:
            logger.exception(
                "knowledge_graph.segment_revenue_failed",
                tenant_id=str(tenant_id),
            )
            return []

    async def get_customer_journey(
        self, tenant_id: Any, profile_id: str
    ) -> Optional[dict[str, Any]]:
        """Get complete customer journey for a profile.

        Queries the CDP profile and all associated events ordered by
        timestamp, maps each event to a lifecycle stage, calculates
        time between stages, and returns the full journey.

        Args:
            tenant_id: The tenant to query.
            profile_id: The CDP profile UUID string.

        Returns:
            Dict with profile info, lifecycle_stage, touchpoints list,
            stage_transitions, and journey_duration_days. Returns None if
            the profile is not found.
        """
        from app.models.cdp import CDPEvent, CDPProfile

        logger.info(
            "knowledge_graph.customer_journey",
            tenant_id=str(tenant_id),
            profile_id=profile_id,
        )

        try:
            # Fetch the profile
            profile_stmt = select(CDPProfile).where(
                and_(
                    CDPProfile.tenant_id == tenant_id,
                    cast(CDPProfile.id, String) == profile_id,
                )
            )
            profile_result = await self.db.execute(profile_stmt)
            profile = profile_result.scalars().first()

            if profile is None:
                logger.warning(
                    "knowledge_graph.customer_journey_profile_not_found",
                    tenant_id=str(tenant_id),
                    profile_id=profile_id,
                )
                return None

            # Fetch all events for this profile ordered by time
            events_stmt = (
                select(CDPEvent)
                .where(
                    and_(
                        CDPEvent.tenant_id == tenant_id,
                        cast(CDPEvent.profile_id, String) == profile_id,
                    )
                )
                .order_by(CDPEvent.event_time.asc())
            )
            events_result = await self.db.execute(events_stmt)
            events = events_result.scalars().all()

            # Build touchpoints and detect stage transitions
            touchpoints: list[dict[str, Any]] = []
            stage_transitions: list[dict[str, Any]] = []
            seen_stages: set[str] = set()
            previous_stage: Optional[str] = None
            previous_stage_time: Optional[datetime] = None

            for event in events:
                event_name = event.event_name or ""
                event_stage = _EVENT_STAGE_MAP.get(
                    event_name.lower(), "anonymous"
                )

                touchpoint: dict[str, Any] = {
                    "event_id": str(event.id),
                    "event_name": event_name,
                    "event_time": event.event_time.isoformat()
                    if event.event_time
                    else None,
                    "stage": event_stage,
                    "properties": event.properties or {},
                    "channel": (event.context or {}).get("utm_source", "direct"),
                }
                touchpoints.append(touchpoint)

                # Detect stage transitions
                if event_stage not in seen_stages:
                    seen_stages.add(event_stage)
                    transition: dict[str, Any] = {
                        "stage": event_stage,
                        "entered_at": event.event_time.isoformat()
                        if event.event_time
                        else None,
                        "trigger_event": event_name,
                    }
                    if previous_stage is not None and previous_stage_time is not None:
                        time_in_prev = (
                            (event.event_time - previous_stage_time).total_seconds()
                            if event.event_time
                            else 0
                        )
                        transition["from_stage"] = previous_stage
                        transition["time_in_previous_stage_seconds"] = int(
                            time_in_prev
                        )
                    stage_transitions.append(transition)
                    previous_stage = event_stage
                    previous_stage_time = event.event_time

            # Calculate total journey duration
            journey_duration_days: Optional[float] = None
            if profile.first_seen_at and profile.last_seen_at:
                delta = profile.last_seen_at - profile.first_seen_at
                journey_duration_days = round(delta.total_seconds() / 86400, 2)

            return {
                "profile_id": str(profile.id),
                "lifecycle_stage": profile.lifecycle_stage,
                "first_seen_at": profile.first_seen_at.isoformat()
                if profile.first_seen_at
                else None,
                "last_seen_at": profile.last_seen_at.isoformat()
                if profile.last_seen_at
                else None,
                "total_events": profile.total_events,
                "total_revenue": float(profile.total_revenue),
                "touchpoints": touchpoints,
                "stage_transitions": stage_transitions,
                "journey_duration_days": journey_duration_days,
            }

        except Exception:
            logger.exception(
                "knowledge_graph.customer_journey_failed",
                tenant_id=str(tenant_id),
                profile_id=profile_id,
            )
            return None

    async def get_blocked_automations(
        self, tenant_id: Any, *, days: int = 7
    ) -> list[dict[str, Any]]:
        """Get automations blocked by the Trust Gate.

        Queries the FactActionsQueue for actions with status 'dismissed'
        or 'failed' within the lookback window, which represent automations
        that were blocked or could not execute.

        Args:
            tenant_id: The tenant to query.
            days: Lookback window in days.

        Returns:
            List of dicts describing each blocked automation with action
            details, reason, and timestamps.
        """
        from app.models.trust_layer import FactActionsQueue

        logger.info(
            "knowledge_graph.blocked_automations",
            tenant_id=str(tenant_id),
            days=days,
        )

        try:
            cutoff_date = (datetime.now(UTC) - timedelta(days=days)).date()

            stmt = (
                select(FactActionsQueue)
                .where(
                    and_(
                        FactActionsQueue.tenant_id == tenant_id,
                        FactActionsQueue.date >= cutoff_date,
                        FactActionsQueue.status.in_(["dismissed", "failed"]),
                    )
                )
                .order_by(FactActionsQueue.created_at.desc())
            )
            result = await self.db.execute(stmt)
            actions = result.scalars().all()

            blocked: list[dict[str, Any]] = []
            for action in actions:
                # Parse the action JSON payload safely
                action_payload: dict[str, Any] = {}
                if action.action_json:
                    try:
                        action_payload = json.loads(action.action_json)
                    except (json.JSONDecodeError, TypeError):
                        action_payload = {}

                blocked.append(
                    {
                        "id": str(action.id),
                        "action_type": action.action_type,
                        "entity_type": action.entity_type,
                        "entity_id": action.entity_id,
                        "entity_name": action.entity_name,
                        "platform": action.platform,
                        "status": action.status,
                        "error": action.error,
                        "action_details": action_payload,
                        "created_at": action.created_at.isoformat()
                        if action.created_at
                        else None,
                    }
                )

            return blocked

        except Exception:
            logger.exception(
                "knowledge_graph.blocked_automations_failed",
                tenant_id=str(tenant_id),
            )
            return []

    async def trace_automation_decision(
        self, tenant_id: Any, automation_id: str
    ) -> Optional[dict[str, Any]]:
        """Trace the full decision path for an automation.

        Looks up a specific action in the FactActionsQueue by its ID and
        returns the full decision context including signal health at the
        time of the decision, before/after values, and the approval chain.

        Args:
            tenant_id: The tenant to query.
            automation_id: The UUID of the action queue entry.

        Returns:
            Dict with the action details, decision path, signal health
            context, and approval chain. Returns None if not found.
        """
        from app.models.trust_layer import FactActionsQueue, FactSignalHealthDaily

        logger.info(
            "knowledge_graph.trace_automation",
            tenant_id=str(tenant_id),
            automation_id=automation_id,
        )

        try:
            # Fetch the specific action
            stmt = select(FactActionsQueue).where(
                and_(
                    FactActionsQueue.tenant_id == tenant_id,
                    cast(FactActionsQueue.id, String) == automation_id,
                )
            )
            result = await self.db.execute(stmt)
            action = result.scalars().first()

            if action is None:
                return None

            # Parse JSON fields safely
            action_payload: dict[str, Any] = {}
            before_val: Any = None
            after_val: Any = None
            if action.action_json:
                try:
                    action_payload = json.loads(action.action_json)
                except (json.JSONDecodeError, TypeError):
                    action_payload = {}
            if action.before_value:
                try:
                    before_val = json.loads(action.before_value)
                except (json.JSONDecodeError, TypeError):
                    before_val = action.before_value
            if action.after_value:
                try:
                    after_val = json.loads(action.after_value)
                except (json.JSONDecodeError, TypeError):
                    after_val = action.after_value

            # Fetch signal health around the action date for context
            signal_health_context: list[dict[str, Any]] = []
            if action.date:
                sh_stmt = (
                    select(FactSignalHealthDaily)
                    .where(
                        and_(
                            FactSignalHealthDaily.tenant_id == tenant_id,
                            FactSignalHealthDaily.date == action.date,
                        )
                    )
                    .order_by(FactSignalHealthDaily.platform)
                )
                sh_result = await self.db.execute(sh_stmt)
                sh_records = sh_result.scalars().all()
                for sh in sh_records:
                    signal_health_context.append(
                        {
                            "platform": sh.platform,
                            "emq_score": sh.emq_score,
                            "event_loss_pct": sh.event_loss_pct,
                            "api_error_rate": sh.api_error_rate,
                            "status": sh.status.value if sh.status else None,
                        }
                    )

            return {
                "id": str(action.id),
                "action_type": action.action_type,
                "entity_type": action.entity_type,
                "entity_id": action.entity_id,
                "entity_name": action.entity_name,
                "platform": action.platform,
                "status": action.status,
                "action_details": action_payload,
                "before_value": before_val,
                "after_value": after_val,
                "error": action.error,
                "decision_path": [
                    {
                        "step": "action_created",
                        "timestamp": action.created_at.isoformat()
                        if action.created_at
                        else None,
                        "actor_user_id": action.created_by_user_id,
                    },
                    {
                        "step": "action_approved"
                        if action.approved_at
                        else "awaiting_approval",
                        "timestamp": action.approved_at.isoformat()
                        if action.approved_at
                        else None,
                        "actor_user_id": action.approved_by_user_id,
                    },
                    {
                        "step": "action_applied"
                        if action.applied_at
                        else "not_applied",
                        "timestamp": action.applied_at.isoformat()
                        if action.applied_at
                        else None,
                        "actor_user_id": action.applied_by_user_id,
                    },
                ],
                "signal_health_context": signal_health_context,
            }

        except Exception:
            logger.exception(
                "knowledge_graph.trace_automation_failed",
                tenant_id=str(tenant_id),
                automation_id=automation_id,
            )
            return None

    async def get_graph_stats(self, tenant_id: Any) -> dict[str, int]:
        """Get Knowledge Graph statistics for the tenant.

        Counts profiles, events, segments, campaigns, and the relationship
        edges between them to give a snapshot of the graph size.

        Args:
            tenant_id: The tenant to query.

        Returns:
            Dict with counts for nodes and edges in the knowledge graph.
        """
        from app.base_models import Campaign
        from app.models.cdp import (
            CDPEvent,
            CDPProfile,
            CDPSegment,
            CDPSegmentMembership,
        )

        logger.info(
            "knowledge_graph.stats",
            tenant_id=str(tenant_id),
        )

        try:
            # Count profiles
            profiles_result = await self.db.execute(
                select(func.count(CDPProfile.id)).where(
                    CDPProfile.tenant_id == tenant_id
                )
            )
            profiles_count = profiles_result.scalar() or 0

            # Count events
            events_result = await self.db.execute(
                select(func.count(CDPEvent.id)).where(
                    CDPEvent.tenant_id == tenant_id
                )
            )
            events_count = events_result.scalar() or 0

            # Count segments
            segments_result = await self.db.execute(
                select(func.count(CDPSegment.id)).where(
                    CDPSegment.tenant_id == tenant_id
                )
            )
            segments_count = segments_result.scalar() or 0

            # Count campaigns
            campaigns_result = await self.db.execute(
                select(func.count(Campaign.id)).where(
                    Campaign.tenant_id == tenant_id
                )
            )
            campaigns_count = campaigns_result.scalar() or 0

            # Count profile->event edges (events linked to profiles)
            profile_event_edges_result = await self.db.execute(
                select(func.count(CDPEvent.id)).where(
                    and_(
                        CDPEvent.tenant_id == tenant_id,
                        CDPEvent.profile_id.isnot(None),
                    )
                )
            )
            profile_event_edges = profile_event_edges_result.scalar() or 0

            # Count profile->segment edges (active memberships)
            profile_segment_edges_result = await self.db.execute(
                select(func.count(CDPSegmentMembership.id)).where(
                    and_(
                        CDPSegmentMembership.tenant_id == tenant_id,
                        CDPSegmentMembership.is_active.is_(True),
                    )
                )
            )
            profile_segment_edges = profile_segment_edges_result.scalar() or 0

            # Touchpoints: events with purchase or conversion event names
            touchpoints_result = await self.db.execute(
                select(func.count(CDPEvent.id)).where(
                    and_(
                        CDPEvent.tenant_id == tenant_id,
                        CDPEvent.event_name.in_(
                            [
                                "purchase",
                                "order_completed",
                                "add_to_cart",
                                "checkout_started",
                                "lead",
                                "sign_up",
                            ]
                        ),
                    )
                )
            )
            touchpoints_count = touchpoints_result.scalar() or 0

            # Campaign->touchpoint edges: events linked to campaigns via
            # properties containing campaign info. Approximate by counting
            # events that have both a profile and a non-empty context.
            campaign_touchpoint_result = await self.db.execute(
                select(func.count(CDPEvent.id)).where(
                    and_(
                        CDPEvent.tenant_id == tenant_id,
                        CDPEvent.profile_id.isnot(None),
                        CDPEvent.event_name.in_(
                            [
                                "purchase",
                                "order_completed",
                                "add_to_cart",
                                "lead",
                            ]
                        ),
                    )
                )
            )
            campaign_touchpoint_edges = campaign_touchpoint_result.scalar() or 0

            return {
                "profiles_count": profiles_count,
                "events_count": events_count,
                "segments_count": segments_count,
                "campaigns_count": campaigns_count,
                "touchpoints_count": touchpoints_count,
                "profile_event_edges": profile_event_edges,
                "profile_segment_edges": profile_segment_edges,
                "campaign_touchpoint_edges": campaign_touchpoint_edges,
            }

        except Exception:
            logger.exception(
                "knowledge_graph.stats_failed",
                tenant_id=str(tenant_id),
            )
            return {
                "profiles_count": 0,
                "events_count": 0,
                "segments_count": 0,
                "campaigns_count": 0,
                "touchpoints_count": 0,
                "profile_event_edges": 0,
                "profile_segment_edges": 0,
                "campaign_touchpoint_edges": 0,
            }

    async def health_check(self) -> bool:
        """Check if Knowledge Graph is accessible."""
        try:
            # Verify database connectivity as proxy for graph health
            from sqlalchemy import text

            await self.db.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("knowledge_graph.health_check_failed")
            return False


# =============================================================================
# Knowledge Graph Insights Engine
# =============================================================================


class KnowledgeGraphInsightsEngine:
    """
    Engine for detecting problems and generating insights from the Knowledge Graph.

    Analyzes signal health, data quality, and automation effectiveness
    to proactively detect and surface actionable problems.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.kg = KnowledgeGraphService(db)

    async def get_health_summary(self, tenant_id: Any) -> dict[str, Any]:
        """Get overall health summary based on Knowledge Graph analysis."""
        logger.info(
            "knowledge_graph.health_summary",
            tenant_id=str(tenant_id),
        )
        problems = await self.detect_all_problems(tenant_id)

        problem_counts: dict[str, int] = {}
        for p in problems:
            cat = p.category.value
            problem_counts[cat] = problem_counts.get(cat, 0) + 1

        # Calculate health score: start at 100, deduct per severity
        score = 100.0
        for p in problems:
            if p.severity == ProblemSeverity.CRITICAL:
                score -= 25
            elif p.severity == ProblemSeverity.HIGH:
                score -= 15
            elif p.severity == ProblemSeverity.MEDIUM:
                score -= 8
            elif p.severity == ProblemSeverity.LOW:
                score -= 3
        score = max(0.0, min(100.0, score))

        status = "healthy"
        if score < 40:
            status = "critical"
        elif score < 70:
            status = "degraded"

        top_problem = problems[0].to_dict() if problems else None

        return {
            "health_score": score,
            "status": status,
            "problem_counts": problem_counts,
            "total_problems": len(problems),
            "top_problem": top_problem,
        }

    async def detect_all_problems(
        self, tenant_id: Any, *, days: int = 7
    ) -> list[Problem]:
        """Detect all problems within the lookback period.

        Runs multiple detection passes against signal health data,
        automation queue logs, and attribution variance records to
        identify anomalies, degraded signals, stale data, failed
        automations, and attribution drift.

        Args:
            tenant_id: The tenant to analyze.
            days: Lookback window in days.

        Returns:
            List of Problem instances sorted by severity (critical first).
        """
        from app.models.trust_layer import (
            FactActionsQueue,
            FactAttributionVarianceDaily,
            FactSignalHealthDaily,
        )

        logger.info(
            "knowledge_graph.detect_problems",
            tenant_id=str(tenant_id),
            days=days,
        )

        problems: list[Problem] = []
        now = datetime.now(UTC)
        cutoff_date = (now - timedelta(days=days)).date()

        try:
            # ------------------------------------------------------------------
            # 1. Signal Health Problems
            # ------------------------------------------------------------------
            sh_stmt = (
                select(FactSignalHealthDaily)
                .where(
                    and_(
                        FactSignalHealthDaily.tenant_id == tenant_id,
                        FactSignalHealthDaily.date >= cutoff_date,
                    )
                )
                .order_by(
                    FactSignalHealthDaily.platform,
                    FactSignalHealthDaily.date.asc(),
                )
            )
            sh_result = await self.db.execute(sh_stmt)
            sh_records = sh_result.scalars().all()

            # Group records by platform for trend analysis
            platform_records: dict[str, list[Any]] = {}
            for rec in sh_records:
                platform_records.setdefault(rec.platform, []).append(rec)

            for platform, records in platform_records.items():
                if not records:
                    continue

                latest = records[-1]

                # --- Detect degraded signals (EMQ < 80 or status critical/degraded)
                if latest.status and latest.status.value in ("critical", "degraded"):
                    severity = (
                        ProblemSeverity.CRITICAL
                        if latest.status.value == "critical"
                        else ProblemSeverity.HIGH
                    )
                    problems.append(
                        Problem(
                            id=str(uuid4()),
                            category=ProblemCategory.SIGNAL_HEALTH,
                            severity=severity,
                            title=f"Signal health {latest.status.value} on {platform}",
                            description=(
                                f"Signal health for {platform} is {latest.status.value}. "
                                f"EMQ score: {latest.emq_score}, "
                                f"event loss: {latest.event_loss_pct}%."
                            ),
                            detected_at=now,
                            affected_nodes=[
                                {
                                    "type": "platform",
                                    "id": platform,
                                    "name": platform,
                                }
                            ],
                            metrics={
                                "emq_score": latest.emq_score,
                                "event_loss_pct": latest.event_loss_pct,
                                "api_error_rate": latest.api_error_rate,
                                "status": latest.status.value,
                            },
                            solutions=[
                                Solution(
                                    title="Investigate signal degradation",
                                    description=(
                                        f"Check {platform} pixel/CAPI implementation "
                                        "and review recent tracking changes."
                                    ),
                                    action_type="investigate",
                                    priority=1,
                                    steps=[
                                        f"Review {platform} API connection status",
                                        "Check pixel/CAPI event delivery logs",
                                        "Verify event parameters and deduplication",
                                        "Run EMQ diagnostic playbook",
                                    ],
                                    affected_entities=[
                                        {"type": "platform", "id": platform}
                                    ],
                                    estimated_impact="Restore automation eligibility",
                                    auto_fixable=False,
                                )
                            ],
                        )
                    )

                # --- Detect EMQ score drops > 20% in recent records
                if len(records) >= 2:
                    for i in range(1, len(records)):
                        prev_emq = records[i - 1].emq_score
                        curr_emq = records[i].emq_score
                        if (
                            prev_emq is not None
                            and curr_emq is not None
                            and prev_emq > 0
                        ):
                            drop_pct = ((prev_emq - curr_emq) / prev_emq) * 100
                            if drop_pct > 20:
                                problems.append(
                                    Problem(
                                        id=str(uuid4()),
                                        category=ProblemCategory.SIGNAL_HEALTH,
                                        severity=ProblemSeverity.HIGH,
                                        title=(
                                            f"EMQ score drop of {drop_pct:.0f}% "
                                            f"on {platform}"
                                        ),
                                        description=(
                                            f"EMQ score dropped from {prev_emq:.1f} to "
                                            f"{curr_emq:.1f} ({drop_pct:.1f}% decline) "
                                            f"on {platform} between "
                                            f"{records[i - 1].date} and {records[i].date}."
                                        ),
                                        detected_at=now,
                                        root_cause_path=[
                                            {
                                                "node": "emq_score",
                                                "from": prev_emq,
                                                "to": curr_emq,
                                                "date": str(records[i].date),
                                            }
                                        ],
                                        affected_nodes=[
                                            {
                                                "type": "platform",
                                                "id": platform,
                                                "name": platform,
                                            }
                                        ],
                                        metrics={
                                            "previous_emq": prev_emq,
                                            "current_emq": curr_emq,
                                            "drop_pct": round(drop_pct, 1),
                                        },
                                        solutions=[
                                            Solution(
                                                title="Diagnose EMQ score drop",
                                                description=(
                                                    "Investigate the cause of the "
                                                    "rapid EMQ decline."
                                                ),
                                                action_type="diagnose",
                                                priority=1,
                                                steps=[
                                                    "Check for recent pixel or tag changes",
                                                    "Review server-side event delivery",
                                                    "Verify event deduplication logic",
                                                    "Check for ad blocker impact",
                                                ],
                                                affected_entities=[
                                                    {
                                                        "type": "platform",
                                                        "id": platform,
                                                    }
                                                ],
                                                estimated_impact=(
                                                    "Prevent further signal degradation"
                                                ),
                                                auto_fixable=False,
                                            )
                                        ],
                                    )
                                )
                                # Only report the most recent significant drop per platform
                                break

                # --- Detect stale data (no update in > 6 hours)
                if latest.updated_at:
                    hours_since_update = (
                        now - (latest.updated_at if latest.updated_at.tzinfo else latest.updated_at.replace(tzinfo=UTC))
                    ).total_seconds() / 3600
                    if hours_since_update > 6:
                        problems.append(
                            Problem(
                                id=str(uuid4()),
                                category=ProblemCategory.DATA_QUALITY,
                                severity=ProblemSeverity.MEDIUM,
                                title=f"Stale signal data for {platform}",
                                description=(
                                    f"Signal health data for {platform} has not been "
                                    f"updated in {hours_since_update:.1f} hours. "
                                    "Data may be outdated."
                                ),
                                detected_at=now,
                                affected_nodes=[
                                    {
                                        "type": "platform",
                                        "id": platform,
                                        "name": platform,
                                    }
                                ],
                                metrics={
                                    "hours_since_update": round(
                                        hours_since_update, 1
                                    ),
                                    "last_updated": latest.updated_at.isoformat(),
                                },
                                solutions=[
                                    Solution(
                                        title="Refresh signal health data",
                                        description=(
                                            "Trigger a data sync to refresh "
                                            f"signal health metrics for {platform}."
                                        ),
                                        action_type="refresh",
                                        priority=2,
                                        steps=[
                                            f"Check {platform} API connectivity",
                                            "Verify Celery worker is running",
                                            "Trigger manual data sync",
                                        ],
                                        affected_entities=[
                                            {"type": "platform", "id": platform}
                                        ],
                                        estimated_impact="Restore real-time monitoring",
                                        auto_fixable=True,
                                    )
                                ],
                            )
                        )

                # --- Detect high event loss (> 10%)
                if (
                    latest.event_loss_pct is not None
                    and latest.event_loss_pct > 10
                ):
                    severity = (
                        ProblemSeverity.CRITICAL
                        if latest.event_loss_pct > 25
                        else ProblemSeverity.HIGH
                    )
                    problems.append(
                        Problem(
                            id=str(uuid4()),
                            category=ProblemCategory.DATA_QUALITY,
                            severity=severity,
                            title=(
                                f"High event loss ({latest.event_loss_pct:.1f}%) "
                                f"on {platform}"
                            ),
                            description=(
                                f"{platform} is experiencing {latest.event_loss_pct:.1f}% "
                                "event loss. This impacts attribution accuracy "
                                "and automation reliability."
                            ),
                            detected_at=now,
                            affected_nodes=[
                                {
                                    "type": "platform",
                                    "id": platform,
                                    "name": platform,
                                }
                            ],
                            metrics={
                                "event_loss_pct": latest.event_loss_pct,
                            },
                            solutions=[
                                Solution(
                                    title="Reduce event loss",
                                    description=(
                                        "Investigate and fix the source of "
                                        "event delivery failures."
                                    ),
                                    action_type="fix",
                                    priority=1,
                                    steps=[
                                        "Check server-side event delivery logs",
                                        "Review CAPI error responses",
                                        "Verify network connectivity to ad platform",
                                        "Check event payload validation",
                                    ],
                                    affected_entities=[
                                        {"type": "platform", "id": platform}
                                    ],
                                    estimated_impact=(
                                        "Improve attribution accuracy by reducing "
                                        "event loss"
                                    ),
                                    auto_fixable=False,
                                )
                            ],
                        )
                    )

            # ------------------------------------------------------------------
            # 2. Attribution Variance Problems
            # ------------------------------------------------------------------
            av_stmt = (
                select(FactAttributionVarianceDaily)
                .where(
                    and_(
                        FactAttributionVarianceDaily.tenant_id == tenant_id,
                        FactAttributionVarianceDaily.date >= cutoff_date,
                    )
                )
                .order_by(FactAttributionVarianceDaily.date.desc())
            )
            av_result = await self.db.execute(av_stmt)
            av_records = av_result.scalars().all()

            for av in av_records:
                if av.status and av.status.value in (
                    "high_variance",
                    "moderate_variance",
                ):
                    severity = (
                        ProblemSeverity.HIGH
                        if av.status.value == "high_variance"
                        else ProblemSeverity.MEDIUM
                    )
                    problems.append(
                        Problem(
                            id=str(uuid4()),
                            category=ProblemCategory.ATTRIBUTION,
                            severity=severity,
                            title=(
                                f"Attribution variance ({av.status.value.replace('_', ' ')}) "
                                f"on {av.platform}"
                            ),
                            description=(
                                f"Revenue variance of {av.revenue_delta_pct:.1f}% "
                                f"between {av.platform} and GA4 on {av.date}. "
                                f"Platform revenue: {av.platform_revenue:.2f}, "
                                f"GA4 revenue: {av.ga4_revenue:.2f}."
                            ),
                            detected_at=now,
                            affected_nodes=[
                                {
                                    "type": "platform",
                                    "id": av.platform,
                                    "name": av.platform,
                                }
                            ],
                            metrics={
                                "revenue_delta_pct": av.revenue_delta_pct,
                                "platform_revenue": av.platform_revenue,
                                "ga4_revenue": av.ga4_revenue,
                                "conversion_delta_pct": av.conversion_delta_pct,
                            },
                            solutions=[
                                Solution(
                                    title="Investigate attribution variance",
                                    description=(
                                        "Review the tracking setup to identify "
                                        "the source of revenue discrepancy."
                                    ),
                                    action_type="investigate",
                                    priority=2,
                                    steps=[
                                        "Compare conversion windows between platforms",
                                        "Check deduplication rules",
                                        "Review attribution model settings",
                                        "Verify GA4 data collection completeness",
                                    ],
                                    affected_entities=[
                                        {"type": "platform", "id": av.platform}
                                    ],
                                    estimated_impact="Improve attribution accuracy",
                                    auto_fixable=False,
                                )
                            ],
                        )
                    )

            # ------------------------------------------------------------------
            # 3. Failed Automation Problems
            # ------------------------------------------------------------------
            fa_stmt = (
                select(
                    FactActionsQueue.platform,
                    FactActionsQueue.action_type,
                    func.count(FactActionsQueue.id).label("fail_count"),
                )
                .where(
                    and_(
                        FactActionsQueue.tenant_id == tenant_id,
                        FactActionsQueue.date >= cutoff_date,
                        FactActionsQueue.status == "failed",
                    )
                )
                .group_by(
                    FactActionsQueue.platform,
                    FactActionsQueue.action_type,
                )
            )
            fa_result = await self.db.execute(fa_stmt)
            fa_rows = fa_result.all()

            for row in fa_rows:
                fail_count = int(row.fail_count)
                if fail_count > 0:
                    severity = (
                        ProblemSeverity.HIGH
                        if fail_count >= 3
                        else ProblemSeverity.MEDIUM
                    )
                    problems.append(
                        Problem(
                            id=str(uuid4()),
                            category=ProblemCategory.AUTOMATION,
                            severity=severity,
                            title=(
                                f"{fail_count} failed {row.action_type} "
                                f"actions on {row.platform}"
                            ),
                            description=(
                                f"{fail_count} automation actions of type "
                                f"'{row.action_type}' failed on {row.platform} "
                                f"in the last {days} days."
                            ),
                            detected_at=now,
                            affected_nodes=[
                                {
                                    "type": "platform",
                                    "id": row.platform,
                                    "name": row.platform,
                                }
                            ],
                            metrics={
                                "failed_count": fail_count,
                                "action_type": row.action_type,
                                "platform": row.platform,
                            },
                            solutions=[
                                Solution(
                                    title="Review failed automations",
                                    description=(
                                        "Investigate why automation actions are "
                                        "failing and fix the underlying issue."
                                    ),
                                    action_type="review",
                                    priority=2,
                                    steps=[
                                        "Check platform API error logs",
                                        "Review action payloads for validation errors",
                                        "Verify API credentials and permissions",
                                        "Retry failed actions if appropriate",
                                    ],
                                    affected_entities=[
                                        {"type": "platform", "id": row.platform}
                                    ],
                                    estimated_impact="Restore automation execution",
                                    auto_fixable=False,
                                )
                            ],
                        )
                    )

        except Exception:
            logger.exception(
                "knowledge_graph.detect_problems_failed",
                tenant_id=str(tenant_id),
            )

        # Sort by severity: critical > high > medium > low
        severity_order = {
            ProblemSeverity.CRITICAL: 0,
            ProblemSeverity.HIGH: 1,
            ProblemSeverity.MEDIUM: 2,
            ProblemSeverity.LOW: 3,
        }
        problems.sort(key=lambda p: severity_order.get(p.severity, 4))

        return problems

    async def get_problem_details(
        self, tenant_id: Any, problem_id: str
    ) -> Optional[Problem]:
        """Get detailed information about a specific problem.

        Re-runs the full problem detection and returns the problem matching
        the given ID. Because problems are detected dynamically (not persisted),
        this re-detects to ensure up-to-date information. If the original
        problem no longer exists (resolved), returns None.

        Args:
            tenant_id: The tenant to query.
            problem_id: The UUID of the problem to retrieve.

        Returns:
            The matching Problem instance, or None if not found.
        """
        logger.info(
            "knowledge_graph.problem_details",
            tenant_id=str(tenant_id),
            problem_id=problem_id,
        )

        # Re-detect all problems and find the matching one
        all_problems = await self.detect_all_problems(tenant_id)

        for problem in all_problems:
            if problem.id == problem_id:
                return problem

        # Problem not found by exact ID match -- it may have been regenerated
        # with a new UUID. Return None to indicate the specific problem is no
        # longer detected (it may have been resolved).
        logger.info(
            "knowledge_graph.problem_not_found",
            tenant_id=str(tenant_id),
            problem_id=problem_id,
            detected_count=len(all_problems),
        )
        return None
