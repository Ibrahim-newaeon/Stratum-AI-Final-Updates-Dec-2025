# =============================================================================
# Signal Auto-Recovery — Feature #3
# =============================================================================
"""
Signal Auto-Recovery — automatically detects signal health degradation,
diagnoses root causes, and triggers recovery actions.

When EMQ drops, event loss spikes, or API health degrades, this module:
1. Identifies the specific issues
2. Generates targeted recovery actions
3. Can trigger platform re-syncs
4. Tracks recovery progress over time

Builds on: signal_health.py, types.py (SignalHealthStatus)
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.analytics.logic.types import SignalHealthStatus


# ── Models ───────────────────────────────────────────────────────────────────

class SignalIssue(BaseModel):
    """A specific signal health issue detected."""
    id: str
    type: Literal["emq_drop", "event_loss", "api_down", "data_stale", "tracking_gap"]
    severity: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    affected_platforms: List[str] = []
    detected_at: str  # ISO timestamp


class RecoveryAction(BaseModel):
    """A recovery action to address a signal issue."""
    id: str
    issue_id: str
    type: Literal["resync", "diagnostics", "check_capi", "check_pixel", "alert_team", "expand_params"]
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    priority: Literal["urgent", "high", "normal"] = "normal"
    auto_triggered: bool = False
    estimated_minutes: Optional[int] = None


class RecoveryTimeline(BaseModel):
    """A timeline entry for recovery tracking."""
    timestamp: str
    event: str
    type: Literal["detection", "action", "progress", "resolution"]
    details: Optional[str] = None


class SignalRecoveryResponse(BaseModel):
    """Full response for the signal recovery dashboard card."""
    status: Literal["healthy", "recovering", "degraded", "critical"]
    summary: str
    issues: List[SignalIssue] = []
    recovery_actions: List[RecoveryAction] = []
    timeline: List[RecoveryTimeline] = []
    overall_health_score: int = 100
    recovery_progress_pct: int = 100
    has_active_recovery: bool = False
    platforms_affected: List[str] = []
    last_healthy_at: Optional[str] = None
    estimated_recovery_minutes: Optional[int] = None


# ── Issue Detection ──────────────────────────────────────────────────────────

ISSUE_TEMPLATES: Dict[str, Dict] = {
    "emq_drop": {
        "title": "Event Match Quality Degraded",
        "description_template": "EMQ score dropped to {value:.0f}/100 (threshold: {threshold:.0f}). "
                                "This reduces ad platform optimization accuracy and may impact ROAS.",
        "recovery_actions": [
            {
                "type": "check_capi",
                "title": "Verify CAPI Event Parameters",
                "description": "Check that server-side events include email, phone (hashed), and all required parameters. Missing fields reduce match rates.",
                "priority": "urgent",
                "estimated_minutes": 15,
            },
            {
                "type": "expand_params",
                "title": "Enrich Event Payloads",
                "description": "Add additional customer identifiers (external_id, click_id, fbp/fbc cookies) to improve matching accuracy.",
                "priority": "high",
                "estimated_minutes": 30,
            },
            {
                "type": "diagnostics",
                "title": "Run EMQ Diagnostics",
                "description": "Analyze EMQ breakdown by platform to identify which integration is underperforming.",
                "priority": "normal",
                "estimated_minutes": 10,
            },
        ],
    },
    "event_loss": {
        "title": "Event Loss Rate Elevated",
        "description_template": "Event loss rate is {value:.1f}% (threshold: {threshold:.1f}%). "
                                "Conversion events may not be reaching ad platforms, undermining attribution.",
        "recovery_actions": [
            {
                "type": "check_capi",
                "title": "Check CAPI Error Logs",
                "description": "Review server-side event delivery logs for HTTP errors, timeouts, or rate limiting from ad platforms.",
                "priority": "urgent",
                "estimated_minutes": 10,
            },
            {
                "type": "check_pixel",
                "title": "Verify Pixel Firing",
                "description": "Test that browser-side pixel events fire correctly on key conversion pages (purchase, lead, add-to-cart).",
                "priority": "high",
                "estimated_minutes": 20,
            },
            {
                "type": "resync",
                "title": "Re-sync Platform Data",
                "description": "Trigger a full data re-sync to recover any events that were delayed or failed to deliver.",
                "priority": "high",
                "estimated_minutes": 5,
                "auto_triggered": True,
            },
        ],
    },
    "api_down": {
        "title": "Platform API Connection Failed",
        "description_template": "API connectivity to {platforms} is down. "
                                "No data is being synced — automation has been automatically suspended.",
        "recovery_actions": [
            {
                "type": "diagnostics",
                "title": "Check API Credentials",
                "description": "Verify OAuth tokens haven't expired. Re-authenticate if needed via Settings → Integrations.",
                "priority": "urgent",
                "estimated_minutes": 5,
            },
            {
                "type": "resync",
                "title": "Attempt Reconnection",
                "description": "Trigger a reconnection attempt to restore API access and resume data sync.",
                "priority": "urgent",
                "estimated_minutes": 2,
                "auto_triggered": True,
            },
            {
                "type": "alert_team",
                "title": "Notify Operations Team",
                "description": "Alert team members that platform connectivity is down and automation is suspended.",
                "priority": "high",
                "estimated_minutes": 1,
                "auto_triggered": True,
            },
        ],
    },
    "data_stale": {
        "title": "Data Sync Stale",
        "description_template": "Campaign data hasn't been refreshed in {value:.0f} hours (threshold: {threshold:.0f}h). "
                                "Dashboard metrics may not reflect current performance.",
        "recovery_actions": [
            {
                "type": "resync",
                "title": "Trigger Full Data Sync",
                "description": "Force a complete re-sync of campaign data across all connected platforms.",
                "priority": "urgent",
                "estimated_minutes": 10,
                "auto_triggered": True,
            },
            {
                "type": "diagnostics",
                "title": "Check Sync Scheduler",
                "description": "Verify the Celery beat scheduler is running and sync tasks are being dispatched.",
                "priority": "high",
                "estimated_minutes": 5,
            },
        ],
    },
    "tracking_gap": {
        "title": "Tracking Gap Detected",
        "description_template": "Significant discrepancy between platform-reported and server-tracked conversions. "
                                "This may indicate a pixel or CAPI configuration issue.",
        "recovery_actions": [
            {
                "type": "check_pixel",
                "title": "Audit Conversion Tracking Setup",
                "description": "Compare pixel events vs. CAPI events to identify where the gap originates.",
                "priority": "high",
                "estimated_minutes": 30,
            },
            {
                "type": "diagnostics",
                "title": "Check Deduplication Settings",
                "description": "Ensure event_id is consistently set across pixel and CAPI to prevent double-counting or missed events.",
                "priority": "normal",
                "estimated_minutes": 15,
            },
        ],
    },
}


def _now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def detect_signal_issues(
    overall_score: int,
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    api_health: bool,
    data_freshness_hours: Optional[float],
    connected_platforms: List[str],
) -> List[SignalIssue]:
    """
    Detect all active signal health issues.

    Args:
        overall_score: Overall signal health score (0-100)
        emq_score: EMQ score as a fraction (e.g. 0.75 = 75%)
        event_loss_pct: Event loss percentage (0-100)
        api_health: Whether API connections are healthy
        data_freshness_hours: Hours since last data sync
        connected_platforms: List of connected platform names

    Returns:
        List of detected signal issues, sorted by severity
    """
    issues: List[SignalIssue] = []
    now = _now_iso()

    # 1. API connectivity check
    if not api_health:
        template = ISSUE_TEMPLATES["api_down"]
        platforms_str = ", ".join(connected_platforms) if connected_platforms else "connected platforms"
        issues.append(SignalIssue(
            id="issue_api_down",
            type="api_down",
            severity="critical",
            title=template["title"],
            description=template["description_template"].format(platforms=platforms_str),
            affected_platforms=connected_platforms,
            detected_at=now,
        ))

    # 2. EMQ degradation
    if emq_score is not None:
        emq_pct = emq_score * 100 if emq_score <= 1.0 else emq_score
        if emq_pct < 80:
            severity = "critical" if emq_pct < 60 else "high"
            template = ISSUE_TEMPLATES["emq_drop"]
            issues.append(SignalIssue(
                id="issue_emq_drop",
                type="emq_drop",
                severity=severity,
                title=template["title"],
                description=template["description_template"].format(value=emq_pct, threshold=80),
                metric_value=emq_pct,
                threshold=80.0,
                affected_platforms=connected_platforms,
                detected_at=now,
            ))

    # 3. Event loss spike
    if event_loss_pct is not None and event_loss_pct > 5.0:
        severity = "critical" if event_loss_pct > 15 else ("high" if event_loss_pct > 10 else "medium")
        template = ISSUE_TEMPLATES["event_loss"]
        issues.append(SignalIssue(
            id="issue_event_loss",
            type="event_loss",
            severity=severity,
            title=template["title"],
            description=template["description_template"].format(value=event_loss_pct, threshold=5.0),
            metric_value=event_loss_pct,
            threshold=5.0,
            affected_platforms=connected_platforms,
            detected_at=now,
        ))

    # 4. Data staleness
    if data_freshness_hours is not None and data_freshness_hours > 24:
        severity = "critical" if data_freshness_hours > 72 else ("high" if data_freshness_hours > 48 else "medium")
        template = ISSUE_TEMPLATES["data_stale"]
        issues.append(SignalIssue(
            id="issue_data_stale",
            type="data_stale",
            severity=severity,
            title=template["title"],
            description=template["description_template"].format(value=data_freshness_hours, threshold=24),
            metric_value=data_freshness_hours,
            threshold=24.0,
            affected_platforms=connected_platforms,
            detected_at=now,
        ))

    # Sort by severity (critical > high > medium > low)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda x: severity_order.get(x.severity, 3))

    return issues


def generate_recovery_actions(issues: List[SignalIssue]) -> List[RecoveryAction]:
    """
    Generate targeted recovery actions for each detected issue.

    Returns actions sorted by priority with auto-triggered actions first.
    """
    actions: List[RecoveryAction] = []
    action_idx = 0

    for issue in issues:
        template = ISSUE_TEMPLATES.get(issue.type, {})
        for action_template in template.get("recovery_actions", []):
            action_idx += 1
            auto = action_template.get("auto_triggered", False)
            actions.append(RecoveryAction(
                id=f"action_{action_idx}",
                issue_id=issue.id,
                type=action_template["type"],
                title=action_template["title"],
                description=action_template["description"],
                status="in_progress" if auto else "pending",
                priority=action_template.get("priority", "normal"),
                auto_triggered=auto,
                estimated_minutes=action_template.get("estimated_minutes"),
            ))

    # Sort: auto-triggered first, then by priority
    priority_order = {"urgent": 0, "high": 1, "normal": 2}
    actions.sort(key=lambda a: (
        0 if a.auto_triggered else 1,
        priority_order.get(a.priority, 2),
    ))

    return actions


def build_recovery_timeline(
    issues: List[SignalIssue],
    actions: List[RecoveryAction],
) -> List[RecoveryTimeline]:
    """Build a timeline of detection and recovery events."""
    timeline: List[RecoveryTimeline] = []
    now = _now_iso()

    # Detection events
    for issue in issues:
        timeline.append(RecoveryTimeline(
            timestamp=issue.detected_at,
            event=f"Detected: {issue.title}",
            type="detection",
            details=f"Severity: {issue.severity}",
        ))

    # Auto-triggered actions
    for action in actions:
        if action.auto_triggered:
            timeline.append(RecoveryTimeline(
                timestamp=now,
                event=f"Auto-triggered: {action.title}",
                type="action",
                details=f"Status: {action.status}",
            ))

    # Pending manual actions
    manual_count = sum(1 for a in actions if not a.auto_triggered)
    if manual_count > 0:
        timeline.append(RecoveryTimeline(
            timestamp=now,
            event=f"{manual_count} manual action{'s' if manual_count > 1 else ''} recommended",
            type="progress",
            details="Review and execute from the recovery panel",
        ))

    return timeline


def determine_recovery_status(
    issues: List[SignalIssue],
) -> Literal["healthy", "recovering", "degraded", "critical"]:
    """Determine overall recovery status."""
    if not issues:
        return "healthy"

    severities = [i.severity for i in issues]
    if "critical" in severities:
        return "critical"
    elif "high" in severities:
        return "degraded"
    else:
        return "recovering"


def calculate_recovery_progress(
    actions: List[RecoveryAction],
) -> int:
    """Calculate overall recovery progress percentage."""
    if not actions:
        return 100

    completed = sum(1 for a in actions if a.status == "completed")
    in_progress = sum(1 for a in actions if a.status == "in_progress")

    # Each completed action = full credit, in-progress = half credit
    progress = (completed + in_progress * 0.5) / len(actions) * 100
    return min(100, int(progress))


def generate_recovery_summary(
    status: str,
    issues: List[SignalIssue],
    actions: List[RecoveryAction],
) -> str:
    """Generate a human-readable recovery summary."""
    if not issues:
        return (
            "All signals are healthy. EMQ, event delivery, and platform "
            "connectivity are operating within normal parameters."
        )

    critical = [i for i in issues if i.severity == "critical"]
    high = [i for i in issues if i.severity == "high"]
    auto_actions = [a for a in actions if a.auto_triggered]

    parts = []

    if critical:
        titles = " and ".join(i.title.lower() for i in critical[:2])
        parts.append(f"Critical issue detected: {titles}")
    elif high:
        titles = " and ".join(i.title.lower() for i in high[:2])
        parts.append(f"Signal health degraded: {titles}")
    else:
        parts.append(f"{len(issues)} signal issue{'s' if len(issues) > 1 else ''} detected")

    if auto_actions:
        parts.append(
            f"{len(auto_actions)} recovery action{'s' if len(auto_actions) > 1 else ''} "
            f"auto-triggered"
        )

    manual = [a for a in actions if not a.auto_triggered and a.status == "pending"]
    if manual:
        parts.append(f"{len(manual)} manual step{'s' if len(manual) > 1 else ''} recommended")

    return ". ".join(parts) + "."


def build_signal_recovery(
    overall_score: int,
    emq_score: Optional[float],
    event_loss_pct: Optional[float],
    api_health: bool,
    data_freshness_hours: Optional[float],
    connected_platforms: List[str],
) -> SignalRecoveryResponse:
    """
    Main entry point: builds the full signal recovery response.

    Analyzes current signal health indicators, detects issues,
    generates recovery actions, and builds a recovery timeline.
    """
    # Detect issues
    issues = detect_signal_issues(
        overall_score=overall_score,
        emq_score=emq_score,
        event_loss_pct=event_loss_pct,
        api_health=api_health,
        data_freshness_hours=data_freshness_hours,
        connected_platforms=connected_platforms,
    )

    # Generate recovery actions
    actions = generate_recovery_actions(issues)

    # Build timeline
    timeline = build_recovery_timeline(issues, actions)

    # Determine status
    status = determine_recovery_status(issues)

    # Calculate progress
    progress = calculate_recovery_progress(actions)

    # Summary
    summary = generate_recovery_summary(status, issues, actions)

    # Affected platforms
    all_platforms = set()
    for issue in issues:
        all_platforms.update(issue.affected_platforms)

    # Estimated recovery time
    est_minutes = None
    if actions:
        pending_actions = [a for a in actions if a.status != "completed"]
        estimates = [a.estimated_minutes for a in pending_actions if a.estimated_minutes]
        if estimates:
            est_minutes = max(estimates)  # Parallel execution, use longest

    return SignalRecoveryResponse(
        status=status,
        summary=summary,
        issues=issues,
        recovery_actions=actions,
        timeline=timeline,
        overall_health_score=overall_score,
        recovery_progress_pct=progress,
        has_active_recovery=len(issues) > 0,
        platforms_affected=sorted(all_platforms),
        estimated_recovery_minutes=est_minutes,
    )
