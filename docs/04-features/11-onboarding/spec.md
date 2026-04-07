# Onboarding Wizard Specification

## Overview

The Onboarding Wizard guides new tenants through initial configuration of the Stratum AI platform. It collects business profile information, platform connections, goals, automation preferences, and trust gate settings.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONBOARDING WIZARD FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    WIZARD STEPS                           │  │
│  │                                                          │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐                │  │
│  │  │   1     │   │   2     │   │   3     │                │  │
│  │  │Business │──►│Platform │──►│  Goals  │                │  │
│  │  │ Profile │   │Selection│   │  Setup  │                │  │
│  │  └─────────┘   └─────────┘   └─────────┘                │  │
│  │       │             │             │                      │  │
│  │       ▼             ▼             ▼                      │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐                │  │
│  │  │   4     │   │   5     │   │Complete │                │  │
│  │  │Automation│──►│ Trust   │──►│  ✓     │                │  │
│  │  │  Prefs  │   │  Gate   │   │         │                │  │
│  │  └─────────┘   └─────────┘   └─────────┘                │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    STATE MANAGEMENT                       │  │
│  │                                                          │  │
│  │  • Progress persisted to database                        │  │
│  │  • Can resume from any step                              │  │
│  │  • Steps can be skipped (with limitations)               │  │
│  │  • Back navigation preserves data                        │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### OnboardingStatus

```python
class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
```

### OnboardingStep

```python
class OnboardingStep(str, Enum):
    BUSINESS_PROFILE = "business_profile"
    PLATFORM_SELECTION = "platform_selection"
    GOALS_SETUP = "goals_setup"
    AUTOMATION_PREFERENCES = "automation_preferences"
    TRUST_GATE_CONFIG = "trust_gate_config"
```

### OnboardingState

```python
class OnboardingState:
    tenant_id: int
    current_step: OnboardingStep
    overall_status: OnboardingStatus
    steps: dict[OnboardingStep, StepStatus]
    started_at: datetime
    completed_at: datetime | None

class StepStatus:
    step: OnboardingStep
    status: OnboardingStatus
    data: dict
    completed_at: datetime | None
```

---

## Enums

### Industry

```python
class Industry(str, Enum):
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    LEAD_GEN = "lead_gen"
    MOBILE_APP = "mobile_app"
    AGENCY = "agency"
    RETAIL = "retail"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    OTHER = "other"
```

### MonthlyAdSpend

```python
class MonthlyAdSpend(str, Enum):
    UNDER_10K = "under_10k"
    FROM_10K_TO_50K = "10k_50k"
    FROM_50K_TO_100K = "50k_100k"
    FROM_100K_TO_500K = "100k_500k"
    OVER_500K = "over_500k"
```

### TeamSize

```python
class TeamSize(str, Enum):
    SOLO = "solo"
    SMALL = "2_5"
    MEDIUM = "6_20"
    LARGE = "21_50"
    ENTERPRISE = "50_plus"
```

### AutomationMode

```python
class AutomationMode(str, Enum):
    CONSERVATIVE = "conservative"    # Advisory only
    MODERATE = "moderate"            # Soft block
    AGGRESSIVE = "aggressive"        # Full autopilot
```

### PrimaryKPI

```python
class PrimaryKPI(str, Enum):
    ROAS = "roas"
    CPA = "cpa"
    REVENUE = "revenue"
    CONVERSIONS = "conversions"
    LEADS = "leads"
```

---

## Step 1: Business Profile

### Purpose
Collect basic business information for context and personalization.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_name` | string | Yes | Business name |
| `industry` | Industry | Yes | Business sector |
| `monthly_ad_spend` | MonthlyAdSpend | Yes | Estimated monthly spend |
| `team_size` | TeamSize | Yes | Marketing team size |
| `website_url` | string | No | Company website |
| `timezone` | string | Yes | Preferred timezone |

### Validation

```python
class BusinessProfileRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=100)
    industry: Industry
    monthly_ad_spend: MonthlyAdSpend
    team_size: TeamSize
    website_url: str | None = Field(None, pattern=r'^https?://')
    timezone: str = Field(default="America/Los_Angeles")
```

---

## Step 2: Platform Selection

### Purpose
Select and connect advertising platforms.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platforms` | list[Platform] | Yes | Selected platforms |
| `primary_platform` | Platform | No | Main platform |
| `credentials` | dict | No | Platform credentials |

### Platforms

```python
class Platform(str, Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
```

### Validation

```python
class PlatformSelectionRequest(BaseModel):
    platforms: list[Platform] = Field(..., min_items=1)
    primary_platform: Platform | None = None
    connect_later: bool = False  # Skip credential entry
```

---

## Step 3: Goals Setup

### Purpose
Define business goals and key performance indicators.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `primary_kpi` | PrimaryKPI | Yes | Main success metric |
| `target_roas` | float | If ROAS | Target ROAS value |
| `target_cpa` | float | If CPA | Target CPA value |
| `monthly_budget_target` | float | No | Budget goal |
| `revenue_goal` | float | No | Revenue target |

### Validation

```python
class GoalsSetupRequest(BaseModel):
    primary_kpi: PrimaryKPI
    target_roas: float | None = Field(None, gt=0)
    target_cpa: float | None = Field(None, gt=0)
    monthly_budget_target: float | None = Field(None, gt=0)
    revenue_goal: float | None = Field(None, gt=0)

    @validator('target_roas')
    def roas_required_if_kpi(cls, v, values):
        if values.get('primary_kpi') == PrimaryKPI.ROAS and v is None:
            raise ValueError('Target ROAS required when ROAS is primary KPI')
        return v
```

---

## Step 4: Automation Preferences

### Purpose
Configure automation behavior and risk tolerance.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `automation_mode` | AutomationMode | Yes | Automation level |
| `auto_pause_enabled` | bool | No | Auto-pause poor performers |
| `budget_automation` | bool | No | Enable budget changes |
| `notification_preferences` | dict | No | Alert settings |

### Automation Modes

| Mode | Behavior | Trust Gate |
|------|----------|------------|
| `conservative` | Advisory only, no auto-actions | All actions require approval |
| `moderate` | Soft block, confirmations required | Some auto-actions with caps |
| `aggressive` | Full autopilot when healthy | Auto-execute within thresholds |

### Validation

```python
class AutomationPreferencesRequest(BaseModel):
    automation_mode: AutomationMode
    auto_pause_enabled: bool = False
    budget_automation: bool = False
    max_budget_change_percent: float = Field(20.0, ge=5, le=50)
    notification_email: str | None = None
    slack_webhook: str | None = None
```

---

## Step 5: Trust Gate Configuration

### Purpose
Set trust thresholds and safety controls.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `signal_health_threshold` | int | Yes | Minimum health score |
| `min_roas_threshold` | float | No | Minimum ROAS for automation |
| `max_budget_increase` | float | No | Max budget increase % |
| `cooldown_hours` | int | No | Hours between changes |
| `require_confirmation` | bool | No | Require approval |

### Defaults by Mode

| Setting | Conservative | Moderate | Aggressive |
|---------|-------------|----------|------------|
| `signal_health_threshold` | 80 | 70 | 60 |
| `min_roas_threshold` | 1.5 | 1.0 | 0.8 |
| `max_budget_increase` | 10% | 20% | 30% |
| `cooldown_hours` | 48 | 24 | 12 |
| `require_confirmation` | Always | Soft block | Never |

### Validation

```python
class TrustGateConfigRequest(BaseModel):
    signal_health_threshold: int = Field(70, ge=40, le=100)
    min_roas_threshold: float = Field(1.0, ge=0.5, le=5.0)
    max_budget_increase_percent: float = Field(20.0, ge=5, le=50)
    max_budget_decrease_percent: float = Field(30.0, ge=10, le=80)
    cooldown_hours: int = Field(24, ge=1, le=168)
    require_confirmation: bool = True
```

---

## Progress Tracking

### Step Status

```python
# Check step completion
async def get_step_status(tenant_id: int, step: OnboardingStep) -> StepStatus:
    state = await get_onboarding_state(tenant_id)
    return state.steps.get(step, StepStatus(step=step, status=OnboardingStatus.NOT_STARTED))
```

### Overall Progress

```python
# Calculate completion percentage
def calculate_progress(state: OnboardingState) -> float:
    total_steps = len(OnboardingStep)
    completed = sum(
        1 for step in state.steps.values()
        if step.status in [OnboardingStatus.COMPLETED, OnboardingStatus.SKIPPED]
    )
    return (completed / total_steps) * 100
```

---

## Skip Logic

### Skippable Steps

| Step | Skippable | Consequences |
|------|-----------|--------------|
| business_profile | No | Required for personalization |
| platform_selection | No | Required for functionality |
| goals_setup | Yes | Uses defaults |
| automation_preferences | Yes | Uses conservative mode |
| trust_gate_config | Yes | Uses safe defaults |

### Skip Handling

```python
async def skip_step(tenant_id: int, step: OnboardingStep) -> bool:
    if step in [OnboardingStep.BUSINESS_PROFILE, OnboardingStep.PLATFORM_SELECTION]:
        raise ValueError(f"Step {step} cannot be skipped")

    # Apply defaults
    defaults = get_default_config(step)
    await save_step_data(tenant_id, step, defaults)
    await update_step_status(tenant_id, step, OnboardingStatus.SKIPPED)

    return True
```

---

## Resume Capability

### State Persistence

- All step data saved to database
- User can close and resume later
- Progress bar shows completion
- Last saved step auto-selected

### Resume Flow

```python
async def resume_onboarding(tenant_id: int) -> OnboardingState:
    state = await get_onboarding_state(tenant_id)

    if state.overall_status == OnboardingStatus.NOT_STARTED:
        state.current_step = OnboardingStep.BUSINESS_PROFILE
    elif state.overall_status == OnboardingStatus.COMPLETED:
        return state  # Already complete
    else:
        # Find first incomplete step
        for step in OnboardingStep:
            if state.steps.get(step, {}).status == OnboardingStatus.NOT_STARTED:
                state.current_step = step
                break

    return state
```

---

## Completion Actions

### On Complete

1. Create default dashboard configuration
2. Initialize trust gate settings
3. Schedule platform data sync
4. Send welcome email
5. Create sample reports

```python
async def complete_onboarding(tenant_id: int):
    # Apply all configurations
    await apply_automation_settings(tenant_id)
    await apply_trust_gate_settings(tenant_id)
    await initialize_dashboard(tenant_id)

    # Update status
    await update_onboarding_status(
        tenant_id,
        OnboardingStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc)
    )

    # Trigger welcome actions
    await send_welcome_email(tenant_id)
    await schedule_initial_sync(tenant_id)
```

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
