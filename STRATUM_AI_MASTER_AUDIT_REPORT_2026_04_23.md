# STRATUM AI — MASTER TECHNICAL AUDIT REPORT
**Audit Date:** April 23, 2026  
**Auditor:** Claude Code Desktop (Full-Stack Systems Audit)  
**Commit Range:** `1faa60b` (HEAD) — `2be4326` (recent)  
**Environment Audited:** Local Docker + Static Code Analysis  
**Total Files Scanned:** 400+ backend modules, 200+ frontend components, 30+ infrastructure configs  

---

## EXECUTIVE SUMMARY

Stratum AI is a sophisticated multi-tenant marketing intelligence platform with a strong architectural foundation. However, this audit uncovered **significant security vulnerabilities, data integrity risks, and production reliability gaps** that require immediate attention before the platform can safely scale to enterprise tenants.

### Key Metrics

| Category | Total | Critical (P0) | High (P1) | Medium (P2) | Low (P3) |
|----------|-------|---------------|-----------|-------------|----------|
| Backend | 52 | 8 | 16 | 19 | 9 |
| API Contract & Auth | 35 | 7 | 15 | 9 | 4 |
| Frontend | 45 | 21 | 8 | 12 | 4 |
| Database & Migrations | 43 | 6 | 17 | 19 | 3 |
| Infrastructure & DevOps | 47 | 4 | 11 | 22 | 10 |
| Security Deep Dive | 16 | 5 | 4 | 5 | 2 |
| Performance | 10 | 0 | 4 | 5 | 1 |
| **TOTAL UNIQUE** | **~180** | **~28** | **~52** | **~68** | **~30** |

### Overall System Health: ⚠️ DEGRADED — CRITICAL ISSUES REQUIRE IMMEDIATE REMEDIATION

The platform **must not** be deployed to new enterprise tenants until P0 issues are resolved. The most severe risks are:

1. **Authentication bypass** on Meta CAPI and EMQ v2 endpoints
2. **Cross-tenant data leakage** via middleware spoofing and missing tenant filters
3. **Hardcoded credentials** in seed scripts and Docker startup
4. **Double-commit SQLAlchemy anti-pattern** causing transaction corruption
5. **Refresh token reuse** enabling indefinite session hijacking

---

## ISSUE TRACKING MATRIX

| ID | Severity | Layer | Component | Status |
|----|----------|-------|-----------|--------|
| BE-001 | CRITICAL | Backend | `app/middleware/tenant.py` | OPEN |
| BE-002 | CRITICAL | Backend | `app/api/v1/endpoints/capi.py` | OPEN |
| BE-003 | CRITICAL | Backend | `app/db/session.py` | OPEN |
| BE-004 | CRITICAL | Backend | `app/api/v1/endpoints/stripe_webhook.py` | OPEN |
| BE-005 | CRITICAL | Backend | `app/workers/tasks/sync.py` | OPEN |
| BE-006 | CRITICAL | Backend | `app/api/v1/endpoints/insights.py` | OPEN |
| BE-007 | CRITICAL | Backend | `scripts/seed_superadmin.py` | OPEN |
| BE-008 | CRITICAL | Backend | `scripts/seed-data.sql` | OPEN |
| API-001 | CRITICAL | API | `meta_capi.py` | OPEN |
| API-002 | CRITICAL | API | `emq_v2.py` | OPEN |
| API-003 | CRITICAL | API | `capi.py` | OPEN |
| API-004 | CRITICAL | API | `tenants.py` | OPEN |
| API-005 | CRITICAL | API | `auth.py` (refresh/logout) | OPEN |
| SEC-001 | CRITICAL | Security | `requirements.txt` (python-jose) | OPEN |
| SEC-002 | CRITICAL | Security | `.env.production.template` | OPEN |
| DB-001 | CRITICAL | Database | `migrations/versions/020_*` | OPEN |
| DB-002 | CRITICAL | Database | `migrations/versions/012_*` (duplicate) | OPEN |
| DB-003 | CRITICAL | Database | `app/db/base.py` (StrEnumType) | OPEN |
| DB-004 | CRITICAL | Database | All `app/models/*` (soft delete) | OPEN |
| INF-001 | CRITICAL | Infra | `Dockerfile.frontend` | OPEN |
| INF-002 | CRITICAL | Infra | `docker-compose.yml` & editions | OPEN |
| INF-003 | CRITICAL | Infra | `scripts/load_datasets.py` | OPEN |
| INF-004 | CRITICAL | Infra | `backend/start.sh` | OPEN |
| FE-001 | CRITICAL | Frontend | `src/api/insights.ts` | OPEN |
| FE-002 | CRITICAL | Frontend | `src/api/autopilot.ts` | OPEN |
| FE-003 | CRITICAL | Frontend | `src/api/trustLayer.ts` | OPEN |
| FE-004 | CRITICAL | Frontend | `src/api/featureFlags.ts` | OPEN |
| FE-005 | CRITICAL | Frontend | `src/api/dashboard.ts` | OPEN |
| FE-006 | CRITICAL | Frontend | `src/api/campaigns.ts` | OPEN |
| FE-007..021 | CRITICAL | Frontend | Missing API clients (15 files) | OPEN |

*(Full matrix continues in appendix)*

---

## BACKEND AUDIT FINDINGS

---

### Issue BE-001: X-Tenant-ID Header Spoofing in TenantMiddleware
**Severity:** CRITICAL  
**Component Affected:** `backend/app/middleware/tenant.py` (lines 166-172)  
**Problem Description:** The `_extract_tenant_id()` function trusts the `X-Tenant-ID` header whenever **any** `Authorization` header is present — even if the token is completely invalid. An attacker can send `Authorization: Bearer invalid` + `X-Tenant-ID: 123` and the middleware will set `request.state.tenant_id = 123`, bypassing authentication entirely for endpoints that rely solely on middleware tenant extraction.  
**Root Cause:** The code checks `auth_header` presence but does not validate the JWT before trusting `X-Tenant-ID`.  
**Recommended Solution:** Validate the JWT and extract the tenant claim from the token before accepting `X-Tenant-ID`, or reject mismatched headers.  
**Implementation Steps:**
1. In `_extract_tenant_id()`, decode and verify the JWT before trusting `X-Tenant-ID`.
2. Compare `X-Tenant-ID` against the `tenant_id` claim in the validated token payload.
3. If mismatch or invalid token, raise `HTTPException(401)`.
**Code Example:**
```python
# BEFORE (vulnerable)
if tenant_header and auth_header:
    return int(tenant_header)

# AFTER (secure)
if tenant_header and auth_header:
    try:
        payload = decode_access_token(auth_header.replace("Bearer ", ""))
        token_tenant = payload.get("tenant_id")
        if token_tenant and int(tenant_header) == token_tenant:
            return int(tenant_header)
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="Invalid tenant context")
```
**Verification:** Send `curl -H "Authorization: Bearer invalid" -H "X-Tenant-ID: 1" http://localhost:8000/api/v1/campaigns`. Should return 401, not 200.

---

### Issue BE-002: CAPI Service Global State Leakage (Cross-Tenant Memory)
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/capi.py` (lines 26-33)  
**Problem Description:** `_capi_services: Dict[int, CAPIService]` is a module-level global dictionary that caches service instances per tenant. There is **no eviction** — this grows unbounded and will eventually OOM. More critically, if `CAPIService` holds any state (credentials, buffers, connections), it can leak across requests or tenants.  
**Root Cause:** Global mutable state without TTL, cleanup, or bounded size.  
**Recommended Solution:** Replace the unbounded dict with an LRU cache or instantiate per-request.  
**Implementation Steps:**
1. Replace global dict with `functools.lru_cache(maxsize=128)`.
2. Ensure `CAPIService` is stateless or properly isolates tenant credentials.
3. Add memory monitoring alert for CAPI service cache size.
**Code Example:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_capi_service(tenant_id: int) -> CAPIService:
    return CAPIService(tenant_id=tenant_id)
```

---

### Issue BE-003: Widespread Double-Commit Anti-Pattern
**Severity:** CRITICAL  
**Component Affected:** `backend/app/db/session.py` (lines 90-98) + ~40 endpoint files  
**Problem Description:** `get_async_session()` **auto-commits** on successful generator exit (`await session.commit()` at line 93). However, nearly every endpoint also calls `await db.commit()` explicitly. This causes **two commits per request**. In SQLAlchemy 2.0 async, this is fragile — if the explicit commit succeeds but subsequent lazy-loaded operations occur before dependency cleanup, the second commit can fail with "Transaction is closed" or silently corrupt session state.  
**Root Cause:** FastAPI dependency auto-commits while endpoints also manage transactions manually.  
**Recommended Solution:** Remove auto-commit from `get_async_session()` and let endpoints own transaction boundaries.  
**Implementation Steps:**
1. Remove `await session.commit()` from `get_async_session()`.
2. Keep `await session.rollback()` in the except block.
3. Audit all endpoints to ensure they explicitly commit where needed.
**Code Example:**
```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```
**Verification:** Add SQLAlchemy event listeners or query `pg_stat_statements` to confirm single commit per request.

---

### Issue BE-004: Stripe Webhook Double Commit with Context Manager
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/stripe_webhook.py` (lines 130-156)  
**Problem Description:** The webhook handler uses `async with async_session_maker() as db` (which **auto-commits** on success), then explicitly calls `await db.commit()` at line 156. This is a guaranteed double commit. If an exception occurs after the explicit commit but before the context exits, the context manager will attempt to commit again.  
**Root Cause:** `async_session_context()` auto-commits just like `get_async_session()`.  
**Recommended Solution:** Remove explicit `await db.commit()` and `await db.rollback()` from the webhook handler; let the context manager handle it.  
**Implementation Steps:**
1. Remove lines 156 and 161 (explicit commit/rollback).
2. Ensure `async_session_context()` handles commit/rollback correctly.
3. Add unit test for webhook idempotency.

---

### Issue BE-005: Celery Task Creates New Event Loop Per Execution
**Severity:** CRITICAL  
**Component Affected:** `backend/app/workers/tasks/sync.py` (lines 27-34)  
**Problem Description:** `_run_async()` creates a **brand new asyncio event loop** for every Celery task invocation, runs the coroutine, then closes the loop. In a high-throughput Celery worker, this causes severe resource leaks (file descriptors, threads) and can crash workers. SQLAlchemy async sessions require an existing loop; creating/closing loops repeatedly is undefined behavior.  
**Root Cause:** Running async code from sync Celery tasks incorrectly.  
**Recommended Solution:** Use `celery-aio-pool` or delegate async tasks to a dedicated async worker.  
**Implementation Steps:**
1. Install `celery-aio-pool`.
2. Configure Celery to use `aio` pool for async tasks.
3. Remove `_run_async()` helper and define tasks as `async def` with proper decorator.
**Code Example:**
```python
# Use asyncio.run as intermediate fix
def sync_campaign_data(...):
    asyncio.run(_do_sync(...))

# Proper fix: celery-aio-pool
from celery_aio_pool import AsyncIOPool
app = Celery(..., pool=AsyncIOPool)
```

---

### Issue BE-006: Insights Endpoints Load ALL Campaigns Into Memory
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/insights.py` (lines 33-69, 72-114, 360-370, 480-490)  
**Problem Description:** `get_entity_metrics`, `get_baseline_metrics`, `get_anomalies`, and `get_kpis` all execute `select(Campaign).where(...)` with **no pagination, no limit, no offset**. For a tenant with 10,000+ campaigns, this loads the entire table into Python memory, computes aggregates in Python, and can OOM the worker.  
**Root Cause:** ORM full-table fetch instead of SQL aggregation.  
**Recommended Solution:** Use SQL-level aggregation instead of Python loops.  
**Implementation Steps:**
1. Replace `select(Campaign)` with aggregated `select(func.sum(...), func.count(...))`.
2. Add `LIMIT` and `OFFSET` to any remaining list queries.
3. Set a maximum limit (e.g., 1000) enforced at the schema level.
**Code Example:**
```python
from sqlalchemy import func

result = await db.execute(
    select(
        func.coalesce(func.sum(Campaign.total_spend_cents), 0),
        func.coalesce(func.sum(Campaign.revenue_cents), 0),
        func.coalesce(func.sum(Campaign.conversions), 0),
    ).where(Campaign.tenant_id == tenant_id, Campaign.is_deleted == False)
)
```

---

### Issue BE-007: Auth Endpoints Perform Multiple Commits Per Request
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 580, 606, 742, 884, 1029, 1239, 1324)  
**Problem Description:** Login commits at line 580 (last_login), then again at 606 (audit log). Register commits at 742 then refreshes. Switch-tenant commits at 1029. These multiple commits within a single request are fragile because if the first commit succeeds and the second fails, the DB is left in a partially-updated state with no overarching transaction.  
**Root Cause:** No use of explicit `await db.begin()` or nested transactions for multi-step operations.  
**Recommended Solution:** Use `await db.begin()` at the start of multi-step endpoints and commit once at the end.  
**Implementation Steps:**
1. Wrap multi-step auth operations in explicit transactions.
2. Use `await db.begin()` and commit once at the end.
3. Rollback on any exception.

---

### Issue BE-008: Login Endpoint Cross-Tenant Email Hash Lookup
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 545-558)  
**Problem Description:** Login queries `User.email_hash` **without filtering by tenant**, returning candidates from **all tenants**. It then loops through all candidates doing `verify_password()` (expensive bcrypt) until a match is found. This enables timing attacks and cross-tenant email enumeration.  
**Root Cause:** Missing `tenant_id` filter in login query.  
**Recommended Solution:** Require tenant identification at login and filter by tenant.  
**Implementation Steps:**
1. Add `tenant_id` to `LoginRequest` schema.
2. Filter query by `User.tenant_id == login_data.tenant_id`.
3. Reject login if tenant_id is missing.

---

### Issue BE-009: Webhook Test Endpoint SSRF Vulnerability
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/webhooks.py` (lines 476-483)  
**Problem Description:** The `test_webhook` endpoint accepts **any URL** from the database and issues an HTTP POST to it via `httpx.AsyncClient`. There is **no URL validation** — an attacker with admin access can store a webhook pointing to `http://169.254.169.254/latest/meta-data/` and trigger it, exfiltrating AWS metadata or attacking internal services.  
**Root Cause:** No SSRF protection (no blocklist, no URL scheme restriction, no internal IP validation).  
**Recommended Solution:** Validate webhook URLs on create/update and re-validate before testing.  
**Implementation Steps:**
1. Implement `is_safe_webhook_url()` helper.
2. Block private, loopback, and reserved IP ranges.
3. Restrict schemes to `https` (preferably) and `http`.
4. Add unit tests for SSRF bypass attempts.
**Code Example:**
```python
import ipaddress
from urllib.parse import urlparse

def is_safe_webhook_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return False
    except ValueError:
        pass
    return True
```

---

### Issue BE-010: Redis Connection Per Event Publish (No Pooling)
**Severity:** HIGH  
**Component Affected:** `backend/app/workers/tasks/helpers.py` (lines 47-76)  
**Problem Description:** `publish_event()` creates a **new Redis connection** for every call via `redis.from_url()`, publishes, then closes. Under high task load, this exhausts Redis connection limits and adds massive latency.  
**Root Cause:** No connection pooling; uses sync Redis client in what should be an async-friendly path.  
**Recommended Solution:** Use the shared `aioredis` pool from `app.core.security.get_redis_pool()`.  
**Implementation Steps:**
1. Replace `redis.from_url()` with shared async pool.
2. Use `await client.publish()` instead of sync `r.publish()`.
3. Add connection pool metrics to monitoring.

---

### Issue BE-011: Superadmin Portfolio N+1 Query
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/superadmin.py` (lines 241-261)  
**Problem Description:** For every tenant in the portfolio, the code executes **two separate queries** (user count and campaign count). For 50 tenants = 100 extra queries.  
**Root Cause:** Looping over tenants with individual queries.  
**Recommended Solution:** Use a single JOINed aggregation query or batch the counts with `group_by`.  
**Implementation Steps:**
1. Replace loop with aggregated subqueries.
2. Use `select(Tenant, func.count(User.id), func.count(Campaign.id)).join(...).group_by(Tenant.id)`.

---

### Issue BE-012: Dashboard Catches Bare `Exception` and Returns 200
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/dashboard.py` (line 1003)  
**Problem Description:** A bare `except Exception as e:` catches **everything** (including `KeyboardInterrupt`, `SystemExit` if propagated, and programming errors like `NameError`), logs it, and returns a seemingly valid response. This masks critical bugs.  
**Root Cause:** Overly broad exception handler.  
**Recommended Solution:** Catch specific exceptions (`SQLAlchemyError`, `ValueError`, `TypeError`) only.  
**Implementation Steps:**
1. Replace `except Exception` with `except (SQLAlchemyError, ValueError, TypeError)`.
2. Let unexpected exceptions propagate as 500 for Sentry capture.

---

### Issue BE-013: Meta CAPI Catches Bare `Exception` and Swallows
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/meta_capi.py` (lines 142, 228, 283)  
**Problem Description:** Multiple bare `except Exception as e:` blocks catch and return error responses. This can mask syntax errors, import failures, or database connection failures, making debugging impossible.  
**Root Cause:** Overly broad exception handling.  
**Recommended Solution:** Catch specific exceptions (`httpx.HTTPError`, `ValueError`, etc.).  

---

### Issue BE-014: Password Reset & Verification Endpoints Lack Rate Limiting
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 1058, 1263, 1363)  
**Problem Description:** `forgot-password`, `resend-verification`, and `verify-email` endpoints have **no rate limiting**. An attacker can abuse these to flood Redis with reset tokens, spam users with emails/WhatsApp messages, or brute-force verification tokens.  
**Root Cause:** Only `/login` has rate limiting; other auth flows are unprotected.  
**Recommended Solution:** Add per-IP and per-target rate limiting to all auth endpoints.  
**Implementation Steps:**
1. Add dedicated rate limiter for OTP endpoints (max 3 per 15 minutes per target).
2. Add per-email rate limiting on forgot-password.
3. Log all rate limit hits to audit log.

---

### Issue BE-015: Soft-Deleted Users Can Access Profile Endpoints
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/users.py` (lines 67, 117)  
**Problem Description:** `GET /me` and `PATCH /me` query `User` by `id` only, without `is_deleted == False`. A soft-deleted user can still retrieve and modify their profile if they possess a valid JWT.  
**Root Cause:** Missing `is_deleted` filter.  
**Recommended Solution:** Add `is_deleted == False` to all user lookups.  
**Code Example:**
```python
result = await db.execute(
    select(User).where(User.id == user_id, User.is_deleted == False)
)
```

---

### Issue BE-016: Superadmin Raw SQL Column Injection Risk
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/superadmin.py` (line 807)  
**Problem Description:** The `update_subscription_plan` endpoint dynamically builds a raw SQL UPDATE statement using f-string concatenation for **column names**. While values are parameterized, column names are interpolated. If an attacker can influence the schema validation path, this becomes SQL injection.  
**Root Cause:** Dynamic SQL construction with f-strings.  
**Recommended Solution:** Use a whitelist mapping and static SQL.  
**Code Example:**
```python
column_map = {
    "price_cents": "price_cents = :price_cents",
    "max_users": "max_users = :max_users",
}
updates = [column_map[k] for k in column_map if getattr(update, k) is not None]
```

---

### Issue BE-017: JWT Tenant Claim Never Re-validated Against Database
**Severity:** HIGH  
**Component Affected:** `backend/app/auth/deps.py` (lines 113-119)  
**Problem Description:** `get_current_user` validates the JWT signature and expiration, but never checks whether the `tenant_id` claim in the token still matches the user's **current** `user.tenant_id`. If a user is moved to a different tenant, the old token remains valid for the original tenant.  
**Root Cause:** Token claims are trusted without DB reconciliation.  
**Recommended Solution:** Verify `payload.get("tenant_id") == user.tenant_id` in `get_current_user`.  
**Implementation Steps:**
1. Add DB check in `get_current_user`.
2. Optionally maintain a token version field on the user model.
3. Reject tokens where tenant claim mismatches current membership.

---

### Issue BE-018: Unnecessary `await db.refresh()` After Commit
**Severity:** MEDIUM  
**Component Affected:** Widespread (`campaigns.py`, `clients.py`, `users.py`, etc.)  
**Problem Description:** Dozens of endpoints call `await db.refresh(instance)` immediately after `await db.commit()`. With `expire_on_commit=False`, the instance is already detached and fresh. The refresh is a redundant DB round-trip.  
**Root Cause:** Cargo-culted from SQLAlchemy 1.x patterns.  
**Recommended Solution:** Remove `await db.refresh()` calls when `expire_on_commit=False` and no subsequent lazy-loading is needed.  

---

### Issue BE-019: ML Prediction Task Commits Empty Batches on Total Failure
**Severity:** HIGH  
**Component Affected:** `backend/app/workers/tasks/ml.py` (line 91)  
**Problem Description:** `run_live_predictions` commits at line 91 **outside** the per-campaign try/except. If all campaigns fail, an empty transaction is committed. If the loop partially succeeds then fails on a late campaign, early predictions are committed but the event publish still claims success.  
**Root Cause:** Commit placement outside granular error handling.  
**Recommended Solution:** Move `db.commit()` inside the loop after each successful prediction, or collect all predictions and commit once with proper rollback on failure.  

---

### Issue BE-020: Sync Tasks Use `SyncSessionLocal()` Without Explicit Rollback on Exception
**Severity:** MEDIUM  
**Component Affected:** `backend/app/workers/tasks/sync.py` (lines 52-133)  
**Problem Description:** The task uses `with SyncSessionLocal() as db:` but `sessionmaker()` context manager does **not** auto-rollback on exception. If an exception occurs after `db.add(metric)` but before `db.commit()`, the session is closed with uncommitted changes and no rollback.  
**Root Cause:** Missing explicit rollback in exception handlers.  
**Recommended Solution:**
```python
with SyncSessionLocal() as db:
    try:
        ...
        db.commit()
    except Exception:
        db.rollback()
        raise
```

---

### Issue BE-021: Changelog Admin Endpoints Lack Tenant Scoping
**Severity:** MEDIUM  
**Component Affected:** `backend/app/api/v1/endpoints/changelog.py` (lines 110-180, 232-282, 386-535)  
**Problem Description:** `ChangelogEntry` queries have **zero `tenant_id` filtering**. Any admin can create, update, delete, and read any changelog entry globally.  
**Root Cause:** `ChangelogEntry` model queries do not include `tenant_id` predicates.  
**Recommended Solution:** Add `tenant_id` to `ChangelogEntry` and `ChangelogReadStatus` models, and filter all queries by `request.state.tenant_id`.  

---

### Issue BE-022: Register Endpoint Returns 200 Instead of 201
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (line 649)  
**Problem Description:** Resource creation endpoint returns HTTP 200 instead of 201 Created.  
**Root Cause:** Missing `status_code=status.HTTP_201_CREATED`.  
**Recommended Solution:** Add `status_code=status.HTTP_201_CREATED` to the route decorator.  

---

### Issue BE-023: Register Endpoint Global Email Existence Check
**Severity:** MEDIUM  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 693-696)  
**Problem Description:** Registration checks `email_hash` globally with no tenant filter. This allows **global email enumeration** — an attacker can probe email existence via registration attempts.  
**Root Cause:** Global uniqueness check leaks existence information.  
**Recommended Solution:** Add rate limiting and CAPTCHA on registration. Consider per-tenant email uniqueness if product allows.  

---

### Issue BE-024: `get_current_user` Decrypts PII on Every Request
**Severity:** MEDIUM  
**Component Affected:** `backend/app/auth/deps.py` (lines 130-145)  
**Problem Description:** Every authenticated request triggers `decrypt_pii(user.email)` and `decrypt_pii(user.full_name)`. With high traffic, this is unnecessary CPU load since the email is often only needed for audit logging.  
**Root Cause:** Eager decryption.  
**Recommended Solution:** Only decrypt when the endpoint actually needs the raw email. Use lazy decryption or cache decrypted values in request state.  

---

### Issue BE-025: `get_redis_client()` in `auth.py` Creates Connection Without Pool
**Severity:** LOW  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 200-203)  
**Problem Description:** `get_redis_client()` creates a new Redis connection per call. OTP verify/register endpoints call this multiple times per request.  
**Root Cause:** No connection pooling.  
**Recommended Solution:** Use the shared `get_redis_pool()` from `app.core.security`.  

---

### Issue BE-026: `_safe_decrypt` in `users.py` Returns Raw Value on Failure
**Severity:** LOW  
**Component Affected:** `backend/app/api/v1/endpoints/users.py` (lines 32-40)  
**Problem Description:** On decryption failure, `_safe_decrypt` returns the raw (potentially encrypted) value as plaintext. This could expose ciphertext or garbled data in API responses.  
**Root Cause:** Fallback returns raw value.  
**Recommended Solution:** Return `None` or a placeholder like `[decryption failed]` and log the error.  

---

### Issue BE-027: `campaign_builder.py` Uses `query.order_by()` Without `limit`
**Severity:** LOW  
**Component Affected:** `backend/app/api/v1/endpoints/campaign_builder.py` (line 381)  
**Problem Description:** `result = await db.execute(query.order_by(TenantAdAccount.name))` has no `.limit()`. If a tenant has thousands of ad accounts, this returns all.  
**Root Cause:** Missing pagination.  
**Recommended Solution:** Add `.limit(1000)` or paginate.  

---

## API AUDIT FINDINGS

---

### Issue API-001: Meta CAPI Event Ingestion Completely Unauthenticated
**Severity:** CRITICAL  
**Component Affected:** `POST /meta-capi/events` (`backend/app/api/v1/endpoints/meta_capi.py:75`)  
**Problem Description:** The event ingestion endpoint has **no authentication dependency** and only checks `request.state.tenant_id`. If middleware fails or is bypassed, anyone can inject events.  
**Root Cause:** Missing `CurrentUserDep` or `get_current_user` dependency.  
**Recommended Solution:** Add `current_user: CurrentUserDep` parameter and verify the user belongs to the tenant before processing.  
**Implementation Steps:**
1. Add `Depends(get_current_user)` to the route.
2. Verify `current_user.tenant_id == tenant_id`.
3. Log all unauthorized attempts.

---

### Issue API-002: Meta CAPI Event Validation Publicly Accessible
**Severity:** CRITICAL  
**Component Affected:** `POST /meta-capi/events/validate` (`meta_capi.py:168`)  
**Problem Description:** Zero authentication required. Completely public endpoint that can be probed for internal event schemas and used for reconnaissance.  
**Root Cause:** No auth dependency declared.  
**Recommended Solution:** Add `CurrentUserDep` dependency. If public validation is intentional, gate it behind an API key or captcha.  

---

### Issue API-003: EMQ v2 Endpoints Lack Authentication
**Severity:** CRITICAL  
**Component Affected:** ALL `/tenants/{tenant_id}/emq/*` and `/emq/*` (`emq_v2.py`)  
**Problem Description:** Not a single EMQ endpoint uses `CurrentUserDep`, `get_current_user`, or any auth dependency. They only call `validate_tenant_access(request, tenant_id)` which checks `request.state.tenant_id` — an attacker only needs to spoof tenant context.  
**Root Cause:** Missing auth dependencies throughout the router.  
**Recommended Solution:** Add `current_user: CurrentUserDep` to every endpoint and enforce both authentication and tenant membership.  

---

### Issue API-004: EMQ v2 Super-Admin Endpoints Missing Role Checks
**Severity:** CRITICAL  
**Component Affected:** `GET /emq/benchmarks`, `GET /emq/portfolio` (`emq_v2.py:552-611`)  
**Problem Description:** These are labeled "super admin only" in docstrings but have **no `require_superadmin` check**. Any authenticated user can access platform-wide benchmarks.  
**Root Cause:** Missing RBAC enforcement.  
**Recommended Solution:** Add `Depends(require_superadmin())` dependency.  

---

### Issue API-005: CAPI Batch Event Stream Missing Batch Size Limit
**Severity:** CRITICAL  
**Component Affected:** `POST /events/batch` (`capi.py:236`)  
**Problem Description:** `BatchEventsRequest.events` is a `List[ConversionEvent]` with **no `max_length` constraint**. An attacker can submit an enormous batch causing memory exhaustion.  
**Root Cause:** Missing `max_length` validator on the events list.  
**Recommended Solution:** Add `Field(..., max_length=1000)` or similar to `BatchEventsRequest.events`.  

---

### Issue API-006: Tenant Feature Flags Accepts Raw Untyped Dict
**Severity:** CRITICAL  
**Component Affected:** `PATCH /{tenant_id}/features` (`tenants.py:499`)  
**Problem Description:** Accepts `feature_flags: dict` with **zero Pydantic validation**. Any nested structure, massive payload, or malicious keys can be written directly to the tenant record.  
**Root Cause:** Raw `dict` parameter instead of a validated schema.  
**Recommended Solution:** Create a `TenantFeatureFlagsUpdate` Pydantic model with explicit allowed fields and validators.  

---

### Issue API-007: Auth `/switch-tenant` Accepts Raw Dict Instead of Pydantic Schema
**Severity:** HIGH  
**Component Affected:** `POST /auth/switch-tenant` (`auth.py:945`)  
**Problem Description:** Parameter is `switch_data: dict`. No field validation, no type safety, no OpenAPI spec accuracy. Only manual `switch_data.get("tenant_id")` is checked.  
**Root Cause:** Missing `SwitchTenantRequest` Pydantic model.  
**Recommended Solution:** Replace `switch_data: dict` with `switch_data: SwitchTenantRequest`.  

---

### Issue API-008: Payments Module Breaks Response Envelope Contract
**Severity:** HIGH  
**Component Affected:** `payments.py` (all endpoints)  
**Problem Description:** Every payments endpoint returns raw Pydantic models instead of the standard `APIResponse` wrapper. The frontend expects `{"success": true, "data": ...}`.  
**Root Cause:** Inconsistent response pattern across module.  
**Recommended Solution:** Wrap all return values in `APIResponse(...)`.  

---

### Issue API-009: Multiple Endpoints Return 200 on Deletion Instead of 204
**Severity:** HIGH  
**Component Affected:** `DELETE /users/{user_id}`, `DELETE /tenants/{tenant_id}`, `DELETE /clients/{client_id}`  
**Problem Description:** REST best practice expects `204 No Content` for successful deletions. Returning `200` with a body breaks HTTP semantics and can confuse HTTP clients.  
**Root Cause:** Missing `status_code=status.HTTP_204_NO_CONTENT` and returning body.  
**Recommended Solution:** Set `status_code=204` and return `None`.  

---

### Issue API-010: Superadmin Endpoints Use Fragile Inline Auth Instead of Reusable Dependencies
**Severity:** HIGH  
**Component Affected:** ALL `/superadmin/*` (`superadmin.py`)  
**Problem Description:** Uses a local `require_superadmin(request)` function that reads `request.state.role`. This duplicates logic from `app.auth.deps.require_superadmin()` but is less maintainable. Endpoints do not use FastAPI's `Depends()` system, so auth is not declared in OpenAPI.  
**Root Cause:** Inline auth checker instead of standard dependency.  
**Recommended Solution:** Use `Depends(require_superadmin())` from `app.auth.deps` on every route.  

---

### Issue API-011: OTP Endpoints Only Protected by Global 100 req/min Rate Limit
**Severity:** HIGH  
**Component Affected:** `POST /auth/whatsapp/send-otp`, `POST /auth/email/send-otp` (`auth.py:205`, `386`)  
**Problem Description:** Beyond generic `RateLimitMiddleware`, there is **no per-IP or per-target rate limiting** on OTP generation. An attacker can burn through the global limit quickly and cause SMS/email bombing or financial loss.  
**Root Cause:** No dedicated rate limiter for OTP endpoints.  
**Recommended Solution:** Add per-phone/per-email rate limiting (e.g., max 3 OTPs per 15 minutes per target).  

---

### Issue API-012: EMQ v2 Playbook Update Returns Mock Data
**Severity:** HIGH  
**Component Affected:** `PATCH /tenants/{tenant_id}/emq/playbook/{item_id}` (`emq_v2.py:276`)  
**Problem Description:** Code explicitly states: *"In production, this would update a playbook_items table. For now, return the updated item."* It returns a hardcoded mock item regardless of input.  
**Root Cause:** Missing database persistence layer.  
**Recommended Solution:** Implement actual playbook item storage or remove the endpoint from production.  

---

### Issue API-013: EMQ v2 Autopilot Mode Override Returns Mock Data
**Severity:** HIGH  
**Component Affected:** `PUT /tenants/{tenant_id}/emq/autopilot-mode` (`emq_v2.py:461`)  
**Problem Description:** Comment states: *"In production, this would persist the override to database."* Returns hardcoded `budgetAtRisk=45000.00` and static allowed actions.  
**Root Cause:** Missing persistence.  
**Recommended Solution:** Persist override to tenant settings or EMQ state table.  

---

### Issue API-014: CAPI Endpoints Accept Raw Dicts for Sensitive Operations
**Severity:** HIGH  
**Component Affected:** `POST /capi/events/map`, `POST /capi/pii/detect`, `POST /capi/pii/hash` (`capi.py:398-462`)  
**Problem Description:** All accept `Dict[str, Any]` instead of validated Pydantic models. No field constraints, no size limits, no sanitization.  
**Root Cause:** Lazily typed parameters.  
**Recommended Solution:** Define strict Pydantic models for event mapping parameters, PII detection input, and hashing input.  

---

### Issue API-015: Mass Assignment Risk in Tenant Update
**Severity:** HIGH  
**Component Affected:** `PATCH /tenants/{tenant_id}` (`tenants.py:267`)  
**Problem Description:** While `ALLOWED_FIELDS` is declared, `plan_expires_at` is in the whitelist. A manager role can manipulate the plan expiry date.  
**Root Cause:** Overly permissive allowed fields list.  
**Recommended Solution:** Restrict `plan`, `plan_expires_at`, `max_users`, `max_campaigns` to admin/superadmin only.  

---

### Issue API-016: Implicit Authentication via Middleware Only
**Severity:** MEDIUM  
**Component Affected:** `campaigns.py`, `analytics.py`, `dashboard.py`, `autopilot.py`, `users.py`, `tenants.py`, `gdpr.py`, `payments.py`  
**Problem Description:** Endpoints rely exclusively on `tenant_id = getattr(request.state, "tenant_id", None)` without declaring explicit `Depends(get_current_user)`. If `TenantMiddleware` is misconfigured, skipped, or bypassed, endpoints become unprotected.  
**Root Cause:** Implicit auth pattern instead of explicit FastAPI dependencies.  
**Recommended Solution:** Add `current_user: CurrentUserDep` to all endpoint signatures as defense-in-depth.  

---

### Issue API-017: Campaign Creation Conflict Returns 400 Instead of 409
**Severity:** MEDIUM  
**Component Affected:** `POST /campaigns` (`campaigns.py:184`)  
**Problem Description:** Duplicate `external_id` check raises `HTTPException(status_code=400)` instead of `409 Conflict`.  
**Root Cause:** Wrong status code mapping.  
**Recommended Solution:** Change to `status.HTTP_409_CONFLICT`.  

---

### Issue API-018: API Key Creation Returns 400 on Limit Exceeded
**Severity:** MEDIUM  
**Component Affected:** `POST /api-keys` (`api_keys.py:166`)  
**Problem Description:** Exceeding the 10-key limit returns `400 Bad Request` instead of `409 Conflict` or `403 Forbidden`.  
**Root Cause:** Incorrect status code choice.  
**Recommended Solution:** Return `409` or `403`.  

---

### Issue API-019: Login Endpoint Returns Raw Dict Instead of TokenResponse Schema
**Severity:** MEDIUM  
**Component Affected:** `POST /auth/login` (`auth.py:507`)  
**Problem Description:** Returns `data={...}` with a raw Python dict containing `available_tenants`. The `TokenResponse` schema does not include `available_tenants`, causing a schema mismatch.  
**Root Cause:** Schema does not match actual returned payload.  
**Recommended Solution:** Update `TokenResponse` to include `available_tenants` or create a `LoginResponse` schema.  

---

### Issue API-020: Meta CAPI `/health` Returns Raw Dict
**Severity:** MEDIUM  
**Component Affected:** `GET /meta-capi/health` (`meta_capi.py:64`)  
**Problem Description:** Returns raw `{"status": "healthy"}` instead of `APIResponse` wrapper.  
**Root Cause:** Inconsistent response format.  
**Recommended Solution:** Return `APIResponse(success=True, data={"status": "healthy"})`.  

---

### Issue API-021: Superadmin Audit Log Query Missing Tenant Isolation on Raw SQL
**Severity:** MEDIUM  
**Component Affected:** `GET /superadmin/audit` (`superadmin.py:541`)  
**Problem Description:** While parameterized queries prevent SQL injection, the `action` filter uses `ILIKE` with user input: `params["action"] = f"%{action}%"`. The `action` string is not validated against an enum.  
**Root Cause:** Unvalidated user input in ILIKE pattern.  
**Recommended Solution:** Validate `action` against `AuditAction` enum before appending to query.  

---

### Issue API-022: Autopilot Endpoints Lack Role-Based Checks
**Severity:** MEDIUM  
**Component Affected:** `POST /tenant/{tenant_id}/autopilot/actions`, `/actions/{action_id}/approve`, `/actions/approve-all` (`autopilot.py`)  
**Problem Description:** Only checks `request.state.user_id` and `tenant_id`. No check if the user has `CAMPAIGN_WRITE` or `RULE_EXECUTE` permission. A VIEWER role could queue and approve autopilot actions.  
**Root Cause:** Missing RBAC enforcement.  
**Recommended Solution:** Add `Depends(require_permission("campaigns", PermLevel.EDIT))` or similar.  

---

### Issue API-023: API Keys Router Restricted to Superadmin
**Severity:** HIGH  
**Component Affected:** ALL `/api-keys/*` (`api_keys.py:28-32`)  
**Problem Description:** Router declares `dependencies=[Depends(require_super_admin)]`, but endpoint docstrings say "for the current user" and filter by `user_id`. Non-superadmins are completely blocked from managing their own API keys.  
**Root Cause:** Overly restrictive router-level dependency contradicts endpoint logic.  
**Recommended Solution:** Remove router-level `require_super_admin`. Add `CurrentUserDep` to endpoints and optionally require admin for creation.  

---

### Issue API-024: Webhooks Router Restricted to Superadmin
**Severity:** HIGH  
**Component Affected:** ALL `/webhooks/*` (`webhooks.py:34-38`)  
**Problem Description:** Same as API-023. Router requires superadmin, but endpoints filter by `tenant_id` and docstrings indicate tenant-scoped usage.  
**Root Cause:** Overly restrictive router-level dependency.  
**Recommended Solution:** Remove router-level `require_super_admin`; use `CurrentUserDep` with tenant isolation.  

---

## FRONTEND AUDIT FINDINGS

---

### Issue FE-001: API Path Mismatch — insights.ts uses wrong URL prefix
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/insights.ts` (lines 152-165, 180-196, 210-225, 238-253)  
**Problem Description:** All hooks call `/insights/tenant/{tenantId}/...` but backend `insights.py` only defines `/insights`, `/recommendations`, `/anomalies`, `/kpis` (no `tenant/{id}` prefix). Backend reads tenant from `X-Tenant-ID` header.  
**Root Cause:** Frontend incorrectly prepends tenant ID to the path.  
**Recommended Solution:** Remove `/tenant/{tenantId}` from all insights URLs.  
**Code Example:**
```typescript
// BEFORE (broken)
const response = await apiClient.get<{ data: InsightsData }>(
  `/insights/tenant/${tenantId}/insights${params}`
);

// AFTER
const response = await apiClient.get<{ data: InsightsData }>(
  `/insights${params}`
);
```

---

### Issue FE-002: API Path Mismatch — autopilot.ts uses wrong URL prefix
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/autopilot.ts` (lines 92-134, 160-196)  
**Problem Description:** All hooks call `/autopilot/tenant/{tenantId}/...` but backend `autopilot.py` only defines `/autopilot/status`, `/autopilot/actions`, etc.  
**Root Cause:** Frontend incorrectly prepends tenant ID to the path.  
**Recommended Solution:** Remove `/tenant/${tenantId}` from all autopilot URLs.  

---

### Issue FE-003: API Path Mismatch — trustLayer.ts uses wrong URL prefix
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/trustLayer.ts` (lines 93-169)  
**Problem Description:** All hooks call `/trust-layer/tenant/{tenantId}/...` but backend `trust_layer.py` only defines `/trust-layer/signal-health`, etc.  
**Root Cause:** Frontend incorrectly prepends tenant ID to the path.  
**Recommended Solution:** Remove `/tenant/${tenantId}` from all trust-layer URLs.  

---

### Issue FE-004: API Path Mismatch — featureFlags.ts uses wrong tenant path
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/featureFlags.ts` (lines 50, 84, 103, 120, 140)  
**Problem Description:** Calls `/tenant/{tenantId}/features` but backend `tenants.py` defines `/tenants/{tenant_id}/features` (plural `tenants`, not singular `tenant`).  
**Root Cause:** Typo in URL path.  
**Recommended Solution:** Change to `/tenants/${tenantId}/features`.  

---

### Issue FE-005: API Path Mismatch — dashboard.ts syncPlatform uses wrong path
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/dashboard.ts` (lines 448-454)  
**Problem Description:** Calls `/campaigns/sync/{platform}` but backend `campaigns.py` defines `/campaigns/sync-platform/{platform}`.  
**Root Cause:** Missing `-platform` suffix in path.  
**Recommended Solution:** Change to `/campaigns/sync-platform/${platform}`.  

---

### Issue FE-006: Non-existent endpoints in campaigns.ts
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/api/campaigns.ts` (lines 167-176, 181-192)  
**Problem Description:** `bulkUpdateStatus` calls `/campaigns/bulk/status`, `pauseCampaign` calls `/campaigns/${id}/pause`, and `activateCampaign` calls `/campaigns/${id}/activate`. None of these exist in backend `campaigns.py`.  
**Root Cause:** Frontend invented endpoints that don't exist.  
**Recommended Solution:** Use `PATCH /campaigns/{campaign_id}` with `{ status: 'paused' | 'active' }` instead.  

---

### Issue FE-007: Missing WhatsApp API client
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/views/WhatsApp.tsx` (no `src/api/whatsapp.ts`)  
**Problem Description:** WhatsApp view exists (2501 lines) but there is no `src/api/whatsapp.ts`. The view imports `axios` directly and uses `apiClient` inconsistently.  
**Root Cause:** API layer was never created for this feature.  
**Recommended Solution:** Create `src/api/whatsapp.ts` with all backend endpoints (contacts, templates, messages, broadcasts, webhooks, conversations).  

---

### Issue FE-008: Missing MFA API client
**Severity:** CRITICAL  
**Component Affected:** `frontend/src/views/Settings.tsx` (no `src/api/mfa.ts`)  
**Problem Description:** Settings view shows MFA QR code but there is no `src/api/mfa.ts`. Backend `mfa.py` defines `/mfa/status`, `/mfa/setup`, `/mfa/verify`, `/mfa/disable`, `/mfa/backup-codes`, `/mfa/validate`, `/mfa/check/{user_id}`.  
**Root Cause:** API layer was never created for MFA.  
**Recommended Solution:** Create `src/api/mfa.ts` with all MFA hooks.  

---

### Issue FE-009: Missing Subscription API client
**Severity:** CRITICAL  
**Component Affected:** N/A (no `src/api/subscription.ts`)  
**Problem Description:** Backend `subscription.py` defines `/subscription/status`, `/subscription/config`, `/subscription/check`, `/subscription/warnings`, `/subscription/usage-summary`. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/subscription.ts`.  

---

### Issue FE-010: Missing Webhooks API client
**Severity:** CRITICAL  
**Component Affected:** N/A (no `src/api/webhooks.ts`)  
**Problem Description:** Backend `webhooks.py` defines 8 webhook management endpoints. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/webhooks.ts`.  

---

### Issue FE-011: Missing Notifications API client
**Severity:** CRITICAL  
**Component Affected:** `src/components/notifications/NotificationCenter.tsx` (no `src/api/notifications.ts`)  
**Problem Description:** NotificationCenter component exists but no `src/api/notifications.ts`. Backend `notifications.py` defines `/notifications`, `/notifications/count`, `/notifications/mark-read`, `/notifications/{notification_id}`.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/notifications.ts`.  

---

### Issue FE-012: Missing Slack API client
**Severity:** CRITICAL  
**Component Affected:** `src/components/settings/SlackIntegration.tsx` (no `src/api/slack.ts`)  
**Problem Description:** SlackIntegration component exists but no `src/api/slack.ts`. Backend `slack.py` defines 6 endpoints.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/slack.ts`.  

---

### Issue FE-013: Missing Simulator API client
**Severity:** CRITICAL  
**Component Affected:** N/A (no `src/api/simulator.ts`)  
**Problem Description:** Backend `simulator.py` defines 4 endpoints. No frontend API file exists, though there is a `SimulatorWidget` component.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/simulator.ts`.  

---

### Issue FE-014: Missing API Keys client
**Severity:** CRITICAL  
**Component Affected:** N/A (no `src/api/apiKeys.ts`)  
**Problem Description:** Backend `api_keys.py` defines 5 endpoints. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/apiKeys.ts`.  

---

### Issue FE-015: Missing CAPI client
**Severity:** CRITICAL  
**Component Affected:** `src/views/CAPISetup.tsx` (no `src/api/capi.ts` or `src/api/metaCapi.ts`)  
**Problem Description:** CAPISetup view exists but no dedicated API client. Backend `capi.py` and `meta_capi.py` define 15+ endpoints.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/capi.ts` and `src/api/metaCapi.ts`.  

---

### Issue FE-016: Missing Newsletter API client
**Severity:** CRITICAL  
**Component Affected:** `src/views/Newsletter.tsx` (no `src/api/newsletter.ts`)  
**Problem Description:** Backend `newsletter.py` defines CRUD endpoints. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/newsletter.ts`.  

---

### Issue FE-017: Missing CDP API client
**Severity:** CRITICAL  
**Component Affected:** `src/views/tenant/Integrations.tsx` (no `src/api/cdp.ts`)  
**Problem Description:** Backend `cdp.py` defines 20+ endpoints. No dedicated frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/cdp.ts`.  

---

### Issue FE-018: Missing Clients API client
**Severity:** CRITICAL  
**Component Affected:** `src/views/tenant/Console.tsx` (no `src/api/clients.ts`)  
**Problem Description:** Backend `clients.py` defines 15+ endpoints. No dedicated frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/clients.ts`.  

---

### Issue FE-019: Missing Landing CMS API client
**Severity:** HIGH  
**Component Affected:** `src/views/landing/CMSDashboard.tsx` (no `src/api/landingCms.ts`)  
**Problem Description:** Backend `landing_cms.py` defines endpoints. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/landingCms.ts`.  

---

### Issue FE-020: Missing Competitors API client
**Severity:** HIGH  
**Component Affected:** `src/views/Competitors.tsx` (no `src/api/competitors.ts`)  
**Problem Description:** Backend `competitors.py` defines endpoints. No frontend API file exists.  
**Root Cause:** API layer never created.  
**Recommended Solution:** Create `src/api/competitors.ts`.  

---

### Issue FE-021: console.error placeholders in production views
**Severity:** HIGH  
**Component Affected:** Multiple files (see below)  
**Problem Description:** `console.error` is used as the sole error handler for user-facing operations. Users see no feedback; errors only appear in DevTools.  
**Affected Files:**
- `src/views/CAPISetup.tsx:137,192`
- `src/views/Competitors.tsx:132,145`
- `src/views/CustomAutopilotRules.tsx:270,282,295,325`
- `src/views/MLTraining.tsx:75,84,129,154,178,196`
- `src/views/portal/PortalDashboard.tsx:207`
- `src/views/superadmin/Billing.tsx:160`
- `src/views/tenant/AdAccounts.tsx:86,101`
- `src/views/tenant/CampaignBuilder.tsx:303,342`
- `src/views/WhatsApp.tsx:427,443,494,628,660,724,739,755,787,801,1386`
- `src/views/superadmin/System.tsx:135`
- `src/views/tenant/ConnectPlatforms.tsx:168,179,188`
**Root Cause:** Missing error-to-UI wiring (toast notifications, error banners).  
**Recommended Solution:** Replace `console.error` with `toast({ variant: 'destructive', title: 'Error', description: getErrorMessage(err) })`.  

---

### Issue FE-022: console.warn placeholder in PortalDashboard
**Severity:** HIGH  
**Component Affected:** `frontend/src/views/portal/PortalDashboard.tsx:207`  
**Problem Description:** `console.warn('Request submission endpoint not available, saving locally', err);` — this is a dead endpoint fallback that silently degrades functionality without telling the user.  
**Root Cause:** Endpoint was never implemented; placeholder left in production.  
**Recommended Solution:** Implement the backend endpoint or show a clear UI message that the feature is unavailable.  

---

### Issue FE-023: console.log in production code
**Severity:** HIGH  
**Component Affected:** `frontend/src/views/pages/ApiDocs.tsx:229`  
**Problem Description:** `console.log(health.score); // 85` — debug logging left in production with a hardcoded comment.  
**Root Cause:** Committed debug code.  
**Recommended Solution:** Remove the line.  

---

### Issue FE-024: `any` types in production components
**Severity:** HIGH  
**Component Affected:** Multiple WhatsApp and AM components  
**Problem Description:** API responses are typed as `any`, bypassing TypeScript safety and making refactoring dangerous.  
**Affected Files:**
- `src/views/whatsapp/WhatsAppTemplates.tsx:73`
- `src/views/whatsapp/WhatsAppMessages.tsx:86`
- `src/views/whatsapp/WhatsAppContacts.tsx:66`
- `src/views/whatsapp/WhatsAppBroadcast.tsx:68`
- `src/views/am/Portfolio.tsx:64`
**Root Cause:** Missing interface definitions for paginated API responses.  
**Recommended Solution:** Define strict interfaces and replace `any` with them.  

---

### Issue FE-025: `as any` casts for Recharts formatters
**Severity:** HIGH  
**Component Affected:** Multiple chart components  
**Problem Description:** `formatter={(... ) as any}` suppresses TypeScript errors instead of fixing the type signature.  
**Affected Files:**
- `src/components/charts/DailyTrendChart.tsx:111`
- `src/components/charts/PlatformPerformanceChart.tsx:87`
- `src/components/charts/ROASByPlatformChart.tsx:111`
- `src/components/charts/RegionalBreakdownChart.tsx:105`
**Root Cause:** Recharts type mismatch worked around with casts.  
**Recommended Solution:** Provide correctly typed formatter functions that match Recharts' `TooltipFormatter` signature.  

---

### Issue FE-026: Incorrect UserRole in admin.ts
**Severity:** HIGH  
**Component Affected:** `frontend/src/api/admin.ts:11`  
**Problem Description:** `export type UserRole = 'superadmin' | 'admin' | 'user' | 'viewer'` — `'user'` does not exist in backend. Backend has `'manager'`, `'analyst'`, and `'viewer'`.  
**Root Cause:** Frontend type drifted from backend enum.  
**Recommended Solution:** Align with backend: `'superadmin' | 'admin' | 'manager' | 'analyst' | 'viewer'`.  

---

### Issue FE-027: Missing role types in auth.ts User interface
**Severity:** HIGH  
**Component Affected:** `frontend/src/api/auth.ts:12-23`  
**Problem Description:** `role` type is inconsistent across auth and admin modules.  
**Root Cause:** No shared `UserRole` type.  
**Recommended Solution:** Use a shared `UserRole` type imported from a common types file.  

---

### Issue FE-028: Zustand store duplicates server state without persistence
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/stores/featureFlagsStore.ts` + `src/api/featureFlags.ts:60-71`  
**Problem Description:** `useFeatureFlags` copies TanStack Query data into Zustand via `useEffect`. This creates a second source of truth. The Zustand store is not persisted, so feature flags are re-fetched and re-copied on every mount.  
**Root Cause:** Unnecessary state duplication.  
**Recommended Solution:** Remove the Zustand feature flags store. Use TanStack Query as the single source of truth.  

---

### Issue FE-029: Placeholder/fake data in query hooks
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/api/audit.ts:88-183`, `src/api/knowledgeGraph.ts:81-128,155-189`  
**Problem Description:** `placeholderData` and `initialData` contain hardcoded fake/demo data (e.g., "Sarah Miller", "Ahmed Hassan") that will flash on screen before real data loads.  
**Root Cause:** Hooks were built with demo data instead of proper loading skeletons.  
**Recommended Solution:** Remove `placeholderData`/`initialData`. Use `isLoading` + `<Skeleton>` components.  

---

### Issue FE-030: TenantStore logout doesn't clear TanStack Query cache
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/stores/tenantStore.ts:171-183`  
**Problem Description:** `logout()` clears localStorage and Zustand state, but does not call `queryClient.clear()`. If a user logs out and another logs in on the same tab, stale cached data from the previous tenant may be visible.  
**Root Cause:** Logout logic is split between store and auth hook.  
**Recommended Solution:** Move `queryClient.clear()` into the store's logout action or ensure all logout flows call it.  

---

### Issue FE-031: Direct axios usage bypasses tenant header injection
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/views/WhatsApp.tsx:37`  
**Problem Description:** `import axios from 'axios'` is used alongside `apiClient`. Direct axios calls will miss `X-Tenant-ID`, auth tokens, and error interceptors.  
**Root Cause:** Developer used axios directly instead of the centralized client.  
**Recommended Solution:** Remove `import axios from 'axios'` and use `apiClient` for all HTTP calls.  

---

### Issue FE-032: Dangerous default tenant ID
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/api/client.ts:57-63`  
**Problem Description:** `getTenantId()` defaults to `1` when no tenant is stored. This can cause requests to be silently routed to tenant 1, leaking or mutating wrong tenant data.  
**Root Cause:** Defensive default that is unsafe in multi-tenant context.  
**Recommended Solution:** Return `null` when no tenant is set and let the request interceptor skip the header. The backend should reject requests without a tenant ID.  

---

### Issue FE-033: Missing ErrorBoundary on many routes
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/App.tsx`  
**Problem Description:** Only a subset of routes are wrapped in `<ErrorBoundary>`. CMS portal routes, checkout routes, portal routes, and most dashboard child routes only have `<Suspense>` with no error boundary. A JS crash in any of these will unmount the entire app.  
**Root Cause:** Inconsistent error boundary coverage.  
**Recommended Solution:** Wrap every `<Suspense>` route with `<ErrorBoundary>`.  

---

### Issue FE-034: Skipped test in tenant flows
**Severity:** MEDIUM  
**Component Affected:** `frontend/e2e/tenant-flows.spec.ts`  
**Problem Description:** `test.skip('should display trust page content', ...)` is skipped with a comment about flaky parallel execution.  
**Root Cause:** Test is flaky.  
**Recommended Solution:** Stabilize the test by using unique test data per worker or serial execution.  

---

### Issue FE-035: Missing e2e coverage for critical flows
**Severity:** MEDIUM  
**Component Affected:** `frontend/e2e/` directory  
**Problem Description:** No e2e specs for: WhatsApp, Newsletter, CDP, Campaign Builder, Settings (MFA, billing), Profit/ROAS, Onboarding wizard, Superadmin, CMS, Checkout flow.  
**Root Cause:** E2E suite has not kept pace with feature development.  
**Recommended Solution:** Add specs for at least the critical user journeys.  

---

### Issue FE-036: Missing tsconfig.build.json
**Severity:** MEDIUM  
**Component Affected:** `frontend/package.json:8`  
**Problem Description:** Build script runs `tsc --noEmit -p tsconfig.build.json` but no `tsconfig.build.json` exists in the frontend directory.  
**Root Cause:** File was deleted or never created.  
**Recommended Solution:** Create `tsconfig.build.json` that extends `tsconfig.json` and excludes test files.  

---

### Issue FE-037: Source maps disabled
**Severity:** MEDIUM  
**Component Affected:** `frontend/vite.config.ts:25`  
**Problem Description:** `sourcemap: false` makes production debugging nearly impossible.  
**Root Cause:** Likely set for performance.  
**Recommended Solution:** Set `sourcemap: true` for production builds.  

---

## DATABASE & MIGRATION AUDIT FINDINGS

---

### Issue DB-001: Orphan Tables Created by Dead Migration Branch
**Severity:** CRITICAL  
**Component Affected:** `migrations/versions/20260107_000000_020_add_autopilot_enforcement_tables.py`  
**Problem Description:** Migration 020 creates three tables with **Integer PKs** and **VARCHAR columns** (no enums) that have **no corresponding SQLAlchemy models**. The actual models are created by migration `012_add_autopilot_enforcement` with UUID PKs and proper enums. The database contains **six autopilot tables**, three of which are dead weight.  
**Root Cause:** Autopilot feature was started on main branch (020), abandoned, then re-implemented on a side branch (012).  
**Recommended Solution:** Create a new migration to drop the orphaned tables if they contain no production data.  

---

### Issue DB-002: Conflicting "012" Revision IDs Create Two Heads
**Severity:** CRITICAL  
**Component Affected:** `migrations/versions/20260105_000000_012_add_ml_prediction_columns.py` and `20260112_000000_012_add_autopilot_enforcement.py`  
**Problem Description:** Both migrations declare `down_revision = '011_add_usp_layer_tables'`, creating two divergent heads. Using the same numeric prefix for unrelated features makes rollback/targeting by partial revision ID impossible and dangerous.  
**Root Cause:** Two developers picked the same sequential number.  
**Recommended Solution:** Do not rename historical revisions. Document the branch topology in `migrations/README.md` and ensure CI/CD uses `alembic merge` before deploying.  

---

### Issue DB-003: `StrEnumType` Cast Depends on Missing Enum Types
**Severity:** CRITICAL  
**Component Affected:** `backend/app/db/base.py` (lines 30-75)  
**Problem Description:** `StrEnumType.bind_expression()` casts bind values to a PostgreSQL enum type. If a migration creates a column using `StrEnumType` but only defines the column as `sa.String()` **without creating the corresponding PG enum type**, any query using this column in a `WHERE` clause will fail with `type "xxx" does not exist`.  
**Root Cause:** Migrations must manually create PG enums for every `StrEnumType` used.  
**Recommended Solution:** Audit every model using `StrEnumType` and verify its corresponding migration calls `CREATE TYPE`. Add a unit test that introspects `Base.metadata` and checks every `StrEnumType` column.  

---

### Issue DB-004: ~80% of Tenant-Facing Tables Lack Soft Delete
**Severity:** CRITICAL  
**Component Affected:** Nearly all model files under `app/models/`  
**Problem Description:** Only core models inherit `SoftDeleteMixin`: `Tenant`, `User`, `Campaign`, `CreativeAsset`, `Rule`, `Client`, `CMSPost`, `CMSPage`. Every other tenant-scoped table is missing `is_deleted` / `deleted_at`, including all CRM, CDP, Pacing, Profit, Reporting, Attribution, Newsletter, Webhooks, and Campaign Builder tables.  
**Root Cause:** `SoftDeleteMixin` was added to base architecture but not applied to feature modules.  
**Recommended Solution:** For each tenant-facing table, decide if soft-delete is required. If yes: add mixin, create migration, update all queries. If no: document explicit decision.  

---

### Issue DB-005: Newsletter Tables Lack `tenant_id` Indexes
**Severity:** HIGH  
**Component Affected:** `app/models/newsletter.py` (lines 80, 131)  
**Problem Description:** `NewsletterTemplate.tenant_id` and `NewsletterCampaign.tenant_id` are `ForeignKey` but have **no `index=True`** and no composite index.  
**Root Cause:** Missing inline index declaration.  
**Recommended Solution:** Add `index=True` to both `tenant_id` columns or add `Index(...)` in `__table_args__`.  

---

### Issue DB-006: CRM ForeignKey Columns Missing Indexes
**Severity:** HIGH  
**Component Affected:** `app/models/crm.py` (lines 146, 226, 227, 304)  
**Problem Description:** Heavily-queried FK columns lack indexes: `CRMContact.connection_id`, `CRMDeal.connection_id`, `CRMDeal.contact_id`, `Touchpoint.contact_id`.  
**Root Cause:** Indexes omitted during model creation.  
**Recommended Solution:** Add inline `index=True` to each, or add composite indexes (e.g., `tenant_id, connection_id`).  

---

### Issue DB-007: Campaign Builder FK Columns Missing Indexes
**Severity:** HIGH  
**Component Affected:** `app/models/campaign_builder.py` (lines 120, 169, 223)  
**Problem Description:** `TenantAdAccount.connection_id`, `CampaignDraft.ad_account_id`, `CampaignPublishLog.draft_id` lack indexes.  
**Root Cause:** No index declarations.  
**Recommended Solution:** Add `index=True` to each ForeignKey column.  

---

### Issue DB-008: `user_id` and `created_by_user_id` Columns Missing Indexes
**Severity:** HIGH  
**Component Affected:** `app/models/autopilot.py`, `app/models/campaign_builder.py`, `app/models/audit_services.py`  
**Problem Description:** User-scoped columns frequently used for filtering/ownership queries lack indexes.  
**Root Cause:** Ownership/audit columns were not indexed.  
**Recommended Solution:** Add indexes on user-scoped columns.  

---

### Issue DB-009: Missing `email_hash` Index on `landing_page_subscribers`
**Severity:** HIGH  
**Component Affected:** `app/base_models.py` (line 157)  
**Problem Description:** `LandingPageSubscriber.email_hash` exists but has **no index**, while `email` does. If `email_hash` is used for deduplication or lookups, it needs an index.  
**Root Cause:** Index oversight.  
**Recommended Solution:** Add `Index("ix_lps_email_hash", "email_hash")` in `__table_args__`.  

---

### Issue DB-010: Financial Amounts Use `Integer` Instead of `BigInteger`
**Severity:** HIGH  
**Component Affected:** `app/base_models.py`, `app/models/campaign_builder.py`  
**Problem Description:** `Campaign.total_spend_cents`, `revenue_cents`, `CampaignMetric.spend_cents`, `revenue_cents` use `Integer` (32-bit, max ~2.1B). A large tenant could exceed 2.1 billion cents ($21M) in lifetime spend.  
**Root Cause:** `Integer` chosen without considering scale limits.  
**Recommended Solution:** Migrate financial `_cents` columns to `BigInteger`.  

---

### Issue DB-011: `Campaign.start_date` / `end_date` Type Mismatch
**Severity:** HIGH  
**Component Affected:** `app/base_models.py` (lines 541-542)  
**Problem Description:** Declared as `Mapped[Optional[datetime]]` but column type is `Date` (not `DateTime`). This causes silent truncation of time components.  
**Root Cause:** Typo or oversight during SQLAlchemy 2.0 migration.  
**Recommended Solution:** Change model annotation to `Mapped[Optional[date]]` or change column to `DateTime(timezone=True)`.  

---

### Issue DB-012: `TenantPlatformConnection` `error_count` Missing `nullable=False`
**Severity:** HIGH  
**Component Affected:** `app/models/campaign_builder.py` (line 98)  
**Problem Description:** `error_count = Column(Integer, default=0)` has no `nullable=False`, allowing NULL values which breaks aggregation queries.  
**Root Cause:** Missing nullability constraint.  
**Recommended Solution:** Add `nullable=False`.  

---

### Issue DB-013: Mixed SQLAlchemy 1.x `Column` vs 2.0 `mapped_column` Styles
**Severity:** MEDIUM  
**Component Affected:** Most model files  
**Problem Description:** `app/models/campaign_builder.py`, `crm.py`, `cdp.py`, etc. use `Column(...)` (1.x style), while `base_models.py`, `newsletter.py`, `onboarding.py` use `mapped_column(...)` (2.0 style). Mixed styles prevent full type-checking benefits.  
**Root Cause:** Incomplete migration to SQLAlchemy 2.0 patterns.  
**Recommended Solution:** Standardize on `mapped_column` across all models.  

---

### Issue DB-014: Migration Downgrade Drops Enum Types Unconditionally
**Severity:** HIGH  
**Component Affected:** `migrations/versions/20240101_000000_001_initial_schema.py` (lines 400-408)  
**Problem Description:** `downgrade()` drops enum types with `DROP TYPE auditaction` etc. without `IF EXISTS`. If dependent objects exist, downgrade will fail.  
**Root Cause:** Missing `IF EXISTS` and `CASCADE` guards.  
**Recommended Solution:** Change to `op.execute("DROP TYPE IF EXISTS auditaction CASCADE")`.  

---

### Issue DB-015: Empty Merge Migration with No Validation
**Severity:** HIGH  
**Component Affected:** `migrations/versions/20260407_075514_25b2d4ee6525_merge_migration_heads.py`  
**Problem Description:** Empty `upgrade()` and `downgrade()` functions. The two branches were never validated against each other for table/column name collisions.  
**Root Cause:** Relying on default merge behavior without manual conflict review.  
**Recommended Solution:** Add comment block documenting which tables were added by each branch.  

---

### Issue DB-016: `CampaignMetric` Missing `created_at` / `updated_at`
**Severity:** MEDIUM  
**Component Affected:** `app/base_models.py` (lines 598-638)  
**Problem Description:** `CampaignMetric` inherits `TenantMixin` but **not** `TimestampMixin`. No `created_at` or `updated_at` columns.  
**Root Cause:** Mixin not applied.  
**Recommended Solution:** Add `TimestampMixin` to `CampaignMetric` and create a migration.  

---

## INFRASTRUCTURE & DEVOPS AUDIT FINDINGS

---

### Issue INF-001: Dockerfile.frontend Runs as Root
**Severity:** CRITICAL  
**Component Affected:** `Dockerfile.frontend` (production stage)  
**Problem Description:** Production stage runs as **root** (no `USER` directive). The `node:20-alpine` final stage installs `serve` globally and executes it as root. Container compromise gives host root privileges if Docker runtime is misconfigured.  
**Root Cause:** Missing non-root user creation / `USER` switch.  
**Recommended Solution:** Add non-root user and switch before `CMD`.  
**Code Example:**
```dockerfile
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
USER nextjs
```

---

### Issue INF-002: Docker Compose Weak DB/Redis Passwords + Exposed Ports
**Severity:** CRITICAL  
**Component Affected:** `docker-compose.yml`, `editions/*/docker-compose.yml`  
**Problem Description:** `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}` and `REDIS_PASSWORD: ${REDIS_PASSWORD:-stratum-dev-redis-pass}` — weak hardcoded defaults. Ports `5432:5432` and `6379:6379` exposed to host.  
**Root Cause:** Fallback passwords + exposed ports in dev compose.  
**Recommended Solution:** Remove fallback (`:-password`) and require env var (`:?POSTGRES_PASSWORD must be set`). Consider removing host port mapping.  

---

### Issue INF-003: SQL Injection in load_datasets.py
**Severity:** CRITICAL  
**Component Affected:** `scripts/load_datasets.py`  
**Problem Description:** `DROP TABLE IF EXISTS {schema}.{table_name} CASCADE;` where `table_name` derives from user-controlled filenames (`csv_file.stem`).  
**Root Cause:** Unsafe string interpolation into SQL.  
**Recommended Solution:** Use SQLAlchemy `text()` with bound parameters, or validate `table_name` against strict allow-list regex (`^[a-z0-9_]+$`).  

---

### Issue INF-004: Hardcoded Fallback Superadmin Password in start.sh
**Severity:** CRITICAL  
**Component Affected:** `backend/start.sh`  
**Problem Description:** `SUPERADMIN_PASSWORD="${SUPERADMIN_PASSWORD:-StratumAdmin2026!}"` — if env var is unset, a known password is used.  
**Root Cause:** Default value is a real, guessable password.  
**Recommended Solution:** Remove fallback: `SUPERADMIN_PASSWORD="${SUPERADMIN_PASSWORD:?SUPERADMIN_PASSWORD must be set}"`  

---

### Issue INF-005: Hardcoded bcrypt hash in seed-data.sql
**Severity:** CRITICAL  
**Component Affected:** `scripts/seed-data.sql`  
**Problem Description:** Hardcoded bcrypt hash for password `Admin123!`: `$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4URbWtA3rP.5TxuS`. Creates a known-password admin account.  
**Root Cause:** Pre-computed hash of a weak, known password.  
**Recommended Solution:** Remove the hash. Force password reset via application onboarding or generate hash at runtime with a strong random password.  

---

### Issue INF-006: No `.dockerignore` at Repository Root
**Severity:** HIGH  
**Component Affected:** Repository root  
**Problem Description:** Root-context builds send the entire repo (including `.git`, potential `.env` files, secrets) as build context.  
**Root Cause:** File missing.  
**Recommended Solution:** Create root `.dockerignore` excluding `.git/`, `.env*`, `node_modules/`, `*.pem`, `secrets/`.  

---

### Issue INF-007: Redis Unauthenticated in beta, staging, and editions
**Severity:** HIGH  
**Component Affected:** `docker-compose.beta.yml`, `docker-compose.staging.yml`, `editions/*/docker-compose.yml`  
**Problem Description:** Redis runs **without `--requirepass`** and ports are exposed. Any compromised container can read/write the entire Redis keyspace (sessions, Celery tasks, caches).  
**Root Cause:** Missing auth flag.  
**Recommended Solution:** Add `--requirepass ${REDIS_PASSWORD:?...}` and remove host port mapping.  

---

### Issue INF-008: Grafana Hardcoded Weak Password
**Severity:** HIGH  
**Component Affected:** `docker-compose.monitoring.yml`  
**Problem Description:** `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-stratum123}` — hardcoded weak Grafana admin password.  
**Root Cause:** Weak fallback in monitoring stack.  
**Recommended Solution:** Remove fallback; require env var.  

---

### Issue INF-009: Prometheus Exposed Without Authentication
**Severity:** HIGH  
**Component Affected:** `docker-compose.monitoring.yml`  
**Problem Description:** Prometheus exposed on `9090:9090` without authentication. Anyone with network access can query metrics.  
**Root Cause:** No auth layer on Prometheus.  
**Recommended Solution:** Put Prometheus behind reverse proxy with basic auth or remove host port mapping.  

---

### Issue INF-010: Migration Failures Are Non-Fatal in start.sh
**Severity:** HIGH  
**Component Affected:** `backend/start.sh`  
**Problem Description:** `timeout 120 python -m alembic upgrade head 2>&1 || echo "Migration warning (non-fatal)"`. App starts even with a broken schema.  
**Root Cause:** `|| echo` swallows exit code.  
**Recommended Solution:** Remove `|| echo ...`. If migrations fail, container must exit.  

---

### Issue INF-011: CI/CD Uses Non-Existent Action Versions
**Severity:** HIGH  
**Component Affected:** `.github/workflows/ci.yml`  
**Problem Description:** Uses `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`. Latest stable are v4/v5. Typosquatting risk.  
**Root Cause:** Incorrect version tags.  
**Recommended Solution:** Pin to verified versions: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`.  

---

### Issue INF-012: Trivy Scans Use Non-Failing Exit Code
**Severity:** HIGH  
**Component Affected:** `.github/workflows/ci.yml`  
**Problem Description:** `exit-code: "0"` means critical/high vulnerabilities do **not** fail the build.  
**Root Cause:** Explicit non-failing exit code.  
**Recommended Solution:** Change to `exit-code: "1"` for CI-blocking vulnerability detection.  

---

### Issue INF-013: Docker.yml Missing Vulnerability Scanning
**Severity:** MEDIUM  
**Component Affected:** `.github/workflows/docker.yml`  
**Problem Description:** No vulnerability scanning before pushing images to registry.  
**Root Cause:** Missing scan step.  
**Recommended Solution:** Add Trivy/Grype image scan between build and push; fail on CRITICAL/HIGH.  

---

### Issue INF-014: Vercel Missing Security Headers
**Severity:** MEDIUM  
**Component Affected:** `vercel.json` (root), `frontend/vercel.json`  
**Problem Description:** No `X-Frame-Options`, `Strict-Transport-Security`, or `Content-Security-Policy` headers defined.  
**Root Cause:** Headers array omitted.  
**Recommended Solution:** Add headers block with security headers.  

---

### Issue INF-015: Nginx Missing `X-Tenant-ID` Forwarding
**Severity:** MEDIUM  
**Component Affected:** `nginx/beta.conf`  
**Problem Description:** Does not forward `X-Tenant-ID` header to the backend. The backend middleware relies on it.  
**Root Cause:** Missing `proxy_set_header` directive.  
**Recommended Solution:** Add `proxy_set_header X-Tenant-ID $http_x_tenant_id;` in API location blocks.  

---

### Issue INF-016: Nginx CSP Weakens Application CSP
**Severity:** HIGH  
**Component Affected:** `nginx/beta.conf`  
**Problem Description:** Nginx adds a hardcoded CSP header with **`'unsafe-inline'`** and **`'unsafe-eval'`** for scripts, overriding stricter FastAPI middleware CSP.  
**Root Cause:** Nginx config was loosened to support Tailwind CDN and inline scripts.  
**Recommended Solution:** Remove CSP from nginx and let the application middleware handle it.  

---

## SECURITY & PERFORMANCE DEEP-DIVE FINDINGS

---

### Issue SEC-001: Hardcoded Production Superadmin Credentials
**Severity:** CRITICAL  
**Component Affected:** `backend/scripts/seed_superadmin.py` (lines 34-35)  
**Problem Description:** Superadmin email and password are hardcoded in source code:
```python
SUPERADMIN_EMAIL = "ibrahim@new-aeon.com"
SUPERADMIN_PASSWORD = "Newaeon@2026"
```
**Root Cause:** Seed script reads from env vars with hardcoded fallbacks "for dev only," but these are production-grade credentials committed to version control.  
**Recommended Solution:** Remove hardcoded strings. Require environment variables and fail fast if missing:
```python
SUPERADMIN_EMAIL = os.environ["SUPERADMIN_EMAIL"]
SUPERADMIN_PASSWORD = os.environ["SUPERADMIN_PASSWORD"]
```

---

### Issue SEC-002: Committed Production Secrets Template
**Severity:** CRITICAL  
**Component Affected:** `.env.production.template` (root)  
**Problem Description:** The file was blocked by the sensitive-file scanner, indicating it contains real credentials or production secrets. Git history shows it was added in commit `4930b8f`.  
**Root Cause:** Production template file committed to git instead of generated at deploy time.  
**Recommended Solution:**
1. Rotate any credentials that may have been in this file.
2. Add `.env.production*` to `.gitignore`.
3. Use CI/CD secret injection mechanism.  

---

### Issue SEC-003: Refresh Token Reuse (No Rotation Blacklisting)
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 785-845)  
**Problem Description:** The `/refresh` endpoint decodes the refresh token, verifies the user, issues **new** tokens, but **never blacklists the old refresh token**. An attacker who steals a refresh token can use it repeatedly until it naturally expires (up to 7 days).  
**Root Cause:** Missing token rotation implementation.  
**Recommended Solution:** Blacklist the old refresh token's `jti` before issuing new tokens:
```python
await blacklist_token(token_data.refresh_token, payload)
```

---

### Issue SEC-004: Logout Does Not Invalidate Refresh Tokens
**Severity:** CRITICAL  
**Component Affected:** `backend/app/api/v1/endpoints/auth.py` (lines 848-888)  
**Problem Description:** Logout only blacklists the **access token** from the `Authorization` header. The refresh token remains fully valid and can continue to mint new access tokens.  
**Root Cause:** Logout handler does not accept or invalidate the refresh token.  
**Recommended Solution:** Require the refresh token in the logout request body and blacklist both tokens.  

---

### Issue SEC-005: Dependency Vulnerability — python-jose 3.5.0
**Severity:** CRITICAL  
**Component Affected:** `backend/requirements.txt` (line 35)  
**Problem Description:** `python-jose[cryptography]==3.5.0` is affected by **CVE-2024-33663** and **CVE-2024-33664** (algorithm confusion / key confusion attacks). The library is also unmaintained.  
**Root Cause:** Pinned to a vulnerable version.  
**Recommended Solution:** Replace `python-jose` with `PyJWT==2.10.1` or `joserfc`. Update `decode_token` and `create_access_token` to use the new library.  

---

### Issue SEC-006: PII Logged in Plaintext
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/cms.py` (line 491)  
**Problem Description:** Contact form submissions log raw email addresses:
```python
logger.info(f"Contact form submitted: {body.email}")
```
**Root Cause:** Direct f-string interpolation of PII into log messages.  
**Recommended Solution:** Log a hashed or masked version:
```python
logger.info("contact_form_submitted", email_hash=hash_pii_for_lookup(body.email))
```

---

### Issue SEC-007: File Upload MIME Type Spoofing
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/assets.py` (lines 77-82)  
**Problem Description:** Asset upload validates MIME type using `file.content_type`, which is **client-controlled**. A malicious user can upload a `.php` or `.exe` file with `Content-Type: image/jpeg`.  
**Root Cause:** No server-side file magic/signature validation.  
**Recommended Solution:** Validate actual file content using `python-magic`:
```python
import magic
detected = magic.from_buffer(contents, mime=True)
if detected not in ALLOWED_MIME_TYPES:
    raise HTTPException(400, "File content does not match declared type")
```

---

### Issue SEC-008: CORS Origin Wildcard Risk
**Severity:** HIGH  
**Component Affected:** `backend/app/core/config.py` (lines 201-219)  
**Problem Description:** `cors_origins_list` dynamically appends `frontend_url`. There is **no validation** preventing `CORS_ORIGINS="*"` or overly broad origins in production. Combined with `allow_credentials=true`, this allows any website to make authenticated cross-origin requests.  
**Root Cause:** `enforce_production_safety` validator checks secret keys but not CORS origins.  
**Recommended Solution:** Add a production validator that rejects `*`, `http://*`, and empty origins when `app_env == "production"`.  

---

### Issue SEC-009: Rate Limiter Proxy Trust Gaps
**Severity:** MEDIUM  
**Component Affected:** `backend/app/middleware/rate_limit.py` (lines 233-237)  
**Problem Description:** Trusted proxy IP list uses string `startswith` checks. Cloud providers use IPs outside standard private ranges. If deployed behind a cloud load balancer not in the hardcoded list, rate limiting applies to the load balancer IP.  
**Root Cause:** Hardcoded private ranges instead of configurable trusted proxies.  
**Recommended Solution:** Make trusted proxies configurable via env var (`TRUSTED_PROXIES`).  

---

### Issue SEC-010: WhatsApp Webhook Verify Token Default Empty
**Severity:** MEDIUM  
**Component Affected:** `backend/app/core/config.py` (line 151-154)  
**Problem Description:** `whatsapp_verify_token` defaults to empty string `""`. An empty verify token makes webhook verification trivially bypassable.  
**Root Cause:** Default is empty instead of a required value.  
**Recommended Solution:** Default to `None` and raise `ValueError` in production if `whatsapp_phone_number_id` is set but `whatsapp_verify_token` is missing or too short.  

---

## PERFORMANCE FINDINGS

---

### Issue PERF-001: Dashboard Overview Loads ALL Campaigns (Unbounded Query)
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/dashboard.py` (lines 528-536)  
**Problem Description:** `_build_dashboard_overview` executes `select(Campaign)` with **no `LIMIT`**. For enterprise tenants with 10,000+ campaigns, this loads the entire table into memory.  
**Root Cause:** Missing pagination on campaign queries used for overview stats.  
**Recommended Solution:** Use aggregated SQL queries instead of ORM object loading.  

---

### Issue PERF-002: No Query Result Caching
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/dashboard.py`, `analytics.py`  
**Problem Description:** Expensive dashboard overview and analytics endpoints recompute aggregates on every request. There is **no Redis-based query result caching**.  
**Root Cause:** Cache-aside pattern not implemented.  
**Recommended Solution:** Add a Redis cache decorator for endpoint responses:
```python
@cache_response(ttl=300, key_prefix="dashboard:overview")
async def get_dashboard_overview(...):
```

---

### Issue PERF-003: CDP Profile Export Allows 50,000 Record Exports
**Severity:** HIGH  
**Component Affected:** `backend/app/api/v1/endpoints/cdp.py` (lines 1907-1909)  
**Problem Description:** `/audiences/export` allows `limit=50000`. 50k profiles with `include_identifiers=true` triggers massive JSON serialization and memory usage.  
**Root Cause:** High upper bound on export limit without streaming response.  
**Recommended Solution:**
1. Reduce max limit to 10,000.
2. Implement streaming CSV/JSON generation using `StreamingResponse`.
3. Offload large exports to Celery background task.  

---

### Issue PERF-004: Frontend Memory Leak — Signup OTP Countdown
**Severity:** MEDIUM  
**Component Affected:** `frontend/src/views/Signup.tsx` (lines 83-94)  
**Problem Description:** `startOTPCountdown` creates a `setInterval` that is only cleared when the counter reaches 0. If the user navigates away, the interval continues running.  
**Root Cause:** Missing cleanup in `useEffect` for the interval.  
**Recommended Solution:** Store interval ID in a ref and clear it in a `useEffect` cleanup.  

---

### Issue PERF-005: Nginx Missing Static Asset Cache Headers
**Severity:** MEDIUM  
**Component Affected:** `nginx/beta.conf`  
**Problem Description:** Nginx config serves the frontend SPA without `Cache-Control`, `Expires`, or `ETag` headers for static JS/CSS assets. Every page reload re-fetches all chunks.  
**Root Cause:** No `location` block for `dist/assets/` with long-term caching.  
**Recommended Solution:** Add cache headers for hashed assets:
```nginx
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

### Issue PERF-006: PDF Generation Bundle Bloat
**Severity:** MEDIUM  
**Component Affected:** `frontend/vite.config.ts` (line 37)  
**Problem Description:** `jspdf` and `html2canvas` are bundled together in `vendor-pdf`. These libraries are large (~500KB+ combined) and may not be needed on initial page load.  
**Root Cause:** Manual chunking groups them together but doesn't lazy-load the route.  
**Recommended Solution:** Use dynamic imports for PDF export functionality:
```ts
const { jsPDF } = await import('jspdf')
```

---

## REMEDIATION ROADMAP

### Sprint 1 (Week 1): CRITICAL Security & Data Integrity — DO NOT DEPLOY WITHOUT THESE

| Priority | Issue ID | Description | Owner |
|----------|----------|-------------|-------|
| P0 | SEC-001, SEC-002 | Rotate all hardcoded/committed credentials | DevOps |
| P0 | SEC-005 | Replace python-jose with PyJWT | Backend |
| P0 | SEC-003, SEC-004 | Implement refresh token rotation and logout invalidation | Backend |
| P0 | BE-001 | Fix X-Tenant-ID header spoofing | Backend |
| P0 | API-001, API-002, API-003 | Add authentication to unprotected endpoints (Meta CAPI, EMQ v2) | Backend |
| P0 | INF-004, INF-005 | Remove hardcoded passwords from start.sh and seed-data.sql | DevOps |
| P0 | INF-003 | Fix SQL injection in load_datasets.py | Backend |
| P0 | BE-003, BE-004 | Fix double-commit anti-pattern | Backend |
| P0 | DB-004 | Audit soft-delete coverage and add to critical tables | Backend / DBA |

### Sprint 2 (Week 2): HIGH Priority — API Contract, Auth Hardening, Frontend Fixes

| Priority | Issue ID | Description | Owner |
|----------|----------|-------------|-------|
| P1 | FE-001..FE-006 | Fix API path mismatches (insights, autopilot, trustLayer, featureFlags, dashboard, campaigns) | Frontend |
| P1 | FE-007..FE-018 | Create missing API client files (12 files) | Frontend |
| P1 | API-005 | Add batch size limits to CAPI event ingestion | Backend |
| P1 | BE-009 | Add SSRF protection to webhook test endpoint | Backend |
| P1 | BE-014 | Add rate limiting to forgot-password, verify-email, resend-verification | Backend |
| P1 | BE-015 | Fix soft-deleted user access in users.py | Backend |
| P1 | API-023, API-024 | Fix API keys and webhooks router permissions | Backend |
| P1 | BE-016 | Fix superadmin raw SQL column interpolation | Backend |
| P1 | INF-001 | Fix Dockerfile.frontend to run as non-root | DevOps |
| P1 | INF-002 | Fix Docker Compose weak passwords and exposed ports | DevOps |
| P1 | INF-010 | Make migration failures fatal in start.sh | DevOps |

### Sprint 3 (Week 3): MEDIUM Priority — Database Integrity, Performance, Reliability

| Priority | Issue ID | Description | Owner |
|----------|----------|-------------|-------|
| P2 | DB-005..DB-012 | Add missing indexes to FK and query columns | Backend / DBA |
| P2 | DB-010 | Migrate financial columns from Integer to BigInteger | Backend / DBA |
| P2 | DB-014 | Fix migration downgrade enum drops | Backend |
| P2 | BE-005 | Fix Celery event loop creation | Backend |
| P2 | BE-010 | Add Redis connection pooling to publish_event | Backend |
| P2 | BE-011 | Fix N+1 queries in superadmin portfolio | Backend |
| P2 | BE-006 | Add pagination/aggregation to insights endpoints | Backend |
| P2 | PERF-001..PERF-003 | Fix unbounded queries and add caching | Backend |
| P2 | FE-021..FE-023 | Replace console.error/log placeholders with toast notifications | Frontend |
| P2 | FE-024..FE-027 | Fix TypeScript types (any casts, role mismatches) | Frontend |
| P2 | INF-011, INF-012 | Fix CI/CD action versions and Trivy exit code | DevOps |

### Sprint 4 (Week 4): LOW Priority — Polish, Optimization, Documentation

| Priority | Issue ID | Description | Owner |
|----------|----------|-------------|-------|
| P3 | BE-018 | Remove unnecessary `await db.refresh()` calls | Backend |
| P3 | FE-028..FE-030 | Fix state management anti-patterns | Frontend |
| P3 | FE-033 | Add ErrorBoundary to all routes | Frontend |
| P3 | FE-034..FE-035 | Fix and expand E2E tests | Frontend |
| P3 | INF-014..INF-016 | Add security headers to Vercel and nginx | DevOps |
| P3 | DB-013 | Standardize all models on `mapped_column` | Backend |
| P3 | BE-021 | Add tenant_id filters to changelog and client assignments | Backend |
| P3 | PERF-004..PERF-006 | Fix frontend memory leaks and bundle optimization | Frontend |

---

## APPENDIX A: AUDIT COMMANDS REFERENCE

```bash
# Backend tests baseline
cd backend && pytest tests/ -v --tb=short

# Frontend build baseline
cd frontend && npm run build

# Type check
cd frontend && npx tsc --noEmit

# E2E baseline
cd frontend && npx playwright test --reporter=line

# Docker security scan
trivy image stratum-ai-backend:latest
trivy image stratum-ai-frontend:latest

# Alembic status
cd backend && alembic current && alembic history --verbose

# Redis auth check (should fail without password)
redis-cli -h localhost -p 6379 KEYS '*'

# Secret scan
gitleaks detect --source . --verbose
```

## APPENDIX B: POSITIVES & GOOD PRACTICES OBSERVED

1. **Vite Code Splitting**: Excellent manual chunking strategy in `vite.config.ts`.
2. **Load Tests**: Valid k6 scripts exist in `tests/load/` with smoke, load, stress, spike, and soak scenarios.
3. **Password Security**: Bcrypt truncation fix implemented (72-byte limit handled in `security.py`).
4. **PII at Rest**: Email and full name are encrypted via Fernet/PBKDF2 in the database.
5. **Rate Limiting**: Redis-backed sliding window with graceful in-memory fallback.
6. **Login Protection**: Account lockout after 5 failed attempts, with Redis TTL cleanup.
7. **JWT Blacklisting**: Redis-backed blacklist with automatic TTL expiry.
8. **CSP Middleware**: Environment-aware CSP (strict in production, relaxed in dev).
9. **Health Checks**: `/health`, `/health/ready`, `/health/live` endpoints present.
10. **Structured Logging**: `structlog` used consistently with JSON format in production.

---

*End of Report*
*Audit completed on 2026-04-23*
*Total unique issues documented: 180+*
*Critical issues requiring immediate action: 28*
