# Platform Integrations API Contracts

## Overview

API endpoints for managing platform integrations and CAPI connectors.

**Base URL**: `/api/v1/tenant/{tenant_id}`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Platform Connections

### GET /integrations/platforms

List all supported platforms and their connection status.

#### Response

```json
{
  "success": true,
  "data": {
    "platforms": [
      {
        "platform": "meta",
        "name": "Meta (Facebook)",
        "status": "connected",
        "connected_at": "2024-01-15T10:00:00Z",
        "health": {
          "status": "healthy",
          "success_rate": 98.5,
          "avg_latency_ms": 245,
          "last_check": "2024-01-15T14:30:00Z"
        }
      },
      {
        "platform": "google",
        "name": "Google Ads",
        "status": "connected",
        "connected_at": "2024-01-10T09:00:00Z",
        "health": {
          "status": "healthy",
          "success_rate": 99.1,
          "avg_latency_ms": 180,
          "last_check": "2024-01-15T14:30:00Z"
        }
      },
      {
        "platform": "tiktok",
        "name": "TikTok",
        "status": "connected",
        "connected_at": "2024-01-12T11:00:00Z",
        "health": {
          "status": "degraded",
          "success_rate": 82.3,
          "avg_latency_ms": 1245,
          "last_check": "2024-01-15T14:30:00Z",
          "issues": ["High latency detected"]
        }
      },
      {
        "platform": "snapchat",
        "name": "Snapchat",
        "status": "disconnected",
        "health": null
      }
    ]
  }
}
```

---

### POST /integrations/platforms/{platform}/connect

Connect to a platform with credentials.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Platform: meta, google, tiktok, snapchat |

#### Request (Meta)

```json
{
  "pixel_id": "1234567890123456",
  "access_token": "EAABsb..."
}
```

#### Request (Google)

```json
{
  "customer_id": "123-456-7890",
  "conversion_action_id": "1234567890",
  "developer_token": "...",
  "refresh_token": "...",
  "client_id": "...",
  "client_secret": "..."
}
```

#### Request (TikTok)

```json
{
  "pixel_code": "ABCDEFG123",
  "access_token": "..."
}
```

#### Request (Snapchat)

```json
{
  "pixel_id": "...",
  "access_token": "..."
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "status": "connected",
    "platform": "meta",
    "message": "Successfully connected to Meta CAPI",
    "details": {
      "pixel_name": "Summer Sale Pixel"
    }
  }
}
```

---

### POST /integrations/platforms/{platform}/test

Test connection without saving.

#### Request

Same as connect request.

#### Response

```json
{
  "success": true,
  "data": {
    "status": "connected",
    "platform": "meta",
    "message": "Connection test successful",
    "details": {
      "pixel_name": "Summer Sale Pixel"
    }
  }
}
```

---

### DELETE /integrations/platforms/{platform}/disconnect

Disconnect from a platform.

#### Response

```json
{
  "success": true,
  "data": {
    "status": "disconnected",
    "platform": "meta",
    "message": "Platform disconnected successfully"
  }
}
```

---

## Health Monitoring

### GET /integrations/health

Get health summary for all connected platforms.

#### Response

```json
{
  "success": true,
  "data": {
    "overall_status": "degraded",
    "checked_at": "2024-01-15T14:30:00Z",
    "platforms": {
      "meta": {
        "status": "healthy",
        "success_rate": 98.5,
        "avg_latency_ms": 245,
        "issues": []
      },
      "google": {
        "status": "healthy",
        "success_rate": 99.1,
        "avg_latency_ms": 180,
        "issues": []
      },
      "tiktok": {
        "status": "degraded",
        "success_rate": 82.3,
        "avg_latency_ms": 1245,
        "issues": ["High latency: 1245ms"]
      }
    }
  }
}
```

---

### GET /integrations/platforms/{platform}/health

Get detailed health for a specific platform.

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "status": "healthy",
    "last_check": "2024-01-15T14:30:00Z",
    "success_rate_1h": 98.5,
    "avg_latency_ms": 245,
    "circuit_state": "closed",
    "error_count_1h": 19,
    "events_processed_1h": 1234,
    "issues": []
  }
}
```

---

### GET /integrations/platforms/{platform}/health/history

Get health history for a platform.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours` | integer | Lookback period (default: 24) |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T14:00:00Z",
      "status": "healthy",
      "success_rate": 98.5,
      "avg_latency_ms": 245,
      "error_count": 5
    },
    {
      "timestamp": "2024-01-15T13:00:00Z",
      "status": "healthy",
      "success_rate": 99.2,
      "avg_latency_ms": 220,
      "error_count": 3
    }
  ]
}
```

---

## Event Delivery

### POST /capi/events

Send conversion events to connected platforms.

#### Request

```json
{
  "events": [
    {
      "event_id": "evt_abc123",
      "event_name": "purchase",
      "event_time": 1705329600,
      "action_source": "website",
      "event_source_url": "https://example.com/checkout/success",
      "user_data": {
        "email": "user@example.com",
        "phone": "+1234567890",
        "first_name": "John",
        "last_name": "Doe"
      },
      "parameters": {
        "value": 99.99,
        "currency": "USD",
        "order_id": "ORD-12345"
      }
    }
  ],
  "platforms": ["meta", "google"]
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "results": {
      "meta": {
        "success": true,
        "events_received": 1,
        "events_processed": 1,
        "request_id": "abc123",
        "errors": []
      },
      "google": {
        "success": true,
        "events_received": 1,
        "events_processed": 1,
        "request_id": "xyz789",
        "errors": []
      }
    },
    "total_sent": 1,
    "total_processed": 2
  }
}
```

---

### POST /capi/events/batch

Send batch of events for a specific platform.

#### Request

```json
{
  "platform": "meta",
  "events": [
    {
      "event_name": "purchase",
      "event_time": 1705329600,
      "user_data": { "email": "user1@example.com" },
      "parameters": { "value": 50.00 }
    },
    {
      "event_name": "purchase",
      "event_time": 1705329700,
      "user_data": { "email": "user2@example.com" },
      "parameters": { "value": 75.00 }
    }
  ]
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "success": true,
    "events_received": 2,
    "events_processed": 2,
    "errors": [],
    "request_id": "batch_abc123",
    "latency_ms": 450
  }
}
```

---

## Event Logs

### GET /integrations/events/logs

Get event delivery logs.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Filter by platform (optional) |
| `status` | string | Filter: success, failed (optional) |
| `event_name` | string | Filter by event type (optional) |
| `since` | datetime | Start time (ISO 8601) |
| `until` | datetime | End time (ISO 8601) |
| `limit` | integer | Max results (default: 100) |

#### Response

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "event_id": "evt_abc123",
        "platform": "meta",
        "event_name": "Purchase",
        "timestamp": "2024-01-15T14:30:15Z",
        "success": true,
        "latency_ms": 245,
        "request_id": "abc123",
        "retry_count": 0
      },
      {
        "event_id": "evt_xyz789",
        "platform": "tiktok",
        "event_name": "CompletePayment",
        "timestamp": "2024-01-15T14:29:45Z",
        "success": false,
        "latency_ms": 1245,
        "error_message": "Rate limit exceeded",
        "retry_count": 2
      }
    ],
    "total": 1234,
    "has_more": true
  }
}
```

---

## Circuit Breaker

### GET /integrations/platforms/{platform}/circuit

Get circuit breaker state.

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "state": "closed",
    "failure_count": 0,
    "last_failure": null,
    "recovery_timeout_seconds": 60
  }
}
```

---

### POST /integrations/platforms/{platform}/circuit/reset

Manually reset circuit breaker.

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "state": "closed",
    "message": "Circuit breaker reset successfully"
  }
}
```

---

## Batch Optimization

### GET /integrations/platforms/{platform}/batch/recommendation

Get batch size recommendation.

#### Response

```json
{
  "success": true,
  "data": {
    "platform": "meta",
    "current_batch_size": 500,
    "recommended_batch_size": 1000,
    "estimated_throughput_improvement": 15.5,
    "recommendation": "Increase batch size for better throughput."
  }
}
```

---

## Deduplication Stats

### GET /integrations/deduplication/stats

Get deduplication statistics.

#### Response

```json
{
  "success": true,
  "data": {
    "tracked_events": 45678,
    "max_size": 100000,
    "ttl_hours": 24,
    "duplicates_blocked_24h": 234
  }
}
```

---

## Connection Pool

### GET /integrations/pool/stats

Get connection pool statistics.

#### Response

```json
{
  "success": true,
  "data": {
    "meta": {
      "connections": 5,
      "max_connections": 10
    },
    "google": {
      "connections": 3,
      "max_connections": 10
    },
    "tiktok": {
      "connections": 2,
      "max_connections": 10
    }
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
    "code": "CONNECTION_FAILED",
    "message": "Failed to connect to platform",
    "details": {
      "platform": "meta",
      "reason": "Invalid access token"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PLATFORM_NOT_FOUND` | 404 | Unknown platform |
| `CONNECTION_FAILED` | 400 | Connection test failed |
| `INVALID_CREDENTIALS` | 401 | Invalid platform credentials |
| `ALREADY_CONNECTED` | 400 | Platform already connected |
| `NOT_CONNECTED` | 400 | Platform not connected |
| `CIRCUIT_OPEN` | 503 | Circuit breaker open |
| `RATE_LIMITED` | 429 | Platform rate limit exceeded |
| `EVENT_REJECTED` | 400 | Event rejected by platform |

---

## Webhooks

### POST /integrations/webhooks/{platform}

Webhook endpoint for platform callbacks.

#### Meta Webhook

```json
{
  "object": "page",
  "entry": [
    {
      "id": "PAGE_ID",
      "time": 1705329600,
      "changes": [
        {
          "field": "leadgen",
          "value": {
            "leadgen_id": "123456789",
            "page_id": "PAGE_ID"
          }
        }
      ]
    }
  ]
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 120/min |
| Connect/disconnect | 10/min |
| Event sending | Platform-specific |
| Circuit reset | 5/min |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
