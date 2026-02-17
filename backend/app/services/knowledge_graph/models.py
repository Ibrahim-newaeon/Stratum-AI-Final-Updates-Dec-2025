"""
Knowledge Graph Node and Edge Models

Pydantic models for graph entities that integrate with Stratum's
CDP, Trust Engine, and Revenue Attribution systems.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

# =============================================================================
# ENUMS
# =============================================================================

class NodeLabel(str, Enum):
    """Vertex labels in the knowledge graph."""
    PROFILE = "Profile"
    ACCOUNT = "Account"
    EVENT = "Event"
    SIGNAL = "Signal"
    TRUST_GATE = "TrustGate"
    AUTOMATION = "Automation"
    SEGMENT = "Segment"
    CAMPAIGN = "Campaign"
    CHANNEL = "Channel"
    REVENUE = "Revenue"
    TOUCHPOINT = "Touchpoint"
    HEALTH_SCORE = "HealthScore"


class EdgeLabel(str, Enum):
    """Edge labels in the knowledge graph."""
    BELONGS_TO = "BELONGS_TO"
    PERFORMED = "PERFORMED"
    GENERATED = "GENERATED"
    EVALUATED_BY = "EVALUATED_BY"
    TRIGGERED = "TRIGGERED"
    BLOCKED = "BLOCKED"
    PRODUCED = "PRODUCED"
    ATTRIBUTED_TO = "ATTRIBUTED_TO"
    DROVE = "DROVE"
    RECEIVED = "RECEIVED"
    HAS_HEALTH = "HAS_HEALTH"
    MERGED_INTO = "MERGED_INTO"
    LINKED_TO = "LINKED_TO"
    CONVERTED_FROM = "CONVERTED_FROM"
    INFLUENCED = "INFLUENCED"


class LifecycleStage(str, Enum):
    """CDP profile lifecycle stages."""
    ANONYMOUS = "anonymous"
    KNOWN = "known"
    CUSTOMER = "customer"
    CHURNED = "churned"


class SignalStatus(str, Enum):
    """Signal health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class GateDecision(str, Enum):
    """Trust gate decision outcomes."""
    PASS = "pass"
    HOLD = "hold"
    BLOCK = "block"


class AutomationStatus(str, Enum):
    """Automation execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Platform(str, Enum):
    """Advertising platforms."""
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
    WHATSAPP = "whatsapp"
    ORGANIC = "organic"
    DIRECT = "direct"


# =============================================================================
# BASE MODELS
# =============================================================================

class GraphNode(BaseModel):
    """Base class for all graph nodes."""
    id: Optional[str] = Field(default=None, description="AGE vertex ID")
    tenant_id: UUID = Field(..., description="Tenant isolation")
    external_id: str = Field(..., description="External system ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    properties: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def label(self) -> str:
        """Return the node label for Cypher queries."""
        return self.__class__.__name__.replace("Node", "")

    def to_cypher_properties(self) -> dict[str, Any]:
        """Convert to properties dict for Cypher CREATE/MERGE."""
        props = {
            "tenant_id": str(self.tenant_id),
            "external_id": self.external_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            **self.properties,
        }
        # Add class-specific fields
        for field_name, field_info in self.model_fields.items():
            if field_name not in ("id", "tenant_id", "external_id", "created_at", "updated_at", "properties"):
                value = getattr(self, field_name)
                if value is not None:
                    if isinstance(value, Enum):
                        props[field_name] = value.value
                    elif isinstance(value, (datetime,)):
                        props[field_name] = value.isoformat()
                    elif isinstance(value, (UUID,)):
                        props[field_name] = str(value)
                    elif isinstance(value, (Decimal,)):
                        props[field_name] = float(value)
                    else:
                        props[field_name] = value
        return props


class GraphEdge(BaseModel):
    """Base class for all graph edges."""
    id: Optional[str] = Field(default=None, description="AGE edge ID")
    start_node_id: str = Field(..., description="Source vertex ID")
    end_node_id: str = Field(..., description="Target vertex ID")
    label: EdgeLabel = Field(..., description="Relationship type")
    tenant_id: UUID = Field(..., description="Tenant isolation")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    properties: dict[str, Any] = Field(default_factory=dict)

    def to_cypher_properties(self) -> dict[str, Any]:
        """Convert to properties dict for Cypher CREATE."""
        return {
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat(),
            **self.properties,
        }


# =============================================================================
# ACTOR NODES (Who)
# =============================================================================

class ProfileNode(GraphNode):
    """
    CDP customer profile vertex.

    Represents a unified customer identity with lifecycle tracking.
    Maps to: CDPProfile in the relational model.
    """
    lifecycle_stage: LifecycleStage = Field(default=LifecycleStage.ANONYMOUS)
    email_hash: Optional[str] = Field(default=None, description="SHA256 of email")
    phone_hash: Optional[str] = Field(default=None, description="SHA256 of phone")
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    total_events: int = Field(default=0)
    total_sessions: int = Field(default=0)
    total_purchases: int = Field(default=0)
    total_revenue_cents: int = Field(default=0)
    rfm_segment: Optional[str] = Field(default=None, description="RFM segment label")
    rfm_score: Optional[int] = Field(default=None, description="Composite RFM score")
    computed_traits: dict[str, Any] = Field(default_factory=dict)


class AccountNode(GraphNode):
    """
    Business account vertex.

    Represents a B2B account that profiles belong to.
    """
    name: str
    industry: Optional[str] = None
    arr_cents: Optional[int] = Field(default=None, description="Annual recurring revenue")
    health_score: Optional[float] = Field(default=None, ge=0, le=100)
    employee_count: Optional[int] = None


class SegmentNode(GraphNode):
    """
    Customer segment vertex.

    Represents a dynamic or static segment from CDP.
    Maps to: CDPSegment in the relational model.
    """
    name: str
    segment_type: str = Field(default="dynamic", description="static|dynamic|computed")
    profile_count: int = Field(default=0)
    conditions: dict[str, Any] = Field(default_factory=dict, description="Segment rules")
    last_computed_at: Optional[datetime] = None


# =============================================================================
# ACTION NODES (What)
# =============================================================================

class EventNode(GraphNode):
    """
    Customer event vertex.

    Represents an action taken by a profile (page_view, purchase, etc.).
    Maps to: CDPEvent in the relational model.
    """
    event_type: str = Field(..., description="Event name (e.g., 'purchase', 'page_view')")
    event_time: datetime
    source: Optional[str] = Field(default=None, description="Event source (website, app, etc.)")
    emq_score: Optional[float] = Field(default=None, ge=0, le=100, description="Event Match Quality")
    revenue_cents: Optional[int] = Field(default=None, description="Revenue if applicable")
    event_properties: dict[str, Any] = Field(default_factory=dict)


class TouchpointNode(GraphNode):
    """
    Marketing touchpoint vertex.

    Represents a customer interaction (email, ad impression, etc.).
    """
    touchpoint_type: str = Field(..., description="email|ad|social|organic|direct")
    channel: str
    campaign_id: Optional[str] = None
    timestamp: datetime
    is_converting: bool = Field(default=False)


class AutomationNode(GraphNode):
    """
    Automation action vertex.

    Represents an automated action from the Autopilot engine.
    """
    action_type: str = Field(..., description="update_budget|pause|scale|etc.")
    entity_type: str = Field(default="campaign", description="campaign|adset|ad")
    entity_id: str
    platform: Platform
    status: AutomationStatus = Field(default=AutomationStatus.PENDING)
    parameters: dict[str, Any] = Field(default_factory=dict)
    executed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    signal_health_at_execution: Optional[float] = None


# =============================================================================
# CONTROL NODES (How/Why)
# =============================================================================

class SignalNode(GraphNode):
    """
    Data quality signal vertex.

    Represents a signal health measurement from the Trust Engine.
    """
    signal_type: str = Field(..., description="emq|freshness|variance|anomaly|cdp")
    source: str = Field(..., description="Data source (platform, CDP, etc.)")
    platform: Optional[Platform] = None
    score: float = Field(..., ge=0, le=100)
    status: SignalStatus
    issues: list[str] = Field(default_factory=list)
    measured_at: datetime


class TrustGateNode(GraphNode):
    """
    Trust gate decision vertex.

    Represents a decision checkpoint from the Trust Engine.
    """
    decision: GateDecision
    signal_health_score: float = Field(..., ge=0, le=100)
    threshold_used: float
    action_type: str = Field(..., description="Action being evaluated")
    action_risk_level: str = Field(default="standard", description="high|standard|conservative")
    reason: str = Field(..., description="Human-readable decision reason")
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: datetime
    is_dry_run: bool = Field(default=False)


class HealthScoreNode(GraphNode):
    """
    Composite health score vertex.

    Aggregates multiple signals into overall health.
    """
    overall_score: float = Field(..., ge=0, le=100)
    emq_score: Optional[float] = None
    freshness_score: Optional[float] = None
    variance_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    cdp_emq_score: Optional[float] = None
    status: SignalStatus
    measured_at: datetime


# =============================================================================
# OUTCOME NODES (Results)
# =============================================================================

class RevenueNode(GraphNode):
    """
    Revenue event vertex.

    Represents a revenue-generating outcome.
    """
    amount_cents: int
    currency: str = Field(default="USD")
    revenue_type: str = Field(default="purchase", description="purchase|subscription|renewal|upsell")
    occurred_at: datetime
    attributed_campaign_id: Optional[str] = None
    attributed_channel: Optional[str] = None
    attribution_model: Optional[str] = Field(default=None, description="first_touch|last_touch|linear|data_driven")


class CampaignNode(GraphNode):
    """
    Marketing campaign vertex.

    Represents an advertising campaign.
    Maps to: Campaign in the relational model.
    """
    name: str
    platform: Platform
    platform_campaign_id: str
    status: str = Field(default="active")
    objective: Optional[str] = None
    budget_cents: Optional[int] = None
    spend_cents: int = Field(default=0)
    impressions: int = Field(default=0)
    clicks: int = Field(default=0)
    conversions: int = Field(default=0)
    revenue_cents: int = Field(default=0)
    roas: Optional[float] = None


class ChannelNode(GraphNode):
    """
    Acquisition channel vertex.

    Represents a traffic/acquisition source.
    """
    name: str
    channel_type: str = Field(..., description="paid|organic|direct|referral|social|email")
    platform: Optional[Platform] = None
    total_profiles: int = Field(default=0)
    total_revenue_cents: int = Field(default=0)
    conversion_rate: Optional[float] = None


# =============================================================================
# EDGE PROPERTY MODELS
# =============================================================================

class BelongsToEdge(GraphEdge):
    """Profile belongs to Segment or Account."""
    label: EdgeLabel = EdgeLabel.BELONGS_TO
    added_at: datetime = Field(default_factory=datetime.utcnow)
    match_score: Optional[float] = Field(default=None, ge=0, le=1)


class PerformedEdge(GraphEdge):
    """Profile performed Event."""
    label: EdgeLabel = EdgeLabel.PERFORMED
    session_id: Optional[str] = None


class GeneratedEdge(GraphEdge):
    """Event generated Signal or Revenue."""
    label: EdgeLabel = EdgeLabel.GENERATED
    confidence: float = Field(default=1.0, ge=0, le=1)


class EvaluatedByEdge(GraphEdge):
    """Signal evaluated by TrustGate."""
    label: EdgeLabel = EdgeLabel.EVALUATED_BY
    weight: float = Field(default=1.0, description="Signal weight in evaluation")


class TriggeredEdge(GraphEdge):
    """Signal or TrustGate triggered Automation."""
    label: EdgeLabel = EdgeLabel.TRIGGERED
    trigger_type: str = Field(default="rule", description="rule|threshold|manual")


class BlockedEdge(GraphEdge):
    """TrustGate blocked Automation."""
    label: EdgeLabel = EdgeLabel.BLOCKED
    reason: str
    signal_health_at_block: float


class ProducedEdge(GraphEdge):
    """Automation produced Revenue outcome."""
    label: EdgeLabel = EdgeLabel.PRODUCED
    attribution_weight: float = Field(default=1.0, ge=0, le=1)


class AttributedToEdge(GraphEdge):
    """Revenue attributed to Campaign or Channel."""
    label: EdgeLabel = EdgeLabel.ATTRIBUTED_TO
    attribution_model: str = Field(default="last_touch")
    attribution_weight: float = Field(default=1.0, ge=0, le=1)
    touchpoint_position: Optional[int] = Field(default=None, description="Position in journey")


class DroveEdge(GraphEdge):
    """Campaign drove Revenue."""
    label: EdgeLabel = EdgeLabel.DROVE
    contribution_cents: int = Field(default=0)


class InfluencedEdge(GraphEdge):
    """Touchpoint influenced conversion (multi-touch)."""
    label: EdgeLabel = EdgeLabel.INFLUENCED
    influence_score: float = Field(default=0.5, ge=0, le=1)
    days_before_conversion: Optional[int] = None
