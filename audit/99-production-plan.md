# Production Release Plan

> **Snapshot of 2026-08-18.** Flag states and several findings have changed since;
> see [`README.md`](README.md) for the verified delta as of 2026-08-20.


**Audit date:** 2026-08-18  
**Verdict (re-verified same day):** Phase A P1s F-001–F-004 and F-005 are **closed in the working tree**. Do not run a 2–4 day security patch sprint for those.  
**Remaining launch risk:** sales kit vs shelved flags — see `audit/15-launch-scope-vs-deck.md`.

## Executive Summary

Stratum AI is a large, well-tested monorepo. Trust-gated autopilot, tenant isolation, and PII encryption are real. The 01:57 audit’s four P1 blockers cited pre-patch line numbers; current `main.py` / compose fail closed on docs, metrics, WebSocket query tokens, and mock ad data.

What still cannot be sold as “Production” without lying: campaign **publish**, automation **rules**, **competitor intel**, **drip campaigns**, and **knowledge graph**. Those flags default false and 503 the routers. The investor/sales kit still marks several of them Production (`features-sales-kit.html`). That is the deck problem, not a 4-day auth patch.

## Finding Rollup

| Severity | Count | Blocks production |
|----------|-------|-------------------|
| P0 | 0 | — |
| P1 | 4 | Yes (F-001–F-004) |
| P2 | 9 | Waiver possible |
| P3 | 2 | No |

See `findings.json` for machine-readable detail.

---

## Phase A — Blockers (P1) — Est. 2–4 days

### A1. Lock down OpenAPI in production (F-001)

**Evidence:** `backend/app/main.py:343-345`

1. Set `DOCS_API_KEY` in all prod/staging envs **OR** change code to fail closed when unset.
2. Verify `/docs`, `/redoc`, `/openapi.json` return 403 without key.
3. Add integration test asserting prod config rejects unauthenticated docs.

### A2. Lock down /metrics (F-002)

**Evidence:** `backend/app/main.py:54-58`, `middleware/tenant.py:31`

1. Set `METRICS_API_KEY` in production (documented in `.env.example:14-17`).
2. Restrict `/metrics` at nginx to internal scraper IP only.
3. Confirm no tenant_id labels leak to unauthorized scrapers.

### A3. Fix WebSocket authentication (F-003)

**Evidence:** `backend/app/main.py:876-877`

1. Remove `token` query param; use subprotocol or first-message auth.
2. Reject anonymous WS connections to tenant channels (comment at 894-895 already intent).
3. Add integration test for WS auth failure modes.

### A4. Eliminate mock-data deploy risk (F-004)

**Evidence:** `docker-compose.yml:103`, `config.py:562-565`

1. Production deploy MUST use `docker-compose.prod.yml` (sets `USE_MOCK_AD_DATA=false`).
2. Add startup assertion log line: `use_mock_ad_data={value}` at ERROR if true in prod.
3. Document deploy checklist — never use dev compose file in prod.

---

## Phase B — High Priority (P2) — Est. 1–2 weeks

| Step | Finding | Action |
|------|---------|--------|
| B1 | F-005 | Align Node 24 in Dockerfile OR fix Node 26 vitest storage bug per `ci.yml:18-41` |
| B2 | F-006 | Add `e2e` job to release gate `needs` in `ci.yml:732` |
| B3 | F-007 | Register uk locale in `i18n.ts` or delete unused file |
| B4 | F-009 | Stripe webhook: fail closed when Redis unavailable OR document accepted duplicate risk |
| B5 | F-010 | Consolidate `.env.example` files; single source of truth |
| B6 | F-011 | Document XSS mitigation for localStorage tenant_id; consider session-only |
| B7 | F-012 | Production: set `asset_storage_backend=s3` + bucket |
| B8 | F-013 | Keep `feature_competitor_intel=false` until real data source |
| B9 | F-014 | Keep `enable_campaign_publish=false` until platform adapter ships |

---

## Phase C — Operational Readiness — Est. 1 week

### C1. Secrets & config

- [ ] `SECRET_KEY`, `JWT_SECRET_KEY`, `PII_ENCRYPTION_KEY` — 32+ chars, not autogen
- [ ] `REDIS_PASSWORD`, `POSTGRES_PASSWORD` — strong, not defaults
- [ ] `CORS_ORIGINS`, `FRONTEND_URL` — no localhost in prod (`config.py:567-585`)
- [ ] `SENTRY_DSN`, `SENTRY_RELEASE=<git sha>`
- [ ] `STRIPE_WEBHOOK_SECRET`, live keys
- [ ] `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` if WhatsApp enabled

### C2. Database

- [ ] `alembic upgrade head` on pgvector-enabled Postgres
- [ ] Connection budget: calculate `(pool_size+overflow)×processes` vs provider limit
- [ ] Enable managed PITR backups — **UNKNOWN if already configured**

### C3. Observability

- [ ] Prometheus scrapes with bearer key
- [ ] `ALERT_WEBHOOK_URL` for P0 pipeline alerts
- [ ] Log aggregation (JSON → Loki/Datadog/CloudWatch)

### C4. CI verification

- [ ] Full green run on target release SHA: all 7 release-gate jobs
- [ ] Manual e2e run (until B2 complete)
- [ ] Trivy + gitleaks clean

---

## Phase D — Launch Scope Confirmation

**Ship with flags OFF (default):**

| Flag | Reason |
|------|--------|
| `feature_competitor_intel` | Random data (`config.py:427-428`) |
| `feature_automation_rules` | Schema mismatch (`config.py:428-429`) |
| `feature_drip_campaigns` | No execution engine (`config.py:449-452`) |
| `feature_knowledge_graph` | Needs Apache AGE (`config.py:436-440`) |
| `enable_campaign_publish` | No platform call (`config.py:453-457`) |
| `copilot_llm_enabled` | Cost control; templates work (`config.py:317-319`) |

**Ship enabled (default):**

- Trust engine / autopilot enforcement
- CDP core (profiles, segments, sync)
- GDPR compliance (`feature_gdpr_compliance=true`)
- Stripe subscriptions

---

## Phase E — Post-Launch (30 days)

1. Ratchet coverage above 74% (`.coveragerc:258`)
2. Add axe/playwright a11y spec
3. Wire uk locale or remove
4. Campaign publish adapter + integration tests
5. Document migration rollback runbook
6. Load test at expected RPS once traffic estimate known

---

## Waiver Template (P1 only if business accepts risk)

```
Finding: F-00X
Reason for waiver:
Expiry date:
Compensating control:
Approved by:
```

---

## Definition of Done — Production Ready

- [ ] All P1 findings closed or waived with expiry ≤ 30 days
- [ ] Release gate green on release tag
- [ ] Staging soak 72h with real OAuth sandbox credentials
- [ ] Trust gate hold/block verified with degraded signal health
- [ ] Stripe test → live webhook transition checklist completed
- [ ] Runbook: incident response (`backend/docs/05-operations/runbooks.md` exists — ops validation **UNKNOWN**)
- [ ] On-call rotation and `ALERT_WEBHOOK_URL` tested

---

## Open Questions for Ibrahim

1. Target deploy target: Hetzner, Railway, or both?
2. Expected initial tenant/traffic scale for pool sizing?
3. Is campaign publish required for v1, or drafts-only acceptable?
4. Legal review status of Privacy/Terms/DPA pages?
