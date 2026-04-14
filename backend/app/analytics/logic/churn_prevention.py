# =============================================================================
# Churn Prevention Automations — Feature #7
# =============================================================================
"""
Churn Prevention — detects at-risk campaigns and clients using engagement,
performance, and activity signals. Generates risk scores and automated
intervention recommendations.

Architecture:
1. Scores each campaign across 4 risk dimensions (performance, engagement,
   spend trend, data freshness)
2. Aggregates into client-level churn risk
3. Generates intervention playbooks per risk profile
4. Tracks overall portfolio retention health

Builds on: scoring.py, signal_health.py, Tenant.churn_risk_score field
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class ChurnSignal(BaseModel):
    """Individual churn risk signal."""
    signal: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    weight: float  # contribution to risk score 0.0-1.0


class Intervention(BaseModel):
    """Recommended intervention for an at-risk entity."""
    action: str
    title: str
    description: str
    priority: Literal["immediate", "soon", "monitor"]
    category: Literal["outreach", "optimize", "budget", "creative", "technical"]
    auto_eligible: bool = False


class AtRiskCampaign(BaseModel):
    """A campaign identified as at-risk for churn."""
    campaign_id: int
    campaign_name: str
    platform: str
    risk_score: float  # 0-100
    risk_level: Literal["low", "medium", "high", "critical"]
    signals: List[ChurnSignal] = []
    interventions: List[Intervention] = []
    days_declining: int = 0
    current_roas: float = 0.0
    spend: float = 0.0


class RetentionMetric(BaseModel):
    """A retention-related metric."""
    label: str
    value: str
    trend: Literal["improving", "stable", "declining"]
    is_healthy: bool


class ChurnPreventionResponse(BaseModel):
    """Full churn prevention analysis response."""
    summary: str
    portfolio_risk_level: Literal["healthy", "watch", "warning", "critical"]
    portfolio_risk_score: float  # 0-100
    total_campaigns_analyzed: int
    at_risk_count: int
    critical_count: int
    healthy_count: int
    retention_rate_pct: float
    metrics: List[RetentionMetric] = []
    at_risk_campaigns: List[AtRiskCampaign] = []
    top_interventions: List[Intervention] = []
    risk_distribution: Dict[str, int] = {}  # low/medium/high/critical counts


# ── Risk Scoring ─────────────────────────────────────────────────────────────

def _score_performance_risk(
    roas: float,
    conversions: int,
    spend: float,
) -> tuple:
    """Score performance-based churn risk."""
    signals = []
    risk = 0.0

    if roas < 0.5 and spend > 100:
        risk += 35
        signals.append(ChurnSignal(
            signal="critical_roas",
            description=f"ROAS of {roas:.2f}x is critically low — well below breakeven.",
            severity="critical",
            weight=0.35,
        ))
    elif roas < 1.0 and spend > 50:
        risk += 25
        signals.append(ChurnSignal(
            signal="low_roas",
            description=f"ROAS of {roas:.2f}x is below breakeven.",
            severity="high",
            weight=0.25,
        ))
    elif roas < 2.0:
        risk += 10
        signals.append(ChurnSignal(
            signal="underperforming_roas",
            description=f"ROAS of {roas:.2f}x is below the 3x target.",
            severity="medium",
            weight=0.10,
        ))

    if conversions == 0 and spend > 100:
        risk += 20
        signals.append(ChurnSignal(
            signal="zero_conversions",
            description="No conversions despite active spend.",
            severity="critical",
            weight=0.20,
        ))
    elif conversions < 5 and spend > 100:
        risk += 10
        signals.append(ChurnSignal(
            signal="low_conversions",
            description=f"Only {conversions} conversions — insufficient for optimization.",
            severity="medium",
            weight=0.10,
        ))

    return min(risk, 50), signals


def _score_spend_risk(
    spend: float,
    avg_spend: float,
) -> tuple:
    """Score spend-trend churn risk."""
    signals = []
    risk = 0.0

    if avg_spend > 0:
        ratio = spend / avg_spend
        if ratio < 0.3:
            risk += 25
            signals.append(ChurnSignal(
                signal="spend_collapse",
                description=f"Spend is {ratio*100:.0f}% of portfolio average — severe decline.",
                severity="critical",
                weight=0.25,
            ))
        elif ratio < 0.6:
            risk += 15
            signals.append(ChurnSignal(
                signal="spend_declining",
                description=f"Spend is {ratio*100:.0f}% of portfolio average — declining.",
                severity="high",
                weight=0.15,
            ))

    if spend < 10 and spend > 0:
        risk += 10
        signals.append(ChurnSignal(
            signal="minimal_spend",
            description="Spend is near-zero — campaign may be abandoned.",
            severity="high",
            weight=0.10,
        ))

    return min(risk, 30), signals


def _score_engagement_risk(
    status: str,
    has_recent_sync: bool,
) -> tuple:
    """Score engagement-based churn risk."""
    signals = []
    risk = 0.0

    if status in ("paused", "Paused", "PAUSED"):
        risk += 15
        signals.append(ChurnSignal(
            signal="campaign_paused",
            description="Campaign is paused — may indicate client disengagement.",
            severity="medium",
            weight=0.15,
        ))
    elif status in ("archived", "Archived", "ARCHIVED", "completed", "Completed"):
        risk += 20
        signals.append(ChurnSignal(
            signal="campaign_inactive",
            description="Campaign is no longer active.",
            severity="high",
            weight=0.20,
        ))

    if not has_recent_sync:
        risk += 10
        signals.append(ChurnSignal(
            signal="stale_data",
            description="No recent data sync — potential technical disengagement.",
            severity="medium",
            weight=0.10,
        ))

    return min(risk, 25), signals


def _generate_interventions(
    risk_score: float,
    signals: List[ChurnSignal],
    roas: float,
    conversions: int,
    spend: float,
    platform: str,
) -> List[Intervention]:
    """Generate intervention recommendations based on risk profile."""
    interventions = []
    signal_names = {s.signal for s in signals}

    if risk_score >= 70:
        interventions.append(Intervention(
            action="urgent_review",
            title="Schedule Urgent Client Review",
            description="High churn risk detected. Schedule a call to discuss performance and strategy adjustments.",
            priority="immediate",
            category="outreach",
        ))

    if "critical_roas" in signal_names or "low_roas" in signal_names:
        interventions.append(Intervention(
            action="creative_refresh",
            title="Refresh Creative Assets",
            description=f"Current ROAS of {roas:.2f}x suggests ad fatigue or poor targeting. Test new creative variations.",
            priority="soon",
            category="creative",
        ))
        interventions.append(Intervention(
            action="targeting_audit",
            title="Audit Targeting & Audiences",
            description="Review audience segments, lookalikes, and exclusions for optimization opportunities.",
            priority="soon",
            category="optimize",
        ))

    if "zero_conversions" in signal_names or "low_conversions" in signal_names:
        interventions.append(Intervention(
            action="conversion_audit",
            title="Audit Conversion Tracking",
            description="Verify pixel/CAPI setup, conversion events, and attribution windows.",
            priority="immediate",
            category="technical",
            auto_eligible=True,
        ))

    if "spend_collapse" in signal_names or "spend_declining" in signal_names:
        interventions.append(Intervention(
            action="budget_proposal",
            title="Propose Revised Budget Strategy",
            description="Prepare a performance-backed budget proposal showing projected returns at recommended spend levels.",
            priority="soon",
            category="budget",
        ))

    if "campaign_paused" in signal_names:
        interventions.append(Intervention(
            action="reactivation_plan",
            title="Create Reactivation Plan",
            description="Prepare an optimized reactivation plan with refreshed targeting and creative before resuming.",
            priority="soon",
            category="optimize",
        ))

    if "stale_data" in signal_names:
        interventions.append(Intervention(
            action="resync_platform",
            title=f"Re-sync {platform} Data",
            description="Reconnect and sync latest data to ensure accurate reporting.",
            priority="immediate",
            category="technical",
            auto_eligible=True,
        ))

    if risk_score >= 40 and not any(i.category == "outreach" for i in interventions):
        interventions.append(Intervention(
            action="proactive_checkup",
            title="Send Proactive Performance Update",
            description="Share a performance summary with optimization recommendations to show proactive value.",
            priority="soon",
            category="outreach",
        ))

    return interventions[:5]


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_churn_prevention(
    campaigns: List[Dict],
) -> ChurnPreventionResponse:
    """
    Main entry point: analyzes all campaigns for churn risk signals and
    generates intervention recommendations.

    Args:
        campaigns: List of campaign dicts with id, name, platform, status,
                   spend, revenue, conversions, has_recent_sync

    Returns:
        ChurnPreventionResponse with risk analysis and interventions
    """
    if not campaigns:
        return ChurnPreventionResponse(
            summary="No campaigns available for churn analysis.",
            portfolio_risk_level="healthy",
            portfolio_risk_score=0,
            total_campaigns_analyzed=0,
            at_risk_count=0,
            critical_count=0,
            healthy_count=0,
            retention_rate_pct=100,
        )

    # Portfolio averages
    total_spend = sum(c.get("spend", 0) for c in campaigns)
    n = len(campaigns)
    avg_spend = total_spend / n if n > 0 else 0

    # Analyze each campaign
    at_risk_campaigns: List[AtRiskCampaign] = []

    for campaign in campaigns:
        c_id = campaign.get("id", 0)
        c_name = campaign.get("name", "Unknown")
        c_platform = campaign.get("platform", "Unknown")
        c_status = campaign.get("status", "active")
        c_spend = campaign.get("spend", 0)
        c_revenue = campaign.get("revenue", 0)
        c_conversions = campaign.get("conversions", 0)
        c_has_sync = campaign.get("has_recent_sync", True)

        roas = c_revenue / c_spend if c_spend > 0 else 0

        # Score across dimensions
        perf_risk, perf_signals = _score_performance_risk(roas, c_conversions, c_spend)
        spend_risk, spend_signals = _score_spend_risk(c_spend, avg_spend)
        engage_risk, engage_signals = _score_engagement_risk(c_status, c_has_sync)

        total_risk = min(100, perf_risk + spend_risk + engage_risk)
        all_signals = perf_signals + spend_signals + engage_signals

        # Determine risk level
        if total_risk >= 70:
            risk_level = "critical"
        elif total_risk >= 45:
            risk_level = "high"
        elif total_risk >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate interventions for at-risk campaigns
        interventions = []
        if total_risk >= 25:
            interventions = _generate_interventions(
                risk_score=total_risk,
                signals=all_signals,
                roas=roas,
                conversions=c_conversions,
                spend=c_spend,
                platform=c_platform,
            )

        at_risk_campaigns.append(AtRiskCampaign(
            campaign_id=c_id,
            campaign_name=c_name,
            platform=c_platform,
            risk_score=round(total_risk, 1),
            risk_level=risk_level,
            signals=all_signals,
            interventions=interventions,
            current_roas=round(roas, 2),
            spend=round(c_spend, 2),
        ))

    # Sort by risk score descending
    at_risk_campaigns.sort(key=lambda c: -c.risk_score)

    # Risk distribution
    risk_dist = {
        "critical": sum(1 for c in at_risk_campaigns if c.risk_level == "critical"),
        "high": sum(1 for c in at_risk_campaigns if c.risk_level == "high"),
        "medium": sum(1 for c in at_risk_campaigns if c.risk_level == "medium"),
        "low": sum(1 for c in at_risk_campaigns if c.risk_level == "low"),
    }

    at_risk_count = risk_dist["critical"] + risk_dist["high"] + risk_dist["medium"]
    healthy_count = risk_dist["low"]
    critical_count = risk_dist["critical"]
    retention_rate = (healthy_count / n * 100) if n > 0 else 100

    # Portfolio risk score (weighted average)
    portfolio_risk = sum(c.risk_score for c in at_risk_campaigns) / n if n > 0 else 0

    if portfolio_risk >= 60:
        portfolio_level = "critical"
    elif portfolio_risk >= 40:
        portfolio_level = "warning"
    elif portfolio_risk >= 20:
        portfolio_level = "watch"
    else:
        portfolio_level = "healthy"

    # Top interventions (deduplicated by action, highest priority first)
    priority_order = {"immediate": 0, "soon": 1, "monitor": 2}
    all_interventions = []
    seen_actions = set()
    for campaign in at_risk_campaigns:
        for interv in campaign.interventions:
            if interv.action not in seen_actions:
                seen_actions.add(interv.action)
                all_interventions.append(interv)
    all_interventions.sort(key=lambda i: priority_order.get(i.priority, 2))
    top_interventions = all_interventions[:6]

    # Retention metrics
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    avg_roas = total_revenue / total_spend if total_spend > 0 else 0
    active_count = sum(1 for c in campaigns if c.get("status", "").lower() in ("active", "enabled"))

    metrics = [
        RetentionMetric(
            label="Retention Rate",
            value=f"{retention_rate:.0f}%",
            trend="improving" if retention_rate >= 80 else ("stable" if retention_rate >= 60 else "declining"),
            is_healthy=retention_rate >= 70,
        ),
        RetentionMetric(
            label="At-Risk Campaigns",
            value=str(at_risk_count),
            trend="declining" if at_risk_count > n * 0.3 else ("stable" if at_risk_count > 0 else "improving"),
            is_healthy=at_risk_count <= n * 0.2,
        ),
        RetentionMetric(
            label="Active Campaigns",
            value=f"{active_count}/{n}",
            trend="improving" if active_count >= n * 0.8 else ("stable" if active_count >= n * 0.5 else "declining"),
            is_healthy=active_count >= n * 0.7,
        ),
        RetentionMetric(
            label="Avg ROAS",
            value=f"{avg_roas:.2f}x",
            trend="improving" if avg_roas >= 3.0 else ("stable" if avg_roas >= 2.0 else "declining"),
            is_healthy=avg_roas >= 2.0,
        ),
    ]

    # Build summary
    summary = _build_summary(
        n, at_risk_count, critical_count, healthy_count,
        retention_rate, portfolio_level, top_interventions,
    )

    # Filter to only show campaigns with risk >= medium
    visible_campaigns = [c for c in at_risk_campaigns if c.risk_level != "low"]

    return ChurnPreventionResponse(
        summary=summary,
        portfolio_risk_level=portfolio_level,
        portfolio_risk_score=round(portfolio_risk, 1),
        total_campaigns_analyzed=n,
        at_risk_count=at_risk_count,
        critical_count=critical_count,
        healthy_count=healthy_count,
        retention_rate_pct=round(retention_rate, 1),
        metrics=metrics,
        at_risk_campaigns=visible_campaigns,
        top_interventions=top_interventions,
        risk_distribution=risk_dist,
    )


def _build_summary(
    total: int,
    at_risk: int,
    critical: int,
    healthy: int,
    retention_rate: float,
    portfolio_level: str,
    top_interventions: List[Intervention],
) -> str:
    """Build executive summary for churn prevention."""
    parts = []

    if critical > 0:
        parts.append(
            f"{critical} campaign{'s' if critical > 1 else ''} at critical risk "
            f"requiring immediate attention."
        )

    if at_risk > 0:
        parts.append(
            f"{at_risk} of {total} campaigns showing churn risk signals."
        )
    else:
        parts.append(f"All {total} campaigns are healthy — no churn risks detected.")

    parts.append(f"Portfolio retention rate: {retention_rate:.0f}%.")

    if portfolio_level == "critical":
        parts.append("Urgent: Portfolio risk is critical — prioritize interventions.")
    elif portfolio_level == "warning":
        parts.append("Warning: Elevated churn risk — proactive action recommended.")
    elif portfolio_level == "watch":
        parts.append("Monitoring: Some campaigns need attention but overall health is stable.")

    immediate = sum(1 for i in top_interventions if i.priority == "immediate")
    if immediate > 0:
        parts.append(f"{immediate} immediate intervention{'s' if immediate > 1 else ''} recommended.")

    return " ".join(parts)
