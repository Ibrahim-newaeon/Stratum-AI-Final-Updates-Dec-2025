# Stratum AI - API Reference

**Version:** 2.0.0
**Base URL:** `https://api.stratum.ai/api/v1`
**Last Updated:** January 2026

---

## Table of Contents

1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
   - [Health](#health)
   - [Auth](#auth)
   - [Users](#users)
   - [Tenants](#tenants)
3. [Dashboard & Analytics](#dashboard--analytics)
   - [Dashboard](#dashboard)
   - [Analytics](#analytics)
   - [Reporting](#reporting)
4. [Campaign Management](#campaign-management)
   - [Campaigns](#campaigns)
   - [Campaign Builder](#campaign-builder)
   - [Pacing](#pacing)
5. [Trust Engine](#trust-engine)
   - [Trust Layer](#trust-layer)
   - [Autopilot](#autopilot)
   - [Rules](#rules)
6. [CDP (Customer Data Platform)](#cdp-customer-data-platform)
   - [Profiles](#profiles)
   - [Segments](#segments)
   - [Events](#events)
   - [Audience Sync](#audience-sync)
7. [Integrations](#integrations)
   - [OAuth](#oauth)
   - [Ad Platforms](#ad-platforms)
   - [CRM](#crm)
   - [Webhooks](#webhooks)
8. [Settings & Configuration](#settings--configuration)
   - [API Keys](#api-keys)
   - [Notifications](#notifications)
   - [Feature Flags](#feature-flags)
9. [Admin Endpoints](#admin-endpoints)
   - [Super Admin](#super-admin)
   - [Subscription & Payments](#subscription--payments)

---

## Authentication

All API requests require authentication using JWT Bearer tokens.

### Obtain Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
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

### Using the Token

Include the token in the `Authorization` header:

```http
GET /api/v1/dashboard/overview
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Core Endpoints

### Health

#### Check API Health
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

---

### Auth

#### Register New User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "name": "John Doe",
  "phone": "+1234567890"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer {token}
```

#### Request Password Reset
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
  "token": "reset-token",
  "new_password": "NewSecurePass123!"
}
```

#### Verify Email
```http
GET /api/v1/auth/verify-email?token={verification_token}
```

---

### Users

#### Get Current User
```http
GET /api/v1/users/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "admin",
  "tenant_id": "uuid",
  "is_active": true,
  "is_verified": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

#### Update Current User
```http
PATCH /api/v1/users/me
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Name",
  "preferences": {
    "theme": "dark",
    "language": "en"
  }
}
```

#### Change Password
```http
POST /api/v1/users/me/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_password": "current-pass",
  "new_password": "new-secure-pass"
}
```

#### List Tenant Users (Admin)
```http
GET /api/v1/users?page=1&limit=20
Authorization: Bearer {token}
```

---

### Tenants

#### Get Current Tenant
```http
GET /api/v1/tenants/current
Authorization: Bearer {token}
```

#### Update Tenant Settings
```http
PATCH /api/v1/tenants/current
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Company Name",
  "settings": {
    "timezone": "UTC",
    "currency": "USD"
  }
}
```

---

## Dashboard & Analytics

### Dashboard

#### Get Dashboard Overview
```http
GET /api/v1/dashboard/overview
Authorization: Bearer {token}
```

**Response:**
```json
{
  "total_spend": 45230.00,
  "total_revenue": 186500.00,
  "roas": 4.12,
  "conversions": 1560,
  "signal_health": 87,
  "active_campaigns": 24,
  "platforms": {
    "meta": {"spend": 20000, "revenue": 85000},
    "google": {"spend": 15000, "revenue": 62000},
    "tiktok": {"spend": 10230, "revenue": 39500}
  }
}
```

#### Get Performance Metrics
```http
GET /api/v1/dashboard/performance?start_date=2026-01-01&end_date=2026-01-31
Authorization: Bearer {token}
```

#### Get Signal Health Summary
```http
GET /api/v1/dashboard/signal-health
Authorization: Bearer {token}
```

---

### Analytics

#### Get Campaign Analytics
```http
GET /api/v1/analytics/campaigns?period=30d
Authorization: Bearer {token}
```

#### Get Attribution Data
```http
GET /api/v1/analytics/attribution?model=data_driven
Authorization: Bearer {token}
```

#### Get Conversion Funnel
```http
GET /api/v1/analytics/funnel?funnel_id={id}
Authorization: Bearer {token}
```

#### Get AI Insights
```http
GET /api/v1/analytics/ai/insights
Authorization: Bearer {token}
```

**Response:**
```json
{
  "insights": [
    {
      "type": "optimization",
      "severity": "high",
      "title": "Budget Reallocation Opportunity",
      "description": "Moving 20% budget from Campaign A to Campaign B could increase ROAS by 15%",
      "potential_impact": "+$5,200 revenue",
      "confidence": 0.87
    }
  ]
}
```

---

### Reporting

#### List Report Templates
```http
GET /api/v1/reporting/templates
Authorization: Bearer {token}
```

#### Create Report
```http
POST /api/v1/reporting/reports
Authorization: Bearer {token}
Content-Type: application/json

{
  "template_id": "uuid",
  "name": "Monthly Performance Report",
  "date_range": {
    "start": "2026-01-01",
    "end": "2026-01-31"
  },
  "format": "pdf"
}
```

#### Schedule Report
```http
POST /api/v1/reporting/schedules
Authorization: Bearer {token}
Content-Type: application/json

{
  "report_id": "uuid",
  "frequency": "weekly",
  "recipients": ["email@example.com"],
  "day_of_week": "monday",
  "time": "09:00"
}
```

#### Export Dashboard
```http
POST /api/v1/reporting/export
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "dashboard",
  "format": "pdf",
  "include_charts": true
}
```

---

## Campaign Management

### Campaigns

#### List Campaigns
```http
GET /api/v1/campaigns?status=active&platform=meta&page=1&limit=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Summer Sale Campaign",
      "platform": "meta",
      "status": "active",
      "budget": 5000.00,
      "spend": 3245.00,
      "revenue": 14500.00,
      "roas": 4.47,
      "conversions": 145,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 24,
  "page": 1,
  "pages": 2
}
```

#### Get Campaign Details
```http
GET /api/v1/campaigns/{campaign_id}
Authorization: Bearer {token}
```

#### Get Campaign Performance
```http
GET /api/v1/campaigns/{campaign_id}/performance?period=7d
Authorization: Bearer {token}
```

#### Get Campaign Recommendations
```http
GET /api/v1/campaigns/{campaign_id}/recommendations
Authorization: Bearer {token}
```

---

### Campaign Builder

#### List Connected Platforms
```http
GET /api/v1/campaign-builder/platforms
Authorization: Bearer {token}
```

#### List Ad Accounts
```http
GET /api/v1/campaign-builder/accounts?platform=meta
Authorization: Bearer {token}
```

#### Create Campaign
```http
POST /api/v1/campaign-builder/campaigns
Authorization: Bearer {token}
Content-Type: application/json

{
  "platform": "meta",
  "ad_account_id": "act_123456",
  "name": "New Campaign",
  "objective": "conversions",
  "budget": {
    "type": "daily",
    "amount": 100.00
  },
  "targeting": {
    "locations": ["US", "CA"],
    "age_min": 25,
    "age_max": 54,
    "interests": ["technology", "business"]
  }
}
```

---

### Pacing

#### Get Pacing Status
```http
GET /api/v1/pacing/status
Authorization: Bearer {token}
```

#### Get Pacing Alerts
```http
GET /api/v1/pacing/alerts
Authorization: Bearer {token}
```

**Response:**
```json
{
  "alerts": [
    {
      "campaign_id": "uuid",
      "campaign_name": "Holiday Sale",
      "type": "underpacing",
      "severity": "warning",
      "message": "Campaign is 25% behind pace. Expected $500, actual $375.",
      "recommendation": "Consider increasing bid or expanding targeting."
    }
  ]
}
```

---

## Trust Engine

### Trust Layer

#### Get Signal Health
```http
GET /api/v1/trust/signal-health
Authorization: Bearer {token}
```

**Response:**
```json
{
  "overall_score": 87,
  "status": "healthy",
  "signals": [
    {
      "name": "pixel_coverage",
      "score": 95,
      "status": "healthy"
    },
    {
      "name": "conversion_accuracy",
      "score": 82,
      "status": "healthy"
    },
    {
      "name": "data_freshness",
      "score": 78,
      "status": "degraded"
    }
  ],
  "thresholds": {
    "healthy": 70,
    "degraded": 40,
    "unhealthy": 0
  }
}
```

#### Get Trust Gate Status
```http
GET /api/v1/trust/gate-status
Authorization: Bearer {token}
```

#### Get Trust Gate Audit Logs
```http
GET /api/v1/trust/audit-logs?page=1&limit=50
Authorization: Bearer {token}
```

---

### Autopilot

#### Get Autopilot Status
```http
GET /api/v1/autopilot/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "enabled": true,
  "mode": "conservative",
  "last_action": "2026-01-15T10:30:00Z",
  "pending_actions": 3,
  "blocked_actions": 1,
  "settings": {
    "max_budget_change_percent": 20,
    "require_approval_above": 500,
    "pause_on_degraded_signal": true
  }
}
```

#### Update Autopilot Settings
```http
PATCH /api/v1/autopilot/settings
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": true,
  "mode": "aggressive",
  "max_budget_change_percent": 30
}
```

#### Get Pending Actions
```http
GET /api/v1/autopilot/pending-actions
Authorization: Bearer {token}
```

#### Approve Action
```http
POST /api/v1/autopilot/actions/{action_id}/approve
Authorization: Bearer {token}
```

#### Reject Action
```http
POST /api/v1/autopilot/actions/{action_id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "Budget constraints"
}
```

---

### Rules

#### List Automation Rules
```http
GET /api/v1/rules
Authorization: Bearer {token}
```

#### Create Rule
```http
POST /api/v1/rules
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Pause Low ROAS Campaigns",
  "description": "Automatically pause campaigns with ROAS below 1.5",
  "enabled": true,
  "conditions": [
    {
      "field": "roas",
      "operator": "less_than",
      "value": 1.5
    },
    {
      "field": "spend",
      "operator": "greater_than",
      "value": 100
    }
  ],
  "actions": [
    {
      "type": "pause_campaign",
      "notify": true
    }
  ],
  "frequency": "hourly"
}
```

#### Update Rule
```http
PATCH /api/v1/rules/{rule_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": false
}
```

#### Delete Rule
```http
DELETE /api/v1/rules/{rule_id}
Authorization: Bearer {token}
```

---

## CDP (Customer Data Platform)

### Profiles

#### Search Profiles
```http
GET /api/v1/cdp/profiles?query=john@example.com&page=1&limit=20
Authorization: Bearer {token}
```

#### Get Profile
```http
GET /api/v1/cdp/profiles/{profile_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "external_id": "cust_123",
  "email": "john@example.com",
  "phone": "+1234567890",
  "lifecycle_stage": "customer",
  "rfm": {
    "recency_score": 5,
    "frequency_score": 4,
    "monetary_score": 5,
    "segment": "champions"
  },
  "traits": {
    "first_name": "John",
    "last_name": "Doe",
    "total_orders": 15,
    "ltv": 2500.00
  },
  "identities": [
    {"type": "email", "value": "john@example.com"},
    {"type": "phone", "value": "+1234567890"}
  ],
  "created_at": "2025-06-15T00:00:00Z",
  "updated_at": "2026-01-15T00:00:00Z"
}
```

#### Get Profile Statistics
```http
GET /api/v1/cdp/profiles/statistics
Authorization: Bearer {token}
```

---

### Segments

#### List Segments
```http
GET /api/v1/cdp/segments
Authorization: Bearer {token}
```

#### Create Segment
```http
POST /api/v1/cdp/segments
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "High Value Customers",
  "description": "Customers with LTV > $1000",
  "conditions": {
    "operator": "and",
    "rules": [
      {
        "field": "traits.ltv",
        "operator": "greater_than",
        "value": 1000
      },
      {
        "field": "lifecycle_stage",
        "operator": "equals",
        "value": "customer"
      }
    ]
  }
}
```

#### Get Segment Preview
```http
POST /api/v1/cdp/segments/preview
Authorization: Bearer {token}
Content-Type: application/json

{
  "conditions": {
    "operator": "and",
    "rules": [
      {"field": "traits.ltv", "operator": "greater_than", "value": 1000}
    ]
  }
}
```

**Response:**
```json
{
  "estimated_size": 2450,
  "sample_profiles": [...]
}
```

#### Update Segment
```http
PATCH /api/v1/cdp/segments/{segment_id}
Authorization: Bearer {token}
```

#### Delete Segment
```http
DELETE /api/v1/cdp/segments/{segment_id}
Authorization: Bearer {token}
```

---

### Events

#### Get Event Timeline
```http
GET /api/v1/cdp/events?profile_id={id}&page=1&limit=50
Authorization: Bearer {token}
```

#### Get Event Statistics
```http
GET /api/v1/cdp/events/statistics?period=30d
Authorization: Bearer {token}
```

#### Track Event
```http
POST /api/v1/cdp/events/track
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_id": "uuid",
  "event_type": "purchase",
  "properties": {
    "order_id": "ORD-123",
    "amount": 150.00,
    "products": ["SKU-001", "SKU-002"]
  },
  "timestamp": "2026-01-15T10:30:00Z"
}
```

---

### Audience Sync

#### List Connected Platforms
```http
GET /api/v1/cdp/audience-sync/platforms
Authorization: Bearer {token}
```

#### List Audiences
```http
GET /api/v1/cdp/audience-sync/audiences
Authorization: Bearer {token}
```

#### Create Audience
```http
POST /api/v1/cdp/audience-sync/audiences
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "High Value Lookalike Source",
  "segment_id": "uuid",
  "platform": "meta",
  "platform_config": {
    "ad_account_id": "act_123456",
    "audience_type": "custom"
  },
  "sync_frequency": "daily"
}
```

#### Trigger Sync
```http
POST /api/v1/cdp/audience-sync/audiences/{audience_id}/sync
Authorization: Bearer {token}
```

#### Get Sync History
```http
GET /api/v1/cdp/audience-sync/audiences/{audience_id}/history
Authorization: Bearer {token}
```

#### Export Audience
```http
POST /api/v1/cdp/audiences/export
Authorization: Bearer {token}
Content-Type: application/json

{
  "segment_id": "uuid",
  "format": "csv",
  "include_traits": true,
  "include_events": false
}
```

---

## Integrations

### OAuth

#### Initiate OAuth Flow
```http
GET /api/v1/oauth/{platform}/authorize
Authorization: Bearer {token}
```

Supported platforms: `meta`, `google`, `tiktok`, `snapchat`, `hubspot`, `pipedrive`, `salesforce`, `zoho`

#### OAuth Callback
```http
GET /api/v1/oauth/{platform}/callback?code={auth_code}&state={state}
```

#### Disconnect Platform
```http
DELETE /api/v1/oauth/{platform}/disconnect
Authorization: Bearer {token}
```

---

### Ad Platforms

#### Get Meta Accounts
```http
GET /api/v1/integrations/meta/accounts
Authorization: Bearer {token}
```

#### Get Google Ads Accounts
```http
GET /api/v1/integrations/google/accounts
Authorization: Bearer {token}
```

#### Get TikTok Accounts
```http
GET /api/v1/integrations/tiktok/accounts
Authorization: Bearer {token}
```

#### Get Snapchat Accounts
```http
GET /api/v1/integrations/snapchat/accounts
Authorization: Bearer {token}
```

---

### CRM

#### Sync CRM Contacts
```http
POST /api/v1/integrations/crm/sync
Authorization: Bearer {token}
Content-Type: application/json

{
  "provider": "hubspot",
  "direction": "bidirectional"
}
```

#### Get CRM Sync Status
```http
GET /api/v1/integrations/crm/status
Authorization: Bearer {token}
```

---

### Webhooks

#### List Webhooks
```http
GET /api/v1/webhooks
Authorization: Bearer {token}
```

#### Create Webhook
```http
POST /api/v1/webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Campaign Status Changes",
  "url": "https://yourapp.com/webhooks/stratum",
  "events": ["campaign.paused", "campaign.activated", "budget.changed"],
  "secret": "your-webhook-secret"
}
```

**Webhook Payload Example:**
```json
{
  "event": "campaign.paused",
  "timestamp": "2026-01-15T10:30:00Z",
  "data": {
    "campaign_id": "uuid",
    "campaign_name": "Summer Sale",
    "reason": "autopilot_low_roas",
    "previous_status": "active"
  }
}
```

#### Update Webhook
```http
PATCH /api/v1/webhooks/{webhook_id}
Authorization: Bearer {token}
```

#### Delete Webhook
```http
DELETE /api/v1/webhooks/{webhook_id}
Authorization: Bearer {token}
```

#### Test Webhook
```http
POST /api/v1/webhooks/{webhook_id}/test
Authorization: Bearer {token}
```

---

## Settings & Configuration

### API Keys

#### List API Keys
```http
GET /api/v1/api-keys
Authorization: Bearer {token}
```

#### Create API Key
```http
POST /api/v1/api-keys
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Production API Key",
  "permissions": ["read:campaigns", "read:analytics", "write:webhooks"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Production API Key",
  "key": "sk_live_xxxxxxxxxxxxxxxxxxxx",
  "prefix": "sk_live_xxxx",
  "permissions": ["read:campaigns", "read:analytics", "write:webhooks"],
  "created_at": "2026-01-15T00:00:00Z",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

> **Note:** The full API key is only shown once upon creation.

#### Revoke API Key
```http
DELETE /api/v1/api-keys/{key_id}
Authorization: Bearer {token}
```

---

### Notifications

#### Get Notifications
```http
GET /api/v1/notifications?unread_only=true&page=1&limit=20
Authorization: Bearer {token}
```

#### Mark as Read
```http
POST /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}
```

#### Mark All as Read
```http
POST /api/v1/notifications/mark-all-read
Authorization: Bearer {token}
```

#### Get Notification Preferences
```http
GET /api/v1/notifications/preferences
Authorization: Bearer {token}
```

#### Update Notification Preferences
```http
PATCH /api/v1/notifications/preferences
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": {
    "campaign_alerts": true,
    "weekly_digest": true,
    "budget_alerts": true
  },
  "slack": {
    "campaign_alerts": true,
    "budget_alerts": true
  },
  "in_app": {
    "all": true
  }
}
```

---

### Feature Flags

#### Get Feature Flags
```http
GET /api/v1/features
Authorization: Bearer {token}
```

**Response:**
```json
{
  "features": {
    "autopilot": true,
    "cdp": true,
    "audience_sync": true,
    "predictive_churn": false,
    "custom_reports": false,
    "what_if_simulator": true
  },
  "tier": "professional",
  "limits": {
    "max_ad_accounts": 15,
    "max_users": 10,
    "max_segments": 50
  }
}
```

---

## Admin Endpoints

### Super Admin

> These endpoints require `superadmin` role.

#### List All Tenants
```http
GET /api/v1/superadmin/tenants?page=1&limit=20
Authorization: Bearer {token}
```

#### Get Tenant Details
```http
GET /api/v1/superadmin/tenants/{tenant_id}
Authorization: Bearer {token}
```

#### Update Tenant
```http
PATCH /api/v1/superadmin/tenants/{tenant_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "enterprise",
  "max_users": 100,
  "feature_flags": {
    "predictive_churn": true
  }
}
```

#### Get Platform Analytics
```http
GET /api/v1/superadmin/analytics/overview
Authorization: Bearer {token}
```

---

### Subscription & Payments

#### Get Current Subscription
```http
GET /api/v1/subscription
Authorization: Bearer {token}
```

#### Get Available Plans
```http
GET /api/v1/subscription/plans
Authorization: Bearer {token}
```

#### Create Checkout Session
```http
POST /api/v1/payments/checkout
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "professional",
  "billing_period": "monthly"
}
```

#### Get Billing History
```http
GET /api/v1/payments/history
Authorization: Bearer {token}
```

#### Cancel Subscription
```http
POST /api/v1/subscription/cancel
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "optional cancellation reason"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong",
  "code": "ERROR_CODE",
  "status_code": 400
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limits

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| Starter | 60 | 20 |
| Professional | 300 | 50 |
| Enterprise | 1000 | 100 |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 295
X-RateLimit-Reset: 1642234567
```

---

## Pagination

List endpoints support pagination:

```http
GET /api/v1/campaigns?page=1&limit=20
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "pages": 8,
  "limit": 20
}
```

---

## Webhooks Events

Available webhook events:

| Event | Description |
|-------|-------------|
| `campaign.created` | New campaign created |
| `campaign.activated` | Campaign activated |
| `campaign.paused` | Campaign paused |
| `campaign.deleted` | Campaign deleted |
| `budget.changed` | Budget modified |
| `signal.degraded` | Signal health degraded |
| `signal.recovered` | Signal health recovered |
| `autopilot.action` | Autopilot action executed |
| `sync.completed` | Audience sync completed |
| `sync.failed` | Audience sync failed |

---

*For additional support, contact api-support@stratum.ai*
