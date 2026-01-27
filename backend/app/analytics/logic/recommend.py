# =============================================================================
# Daily Recommendations Generator
# =============================================================================
"""
Daily Recommendations Generator (human-readable).
From AI_Logic_Formulas_Pseudocode.md Section 7.

Goal: Turn math into actions.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from app.analytics.logic.anomalies import detect_anomalies
from app.analytics.logic.budget import reallocate_budget, summarize_reallocation
from app.analytics.logic.fatigue import batch_creative_fatigue
from app.analytics.logic.scoring import batch_scaling_scores
from app.analytics.logic.signal_health import should_suspend_automation, signal_health
from app.analytics.logic.types import (
    AlertSeverity,
    BaselineMetrics,
    EntityMetrics,
    FatigueState,
    RecommendationAction,
    ScalingAction,
)


class RecommendationsEngine:
    """
    Central engine for generating daily recommendations.
    Combines all analytics logic into actionable insights.
    """

    def __init__(self):
        self.generated_at = None

    def generate_recommendations(
        self,
        entities_today: list[EntityMetrics],
        baselines: dict[str, BaselineMetrics],
        creatives_today: Optional[list[EntityMetrics]] = None,
        creative_baselines: Optional[dict[str, BaselineMetrics]] = None,
        metrics_history: Optional[dict[str, list[float]]] = None,
        current_metrics: Optional[dict[str, float]] = None,
        emq_score: Optional[float] = None,
        event_loss_pct: Optional[float] = None,
        api_health: bool = True,
        current_spends: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """
        Generate comprehensive daily recommendations.

        Args:
            entities_today: Today's metrics for campaigns/adsets
            baselines: Baseline metrics for each entity
            creatives_today: Today's metrics for creatives
            creative_baselines: Baseline metrics for creatives
            metrics_history: Historical metrics for anomaly detection
            current_metrics: Current metrics for anomaly detection
            emq_score: Account EMQ score
            event_loss_pct: Account event loss percentage
            api_health: API connectivity status
            current_spends: Current daily spend by entity

        Returns:
            Dict with recommendations, actions, alerts, and insights
        """
        self.generated_at = datetime.now(UTC)

        recommendations = []
        actions = []
        alerts = []
        insights = []

        # 1. Check signal health first
        health_result = signal_health(emq_score, event_loss_pct, api_health)

        if should_suspend_automation(health_result):
            # Data quality issue - prioritize this
            recommendations.append(
                RecommendationAction(
                    type="signal_health",
                    priority=AlertSeverity.CRITICAL,
                    title="Data Quality Issue Detected",
                    description="Pause automation and check pixel/CAPI implementation.",
                    expected_impact={"automation_suspended": True},
                    action_params={"check_areas": ["pixel", "capi", "event_mapping"]},
                )
            )

            alerts.append(
                {
                    "type": "emq_degraded",
                    "severity": health_result.status.value,
                    "message": f"Signal health: {health_result.status.value}",
                    "issues": health_result.issues,
                    "actions": health_result.actions,
                }
            )

            return {
                "recommendations": [r.dict() for r in recommendations],
                "actions": actions,
                "alerts": alerts,
                "insights": insights,
                "health": health_result.dict(),
                "generated_at": self.generated_at.isoformat(),
                "automation_blocked": True,
            }

        # 2. Detect anomalies
        if metrics_history and current_metrics:
            anomalies = detect_anomalies(metrics_history, current_metrics)
            for anomaly in anomalies:
                if anomaly.is_anomaly:
                    alerts.append(
                        {
                            "type": "anomaly",
                            "metric": anomaly.metric,
                            "severity": anomaly.severity.value,
                            "zscore": anomaly.zscore,
                            "message": f"{anomaly.metric} is {anomaly.direction} (z={anomaly.zscore:.1f})",
                            "current_value": anomaly.current_value,
                            "baseline": anomaly.baseline_mean,
                        }
                    )

                    if anomaly.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                        recommendations.append(
                            RecommendationAction(
                                type="anomaly_investigation",
                                priority=anomaly.severity,
                                title=f"Investigate {anomaly.metric} anomaly",
                                description=f"{anomaly.metric} is significantly {anomaly.direction} vs baseline.",
                                action_params={
                                    "metric": anomaly.metric,
                                    "zscore": anomaly.zscore,
                                },
                            )
                        )

        # 3. Calculate scaling scores
        scaling_results = batch_scaling_scores(entities_today, baselines)

        # 4. Budget reallocation
        if current_spends:
            budget_actions = reallocate_budget(scaling_results, current_spends)
            budget_summary = summarize_reallocation(budget_actions)

            for ba in budget_actions:
                actions.append(
                    {
                        "type": ba.action,
                        "entity_id": ba.entity_id,
                        "entity_name": ba.entity_name,
                        "amount": ba.amount,
                        "reason": ba.reason,
                    }
                )

            if budget_summary["entities_scaled"] > 0:
                insights.append(
                    {
                        "type": "budget_opportunity",
                        "title": f"Scale {budget_summary['entities_scaled']} high-performing campaigns",
                        "description": f"Potential +${budget_summary['total_increase']:.0f} budget shift",
                        "impact": "high",
                    }
                )

        # 5. Creative fatigue
        if creatives_today and creative_baselines:
            fatigue_results = batch_creative_fatigue(creatives_today, creative_baselines)
            fatigued_creatives = [f for f in fatigue_results if f.state == FatigueState.REFRESH]

            for fc in fatigued_creatives:
                recommendations.append(
                    RecommendationAction(
                        type="creative_refresh",
                        priority=AlertSeverity.HIGH,
                        title=f"Refresh creative: {fc.creative_name}",
                        description=f"Fatigue score {fc.fatigue_score:.2f}. {fc.recommendations[0] if fc.recommendations else ''}",
                        entity_id=fc.creative_id,
                        entity_name=fc.creative_name,
                        expected_impact={"fatigue_score": fc.fatigue_score},
                    )
                )

        # 6. Entity-level recommendations
        for sr in scaling_results:
            if sr.action == ScalingAction.SCALE:
                insights.append(
                    {
                        "type": "scaling_opportunity",
                        "entity_id": sr.entity_id,
                        "entity_name": sr.entity_name,
                        "title": f"Scale opportunity: {sr.entity_name}",
                        "score": sr.score,
                        "recommendations": sr.recommendations,
                    }
                )
            elif sr.action == ScalingAction.FIX:
                recommendations.append(
                    RecommendationAction(
                        type="fix_campaign",
                        priority=AlertSeverity.HIGH if sr.score < -0.5 else AlertSeverity.MEDIUM,
                        title=f"Investigate: {sr.entity_name}",
                        description=f"ROAS {sr.roas_delta*100:+.1f}% / CPA {sr.cpa_delta*100:+.1f}% vs baseline.",
                        entity_id=sr.entity_id,
                        entity_name=sr.entity_name,
                        expected_impact={"scaling_score": sr.score},
                        action_params={"recommendations": sr.recommendations},
                    )
                )

        # Sort recommendations by priority
        priority_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3,
            AlertSeverity.INFO: 4,
        }
        recommendations.sort(key=lambda x: priority_order.get(x.priority, 5))

        return {
            "recommendations": [r.dict() for r in recommendations],
            "actions": actions,
            "alerts": alerts,
            "insights": insights,
            "health": health_result.dict(),
            "scaling_summary": {
                "scale_candidates": len(
                    [s for s in scaling_results if s.action == ScalingAction.SCALE]
                ),
                "fix_candidates": len(
                    [s for s in scaling_results if s.action == ScalingAction.FIX]
                ),
                "watch_candidates": len(
                    [s for s in scaling_results if s.action == ScalingAction.WATCH]
                ),
            },
            "generated_at": self.generated_at.isoformat(),
            "automation_blocked": False,
        }


def generate_recommendations(
    entities_today: list[EntityMetrics],
    baselines: dict[str, BaselineMetrics],
    **kwargs,
) -> dict[str, Any]:
    """
    Convenience function to generate recommendations.

    Args:
        entities_today: Today's metrics for entities
        baselines: Baseline metrics for each entity
        **kwargs: Additional parameters for RecommendationsEngine

    Returns:
        Recommendations dict
    """
    engine = RecommendationsEngine()
    return engine.generate_recommendations(entities_today, baselines, **kwargs)
