# =============================================================================
# Stratum AI - Knowledge Graph (analytics logic) unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.knowledge_graph.

Pure graph-assembly logic, no I/O. Covers the Pearson helper, node /
edge generation, relationship tiering by ROAS, cross-platform
correlations, pattern discovery (concentration, performance gap, volume
vs efficiency, CPA), and ROAS-tier clustering.
"""

import pytest

from app.analytics.logic.knowledge_graph import (
    KnowledgeGraphResponse,
    _compute_correlation,
    build_knowledge_graph,
)

pytestmark = pytest.mark.unit


def _campaign(platform, spend, revenue, conversions=50, impressions=10000, clicks=500):
    return {
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
        "impressions": impressions,
        "clicks": clicks,
    }


# =============================================================================
# _compute_correlation
# =============================================================================
class TestCorrelation:
    def test_insufficient_points(self):
        assert _compute_correlation([1.0, 2.0], [1.0, 2.0]) == 0.0

    def test_perfect_positive(self):
        assert _compute_correlation([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)

    def test_perfect_negative(self):
        assert _compute_correlation([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)

    def test_zero_variance(self):
        assert _compute_correlation([5, 5, 5], [1, 2, 3]) == 0.0

    def test_uses_min_length(self):
        # extra values on one side are truncated
        assert _compute_correlation([1, 2, 3], [2, 4, 6, 99, 99]) == pytest.approx(1.0)


# =============================================================================
# Entry contract
# =============================================================================
class TestEmpty:
    def test_no_campaigns(self):
        resp = build_knowledge_graph([])
        assert isinstance(resp, KnowledgeGraphResponse)
        assert "No campaign data" in resp.summary
        assert resp.nodes == []


# =============================================================================
# Nodes
# =============================================================================
class TestNodes:
    def test_metric_nodes_present(self):
        resp = build_knowledge_graph([_campaign("meta", 1000.0, 3000.0)])
        node_ids = {n.node_id for n in resp.nodes}
        assert {"n_spend", "n_revenue", "n_roas", "n_cpa", "n_conversions"} <= node_ids
        roas_node = next(n for n in resp.nodes if n.node_id == "n_roas")
        assert roas_node.value == "3.00x"
        assert roas_node.importance == 100

    def test_platform_node_importance_is_spend_share(self):
        resp = build_knowledge_graph(
            [_campaign("meta", 750.0, 2000.0), _campaign("google", 250.0, 500.0)]
        )
        meta_node = next(n for n in resp.nodes if n.node_id == "n_meta")
        assert meta_node.node_type == "platform"
        assert meta_node.importance == pytest.approx(75.0)


# =============================================================================
# Edges
# =============================================================================
class TestEdges:
    def test_core_metric_edges(self):
        resp = build_knowledge_graph([_campaign("meta", 1000.0, 3000.0)])
        rels = {(e.source, e.target) for e in resp.edges}
        assert ("n_spend", "n_revenue") in rels
        assert ("n_revenue", "n_roas") in rels

    @pytest.mark.parametrize(
        "revenue,expected_rel",
        [
            (4000.0, "drives"),  # roas 4 >= 3
            (2000.0, "correlates_with"),  # roas 2, in [1.5,3)
            (1000.0, "inhibits"),  # roas 1 < 1.5
        ],
    )
    def test_platform_roas_relationship(self, revenue, expected_rel):
        resp = build_knowledge_graph([_campaign("meta", 1000.0, revenue)])
        edge = next(
            e for e in resp.edges if e.source == "n_meta" and e.target == "n_roas"
        )
        assert edge.relationship == expected_rel

    def test_cross_platform_correlation_when_similar(self):
        # two platforms with near-identical ROAS -> correlates_with edge
        resp = build_knowledge_graph(
            [_campaign("meta", 1000.0, 3000.0), _campaign("google", 1000.0, 3100.0)]
        )
        cross = [
            e for e in resp.edges if {e.source, e.target} == {"n_meta", "n_google"}
        ]
        assert cross and cross[0].relationship == "correlates_with"

    def test_no_cross_edge_when_divergent(self):
        resp = build_knowledge_graph(
            [_campaign("meta", 1000.0, 5000.0), _campaign("google", 1000.0, 500.0)]
        )
        cross = [
            e for e in resp.edges if {e.source, e.target} == {"n_meta", "n_google"}
        ]
        assert cross == []


# =============================================================================
# Patterns
# =============================================================================
class TestPatterns:
    def test_spend_concentration(self):
        resp = build_knowledge_graph(
            [_campaign("meta", 900.0, 2000.0), _campaign("google", 100.0, 300.0)]
        )
        conc = next(p for p in resp.patterns if p.pattern_type == "concentration")
        assert "concentrated on Meta" in conc.title
        assert conc.severity == "warning"

    def test_performance_gap(self):
        resp = build_knowledge_graph(
            [_campaign("meta", 1000.0, 4000.0), _campaign("google", 1000.0, 1000.0)]
        )
        gap = next(
            p for p in resp.patterns if p.title == "Performance gap between platforms"
        )
        assert gap.pattern_type == "correlation"

    def test_cpa_pattern_always_present_with_conversions(self):
        resp = build_knowledge_graph([_campaign("meta", 1000.0, 3000.0)])
        assert any("Average CPA" in p.title for p in resp.patterns)

    def test_key_insight_is_first_pattern(self):
        resp = build_knowledge_graph(
            [_campaign("meta", 900.0, 2000.0), _campaign("google", 100.0, 300.0)]
        )
        assert resp.key_insight == resp.patterns[0].title


# =============================================================================
# Clusters
# =============================================================================
class TestClusters:
    def test_roas_tier_clustering(self):
        campaigns = [
            _campaign("meta", 1000.0, 4000.0),  # 4x -> top
            _campaign("google", 1000.0, 2500.0),  # 2.5x -> above_average
            _campaign("tiktok", 1000.0, 1500.0),  # 1.5x -> average
            _campaign("snapchat", 1000.0, 500.0),  # 0.5x -> below_average
        ]
        resp = build_knowledge_graph(campaigns)
        levels = {c.performance_level for c in resp.clusters}
        assert levels == {"top", "above_average", "average", "below_average"}
        top = next(c for c in resp.clusters if c.performance_level == "top")
        assert top.campaign_count == 1
        assert top.avg_roas == 4.0

    def test_summary_counts(self):
        resp = build_knowledge_graph([_campaign("meta", 1000.0, 3000.0)])
        assert "entities" in resp.summary
        assert resp.total_relationships == len(resp.edges)
        assert resp.patterns_discovered == len(resp.patterns)
        assert "%" in resp.strongest_correlation
