# =============================================================================
# Stratum AI - Onboarding Models
# =============================================================================
"""
Database models for the onboarding flow.

Tracks user progress through the onboarding wizard and stores
preferences collected during setup.

Onboarding Steps:
1. Business Profile - Industry, spend, team size, market
2. Platform Selection - Which ad platforms to connect
3. Goals Setup - KPIs, targets, currency, timezone
4. Automation Preferences - Manual/assisted/autopilot mode
5. Trust Gate Configuration - Safety thresholds
"""

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

# =============================================================================
# Enums
# =============================================================================


class OnboardingStatus(str, enum.Enum):
    """Overall onboarding status."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class OnboardingStep(str, enum.Enum):
    """Onboarding wizard steps."""

    BUSINESS_PROFILE = "business_profile"
    PLATFORM_SELECTION = "platform_selection"
    GOALS_SETUP = "goals_setup"
    AUTOMATION_PREFERENCES = "automation_preferences"
    TRUST_GATE_CONFIG = "trust_gate_config"


class Industry(str, enum.Enum):
    """Business industry categories."""

    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    LEAD_GEN = "lead_gen"
    MOBILE_APP = "mobile_app"
    GAMING = "gaming"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    REAL_ESTATE = "real_estate"
    TRAVEL = "travel"
    FOOD_BEVERAGE = "food_beverage"
    RETAIL = "retail"
    AUTOMOTIVE = "automotive"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class MonthlyAdSpend(str, enum.Enum):
    """Monthly ad spend ranges."""

    UNDER_10K = "under_10k"
    FROM_10K_50K = "10k_50k"
    FROM_50K_100K = "50k_100k"
    FROM_100K_500K = "100k_500k"
    FROM_500K_1M = "500k_1m"
    OVER_1M = "over_1m"


class TeamSize(str, enum.Enum):
    """Marketing team size."""

    SOLO = "solo"
    SMALL = "2_5"
    MEDIUM = "6_15"
    LARGE = "16_50"
    ENTERPRISE = "50_plus"


class AutomationMode(str, enum.Enum):
    """Automation preference modes."""

    MANUAL = "manual"  # All changes require approval
    ASSISTED = "assisted"  # Recommendations shown, user approves
    AUTOPILOT = "autopilot"  # Automatic execution when trust gate passes


class PrimaryKPI(str, enum.Enum):
    """Primary KPI focus."""

    ROAS = "roas"
    CPA = "cpa"
    CPL = "cpl"
    REVENUE = "revenue"
    CONVERSIONS = "conversions"
    LEADS = "leads"
    APP_INSTALLS = "app_installs"
    BRAND_AWARENESS = "brand_awareness"


# =============================================================================
# Models
# =============================================================================


class TenantOnboarding(Base):
    """
    Tracks onboarding progress and stores collected preferences.
    One record per tenant.
    """

    __tablename__ = "tenant_onboarding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Overall status (stored as strings for portability)
    status: Mapped[str] = mapped_column(
        String(50), default=OnboardingStatus.NOT_STARTED.value, nullable=False
    )
    current_step: Mapped[str] = mapped_column(
        String(50), default=OnboardingStep.BUSINESS_PROFILE.value, nullable=False
    )

    # Step completion tracking
    completed_steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Step 1: Business Profile
    industry: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry_other: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    monthly_ad_spend: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    team_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    target_markets: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # List of country codes

    # Step 2: Platform Selection
    selected_platforms: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # ["meta", "google", ...]

    # Step 3: Goals Setup
    primary_kpi: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_roas: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_cpa_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_budget_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)

    # Step 4: Automation Preferences
    automation_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auto_pause_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_scale_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_slack: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Step 5: Trust Gate Configuration
    trust_threshold_autopilot: Mapped[int] = mapped_column(
        Integer, default=70, nullable=False
    )  # Score needed for autopilot
    trust_threshold_alert: Mapped[int] = mapped_column(
        Integer, default=40, nullable=False
    )  # Score to trigger alert
    require_approval_above: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Spend above this needs approval
    max_daily_actions: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )  # Max auto actions per day

    # Additional preferences (flexible JSON)
    additional_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # User who completed onboarding
    completed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])

    __table_args__ = (Index("ix_tenant_onboarding_status", "status"),)

    def is_step_completed(self, step: OnboardingStep) -> bool:
        """Check if a step is completed."""
        return step.value in (self.completed_steps or [])

    def get_next_step(self) -> Optional[OnboardingStep]:
        """Get the next incomplete step."""
        step_order = [
            OnboardingStep.BUSINESS_PROFILE,
            OnboardingStep.PLATFORM_SELECTION,
            OnboardingStep.GOALS_SETUP,
            OnboardingStep.AUTOMATION_PREFERENCES,
            OnboardingStep.TRUST_GATE_CONFIG,
        ]
        for step in step_order:
            if not self.is_step_completed(step):
                return step
        return None

    def get_progress_percentage(self) -> int:
        """Calculate onboarding progress percentage."""
        total_steps = 5
        completed = len(self.completed_steps or [])
        return int((completed / total_steps) * 100)
