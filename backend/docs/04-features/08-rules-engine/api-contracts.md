# Rules Engine API Contracts

## Overview

Tenant-scoped API endpoints for automation rules management.

**Base URL**: `/api/v1/tenant/{tenant_id}/rules`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Rules

### GET /rules

List automation rules.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default 1) |
| `page_size` | integer | Items per page (default 20, max 100) |
| `status` | string | Filter by status: draft, active, paused |

#### Response

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "tenant_id": 1,
        "name": "Pause Low ROAS Campaigns",
        "description": "Auto-pause campaigns with ROAS below 1.0",
        "status": "active",
        "condition_field": "roas",
        "condition_operator": "lt",
        "condition_value": "1.0",
        "condition_duration_hours": 24,
        "action_type": "pause_campaign",
        "action_config": {},
        "applies_to_campaigns": null,
        "applies_to_platforms": ["meta", "google"],
        "cooldown_hours": 24,
        "last_evaluated_at": "2024-01-15T14:30:00Z",
        "last_triggered_at": "2024-01-15T14:30:00Z",
        "trigger_count": 12,
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-15T14:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

### POST /rules

Create a new rule.

#### Request

```json
{
  "name": "Pause Low ROAS Campaigns",
  "description": "Auto-pause campaigns with ROAS below 1.0 for 24 hours",
  "condition_field": "roas",
  "condition_operator": "lt",
  "condition_value": "1.0",
  "condition_duration_hours": 24,
  "action_type": "pause_campaign",
  "action_config": {},
  "applies_to_platforms": ["meta", "google"],
  "cooldown_hours": 24
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "tenant_id": 1,
    "name": "Pause Low ROAS Campaigns",
    "status": "draft",
    "...": "..."
  },
  "message": "Rule created successfully"
}
```

### GET /rules/{rule_id}

Get rule details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "tenant_id": 1,
    "name": "Pause Low ROAS Campaigns",
    "description": "Auto-pause campaigns with ROAS below 1.0",
    "status": "active",
    "condition_field": "roas",
    "condition_operator": "lt",
    "condition_value": "1.0",
    "condition_duration_hours": 24,
    "action_type": "pause_campaign",
    "action_config": {},
    "applies_to_campaigns": null,
    "applies_to_platforms": ["meta", "google"],
    "cooldown_hours": 24,
    "last_evaluated_at": "2024-01-15T14:30:00Z",
    "last_triggered_at": "2024-01-15T14:30:00Z",
    "trigger_count": 12,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
}
```

### PATCH /rules/{rule_id}

Update a rule.

#### Request

```json
{
  "name": "Pause Very Low ROAS Campaigns",
  "condition_value": "0.5",
  "cooldown_hours": 48
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Pause Very Low ROAS Campaigns",
    "condition_value": "0.5",
    "cooldown_hours": 48,
    "...": "..."
  },
  "message": "Rule updated successfully"
}
```

### DELETE /rules/{rule_id}

Soft delete a rule.

#### Response

```
HTTP 204 No Content
```

---

## Rule Actions

### POST /rules/{rule_id}/activate

Activate a rule.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "active",
    "...": "..."
  },
  "message": "Rule activated"
}
```

### POST /rules/{rule_id}/pause

Pause a rule.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "paused",
    "...": "..."
  },
  "message": "Rule paused"
}
```

### POST /rules/{rule_id}/test

Test a rule without executing actions (dry-run).

#### Response

```json
{
  "success": true,
  "data": {
    "status": "completed",
    "campaigns_evaluated": 15,
    "campaigns_matched": 3,
    "dry_run": true,
    "results": [
      {
        "campaign_id": 101,
        "campaign_name": "Summer Sale 2024",
        "matched": true,
        "condition": {
          "field": "roas",
          "operator": "lt",
          "expected": 1.0,
          "actual": 0.72
        }
      },
      {
        "campaign_id": 102,
        "campaign_name": "Q1 Promo",
        "matched": true,
        "condition": {
          "field": "roas",
          "operator": "lt",
          "expected": 1.0,
          "actual": 0.45
        }
      },
      {
        "campaign_id": 103,
        "campaign_name": "Winter Campaign",
        "matched": false,
        "condition": {
          "field": "roas",
          "operator": "lt",
          "expected": 1.0,
          "actual": 2.3
        }
      }
    ]
  },
  "message": "Rule test completed"
}
```

---

## Rule Executions

### GET /rules/{rule_id}/executions

Get execution history for a rule.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max results (default 50, max 200) |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "tenant_id": 1,
      "rule_id": 1,
      "campaign_id": 101,
      "executed_at": "2024-01-15T14:30:00Z",
      "triggered": true,
      "condition_result": {
        "field": "roas",
        "operator": "lt",
        "expected": 1.0,
        "actual": 0.72,
        "matched": true
      },
      "action_result": {
        "action": "pause_campaign",
        "success": true,
        "new_status": "paused"
      }
    },
    {
      "id": 2,
      "tenant_id": 1,
      "rule_id": 1,
      "campaign_id": 102,
      "executed_at": "2024-01-15T14:30:00Z",
      "triggered": true,
      "condition_result": {
        "field": "roas",
        "operator": "lt",
        "expected": 1.0,
        "actual": 0.45,
        "matched": true
      },
      "action_result": {
        "action": "pause_campaign",
        "success": true,
        "new_status": "paused"
      }
    }
  ]
}
```

---

## Schemas

### RuleCreate

```typescript
interface RuleCreate {
  name: string                       // Rule name (required)
  description?: string               // Optional description
  condition_field: string            // Field to evaluate
  condition_operator: string         // Comparison operator
  condition_value: string            // Value to compare against
  condition_duration_hours?: number  // Duration condition must be true (default 24)
  action_type: string                // Action to execute
  action_config?: object             // Action configuration
  applies_to_campaigns?: number[]    // Specific campaign IDs
  applies_to_platforms?: string[]    // Specific platforms
  cooldown_hours?: number            // Hours between triggers (default 24)
}
```

### RuleUpdate

```typescript
interface RuleUpdate {
  name?: string
  description?: string
  condition_field?: string
  condition_operator?: string
  condition_value?: string
  condition_duration_hours?: number
  action_type?: string
  action_config?: object
  applies_to_campaigns?: number[]
  applies_to_platforms?: string[]
  cooldown_hours?: number
}
```

### ActionConfig by Type

#### apply_label

```typescript
{
  "label": "needs_attention"
}
```

#### send_alert

```typescript
{
  "recipients": ["alerts@company.com"],
  "include_metrics": true
}
```

#### adjust_budget

```typescript
{
  "adjustment_percent": 20  // Positive = increase, negative = decrease
}
```

#### notify_slack

```typescript
{
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#alerts"  // Optional
}
```

#### notify_whatsapp

```typescript
{
  "contact_ids": [1, 2, 3],
  "template_name": "rule_alert",
  "message": "Optional custom message"  // For text messages in conversation window
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "RULE_NOT_FOUND",
    "message": "Rule not found",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RULE_NOT_FOUND` | 404 | Rule not found |
| `INVALID_CONDITION` | 400 | Invalid condition field or operator |
| `INVALID_ACTION` | 400 | Invalid action type |
| `RULE_ALREADY_ACTIVE` | 400 | Rule is already active |
| `RULE_ALREADY_PAUSED` | 400 | Rule is already paused |
| `MISSING_ACTION_CONFIG` | 400 | Required action config missing |
| `INVALID_WEBHOOK_URL` | 400 | Invalid Slack webhook URL |
| `NO_CAMPAIGNS_FOUND` | 404 | No campaigns match rule scope |

---

## Condition Operators

| Operator | Value | Description |
|----------|-------|-------------|
| Equals | `eq` | Field equals value |
| Not Equals | `ne` | Field does not equal value |
| Greater Than | `gt` | Field is greater than value |
| Less Than | `lt` | Field is less than value |
| Greater Than or Equal | `gte` | Field is >= value |
| Less Than or Equal | `lte` | Field is <= value |
| Contains | `contains` | Field contains value (string) |
| In | `in` | Field is in list of values |

---

## Action Types

| Type | Description | Config Required |
|------|-------------|-----------------|
| `apply_label` | Apply label to campaign | `label` |
| `send_alert` | Send email notification | `recipients` |
| `pause_campaign` | Pause the campaign | None |
| `adjust_budget` | Adjust budget by percentage | `adjustment_percent` |
| `notify_slack` | Send Slack notification | `webhook_url` |
| `notify_whatsapp` | Send WhatsApp message | `contact_ids` |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 60/min |
| POST/PATCH endpoints | 30/min |
| Test endpoint | 10/min |
| DELETE endpoint | 10/min |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
