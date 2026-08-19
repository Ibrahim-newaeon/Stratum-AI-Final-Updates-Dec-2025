# =============================================================================
# Feature #15 — Competitor Intelligence Automation
# =============================================================================
"""
Your paid-media position per platform, from your own campaigns.

This module receives one input: the tenant's campaigns. It has no competitor
data, no market panel and no ad-intelligence provider, so it reports only what
those campaigns support — spend, ROAS, CTR and CPM per platform, and how your
CPM compares to a published industry average.

Three things it used to return were manufactured from that same nothing and
have been removed rather than relabelled:

* Five invented competitor companies ("Apex Digital Group", "VeloMedia", ...)
  with spends that were the tenant's own spend times a hard-coded multiplier.
  Every tenant saw the same five names.
* ``your_estimated_sov`` — ``spend / (spend * MARKET_MULTIPLIER)``, which is
  ``100 / MARKET_MULTIPLIER``: a constant fixed by platform mix alone. A
  meta-only tenant read 12.5% at $1k/month and 12.5% at $5M/month.
  ``market_position`` thresholded that constant, so it never moved either.
* ``estimated_market_spend`` — your own spend times the same multiplier.

A share of voice that cannot move is not a weaker measurement; it is not one.
Restoring any of them means wiring a real market source first.

Analyses:
- Platform-level competitive pressure from measured CPM and ROAS
- Opportunity identification (gaps, timing, underserved segments)
- Strategic recommendations
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# ── Response models ──────────────────────────────────────────────────────────


class PlatformCompetition(BaseModel):
    """Competitive landscape for a single platform."""

    platform: str = ""
    your_spend: float = 0.0
    your_roas: float = 0.0
    your_ctr: float = 0.0
    # Ours, computed from the spend and impressions given — not a measurement
    # of what anyone else pays. It was called estimated_market_cpm.
    your_cpm: float = 0.0  # cost per thousand
    competition_level: str = "medium"  # low / medium / high / saturated
    competition_score: float = 0.0  # 0-100
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
    competitive_pressure: float = 0.0  # 0-100
    pressure_trend: str = "stable"  # increasing / stable / decreasing
    platform_competition: list[PlatformCompetition] = Field(default_factory=list)
    opportunities: list[MarketOpportunity] = Field(default_factory=list)
    insights: list[CompetitorInsight] = Field(default_factory=list)
    total_your_spend: float = 0.0
    platforms_tracked: int = 0
    opportunities_count: int = 0


# ── Constants ────────────────────────────────────────────────────────────────

# Published industry average CPMs by platform (USD). These are an external
# reference point, not something this system measured — comparing your CPM to a
# published average is a real and useful thing to do, presenting the average as
# observed market data would not be.
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


def _estimate_competition_score(
    your_roas: float,
    cpm: float,
    benchmark_cpm: float,
) -> float:
    """Score how competitive a platform is (0-100, higher = more competitive)."""
    score = 0.0

    # CPM pressure (60 pts) — higher CPMs indicate more competition
    if benchmark_cpm > 0:
        cpm_ratio = cpm / benchmark_cpm
        score += min(cpm_ratio * 35, 60)

    # The "market saturation" term that used to sit here contributed
    # your_spend / (your_spend * MARKET_MULTIPLIER) — a constant. It shifted
    # every score by the same amount and told you nothing, so the remaining
    # two measured components carry the full 100.

    # ROAS pressure (40 pts) — low ROAS suggests high competition driving up costs
    if your_roas > 0:
        if your_roas < 2:
            score += 40
        elif your_roas < 3:
            score += 20
        elif your_roas < 5:
            score += 10
        else:
            score += 5

    return min(score, 100)


def _find_opportunities(
    platform_competition: list[PlatformCompetition],
    total_spend: float,
) -> list[MarketOpportunity]:
    """Identify competitive opportunities."""
    opps: list[MarketOpportunity] = []

    # Low-competition platforms
    low_comp = [
        p for p in platform_competition if p.competition_level in ("low", "medium")
    ]
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
        p for p in ["Meta", "Google", "TikTok", "LinkedIn"] if p not in active_platforms
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
        )

    # Aggregate by platform
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {
                "spend": 0.0,
                "revenue": 0.0,
                "conversions": 0,
                "impressions": 0,
                "clicks": 0,
            }
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))
        platform_data[plat]["impressions"] += int(c.get("impressions", 0))
        platform_data[plat]["clicks"] += int(c.get("clicks", 0))

    total_spend = sum(d["spend"] for d in platform_data.values())
    total_revenue = sum(d["revenue"] for d in platform_data.values())

    # Platform competition
    platform_competition: list[PlatformCompetition] = []
    competition_scores: list[float] = []

    for plat, data in sorted(
        platform_data.items(), key=lambda x: x[1]["spend"], reverse=True
    ):
        your_roas = data["revenue"] / data["spend"] if data["spend"] > 0 else 0
        your_ctr = (
            (data["clicks"] / data["impressions"] * 100)
            if data["impressions"] > 0
            else 0
        )
        benchmark_cpm = CPM_BENCHMARKS.get(plat, CPM_BENCHMARKS["default"])
        actual_cpm = (
            (data["spend"] / data["impressions"] * 1000)
            if data["impressions"] > 0
            else benchmark_cpm
        )
        comp_score = _estimate_competition_score(
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
                your_cpm=round(actual_cpm, 2),
                competition_level=_competition_level(comp_score),
                competition_score=round(comp_score, 1),
                opportunity_score=round(opp_score, 1),
                avg_cpc_trend=(
                    "rising"
                    if comp_score > 60
                    else "stable" if comp_score > 30 else "falling"
                ),
            )
        )

    # Overall competitive pressure
    avg_pressure = (
        sum(competition_scores) / len(competition_scores) if competition_scores else 0
    )
    pressure_trend = (
        "increasing"
        if avg_pressure > 60
        else "stable" if avg_pressure > 35 else "decreasing"
    )

    # Opportunities
    opportunities = _find_opportunities(platform_competition, total_spend)

    # Insights
    insights: list[CompetitorInsight] = []

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

    # A "N growing competitors detected" insight used to sit here, naming one
    # of the five invented companies and reporting that it was "increasing
    # spend aggressively". Nothing detected anything: the trend was a literal
    # in the hard-coded profile list.

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
        f"Competitive pressure is {avg_pressure:.0f}/100 ({pressure_trend}). "
        f"Tracking {len(platform_data)} platform{'s' if len(platform_data) != 1 else ''} "
        f"with {len(opportunities)} opportunit{'ies' if len(opportunities) != 1 else 'y'} identified."
    )

    return CompetitorIntelResponse(
        summary=summary,
        competitive_pressure=round(avg_pressure, 1),
        pressure_trend=pressure_trend,
        platform_competition=platform_competition,
        opportunities=opportunities,
        insights=insights,
        total_your_spend=round(total_spend, 2),
        platforms_tracked=len(platform_data),
        opportunities_count=len(opportunities),
    )
