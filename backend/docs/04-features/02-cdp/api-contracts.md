# CDP API Contracts

## Overview

API endpoints for the Customer Data Platform, including event ingestion, profile management, segments, and identity resolution.

**Base URL**: `/api/v1/cdp`

---

## Authentication

All endpoints require Bearer token authentication except event ingestion, which uses source key authentication.

---

## Event Ingestion

### POST /events

Ingest events (single or batch).

#### Request

```http
POST /api/v1/cdp/events
Content-Type: application/json
Authorization: Bearer <token>
X-Source-Key: <source_key>
```

```json
{
  "events": [
    {
      "event_name": "Purchase",
      "event_time": "2024-01-15T14:30:00Z",
      "idempotency_key": "order-12345",
      "identifiers": [
        {"type": "email", "value": "john@example.com"},
        {"type": "anonymous_id", "value": "abc123"}
      ],
      "properties": {
        "order_id": "12345",
        "total": 99.99,
        "currency": "USD",
        "products": [
          {"sku": "SHOE-001", "quantity": 1, "price": 99.99}
        ]
      },
      "context": {
        "user_agent": "Mozilla/5.0...",
        "ip": "192.168.1.1",
        "locale": "en-US",
        "campaign": {
          "source": "google",
          "medium": "cpc",
          "name": "summer_sale"
        }
      },
      "consent": {
        "analytics": true,
        "ads": true
      }
    }
  ]
}
```

#### Response

```json
{
  "accepted": 1,
  "rejected": 0,
  "duplicates": 0,
  "results": [
    {
      "event_id": "uuid-...",
      "status": "accepted",
      "profile_id": "uuid-...",
      "emq_score": 85.5
    }
  ]
}
```

#### Status Values

| Status | Description |
|--------|-------------|
| `accepted` | Event stored successfully |
| `rejected` | Validation failed |
| `duplicate` | Idempotency key already processed |

---

## Profile Endpoints

### GET /profiles/{profile_id}

Get profile by ID.

#### Request

```http
GET /api/v1/cdp/profiles/uuid-...
Authorization: Bearer <token>
```

#### Response

```json
{
  "id": "uuid-...",
  "tenant_id": 123,
  "external_id": "CUST-001",
  "first_seen_at": "2024-01-01T10:00:00Z",
  "last_seen_at": "2024-01-15T14:30:00Z",
  "profile_data": {
    "first_name": "John",
    "last_name": "Doe",
    "country": "US"
  },
  "computed_traits": {
    "total_purchases": 8,
    "avg_order_value": 125.50,
    "days_since_last_purchase": 5,
    "rfm_segment": "Champions"
  },
  "lifecycle_stage": "customer",
  "total_events": 42,
  "total_sessions": 15,
  "total_purchases": 8,
  "total_revenue": 1250.00,
  "identifiers": [
    {
      "id": "uuid-...",
      "identifier_type": "email",
      "identifier_value": "john@example.com",
      "identifier_hash": "sha256...",
      "is_primary": true,
      "confidence_score": 1.0,
      "verified_at": "2024-01-05T12:00:00Z"
    }
  ],
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

### GET /profiles

Lookup profile by identifier.

#### Request

```http
GET /api/v1/cdp/profiles?identifier_type=email&identifier_value=john@example.com
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `identifier_type` | string | Yes | Type: email, phone, device_id, etc. |
| `identifier_value` | string | Yes | Value to search for |

### GET /profiles/search

Search profiles with pagination.

#### Request

```http
GET /api/v1/cdp/profiles/search?q=john&lifecycle_stage=customer&page=1&page_size=20
Authorization: Bearer <token>
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (email, name, ID) |
| `lifecycle_stage` | string | Filter by stage |
| `segment_id` | string | Filter by segment membership |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20, max: 100) |

#### Response

```json
{
  "profiles": [...],
  "total": 1234,
  "page": 1,
  "page_size": 20
}
```

### DELETE /profiles/{profile_id}

Delete a profile (GDPR compliance).

#### Response

```json
{
  "profile_id": "uuid-...",
  "deleted_at": "2024-01-15T14:30:00Z",
  "events_deleted": 42,
  "identifiers_deleted": 3
}
```

---

## Source Endpoints

### GET /sources

List data sources.

```json
{
  "sources": [
    {
      "id": "uuid-...",
      "name": "Website Pixel",
      "source_type": "website",
      "source_key": "sk_live_abc...",
      "is_active": true,
      "event_count": 125000,
      "last_event_at": "2024-01-15T14:30:00Z"
    }
  ],
  "total": 3
}
```

### POST /sources

Create new source.

#### Request

```json
{
  "name": "Server API",
  "source_type": "server",
  "config": {
    "allowed_ips": ["10.0.0.0/8"]
  }
}
```

#### Response

```json
{
  "id": "uuid-...",
  "name": "Server API",
  "source_type": "server",
  "source_key": "sk_live_xyz...",
  "config": {...},
  "is_active": true
}
```

---

## Segment Endpoints

### GET /segments

List segments.

```json
{
  "segments": [
    {
      "id": "uuid-...",
      "name": "High Value Customers",
      "segment_type": "dynamic",
      "status": "active",
      "profile_count": 1234,
      "last_computed_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 10
}
```

### POST /segments

Create segment.

#### Request

```json
{
  "name": "High Value Customers",
  "description": "Customers with 3+ purchases over $500",
  "segment_type": "dynamic",
  "rules": {
    "logic": "and",
    "conditions": [
      {
        "field": "lifecycle_stage",
        "operator": "equals",
        "value": "customer"
      },
      {
        "field": "total_purchases",
        "operator": "greater_than",
        "value": 3
      },
      {
        "field": "total_revenue",
        "operator": "greater_than",
        "value": 500
      }
    ]
  },
  "auto_refresh": true,
  "refresh_interval_hours": 24
}
```

### POST /segments/{id}/preview

Preview segment before saving.

#### Request

```json
{
  "rules": {
    "logic": "and",
    "conditions": [...]
  },
  "sample_size": 10
}
```

#### Response

```json
{
  "estimated_count": 1234,
  "sample_profiles": [
    {
      "id": "uuid-...",
      "email": "john@example.com",
      "total_purchases": 8,
      "total_revenue": 1250.00
    }
  ],
  "computation_time_ms": 245
}
```

### POST /segments/{id}/compute

Trigger segment recomputation.

```json
{
  "segment_id": "uuid-...",
  "status": "computing",
  "started_at": "2024-01-15T14:30:00Z"
}
```

### GET /segments/{id}/profiles

Get segment members.

```json
{
  "segment_id": "uuid-...",
  "profiles": [...],
  "total": 1234,
  "page": 1,
  "page_size": 20
}
```

---

## Identity Graph Endpoints

### GET /profiles/{id}/identity-graph

Get identity graph for a profile.

```json
{
  "profile_id": "uuid-...",
  "nodes": [
    {
      "id": "uuid-...",
      "identifier_type": "email",
      "identifier_hash": "sha256...",
      "is_primary": true,
      "is_canonical": true,
      "confidence_score": 1.0
    },
    {
      "id": "uuid-...",
      "identifier_type": "anonymous_id",
      "identifier_hash": "sha256...",
      "is_primary": false,
      "is_canonical": false,
      "confidence_score": 0.95
    }
  ],
  "edges": [
    {
      "source_id": "uuid-...",
      "target_id": "uuid-...",
      "link_type": "login",
      "confidence_score": 1.0,
      "created_at": "2024-01-05T12:00:00Z"
    }
  ]
}
```

### POST /profiles/merge

Merge two profiles.

#### Request

```json
{
  "surviving_profile_id": "uuid-1",
  "merged_profile_id": "uuid-2"
}
```

#### Response

```json
{
  "surviving_profile_id": "uuid-1",
  "merged_profile_id": "uuid-2",
  "merged_at": "2024-01-15T14:30:00Z",
  "events_transferred": 15,
  "identifiers_transferred": 2
}
```

### GET /profiles/{id}/merge-history

Get merge history for a profile.

```json
{
  "profile_id": "uuid-...",
  "merges": [
    {
      "id": "uuid-...",
      "merged_profile_id": "uuid-...",
      "merge_reason": "identity_match",
      "merged_event_count": 15,
      "merged_identifier_count": 2,
      "created_at": "2024-01-15T14:30:00Z"
    }
  ]
}
```

---

## Funnel Endpoints

### GET /funnels

List funnels.

### POST /funnels

Create funnel.

#### Request

```json
{
  "name": "Purchase Funnel",
  "steps": [
    {"step_name": "View Product", "event_name": "ProductView"},
    {"step_name": "Add to Cart", "event_name": "AddToCart"},
    {"step_name": "Checkout", "event_name": "BeginCheckout"},
    {"step_name": "Purchase", "event_name": "Purchase"}
  ],
  "conversion_window_days": 7
}
```

### POST /funnels/{id}/compute

Compute funnel metrics.

### GET /funnels/{id}/analysis

Get funnel analysis.

```json
{
  "funnel_id": "uuid-...",
  "name": "Purchase Funnel",
  "total_entered": 10000,
  "total_converted": 3000,
  "overall_conversion_rate": 30.0,
  "step_metrics": [
    {
      "step": 1,
      "name": "View Product",
      "count": 10000,
      "conversion_rate": 100.0,
      "drop_off_rate": 0.0
    },
    {
      "step": 2,
      "name": "Add to Cart",
      "count": 5500,
      "conversion_rate": 55.0,
      "drop_off_rate": 45.0
    },
    {
      "step": 3,
      "name": "Checkout",
      "count": 4000,
      "conversion_rate": 72.7,
      "drop_off_rate": 27.3
    },
    {
      "step": 4,
      "name": "Purchase",
      "count": 3000,
      "conversion_rate": 75.0,
      "drop_off_rate": 25.0
    }
  ],
  "avg_time_to_convert_hours": 55.2
}
```

---

## Computed Traits Endpoints

### GET /computed-traits

List computed trait definitions.

### POST /computed-traits

Create computed trait.

#### Request

```json
{
  "name": "total_purchases",
  "display_name": "Total Purchases",
  "trait_type": "count",
  "source_config": {
    "event_name": "Purchase",
    "time_window_days": 365
  },
  "output_type": "number",
  "default_value": "0"
}
```

### POST /computed-traits/rfm

Compute RFM scores.

#### Request

```json
{
  "recency_event": "Purchase",
  "frequency_event": "Purchase",
  "monetary_property": "total",
  "lookback_days": 365
}
```

#### Response

```json
{
  "profiles_analyzed": 5000,
  "computation_time_ms": 3500,
  "segment_distribution": {
    "Champions": 250,
    "Loyal": 800,
    "Potential Loyal": 1200,
    "New": 500,
    "At Risk": 400,
    "Hibernating": 1850
  }
}
```

---

## Webhook Endpoints

### GET /webhooks

List webhooks.

### POST /webhooks

Create webhook.

#### Request

```json
{
  "name": "Event Receiver",
  "url": "https://example.com/webhook",
  "event_types": ["event.received", "profile.created"],
  "max_retries": 3,
  "timeout_seconds": 30
}
```

### POST /webhooks/{id}/test

Test webhook endpoint.

```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 125
}
```

---

## Health & Statistics

### GET /health

CDP health check.

```json
{
  "status": "healthy",
  "module": "CDP",
  "version": "1.0.0"
}
```

### GET /statistics

CDP usage statistics.

```json
{
  "profiles_total": 125000,
  "profiles_by_stage": {
    "anonymous": 45000,
    "known": 35000,
    "customer": 40000,
    "churned": 5000
  },
  "events_total": 2500000,
  "events_today": 15000,
  "segments_active": 15,
  "sources_active": 4
}
```

### GET /events/anomalies

Detect event anomalies.

```json
{
  "anomalies": [
    {
      "source_name": "Website Pixel",
      "metric": "event_count",
      "zscore": 3.5,
      "severity": "high",
      "current_value": 5000,
      "baseline_mean": 2000,
      "direction": "high",
      "pct_change": 150.0
    }
  ],
  "anomaly_count": 1,
  "has_critical": false,
  "has_high": true
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "PROFILE_NOT_FOUND",
    "message": "Profile with ID uuid-... not found",
    "details": {
      "profile_id": "uuid-..."
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `PROFILE_NOT_FOUND` | 404 | Profile ID not found |
| `SEGMENT_NOT_FOUND` | 404 | Segment ID not found |
| `INVALID_IDENTIFIER` | 400 | Identifier format invalid |
| `DUPLICATE_EVENT` | 200 | Idempotency key already used |
| `SOURCE_INACTIVE` | 403 | Source key is deactivated |

---

## Rate Limits

| Endpoint | Limit | Notes |
|----------|-------|-------|
| POST /events | 100/min | Per tenant |
| GET /profiles/* | 300/min | Per tenant |
| POST /sources | 30/min | Per tenant |
| POST /segments/* | 30/min | Per tenant |
