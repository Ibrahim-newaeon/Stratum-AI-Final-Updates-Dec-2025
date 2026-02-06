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

from .service import KnowledgeGraphService
from .models import (
    GraphNode,
    GraphEdge,
    ProfileNode,
    EventNode,
    SignalNode,
    TrustGateNode,
    AutomationNode,
    RevenueNode,
    CampaignNode,
    SegmentNode,
    ChannelNode,
    TouchpointNode,
)
from .queries import CypherQueryBuilder
from .sync import KnowledgeGraphSyncService

__all__ = [
    "KnowledgeGraphService",
    "KnowledgeGraphSyncService",
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
]
