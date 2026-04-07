# Stratum CDP - Event Specification

> Minimal event spec for CDP event ingestion

---

## Quick Start

### Ingest a Single Event

```bash
curl -X POST https://api.stratum.ai/api/v1/cdp/events \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "event_name": "PageView",
      "event_time": "2026-01-13T15:30:00Z",
      "identifiers": [
        {"type": "anonymous_id", "value": "anon_abc123"}
      ],
      "properties": {
        "page_url": "/products/sofa",
        "page_title": "Milano Sofa"
      }
    }]
  }'
```

---

## Event Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_name` | string | Event name (e.g., `PageView`, `Purchase`) |
| `event_time` | ISO8601 | When the event occurred |
| `identifiers` | array | At least one identifier required |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `idempotency_key` | string | Unique key for deduplication (max 128 chars) |
| `properties` | object | Event-specific data |
| `context` | object | Device, geo, campaign info |
| `consent` | object | Privacy consent flags |

---

## Identifier Types

| Type | Format | Example |
|------|--------|---------|
| `email` | Valid email | `user@example.com` |
| `phone` | E.164 format | `+971501234567` |
| `device_id` | String | `ABC123-DEF456` |
| `anonymous_id` | String | `anon_abc123` |
| `external_id` | String | `CRM-12345` |

### Identifier Normalization

- **Email**: Lowercased, trimmed
- **Phone**: Non-digits removed, `+` prefix ensured
- **Others**: Trimmed only

### Identifier Hashing

All identifiers are hashed using SHA256 before storage:
```
SHA256(normalized_value) → 64-char hex string
```

---

## Standard Event Names

### E-commerce Events

| Event | When to Send | Key Properties |
|-------|--------------|----------------|
| `PageView` | Page load | `page_url`, `page_title`, `referrer` |
| `ProductViewed` | Product page | `product_id`, `product_name`, `price` |
| `AddToCart` | Add to cart | `product_id`, `quantity`, `price` |
| `RemoveFromCart` | Remove from cart | `product_id`, `quantity` |
| `CheckoutStarted` | Checkout begins | `cart_total`, `item_count` |
| `Purchase` | Order complete | `order_id`, `total`, `currency`, `items` |

### Engagement Events

| Event | When to Send | Key Properties |
|-------|--------------|----------------|
| `SignUp` | User registers | `method` (email, google, etc.) |
| `Login` | User logs in | `method` |
| `FormSubmitted` | Form submission | `form_id`, `form_name` |
| `NewsletterSubscribed` | Newsletter signup | `list_id` |

### Custom Events

Any `event_name` is accepted. Use `PascalCase` naming:
- `WebinarRegistered`
- `TrialStarted`
- `FeedbackSubmitted`

---

## Full Event Example

```json
{
  "events": [
    {
      "event_name": "Purchase",
      "event_time": "2026-01-13T15:30:00Z",
      "idempotency_key": "order_12345_1705159800",

      "identifiers": [
        {"type": "email", "value": "ahmed@example.com"},
        {"type": "anonymous_id", "value": "anon_xyz789"}
      ],

      "properties": {
        "order_id": "ORD-12345",
        "total": 2499.00,
        "currency": "AED",
        "items": [
          {
            "product_id": "SKU-001",
            "name": "Milano Sofa",
            "price": 2499.00,
            "quantity": 1
          }
        ],
        "payment_method": "credit_card",
        "coupon_code": "SPRING20"
      },

      "context": {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)...",
        "ip": "185.23.45.67",
        "locale": "ar-AE",
        "timezone": "Asia/Dubai",
        "screen": {"width": 390, "height": 844},
        "campaign": {
          "source": "google",
          "medium": "cpc",
          "campaign": "spring_sale_2026",
          "content": "sofa_ad_v2"
        }
      },

      "consent": {
        "analytics": true,
        "ads": true,
        "email": true
      }
    }
  ]
}
```

---

## API Response

### Success Response (201 Created)

```json
{
  "accepted": 1,
  "rejected": 0,
  "duplicates": 0,
  "results": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "accepted",
      "profile_id": "661e8400-e29b-41d4-a716-446655440001"
    }
  ]
}
```

### Error Response (400 Bad Request)

```json
{
  "accepted": 0,
  "rejected": 1,
  "duplicates": 0,
  "results": [
    {
      "status": "rejected",
      "error": "Invalid identifier type. Allowed: {email, phone, device_id, anonymous_id, external_id}"
    }
  ]
}
```

### Duplicate Response

```json
{
  "accepted": 0,
  "rejected": 0,
  "duplicates": 1,
  "results": [
    {
      "status": "duplicate",
      "error": "Event with same idempotency_key already exists"
    }
  ]
}
```

---

## Batch Ingestion

Send up to 1000 events per request:

```bash
curl -X POST https://api.stratum.ai/api/v1/cdp/events \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_name": "PageView", "event_time": "2026-01-13T15:30:00Z", "identifiers": [{"type": "anonymous_id", "value": "a1"}]},
      {"event_name": "PageView", "event_time": "2026-01-13T15:31:00Z", "identifiers": [{"type": "anonymous_id", "value": "a2"}]},
      {"event_name": "PageView", "event_time": "2026-01-13T15:32:00Z", "identifiers": [{"type": "anonymous_id", "value": "a3"}]}
    ]
  }'
```

---

## Profile Lookup

### By Profile ID

```bash
curl https://api.stratum.ai/api/v1/cdp/profiles/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### By Identifier

```bash
curl "https://api.stratum.ai/api/v1/cdp/profiles?identifier_type=email&identifier_value=ahmed@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## EMQ (Event Match Quality)

Each event receives an EMQ score (0-100) based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Identifier Quality | 40% | Has email or phone identifier |
| Data Completeness | 25% | Properties object not empty |
| Timeliness | 20% | Event time within 5 min of received |
| Context Richness | 15% | Has campaign, user_agent, IP |

### Score Interpretation

| Score | Quality | Action |
|-------|---------|--------|
| 80-100 | Excellent | Full trust, all automation enabled |
| 60-79 | Good | Minor gaps, most automation enabled |
| 40-59 | Fair | Some gaps, reduced automation |
| 0-39 | Poor | Significant gaps, manual review |

---

## Deduplication

### Using idempotency_key

Recommended format: `{source}_{event_name}_{user_id}_{timestamp}`

```json
{
  "event_name": "Purchase",
  "idempotency_key": "web_Purchase_user123_1705159800",
  ...
}
```

- TTL: 24 hours
- Duplicate events return `status: "duplicate"`
- No database write for duplicates

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request body or validation error |
| 401 | Missing or invalid JWT token |
| 403 | Access denied (wrong tenant) |
| 404 | Profile not found (lookup endpoints) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /events | 1000 requests/minute |
| GET /profiles | 500 requests/minute |
| GET /sources | 100 requests/minute |

---

## Best Practices

1. **Always include `idempotency_key`** for critical events (Purchase, SignUp)
2. **Use `anonymous_id`** for anonymous visitors, upgrade to email/phone when collected
3. **Include `context.campaign`** for attribution tracking
4. **Send events in real-time** for best EMQ scores
5. **Batch events** for bulk imports (max 1000 per request)
6. **Handle rate limits** with exponential backoff
