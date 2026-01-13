# =============================================================================
# Stratum AI - Unified Data Models for Multiplatform Integration
# =============================================================================
"""
Unified Data Models for Cross-Platform Advertising Management.

These models provide a consistent interface across all supported platforms
(Meta, Google, TikTok, Snapchat), enabling the trust engine to work with
normalized data regardless of the source platform.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported advertising platforms."""
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
    WHATSAPP = "whatsapp"


class EntityStatus(str, Enum):
    """Unified status values across platforms."""
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"
    ARCHIVED = "archived"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class BiddingStrategy(str, Enum):
    """Unified bidding strategy types."""
    LOWEST_COST = "lowest_cost"
    COST_CAP = "cost_cap"
    BID_CAP = "bid_cap"
    TARGET_CPA = "target_cpa"
    TARGET_ROAS = "target_roas"
    MAXIMIZE_CONVERSIONS = "maximize_conversions"
    MAXIMIZE_VALUE = "maximize_value"
    MANUAL_CPC = "manual_cpc"
    MANUAL_CPM = "manual_cpm"


class OptimizationGoal(str, Enum):
    """Unified optimization goals."""
    CONVERSIONS = "conversions"
    VALUE = "value"
    LEADS = "leads"
    TRAFFIC = "traffic"
    REACH = "reach"
    ENGAGEMENT = "engagement"
    APP_INSTALLS = "app_installs"
    VIDEO_VIEWS = "video_views"


class UnifiedAccount(BaseModel):
    """Unified advertising account model."""
    platform: Platform
    account_id: str
    account_name: str
    business_id: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"
    daily_spend_limit: Optional[float] = None
    last_synced: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class UnifiedCampaign(BaseModel):
    """Unified campaign model across platforms."""
    platform: Platform
    account_id: str
    campaign_id: str
    campaign_name: str
    status: EntityStatus = EntityStatus.ACTIVE
    objective: Optional[str] = None
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    budget_remaining: Optional[float] = None
    bidding_strategy: Optional[BiddingStrategy] = None
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class UnifiedAdSet(BaseModel):
    """Unified ad set / ad group model."""
    platform: Platform
    account_id: str
    campaign_id: str
    adset_id: str
    adset_name: str
    status: EntityStatus = EntityStatus.ACTIVE
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    bid_amount: Optional[float] = None
    bid_strategy: Optional[BiddingStrategy] = None
    optimization_goal: Optional[OptimizationGoal] = None
    targeting_summary: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class UnifiedAd(BaseModel):
    """Unified ad model."""
    platform: Platform
    account_id: str
    campaign_id: str
    adset_id: str
    ad_id: str
    ad_name: str
    status: EntityStatus = EntityStatus.ACTIVE
    creative_id: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    destination_url: Optional[str] = None
    call_to_action: Optional[str] = None
    review_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class PerformanceMetrics(BaseModel):
    """Unified performance metrics."""
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    ctr: Optional[float] = None
    cpc: Optional[float] = None
    cpm: Optional[float] = None
    conversions: Optional[int] = None
    conversion_value: Optional[float] = None
    cpa: Optional[float] = None
    roas: Optional[float] = None
    video_views: Optional[int] = None
    video_p25: Optional[int] = None
    video_p50: Optional[int] = None
    video_p75: Optional[int] = None
    video_p100: Optional[int] = None
    reach: Optional[int] = None
    frequency: Optional[float] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None

    def compute_derived_metrics(self) -> None:
        """Compute derived metrics from raw values."""
        if self.impressions > 0 and self.clicks > 0 and self.ctr is None:
            self.ctr = (self.clicks / self.impressions) * 100
        if self.clicks > 0 and self.spend > 0 and self.cpc is None:
            self.cpc = self.spend / self.clicks
        if self.impressions > 0 and self.spend > 0 and self.cpm is None:
            self.cpm = (self.spend / self.impressions) * 1000
        if self.conversions and self.conversions > 0 and self.spend > 0 and self.cpa is None:
            self.cpa = self.spend / self.conversions
        if self.conversion_value and self.conversion_value > 0 and self.spend > 0 and self.roas is None:
            self.roas = self.conversion_value / self.spend


class EMQScore(BaseModel):
    """Event Match Quality score for a platform/event combination."""
    platform: Platform
    event_name: str
    score: float = Field(ge=0, le=10, description="EMQ score 0-10")
    match_rate: Optional[float] = Field(None, ge=0, le=100)
    email_match_rate: Optional[float] = None
    phone_match_rate: Optional[float] = None
    external_id_match_rate: Optional[float] = None
    last_updated: Optional[datetime] = None

    class Config:
        use_enum_values = True

    def is_healthy(self) -> bool:
        """Check if EMQ is in healthy range (>= 7.0)."""
        return self.score >= 7.0

    def to_percentage(self) -> float:
        """Convert 0-10 score to 0-100 percentage."""
        return self.score * 10


class SignalHealth(BaseModel):
    """Composite signal health score with component breakdown."""
    overall_score: float = Field(ge=0, le=100)
    emq_score: float = Field(ge=0, le=100)
    freshness_score: float = Field(ge=0, le=100)
    variance_score: float = Field(ge=0, le=100)
    anomaly_score: float = Field(ge=0, le=100)
    cdp_emq_score: Optional[float] = Field(default=None, ge=0, le=100)  # CDP EMQ integration
    status: str = "healthy"  # healthy, degraded, critical
    issues: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def is_autopilot_safe(self, threshold: float = 70.0) -> bool:
        """Check if signal health allows autopilot operations."""
        return self.overall_score >= threshold and self.status != "critical"

    def has_cdp_data(self) -> bool:
        """Check if CDP EMQ data is available."""
        return self.cdp_emq_score is not None


class AutomationAction(BaseModel):
    """Represents an automation action to be executed."""
    platform: Platform
    account_id: str
    entity_type: str  # campaign, adset, ad
    entity_id: str
    action_type: str  # update_budget, update_status, update_bid, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, executing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    trust_gate_passed: bool = False
    signal_health_at_execution: Optional[float] = None

    class Config:
        use_enum_values = True


class WebhookEvent(BaseModel):
    """Normalized webhook event from any platform."""
    platform: Platform
    event_type: str
    payload: Dict[str, Any]
    received_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
