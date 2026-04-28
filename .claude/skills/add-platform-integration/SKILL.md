---
name: add-platform-integration
description: Use when adding a new ad-platform or CRM integration to Stratum AI (e.g., LinkedIn Ads, Pinterest, Salesforce). Encodes the 5-step process for wiring a new source through OAuth, signal collection, health scoring, and the integration registry. Trigger when the user says "add X integration", "wire up Y platform", or creates a new directory under `backend/app/services/`.
---

# Add Platform Integration

Stratum AI integrates with external platforms via a uniform contract: OAuth → Collector → Signal → Health → Registry. Skipping any step leaves the integration partially wired and breaks the Trust Engine.

## The 5-step process

### 1. Service scaffold
Create `backend/app/services/<platform>/` with:

```
services/<platform>/
├── __init__.py
├── client.py            # Async HTTP client (httpx)
├── oauth.py             # OAuth provider implementation
├── collector.py         # Signal collector (Celery task entry)
├── schemas.py           # Pydantic models for platform payloads
├── mapper.py            # Platform → Stratum domain mapping
└── exceptions.py        # Platform-specific errors
```

The client must:
- Use `httpx.AsyncClient` with timeouts (connect=5s, read=30s).
- Honor rate limits (exponential backoff, respect `Retry-After`).
- Encrypt stored credentials with Fernet before write (`backend/app/core/security.py`).
- Never log raw access tokens.

### 2. OAuth registration
Edit `backend/app/services/oauth/factory.py`:
- Add the provider class.
- Register it in `OAUTH_PROVIDERS` dict.
- Add scopes constant in `backend/app/services/oauth/scopes.py`.
- Update `.env.example` with `<PLATFORM>_CLIENT_ID` and `<PLATFORM>_CLIENT_SECRET`.

### 3. Signal collector
In `backend/app/workers/`:
- Add a Celery task `collect_<platform>_signals(tenant_id, account_id)`.
- Schedule it in `backend/app/workers/celery_beat.py` (cadence per integration).
- The task must emit a `SignalEvent` per record into the canonical signal table.
- On failure: increment `event_loss` counter, structured-log the error, do NOT swallow.

### 4. Health calculation
Edit `backend/app/analytics/logic/signal_health.py`:
- Add the platform to `PLATFORM_REGISTRY`.
- Wire it into the existing 5-component score (EMQ / API Health / Event Loss / Platform Stability / Data Quality). Do NOT change the weights.
- Add API-health probe: latency, error rate, last successful sync timestamp.
- Verify `pytest backend/tests/unit/test_signal_health.py` still passes (weights sum to 1.0).

### 5. Integration registry + UI
- Register in `backend/app/services/integrations/registry.py` (display name, logo, supported features).
- Add migration if a new table or column is needed (see `migration-auditor` agent before merging).
- Add frontend connector card in `frontend/src/components/integrations/`.
- Document in `docs/integrations/<platform>.md` (auth flow, scopes, troubleshooting).

## Required tests

Every new integration must ship with:
- `backend/tests/unit/services/test_<platform>_client.py` — client retries, rate-limit handling, error parsing.
- `backend/tests/unit/services/test_<platform>_mapper.py` — payload → domain mapping edge cases.
- `backend/tests/integration/test_<platform>_oauth.py` — full OAuth round-trip with mocked provider.
- `backend/tests/integration/test_<platform>_signal_flow.py` — collector → signal → health.

Coverage target for new code: **90%+** (matches `core/`, `autopilot/`).

## Definition of Done

- [ ] All 5 steps complete, code committed
- [ ] OAuth round-trip works end-to-end against the platform sandbox
- [ ] Collector runs on schedule and produces SignalEvent rows
- [ ] Signal health formula updated; weights still sum to 1.0
- [ ] Integration appears in the UI registry with logo
- [ ] Docs written under `docs/integrations/<platform>.md`
- [ ] All tests pass: `make test`
- [ ] Lint clean: `make lint`
- [ ] No raw credentials in logs (grep -rn "<platform>_token" backend/)
- [ ] Migration audited (if schema changed) — invoke `migration-auditor`

## Anti-patterns

- ❌ Storing raw access tokens (must Fernet-encrypt before write)
- ❌ Hardcoding API endpoints (use config)
- ❌ Skipping rate-limit handling ("we'll add it later")
- ❌ Mixing collector and mapper logic in one file
- ❌ Adding a platform to health calc without updating its tests
- ❌ Adding the UI card before the backend OAuth works
