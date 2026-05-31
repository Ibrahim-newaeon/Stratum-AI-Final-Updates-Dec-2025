# =============================================================================
# Stratum AI - Analytics Module
# =============================================================================
"""
AI-powered analytics engine for campaign optimization.
Implements the Analytics Design System scoring and recommendations.
"""

from app.analytics.logic.anomalies import anomaly_zscore, detect_anomalies
from app.analytics.logic.attribution import attribution_variance
from app.analytics.logic.budget import reallocate_budget
from app.analytics.logic.fatigue import creative_fatigue
from app.analytics.logic.recommend import generate_recommendations
from app.analytics.logic.scoring import scaling_score
from app.analytics.logic.signal_health import auto_resolve, signal_health
from app.analytics.logic.types import (
    AnomalyResult,
    EntityMetrics,
    FatigueResult,
    RecommendationAction,
    ScalingScoreResult,
    SignalHealthStatus,
)

__all__ = [
    "AnomalyResult",
    # Types
    "EntityMetrics",
    "FatigueResult",
    "RecommendationAction",
    "ScalingScoreResult",
    "SignalHealthStatus",
    "anomaly_zscore",
    "attribution_variance",
    "auto_resolve",
    "creative_fatigue",
    "detect_anomalies",
    "generate_recommendations",
    "reallocate_budget",
    # Logic functions
    "scaling_score",
    "signal_health",
]
