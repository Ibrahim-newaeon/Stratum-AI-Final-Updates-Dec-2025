# =============================================================================
# Feature #13 — Customer LTV Forecasting
# =============================================================================
"""
Forecasts customer lifetime value by cohort and segment.

Analyses:
- Cohort-based LTV calculation (monthly acquisition cohorts)
- Segment forecasting (by platform/channel)
- LTV distribution buckets
- Revenue projection at 3/6/12 month horizons
- Risk-level assessment per segment
- Actionable insights
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class CohortLTV(BaseModel):
    """LTV data for a single acquisition cohort."""

    cohort_id: str = ""
    cohort_label: str = ""  # "Jan 2026", "Feb 2026"
    size: int = 0  # number of customers
    avg_ltv: float = 0.0
    projected_ltv_3m: float = 0.0
    projected_ltv_6m: float = 0.0
    projected_ltv_12m: float = 0.0
    confidence: float = 0.0  # 0-100
    retention_rate: float = 0.0  # 0-100
    avg_order_value: float = 0.0
    purchase_frequency: float = 0.0  # orders per month
    total_revenue: float = 0.0
    months_active: int = 0


class SegmentForecast(BaseModel):
    """LTV forecast for a customer segment."""

    segment: str = ""
    segment_label: str = ""
    customer_count: int = 0
    current_avg_ltv: float = 0.0
    projected_12m_ltv: float = 0.0
    growth_rate: float = 0.0  # percentage
    risk_level: str = "medium"  # low / medium / high / critical
    revenue_contribution_pct: float = 0.0
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    cac: float = 0.0  # customer acquisition cost
    ltv_to_cac_ratio: float = 0.0


class LTVDistributionBucket(BaseModel):
    """Distribution bucket for LTV values."""

    bucket_label: str = ""  # "$0-50", "$50-100", etc.
    bucket_min: float = 0.0
    bucket_max: float = 0.0
    count: int = 0
    pct: float = 0.0
    revenue_pct: float = 0.0
    avg_ltv: float = 0.0


class LTVInsight(BaseModel):
    """AI-generated insight about LTV patterns."""

    title: str = ""
    description: str = ""
    severity: str = "info"  # positive / info / warning / critical
    metric: str = ""
    action_label: str = ""


class LTVForecastResponse(BaseModel):
    """Full LTV forecasting dashboard response."""

    summary: str = ""
    overall_avg_ltv: float = 0.0
    projected_avg_ltv_12m: float = 0.0
    total_customer_value: float = 0.0
    projected_total_12m: float = 0.0
    total_customers: int = 0
    avg_ltv_to_cac: float = 0.0
    ltv_health: str = "unknown"  # excellent / good / needs_attention / poor
    cohorts: list[CohortLTV] = Field(default_factory=list)
    segments: list[SegmentForecast] = Field(default_factory=list)
    distribution: list[LTVDistributionBucket] = Field(default_factory=list)
    insights: list[LTVInsight] = Field(default_factory=list)
    high_value_pct: float = 0.0  # % customers in top 20% LTV
    at_risk_revenue_pct: float = 0.0  # % revenue from at-risk segments


# ── Constants ────────────────────────────────────────────────────────────────

LTV_HEALTH_THRESHOLDS = {
    "excellent": 5.0,  # LTV:CAC >= 5x
    "good": 3.0,       # LTV:CAC >= 3x
    "needs_attention": 1.5,  # LTV:CAC >= 1.5x
}

RISK_THRESHOLDS = {
    "low": 3.0,       # LTV:CAC >= 3
    "medium": 2.0,    # LTV:CAC >= 2
    "high": 1.0,      # LTV:CAC >= 1
}

DISTRIBUTION_BUCKETS = [
    (0, 50, "$0–$50"),
    (50, 100, "$50–$100"),
    (100, 250, "$100–$250"),
    (250, 500, "$250–$500"),
    (500, 1000, "$500–$1K"),
    (1000, 5000, "$1K–$5K"),
    (5000, float("inf"), "$5K+"),
]

# Growth multipliers for LTV projection
PROJECTION_MULTIPLIERS = {
    3: 1.15,   # 3-month: +15% from current
    6: 1.35,   # 6-month: +35%
    12: 1.65,  # 12-month: +65%
}


# ── Helper functions ─────────────────────────────────────────────────────────


def _ltv_health(ltv_to_cac: float) -> str:
    if ltv_to_cac >= LTV_HEALTH_THRESHOLDS["excellent"]:
        return "excellent"
    if ltv_to_cac >= LTV_HEALTH_THRESHOLDS["good"]:
        return "good"
    if ltv_to_cac >= LTV_HEALTH_THRESHOLDS["needs_attention"]:
        return "needs_attention"
    return "poor"


def _risk_level(ltv_to_cac: float) -> str:
    if ltv_to_cac >= RISK_THRESHOLDS["low"]:
        return "low"
    if ltv_to_cac >= RISK_THRESHOLDS["medium"]:
        return "medium"
    if ltv_to_cac >= RISK_THRESHOLDS["high"]:
        return "high"
    return "critical"


def _format_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def _build_cohorts(platform_data: dict[str, dict], total_customers: int) -> list[CohortLTV]:
    """Build monthly cohorts from platform data (simulated from campaign metrics)."""
    cohorts: list[CohortLTV] = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Distribute customers across recent months (weighted toward recent)
    total_rev = sum(d["revenue"] for d in platform_data.values())
    total_conv = sum(d["conversions"] for d in platform_data.values())

    if total_conv == 0:
        return cohorts

    avg_ltv = total_rev / total_conv if total_conv > 0 else 0
    # Create 6 monthly cohorts with declining size
    weights = [0.25, 0.22, 0.18, 0.15, 0.12, 0.08]

    for i, weight in enumerate(weights):
        month_idx = (3 - i) % 12  # start from recent month
        month_label = f"{months[month_idx]} 2026"
        cohort_size = max(int(total_conv * weight), 1)
        cohort_rev = total_rev * weight
        cohort_ltv = cohort_rev / cohort_size if cohort_size > 0 else 0

        # Older cohorts have higher LTV (more purchase cycles)
        maturity_mult = 1.0 + (i * 0.12)
        cohort_ltv *= maturity_mult

        # Retention decays for older cohorts
        retention = max(95 - (i * 8), 40)

        aov = cohort_ltv / max(1 + i * 0.3, 1)
        freq = cohort_ltv / max(aov, 1) if aov > 0 else 0

        cohorts.append(
            CohortLTV(
                cohort_id=f"cohort_{6 - i}",
                cohort_label=month_label,
                size=cohort_size,
                avg_ltv=round(cohort_ltv, 2),
                projected_ltv_3m=round(cohort_ltv * PROJECTION_MULTIPLIERS[3], 2),
                projected_ltv_6m=round(cohort_ltv * PROJECTION_MULTIPLIERS[6], 2),
                projected_ltv_12m=round(cohort_ltv * PROJECTION_MULTIPLIERS[12], 2),
                confidence=round(min(cohort_size * 0.5, 95), 1),
                retention_rate=round(retention, 1),
                avg_order_value=round(aov, 2),
                purchase_frequency=round(freq, 2),
                total_revenue=round(cohort_rev * maturity_mult, 2),
                months_active=i + 1,
            )
        )

    return cohorts


def _build_segments(platform_data: dict[str, dict], total_revenue: float) -> list[SegmentForecast]:
    """Build segment forecasts from platform-level data."""
    segments: list[SegmentForecast] = []

    for plat, data in sorted(platform_data.items(), key=lambda x: x[1]["revenue"], reverse=True):
        if data["conversions"] == 0:
            continue

        avg_ltv = data["revenue"] / data["conversions"]
        cac = data["spend"] / data["conversions"] if data["conversions"] > 0 else 0
        ltv_cac = avg_ltv / cac if cac > 0 else 0
        rev_pct = (data["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        projected_12m = avg_ltv * PROJECTION_MULTIPLIERS[12]

        # Growth rate based on LTV:CAC ratio
        if ltv_cac >= 5:
            growth = 25.0
        elif ltv_cac >= 3:
            growth = 15.0
        elif ltv_cac >= 2:
            growth = 5.0
        else:
            growth = -5.0

        segments.append(
            SegmentForecast(
                segment=plat,
                segment_label=plat.replace("_", " ").title(),
                customer_count=data["conversions"],
                current_avg_ltv=round(avg_ltv, 2),
                projected_12m_ltv=round(projected_12m, 2),
                growth_rate=growth,
                risk_level=_risk_level(ltv_cac),
                revenue_contribution_pct=round(rev_pct, 1),
                total_revenue=round(data["revenue"], 2),
                avg_order_value=round(avg_ltv, 2),
                cac=round(cac, 2),
                ltv_to_cac_ratio=round(ltv_cac, 2),
            )
        )

    return segments


def _build_distribution(
    segments: list[SegmentForecast],
    total_customers: int,
    total_revenue: float,
) -> list[LTVDistributionBucket]:
    """Build LTV distribution buckets."""
    buckets: list[LTVDistributionBucket] = []

    for bmin, bmax, label in DISTRIBUTION_BUCKETS:
        matching = [s for s in segments if bmin <= s.current_avg_ltv < bmax]
        count = sum(s.customer_count for s in matching)
        rev = sum(s.total_revenue for s in matching)
        avg = sum(s.current_avg_ltv * s.customer_count for s in matching) / max(count, 1)

        buckets.append(
            LTVDistributionBucket(
                bucket_label=label,
                bucket_min=bmin,
                bucket_max=bmax if bmax != float("inf") else 999999,
                count=count,
                pct=round((count / max(total_customers, 1)) * 100, 1),
                revenue_pct=round((rev / max(total_revenue, 1)) * 100, 1),
                avg_ltv=round(avg, 2),
            )
        )

    return [b for b in buckets if b.count > 0]


def _build_insights(
    segments: list[SegmentForecast],
    overall_ltv: float,
    ltv_cac: float,
    total_customers: int,
) -> list[LTVInsight]:
    """Generate AI insights about LTV patterns."""
    insights: list[LTVInsight] = []

    # LTV:CAC health
    if ltv_cac >= 5:
        insights.append(
            LTVInsight(
                title="Excellent LTV:CAC ratio",
                description=f"Your {ltv_cac:.1f}x LTV:CAC ratio indicates highly efficient customer acquisition. Consider scaling spend.",
                severity="positive",
                metric="ltv_cac",
                action_label="Scale Budget",
            )
        )
    elif ltv_cac < 2:
        insights.append(
            LTVInsight(
                title="LTV:CAC ratio needs improvement",
                description=f"At {ltv_cac:.1f}x, acquisition costs are high relative to customer value. Focus on retention and reducing CAC.",
                severity="warning" if ltv_cac >= 1 else "critical",
                metric="ltv_cac",
                action_label="Optimize CAC",
            )
        )

    # Top segment
    if segments:
        top = max(segments, key=lambda s: s.ltv_to_cac_ratio)
        insights.append(
            LTVInsight(
                title=f"{top.segment_label} is your highest-value channel",
                description=f"With {top.ltv_to_cac_ratio:.1f}x LTV:CAC and {_format_currency(top.current_avg_ltv)} avg LTV, this segment delivers the best unit economics.",
                severity="positive",
                metric="top_segment",
                action_label="Increase Investment",
            )
        )

    # At-risk segments
    at_risk = [s for s in segments if s.risk_level in ("high", "critical")]
    if at_risk:
        names = ", ".join(s.segment_label for s in at_risk[:3])
        insights.append(
            LTVInsight(
                title=f"{len(at_risk)} segment{'s' if len(at_risk) > 1 else ''} at risk",
                description=f"{names} {'have' if len(at_risk) > 1 else 'has'} low LTV:CAC ratios. Consider reducing spend or improving conversion quality.",
                severity="warning",
                metric="at_risk",
                action_label="Review Segments",
            )
        )

    # Growth opportunity
    growth_segs = [s for s in segments if s.growth_rate >= 15]
    if growth_segs:
        insights.append(
            LTVInsight(
                title=f"{len(growth_segs)} high-growth segment{'s' if len(growth_segs) > 1 else ''}",
                description=f"Segments with strong unit economics projected to grow {growth_segs[0].growth_rate:.0f}%+ over 12 months.",
                severity="info",
                metric="growth",
                action_label="View Projections",
            )
        )

    # Customer concentration
    if segments and total_customers > 0:
        top_seg = max(segments, key=lambda s: s.revenue_contribution_pct)
        if top_seg.revenue_contribution_pct > 60:
            insights.append(
                LTVInsight(
                    title="Revenue concentration risk",
                    description=f"{top_seg.segment_label} contributes {top_seg.revenue_contribution_pct:.0f}% of revenue. Diversifying channels reduces risk.",
                    severity="warning",
                    metric="concentration",
                    action_label="Diversify Channels",
                )
            )

    return insights


# ── Main entry point ─────────────────────────────────────────────────────────


def build_ltv_forecast(
    campaigns: list[dict],
    profiles: Optional[list[dict]] = None,
) -> LTVForecastResponse:
    """
    Build LTV forecasting dashboard from campaign and profile data.

    Args:
        campaigns: List of campaign dicts with keys:
            platform, spend, revenue, conversions
        profiles: Optional CDP profiles (for future use)
    """
    if not campaigns:
        return LTVForecastResponse(
            summary="No campaign data available for LTV forecasting.",
            ltv_health="poor",
        )

    # ── Aggregate by platform ────────────────────────────────────────
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {"spend": 0.0, "revenue": 0.0, "conversions": 0}
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))

    total_revenue = sum(d["revenue"] for d in platform_data.values())
    total_conversions = sum(d["conversions"] for d in platform_data.values())
    total_spend = sum(d["spend"] for d in platform_data.values())

    if total_conversions == 0:
        return LTVForecastResponse(
            summary="No conversions tracked yet. LTV forecasting requires conversion data.",
            ltv_health="poor",
        )

    overall_ltv = total_revenue / total_conversions
    overall_cac = total_spend / total_conversions if total_conversions > 0 else 0
    ltv_cac = overall_ltv / overall_cac if overall_cac > 0 else 0
    projected_12m = overall_ltv * PROJECTION_MULTIPLIERS[12]
    projected_total = projected_12m * total_conversions

    # ── Build components ─────────────────────────────────────────────
    cohorts = _build_cohorts(platform_data, total_conversions)
    segments = _build_segments(platform_data, total_revenue)
    distribution = _build_distribution(segments, total_conversions, total_revenue)
    insights = _build_insights(segments, overall_ltv, ltv_cac, total_conversions)

    health = _ltv_health(ltv_cac)

    # High-value percentage (top 20% threshold)
    sorted_segs = sorted(segments, key=lambda s: s.current_avg_ltv, reverse=True)
    top_20_count = max(int(total_conversions * 0.2), 1)
    accumulated = 0
    high_value_rev = 0.0
    for seg in sorted_segs:
        take = min(seg.customer_count, top_20_count - accumulated)
        high_value_rev += (take / max(seg.customer_count, 1)) * seg.total_revenue
        accumulated += take
        if accumulated >= top_20_count:
            break
    high_value_pct = (high_value_rev / max(total_revenue, 1)) * 100

    # At-risk revenue
    at_risk_rev = sum(s.total_revenue for s in segments if s.risk_level in ("high", "critical"))
    at_risk_pct = (at_risk_rev / max(total_revenue, 1)) * 100

    # ── Summary ──────────────────────────────────────────────────────
    summary = (
        f"Average customer LTV is {_format_currency(overall_ltv)} with a "
        f"{ltv_cac:.1f}x LTV:CAC ratio ({health.replace('_', ' ')}). "
        f"Projected 12-month LTV is {_format_currency(projected_12m)} across "
        f"{total_conversions:,} customers. "
    )
    if at_risk_pct > 20:
        summary += f"{at_risk_pct:.0f}% of revenue is from at-risk segments."
    elif health in ("excellent", "good"):
        summary += "Unit economics are healthy across segments."

    return LTVForecastResponse(
        summary=summary,
        overall_avg_ltv=round(overall_ltv, 2),
        projected_avg_ltv_12m=round(projected_12m, 2),
        total_customer_value=round(total_revenue, 2),
        projected_total_12m=round(projected_total, 2),
        total_customers=total_conversions,
        avg_ltv_to_cac=round(ltv_cac, 2),
        ltv_health=health,
        cohorts=cohorts,
        segments=segments,
        distribution=distribution,
        insights=insights,
        high_value_pct=round(high_value_pct, 1),
        at_risk_revenue_pct=round(at_risk_pct, 1),
    )
