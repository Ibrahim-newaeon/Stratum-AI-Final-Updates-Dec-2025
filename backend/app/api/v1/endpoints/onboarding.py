# =============================================================================
# Stratum AI - Onboarding API Endpoints
# =============================================================================
"""
Onboarding wizard endpoints for new tenant setup.

The onboarding flow has 5 steps:
1. Business Profile - Industry, spend, team size, market
2. Platform Selection - Which ad platforms to connect
3. Goals Setup - KPIs, targets, currency, timezone
4. Automation Preferences - Manual/assisted/autopilot mode
5. Trust Gate Configuration - Safety thresholds

Each step can be saved independently, and progress is tracked.
"""

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUserDep, VerifiedUserDep
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.onboarding import (
    AutomationMode,
    Industry,
    MonthlyAdSpend,
    OnboardingStatus,
    OnboardingStep,
    PrimaryKPI,
    TeamSize,
    TenantOnboarding,
)
from app.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


# --- Step 1: Business Profile ---
class BusinessProfileRequest(BaseModel):
    """Step 1: Business profile information."""

    industry: Industry
    industry_other: Optional[str] = Field(None, max_length=255)
    monthly_ad_spend: MonthlyAdSpend
    team_size: TeamSize
    company_website: Optional[str] = Field(None, max_length=500)
    target_markets: list[str] = Field(
        default=["US"], description="List of country codes (ISO 3166-1 alpha-2)"
    )

    @field_validator("industry_other")
    @classmethod
    def validate_industry_other(cls, v, info):
        """Require industry_other when industry is OTHER."""
        if info.data.get("industry") == Industry.OTHER and not v:
            raise ValueError("Please specify your industry")
        return v

    @field_validator("target_markets")
    @classmethod
    def validate_target_markets(cls, v):
        """Validate country codes."""
        if not v:
            raise ValueError("At least one target market is required")
        return [code.upper() for code in v]


class BusinessProfileResponse(BaseModel):
    """Business profile data."""

    industry: Optional[str] = None
    industry_other: Optional[str] = None
    monthly_ad_spend: Optional[str] = None
    team_size: Optional[str] = None
    company_website: Optional[str] = None
    target_markets: list[str] = []


# --- Step 2: Platform Selection ---
class PlatformSelectionRequest(BaseModel):
    """Step 2: Ad platforms to use."""

    platforms: list[str] = Field(
        ..., min_length=1, description="List of platforms: meta, google, tiktok, snapchat"
    )

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v):
        """Validate platform names."""
        valid_platforms = {"meta", "google", "tiktok", "snapchat"}
        for platform in v:
            if platform.lower() not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}")
        return [p.lower() for p in v]


class PlatformSelectionResponse(BaseModel):
    """Platform selection data."""

    platforms: list[str] = []


# --- Step 3: Goals Setup ---
class GoalsSetupRequest(BaseModel):
    """Step 3: Goals and targets."""

    primary_kpi: PrimaryKPI
    target_roas: Optional[float] = Field(
        None, ge=0.1, le=100, description="Target ROAS (e.g., 3.0 for 3x)"
    )
    target_cpa: Optional[float] = Field(None, ge=0, description="Target CPA in dollars")
    monthly_budget: Optional[float] = Field(None, ge=0, description="Monthly budget in dollars")
    currency: str = Field(default="USD", max_length=3)
    timezone: str = Field(default="UTC", max_length=100)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency code."""
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "INR", "BRL", "MXN"}
        if v.upper() not in valid_currencies:
            # Allow any 3-letter code
            if len(v) != 3 or not v.isalpha():
                raise ValueError("Currency must be a valid 3-letter code")
        return v.upper()


class GoalsSetupResponse(BaseModel):
    """Goals setup data."""

    primary_kpi: Optional[str] = None
    target_roas: Optional[float] = None
    target_cpa: Optional[float] = None
    monthly_budget: Optional[float] = None
    currency: str = "USD"
    timezone: str = "UTC"


# --- Step 4: Automation Preferences ---
class AutomationPreferencesRequest(BaseModel):
    """Step 4: Automation settings."""

    automation_mode: AutomationMode
    auto_pause_enabled: bool = Field(
        default=True, description="Automatically pause underperforming campaigns"
    )
    auto_scale_enabled: bool = Field(
        default=False, description="Automatically scale well-performing campaigns"
    )
    notification_email: bool = True
    notification_slack: bool = False
    notification_whatsapp: bool = False
    slack_webhook_url: Optional[str] = Field(None, max_length=500)
    whatsapp_phone: Optional[str] = Field(None, max_length=50)


class AutomationPreferencesResponse(BaseModel):
    """Automation preferences data."""

    automation_mode: Optional[str] = None
    auto_pause_enabled: bool = True
    auto_scale_enabled: bool = False
    notification_email: bool = True
    notification_slack: bool = False
    notification_whatsapp: bool = False


# --- Step 5: Trust Gate Configuration ---
class TrustGateConfigRequest(BaseModel):
    """Step 5: Trust gate thresholds."""

    trust_threshold_autopilot: int = Field(
        default=70,
        ge=50,
        le=100,
        description="Signal health score required for autopilot execution",
    )
    trust_threshold_alert: int = Field(
        default=40, ge=20, le=70, description="Signal health score that triggers alerts"
    )
    require_approval_above: Optional[float] = Field(
        None, ge=0, description="Spend changes above this amount require approval (in dollars)"
    )
    max_daily_actions: int = Field(
        default=10, ge=1, le=100, description="Maximum automatic actions per day"
    )

    @field_validator("trust_threshold_alert")
    @classmethod
    def validate_thresholds(cls, v, info):
        """Ensure alert threshold is below autopilot threshold."""
        autopilot = info.data.get("trust_threshold_autopilot", 70)
        if v >= autopilot:
            raise ValueError("Alert threshold must be below autopilot threshold")
        return v


class TrustGateConfigResponse(BaseModel):
    """Trust gate configuration data."""

    trust_threshold_autopilot: int = 70
    trust_threshold_alert: int = 40
    require_approval_above: Optional[float] = None
    max_daily_actions: int = 10


# --- Overall Status ---
class OnboardingStatusResponse(BaseModel):
    """Overall onboarding status."""

    status: str
    current_step: str
    completed_steps: list[str]
    progress_percentage: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Step data
    business_profile: Optional[BusinessProfileResponse] = None
    platform_selection: Optional[PlatformSelectionResponse] = None
    goals_setup: Optional[GoalsSetupResponse] = None
    automation_preferences: Optional[AutomationPreferencesResponse] = None
    trust_gate_config: Optional[TrustGateConfigResponse] = None


class StepCompletionResponse(BaseModel):
    """Response after completing a step."""

    step: str
    completed: bool
    next_step: Optional[str] = None
    progress_percentage: int
    message: str


# =============================================================================
# Helper Functions
# =============================================================================


async def get_or_create_onboarding(
    tenant_id: int,
    db: AsyncSession,
) -> TenantOnboarding:
    """Get or create onboarding record for tenant."""
    result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant_id)
    )
    onboarding = result.scalar_one_or_none()

    if not onboarding:
        onboarding = TenantOnboarding(
            tenant_id=tenant_id,
            status=OnboardingStatus.NOT_STARTED,
            current_step=OnboardingStep.BUSINESS_PROFILE,
            completed_steps=[],
        )
        db.add(onboarding)
        await db.flush()

    return onboarding


def mark_step_completed(
    onboarding: TenantOnboarding,
    step: OnboardingStep,
) -> None:
    """Mark a step as completed and update current step."""
    completed = list(onboarding.completed_steps or [])
    if step.value not in completed:
        completed.append(step.value)
        onboarding.completed_steps = completed

    # Update status
    if onboarding.status == OnboardingStatus.NOT_STARTED:
        onboarding.status = OnboardingStatus.IN_PROGRESS
        onboarding.started_at = datetime.now(UTC)

    # Set next step
    next_step = onboarding.get_next_step()
    if next_step:
        onboarding.current_step = next_step
    else:
        # All steps completed
        onboarding.status = OnboardingStatus.COMPLETED
        onboarding.completed_at = datetime.now(UTC)


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=APIResponse[OnboardingStatusResponse])
async def get_onboarding_status(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current onboarding status and progress.

    Returns all saved step data along with completion status.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)
    await db.commit()

    # Build step data
    business_profile = None
    if onboarding.industry:
        business_profile = BusinessProfileResponse(
            industry=onboarding.industry,
            industry_other=onboarding.industry_other,
            monthly_ad_spend=onboarding.monthly_ad_spend,
            team_size=onboarding.team_size,
            company_website=onboarding.company_website,
            target_markets=onboarding.target_markets or [],
        )

    platform_selection = None
    if onboarding.selected_platforms:
        platform_selection = PlatformSelectionResponse(
            platforms=onboarding.selected_platforms,
        )

    goals_setup = None
    if onboarding.primary_kpi:
        goals_setup = GoalsSetupResponse(
            primary_kpi=onboarding.primary_kpi,
            target_roas=onboarding.target_roas,
            target_cpa=onboarding.target_cpa_cents / 100 if onboarding.target_cpa_cents else None,
            monthly_budget=onboarding.monthly_budget_cents / 100
            if onboarding.monthly_budget_cents
            else None,
            currency=onboarding.currency,
            timezone=onboarding.timezone,
        )

    automation_preferences = None
    if onboarding.automation_mode:
        automation_preferences = AutomationPreferencesResponse(
            automation_mode=onboarding.automation_mode,
            auto_pause_enabled=onboarding.auto_pause_enabled,
            auto_scale_enabled=onboarding.auto_scale_enabled,
            notification_email=onboarding.notification_email,
            notification_slack=onboarding.notification_slack,
            notification_whatsapp=onboarding.notification_whatsapp,
        )

    trust_gate_config = TrustGateConfigResponse(
        trust_threshold_autopilot=onboarding.trust_threshold_autopilot,
        trust_threshold_alert=onboarding.trust_threshold_alert,
        require_approval_above=onboarding.require_approval_above / 100
        if onboarding.require_approval_above
        else None,
        max_daily_actions=onboarding.max_daily_actions,
    )

    return APIResponse(
        success=True,
        data=OnboardingStatusResponse(
            status=onboarding.status,
            current_step=onboarding.current_step,
            completed_steps=onboarding.completed_steps or [],
            progress_percentage=onboarding.get_progress_percentage(),
            started_at=onboarding.started_at,
            completed_at=onboarding.completed_at,
            business_profile=business_profile,
            platform_selection=platform_selection,
            goals_setup=goals_setup,
            automation_preferences=automation_preferences,
            trust_gate_config=trust_gate_config,
        ),
    )


@router.post("/business-profile", response_model=APIResponse[StepCompletionResponse])
async def save_business_profile(
    data: BusinessProfileRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Save Step 1: Business Profile.

    Captures industry, ad spend, team size, and target markets.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Save data
    onboarding.industry = data.industry.value
    onboarding.industry_other = data.industry_other
    onboarding.monthly_ad_spend = data.monthly_ad_spend.value
    onboarding.team_size = data.team_size.value
    onboarding.company_website = data.company_website
    onboarding.target_markets = data.target_markets

    # Mark step completed
    mark_step_completed(onboarding, OnboardingStep.BUSINESS_PROFILE)
    await db.commit()

    next_step = onboarding.get_next_step()

    logger.info(
        "onboarding_step_completed",
        step="business_profile",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return APIResponse(
        success=True,
        data=StepCompletionResponse(
            step=OnboardingStep.BUSINESS_PROFILE.value,
            completed=True,
            next_step=next_step.value if next_step else None,
            progress_percentage=onboarding.get_progress_percentage(),
            message="Business profile saved successfully",
        ),
    )


@router.post("/platform-selection", response_model=APIResponse[StepCompletionResponse])
async def save_platform_selection(
    data: PlatformSelectionRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Save Step 2: Platform Selection.

    Captures which ad platforms the tenant wants to use.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Save data
    onboarding.selected_platforms = data.platforms

    # Mark step completed
    mark_step_completed(onboarding, OnboardingStep.PLATFORM_SELECTION)
    await db.commit()

    next_step = onboarding.get_next_step()

    logger.info(
        "onboarding_step_completed",
        step="platform_selection",
        tenant_id=current_user.tenant_id,
        platforms=data.platforms,
    )

    return APIResponse(
        success=True,
        data=StepCompletionResponse(
            step=OnboardingStep.PLATFORM_SELECTION.value,
            completed=True,
            next_step=next_step.value if next_step else None,
            progress_percentage=onboarding.get_progress_percentage(),
            message="Platform selection saved successfully",
        ),
    )


@router.post("/goals-setup", response_model=APIResponse[StepCompletionResponse])
async def save_goals_setup(
    data: GoalsSetupRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Save Step 3: Goals Setup.

    Captures KPIs, targets, currency, and timezone.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Save data (convert dollars to cents for storage)
    onboarding.primary_kpi = data.primary_kpi.value
    onboarding.target_roas = data.target_roas
    onboarding.target_cpa_cents = int(data.target_cpa * 100) if data.target_cpa else None
    onboarding.monthly_budget_cents = (
        int(data.monthly_budget * 100) if data.monthly_budget else None
    )
    onboarding.currency = data.currency
    onboarding.timezone = data.timezone

    # Mark step completed
    mark_step_completed(onboarding, OnboardingStep.GOALS_SETUP)
    await db.commit()

    next_step = onboarding.get_next_step()

    logger.info(
        "onboarding_step_completed",
        step="goals_setup",
        tenant_id=current_user.tenant_id,
        primary_kpi=data.primary_kpi.value,
    )

    return APIResponse(
        success=True,
        data=StepCompletionResponse(
            step=OnboardingStep.GOALS_SETUP.value,
            completed=True,
            next_step=next_step.value if next_step else None,
            progress_percentage=onboarding.get_progress_percentage(),
            message="Goals setup saved successfully",
        ),
    )


@router.post("/automation-preferences", response_model=APIResponse[StepCompletionResponse])
async def save_automation_preferences(
    data: AutomationPreferencesRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Save Step 4: Automation Preferences.

    Captures automation mode and notification settings.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Save data
    onboarding.automation_mode = data.automation_mode.value
    onboarding.auto_pause_enabled = data.auto_pause_enabled
    onboarding.auto_scale_enabled = data.auto_scale_enabled
    onboarding.notification_email = data.notification_email
    onboarding.notification_slack = data.notification_slack
    onboarding.notification_whatsapp = data.notification_whatsapp

    # Store additional preferences
    additional = onboarding.additional_preferences or {}
    if data.slack_webhook_url:
        additional["slack_webhook_url"] = data.slack_webhook_url
    if data.whatsapp_phone:
        additional["whatsapp_phone"] = data.whatsapp_phone
    onboarding.additional_preferences = additional

    # Mark step completed
    mark_step_completed(onboarding, OnboardingStep.AUTOMATION_PREFERENCES)
    await db.commit()

    next_step = onboarding.get_next_step()

    logger.info(
        "onboarding_step_completed",
        step="automation_preferences",
        tenant_id=current_user.tenant_id,
        automation_mode=data.automation_mode.value,
    )

    return APIResponse(
        success=True,
        data=StepCompletionResponse(
            step=OnboardingStep.AUTOMATION_PREFERENCES.value,
            completed=True,
            next_step=next_step.value if next_step else None,
            progress_percentage=onboarding.get_progress_percentage(),
            message="Automation preferences saved successfully",
        ),
    )


@router.post("/trust-gate-config", response_model=APIResponse[StepCompletionResponse])
async def save_trust_gate_config(
    data: TrustGateConfigRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Save Step 5: Trust Gate Configuration.

    Captures trust thresholds and action limits.
    This is the final step of onboarding.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Save data (convert dollars to cents for storage)
    onboarding.trust_threshold_autopilot = data.trust_threshold_autopilot
    onboarding.trust_threshold_alert = data.trust_threshold_alert
    onboarding.require_approval_above = (
        int(data.require_approval_above * 100) if data.require_approval_above else None
    )
    onboarding.max_daily_actions = data.max_daily_actions

    # Mark step completed
    mark_step_completed(onboarding, OnboardingStep.TRUST_GATE_CONFIG)
    onboarding.completed_by_user_id = current_user.id

    # Update tenant settings with trust thresholds
    from app.models import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        settings = tenant.settings or {}
        settings["trust_threshold_autopilot"] = data.trust_threshold_autopilot
        settings["trust_threshold_alert"] = data.trust_threshold_alert
        settings["max_daily_actions"] = data.max_daily_actions
        settings["automation_mode"] = onboarding.automation_mode
        settings["onboarding_completed"] = True
        tenant.settings = settings

    await db.commit()

    logger.info(
        "onboarding_completed",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return APIResponse(
        success=True,
        data=StepCompletionResponse(
            step=OnboardingStep.TRUST_GATE_CONFIG.value,
            completed=True,
            next_step=None,
            progress_percentage=100,
            message="Onboarding completed! Welcome to Stratum AI.",
        ),
    )


@router.post("/skip", response_model=APIResponse[dict])
async def skip_onboarding(
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Skip remaining onboarding steps.

    Uses default values for uncompleted steps.
    Not recommended but available for users who want to explore first.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)

    # Mark as skipped
    onboarding.status = OnboardingStatus.SKIPPED
    onboarding.completed_at = datetime.now(UTC)

    # Update tenant settings
    from app.models import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        settings = tenant.settings or {}
        settings["onboarding_skipped"] = True
        tenant.settings = settings

    await db.commit()

    logger.info(
        "onboarding_skipped",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return APIResponse(
        success=True,
        data={"message": "Onboarding skipped. You can complete setup later in Settings."},
    )


@router.post("/reset", response_model=APIResponse[dict])
async def reset_onboarding(
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reset onboarding to start over.

    Clears all saved preferences and resets to step 1.
    """
    result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == current_user.tenant_id)
    )
    onboarding = result.scalar_one_or_none()

    if onboarding:
        # Reset all fields
        onboarding.status = OnboardingStatus.NOT_STARTED
        onboarding.current_step = OnboardingStep.BUSINESS_PROFILE
        onboarding.completed_steps = []
        onboarding.industry = None
        onboarding.industry_other = None
        onboarding.monthly_ad_spend = None
        onboarding.team_size = None
        onboarding.company_website = None
        onboarding.target_markets = None
        onboarding.selected_platforms = None
        onboarding.primary_kpi = None
        onboarding.target_roas = None
        onboarding.target_cpa_cents = None
        onboarding.monthly_budget_cents = None
        onboarding.automation_mode = None
        onboarding.started_at = None
        onboarding.completed_at = None
        onboarding.completed_by_user_id = None
        onboarding.additional_preferences = {}

        await db.commit()

    logger.info(
        "onboarding_reset",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return APIResponse(
        success=True,
        data={"message": "Onboarding reset. Start from step 1."},
    )


@router.get("/check", response_model=APIResponse[dict])
async def check_onboarding_required(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Check if onboarding is required for the current tenant.

    Returns whether to show the onboarding wizard.
    """
    onboarding = await get_or_create_onboarding(current_user.tenant_id, db)
    await db.commit()

    required = onboarding.status in [
        OnboardingStatus.NOT_STARTED,
        OnboardingStatus.IN_PROGRESS,
    ]

    return APIResponse(
        success=True,
        data={
            "required": required,
            "redirect_to": "/onboarding" if required else None,
        },
    )
