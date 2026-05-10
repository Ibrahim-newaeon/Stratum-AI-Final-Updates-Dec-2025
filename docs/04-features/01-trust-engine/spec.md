# Trust Engine Specification

## Overview

The Trust Engine is Stratum AI's core decision-making component that evaluates signal health before allowing automation execution. It implements the "Trust-Gated Autopilot" philosophy: automated actions only execute when data quality meets safety thresholds.

---

## Philosophy

> "Automated budget decisions should NEVER execute when data quality is compromised."

The Trust Engine protects advertisers from costly mistakes based on unreliable signals by implementing a three-tier decision system:

| Status | Score Range | Behavior |
|--------|-------------|----------|
| **HEALTHY** | 70-100 | Full autopilot enabled |
| **DEGRADED** | 40-69 | Alert + hold for review |
| **CRITICAL** | 0-39 | Manual intervention required |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TRUST ENGINE FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   SIGNALS    │───▶│   HEALTH     │───▶│   TRUST      │      │
│  │  COLLECTORS  │    │ CALCULATOR   │    │    GATE      │      │
│  └──────────────┘    └──────────────┘    └───────┬──────┘      │
│                                                   │             │
│                           ┌───────────────────────┼─────┐       │
│                           ▼                       ▼     ▼       │
│                      ┌────────┐            ┌──────┐ ┌──────┐    │
│                      │  PASS  │            │ HOLD │ │BLOCK │    │
│                      └───┬────┘            └──┬───┘ └──┬───┘    │
│                          │                    │        │        │
│                          ▼                    ▼        ▼        │
│                   ┌───────────┐         ┌─────────────────┐     │
│                   │  EXECUTE  │         │  ALERT / MANUAL │     │
│                   │ AUTOMATION│         │   INTERVENTION  │     │
│                   └───────────┘         └─────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Signal Health Calculator

Computes a composite signal health score from four components:

| Component | Weight | Description |
|-----------|--------|-------------|
| **EMQ Score** | 40% | Event Match Quality from platform data |
| **Freshness Score** | 25% | How recent and complete the data is |
| **Variance Score** | 20% | Consistency between reported and actual metrics |
| **Anomaly Score** | 15% | Detection of unusual patterns |
| **CDP EMQ** | +10% | CDP identity resolution quality (when available) |

#### Weight Redistribution with CDP

When CDP data is available, weights are proportionally reduced:

```
Without CDP:          With CDP:
EMQ: 40%              EMQ: 36% (40% × 0.90)
Freshness: 25%        Freshness: 22.5%
Variance: 20%         Variance: 18%
Anomaly: 15%          Anomaly: 13.5%
                      CDP: 10%
```

### 2. Trust Gate

The binary decision checkpoint that evaluates whether an automation action should proceed.

#### Gate Decisions

```python
class GateDecision(str, Enum):
    PASS = "pass"    # Execute automation
    HOLD = "hold"    # Queue for review
    BLOCK = "block"  # Require manual intervention
```

#### Action Risk Levels

| Risk Level | Threshold | Example Actions |
|------------|-----------|-----------------|
| **High-Risk** | 80+ | `increase_budget`, `launch_new_campaigns`, `expand_targeting` |
| **Standard** | 70+ | `update_budget`, `update_bid`, `update_status` |
| **Conservative** | 60+ | `pause_underperforming`, `reduce_budget`, `reduce_bid` |
| **Always Allowed** | Any | `pause_all`, `emergency_stop` |

### 3. Autopilot Engine

Orchestrates rule evaluation and action generation.

#### Built-in Rules

| Rule | Type | Description |
|------|------|-------------|
| Budget Pacing | `budget_pacing` | Ensures even spend throughout day/month |
| Performance Scaling | `performance_scaling` | Adjusts budget based on ROAS/CPA |
| Status Management | `status_management` | Pauses poor performers |

---

## Data Models

### SignalHealth

```python
class SignalHealth(BaseModel):
    overall_score: float       # 0-100 composite score
    emq_score: float           # 0-100 EMQ component
    freshness_score: float     # 0-100 freshness component
    variance_score: float      # 0-100 variance component
    anomaly_score: float       # 0-100 anomaly component
    cdp_emq_score: float | None  # 0-100 CDP component (optional)
    status: str                # "healthy" | "degraded" | "critical"
    issues: list[str]          # Human-readable issue descriptions
    last_updated: datetime
```

### TrustGateConfig

```python
class TrustGateConfig:
    pass_threshold: float = 70.0       # Score >= 70 allows execution
    hold_threshold: float = 40.0       # Score 40-69 holds for review
    high_risk_threshold: float = 80.0  # Higher threshold for risky actions
    conservative_threshold: float = 60.0  # Lower for safe actions

    high_risk_actions: list[str] = [
        "increase_budget",
        "launch_new_campaigns",
        "expand_targeting",
        "increase_bid",
    ]

    conservative_actions: list[str] = [
        "pause_underperforming",
        "reduce_budget",
        "reduce_bid",
    ]

    always_allowed_actions: list[str] = [
        "pause_all",
        "emergency_stop",
    ]
```

### AutomationAction

```python
class AutomationAction(BaseModel):
    platform: Platform           # meta, google, tiktok, snapchat
    account_id: str
    entity_type: str             # campaign, adset, ad
    entity_id: str
    action_type: str             # update_budget, update_status, etc.
    parameters: dict[str, Any]
    status: str = "pending"
    created_at: datetime
    executed_at: datetime | None
    result: dict | None
    trust_gate_passed: bool
    signal_health_at_execution: float | None
```

---

## Component Score Calculations

### EMQ Score

```python
def calculate_emq_component(emq_scores: list[float]) -> float:
    """
    Convert platform EMQ scores (0-10) to 0-100 scale.
    Returns average across all platforms.
    """
    if not emq_scores:
        return 75.0  # Default moderate score

    converted = [min(100, max(0, score * 10)) for score in emq_scores]
    return sum(converted) / len(converted)
```

### Freshness Score

```python
def calculate_freshness_component(last_received: datetime) -> float:
    """
    Score based on data age:
    - < 24 hours: 100
    - 24-48 hours: Linear decay
    - > 48 hours: 0 (stale)
    """
    age_hours = (now - last_received).total_seconds() / 3600

    if age_hours <= 24:
        return 100.0
    elif age_hours >= 48:
        return 0.0
    else:
        decay = (age_hours - 24) / 24
        return 100.0 * (1.0 - decay)
```

### Variance Score

```python
def calculate_variance_component(
    platform_revenue: float,
    ga4_revenue: float
) -> float:
    """
    Score based on revenue variance between platforms.
    - < 10%: 100
    - 10-15%: Linear decay
    - > 15%: Significant penalty
    """
    if ga4_revenue > 0:
        variance = abs(platform_revenue - ga4_revenue) / ga4_revenue
    else:
        variance = 1.0 if platform_revenue > 0 else 0.0

    if variance <= 0.10:
        return 100.0
    elif variance >= 0.15:
        # Decay continues beyond 15%
        return max(0, 100 - (variance - 0.10) * 500)
    else:
        # Linear decay 10-15%
        return 100 * (1 - (variance - 0.10) / 0.05 * 0.3)
```

### Anomaly Score

```python
def calculate_anomaly_component(
    current: dict[str, float],
    historical: list[dict[str, float]]
) -> float:
    """
    Detect anomalies using z-score analysis.
    Checks: spend, conversions, cpa, roas
    """
    if len(historical) < 7:
        return 90.0  # Default with insufficient data

    anomaly_count = 0
    metrics_checked = 0

    for metric in ["spend", "conversions", "cpa", "roas"]:
        values = [h.get(metric) for h in historical if h.get(metric)]
        if len(values) < 7:
            continue

        mean = sum(values) / len(values)
        std = (sum((x - mean)**2 for x in values) / len(values)) ** 0.5

        if std > 0:
            z = abs(current[metric] - mean) / std
            if z > 3.0:  # 3 standard deviations
                anomaly_count += 1

        metrics_checked += 1

    anomaly_ratio = anomaly_count / metrics_checked
    if anomaly_ratio == 0:
        return 100.0
    elif anomaly_ratio <= 0.25:
        return 80.0
    elif anomaly_ratio <= 0.5:
        return 50.0
    else:
        return 20.0
```

---

## Autopilot Modes

Based on signal health, the system operates in different modes:

| Mode | Score Range | Allowed Actions |
|------|-------------|-----------------|
| **Normal** | 70+ | All actions enabled |
| **Limited** | 60-69 | Conservative actions only |
| **Cuts Only** | 40-59 | Pause/reduce actions only |
| **Frozen** | <40 | No automation |

```python
def get_autopilot_mode(signal_health: SignalHealth) -> tuple[str, str]:
    score = signal_health.overall_score

    if score >= 80:
        return "normal", "Signal health excellent - full autopilot"
    elif score >= 70:
        return "normal", "Signal health good - autopilot enabled"
    elif score >= 60:
        return "limited", "Signal health degraded - conservative only"
    elif score >= 40:
        return "cuts_only", "Signal health low - pause/reduce only"
    else:
        return "frozen", "Signal health critical - automation frozen"
```

---

## Configuration

### Environment Variables

```bash
# Thresholds
TRUST_HEALTHY_THRESHOLD=70
TRUST_DEGRADED_THRESHOLD=40
TRUST_HIGH_RISK_THRESHOLD=80

# Freshness
TRUST_MAX_DATA_AGE_HOURS=24
TRUST_STALE_DATA_AGE_HOURS=48

# Variance
TRUST_MAX_VARIANCE_PCT=15
TRUST_WARNING_VARIANCE_PCT=10

# Anomaly
TRUST_ANOMALY_ZSCORE_THRESHOLD=3.0

# CDP
TRUST_CDP_WEIGHT=0.10
TRUST_CDP_ENABLED=true
```

### Feature Flags

| Flag | Description |
|------|-------------|
| `signal_health` | Enable signal health calculation |
| `signal_health_history` | Enable historical tracking |
| `attribution_variance` | Enable variance tracking |
| `trust_audit_logs` | Enable audit logging |

---

## Database Schema

### Signal Health History

```sql
CREATE TABLE signal_health_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    date DATE NOT NULL,
    overall_score DECIMAL(5,2),
    status VARCHAR(20),
    emq_score_avg DECIMAL(5,2),
    event_loss_pct_avg DECIMAL(5,2),
    freshness_minutes_avg INTEGER,
    api_error_rate_avg DECIMAL(5,4),
    platforms_ok INTEGER DEFAULT 0,
    platforms_risk INTEGER DEFAULT 0,
    platforms_degraded INTEGER DEFAULT 0,
    platforms_critical INTEGER DEFAULT 0,
    automation_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, date)
);
```

### Trust Gate Audit Log

```sql
CREATE TABLE trust_gate_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    decision_type VARCHAR(20) NOT NULL, -- execute, hold, block
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(20),
    entity_id VARCHAR(100),
    entity_name VARCHAR(255),
    platform VARCHAR(20),
    signal_health_score DECIMAL(5,2),
    signal_health_status VARCHAR(20),
    gate_passed BOOLEAN,
    gate_reason JSONB,
    action_payload JSONB,
    action_result JSONB,
    healthy_threshold DECIMAL(5,2),
    degraded_threshold DECIMAL(5,2),
    is_dry_run BOOLEAN DEFAULT FALSE,
    triggered_by_system BOOLEAN DEFAULT TRUE,
    triggered_by_user_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
- [Autopilot Feature](../07-autopilot/spec.md) - Automation engine details
