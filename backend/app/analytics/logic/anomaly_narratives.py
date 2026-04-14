# =============================================================================
# Smart Anomaly Narratives
# =============================================================================
"""
Smart Anomaly Narratives — Feature #2.

Transforms raw z-score anomalies into contextual, human-readable stories
with likely causes and recommended actions. Uses template-based narrative
generation with cross-metric correlation analysis.
"""

from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field

from app.analytics.logic.types import AnomalyResult, AlertSeverity


class AnomalyNarrative(BaseModel):
    """A human-readable narrative for a detected anomaly."""
    metric: str
    title: str
    summary: str
    likely_causes: List[str]
    recommended_actions: List[str]
    severity: str  # critical, high, medium, low
    direction: str  # up, down
    change_percent: float
    current_value: float
    baseline_value: float
    zscore: float
    category: str  # spend, revenue, efficiency, quality


class CorrelationInsight(BaseModel):
    """Cross-metric correlation insight."""
    title: str
    description: str
    severity: str
    related_metrics: List[str]
    pattern: str  # e.g. "spend_up_roas_down", "quality_degradation"


class AnomalyNarrativesResponse(BaseModel):
    """Full response for the anomaly narratives endpoint."""
    executive_summary: str
    total_anomalies: int = 0
    critical_count: int = 0
    high_count: int = 0
    narratives: List[AnomalyNarrative] = []
    correlations: List[CorrelationInsight] = []
    portfolio_risk: str = "low"  # low, moderate, elevated, high


# ── Metric metadata for narrative templates ──────────────────────────────────

METRIC_CONFIG: Dict[str, Dict] = {
    "spend": {
        "label": "Ad Spend",
        "format": "currency",
        "category": "spend",
        "up_title": "Spend Surge Detected",
        "down_title": "Spend Drop Detected",
        "up_causes": [
            "Campaign budget caps were raised or removed",
            "New campaigns or ad sets were activated",
            "Auction competition increased, raising CPMs",
            "Automated bidding strategy is scaling aggressively",
        ],
        "down_causes": [
            "Campaign budgets were exhausted early",
            "Ad accounts hit spending limits",
            "Campaigns were paused or audience sizes narrowed",
            "Platform delivery issues or ad rejections",
        ],
        "up_actions": [
            "Review budget allocation across campaigns to ensure spend aligns with targets",
            "Check if automated bidding is overspending on low-ROAS segments",
            "Set daily budget caps if running uncapped",
        ],
        "down_actions": [
            "Check campaign statuses for paused or rejected ads",
            "Review account-level spending limits",
            "Verify payment method and billing status",
            "Expand audiences if delivery is limited",
        ],
    },
    "revenue": {
        "label": "Revenue",
        "format": "currency",
        "category": "revenue",
        "up_title": "Revenue Spike Detected",
        "down_title": "Revenue Drop Detected",
        "up_causes": [
            "High-performing campaigns are converting exceptionally well",
            "Seasonal demand or promotional event driving sales",
            "New audience segments are delivering strong returns",
            "Attribution window captured delayed conversions",
        ],
        "down_causes": [
            "Conversion tracking may be broken or delayed",
            "Landing page or checkout issues reducing conversions",
            "Audience fatigue reducing engagement quality",
            "Competitive pressure shifted demand",
        ],
        "up_actions": [
            "Identify top-converting campaigns and consider scaling budget",
            "Document what's working for future campaign templates",
            "Monitor whether the spike is sustainable or a one-time event",
        ],
        "down_actions": [
            "Verify pixel/CAPI event firing on purchase events",
            "Check landing page load speed and conversion funnel",
            "Review recent audience or creative changes",
            "Cross-reference with GA4 data for attribution accuracy",
        ],
    },
    "roas": {
        "label": "ROAS",
        "format": "ratio",
        "category": "efficiency",
        "up_title": "ROAS Efficiency Improved",
        "down_title": "ROAS Efficiency Declining",
        "up_causes": [
            "Revenue increased while spend held steady",
            "Better audience targeting improving conversion quality",
            "Creative refresh driving higher engagement",
            "Platform algorithm optimization kicking in",
        ],
        "down_causes": [
            "Spend increased without proportional revenue growth",
            "Audience saturation or creative fatigue reducing conversions",
            "Competitive pressure raising acquisition costs",
            "Tracking issues understating actual conversions",
        ],
        "up_actions": [
            "Consider scaling budget on high-ROAS campaigns by 15-20%",
            "Analyze which audiences and creatives are driving the improvement",
            "Set these campaigns as benchmarks for underperformers",
        ],
        "down_actions": [
            "Pause or reduce budget on campaigns with ROAS below target",
            "Refresh creatives on campaigns showing fatigue signals",
            "Check signal health — EMQ issues can cause ROAS to appear lower",
            "Review audience overlap across campaigns",
        ],
    },
    "cpa": {
        "label": "Cost per Acquisition",
        "format": "currency",
        "category": "efficiency",
        "up_title": "Acquisition Costs Rising",
        "down_title": "Acquisition Costs Improving",
        "up_causes": [
            "Increased auction competition raising bid prices",
            "Audience saturation requiring broader (costlier) targeting",
            "Creative fatigue reducing click-through and conversion rates",
            "Landing page changes impacting conversion rate",
        ],
        "down_causes": [
            "Improved targeting is finding cheaper conversions",
            "Creative refresh driving better engagement",
            "Platform learning phase completed, optimizing delivery",
            "Seasonal dip in competition lowering CPMs",
        ],
        "up_actions": [
            "Review campaigns where CPA exceeds 2x your target",
            "Test new creatives to combat fatigue",
            "Narrow targeting to higher-intent audiences",
            "Evaluate if landing page changes impacted conversion rate",
        ],
        "down_actions": [
            "Capitalize on lower CPAs by scaling budget on these campaigns",
            "Document the audience/creative combo that's working",
            "Consider expanding to similar lookalike audiences",
        ],
    },
    "conversions": {
        "label": "Conversions",
        "format": "number",
        "category": "revenue",
        "up_title": "Conversion Volume Surge",
        "down_title": "Conversion Volume Drop",
        "up_causes": [
            "Campaign scaling is driving more qualified traffic",
            "Promotional offer or seasonal demand spike",
            "New campaign or audience segment performing well",
            "Improved landing page boosting conversion rate",
        ],
        "down_causes": [
            "Pixel or CAPI tracking may be missing events",
            "Budget reductions limiting impression volume",
            "Audience fatigue reducing engagement quality",
            "Funnel bottleneck (e.g., checkout errors, page speed)",
        ],
        "up_actions": [
            "Verify conversion tracking accuracy with GA4 cross-reference",
            "Scale budgets on top-converting campaigns",
            "Monitor CPA to ensure volume growth is profitable",
        ],
        "down_actions": [
            "Check event tracking — test a conversion and verify it fires",
            "Review campaign delivery status for any paused or limited ads",
            "Analyze funnel drop-off points",
            "Check if attribution window settings changed",
        ],
    },
    "event_loss_pct": {
        "label": "Event Loss Rate",
        "format": "percent",
        "category": "quality",
        "up_title": "Signal Quality Degrading",
        "down_title": "Signal Quality Improving",
        "up_causes": [
            "Browser privacy changes blocking client-side events",
            "Server-side (CAPI) integration experiencing errors",
            "Event deduplication misconfigured",
            "Platform API rate limiting dropping events",
        ],
        "down_causes": [
            "CAPI integration is recovering and catching missed events",
            "Recent fix to event tracking is taking effect",
            "Deduplication configuration was corrected",
        ],
        "up_actions": [
            "Check CAPI error logs for failed event deliveries",
            "Verify pixel is firing correctly on key pages",
            "Review event deduplication settings",
            "Contact platform support if API errors persist",
        ],
        "down_actions": [
            "Good news — signal quality is recovering",
            "Continue monitoring to confirm stability",
            "If recently fixed, document the resolution for future reference",
        ],
    },
    "emq_score": {
        "label": "Event Match Quality",
        "format": "score",
        "category": "quality",
        "up_title": "EMQ Score Improved",
        "down_title": "EMQ Score Declining",
        "up_causes": [
            "Better customer data enrichment improving match rates",
            "CAPI sending more complete event parameters",
            "Improved email/phone hash matching",
        ],
        "down_causes": [
            "Customer data missing key identifiers (email, phone)",
            "CAPI parameters incomplete or incorrectly formatted",
            "Privacy changes reducing available match signals",
            "New audience segments have lower data quality",
        ],
        "up_actions": [
            "Continue enriching event payloads with available PII (hashed)",
            "Monitor to confirm the improvement is sustained",
        ],
        "down_actions": [
            "Audit CAPI event payloads for missing parameters",
            "Ensure email and phone are hashed and included when available",
            "Review consent management — users may be opting out of tracking",
            "Check EMQ score per platform in Signal Health panel",
        ],
    },
}


def _format_value(value: float, fmt: str) -> str:
    """Format a metric value for display."""
    if fmt == "currency":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:,.1f}K"
        return f"${value:,.2f}"
    elif fmt == "ratio":
        return f"{value:.2f}x"
    elif fmt == "percent":
        return f"{value:.1f}%"
    elif fmt == "score":
        return f"{value:.0f}/100"
    else:
        if abs(value) >= 1_000:
            return f"{value / 1_000:,.1f}K"
        return f"{value:,.0f}"


def _pct_change(current: float, baseline: float) -> float:
    """Calculate percentage change."""
    if baseline == 0:
        return 0.0
    return ((current - baseline) / abs(baseline)) * 100


def generate_narrative(anomaly: AnomalyResult) -> AnomalyNarrative:
    """
    Generate a contextual narrative for a single anomaly.

    Transforms raw z-score data into a human-readable story with
    likely causes and recommended actions.
    """
    config = METRIC_CONFIG.get(anomaly.metric, {})
    label = config.get("label", anomaly.metric.replace("_", " ").title())
    fmt = config.get("format", "number")
    category = config.get("category", "other")
    is_up = anomaly.direction == "high"

    change_pct = abs(_pct_change(anomaly.current_value, anomaly.baseline_mean))
    current_fmt = _format_value(anomaly.current_value, fmt)
    baseline_fmt = _format_value(anomaly.baseline_mean, fmt)

    # Select title
    if is_up:
        title = config.get("up_title", f"{label} Increased Significantly")
    else:
        title = config.get("down_title", f"{label} Decreased Significantly")

    # Build summary narrative
    direction_word = "increased" if is_up else "decreased"
    summary = (
        f"{label} {direction_word} by {change_pct:.1f}% — "
        f"currently at {current_fmt} versus your 14-day average of {baseline_fmt}. "
    )

    # Add severity context
    if anomaly.severity in (AlertSeverity.CRITICAL, "critical"):
        summary += "This is a critical deviation that requires immediate attention."
    elif anomaly.severity in (AlertSeverity.HIGH, "high"):
        summary += "This is a significant deviation worth investigating today."
    else:
        summary += "This is a moderate deviation to keep an eye on."

    # Select causes and actions
    if is_up:
        causes = config.get("up_causes", [f"{label} is higher than the 14-day baseline"])
        actions = config.get("up_actions", [f"Investigate what caused the {label.lower()} increase"])
    else:
        causes = config.get("down_causes", [f"{label} is lower than the 14-day baseline"])
        actions = config.get("down_actions", [f"Investigate what caused the {label.lower()} decrease"])

    # Limit to top 3 most relevant
    causes = causes[:3]
    actions = actions[:3]

    return AnomalyNarrative(
        metric=anomaly.metric,
        title=title,
        summary=summary,
        likely_causes=causes,
        recommended_actions=actions,
        severity=anomaly.severity.value if hasattr(anomaly.severity, "value") else str(anomaly.severity),
        direction="up" if is_up else "down",
        change_percent=round(change_pct, 1),
        current_value=anomaly.current_value,
        baseline_value=anomaly.baseline_mean,
        zscore=anomaly.zscore,
        category=category,
    )


def detect_correlations(anomalies: List[AnomalyResult]) -> List[CorrelationInsight]:
    """
    Detect cross-metric correlations among anomalies.

    Identifies patterns like:
    - Spend up + ROAS down = scaling inefficiency
    - Revenue down + event_loss up = tracking issue
    - CPA up + conversions down = funnel problem
    """
    insights: List[CorrelationInsight] = []

    anomaly_map: Dict[str, AnomalyResult] = {a.metric: a for a in anomalies if a.is_anomaly}

    # Pattern: Spend up + ROAS down → scaling inefficiency
    if ("spend" in anomaly_map and "roas" in anomaly_map
            and anomaly_map["spend"].direction == "high"
            and anomaly_map["roas"].direction == "low"):
        insights.append(CorrelationInsight(
            title="Scaling Inefficiency Detected",
            description=(
                "Spend is increasing but ROAS is declining — you may be scaling into "
                "less efficient audiences or hitting diminishing returns. Consider "
                "tightening targeting or capping budgets on underperformers."
            ),
            severity="high",
            related_metrics=["spend", "roas"],
            pattern="spend_up_roas_down",
        ))

    # Pattern: Revenue down + event_loss up → tracking issue
    if ("revenue" in anomaly_map and "event_loss_pct" in anomaly_map
            and anomaly_map["revenue"].direction == "low"
            and anomaly_map["event_loss_pct"].direction == "high"):
        insights.append(CorrelationInsight(
            title="Possible Tracking Issue",
            description=(
                "Revenue is declining while event loss is increasing — this suggests "
                "conversion events may not be reaching the platform. Check your "
                "pixel/CAPI implementation before making campaign changes."
            ),
            severity="critical",
            related_metrics=["revenue", "event_loss_pct"],
            pattern="tracking_degradation",
        ))

    # Pattern: CPA up + conversions down → funnel problem
    if ("cpa" in anomaly_map and "conversions" in anomaly_map
            and anomaly_map["cpa"].direction == "high"
            and anomaly_map["conversions"].direction == "low"):
        insights.append(CorrelationInsight(
            title="Conversion Funnel Under Pressure",
            description=(
                "Acquisition costs are rising while conversion volume is dropping. "
                "This typically indicates a funnel issue — check landing page performance, "
                "checkout flow, and creative relevance."
            ),
            severity="high",
            related_metrics=["cpa", "conversions"],
            pattern="funnel_pressure",
        ))

    # Pattern: EMQ down + revenue down → data quality impact
    if ("emq_score" in anomaly_map and "revenue" in anomaly_map
            and anomaly_map["emq_score"].direction == "low"
            and anomaly_map["revenue"].direction == "low"):
        insights.append(CorrelationInsight(
            title="Data Quality Impacting Performance",
            description=(
                "EMQ score and revenue are both declining. Lower event match quality "
                "reduces the platform's ability to optimize delivery. Fix signal "
                "health before adjusting campaign strategies."
            ),
            severity="critical",
            related_metrics=["emq_score", "revenue"],
            pattern="quality_degradation",
        ))

    # Pattern: Spend down + conversions down → delivery issue
    if ("spend" in anomaly_map and "conversions" in anomaly_map
            and anomaly_map["spend"].direction == "low"
            and anomaly_map["conversions"].direction == "low"):
        insights.append(CorrelationInsight(
            title="Delivery Volume Constrained",
            description=(
                "Both spend and conversions dropped together — campaigns may be "
                "under-delivering. Check for paused ads, budget exhaustion, or "
                "audience targeting that's too narrow."
            ),
            severity="medium",
            related_metrics=["spend", "conversions"],
            pattern="delivery_constrained",
        ))

    return insights


def generate_executive_summary(
    narratives: List[AnomalyNarrative],
    correlations: List[CorrelationInsight],
) -> str:
    """Generate an executive summary for all anomalies."""
    if not narratives:
        return (
            "No significant anomalies detected in the last 24 hours. "
            "All metrics are within normal operating ranges."
        )

    critical = [n for n in narratives if n.severity == "critical"]
    high = [n for n in narratives if n.severity == "high"]
    total = len(narratives)

    parts = []

    if critical:
        metrics = ", ".join(n.metric.replace("_", " ") for n in critical)
        parts.append(f"{len(critical)} critical anomaly detected in {metrics}")

    if high:
        metrics = ", ".join(n.metric.replace("_", " ") for n in high)
        parts.append(f"{len(high)} high-severity change in {metrics}")

    remaining = total - len(critical) - len(high)
    if remaining > 0:
        parts.append(f"{remaining} moderate deviation{'s' if remaining > 1 else ''}")

    summary = ". ".join(parts) + ". "

    if correlations:
        top = correlations[0]
        summary += f"Key insight: {top.title.lower()} — {top.description.split('.')[0].strip()}."

    return summary


def assess_portfolio_risk(
    narratives: List[AnomalyNarrative],
    correlations: List[CorrelationInsight],
) -> str:
    """Assess overall portfolio risk level."""
    critical_count = sum(1 for n in narratives if n.severity == "critical")
    high_count = sum(1 for n in narratives if n.severity == "high")
    has_critical_correlation = any(c.severity == "critical" for c in correlations)

    if critical_count >= 2 or has_critical_correlation:
        return "high"
    elif critical_count >= 1 or high_count >= 2:
        return "elevated"
    elif high_count >= 1 or len(narratives) >= 3:
        return "moderate"
    else:
        return "low"


def build_anomaly_narratives(
    anomalies: List[AnomalyResult],
) -> AnomalyNarrativesResponse:
    """
    Main entry point: builds the full anomaly narratives response.

    Takes raw AnomalyResult list from detect_anomalies() and produces
    human-readable narratives with correlations and executive summary.
    """
    # Filter to actual anomalies only
    significant = [a for a in anomalies if a.is_anomaly]

    # Generate narratives for each
    narratives = [generate_narrative(a) for a in significant]

    # Detect cross-metric correlations
    correlations = detect_correlations(significant)

    # Build executive summary
    executive_summary = generate_executive_summary(narratives, correlations)

    # Assess risk
    portfolio_risk = assess_portfolio_risk(narratives, correlations)

    return AnomalyNarrativesResponse(
        executive_summary=executive_summary,
        total_anomalies=len(narratives),
        critical_count=sum(1 for n in narratives if n.severity == "critical"),
        high_count=sum(1 for n in narratives if n.severity == "high"),
        narratives=narratives,
        correlations=correlations,
        portfolio_risk=portfolio_risk,
    )
