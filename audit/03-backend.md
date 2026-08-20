# Phase 3 — Backend

## 1. Application Entry

Single entry: `backend/app/main.py` — lifespan, Sentry, ML auto-train, middleware stack, health, metrics, SSE, WebSocket.

Production docs gate:

```343:345:backend/app/main.py
            # Skip if DOCS_API_KEY not configured (fallback to open)
            if not DOCS_API_KEY:
                return
```

## 2. Configuration

Pydantic Settings (`backend/app/core/config.py`):

- Auto-generated dev secrets (`config.py:22-24`) — **blocked in prod/staging** (`config.py:529-542`)
- `use_mock_ad_data` raises in prod if true (`config.py:562-565`)
- CORS localhost rejected in prod (`config.py:567-577`)
- Pool sizing documented for multi-process deploys (`config.py:60-69`)

**Conflict:** `docker-compose.yml` sets `USE_MOCK_AD_DATA=${USE_MOCK_AD_DATA:-true}` (`docker-compose.yml:103`) while `config.py` default is `False` (`config.py:122-125`) and `docker-compose.prod.yml` forces `false`.

## 3. Security Module

`backend/app/core/security.py`:

- bcrypt password hashing with 72-byte truncation (`security.py:60-72`)
- JWT access + refresh with `jti` for revocation (`security.py:134-144`)
- PII Fernet encryption with per-tenant DEK dual-read (`security.py:218-270`)
- Redis-backed token blacklist + per-user revocation cutoff — **fail closed** on Redis error in middleware (`tenant.py:96-112`, `security.py:487-490`)
- Login rate limit: 5 attempts / 15 min lockout (`security.py:497-501`)

## 4. Middleware

| Middleware | File | Notes |
|------------|------|-------|
| Tenant | `middleware/tenant.py` | JWT type=access, revocation, public list |
| CSRF | `middleware/csrf.py` | State-changing requests |
| Rate limit | `middleware/rate_limit.py` | Configurable RPM |
| Audit | `middleware/audit.py` | Mutations |
| Security headers | `middleware/security.py` | CSP/HSTS in prod |
| Request logging | `middleware/request_logging.py` | structlog |

## 5. Workers

Celery app in `app/workers/celery_app.py` (omitted from coverage). Beat tasks gated by feature flags (`config.py:432-457`).

Worker receives same `SECRET_KEY`, `JWT_SECRET_KEY`, `PII_ENCRYPTION_KEY` as API (`docker-compose.yml:224-229`).

## 6. Notable Endpoints

| Module | Risk note |
|--------|-----------|
| `qa_fixes.py` | Applies EMQ fixes; tenant check via `request.state.tenant_id` only (`qa_fixes.py:76-77`) |
| `developer.py` | Dev portal / webhook mgmt — tenant-scoped |
| `stripe_webhook.py` | Signature verify + Redis idempotency |
| `superadmin.py` | Requires `require_super_admin` at router level (`api/v1/__init__.py:79`) |

## 7. Backend Findings

| ID | Sev | Title |
|----|-----|-------|
| F-001 | P1 | OpenAPI/docs unprotected when DOCS_API_KEY unset in production |
| F-002 | P1 | /metrics publicly readable when METRICS_API_KEY unset |
| F-003 | P1 | WebSocket auth token accepted via query string |
| F-004 | P1 | Dev compose defaults USE_MOCK_AD_DATA=true |
| F-009 | P2 | Stripe webhook idempotency fails open if Redis unavailable |
| F-010 | P2 | Conflicting .env.example templates |
| F-015 | P3 | main.py excluded from coverage |

## 8. Positive Controls

- Production safety validator rejects autogen secrets (`config.py:526-587`)
- Tenant middleware rejects refresh tokens on API routes (`tenant.py:88-93`)
- Revocation check fails closed → 503 (`tenant.py:96-112`)
- Stripe `construct_event` required (`stripe_webhook.py:150-161`)
- Structured JSON logging + Sentry PII scrubbing (`main.py:124-141`)

## 9. Searches Run

```
grep -i "password|secret|bypass" backend/app/**/*.py  → reviewed top 60 hits, no hardcoded prod secrets
glob backend/app/api/v1/endpoints/*.py                → 68 files
read qa_fixes.py, developer.py, stripe_webhook.py, config.py, security.py, tenant.py, main.py
```

## 10. Proposed Fix (DO NOT APPLY)

**F-001** — Fail closed when `DOCS_API_KEY` empty in production:

```python
# backend/app/main.py — inside verify_docs_access, replace lines 343-345
if not DOCS_API_KEY:
    raise HTTPException(status_code=503, detail="Documentation disabled in production")
```
