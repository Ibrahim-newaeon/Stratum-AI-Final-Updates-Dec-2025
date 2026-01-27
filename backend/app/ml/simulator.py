# =============================================================================
# Stratum AI - What-If Simulator
# =============================================================================
"""
What-If Simulator for budget impact prediction.
Uses the hybrid ML strategy to predict outcomes based on budget changes.
"""

from typing import Any

import numpy as np

from app.core.logging import get_logger
from app.ml.inference import ModelRegistry

logger = get_logger(__name__)


class WhatIfSimulator:
    """
    Simulates the impact of budget changes on campaign performance.

    Uses the configured ML strategy (local or vertex) to predict:
    - Revenue changes
    - ROAS impact
    - Conversion volume changes
    """

    def __init__(self):
        self.registry = ModelRegistry()

    async def predict_budget_impact(
        self,
        current_metrics: dict[str, Any],
        budget_change_percent: float,
        days_ahead: int = 30,
        include_confidence: bool = True,
    ) -> dict[str, Any]:
        """
        Predict the impact of a budget change on campaign performance.

        Args:
            current_metrics: Current campaign metrics
                - current_spend: Current total spend
                - impressions: Total impressions
                - clicks: Total clicks
                - conversions: Total conversions
                - revenue: Total revenue
                - ctr: Click-through rate
                - roas: Return on ad spend
            budget_change_percent: Percentage change (-100 to +1000)
            days_ahead: Number of days to forecast
            include_confidence: Whether to include confidence intervals

        Returns:
            Prediction results with current and predicted metrics
        """
        # Calculate new budget
        current_spend = current_metrics.get("current_spend", 0)
        new_spend = current_spend * (1 + budget_change_percent / 100)

        # Prepare features for ML model
        features = {
            "current_spend": current_spend,
            "new_spend": new_spend,
            "budget_change_pct": budget_change_percent,
            "impressions": current_metrics.get("impressions", 0),
            "clicks": current_metrics.get("clicks", 0),
            "conversions": current_metrics.get("conversions", 0),
            "ctr": current_metrics.get("ctr", 0),
            "roas": current_metrics.get("roas", 0),
            "days_ahead": days_ahead,
        }

        # Get ROAS prediction
        roas_prediction = await self.registry.predict("roas_predictor", features)

        # Get conversion prediction
        conversion_features = {**features, "predicted_spend": new_spend}
        conversion_prediction = await self.registry.predict(
            "conversion_predictor", conversion_features
        )

        # Calculate predicted metrics
        predicted_roas = roas_prediction.get("value", current_metrics.get("roas", 1.5))

        # Apply diminishing returns curve for large budget increases
        if budget_change_percent > 50:
            diminishing_factor = 1 - (budget_change_percent - 50) / 1000
            predicted_roas *= max(0.5, diminishing_factor)

        # Calculate predicted revenue
        predicted_revenue = new_spend * predicted_roas

        # Calculate predicted metrics based on scaling
        spend_ratio = new_spend / current_spend if current_spend > 0 else 1

        # Apply realistic scaling with diminishing returns
        impression_scale = self._calculate_scale_factor(spend_ratio, "impressions")
        click_scale = self._calculate_scale_factor(spend_ratio, "clicks")
        conversion_scale = self._calculate_scale_factor(spend_ratio, "conversions")

        predicted_metrics = {
            "spend": round(new_spend, 2),
            "revenue": round(predicted_revenue, 2),
            "roas": round(predicted_roas, 2),
            "impressions": int(current_metrics.get("impressions", 0) * impression_scale),
            "clicks": int(current_metrics.get("clicks", 0) * click_scale),
            "conversions": int(current_metrics.get("conversions", 0) * conversion_scale),
            "ctr": current_metrics.get("ctr", 0),  # CTR typically stays similar
        }

        # Calculate changes
        changes = {}
        for metric in ["spend", "revenue", "roas", "impressions", "clicks", "conversions"]:
            current_val = current_metrics.get(metric if metric != "spend" else "current_spend", 0)
            predicted_val = predicted_metrics.get(metric, 0)
            if current_val > 0:
                changes[metric] = round((predicted_val - current_val) / current_val * 100, 1)
            else:
                changes[metric] = 0

        predicted_metrics["changes"] = changes

        result = {
            "predicted_metrics": predicted_metrics,
            "model_version": roas_prediction.get("model_version", "1.0.0"),
        }

        # Add confidence intervals
        if include_confidence:
            base_confidence = roas_prediction.get("confidence") or 0.8
            confidence = self._calculate_confidence_intervals(
                predicted_metrics,
                base_confidence,
                budget_change_percent,
            )
            result["confidence_interval"] = confidence

        # Add feature importances if available
        if roas_prediction.get("feature_importances"):
            result["feature_importances"] = roas_prediction["feature_importances"]

        return result

    def _calculate_scale_factor(self, spend_ratio: float, metric_type: str) -> float:
        """
        Calculate scaling factor with diminishing returns.

        Uses a logarithmic curve to model diminishing returns at higher spend.
        """
        if spend_ratio <= 0:
            return 0

        if spend_ratio <= 1:
            # Linear scaling for decreases
            return spend_ratio

        # Diminishing returns for increases
        # factor = 1 + log(ratio) * coefficient
        coefficients = {
            "impressions": 0.9,  # Impressions scale well
            "clicks": 0.85,  # Clicks slightly less
            "conversions": 0.75,  # Conversions have more diminishing returns
        }

        coef = coefficients.get(metric_type, 0.8)
        return 1 + np.log(spend_ratio) * coef

    def _calculate_confidence_intervals(
        self,
        predicted_metrics: dict[str, Any],
        base_confidence: float,
        budget_change_percent: float,
    ) -> dict[str, Any]:
        """
        Calculate confidence intervals for predictions.

        Wider intervals for larger budget changes (more uncertainty).
        """
        # Ensure base_confidence is a valid float
        if base_confidence is None:
            base_confidence = 0.8

        # Increase uncertainty for larger changes
        uncertainty_factor = 1 + abs(budget_change_percent) / 200

        # Base variance
        base_variance = (1 - base_confidence) * uncertainty_factor

        intervals = {}
        for metric in ["revenue", "roas", "conversions"]:
            value = predicted_metrics.get(metric, 0)
            variance = value * base_variance

            intervals[metric] = {
                "lower": round(value - variance, 2),
                "upper": round(value + variance, 2),
                "confidence": round(base_confidence / uncertainty_factor, 2),
            }

        return intervals


class ScenarioAnalyzer:
    """
    Analyzes multiple budget scenarios to find optimal allocation.
    """

    def __init__(self):
        self.simulator = WhatIfSimulator()

    async def analyze_scenarios(
        self,
        current_metrics: dict[str, Any],
        scenarios: list[float] = None,
    ) -> dict[str, Any]:
        """
        Run multiple budget scenarios and compare results.

        Args:
            current_metrics: Current campaign metrics
            scenarios: List of budget change percentages to test
                      Default: [-50, -25, 0, 25, 50, 100]

        Returns:
            Comparison of all scenarios with recommendations
        """
        if scenarios is None:
            scenarios = [-50, -25, 0, 25, 50, 100]

        results = []

        for change_pct in scenarios:
            prediction = await self.simulator.predict_budget_impact(
                current_metrics,
                change_pct,
                include_confidence=True,
            )

            results.append(
                {
                    "budget_change_percent": change_pct,
                    "predicted_spend": prediction["predicted_metrics"]["spend"],
                    "predicted_revenue": prediction["predicted_metrics"]["revenue"],
                    "predicted_roas": prediction["predicted_metrics"]["roas"],
                    "predicted_conversions": prediction["predicted_metrics"]["conversions"],
                    "confidence": prediction.get("confidence_interval", {})
                    .get("roas", {})
                    .get("confidence", 0.8),
                }
            )

        # Find optimal scenario (highest ROAS above minimum threshold)
        min_roas_threshold = 1.5
        viable_scenarios = [r for r in results if r["predicted_roas"] >= min_roas_threshold]

        if viable_scenarios:
            # Sort by revenue potential
            optimal = max(viable_scenarios, key=lambda x: x["predicted_revenue"])
            recommendation = {
                "recommended_change": optimal["budget_change_percent"],
                "expected_roas": optimal["predicted_roas"],
                "expected_revenue": optimal["predicted_revenue"],
                "reasoning": f"Maximizes revenue while maintaining ROAS >= {min_roas_threshold}",
            }
        else:
            # Recommend decrease if no viable scenarios
            conservative = min(results, key=lambda x: abs(x["budget_change_percent"]))
            recommendation = {
                "recommended_change": conservative["budget_change_percent"],
                "expected_roas": conservative["predicted_roas"],
                "expected_revenue": conservative["predicted_revenue"],
                "reasoning": "Current performance suggests maintaining or reducing budget",
            }

        return {
            "scenarios": results,
            "recommendation": recommendation,
            "current_metrics": current_metrics,
        }
