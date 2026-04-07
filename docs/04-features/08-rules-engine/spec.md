# Rules Engine Specification

## Overview

The Rules Engine provides IFTTT-style automation for advertising campaign management. It enables users to define conditional rules that automatically trigger actions based on campaign performance metrics.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RULES ENGINE ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    RULE DEFINITION                        │  │
│  │                                                          │  │
│  │  IF [condition_field] [operator] [value]                 │  │
│  │  THEN [action_type] WITH [config]                        │  │
│  │  FOR [campaigns/platforms]                               │  │
│  │                                                          │  │
│  │  Example:                                                │  │
│  │  IF roas < 1.0 THEN pause_campaign FOR meta campaigns    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  RULE EVALUATION                          │  │
│  │                                                          │  │
│  │  1. Get applicable campaigns                             │  │
│  │  2. Evaluate condition per campaign                      │  │
│  │  3. Execute action for matched campaigns                 │  │
│  │  4. Log execution results                                │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ACTIONS                                │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │  Apply   │ │   Send   │ │  Pause   │ │  Adjust  │   │  │
│  │  │  Label   │ │  Alert   │ │ Campaign │ │  Budget  │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  │  ┌──────────┐ ┌──────────┐                             │  │
│  │  │  Notify  │ │  Notify  │                             │  │
│  │  │  Slack   │ │ WhatsApp │                             │  │
│  │  └──────────┘ └──────────┘                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Rule

Core rule definition.

```python
class Rule:
    id: int
    tenant_id: int

    # Identification
    name: str
    description: str | None
    status: RuleStatus               # draft, active, paused

    # Condition (IF)
    condition_field: str             # roas, ctr, cpc, cpa, spend, etc.
    condition_operator: RuleOperator # eq, ne, gt, lt, gte, lte, contains, in
    condition_value: str             # Value to compare against
    condition_duration_hours: int    # How long condition must be true

    # Action (THEN)
    action_type: RuleAction          # apply_label, send_alert, pause, etc.
    action_config: dict              # Action-specific configuration

    # Scope
    applies_to_campaigns: list[int] | None   # Specific campaigns
    applies_to_platforms: list[str] | None   # Specific platforms

    # Frequency Control
    cooldown_hours: int = 24         # Hours between triggers

    # Tracking
    last_evaluated_at: datetime | None
    last_triggered_at: datetime | None
    trigger_count: int = 0

    # Soft delete
    is_deleted: bool = False
```

### RuleExecution

Audit log for rule executions.

```python
class RuleExecution:
    id: int
    tenant_id: int
    rule_id: int
    campaign_id: int

    executed_at: datetime
    triggered: bool                  # Whether condition matched

    condition_result: dict           # Evaluation details
    action_result: dict              # Action execution result
```

---

## Enums

### RuleStatus

```python
class RuleStatus(str, Enum):
    DRAFT = "draft"      # Not yet active
    ACTIVE = "active"    # Running
    PAUSED = "paused"    # Temporarily disabled
```

### RuleOperator

```python
class RuleOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    IN = "in"
```

### RuleAction

```python
class RuleAction(str, Enum):
    APPLY_LABEL = "apply_label"
    SEND_ALERT = "send_alert"
    PAUSE_CAMPAIGN = "pause_campaign"
    ADJUST_BUDGET = "adjust_budget"
    NOTIFY_SLACK = "notify_slack"
    NOTIFY_WHATSAPP = "notify_whatsapp"
```

---

## Supported Condition Fields

### Direct Campaign Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Campaign status |
| `name` | string | Campaign name |
| `daily_budget_cents` | integer | Daily budget in cents |
| `impressions` | integer | Total impressions |
| `clicks` | integer | Total clicks |
| `conversions` | integer | Total conversions |
| `total_spend_cents` | integer | Total spend in cents |
| `revenue_cents` | integer | Total revenue in cents |
| `roas` | float | Return on Ad Spend |
| `ctr` | float | Click-through rate |
| `labels` | list | Applied labels |

### Computed Fields

| Field | Calculation | Description |
|-------|-------------|-------------|
| `spend` | `total_spend_cents / 100` | Spend in dollars |
| `revenue` | `revenue_cents / 100` | Revenue in dollars |
| `cpc` | `spend / clicks` | Cost per click |
| `cpm` | `spend / impressions * 1000` | Cost per mille |
| `cpa` | `spend / conversions` | Cost per acquisition |
| `conversion_rate` | `conversions / clicks * 100` | Conversion rate % |

---

## Actions

### APPLY_LABEL

Apply a label to the campaign.

```python
# Config
{
    "label": "needs_attention"
}

# Result
{
    "action": "apply_label",
    "label": "needs_attention",
    "success": true
}
```

### SEND_ALERT

Send email notification.

```python
# Config
{
    "recipients": ["alerts@company.com"],
    "include_metrics": true
}

# Result
{
    "action": "send_alert",
    "success": true,
    "message": "Alert sent for campaign Summer Sale 2024"
}
```

### PAUSE_CAMPAIGN

Pause the campaign.

```python
# Config
{}  # No config needed

# Result
{
    "action": "pause_campaign",
    "success": true,
    "new_status": "paused"
}
```

### ADJUST_BUDGET

Adjust campaign budget by percentage.

```python
# Config
{
    "adjustment_percent": -20  # Decrease by 20%
}

# Result
{
    "action": "adjust_budget",
    "success": true,
    "old_budget_cents": 50000,
    "new_budget_cents": 40000,
    "adjustment_percent": -20
}
```

### NOTIFY_SLACK

Send Slack notification.

```python
# Config
{
    "webhook_url": "https://hooks.slack.com/...",
    "channel": "#alerts"
}

# Result
{
    "action": "notify_slack",
    "success": true,
    "webhook_called": true
}
```

### NOTIFY_WHATSAPP

Send WhatsApp notification to opted-in contacts.

```python
# Config
{
    "contact_ids": [1, 2, 3],
    "template_name": "rule_alert",
    "message": "Optional custom message"
}

# Result
{
    "action": "notify_whatsapp",
    "success": true,
    "sent_count": 2,
    "failed_count": 1,
    "results": [
        {"contact_id": 1, "status": "sent"},
        {"contact_id": 2, "status": "sent"},
        {"contact_id": 3, "status": "failed", "error": "Not opted in"}
    ]
}
```

---

## Evaluation Flow

```python
async def evaluate_rule(rule: Rule, dry_run: bool = False):
    # 1. Check if rule is active
    if rule.status != RuleStatus.ACTIVE and not dry_run:
        return {"status": "skipped", "reason": "Rule not active"}

    # 2. Check cooldown
    if rule.last_triggered_at:
        cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
        if datetime.now() < cooldown_end:
            return {"status": "skipped", "reason": "In cooldown"}

    # 3. Get applicable campaigns
    campaigns = await get_applicable_campaigns(rule)

    # 4. Evaluate each campaign
    results = []
    matched = []

    for campaign in campaigns:
        evaluation = evaluate_condition(rule, campaign)
        results.append(evaluation)

        if evaluation["matched"]:
            matched.append(campaign)

            if not dry_run:
                action_result = await execute_action(rule, campaign)
                await log_execution(rule, campaign, evaluation, action_result)

    # 5. Update rule metadata
    if matched and not dry_run:
        rule.last_triggered_at = datetime.now()
        rule.trigger_count += 1

    return {
        "status": "completed",
        "campaigns_evaluated": len(campaigns),
        "campaigns_matched": len(matched),
        "dry_run": dry_run,
        "results": results
    }
```

---

## Rule Builder Pattern

```python
# Fluent API for rule creation
rule = (
    RuleBuilder(tenant_id=1)
    .name("Pause Low ROAS Campaigns")
    .description("Auto-pause campaigns with ROAS below 1.0")
    .when(field="roas", operator=RuleOperator.LESS_THAN, value="1.0")
    .then(action=RuleAction.PAUSE_CAMPAIGN)
    .applies_to(platforms=["meta", "google"])
    .cooldown(hours=24)
    .build()
)

# Validation
errors = rule_builder.validate()
if errors:
    raise ValidationError(errors)
```

---

## Database Schema

```sql
-- Rules table
CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',

    -- Condition
    condition_field VARCHAR(100) NOT NULL,
    condition_operator VARCHAR(50) NOT NULL,
    condition_value VARCHAR(255) NOT NULL,
    condition_duration_hours INTEGER NOT NULL DEFAULT 24,

    -- Action
    action_type VARCHAR(50) NOT NULL,
    action_config JSONB NOT NULL DEFAULT '{}',

    -- Scope
    applies_to_campaigns JSONB,
    applies_to_platforms JSONB,

    -- Frequency
    cooldown_hours INTEGER NOT NULL DEFAULT 24,

    -- Tracking
    last_evaluated_at TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER NOT NULL DEFAULT 0,

    -- Soft delete
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rules_tenant_id ON rules(tenant_id);
CREATE INDEX idx_rules_status ON rules(status);

-- Rule executions
CREATE TABLE rule_executions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id INTEGER NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

    executed_at TIMESTAMPTZ NOT NULL,
    triggered BOOLEAN NOT NULL,

    condition_result JSONB,
    action_result JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rule_executions_rule_id ON rule_executions(rule_id);
CREATE INDEX idx_rule_executions_executed_at ON rule_executions(executed_at);
```

---

## Scheduling

Rules are evaluated by a Celery task on a configurable schedule.

```python
# Celery task
@celery_app.task
async def evaluate_all_rules():
    """Evaluate all active rules for all tenants."""
    tenants = await get_active_tenants()

    for tenant in tenants:
        rules = await get_active_rules(tenant.id)

        for rule in rules:
            try:
                result = await engine.evaluate_rule(rule)
                logger.info("rule_evaluated", rule_id=rule.id, result=result)
            except Exception as e:
                logger.error("rule_evaluation_failed", rule_id=rule.id, error=str(e))
```

Default schedule: Every 15 minutes.

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
