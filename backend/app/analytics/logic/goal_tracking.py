# =============================================================================
# Goal Tracking & Pacing — Feature #11
# =============================================================================
"""
Goal Tracking & Pacing — provides real-time progress tracking toward
revenue, spend, ROAS, and conversion targets with pacing status,
EOM projections, and daily-needed calculations.

Architecture:
1. Calculates MTD actuals from campaign data
2. Computes pacing percentage vs expected pace
3. Projects end-of-month outcomes using run-rate
4. Generates gap analysis with daily needed amounts
5. Assesses pacing health across all goals

Builds on: Pacing Service (pacing_service.py, forecasting.py)
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone, date
from pydantic import BaseModel, Field
import calendar


# ── Models ───────────────────────────────────────────────────────────────────

class GoalProgress(BaseModel):
    """Progress tracking for a single goal/target."""
    goal_id: str
    metric: str  # spend, revenue, roas, conversions, cpa
    label: str
    target_value: float
    current_value: float
    progress_pct: float  # 0-100+
    pacing_pct: float  # 0-100+ (vs expected pace)
    pacing_status: Literal["ahead", "on_track", "behind", "at_risk", "critical"]
    projected_value: float  # EOM projection
    projected_pct: float  # projected % of target
    gap: float  # target - current
    daily_needed: float  # daily amount needed to hit target
    days_remaining: int
    days_elapsed: int
    trend: Literal["improving", "stable", "declining"]
    formatted_current: str
    formatted_target: str
    formatted_projected: str
    is_inverted: bool = False  # True for metrics where lower is better (CPA)


class PacingMilestone(BaseModel):
    """A pacing milestone or checkpoint."""
    label: str  # e.g., "25% mark", "50% mark", "Week 2"
    expected_value: float
    actual_value: float
    status: Literal["hit", "missed", "upcoming"]
    date_label: str


class GoalInsight(BaseModel):
    """An AI insight about goal performance."""
    title: str
    description: str
    severity: Literal["positive", "info", "warning", "critical"]
    metric: str
    action_label: Optional[str] = None


class GoalTrackingResponse(BaseModel):
    """Full goal tracking & pacing response."""
    summary: str
    period_label: str
    days_elapsed: int
    days_remaining: int
    days_total: int
    progress_pct: float  # overall period progress
    goals: List[GoalProgress] = []
    milestones: List[PacingMilestone] = []
    insights: List[GoalInsight] = []
    overall_pacing: Literal["ahead", "on_track", "behind", "at_risk", "critical"] = "on_track"
    goals_on_track: int = 0
    goals_at_risk: int = 0
    goals_behind: int = 0


# ── Pacing Calculation ────────────────────────────────────────────────────────

PACING_THRESHOLDS = {
    "ahead": (1.10, 999),      # >110% of expected pace
    "on_track": (0.90, 1.10),  # 90-110%
    "behind": (0.75, 0.90),    # 75-90%
    "at_risk": (0.50, 0.75),   # 50-75%
    "critical": (0.0, 0.50),   # <50%
}


def _get_pacing_status(pacing_pct: float, is_inverted: bool = False) -> str:
    """Determine pacing status from pacing percentage."""
    # For inverted metrics (CPA), being over pace is bad
    ratio = pacing_pct / 100 if pacing_pct > 0 else 0
    if is_inverted:
        ratio = 2.0 - ratio if ratio > 0 else 0  # flip for inverted

    if ratio >= 1.10:
        return "ahead"
    elif ratio >= 0.90:
        return "on_track"
    elif ratio >= 0.75:
        return "behind"
    elif ratio >= 0.50:
        return "at_risk"
    return "critical"


def _format_metric(value: float, metric: str) -> str:
    """Format a metric value for display."""
    if metric in ("spend", "revenue", "cpa"):
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:,.0f}"
    elif metric == "roas":
        return f"{value:.2f}x"
    elif metric == "conversions":
        if value >= 1_000:
            return f"{value / 1_000:.1f}K"
        return f"{int(value):,}"
    return f"{value:,.0f}"


def _detect_trend(current_pace: float, days_elapsed: int) -> str:
    """Detect pacing trend (simplified without historical data)."""
    # In production, compare week-over-week pacing
    if current_pace >= 1.05:
        return "improving"
    elif current_pace <= 0.85:
        return "declining"
    return "stable"


def _build_goals(
    campaigns: List[Dict],
    targets: Dict[str, float],
    today: date,
    period_start: date,
    period_end: date,
) -> List[GoalProgress]:
    """Build goal progress for each target metric."""
    days_elapsed = max(1, (today - period_start).days)
    days_remaining = max(0, (period_end - today).days)
    days_total = max(1, (period_end - period_start).days)
    expected_progress = days_elapsed / days_total

    # Aggregate current values
    total_spend = sum(c.get("spend", 0) for c in campaigns)
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    total_conversions = sum(c.get("conversions", 0) for c in campaigns)
    current_roas = total_revenue / total_spend if total_spend > 0 else 0
    current_cpa = total_spend / total_conversions if total_conversions > 0 else 0

    actuals = {
        "spend": total_spend,
        "revenue": total_revenue,
        "conversions": total_conversions,
        "roas": current_roas,
        "cpa": current_cpa,
    }

    labels = {
        "spend": "Ad Spend",
        "revenue": "Revenue",
        "conversions": "Conversions",
        "roas": "ROAS",
        "cpa": "Cost per Acquisition",
    }

    inverted_metrics = {"cpa"}  # lower is better

    goals = []
    for metric, target in targets.items():
        if target <= 0:
            continue

        current = actuals.get(metric, 0)
        is_inverted = metric in inverted_metrics
        progress_pct = (current / target * 100) if target > 0 else 0

        # Expected value at this point in the period
        expected_value = target * expected_progress

        # Pacing: actual vs expected
        if is_inverted:
            # For CPA, being under expected is good
            pacing_pct = (expected_value / current * 100) if current > 0 else 100
        else:
            pacing_pct = (current / expected_value * 100) if expected_value > 0 else 0

        pacing_status = _get_pacing_status(pacing_pct, is_inverted)

        # Project end-of-period value (run-rate projection)
        if days_elapsed > 0:
            daily_rate = current / days_elapsed
            projected = daily_rate * days_total
        else:
            projected = 0

        projected_pct = (projected / target * 100) if target > 0 else 0

        # Gap analysis
        gap = target - current
        daily_needed = gap / days_remaining if days_remaining > 0 else gap

        # Trend
        pace_ratio = pacing_pct / 100
        trend = _detect_trend(pace_ratio, days_elapsed)

        goals.append(GoalProgress(
            goal_id=f"goal_{metric}",
            metric=metric,
            label=labels.get(metric, metric.title()),
            target_value=round(target, 2),
            current_value=round(current, 2),
            progress_pct=round(progress_pct, 1),
            pacing_pct=round(pacing_pct, 1),
            pacing_status=pacing_status,
            projected_value=round(projected, 2),
            projected_pct=round(projected_pct, 1),
            gap=round(gap, 2),
            daily_needed=round(daily_needed, 2),
            days_remaining=days_remaining,
            days_elapsed=days_elapsed,
            trend=trend,
            formatted_current=_format_metric(current, metric),
            formatted_target=_format_metric(target, metric),
            formatted_projected=_format_metric(projected, metric),
            is_inverted=is_inverted,
        ))

    return goals


def _build_milestones(
    goals: List[GoalProgress],
    days_elapsed: int,
    days_total: int,
) -> List[PacingMilestone]:
    """Build pacing milestones (25%, 50%, 75%, 100%)."""
    milestones = []
    progress_pct = (days_elapsed / days_total * 100) if days_total > 0 else 0

    # Use the primary goal (revenue if available, else first)
    primary = next((g for g in goals if g.metric == "revenue"), goals[0] if goals else None)
    if not primary:
        return milestones

    for pct, label in [(25, "25% Mark"), (50, "Halfway"), (75, "75% Mark"), (100, "Target")]:
        expected = primary.target_value * (pct / 100)
        milestone_day = int(days_total * pct / 100)

        if progress_pct >= pct:
            status = "hit" if primary.current_value >= expected else "missed"
        else:
            status = "upcoming"

        milestones.append(PacingMilestone(
            label=label,
            expected_value=round(expected, 2),
            actual_value=round(primary.current_value, 2) if status != "upcoming" else 0,
            status=status,
            date_label=f"Day {milestone_day}",
        ))

    return milestones


def _build_insights(goals: List[GoalProgress]) -> List[GoalInsight]:
    """Generate AI insights about goal performance."""
    insights = []

    for g in goals:
        if g.pacing_status == "critical":
            insights.append(GoalInsight(
                title=f"{g.label} critically behind target",
                description=(
                    f"{g.label} is at {g.progress_pct:.0f}% of target with {g.days_remaining} days remaining. "
                    f"Need {g.formatted_current} → {g.formatted_target}. "
                    f"Daily run-rate must increase significantly to recover."
                ),
                severity="critical",
                metric=g.metric,
                action_label="Review strategy immediately",
            ))
        elif g.pacing_status == "at_risk":
            insights.append(GoalInsight(
                title=f"{g.label} at risk of missing target",
                description=(
                    f"{g.label} is pacing at {g.pacing_pct:.0f}% of expected. "
                    f"Need ~{_format_metric(g.daily_needed, g.metric)}/day to close the gap."
                ),
                severity="warning",
                metric=g.metric,
                action_label="Increase daily output",
            ))
        elif g.pacing_status == "ahead":
            insights.append(GoalInsight(
                title=f"{g.label} ahead of schedule",
                description=(
                    f"{g.label} is at {g.progress_pct:.0f}% of target, "
                    f"projected to reach {g.formatted_projected} ({g.projected_pct:.0f}% of target). "
                    f"Consider raising the target or reallocating excess."
                ),
                severity="positive",
                metric=g.metric,
            ))

    # Cross-goal insights
    behind_count = sum(1 for g in goals if g.pacing_status in ("behind", "at_risk", "critical"))
    if behind_count >= 2:
        insights.append(GoalInsight(
            title="Multiple goals behind — review overall strategy",
            description=f"{behind_count} out of {len(goals)} goals are behind pace. A portfolio-level strategy review may be needed.",
            severity="warning",
            metric="portfolio",
            action_label="Review portfolio strategy",
        ))

    return insights[:6]


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_goal_tracking(
    campaigns: List[Dict],
    targets: Optional[Dict[str, float]] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> GoalTrackingResponse:
    """
    Main entry point: calculates goal progress, pacing status, projections,
    and generates insights for all tracked metrics.

    Args:
        campaigns: List of campaign dicts with spend, revenue, conversions
        targets: Dict of metric → target value (e.g., {"revenue": 50000, "roas": 3.0})
        period_start: Start of tracking period (default: 1st of current month)
        period_end: End of tracking period (default: last day of current month)

    Returns:
        GoalTrackingResponse with goals, milestones, and insights
    """
    today = date.today()

    # Default period: current month
    if period_start is None:
        period_start = today.replace(day=1)
    if period_end is None:
        last_day = calendar.monthrange(today.year, today.month)[1]
        period_end = today.replace(day=last_day)

    days_elapsed = max(1, (today - period_start).days)
    days_remaining = max(0, (period_end - today).days)
    days_total = max(1, (period_end - period_start).days)
    progress_pct = round(days_elapsed / days_total * 100, 1)

    period_label = f"{period_start.strftime('%b %d')} – {period_end.strftime('%b %d, %Y')}"

    if not campaigns:
        return GoalTrackingResponse(
            summary="No campaign data available for goal tracking.",
            period_label=period_label,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            days_total=days_total,
            progress_pct=progress_pct,
        )

    # Default targets if none provided
    if not targets:
        total_spend = sum(c.get("spend", 0) for c in campaigns)
        total_revenue = sum(c.get("revenue", 0) for c in campaigns)
        total_conversions = sum(c.get("conversions", 0) for c in campaigns)

        # Set reasonable targets based on current run-rate + 20% growth
        daily_rate_spend = total_spend / days_elapsed if days_elapsed > 0 else 0
        daily_rate_revenue = total_revenue / days_elapsed if days_elapsed > 0 else 0
        daily_rate_conv = total_conversions / days_elapsed if days_elapsed > 0 else 0

        targets = {
            "revenue": round(daily_rate_revenue * days_total * 1.2, -2),  # 20% above run-rate
            "spend": round(daily_rate_spend * days_total, -2),
            "conversions": max(10, int(daily_rate_conv * days_total * 1.15)),
            "roas": round(total_revenue / total_spend * 1.1, 2) if total_spend > 0 else 3.0,
        }

    # Build goals
    goals = _build_goals(campaigns, targets, today, period_start, period_end)

    # Build milestones
    milestones = _build_milestones(goals, days_elapsed, days_total)

    # Generate insights
    insights = _build_insights(goals)

    # Overall pacing
    pacing_scores = [g.pacing_pct for g in goals if not g.is_inverted]
    avg_pacing = sum(pacing_scores) / len(pacing_scores) if pacing_scores else 100
    overall_pacing = _get_pacing_status(avg_pacing)

    goals_on_track = sum(1 for g in goals if g.pacing_status in ("ahead", "on_track"))
    goals_at_risk = sum(1 for g in goals if g.pacing_status in ("at_risk",))
    goals_behind = sum(1 for g in goals if g.pacing_status in ("behind", "critical"))

    # Summary
    summary = _build_summary(goals, overall_pacing, days_remaining, days_elapsed, days_total)

    return GoalTrackingResponse(
        summary=summary,
        period_label=period_label,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        days_total=days_total,
        progress_pct=progress_pct,
        goals=goals,
        milestones=milestones,
        insights=insights,
        overall_pacing=overall_pacing,
        goals_on_track=goals_on_track,
        goals_at_risk=goals_at_risk,
        goals_behind=goals_behind,
    )


def _build_summary(
    goals: List[GoalProgress],
    overall: str,
    days_remaining: int,
    days_elapsed: int,
    days_total: int,
) -> str:
    """Build executive summary."""
    parts = []

    status_labels = {
        "ahead": "ahead of schedule",
        "on_track": "on track",
        "behind": "slightly behind",
        "at_risk": "at risk",
        "critical": "critically behind",
    }
    parts.append(f"Day {days_elapsed} of {days_total} — overall pacing is {status_labels.get(overall, overall)}.")

    on_track = sum(1 for g in goals if g.pacing_status in ("ahead", "on_track"))
    total = len(goals)
    if total > 0:
        parts.append(f"{on_track}/{total} goals on track.")

    # Highlight biggest concern
    worst = min(goals, key=lambda g: g.pacing_pct) if goals else None
    if worst and worst.pacing_status in ("at_risk", "critical"):
        parts.append(
            f"{worst.label} needs attention — {worst.formatted_current} of {worst.formatted_target} target."
        )

    if days_remaining > 0:
        parts.append(f"{days_remaining} days remaining.")

    return " ".join(parts)
