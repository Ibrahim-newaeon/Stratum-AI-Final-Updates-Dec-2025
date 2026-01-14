# =============================================================================
# Budget Reallocation Logic
# =============================================================================
"""
Budget Reallocation (daily).
From AI_Logic_Formulas_Pseudocode.md Section 2.

Goal: Move budget from underperformers to winners while limiting risk.

Guardrails:
- Never shift more than 10-20% of total daily spend per day.
- Respect learning phases (Meta/TikTok).
- If EMQ degraded (section 6), suspend automation.
"""

from typing import List, Optional
from app.analytics.logic.types import (
    ScalingScoreResult,
    BudgetAction,
)


class BudgetReallocationParams:
    """Configuration for budget reallocation."""
    # Thresholds
    scale_threshold: float = 0.25
    fix_threshold: float = -0.25
    min_spend_threshold: float = 10.0  # Minimum spend to consider

    # Caps
    max_decrease_pct: float = 0.20  # Max 20% decrease per entity per day
    max_increase_pct: float = 0.30  # Max 30% increase per entity per day
    max_move_per_entity: float = 500.0  # Max absolute amount to move

    # Safety
    max_total_move_pct: float = 0.15  # Max 15% of total daily spend to move


def reallocate_budget(
    scaling_scores: List[ScalingScoreResult],
    current_spends: dict[str, float],
    params: Optional[BudgetReallocationParams] = None,
) -> List[BudgetAction]:
    """
    Calculate budget reallocation based on scaling scores.

    Args:
        scaling_scores: List of scaling score results for all entities
        current_spends: Dict mapping entity_id to current daily spend
        params: Reallocation parameters

    Returns:
        List of BudgetAction with increase/decrease recommendations
    """
    if params is None:
        params = BudgetReallocationParams()

    winners = []
    losers = []

    # Categorize entities
    for score_result in scaling_scores:
        entity_id = score_result.entity_id
        spend = current_spends.get(entity_id, 0)

        if spend < params.min_spend_threshold:
            continue  # Skip entities with insufficient spend

        if score_result.score >= params.scale_threshold:
            winners.append((score_result, spend))
        elif score_result.score <= params.fix_threshold:
            losers.append((score_result, spend))

    # Calculate safe amount to move from losers
    move_pool = 0.0
    loser_decreases = {}

    for score_result, spend in losers:
        decrease = min(
            spend * params.max_decrease_pct,
            params.max_move_per_entity,
        )
        loser_decreases[score_result.entity_id] = decrease
        move_pool += decrease

    # Apply total move cap
    total_spend = sum(current_spends.values())
    max_total_move = total_spend * params.max_total_move_pct
    if move_pool > max_total_move:
        # Scale down proportionally
        scale_factor = max_total_move / move_pool
        loser_decreases = {k: v * scale_factor for k, v in loser_decreases.items()}
        move_pool = max_total_move

    # Distribute to winners proportional to score
    actions = []

    if winners and move_pool > 0:
        total_weight = sum(max(0.01, sr.score) for sr, _ in winners)

        for score_result, spend in winners:
            weight = max(0.01, score_result.score)
            share = weight / total_weight
            increase = move_pool * share

            # Cap increases
            increase = min(
                increase,
                spend * params.max_increase_pct,
                params.max_move_per_entity,
            )

            if increase > 0:
                actions.append(BudgetAction(
                    entity_id=score_result.entity_id,
                    entity_name=score_result.entity_name,
                    action="increase_budget",
                    amount=round(increase, 2),
                    current_spend=spend,
                    scaling_score=score_result.score,
                    reason=f"High ROAS ({score_result.roas_delta*100:+.1f}%), scaling candidate",
                ))

    # Add loser decreases
    for score_result, spend in losers:
        decrease = loser_decreases.get(score_result.entity_id, 0)
        if decrease > 0:
            actions.append(BudgetAction(
                entity_id=score_result.entity_id,
                entity_name=score_result.entity_name,
                action="decrease_budget",
                amount=round(decrease, 2),
                current_spend=spend,
                scaling_score=score_result.score,
                reason=f"Low ROAS ({score_result.roas_delta*100:+.1f}%), needs optimization",
            ))

    # Sort by action (increases first, then decreases)
    actions.sort(key=lambda x: (x.action != "increase_budget", -abs(x.amount)))

    return actions


def summarize_reallocation(actions: List[BudgetAction]) -> dict:
    """
    Summarize budget reallocation actions.

    Args:
        actions: List of budget actions

    Returns:
        Summary dict with totals and counts
    """
    increases = [a for a in actions if a.action == "increase_budget"]
    decreases = [a for a in actions if a.action == "decrease_budget"]

    total_increase = sum(a.amount for a in increases)
    total_decrease = sum(a.amount for a in decreases)

    return {
        "total_increase": round(total_increase, 2),
        "total_decrease": round(total_decrease, 2),
        "net_change": round(total_increase - total_decrease, 2),
        "entities_scaled": len(increases),
        "entities_reduced": len(decreases),
        "top_increase": increases[0] if increases else None,
        "top_decrease": decreases[0] if decreases else None,
    }


def validate_reallocation(
    actions: List[BudgetAction],
    learning_phase_entities: set[str],
) -> List[BudgetAction]:
    """
    Validate and filter reallocation actions.
    Removes actions for entities in learning phase.

    Args:
        actions: Proposed budget actions
        learning_phase_entities: Set of entity IDs in learning phase

    Returns:
        Filtered list of valid actions
    """
    valid_actions = []

    for action in actions:
        if action.entity_id in learning_phase_entities:
            # Skip entities in learning phase
            continue
        valid_actions.append(action)

    return valid_actions
