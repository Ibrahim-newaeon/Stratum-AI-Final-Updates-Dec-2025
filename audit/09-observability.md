# Phase 9 — Observability

## 1. Logging

- **Library:** structlog (`requirements.txt:72`, `main.py:18`)
- **Format:** JSON default (`config.py:250`, `docker-compose.yml:113`)
- **Request completion:** `request_completed` with method, path, status, duration (`main.py:437-443`)
- **PII in logs:** masked via `mask_email`, `mask_phone` in security module

## 2. Error Tracking

Sentry initialized for production/staging when `SENTRY_DSN` set (`main.py:117-163`):

- `send_default_pii=False`
- `before_send` redacts password/token/secret fields (`main.py:124-141`)
- Integrations: FastAPI, SQLAlchemy, Celery, Redis

Frontend: `@sentry/react` in `main.tsx`, `lib/sentry.ts`, `ErrorBoundary.tsx`.

## 3. Metrics

| Type | Endpoint / mechanism |
|------|---------------------|
| HTTP latency/size | prometheus-fastapi-instrumentator (`main.py:311-317`) |
| Domain metrics | `app.core.metrics` (EMQ, trust gate, autopilot, Celery) |
| Exposition | GET `/metrics` (`main.py:797-814`) |
| Worker liveness | Redis heartbeat refreshed at scrape (`main.py:806-810`) |

Gate: `METRICS_API_KEY` bearer optional (`main.py:54-58`, `795-805`).

Prometheus config referenced: `infrastructure/prometheus/prometheus.yml` (comment `main.py:790`).

## 4. Health Checks

| Path | Purpose |
|------|---------|
| `/health` | Liveness (curl in compose) |
| `/health/ready` | DB + Redis readiness (`main.py:62-91`) |
| `/health/live` | Listed public (`tenant.py:28`) |

## 5. Alerting

```261:268:backend/app/core/config.py
    alert_webhook_url: Optional[str] = Field(
        default=None,
        description="Incoming webhook for critical (P0) operational alerts",
    )
```

Wired for monitoring task — **UNKNOWN — not present in available evidence** whether prod sets this URL.

## 6. Observability Findings

| ID | Sev | Title |
|----|-----|-------|
| F-002 | P1 | Unauthenticated /metrics when key unset |
| — | P2 | No evidence of centralized log aggregation config in repo |

## 7. Positive Controls

- Structured JSON logs suitable for Loki/Datadog ingestion
- Request ID propagation (`main.py:426-433`)
- Sentry PII scrubbing hook
- Readiness excludes non-critical deps (SendGrid) (`main.py:66-69`)
- Flower behind basic auth + monitoring profile (`docker-compose.yml:408,426-427`)

## 8. Observability Checklist (Production)

- [ ] Set `SENTRY_DSN`, `SENTRY_RELEASE` to git SHA
- [ ] Set `METRICS_API_KEY`; restrict `/metrics` at ingress
- [ ] Set `ALERT_WEBHOOK_URL` for P0 pipeline failures
- [ ] Enable `docker-compose.observability.yml` or managed equivalent
- [ ] Verify `LOG_FORMAT=json` in prod compose

## 9. Searches Run

```
grep "sentry|structlog|prometheus" backend/app/main.py     → multiple hits
grep "METRICS_API_KEY|ENABLE_METRICS" docker-compose.yml   → 96-99
glob infrastructure/prometheus/*                           → referenced in comments
grep "alert_webhook" backend/                              → config.py:266
```

## 10. Missing Data

- Actual scrape interval, retention, dashboard URLs: **UNKNOWN**
- Production Sentry sample rates impact on cost: needs traffic data **UNKNOWN**
