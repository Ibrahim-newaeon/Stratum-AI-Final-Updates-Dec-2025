# Autopilot Specification

## Overview

The Autopilot system provides trust-gated automation for advertising campaign management. It evaluates campaign performance and generates optimization actions that pass through the Trust Gate before execution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOPILOT ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   SIGNAL HEALTH                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ EMQ Score   │  │  Metrics    │  │  Platform   │     │  │
│  │  │  Quality    │  │ Freshness   │  │  Status     │     │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │  │
│  └─────────┼────────────────┼────────────────┼────────────┘  │
│            └────────────────┼────────────────┘               │
│                             ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    TRUST GATE                            │  │
│  │                                                          │  │
│  │  Score ≥ 70  →  HEALTHY   →  Auto-execute               │  │
│  │  Score 40-69 →  DEGRADED  →  Hold + Alert               │  │
│  │  Score < 40  →  UNHEALTHY →  Block + Manual             │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                 │
│                             ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 AUTOPILOT ENGINE                         │  │
│  │                                                          │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │  │  Budget    │ │Performance │ │  Status    │          │  │
│  │  │  Pacing    │ │  Scaling   │ │ Management │          │  │
│  │  └────────────┘ └────────────┘ └────────────┘          │  │
│  │                                                          │  │
│  │  Rules evaluate → Actions proposed → Gate approves       │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                 │
│                             ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 ENFORCEMENT LAYER                        │  │
│  │                                                          │  │
│  │  Mode: advisory | soft_block | hard_block               │  │
│  │  Budget caps, ROAS thresholds, frequency limits         │  │
│  │  Kill switch for emergency override                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Autopilot Levels

| Level | Name | Behavior |
|-------|------|----------|
| 0 | Suggest Only | Generate suggestions, no auto-execution |
| 1 | Guarded Auto | Auto-execute within caps |
| 2 | Approval Required | All actions require manual approval |

---

## Data Models

### QueuedAutopilotAction

Stores actions pending execution or approval.

```python
class QueuedAutopilotAction:
    id: UUID
    tenant_id: int
    date: date                     # Action date

    # Entity
    action_type: str               # budget_increase, pause_campaign, etc.
    entity_type: str               # campaign, adset, creative
    entity_id: str                 # Platform entity ID
    entity_name: str               # Human-readable name
    platform: str                  # meta, google, tiktok, snapchat

    # Action details
    action_json: dict              # Full action payload
    before_value: dict | None      # State before change
    after_value: dict | None       # State after change

    # Workflow
    status: str                    # queued, approved, applied, failed, dismissed
    created_at: datetime
    approved_at: datetime | None
    applied_at: datetime | None
    approved_by_user_id: int | None
    created_by_user_id: int | None
    error: str | None
```

### TenantEnforcementSettings

Per-tenant enforcement configuration.

```python
class TenantEnforcementSettings:
    id: UUID
    tenant_id: int

    # Kill switch
    enforcement_enabled: bool = True

    # Default mode
    default_mode: EnforcementMode = ADVISORY

    # Budget thresholds
    max_daily_budget: float | None
    max_campaign_budget: float | None
    budget_increase_limit_pct: float = 30.0

    # ROAS thresholds
    min_roas_threshold: float = 1.0
    roas_lookback_days: int = 7

    # Frequency settings
    max_budget_changes_per_day: int = 5
    min_hours_between_changes: int = 4
```

### TenantEnforcementRule

Custom enforcement rules per tenant.

```python
class TenantEnforcementRule:
    id: UUID
    settings_id: UUID
    tenant_id: int

    rule_id: str                   # Unique identifier
    rule_type: ViolationType       # budget_exceeded, roas_below_threshold
    threshold_value: float
    enforcement_mode: EnforcementMode
    enabled: bool = True
    description: str | None
```

### EnforcementAuditLog

Audit trail for enforcement interventions.

```python
class EnforcementAuditLog:
    id: UUID
    tenant_id: int
    timestamp: datetime

    # Context
    action_type: str
    entity_type: str
    entity_id: str

    # Violation
    violation_type: ViolationType

    # Intervention
    intervention_action: InterventionAction
    enforcement_mode: EnforcementMode

    # Details
    details: dict | None
    user_id: int | None
    override_reason: str | None
```

---

## Enums

### EnforcementMode

```python
class EnforcementMode(str, Enum):
    ADVISORY = "advisory"      # Warn only, no blocking
    SOFT_BLOCK = "soft_block"  # Warn + require confirmation
    HARD_BLOCK = "hard_block"  # Prevent action via API
```

### ViolationType

```python
class ViolationType(str, Enum):
    BUDGET_EXCEEDED = "budget_exceeded"
    ROAS_BELOW_THRESHOLD = "roas_below_threshold"
    DAILY_SPEND_LIMIT = "daily_spend_limit"
    CAMPAIGN_PAUSE_REQUIRED = "campaign_pause_required"
    FREQUENCY_CAP_EXCEEDED = "frequency_cap_exceeded"
```

### InterventionAction

```python
class InterventionAction(str, Enum):
    WARNED = "warned"
    BLOCKED = "blocked"
    AUTO_PAUSED = "auto_paused"
    OVERRIDE_LOGGED = "override_logged"
    NOTIFICATION_SENT = "notification_sent"
    KILL_SWITCH_CHANGED = "kill_switch_changed"
```

### ActionStatus

```python
class ActionStatus(str, Enum):
    QUEUED = "queued"         # Pending approval
    APPROVED = "approved"     # Approved, awaiting execution
    APPLIED = "applied"       # Successfully executed
    FAILED = "failed"         # Execution failed
    DISMISSED = "dismissed"   # Manually dismissed
```

---

## Built-in Optimization Rules

### 1. Budget Pacing Rule

Ensures campaigns spend budget evenly throughout the day.

```python
class BudgetPacingRule:
    underpace_threshold: float = 0.7   # <70% expected spend
    overpace_threshold: float = 1.3    # >130% expected spend
    adjustment_percent: float = 20.0   # Budget adjustment
```

**Logic**:
- Calculate expected spend: `hours_elapsed / 24 * daily_budget`
- Compare actual spend to expected
- Under-pacing → Suggest budget increase
- Over-pacing → Log warning for manual review

### 2. Performance Scaling Rule

Scales budget based on ROAS/CPA performance.

```python
class PerformanceScalingRule:
    scale_up_multiplier: float = 1.2    # +20% for good performance
    scale_down_multiplier: float = 0.8  # -20% for poor performance
    min_conversions: int = 5            # Minimum data threshold
    cooldown_days: int = 1              # Days between changes
```

**Logic**:
- ROAS ≥ 120% of target → Scale up budget
- ROAS ≤ 70% of target → Scale down budget
- Same logic for CPA (inverted)

### 3. Status Management Rule

Pauses poor-performing campaigns.

```python
class StatusManagementRule:
    pause_after_days: int = 7           # Days before pause
    max_cpa_multiplier: float = 2.0     # Pause if CPA is 2x target
    min_roas_multiplier: float = 0.5    # Pause if ROAS is 0.5x target
```

---

## Trust Gate Integration

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   HEALTHY   │     │  DEGRADED   │     │  UNHEALTHY  │
│  Score ≥70  │     │ Score 40-69 │     │  Score <40  │
├─────────────┤     ├─────────────┤     ├─────────────┤
│   EXECUTE   │     │    HOLD     │     │    BLOCK    │
│  Auto-run   │     │   + Alert   │     │   Manual    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Gate Evaluation Flow

```python
async def evaluate_action(action, signal_health):
    # Check signal health
    if signal_health.score >= 70:
        decision = GateDecision.APPROVED
    elif signal_health.score >= 40:
        decision = GateDecision.HOLD
    else:
        decision = GateDecision.BLOCKED

    # Check enforcement rules
    enforcement_result = await check_enforcement(action)

    if enforcement_result.has_violations:
        if enforcement_result.mode == HARD_BLOCK:
            decision = GateDecision.BLOCKED
        elif enforcement_result.mode == SOFT_BLOCK:
            decision = GateDecision.HOLD

    return decision
```

---

## Enforcement Thresholds

### Default Values

| Setting | Default | Description |
|---------|---------|-------------|
| `budget_increase_limit_pct` | 30% | Max budget increase per change |
| `min_roas_threshold` | 1.0x | Minimum acceptable ROAS |
| `roas_lookback_days` | 7 | Days for ROAS calculation |
| `max_budget_changes_per_day` | 5 | Change frequency limit |
| `min_hours_between_changes` | 4 | Cooldown between changes |

### Caps (Guarded Mode)

```python
AUTOPILOT_CAPS = {
    "daily_max": 1000.00,      # Max daily budget increase
    "campaign_max": 5000.00,   # Max per-campaign budget
    "cpa_ceiling": 50.00,      # Max acceptable CPA
    "roas_floor": 1.5,         # Minimum acceptable ROAS
}
```

---

## Database Schema

```sql
-- Queued actions
CREATE TABLE queued_autopilot_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date DATE NOT NULL,

    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_name VARCHAR(255),
    platform VARCHAR(50) NOT NULL,

    action_json TEXT NOT NULL,
    before_value TEXT,
    after_value TEXT,

    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    approved_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    error TEXT
);

-- Enforcement settings
CREATE TABLE tenant_enforcement_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,

    enforcement_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    default_mode VARCHAR(50) NOT NULL DEFAULT 'advisory',

    max_daily_budget FLOAT,
    max_campaign_budget FLOAT,
    budget_increase_limit_pct FLOAT NOT NULL DEFAULT 30.0,

    min_roas_threshold FLOAT NOT NULL DEFAULT 1.0,
    roas_lookback_days INTEGER NOT NULL DEFAULT 7,

    max_budget_changes_per_day INTEGER NOT NULL DEFAULT 5,
    min_hours_between_changes INTEGER NOT NULL DEFAULT 4,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Custom rules
CREATE TABLE tenant_enforcement_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settings_id UUID NOT NULL REFERENCES tenant_enforcement_settings(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    rule_id VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    threshold_value FLOAT NOT NULL,
    enforcement_mode VARCHAR(50) NOT NULL DEFAULT 'advisory',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,

    UNIQUE(tenant_id, rule_id)
);

-- Audit log
CREATE TABLE enforcement_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,

    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,

    violation_type VARCHAR(50) NOT NULL,
    intervention_action VARCHAR(50) NOT NULL,
    enforcement_mode VARCHAR(50) NOT NULL,

    details JSONB,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    override_reason TEXT
);
```

---

## Dry-Run Mode

Test actions without executing them.

```python
async def dry_run_action(action):
    """
    Evaluate action through full pipeline without execution.

    Returns:
        - would_execute: bool
        - decision_type: execute | hold | block
        - signal_health_score: float
        - gate_passed: bool
        - gate_reasons: list
        - warnings: list
    """
    pass
```

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
