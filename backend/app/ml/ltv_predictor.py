# =============================================================================
# Stratum AI - Customer Lifetime Value (LTV) Prediction Model
# =============================================================================
"""
Machine learning model for predicting customer lifetime value.

Provides:
- LTV prediction based on early customer behavior
- Cohort-based LTV analysis
- LTV/CAC ratio calculations
- Customer segmentation by predicted value
- Budget optimization based on predicted LTV
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import json
import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import ML libraries
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn not available. LTV prediction will use heuristic model.")


class CustomerSegment(str, Enum):
    """Customer value segments."""
    VIP = "vip"  # Top 5%
    HIGH_VALUE = "high_value"  # Top 25%
    MEDIUM_VALUE = "medium_value"  # 25-75%
    LOW_VALUE = "low_value"  # Bottom 25%
    AT_RISK = "at_risk"  # Declining value


class LTVTimeframe(str, Enum):
    """LTV prediction timeframes."""
    DAYS_30 = "30_day"
    DAYS_90 = "90_day"
    DAYS_180 = "180_day"
    DAYS_365 = "365_day"
    LIFETIME = "lifetime"


@dataclass
class CustomerBehavior:
    """Early customer behavior for LTV prediction."""
    customer_id: str
    acquisition_date: datetime
    acquisition_channel: str
    acquisition_campaign_id: Optional[str] = None

    # First purchase data
    first_order_value: float = 0.0
    first_order_items: int = 0
    first_order_category: Optional[str] = None

    # Early engagement (first 7-30 days)
    days_to_first_purchase: int = 0
    sessions_first_week: int = 0
    pages_viewed_first_week: int = 0
    email_opens_first_week: int = 0
    email_clicks_first_week: int = 0

    # Subsequent behavior (if available)
    total_orders: int = 1
    total_revenue: float = 0.0
    days_since_last_order: int = 0
    avg_order_value: float = 0.0
    order_frequency_days: float = 0.0

    # Demographics
    location_tier: str = "unknown"  # tier1, tier2, tier3
    device_type: str = "unknown"  # desktop, mobile, tablet


@dataclass
class LTVPrediction:
    """LTV prediction result."""
    customer_id: str
    predicted_ltv_30d: float
    predicted_ltv_90d: float
    predicted_ltv_180d: float
    predicted_ltv_365d: float
    predicted_ltv_lifetime: float
    confidence: float
    segment: CustomerSegment

    # Decomposition
    predicted_orders: float
    predicted_aov: float
    churn_probability: float

    # Recommendations
    recommended_cac_max: float  # Max CAC to maintain profitability
    ltv_cac_ratio: Optional[float] = None


@dataclass
class CohortAnalysis:
    """LTV analysis by cohort."""
    cohort_month: str
    customers: int
    total_revenue: float
    avg_ltv: float
    median_ltv: float
    ltv_p90: float
    avg_orders: float
    avg_retention_days: float
    segment_distribution: Dict[str, int]


class LTVPredictor:
    """
    Customer Lifetime Value prediction model.

    Uses a combination of:
    1. BG/NBD model concepts for purchase frequency
    2. Gamma-Gamma model concepts for monetary value
    3. Gradient boosting for overall LTV prediction

    Usage:
        predictor = LTVPredictor()

        # Predict LTV for a customer
        prediction = predictor.predict(customer_behavior)

        # Get segment distribution
        segments = predictor.segment_customers(customer_list)

        # Calculate optimal CAC
        max_cac = predictor.calculate_max_cac(predicted_ltv, target_ratio=3.0)
    """

    def __init__(self, models_path: str = "./models"):
        self.models_path = Path(models_path)
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = []

        # LTV multipliers by timeframe (based on typical retention curves)
        self.ltv_multipliers = {
            LTVTimeframe.DAYS_30: 1.0,
            LTVTimeframe.DAYS_90: 2.2,
            LTVTimeframe.DAYS_180: 3.5,
            LTVTimeframe.DAYS_365: 5.0,
            LTVTimeframe.LIFETIME: 8.0,
        }

        # Channel quality scores (based on typical performance)
        self.channel_quality = {
            "organic": 1.2,
            "referral": 1.3,
            "email": 1.1,
            "meta": 1.0,
            "google": 1.05,
            "tiktok": 0.9,
            "affiliate": 0.85,
            "unknown": 0.95,
        }

        self._load_model()

    def _load_model(self):
        """Load trained model if available."""
        model_path = self.models_path / "ltv_predictor.pkl"
        if model_path.exists() and ML_AVAILABLE:
            try:
                self.model = joblib.load(model_path)
                scaler_path = self.models_path / "ltv_predictor_scaler.pkl"
                if scaler_path.exists():
                    self.scaler = joblib.load(scaler_path)
                logger.info("Loaded LTV prediction model")
            except Exception as e:
                logger.warning(f"Could not load LTV model: {e}")

    def predict(self, behavior: CustomerBehavior) -> LTVPrediction:
        """
        Predict customer lifetime value.

        Args:
            behavior: Customer behavior data

        Returns:
            LTVPrediction with predicted values and segment
        """
        # Extract features
        features = self._extract_features(behavior)

        # Use ML model if available, otherwise use heuristic
        if self.model is not None and ML_AVAILABLE:
            base_ltv = self._ml_predict(features)
        else:
            base_ltv = self._heuristic_predict(behavior)

        # Calculate LTV for different timeframes
        ltv_30d = base_ltv
        ltv_90d = base_ltv * self.ltv_multipliers[LTVTimeframe.DAYS_90]
        ltv_180d = base_ltv * self.ltv_multipliers[LTVTimeframe.DAYS_180]
        ltv_365d = base_ltv * self.ltv_multipliers[LTVTimeframe.DAYS_365]
        ltv_lifetime = base_ltv * self.ltv_multipliers[LTVTimeframe.LIFETIME]

        # Calculate components
        predicted_orders = self._predict_orders(behavior)
        predicted_aov = self._predict_aov(behavior)
        churn_probability = self._predict_churn(behavior)

        # Adjust for churn
        retention_factor = 1 - (churn_probability * 0.5)
        ltv_lifetime *= retention_factor

        # Determine segment
        segment = self._determine_segment(ltv_365d)

        # Calculate confidence
        confidence = self._calculate_confidence(behavior)

        # Calculate max CAC (targeting 3:1 LTV:CAC ratio)
        recommended_cac_max = ltv_365d / 3.0

        return LTVPrediction(
            customer_id=behavior.customer_id,
            predicted_ltv_30d=round(ltv_30d, 2),
            predicted_ltv_90d=round(ltv_90d, 2),
            predicted_ltv_180d=round(ltv_180d, 2),
            predicted_ltv_365d=round(ltv_365d, 2),
            predicted_ltv_lifetime=round(ltv_lifetime, 2),
            confidence=round(confidence, 2),
            segment=segment,
            predicted_orders=round(predicted_orders, 1),
            predicted_aov=round(predicted_aov, 2),
            churn_probability=round(churn_probability, 2),
            recommended_cac_max=round(recommended_cac_max, 2),
        )

    def _extract_features(self, behavior: CustomerBehavior) -> np.ndarray:
        """Extract features for ML model."""
        features = [
            behavior.first_order_value,
            behavior.first_order_items,
            behavior.days_to_first_purchase,
            behavior.sessions_first_week,
            behavior.pages_viewed_first_week,
            behavior.email_opens_first_week,
            behavior.email_clicks_first_week,
            behavior.total_orders,
            behavior.total_revenue,
            behavior.avg_order_value,
            1 if behavior.device_type == "desktop" else 0,
            1 if behavior.device_type == "mobile" else 0,
            self.channel_quality.get(behavior.acquisition_channel.lower(), 1.0),
        ]

        return np.array(features).reshape(1, -1)

    def _ml_predict(self, features: np.ndarray) -> float:
        """Predict using ML model."""
        if self.scaler is not None:
            features = self.scaler.transform(features)

        prediction = self.model.predict(features)[0]
        return max(0, float(prediction))

    def _heuristic_predict(self, behavior: CustomerBehavior) -> float:
        """
        Heuristic-based LTV prediction when ML model is unavailable.

        Uses a simplified model based on:
        - First order value (30% weight)
        - Early engagement signals (25% weight)
        - Channel quality (20% weight)
        - Historical behavior if available (25% weight)
        """
        # Base prediction from first order
        base_ltv = behavior.first_order_value

        # Engagement multiplier
        engagement_score = 1.0
        if behavior.sessions_first_week >= 5:
            engagement_score += 0.3
        if behavior.email_opens_first_week >= 3:
            engagement_score += 0.2
        if behavior.email_clicks_first_week >= 1:
            engagement_score += 0.15

        # Quick conversion bonus
        if behavior.days_to_first_purchase <= 1:
            engagement_score += 0.2
        elif behavior.days_to_first_purchase <= 3:
            engagement_score += 0.1

        # Channel quality
        channel_multiplier = self.channel_quality.get(
            behavior.acquisition_channel.lower(), 1.0
        )

        # Historical behavior (if available)
        historical_multiplier = 1.0
        if behavior.total_orders > 1:
            # Repeat customer - higher LTV
            historical_multiplier = 1.0 + (behavior.total_orders * 0.2)
            historical_multiplier = min(historical_multiplier, 3.0)

        # AOV factor
        if behavior.avg_order_value > 0:
            aov_factor = behavior.avg_order_value / max(behavior.first_order_value, 1)
            aov_factor = min(aov_factor, 1.5)
        else:
            aov_factor = 1.0

        # Calculate 30-day LTV
        ltv_30d = (
            base_ltv
            * engagement_score
            * channel_multiplier
            * historical_multiplier
            * aov_factor
        )

        return max(0, ltv_30d)

    def _predict_orders(self, behavior: CustomerBehavior) -> float:
        """Predict number of future orders."""
        # Base prediction on current orders
        current_orders = behavior.total_orders

        # Engagement factor
        engagement = (
            behavior.sessions_first_week * 0.1 +
            behavior.email_opens_first_week * 0.15 +
            behavior.email_clicks_first_week * 0.2
        )

        # Quick conversion bonus
        conversion_factor = 1.0
        if behavior.days_to_first_purchase <= 1:
            conversion_factor = 1.3
        elif behavior.days_to_first_purchase <= 7:
            conversion_factor = 1.1

        # Predict annual orders
        predicted_annual = (
            current_orders +
            (engagement * conversion_factor * 2) +
            (current_orders * 0.5)  # Repeat rate estimate
        )

        return min(predicted_annual, 24)  # Cap at 2 orders/month

    def _predict_aov(self, behavior: CustomerBehavior) -> float:
        """Predict future average order value."""
        if behavior.avg_order_value > 0:
            return behavior.avg_order_value * 1.05  # Slight increase expected
        return behavior.first_order_value * 0.95  # Slight decrease from first order

    def _predict_churn(self, behavior: CustomerBehavior) -> float:
        """Predict churn probability."""
        churn_score = 0.3  # Base churn rate

        # Recency factor
        if behavior.days_since_last_order > 90:
            churn_score += 0.3
        elif behavior.days_since_last_order > 60:
            churn_score += 0.15
        elif behavior.days_since_last_order > 30:
            churn_score += 0.05

        # Engagement factor
        if behavior.email_opens_first_week < 2:
            churn_score += 0.1
        if behavior.sessions_first_week < 2:
            churn_score += 0.1

        # Repeat purchase factor
        if behavior.total_orders > 2:
            churn_score -= 0.15
        elif behavior.total_orders > 1:
            churn_score -= 0.1

        return max(0.1, min(0.9, churn_score))

    def _determine_segment(self, ltv_365d: float) -> CustomerSegment:
        """Determine customer segment based on predicted LTV."""
        # Thresholds (would be calibrated based on actual data)
        if ltv_365d >= 1000:
            return CustomerSegment.VIP
        elif ltv_365d >= 500:
            return CustomerSegment.HIGH_VALUE
        elif ltv_365d >= 200:
            return CustomerSegment.MEDIUM_VALUE
        else:
            return CustomerSegment.LOW_VALUE

    def _calculate_confidence(self, behavior: CustomerBehavior) -> float:
        """Calculate confidence in prediction."""
        confidence = 0.5  # Base confidence

        # More orders = more confidence
        if behavior.total_orders >= 3:
            confidence += 0.25
        elif behavior.total_orders >= 2:
            confidence += 0.15

        # More engagement data = more confidence
        if behavior.sessions_first_week > 0:
            confidence += 0.1
        if behavior.email_opens_first_week > 0:
            confidence += 0.1

        return min(0.95, confidence)

    def segment_customers(
        self,
        customers: List[CustomerBehavior],
    ) -> Dict[str, Any]:
        """
        Segment customers by predicted LTV.

        Returns:
            Dict with segment distribution and statistics
        """
        predictions = [self.predict(c) for c in customers]

        segments = {
            CustomerSegment.VIP: [],
            CustomerSegment.HIGH_VALUE: [],
            CustomerSegment.MEDIUM_VALUE: [],
            CustomerSegment.LOW_VALUE: [],
        }

        for pred in predictions:
            segments[pred.segment].append(pred)

        # Calculate statistics
        result = {
            "total_customers": len(customers),
            "segments": {},
            "total_predicted_ltv": sum(p.predicted_ltv_365d for p in predictions),
        }

        for segment, preds in segments.items():
            if preds:
                ltv_values = [p.predicted_ltv_365d for p in preds]
                result["segments"][segment.value] = {
                    "count": len(preds),
                    "percent": round(len(preds) / len(customers) * 100, 1),
                    "avg_ltv_365d": round(sum(ltv_values) / len(preds), 2),
                    "total_ltv": round(sum(ltv_values), 2),
                    "max_recommended_cac": round(
                        sum(p.recommended_cac_max for p in preds) / len(preds), 2
                    ),
                }

        return result

    def calculate_max_cac(
        self,
        predicted_ltv: float,
        target_ratio: float = 3.0,
        margin_percent: float = 30.0,
    ) -> Dict[str, float]:
        """
        Calculate maximum allowable CAC based on LTV.

        Args:
            predicted_ltv: Predicted customer lifetime value
            target_ratio: Target LTV:CAC ratio (default 3:1)
            margin_percent: Gross margin percentage

        Returns:
            Dict with CAC recommendations
        """
        # Basic max CAC based on ratio
        max_cac_ratio = predicted_ltv / target_ratio

        # Margin-adjusted max CAC
        margin = margin_percent / 100
        gross_profit = predicted_ltv * margin
        max_cac_profitable = gross_profit * 0.5  # Allow 50% of margin for acquisition

        return {
            "predicted_ltv": round(predicted_ltv, 2),
            "target_ltv_cac_ratio": target_ratio,
            "max_cac_by_ratio": round(max_cac_ratio, 2),
            "max_cac_profitable": round(max_cac_profitable, 2),
            "recommended_max_cac": round(min(max_cac_ratio, max_cac_profitable), 2),
        }

    def analyze_cohort(
        self,
        customers: List[CustomerBehavior],
    ) -> List[CohortAnalysis]:
        """
        Analyze LTV by acquisition cohort.

        Groups customers by acquisition month and calculates LTV metrics.
        """
        # Group by cohort month
        cohorts: Dict[str, List[CustomerBehavior]] = {}

        for customer in customers:
            cohort_key = customer.acquisition_date.strftime("%Y-%m")
            if cohort_key not in cohorts:
                cohorts[cohort_key] = []
            cohorts[cohort_key].append(customer)

        # Analyze each cohort
        analyses = []

        for cohort_month, cohort_customers in sorted(cohorts.items()):
            predictions = [self.predict(c) for c in cohort_customers]

            ltv_values = [p.predicted_ltv_365d for p in predictions]
            segments = [p.segment for p in predictions]

            segment_dist = {}
            for seg in CustomerSegment:
                segment_dist[seg.value] = sum(1 for s in segments if s == seg)

            analyses.append(CohortAnalysis(
                cohort_month=cohort_month,
                customers=len(cohort_customers),
                total_revenue=sum(c.total_revenue for c in cohort_customers),
                avg_ltv=round(sum(ltv_values) / len(ltv_values), 2),
                median_ltv=round(sorted(ltv_values)[len(ltv_values) // 2], 2),
                ltv_p90=round(sorted(ltv_values)[int(len(ltv_values) * 0.9)], 2) if len(ltv_values) > 1 else ltv_values[0],
                avg_orders=round(sum(c.total_orders for c in cohort_customers) / len(cohort_customers), 1),
                avg_retention_days=round(
                    sum(
                        (datetime.now(timezone.utc) - c.acquisition_date).days
                        for c in cohort_customers
                    ) / len(cohort_customers),
                    0
                ),
                segment_distribution=segment_dist,
            ))

        return analyses

    def train(self, training_data: pd.DataFrame) -> Dict[str, float]:
        """
        Train the LTV prediction model.

        Args:
            training_data: DataFrame with columns matching CustomerBehavior fields
                          plus 'actual_ltv_365d' target column

        Returns:
            Training metrics
        """
        if not ML_AVAILABLE:
            return {"error": "scikit-learn not available"}

        # Prepare features
        feature_cols = [
            "first_order_value",
            "first_order_items",
            "days_to_first_purchase",
            "sessions_first_week",
            "pages_viewed_first_week",
            "email_opens_first_week",
            "email_clicks_first_week",
            "total_orders",
            "total_revenue",
            "avg_order_value",
        ]

        # Filter available columns
        available_cols = [c for c in feature_cols if c in training_data.columns]
        self.feature_names = available_cols

        X = training_data[available_cols].values
        y = training_data["actual_ltv_365d"].values

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)

        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        metrics = {
            "r2": float(r2_score(y_test, y_pred)),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        }

        # Save model
        self.models_path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.models_path / "ltv_predictor.pkl")
        joblib.dump(self.scaler, self.models_path / "ltv_predictor_scaler.pkl")

        logger.info(f"Trained LTV model: R²={metrics['r2']:.3f}, MAE=${metrics['mae']:.2f}")

        return metrics


# Singleton instance
ltv_predictor = LTVPredictor()


# =============================================================================
# Convenience Functions
# =============================================================================

def predict_customer_ltv(
    customer_id: str,
    first_order_value: float,
    acquisition_channel: str,
    first_order_items: int = 1,
    days_to_first_purchase: int = 0,
    sessions_first_week: int = 1,
    **kwargs,
) -> Dict[str, Any]:
    """
    Predict LTV for a customer.

    Returns:
        Dict with LTV predictions and recommendations
    """
    behavior = CustomerBehavior(
        customer_id=customer_id,
        acquisition_date=datetime.now(timezone.utc),
        acquisition_channel=acquisition_channel,
        first_order_value=first_order_value,
        first_order_items=first_order_items,
        days_to_first_purchase=days_to_first_purchase,
        sessions_first_week=sessions_first_week,
        **kwargs,
    )

    prediction = ltv_predictor.predict(behavior)

    return {
        "customer_id": prediction.customer_id,
        "segment": prediction.segment.value,
        "predictions": {
            "ltv_30d": prediction.predicted_ltv_30d,
            "ltv_90d": prediction.predicted_ltv_90d,
            "ltv_180d": prediction.predicted_ltv_180d,
            "ltv_365d": prediction.predicted_ltv_365d,
            "ltv_lifetime": prediction.predicted_ltv_lifetime,
        },
        "components": {
            "predicted_orders": prediction.predicted_orders,
            "predicted_aov": prediction.predicted_aov,
            "churn_probability": prediction.churn_probability,
        },
        "recommendations": {
            "max_cac": prediction.recommended_cac_max,
        },
        "confidence": prediction.confidence,
    }


def get_ltv_based_max_cac(
    predicted_ltv: float,
    target_ratio: float = 3.0,
) -> float:
    """Calculate maximum CAC based on predicted LTV."""
    result = ltv_predictor.calculate_max_cac(predicted_ltv, target_ratio)
    return result["recommended_max_cac"]
