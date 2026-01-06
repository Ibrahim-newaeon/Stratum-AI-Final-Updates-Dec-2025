# =============================================================================
# Stratum AI - ML Model Explainability with SHAP
# =============================================================================
"""
SHAP (SHapley Additive exPlanations) integration for ML model explainability.

Provides:
- Feature importance explanations for individual predictions
- Global feature importance across all predictions
- Interaction effects between features
- User-friendly explanations for non-technical users
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import SHAP - it's optional
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not installed. Explainability features will use fallback methods.")


@dataclass
class FeatureContribution:
    """Contribution of a single feature to a prediction."""
    feature_name: str
    feature_value: Any
    contribution: float  # SHAP value (positive = increases prediction)
    contribution_percent: float  # Percentage of total impact
    direction: str  # "positive", "negative", "neutral"
    human_explanation: str  # User-friendly explanation


@dataclass
class PredictionExplanation:
    """Complete explanation for a single prediction."""
    prediction_id: str
    model_name: str
    predicted_value: float
    base_value: float  # Expected value (average prediction)

    # Feature contributions
    top_positive_factors: List[FeatureContribution]
    top_negative_factors: List[FeatureContribution]
    all_contributions: List[FeatureContribution]

    # Summary
    confidence_score: float  # How reliable is this prediction
    explanation_summary: str  # One-line summary
    detailed_explanation: str  # Paragraph explanation

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GlobalExplanation:
    """Global explanation across many predictions."""
    model_name: str
    num_samples: int

    # Feature importance
    feature_importance: Dict[str, float]  # feature -> mean |SHAP value|
    feature_importance_ranked: List[Tuple[str, float]]

    # Interaction effects
    top_interactions: List[Tuple[str, str, float]]  # (feature1, feature2, strength)

    # Summary
    key_drivers: List[str]
    summary: str


class ModelExplainer:
    """
    Explains ML model predictions using SHAP values.

    Usage:
        explainer = ModelExplainer("roas_predictor")

        # Explain a single prediction
        explanation = explainer.explain_prediction(
            features={"spend": 1000, "ctr": 2.5, ...},
            prediction=2.3
        )

        # Get global feature importance
        global_exp = explainer.get_global_explanation(X_sample)
    """

    def __init__(self, model_name: str, models_path: str = "./models"):
        self.model_name = model_name
        self.models_path = Path(models_path)

        self.model = None
        self.scaler = None
        self.imputer = None
        self.feature_names: List[str] = []
        self.shap_explainer = None
        self.base_value = 0.0

        self._load_model()

    def _load_model(self):
        """Load model and metadata."""
        try:
            # Load model
            model_path = self.models_path / f"{self.model_name}.pkl"
            if model_path.exists():
                self.model = joblib.load(model_path)

            # Load scaler
            scaler_path = self.models_path / f"{self.model_name}_scaler.pkl"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)

            # Load imputer
            imputer_path = self.models_path / f"{self.model_name}_imputer.pkl"
            if imputer_path.exists():
                self.imputer = joblib.load(imputer_path)

            # Load metadata
            metadata_path = self.models_path / f"{self.model_name}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    self.feature_names = metadata.get("features", [])

            logger.info(f"Loaded model {self.model_name} with {len(self.feature_names)} features")

        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")

    def _init_shap_explainer(self, X_background: np.ndarray):
        """Initialize SHAP explainer with background data."""
        if not SHAP_AVAILABLE or self.model is None:
            return

        try:
            # Use TreeExplainer for tree-based models, KernelExplainer otherwise
            model_type = type(self.model).__name__

            if "Gradient" in model_type or "Forest" in model_type or "Tree" in model_type:
                self.shap_explainer = shap.TreeExplainer(self.model)
            else:
                # Use a sample of background data for KernelExplainer
                background = shap.sample(X_background, min(100, len(X_background)))
                self.shap_explainer = shap.KernelExplainer(self.model.predict, background)

            # Calculate base value
            if hasattr(self.shap_explainer, 'expected_value'):
                ev = self.shap_explainer.expected_value
                self.base_value = float(ev) if np.isscalar(ev) else float(ev[0])

            logger.info(f"Initialized SHAP explainer for {self.model_name}")

        except Exception as e:
            logger.error(f"Error initializing SHAP explainer: {e}")
            self.shap_explainer = None

    def explain_prediction(
        self,
        features: Dict[str, Any],
        prediction: Optional[float] = None,
        prediction_id: Optional[str] = None,
        top_k: int = 5,
    ) -> PredictionExplanation:
        """
        Explain a single prediction.

        Args:
            features: Dict of feature name -> value
            prediction: The predicted value (will compute if not provided)
            prediction_id: Optional ID for tracking
            top_k: Number of top factors to highlight

        Returns:
            PredictionExplanation with feature contributions
        """
        if prediction_id is None:
            prediction_id = f"pred_{datetime.now(timezone.utc).timestamp()}"

        # Prepare feature vector
        X = self._prepare_features(features)

        # Get prediction if not provided
        if prediction is None and self.model is not None:
            prediction = float(self.model.predict(X)[0])

        # Calculate SHAP values or use fallback
        contributions = self._calculate_contributions(X, features)

        # Sort by absolute contribution
        sorted_contribs = sorted(contributions, key=lambda x: abs(x.contribution), reverse=True)

        # Split into positive and negative
        positive = [c for c in sorted_contribs if c.contribution > 0][:top_k]
        negative = [c for c in sorted_contribs if c.contribution < 0][:top_k]

        # Calculate confidence based on feature coverage
        confidence = self._calculate_confidence(features)

        # Generate explanations
        summary = self._generate_summary(prediction, positive, negative)
        detailed = self._generate_detailed_explanation(prediction, sorted_contribs[:10])

        return PredictionExplanation(
            prediction_id=prediction_id,
            model_name=self.model_name,
            predicted_value=prediction,
            base_value=self.base_value,
            top_positive_factors=positive,
            top_negative_factors=negative,
            all_contributions=sorted_contribs,
            confidence_score=confidence,
            explanation_summary=summary,
            detailed_explanation=detailed,
        )

    def _prepare_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Prepare feature dict as model input."""
        # Create feature vector in correct order
        X = np.zeros((1, len(self.feature_names)))

        for i, name in enumerate(self.feature_names):
            if name in features:
                X[0, i] = features[name]

        # Apply imputer if available
        if self.imputer is not None:
            X = self.imputer.transform(X)

        # Apply scaler if available
        if self.scaler is not None:
            X = self.scaler.transform(X)

        return X

    def _calculate_contributions(
        self,
        X: np.ndarray,
        features: Dict[str, Any],
    ) -> List[FeatureContribution]:
        """Calculate feature contributions using SHAP or fallback."""
        contributions = []

        if SHAP_AVAILABLE and self.shap_explainer is not None:
            # Use SHAP values
            try:
                shap_values = self.shap_explainer.shap_values(X)
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]
                shap_values = shap_values.flatten()

                total_impact = sum(abs(v) for v in shap_values)

                for i, name in enumerate(self.feature_names):
                    value = features.get(name, 0)
                    contrib = float(shap_values[i])
                    pct = (abs(contrib) / total_impact * 100) if total_impact > 0 else 0

                    contributions.append(FeatureContribution(
                        feature_name=name,
                        feature_value=value,
                        contribution=contrib,
                        contribution_percent=round(pct, 1),
                        direction="positive" if contrib > 0.01 else "negative" if contrib < -0.01 else "neutral",
                        human_explanation=self._explain_feature(name, value, contrib),
                    ))

            except Exception as e:
                logger.warning(f"SHAP calculation failed, using fallback: {e}")
                contributions = self._fallback_contributions(features)
        else:
            contributions = self._fallback_contributions(features)

        return contributions

    def _fallback_contributions(self, features: Dict[str, Any]) -> List[FeatureContribution]:
        """Fallback contribution calculation when SHAP is unavailable."""
        contributions = []

        # Use feature importance from model if available
        importances = {}
        if hasattr(self.model, 'feature_importances_'):
            for i, name in enumerate(self.feature_names):
                if i < len(self.model.feature_importances_):
                    importances[name] = self.model.feature_importances_[i]

        total_importance = sum(importances.values()) if importances else 1.0

        for name in self.feature_names:
            value = features.get(name, 0)
            importance = importances.get(name, 1.0 / len(self.feature_names))

            # Estimate contribution direction based on value
            # This is a simplified heuristic
            if "roas" in name or "revenue" in name or "conversion" in name:
                direction = "positive" if value > 0 else "neutral"
                contrib = importance * (1 if value > 0 else -0.5)
            elif "cost" in name or "cpa" in name or "spend" in name:
                direction = "negative" if value > 100 else "neutral"
                contrib = -importance if value > 100 else importance * 0.5
            else:
                direction = "neutral"
                contrib = importance * 0.1

            pct = (importance / total_importance * 100) if total_importance > 0 else 0

            contributions.append(FeatureContribution(
                feature_name=name,
                feature_value=value,
                contribution=contrib,
                contribution_percent=round(pct, 1),
                direction=direction,
                human_explanation=self._explain_feature(name, value, contrib),
            ))

        return contributions

    def _explain_feature(self, name: str, value: Any, contribution: float) -> str:
        """Generate human-readable explanation for a feature."""
        direction = "increases" if contribution > 0 else "decreases"
        impact = "significantly" if abs(contribution) > 0.1 else "slightly"

        # Feature-specific explanations
        explanations = {
            "ctr": f"Click-through rate of {value:.2f}% {impact} {direction} predicted ROAS",
            "cvr": f"Conversion rate of {value:.2f}% {impact} {direction} predicted ROAS",
            "cpc": f"Cost per click of ${value:.2f} {impact} {direction} predicted ROAS",
            "cpm": f"CPM of ${value:.2f} {impact} {direction} predicted ROAS",
            "log_spend": f"Spend level {impact} {direction} predicted ROAS",
            "roas_7d_avg": f"7-day average ROAS of {value:.2f} {impact} {direction} prediction",
            "creative_video": f"Video creative {impact} {direction} predicted ROAS" if value else "Non-video creative",
            "audience_retargeting": f"Retargeting audience {impact} {direction} predicted ROAS" if value else "Non-retargeting audience",
            "platform_meta": f"Meta platform {impact} {direction} predicted ROAS" if value else "",
            "platform_google": f"Google platform {impact} {direction} predicted ROAS" if value else "",
            "is_weekend": f"Weekend timing {impact} {direction} predicted ROAS" if value else "Weekday timing",
        }

        # Check for partial matches
        for key, explanation in explanations.items():
            if key in name.lower():
                return explanation

        # Default explanation
        return f"{name} = {value} {impact} {direction} the prediction"

    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """Calculate confidence score based on feature coverage and values."""
        # Check how many expected features are present
        present = sum(1 for name in self.feature_names if name in features and features[name] is not None)
        coverage = present / len(self.feature_names) if self.feature_names else 0

        # Check for extreme values
        extreme_penalty = 0
        for name, value in features.items():
            if isinstance(value, (int, float)):
                if value > 1000 or value < -1000:
                    extreme_penalty += 0.05

        confidence = max(0.0, min(1.0, coverage - extreme_penalty))
        return round(confidence, 2)

    def _generate_summary(
        self,
        prediction: float,
        positive: List[FeatureContribution],
        negative: List[FeatureContribution],
    ) -> str:
        """Generate one-line summary."""
        if not positive and not negative:
            return f"Predicted ROAS: {prediction:.2f}"

        top_positive = positive[0].feature_name if positive else None
        top_negative = negative[0].feature_name if negative else None

        parts = [f"Predicted ROAS: {prediction:.2f}"]

        if top_positive:
            parts.append(f"boosted by {self._friendly_name(top_positive)}")
        if top_negative:
            parts.append(f"limited by {self._friendly_name(top_negative)}")

        return ", ".join(parts)

    def _generate_detailed_explanation(
        self,
        prediction: float,
        contributions: List[FeatureContribution],
    ) -> str:
        """Generate detailed paragraph explanation."""
        lines = [f"The model predicts a ROAS of {prediction:.2f}."]

        positive = [c for c in contributions if c.contribution > 0.01]
        negative = [c for c in contributions if c.contribution < -0.01]

        if positive:
            factors = [c.feature_name for c in positive[:3]]
            lines.append(f"Key factors driving this prediction higher: {', '.join(self._friendly_name(f) for f in factors)}.")

        if negative:
            factors = [c.feature_name for c in negative[:3]]
            lines.append(f"Factors limiting the prediction: {', '.join(self._friendly_name(f) for f in factors)}.")

        # Add specific insights
        for c in contributions[:5]:
            if c.contribution_percent > 10:
                lines.append(c.human_explanation + ".")

        return " ".join(lines)

    def _friendly_name(self, feature_name: str) -> str:
        """Convert feature name to user-friendly name."""
        friendly_names = {
            "ctr": "click-through rate",
            "cvr": "conversion rate",
            "cpc": "cost per click",
            "cpm": "cost per thousand impressions",
            "cpa": "cost per acquisition",
            "log_spend": "spend level",
            "log_impressions": "impression volume",
            "roas_7d_avg": "recent ROAS trend",
            "creative_video": "video creative",
            "creative_image": "image creative",
            "audience_retargeting": "retargeting audience",
            "audience_lookalike": "lookalike audience",
            "platform_meta": "Meta platform",
            "platform_google": "Google platform",
            "platform_tiktok": "TikTok platform",
            "is_weekend": "weekend timing",
            "objective_conversions": "conversion objective",
        }

        for key, friendly in friendly_names.items():
            if key in feature_name.lower():
                return friendly

        return feature_name.replace("_", " ")

    def get_global_explanation(
        self,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> GlobalExplanation:
        """
        Get global feature importance across many predictions.

        Args:
            X: Feature matrix (n_samples, n_features)
            feature_names: Optional feature names

        Returns:
            GlobalExplanation with feature importance and interactions
        """
        if feature_names is None:
            feature_names = self.feature_names

        # Initialize explainer if needed
        if self.shap_explainer is None:
            self._init_shap_explainer(X)

        feature_importance = {}

        if SHAP_AVAILABLE and self.shap_explainer is not None:
            try:
                shap_values = self.shap_explainer.shap_values(X)
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]

                # Calculate mean absolute SHAP value per feature
                mean_abs_shap = np.abs(shap_values).mean(axis=0)

                for i, name in enumerate(feature_names):
                    if i < len(mean_abs_shap):
                        feature_importance[name] = float(mean_abs_shap[i])

            except Exception as e:
                logger.warning(f"SHAP global calculation failed: {e}")
                feature_importance = self._fallback_importance()
        else:
            feature_importance = self._fallback_importance()

        # Sort by importance
        ranked = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        # Get top interactions (simplified)
        top_interactions = self._estimate_interactions(feature_importance)

        # Identify key drivers
        key_drivers = [name for name, _ in ranked[:5]]

        # Generate summary
        summary = self._generate_global_summary(ranked[:10], len(X))

        return GlobalExplanation(
            model_name=self.model_name,
            num_samples=len(X),
            feature_importance=feature_importance,
            feature_importance_ranked=ranked,
            top_interactions=top_interactions,
            key_drivers=key_drivers,
            summary=summary,
        )

    def _fallback_importance(self) -> Dict[str, float]:
        """Fallback feature importance from model."""
        importance = {}

        if hasattr(self.model, 'feature_importances_'):
            for i, name in enumerate(self.feature_names):
                if i < len(self.model.feature_importances_):
                    importance[name] = float(self.model.feature_importances_[i])
        else:
            # Equal importance as last resort
            for name in self.feature_names:
                importance[name] = 1.0 / len(self.feature_names)

        return importance

    def _estimate_interactions(
        self,
        importance: Dict[str, float],
    ) -> List[Tuple[str, str, float]]:
        """Estimate feature interactions based on importance."""
        # Simplified: pair top features
        ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

        interactions = []
        for i, (name1, imp1) in enumerate(ranked):
            for name2, imp2 in ranked[i+1:i+3]:
                # Estimate interaction as product of importances
                strength = (imp1 * imp2) ** 0.5
                interactions.append((name1, name2, round(strength, 4)))

        return sorted(interactions, key=lambda x: x[2], reverse=True)[:5]

    def _generate_global_summary(
        self,
        ranked: List[Tuple[str, float]],
        num_samples: int,
    ) -> str:
        """Generate global explanation summary."""
        if not ranked:
            return "No feature importance data available."

        top_features = [self._friendly_name(name) for name, _ in ranked[:3]]

        return (
            f"Based on analysis of {num_samples} predictions, the most important factors "
            f"driving {self.model_name} predictions are: {', '.join(top_features)}. "
            f"Together, these features account for the majority of prediction variance."
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def explain_roas_prediction(
    features: Dict[str, Any],
    prediction: float,
    models_path: str = "./models",
) -> Dict[str, Any]:
    """
    Explain a ROAS prediction.

    Args:
        features: Feature values used for prediction
        prediction: The ROAS prediction value
        models_path: Path to models directory

    Returns:
        Dict with explanation details
    """
    explainer = ModelExplainer("roas_predictor", models_path)
    explanation = explainer.explain_prediction(features, prediction)

    return {
        "prediction": explanation.predicted_value,
        "confidence": explanation.confidence_score,
        "summary": explanation.explanation_summary,
        "detailed_explanation": explanation.detailed_explanation,
        "top_positive_factors": [
            {
                "feature": c.feature_name,
                "value": c.feature_value,
                "impact_percent": c.contribution_percent,
                "explanation": c.human_explanation,
            }
            for c in explanation.top_positive_factors
        ],
        "top_negative_factors": [
            {
                "feature": c.feature_name,
                "value": c.feature_value,
                "impact_percent": c.contribution_percent,
                "explanation": c.human_explanation,
            }
            for c in explanation.top_negative_factors
        ],
    }


def get_model_feature_importance(
    model_name: str = "roas_predictor",
    models_path: str = "./models",
) -> Dict[str, float]:
    """
    Get global feature importance for a model.

    Returns:
        Dict of feature name -> importance score
    """
    explainer = ModelExplainer(model_name, models_path)
    return explainer._fallback_importance()
