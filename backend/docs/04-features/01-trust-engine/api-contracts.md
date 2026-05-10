# Trust Engine API Contracts

## Overview

API endpoints for the Trust Engine feature, including signal health monitoring, attribution variance tracking, and trust gate audit logs.

**Base URL**: `/api/v1/tenant/{tenant_id}`

---

## Authentication

All endpoints require:
- Bearer token authentication
- Tenant context matching (user must have access to `tenant_id`)
- Feature flag enabled for the specific endpoint

---

## Endpoints

### GET /signal-health

Get current signal health status and metrics.

#### Request

```http
GET /api/v1/tenant/123/signal-health?date=2024-01-15
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | date | No | Target date (defaults to today) |

#### Response

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "automation_blocked": false,
    "overall_score": 78.5,
    "cards": [
      {
        "label": "Overall Signal Health",
        "value": "78.5",
        "unit": "%",
        "trend": "up",
        "trend_value": "+2.3"
      },
      {
        "label": "EMQ Score",
        "value": "82.0",
        "unit": "%",
        "status": "healthy"
      },
      {
        "label": "Data Freshness",
        "value": "95.0",
        "unit": "%",
        "status": "healthy"
      },
      {
        "label": "Attribution Variance",
        "value": "12.3",
        "unit": "%",
        "status": "warning"
      }
    ],
    "platform_rows": [
      {
        "platform": "meta",
        "status": "healthy",
        "emq_score": 8.5,
        "event_loss_pct": 3.2,
        "freshness_minutes": 15,
        "last_sync": "2024-01-15T14:30:00Z"
      },
      {
        "platform": "google",
        "status": "healthy",
        "emq_score": 7.8,
        "event_loss_pct": 5.1,
        "freshness_minutes": 22,
        "last_sync": "2024-01-15T14:28:00Z"
      }
    ],
    "banners": [
      {
        "type": "warning",
        "message": "Attribution variance elevated (12.3%). Review platform vs GA4 settings.",
        "action_url": "/settings/attribution",
        "dismissible": true
      }
    ],
    "components": {
      "emq": 82.0,
      "freshness": 95.0,
      "variance": 65.0,
      "anomaly": 88.0,
      "cdp": 76.5
    },
    "issues": [
      "Attribution variance above warning threshold (10%)"
    ]
  }
}
```

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 403 | Feature not enabled or access denied |
| 404 | Tenant not found |

---

### GET /signal-health/history

Get historical signal health data for trend analysis.

#### Request

```http
GET /api/v1/tenant/123/signal-health/history?days=14&platform=meta
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | No | Number of days (1-30, default: 7) |
| `platform` | string | No | Filter by platform |

#### Response

```json
{
  "success": true,
  "data": {
    "days": 14,
    "platform": null,
    "start_date": "2024-01-01",
    "end_date": "2024-01-15",
    "history": [
      {
        "date": "2024-01-15",
        "overall_score": 78.5,
        "status": "healthy",
        "emq_score_avg": 82.0,
        "event_loss_pct_avg": 4.1,
        "freshness_minutes_avg": 18,
        "api_error_rate_avg": 0.002,
        "platforms_ok": 3,
        "platforms_risk": 1,
        "platforms_degraded": 0,
        "platforms_critical": 0,
        "automation_blocked": false
      },
      {
        "date": "2024-01-14",
        "overall_score": 76.2,
        "status": "healthy",
        "emq_score_avg": 80.5,
        "event_loss_pct_avg": 5.2,
        "freshness_minutes_avg": 21,
        "api_error_rate_avg": 0.003,
        "platforms_ok": 3,
        "platforms_risk": 1,
        "platforms_degraded": 0,
        "platforms_critical": 0,
        "automation_blocked": false
      }
    ],
    "total_records": 14
  }
}
```

---

### GET /attribution-variance

Get attribution variance between platform and GA4.

#### Request

```http
GET /api/v1/tenant/123/attribution-variance?date=2024-01-15
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | date | No | Target date (defaults to today) |

#### Response

```json
{
  "success": true,
  "data": {
    "status": "minor",
    "overall_revenue_variance_pct": 8.5,
    "cards": [
      {
        "label": "Revenue Variance",
        "value": "8.5",
        "unit": "%",
        "status": "warning"
      },
      {
        "label": "Platform Revenue",
        "value": "125,430",
        "unit": "$",
        "source": "meta + google"
      },
      {
        "label": "GA4 Revenue",
        "value": "114,856",
        "unit": "$",
        "source": "ga4"
      }
    ],
    "platform_rows": [
      {
        "platform": "meta",
        "platform_revenue": 85000.00,
        "ga4_revenue": 78500.00,
        "variance_pct": 7.6,
        "variance_abs": 6500.00,
        "status": "minor"
      },
      {
        "platform": "google",
        "platform_revenue": 40430.00,
        "ga4_revenue": 36356.00,
        "variance_pct": 10.1,
        "variance_abs": 4074.00,
        "status": "moderate"
      }
    ],
    "banners": [
      {
        "type": "info",
        "message": "Google Ads variance elevated. Check conversion window settings.",
        "action_url": "/settings/google/conversions"
      }
    ]
  }
}
```

#### Variance Status Levels

| Status | Variance % | Description |
|--------|------------|-------------|
| `healthy` | < 5% | Normal variance |
| `minor` | 5-10% | Slight discrepancy |
| `moderate` | 10-15% | Review recommended |
| `high` | > 15% | Investigation required |

---

### GET /trust-status

Get combined trust status including signal health and attribution variance.

#### Request

```http
GET /api/v1/tenant/123/trust-status?date=2024-01-15
Authorization: Bearer <token>
```

#### Response

```json
{
  "success": true,
  "data": {
    "date": "2024-01-15",
    "overall_status": "ok",
    "automation_allowed": true,
    "signal_health": {
      "status": "healthy",
      "overall_score": 78.5,
      "automation_blocked": false
    },
    "attribution_variance": {
      "status": "minor",
      "overall_revenue_variance_pct": 8.5
    },
    "banners": [
      {
        "type": "info",
        "source": "attribution",
        "message": "Attribution variance at 8.5%. Monitor for changes."
      }
    ],
    "autopilot_mode": "normal",
    "allowed_actions": [
      "update_budget",
      "update_bid",
      "update_status",
      "update_targeting",
      "pause_underperforming",
      "reduce_budget",
      "pause_all",
      "emergency_stop"
    ],
    "restricted_actions": [
      "increase_budget",
      "launch_new_campaigns",
      "expand_targeting",
      "increase_bid"
    ]
  }
}
```

---

### GET /trust-gate/audit-logs

Get trust gate decision audit logs.

#### Request

```http
GET /api/v1/tenant/123/trust-gate/audit-logs?days=7&decision_type=hold&limit=20
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | No | Date range (1-30, default: 7) |
| `decision_type` | string | No | Filter: `execute`, `hold`, `block` |
| `entity_type` | string | No | Filter: `campaign`, `adset`, `creative` |
| `limit` | integer | No | Page size (1-200, default: 50) |
| `offset` | integer | No | Pagination offset (default: 0) |

#### Response

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "7f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
        "created_at": "2024-01-15T14:32:18Z",
        "decision_type": "hold",
        "action_type": "increase_budget",
        "entity_type": "campaign",
        "entity_id": "12345678",
        "entity_name": "Summer Sale Campaign",
        "platform": "meta",
        "signal_health_score": 72.4,
        "signal_health_status": "healthy",
        "gate_passed": false,
        "gate_reason": {
          "threshold_required": 80.0,
          "score_actual": 72.4,
          "reason": "Signal health below high-risk threshold"
        },
        "is_dry_run": false,
        "healthy_threshold": 70.0,
        "degraded_threshold": 40.0,
        "triggered_by_system": true
      }
    ],
    "pagination": {
      "total": 156,
      "limit": 20,
      "offset": 0,
      "has_more": true
    },
    "summary": {
      "total_decisions": 20,
      "executed": 12,
      "held": 6,
      "blocked": 2,
      "pass_rate": 60.0
    },
    "date_range": {
      "start": "2024-01-08T00:00:00Z",
      "end": "2024-01-15T23:59:59Z"
    }
  }
}
```

---

### GET /trust-gate/audit-logs/{log_id}

Get detailed information about a specific trust gate decision.

#### Request

```http
GET /api/v1/tenant/123/trust-gate/audit-logs/7f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c
Authorization: Bearer <token>
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "7f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "created_at": "2024-01-15T14:32:18Z",
    "decision_type": "hold",
    "action_type": "increase_budget",
    "entity_type": "campaign",
    "entity_id": "12345678",
    "entity_name": "Summer Sale Campaign",
    "platform": "meta",
    "signal_health_score": 72.4,
    "signal_health_status": "healthy",
    "gate_passed": false,
    "gate_reason": {
      "threshold_required": 80.0,
      "score_actual": 72.4,
      "reason": "Signal health 72.4 below threshold 80.0 for increase_budget",
      "allowed_actions": ["reduce_budget", "pause_underperforming"],
      "restricted_actions": ["increase_budget", "expand_targeting"],
      "recommendations": [
        "Review signal health issues before proceeding",
        "Consider conservative actions only",
        "Investigate attribution discrepancies"
      ]
    },
    "healthy_threshold": 70.0,
    "degraded_threshold": 40.0,
    "is_dry_run": false,
    "action_payload": {
      "entity_type": "campaign",
      "entity_id": "12345678",
      "action_type": "increase_budget",
      "parameters": {
        "daily_budget": 150.00,
        "previous_budget": 120.00,
        "change_percent": 25.0
      }
    },
    "action_result": null,
    "triggered_by_system": true,
    "triggered_by_user_id": null
  }
}
```

---

## Schemas

### SignalHealthResponse

```typescript
interface SignalHealthResponse {
  status: 'ok' | 'risk' | 'degraded' | 'critical';
  automation_blocked: boolean;
  overall_score: number;
  cards: MetricCard[];
  platform_rows: PlatformHealth[];
  banners: Banner[];
  components: {
    emq: number;
    freshness: number;
    variance: number;
    anomaly: number;
    cdp?: number;
  };
  issues: string[];
}

interface MetricCard {
  label: string;
  value: string;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  trend_value?: string;
  status?: 'healthy' | 'warning' | 'critical';
}

interface PlatformHealth {
  platform: 'meta' | 'google' | 'tiktok' | 'snapchat';
  status: 'ok' | 'risk' | 'degraded' | 'critical';
  emq_score: number;
  event_loss_pct: number;
  freshness_minutes: number;
  last_sync: string;
}

interface Banner {
  type: 'info' | 'warning' | 'error' | 'success';
  message: string;
  action_url?: string;
  dismissible?: boolean;
}
```

### TrustGateResult

```typescript
interface TrustGateResult {
  decision: 'pass' | 'hold' | 'block';
  signalHealth: {
    score: number;
    status: 'healthy' | 'degraded' | 'critical';
    components: {
      emq: number;
      freshness: number;
      variance: number;
      anomaly: number;
      cdp?: number;
    };
    issues: string[];
    hasCdpData: boolean;
  };
  action: {
    type: string;
    entity: string;
    platform: string;
  };
  reason: string;
  allowedActions: string[];
  restrictedActions: string[];
  recommendations: string[];
  evaluatedAt: string;
}
```

### AuditLogEntry

```typescript
interface AuditLogEntry {
  id: string;
  created_at: string;
  decision_type: 'execute' | 'hold' | 'block';
  action_type: string;
  entity_type: 'campaign' | 'adset' | 'ad' | 'creative';
  entity_id: string;
  entity_name: string;
  platform: string;
  signal_health_score: number;
  signal_health_status: string;
  gate_passed: boolean;
  gate_reason: {
    threshold_required: number;
    score_actual: number;
    reason: string;
    recommendations?: string[];
  };
  is_dry_run: boolean;
  healthy_threshold: number;
  degraded_threshold: number;
  triggered_by_system: boolean;
  triggered_by_user_id?: number;
  action_payload?: object;
  action_result?: object;
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "success": false,
  "error": {
    "code": "FEATURE_NOT_ENABLED",
    "message": "Signal health feature is not enabled for this tenant",
    "details": {
      "feature": "signal_health",
      "tenant_id": 123
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `FEATURE_NOT_ENABLED` | 403 | Required feature flag not enabled |
| `ACCESS_DENIED` | 403 | User doesn't have access to tenant |
| `TENANT_NOT_FOUND` | 404 | Tenant ID not found |
| `INVALID_DATE_RANGE` | 400 | Invalid date or days parameter |
| `AUDIT_LOG_NOT_FOUND` | 404 | Audit log entry not found |

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| GET /signal-health | 60/minute |
| GET /signal-health/history | 30/minute |
| GET /attribution-variance | 60/minute |
| GET /trust-status | 60/minute |
| GET /trust-gate/audit-logs | 30/minute |

---

## Webhooks

### Signal Health Status Change

When signal health status changes, a webhook is sent:

```json
{
  "event": "signal_health.status_changed",
  "timestamp": "2024-01-15T14:32:18Z",
  "data": {
    "tenant_id": 123,
    "previous_status": "healthy",
    "new_status": "degraded",
    "overall_score": 65.2,
    "automation_blocked": false,
    "issues": [
      "EMQ score below target: 62.0 (target: 70+)",
      "Data freshness degraded (26.0h old)"
    ]
  }
}
```

### Trust Gate Decision

For each trust gate decision:

```json
{
  "event": "trust_gate.decision",
  "timestamp": "2024-01-15T14:32:18Z",
  "data": {
    "tenant_id": 123,
    "decision": "hold",
    "action_type": "increase_budget",
    "entity_type": "campaign",
    "entity_id": "12345678",
    "signal_health_score": 72.4,
    "threshold_required": 80.0
  }
}
```
