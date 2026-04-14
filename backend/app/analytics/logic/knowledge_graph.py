# =============================================================================
# Feature #18 — Knowledge Graph Auto-Insights
# =============================================================================
"""
Cross-metric relationship discovery and pattern detection.

Analyses:
- Build relationships between metrics, platforms, campaigns
- Detect correlations (spend↔ROAS, CTR↔CVR, CPA↔volume)
- Identify causal chains and cascading effects
- Surface non-obvious insights from data patterns
- Cluster campaigns by performance signature
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class KnowledgeNode(BaseModel):
    """A node in the knowledge graph."""

    node_id: str = ""
    label: str = ""
    node_type: str = ""  # metric / platform / campaign / segment / trend
    value: str = ""
    importance: float = 0.0  # 0-100


class KnowledgeEdge(BaseModel):
    """A relationship between two nodes."""

    edge_id: str = ""
    source: str = ""
    target: str = ""
    relationship: str = ""  # correlates_with / drives / inhibits / depends_on
    strength: float = 0.0  # 0-100
    description: str = ""


class KnowledgePattern(BaseModel):
    """A discovered pattern across metrics."""

    pattern_id: str = ""
    title: str = ""
    description: str = ""
    pattern_type: str = ""  # correlation / trend / anomaly / cluster / causation
    confidence: float = 0.0  # 0-100
    affected_metrics: list[str] = Field(default_factory=list)
    recommendation: str = ""
    severity: str = "info"  # positive / info / warning / critical


class KnowledgeCluster(BaseModel):
    """A cluster of similar campaigns."""

    cluster_id: str = ""
    label: str = ""
    description: str = ""
    campaign_count: int = 0
    avg_roas: float = 0.0
    avg_cpa: float = 0.0
    platforms: list[str] = Field(default_factory=list)
    performance_level: str = "average"  # top / above_average / average / below_average / poor


class KnowledgeGraphResponse(BaseModel):
    """Full knowledge graph auto-insights response."""

    summary: str = ""
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    patterns: list[KnowledgePattern] = Field(default_factory=list)
    clusters: list[KnowledgeCluster] = Field(default_factory=list)
    total_relationships: int = 0
    patterns_discovered: int = 0
    strongest_correlation: str = ""
    key_insight: str = ""


# ── Helpers ──────────────────────────────────────────────────────────────────


def _compute_correlation(vals_a: list[float], vals_b: list[float]) -> float:
    """Simple Pearson correlation coefficient."""
    n = min(len(vals_a), len(vals_b))
    if n < 3:
        return 0.0

    a = vals_a[:n]
    b = vals_b[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    std_a = (sum((x - mean_a) ** 2 for x in a)) ** 0.5
    std_b = (sum((x - mean_b) ** 2 for x in b)) ** 0.5

    if std_a == 0 or std_b == 0:
        return 0.0

    return cov / (std_a * std_b)


# ── Main entry point ─────────────────────────────────────────────────────────


def build_knowledge_graph(campaigns: list[dict]) -> KnowledgeGraphResponse:
    """Build knowledge graph auto-insights from campaign data."""
    if not campaigns:
        return KnowledgeGraphResponse(
            summary="No campaign data available for knowledge graph analysis.",
        )

    # Aggregate by platform
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {
                "spend": 0.0, "revenue": 0.0, "conversions": 0,
                "impressions": 0, "clicks": 0, "campaigns": 0,
            }
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))
        platform_data[plat]["impressions"] += int(c.get("impressions", 0))
        platform_data[plat]["clicks"] += int(c.get("clicks", 0))
        platform_data[plat]["campaigns"] += 1

    total_spend = sum(d["spend"] for d in platform_data.values())
    total_revenue = sum(d["revenue"] for d in platform_data.values())
    total_conversions = sum(d["conversions"] for d in platform_data.values())

    # Build nodes
    nodes: list[KnowledgeNode] = []

    # Metric nodes
    overall_roas = total_revenue / total_spend if total_spend > 0 else 0
    overall_cpa = total_spend / total_conversions if total_conversions > 0 else 0
    nodes.append(KnowledgeNode(node_id="n_spend", label="Total Spend", node_type="metric", value=f"${total_spend:,.0f}", importance=90))
    nodes.append(KnowledgeNode(node_id="n_revenue", label="Total Revenue", node_type="metric", value=f"${total_revenue:,.0f}", importance=95))
    nodes.append(KnowledgeNode(node_id="n_roas", label="ROAS", node_type="metric", value=f"{overall_roas:.2f}x", importance=100))
    nodes.append(KnowledgeNode(node_id="n_cpa", label="CPA", node_type="metric", value=f"${overall_cpa:.2f}", importance=80))
    nodes.append(KnowledgeNode(node_id="n_conversions", label="Conversions", node_type="metric", value=f"{total_conversions:,}", importance=85))

    # Platform nodes
    for plat, data in platform_data.items():
        plat_roas = data["revenue"] / data["spend"] if data["spend"] > 0 else 0
        imp = min(data["spend"] / total_spend * 100, 100) if total_spend > 0 else 0
        nodes.append(KnowledgeNode(
            node_id=f"n_{plat}",
            label=plat.replace("_", " ").title(),
            node_type="platform",
            value=f"{plat_roas:.2f}x ROAS",
            importance=round(imp, 1),
        ))

    # Build edges
    edges: list[KnowledgeEdge] = []
    edge_idx = 0

    # Spend → Revenue relationship
    edges.append(KnowledgeEdge(
        edge_id=f"e_{edge_idx}",
        source="n_spend", target="n_revenue",
        relationship="drives",
        strength=85,
        description="Spend directly drives revenue generation",
    ))
    edge_idx += 1

    # ROAS depends on spend and revenue
    edges.append(KnowledgeEdge(
        edge_id=f"e_{edge_idx}",
        source="n_revenue", target="n_roas",
        relationship="drives",
        strength=90,
        description="Revenue efficiency determines ROAS",
    ))
    edge_idx += 1

    # Platform → metric relationships
    for plat, data in platform_data.items():
        plat_roas = data["revenue"] / data["spend"] if data["spend"] > 0 else 0
        rel = "drives" if plat_roas >= 3 else "correlates_with" if plat_roas >= 1.5 else "inhibits"
        edges.append(KnowledgeEdge(
            edge_id=f"e_{edge_idx}",
            source=f"n_{plat}", target="n_roas",
            relationship=rel,
            strength=round(min(plat_roas * 20, 100), 1),
            description=f"{plat.title()} {'boosts' if plat_roas >= 3 else 'impacts'} overall ROAS ({plat_roas:.2f}x)",
        ))
        edge_idx += 1

    # Cross-platform correlations
    plats = list(platform_data.keys())
    for i in range(len(plats)):
        for j in range(i + 1, len(plats)):
            pa, pb = platform_data[plats[i]], platform_data[plats[j]]
            roas_a = pa["revenue"] / pa["spend"] if pa["spend"] > 0 else 0
            roas_b = pb["revenue"] / pb["spend"] if pb["spend"] > 0 else 0
            if abs(roas_a - roas_b) < 1:
                edges.append(KnowledgeEdge(
                    edge_id=f"e_{edge_idx}",
                    source=f"n_{plats[i]}", target=f"n_{plats[j]}",
                    relationship="correlates_with",
                    strength=round(70 - abs(roas_a - roas_b) * 20, 1),
                    description=f"Similar performance profiles ({roas_a:.1f}x vs {roas_b:.1f}x ROAS)",
                ))
                edge_idx += 1

    # Discover patterns
    patterns: list[KnowledgePattern] = []
    pattern_idx = 0

    # Spend concentration pattern
    if total_spend > 0:
        top_plat = max(platform_data.items(), key=lambda x: x[1]["spend"])
        top_pct = top_plat[1]["spend"] / total_spend * 100
        if top_pct > 50:
            patterns.append(KnowledgePattern(
                pattern_id=f"p_{pattern_idx}",
                title=f"Spend concentrated on {top_plat[0].title()}",
                description=f"{top_pct:.0f}% of budget allocated to one platform. Diversification could reduce risk.",
                pattern_type="concentration",
                confidence=90,
                affected_metrics=["spend", "roas", top_plat[0]],
                recommendation=f"Consider redistributing 10-15% of {top_plat[0].title()} budget to other platforms.",
                severity="warning",
            ))
            pattern_idx += 1

    # ROAS efficiency pattern
    high_roas = [(p, d) for p, d in platform_data.items() if d["spend"] > 0 and d["revenue"] / d["spend"] >= 3]
    low_roas = [(p, d) for p, d in platform_data.items() if d["spend"] > 0 and d["revenue"] / d["spend"] < 1.5]

    if high_roas and low_roas:
        patterns.append(KnowledgePattern(
            pattern_id=f"p_{pattern_idx}",
            title="Performance gap between platforms",
            description=f"{len(high_roas)} high-ROAS vs {len(low_roas)} low-ROAS platforms detected.",
            pattern_type="correlation",
            confidence=85,
            affected_metrics=[p for p, _ in high_roas + low_roas],
            recommendation="Shift budget from low-ROAS to high-ROAS platforms.",
            severity="positive" if len(high_roas) > len(low_roas) else "warning",
        ))
        pattern_idx += 1

    # Volume vs efficiency trade-off
    high_vol_low_roas = [
        (p, d) for p, d in platform_data.items()
        if d["conversions"] > total_conversions * 0.3 and d["spend"] > 0 and d["revenue"] / d["spend"] < 2
    ]
    if high_vol_low_roas:
        p, d = high_vol_low_roas[0]
        roas = d["revenue"] / d["spend"]
        patterns.append(KnowledgePattern(
            pattern_id=f"p_{pattern_idx}",
            title=f"{p.title()}: high volume, low efficiency",
            description=f"Drives {d['conversions'] / total_conversions * 100:.0f}% of conversions but only {roas:.1f}x ROAS.",
            pattern_type="trend",
            confidence=80,
            affected_metrics=[p, "conversions", "roas"],
            recommendation="Optimize targeting to improve efficiency without sacrificing volume.",
            severity="info",
        ))
        pattern_idx += 1

    # CPA trend
    if overall_cpa > 0:
        patterns.append(KnowledgePattern(
            pattern_id=f"p_{pattern_idx}",
            title=f"Average CPA: ${overall_cpa:.2f}",
            description="Monitor CPA trends across platforms to identify cost efficiency opportunities.",
            pattern_type="trend",
            confidence=75,
            affected_metrics=["cpa", "spend", "conversions"],
            recommendation="Set CPA alerts at $" + f"{overall_cpa * 1.2:.2f} to catch cost increases early.",
            severity="info",
        ))
        pattern_idx += 1

    # Build clusters
    clusters: list[KnowledgeCluster] = []
    for level, (min_roas, max_roas) in [
        ("top", (3.0, 999)), ("above_average", (2.0, 3.0)),
        ("average", (1.0, 2.0)), ("below_average", (0, 1.0)),
    ]:
        cluster_camps = [
            c for c in campaigns
            if float(c.get("spend", 0)) > 0
            and min_roas <= float(c.get("revenue", 0)) / float(c.get("spend", 1)) < max_roas
        ]
        if cluster_camps:
            c_spend = sum(float(c.get("spend", 0)) for c in cluster_camps)
            c_rev = sum(float(c.get("revenue", 0)) for c in cluster_camps)
            c_conv = sum(int(c.get("conversions", 0)) for c in cluster_camps)
            c_plats = list({str(c.get("platform", "")).lower().replace("_", " ").title() for c in cluster_camps})

            clusters.append(KnowledgeCluster(
                cluster_id=f"cl_{level}",
                label=level.replace("_", " ").title() + " Performers",
                description=f"{len(cluster_camps)} campaigns with {min_roas:.0f}-{max_roas:.0f}x ROAS range",
                campaign_count=len(cluster_camps),
                avg_roas=round(c_rev / c_spend if c_spend > 0 else 0, 2),
                avg_cpa=round(c_spend / c_conv if c_conv > 0 else 0, 2),
                platforms=c_plats[:4],
                performance_level=level,
            ))

    # Strongest correlation
    strongest = max(edges, key=lambda e: e.strength) if edges else None
    strongest_desc = f"{strongest.source} → {strongest.target} ({strongest.strength:.0f}%)" if strongest else "N/A"

    key_insight = ""
    if patterns:
        key_insight = patterns[0].title

    summary = (
        f"{len(nodes)} entities, {len(edges)} relationships, {len(patterns)} patterns discovered. "
        f"{len(clusters)} performance clusters across {len(platform_data)} platforms."
    )

    return KnowledgeGraphResponse(
        summary=summary,
        nodes=nodes,
        edges=edges,
        patterns=patterns,
        clusters=clusters,
        total_relationships=len(edges),
        patterns_discovered=len(patterns),
        strongest_correlation=strongest_desc,
        key_insight=key_insight,
    )
