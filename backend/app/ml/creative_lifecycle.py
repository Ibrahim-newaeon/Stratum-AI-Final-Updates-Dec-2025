# =============================================================================
# Stratum AI - Creative Lifecycle & Fatigue Prediction
# =============================================================================
"""
ML-based creative fatigue prediction and lifecycle management.

Features:
- Predict time until creative fatigue
- Model creative performance decay curves
- Cluster similar creatives to learn patterns
- Proactive refresh recommendations
- Budget-aware creative rotation suggestions
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import math

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import ML libraries
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from scipy.optimize import curve_fit
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn/scipy not available. Using heuristic predictions.")


class LifecyclePhase(str, Enum):
    """Creative lifecycle phases."""
    LEARNING = "learning"       # Days 1-3: Algorithm learning
    GROWTH = "growth"           # Days 4-7: Performance increasing
    MATURITY = "maturity"       # Days 8-14: Peak performance
    DECLINE = "decline"         # Days 15+: Performance decreasing
    FATIGUE = "fatigue"         # Performance dropped significantly


class RefreshUrgency(str, Enum):
    """Urgency level for creative refresh."""
    IMMEDIATE = "immediate"     # Refresh now
    SOON = "soon"              # Refresh within 3 days
    PLANNED = "planned"        # Schedule refresh for next week
    MONITOR = "monitor"        # Watch but no action needed
    HEALTHY = "healthy"        # No refresh needed


@dataclass
class CreativePerformanceHistory:
    """Historical performance data for a creative."""
    creative_id: str
    creative_name: str
    platform: str
    creative_type: str  # image, video, carousel

    # Daily metrics (lists, index 0 = day 1)
    dates: List[datetime] = field(default_factory=list)
    impressions: List[int] = field(default_factory=list)
    clicks: List[int] = field(default_factory=list)
    conversions: List[int] = field(default_factory=list)
    spend: List[float] = field(default_factory=list)
    ctr: List[float] = field(default_factory=list)
    cvr: List[float] = field(default_factory=list)
    cpa: List[float] = field(default_factory=list)
    roas: List[float] = field(default_factory=list)
    frequency: List[float] = field(default_factory=list)

    # Metadata
    launch_date: Optional[datetime] = None
    total_spend: float = 0.0
    days_active: int = 0


@dataclass
class FatiguePrediction:
    """Prediction result for creative fatigue."""
    creative_id: str
    creative_name: str

    # Current state
    current_phase: LifecyclePhase
    current_fatigue_score: float
    days_active: int

    # Predictions
    days_until_fatigue: int
    predicted_fatigue_date: datetime
    confidence: float

    # Performance projections
    projected_ctr_7d: float
    projected_roas_7d: float
    projected_cpa_7d: float

    # Recommendations
    refresh_urgency: RefreshUrgency
    recommendations: List[str]
    estimated_performance_loss_if_not_refreshed: float  # % loss in next 7 days

    # Decay model parameters (if fitted)
    decay_rate: Optional[float] = None
    peak_day: Optional[int] = None
    peak_ctr: Optional[float] = None


@dataclass
class CreativeCluster:
    """A cluster of similar creatives."""
    cluster_id: int
    creatives: List[str]  # creative_ids
    avg_days_to_fatigue: float
    avg_peak_day: float
    avg_peak_ctr: float
    decay_rate: float
    platform_distribution: Dict[str, int]
    type_distribution: Dict[str, int]


class CreativeLifecyclePredictor:
    """
    ML-based creative lifecycle and fatigue predictor.

    Uses historical creative performance data to:
    1. Model decay curves
    2. Predict time to fatigue
    3. Cluster similar creatives
    4. Provide proactive recommendations

    Usage:
        predictor = CreativeLifecyclePredictor()

        # Predict fatigue for a creative
        prediction = predictor.predict_fatigue(creative_history)

        # Get rotation recommendations
        rotation = predictor.get_rotation_plan(creatives, budget)

        # Cluster creatives by decay pattern
        clusters = predictor.cluster_creatives(all_creatives)
    """

    def __init__(self):
        # Platform-specific decay rates (days to half performance)
        self.platform_decay_rates = {
            "meta": 12,      # Meta creatives fatigue faster
            "google": 21,    # Search ads last longer
            "tiktok": 7,     # TikTok needs frequent refresh
            "snapchat": 10,
            "linkedin": 28,  # B2B has longer cycles
            "default": 14,
        }

        # Creative type adjustment factors
        self.type_factors = {
            "video": 0.85,      # Videos fatigue faster
            "image": 1.0,       # Baseline
            "carousel": 1.15,   # Carousels last longer
            "stories": 0.7,     # Stories fatigue quickly
            "reels": 0.75,
            "collection": 1.1,
        }

        # Fatigue thresholds
        self.fatigue_threshold = 0.65
        self.watch_threshold = 0.45

        # Fitted clusters
        self._clusters: List[CreativeCluster] = []
        self._scaler: Optional[Any] = None

    def predict_fatigue(
        self,
        history: CreativePerformanceHistory,
        use_ml: bool = True,
    ) -> FatiguePrediction:
        """
        Predict when a creative will reach fatigue.

        Args:
            history: Historical performance data
            use_ml: Whether to use ML decay fitting (requires scipy)

        Returns:
            FatiguePrediction with timing and recommendations
        """
        if len(history.ctr) < 3:
            return self._insufficient_data_prediction(history)

        # Determine current phase
        current_phase = self._determine_phase(history)

        # Calculate current fatigue score
        current_fatigue = self._calculate_current_fatigue(history)

        # Fit decay model and predict
        if use_ml and ML_AVAILABLE and len(history.ctr) >= 7:
            decay_params = self._fit_decay_model(history)
        else:
            decay_params = self._heuristic_decay(history)

        # Predict days until fatigue
        days_to_fatigue = self._predict_days_to_fatigue(
            history, decay_params, current_fatigue
        )

        # Project future performance
        projections = self._project_performance(history, decay_params, days=7)

        # Determine urgency and recommendations
        urgency = self._determine_urgency(days_to_fatigue, current_fatigue, current_phase)
        recommendations = self._generate_recommendations(
            history, current_phase, urgency, days_to_fatigue, projections
        )

        # Calculate performance loss if not refreshed
        performance_loss = self._estimate_performance_loss(history, projections)

        return FatiguePrediction(
            creative_id=history.creative_id,
            creative_name=history.creative_name,
            current_phase=current_phase,
            current_fatigue_score=round(current_fatigue, 3),
            days_active=history.days_active,
            days_until_fatigue=days_to_fatigue,
            predicted_fatigue_date=datetime.now(timezone.utc) + timedelta(days=days_to_fatigue),
            confidence=self._calculate_prediction_confidence(history, decay_params),
            projected_ctr_7d=round(projections.get("ctr", 0), 4),
            projected_roas_7d=round(projections.get("roas", 0), 2),
            projected_cpa_7d=round(projections.get("cpa", 0), 2),
            refresh_urgency=urgency,
            recommendations=recommendations,
            estimated_performance_loss_if_not_refreshed=round(performance_loss, 1),
            decay_rate=decay_params.get("decay_rate"),
            peak_day=decay_params.get("peak_day"),
            peak_ctr=decay_params.get("peak_ctr"),
        )

    def _determine_phase(self, history: CreativePerformanceHistory) -> LifecyclePhase:
        """Determine the current lifecycle phase."""
        days = history.days_active

        if days <= 3:
            return LifecyclePhase.LEARNING
        elif days <= 7:
            # Check if still growing
            if len(history.ctr) >= 4:
                recent_trend = np.mean(history.ctr[-3:]) - np.mean(history.ctr[:3])
                if recent_trend > 0:
                    return LifecyclePhase.GROWTH
            return LifecyclePhase.MATURITY
        elif days <= 14:
            # Check if declining
            if len(history.ctr) >= 7:
                recent_avg = np.mean(history.ctr[-3:])
                peak_avg = np.mean(history.ctr[4:7]) if len(history.ctr) >= 7 else recent_avg
                if recent_avg < peak_avg * 0.85:
                    return LifecyclePhase.DECLINE
            return LifecyclePhase.MATURITY
        else:
            # Check fatigue level
            fatigue = self._calculate_current_fatigue(history)
            if fatigue >= self.fatigue_threshold:
                return LifecyclePhase.FATIGUE
            return LifecyclePhase.DECLINE

    def _calculate_current_fatigue(self, history: CreativePerformanceHistory) -> float:
        """Calculate current fatigue score."""
        if len(history.ctr) < 3:
            return 0.0

        # Get baseline (days 4-7 or first available)
        if len(history.ctr) >= 7:
            baseline_ctr = np.mean(history.ctr[3:7])
            baseline_roas = np.mean(history.roas[3:7]) if history.roas else 0
            baseline_cpa = np.mean(history.cpa[3:7]) if history.cpa else 0
        else:
            baseline_ctr = np.mean(history.ctr[:min(3, len(history.ctr))])
            baseline_roas = np.mean(history.roas[:min(3, len(history.roas))]) if history.roas else 0
            baseline_cpa = np.mean(history.cpa[:min(3, len(history.cpa))]) if history.cpa else 0

        # Get recent metrics
        recent_ctr = np.mean(history.ctr[-3:])
        recent_roas = np.mean(history.roas[-3:]) if history.roas else 0
        recent_cpa = np.mean(history.cpa[-3:]) if history.cpa else 0
        recent_freq = history.frequency[-1] if history.frequency else 1.0

        # Calculate drops
        ctr_drop = max(0, (baseline_ctr - recent_ctr) / baseline_ctr) if baseline_ctr > 0 else 0
        roas_drop = max(0, (baseline_roas - recent_roas) / baseline_roas) if baseline_roas > 0 else 0
        cpa_rise = max(0, (recent_cpa - baseline_cpa) / baseline_cpa) if baseline_cpa > 0 else 0
        freq_factor = min(1.0, max(0, (recent_freq - 2) / 3))

        # Weighted fatigue score
        fatigue = (
            0.25 * ctr_drop +
            0.25 * roas_drop +
            0.25 * cpa_rise +
            0.25 * freq_factor
        )

        return min(1.0, fatigue)

    def _fit_decay_model(self, history: CreativePerformanceHistory) -> Dict[str, Any]:
        """Fit an exponential decay model to CTR data."""
        if not ML_AVAILABLE:
            return self._heuristic_decay(history)

        days = np.arange(1, len(history.ctr) + 1)
        ctr_values = np.array(history.ctr)

        # Find peak
        peak_idx = np.argmax(ctr_values)
        peak_day = int(peak_idx + 1)
        peak_ctr = float(ctr_values[peak_idx])

        # Only fit decay after peak
        if peak_idx < len(ctr_values) - 3:
            decay_days = days[peak_idx:] - peak_day
            decay_values = ctr_values[peak_idx:]

            try:
                # Fit exponential decay: y = a * exp(-b * x) + c
                def exp_decay(x, a, b, c):
                    return a * np.exp(-b * x) + c

                # Initial guess
                p0 = [peak_ctr, 0.05, peak_ctr * 0.3]

                popt, _ = curve_fit(
                    exp_decay, decay_days, decay_values,
                    p0=p0, maxfev=1000,
                    bounds=([0, 0, 0], [peak_ctr * 2, 1, peak_ctr])
                )

                decay_rate = float(popt[1])
                floor = float(popt[2])

            except Exception as e:
                logger.warning(f"Decay fitting failed: {e}")
                return self._heuristic_decay(history)
        else:
            # Not enough post-peak data
            decay_rate = self._get_platform_decay_rate(history.platform, history.creative_type)
            floor = peak_ctr * 0.3

        return {
            "peak_day": peak_day,
            "peak_ctr": peak_ctr,
            "decay_rate": decay_rate,
            "floor_ctr": floor,
            "method": "ml_fit",
        }

    def _heuristic_decay(self, history: CreativePerformanceHistory) -> Dict[str, Any]:
        """Heuristic decay estimation when ML is unavailable."""
        ctr_values = history.ctr

        # Find peak
        peak_idx = np.argmax(ctr_values) if ctr_values else 0
        peak_day = peak_idx + 1
        peak_ctr = ctr_values[peak_idx] if ctr_values else 0

        # Estimate decay from platform defaults
        base_decay = self._get_platform_decay_rate(history.platform, history.creative_type)

        # Adjust based on observed decline
        if len(ctr_values) > peak_idx + 3:
            recent_ctr = np.mean(ctr_values[-3:])
            days_since_peak = len(ctr_values) - peak_idx
            if peak_ctr > 0 and recent_ctr < peak_ctr:
                observed_decline = (peak_ctr - recent_ctr) / peak_ctr
                observed_decay = -math.log(1 - observed_decline) / days_since_peak if observed_decline < 1 else 0.1
                decay_rate = (base_decay + observed_decay) / 2
            else:
                decay_rate = base_decay
        else:
            decay_rate = base_decay

        return {
            "peak_day": peak_day,
            "peak_ctr": peak_ctr,
            "decay_rate": decay_rate,
            "floor_ctr": peak_ctr * 0.3,
            "method": "heuristic",
        }

    def _get_platform_decay_rate(self, platform: str, creative_type: str) -> float:
        """Get decay rate based on platform and creative type."""
        # Half-life in days
        half_life = self.platform_decay_rates.get(
            platform.lower(),
            self.platform_decay_rates["default"]
        )

        # Apply creative type factor
        type_factor = self.type_factors.get(creative_type.lower(), 1.0)
        adjusted_half_life = half_life * type_factor

        # Convert to decay rate (lambda in exponential decay)
        decay_rate = math.log(2) / adjusted_half_life

        return decay_rate

    def _predict_days_to_fatigue(
        self,
        history: CreativePerformanceHistory,
        decay_params: Dict[str, Any],
        current_fatigue: float,
    ) -> int:
        """Predict days until fatigue threshold is reached."""
        if current_fatigue >= self.fatigue_threshold:
            return 0

        # Simple projection based on decay rate
        decay_rate = decay_params.get("decay_rate", 0.05)

        # How much more fatigue is needed
        fatigue_needed = self.fatigue_threshold - current_fatigue

        # Estimate days (simplified - fatigue increases roughly linearly with CTR decline)
        if decay_rate > 0:
            days_estimate = int(fatigue_needed / (decay_rate * 0.3))  # 0.3 is approximate conversion
        else:
            days_estimate = 30

        # Cap at reasonable range
        return max(0, min(days_estimate, 60))

    def _project_performance(
        self,
        history: CreativePerformanceHistory,
        decay_params: Dict[str, Any],
        days: int = 7,
    ) -> Dict[str, float]:
        """Project performance metrics for next N days."""
        if not history.ctr:
            return {"ctr": 0, "roas": 0, "cpa": 0}

        current_ctr = history.ctr[-1]
        decay_rate = decay_params.get("decay_rate", 0.05)
        floor_ctr = decay_params.get("floor_ctr", current_ctr * 0.3)

        # Project CTR using exponential decay
        projected_ctr = floor_ctr + (current_ctr - floor_ctr) * math.exp(-decay_rate * days)

        # Project ROAS (correlates with CTR)
        current_roas = history.roas[-1] if history.roas else 0
        roas_factor = projected_ctr / current_ctr if current_ctr > 0 else 1
        projected_roas = current_roas * roas_factor

        # Project CPA (inverse relationship)
        current_cpa = history.cpa[-1] if history.cpa else 0
        cpa_factor = 1 / roas_factor if roas_factor > 0 else 1
        projected_cpa = current_cpa * cpa_factor

        return {
            "ctr": projected_ctr,
            "roas": projected_roas,
            "cpa": projected_cpa,
        }

    def _determine_urgency(
        self,
        days_to_fatigue: int,
        current_fatigue: float,
        phase: LifecyclePhase,
    ) -> RefreshUrgency:
        """Determine refresh urgency."""
        if phase == LifecyclePhase.FATIGUE or days_to_fatigue == 0:
            return RefreshUrgency.IMMEDIATE
        elif days_to_fatigue <= 3 or current_fatigue > 0.55:
            return RefreshUrgency.SOON
        elif days_to_fatigue <= 7 or current_fatigue > self.watch_threshold:
            return RefreshUrgency.PLANNED
        elif phase == LifecyclePhase.DECLINE:
            return RefreshUrgency.MONITOR
        else:
            return RefreshUrgency.HEALTHY

    def _generate_recommendations(
        self,
        history: CreativePerformanceHistory,
        phase: LifecyclePhase,
        urgency: RefreshUrgency,
        days_to_fatigue: int,
        projections: Dict[str, float],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if urgency == RefreshUrgency.IMMEDIATE:
            recommendations.append("🚨 Refresh creative immediately - performance has degraded significantly")
            recommendations.append(f"Consider pausing until new creative is ready")
        elif urgency == RefreshUrgency.SOON:
            recommendations.append(f"⚠️ Prepare new creative - estimated {days_to_fatigue} days until fatigue")
            recommendations.append("Start testing new variants now")
        elif urgency == RefreshUrgency.PLANNED:
            recommendations.append(f"📅 Schedule creative refresh for next week (day {days_to_fatigue})")

        # Platform-specific recommendations
        platform = history.platform.lower()
        if platform == "tiktok":
            recommendations.append("TikTok tip: Use trending sounds and effects in new creative")
        elif platform == "meta":
            recommendations.append("Meta tip: Test UGC-style content for refresh")
        elif platform == "google":
            recommendations.append("Google tip: Update responsive ad assets")

        # Phase-specific advice
        if phase == LifecyclePhase.LEARNING:
            recommendations.append("Creative is still in learning phase - allow 3+ days before evaluating")
        elif phase == LifecyclePhase.GROWTH:
            recommendations.append("Creative is performing well - consider increasing budget")

        # Frequency warning
        if history.frequency and history.frequency[-1] > 3:
            recommendations.append(f"High frequency ({history.frequency[-1]:.1f}) - expand audience targeting")

        return recommendations

    def _estimate_performance_loss(
        self,
        history: CreativePerformanceHistory,
        projections: Dict[str, float],
    ) -> float:
        """Estimate performance loss if creative is not refreshed."""
        if not history.roas:
            return 0.0

        current_roas = history.roas[-1]
        projected_roas = projections.get("roas", current_roas)

        if current_roas > 0:
            loss = ((current_roas - projected_roas) / current_roas) * 100
            return max(0, loss)
        return 0.0

    def _calculate_prediction_confidence(
        self,
        history: CreativePerformanceHistory,
        decay_params: Dict[str, Any],
    ) -> float:
        """Calculate confidence in the prediction."""
        confidence = 0.5

        # More data = higher confidence
        if history.days_active >= 14:
            confidence += 0.2
        elif history.days_active >= 7:
            confidence += 0.1

        # ML fit = higher confidence
        if decay_params.get("method") == "ml_fit":
            confidence += 0.15

        # Consistent patterns = higher confidence
        if len(history.ctr) >= 7:
            ctr_std = np.std(history.ctr)
            ctr_mean = np.mean(history.ctr)
            if ctr_mean > 0 and ctr_std / ctr_mean < 0.3:
                confidence += 0.1

        return min(0.95, confidence)

    def _insufficient_data_prediction(
        self,
        history: CreativePerformanceHistory,
    ) -> FatiguePrediction:
        """Return prediction when insufficient data."""
        return FatiguePrediction(
            creative_id=history.creative_id,
            creative_name=history.creative_name,
            current_phase=LifecyclePhase.LEARNING,
            current_fatigue_score=0.0,
            days_active=history.days_active,
            days_until_fatigue=14,  # Default estimate
            predicted_fatigue_date=datetime.now(timezone.utc) + timedelta(days=14),
            confidence=0.3,
            projected_ctr_7d=0.0,
            projected_roas_7d=0.0,
            projected_cpa_7d=0.0,
            refresh_urgency=RefreshUrgency.HEALTHY,
            recommendations=["Insufficient data - continue running for at least 3 days"],
            estimated_performance_loss_if_not_refreshed=0.0,
        )

    # =========================================================================
    # Creative Rotation Planning
    # =========================================================================

    def get_rotation_plan(
        self,
        creatives: List[CreativePerformanceHistory],
        weekly_budget: float,
        max_creatives_at_once: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate a creative rotation plan based on fatigue predictions.

        Returns recommended budget allocation and refresh schedule.
        """
        predictions = [self.predict_fatigue(c) for c in creatives]

        # Sort by urgency and performance
        def urgency_score(p: FatiguePrediction) -> int:
            scores = {
                RefreshUrgency.IMMEDIATE: 4,
                RefreshUrgency.SOON: 3,
                RefreshUrgency.PLANNED: 2,
                RefreshUrgency.MONITOR: 1,
                RefreshUrgency.HEALTHY: 0,
            }
            return scores.get(p.refresh_urgency, 0)

        predictions.sort(key=lambda p: (-urgency_score(p), p.current_fatigue_score), reverse=True)

        # Build rotation plan
        needs_refresh = [p for p in predictions if urgency_score(p) >= 2]
        healthy = [p for p in predictions if urgency_score(p) < 2]

        # Budget allocation (favor healthy creatives)
        budget_allocation = {}
        total_roas = sum(p.projected_roas_7d for p in healthy if p.projected_roas_7d > 0) or 1

        for pred in healthy[:max_creatives_at_once]:
            weight = pred.projected_roas_7d / total_roas if total_roas > 0 else 1 / len(healthy)
            budget_allocation[pred.creative_id] = round(weekly_budget * weight, 2)

        return {
            "total_creatives": len(creatives),
            "active_creatives": len(healthy[:max_creatives_at_once]),
            "needs_refresh": [
                {
                    "creative_id": p.creative_id,
                    "creative_name": p.creative_name,
                    "urgency": p.refresh_urgency.value,
                    "days_until_fatigue": p.days_until_fatigue,
                }
                for p in needs_refresh
            ],
            "budget_allocation": budget_allocation,
            "refresh_schedule": self._build_refresh_schedule(predictions),
        }

    def _build_refresh_schedule(
        self,
        predictions: List[FatiguePrediction],
    ) -> List[Dict[str, Any]]:
        """Build a weekly refresh schedule."""
        schedule = []

        for pred in predictions:
            if pred.refresh_urgency in [RefreshUrgency.IMMEDIATE, RefreshUrgency.SOON]:
                schedule.append({
                    "creative_id": pred.creative_id,
                    "action": "refresh",
                    "when": "this_week",
                    "reason": pred.recommendations[0] if pred.recommendations else "Fatigue detected",
                })
            elif pred.refresh_urgency == RefreshUrgency.PLANNED:
                schedule.append({
                    "creative_id": pred.creative_id,
                    "action": "prepare_replacement",
                    "when": "next_week",
                    "days_remaining": pred.days_until_fatigue,
                })

        return schedule


# Singleton instance
lifecycle_predictor = CreativeLifecyclePredictor()


# =============================================================================
# Convenience Functions
# =============================================================================

def predict_creative_fatigue(
    creative_id: str,
    creative_name: str,
    platform: str,
    creative_type: str,
    daily_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Predict fatigue for a creative from daily metrics.

    Args:
        creative_id: Unique creative identifier
        creative_name: Human-readable name
        platform: Ad platform (meta, google, tiktok, etc.)
        creative_type: Type of creative (image, video, carousel)
        daily_metrics: List of daily metric dicts with:
            - date, impressions, clicks, conversions, spend
            - ctr, cvr, cpa, roas, frequency

    Returns:
        Dict with fatigue prediction and recommendations
    """
    history = CreativePerformanceHistory(
        creative_id=creative_id,
        creative_name=creative_name,
        platform=platform,
        creative_type=creative_type,
        dates=[datetime.fromisoformat(d["date"]) if isinstance(d["date"], str) else d["date"] for d in daily_metrics],
        impressions=[d.get("impressions", 0) for d in daily_metrics],
        clicks=[d.get("clicks", 0) for d in daily_metrics],
        conversions=[d.get("conversions", 0) for d in daily_metrics],
        spend=[d.get("spend", 0) for d in daily_metrics],
        ctr=[d.get("ctr", 0) for d in daily_metrics],
        cvr=[d.get("cvr", 0) for d in daily_metrics],
        cpa=[d.get("cpa", 0) for d in daily_metrics],
        roas=[d.get("roas", 0) for d in daily_metrics],
        frequency=[d.get("frequency", 1) for d in daily_metrics],
        days_active=len(daily_metrics),
    )

    prediction = lifecycle_predictor.predict_fatigue(history)

    return {
        "creative_id": prediction.creative_id,
        "creative_name": prediction.creative_name,
        "current_phase": prediction.current_phase.value,
        "fatigue_score": prediction.current_fatigue_score,
        "days_active": prediction.days_active,
        "days_until_fatigue": prediction.days_until_fatigue,
        "predicted_fatigue_date": prediction.predicted_fatigue_date.isoformat(),
        "confidence": prediction.confidence,
        "refresh_urgency": prediction.refresh_urgency.value,
        "projections": {
            "ctr_7d": prediction.projected_ctr_7d,
            "roas_7d": prediction.projected_roas_7d,
            "cpa_7d": prediction.projected_cpa_7d,
        },
        "estimated_loss_percent": prediction.estimated_performance_loss_if_not_refreshed,
        "recommendations": prediction.recommendations,
    }


# =============================================================================
# Creative Clustering by Decay Pattern
# =============================================================================

@dataclass
class CreativeDecayPattern:
    """Extracted decay pattern from a creative's history."""
    creative_id: str
    peak_day: int
    peak_ctr: float
    decay_rate: float
    floor_ctr: float
    days_to_50_percent: float  # Days to reach 50% of peak
    days_to_fatigue: int
    total_lifetime_ctr: float  # Area under curve


class CreativeClusterAnalyzer:
    """
    Cluster creatives by their decay patterns to learn optimal strategies.

    Enables:
    - Identify which creative types last longest
    - Learn platform-specific decay patterns
    - Transfer learning for new creatives
    - Benchmark against similar creatives
    """

    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters
        self._kmeans: Optional[Any] = None
        self._scaler: Optional[Any] = None
        self._patterns: List[CreativeDecayPattern] = []
        self._clusters: Dict[int, List[str]] = {}

    def extract_pattern(self, history: CreativePerformanceHistory) -> Optional[CreativeDecayPattern]:
        """Extract decay pattern features from creative history."""
        if len(history.ctr) < 7:
            return None

        ctr_arr = np.array(history.ctr)

        # Find peak
        peak_idx = np.argmax(ctr_arr)
        peak_day = int(peak_idx + 1)
        peak_ctr = float(ctr_arr[peak_idx])

        if peak_ctr <= 0:
            return None

        # Calculate decay rate
        if peak_idx < len(ctr_arr) - 3:
            post_peak = ctr_arr[peak_idx:]
            if len(post_peak) > 1:
                # Fit exponential decay
                days_post = np.arange(len(post_peak))
                # Simple estimation: find when we hit 50%
                half_peak = peak_ctr * 0.5
                below_half = np.where(post_peak < half_peak)[0]
                if len(below_half) > 0:
                    days_to_50 = float(below_half[0])
                    decay_rate = math.log(2) / max(days_to_50, 1)
                else:
                    days_to_50 = len(post_peak) * 2  # Estimate
                    decay_rate = math.log(2) / days_to_50
            else:
                decay_rate = 0.05
                days_to_50 = 14
        else:
            decay_rate = 0.05
            days_to_50 = 14

        # Floor CTR (last 3 days average)
        floor_ctr = float(np.mean(ctr_arr[-3:]))

        # Days to fatigue (when CTR drops to 35% of peak)
        fatigue_threshold = peak_ctr * 0.35
        below_fatigue = np.where(ctr_arr < fatigue_threshold)[0]
        if len(below_fatigue) > 0:
            days_to_fatigue = int(below_fatigue[0])
        else:
            days_to_fatigue = len(ctr_arr) + 7

        # Total lifetime CTR (area under curve, proxy for total value)
        total_ctr = float(np.sum(ctr_arr))

        return CreativeDecayPattern(
            creative_id=history.creative_id,
            peak_day=peak_day,
            peak_ctr=round(peak_ctr, 6),
            decay_rate=round(decay_rate, 4),
            floor_ctr=round(floor_ctr, 6),
            days_to_50_percent=round(days_to_50, 1),
            days_to_fatigue=days_to_fatigue,
            total_lifetime_ctr=round(total_ctr, 4),
        )

    def fit(self, histories: List[CreativePerformanceHistory]) -> "CreativeClusterAnalyzer":
        """
        Fit clustering model on creative histories.

        Clusters creatives by their decay pattern similarities.
        """
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available for clustering")
            return self

        # Extract patterns
        self._patterns = []
        for h in histories:
            pattern = self.extract_pattern(h)
            if pattern:
                self._patterns.append(pattern)

        if len(self._patterns) < self.n_clusters:
            logger.warning(f"Not enough patterns for clustering: {len(self._patterns)}")
            return self

        # Create feature matrix
        features = np.array([
            [p.peak_day, p.peak_ctr, p.decay_rate, p.days_to_50_percent, p.days_to_fatigue]
            for p in self._patterns
        ])

        # Scale features
        self._scaler = StandardScaler()
        features_scaled = self._scaler.fit_transform(features)

        # Cluster
        self._kmeans = KMeans(n_clusters=min(self.n_clusters, len(self._patterns)), random_state=42)
        labels = self._kmeans.fit_predict(features_scaled)

        # Store clusters
        self._clusters = {}
        for pattern, label in zip(self._patterns, labels):
            if label not in self._clusters:
                self._clusters[label] = []
            self._clusters[label].append(pattern.creative_id)

        logger.info(f"Clustered {len(self._patterns)} creatives into {len(self._clusters)} groups")

        return self

    def get_cluster_profiles(self) -> List[Dict[str, Any]]:
        """Get profile of each cluster."""
        profiles = []

        for cluster_id, creative_ids in self._clusters.items():
            cluster_patterns = [p for p in self._patterns if p.creative_id in creative_ids]

            if not cluster_patterns:
                continue

            avg_peak_day = np.mean([p.peak_day for p in cluster_patterns])
            avg_decay_rate = np.mean([p.decay_rate for p in cluster_patterns])
            avg_days_to_fatigue = np.mean([p.days_to_fatigue for p in cluster_patterns])
            avg_lifetime_ctr = np.mean([p.total_lifetime_ctr for p in cluster_patterns])

            # Determine cluster type
            if avg_decay_rate > 0.1:
                cluster_type = "fast_burner"
                description = "High initial impact, rapid decay - best for short campaigns"
            elif avg_decay_rate < 0.03:
                cluster_type = "evergreen"
                description = "Slow decay, long lifespan - good for always-on campaigns"
            elif avg_peak_day > 10:
                cluster_type = "slow_starter"
                description = "Takes time to peak, but maintains well"
            else:
                cluster_type = "balanced"
                description = "Moderate peak and decay - versatile performer"

            profiles.append({
                "cluster_id": int(cluster_id),
                "cluster_type": cluster_type,
                "description": description,
                "creative_count": len(cluster_patterns),
                "avg_peak_day": round(avg_peak_day, 1),
                "avg_decay_rate": round(avg_decay_rate, 4),
                "avg_days_to_fatigue": round(avg_days_to_fatigue, 0),
                "avg_lifetime_value": round(avg_lifetime_ctr, 4),
                "creative_ids": creative_ids[:10],  # Sample
            })

        return sorted(profiles, key=lambda x: x["avg_lifetime_value"], reverse=True)

    def predict_cluster(self, history: CreativePerformanceHistory) -> Optional[Dict[str, Any]]:
        """Predict which cluster a new creative belongs to."""
        if not self._kmeans or not self._scaler:
            return None

        pattern = self.extract_pattern(history)
        if not pattern:
            return None

        features = np.array([[
            pattern.peak_day, pattern.peak_ctr, pattern.decay_rate,
            pattern.days_to_50_percent, pattern.days_to_fatigue
        ]])
        features_scaled = self._scaler.transform(features)
        cluster_id = int(self._kmeans.predict(features_scaled)[0])

        # Get cluster profile
        profiles = self.get_cluster_profiles()
        matching_profile = next((p for p in profiles if p["cluster_id"] == cluster_id), None)

        return {
            "creative_id": history.creative_id,
            "predicted_cluster": cluster_id,
            "cluster_profile": matching_profile,
            "pattern": {
                "peak_day": pattern.peak_day,
                "decay_rate": pattern.decay_rate,
                "days_to_fatigue": pattern.days_to_fatigue,
            },
        }


# =============================================================================
# Cross-Creative Learning (Transfer Learning)
# =============================================================================

class CrossCreativeLearner:
    """
    Learn from historical creatives to improve predictions for new ones.

    Enables "cold start" predictions using transfer learning from
    similar creatives.
    """

    def __init__(self):
        self._historical_data: List[Tuple[CreativePerformanceHistory, FatiguePrediction]] = []
        self._platform_benchmarks: Dict[str, Dict[str, float]] = {}
        self._type_benchmarks: Dict[str, Dict[str, float]] = {}

    def learn(
        self,
        histories: List[CreativePerformanceHistory],
        predictions: List[FatiguePrediction],
    ) -> "CrossCreativeLearner":
        """
        Learn from historical creative data.

        Builds benchmarks for platforms and creative types.
        """
        self._historical_data = list(zip(histories, predictions))

        # Calculate platform benchmarks
        platform_data: Dict[str, List[FatiguePrediction]] = {}
        for h, p in self._historical_data:
            platform = h.platform.lower()
            if platform not in platform_data:
                platform_data[platform] = []
            platform_data[platform].append(p)

        for platform, preds in platform_data.items():
            self._platform_benchmarks[platform] = {
                "avg_days_to_fatigue": np.mean([p.days_until_fatigue for p in preds]),
                "avg_fatigue_score": np.mean([p.current_fatigue_score for p in preds]),
                "avg_decay_rate": np.mean([p.decay_rate or 0.05 for p in preds]),
                "sample_count": len(preds),
            }

        # Calculate type benchmarks
        type_data: Dict[str, List[FatiguePrediction]] = {}
        for h, p in self._historical_data:
            ctype = h.creative_type.lower()
            if ctype not in type_data:
                type_data[ctype] = []
            type_data[ctype].append(p)

        for ctype, preds in type_data.items():
            self._type_benchmarks[ctype] = {
                "avg_days_to_fatigue": np.mean([p.days_until_fatigue for p in preds]),
                "avg_fatigue_score": np.mean([p.current_fatigue_score for p in preds]),
                "avg_decay_rate": np.mean([p.decay_rate or 0.05 for p in preds]),
                "sample_count": len(preds),
            }

        logger.info(
            f"Learned from {len(histories)} creatives: "
            f"{len(self._platform_benchmarks)} platforms, "
            f"{len(self._type_benchmarks)} types"
        )

        return self

    def get_cold_start_prediction(
        self,
        platform: str,
        creative_type: str,
    ) -> Dict[str, Any]:
        """
        Get prediction for a new creative with no history.

        Uses learned benchmarks from similar creatives.
        """
        platform = platform.lower()
        creative_type = creative_type.lower()

        # Get platform benchmark
        platform_bench = self._platform_benchmarks.get(platform, {})
        type_bench = self._type_benchmarks.get(creative_type, {})

        # Blend benchmarks (prefer type-specific if available)
        if type_bench and platform_bench:
            days_to_fatigue = (type_bench["avg_days_to_fatigue"] + platform_bench["avg_days_to_fatigue"]) / 2
            decay_rate = (type_bench["avg_decay_rate"] + platform_bench["avg_decay_rate"]) / 2
        elif type_bench:
            days_to_fatigue = type_bench["avg_days_to_fatigue"]
            decay_rate = type_bench["avg_decay_rate"]
        elif platform_bench:
            days_to_fatigue = platform_bench["avg_days_to_fatigue"]
            decay_rate = platform_bench["avg_decay_rate"]
        else:
            # Default fallback
            days_to_fatigue = 14
            decay_rate = 0.05

        return {
            "predicted_days_to_fatigue": round(days_to_fatigue, 0),
            "predicted_decay_rate": round(decay_rate, 4),
            "confidence": 0.4,  # Lower confidence for cold start
            "basis": {
                "platform_benchmark": platform_bench,
                "type_benchmark": type_bench,
            },
            "recommendation": (
                f"Based on similar {creative_type} creatives on {platform}, "
                f"expect ~{int(days_to_fatigue)} days until fatigue. "
                f"Monitor closely and update predictions as data accumulates."
            ),
        }

    def find_similar_creatives(
        self,
        history: CreativePerformanceHistory,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find historically similar creatives for benchmarking.

        Matches on platform, type, and performance profile.
        """
        candidates = []

        for hist, pred in self._historical_data:
            # Score similarity
            similarity = 0

            # Platform match
            if hist.platform.lower() == history.platform.lower():
                similarity += 0.3

            # Type match
            if hist.creative_type.lower() == history.creative_type.lower():
                similarity += 0.3

            # Performance similarity (if enough data)
            if len(history.ctr) >= 3 and len(hist.ctr) >= 3:
                # Compare early CTR patterns
                early_ctr_this = np.mean(history.ctr[:3])
                early_ctr_that = np.mean(hist.ctr[:3])
                if early_ctr_that > 0:
                    ctr_ratio = min(early_ctr_this, early_ctr_that) / max(early_ctr_this, early_ctr_that)
                    similarity += 0.4 * ctr_ratio

            candidates.append({
                "creative_id": hist.creative_id,
                "creative_name": hist.creative_name,
                "platform": hist.platform,
                "creative_type": hist.creative_type,
                "similarity_score": round(similarity, 3),
                "days_to_fatigue": pred.days_until_fatigue,
                "final_phase": pred.current_phase.value,
            })

        # Sort by similarity and return top N
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidates[:top_n]


# =============================================================================
# Creative A/B Test Suggestions
# =============================================================================

class CreativeTestSuggester:
    """
    Suggest A/B test variations for creatives based on fatigue patterns.

    Analyzes what makes creatives last longer and suggests variations
    to test for improved longevity.
    """

    VARIATION_STRATEGIES = {
        "hook_change": {
            "description": "Change the opening hook (first 3 seconds for video, headline for image)",
            "expected_impact": "Can extend lifecycle by 20-40% if new hook resonates",
            "effort": "medium",
        },
        "cta_variation": {
            "description": "Test different call-to-action text and design",
            "expected_impact": "Typically 5-15% improvement in conversion rate",
            "effort": "low",
        },
        "format_switch": {
            "description": "Convert between formats (image to video, single to carousel)",
            "expected_impact": "Can reset fatigue and add 1-2 weeks of runway",
            "effort": "high",
        },
        "color_refresh": {
            "description": "Update color scheme while keeping core creative concept",
            "expected_impact": "Light refresh can add 3-7 days of performance",
            "effort": "low",
        },
        "copy_iteration": {
            "description": "Test new body copy and value propositions",
            "expected_impact": "10-20% variation in CTR common",
            "effort": "low",
        },
        "audience_segment": {
            "description": "Test same creative on different audience segments",
            "expected_impact": "Can find segments where creative has fresh appeal",
            "effort": "medium",
        },
    }

    def suggest_tests(
        self,
        prediction: FatiguePrediction,
        history: CreativePerformanceHistory,
        max_suggestions: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Suggest A/B test variations based on fatigue prediction.
        """
        suggestions = []

        # Priority based on urgency
        if prediction.refresh_urgency == RefreshUrgency.IMMEDIATE:
            # Urgent - suggest high-impact changes
            strategies = ["format_switch", "hook_change", "audience_segment"]
        elif prediction.refresh_urgency == RefreshUrgency.SOON:
            # Preparing - test variations before crisis
            strategies = ["hook_change", "cta_variation", "copy_iteration"]
        else:
            # Healthy - optimize incrementally
            strategies = ["cta_variation", "color_refresh", "copy_iteration"]

        for strategy in strategies[:max_suggestions]:
            strategy_info = self.VARIATION_STRATEGIES.get(strategy, {})

            suggestions.append({
                "strategy": strategy,
                "description": strategy_info.get("description", ""),
                "expected_impact": strategy_info.get("expected_impact", ""),
                "effort_level": strategy_info.get("effort", "medium"),
                "priority": "high" if strategy in ["format_switch", "hook_change"] else "medium",
                "rationale": self._get_rationale(strategy, prediction, history),
            })

        return suggestions

    def _get_rationale(
        self,
        strategy: str,
        prediction: FatiguePrediction,
        history: CreativePerformanceHistory,
    ) -> str:
        """Generate rationale for why this test is recommended."""
        if strategy == "hook_change":
            if prediction.current_phase == LifecyclePhase.DECLINE:
                return "CTR is declining - a new hook can recapture attention"
            return "Proactive hook testing before fatigue sets in"

        elif strategy == "format_switch":
            return f"Current {history.creative_type} format showing fatigue; switching formats can reset audience perception"

        elif strategy == "cta_variation":
            if history.cvr and np.mean(history.cvr[-3:]) < np.mean(history.cvr[:3]) * 0.8:
                return "Conversion rate declining - test CTAs to improve click-to-conversion"
            return "Standard optimization - always worth testing CTA variations"

        elif strategy == "audience_segment":
            if history.frequency and history.frequency[-1] > 3:
                return f"High frequency ({history.frequency[-1]:.1f}) - finding new audiences can extend reach"
            return "Test creative on new segments to find untapped potential"

        return "Recommended based on lifecycle analysis"


# Singleton instances
cluster_analyzer = CreativeClusterAnalyzer()
cross_creative_learner = CrossCreativeLearner()
test_suggester = CreativeTestSuggester()
