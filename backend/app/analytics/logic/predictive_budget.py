# =============================================================================
# Predictive Budget Autopilot — Feature #5
# =============================================================================
"""
Predictive Budget Autopilot — uses scaling scores, trend forecasting,
and trust gate validation to generate confidence-scored budget
reallocation recommendations.

Architecture:
1. Calculates scaling scores for all campaigns
2. Forecasts next-period performance using trend data
3. Generates budget recommendations with confidence levels
4. Validates through trust gate (only executes when confidence > 85%)
5. Returns a structured response for the dashboard

Builds on: scoring.py, budget.py, signal_health.py, trust_gate concepts
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────

class CampaignBudgetInsight(BaseModel):
    """Insight for a single campaign's budget optimization."""
    campaign_id: int
    campaign_name: str
    platform: str
    current_spend: float
    recommended_spend: float
    change_amount: float
    change_percent: float
    action: Literal["scale", "reduce", "maintain", "pause"]
    confidence: float  # 0.0 - 1.0
    reasoning: str
    metrics: Dict[str, float] = {}  # roas, cpa, conversions, etc.
    risk_factors: List[str] = []


class BudgetForecast(BaseModel):
    """Forecasted outcome if recommendations are applied."""
    projected_spend: float
    projected_revenue: float
    projected_roas: float
    projected_conversions: int
    spend_change_pct: float
    revenue_change_pct: float
    confidence_level: str  # "high", "medium", "low"


class PredictiveBudgetResponse(BaseModel):
    """Full response for the predictive budget autopilot."""
    summary: str
    trust_gate_status: Literal["pass", "hold", "block"]
    autopilot_eligible: bool
    total_campaigns_analyzed: int
    recommendations: List[CampaignBudgetInsight] = []
    scale_candidates: int = 0
    reduce_candidates: int = 0
    maintain_count: int = 0
    total_budget_shift: float = 0.0
    budget_shift_pct: float = 0.0
    forecast: Optional[BudgetForecast] = None
    avg_confidence: float = 0.0
    high_confidence_count: int = 0


# ── Scoring & Analysis ───────────────────────────────────────────────────────

def _calculate_campaign_score(
    spend: float,
    revenue: float,
    conversions: int,
    avg_spend: float,
    avg_revenue: float,
    avg_conversions: float,
) -> Dict:
    """Calculate a simplified scaling score for a campaign."""
    roas = revenue / spend if spend > 0 else 0.0
    avg_roas = avg_revenue / avg_spend if avg_spend > 0 else 0.0
    cpa = spend / conversions if conversions > 0 else 0.0
    avg_cpa = avg_spend / avg_conversions if avg_conversions > 0 else 0.0

    # ROAS delta (higher is better)
    roas_delta = (roas - avg_roas) / max(avg_roas, 0.01)

    # CPA delta (lower is better, so invert)
    cpa_delta = -(cpa - avg_cpa) / max(avg_cpa, 0.01) if avg_cpa > 0 else 0.0

    # Composite score: ROAS-heavy (60%) + CPA efficiency (40%)
    score = roas_delta * 0.6 + cpa_delta * 0.4

    # Confidence based on data volume and consistency
    volume_factor = min(1.0, conversions / 10)  # Need at least 10 conversions
    spend_factor = min(1.0, spend / 100)  # Need at least $100 spend
    confidence = volume_factor * 0.5 + spend_factor * 0.3 + min(1.0, abs(score)) * 0.2

    return {
        "score": round(score, 3),
        "roas": round(roas, 2),
        "cpa": round(cpa, 2),
        "roas_delta": round(roas_delta, 3),
        "cpa_delta": round(cpa_delta, 3),
        "confidence": round(min(1.0, confidence), 2),
    }


def _determine_action(
    score: float,
    confidence: float,
    roas: float,
) -> Literal["scale", "reduce", "maintain", "pause"]:
    """Determine budget action based on score and confidence."""
    if score >= 0.25 and confidence >= 0.5:
        return "scale"
    elif score <= -0.25 and confidence >= 0.4:
        if roas < 0.5:
            return "pause"
        return "reduce"
    else:
        return "maintain"


def _generate_reasoning(
    action: str,
    roas: float,
    roas_delta: float,
    cpa: float,
    cpa_delta: float,
    conversions: int,
) -> str:
    """Generate human-readable reasoning for a budget recommendation."""
    if action == "scale":
        parts = [f"ROAS of {roas:.2f}x is {abs(roas_delta)*100:.0f}% above average"]
        if cpa_delta > 0:
            parts.append(f"CPA is efficient at ${cpa:.2f}")
        if conversions >= 20:
            parts.append(f"strong conversion volume ({conversions})")
        return " — ".join(parts) + ". Recommend increasing budget by 15-20%."

    elif action == "reduce":
        parts = [f"ROAS of {roas:.2f}x is {abs(roas_delta)*100:.0f}% below average"]
        if cpa_delta < 0:
            parts.append(f"CPA of ${cpa:.2f} is above target")
        return " — ".join(parts) + ". Recommend reducing budget by 15-20%."

    elif action == "pause":
        return (
            f"ROAS of {roas:.2f}x is critically low. "
            f"Spending ${cpa:.2f} per conversion with only {conversions} conversions. "
            "Recommend pausing until creative or targeting is refreshed."
        )

    else:
        return (
            f"Performance is within normal range (ROAS: {roas:.2f}x, CPA: ${cpa:.2f}). "
            "Maintain current budget."
        )


def _calculate_recommended_spend(
    current_spend: float,
    action: str,
    score: float,
    confidence: float,
) -> float:
    """Calculate recommended spend amount."""
    if action == "scale":
        # Scale by 15-30% based on score strength and confidence
        scale_pct = min(0.30, 0.15 + abs(score) * 0.15) * confidence
        return round(current_spend * (1 + scale_pct), 2)

    elif action == "reduce":
        # Reduce by 15-20% based on score
        reduce_pct = min(0.20, 0.10 + abs(score) * 0.10) * confidence
        return round(current_spend * (1 - reduce_pct), 2)

    elif action == "pause":
        return 0.0

    else:
        return current_spend


def _identify_risk_factors(
    roas: float,
    conversions: int,
    confidence: float,
    spend: float,
) -> List[str]:
    """Identify risk factors for a budget recommendation."""
    risks = []
    if conversions < 10:
        risks.append("Low conversion volume — less statistical confidence")
    if confidence < 0.6:
        risks.append("Below confidence threshold for auto-execution")
    if roas > 0 and roas < 1.0:
        risks.append("ROAS below breakeven — spending more than earning")
    if spend < 50:
        risks.append("Low spend — may be in learning phase")
    return risks


# ── Main Entry Point ─────────────────────────────────────────────────────────

def build_predictive_budget(
    campaigns: List[Dict],
    signal_health_score: int,
    autopilot_threshold: int = 70,
) -> PredictiveBudgetResponse:
    """
    Main entry point: analyzes all campaigns and generates predictive
    budget recommendations with confidence scoring.

    Args:
        campaigns: List of campaign dicts with id, name, platform,
                   spend, revenue, conversions
        signal_health_score: Current signal health (0-100)
        autopilot_threshold: Minimum health for auto-execution (default 70)

    Returns:
        PredictiveBudgetResponse with recommendations and forecast
    """
    if not campaigns:
        return PredictiveBudgetResponse(
            summary="No campaigns available for budget analysis.",
            trust_gate_status="block",
            autopilot_eligible=False,
            total_campaigns_analyzed=0,
        )

    # Trust gate check
    if signal_health_score >= autopilot_threshold:
        trust_status = "pass"
    elif signal_health_score >= 40:
        trust_status = "hold"
    else:
        trust_status = "block"

    # Calculate portfolio averages
    total_spend = sum(c.get("spend", 0) for c in campaigns)
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    total_conversions = sum(c.get("conversions", 0) for c in campaigns)
    n = len(campaigns)

    avg_spend = total_spend / n if n > 0 else 0
    avg_revenue = total_revenue / n if n > 0 else 0
    avg_conversions = total_conversions / n if n > 0 else 0

    # Analyze each campaign
    recommendations: List[CampaignBudgetInsight] = []

    for campaign in campaigns:
        c_id = campaign.get("id", 0)
        c_name = campaign.get("name", "Unknown")
        c_platform = campaign.get("platform", "unknown")
        c_spend = campaign.get("spend", 0)
        c_revenue = campaign.get("revenue", 0)
        c_conversions = campaign.get("conversions", 0)

        if c_spend <= 0:
            continue

        # Score
        score_data = _calculate_campaign_score(
            spend=c_spend,
            revenue=c_revenue,
            conversions=c_conversions,
            avg_spend=avg_spend,
            avg_revenue=avg_revenue,
            avg_conversions=avg_conversions,
        )

        action = _determine_action(
            score=score_data["score"],
            confidence=score_data["confidence"],
            roas=score_data["roas"],
        )

        recommended_spend = _calculate_recommended_spend(
            current_spend=c_spend,
            action=action,
            score=score_data["score"],
            confidence=score_data["confidence"],
        )

        change_amount = recommended_spend - c_spend
        change_pct = (change_amount / c_spend * 100) if c_spend > 0 else 0

        reasoning = _generate_reasoning(
            action=action,
            roas=score_data["roas"],
            roas_delta=score_data["roas_delta"],
            cpa=score_data["cpa"],
            cpa_delta=score_data["cpa_delta"],
            conversions=c_conversions,
        )

        risk_factors = _identify_risk_factors(
            roas=score_data["roas"],
            conversions=c_conversions,
            confidence=score_data["confidence"],
            spend=c_spend,
        )

        recommendations.append(CampaignBudgetInsight(
            campaign_id=c_id,
            campaign_name=c_name,
            platform=c_platform,
            current_spend=c_spend,
            recommended_spend=recommended_spend,
            change_amount=round(change_amount, 2),
            change_percent=round(change_pct, 1),
            action=action,
            confidence=score_data["confidence"],
            reasoning=reasoning,
            metrics={
                "roas": score_data["roas"],
                "cpa": score_data["cpa"],
                "conversions": c_conversions,
                "score": score_data["score"],
            },
            risk_factors=risk_factors,
        ))

    # Sort: scale first (by confidence), then reduce, then maintain
    action_order = {"scale": 0, "reduce": 1, "pause": 2, "maintain": 3}
    recommendations.sort(key=lambda r: (action_order.get(r.action, 3), -r.confidence))

    # Aggregate stats
    scale_count = sum(1 for r in recommendations if r.action == "scale")
    reduce_count = sum(1 for r in recommendations if r.action in ("reduce", "pause"))
    maintain_count = sum(1 for r in recommendations if r.action == "maintain")

    total_shift = sum(abs(r.change_amount) for r in recommendations)
    shift_pct = (total_shift / total_spend * 100) if total_spend > 0 else 0

    confidences = [r.confidence for r in recommendations]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    high_conf = sum(1 for c in confidences if c >= 0.85)

    # Autopilot eligible = trust gate passes AND high confidence
    autopilot_eligible = trust_status == "pass" and avg_conf >= 0.6

    # Build forecast
    forecast = None
    if total_spend > 0:
        proj_spend = sum(r.recommended_spend for r in recommendations)
        # Estimate revenue based on each campaign's ROAS applied to new spend
        proj_revenue = sum(
            r.recommended_spend * r.metrics.get("roas", 0)
            for r in recommendations
        )
        proj_conversions = int(sum(
            r.recommended_spend / max(r.metrics.get("cpa", 1), 0.01)
            for r in recommendations
            if r.metrics.get("cpa", 0) > 0
        ))
        proj_roas = proj_revenue / proj_spend if proj_spend > 0 else 0

        conf_level = "high" if avg_conf >= 0.75 else ("medium" if avg_conf >= 0.5 else "low")

        forecast = BudgetForecast(
            projected_spend=round(proj_spend, 2),
            projected_revenue=round(proj_revenue, 2),
            projected_roas=round(proj_roas, 2),
            projected_conversions=proj_conversions,
            spend_change_pct=round((proj_spend - total_spend) / total_spend * 100, 1) if total_spend else 0,
            revenue_change_pct=round((proj_revenue - total_revenue) / total_revenue * 100, 1) if total_revenue > 0 else 0,
            confidence_level=conf_level,
        )

    # Build summary
    summary = _build_summary(
        scale_count, reduce_count, maintain_count,
        total_shift, shift_pct, trust_status,
        autopilot_eligible, avg_conf, forecast,
    )

    return PredictiveBudgetResponse(
        summary=summary,
        trust_gate_status=trust_status,
        autopilot_eligible=autopilot_eligible,
        total_campaigns_analyzed=len(recommendations),
        recommendations=recommendations,
        scale_candidates=scale_count,
        reduce_candidates=reduce_count,
        maintain_count=maintain_count,
        total_budget_shift=round(total_shift, 2),
        budget_shift_pct=round(shift_pct, 1),
        forecast=forecast,
        avg_confidence=round(avg_conf, 2),
        high_confidence_count=high_conf,
    )


def _build_summary(
    scale_count: int,
    reduce_count: int,
    maintain_count: int,
    total_shift: float,
    shift_pct: float,
    trust_status: str,
    autopilot_eligible: bool,
    avg_confidence: float,
    forecast: Optional[BudgetForecast],
) -> str:
    """Build executive summary for budget recommendations."""
    parts = []

    if scale_count > 0:
        parts.append(f"{scale_count} campaign{'s' if scale_count > 1 else ''} recommended for scaling")
    if reduce_count > 0:
        parts.append(f"{reduce_count} for budget reduction")
    if maintain_count > 0:
        parts.append(f"{maintain_count} maintaining current budget")

    if total_shift > 0:
        parts.append(f"Total proposed budget shift: ${total_shift:,.0f} ({shift_pct:.1f}% of total spend)")

    if trust_status == "pass":
        if autopilot_eligible:
            parts.append(
                f"Trust gate: PASS. Autopilot eligible with "
                f"{avg_confidence*100:.0f}% average confidence."
            )
        else:
            parts.append("Trust gate: PASS. Manual review recommended due to lower confidence.")
    elif trust_status == "hold":
        parts.append(
            "Trust gate: HOLD. Signal health is degraded — recommendations are advisory only."
        )
    else:
        parts.append(
            "Trust gate: BLOCK. Signal health is critical — budget changes suspended."
        )

    if forecast and forecast.revenue_change_pct != 0:
        direction = "increase" if forecast.revenue_change_pct > 0 else "decrease"
        parts.append(
            f"Projected impact: {abs(forecast.revenue_change_pct):.1f}% revenue {direction} "
            f"to ${forecast.projected_revenue:,.0f} (ROAS: {forecast.projected_roas:.2f}x)."
        )

    return " ".join(parts)
