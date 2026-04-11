# =============================================================================
# Stratum AI - Knowledge Graph Integration Tests
# =============================================================================
"""
Integration tests for the Knowledge Graph service.
Tests model creation, Cypher property serialization, node/edge validation,
and service operations without requiring a live database.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.services.knowledge_graph.models import (
    AccountNode,
    AutomationStatus,
    EdgeLabel,
    GateDecision,
    GraphEdge,
    GraphNode,
    LifecycleStage,
    NodeLabel,
    Platform,
    ProfileNode,
    SignalStatus,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def profile_node(tenant_id):
    return ProfileNode(
        tenant_id=tenant_id,
        external_id="profile_001",
        lifecycle_stage=LifecycleStage.CUSTOMER,
        email_hash="abc123def456",
        total_events=50,
        total_purchases=3,
        total_revenue_cents=15000,
    )


@pytest.fixture
def account_node(tenant_id):
    return AccountNode(
        tenant_id=tenant_id,
        external_id="account_001",
        name="Acme Corp",
        industry="Technology",
        arr_cents=1200000,
        health_score=85.5,
    )


@pytest.fixture
def sample_edge(tenant_id):
    return GraphEdge(
        start_node_id="v_001",
        end_node_id="v_002",
        label=EdgeLabel.BELONGS_TO,
        tenant_id=tenant_id,
        properties={"weight": 1.0},
    )


# =============================================================================
# Node Model Tests
# =============================================================================

class TestProfileNode:
    """Tests for ProfileNode creation and serialization."""

    def test_profile_node_creation(self, profile_node, tenant_id):
        """Profile node should have correct fields."""
        assert profile_node.tenant_id == tenant_id
        assert profile_node.external_id == "profile_001"
        assert profile_node.lifecycle_stage == LifecycleStage.CUSTOMER
        assert profile_node.total_events == 50
        assert profile_node.total_purchases == 3

    def test_profile_node_default_lifecycle(self, tenant_id):
        """Default lifecycle stage should be ANONYMOUS."""
        node = ProfileNode(tenant_id=tenant_id, external_id="test")
        assert node.lifecycle_stage == LifecycleStage.ANONYMOUS

    def test_profile_node_cypher_properties(self, profile_node):
        """Cypher properties dict should serialize all fields."""
        props = profile_node.to_cypher_properties()
        assert props["external_id"] == "profile_001"
        assert props["lifecycle_stage"] == "customer"
        assert props["total_events"] == 50
        assert props["total_revenue_cents"] == 15000
        assert "tenant_id" in props
        assert "created_at" in props

    def test_profile_node_computed_label(self, profile_node):
        """Computed label should return 'Profile'."""
        assert profile_node.label == "Profile"

    def test_profile_node_timestamps(self, profile_node):
        """created_at and updated_at should be set."""
        assert profile_node.created_at is not None
        assert profile_node.updated_at is not None
        assert isinstance(profile_node.created_at, datetime)


class TestAccountNode:
    """Tests for AccountNode creation and serialization."""

    def test_account_node_creation(self, account_node):
        """Account node should store business data."""
        assert account_node.name == "Acme Corp"
        assert account_node.industry == "Technology"
        assert account_node.arr_cents == 1200000
        assert account_node.health_score == 85.5

    def test_account_node_cypher_properties(self, account_node):
        """Account cypher properties should serialize correctly."""
        props = account_node.to_cypher_properties()
        assert props["name"] == "Acme Corp"
        assert props["industry"] == "Technology"
        assert props["arr_cents"] == 1200000
        assert props["health_score"] == 85.5

    def test_account_node_label(self, account_node):
        """Computed label should return 'Account'."""
        assert account_node.label == "Account"


# =============================================================================
# Edge Model Tests
# =============================================================================

class TestGraphEdge:
    """Tests for GraphEdge creation and serialization."""

    def test_edge_creation(self, sample_edge, tenant_id):
        """Edge should link two nodes with a label."""
        assert sample_edge.start_node_id == "v_001"
        assert sample_edge.end_node_id == "v_002"
        assert sample_edge.label == EdgeLabel.BELONGS_TO
        assert sample_edge.tenant_id == tenant_id

    def test_edge_cypher_properties(self, sample_edge):
        """Edge cypher properties should include custom properties."""
        props = sample_edge.to_cypher_properties()
        assert props["weight"] == 1.0
        assert "tenant_id" in props
        assert "created_at" in props

    def test_all_edge_labels_valid(self):
        """All EdgeLabel values should be non-empty strings."""
        for label in EdgeLabel:
            assert isinstance(label.value, str)
            assert len(label.value) > 0


# =============================================================================
# Enum Tests
# =============================================================================

class TestKnowledgeGraphEnums:
    """Tests for Knowledge Graph enums."""

    def test_node_labels_complete(self):
        """NodeLabel should have all required labels."""
        required = {"Profile", "Account", "Event", "Signal", "TrustGate",
                     "Automation", "Segment", "Campaign", "Channel", "Revenue"}
        actual = {nl.value for nl in NodeLabel}
        assert required.issubset(actual), f"Missing labels: {required - actual}"

    def test_edge_labels_complete(self):
        """EdgeLabel should have attribution and trust edges."""
        required = {"ATTRIBUTED_TO", "EVALUATED_BY", "TRIGGERED", "BLOCKED", "DROVE"}
        actual = {el.value for el in EdgeLabel}
        assert required.issubset(actual), f"Missing edges: {required - actual}"

    def test_lifecycle_stages(self):
        """All lifecycle stages should be valid."""
        stages = [s.value for s in LifecycleStage]
        assert "anonymous" in stages
        assert "customer" in stages
        assert "churned" in stages

    def test_gate_decisions(self):
        """Trust gate decisions should match architecture."""
        decisions = {d.value for d in GateDecision}
        assert decisions == {"pass", "hold", "block"}

    def test_signal_statuses(self):
        """Signal statuses should match health model."""
        statuses = {s.value for s in SignalStatus}
        assert "healthy" in statuses
        assert "degraded" in statuses
        assert "critical" in statuses

    def test_platforms_include_major(self):
        """Platform enum should include all major ad platforms."""
        platforms = {p.value for p in Platform}
        assert {"meta", "google", "tiktok", "snapchat"}.issubset(platforms)


# =============================================================================
# Cross-Node Relationship Tests
# =============================================================================

class TestNodeRelationships:
    """Tests for creating valid node-edge-node triples."""

    def test_profile_belongs_to_account(self, tenant_id, profile_node, account_node):
        """Can create a BELONGS_TO edge between profile and account."""
        edge = GraphEdge(
            start_node_id=profile_node.external_id,
            end_node_id=account_node.external_id,
            label=EdgeLabel.BELONGS_TO,
            tenant_id=tenant_id,
        )
        assert edge.label == EdgeLabel.BELONGS_TO
        assert edge.start_node_id == "profile_001"
        assert edge.end_node_id == "account_001"

    def test_attributed_to_edge(self, tenant_id):
        """Revenue attribution edge should carry properties."""
        edge = GraphEdge(
            start_node_id="revenue_001",
            end_node_id="channel_meta",
            label=EdgeLabel.ATTRIBUTED_TO,
            tenant_id=tenant_id,
            properties={
                "attribution_model": "data_driven",
                "credit_pct": 0.35,
                "revenue_cents": 50000,
            },
        )
        props = edge.to_cypher_properties()
        assert props["attribution_model"] == "data_driven"
        assert props["credit_pct"] == 0.35

    def test_trust_gate_evaluation_edge(self, tenant_id):
        """Trust gate edge should capture decision metadata."""
        edge = GraphEdge(
            start_node_id="signal_001",
            end_node_id="gate_001",
            label=EdgeLabel.EVALUATED_BY,
            tenant_id=tenant_id,
            properties={
                "health_score": 72.5,
                "decision": "pass",
                "threshold": 70.0,
            },
        )
        props = edge.to_cypher_properties()
        assert props["decision"] == "pass"
        assert props["health_score"] == 72.5
