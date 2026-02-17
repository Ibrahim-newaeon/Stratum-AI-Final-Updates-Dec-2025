# =============================================================================
# Creative Fatigue Score Calculator
# =============================================================================
"""
Creative Fatigue Score.
From AI_Logic_Formulas_Pseudocode.md Section 3.

Goal: Detect when a creative is losing efficiency due to overexposure.

Interpretation:
- fatigue >= 0.65: refresh creative (new hook/visual)
- 0.45..0.65: watch, rotate variants
- < 0.45: healthy
"""

from typing import Optional
from app.analytics.logic.types import (
    EntityMetrics,
    BaselineMetrics,
    FatigueParams,
    FatigueResult,
    FatigueState,
)
from app.analytics.logic.scoring import clamp01


def ema(current: float, prev: float, alpha: float = 0.4) -> float:
    """Exponential moving average."""
    return alpha * current + (1 - alpha) * prev


def creative_fatigue(
    today: EntityMetrics,
    baseline: BaselineMetrics,
    params: Optional[FatigueParams] = None,
    prev_ema: Optional[float] = None,
) -> FatigueResult:
    """
    Calculate creative fatigue score.

    Signals (typical patterns: CTR down, CPA up, ROAS down, frequency up)

    Args:
        today: Today's metrics for the creative
        baseline: Baseline metrics (last 7 days average)
        params: Fatigue calculation parameters
        prev_ema: Previous EMA value for smoothing

    Returns:
        FatigueResult with score, state, and recommendations
    """
    if params is None:
        params = FatigueParams()

    # Calculate signal drops
    # CTR drop
    if baseline.ctr > 0.0001:
        ctr_drop = clamp01((baseline.ctr - today.ctr) / baseline.ctr)
    else:
        ctr_drop = 0.0

    # ROAS drop
    if baseline.roas > 0.01:
        roas_drop = clamp01((baseline.roas - today.roas) / baseline.roas)
    else:
        roas_drop = 0.0

    # CPA rise (higher is worse)
    if baseline.cpa > 0.01:
        cpa_rise = clamp01((today.cpa - baseline.cpa) / baseline.cpa)
    else:
        cpa_rise = 0.0

    # Exposure factor (frequency based)
    # frequency 2->5 maps to 0..1
    if today.frequency and today.frequency > 0:
        exposure_factor = clamp01((today.frequency - 2.0) / 3.0)
    else:
        exposure_factor = 0.0

    # Calculate raw fatigue score
    fatigue = (
        params.ctr_weight * ctr_drop +
        params.roas_weight * roas_drop +
        params.cpa_weight * cpa_rise +
        params.exposure_weight * exposure_factor
    )

    # Smooth with EMA to avoid noise
    if prev_ema is not None:
        smoothed_fatigue = ema(fatigue, prev_ema, params.ema_alpha)
    else:
        smoothed_fatigue = fatigue

    # Determine state
    if smoothed_fatigue >= params.refresh_threshold:
        state = FatigueState.REFRESH
    elif smoothed_fatigue >= params.watch_threshold:
        state = FatigueState.WATCH
    else:
        state = FatigueState.HEALTHY

    # Generate recommendations
    recommendations = []
    if state == FatigueState.REFRESH:
        recommendations.append("Refresh creative immediately - create new hook/visual")
        if ctr_drop > 0.3:
            recommendations.append(f"CTR dropped {ctr_drop*100:.0f}% - test new headlines")
        if roas_drop > 0.3:
            recommendations.append(f"ROAS dropped {roas_drop*100:.0f}% - review offer/CTA")
        if exposure_factor > 0.5:
            recommendations.append(f"High frequency ({today.frequency:.1f}) - expand audience")
    elif state == FatigueState.WATCH:
        recommendations.append("Monitor closely - prepare backup creatives")
        recommendations.append("Consider A/B testing new variants")
    else:
        recommendations.append("Creative performing well - no action needed")

    return FatigueResult(
        creative_id=today.entity_id,
        creative_name=today.entity_name,
        fatigue_score=round(smoothed_fatigue, 4),
        state=state,
        ctr_drop=round(ctr_drop, 4),
        roas_drop=round(roas_drop, 4),
        cpa_rise=round(cpa_rise, 4),
        exposure_factor=round(exposure_factor, 4),
        ema_fatigue=round(smoothed_fatigue, 4) if prev_ema is not None else None,
        recommendations=recommendations,
    )


def batch_creative_fatigue(
    creatives_today: list[EntityMetrics],
    baselines: dict[str, BaselineMetrics],
    prev_emas: Optional[dict[str, float]] = None,
    params: Optional[FatigueParams] = None,
) -> list[FatigueResult]:
    """
    Calculate fatigue scores for multiple creatives.

    Args:
        creatives_today: List of today's metrics for each creative
        baselines: Dict mapping creative_id to baseline metrics
        prev_emas: Dict mapping creative_id to previous EMA value
        params: Fatigue calculation parameters

    Returns:
        List of FatigueResult, sorted by fatigue score (descending)
    """
    if prev_emas is None:
        prev_emas = {}

    results = []
    for creative in creatives_today:
        baseline = baselines.get(creative.entity_id)
        if baseline:
            prev = prev_emas.get(creative.entity_id)
            result = creative_fatigue(creative, baseline, params, prev)
            results.append(result)

    # Sort by fatigue score (most fatigued first)
    results.sort(key=lambda x: x.fatigue_score, reverse=True)
    return results


def get_refresh_candidates(
    results: list[FatigueResult],
    threshold: float = 0.65,
) -> list[FatigueResult]:
    """
    Get creatives that need refreshing.

    Args:
        results: List of fatigue results
        threshold: Fatigue threshold for refresh (default 0.65)

    Returns:
        List of creatives exceeding threshold
    """
    return [r for r in results if r.fatigue_score >= threshold]
