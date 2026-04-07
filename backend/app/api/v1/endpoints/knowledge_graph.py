"""
Knowledge Graph API Endpoints

Provides REST API for Knowledge Graph analytics, insights, and problem detection.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import User
from app.services.knowledge_graph import (
    KnowledgeGraphInsightsEngine,
    KnowledgeGraphService,
    ProblemCategory,
    ProblemSeverity,
)
from app.tenancy.deps import get_current_user, get_db

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class SolutionResponse(BaseModel):
    """Solution suggestion for a detected problem."""
    title: str
    description: str
    action_type: str
    priority: int
    steps: list[str]
    affected_entities: list[dict[str, Any]]
    estimated_impact: Optional[str]
    auto_fixable: bool


class ProblemResponse(BaseModel):
    """Detected problem with context and solutions."""
    id: str
    category: str
    severity: str
    title: str
    description: str
    detected_at: datetime
    root_cause_path: list[dict[str, Any]]
    affected_nodes: list[dict[str, Any]]
    metrics: dict[str, Any]
    solutions: list[SolutionResponse]


class HealthSummaryResponse(BaseModel):
    """Overall health summary from Knowledge Graph analysis."""
    health_score: float = Field(..., ge=0, le=100)
    status: str  # healthy, degraded, critical
    problem_counts: dict[str, int]
    total_problems: int
    top_problem: Optional[ProblemResponse]


class ProblemsListResponse(BaseModel):
    """List of detected problems."""
    problems: list[ProblemResponse]
    total: int
    by_severity: dict[str, int]


class RevenueByChannelResponse(BaseModel):
    """Revenue breakdown by channel."""
    channel: str
    transaction_count: int = 0
    revenue: float = 0.0
    avg_order_value: float = 0.0


class RevenueBySegmentResponse(BaseModel):
    """Revenue breakdown by segment."""
    segment_id: str = ""
    segment_name: str
    profile_count: int = 0
    total_revenue: float = 0.0
    avg_revenue_per_profile: float = 0.0


class CustomerJourneyResponse(BaseModel):
    """Customer journey data."""
    profile_id: str
    lifecycle_stage: Optional[str] = "unknown"
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    total_events: int = 0
    total_revenue: float = 0.0
    touchpoints: list[dict[str, Any]] = []
    stage_transitions: list[dict[str, Any]] = []
    journey_duration_days: Optional[float] = None


class GraphStatsResponse(BaseModel):
    """Knowledge Graph statistics."""
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    total_nodes: int
    total_edges: int


# =============================================================================
# INSIGHTS ENDPOINTS
# =============================================================================

@router.get("/insights/health", response_model=HealthSummaryResponse)
async def get_health_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthSummaryResponse:
    """
    Get overall health summary based on Knowledge Graph analysis.

    Returns health score, status, and top problem if any.
    """
    engine = KnowledgeGraphInsightsEngine(db)
    summary = await engine.get_health_summary(current_user.tenant_id)

    return HealthSummaryResponse(
        health_score=summary["health_score"],
        status=summary["status"],
        problem_counts=summary["problem_counts"],
        total_problems=summary["total_problems"],
        top_problem=summary.get("top_problem"),
    )


@router.get("/insights/problems", response_model=ProblemsListResponse)
async def get_detected_problems(
    days: int = Query(default=7, ge=1, le=90, description="Lookback period in days"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProblemsListResponse:
    """
    Get all detected problems with solutions.

    Problems are sorted by severity (critical first).
    Each problem includes root cause analysis and suggested solutions.
    """
    engine = KnowledgeGraphInsightsEngine(db)
    problems = await engine.detect_all_problems(current_user.tenant_id, days=days)

    # Apply filters
    if severity:
        try:
            sev = ProblemSeverity(severity.lower())
            problems = [p for p in problems if p.severity == sev]
        except ValueError:
            pass

    if category:
        try:
            cat = ProblemCategory(category.lower())
            problems = [p for p in problems if p.category == cat]
        except ValueError:
            pass

    # Count by severity
    by_severity = {
        "critical": len([p for p in problems if p.severity == ProblemSeverity.CRITICAL]),
        "high": len([p for p in problems if p.severity == ProblemSeverity.HIGH]),
        "medium": len([p for p in problems if p.severity == ProblemSeverity.MEDIUM]),
        "low": len([p for p in problems if p.severity == ProblemSeverity.LOW]),
    }

    return ProblemsListResponse(
        problems=[ProblemResponse(**p.to_dict()) for p in problems],
        total=len(problems),
        by_severity=by_severity,
    )


@router.get("/insights/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem_details(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProblemResponse:
    """
    Get detailed information about a specific problem.

    Includes extended root cause analysis and all suggested solutions.
    """
    engine = KnowledgeGraphInsightsEngine(db)
    problem = await engine.get_problem_details(current_user.tenant_id, problem_id)

    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    return ProblemResponse(**problem.to_dict())


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/revenue/by-channel", response_model=list[RevenueByChannelResponse])
async def get_revenue_by_channel(
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RevenueByChannelResponse]:
    """
    Get revenue breakdown by acquisition channel.

    Uses Knowledge Graph to trace revenue attribution through touchpoints.
    """
    kg = KnowledgeGraphService(db)
    results = await kg.get_revenue_by_channel(current_user.tenant_id, days=days)

    return [
        RevenueByChannelResponse(
            channel=r.get("channel", "Unknown"),
            transaction_count=r.get("transaction_count", 0),
            revenue=r.get("revenue", 0.0),
            avg_order_value=r.get("avg_order_value", 0.0),
        )
        for r in results
    ]


@router.get("/analytics/revenue/by-segment", response_model=list[RevenueBySegmentResponse])
async def get_revenue_by_segment(
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RevenueBySegmentResponse]:
    """
    Get revenue breakdown by customer segment.

    Shows which CDP segments are driving the most revenue.
    """
    kg = KnowledgeGraphService(db)
    results = await kg.get_segment_revenue_performance(current_user.tenant_id, days=days)

    return [
        RevenueBySegmentResponse(
            segment_id=r.get("segment_id", ""),
            segment_name=r.get("segment_name", "Unknown"),
            profile_count=r.get("profile_count", 0),
            total_revenue=r.get("total_revenue", 0.0),
            avg_revenue_per_profile=r.get("avg_revenue_per_profile", 0.0),
        )
        for r in results
    ]


@router.get("/analytics/journey/{profile_id}", response_model=CustomerJourneyResponse)
async def get_customer_journey(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerJourneyResponse:
    """
    Get complete customer journey for a profile.

    Traces all events, touchpoints, and revenue through the Knowledge Graph.
    """
    kg = KnowledgeGraphService(db)
    journey = await kg.get_customer_journey(current_user.tenant_id, profile_id)

    if not journey:
        raise HTTPException(status_code=404, detail="Profile not found")

    return CustomerJourneyResponse(
        profile_id=journey.get("profile_id", profile_id),
        lifecycle_stage=journey.get("lifecycle_stage", "unknown"),
        first_seen_at=journey.get("first_seen_at"),
        last_seen_at=journey.get("last_seen_at"),
        total_events=journey.get("total_events", 0),
        total_revenue=journey.get("total_revenue", 0.0),
        touchpoints=journey.get("touchpoints", []),
        stage_transitions=journey.get("stage_transitions", []),
        journey_duration_days=journey.get("journey_duration_days"),
    )


@router.get("/analytics/blocked-automations")
async def get_blocked_automations(
    days: int = Query(default=7, ge=1, le=90, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Get automations that were blocked by Trust Gate.

    Includes block reason and signal health at time of block.
    """
    kg = KnowledgeGraphService(db)
    return await kg.get_blocked_automations(current_user.tenant_id, days=days)


@router.get("/analytics/automation/{automation_id}/trace")
async def trace_automation_decision(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Trace the full decision path for an automation.

    Shows: Signal -> TrustGate -> Automation -> Outcome
    """
    kg = KnowledgeGraphService(db)
    trace = await kg.trace_automation_decision(current_user.tenant_id, automation_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Automation not found")

    return trace


# =============================================================================
# GRAPH STATS ENDPOINTS
# =============================================================================

@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GraphStatsResponse:
    """
    Get Knowledge Graph statistics for the tenant.

    Returns counts of all node and edge types.
    """
    kg = KnowledgeGraphService(db)
    stats = await kg.get_graph_stats(current_user.tenant_id)

    # Separate node and edge counts
    node_counts = {k: v for k, v in stats.items() if k.endswith("_count") and not k.endswith("_edges")}
    edge_counts = {k: v for k, v in stats.items() if k.endswith("_edges")}

    return GraphStatsResponse(
        node_counts=node_counts,
        edge_counts=edge_counts,
        total_nodes=sum(node_counts.values()),
        total_edges=sum(edge_counts.values()),
    )


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Check if Knowledge Graph is accessible.

    Used for monitoring and health checks.
    """
    kg = KnowledgeGraphService(db)
    is_healthy = await kg.health_check()

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "graph_name": kg.GRAPH_NAME,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
