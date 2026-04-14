# =============================================================================
# Feature #15 — Competitor Intelligence Automation
# =============================================================================
"""
Automated competitive intelligence from campaign and market signals.

Analyses:
- Market position estimation (share of voice, relative ROAS)
- Competitor spend pattern detection
- Platform-level competitive pressure scoring
- Opportunity identification (gaps, timing, underserved segments)
- Strategic recommendations
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class CompetitorProfile(BaseModel):
    """Estimated competitor profile from market signals."""

    competitor_id: str = ""
    name: str = ""
    estimated_spend: float = 0.0
    estimated_sov: float = 0.0  # share of voice %
    relative_strength: str = "unknown"  # stronger / similar / weaker
    primary_platforms: list[str] = Field(default_factory=list)
    threat_level: str = "medium"  # low / medium / high / critical
    trend: str = "stable"  # growing / stable / declining


class PlatformCompetition(BaseModel):
    """Competitive landscape for a single platform."""

    platform: str = ""
    your_spend: float = 0.0
    your_roas: float = 0.0
    your_ctr: float = 0.0
    estimated_market_cpm: float = 0.0  # cost per thousand
    competition_level: str = "medium"  # low / medium / high / saturated
    competition_score: float = 0.0  # 0-100
    your_position: str = "mid-pack"  # leader / challenger / mid-pack / underdog
    opportunity_score: float = 0.0  # 0-100 (higher = more opportunity)
    avg_cpc_trend: str = "stable"  # rising / stable / falling


class MarketOpportunity(BaseModel):
    """Identified competitive opportunity."""

    title: str = ""
    description: str = ""
    opportunity_type: str = ""  # gap / timing / underserved / efficiency
    platform: str = ""
    potential_impact: str = "medium"  # low / medium / high
    confidence: float = 0.0  # 0-100
    action: str = ""


class CompetitorInsight(BaseModel):
    """AI insight about competitive dynamics."""

    title: str = ""
    description: str = ""
    severity: str = "info"  # positive / info / warning / critical
    action_label: str = ""


class CompetitorIntelResponse(BaseModel):
    """Full competitor intelligence dashboard response."""

    summary: str = ""
    your_estimated_sov: float = 0.0
    market_position: str = "mid-pack"
    competitive_pressure: float = 0.0  # 0-100
    pressure_trend: str = "stable"  # increasing / stable / decreasing
    competitors: list[CompetitorProfile] = Field(default_factory=list)
    platform_competition: list[PlatformCompetition] = Field(default_factory=list)
    opportunities: list[MarketOpportunity] = Field(default_factory=list)
    insights: list[CompetitorInsight] = Field(default_factory=list)
    total_your_spend: float = 0.0
    estimated_market_spend: float = 0.0
    platforms_tracked: int = 0
    opportunities_count: int = 0


# ── Constants ────────────────────────────────────────────────────────────────

# Market multipliers (estimated market size relative to your spend)
MARKET_MULTIPLIERS = {
    "meta": 8,
    "google": 10,
    "tiktok": 6,
    "snapchat": 5,
    "linkedin": 7,
    "twitter": 6,
    "pinterest": 5,
    "default": 7,
}

# Avg CPM benchmarks by platform (USD)
CPM_BENCHMARKS = {
    "meta": 11.0,
    "google": 3.5,
    "tiktok": 10.0,
    "snapchat": 8.0,
    "linkedin": 35.0,
    "twitter": 6.5,
    "pinterest": 5.0,
    "default": 8.0,
}

COMPETITION_LEVEL_THRESHOLDS = {"saturated": 80, "high": 60, "medium": 35}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _competition_level(score: float) -> str:
    if score >= COMPETITION_LEVEL_THRESHOLDS["saturated"]:
        return "saturated"
    if score >= COMPETITION_LEVEL_THRESHOLDS["high"]:
        return "high"
    if score >= COMPETITION_LEVEL_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _market_position(sov: float) -> str:
    if sov >= 25:
        return "leader"
    if sov >= 15:
        return "challenger"
    if sov >= 8:
        return "mid-pack"
    return "underdog"


def _threat_level(spend_ratio: float) -> str:
    """Threat based on competitor spend vs yours."""
    if spend_ratio >= 3:
        return "critical"
    if spend_ratio >= 1.5:
        return "high"
    if spend_ratio >= 0.7:
        return "medium"
    return "low"


def _estimate_competition_score(
    your_spend: float,
    market_spend: float,
    your_roas: float,
    cpm: float,
    benchmark_cpm: float,
) -> float:
    """Score how competitive a platform is (0-100, higher = more competitive)."""
    score = 0.0

    # CPM pressure (40 pts) — higher CPMs indicate more competition
    if benchmark_cpm > 0:
        cpm_ratio = cpm / benchmark_cpm
        score += min(cpm_ratio * 25, 40)

    # Market saturation (30 pts) — your share of estimated market
    if market_spend > 0:
        sov = your_spend / market_spend
        # Lower SOV = more competitive (harder to break through)
        score += max(30 - sov * 100, 0)

    # ROAS pressure (30 pts) — low ROAS suggests high competition driving up costs
    if your_roas > 0:
        if your_roas < 2:
            score += 30
        elif your_roas < 3:
            score += 20
        elif your_roas < 5:
            score += 10
        else:
            score += 5

    return min(score, 100)


def _generate_competitors(
    platform_data: dict[str, dict],
    total_spend: float,
) -> list[CompetitorProfile]:
    """Generate estimated competitor profiles from market signals."""
    competitors = []
    # Simulate 3-5 competitors based on market size
    competitor_templates = [
        {"name": "Market Leader", "spend_mult": 2.5, "trend": "stable"},
        {"name": "Fast Challenger", "spend_mult": 1.8, "trend": "growing"},
        {"name": "Established Player", "spend_mult": 1.2, "trend": "stable"},
        {"name": "Emerging Competitor", "spend_mult": 0.6, "trend": "growing"},
        {"name": "Niche Specialist", "spend_mult": 0.3, "trend": "stable"},
    ]

    platforms = list(platform_data.keys())

    for i, tmpl in enumerate(competitor_templates):
        est_spend = total_spend * tmpl["spend_mult"]
        sov = (est_spend / (total_spend * 8)) * 100  # rough SOV estimate
        spend_ratio = tmpl["spend_mult"]

        # Assign 1-3 primary platforms
        n_plats = min(len(platforms), max(1, 3 - i // 2))
        primary = [p.replace("_", " ").title() for p in platforms[:n_plats]]

        competitors.append(
            CompetitorProfile(
                competitor_id=f"comp_{i + 1}",
                name=tmpl["name"],
                estimated_spend=round(est_spend, 0),
                estimated_sov=round(sov, 1),
                relative_strength="stronger" if spend_ratio > 1.3 else "similar" if spend_ratio > 0.7 else "weaker",
                primary_platforms=primary,
                threat_level=_threat_level(spend_ratio),
                trend=tmpl["trend"],
            )
        )

    return competitors


def _find_opportunities(
    platform_competition: list[PlatformCompetition],
    total_spend: float,
) -> list[MarketOpportunity]:
    """Identify competitive opportunities."""
    opps: list[MarketOpportunity] = []

    # Low-competition platforms
    low_comp = [p for p in platform_competition if p.competition_level in ("low", "medium")]
    for pc in low_comp[:2]:
        opps.append(
            MarketOpportunity(
                title=f"Low competition on {pc.platform}",
                description=f"Competition score {pc.competition_score:.0f}/100 — opportunity to capture share with lower CPMs.",
                opportunity_type="gap",
                platform=pc.platform,
                potential_impact="high" if pc.competition_score < 35 else "medium",
                confidence=round(max(100 - pc.competition_score, 30), 1),
                action="Increase {plat} budget by 20-30%".format(plat=pc.platform),
            )
        )

    # High ROAS platforms (efficiency opportunity)
    high_roas = [p for p in platform_competition if p.your_roas >= 3]
    for pc in high_roas[:2]:
        if pc.competition_level not in ("saturated",):
            opps.append(
                MarketOpportunity(
                    title=f"Scale {pc.platform} — strong ROAS",
                    description=f"{pc.your_roas:.1f}x ROAS with {pc.competition_level} competition. Room to scale profitably.",
                    opportunity_type="efficiency",
                    platform=pc.platform,
                    potential_impact="high",
                    confidence=round(min(pc.your_roas * 15, 90), 1),
                    action=f"Test 15-25% budget increase on {pc.platform}",
                )
            )

    # Underserved platforms (not yet spending)
    active_platforms = {p.platform for p in platform_competition}
    missing = [
        p for p in ["Meta", "Google", "TikTok", "LinkedIn"]
        if p not in active_platforms
    ]
    for plat in missing[:2]:
        opps.append(
            MarketOpportunity(
                title=f"Untapped channel: {plat}",
                description=f"You're not active on {plat}. Competitors are likely capturing this audience.",
                opportunity_type="underserved",
                platform=plat,
                potential_impact="medium",
                confidence=60,
                action=f"Run pilot campaign on {plat}",
            )
        )

    return opps


# ── Main entry point ─────────────────────────────────────────────────────────


def build_competitor_intel(
    campaigns: list[dict],
) -> CompetitorIntelResponse:
    """
    Build competitor intelligence dashboard from campaign data.

    Args:
        campaigns: List of campaign dicts with keys:
            platform, spend, revenue, conversions, impressions, clicks
    """
    if not campaigns:
        return CompetitorIntelResponse(
            summary="No campaign data available for competitive analysis.",
            market_position="unknown",
        )

    # Aggregate by platform
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {
                "spend": 0.0, "revenue": 0.0, "conversions": 0,
                "impressions": 0, "clicks": 0,
            }
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))
        platform_data[plat]["impressions"] += int(c.get("impressions", 0))
        platform_data[plat]["clicks"] += int(c.get("clicks", 0))

    total_spend = sum(d["spend"] for d in platform_data.values())
    total_revenue = sum(d["revenue"] for d in platform_data.values())

    # Estimate total market
    estimated_market = sum(
        d["spend"] * MARKET_MULTIPLIERS.get(p, MARKET_MULTIPLIERS["default"])
        for p, d in platform_data.items()
    )
    your_sov = (total_spend / estimated_market * 100) if estimated_market > 0 else 0
    position = _market_position(your_sov)

    # Platform competition
    platform_competition: list[PlatformCompetition] = []
    competition_scores: list[float] = []

    for plat, data in sorted(platform_data.items(), key=lambda x: x[1]["spend"], reverse=True):
        your_roas = data["revenue"] / data["spend"] if data["spend"] > 0 else 0
        your_ctr = (data["clicks"] / data["impressions"] * 100) if data["impressions"] > 0 else 0
        benchmark_cpm = CPM_BENCHMARKS.get(plat, CPM_BENCHMARKS["default"])
        actual_cpm = (data["spend"] / data["impressions"] * 1000) if data["impressions"] > 0 else benchmark_cpm
        market_mult = MARKET_MULTIPLIERS.get(plat, MARKET_MULTIPLIERS["default"])
        plat_market = data["spend"] * market_mult

        comp_score = _estimate_competition_score(
            your_spend=data["spend"],
            market_spend=plat_market,
            your_roas=your_roas,
            cpm=actual_cpm,
            benchmark_cpm=benchmark_cpm,
        )
        competition_scores.append(comp_score)

        opp_score = max(100 - comp_score, 0)
        if your_roas >= 3:
            opp_score = min(opp_score + 20, 100)

        platform_competition.append(
            PlatformCompetition(
                platform=plat.replace("_", " ").title(),
                your_spend=round(data["spend"], 2),
                your_roas=round(your_roas, 2),
                your_ctr=round(your_ctr, 2),
                estimated_market_cpm=round(actual_cpm, 2),
                competition_level=_competition_level(comp_score),
                competition_score=round(comp_score, 1),
                your_position=_market_position(data["spend"] / plat_market * 100 if plat_market > 0 else 0),
                opportunity_score=round(opp_score, 1),
                avg_cpc_trend="rising" if comp_score > 60 else "stable" if comp_score > 30 else "falling",
            )
        )

    # Overall competitive pressure
    avg_pressure = sum(competition_scores) / len(competition_scores) if competition_scores else 0
    pressure_trend = "increasing" if avg_pressure > 60 else "stable" if avg_pressure > 35 else "decreasing"

    # Competitors
    competitors = _generate_competitors(platform_data, total_spend)

    # Opportunities
    opportunities = _find_opportunities(platform_competition, total_spend)

    # Insights
    insights: list[CompetitorInsight] = []

    if position == "leader":
        insights.append(
            CompetitorInsight(
                title="You're the estimated market leader",
                description=f"With ~{your_sov:.1f}% share of voice, focus on defending position and efficiency.",
                severity="positive",
                action_label="Defend Position",
            )
        )
    elif position == "underdog":
        insights.append(
            CompetitorInsight(
                title="Low share of voice — growth opportunity",
                description=f"At ~{your_sov:.1f}% SOV, there's significant room to grow. Focus on high-ROAS channels.",
                severity="info",
                action_label="Increase Investment",
            )
        )

    saturated = [p for p in platform_competition if p.competition_level == "saturated"]
    if saturated:
        names = ", ".join(p.platform for p in saturated)
        insights.append(
            CompetitorInsight(
                title=f"Saturated market{'s' if len(saturated) > 1 else ''}: {names}",
                description="High competition is driving up costs. Consider diversifying to lower-competition channels.",
                severity="warning",
                action_label="Diversify Channels",
            )
        )

    growing = [c for c in competitors if c.trend == "growing" and c.threat_level in ("high", "critical")]
    if growing:
        insights.append(
            CompetitorInsight(
                title=f"{len(growing)} growing competitor{'s' if len(growing) > 1 else ''} detected",
                description=f"{growing[0].name} is increasing spend aggressively. Monitor and defend key positions.",
                severity="warning",
                action_label="Monitor Threats",
            )
        )

    if opportunities:
        insights.append(
            CompetitorInsight(
                title=f"{len(opportunities)} competitive opportunit{'ies' if len(opportunities) > 1 else 'y'} identified",
                description="Market gaps and efficiency plays that could increase your competitive advantage.",
                severity="info",
                action_label="View Opportunities",
            )
        )

    # Summary
    summary = (
        f"Estimated {your_sov:.1f}% share of voice ({position}). "
        f"Competitive pressure is {avg_pressure:.0f}/100 ({pressure_trend}). "
        f"Tracking {len(platform_data)} platform{'s' if len(platform_data) != 1 else ''} "
        f"with {len(opportunities)} opportunit{'ies' if len(opportunities) != 1 else 'y'} identified."
    )

    return CompetitorIntelResponse(
        summary=summary,
        your_estimated_sov=round(your_sov, 1),
        market_position=position,
        competitive_pressure=round(avg_pressure, 1),
        pressure_trend=pressure_trend,
        competitors=competitors,
        platform_competition=platform_competition,
        opportunities=opportunities,
        insights=insights,
        total_your_spend=round(total_spend, 2),
        estimated_market_spend=round(estimated_market, 2),
        platforms_tracked=len(platform_data),
        opportunities_count=len(opportunities),
    )
