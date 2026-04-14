# =============================================================================
# Unified Notifications with AI Priority — Feature #8
# =============================================================================
"""
Unified Notifications — aggregates alerts from multiple sources (pacing,
signal health, campaign performance, system), scores each by urgency,
impact, and actionability, then returns a priority-ranked feed.

Architecture:
1. Collects notifications from all sources
2. Scores urgency (severity, recency, time-sensitivity)
3. Scores impact (spend at risk, deviation magnitude)
4. Scores actionability (can user act? suggested action available?)
5. Computes composite priority score
6. Groups by category, deduplicates, returns ranked feed

Builds on: notifications model, pacing alerts, signal health, anomalies
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class SuggestedAction(BaseModel):
    """A suggested action for a notification."""
    action_type: str  # e.g. "navigate", "adjust_budget", "resync", "review"
    label: str
    description: str
    url: Optional[str] = None


class PrioritizedNotification(BaseModel):
    """A single notification with AI priority scoring."""
    id: str
    title: str
    message: str
    source: Literal["pacing", "signal_health", "campaign", "anomaly", "system", "trust_gate", "churn"]
    notification_type: Literal["info", "warning", "error", "success", "alert"]
    category: str
    priority_score: float  # 0-100 (higher = more urgent)
    urgency: float  # 0-100
    impact: float  # 0-100
    actionability: float  # 0-100
    priority_label: Literal["critical", "high", "medium", "low"]
    created_at: str
    is_read: bool = False
    suggested_action: Optional[SuggestedAction] = None
    context: Dict = {}  # extra context data


class NotificationGroup(BaseModel):
    """A group of related notifications."""
    category: str
    label: str
    count: int
    top_priority: float
    notifications: List[PrioritizedNotification] = []


class UnifiedNotificationsResponse(BaseModel):
    """Full unified notifications response."""
    summary: str
    total_count: int
    unread_count: int
    critical_count: int
    high_count: int
    notifications: List[PrioritizedNotification] = []
    groups: List[NotificationGroup] = []
    top_actions: List[SuggestedAction] = []


# ── Scoring ──────────────────────────────────────────────────────────────────

def _score_urgency(
    severity: str,
    hours_ago: float,
    is_time_sensitive: bool = False,
) -> float:
    """Score urgency based on severity and recency."""
    # Severity base
    severity_scores = {
        "critical": 90,
        "error": 75,
        "warning": 50,
        "alert": 45,
        "info": 20,
        "success": 10,
    }
    base = severity_scores.get(severity.lower(), 30)

    # Recency boost (newer = more urgent)
    if hours_ago < 1:
        recency_boost = 10
    elif hours_ago < 6:
        recency_boost = 5
    elif hours_ago < 24:
        recency_boost = 0
    else:
        recency_boost = -10

    # Time sensitivity
    time_boost = 15 if is_time_sensitive else 0

    return min(100, max(0, base + recency_boost + time_boost))


def _score_impact(
    spend_at_risk: float = 0,
    deviation_pct: float = 0,
    campaigns_affected: int = 0,
) -> float:
    """Score business impact of the notification."""
    score = 0

    # Spend at risk
    if spend_at_risk >= 10000:
        score += 40
    elif spend_at_risk >= 5000:
        score += 30
    elif spend_at_risk >= 1000:
        score += 20
    elif spend_at_risk > 0:
        score += 10

    # Deviation magnitude
    if abs(deviation_pct) >= 50:
        score += 30
    elif abs(deviation_pct) >= 25:
        score += 20
    elif abs(deviation_pct) >= 10:
        score += 10

    # Campaigns affected
    if campaigns_affected >= 5:
        score += 20
    elif campaigns_affected >= 2:
        score += 10
    elif campaigns_affected >= 1:
        score += 5

    return min(100, score)


def _score_actionability(
    has_suggested_action: bool,
    can_auto_resolve: bool = False,
    requires_manual: bool = False,
) -> float:
    """Score how actionable the notification is."""
    if can_auto_resolve:
        return 90
    if has_suggested_action and not requires_manual:
        return 70
    if has_suggested_action:
        return 50
    if requires_manual:
        return 30
    return 20


def _compute_priority(urgency: float, impact: float, actionability: float) -> float:
    """Compute composite priority score."""
    return round(urgency * 0.5 + impact * 0.3 + actionability * 0.2, 1)


def _priority_label(score: float) -> str:
    """Convert priority score to label."""
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"


# ── Notification Builders ────────────────────────────────────────────────────

def _build_campaign_notifications(
    campaigns: List[Dict],
    now: datetime,
) -> List[PrioritizedNotification]:
    """Generate notifications from campaign performance data."""
    notifications = []

    for c in campaigns:
        spend = c.get("spend", 0)
        revenue = c.get("revenue", 0)
        conversions = c.get("conversions", 0)
        roas = revenue / spend if spend > 0 else 0
        name = c.get("name", "Unknown")
        platform = c.get("platform", "Unknown")

        # Critical ROAS
        if spend > 100 and roas < 0.5:
            urgency = _score_urgency("critical", 2)
            impact = _score_impact(spend_at_risk=spend, deviation_pct=50)
            actionability = _score_actionability(True)
            priority = _compute_priority(urgency, impact, actionability)

            notifications.append(PrioritizedNotification(
                id=f"camp_roas_{c.get('id', 0)}",
                title=f"Critical ROAS: {name}",
                message=f"{name} on {platform} has {roas:.2f}x ROAS with ${spend:,.0f} spend — well below breakeven.",
                source="campaign",
                notification_type="error",
                category="Performance",
                priority_score=priority,
                urgency=urgency,
                impact=impact,
                actionability=actionability,
                priority_label=_priority_label(priority),
                created_at=now.isoformat(),
                suggested_action=SuggestedAction(
                    action_type="review",
                    label="Review Campaign",
                    description=f"Audit targeting, creative, and budget for {name}.",
                ),
                context={"campaign_id": c.get("id"), "roas": roas, "spend": spend},
            ))

        # Zero conversions with spend
        elif spend > 200 and conversions == 0:
            urgency = _score_urgency("warning", 4)
            impact = _score_impact(spend_at_risk=spend)
            actionability = _score_actionability(True, can_auto_resolve=False)
            priority = _compute_priority(urgency, impact, actionability)

            notifications.append(PrioritizedNotification(
                id=f"camp_noconv_{c.get('id', 0)}",
                title=f"No Conversions: {name}",
                message=f"{name} has spent ${spend:,.0f} with zero conversions. Check tracking setup.",
                source="campaign",
                notification_type="warning",
                category="Performance",
                priority_score=priority,
                urgency=urgency,
                impact=impact,
                actionability=actionability,
                priority_label=_priority_label(priority),
                created_at=now.isoformat(),
                suggested_action=SuggestedAction(
                    action_type="audit",
                    label="Audit Tracking",
                    description="Verify pixel/CAPI setup and conversion events.",
                ),
                context={"campaign_id": c.get("id"), "spend": spend},
            ))

        # High performer opportunity
        elif roas >= 5.0 and spend > 50:
            urgency = _score_urgency("info", 12)
            impact = _score_impact(spend_at_risk=0, deviation_pct=0, campaigns_affected=1)
            actionability = _score_actionability(True)
            priority = _compute_priority(urgency, impact, actionability)

            notifications.append(PrioritizedNotification(
                id=f"camp_star_{c.get('id', 0)}",
                title=f"Top Performer: {name}",
                message=f"{name} is achieving {roas:.2f}x ROAS — consider scaling budget.",
                source="campaign",
                notification_type="success",
                category="Opportunity",
                priority_score=priority,
                urgency=urgency,
                impact=impact,
                actionability=actionability,
                priority_label=_priority_label(priority),
                created_at=now.isoformat(),
                suggested_action=SuggestedAction(
                    action_type="adjust_budget",
                    label="Scale Budget",
                    description=f"Increase budget for {name} to capture more conversions.",
                ),
                context={"campaign_id": c.get("id"), "roas": roas, "spend": spend},
            ))

    return notifications


def _build_signal_notifications(
    signal_health_score: int,
    now: datetime,
) -> List[PrioritizedNotification]:
    """Generate notifications from signal health data."""
    notifications = []

    if signal_health_score < 40:
        urgency = _score_urgency("critical", 1, is_time_sensitive=True)
        impact = _score_impact(deviation_pct=60)
        actionability = _score_actionability(True, requires_manual=True)
        priority = _compute_priority(urgency, impact, actionability)

        notifications.append(PrioritizedNotification(
            id="signal_critical",
            title="Signal Health Critical",
            message=f"Signal health score is {signal_health_score}/100 — automations are blocked. Immediate investigation needed.",
            source="signal_health",
            notification_type="error",
            category="Signal Health",
            priority_score=priority,
            urgency=urgency,
            impact=impact,
            actionability=actionability,
            priority_label=_priority_label(priority),
            created_at=now.isoformat(),
            suggested_action=SuggestedAction(
                action_type="navigate",
                label="View Signal Recovery",
                description="Check signal recovery dashboard for active issues.",
            ),
            context={"health_score": signal_health_score},
        ))
    elif signal_health_score < 70:
        urgency = _score_urgency("warning", 3)
        impact = _score_impact(deviation_pct=30)
        actionability = _score_actionability(True)
        priority = _compute_priority(urgency, impact, actionability)

        notifications.append(PrioritizedNotification(
            id="signal_degraded",
            title="Signal Health Degraded",
            message=f"Signal health at {signal_health_score}/100 — automations on hold. Monitor closely.",
            source="signal_health",
            notification_type="warning",
            category="Signal Health",
            priority_score=priority,
            urgency=urgency,
            impact=impact,
            actionability=actionability,
            priority_label=_priority_label(priority),
            created_at=now.isoformat(),
            suggested_action=SuggestedAction(
                action_type="navigate",
                label="Check Signals",
                description="Review signal health details for degradation causes.",
            ),
            context={"health_score": signal_health_score},
        ))

    return notifications


def _build_system_notifications(
    total_campaigns: int,
    total_spend: float,
    overall_roas: float,
    now: datetime,
) -> List[PrioritizedNotification]:
    """Generate portfolio-level system notifications."""
    notifications = []

    if total_campaigns == 0:
        notifications.append(PrioritizedNotification(
            id="sys_no_campaigns",
            title="No Active Campaigns",
            message="No campaigns found. Connect your ad platforms to get started.",
            source="system",
            notification_type="info",
            category="System",
            priority_score=40,
            urgency=30,
            impact=50,
            actionability=60,
            priority_label="medium",
            created_at=now.isoformat(),
            suggested_action=SuggestedAction(
                action_type="navigate",
                label="Connect Platforms",
                description="Set up your ad platform integrations.",
            ),
        ))

    if overall_roas > 0 and overall_roas < 1.0 and total_spend > 500:
        urgency = _score_urgency("warning", 6)
        impact = _score_impact(spend_at_risk=total_spend, deviation_pct=40)
        actionability = _score_actionability(True)
        priority = _compute_priority(urgency, impact, actionability)

        notifications.append(PrioritizedNotification(
            id="sys_portfolio_roas",
            title="Portfolio Below Breakeven",
            message=f"Overall ROAS is {overall_roas:.2f}x across {total_campaigns} campaigns — portfolio is losing money.",
            source="system",
            notification_type="error",
            category="Performance",
            priority_score=priority,
            urgency=urgency,
            impact=impact,
            actionability=actionability,
            priority_label=_priority_label(priority),
            created_at=now.isoformat(),
            suggested_action=SuggestedAction(
                action_type="review",
                label="Review Budget Allocation",
                description="Open Budget Autopilot to see reallocation recommendations.",
            ),
            context={"roas": overall_roas, "total_spend": total_spend},
        ))

    return notifications


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_unified_notifications(
    campaigns: List[Dict],
    signal_health_score: int = 80,
    existing_notifications: Optional[List[Dict]] = None,
) -> UnifiedNotificationsResponse:
    """
    Main entry point: aggregates all notification sources, scores by
    AI priority, and returns a unified ranked feed.

    Args:
        campaigns: Campaign dicts with id, name, platform, spend, revenue, conversions
        signal_health_score: Current signal health (0-100)
        existing_notifications: Optional list of existing DB notifications

    Returns:
        UnifiedNotificationsResponse with prioritized notifications
    """
    now = datetime.now(timezone.utc)
    all_notifications: List[PrioritizedNotification] = []

    # Aggregate totals
    total_spend = sum(c.get("spend", 0) for c in campaigns)
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    overall_roas = total_revenue / total_spend if total_spend > 0 else 0

    # 1. Campaign-level notifications
    all_notifications.extend(_build_campaign_notifications(campaigns, now))

    # 2. Signal health notifications
    all_notifications.extend(_build_signal_notifications(signal_health_score, now))

    # 3. System / portfolio notifications
    all_notifications.extend(
        _build_system_notifications(len(campaigns), total_spend, overall_roas, now)
    )

    # 4. Include existing DB notifications (re-score them)
    if existing_notifications:
        for notif in existing_notifications:
            severity = notif.get("type", "info")
            created = notif.get("created_at")
            hours_ago = 24.0
            if created:
                try:
                    if isinstance(created, datetime):
                        hours_ago = (now - created).total_seconds() / 3600
                    elif isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        hours_ago = (now - dt).total_seconds() / 3600
                except (ValueError, TypeError):
                    pass

            urgency = _score_urgency(severity, hours_ago)
            impact = _score_impact()
            actionability = _score_actionability(bool(notif.get("action_url")))
            priority = _compute_priority(urgency, impact, actionability)

            all_notifications.append(PrioritizedNotification(
                id=str(notif.get("id", "")),
                title=notif.get("title", "Notification"),
                message=notif.get("message", ""),
                source="system",
                notification_type=severity.lower() if severity else "info",
                category=notif.get("category", "System"),
                priority_score=priority,
                urgency=urgency,
                impact=impact,
                actionability=actionability,
                priority_label=_priority_label(priority),
                created_at=str(created) if created else now.isoformat(),
                is_read=bool(notif.get("is_read", False)),
                suggested_action=SuggestedAction(
                    action_type="navigate",
                    label=notif.get("action_label", "View"),
                    description="",
                    url=notif.get("action_url"),
                ) if notif.get("action_url") else None,
                context=notif.get("extra_data") or {},
            ))

    # Sort by priority score descending
    all_notifications.sort(key=lambda n: -n.priority_score)

    # Group by category
    groups_map: Dict[str, List[PrioritizedNotification]] = {}
    for notif in all_notifications:
        cat = notif.category
        if cat not in groups_map:
            groups_map[cat] = []
        groups_map[cat].append(notif)

    groups = [
        NotificationGroup(
            category=cat,
            label=cat,
            count=len(items),
            top_priority=max(n.priority_score for n in items),
            notifications=items,
        )
        for cat, items in sorted(groups_map.items(), key=lambda x: -max(n.priority_score for n in x[1]))
    ]

    # Counts
    total = len(all_notifications)
    unread = sum(1 for n in all_notifications if not n.is_read)
    critical = sum(1 for n in all_notifications if n.priority_label == "critical")
    high = sum(1 for n in all_notifications if n.priority_label == "high")

    # Top suggested actions (deduplicated)
    seen_actions = set()
    top_actions = []
    for n in all_notifications:
        if n.suggested_action and n.suggested_action.action_type not in seen_actions:
            seen_actions.add(n.suggested_action.action_type)
            top_actions.append(n.suggested_action)
        if len(top_actions) >= 5:
            break

    # Summary
    summary = _build_summary(total, critical, high, unread, signal_health_score)

    return UnifiedNotificationsResponse(
        summary=summary,
        total_count=total,
        unread_count=unread,
        critical_count=critical,
        high_count=high,
        notifications=all_notifications[:20],  # Top 20
        groups=groups,
        top_actions=top_actions,
    )


def _build_summary(
    total: int,
    critical: int,
    high: int,
    unread: int,
    signal_health: int,
) -> str:
    """Build notification summary."""
    parts = []
    if critical > 0:
        parts.append(f"{critical} critical alert{'s' if critical > 1 else ''} requiring immediate attention.")
    if high > 0:
        parts.append(f"{high} high-priority notification{'s' if high > 1 else ''}.")
    if unread > 0:
        parts.append(f"{unread} unread of {total} total.")
    if total == 0:
        parts.append("No active notifications — all systems healthy.")
    return " ".join(parts) if parts else "Notifications are up to date."
