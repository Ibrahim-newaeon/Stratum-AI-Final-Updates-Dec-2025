"""
Stratum Knowledge Graph

Revenue-focused Knowledge Graph using PostgreSQL + Apache AGE.
Integrates with CDP profiles, Trust Engine signals, and automation decisions.

Usage:
    from app.services.knowledge_graph import KnowledgeGraphService

    kg = KnowledgeGraphService(db_session)

    # Add a profile node
    kg.create_profile(tenant_id, profile_id, properties)

    # Query revenue attribution
    results = kg.get_revenue_attribution(tenant_id, date_range)

    # Trace automation decision
    path = kg.trace_automation_decision(automation_id)
"""

from .insights import (
    KnowledgeGraphInsightsEngine,
    Problem,
    ProblemCategory,
    ProblemSeverity,
    Solution,
)
from .models import (
    AutomationNode,
    CampaignNode,
    ChannelNode,
    EventNode,
    GraphEdge,
    GraphNode,
    ProfileNode,
    RevenueNode,
    SegmentNode,
    SignalNode,
    TouchpointNode,
    TrustGateNode,
)
from .queries import CypherQueryBuilder
from .service import KnowledgeGraphService
from .sync import KnowledgeGraphSyncService

__all__ = [
    "KnowledgeGraphService",
    "KnowledgeGraphSyncService",
    "KnowledgeGraphInsightsEngine",
    "CypherQueryBuilder",
    "GraphNode",
    "GraphEdge",
    "ProfileNode",
    "EventNode",
    "SignalNode",
    "TrustGateNode",
    "AutomationNode",
    "RevenueNode",
    "CampaignNode",
    "SegmentNode",
    "ChannelNode",
    "TouchpointNode",
    "Problem",
    "Solution",
    "ProblemSeverity",
    "ProblemCategory",
]
