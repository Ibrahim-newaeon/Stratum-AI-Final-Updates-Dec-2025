# =============================================================================
# Feature #14 — Campaign Creative Scoring
# =============================================================================
"""
Scores campaign creatives based on performance signals.

Analyses:
- Per-creative performance scoring (CTR, conversion rate, ROAS, fatigue)
- Creative health grading (A-F)
- Fatigue detection (declining CTR over time)
- Winning vs underperforming creative identification
- Actionable recommendations for creative refresh
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class CreativeScore(BaseModel):
    """Score for a single campaign creative."""

    creative_id: str = ""
    campaign_name: str = ""
    platform: str = ""
    overall_score: float = 0.0  # 0-100
    grade: str = "C"  # A, B, C, D, F
    ctr: float = 0.0
    ctr_score: float = 0.0  # 0-100
    conversion_rate: float = 0.0
    cvr_score: float = 0.0
    roas: float = 0.0
    roas_score: float = 0.0
    cpa: float = 0.0
    cpa_score: float = 0.0
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    fatigue_level: str = "none"  # none / low / medium / high
    fatigue_score: float = 0.0  # 0-100 (higher = more fatigued)
    status: str = "active"  # winner / active / underperforming / fatigued / new
    days_running: int = 0
    recommendation: str = ""


class CreativeInsight(BaseModel):
    """AI-generated insight about creative performance."""

    title: str = ""
    description: str = ""
    severity: str = "info"  # positive / info / warning / critical
    creative_id: str = ""
    action_label: str = ""


class PlatformCreativeSummary(BaseModel):
    """Summary of creative performance per platform."""

    platform: str = ""
    total_creatives: int = 0
    avg_score: float = 0.0
    winners: int = 0
    fatigued: int = 0
    underperforming: int = 0
    top_creative_score: float = 0.0
    total_spend: float = 0.0


class CreativeScoringResponse(BaseModel):
    """Full creative scoring dashboard response."""

    summary: str = ""
    creatives: list[CreativeScore] = Field(default_factory=list)
    platform_summaries: list[PlatformCreativeSummary] = Field(default_factory=list)
    insights: list[CreativeInsight] = Field(default_factory=list)
    total_creatives: int = 0
    avg_score: float = 0.0
    overall_grade: str = "C"
    winners_count: int = 0
    fatigued_count: int = 0
    underperforming_count: int = 0
    refresh_needed_pct: float = 0.0  # % creatives needing refresh


# ── Constants ────────────────────────────────────────────────────────────────

GRADE_THRESHOLDS = {"A": 80, "B": 65, "C": 50, "D": 35}

# Benchmark CTRs by platform (approximate industry averages)
PLATFORM_CTR_BENCHMARKS = {
    "meta": 1.2,
    "google": 3.5,
    "tiktok": 0.8,
    "snapchat": 0.6,
    "linkedin": 0.5,
    "twitter": 0.8,
    "pinterest": 0.5,
    "default": 1.0,
}

FATIGUE_THRESHOLDS = {"high": 70, "medium": 40, "low": 15}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _grade(score: float) -> str:
    for g, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return g
    return "F"


def _fatigue_level(score: float) -> str:
    if score >= FATIGUE_THRESHOLDS["high"]:
        return "high"
    if score >= FATIGUE_THRESHOLDS["medium"]:
        return "medium"
    if score >= FATIGUE_THRESHOLDS["low"]:
        return "low"
    return "none"


def _creative_status(score: float, fatigue: float) -> str:
    if fatigue >= FATIGUE_THRESHOLDS["high"]:
        return "fatigued"
    if score >= 75:
        return "winner"
    if score < 35:
        return "underperforming"
    return "active"


def _score_ctr(ctr: float, platform: str) -> float:
    benchmark = PLATFORM_CTR_BENCHMARKS.get(platform, PLATFORM_CTR_BENCHMARKS["default"])
    ratio = ctr / benchmark if benchmark > 0 else 0
    if ratio >= 2.0:
        return 100
    if ratio >= 1.5:
        return 85
    if ratio >= 1.0:
        return 70
    if ratio >= 0.7:
        return 50
    if ratio >= 0.4:
        return 30
    return max(ratio * 50, 0)


def _score_cvr(cvr: float) -> float:
    # Industry avg ~2-3%
    if cvr >= 8:
        return 100
    if cvr >= 5:
        return 85
    if cvr >= 3:
        return 70
    if cvr >= 1.5:
        return 50
    if cvr >= 0.5:
        return 30
    return max(cvr * 20, 0)


def _score_roas(roas: float) -> float:
    if roas >= 8:
        return 100
    if roas >= 5:
        return 85
    if roas >= 3:
        return 70
    if roas >= 2:
        return 55
    if roas >= 1:
        return 35
    return max(roas * 30, 0)


def _score_cpa(cpa: float, avg_cpa: float) -> float:
    if avg_cpa == 0:
        return 50
    ratio = cpa / avg_cpa
    # Lower CPA is better
    if ratio <= 0.5:
        return 100
    if ratio <= 0.7:
        return 85
    if ratio <= 1.0:
        return 65
    if ratio <= 1.3:
        return 45
    if ratio <= 1.8:
        return 25
    return 10


def _estimate_fatigue(spend: float, impressions: int, days: int) -> float:
    """Estimate creative fatigue based on frequency and run duration."""
    if days == 0 or impressions == 0:
        return 0
    daily_impressions = impressions / days
    # High frequency + long run = fatigue
    duration_factor = min(days / 30, 1.0) * 40  # up to 40 pts for 30+ days
    frequency_factor = min(daily_impressions / 50000, 1.0) * 30  # up to 30 pts for high volume
    spend_factor = min(spend / 10000, 1.0) * 30  # up to 30 pts for high spend
    return min(duration_factor + frequency_factor + spend_factor, 100)


# ── Main entry point ─────────────────────────────────────────────────────────


def build_creative_scoring(
    campaigns: list[dict],
) -> CreativeScoringResponse:
    """
    Build creative scoring dashboard from campaign data.

    Args:
        campaigns: List of campaign dicts with keys:
            name, platform, spend, revenue, conversions, impressions, clicks, days_running
    """
    if not campaigns:
        return CreativeScoringResponse(
            summary="No campaign data available for creative scoring.",
            overall_grade="F",
        )

    # Calculate averages for relative scoring
    total_spend = sum(float(c.get("spend", 0)) for c in campaigns)
    total_conv = sum(int(c.get("conversions", 0)) for c in campaigns)
    avg_cpa = total_spend / total_conv if total_conv > 0 else 0

    creatives: list[CreativeScore] = []

    for i, c in enumerate(campaigns):
        spend = float(c.get("spend", 0))
        revenue = float(c.get("revenue", 0))
        conversions = int(c.get("conversions", 0))
        impressions = int(c.get("impressions", 0))
        clicks = int(c.get("clicks", 0))
        platform = str(c.get("platform", "unknown")).lower()
        name = str(c.get("name", f"Campaign {i + 1}"))
        days = int(c.get("days_running", 14))

        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        roas = revenue / spend if spend > 0 else 0
        cpa = spend / conversions if conversions > 0 else 0

        ctr_s = _score_ctr(ctr, platform)
        cvr_s = _score_cvr(cvr)
        roas_s = _score_roas(roas)
        cpa_s = _score_cpa(cpa, avg_cpa)

        # Weighted overall: CTR 20%, CVR 30%, ROAS 30%, CPA 20%
        overall = ctr_s * 0.20 + cvr_s * 0.30 + roas_s * 0.30 + cpa_s * 0.20

        fatigue = _estimate_fatigue(spend, impressions, days)

        # Fatigue penalty on overall score
        if fatigue >= FATIGUE_THRESHOLDS["high"]:
            overall *= 0.75
        elif fatigue >= FATIGUE_THRESHOLDS["medium"]:
            overall *= 0.90

        status = _creative_status(overall, fatigue)

        # Recommendation
        if status == "winner":
            rec = "Scale budget — this creative is a top performer."
        elif status == "fatigued":
            rec = "Refresh creative — performance declining due to audience fatigue."
        elif status == "underperforming":
            rec = "Pause or replace — this creative is underperforming benchmarks."
        else:
            rec = "Monitor — performance is within acceptable range."

        creatives.append(
            CreativeScore(
                creative_id=f"cr_{i + 1}",
                campaign_name=name,
                platform=platform.replace("_", " ").title(),
                overall_score=round(overall, 1),
                grade=_grade(overall),
                ctr=round(ctr, 2),
                ctr_score=round(ctr_s, 1),
                conversion_rate=round(cvr, 2),
                cvr_score=round(cvr_s, 1),
                roas=round(roas, 2),
                roas_score=round(roas_s, 1),
                cpa=round(cpa, 2),
                cpa_score=round(cpa_s, 1),
                spend=round(spend, 2),
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                revenue=round(revenue, 2),
                fatigue_level=_fatigue_level(fatigue),
                fatigue_score=round(fatigue, 1),
                status=status,
                days_running=days,
                recommendation=rec,
            )
        )

    # Sort by score descending
    creatives.sort(key=lambda x: x.overall_score, reverse=True)

    # Platform summaries
    plat_data: dict[str, list[CreativeScore]] = {}
    for cr in creatives:
        plat_data.setdefault(cr.platform, []).append(cr)

    platform_summaries = []
    for plat, crs in sorted(plat_data.items(), key=lambda x: sum(c.spend for c in x[1]), reverse=True):
        platform_summaries.append(
            PlatformCreativeSummary(
                platform=plat,
                total_creatives=len(crs),
                avg_score=round(sum(c.overall_score for c in crs) / len(crs), 1),
                winners=sum(1 for c in crs if c.status == "winner"),
                fatigued=sum(1 for c in crs if c.status == "fatigued"),
                underperforming=sum(1 for c in crs if c.status == "underperforming"),
                top_creative_score=max(c.overall_score for c in crs),
                total_spend=round(sum(c.spend for c in crs), 2),
            )
        )

    # Aggregates
    total = len(creatives)
    avg_score = sum(c.overall_score for c in creatives) / total if total > 0 else 0
    winners = sum(1 for c in creatives if c.status == "winner")
    fatigued = sum(1 for c in creatives if c.status == "fatigued")
    underperforming = sum(1 for c in creatives if c.status == "underperforming")
    refresh = fatigued + underperforming
    refresh_pct = (refresh / total * 100) if total > 0 else 0

    # Insights
    insights: list[CreativeInsight] = []

    if winners > 0:
        top = creatives[0]
        insights.append(
            CreativeInsight(
                title=f"Top performer: {top.campaign_name}",
                description=f"Score {top.overall_score:.0f}/100 ({top.grade}) with {top.roas:.1f}x ROAS and {top.ctr:.2f}% CTR. Consider increasing budget.",
                severity="positive",
                creative_id=top.creative_id,
                action_label="Scale Budget",
            )
        )

    if fatigued > 0:
        insights.append(
            CreativeInsight(
                title=f"{fatigued} creative{'s' if fatigued > 1 else ''} showing fatigue",
                description="Declining performance indicates audience saturation. Refresh copy, visuals, or targeting.",
                severity="warning",
                action_label="Refresh Creatives",
            )
        )

    if underperforming > 0:
        worst = creatives[-1]
        insights.append(
            CreativeInsight(
                title=f"{underperforming} underperforming creative{'s' if underperforming > 1 else ''}",
                description=f"Lowest: {worst.campaign_name} at {worst.overall_score:.0f}/100. Consider pausing to reallocate budget.",
                severity="critical" if underperforming > total * 0.3 else "warning",
                creative_id=worst.creative_id,
                action_label="Pause & Reallocate",
            )
        )

    if refresh_pct > 50:
        insights.append(
            CreativeInsight(
                title="Majority of creatives need attention",
                description=f"{refresh_pct:.0f}% of creatives are fatigued or underperforming. Schedule a creative sprint.",
                severity="critical",
                action_label="Plan Creative Sprint",
            )
        )
    elif refresh_pct == 0 and total > 0:
        insights.append(
            CreativeInsight(
                title="All creatives performing well",
                description="No immediate refresh needed. Continue monitoring for fatigue signals.",
                severity="positive",
                action_label="Continue Monitoring",
            )
        )

    # Summary
    summary = (
        f"Scoring {total} creative{'s' if total != 1 else ''} — avg score {avg_score:.0f}/100 ({_grade(avg_score)}). "
        f"{winners} winner{'s' if winners != 1 else ''}, "
        f"{fatigued} fatigued, {underperforming} underperforming. "
    )
    if refresh_pct > 30:
        summary += f"{refresh_pct:.0f}% need refresh."
    elif total > 0:
        summary += "Creative portfolio is healthy."

    return CreativeScoringResponse(
        summary=summary,
        creatives=creatives,
        platform_summaries=platform_summaries,
        insights=insights,
        total_creatives=total,
        avg_score=round(avg_score, 1),
        overall_grade=_grade(avg_score),
        winners_count=winners,
        fatigued_count=fatigued,
        underperforming_count=underperforming,
        refresh_needed_pct=round(refresh_pct, 1),
    )
