# =============================================================================
# Stratum AI - Analytics Module
# =============================================================================
"""
AI-powered analytics engine for campaign optimization.
Implements the Analytics Design System scoring and recommendations.
"""

from app.analytics.logic.types import (
    EntityMetrics,
    ScalingScoreResult,
    FatigueResult,
    AnomalyResult,
    SignalHealthStatus,
    RecommendationAction,
)
from app.analytics.logic.scoring import scaling_score
from app.analytics.logic.fatigue import creative_fatigue
from app.analytics.logic.anomalies import detect_anomalies, anomaly_zscore
from app.analytics.logic.signal_health import signal_health, auto_resolve
from app.analytics.logic.attribution import attribution_variance
from app.analytics.logic.budget import reallocate_budget
from app.analytics.logic.recommend import generate_recommendations

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
