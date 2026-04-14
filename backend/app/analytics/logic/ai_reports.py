# =============================================================================
# AI-Generated Reports — Feature #6
# =============================================================================
"""
AI-Generated Reports — produces executive-quality performance reports
with narrative insights, trend analysis, and actionable recommendations.

Architecture:
1. Aggregates campaign metrics across platforms
2. Calculates period-over-period changes
3. Identifies top/bottom performers with narratives
4. Generates trend insights and risk callouts
5. Produces platform-level breakdown with commentary
6. Returns structured report for dashboard + PDF export

Builds on: reporting infrastructure, predictive_budget, anomaly_narratives
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class ReportKPI(BaseModel):
    """A single KPI metric for the report."""
    label: str
    value: float
    formatted: str
    change_pct: float = 0.0
    trend: Literal["up", "down", "flat"] = "flat"
    is_good: bool = True


class PlatformBreakdown(BaseModel):
    """Performance breakdown for a single platform."""
    platform: str
    spend: float
    revenue: float
    roas: float
    conversions: int
    campaigns: int
    spend_share_pct: float  # % of total spend
    change_summary: str  # narrative about platform


class CampaignHighlight(BaseModel):
    """A highlighted campaign (top performer or underperformer)."""
    campaign_id: int
    campaign_name: str
    platform: str
    metric_label: str  # what makes it notable
    metric_value: str
    roas: float
    spend: float
    insight: str


class ReportInsight(BaseModel):
    """A narrative insight within the report."""
    category: Literal["trend", "opportunity", "risk", "milestone"]
    title: str
    narrative: str
    severity: Literal["info", "positive", "warning", "critical"] = "info"


class ReportSection(BaseModel):
    """A section of the generated report."""
    title: str
    section_type: Literal[
        "executive_summary", "kpi_grid", "platform_breakdown",
        "top_performers", "underperformers", "insights", "recommendations"
    ]
    content: str = ""
    kpis: List[ReportKPI] = []
    platforms: List[PlatformBreakdown] = []
    highlights: List[CampaignHighlight] = []
    insights: List[ReportInsight] = []


class AIReportResponse(BaseModel):
    """Full AI-generated report response."""
    report_title: str
    generated_at: str
    period_label: str
    executive_summary: str
    health_grade: Literal["A", "B", "C", "D", "F"]
    health_label: str
    sections: List[ReportSection] = []
    total_spend: float = 0.0
    total_revenue: float = 0.0
    overall_roas: float = 0.0
    total_conversions: int = 0
    total_campaigns: int = 0
    platforms_count: int = 0
    top_recommendations: List[str] = []


# ── Analysis Helpers ─────────────────────────────────────────────────────────

def _format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.2f}"


def _format_number(value: int) -> str:
    """Format number with commas."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:,.1f}K"
    return f"{value:,}"


def _calculate_grade(roas: float, spend: float, conversions: int) -> tuple:
    """Calculate portfolio health grade."""
    if roas >= 4.0 and conversions >= 100:
        return "A", "Excellent"
    elif roas >= 3.0 and conversions >= 50:
        return "B", "Strong"
    elif roas >= 2.0 and conversions >= 20:
        return "C", "Average"
    elif roas >= 1.0:
        return "D", "Below Average"
    else:
        return "F", "Critical"


def _build_executive_summary(
    total_spend: float,
    total_revenue: float,
    roas: float,
    total_conversions: int,
    n_campaigns: int,
    n_platforms: int,
    prev_spend: float,
    prev_revenue: float,
    grade: str,
    grade_label: str,
) -> str:
    """Build the executive narrative summary."""
    spend_change = ((total_spend - prev_spend) / prev_spend * 100) if prev_spend > 0 else 0
    rev_change = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    parts = []
    parts.append(
        f"Across {n_campaigns} active campaigns on {n_platforms} platform{'s' if n_platforms > 1 else ''}, "
        f"your portfolio achieved a {roas:.2f}x ROAS generating {_format_currency(total_revenue)} "
        f"in revenue from {_format_currency(total_spend)} in spend."
    )

    if spend_change != 0:
        direction = "increased" if spend_change > 0 else "decreased"
        parts.append(
            f"Spend {direction} {abs(spend_change):.1f}% period-over-period"
            f"{f' while revenue grew {rev_change:.1f}%' if rev_change > 0 else ''}."
        )

    if total_conversions > 0:
        cpa = total_spend / total_conversions
        parts.append(
            f"Total conversions: {_format_number(total_conversions)} "
            f"at an average CPA of {_format_currency(cpa)}."
        )

    parts.append(f"Overall portfolio grade: {grade} ({grade_label}).")

    return " ".join(parts)


def _analyze_platforms(campaigns: List[Dict], total_spend: float) -> List[PlatformBreakdown]:
    """Aggregate and analyze per-platform performance."""
    platform_data: Dict[str, Dict] = {}

    for c in campaigns:
        plat = c.get("platform", "Unknown")
        if plat not in platform_data:
            platform_data[plat] = {
                "spend": 0, "revenue": 0, "conversions": 0, "campaigns": 0
            }
        platform_data[plat]["spend"] += c.get("spend", 0)
        platform_data[plat]["revenue"] += c.get("revenue", 0)
        platform_data[plat]["conversions"] += c.get("conversions", 0)
        platform_data[plat]["campaigns"] += 1

    breakdowns = []
    for plat, data in sorted(platform_data.items(), key=lambda x: -x[1]["spend"]):
        spend = data["spend"]
        revenue = data["revenue"]
        roas = revenue / spend if spend > 0 else 0
        share = (spend / total_spend * 100) if total_spend > 0 else 0
        convs = data["conversions"]

        # Narrative
        if roas >= 4.0:
            summary = f"Exceptional performance — {roas:.2f}x ROAS is well above target."
        elif roas >= 3.0:
            summary = f"Strong returns at {roas:.2f}x ROAS. Consider scaling top campaigns."
        elif roas >= 2.0:
            summary = f"Moderate performance at {roas:.2f}x ROAS. Review underperformers."
        elif roas >= 1.0:
            summary = f"Marginal returns at {roas:.2f}x ROAS — approaching breakeven."
        else:
            summary = f"Below breakeven at {roas:.2f}x ROAS. Immediate attention required."

        breakdowns.append(PlatformBreakdown(
            platform=plat,
            spend=round(spend, 2),
            revenue=round(revenue, 2),
            roas=round(roas, 2),
            conversions=convs,
            campaigns=data["campaigns"],
            spend_share_pct=round(share, 1),
            change_summary=summary,
        ))

    return breakdowns


def _find_highlights(
    campaigns: List[Dict],
) -> tuple:
    """Find top performers and underperformers."""
    scored = []
    for c in campaigns:
        spend = c.get("spend", 0)
        revenue = c.get("revenue", 0)
        conversions = c.get("conversions", 0)
        if spend <= 0:
            continue
        roas = revenue / spend
        cpa = spend / conversions if conversions > 0 else 0
        scored.append({**c, "_roas": roas, "_cpa": cpa})

    # Sort by ROAS descending
    scored.sort(key=lambda x: -x["_roas"])

    top = []
    for c in scored[:3]:
        roas = c["_roas"]
        spend = c.get("spend", 0)
        if roas >= 2.0:
            insight = (
                f"Generating {_format_currency(c.get('revenue', 0))} revenue at "
                f"{roas:.2f}x ROAS — strong candidate for budget scaling."
            )
        else:
            insight = (
                f"Best relative performer at {roas:.2f}x ROAS with "
                f"{_format_number(c.get('conversions', 0))} conversions."
            )
        top.append(CampaignHighlight(
            campaign_id=c.get("id", 0),
            campaign_name=c.get("name", "Unknown"),
            platform=c.get("platform", "Unknown"),
            metric_label="ROAS",
            metric_value=f"{roas:.2f}x",
            roas=round(roas, 2),
            spend=round(spend, 2),
            insight=insight,
        ))

    bottom = []
    for c in scored[-3:]:
        roas = c["_roas"]
        spend = c.get("spend", 0)
        if roas < 1.0:
            insight = (
                f"Spending {_format_currency(spend)} with only {roas:.2f}x ROAS — "
                f"below breakeven. Consider pausing or reducing budget."
            )
        else:
            insight = (
                f"Underperforming at {roas:.2f}x ROAS. "
                f"Review targeting and creative for optimization."
            )
        bottom.append(CampaignHighlight(
            campaign_id=c.get("id", 0),
            campaign_name=c.get("name", "Unknown"),
            platform=c.get("platform", "Unknown"),
            metric_label="ROAS",
            metric_value=f"{roas:.2f}x",
            roas=round(roas, 2),
            spend=round(spend, 2),
            insight=insight,
        ))

    return top, bottom


def _generate_insights(
    campaigns: List[Dict],
    total_spend: float,
    total_revenue: float,
    roas: float,
    platforms: List[PlatformBreakdown],
) -> List[ReportInsight]:
    """Generate narrative insights about the portfolio."""
    insights = []

    # Concentration risk
    if platforms and platforms[0].spend_share_pct > 70:
        insights.append(ReportInsight(
            category="risk",
            title="High Platform Concentration",
            narrative=(
                f"{platforms[0].platform} accounts for {platforms[0].spend_share_pct:.0f}% "
                f"of total spend. Consider diversifying to reduce platform dependency risk."
            ),
            severity="warning",
        ))

    # High ROAS opportunity
    high_roas = [c for c in campaigns if c.get("spend", 0) > 0 and (c.get("revenue", 0) / c["spend"]) >= 4.0]
    if high_roas:
        insights.append(ReportInsight(
            category="opportunity",
            title=f"{len(high_roas)} High-ROAS Campaigns",
            narrative=(
                f"{len(high_roas)} campaign{'s' if len(high_roas) > 1 else ''} achieving 4x+ ROAS. "
                f"These are prime candidates for budget scaling to maximize returns."
            ),
            severity="positive",
        ))

    # Low conversion campaigns
    low_conv = [c for c in campaigns if c.get("spend", 0) > 100 and c.get("conversions", 0) < 5]
    if low_conv:
        insights.append(ReportInsight(
            category="risk",
            title=f"{len(low_conv)} Campaigns with Low Conversions",
            narrative=(
                f"{len(low_conv)} campaign{'s' if len(low_conv) > 1 else ''} spending over $100 "
                f"with fewer than 5 conversions. Review creative, targeting, and landing pages."
            ),
            severity="warning",
        ))

    # ROAS milestone
    if roas >= 4.0:
        insights.append(ReportInsight(
            category="milestone",
            title="Portfolio ROAS Exceeds 4x",
            narrative=(
                f"Overall portfolio ROAS of {roas:.2f}x significantly exceeds the 3x target. "
                f"Strong indication that current strategy is effective."
            ),
            severity="positive",
        ))
    elif roas < 1.5:
        insights.append(ReportInsight(
            category="risk",
            title="Portfolio ROAS Below Target",
            narrative=(
                f"Overall ROAS of {roas:.2f}x is below the 3x target. "
                f"Priority: reduce spend on underperformers and reallocate to top campaigns."
            ),
            severity="critical",
        ))

    # Revenue trend
    if total_revenue > 0:
        efficiency = total_revenue / total_spend if total_spend > 0 else 0
        if efficiency > 3:
            insights.append(ReportInsight(
                category="trend",
                title="Strong Revenue Efficiency",
                narrative=(
                    f"Generating {_format_currency(efficiency)} revenue per dollar spent. "
                    f"Portfolio is in a healthy growth position."
                ),
                severity="positive",
            ))

    # Multi-platform insight
    if len(platforms) >= 3:
        best_plat = max(platforms, key=lambda p: p.roas)
        insights.append(ReportInsight(
            category="trend",
            title="Cross-Platform Performance",
            narrative=(
                f"Active on {len(platforms)} platforms. {best_plat.platform} leads with "
                f"{best_plat.roas:.2f}x ROAS across {best_plat.campaigns} campaigns."
            ),
            severity="info",
        ))

    return insights


def _generate_recommendations(
    roas: float,
    platforms: List[PlatformBreakdown],
    top_campaigns: List[CampaignHighlight],
    bottom_campaigns: List[CampaignHighlight],
    insights: List[ReportInsight],
) -> List[str]:
    """Generate top-level actionable recommendations."""
    recs = []

    # Scale top performers
    if top_campaigns and top_campaigns[0].roas >= 3.0:
        recs.append(
            f"Scale budget for \"{top_campaigns[0].campaign_name}\" — "
            f"currently achieving {top_campaigns[0].roas:.2f}x ROAS."
        )

    # Cut underperformers
    for c in bottom_campaigns:
        if c.roas < 1.0:
            recs.append(
                f"Reduce or pause \"{c.campaign_name}\" — "
                f"{c.roas:.2f}x ROAS is below breakeven."
            )
            break  # only first one

    # Platform diversification
    if platforms and platforms[0].spend_share_pct > 70:
        second_best = platforms[1] if len(platforms) > 1 else None
        if second_best:
            recs.append(
                f"Diversify spend: shift 10-15% from {platforms[0].platform} "
                f"to {second_best.platform} ({second_best.roas:.2f}x ROAS)."
            )

    # Overall ROAS
    if roas < 2.0:
        recs.append(
            "Review targeting and creative across all campaigns — "
            "portfolio ROAS is below the healthy 3x threshold."
        )

    # Conversion optimization
    risk_insights = [i for i in insights if i.category == "risk"]
    if any("Low Conversions" in i.title for i in risk_insights):
        recs.append(
            "Audit landing pages and conversion funnels for campaigns "
            "with high spend but low conversion volume."
        )

    if not recs:
        recs.append(
            "Portfolio is performing well. Continue monitoring and "
            "consider incremental budget increases on top performers."
        )

    return recs[:5]  # Max 5 recommendations


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_ai_report(
    campaigns: List[Dict],
    prev_campaigns: Optional[List[Dict]] = None,
    period_label: str = "Last 30 Days",
) -> AIReportResponse:
    """
    Main entry point: generates an AI-powered performance report
    with narrative insights and actionable recommendations.

    Args:
        campaigns: List of campaign dicts with id, name, platform,
                   spend, revenue, conversions
        prev_campaigns: Optional previous period campaigns for comparison
        period_label: Display label for the report period

    Returns:
        AIReportResponse with sections, insights, and recommendations
    """
    if not campaigns:
        return AIReportResponse(
            report_title="AI Performance Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_label=period_label,
            executive_summary="No campaign data available for this period.",
            health_grade="F",
            health_label="No Data",
        )

    # Aggregate current period
    total_spend = sum(c.get("spend", 0) for c in campaigns)
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    total_conversions = sum(c.get("conversions", 0) for c in campaigns)
    overall_roas = total_revenue / total_spend if total_spend > 0 else 0
    overall_cpa = total_spend / total_conversions if total_conversions > 0 else 0

    # Aggregate previous period
    prev_spend = sum(c.get("spend", 0) for c in (prev_campaigns or []))
    prev_revenue = sum(c.get("revenue", 0) for c in (prev_campaigns or []))
    prev_conversions = sum(c.get("conversions", 0) for c in (prev_campaigns or []))
    prev_roas = prev_revenue / prev_spend if prev_spend > 0 else 0

    # Grade
    grade, grade_label = _calculate_grade(overall_roas, total_spend, total_conversions)

    # Platform breakdown
    platforms = _analyze_platforms(campaigns, total_spend)
    unique_platforms = len(platforms)

    # Campaign highlights
    top_campaigns, bottom_campaigns = _find_highlights(campaigns)

    # Insights
    insights = _generate_insights(
        campaigns, total_spend, total_revenue, overall_roas, platforms
    )

    # Recommendations
    recommendations = _generate_recommendations(
        overall_roas, platforms, top_campaigns, bottom_campaigns, insights
    )

    # Executive summary
    executive_summary = _build_executive_summary(
        total_spend, total_revenue, overall_roas, total_conversions,
        len(campaigns), unique_platforms,
        prev_spend, prev_revenue, grade, grade_label,
    )

    # Change calculations
    spend_change = ((total_spend - prev_spend) / prev_spend * 100) if prev_spend > 0 else 0
    rev_change = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    conv_change = ((total_conversions - prev_conversions) / prev_conversions * 100) if prev_conversions > 0 else 0
    roas_change = ((overall_roas - prev_roas) / prev_roas * 100) if prev_roas > 0 else 0

    # Build sections
    sections = []

    # 1. Executive Summary section
    sections.append(ReportSection(
        title="Executive Summary",
        section_type="executive_summary",
        content=executive_summary,
    ))

    # 2. KPI Grid
    sections.append(ReportSection(
        title="Key Performance Indicators",
        section_type="kpi_grid",
        kpis=[
            ReportKPI(
                label="Total Spend",
                value=total_spend,
                formatted=_format_currency(total_spend),
                change_pct=round(spend_change, 1),
                trend="up" if spend_change > 0 else ("down" if spend_change < 0 else "flat"),
                is_good=spend_change <= 10,
            ),
            ReportKPI(
                label="Revenue",
                value=total_revenue,
                formatted=_format_currency(total_revenue),
                change_pct=round(rev_change, 1),
                trend="up" if rev_change > 0 else ("down" if rev_change < 0 else "flat"),
                is_good=rev_change >= 0,
            ),
            ReportKPI(
                label="ROAS",
                value=overall_roas,
                formatted=f"{overall_roas:.2f}x",
                change_pct=round(roas_change, 1),
                trend="up" if roas_change > 0 else ("down" if roas_change < 0 else "flat"),
                is_good=overall_roas >= 3.0,
            ),
            ReportKPI(
                label="Conversions",
                value=total_conversions,
                formatted=_format_number(total_conversions),
                change_pct=round(conv_change, 1),
                trend="up" if conv_change > 0 else ("down" if conv_change < 0 else "flat"),
                is_good=conv_change >= 0,
            ),
            ReportKPI(
                label="CPA",
                value=overall_cpa,
                formatted=_format_currency(overall_cpa),
                change_pct=0,
                trend="flat",
                is_good=overall_cpa < 50,
            ),
            ReportKPI(
                label="Campaigns",
                value=len(campaigns),
                formatted=str(len(campaigns)),
                change_pct=0,
                trend="flat",
                is_good=True,
            ),
        ],
    ))

    # 3. Platform Breakdown
    sections.append(ReportSection(
        title="Platform Performance",
        section_type="platform_breakdown",
        platforms=platforms,
    ))

    # 4. Top Performers
    if top_campaigns:
        sections.append(ReportSection(
            title="Top Performers",
            section_type="top_performers",
            highlights=top_campaigns,
        ))

    # 5. Underperformers
    if bottom_campaigns:
        sections.append(ReportSection(
            title="Needs Attention",
            section_type="underperformers",
            highlights=bottom_campaigns,
        ))

    # 6. Insights
    if insights:
        sections.append(ReportSection(
            title="AI Insights",
            section_type="insights",
            insights=insights,
        ))

    # 7. Recommendations
    sections.append(ReportSection(
        title="Recommendations",
        section_type="recommendations",
        content="\n".join(f"• {r}" for r in recommendations),
    ))

    return AIReportResponse(
        report_title="AI Performance Report",
        generated_at=datetime.now(timezone.utc).isoformat(),
        period_label=period_label,
        executive_summary=executive_summary,
        health_grade=grade,
        health_label=grade_label,
        sections=sections,
        total_spend=round(total_spend, 2),
        total_revenue=round(total_revenue, 2),
        overall_roas=round(overall_roas, 2),
        total_conversions=total_conversions,
        total_campaigns=len(campaigns),
        platforms_count=unique_platforms,
        top_recommendations=recommendations,
    )
