# =============================================================================
# Cross-Platform Budget Optimizer — Feature #9
# =============================================================================
"""
Cross-Platform Budget Optimizer — analyzes performance across all ad platforms
to recommend optimal budget distribution. Identifies which platforms to scale,
reduce, or shift spend between based on efficiency metrics.

Architecture:
1. Aggregates campaigns by platform
2. Scores each platform on efficiency (ROAS, CPA, volume)
3. Computes optimal allocation vs current allocation
4. Generates platform-level shift recommendations
5. Simulates projected outcomes of reallocation

Builds on: budget.py, scoring.py, predictive_budget.py, pacing
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class PlatformEfficiency(BaseModel):
    """Efficiency metrics for a single platform."""
    platform: str
    campaigns: int
    current_spend: float
    current_revenue: float
    roas: float
    cpa: float
    conversions: int
    spend_share_pct: float  # current % of total spend
    efficiency_score: float  # 0-100 composite
    efficiency_rank: int


class AllocationShift(BaseModel):
    """A recommended budget shift between platforms."""
    from_platform: str
    to_platform: str
    shift_amount: float
    shift_pct: float  # % of total budget
    reasoning: str


class PlatformRecommendation(BaseModel):
    """Budget recommendation for a single platform."""
    platform: str
    current_spend: float
    recommended_spend: float
    change_amount: float
    change_pct: float
    action: Literal["scale", "reduce", "maintain"]
    reasoning: str
    projected_roas: float
    projected_revenue: float
    confidence: float  # 0-1


class OptimizationScenario(BaseModel):
    """A what-if scenario for budget distribution."""
    name: str
    description: str
    allocations: Dict[str, float]  # platform -> spend
    projected_revenue: float
    projected_roas: float
    projected_conversions: int
    improvement_pct: float  # vs current


class CrossPlatformOptimizerResponse(BaseModel):
    """Full cross-platform optimizer response."""
    summary: str
    strategy: Literal["roas_max", "balanced", "volume_max"]
    total_budget: float
    current_roas: float
    optimized_roas: float
    roas_improvement_pct: float
    platforms: List[PlatformEfficiency] = []
    recommendations: List[PlatformRecommendation] = []
    shifts: List[AllocationShift] = []
    scenarios: List[OptimizationScenario] = []
    total_campaigns: int = 0
    platforms_count: int = 0
    reallocation_amount: float = 0.0
    reallocation_pct: float = 0.0


# ── Scoring ──────────────────────────────────────────────────────────────────

def _compute_efficiency_score(
    roas: float,
    cpa: float,
    conversions: int,
    avg_roas: float,
    avg_cpa: float,
) -> float:
    """Compute platform efficiency score (0-100)."""
    score = 50.0  # baseline

    # ROAS contribution (50% weight)
    if avg_roas > 0:
        roas_ratio = roas / avg_roas
        score += (roas_ratio - 1.0) * 25  # +25 per 100% above avg

    # CPA contribution (30% weight, inverted — lower is better)
    if avg_cpa > 0 and cpa > 0:
        cpa_ratio = avg_cpa / cpa  # inverted
        score += (cpa_ratio - 1.0) * 15

    # Volume contribution (20% weight)
    if conversions >= 50:
        score += 10
    elif conversions >= 20:
        score += 5
    elif conversions < 5:
        score -= 10

    return max(0, min(100, round(score, 1)))


def _compute_optimal_allocation(
    platforms: List[PlatformEfficiency],
    total_budget: float,
    strategy: str,
) -> Dict[str, float]:
    """Compute optimal budget allocation across platforms."""
    if not platforms:
        return {}

    if strategy == "roas_max":
        # Weight by efficiency score (ROAS-focused)
        weights = {p.platform: max(p.efficiency_score, 5) for p in platforms}
    elif strategy == "volume_max":
        # Weight by conversion volume + efficiency
        weights = {
            p.platform: max(p.conversions * 0.5 + p.efficiency_score * 0.5, 5)
            for p in platforms
        }
    else:  # balanced
        # Equal weight to efficiency and current share
        weights = {
            p.platform: max(p.efficiency_score * 0.6 + p.spend_share_pct * 0.4, 5)
            for p in platforms
        }

    total_weight = sum(weights.values())
    allocation = {
        plat: round(total_budget * (w / total_weight), 2)
        for plat, w in weights.items()
    }
    return allocation


def _generate_shifts(
    platforms: List[PlatformEfficiency],
    optimal: Dict[str, float],
    total_budget: float,
) -> List[AllocationShift]:
    """Generate platform-to-platform shift recommendations."""
    shifts = []
    current_map = {p.platform: p.current_spend for p in platforms}
    eff_map = {p.platform: p for p in platforms}

    # Find platforms to reduce (current > optimal)
    reducers = []
    scalers = []
    for plat, opt_spend in optimal.items():
        curr = current_map.get(plat, 0)
        diff = opt_spend - curr
        if diff < -50:  # reduce threshold
            reducers.append((plat, abs(diff)))
        elif diff > 50:  # scale threshold
            scalers.append((plat, diff))

    # Sort: reduce from least efficient, scale to most efficient
    reducers.sort(key=lambda x: eff_map.get(x[0], PlatformEfficiency(
        platform="", campaigns=0, current_spend=0, current_revenue=0,
        roas=0, cpa=0, conversions=0, spend_share_pct=0,
        efficiency_score=0, efficiency_rank=0,
    )).efficiency_score)
    scalers.sort(key=lambda x: -eff_map.get(x[0], PlatformEfficiency(
        platform="", campaigns=0, current_spend=0, current_revenue=0,
        roas=0, cpa=0, conversions=0, spend_share_pct=0,
        efficiency_score=0, efficiency_rank=0,
    )).efficiency_score)

    for from_plat, from_amt in reducers:
        for to_plat, to_amt in scalers:
            shift = min(from_amt, to_amt)
            if shift < 50:
                continue
            from_eff = eff_map.get(from_plat)
            to_eff = eff_map.get(to_plat)
            if not from_eff or not to_eff:
                continue

            shifts.append(AllocationShift(
                from_platform=from_plat,
                to_platform=to_plat,
                shift_amount=round(shift, 2),
                shift_pct=round(shift / total_budget * 100, 1) if total_budget > 0 else 0,
                reasoning=(
                    f"Shift ${shift:,.0f} from {from_plat} ({from_eff.roas:.2f}x ROAS) "
                    f"to {to_plat} ({to_eff.roas:.2f}x ROAS) for better returns."
                ),
            ))
            break  # one shift per reducer

    return shifts[:5]


def _build_scenarios(
    platforms: List[PlatformEfficiency],
    total_budget: float,
    current_revenue: float,
    current_roas: float,
) -> List[OptimizationScenario]:
    """Build what-if optimization scenarios."""
    scenarios = []
    eff_map = {p.platform: p for p in platforms}

    def project(alloc: Dict[str, float]) -> tuple:
        rev = sum(
            alloc.get(p.platform, 0) * p.roas
            for p in platforms
        )
        spend = sum(alloc.values())
        roas = rev / spend if spend > 0 else 0
        convs = int(sum(
            alloc.get(p.platform, 0) / max(p.cpa, 0.01)
            for p in platforms
            if p.cpa > 0
        ))
        improvement = ((rev - current_revenue) / current_revenue * 100) if current_revenue > 0 else 0
        return round(rev, 2), round(roas, 2), convs, round(improvement, 1)

    # Scenario 1: ROAS-optimized
    roas_alloc = _compute_optimal_allocation(platforms, total_budget, "roas_max")
    rev, roas, convs, imp = project(roas_alloc)
    scenarios.append(OptimizationScenario(
        name="ROAS Maximized",
        description="Allocate more to highest-ROAS platforms.",
        allocations=roas_alloc,
        projected_revenue=rev,
        projected_roas=roas,
        projected_conversions=convs,
        improvement_pct=imp,
    ))

    # Scenario 2: Volume-optimized
    vol_alloc = _compute_optimal_allocation(platforms, total_budget, "volume_max")
    rev, roas, convs, imp = project(vol_alloc)
    scenarios.append(OptimizationScenario(
        name="Volume Maximized",
        description="Prioritize platforms with highest conversion volume.",
        allocations=vol_alloc,
        projected_revenue=rev,
        projected_roas=roas,
        projected_conversions=convs,
        improvement_pct=imp,
    ))

    # Scenario 3: Equal distribution
    n = len(platforms)
    if n > 0:
        equal_alloc = {p.platform: round(total_budget / n, 2) for p in platforms}
        rev, roas, convs, imp = project(equal_alloc)
        scenarios.append(OptimizationScenario(
            name="Equal Distribution",
            description="Split budget equally across all platforms.",
            allocations=equal_alloc,
            projected_revenue=rev,
            projected_roas=roas,
            projected_conversions=convs,
            improvement_pct=imp,
        ))

    return scenarios


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_cross_platform_optimizer(
    campaigns: List[Dict],
    strategy: str = "balanced",
) -> CrossPlatformOptimizerResponse:
    """
    Main entry point: analyzes campaigns across platforms and generates
    optimal cross-platform budget distribution recommendations.

    Args:
        campaigns: List of campaign dicts with id, name, platform,
                   spend, revenue, conversions
        strategy: Optimization strategy — "roas_max", "balanced", "volume_max"

    Returns:
        CrossPlatformOptimizerResponse with recommendations and scenarios
    """
    if not campaigns:
        return CrossPlatformOptimizerResponse(
            summary="No campaigns available for cross-platform optimization.",
            strategy=strategy,
            total_budget=0,
            current_roas=0,
            optimized_roas=0,
            roas_improvement_pct=0,
        )

    # Aggregate by platform
    plat_data: Dict[str, Dict] = {}
    for c in campaigns:
        plat = c.get("platform", "Unknown")
        if plat not in plat_data:
            plat_data[plat] = {"spend": 0, "revenue": 0, "conversions": 0, "campaigns": 0}
        plat_data[plat]["spend"] += c.get("spend", 0)
        plat_data[plat]["revenue"] += c.get("revenue", 0)
        plat_data[plat]["conversions"] += c.get("conversions", 0)
        plat_data[plat]["campaigns"] += 1

    total_spend = sum(d["spend"] for d in plat_data.values())
    total_revenue = sum(d["revenue"] for d in plat_data.values())
    total_conversions = sum(d["conversions"] for d in plat_data.values())
    current_roas = total_revenue / total_spend if total_spend > 0 else 0

    # Portfolio averages
    n_platforms = len(plat_data)
    avg_roas = current_roas
    avg_cpa = total_spend / total_conversions if total_conversions > 0 else 0

    # Build platform efficiency metrics
    platforms: List[PlatformEfficiency] = []
    for plat, data in plat_data.items():
        spend = data["spend"]
        revenue = data["revenue"]
        conversions = data["conversions"]
        roas = revenue / spend if spend > 0 else 0
        cpa = spend / conversions if conversions > 0 else 0
        share = (spend / total_spend * 100) if total_spend > 0 else 0

        eff_score = _compute_efficiency_score(roas, cpa, conversions, avg_roas, avg_cpa)

        platforms.append(PlatformEfficiency(
            platform=plat,
            campaigns=data["campaigns"],
            current_spend=round(spend, 2),
            current_revenue=round(revenue, 2),
            roas=round(roas, 2),
            cpa=round(cpa, 2),
            conversions=conversions,
            spend_share_pct=round(share, 1),
            efficiency_score=eff_score,
            efficiency_rank=0,
        ))

    # Rank by efficiency
    platforms.sort(key=lambda p: -p.efficiency_score)
    for i, p in enumerate(platforms):
        p.efficiency_rank = i + 1

    # Compute optimal allocation
    optimal = _compute_optimal_allocation(platforms, total_spend, strategy)

    # Generate recommendations per platform
    recommendations: List[PlatformRecommendation] = []
    for p in platforms:
        opt_spend = optimal.get(p.platform, p.current_spend)
        change = opt_spend - p.current_spend
        change_pct = (change / p.current_spend * 100) if p.current_spend > 0 else 0

        # Limit changes (guardrails)
        max_increase = p.current_spend * 0.30  # max 30% increase
        max_decrease = p.current_spend * 0.20  # max 20% decrease
        if change > max_increase:
            change = max_increase
            opt_spend = p.current_spend + change
            change_pct = 30.0
        elif change < -max_decrease:
            change = -max_decrease
            opt_spend = p.current_spend + change
            change_pct = -20.0

        if change_pct > 5:
            action = "scale"
        elif change_pct < -5:
            action = "reduce"
        else:
            action = "maintain"

        # Projected metrics
        proj_roas = p.roas  # assume same efficiency
        proj_revenue = opt_spend * proj_roas

        # Confidence based on data volume
        conf = min(1.0, p.conversions / 30) * 0.5 + min(1.0, p.current_spend / 500) * 0.3 + 0.2

        # Reasoning
        if action == "scale":
            reasoning = (
                f"{p.platform} is #{p.efficiency_rank} in efficiency ({p.efficiency_score:.0f}/100) "
                f"with {p.roas:.2f}x ROAS. Increasing budget by {abs(change_pct):.0f}% "
                f"should generate additional ${abs(change) * p.roas:,.0f} in revenue."
            )
        elif action == "reduce":
            reasoning = (
                f"{p.platform} is underperforming at {p.roas:.2f}x ROAS "
                f"(efficiency: {p.efficiency_score:.0f}/100). Redirect "
                f"${abs(change):,.0f} to higher-performing platforms."
            )
        else:
            reasoning = (
                f"{p.platform} is performing at expected levels ({p.roas:.2f}x ROAS). "
                f"Maintain current allocation."
            )

        recommendations.append(PlatformRecommendation(
            platform=p.platform,
            current_spend=p.current_spend,
            recommended_spend=round(opt_spend, 2),
            change_amount=round(change, 2),
            change_pct=round(change_pct, 1),
            action=action,
            reasoning=reasoning,
            projected_roas=round(proj_roas, 2),
            projected_revenue=round(proj_revenue, 2),
            confidence=round(conf, 2),
        ))

    recommendations.sort(key=lambda r: -abs(r.change_pct))

    # Generate shifts
    shifts = _generate_shifts(platforms, optimal, total_spend)

    # Build scenarios
    scenarios = _build_scenarios(platforms, total_spend, total_revenue, current_roas)

    # Calculate optimized ROAS (from balanced scenario)
    optimized_revenue = sum(
        optimal.get(p.platform, p.current_spend) * p.roas
        for p in platforms
    )
    optimized_roas = optimized_revenue / total_spend if total_spend > 0 else 0
    roas_improvement = ((optimized_roas - current_roas) / current_roas * 100) if current_roas > 0 else 0

    realloc_amount = sum(abs(r.change_amount) for r in recommendations) / 2  # divide by 2 since shifts are paired
    realloc_pct = (realloc_amount / total_spend * 100) if total_spend > 0 else 0

    # Summary
    summary = _build_summary(
        platforms, recommendations, current_roas, optimized_roas,
        roas_improvement, realloc_amount, strategy,
    )

    return CrossPlatformOptimizerResponse(
        summary=summary,
        strategy=strategy,
        total_budget=round(total_spend, 2),
        current_roas=round(current_roas, 2),
        optimized_roas=round(optimized_roas, 2),
        roas_improvement_pct=round(roas_improvement, 1),
        platforms=platforms,
        recommendations=recommendations,
        shifts=shifts,
        scenarios=scenarios,
        total_campaigns=len(campaigns),
        platforms_count=n_platforms,
        reallocation_amount=round(realloc_amount, 2),
        reallocation_pct=round(realloc_pct, 1),
    )


def _build_summary(
    platforms: List[PlatformEfficiency],
    recommendations: List[PlatformRecommendation],
    current_roas: float,
    optimized_roas: float,
    improvement: float,
    realloc_amount: float,
    strategy: str,
) -> str:
    """Build executive summary."""
    parts = []

    strategy_labels = {"roas_max": "ROAS maximization", "balanced": "balanced", "volume_max": "volume maximization"}
    parts.append(
        f"Analyzing {len(platforms)} platform{'s' if len(platforms) > 1 else ''} "
        f"using {strategy_labels.get(strategy, strategy)} strategy."
    )

    scale_count = sum(1 for r in recommendations if r.action == "scale")
    reduce_count = sum(1 for r in recommendations if r.action == "reduce")

    if scale_count > 0:
        parts.append(f"{scale_count} platform{'s' if scale_count > 1 else ''} recommended for scaling.")
    if reduce_count > 0:
        parts.append(f"{reduce_count} platform{'s' if reduce_count > 1 else ''} recommended for reduction.")

    if improvement > 0:
        parts.append(
            f"Projected ROAS improvement: {current_roas:.2f}x → {optimized_roas:.2f}x "
            f"(+{improvement:.1f}%) with ${realloc_amount:,.0f} reallocation."
        )
    elif improvement == 0:
        parts.append("Current allocation is near optimal — no significant changes needed.")

    return " ".join(parts)
