# Stratum AI — API Explorer & Integration Guide

**Base URL:** `https://api.stratumai.app`  
**API Version:** v1  
**Protocol:** HTTPS / WSS (WebSocket)

---

## Authentication

All API requests (except public endpoints) require a valid JWT token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <token>" \
     https://api.stratumai.app/api/v1/campaigns
```

### Public Endpoints (No Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health check |
| `GET /health/ready` | Readiness probe |
| `GET /health/live` | Liveness probe |
| `GET /public/demo-metrics` | Aggregate platform metrics for landing page |
| `GET /public/events/stream` | Public Server-Sent Events stream |

### Authentication Flow

```
1. POST /api/v1/auth/register      → Create account
2. POST /api/v1/auth/login       → Receive JWT token
3. Include token in all requests  → Authorization: Bearer <token>
4. POST /api/v1/auth/mfa/verify  → Complete MFA if enabled
```

---

## Interactive Documentation

| Format | URL | Access |
|--------|-----|--------|
| Swagger UI | `https://api.stratumai.app/docs` | Production: `?api_key=$DOCS_API_KEY` |
| ReDoc | `https://api.stratumai.app/redoc` | Production: `?api_key=$DOCS_API_KEY` |
| OpenAPI JSON | `https://api.stratumai.app/openapi.json` | Production: `?api_key=$DOCS_API_KEY` |

For local development, no API key is required.

---

## Endpoint Categories

### Campaigns

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/campaigns` | List campaigns (paginated, filtered) |
| POST | `/api/v1/campaigns` | Create new campaign |
| GET | `/api/v1/campaigns/{id}` | Get campaign details |
| PUT | `/api/v1/campaigns/{id}` | Update campaign |
| DELETE | `/api/v1/campaigns/{id}` | Soft-delete campaign |
| GET | `/api/v1/campaigns/{id}/metrics` | Get time-series metrics |

### Trust Engine

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/signal-health` | Current signal health score |
| GET | `/api/v1/analytics/trust-gate` | Trust gate evaluation status |
| GET | `/api/v1/analytics/emq` | Event Match Quality score |
| POST | `/api/v1/analytics/trust-gate/evaluate` | Run manual evaluation |

### CDP (Customer Data Platform)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/cdp/events` | Ingest events (batch up to 1000) |
| GET | `/api/v1/cdp/profiles/{uuid}` | Get unified profile |
| GET | `/api/v1/cdp/profiles` | Lookup by identifier |
| GET | `/api/v1/cdp/segments` | List segments |
| POST | `/api/v1/cdp/segments` | Create segment |
| GET | `/api/v1/cdp/health` | CDP module health |

### Autopilot

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/autopilot/status` | Current autopilot status |
| POST | `/api/v1/autopilot/mode` | Change enforcement mode |
| GET | `/api/v1/autopilot/actions` | Pending action queue |
| POST | `/api/v1/autopilot/actions/{id}/approve` | Approve pending action |

### Real-Time Streaming

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WebSocket | `wss://api.stratumai.app/ws?token=<jwt>` | Bi-directional real-time updates |
| SSE | `GET /api/v1/events/stream` | Server-Sent Events (tenant-scoped) |
| SSE | `GET /public/events/stream` | Public SSE (landing page) |

---

## Rate Limits

| Tier | Requests/Min | Burst |
|------|-------------|-------|
| Default | 100 | 20 |
| Enterprise | 500 | 100 |

Rate limit headers are included in all responses:
- `X-Rate-Limit-Remaining`: Requests remaining in window
- `X-Rate-Limit-Reset`: Unix timestamp when limit resets

---

## WebSocket Message Types

```json
// EMQ Score Update
{
  "type": "emq_update",
  "tenant_id": 1,
  "data": { "emq_score": 92.5, "previous": 89.1 }
}

// Trust Gate Change
{
  "type": "trust_gate_change",
  "tenant_id": 1,
  "data": { "gate_status": "PASS", "signal_health": 94.2 }
}

// Campaign Performance Alert
{
  "type": "campaign_alert",
  "tenant_id": 1,
  "data": { "campaign_id": 123, "alert_type": "roas_drop", "value": 1.2 }
}
```

---

## SDK Examples

### Python

```python
import requests

API_URL = "https://api.stratumai.app/api/v1"
TOKEN = "your-jwt-token"

headers = {"Authorization": f"Bearer {TOKEN}"}

# List campaigns
response = requests.get(f"{API_URL}/campaigns", headers=headers)
campaigns = response.json()["data"]["items"]

# Get signal health
health = requests.get(f"{API_URL}/analytics/signal-health", headers=headers).json()
print(f"Trust Score: {health['data']['composite_score']}%")
```

### JavaScript

```javascript
const API_URL = 'https://api.stratumai.app/api/v1';
const TOKEN = 'your-jwt-token';

// Fetch campaigns
const campaigns = await fetch(`${API_URL}/campaigns`, {
  headers: { 'Authorization': `Bearer ${TOKEN}` }
}).then(r => r.json());

// Connect to WebSocket
const ws = new WebSocket(`wss://api.stratumai.app/ws?token=${TOKEN}`);
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Real-time update:', msg);
};
```

### cURL

```bash
# Health check
curl https://api.stratumai.app/health

# List campaigns
curl -H "Authorization: Bearer $TOKEN" \
  https://api.stratumai.app/api/v1/campaigns?page=1&page_size=20

# Ingest CDP events
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"events": [...]}' \
  https://api.stratumai.app/api/v1/cdp/events
```

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `TENANT_REQUIRED` | 401 | Missing or invalid tenant context |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CAMPAIGN_NOT_FOUND` | 404 | Campaign ID does not exist |
| `TRUST_GATE_BLOCKED` | 403 | Action blocked by trust gate |
| `INVALID_MFA_CODE` | 401 | MFA verification failed |

---

## Changelog

- **v1.1.0 (2026-04-27)**: Added public demo metrics, enabled API docs with access control, optimized campaign queries with database indexes, connected real-time SSE to landing page.
- **v1.0.0 (2026-04-20)**: Initial production release with Trust-Gated Autopilot, CDP, multi-platform integrations.
