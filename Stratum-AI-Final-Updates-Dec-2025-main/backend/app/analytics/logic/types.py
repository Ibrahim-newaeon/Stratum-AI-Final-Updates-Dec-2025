# =============================================================================
# Analytics Types and Data Models
# =============================================================================
"""
Type definitions for the analytics engine.
Based on AI_Logic_Formulas_Pseudocode.md and Data_Schema_Events_and_Tables.md.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


# =============================================================================
# Enums
# =============================================================================
class Platform(str, Enum):
    """Supported advertising platforms."""

    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAP = "snap"
    LINKEDIN = "linkedin"


class EntityLevel(str, Enum):
    """Entity hierarchy levels."""

    ACCOUNT = "account"
    CAMPAIGN = "campaign"
    ADSET_ADGROUP = "adset_adgroup"
    CREATIVE = "creative"
    AUDIENCE = "audience"


class SignalHealthStatus(str, Enum):
    """Signal/EMQ health status levels."""

    HEALTHY = "healthy"
    RISK = "risk"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class ScalingAction(str, Enum):
    """Scaling action recommendations."""

    SCALE = "scale"
    WATCH = "watch"
    FIX = "fix"
    PAUSE = "pause"


class FatigueState(str, Enum):
    """Creative fatigue states."""

    HEALTHY = "healthy"
    WATCH = "watch"
    REFRESH = "refresh"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFO = "info"


# =============================================================================
# Core Metric Models
# =============================================================================
class EntityMetrics(BaseModel):
    """Core daily metrics for any entity level."""

    entity_id: str
    entity_name: str
    entity_level: EntityLevel
    platform: Platform
    date: datetime

    # Core metrics
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    sessions: int = 0  # GA4
    add_to_cart: int = 0
    purchases: int = 0
    revenue: float = 0.0
    leads: int = 0
    conversions: int = 0

    # Computed metrics
    cpa: float = 0.0
    roas: float = 0.0
    cvr: float = 0.0
    ctr: float = 0.0
    cpm: float = 0.0
    frequency: Optional[float] = None

    # Quality metrics
    emq_score: Optional[float] = None  # 0-100
    event_loss_pct: Optional[float] = None  # 0-100

    class Config:
        use_enum_values = True


class BaselineMetrics(BaseModel):
    """Aggregated baseline metrics over a time window."""

    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0

    cpa: float = 0.0
    roas: float = 0.0
    cvr: float = 0.0
    ctr: float = 0.0
    cpm: float = 0.0
    frequency: Optional[float] = None
    emq_score: Optional[float] = None


# =============================================================================
# Scoring Parameters
# =============================================================================
class ScoringParams(BaseModel):
    """Configuration parameters for scoring functions."""

    # Scaling score weights
    roas_weight: float = 0.45
    cpa_weight: float = 0.25
    cvr_weight: float = 0.20
    ctr_weight: float = 0.10

    # Penalty weights
    freq_penalty_weight: float = 0.25
    emq_penalty_weight: float = 0.20
    vol_penalty_weight: float = 0.15

    # Targets/thresholds
    freq_target: float = 3.0
    emq_target: float = 90.0
    min_conversions: int = 10

    # Scaling action thresholds
    scale_threshold: float = 0.25
    fix_threshold: float = -0.25


class FatigueParams(BaseModel):
    """Configuration for fatigue scoring."""

    ctr_weight: float = 0.35
    roas_weight: float = 0.35
    cpa_weight: float = 0.20
    exposure_weight: float = 0.10

    # Fatigue thresholds
    refresh_threshold: float = 0.65
    watch_threshold: float = 0.45

    # EMA smoothing
    ema_alpha: float = 0.4


class AnomalyParams(BaseModel):
    """Configuration for anomaly detection."""

    window_days: int = 14
    zscore_threshold: float = 2.5
    metrics_to_check: list[str] = [
        "spend",
        "revenue",
        "roas",
        "cpa",
        "conversions",
        "event_loss_pct",
        "emq_score",
    ]


class SignalHealthParams(BaseModel):
    """Configuration for signal health checks."""

    emq_healthy: float = 90.0
    emq_risk: float = 80.0
    event_loss_healthy: float = 5.0
    event_loss_risk: float = 10.0


# =============================================================================
# Result Models
# =============================================================================
class ScalingScoreResult(BaseModel):
    """Result of scaling score calculation."""

    entity_id: str
    entity_name: str
    score: float  # -1 to +1
    action: ScalingAction

    # Score breakdown
    roas_delta: float
    cpa_delta: float
    cvr_delta: float
    ctr_delta: float

    # Penalties applied
    freq_penalty: float = 0.0
    emq_penalty: float = 0.0
    vol_penalty: float = 0.0

    # Recommendations
    recommendations: list[str] = []


class FatigueResult(BaseModel):
    """Result of creative fatigue calculation."""

    creative_id: str
    creative_name: str
    fatigue_score: float  # 0 to 1
    state: FatigueState

    # Breakdown
    ctr_drop: float
    roas_drop: float
    cpa_rise: float
    exposure_factor: float

    # Smoothed value
    ema_fatigue: Optional[float] = None

    recommendations: list[str] = []


class AnomalyResult(BaseModel):
    """Result of anomaly detection."""

    metric: str
    zscore: float
    severity: AlertSeverity
    current_value: float
    baseline_mean: float
    baseline_std: float
    is_anomaly: bool
    direction: Literal["high", "low"]


class SignalHealthResult(BaseModel):
    """Result of signal health check."""

    status: SignalHealthStatus
    emq_score: Optional[float]
    event_loss_pct: Optional[float]
    api_health: bool

    issues: list[str] = []
    actions: list[str] = []


class AttributionVarianceResult(BaseModel):
    """Result of attribution variance calculation."""

    entity_id: str
    revenue_variance_pct: float
    conversion_variance_pct: float

    platform_revenue: float
    ga4_revenue: float
    platform_conversions: int
    ga4_conversions: int

    has_significant_variance: bool
    warning_message: Optional[str] = None


class BudgetAction(BaseModel):
    """Budget reallocation action."""

    entity_id: str
    entity_name: str
    action: Literal["increase_budget", "decrease_budget"]
    amount: float
    current_spend: float
    scaling_score: float
    reason: str


class RecommendationAction(BaseModel):
    """Generated recommendation action."""

    type: str
    priority: AlertSeverity
    title: str
    description: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    expected_impact: Optional[dict] = None
    action_params: Optional[dict] = None
