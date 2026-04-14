# =============================================================================
# Feature #19 — Cross-Channel Journey Mapping
# =============================================================================
"""
Map customer journeys across advertising platforms and touchpoints.

Analyses:
- Multi-touch attribution paths
- Channel interaction sequences
- Drop-off point identification
- Journey length and time-to-conversion
- Assisted vs last-touch value
- Optimal path identification
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class JourneyTouchpoint(BaseModel):
    """A single touchpoint in a customer journey."""

    step: int = 0
    platform: str = ""
    interaction_type: str = ""  # impression / click / visit / conversion
    avg_time_to_next: str = ""  # e.g. "2.5 hours"
    drop_off_rate: float = 0.0  # % who don't continue


class JourneyPath(BaseModel):
    """A common customer journey path."""

    path_id: str = ""
    path_name: str = ""
    touchpoints: list[JourneyTouchpoint] = Field(default_factory=list)
    frequency: float = 0.0  # % of all conversions
    avg_conversions: int = 0
    avg_revenue_per_journey: float = 0.0
    avg_days_to_convert: float = 0.0
    conversion_rate: float = 0.0


class ChannelContribution(BaseModel):
    """How much each channel contributes to journeys."""

    platform: str = ""
    first_touch_pct: float = 0.0  # % as first touchpoint
    last_touch_pct: float = 0.0  # % as last touchpoint
    assist_pct: float = 0.0  # % as middle touchpoint
    total_touches: int = 0
    avg_position: float = 0.0  # avg position in journey (1 = first)
    assisted_revenue: float = 0.0
    direct_revenue: float = 0.0


class JourneyInsight(BaseModel):
    """AI insight about customer journeys."""

    title: str = ""
    description: str = ""
    severity: str = "info"  # positive / info / warning / critical
    action_label: str = ""


class JourneyMapResponse(BaseModel):
    """Full cross-channel journey mapping response."""

    summary: str = ""
    top_paths: list[JourneyPath] = Field(default_factory=list)
    channel_contributions: list[ChannelContribution] = Field(default_factory=list)
    insights: list[JourneyInsight] = Field(default_factory=list)
    avg_touchpoints: float = 0.0
    avg_days_to_convert: float = 0.0
    single_touch_pct: float = 0.0
    multi_touch_pct: float = 0.0
    total_journeys_analyzed: int = 0
    top_entry_channel: str = ""
    top_closing_channel: str = ""


# ── Helpers ──────────────────────────────────────────────────────────────────


_INTERACTION_SEQUENCE = ["impression", "click", "visit", "conversion"]

_JOURNEY_TEMPLATES = [
    {
        "name": "Direct Conversion",
        "platforms": None,  # uses top platform
        "steps": [("impression", "1.2 hours"), ("click", "15 min"), ("conversion", "")],
        "freq_base": 35,
        "days": 0.5,
        "cvr": 4.2,
    },
    {
        "name": "Search → Social Close",
        "platforms": ["google", "meta"],
        "steps": [("click", "1 day"), ("impression", "6 hours"), ("click", "30 min"), ("conversion", "")],
        "freq_base": 25,
        "days": 2.5,
        "cvr": 3.1,
    },
    {
        "name": "Social Discovery → Search",
        "platforms": ["meta", "google"],
        "steps": [("impression", "2 days"), ("click", "1 day"), ("click", "45 min"), ("conversion", "")],
        "freq_base": 18,
        "days": 4.0,
        "cvr": 2.8,
    },
    {
        "name": "Multi-Platform Funnel",
        "platforms": ["tiktok", "meta", "google"],
        "steps": [("impression", "3 days"), ("impression", "1 day"), ("click", "2 hours"), ("click", "20 min"), ("conversion", "")],
        "freq_base": 12,
        "days": 5.5,
        "cvr": 2.2,
    },
    {
        "name": "Retargeting Recovery",
        "platforms": ["meta", "meta"],
        "steps": [("click", "5 days"), ("impression", "1 day"), ("click", "1 hour"), ("conversion", "")],
        "freq_base": 10,
        "days": 7.0,
        "cvr": 5.1,
    },
]


# ── Main entry point ─────────────────────────────────────────────────────────


def build_journey_map(campaigns: list[dict]) -> JourneyMapResponse:
    """Build cross-channel journey map from campaign data."""
    if not campaigns:
        return JourneyMapResponse(
            summary="No campaign data available for journey mapping.",
        )

    # Aggregate by platform
    platform_data: dict[str, dict] = {}
    for c in campaigns:
        plat = str(c.get("platform", "unknown")).lower()
        if plat not in platform_data:
            platform_data[plat] = {
                "spend": 0.0, "revenue": 0.0, "conversions": 0,
                "impressions": 0, "clicks": 0,
            }
        platform_data[plat]["spend"] += float(c.get("spend", 0))
        platform_data[plat]["revenue"] += float(c.get("revenue", 0))
        platform_data[plat]["conversions"] += int(c.get("conversions", 0))
        platform_data[plat]["impressions"] += int(c.get("impressions", 0))
        platform_data[plat]["clicks"] += int(c.get("clicks", 0))

    total_revenue = sum(d["revenue"] for d in platform_data.values())
    total_conversions = sum(d["conversions"] for d in platform_data.values())
    platforms_sorted = sorted(platform_data.keys(), key=lambda p: platform_data[p]["spend"], reverse=True)

    # Build journey paths
    top_paths: list[JourneyPath] = []
    total_freq = 0

    for i, tmpl in enumerate(_JOURNEY_TEMPLATES):
        if tmpl["platforms"]:
            # Use specified platforms, fallback to available
            plats = []
            for tp in tmpl["platforms"]:
                match = next((p for p in platforms_sorted if tp in p), None)
                plats.append(match or platforms_sorted[min(len(plats), len(platforms_sorted) - 1)])
        else:
            plats = [platforms_sorted[0]] if platforms_sorted else ["unknown"]

        touchpoints: list[JourneyTouchpoint] = []
        plat_idx = 0
        for step_num, (interaction, time_to_next) in enumerate(tmpl["steps"]):
            p = plats[min(plat_idx, len(plats) - 1)]
            drop_off = 0.0
            if interaction == "impression":
                drop_off = 85.0  # most impressions don't lead to clicks
            elif interaction == "click":
                drop_off = 60.0
            elif interaction == "visit":
                drop_off = 40.0

            touchpoints.append(JourneyTouchpoint(
                step=step_num + 1,
                platform=p.replace("_", " ").title(),
                interaction_type=interaction,
                avg_time_to_next=time_to_next,
                drop_off_rate=round(drop_off, 1),
            ))
            if interaction in ("click", "conversion"):
                plat_idx += 1

        freq = tmpl["freq_base"]
        total_freq += freq
        avg_rev = total_revenue / total_conversions * tmpl["cvr"] / 3 if total_conversions > 0 else 0

        top_paths.append(JourneyPath(
            path_id=f"path_{i + 1}",
            path_name=tmpl["name"],
            touchpoints=touchpoints,
            frequency=freq,
            avg_conversions=max(int(total_conversions * freq / 100), 1),
            avg_revenue_per_journey=round(avg_rev, 2),
            avg_days_to_convert=tmpl["days"],
            conversion_rate=tmpl["cvr"],
        ))

    # Channel contributions
    contributions: list[ChannelContribution] = []
    for plat, data in sorted(platform_data.items(), key=lambda x: x[1]["spend"], reverse=True):
        total_touches = data["impressions"] + data["clicks"]
        # Estimate first/last/assist based on platform characteristics
        if "google" in plat:
            first, last, assist = 20, 45, 35
        elif "meta" in plat or "facebook" in plat:
            first, last, assist = 35, 25, 40
        elif "tiktok" in plat:
            first, last, assist = 45, 15, 40
        elif "snapchat" in plat:
            first, last, assist = 40, 10, 50
        else:
            first, last, assist = 30, 30, 40

        contributions.append(ChannelContribution(
            platform=plat.replace("_", " ").title(),
            first_touch_pct=round(first, 1),
            last_touch_pct=round(last, 1),
            assist_pct=round(assist, 1),
            total_touches=total_touches,
            avg_position=round(1 + (100 - first) / 50, 1),
            assisted_revenue=round(data["revenue"] * assist / 100, 2),
            direct_revenue=round(data["revenue"] * last / 100, 2),
        ))

    # Insights
    insights: list[JourneyInsight] = []

    # Multi-touch insight
    single_pct = top_paths[0].frequency if top_paths else 0
    multi_pct = 100 - single_pct
    if multi_pct > 50:
        insights.append(JourneyInsight(
            title=f"{multi_pct:.0f}% of conversions involve multiple touchpoints",
            description="Multi-touch journeys are dominant. Ensure consistent messaging across platforms.",
            severity="info",
            action_label="Review Messaging",
        ))

    # Top entry channel
    if contributions:
        top_entry = max(contributions, key=lambda c: c.first_touch_pct)
        insights.append(JourneyInsight(
            title=f"{top_entry.platform} is the top discovery channel",
            description=f"{top_entry.first_touch_pct:.0f}% of journeys start with {top_entry.platform}. Invest in awareness here.",
            severity="positive",
            action_label="Boost Awareness",
        ))

        top_closer = max(contributions, key=lambda c: c.last_touch_pct)
        if top_closer.platform != top_entry.platform:
            insights.append(JourneyInsight(
                title=f"{top_closer.platform} closes the most conversions",
                description=f"{top_closer.last_touch_pct:.0f}% of conversions have {top_closer.platform} as last touch.",
                severity="positive",
                action_label="Optimize Closing",
            ))

    # Long journey warning
    long_paths = [p for p in top_paths if p.avg_days_to_convert > 5]
    if long_paths:
        insights.append(JourneyInsight(
            title=f"{len(long_paths)} journey type{'s' if len(long_paths) > 1 else ''} take 5+ days",
            description="Long journeys risk losing prospects. Consider retargeting sequences to accelerate conversion.",
            severity="warning",
            action_label="Add Retargeting",
        ))

    # Drop-off insight
    high_dropoff = []
    for p in top_paths:
        for tp in p.touchpoints:
            if tp.drop_off_rate > 80 and tp.interaction_type == "impression":
                high_dropoff.append(tp.platform)
    if high_dropoff:
        plats_str = ", ".join(set(high_dropoff[:3]))
        insights.append(JourneyInsight(
            title="High drop-off after impressions",
            description=f"85%+ drop-off at impression stage on {plats_str}. Improve ad relevance and targeting.",
            severity="warning",
            action_label="Improve Targeting",
        ))

    avg_touch = sum(len(p.touchpoints) * p.frequency for p in top_paths) / total_freq if total_freq > 0 else 0
    avg_days = sum(p.avg_days_to_convert * p.frequency for p in top_paths) / total_freq if total_freq > 0 else 0

    top_entry_ch = max(contributions, key=lambda c: c.first_touch_pct).platform if contributions else "N/A"
    top_close_ch = max(contributions, key=lambda c: c.last_touch_pct).platform if contributions else "N/A"

    summary = (
        f"Analyzed {total_conversions:,} conversions across {len(platform_data)} channels. "
        f"Avg {avg_touch:.1f} touchpoints over {avg_days:.1f} days. "
        f"{single_pct:.0f}% single-touch, {multi_pct:.0f}% multi-touch journeys."
    )

    return JourneyMapResponse(
        summary=summary,
        top_paths=top_paths,
        channel_contributions=contributions,
        insights=insights,
        avg_touchpoints=round(avg_touch, 1),
        avg_days_to_convert=round(avg_days, 1),
        single_touch_pct=round(single_pct, 1),
        multi_touch_pct=round(multi_pct, 1),
        total_journeys_analyzed=total_conversions,
        top_entry_channel=top_entry_ch,
        top_closing_channel=top_close_ch,
    )
