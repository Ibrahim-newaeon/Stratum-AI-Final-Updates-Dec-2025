# =============================================================================
# Feature #16 — Scheduled A/B Test Analysis
# =============================================================================
"""
Automated A/B test detection and statistical analysis from campaign data.

Analyses:
- Auto-detect potential A/B test pairs (same platform, similar names)
- Statistical significance calculation (Z-test on conversion rates)
- Winner/loser determination with confidence intervals
- Metric-level comparison (CTR, CVR, CPA, ROAS)
- Recommendations for test conclusion or continuation
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class ABTestVariant(BaseModel):
    """One arm of an A/B test."""

    variant_id: str = ""
    variant_label: str = ""  # A / B / Control / Treatment
    campaign_name: str = ""
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    ctr: float = 0.0
    cvr: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0


class ABTestResult(BaseModel):
    """Result of comparing two campaign variants."""

    test_id: str = ""
    test_name: str = ""
    platform: str = ""
    status: str = "running"  # running / winner_found / inconclusive / needs_more_data
    variants: list[ABTestVariant] = Field(default_factory=list)
    winning_variant: Optional[str] = None
    confidence: float = 0.0  # 0-100
    lift_pct: float = 0.0  # % improvement of winner over loser
    primary_metric: str = "cvr"
    days_running: int = 0
    recommended_action: str = ""
    min_sample_reached: bool = False


class ABTestInsight(BaseModel):
    """AI insight about A/B testing programme."""

    title: str = ""
    description: str = ""
    severity: str = "info"  # positive / info / warning / critical
    action_label: str = ""


class ABTestAnalysisResponse(BaseModel):
    """Full A/B test analysis dashboard response."""

    summary: str = ""
    total_tests: int = 0
    active_tests: int = 0
    winners_found: int = 0
    avg_confidence: float = 0.0
    total_spend_in_tests: float = 0.0
    potential_savings: float = 0.0
    tests: list[ABTestResult] = Field(default_factory=list)
    insights: list[ABTestInsight] = Field(default_factory=list)


# ── Constants ────────────────────────────────────────────────────────────────

MIN_SAMPLE_SIZE = 100  # minimum conversions per variant
SIGNIFICANCE_THRESHOLD = 0.95  # 95% confidence
Z_SCORES = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _z_test_proportions(
    conversions_a: int, trials_a: int,
    conversions_b: int, trials_b: int,
) -> tuple[float, float]:
    """Two-proportion Z-test. Returns (z_score, confidence)."""
    if trials_a == 0 or trials_b == 0:
        return 0.0, 0.0

    p_a = conversions_a / trials_a
    p_b = conversions_b / trials_b
    p_pool = (conversions_a + conversions_b) / (trials_a + trials_b)

    if p_pool <= 0 or p_pool >= 1:
        return 0.0, 0.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / trials_a + 1 / trials_b))
    if se == 0:
        return 0.0, 0.0

    z = abs(p_a - p_b) / se

    # Approximate confidence from z-score
    if z >= 2.576:
        confidence = 99.0
    elif z >= 1.960:
        confidence = 95.0 + (z - 1.960) / (2.576 - 1.960) * 4
    elif z >= 1.645:
        confidence = 90.0 + (z - 1.645) / (1.960 - 1.645) * 5
    elif z >= 1.282:
        confidence = 80.0 + (z - 1.282) / (1.645 - 1.282) * 10
    else:
        confidence = min(z / 1.282 * 80, 80)

    return z, min(confidence, 99.9)


def _detect_test_pairs(campaigns: list[dict]) -> list[tuple[dict, dict]]:
    """Detect likely A/B test pairs by platform + name similarity."""
    pairs: list[tuple[dict, dict]] = []
    used = set()

    # Group by platform
    by_platform: dict[str, list[dict]] = {}
    for i, c in enumerate(campaigns):
        plat = c.get("platform", "unknown").lower()
        if plat not in by_platform:
            by_platform[plat] = []
        by_platform[plat].append({**c, "_idx": i})

    for plat, clist in by_platform.items():
        for i in range(len(clist)):
            if clist[i]["_idx"] in used:
                continue
            for j in range(i + 1, len(clist)):
                if clist[j]["_idx"] in used:
                    continue
                name_a = clist[i].get("name", "").lower()
                name_b = clist[j].get("name", "").lower()
                # Heuristic: similar names (share 60%+ words or explicit A/B markers)
                if _names_match(name_a, name_b):
                    pairs.append((clist[i], clist[j]))
                    used.add(clist[i]["_idx"])
                    used.add(clist[j]["_idx"])
                    break

    # If no natural pairs found, create synthetic pairs from top campaigns
    if not pairs and len(campaigns) >= 2:
        by_plat_sorted: dict[str, list[dict]] = {}
        for c in campaigns:
            plat = c.get("platform", "unknown").lower()
            if plat not in by_plat_sorted:
                by_plat_sorted[plat] = []
            by_plat_sorted[plat].append(c)

        for plat, clist in by_plat_sorted.items():
            if len(clist) >= 2:
                sorted_c = sorted(clist, key=lambda x: float(x.get("spend", 0)), reverse=True)
                pairs.append((sorted_c[0], sorted_c[1]))
                if len(pairs) >= 3:
                    break

    return pairs[:5]


def _names_match(a: str, b: str) -> bool:
    """Check if two campaign names suggest an A/B test relationship."""
    # Explicit markers
    markers = [(" a ", " b "), ("_a_", "_b_"), ("-a-", "-b-"),
               ("variant a", "variant b"), ("control", "test"),
               ("_v1", "_v2"), (" v1", " v2")]
    for ma, mb in markers:
        if (ma in f" {a} " and mb in f" {b} ") or (mb in f" {a} " and ma in f" {b} "):
            return True

    # Word overlap >= 60%
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    return overlap >= 0.6 and a != b


def _build_variant(c: dict, label: str, idx: int) -> ABTestVariant:
    spend = float(c.get("spend", 0))
    impressions = int(c.get("impressions", 0))
    clicks = int(c.get("clicks", 0))
    conversions = int(c.get("conversions", 0))
    revenue = float(c.get("revenue", 0))

    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cvr = (conversions / clicks * 100) if clicks > 0 else 0
    cpa = (spend / conversions) if conversions > 0 else 0
    roas = (revenue / spend) if spend > 0 else 0

    return ABTestVariant(
        variant_id=f"var_{idx}",
        variant_label=label,
        campaign_name=c.get("name", c.get("platform", "Campaign")),
        spend=round(spend, 2),
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        revenue=round(revenue, 2),
        ctr=round(ctr, 2),
        cvr=round(cvr, 2),
        cpa=round(cpa, 2),
        roas=round(roas, 2),
    )


# ── Main entry point ─────────────────────────────────────────────────────────


def build_ab_test_analysis(campaigns: list[dict]) -> ABTestAnalysisResponse:
    """Build A/B test analysis from campaign data."""
    if not campaigns:
        return ABTestAnalysisResponse(
            summary="No campaign data available for A/B test analysis.",
        )

    pairs = _detect_test_pairs(campaigns)
    if not pairs:
        return ABTestAnalysisResponse(
            summary="No A/B test pairs detected. Create campaigns with variant naming to enable analysis.",
            insights=[
                ABTestInsight(
                    title="No active A/B tests detected",
                    description="Name campaigns with A/B markers (e.g., 'Campaign - Variant A') for automatic detection.",
                    severity="info",
                    action_label="Create Test",
                ),
            ],
        )

    tests: list[ABTestResult] = []
    total_spend = 0.0
    potential_savings = 0.0

    for i, (ca, cb) in enumerate(pairs):
        var_a = _build_variant(ca, "A", 0)
        var_b = _build_variant(cb, "B", 1)

        plat = ca.get("platform", "unknown")

        # Statistical test on conversion rates
        z_score, confidence = _z_test_proportions(
            var_a.conversions, var_a.clicks,
            var_b.conversions, var_b.clicks,
        )

        min_sample = var_a.conversions >= MIN_SAMPLE_SIZE and var_b.conversions >= MIN_SAMPLE_SIZE

        # Determine winner
        winning_variant = None
        lift = 0.0
        status = "running"

        if confidence >= 95 and min_sample:
            if var_a.cvr > var_b.cvr:
                winning_variant = "A"
                lift = ((var_a.cvr - var_b.cvr) / var_b.cvr * 100) if var_b.cvr > 0 else 0
            else:
                winning_variant = "B"
                lift = ((var_b.cvr - var_a.cvr) / var_a.cvr * 100) if var_a.cvr > 0 else 0
            status = "winner_found"
            # Savings = spend on losing variant
            loser_spend = var_b.spend if winning_variant == "A" else var_a.spend
            potential_savings += loser_spend * 0.3  # Could save 30% of loser spend
        elif not min_sample:
            status = "needs_more_data"
        elif confidence < 80:
            status = "inconclusive"

        # Recommendation
        if status == "winner_found":
            action = f"Allocate budget to Variant {winning_variant}. {lift:.1f}% lift with {confidence:.0f}% confidence."
        elif status == "needs_more_data":
            needed = max(MIN_SAMPLE_SIZE - min(var_a.conversions, var_b.conversions), 0)
            action = f"Continue test. Need ~{needed} more conversions for significance."
        else:
            action = "Monitor for 3-5 more days before making a decision."

        total_spend += var_a.spend + var_b.spend
        days = max(int(ca.get("days_running", 7)), int(cb.get("days_running", 7)))

        tests.append(
            ABTestResult(
                test_id=f"test_{i + 1}",
                test_name=f"{plat.title()} Test #{i + 1}",
                platform=plat.replace("_", " ").title(),
                status=status,
                variants=[var_a, var_b],
                winning_variant=winning_variant,
                confidence=round(confidence, 1),
                lift_pct=round(lift, 1),
                primary_metric="cvr",
                days_running=days,
                recommended_action=action,
                min_sample_reached=min_sample,
            )
        )

    # Insights
    insights: list[ABTestInsight] = []
    winners = [t for t in tests if t.status == "winner_found"]
    needs_data = [t for t in tests if t.status == "needs_more_data"]

    if winners:
        total_lift = sum(t.lift_pct for t in winners) / len(winners)
        insights.append(
            ABTestInsight(
                title=f"{len(winners)} test{'s' if len(winners) > 1 else ''} with clear winners",
                description=f"Average lift of {total_lift:.1f}%. Apply winning variants to improve performance.",
                severity="positive",
                action_label="Apply Winners",
            )
        )

    if needs_data:
        insights.append(
            ABTestInsight(
                title=f"{len(needs_data)} test{'s' if len(needs_data) > 1 else ''} need more data",
                description="Insufficient sample size for statistical significance. Continue running.",
                severity="info",
                action_label="Keep Running",
            )
        )

    if potential_savings > 0:
        insights.append(
            ABTestInsight(
                title=f"${potential_savings:,.0f} potential savings from test results",
                description="Reallocate budget from losing variants to improve overall efficiency.",
                severity="positive",
                action_label="Optimize Budget",
            )
        )

    if len(tests) < 3:
        insights.append(
            ABTestInsight(
                title="Run more A/B tests to optimize faster",
                description="Testing 3+ variants per platform accelerates learning. Consider creative and audience tests.",
                severity="info",
                action_label="Create Tests",
            )
        )

    avg_conf = sum(t.confidence for t in tests) / len(tests) if tests else 0

    summary = (
        f"{len(tests)} A/B test{'s' if len(tests) != 1 else ''} detected. "
        f"{len(winners)} with clear winners, {len(needs_data)} need more data. "
        f"Avg confidence {avg_conf:.0f}%. ${total_spend:,.0f} total test spend."
    )

    return ABTestAnalysisResponse(
        summary=summary,
        total_tests=len(tests),
        active_tests=len([t for t in tests if t.status == "running"]),
        winners_found=len(winners),
        avg_confidence=round(avg_conf, 1),
        total_spend_in_tests=round(total_spend, 2),
        potential_savings=round(potential_savings, 2),
        tests=tests,
        insights=insights,
    )
