# Stratum CDP

**Customer Data Platform for First-Party Data Collection & Identity Resolution**

---

## Overview

Stratum CDP enables marketing teams to:
- **Collect** events from web, server, and CRM sources
- **Resolve** customer identities across devices and touchpoints
- **Build** unified customer profiles with complete journey data
- **Trust** data quality through EMQ (Event Match Quality) scoring

CDP integrates with Stratum's Trust Engine to ensure automation only runs when signal health is high.

---

## Quick Start

### 1. Create a Data Source

```bash
curl -X POST https://api.stratum.ai/api/v1/cdp/sources \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Website Pixel",
    "source_type": "website"
  }'
```

Response includes `source_key` for authentication.

### 2. Send Events

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
        "page_url": "/products/sofa"
      }
    }]
  }'
```

### 3. Lookup Profile

```bash
curl "https://api.stratum.ai/api/v1/cdp/profiles?identifier_type=email&identifier_value=user@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/cdp/events` | Ingest events (batch) |
| GET | `/api/v1/cdp/profiles/{id}` | Get profile by UUID |
| GET | `/api/v1/cdp/profiles` | Lookup by identifier |
| GET | `/api/v1/cdp/sources` | List data sources |
| POST | `/api/v1/cdp/sources` | Create data source |
| GET | `/api/v1/cdp/health` | Health check |

### Authentication

All endpoints require JWT Bearer token:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## Data Model

### Profiles
Unified customer records with:
- Identity linkage (email, phone, device)
- Lifecycle stage (anonymous → known → customer)
- Aggregated metrics (events, sessions, purchases, revenue)

### Identifiers
Supported types:
- `email` - Normalized, hashed
- `phone` - E.164 format, hashed
- `device_id` - Device fingerprint
- `anonymous_id` - Cookie/session ID
- `external_id` - CRM/external system ID

### Events
Append-only event store:
- Standard events: PageView, Purchase, SignUp, etc.
- Custom events: Any name in PascalCase
- EMQ score per event (0-100)

---

## EMQ (Event Match Quality)

Each event receives a quality score:

| Score | Quality | Automation |
|-------|---------|------------|
| 80-100 | Excellent | Full |
| 60-79 | Good | Partial |
| 40-59 | Fair | Limited |
| 0-39 | Poor | Manual |

Scoring factors:
- Identifier quality (40%)
- Data completeness (25%)
- Timeliness (20%)
- Context richness (15%)

---

## Documentation

| Document | Description |
|----------|-------------|
| [SCHEMA.md](./SCHEMA.md) | Database schema design |
| [EVENT_SPEC_MINIMAL.md](./EVENT_SPEC_MINIMAL.md) | Event JSON schema + examples |
| [BUILD_PLAN_4W.md](./BUILD_PLAN_4W.md) | Implementation timeline |
| [PITCH_DECK.md](./PITCH_DECK.md) | Sales presentation |
| [DISCOVERY.md](./DISCOVERY.md) | Repository patterns |

---

## Files

### Backend

```
backend/
├── app/
│   ├── models/cdp.py              # SQLAlchemy models
│   ├── schemas/cdp.py             # Pydantic schemas
│   └── api/v1/endpoints/cdp.py    # API endpoints
└── migrations/versions/
    └── 20260113_000000_026_add_cdp_tables.py
```

### Frontend

```
frontend/src/
└── components/widgets/
    └── CDPROICalculator.tsx       # ROI calculator widget
```

---

## Privacy & Security

- **PII Hashing**: Email/phone hashed (SHA256) at ingestion
- **Consent Management**: Track consent per user per type
- **Multi-Tenant**: Row-level security with tenant_id
- **Data Retention**: Events: 13 months, Profiles: permanent

---

## Development

### Run Migrations

```bash
cd backend
alembic upgrade head
```

### Run Tests

```bash
pytest tests/unit/test_cdp.py -v
pytest tests/integration/test_cdp.py -v
```

### API Docs

When running locally:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Support

- Documentation: https://docs.stratum.ai/cdp
- API Status: https://status.stratum.ai
- Support: support@stratum.ai
