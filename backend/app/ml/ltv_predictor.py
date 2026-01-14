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

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
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


# =============================================================================
# Advanced LTV Features (P2 Enhancement)
# =============================================================================

@dataclass
class SurvivalPrediction:
    """Customer survival (retention) prediction."""
    customer_id: str
    survival_probability_30d: float
    survival_probability_90d: float
    survival_probability_180d: float
    survival_probability_365d: float
    median_lifetime_days: int
    risk_level: str  # low, medium, high
    factors: List[str]


@dataclass
class LTVConfidenceInterval:
    """LTV prediction with uncertainty quantification."""
    point_estimate: float
    lower_bound_90: float
    upper_bound_90: float
    lower_bound_95: float
    upper_bound_95: float
    confidence_level: float
    uncertainty_factors: List[str]


@dataclass
class CohortLTVTrajectory:
    """LTV trajectory for a customer cohort."""
    cohort_id: str
    acquisition_period: str
    customer_count: int
    ltv_by_month: Dict[int, float]  # month -> cumulative LTV
    projected_ltv: float
    actual_vs_projected: Optional[float]


class ParetoNBDModel:
    """
    Pareto/NBD (Negative Binomial Distribution) model for CLV prediction.

    Implements the classic RFM-based probabilistic model for:
    - Predicting future purchases
    - Estimating customer lifetime
    - Calculating expected transactions
    """

    def __init__(self):
        # Model parameters (would be fitted from data in production)
        self.r = 0.5  # Shape parameter for purchase frequency
        self.alpha = 10.0  # Scale parameter for purchase frequency
        self.s = 0.5  # Shape parameter for dropout
        self.beta = 10.0  # Scale parameter for dropout

    def fit(self, transactions: List[Dict[str, Any]]):
        """Fit model parameters from transaction data."""
        # In production, this would use MLE or MCMC
        # Simplified: adjust parameters based on data characteristics

        if not transactions:
            return

        # Calculate recency, frequency for each customer
        customer_stats = {}
        for t in transactions:
            cid = t.get("customer_id")
            if cid not in customer_stats:
                customer_stats[cid] = {"count": 0, "first": None, "last": None}

            customer_stats[cid]["count"] += 1
            date = t.get("date")
            if date:
                if customer_stats[cid]["first"] is None or date < customer_stats[cid]["first"]:
                    customer_stats[cid]["first"] = date
                if customer_stats[cid]["last"] is None or date > customer_stats[cid]["last"]:
                    customer_stats[cid]["last"] = date

        # Adjust parameters based on observed patterns
        frequencies = [s["count"] for s in customer_stats.values()]
        avg_freq = statistics.mean(frequencies) if frequencies else 1

        # Simple parameter adjustment
        self.r = min(2, avg_freq / 5)
        self.alpha = max(5, 20 / avg_freq)

    def predict_transactions(
        self,
        frequency: int,
        recency_days: int,
        tenure_days: int,
        future_days: int = 365,
    ) -> float:
        """Predict expected number of future transactions."""
        if tenure_days <= 0:
            return frequency * (future_days / 365)

        # Simplified Pareto/NBD expected transactions
        # E[X(t, t+T)] = (a / (r - 1)) * [1 - ((beta + t) / (beta + t + T))^(r-1)]

        t = tenure_days / 365
        T = future_days / 365
        x = frequency

        # Probability customer is still active
        p_active = 1 - self._probability_alive(x, recency_days, tenure_days)

        if p_active < 0.1:
            return 0

        # Expected transactions if active
        lambda_estimate = (x + self.r) / (t + self.alpha)
        expected = lambda_estimate * T * p_active

        return max(0, expected)

    def _probability_alive(self, frequency: int, recency_days: int, tenure_days: int) -> float:
        """Calculate probability that customer has churned."""
        if tenure_days <= 0:
            return 0

        # Simplified P(alive)
        recency_ratio = recency_days / tenure_days
        frequency_factor = min(1, frequency / 10)

        # High recency = likely churned
        # High frequency = likely still active
        p_churned = recency_ratio * (1 - frequency_factor * 0.5)

        return min(0.95, max(0.05, p_churned))


class SurvivalAnalyzer:
    """
    Survival analysis for customer retention prediction.

    Uses Kaplan-Meier style analysis to predict:
    - Probability of customer remaining active
    - Expected customer lifetime
    - Churn risk factors
    """

    def __init__(self):
        self._survival_curves: Dict[str, List[Tuple[int, float]]] = {}

    def build_survival_curve(
        self,
        segment: str,
        customer_lifetimes: List[int],  # Days until churn (or censored)
        is_churned: List[bool],
    ):
        """Build survival curve from historical data."""
        if len(customer_lifetimes) != len(is_churned):
            return

        # Sort by lifetime
        data = sorted(zip(customer_lifetimes, is_churned))

        n = len(data)
        at_risk = n
        survival_prob = 1.0
        curve = [(0, 1.0)]

        for lifetime, churned in data:
            if churned:
                survival_prob *= (at_risk - 1) / at_risk
                curve.append((lifetime, survival_prob))
            at_risk -= 1

        self._survival_curves[segment] = curve

    def predict_survival(
        self,
        customer_id: str,
        segment: str,
        current_tenure_days: int,
    ) -> SurvivalPrediction:
        """Predict customer survival probabilities."""
        curve = self._survival_curves.get(segment)

        if not curve:
            # Default survival estimates
            base = 0.9 ** (current_tenure_days / 90)
            return SurvivalPrediction(
                customer_id=customer_id,
                survival_probability_30d=min(0.95, base * 0.95),
                survival_probability_90d=min(0.90, base * 0.85),
                survival_probability_180d=min(0.80, base * 0.70),
                survival_probability_365d=min(0.60, base * 0.50),
                median_lifetime_days=365,
                risk_level="medium",
                factors=["Using default model - segment data not available"],
            )

        # Interpolate from curve
        def get_prob(target_days: int) -> float:
            days_from_now = current_tenure_days + target_days
            for i, (day, prob) in enumerate(curve):
                if day >= days_from_now:
                    if i == 0:
                        return prob
                    prev_day, prev_prob = curve[i-1]
                    # Linear interpolation
                    ratio = (days_from_now - prev_day) / max(1, day - prev_day)
                    return prev_prob - ratio * (prev_prob - prob)
            return curve[-1][1] if curve else 0.5

        s30 = get_prob(30)
        s90 = get_prob(90)
        s180 = get_prob(180)
        s365 = get_prob(365)

        # Calculate median lifetime
        median_days = 365
        for day, prob in curve:
            if prob <= 0.5:
                median_days = day
                break

        # Determine risk level
        risk_level = "low"
        if s90 < 0.5:
            risk_level = "high"
        elif s90 < 0.7:
            risk_level = "medium"

        factors = []
        if s30 < 0.9:
            factors.append("High short-term churn risk")
        if s365 < 0.3:
            factors.append("Low long-term retention expected")
        if not factors:
            factors.append("Retention profile looks healthy")

        return SurvivalPrediction(
            customer_id=customer_id,
            survival_probability_30d=round(s30, 3),
            survival_probability_90d=round(s90, 3),
            survival_probability_180d=round(s180, 3),
            survival_probability_365d=round(s365, 3),
            median_lifetime_days=median_days,
            risk_level=risk_level,
            factors=factors,
        )


class LTVUncertaintyQuantifier:
    """
    Quantifies uncertainty in LTV predictions.

    Provides:
    - Confidence intervals
    - Prediction intervals
    - Uncertainty sources
    """

    def __init__(self):
        self._prediction_errors: List[float] = []

    def record_prediction_error(self, predicted: float, actual: float):
        """Record prediction error for calibration."""
        error = actual - predicted
        self._prediction_errors.append(error)

        # Keep last 1000
        if len(self._prediction_errors) > 1000:
            self._prediction_errors = self._prediction_errors[-1000:]

    def quantify_uncertainty(
        self,
        point_estimate: float,
        data_points: int,
        feature_completeness: float = 1.0,
    ) -> LTVConfidenceInterval:
        """Calculate confidence intervals for LTV prediction."""
        # Base uncertainty from historical errors
        if self._prediction_errors:
            std_error = statistics.stdev(self._prediction_errors)
        else:
            # Default uncertainty: 30% of prediction
            std_error = point_estimate * 0.3

        # Adjust for data quality
        data_multiplier = 1 + (1 / max(data_points, 1))
        completeness_multiplier = 1 + (1 - feature_completeness)

        adjusted_std = std_error * data_multiplier * completeness_multiplier

        # Calculate intervals
        z_90 = 1.645
        z_95 = 1.96

        lower_90 = max(0, point_estimate - z_90 * adjusted_std)
        upper_90 = point_estimate + z_90 * adjusted_std

        lower_95 = max(0, point_estimate - z_95 * adjusted_std)
        upper_95 = point_estimate + z_95 * adjusted_std

        # Confidence level based on data quality
        confidence = min(0.95, 0.5 + data_points / 200 * 0.3 + feature_completeness * 0.15)

        # Identify uncertainty factors
        factors = []
        if data_points < 10:
            factors.append("Limited historical data")
        if feature_completeness < 0.8:
            factors.append("Missing customer features")
        if std_error > point_estimate * 0.5:
            factors.append("High historical prediction variance")
        if not factors:
            factors.append("Prediction confidence is high")

        return LTVConfidenceInterval(
            point_estimate=round(point_estimate, 2),
            lower_bound_90=round(lower_90, 2),
            upper_bound_90=round(upper_90, 2),
            lower_bound_95=round(lower_95, 2),
            upper_bound_95=round(upper_95, 2),
            confidence_level=round(confidence, 3),
            uncertainty_factors=factors,
        )


class CohortLTVTracker:
    """
    Tracks LTV trajectories for customer cohorts.

    Enables:
    - Cohort comparison
    - LTV curve analysis
    - Early vs late cohort performance
    """

    def __init__(self):
        self._cohort_data: Dict[str, Dict[int, List[float]]] = {}

    def record_cohort_ltv(
        self,
        cohort_id: str,
        month_number: int,
        ltv_values: List[float],
    ):
        """Record LTV values for a cohort at a specific month."""
        if cohort_id not in self._cohort_data:
            self._cohort_data[cohort_id] = {}

        self._cohort_data[cohort_id][month_number] = ltv_values

    def get_cohort_trajectory(
        self,
        cohort_id: str,
        acquisition_period: str,
    ) -> CohortLTVTrajectory:
        """Get LTV trajectory for a cohort."""
        data = self._cohort_data.get(cohort_id, {})

        if not data:
            return CohortLTVTrajectory(
                cohort_id=cohort_id,
                acquisition_period=acquisition_period,
                customer_count=0,
                ltv_by_month={},
                projected_ltv=0,
                actual_vs_projected=None,
            )

        # Calculate average LTV at each month
        ltv_by_month = {}
        for month, values in sorted(data.items()):
            ltv_by_month[month] = round(statistics.mean(values), 2) if values else 0

        customer_count = len(data.get(1, []))

        # Project future LTV using growth rate
        if len(ltv_by_month) >= 3:
            months = sorted(ltv_by_month.keys())
            recent_growth = []
            for i in range(1, min(4, len(months))):
                m1, m2 = months[i-1], months[i]
                if ltv_by_month[m1] > 0:
                    growth = (ltv_by_month[m2] - ltv_by_month[m1]) / ltv_by_month[m1]
                    recent_growth.append(growth)

            avg_growth = statistics.mean(recent_growth) if recent_growth else 0.05
            last_ltv = ltv_by_month[months[-1]]
            months_to_project = 12 - len(months)
            projected_ltv = last_ltv * (1 + avg_growth) ** months_to_project
        else:
            projected_ltv = ltv_by_month.get(max(ltv_by_month.keys()), 0) * 1.5

        return CohortLTVTrajectory(
            cohort_id=cohort_id,
            acquisition_period=acquisition_period,
            customer_count=customer_count,
            ltv_by_month=ltv_by_month,
            projected_ltv=round(projected_ltv, 2),
            actual_vs_projected=None,
        )

    def compare_cohorts(
        self,
        cohort_ids: List[str],
        at_month: int = 6,
    ) -> Dict[str, Any]:
        """Compare LTV across cohorts at a specific month."""
        comparison = {}

        for cohort_id in cohort_ids:
            data = self._cohort_data.get(cohort_id, {})
            if at_month in data:
                values = data[at_month]
                comparison[cohort_id] = {
                    "avg_ltv": round(statistics.mean(values), 2) if values else 0,
                    "customer_count": len(values),
                    "ltv_std": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                }

        if comparison:
            best_cohort = max(comparison, key=lambda c: comparison[c]["avg_ltv"])
            worst_cohort = min(comparison, key=lambda c: comparison[c]["avg_ltv"])

            return {
                "month": at_month,
                "cohorts": comparison,
                "best_performer": best_cohort,
                "worst_performer": worst_cohort,
                "ltv_range": comparison[best_cohort]["avg_ltv"] - comparison[worst_cohort]["avg_ltv"],
            }

        return {"month": at_month, "cohorts": {}, "message": "No data available"}


# Singleton instances for P2 enhancements
pareto_nbd_model = ParetoNBDModel()
survival_analyzer = SurvivalAnalyzer()
ltv_uncertainty_quantifier = LTVUncertaintyQuantifier()
cohort_ltv_tracker = CohortLTVTracker()
