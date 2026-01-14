# =============================================================================
# Scaling Score Calculator
# =============================================================================
"""
Scaling Score (single number to rank opportunities).
From AI_Logic_Formulas_Pseudocode.md Section 1.

Goal: Score each entity for "scale" vs "fix" in a consistent way.

Interpretation:
- score >= +0.25: scale candidate
- -0.25 < score < +0.25: stable / watch
- score <= -0.25: fix or pause candidate
"""

from typing import Optional
from app.analytics.logic.types import (
    EntityMetrics,
    BaselineMetrics,
    ScoringParams,
    ScalingScoreResult,
    ScalingAction,
)


def pct_change(new: float, old: float) -> float:
    """Calculate percentage change between two values."""
    if abs(old) < 1e-9:
        return 0.0
    return (new - old) / abs(old)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def clamp01(value: float) -> float:
    """Clamp value between 0 and 1."""
    return clamp(value, 0.0, 1.0)


def scaling_score(
    today: EntityMetrics,
    baseline: BaselineMetrics,
    params: Optional[ScoringParams] = None,
    prev_ema: Optional[float] = None,
) -> ScalingScoreResult:
    """
    Calculate scaling score for an entity.

    Args:
        today: Today's metrics for the entity
        baseline: Aggregated baseline metrics (last 7 days)
        params: Scoring configuration parameters
        prev_ema: Previous EMA value for smoothing (optional)

    Returns:
        ScalingScoreResult with score, action, and breakdown
    """
    if params is None:
        params = ScoringParams()

    # Calculate deltas vs baseline
    d_roas = pct_change(today.roas, baseline.roas)
    d_cpa = pct_change(today.cpa, baseline.cpa)  # Lower is better
    d_cvr = pct_change(today.cvr, baseline.cvr)
    d_ctr = pct_change(today.ctr, baseline.ctr)

    # Risk penalties
    # Frequency penalty
    freq_target = params.freq_target
    if today.frequency and today.frequency > 0:
        freq_penalty = clamp01((today.frequency - freq_target) / freq_target)
    else:
        freq_penalty = 0.0

    # EMQ penalty (if emq_score missing -> 0)
    if today.emq_score is not None and today.emq_score < params.emq_target:
        emq_penalty = clamp01((params.emq_target - today.emq_score) / params.emq_target)
    else:
        emq_penalty = 0.0

    # Volume penalty (insufficient conversions)
    min_conversions = params.min_conversions
    if today.conversions > 0:
        vol_penalty = clamp01(min_conversions / today.conversions)
    else:
        vol_penalty = 1.0  # No conversions = max penalty

    # Score components (weights tuned for e-commerce ROAS)
    score = 0.0
    score += params.roas_weight * clamp(d_roas, -1.0, 1.0)
    score += params.cpa_weight * clamp(-d_cpa, -1.0, 1.0)  # Invert CPA delta
    score += params.cvr_weight * clamp(d_cvr, -1.0, 1.0)
    score += params.ctr_weight * clamp(d_ctr, -1.0, 1.0)

    # Apply penalties (reduce score)
    score = score * (1 - params.freq_penalty_weight * freq_penalty)
    score = score * (1 - params.emq_penalty_weight * emq_penalty)
    score = score * (1 - params.vol_penalty_weight * vol_penalty)

    # Optional EMA smoothing
    if prev_ema is not None:
        score = 0.4 * score + 0.6 * prev_ema

    # Determine action
    if score >= params.scale_threshold:
        action = ScalingAction.SCALE
    elif score <= params.fix_threshold:
        action = ScalingAction.FIX
    else:
        action = ScalingAction.WATCH

    # Generate recommendations
    recommendations = []
    if action == ScalingAction.SCALE:
        recommendations.append("Consider increasing budget by 20-30%")
        recommendations.append(f"ROAS improved {d_roas*100:.1f}% vs baseline")
    elif action == ScalingAction.FIX:
        if d_roas < -0.2:
            recommendations.append(f"ROAS dropped {abs(d_roas)*100:.1f}% - review targeting")
        if d_cpa > 0.2:
            recommendations.append(f"CPA increased {d_cpa*100:.1f}% - optimize bidding")
        if emq_penalty > 0.3:
            recommendations.append(f"EMQ score low ({today.emq_score}) - check event tracking")
    else:
        recommendations.append("Performance stable - continue monitoring")

    return ScalingScoreResult(
        entity_id=today.entity_id,
        entity_name=today.entity_name,
        score=round(score, 4),
        action=action,
        roas_delta=round(d_roas, 4),
        cpa_delta=round(d_cpa, 4),
        cvr_delta=round(d_cvr, 4),
        ctr_delta=round(d_ctr, 4),
        freq_penalty=round(freq_penalty, 4),
        emq_penalty=round(emq_penalty, 4),
        vol_penalty=round(vol_penalty, 4),
        recommendations=recommendations,
    )


def batch_scaling_scores(
    entities_today: list[EntityMetrics],
    baselines: dict[str, BaselineMetrics],
    params: Optional[ScoringParams] = None,
) -> list[ScalingScoreResult]:
    """
    Calculate scaling scores for multiple entities.

    Args:
        entities_today: List of today's metrics for each entity
        baselines: Dict mapping entity_id to baseline metrics
        params: Scoring configuration

    Returns:
        List of ScalingScoreResult, sorted by score (descending)
    """
    results = []
    for entity in entities_today:
        baseline = baselines.get(entity.entity_id)
        if baseline:
            result = scaling_score(entity, baseline, params)
            results.append(result)

    # Sort by score (best opportunities first)
    results.sort(key=lambda x: x.score, reverse=True)
    return results
