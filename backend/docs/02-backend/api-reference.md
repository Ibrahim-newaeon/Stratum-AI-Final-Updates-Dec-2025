# API Reference

Complete reference for Stratum AI REST API endpoints.

**Base URL:** `/api/v1`

---

## Authentication

### Login

```http
POST /api/v1/auth/login
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "tenant_id": 1
  }
}
```

### Register

```http
POST /api/v1/auth/register
```

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Doe"
}
```

### Refresh Token

```http
POST /api/v1/auth/refresh
```

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

### Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

### Current User

```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

---

## MFA (Two-Factor Authentication)

### Enable MFA

```http
POST /api/v1/mfa/enable
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "otpauth://totp/Stratum:user@example.com?secret=...",
  "backup_codes": ["abc123", "def456", ...]
}
```

### Verify MFA

```http
POST /api/v1/mfa/verify
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "code": "123456"
}
```

### Disable MFA

```http
POST /api/v1/mfa/disable
Authorization: Bearer {access_token}
```

---

## Users

### List Users

```http
GET /api/v1/users
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| page | int | Page number (default: 1) |
| limit | int | Items per page (default: 20) |
| role | string | Filter by role |
| is_active | bool | Filter by active status |

### Get User

```http
GET /api/v1/users/{user_id}
Authorization: Bearer {access_token}
```

### Create User

```http
POST /api/v1/users
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "analyst",
  "password": "TempPass123!"
}
```

### Update User

```http
PATCH /api/v1/users/{user_id}
Authorization: Bearer {access_token}
```

### Delete User

```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer {access_token}
```

---

## Tenants

### List Tenants (Superadmin)

```http
GET /api/v1/tenants
Authorization: Bearer {access_token}
```

### Get Tenant

```http
GET /api/v1/tenants/{tenant_id}
Authorization: Bearer {access_token}
```

### Create Tenant (Superadmin)

```http
POST /api/v1/tenants
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "plan": "professional",
  "max_users": 10,
  "max_campaigns": 100
}
```

### Update Tenant

```http
PATCH /api/v1/tenants/{tenant_id}
Authorization: Bearer {access_token}
```

---

## Campaigns

### List Campaigns

```http
GET /api/v1/campaigns
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| platform | string | Filter by platform (meta, google, tiktok, snapchat) |
| status | string | Filter by status (active, paused, draft) |
| start_date | date | Filter by start date |
| end_date | date | Filter by end date |
| page | int | Page number |
| limit | int | Items per page |

### Get Campaign

```http
GET /api/v1/campaigns/{campaign_id}
Authorization: Bearer {access_token}
```

### Create Campaign

```http
POST /api/v1/campaigns
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "platform": "meta",
  "name": "Summer Sale 2024",
  "objective": "CONVERSIONS",
  "daily_budget_cents": 5000,
  "targeting": {
    "age_min": 25,
    "age_max": 45,
    "genders": ["male", "female"],
    "locations": ["US", "CA"]
  }
}
```

### Update Campaign

```http
PATCH /api/v1/campaigns/{campaign_id}
Authorization: Bearer {access_token}
```

### Campaign Metrics

```http
GET /api/v1/campaigns/{campaign_id}/metrics
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | date | Start of date range |
| end_date | date | End of date range |
| granularity | string | day, week, month |

---

## Analytics

### Dashboard Summary

```http
GET /api/v1/analytics/dashboard
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_spend": 150000,
  "total_revenue": 450000,
  "roas": 3.0,
  "impressions": 5000000,
  "clicks": 75000,
  "conversions": 2500,
  "ctr": 1.5,
  "cpc": 200,
  "platforms": {
    "meta": { "spend": 80000, "revenue": 250000 },
    "google": { "spend": 50000, "revenue": 150000 },
    "tiktok": { "spend": 20000, "revenue": 50000 }
  }
}
```

### Performance Trends

```http
GET /api/v1/analytics/trends
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| metric | string | spend, revenue, roas, ctr, conversions |
| start_date | date | Start date |
| end_date | date | End date |
| granularity | string | day, week, month |

### Platform Comparison

```http
GET /api/v1/analytics/platforms
Authorization: Bearer {access_token}
```

---

## CDP (Customer Data Platform)

### Health Check

```http
GET /api/v1/cdp/health
Authorization: Bearer {access_token}
```

### Statistics

```http
GET /api/v1/cdp/profiles/statistics
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_profiles": 150000,
  "identified_profiles": 45000,
  "anonymous_profiles": 105000,
  "lifecycle_distribution": {
    "anonymous": 105000,
    "known": 25000,
    "lead": 10000,
    "customer": 8000,
    "active": 1500,
    "churned": 500
  }
}
```

### Search Profiles

```http
GET /api/v1/cdp/profiles
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| q | string | Search query (email, name) |
| lifecycle_stage | string | Filter by stage |
| segment_id | int | Filter by segment |
| page | int | Page number |
| limit | int | Items per page |

### Get Profile

```http
GET /api/v1/cdp/profiles/{profile_id}
Authorization: Bearer {access_token}
```

### Profile Events

```http
GET /api/v1/cdp/profiles/{profile_id}/events
Authorization: Bearer {access_token}
```

### Track Event

```http
POST /api/v1/cdp/events
Authorization: Bearer {api_key}
```

**Request:**
```json
{
  "event_name": "purchase",
  "anonymous_id": "anon_123",
  "user_id": "user_456",
  "properties": {
    "product_id": "prod_789",
    "amount": 99.99,
    "currency": "USD"
  },
  "context": {
    "page_url": "https://example.com/checkout",
    "user_agent": "Mozilla/5.0..."
  }
}
```

---

## CDP Segments

### List Segments

```http
GET /api/v1/cdp/segments
Authorization: Bearer {access_token}
```

### Get Segment

```http
GET /api/v1/cdp/segments/{segment_id}
Authorization: Bearer {access_token}
```

### Create Segment

```http
POST /api/v1/cdp/segments
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "High-Value Customers",
  "description": "Customers with LTV > $500",
  "conditions": {
    "operator": "and",
    "conditions": [
      {
        "type": "computed_trait",
        "trait": "total_purchases",
        "operator": "greater_than",
        "value": 500
      },
      {
        "type": "event",
        "event": "purchase",
        "operator": "occurred",
        "time_window": "last_90_days"
      }
    ]
  }
}
```

### Preview Segment

```http
POST /api/v1/cdp/segments/{segment_id}/preview
Authorization: Bearer {access_token}
```

### Update Segment

```http
PATCH /api/v1/cdp/segments/{segment_id}
Authorization: Bearer {access_token}
```

### Delete Segment

```http
DELETE /api/v1/cdp/segments/{segment_id}
Authorization: Bearer {access_token}
```

---

## CDP Audience Sync

### List Connected Platforms

```http
GET /api/v1/cdp/audience-sync/platforms
Authorization: Bearer {access_token}
```

### List Audiences

```http
GET /api/v1/cdp/audience-sync/audiences
Authorization: Bearer {access_token}
```

### Create Audience

```http
POST /api/v1/cdp/audience-sync/audiences
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "High-Value Customers - Meta",
  "platform": "meta",
  "segment_id": 123,
  "sync_interval": "daily",
  "identifier_types": ["email", "phone"]
}
```

### Trigger Sync

```http
POST /api/v1/cdp/audience-sync/audiences/{audience_id}/sync
Authorization: Bearer {access_token}
```

### Sync History

```http
GET /api/v1/cdp/audience-sync/audiences/{audience_id}/history
Authorization: Bearer {access_token}
```

### Export Audience

```http
POST /api/v1/cdp/audiences/export
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "segment_id": 123,
  "format": "csv",
  "include_traits": true,
  "include_events": false
}
```

---

## Trust Layer

### Get Trust Health

```http
GET /api/v1/trust/health
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "overall_health": 82,
  "status": "healthy",
  "signals": {
    "meta": { "health": 85, "status": "healthy" },
    "google": { "health": 78, "status": "healthy" },
    "tiktok": { "health": 72, "status": "healthy" }
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### Get Signal Details

```http
GET /api/v1/trust/signals/{platform}
Authorization: Bearer {access_token}
```

### Incident History

```http
GET /api/v1/trust/incidents
Authorization: Bearer {access_token}
```

---

## Autopilot

### Get Autopilot Status

```http
GET /api/v1/autopilot/status
Authorization: Bearer {access_token}
```

### Enable/Disable Autopilot

```http
POST /api/v1/autopilot/toggle
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "enabled": true
}
```

### Get Action Queue

```http
GET /api/v1/autopilot/queue
Authorization: Bearer {access_token}
```

### Approve/Reject Action

```http
POST /api/v1/autopilot/actions/{action_id}/approve
POST /api/v1/autopilot/actions/{action_id}/reject
Authorization: Bearer {access_token}
```

---

## Rules Engine

### List Rules

```http
GET /api/v1/rules
Authorization: Bearer {access_token}
```

### Get Rule

```http
GET /api/v1/rules/{rule_id}
Authorization: Bearer {access_token}
```

### Create Rule

```http
POST /api/v1/rules
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "Pause Low ROAS Campaigns",
  "description": "Pause campaigns with ROAS < 1.0",
  "status": "active",
  "conditions": [
    {
      "field": "roas",
      "operator": "less_than",
      "value": 1.0
    }
  ],
  "actions": [
    {
      "type": "pause_campaign"
    },
    {
      "type": "send_alert",
      "config": {
        "channel": "slack",
        "message": "Campaign paused due to low ROAS"
      }
    }
  ]
}
```

### Update Rule

```http
PATCH /api/v1/rules/{rule_id}
Authorization: Bearer {access_token}
```

### Delete Rule

```http
DELETE /api/v1/rules/{rule_id}
Authorization: Bearer {access_token}
```

---

## Predictions

### Get Predictions

```http
GET /api/v1/predictions
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| campaign_id | int | Filter by campaign |
| type | string | spend, conversions, roas |

### Generate Forecast

```http
POST /api/v1/predictions/forecast
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "campaign_ids": [1, 2, 3],
  "days_ahead": 30
}
```

---

## WhatsApp

### Send Message

```http
POST /api/v1/whatsapp/send
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "to": "+1234567890",
  "template": "welcome_message",
  "parameters": {
    "name": "John"
  }
}
```

### List Templates

```http
GET /api/v1/whatsapp/templates
Authorization: Bearer {access_token}
```

### Webhook (Public)

```http
POST /api/v1/whatsapp/webhook
```

---

## Payments

### Create Checkout Session

```http
POST /api/v1/payments/checkout
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "tier": "professional",
  "billing_period": "monthly"
}
```

### Get Subscription

```http
GET /api/v1/subscription/status
Authorization: Bearer {access_token}
```

### Cancel Subscription

```http
POST /api/v1/subscription/cancel
Authorization: Bearer {access_token}
```

### Stripe Webhook (Public)

```http
POST /api/v1/stripe/webhook
```

---

## GDPR

### Export User Data

```http
POST /api/v1/gdpr/export
Authorization: Bearer {access_token}
```

### Delete User Data

```http
POST /api/v1/gdpr/delete
Authorization: Bearer {access_token}
```

### Update Consent

```http
POST /api/v1/gdpr/consent
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "marketing": false,
  "analytics": true
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "success": false,
  "error": "Resource not found",
  "code": "NOT_FOUND",
  "details": {
    "resource": "campaign",
    "id": 123
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |

### Rate Limiting

When rate limited, response includes:

```http
HTTP/1.1 429 Too Many Requests
X-Rate-Limit-Remaining: 0
Retry-After: 60
```

---

## Pagination

### Request

```http
GET /api/v1/campaigns?page=2&limit=20
```

### Response

```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "limit": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": true
}
```
