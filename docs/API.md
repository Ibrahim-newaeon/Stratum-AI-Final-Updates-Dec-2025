# Stratum AI - API Documentation

## Overview

The Stratum AI API is a RESTful API built with FastAPI. All endpoints are versioned under `/api/v1/` and return JSON responses.

**Base URL:** `http://localhost:8000/api/v1`

---

## Authentication

### JWT Token Flow

All protected endpoints require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### Endpoints

#### Login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=secretpassword
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "tenant_name": "Acme Corp"
}
```

#### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Forgot Password

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Reset Password

```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "newsecurepassword123"
}
```

---

## Standard Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Invalid email format",
  "details": [
    {
      "field": "email",
      "message": "value is not a valid email address"
    }
  ]
}
```

---

## Campaigns API

### List Campaigns

```http
GET /api/v1/campaigns
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `platform` | string | Filter by platform: meta, google, tiktok, snapchat, linkedin |
| `status` | string | Filter by status: active, paused, draft, completed |
| `search` | string | Search by campaign name |
| `sort_by` | string | Sort field: name, spend, roas, created_at |
| `sort_order` | string | Sort order: asc, desc |
| `date_from` | date | Filter by start date (YYYY-MM-DD) |
| `date_to` | date | Filter by end date (YYYY-MM-DD) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Summer Sale 2024",
      "platform": "meta",
      "status": "active",
      "external_id": "23851234567890",
      "daily_budget": 500.00,
      "total_spend": 3250.50,
      "impressions": 125000,
      "clicks": 4500,
      "conversions": 180,
      "revenue": 9800.00,
      "ctr": 3.6,
      "cpc": 0.72,
      "cpm": 26.00,
      "cpa": 18.06,
      "roas": 3.01,
      "start_date": "2024-06-01",
      "end_date": "2024-08-31",
      "labels": ["summer", "sale"],
      "created_at": "2024-05-15T10:30:00Z",
      "updated_at": "2024-12-20T08:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45
  }
}
```

### Get Campaign Details

```http
GET /api/v1/campaigns/{id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Summer Sale 2024",
    "platform": "meta",
    "status": "active",
    "objective": "CONVERSIONS",
    "external_id": "23851234567890",
    "account_id": "act_123456789",
    "daily_budget": 500.00,
    "lifetime_budget": null,
    "total_spend": 3250.50,
    "currency": "USD",
    "impressions": 125000,
    "clicks": 4500,
    "conversions": 180,
    "revenue": 9800.00,
    "ctr": 3.6,
    "cpc": 0.72,
    "cpm": 26.00,
    "cpa": 18.06,
    "roas": 3.01,
    "targeting": {
      "age_min": 25,
      "age_max": 54,
      "genders": ["male", "female"],
      "locations": ["US", "CA", "UK"],
      "interests": ["fashion", "online shopping"]
    },
    "demographics": {
      "age": {
        "18-24": 15,
        "25-34": 35,
        "35-44": 30,
        "45-54": 15,
        "55+": 5
      },
      "gender": {
        "male": 45,
        "female": 55
      }
    },
    "start_date": "2024-06-01",
    "end_date": "2024-08-31",
    "labels": ["summer", "sale"],
    "last_synced_at": "2024-12-20T07:45:00Z",
    "created_at": "2024-05-15T10:30:00Z",
    "updated_at": "2024-12-20T08:00:00Z"
  }
}
```

### Create Campaign

```http
POST /api/v1/campaigns
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Holiday Campaign 2024",
  "platform": "meta",
  "account_id": "act_123456789",
  "objective": "CONVERSIONS",
  "daily_budget": 1000.00,
  "currency": "USD",
  "start_date": "2024-12-01",
  "end_date": "2024-12-31",
  "targeting": {
    "age_min": 18,
    "age_max": 65,
    "locations": ["US"]
  },
  "labels": ["holiday", "q4"]
}
```

### Update Campaign

```http
PUT /api/v1/campaigns/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Holiday Campaign 2024 - Updated",
  "daily_budget": 1500.00,
  "status": "active"
}
```

### Delete Campaign

```http
DELETE /api/v1/campaigns/{id}
Authorization: Bearer <token>
```

### Get Campaign Metrics (Time Series)

```http
GET /api/v1/campaigns/{id}/metrics
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | Start date (YYYY-MM-DD) |
| `date_to` | date | End date (YYYY-MM-DD) |
| `granularity` | string | daily, weekly, monthly |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "date": "2024-12-19",
      "impressions": 5000,
      "clicks": 180,
      "conversions": 7,
      "spend": 125.50,
      "revenue": 385.00,
      "ctr": 3.6,
      "roas": 3.07
    },
    {
      "date": "2024-12-20",
      "impressions": 5200,
      "clicks": 195,
      "conversions": 8,
      "spend": 130.00,
      "revenue": 420.00,
      "ctr": 3.75,
      "roas": 3.23
    }
  ]
}
```

---

## Analytics API

### Get KPIs

```http
GET /api/v1/analytics/kpis
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | Start date |
| `date_to` | date | End date |
| `platform` | string | Filter by platform (optional) |
| `compare_period` | string | previous_period, previous_year |

**Response:**
```json
{
  "success": true,
  "data": {
    "total_spend": 45000.00,
    "total_revenue": 135000.00,
    "total_impressions": 2500000,
    "total_clicks": 85000,
    "total_conversions": 3200,
    "avg_roas": 3.00,
    "avg_ctr": 3.4,
    "avg_cpc": 0.53,
    "avg_cpm": 18.00,
    "avg_cpa": 14.06,
    "comparison": {
      "spend_change": 12.5,
      "revenue_change": 18.3,
      "roas_change": 5.2
    }
  }
}
```

### Get Platform Breakdown

```http
GET /api/v1/analytics/platforms
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "platform": "meta",
      "spend": 20000.00,
      "revenue": 62000.00,
      "roas": 3.10,
      "campaigns": 15,
      "conversions": 1400
    },
    {
      "platform": "google",
      "spend": 15000.00,
      "revenue": 48000.00,
      "roas": 3.20,
      "campaigns": 12,
      "conversions": 1100
    },
    {
      "platform": "tiktok",
      "spend": 10000.00,
      "revenue": 25000.00,
      "roas": 2.50,
      "campaigns": 8,
      "conversions": 700
    }
  ]
}
```

### Export Data

```http
POST /api/v1/analytics/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "format": "csv",
  "type": "campaigns",
  "date_from": "2024-01-01",
  "date_to": "2024-12-31",
  "platforms": ["meta", "google"],
  "columns": ["name", "spend", "revenue", "roas"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "download_url": "/api/v1/analytics/export/download/abc123",
    "expires_at": "2024-12-20T12:00:00Z",
    "file_size": 15420,
    "row_count": 450
  }
}
```

---

## Rules API (Automation)

### List Rules

```http
GET /api/v1/rules
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Pause Low ROAS Campaigns",
      "description": "Automatically pause campaigns with ROAS below 1.5",
      "status": "active",
      "condition": {
        "field": "roas",
        "operator": "less_than",
        "value": "1.5",
        "duration_hours": 48
      },
      "action": {
        "type": "pause_campaign",
        "config": {}
      },
      "applies_to": {
        "campaigns": null,
        "platforms": ["meta", "google"]
      },
      "cooldown_hours": 24,
      "last_evaluated_at": "2024-12-20T07:00:00Z",
      "last_triggered_at": "2024-12-19T14:30:00Z",
      "trigger_count": 5
    }
  ]
}
```

### Create Rule

```http
POST /api/v1/rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Alert High Spend",
  "description": "Send Slack alert when daily spend exceeds $500",
  "condition": {
    "field": "daily_spend",
    "operator": "greater_than",
    "value": "500",
    "duration_hours": 24
  },
  "action": {
    "type": "notify_slack",
    "config": {
      "webhook_url": "https://hooks.slack.com/...",
      "message": "Campaign {{campaign_name}} exceeded daily spend limit"
    }
  },
  "applies_to": {
    "campaigns": null,
    "platforms": null
  },
  "cooldown_hours": 12
}
```

### Rule Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | status equals "paused" |
| `not_equals` | Not equal | platform not_equals "tiktok" |
| `greater_than` | Greater than | roas greater_than 2.0 |
| `less_than` | Less than | ctr less_than 1.0 |
| `gte` | Greater or equal | spend gte 1000 |
| `lte` | Less or equal | cpa lte 50 |
| `contains` | String contains | name contains "Summer" |
| `in` | Value in list | platform in ["meta", "google"] |

### Rule Action Types

| Action | Description | Config Fields |
|--------|-------------|---------------|
| `pause_campaign` | Pause the campaign | - |
| `apply_label` | Add label to campaign | `label` |
| `send_alert` | Send email alert | `recipients` |
| `notify_slack` | Send Slack message | `webhook_url`, `message` |
| `notify_whatsapp` | Send WhatsApp message | `template_name`, `contact_id` |
| `adjust_budget` | Modify budget | `adjustment_type`, `value` |

---

## Predictions API (ML)

### Get ROAS Predictions

```http
GET /api/v1/predictions/roas
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `campaign_id` | int | Specific campaign (optional) |
| `days_ahead` | int | Forecast horizon (default: 7) |

**Response:**
```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "campaign_id": 1,
        "campaign_name": "Summer Sale 2024",
        "platform": "meta",
        "current_roas": 2.85,
        "predicted_roas": 3.12,
        "confidence_lower": 2.95,
        "confidence_upper": 3.29,
        "trend": "improving",
        "recommendation": "Consider increasing budget by 15%"
      }
    ],
    "model_version": "roas_v2.1",
    "generated_at": "2024-12-20T08:00:00Z"
  }
}
```

### Get Budget Recommendations

```http
POST /api/v1/predictions/budget-optimize
Authorization: Bearer <token>
Content-Type: application/json

{
  "total_budget": 50000,
  "optimization_goal": "maximize_roas",
  "constraints": {
    "min_spend_per_platform": 5000,
    "max_spend_per_campaign": 10000
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "campaign_id": 1,
        "campaign_name": "Summer Sale 2024",
        "current_budget": 500,
        "recommended_budget": 750,
        "expected_roas": 3.45,
        "expected_revenue_increase": 2500
      }
    ],
    "total_expected_roas": 3.28,
    "total_expected_revenue": 164000
  }
}
```

---

## Simulator API

### Run What-If Simulation

```http
POST /api/v1/simulate
Authorization: Bearer <token>
Content-Type: application/json

{
  "campaign_id": 1,
  "scenarios": [
    {
      "name": "Increase Budget 20%",
      "budget_change_percent": 20
    },
    {
      "name": "Decrease Budget 20%",
      "budget_change_percent": -20
    }
  ],
  "time_horizon_days": 30
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "baseline": {
      "spend": 15000,
      "revenue": 45000,
      "roas": 3.00,
      "conversions": 600
    },
    "scenarios": [
      {
        "name": "Increase Budget 20%",
        "spend": 18000,
        "revenue": 52200,
        "roas": 2.90,
        "conversions": 696,
        "marginal_roas": 2.40
      },
      {
        "name": "Decrease Budget 20%",
        "spend": 12000,
        "revenue": 38400,
        "roas": 3.20,
        "conversions": 512,
        "marginal_roas": 2.20
      }
    ]
  }
}
```

---

## Conversion API (CAPI)

### Send Conversion Event

```http
POST /api/v1/capi/events
Authorization: Bearer <token>
Content-Type: application/json

{
  "event_name": "Purchase",
  "event_time": "2024-12-20T10:30:00Z",
  "event_source_url": "https://example.com/checkout/success",
  "user_data": {
    "email": "customer@example.com",
    "phone": "+1234567890",
    "client_ip_address": "192.168.1.1",
    "client_user_agent": "Mozilla/5.0...",
    "fbc": "fb.1.1234567890.abcdef",
    "fbp": "_fbp.1.1234567890.123456789"
  },
  "custom_data": {
    "value": 99.99,
    "currency": "USD",
    "content_ids": ["PROD-123"],
    "content_type": "product",
    "num_items": 1
  },
  "platforms": ["meta", "google", "tiktok"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "event_id": "evt_abc123xyz",
    "platforms": {
      "meta": {
        "status": "success",
        "event_id": "fb_evt_123"
      },
      "google": {
        "status": "success",
        "event_id": "ggl_evt_456"
      },
      "tiktok": {
        "status": "success",
        "event_id": "tt_evt_789"
      }
    },
    "data_quality": {
      "score": 85,
      "level": "good",
      "missing_fields": ["external_id"]
    }
  }
}
```

### Get Event Quality Score

```http
GET /api/v1/capi/quality
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_score": 78,
    "level": "good",
    "by_platform": {
      "meta": {
        "score": 82,
        "emq": 7.8
      },
      "google": {
        "score": 75,
        "match_rate": 0.72
      }
    },
    "recommendations": [
      "Add external_id for better cross-device tracking",
      "Include click_id for improved attribution"
    ]
  }
}
```

---

## WhatsApp API

### Send Message

```http
POST /api/v1/whatsapp/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "contact_id": 1,
  "message_type": "template",
  "template_name": "campaign_alert",
  "template_variables": {
    "campaign_name": "Summer Sale 2024",
    "metric": "ROAS",
    "value": "3.5"
  }
}
```

### List Templates

```http
GET /api/v1/whatsapp/templates
Authorization: Bearer <token>
```

### Create Template

```http
POST /api/v1/whatsapp/templates
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "campaign_performance",
  "language": "en",
  "category": "UTILITY",
  "header_type": "TEXT",
  "header_content": "Campaign Update",
  "body_text": "Hi {{1}}, your campaign {{2}} achieved {{3}} ROAS today!",
  "footer_text": "Stratum AI",
  "body_variables": ["customer_name", "campaign_name", "roas_value"]
}
```

### Webhook (Incoming Messages)

```http
POST /api/v1/whatsapp/webhook
X-Hub-Signature-256: sha256=...

{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "1234567890",
                "type": "text",
                "text": {
                  "body": "Hello"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

---

## GDPR Compliance API

### Export User Data

```http
POST /api/v1/gdpr/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 123,
  "format": "json"
}
```

### Anonymize User

```http
POST /api/v1/gdpr/anonymize
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 123,
  "reason": "user_request"
}
```

### Delete User Data

```http
DELETE /api/v1/gdpr/user/{user_id}
Authorization: Bearer <token>
```

---

## Health & Monitoring

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "database": "healthy",
  "redis": "healthy"
}
```

### Readiness Probe

```http
GET /health/ready
```

### Liveness Probe

```http
GET /health/live
```

### Metrics

```http
GET /metrics
```

**Response:**
```json
{
  "app": {
    "name": "StratumAI",
    "version": "1.0.0",
    "environment": "production"
  },
  "system": {
    "cpu_percent": 25.5,
    "memory_mb": 512.3,
    "memory_percent": 12.8,
    "threads": 8,
    "open_files": 45
  },
  "uptime_seconds": 86400
}
```

---

## Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 400 | `validation_error` | Invalid request data |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Resource not found |
| 409 | `conflict` | Resource already exists |
| 422 | `unprocessable_entity` | Semantic error |
| 429 | `rate_limited` | Too many requests |
| 500 | `internal_error` | Server error |

---

## Rate Limiting

Default limits:
- **100 requests/minute** per IP
- **20 request burst** allowed

Headers returned:
```
X-Rate-Limit-Remaining: 95
X-Rate-Limit-Reset: 1703073600
```

---

## Pagination

All list endpoints support pagination:

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `page` | int | 1 | - |
| `page_size` | int | 20 | 100 |

Response includes:
```json
{
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```
