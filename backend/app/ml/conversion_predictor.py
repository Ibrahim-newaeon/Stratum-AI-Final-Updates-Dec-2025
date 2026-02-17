# =============================================================================
# Stratum AI - Conversion Predictor
# =============================================================================
"""
ML-based conversion prediction for campaign optimization.
Predicts expected conversions based on campaign features.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from app.core.logging import get_logger
from app.ml.inference import ModelRegistry

logger = get_logger(__name__)


class ConversionPredictor:
    """
    Predicts conversions based on campaign features.

    Features considered:
    - Impressions and clicks
    - Spend and budget
    - Platform characteristics
    - Historical conversion rates
    - Targeting parameters
    """

    def __init__(self):
        self.registry = ModelRegistry()

        # Platform-specific baseline conversion rates
        self.platform_baselines = {
            "meta": 0.025,
            "google": 0.035,
            "tiktok": 0.015,
            "snapchat": 0.012,
        }

    async def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict conversions for given features.

        Args:
            features: Input features including:
                - impressions: Total impressions
                - clicks: Total clicks
                - spend: Total spend
                - ctr: Click-through rate
                - platform: Ad platform

        Returns:
            Prediction with value, conversion rate, confidence, and factors
        """
        # Prepare features for model
        model_features = self._prepare_features(features)

        # Try to get prediction from ML model
        prediction = await self.registry.predict("conversion_predictor", model_features)

        # If model prediction failed, use heuristic
        if prediction.get("inference_strategy", "").endswith("-mock"):
            return self._heuristic_prediction(features)

        # Calculate additional metrics
        impressions = features.get("impressions", 0)
        clicks = features.get("clicks", 0)
        predicted_conversions = prediction.get("value", 0)

        # Calculate rates
        conversion_rate = predicted_conversions / clicks if clicks > 0 else 0
        click_to_conversion = predicted_conversions / impressions if impressions > 0 else 0

        # Identify contributing factors
        factors = self._identify_factors(features, prediction)

        return {
            "value": round(predicted_conversions, 1),
            "conversion_rate": round(conversion_rate * 100, 2),
            "click_to_conversion_rate": round(click_to_conversion * 100, 4),
            "confidence": prediction.get("confidence"),  # Model-derived, None if unavailable
            "contributing_factors": factors,
            "model_version": prediction.get("model_version", "1.0.0"),
        }

    def _prepare_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and normalize features for the model."""
        # Extract and normalize features
        prepared = {
            "impressions_log": np.log1p(features.get("impressions", 0)),
            "clicks_log": np.log1p(features.get("clicks", 0)),
            "spend_log": np.log1p(features.get("spend", 0)),
            "ctr": features.get("ctr", 0),
        }

        # Platform one-hot encoding
        platform = features.get("platform", "meta").lower()
        for p in ["meta", "google", "tiktok", "snapchat"]:
            prepared[f"platform_{p}"] = 1 if platform == p else 0

        # Add any additional features passed
        for key, value in features.items():
            if key not in prepared and isinstance(value, (int, float)):
                prepared[key] = value

        return prepared

    
    def _calculate_heuristic_confidence(
        self,
        features: Dict[str, Any],
        factors: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate confidence for heuristic predictions based on data quality.
        
        Heuristic predictions inherently have lower confidence than ML predictions.
        Confidence is adjusted based on:
        - Data completeness (more features = higher confidence)
        - Data volume (more impressions/clicks = more reliable)
        - Factor signals (clear positive/negative = higher confidence)
        
        Returns:
            Confidence score between 0.3 and 0.75 (capped for heuristics)
        """
        # Base confidence for heuristic predictions
        base_confidence = 0.45
        
        # Data completeness bonus
        has_impressions = features.get("impressions", 0) > 0
        has_clicks = features.get("clicks", 0) > 0
        has_spend = features.get("spend", 0) > 0
        has_ctr = features.get("ctr", 0) > 0
        
        completeness = sum([has_impressions, has_clicks, has_spend, has_ctr]) / 4
        completeness_bonus = completeness * 0.15
        
        # Data volume bonus (more data = more reliable baseline)
        impressions = features.get("impressions", 0)
        clicks = features.get("clicks", 0)
        volume_score = min(0.1, (impressions / 100000) * 0.05 + (clicks / 1000) * 0.05)
        
        # Factor clarity bonus (clear signals = higher confidence)
        positive_factors = sum(1 for f in factors if f.get("impact") == "positive")
        negative_factors = sum(1 for f in factors if f.get("impact") == "negative")
        clarity_bonus = min(0.05, (positive_factors + negative_factors) * 0.02)
        
        confidence = base_confidence + completeness_bonus + volume_score + clarity_bonus
        
        # Cap at 0.75 for heuristic predictions (ML should be higher)
        return round(min(0.75, max(0.3, confidence)), 2)


    def _heuristic_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback heuristic prediction when model unavailable.

        Uses historical baselines and feature correlations.
        """
        impressions = features.get("impressions", 0)
        clicks = features.get("clicks", 0)
        spend = features.get("spend", 0)
        ctr = features.get("ctr", 0)
        platform = features.get("platform", "meta").lower()

        # Get platform baseline
        base_cvr = self.platform_baselines.get(platform, 0.02)

        # Adjust based on CTR (higher CTR often means better targeting)
        ctr_factor = 1.0
        if ctr > 0:
            avg_ctr = 1.5  # Average CTR baseline
            ctr_factor = min(1.5, max(0.5, ctr / avg_ctr))

        # Adjust based on spend efficiency
        spend_factor = 1.0
        if spend > 0 and clicks > 0:
            cpc = spend / clicks
            if cpc < 1.0:  # Efficient spend
                spend_factor = 1.2
            elif cpc > 3.0:  # Expensive traffic
                spend_factor = 0.8

        # Calculate adjusted conversion rate
        adjusted_cvr = base_cvr * ctr_factor * spend_factor

        # Predict conversions
        predicted_conversions = clicks * adjusted_cvr

        # Add some variance for realism
        np.random.seed(int(impressions + clicks) % 10000)
        variance = np.random.uniform(0.9, 1.1)
        predicted_conversions *= variance

        # Identify factors
        factors = []
        if ctr_factor > 1.1:
            factors.append({
                "factor": "High CTR",
                "impact": "positive",
                "description": "Above-average click-through rate indicates good audience targeting",
            })
        elif ctr_factor < 0.9:
            factors.append({
                "factor": "Low CTR",
                "impact": "negative",
                "description": "Below-average CTR may indicate targeting or creative issues",
            })

        if spend_factor > 1.1:
            factors.append({
                "factor": "Efficient Spend",
                "impact": "positive",
                "description": "Low CPC suggests quality traffic at good rates",
            })

        factors.append({
            "factor": f"Platform: {platform.title()}",
            "impact": "neutral",
            "description": f"Baseline CVR for {platform} is {base_cvr*100:.1f}%",
        })

        return {
            "value": round(predicted_conversions, 1),
            "conversion_rate": round(adjusted_cvr * 100, 2),
            "click_to_conversion_rate": round((predicted_conversions / impressions * 100) if impressions > 0 else 0, 4),
            "confidence": self._calculate_heuristic_confidence(features, factors),
            "contributing_factors": factors,
            "model_version": "heuristic-1.0.0",
        }

    def _identify_factors(
        self,
        features: Dict[str, Any],
        prediction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Identify factors contributing to the prediction.

        Uses feature importances from the model when available.
        """
        factors = []

        # Use feature importances if available
        importances = prediction.get("feature_importances", {})

        if importances:
            # Sort by absolute importance
            sorted_features = sorted(
                importances.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )

            for feature_name, importance in sorted_features[:5]:
                impact = "positive" if importance > 0 else "negative"
                factors.append({
                    "factor": feature_name.replace("_", " ").title(),
                    "impact": impact,
                    "importance": round(importance, 3),
                    "description": self._get_feature_description(feature_name, features),
                })

        # Add platform factor
        platform = features.get("platform", "unknown")
        factors.append({
            "factor": f"Platform: {platform.title()}",
            "impact": "neutral",
            "description": f"Predictions calibrated for {platform} advertising",
        })

        return factors

    def _get_feature_description(
        self,
        feature_name: str,
        features: Dict[str, Any],
    ) -> str:
        """Generate human-readable description for a feature."""
        descriptions = {
            "impressions": f"Total impressions: {features.get('impressions', 0):,}",
            "clicks": f"Total clicks: {features.get('clicks', 0):,}",
            "spend": f"Total spend: ${features.get('spend', 0):,.2f}",
            "ctr": f"Click-through rate: {features.get('ctr', 0):.2f}%",
            "impressions_log": "Log-transformed impression volume",
            "clicks_log": "Log-transformed click volume",
            "spend_log": "Log-transformed spend amount",
        }

        return descriptions.get(
            feature_name,
            f"Feature value: {features.get(feature_name, 'N/A')}",
        )


class ConversionOptimizer:
    """
    Provides recommendations for improving conversion rates.
    """

    def __init__(self):
        self.predictor = ConversionPredictor()

    async def get_recommendations(
        self,
        current_features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate recommendations for improving conversions.

        Args:
            current_features: Current campaign features

        Returns:
            Recommendations with expected impact
        """
        # Get current prediction
        current = await self.predictor.predict(current_features)

        recommendations = []

        # Check CTR
        ctr = current_features.get("ctr", 0)
        if ctr < 1.0:
            recommendations.append({
                "area": "Creative/Targeting",
                "recommendation": "Improve ad creative or refine audience targeting",
                "expected_impact": "Could increase conversions by 15-30%",
                "priority": "high",
            })

        # Check spend efficiency
        spend = current_features.get("spend", 0)
        clicks = current_features.get("clicks", 0)
        if clicks > 0 and spend / clicks > 2.5:
            recommendations.append({
                "area": "Bid Strategy",
                "recommendation": "Review bidding strategy to reduce CPC",
                "expected_impact": "Could improve ROI by 10-20%",
                "priority": "medium",
            })

        # Platform-specific recommendations
        platform = current_features.get("platform", "").lower()
        if platform == "meta":
            recommendations.append({
                "area": "Audience Expansion",
                "recommendation": "Test Advantage+ audiences for broader reach",
                "expected_impact": "Typically increases conversions by 10-25%",
                "priority": "medium",
            })
        elif platform == "google":
            recommendations.append({
                "area": "Search Terms",
                "recommendation": "Review and optimize search term match types",
                "expected_impact": "Can improve conversion rate by 5-15%",
                "priority": "medium",
            })

        return {
            "current_prediction": current,
            "recommendations": recommendations,
            "potential_uplift": self._calculate_potential_uplift(recommendations),
        }

    def _calculate_potential_uplift(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate potential conversion uplift from recommendations."""
        # Simplified uplift calculation
        high_priority = sum(1 for r in recommendations if r["priority"] == "high")
        medium_priority = sum(1 for r in recommendations if r["priority"] == "medium")

        min_uplift = high_priority * 0.10 + medium_priority * 0.05
        max_uplift = high_priority * 0.25 + medium_priority * 0.15

        return {
            "min_percent": round(min_uplift * 100, 1),
            "max_percent": round(max_uplift * 100, 1),
            "recommendations_count": len(recommendations),
        }
