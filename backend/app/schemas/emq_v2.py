# =============================================================================
# Stratum AI - EMQ v2 Schemas
# =============================================================================
"""
Pydantic models for EMQ (Event Measurement Quality) v2 API endpoints.
These schemas match the frontend types defined in api/emqV2.ts.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Base Schema
# =============================================================================
class EMQBaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


# =============================================================================
# EMQ Score Schemas
# =============================================================================
class EmqDriver(EMQBaseSchema):
    """EMQ driver component."""

    name: str
    value: float
    weight: float
    status: Literal["good", "warning", "critical"]
    trend: Literal["up", "down", "flat"]


class EmqScoreResponse(EMQBaseSchema):
    """EMQ score response with drivers."""

    score: float = Field(..., ge=0, le=100, description="Overall EMQ score")
    previousScore: float = Field(..., ge=0, le=100, description="Previous period score")
    confidenceBand: Literal["reliable", "directional", "unsafe"]
    drivers: list[EmqDriver]
    lastUpdated: str = Field(..., description="ISO timestamp of last update")


# =============================================================================
# Confidence Schemas
# =============================================================================
class ConfidenceFactor(EMQBaseSchema):
    """Factor contributing to confidence score."""

    name: str
    contribution: float
    status: Literal["positive", "negative", "neutral"]


class ConfidenceThresholds(EMQBaseSchema):
    """Threshold values for confidence bands."""

    reliable: float
    directional: float


class ConfidenceDataResponse(EMQBaseSchema):
    """Confidence band details response."""

    band: Literal["reliable", "directional", "unsafe"]
    score: float
    thresholds: ConfidenceThresholds
    factors: list[ConfidenceFactor]


# =============================================================================
# Playbook Schemas
# =============================================================================
class PlaybookItemResponse(EMQBaseSchema):
    """Playbook item for EMQ fixes."""

    id: str
    title: str
    description: str
    priority: Literal["critical", "high", "medium", "low"]
    owner: Optional[str] = None
    estimatedImpact: float = Field(..., description="Estimated EMQ score improvement")
    estimatedTime: Optional[str] = None
    platform: Optional[str] = None
    status: Literal["pending", "in_progress", "completed"]
    actionUrl: Optional[str] = None


class PlaybookItemUpdate(EMQBaseSchema):
    """Playbook item update request."""

    status: Optional[Literal["pending", "in_progress", "completed"]] = None
    owner: Optional[str] = None


# =============================================================================
# Incident Schemas
# =============================================================================
class EmqIncidentResponse(EMQBaseSchema):
    """EMQ incident event."""

    id: str
    type: Literal["incident_opened", "incident_closed", "degradation", "recovery"]
    title: str
    description: Optional[str] = None
    timestamp: str = Field(..., description="ISO timestamp")
    platform: Optional[str] = None
    severity: Literal["critical", "high", "medium", "low"]
    recoveryHours: Optional[float] = None
    emqImpact: Optional[float] = None


# =============================================================================
# Impact Schemas
# =============================================================================
class ImpactBreakdown(EMQBaseSchema):
    """Per-platform impact breakdown."""

    platform: str
    actualRoas: float
    estimatedRoas: float
    confidence: float
    revenueImpact: float


class EmqImpactResponse(EMQBaseSchema):
    """ROAS impact estimate response."""

    totalImpact: float
    currency: str = "USD"
    breakdown: list[ImpactBreakdown]


# =============================================================================
# Volatility Schemas
# =============================================================================
class VolatilityDataPoint(EMQBaseSchema):
    """Weekly volatility data point."""

    date: str
    value: float


class EmqVolatilityResponse(EMQBaseSchema):
    """Signal Volatility Index response."""

    svi: float = Field(..., description="Signal Volatility Index")
    trend: Literal["increasing", "decreasing", "stable"]
    weeklyData: list[VolatilityDataPoint]


# =============================================================================
# Autopilot Schemas
# =============================================================================
class AutopilotStateResponse(EMQBaseSchema):
    """Autopilot state response."""

    mode: Literal["normal", "limited", "cuts_only", "frozen"]
    reason: Optional[str] = None
    budgetAtRisk: float
    allowedActions: list[str]
    restrictedActions: list[str]


class AutopilotModeUpdate(EMQBaseSchema):
    """Autopilot mode update request."""

    mode: Literal["normal", "limited", "cuts_only", "frozen"]
    reason: Optional[str] = None


# =============================================================================
# Benchmark Schemas (Super Admin)
# =============================================================================
class EmqBenchmarkResponse(EMQBaseSchema):
    """Platform benchmark data."""

    platform: str
    p25: float
    p50: float
    p75: float
    tenantScore: float
    percentile: float


# =============================================================================
# Portfolio Schemas (Super Admin)
# =============================================================================
class TopIssue(EMQBaseSchema):
    """Top issue affecting tenants."""

    driver: str
    affectedTenants: int


class BandDistribution(EMQBaseSchema):
    """Distribution of tenants by confidence band."""

    reliable: int
    directional: int
    unsafe: int


class EmqPortfolioResponse(EMQBaseSchema):
    """Portfolio overview for super admin."""

    totalTenants: int
    byBand: BandDistribution
    atRiskBudget: float
    avgScore: float
    topIssues: list[TopIssue]
