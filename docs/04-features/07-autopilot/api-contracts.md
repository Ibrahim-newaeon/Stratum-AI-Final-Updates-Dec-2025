# Autopilot API Contracts

## Overview

Tenant-scoped API endpoints for autopilot actions, enforcement settings, and audit logging.

**Base URL**: `/api/v1/tenant/{tenant_id}/autopilot`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Autopilot Status

### GET /status

Get current autopilot status and configuration.

#### Response

```json
{
  "success": true,
  "data": {
    "autopilot_level": 1,
    "autopilot_level_name": "Guarded Auto",
    "pending_actions": 3,
    "caps": {
      "daily_max": 1000.00,
      "campaign_max": 5000.00,
      "cpa_ceiling": 50.00,
      "roas_floor": 1.5
    },
    "enabled": true
  }
}
```

---

## Actions

### GET /actions

List autopilot actions.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date` | date | Filter by date |
| `status` | string | Filter: queued, approved, applied, failed, dismissed |
| `platform` | string | Filter by platform |
| `limit` | integer | Max results (default 50) |

#### Response

```json
{
  "success": true,
  "data": {
    "actions": [
      {
        "id": "uuid-...",
        "date": "2024-01-15",
        "action_type": "budget_increase",
        "entity_type": "campaign",
        "entity_id": "123456789",
        "entity_name": "Summer Sale 2024",
        "platform": "meta",
        "action_json": {
          "type": "budget_increase",
          "new_budget": 600.00,
          "change_percent": 20
        },
        "before_value": { "daily_budget": 500.00 },
        "after_value": null,
        "status": "queued",
        "created_at": "2024-01-15T10:00:00Z",
        "approved_at": null,
        "applied_at": null,
        "error": null
      }
    ],
    "count": 1,
    "filters": {
      "date": null,
      "status": "queued",
      "platform": null
    }
  }
}
```

### GET /actions/summary

Get summary of actions over past N days.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | Lookback days (default 7, max 30) |

#### Response

```json
{
  "success": true,
  "data": {
    "total": 45,
    "by_status": {
      "applied": 38,
      "dismissed": 4,
      "failed": 3,
      "queued": 0
    },
    "by_type": {
      "budget_increase": 25,
      "budget_decrease": 12,
      "pause_campaign": 5,
      "enable_campaign": 3
    },
    "pending_approval": 0
  }
}
```

### POST /actions

Queue a new action.

#### Request

```json
{
  "action_type": "budget_increase",
  "entity_type": "campaign",
  "entity_id": "123456789",
  "entity_name": "Summer Sale 2024",
  "platform": "meta",
  "action_json": {
    "type": "budget_increase",
    "new_budget": 600.00,
    "change_percent": 20
  },
  "before_value": { "daily_budget": 500.00 }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "action": {
      "id": "uuid-...",
      "status": "queued",
      "...": "..."
    },
    "auto_approved": false,
    "requires_approval": true,
    "reason": "Autopilot level 2 requires manual approval"
  }
}
```

### GET /actions/{action_id}

Get action details.

#### Response

```json
{
  "success": true,
  "data": {
    "action": {
      "id": "uuid-...",
      "date": "2024-01-15",
      "action_type": "budget_increase",
      "entity_type": "campaign",
      "entity_id": "123456789",
      "entity_name": "Summer Sale 2024",
      "platform": "meta",
      "action_json": { "...": "..." },
      "before_value": { "daily_budget": 500.00 },
      "after_value": { "daily_budget": 600.00 },
      "status": "applied",
      "created_at": "2024-01-15T10:00:00Z",
      "approved_at": "2024-01-15T10:30:00Z",
      "applied_at": "2024-01-15T10:31:00Z",
      "error": null
    }
  }
}
```

### POST /actions/{action_id}/approve

Approve a queued action.

#### Response

```json
{
  "success": true,
  "data": {
    "action": { "...": "..." },
    "message": "Action approved for execution"
  }
}
```

### POST /actions/approve-all

Approve multiple actions at once.

#### Request

```json
{
  "action_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "approved_count": 3,
    "message": "Approved 3 actions for execution"
  }
}
```

### POST /actions/{action_id}/dismiss

Dismiss a queued action.

#### Response

```json
{
  "success": true,
  "data": {
    "action": { "...": "..." },
    "message": "Action dismissed"
  }
}
```

### POST /actions/dry-run

Test an action without executing (dry-run mode).

#### Request

```json
{
  "action_type": "budget_increase",
  "entity_type": "campaign",
  "entity_id": "123456789",
  "entity_name": "Summer Sale 2024",
  "platform": "meta",
  "action_json": {
    "type": "budget_increase",
    "new_budget": 750.00,
    "change_percent": 50
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "would_execute": false,
    "decision_type": "hold",
    "signal_health_score": 62.5,
    "signal_health_status": "degraded",
    "gate_passed": false,
    "gate_reasons": [
      "EMQ score 62.5% is below healthy threshold (70%)",
      "Autopilot check: Budget change 50% exceeds cap of 30%"
    ],
    "healthy_threshold": 70.0,
    "degraded_threshold": 40.0,
    "action_preview": {
      "action_type": "budget_increase",
      "entity_type": "campaign",
      "entity_id": "123456789",
      "entity_name": "Summer Sale 2024",
      "platform": "meta",
      "details": { "...": "..." }
    },
    "warnings": [
      "Consider improving data quality before executing"
    ],
    "audit_log_id": "uuid-...",
    "message": "Dry-run simulation completed. No changes were made."
  }
}
```

---

## Enforcement

**Base URL**: `/api/v1/tenant/{tenant_id}/autopilot/enforcement`

### GET /settings

Get enforcement settings.

#### Response

```json
{
  "success": true,
  "data": {
    "settings": {
      "enforcement_enabled": true,
      "default_mode": "advisory",
      "max_daily_budget": null,
      "max_campaign_budget": 5000.00,
      "budget_increase_limit_pct": 30.0,
      "min_roas_threshold": 1.0,
      "roas_lookback_days": 7,
      "max_budget_changes_per_day": 5,
      "min_hours_between_changes": 4,
      "rules": [
        {
          "rule_id": "high_cpa_block",
          "rule_type": "budget_exceeded",
          "threshold_value": 75.0,
          "enforcement_mode": "soft_block",
          "enabled": true,
          "description": "Block when CPA exceeds $75"
        }
      ]
    },
    "modes": {
      "advisory": "Warn only, no blocking",
      "soft_block": "Warn + require confirmation to proceed",
      "hard_block": "Prevent action via API, log override attempts"
    }
  }
}
```

### PUT /settings

Update enforcement settings.

#### Request

```json
{
  "enforcement_enabled": true,
  "default_mode": "soft_block",
  "max_daily_budget": 2000.00,
  "max_campaign_budget": 5000.00,
  "budget_increase_limit_pct": 25.0,
  "min_roas_threshold": 1.5,
  "roas_lookback_days": 14
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Settings updated successfully",
    "settings": { "...": "..." }
  }
}
```

### POST /check

Check if a proposed action is allowed.

#### Request

```json
{
  "action_type": "budget_increase",
  "entity_type": "campaign",
  "entity_id": "123456789",
  "proposed_value": { "daily_budget": 750.00 },
  "current_value": { "daily_budget": 500.00 },
  "metrics": { "roas": 1.8, "cpa": 35.00 }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "allowed": false,
    "mode": "soft_block",
    "violations": [
      {
        "type": "budget_increase_limit",
        "threshold": 30.0,
        "actual": 50.0,
        "message": "Budget increase 50% exceeds limit of 30%"
      }
    ],
    "warnings": [
      "Budget increase exceeds threshold. Confirmation required to proceed."
    ],
    "requires_confirmation": true,
    "confirmation_token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

### POST /confirm

Confirm a soft-blocked action.

#### Request

```json
{
  "confirmation_token": "eyJhbGciOiJIUzI1NiIs...",
  "override_reason": "Q4 executive approval for aggressive scaling"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Action confirmed - you may now proceed",
    "override_logged": true
  }
}
```

### POST /kill-switch

Toggle enforcement kill switch.

#### Request

```json
{
  "enabled": false,
  "reason": "Platform API maintenance window"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Enforcement disabled for tenant",
    "enforcement_enabled": false,
    "changed_by_user_id": 123
  }
}
```

### GET /audit-log

Get intervention audit log.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | Lookback days (default 30, max 90) |
| `limit` | integer | Max results (default 100, max 500) |

#### Response

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "uuid-...",
        "timestamp": "2024-01-15T14:30:00Z",
        "action_type": "budget_increase",
        "entity_type": "campaign",
        "entity_id": "123456789",
        "violation_type": "budget_exceeded",
        "intervention_action": "blocked",
        "enforcement_mode": "hard_block",
        "details": {
          "proposed_budget": 6000.00,
          "max_budget": 5000.00
        },
        "user_id": null,
        "override_reason": null
      }
    ],
    "count": 25,
    "filters": {
      "days": 30,
      "limit": 100
    }
  }
}
```

### POST /rules

Add a custom enforcement rule.

#### Request

```json
{
  "rule_id": "high_cpa_alert",
  "rule_type": "budget_exceeded",
  "threshold_value": 75.0,
  "enforcement_mode": "soft_block",
  "enabled": true,
  "description": "Block actions when CPA exceeds $75"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Rule 'high_cpa_alert' added successfully",
    "rule": {
      "rule_id": "high_cpa_alert",
      "rule_type": "budget_exceeded",
      "threshold_value": 75.0,
      "enforcement_mode": "soft_block",
      "enabled": true,
      "description": "Block actions when CPA exceeds $75"
    }
  }
}
```

### DELETE /rules/{rule_id}

Delete a custom rule.

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Rule 'high_cpa_alert' deleted successfully"
  }
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "ACTION_NOT_FOUND",
    "message": "Action not found or already processed",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `ACTION_NOT_FOUND` | 404 | Action not found |
| `INVALID_ACTION_ID` | 400 | Invalid UUID format |
| `INVALID_STATUS_TRANSITION` | 400 | Invalid action state |
| `ENFORCEMENT_BLOCKED` | 403 | Hard-blocked by enforcement |
| `CONFIRMATION_REQUIRED` | 403 | Soft-block requires confirmation |
| `INVALID_CONFIRMATION_TOKEN` | 400 | Token invalid or expired |
| `KILL_SWITCH_DISABLED` | 403 | Enforcement disabled |
| `FEATURE_NOT_ENABLED` | 403 | Feature flag disabled |
| `RULE_NOT_FOUND` | 404 | Custom rule not found |
| `RULE_ALREADY_EXISTS` | 409 | Rule ID already exists |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 60/min |
| POST/PUT endpoints | 30/min |
| Dry-run endpoint | 20/min |
| Kill-switch endpoint | 5/min |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
