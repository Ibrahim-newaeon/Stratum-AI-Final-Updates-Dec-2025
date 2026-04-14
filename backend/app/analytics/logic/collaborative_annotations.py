# =============================================================================
# Feature #17 — Collaborative Annotations
# =============================================================================
"""
Team annotations and notes on dashboard metrics and campaigns.

Features:
- Annotations on metrics, campaigns, time periods
- Thread-based discussions
- Tag system (performance, strategy, alert, question)
- Mention system for team members
- Activity feed of recent annotations
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class AnnotationAuthor(BaseModel):
    """Author of an annotation."""

    user_id: int = 0
    name: str = ""
    initials: str = ""
    role: str = ""


class AnnotationReply(BaseModel):
    """Reply in an annotation thread."""

    reply_id: str = ""
    author: AnnotationAuthor = Field(default_factory=AnnotationAuthor)
    content: str = ""
    created_at: str = ""
    reactions: dict[str, int] = Field(default_factory=dict)


class Annotation(BaseModel):
    """A single annotation on a metric or campaign."""

    annotation_id: str = ""
    target_type: str = ""  # metric / campaign / period / platform / general
    target_id: str = ""
    target_label: str = ""
    content: str = ""
    tag: str = "general"  # performance / strategy / alert / question / general
    author: AnnotationAuthor = Field(default_factory=AnnotationAuthor)
    created_at: str = ""
    updated_at: str = ""
    pinned: bool = False
    resolved: bool = False
    replies: list[AnnotationReply] = Field(default_factory=list)
    reply_count: int = 0
    mentions: list[str] = Field(default_factory=list)


class AnnotationSummary(BaseModel):
    """Summary stats for annotations."""

    total: int = 0
    unresolved: int = 0
    pinned: int = 0
    by_tag: dict[str, int] = Field(default_factory=dict)
    recent_activity_count: int = 0
    contributors: int = 0


class AnnotationInsight(BaseModel):
    """AI insight about team activity."""

    title: str = ""
    description: str = ""
    severity: str = "info"


class CollaborativeAnnotationsResponse(BaseModel):
    """Full annotations dashboard response."""

    summary: str = ""
    annotations: list[Annotation] = Field(default_factory=list)
    stats: AnnotationSummary = Field(default_factory=AnnotationSummary)
    insights: list[AnnotationInsight] = Field(default_factory=list)
    active_discussions: int = 0
    team_members_active: int = 0


# ── Sample data generator ────────────────────────────────────────────────────


def _generate_sample_annotations(
    campaigns: list[dict],
    user_name: str,
    user_id: int,
) -> list[Annotation]:
    """Generate contextual annotations from campaign data."""
    annotations: list[Annotation] = []
    now = datetime.now(timezone.utc)

    # Build author
    parts = user_name.split() if user_name else ["User"]
    initials = "".join(p[0].upper() for p in parts[:2]) if parts else "U"
    author = AnnotationAuthor(
        user_id=user_id,
        name=user_name or "Team Member",
        initials=initials,
        role="Marketing Manager",
    )
    ai_author = AnnotationAuthor(
        user_id=0,
        name="Stratum AI",
        initials="AI",
        role="AI Assistant",
    )

    # Aggregate by platform
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {"spend": 0.0, "revenue": 0.0, "conversions": 0}
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))

    total_spend = sum(d["spend"] for d in platform_data.values())
    total_revenue = sum(d["revenue"] for d in platform_data.values())
    overall_roas = total_revenue / total_spend if total_spend > 0 else 0

    # Performance note on overall ROAS
    annotations.append(
        Annotation(
            annotation_id="ann_1",
            target_type="metric",
            target_id="roas",
            target_label="Overall ROAS",
            content=f"ROAS at {overall_roas:.2f}x this period. {'Strong performance — consider scaling top campaigns.' if overall_roas >= 3 else 'Below target — review underperformers.'}",
            tag="performance",
            author=ai_author,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            pinned=overall_roas < 2,
            reply_count=1,
            replies=[
                AnnotationReply(
                    reply_id="rep_1",
                    author=author,
                    content="Noted. Will review campaign allocation this week.",
                    created_at=now.isoformat(),
                ),
            ],
        )
    )

    # Platform-specific annotations
    for i, (plat, data) in enumerate(sorted(platform_data.items(), key=lambda x: x[1]["spend"], reverse=True)):
        plat_roas = data["revenue"] / data["spend"] if data["spend"] > 0 else 0
        if plat_roas < 1.5:
            annotations.append(
                Annotation(
                    annotation_id=f"ann_plat_{i}",
                    target_type="platform",
                    target_id=plat,
                    target_label=plat.replace("_", " ").title(),
                    content=f"{plat.title()} ROAS is {plat_roas:.2f}x — below breakeven threshold. Consider pausing lowest performers.",
                    tag="alert",
                    author=ai_author,
                    created_at=now.isoformat(),
                    updated_at=now.isoformat(),
                )
            )
        elif plat_roas >= 4:
            annotations.append(
                Annotation(
                    annotation_id=f"ann_plat_{i}",
                    target_type="platform",
                    target_id=plat,
                    target_label=plat.replace("_", " ").title(),
                    content=f"Excellent {plat.title()} performance at {plat_roas:.2f}x ROAS. Opportunity to scale budget 20-30%.",
                    tag="strategy",
                    author=ai_author,
                    created_at=now.isoformat(),
                    updated_at=now.isoformat(),
                    pinned=True,
                )
            )

    # Spend allocation note
    if total_spend > 0:
        annotations.append(
            Annotation(
                annotation_id="ann_spend",
                target_type="metric",
                target_id="spend",
                target_label="Total Spend",
                content=f"Total spend: ${total_spend:,.0f} across {len(platform_data)} platforms. Budget pacing on track.",
                tag="general",
                author=author,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )

    # Strategy note
    annotations.append(
        Annotation(
            annotation_id="ann_strategy",
            target_type="general",
            target_id="strategy",
            target_label="Q2 Strategy",
            content="Q2 focus: shift 15% of budget to high-ROAS platforms while testing new creative formats on TikTok.",
            tag="strategy",
            author=author,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            pinned=True,
            replies=[
                AnnotationReply(
                    reply_id="rep_2",
                    author=ai_author,
                    content="Based on current data, this aligns with the platform efficiency scores. Recommend prioritizing Meta and Google.",
                    created_at=now.isoformat(),
                ),
            ],
            reply_count=1,
        )
    )

    return annotations


# ── Main entry point ─────────────────────────────────────────────────────────


def build_collaborative_annotations(
    campaigns: list[dict],
    user_name: str = "",
    user_id: int = 0,
) -> CollaborativeAnnotationsResponse:
    """Build collaborative annotations dashboard."""
    if not campaigns:
        return CollaborativeAnnotationsResponse(
            summary="No campaign data available for annotations.",
        )

    annotations = _generate_sample_annotations(campaigns, user_name, user_id)

    # Stats
    by_tag: dict[str, int] = {}
    pinned = 0
    unresolved = 0
    for a in annotations:
        by_tag[a.tag] = by_tag.get(a.tag, 0) + 1
        if a.pinned:
            pinned += 1
        if not a.resolved:
            unresolved += 1

    contributors = len({a.author.user_id for a in annotations})
    active_discussions = sum(1 for a in annotations if a.reply_count > 0)

    stats = AnnotationSummary(
        total=len(annotations),
        unresolved=unresolved,
        pinned=pinned,
        by_tag=by_tag,
        recent_activity_count=len(annotations),
        contributors=contributors,
    )

    # Insights
    insights: list[AnnotationInsight] = []
    if pinned > 0:
        insights.append(
            AnnotationInsight(
                title=f"{pinned} pinned note{'s' if pinned != 1 else ''} require attention",
                description="Review pinned annotations for important decisions and action items.",
                severity="info",
            )
        )

    alert_count = by_tag.get("alert", 0)
    if alert_count > 0:
        insights.append(
            AnnotationInsight(
                title=f"{alert_count} alert{'s' if alert_count != 1 else ''} flagged",
                description="Team members have flagged issues that need review.",
                severity="warning",
            )
        )

    summary = (
        f"{len(annotations)} annotations across {len(by_tag)} categories. "
        f"{active_discussions} active discussion{'s' if active_discussions != 1 else ''}, "
        f"{pinned} pinned."
    )

    return CollaborativeAnnotationsResponse(
        summary=summary,
        annotations=annotations,
        stats=stats,
        insights=insights,
        active_discussions=active_discussions,
        team_members_active=contributors,
    )
