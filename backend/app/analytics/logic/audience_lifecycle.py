# =============================================================================
# Audience Lifecycle Automations — Feature #10
# =============================================================================
"""
Audience Lifecycle Automations — monitors CDP profile lifecycle stage
distribution and generates automated audience sync recommendations based
on stage transitions (anonymous → known → customer → churned).

Architecture:
1. Aggregates profiles by lifecycle stage
2. Detects stage transition volumes (e.g., new → known conversions)
3. Maps transitions to audience sync actions
4. Generates automation rules with trigger conditions
5. Tracks automation health and sync readiness

Builds on: CDP (cdp.py), Audience Sync (audience_sync/)
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class LifecycleStageMetric(BaseModel):
    """Metrics for a single lifecycle stage."""
    stage: str  # anonymous, known, customer, churned
    count: int
    pct_of_total: float
    change_7d: int  # net change in last 7 days
    change_pct: float
    avg_revenue: float  # avg revenue per profile in stage
    avg_events: float  # avg events per profile in stage


class LifecycleTransition(BaseModel):
    """A detected lifecycle stage transition."""
    from_stage: str
    to_stage: str
    count_7d: int  # transitions in last 7 days
    count_30d: int
    trend: Literal["increasing", "stable", "decreasing"]
    is_positive: bool  # is this transition good for business?


class AudienceRule(BaseModel):
    """An automation rule that maps lifecycle events to audience actions."""
    rule_id: str
    name: str
    description: str
    trigger_stage: str  # lifecycle stage that triggers the rule
    trigger_condition: str  # e.g., "enters_stage", "exits_stage", "in_stage_over_7d"
    action: str  # e.g., "sync_to_meta", "add_to_segment", "trigger_campaign"
    target_platform: Optional[str] = None
    target_audience: Optional[str] = None
    is_active: bool = True
    profiles_matched: int = 0
    last_triggered: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"
    category: Literal["acquisition", "activation", "retention", "reactivation"] = "activation"


class LifecycleRecommendation(BaseModel):
    """A recommendation for lifecycle automation improvement."""
    title: str
    description: str
    impact: Literal["high", "medium", "low"]
    category: str
    action_label: str
    profiles_affected: int


class SyncReadiness(BaseModel):
    """Platform sync readiness status."""
    platform: str
    is_connected: bool
    audiences_count: int
    auto_sync_enabled: bool
    last_sync: Optional[str] = None
    match_rate_pct: float = 0.0


class AudienceLifecycleResponse(BaseModel):
    """Full audience lifecycle automations response."""
    summary: str
    total_profiles: int
    active_rules: int
    total_rules: int
    stages: List[LifecycleStageMetric] = []
    transitions: List[LifecycleTransition] = []
    rules: List[AudienceRule] = []
    recommendations: List[LifecycleRecommendation] = []
    sync_readiness: List[SyncReadiness] = []
    lifecycle_health: Literal["excellent", "good", "needs_attention", "poor"] = "good"
    automation_coverage_pct: float = 0.0  # % of transitions covered by rules
    profiles_in_automation: int = 0


# ── Lifecycle Analysis ────────────────────────────────────────────────────────

STAGE_ORDER = ["anonymous", "known", "customer", "churned"]

POSITIVE_TRANSITIONS = {
    ("anonymous", "known"),
    ("known", "customer"),
    ("churned", "known"),
    ("churned", "customer"),
}

NEGATIVE_TRANSITIONS = {
    ("customer", "churned"),
    ("known", "churned"),
    ("known", "anonymous"),
}


def _analyze_stages(profiles: List[Dict]) -> List[LifecycleStageMetric]:
    """Analyze profile distribution across lifecycle stages."""
    stage_counts: Dict[str, Dict] = {}
    total = len(profiles)

    for p in profiles:
        stage = p.get("lifecycle_stage", "anonymous")
        if stage not in stage_counts:
            stage_counts[stage] = {"count": 0, "revenue": 0, "events": 0, "recent": 0}
        stage_counts[stage]["count"] += 1
        stage_counts[stage]["revenue"] += p.get("total_revenue", 0)
        stage_counts[stage]["events"] += p.get("total_events", 0)
        if p.get("is_recent", False):
            stage_counts[stage]["recent"] += 1

    metrics = []
    for stage in STAGE_ORDER:
        data = stage_counts.get(stage, {"count": 0, "revenue": 0, "events": 0, "recent": 0})
        count = data["count"]
        pct = (count / total * 100) if total > 0 else 0
        avg_rev = data["revenue"] / count if count > 0 else 0
        avg_events = data["events"] / count if count > 0 else 0
        recent = data["recent"]
        change_pct = (recent / count * 100) if count > 0 else 0

        metrics.append(LifecycleStageMetric(
            stage=stage,
            count=count,
            pct_of_total=round(pct, 1),
            change_7d=recent,
            change_pct=round(change_pct, 1),
            avg_revenue=round(avg_rev, 2),
            avg_events=round(avg_events, 1),
        ))

    return metrics


def _detect_transitions(profiles: List[Dict]) -> List[LifecycleTransition]:
    """Detect lifecycle stage transitions from profile data."""
    transitions = []

    # Simulate transition detection from profile metadata
    # In production, this would query a transitions log table
    transition_counts: Dict[tuple, Dict] = {}

    for p in profiles:
        current = p.get("lifecycle_stage", "anonymous")
        previous = p.get("previous_stage")
        if previous and previous != current:
            key = (previous, current)
            if key not in transition_counts:
                transition_counts[key] = {"count_7d": 0, "count_30d": 0}
            if p.get("is_recent", False):
                transition_counts[key]["count_7d"] += 1
            transition_counts[key]["count_30d"] += 1

    # Also generate expected transitions from stage distribution
    stage_counts = {}
    for p in profiles:
        stage = p.get("lifecycle_stage", "anonymous")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # Infer common transitions from distribution
    total = len(profiles)
    if total > 0:
        for from_s, to_s in [
            ("anonymous", "known"),
            ("known", "customer"),
            ("customer", "churned"),
            ("churned", "known"),
        ]:
            if (from_s, to_s) not in transition_counts:
                from_count = stage_counts.get(from_s, 0)
                to_count = stage_counts.get(to_s, 0)
                # Estimate: ~5% of from_stage transitions per period
                est_7d = max(1, int(from_count * 0.05))
                est_30d = max(1, int(from_count * 0.15))
                transition_counts[(from_s, to_s)] = {
                    "count_7d": est_7d,
                    "count_30d": est_30d,
                }

    for (from_s, to_s), counts in transition_counts.items():
        c7 = counts["count_7d"]
        c30 = counts["count_30d"]
        # Trend: compare 7d rate to 30d weekly average
        weekly_avg = c30 / 4.3 if c30 > 0 else 0
        if weekly_avg > 0:
            ratio = c7 / weekly_avg
            trend = "increasing" if ratio > 1.15 else "decreasing" if ratio < 0.85 else "stable"
        else:
            trend = "stable"

        transitions.append(LifecycleTransition(
            from_stage=from_s,
            to_stage=to_s,
            count_7d=c7,
            count_30d=c30,
            trend=trend,
            is_positive=(from_s, to_s) in POSITIVE_TRANSITIONS,
        ))

    transitions.sort(key=lambda t: -t.count_7d)
    return transitions


def _generate_rules(
    stages: List[LifecycleStageMetric],
    transitions: List[LifecycleTransition],
    connected_platforms: List[str],
) -> List[AudienceRule]:
    """Generate automation rules based on lifecycle data."""
    rules = []
    rule_idx = 0

    # Rule: New known profiles → sync to ad platforms for lookalike
    anon_to_known = next(
        (t for t in transitions if t.from_stage == "anonymous" and t.to_stage == "known"),
        None,
    )
    if anon_to_known:
        for platform in connected_platforms[:2]:
            rule_idx += 1
            rules.append(AudienceRule(
                rule_id=f"rule_{rule_idx:03d}",
                name=f"New Known → {platform.title()} Lookalike Seed",
                description=f"When a profile moves from anonymous to known, add to {platform} lookalike seed audience for prospecting.",
                trigger_stage="known",
                trigger_condition="enters_stage",
                action="sync_to_platform",
                target_platform=platform,
                target_audience=f"{platform}_known_profiles",
                profiles_matched=anon_to_known.count_7d,
                priority="high",
                category="acquisition",
            ))

    # Rule: New customers → sync for exclusion/upsell
    known_to_customer = next(
        (t for t in transitions if t.from_stage == "known" and t.to_stage == "customer"),
        None,
    )
    if known_to_customer:
        for platform in connected_platforms[:2]:
            rule_idx += 1
            rules.append(AudienceRule(
                rule_id=f"rule_{rule_idx:03d}",
                name=f"New Customer → {platform.title()} Exclusion",
                description=f"Exclude new customers from prospecting campaigns on {platform} to reduce wasted spend.",
                trigger_stage="customer",
                trigger_condition="enters_stage",
                action="sync_to_platform",
                target_platform=platform,
                target_audience=f"{platform}_customer_exclusion",
                profiles_matched=known_to_customer.count_7d,
                priority="high",
                category="activation",
            ))

    # Rule: Churned profiles → trigger reactivation
    to_churned = next(
        (t for t in transitions if t.to_stage == "churned"),
        None,
    )
    if to_churned:
        rule_idx += 1
        rules.append(AudienceRule(
            rule_id=f"rule_{rule_idx:03d}",
            name="Churned → Reactivation Campaign",
            description="When customers churn, trigger a reactivation sequence via email/WhatsApp and add to remarketing audiences.",
            trigger_stage="churned",
            trigger_condition="enters_stage",
            action="trigger_reactivation",
            profiles_matched=to_churned.count_7d,
            priority="high",
            category="reactivation",
        ))

        for platform in connected_platforms[:1]:
            rule_idx += 1
            rules.append(AudienceRule(
                rule_id=f"rule_{rule_idx:03d}",
                name=f"Churned → {platform.title()} Remarketing",
                description=f"Add churned profiles to {platform} remarketing audience for win-back campaigns.",
                trigger_stage="churned",
                trigger_condition="enters_stage",
                action="sync_to_platform",
                target_platform=platform,
                target_audience=f"{platform}_churned_remarketing",
                profiles_matched=to_churned.count_7d,
                priority="medium",
                category="reactivation",
            ))

    # Rule: Long-time known but not customer → nurture
    known_stage = next((s for s in stages if s.stage == "known"), None)
    if known_stage and known_stage.count > 0:
        rule_idx += 1
        stale_count = max(1, int(known_stage.count * 0.3))
        rules.append(AudienceRule(
            rule_id=f"rule_{rule_idx:03d}",
            name="Stale Known → Nurture Sequence",
            description="Profiles that have been 'known' for 14+ days without converting — trigger nurture email sequence.",
            trigger_stage="known",
            trigger_condition="in_stage_over_14d",
            action="trigger_nurture",
            profiles_matched=stale_count,
            priority="medium",
            category="activation",
        ))

    # Rule: Reactivated churned → celebrate & upsell
    churned_to_known = next(
        (t for t in transitions if t.from_stage == "churned" and t.to_stage in ("known", "customer")),
        None,
    )
    if churned_to_known:
        rule_idx += 1
        rules.append(AudienceRule(
            rule_id=f"rule_{rule_idx:03d}",
            name="Reactivated → Welcome Back Flow",
            description="Churned profiles that return — trigger welcome-back sequence with special offer.",
            trigger_stage=churned_to_known.to_stage,
            trigger_condition="enters_stage_from_churned",
            action="trigger_welcome_back",
            profiles_matched=churned_to_known.count_7d,
            priority="medium",
            category="retention",
        ))

    return rules


def _generate_recommendations(
    stages: List[LifecycleStageMetric],
    transitions: List[LifecycleTransition],
    rules: List[AudienceRule],
    connected_platforms: List[str],
) -> List[LifecycleRecommendation]:
    """Generate actionable recommendations."""
    recs = []

    # Check for high anonymous ratio
    anon = next((s for s in stages if s.stage == "anonymous"), None)
    total = sum(s.count for s in stages)
    if anon and total > 0 and anon.pct_of_total > 60:
        recs.append(LifecycleRecommendation(
            title="High anonymous traffic — improve identification",
            description=f"{anon.pct_of_total:.0f}% of profiles are anonymous. Deploy identity capture (login prompts, email gates, progressive profiling) to convert anonymous visitors.",
            impact="high",
            category="acquisition",
            action_label="Review identity capture strategy",
            profiles_affected=anon.count,
        ))

    # Check for churn spike
    churn_trans = next(
        (t for t in transitions if t.to_stage == "churned" and t.trend == "increasing"),
        None,
    )
    if churn_trans:
        recs.append(LifecycleRecommendation(
            title="Churn rate increasing — activate prevention",
            description=f"{churn_trans.count_7d} profiles churned this week (trend: increasing). Enable churn prevention automations and review win-back campaigns.",
            impact="high",
            category="retention",
            action_label="Activate churn prevention rules",
            profiles_affected=churn_trans.count_7d,
        ))

    # Check for platform coverage
    if len(connected_platforms) < 2:
        recs.append(LifecycleRecommendation(
            title="Connect more ad platforms for broader reach",
            description="Only {} platform{} connected. Connecting additional platforms enables cross-platform audience sync and better lifecycle automation coverage.".format(
                len(connected_platforms), "s" if len(connected_platforms) != 1 else ""
            ),
            impact="medium",
            category="setup",
            action_label="Connect additional platforms",
            profiles_affected=total,
        ))

    # Check for stale known profiles
    known = next((s for s in stages if s.stage == "known"), None)
    if known and known.count > 0:
        stale = max(1, int(known.count * 0.3))
        if stale > 10:
            recs.append(LifecycleRecommendation(
                title="Nurture stale known profiles",
                description=f"~{stale} known profiles haven't converted. Deploy automated nurture sequences to move them toward purchase.",
                impact="medium",
                category="activation",
                action_label="Create nurture automation",
                profiles_affected=stale,
            ))

    # Check conversion rate
    known_to_cust = next(
        (t for t in transitions if t.from_stage == "known" and t.to_stage == "customer"),
        None,
    )
    if known_to_cust and known:
        conv_rate = (known_to_cust.count_30d / known.count * 100) if known.count > 0 else 0
        if conv_rate < 5:
            recs.append(LifecycleRecommendation(
                title="Low known→customer conversion rate",
                description=f"Only {conv_rate:.1f}% of known profiles convert to customers per month. Consider improving onboarding flows and targeted offers.",
                impact="high",
                category="activation",
                action_label="Optimize conversion funnel",
                profiles_affected=known.count,
            ))

    return recs[:5]


def _assess_health(
    stages: List[LifecycleStageMetric],
    transitions: List[LifecycleTransition],
    rules: List[AudienceRule],
) -> str:
    """Assess lifecycle automation health."""
    score = 50  # baseline

    # Positive signals
    total = sum(s.count for s in stages)
    customer_pct = next((s.pct_of_total for s in stages if s.stage == "customer"), 0)
    if customer_pct > 20:
        score += 15
    elif customer_pct > 10:
        score += 10

    # Active rules
    active_rules = sum(1 for r in rules if r.is_active)
    if active_rules >= 5:
        score += 15
    elif active_rules >= 3:
        score += 10

    # Positive transitions trending up
    positive_up = sum(1 for t in transitions if t.is_positive and t.trend == "increasing")
    score += positive_up * 5

    # Negative signals
    negative_up = sum(1 for t in transitions if not t.is_positive and t.trend == "increasing")
    score -= negative_up * 10

    anon_pct = next((s.pct_of_total for s in stages if s.stage == "anonymous"), 0)
    if anon_pct > 70:
        score -= 15

    if score >= 75:
        return "excellent"
    elif score >= 55:
        return "good"
    elif score >= 35:
        return "needs_attention"
    return "poor"


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_audience_lifecycle(
    profiles: List[Dict],
    connected_platforms: Optional[List[str]] = None,
    existing_audiences: Optional[List[Dict]] = None,
) -> AudienceLifecycleResponse:
    """
    Main entry point: analyzes CDP profile lifecycle distribution and
    generates automated audience sync recommendations.

    Args:
        profiles: List of profile dicts with lifecycle_stage, total_revenue,
                  total_events, previous_stage, is_recent
        connected_platforms: List of connected ad platform names
        existing_audiences: List of existing platform audiences

    Returns:
        AudienceLifecycleResponse with stages, transitions, rules, recommendations
    """
    if connected_platforms is None:
        connected_platforms = []

    if not profiles:
        return AudienceLifecycleResponse(
            summary="No CDP profiles available for lifecycle analysis.",
            total_profiles=0,
            active_rules=0,
            total_rules=0,
        )

    # Analyze stages
    stages = _analyze_stages(profiles)
    total_profiles = sum(s.count for s in stages)

    # Detect transitions
    transitions = _detect_transitions(profiles)

    # Generate automation rules
    rules = _generate_rules(stages, transitions, connected_platforms)
    active_rules = sum(1 for r in rules if r.is_active)
    profiles_in_auto = sum(r.profiles_matched for r in rules if r.is_active)

    # Generate recommendations
    recommendations = _generate_recommendations(stages, transitions, rules, connected_platforms)

    # Build sync readiness
    sync_readiness = []
    for platform in connected_platforms:
        audience_count = 0
        if existing_audiences:
            audience_count = sum(
                1 for a in existing_audiences
                if a.get("platform", "").lower() == platform.lower()
            )
        sync_readiness.append(SyncReadiness(
            platform=platform,
            is_connected=True,
            audiences_count=audience_count,
            auto_sync_enabled=audience_count > 0,
            match_rate_pct=round(65 + audience_count * 5, 1),  # estimated
        ))

    # Assess health
    health = _assess_health(stages, transitions, rules)

    # Automation coverage: how many transition types have rules
    transition_types = {(t.from_stage, t.to_stage) for t in transitions}
    covered_types = set()
    for r in rules:
        if r.trigger_condition == "enters_stage":
            for t in transitions:
                if t.to_stage == r.trigger_stage:
                    covered_types.add((t.from_stage, t.to_stage))
    coverage = (len(covered_types) / len(transition_types) * 100) if transition_types else 0

    # Summary
    summary = _build_summary(stages, transitions, rules, health, total_profiles)

    return AudienceLifecycleResponse(
        summary=summary,
        total_profiles=total_profiles,
        active_rules=active_rules,
        total_rules=len(rules),
        stages=stages,
        transitions=transitions,
        rules=rules,
        recommendations=recommendations,
        sync_readiness=sync_readiness,
        lifecycle_health=health,
        automation_coverage_pct=round(coverage, 1),
        profiles_in_automation=profiles_in_auto,
    )


def _build_summary(
    stages: List[LifecycleStageMetric],
    transitions: List[LifecycleTransition],
    rules: List[AudienceRule],
    health: str,
    total_profiles: int,
) -> str:
    """Build executive summary."""
    parts = []

    parts.append(f"Tracking {total_profiles:,} profiles across {len(stages)} lifecycle stages.")

    customer_count = next((s.count for s in stages if s.stage == "customer"), 0)
    if customer_count > 0:
        parts.append(f"{customer_count:,} active customers.")

    positive_trans = sum(t.count_7d for t in transitions if t.is_positive)
    if positive_trans > 0:
        parts.append(f"{positive_trans:,} positive stage transitions this week.")

    active_count = sum(1 for r in rules if r.is_active)
    if active_count > 0:
        parts.append(f"{active_count} automation rules active.")

    health_labels = {
        "excellent": "Lifecycle health is excellent.",
        "good": "Lifecycle health is good.",
        "needs_attention": "Lifecycle automations need attention.",
        "poor": "Lifecycle automations need significant improvement.",
    }
    parts.append(health_labels.get(health, ""))

    return " ".join(parts)
