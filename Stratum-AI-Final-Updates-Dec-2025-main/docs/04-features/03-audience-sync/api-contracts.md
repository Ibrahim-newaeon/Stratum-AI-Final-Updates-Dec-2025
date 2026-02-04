# Audience Sync API Contracts

## Overview

API endpoints for syncing CDP segments to ad platforms.

**Base URL**: `/api/v1/cdp/audience-sync`

---

## Authentication

All endpoints require Bearer token authentication.

---

## Platform Endpoints

### GET /platforms

List connected platforms.

#### Response

```json
{
  "platforms": [
    {
      "platform": "meta",
      "connected": true,
      "ad_accounts": [
        {
          "id": "act_123456789",
          "name": "Main Ad Account",
          "currency": "USD",
          "connected_at": "2024-01-01T10:00:00Z"
        }
      ],
      "scopes": ["ads_management", "custom_audiences"],
      "expires_at": "2024-04-01T10:00:00Z"
    },
    {
      "platform": "google",
      "connected": false,
      "ad_accounts": []
    }
  ]
}
```

### POST /platforms/{platform}/connect

Initiate OAuth connection.

#### Response

```json
{
  "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?client_id=...",
  "state": "random-state-token"
}
```

### POST /platforms/{platform}/callback

OAuth callback handler.

#### Request

```json
{
  "code": "oauth-authorization-code",
  "state": "random-state-token"
}
```

### DELETE /platforms/{platform}

Disconnect platform.

```json
{
  "disconnected": true,
  "platform": "meta",
  "ad_accounts_removed": 2
}
```

---

## Audience Endpoints

### GET /audiences

List platform audiences.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Filter by platform |
| `segment_id` | UUID | Filter by source segment |
| `status` | string | Filter: active, paused |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

#### Response

```json
{
  "audiences": [
    {
      "id": "uuid-...",
      "segment_id": "uuid-...",
      "segment_name": "High Value Customers",
      "platform": "meta",
      "platform_audience_id": "23847583947582",
      "platform_audience_name": "High Value Customers - Stratum",
      "ad_account_id": "act_123456789",
      "is_active": true,
      "auto_sync": true,
      "sync_interval_hours": 24,
      "last_sync_at": "2024-01-15T14:30:00Z",
      "last_sync_status": "completed",
      "platform_size": 1155,
      "matched_size": 1155,
      "match_rate": 88.7,
      "next_sync_at": "2024-01-16T14:30:00Z",
      "created_at": "2024-01-10T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### POST /audiences

Create platform audience.

#### Request

```json
{
  "segment_id": "uuid-...",
  "platform": "meta",
  "ad_account_id": "act_123456789",
  "audience_name": "High Value Customers - Stratum",
  "description": "CDP segment: High Value Customers",
  "auto_sync": true,
  "sync_interval_hours": 24
}
```

#### Response

```json
{
  "audience": {
    "id": "uuid-...",
    "segment_id": "uuid-...",
    "platform": "meta",
    "platform_audience_id": "23847583947582",
    "platform_audience_name": "High Value Customers - Stratum",
    "ad_account_id": "act_123456789"
  },
  "initial_sync": {
    "job_id": "uuid-...",
    "status": "completed",
    "profiles_sent": 1234,
    "matched": 1087,
    "match_rate": 88.1,
    "duration_ms": 12500
  }
}
```

### GET /audiences/{id}

Get audience details.

```json
{
  "id": "uuid-...",
  "segment_id": "uuid-...",
  "segment_name": "High Value Customers",
  "segment_profile_count": 1302,
  "platform": "meta",
  "platform_audience_id": "23847583947582",
  "platform_audience_name": "High Value Customers - Stratum",
  "ad_account_id": "act_123456789",
  "description": "CDP segment: High Value Customers",
  "is_active": true,
  "auto_sync": true,
  "sync_interval_hours": 24,
  "last_sync_at": "2024-01-15T14:30:00Z",
  "last_sync_status": "completed",
  "platform_size": 1155,
  "matched_size": 1155,
  "match_rate": 88.7,
  "next_sync_at": "2024-01-16T14:30:00Z",
  "sync_stats_30d": {
    "total_syncs": 15,
    "successful_syncs": 15,
    "failed_syncs": 0,
    "avg_match_rate": 87.9,
    "profiles_added": 256,
    "profiles_removed": 45
  },
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

### PATCH /audiences/{id}

Update audience settings.

#### Request

```json
{
  "auto_sync": true,
  "sync_interval_hours": 12,
  "is_active": true
}
```

### DELETE /audiences/{id}

Delete platform audience.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `delete_from_platform` | boolean | Also delete from ad platform (default: true) |

#### Response

```json
{
  "deleted": true,
  "audience_id": "uuid-...",
  "platform_audience_deleted": true
}
```

---

## Sync Endpoints

### POST /audiences/{id}/sync

Trigger manual sync.

#### Request

```json
{
  "operation": "update"
}
```

**Operation Values**:
- `update`: Incremental sync (add/remove delta)
- `replace`: Full replace all users

#### Response

```json
{
  "job_id": "uuid-...",
  "status": "pending",
  "operation": "update",
  "segment_size": 1302,
  "estimated_changes": {
    "to_add": 68,
    "to_remove": 0
  }
}
```

### GET /audiences/{id}/history

Get sync history.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | History period (default: 30) |
| `status` | string | Filter by status |
| `limit` | integer | Max results |

#### Response

```json
{
  "audience_id": "uuid-...",
  "history": [
    {
      "job_id": "uuid-...",
      "operation": "update",
      "status": "completed",
      "profiles_sent": 68,
      "profiles_added": 68,
      "profiles_removed": 0,
      "profiles_failed": 0,
      "match_rate": 88.7,
      "triggered_by": "scheduled",
      "started_at": "2024-01-15T14:30:00Z",
      "completed_at": "2024-01-15T14:30:04Z",
      "duration_ms": 4200
    }
  ],
  "summary": {
    "total_syncs": 15,
    "successful": 15,
    "failed": 0,
    "avg_match_rate": 87.9
  }
}
```

### GET /sync-jobs/{job_id}

Get sync job details.

```json
{
  "job_id": "uuid-...",
  "audience_id": "uuid-...",
  "platform": "meta",
  "operation": "update",
  "status": "completed",
  "profiles_sent": 68,
  "profiles_added": 68,
  "profiles_removed": 0,
  "profiles_failed": 0,
  "match_rate": 88.7,
  "triggered_by": "manual",
  "triggered_by_user_id": 123,
  "started_at": "2024-01-15T14:30:00Z",
  "completed_at": "2024-01-15T14:30:04Z",
  "duration_ms": 4200,
  "platform_response": {
    "audience_id": "23847583947582",
    "audience_size": 1155,
    "status": "ready"
  }
}
```

---

## Export Endpoints

### POST /audiences/export

Export segment for manual upload.

#### Request

```json
{
  "segment_id": "uuid-...",
  "format": "csv",
  "options": {
    "include_traits": true,
    "include_events": false,
    "identifier_types": ["email", "phone"],
    "hash_identifiers": true
  }
}
```

#### Response

```json
{
  "export_id": "uuid-...",
  "status": "processing",
  "segment_id": "uuid-...",
  "profile_count": 1234
}
```

### GET /exports/{export_id}

Get export status/download.

```json
{
  "export_id": "uuid-...",
  "status": "completed",
  "download_url": "https://cdn.stratum.ai/exports/segment-123.csv",
  "expires_at": "2024-01-16T14:30:00Z",
  "profile_count": 1234,
  "file_size_bytes": 245000,
  "format": "csv"
}
```

---

## Schemas

### PlatformAudience

```typescript
interface PlatformAudience {
  id: string;
  segment_id: string;
  segment_name: string;
  platform: 'meta' | 'google' | 'tiktok' | 'snapchat';
  platform_audience_id: string | null;
  platform_audience_name: string;
  ad_account_id: string;
  description: string | null;
  is_active: boolean;
  auto_sync: boolean;
  sync_interval_hours: number;
  last_sync_at: string | null;
  last_sync_status: SyncStatus | null;
  platform_size: number | null;
  matched_size: number | null;
  match_rate: number | null;
  next_sync_at: string | null;
  created_at: string;
  updated_at: string;
}
```

### AudienceSyncJob

```typescript
interface AudienceSyncJob {
  job_id: string;
  audience_id: string;
  platform: string;
  operation: 'create' | 'update' | 'replace' | 'delete';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  profiles_sent: number;
  profiles_added: number;
  profiles_removed: number;
  profiles_failed: number;
  match_rate: number | null;
  triggered_by: 'manual' | 'scheduled' | 'api';
  triggered_by_user_id: number | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  platform_response: object | null;
}
```

### CreateAudienceRequest

```typescript
interface CreateAudienceRequest {
  segment_id: string;
  platform: 'meta' | 'google' | 'tiktok' | 'snapchat';
  ad_account_id: string;
  audience_name: string;
  description?: string;
  auto_sync?: boolean;
  sync_interval_hours?: number;
}
```

---

## Error Responses

### Error Format

```json
{
  "error": {
    "code": "PLATFORM_ERROR",
    "message": "Failed to create audience on Meta",
    "details": {
      "platform_error_code": 2654,
      "platform_error_message": "Ad account does not have permission"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SEGMENT_NOT_FOUND` | 404 | Source segment not found |
| `AUDIENCE_NOT_FOUND` | 404 | Platform audience not found |
| `PLATFORM_NOT_CONNECTED` | 400 | Platform not connected |
| `CREDENTIALS_EXPIRED` | 401 | Platform credentials expired |
| `PLATFORM_ERROR` | 502 | Platform API error |
| `SYNC_IN_PROGRESS` | 409 | Sync already running |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Webhooks

### Sync Completed

```json
{
  "event": "audience_sync.completed",
  "timestamp": "2024-01-15T14:30:04Z",
  "data": {
    "job_id": "uuid-...",
    "audience_id": "uuid-...",
    "platform": "meta",
    "operation": "update",
    "profiles_sent": 68,
    "profiles_added": 68,
    "match_rate": 88.7,
    "duration_ms": 4200
  }
}
```

### Sync Failed

```json
{
  "event": "audience_sync.failed",
  "timestamp": "2024-01-15T14:30:04Z",
  "data": {
    "job_id": "uuid-...",
    "audience_id": "uuid-...",
    "platform": "meta",
    "error_code": "PLATFORM_ERROR",
    "error_message": "Rate limit exceeded"
  }
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET /audiences | 60/min |
| POST /audiences | 10/min |
| POST /audiences/{id}/sync | 10/min per audience |
| POST /audiences/export | 5/min |
