# Campaign Builder API Contracts

## Overview

Tenant-scoped API endpoints for platform connections, ad accounts, campaign drafts, and publish logs.

**Base URL**: `/api/v1/tenant/{tenant_id}`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Platform Connectors

### GET /connect/{platform}/status

Get connection status for a platform.

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "status": "connected",
    "connected_at": "2024-01-01T10:00:00Z",
    "last_refreshed_at": "2024-01-15T08:00:00Z",
    "scopes": ["ads_management", "ads_read", "business_management"],
    "last_error": null
  }
}
```

### POST /connect/{platform}/start

Start OAuth flow for a platform.

#### Response

```json
{
  "success": true,
  "data": {
    "oauth_url": "https://www.facebook.com/v18.0/dialog/oauth?client_id=...",
    "message": "Redirect user to OAuth URL for meta"
  }
}
```

### POST /connect/{platform}/callback

OAuth callback handler.

#### Request

```json
{
  "code": "oauth-authorization-code",
  "state": "state-token"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "status": "connected",
    "ad_accounts_synced": 3
  }
}
```

### POST /connect/{platform}/refresh

Refresh OAuth token for a platform.

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Token refreshed for meta"
  }
}
```

### DELETE /connect/{platform}

Disconnect a platform.

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Disconnected from meta"
  }
}
```

---

## Ad Accounts

### GET /ad-accounts/{platform}

List ad accounts for a platform.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled_only` | boolean | Only return enabled accounts |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-...",
      "platform": "meta",
      "platform_account_id": "act_123456789",
      "name": "Acme Corp Main",
      "business_name": "Acme Corporation",
      "currency": "USD",
      "timezone": "America/New_York",
      "is_enabled": true,
      "daily_budget_cap": 1000.00,
      "last_synced_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### POST /ad-accounts/{platform}/sync

Trigger ad accounts sync from platform.

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Sync started for meta ad accounts"
  }
}
```

### PUT /ad-accounts/{platform}/{ad_account_id}

Update ad account settings.

#### Request

```json
{
  "is_enabled": true,
  "daily_budget_cap": 1500.00
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "platform": "meta",
    "platform_account_id": "act_123456789",
    "name": "Acme Corp Main",
    "is_enabled": true,
    "daily_budget_cap": 1500.00
  }
}
```

---

## Campaign Drafts

### GET /campaign-drafts

List campaign drafts.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Filter by platform |
| `status` | string | Filter by status |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

#### Response

```json
{
  "success": true,
  "data": {
    "drafts": [
      {
        "id": "uuid-...",
        "tenant_id": 1,
        "platform": "meta",
        "ad_account_id": "uuid-...",
        "name": "Summer Sale 2024",
        "description": "Summer promotional campaign",
        "status": "draft",
        "draft_json": { ... },
        "created_at": "2024-01-10T10:00:00Z",
        "updated_at": "2024-01-14T15:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 10
  }
}
```

### POST /campaign-drafts

Create a new campaign draft.

#### Request

```json
{
  "platform": "meta",
  "ad_account_id": "uuid-...",
  "name": "Summer Sale 2024",
  "description": "Summer promotional campaign",
  "draft_json": {
    "campaign": {
      "name": "Summer Sale 2024",
      "objective": "CONVERSIONS",
      "budget": {
        "amount": 1000.00,
        "currency": "USD",
        "type": "daily"
      }
    },
    "ad_sets": [...],
    "ads": [...]
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "tenant_id": 1,
    "platform": "meta",
    "name": "Summer Sale 2024",
    "status": "draft",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

### GET /campaign-drafts/{id}

Get campaign draft by ID.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "tenant_id": 1,
    "platform": "meta",
    "ad_account_id": "uuid-...",
    "name": "Summer Sale 2024",
    "description": "Summer promotional campaign",
    "status": "approved",
    "draft_json": { ... },
    "created_at": "2024-01-10T10:00:00Z",
    "updated_at": "2024-01-14T15:30:00Z",
    "submitted_at": "2024-01-14T16:00:00Z",
    "approved_at": "2024-01-15T09:00:00Z",
    "platform_campaign_id": null,
    "published_at": null
  }
}
```

### PUT /campaign-drafts/{id}

Update campaign draft.

#### Request

```json
{
  "name": "Summer Sale 2024 - Updated",
  "draft_json": { ... }
}
```

### DELETE /campaign-drafts/{id}

Delete campaign draft.

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Draft deleted"
  }
}
```

---

## Workflow Endpoints

### POST /campaign-drafts/{id}/submit

Submit draft for approval.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "status": "submitted",
    "submitted_at": "2024-01-15T10:00:00Z"
  }
}
```

### POST /campaign-drafts/{id}/approve

Approve campaign draft.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "status": "approved",
    "approved_at": "2024-01-15T11:00:00Z"
  }
}
```

### POST /campaign-drafts/{id}/reject

Reject campaign draft.

#### Request

```json
{
  "reason": "Budget too high for test campaign"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "status": "rejected",
    "rejected_at": "2024-01-15T11:00:00Z",
    "rejection_reason": "Budget too high for test campaign"
  }
}
```

### POST /campaign-drafts/{id}/publish

Publish campaign to platform.

#### Response (Async)

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "status": "publishing",
    "message": "Publishing campaign to platform"
  }
}
```

### POST /campaign-drafts/{id}/resubmit

Resubmit rejected draft.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "status": "submitted",
    "submitted_at": "2024-01-16T10:00:00Z"
  }
}
```

---

## Publish Logs

### GET /publish-logs

List publish logs for tenant.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `draft_id` | UUID | Filter by draft |
| `platform` | string | Filter by platform |
| `result_status` | string | Filter: success, failure |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

#### Response

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "uuid-...",
        "draft_id": "uuid-...",
        "platform": "meta",
        "platform_account_id": "act_123456789",
        "event_time": "2024-01-15T12:00:00Z",
        "result_status": "success",
        "platform_campaign_id": "23842927...",
        "error_code": null,
        "error_message": null,
        "retry_count": 0
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 10
  }
}
```

### GET /publish-logs/{id}

Get publish log details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "draft_id": "uuid-...",
    "platform": "meta",
    "platform_account_id": "act_123456789",
    "event_time": "2024-01-15T12:00:00Z",
    "request_json": { ... },
    "response_json": { ... },
    "result_status": "success",
    "platform_campaign_id": "23842927...",
    "retry_count": 0
  }
}
```

---

## Schemas

### CampaignDraftCreate

```typescript
interface CampaignDraftCreate {
  platform: 'meta' | 'google' | 'tiktok' | 'snapchat'
  ad_account_id: string              // UUID
  name: string                       // Campaign name
  description?: string               // Optional description
  draft_json: DraftJSON              // Campaign configuration
}
```

### DraftJSON

```typescript
interface DraftJSON {
  campaign: {
    name: string
    objective: string
    budget: {
      amount: number
      currency: string
      type: 'daily' | 'lifetime'
    }
    schedule?: {
      start_date: string
      end_date?: string
    }
  }
  ad_sets: AdSetConfig[]
  ads: AdConfig[]
}
```

### AdSetConfig

```typescript
interface AdSetConfig {
  name: string
  targeting: {
    locations: string[]
    age_min?: number
    age_max?: number
    genders?: string[]
    interests?: string[]
  }
  budget?: {
    amount: number
    type: 'daily' | 'lifetime'
  }
  optimization_goal: string
  billing_event: string
}
```

### AdConfig

```typescript
interface AdConfig {
  name: string
  ad_set_index: number
  creative: {
    type: 'image' | 'video' | 'carousel'
    image_url?: string
    video_url?: string
    headline: string
    description?: string
    call_to_action: string
    link_url: string
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
    "code": "PLATFORM_NOT_CONNECTED",
    "message": "Meta platform is not connected",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PLATFORM_NOT_CONNECTED` | 400 | Platform not connected |
| `TOKEN_EXPIRED` | 401 | OAuth token expired |
| `AD_ACCOUNT_NOT_FOUND` | 404 | Ad account not found |
| `AD_ACCOUNT_NOT_ENABLED` | 400 | Ad account not enabled |
| `DRAFT_NOT_FOUND` | 404 | Campaign draft not found |
| `INVALID_STATUS_TRANSITION` | 400 | Invalid workflow transition |
| `BUDGET_EXCEEDS_CAP` | 400 | Budget exceeds account cap |
| `PUBLISH_FAILED` | 502 | Platform publish failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Platform rate limit hit |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 60/min |
| POST/PUT endpoints | 30/min |
| Publish endpoint | 10/min per draft |
| Sync endpoint | 5/min per platform |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
