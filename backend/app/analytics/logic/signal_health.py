# =============================================================================
# EMQ / Signal Health Logic
# =============================================================================
"""
EMQ / Signal Health Logic (degrade + auto-resolve).
From AI_Logic_Formulas_Pseudocode.md Section 6.

Goal: Stop automation when data quality is compromised.

Thresholds:
- critical: api_ok == false
- degraded: emq < 80 or loss > 10%
- risk: emq < 90 or loss > 5%
- healthy: otherwise
"""

from typing import Optional, List
from app.analytics.logic.types import (
    SignalHealthParams,
    SignalHealthResult,
    SignalHealthStatus,
)


def signal_health(
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    api_health: bool = True,
    params: Optional[SignalHealthParams] = None,
) -> SignalHealthResult:
    """
    Determine signal health status.

    Args:
        emq_score: Event Match Quality score (0-100)
        event_loss_pct: Percentage of lost events (0-100)
        api_health: Whether API connections are healthy
        params: Health check thresholds

    Returns:
        SignalHealthResult with status and recommended actions
    """
    if params is None:
        params = SignalHealthParams()

    issues = []
    actions = []

    # Critical: API down
    if not api_health:
        issues.append("API connection failed")
        actions.append("Check platform API credentials and connectivity")
        actions.append("Suspend automation until resolved")

        return SignalHealthResult(
            status=SignalHealthStatus.CRITICAL,
            emq_score=emq_score,
            event_loss_pct=event_loss_pct,
            api_health=api_health,
            issues=issues,
            actions=actions,
        )

    # Check EMQ score
    if emq_score is not None:
        if emq_score < params.emq_risk:
            issues.append(f"EMQ score critically low: {emq_score:.1f} (target: {params.emq_healthy})")
        elif emq_score < params.emq_healthy:
            issues.append(f"EMQ score below target: {emq_score:.1f} (target: {params.emq_healthy})")

    # Check event loss
    if event_loss_pct is not None:
        if event_loss_pct > params.event_loss_risk:
            issues.append(f"High event loss: {event_loss_pct:.1f}% (max: {params.event_loss_risk}%)")
        elif event_loss_pct > params.event_loss_healthy:
            issues.append(f"Event loss above target: {event_loss_pct:.1f}% (target: <{params.event_loss_healthy}%)")

    # Determine status
    emq_ok = emq_score is None or emq_score >= params.emq_risk
    loss_ok = event_loss_pct is None or event_loss_pct <= params.event_loss_risk

    if not emq_ok or not loss_ok:
        status = SignalHealthStatus.DEGRADED
        actions.append("Suspend budget automation")
        actions.append("Run diagnostics playbook")
        actions.append("Check pixel/CAPI implementation")
        actions.append("Notify team via Slack/email")
    elif emq_score is not None and emq_score < params.emq_healthy:
        status = SignalHealthStatus.RISK
        actions.append("Monitor closely - data quality at risk")
        actions.append("Review recent tracking changes")
    elif event_loss_pct is not None and event_loss_pct > params.event_loss_healthy:
        status = SignalHealthStatus.RISK
        actions.append("Investigate event loss source")
        actions.append("Check server-side event delivery")
    else:
        status = SignalHealthStatus.HEALTHY
        if not issues:
            actions.append("All signals healthy - automation can proceed")

    return SignalHealthResult(
        status=status,
        emq_score=emq_score,
        event_loss_pct=event_loss_pct,
        api_health=api_health,
        issues=issues,
        actions=actions,
    )


def auto_resolve(
    health_result: SignalHealthResult,
) -> dict:
    """
    Auto-resolve actions based on signal health.

    Args:
        health_result: Result from signal_health check

    Returns:
        Dict with actions taken and alerts created
    """
    actions_taken = []
    alerts_created = []

    if health_result.status in [SignalHealthStatus.CRITICAL, SignalHealthStatus.DEGRADED]:
        # Suspend automation
        actions_taken.append("suspend_automation")

        # Create alert
        alerts_created.append({
            "type": "emq_degraded",
            "severity": "high" if health_result.status == SignalHealthStatus.DEGRADED else "critical",
            "message": f"Signal health: {health_result.status.value}. Issues: {', '.join(health_result.issues)}",
            "recommended_actions": health_result.actions,
        })

        # Run diagnostics
        actions_taken.append("run_diagnostics_playbook")

        # Notify
        actions_taken.append("notify_slack")
        actions_taken.append("create_ticket")

    elif health_result.status == SignalHealthStatus.RISK:
        # Create warning alert
        alerts_created.append({
            "type": "emq_risk",
            "severity": "medium",
            "message": f"Signal health at risk. Issues: {', '.join(health_result.issues)}",
            "recommended_actions": health_result.actions,
        })

    return {
        "status": health_result.status.value,
        "actions_taken": actions_taken,
        "alerts_created": alerts_created,
        "automation_suspended": "suspend_automation" in actions_taken,
    }


def should_suspend_automation(health_result: SignalHealthResult) -> bool:
    """
    Check if automation should be suspended.

    Args:
        health_result: Signal health check result

    Returns:
        True if automation should be suspended
    """
    return health_result.status in [
        SignalHealthStatus.CRITICAL,
        SignalHealthStatus.DEGRADED,
    ]


def get_health_color(status: SignalHealthStatus) -> str:
    """Get color code for health status visualization."""
    colors = {
        SignalHealthStatus.HEALTHY: "#22C55E",   # Green
        SignalHealthStatus.RISK: "#FACC15",      # Yellow
        SignalHealthStatus.DEGRADED: "#F97316",  # Orange
        SignalHealthStatus.CRITICAL: "#EF4444",  # Red
    }
    return colors.get(status, "#6E7482")
