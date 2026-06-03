# Stratum AI — Enterprise System Features Audit

**Date:** 2026-05-30
**Branch:** `claude/system-features-audit-DiYfj`
**Scope:** Every system feature audited end-to-end (frontend view → API client → backend endpoint → service/model/worker → tests).
**Method:** 9 parallel domain auditors, each grounded in `file:line` evidence. The highest-severity, falsifiable claims were independently re-verified by the lead auditor (noted ✅ below). Nothing here is assumed — where something could not be confirmed it is marked **UNVERIFIED**.

---

## 1. Executive Verdict

Stratum AI is a **genuinely large, substantially-built platform** — ~67 wired API endpoint domains, ~50 frontend views, ~40 service modules, 1,867 test functions, 49 migrations. It is **not** a skeleton or a demo: the hard algorithmic cores (Markov/Shapley attribution, sklearn ML training, EMQ math, signal-health scoring, identity resolution, OAuth token exchange, audience PII hashing, autopilot enforcement, Stripe billing) are **real implementations**, not stubs.

**However, it is not production-ready as a whole.** The failure pattern is consistent and important: **strong components are let down by wiring, enforcement, and persistence gaps.** Repeatedly, an excellent backend is not reached by the frontend (route mismatches), a real engine is never triggered by a scheduler (orphaned workers), security machinery is defined but never applied (feature gates, MFA, API-key auth), or data is computed but never persisted (audit log, profit metrics, reallocation plans).

**Overall platform readiness: ~62% — "advanced beta."** Roughly one-third of features are go-live ready or close (A/B+). One-third work but have material gaps (B/C). One-third are stubs, broken, or unenforced (D/F) and would mislead a customer if shipped as-is.

| Severity                                  | Count | Examples                                                                                                                   |
| ----------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------- |
| 🟢 Ship-ready / near (A / A-)             | ~9    | OAuth, Audience Sync, CDP core, Attribution, Launch Readiness, CMS                                                         |
| 🟡 Works, material gaps (B / B+)          | ~16   | Payments, WhatsApp, Dashboard, RBAC, Multi-tenancy, Autopilot Enforcement                                                  |
| 🟠 Real but unenforced/partial (C)        | ~14   | EMQ, Rules, API Keys, Feature Flags, Reporting, Webhooks, QA-Fixes                                                         |
| 🔴 Stub / broken / non-functional (D / F) | ~14   | Campaign publish, Drip, Push, Developer Portal, Compliance, Audit Logging, Knowledge Graph, Competitor Intel, MFA-at-login |

---

## 2. Cross-Cutting Blockers (fix these once, fix many features)

These are systemic — each one breaks multiple features and should be prioritized over individual feature fixes.

### P0 — Security / data-integrity (must fix before any production traffic)

| #    | Blocker                                                                                                                                                                                                                                                                                | Evidence                                                                                            | Features affected                                 |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| P0-1 | **MFA is never enforced at login.** `/login` issues full tokens without any TOTP check; `Login.tsx` has no MFA step. The entire MFA subsystem is unreachable.                                                                                                                          | `auth.py:535,611`; `mfa.py` `/validate` has no caller                                               | Authentication, MFA                               |
| P0-2 | **Cross-tenant IDOR in multiple endpoints.** `tenants.py` admin routes act on arbitrary `tenant_id` with no caller-match; `newsletter.py` ignores `tenant_id` entirely (✅ 0 occurrences); `predictions.py`/`analytics_ai.py`/`copilot.py` default to **tenant 1** on missing context. | `tenants.py:149,268,342`; `newsletter.py` (0× tenant_id ✅); `predictions.py:139`; `copilot.py:203` | Tenancy, Newsletter, Predictions, Copilot         |
| P0-3 | **Audit logging is broken end-to-end.** Middleware is registered and pushes to Redis `audit_log_queue`; worker reads `audit:log:queue` — **keys never match, events silently dropped** (✅ verified). No tamper-evidence (no hash chain) despite the claim.                            | `middleware/audit.py:239` vs `workers/tasks/audit.py:33` ✅; `base_models.py:899`                   | Compliance, SuperAdmin, all mutations             |
| P0-4 | **API keys cannot authenticate anything.** CRUD mints keys, but no middleware/dependency ever validates an inbound key; `verify_api_key` is never called in production code.                                                                                                           | `api_keys.py`; `security.py:290` (no callers)                                                       | API Keys, Developer Portal                        |
| P0-5 | **Tier / feature gating is inert.** `FeatureGate`/`TierGate`/`require_feature` are applied to **0** endpoints (✅ 0 usages). A free/expired tenant can call enterprise features.                                                                                                       | `core/feature_gate.py` (0× in `app/api/` ✅)                                                        | Subscription, Feature Flags, all premium features |
| P0-6 | **Plaintext secrets at rest.** Slack `webhook_url` stored plaintext; license HMAC fallback uses hardcoded `"dev-secret-change-me"` with no prod guard.                                                                                                                                 | `models/settings.py:308`; `licensing.py:259`                                                        | Slack, Licensing                                  |

### P1 — Functional integrity (feature claims are false until fixed)

| #    | Blocker                                                                                                                                                                                                                                                                      | Evidence                                                                                                                                                                                                                                                                                                                                                 | Features affected                                       |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| P1-1 | **Frontend↔backend route-prefix mismatches → 404s on wired UI.** The API client injects tenant as a header, never into the path, but several backend routers use `/tenant/{tenant_id}/...` prefixes. (✅ verified for autopilot/trust.)                                      | `autopilot.ts:93` `/autopilot/status` vs `autopilot.py:25` `/tenant/{id}/autopilot`; trust-layer, pacing, CRM, competitors, knowledge-graph clients                                                                                                                                                                                                      | Autopilot, Trust Layer, Pacing, CRM, Competitors, KG    |
| P1-2 | **Orphaned workers / schedulers.** Real engines exist but nothing triggers them: reporting scheduler (no beat task), drip campaigns (no worker), profit `DailyProfitMetrics` (no writer), campaign-builder beat (commented out), CAPI delivery logger + DLQ (never invoked). | `celery_app.py:74`; `scheduler.py`; `campaign_builder_tasks.py:404`; `delivery_logger.py`/`dead_letter_queue.py` (0 call sites)                                                                                                                                                                                                                          | Reporting, Drip, Profit, Campaign Builder, CAPI         |
| P1-3 | **Runtime crash bugs (NameError/SyntaxError) on real paths.**                                                                                                                                                                                                                | `competitor_scraper.py:243` SyntaxError (✅ module won't import); `emq_v2.py:302` (`status` not imported); `offline_conversion_service.py:983` (`statistics` not imported); `cogs_service.py:97` (`timedelta`); `campaign_builder.py:301` (`logger`); `trust_layer.py:58` (`.limit()` on HTTPException); `stratum/core/autopilot.py:697` (reversed args) | Competitors, EMQ, CAPI, Profit, Campaign Builder, Trust |
| P1-4 | **In-memory state that breaks multi-worker / restart.** CAPI connectors, EMQ measurement store, offline-conversion batches, budget-reallocation plans, drip store, push subscriptions, Stripe webhook idempotency, audit dedup — all module-global dicts.                    | `capi_service.py:68`; `budget_reallocation_service.py:172`; `drip_campaigns.py:143`; `stripe_webhook.py:37`                                                                                                                                                                                                                                              | CAPI, Pacing, Drip, Push, Payments                      |
| P1-5 | **Built-but-unwired / dual implementations (dead code creating confusion).** stratum ad-adapters never registered; two trust mechanisms (rich `TrustGate` bypassed by live path); legacy + AGE knowledge-graph services; embed-widgets backend never called by frontend.     | `register_default_adapters()` (0 startup calls); `autopilot/service.py:90`; `EmbedWidgets.tsx` (0 network calls)                                                                                                                                                                                                                                         | Adapters, Trust, KG, Embed Widgets                      |
| P1-6 | **Knowledge Graph undeployable.** Requires Apache AGE; `CREATE EXTENSION age` exists only in the **inactive** `backend/alembic/` tree while `alembic.ini` points at `backend/migrations/` (✅), and the `postgres:16-alpine` image has no AGE. All Cypher fails at runtime.  | `alembic.ini:7` ✅; `docker-compose.yml:6`; AGE not in requirements                                                                                                                                                                                                                                                                                      | Knowledge Graph                                         |

### P2 — Test & coverage debt

- CLAUDE.md mandates **90%+ coverage** for `core/`, `autopilot/`, `analytics/`. Reality: strong suites exist for CDP, Audience Sync, Campaign Builder (validates a stub), Auth, Analytics-logic, Copilot, Launch Readiness, CMS. **Near-zero tests** for: Payments/Stripe, Tier/Subscription, WhatsApp, Slack, Push, Profit, Assets, Campaigns CRUD, Newsletter, Drip, Embed, Onboarding, GDPR, Compliance, SuperAdmin, Webhooks, Feature Flags, Rules engine, Pacing, Markov/Shapley core math, ML training output.

---

## 3. Master Grading Table (every feature)

Grade = engineering completeness & correctness. Readiness% = distance to production for that feature in isolation.

### Domain 1 — Trust Engine / Autopilot / Rules / Pacing

| Feature                      | Grade | Ready% | One-line status                                                                               |
| ---------------------------- | ----- | ------ | --------------------------------------------------------------------------------------------- |
| Autopilot Enforcement Engine | B+    | 80     | Strongest in domain — real DB-backed enforcement, live executors, 46 tests; audit is log-only |
| Signal Health Calculation    | C+    | 60     | Real weighted calc, but a crash bug, stubbed history, 2–3 parallel implementations            |
| Trust Gate                   | C     | 55     | Sound algorithm but bypassed by live path + reversed-arg bug + route mismatch                 |
| Custom Rules Engine          | C+    | 62     | Real IFTTT engine; SEND_ALERT/NOTIFY_SLACK are no-ops; bypasses trust gate; untested          |
| Pacing / Budget Reallocation | D+    | 45     | Pacing real; reallocation non-persistent + no-op execute + route mismatches                   |

### Domain 2 — CDP / EMQ / CAPI

| Feature                            | Grade | Ready% | One-line status                                                                           |
| ---------------------------------- | ----- | ------ | ----------------------------------------------------------------------------------------- |
| CDP Profiles / Identity Resolution | A-    | 90     | Production-grade, tenant-scoped, well-tested                                              |
| CDP Segments                       | A-    | 88     | Real evaluator; sync runs in-request (scale risk)                                         |
| Computed Traits / RFM              | B+    | 85     | Real scoring; batch endpoints synchronous (timeout risk)                                  |
| Funnel / Cohort                    | B+    | 84     | Real funnels; cohort UI points to separate analytics endpoint                             |
| EMQ Calculation / Measurement      | C+    | 65     | Read path real; NameError bug + no-op autopilot-mode write + in-memory store              |
| CAPI Delivery + PII Hash + DLQ     | D+    | 45     | Real connectors+hashing, but `meta_capi` endpoints throw TypeError; DLQ/logging dead code |

### Domain 3 — Auth / MFA / Tenancy / Dev Portal

| Feature                         | Grade | Ready% | One-line status                                                                          |
| ------------------------------- | ----- | ------ | ---------------------------------------------------------------------------------------- |
| Login / JWT                     | B+    | 85     | Solid: rotation, blacklist, lockout, no PII in claims; **MFA not gated**                 |
| Password reset / Email verify   | B     | 80     | Real, Redis-backed; doesn't revoke sessions on reset                                     |
| MFA (TOTP)                      | D     | 45     | A-grade service, **never enforced at login** — unreachable                               |
| RBAC / Permissions              | B     | 80     | Real matrix + anti-escalation; 3 fragmented permission systems                           |
| API Keys                        | C     | 55     | Secure CRUD but **keys authenticate nothing** (no validator wired)                       |
| Multi-tenant isolation / RLS    | B     | 75     | Good middleware; `tenants.py` admin routes leak cross-tenant; app-level only (no PG RLS) |
| Tenant Provisioning / Licensing | C+    | 65     | Real provisioning; license HMAC default secret unguarded; no tests                       |
| Developer Portal                | F     | 20     | Hardcoded mock keys/webhooks; missing tables; broken SQL; no authz                       |

### Domain 4 — Analytics / Attribution / ML

| Feature                                             | Grade | Ready% | One-line status                                                         |
| --------------------------------------------------- | ----- | ------ | ----------------------------------------------------------------------- |
| Attribution (first/last/linear/time-decay/position) | A-    | 90     | Real math, persisted, best-authed                                       |
| Core Analytics / Metrics                            | A-    | 88     | Real aggregation, well-tested                                           |
| Anomaly Detection                                   | A-    | 88     | Textbook Z-score, tested                                                |
| AI Insights / Recommendations                       | B+    | 80     | Real heuristic engine (not LLM); "AI" branding overstates               |
| What-If Simulator                                   | B+    | 78     | Real ML-backed; depends on `.pkl` presence                              |
| Data-Driven Attribution (Markov/Shapley)            | B+    | 75     | Genuinely real math; zero unit tests on the core algorithms             |
| Predictions / LTV / Churn                           | B     | 68     | ROAS path real ML; LTV/churn are heuristics; tenant-default-1 leak      |
| ML Training Pipeline                                | D     | 40     | Real sklearn, but **unauthenticated + not tenant-scoped** upload/delete |

### Domain 5 — Integrations / OAuth / CRM / Competitors / KG

| Feature                             | Grade | Ready% | One-line status                                                                  |
| ----------------------------------- | ----- | ------ | -------------------------------------------------------------------------------- |
| OAuth Connect/Refresh (4 platforms) | A-    | 90     | Real token exchange, Fernet-encrypted, Redis CSRF, well-tested                   |
| Platform Sync / Data Pull           | B+    | 80     | Real, resilient (circuit breaker, backoff); thin tests                           |
| Ad Adapters / Action Execution      | C+    | 55     | Live path real but uses **global** token not per-tenant; duplicate dead adapters |
| CRM Sync + Writeback (4 providers)  | B-    | 60     | Clients excellent; only HubSpot has API routes; frontend routes 404              |
| Competitor Intel / Benchmarking     | D     | 25     | Worker uses random mock; the one real scraper has a **SyntaxError**; routes 404  |
| Knowledge Graph                     | D+    | 30     | Sophisticated design, **undeployable** (no AGE provisioning); untested           |

### Domain 6 — Campaign Builder / Audience / Profit / Assets

| Feature                      | Grade | Ready% | One-line status                                                        |
| ---------------------------- | ----- | ------ | ---------------------------------------------------------------------- |
| Audience Sync (4 platforms)  | A-    | 85     | **Real** hashed-PII upload, encrypted creds, plan limits, deep tests   |
| Campaigns CRUD / Management  | B+    | 80     | Real tenant-scoped CRUD + genuine platform sync                        |
| Assets / Creative Management | B-    | 60     | Secure upload; local-FS only (not S3); fatigue inputs unfed; no tests  |
| Profit / COGS                | C     | 45     | Real math + CSV; **crash on COGS update** + source table never written |
| Campaign Builder (publish)   | D     | 30     | **Fakes publish success** without contacting any platform; mock worker |

### Domain 7 — Payments / Reporting / Notifications / WhatsApp

| Feature                         | Grade | Ready% | One-line status                                                  |
| ------------------------------- | ----- | ------ | ---------------------------------------------------------------- |
| Notifications (in-app)          | B     | 80     | Real, properly scoped                                            |
| WhatsApp (Business API)         | B+    | 80     | Real Meta Graph API + HMAC-signed webhooks; no tests             |
| Slack integration               | B     | 78     | Real webhook + Block Kit; webhook URL stored plaintext           |
| Payments / Stripe               | B     | 75     | **Signature-verified webhooks**; in-memory idempotency; no tests |
| Reporting                       | C+    | 60     | Real PDF/delivery; **scheduler orphaned** (won't auto-fire)      |
| Subscription / Tier enforcement | D     | 40     | Informational only; **enforcement applied nowhere**              |
| Push notifications (Web Push)   | F     | 15     | Full stub: in-memory, fabricated delivery, fake VAPID key        |

### Domain 8 — CMS / Newsletter / Drip / Embed / Onboarding / Dashboard

| Feature                           | Grade | Ready% | One-line status                                                          |
| --------------------------------- | ----- | ------ | ------------------------------------------------------------------------ |
| CMS (content + RBAC + publishing) | A-    | 90     | Full CRUD, real 8-role matrix, 173 tests                                 |
| Landing CMS                       | B     | 80     | Real public read API; no tests                                           |
| Dashboard Overview                | B+    | 75     | Core real + honest mock signaling; some aux endpoints random-synthesized |
| Onboarding + Agent                | B-    | 70     | Form onboarding real/persisted; "agent" is scripted, not LLM             |
| Newsletter                        | C+    | 55     | Well-built send/track; **cross-tenant IDOR**; no tests                   |
| Embed Widgets                     | C     | 50     | A-grade secure backend; **frontend fully mocked, never calls it**        |
| Drip Campaigns                    | D     | 20     | In-memory simulation; no DB, no worker, no real send                     |

### Domain 9 — Copilot / GDPR / SuperAdmin / Launch / Audit / Ops

| Feature                       | Grade | Ready%   | One-line status                                                              |
| ----------------------------- | ----- | -------- | ---------------------------------------------------------------------------- |
| Launch Readiness              | A     | 92       | Complete: 126 real checklist items, phase-gating, audited, 33 tests          |
| AI Copilot (RAG + streaming)  | A-    | 80 / 0\* | Real Claude+pgvector RAG; \*ships off (no keys, flags False, index empty)    |
| SuperAdmin Analytics          | B+    | 72       | Real cross-tenant fact-table aggregation                                     |
| GDPR (export/erasure/consent) | B+    | 78       | Real export/anonymize; lacks explicit route auth + tests                     |
| Audit Services (measurement)  | B+    | 75       | Substantial real services, rate-limited                                      |
| Memory-Debug                  | B     | 75       | Correctly prod-gated, superadmin-only                                        |
| SuperAdmin                    | B     | 70       | Real cross-tenant reads; some metrics honestly stubbed-to-0                  |
| Changelog                     | B     | 68       | Solid backend; frontend client unverified                                    |
| QA-Fixes                      | C+    | 55       | Detection real; remediation advisory-only despite "one-click" framing        |
| Webhooks (outbound)           | C+    | 50       | CRUD + SSRF guard; no dispatcher, unsigned sends → can't deliver real events |
| Feature Flags                 | C     | 45       | Management real; **not enforced anywhere**                                   |
| Audit Logging (middleware)    | D     | 35       | **Pipeline broken** (key mismatch); no tamper-evidence                       |
| Compliance Dashboard          | D     | 30       | RBAC/retention are facades; audit-search query broken vs real schema         |

---

## 4. Security Findings (consolidated)

**Strengths (genuinely well done):** bcrypt + 72-byte truncation, JWT HS256 with refresh rotation + Redis blacklist + login lockout, no PII in JWT claims, Fernet PII encryption with per-tenant salt, `secrets` for tokens, `hmac.compare_digest` constant-time compares, JWT `none`-algorithm attack test, production secret-value rejection, Stripe + WhatsApp webhook signature verification, embed-widget token theft detection, webhook SSRF guard, mock-data forbidden in production env.

**Must-fix before go-live:**

1. Enforce MFA at login (P0-1).
2. Close cross-tenant IDOR: `tenants.py`, newsletter, `predictions`/`analytics_ai`/`copilot` tenant-`1` fallbacks (P0-2).
3. Gate ML-training endpoints with auth + superadmin + tenant-namespaced paths + upload validation (Domain 4).
4. Wire feature/tier/subscription enforcement (P0-5).
5. Encrypt Slack webhook URL; guard license HMAC secret in prod (P0-6).
6. Add API-key inbound authenticator (P0-4).
7. Add `redirect_uri` allowlist on OAuth callback; sign outbound webhook payloads.

---

## 5. What's Needed to Go Live — Prioritized Roadmap

**Phase 0 — Security & data integrity (blocking):** P0-1…P0-6 above + ML-training auth.

**Phase 1 — Make claimed features actually function:**

- Fix the route-prefix mismatches (P1-1) — one client-side path convention or align router prefixes.
- Wire the orphaned workers (P1-2): reporting beat task, drip worker, profit `DailyProfitMetrics` writer, campaign-publish task, CAPI delivery logger + DLQ.
- Fix the 7 runtime crash bugs (P1-3).
- Replace in-memory state with DB/Redis (P1-4) for CAPI, reallocation, drip, push, Stripe idempotency.
- Implement real campaign publish (stop faking success).
- Provision Apache AGE (or move KG migration into the active tree + AGE-enabled image) or shelve KG (P1-6).
- Fix competitor worker to use the real scraper/market_proxy (and fix the SyntaxError).

**Phase 2 — Coverage & operationalization:**

- Add tests for the ~20 untested features (Payments, WhatsApp, Profit, Newsletter, GDPR, Compliance, SuperAdmin, Markov/Shapley, ML output, Rules, Pacing…).
- Set & document operational keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (+ flip Copilot flags + run doc-index), Stripe price IDs/webhook secret, per-platform OAuth app credentials, SendGrid, WeasyPrint native libs, S3 for assets.
- Reconcile dual implementations (trust mechanisms, KG, adapters); delete dead code.
- Wire Embed Widgets frontend to its backend.

**Phase 3 — Scale hardening:**

- Move synchronous in-request batch jobs (segment/trait/funnel/RFM compute, audience sync) to Celery.
- Add Postgres RLS as defense-in-depth behind the app-level tenant filters.
- Tamper-evident audit log (hash chain / HMAC) if compliance requires it.

---

## 6. Related Skills / Agents per Gap Cluster

The repo ships project skills and review subagents that map directly onto these gaps — use them to execute the roadmap consistently:

| Gap cluster                                                                                | Skill / Agent to use                                    |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| Route/auth/schema/audit/rate-limit on endpoints (Dev Portal, ML training, GDPR auth)       | `add-api-endpoint` skill; `api-endpoint-reviewer` agent |
| Orphaned workers / schedulers (reporting, drip, profit, campaign publish, CAPI DLQ, audit) | `add-celery-task` skill; `celery-task-reviewer` agent   |
| Cross-tenant IDOR (newsletter, tenants.py, tenant-1 fallbacks)                             | `tenancy-auditor` agent; `db-query-review` skill        |
| Trust-gate bypass / reversed-arg / rules-bypass-gate                                       | `trust-gate-reviewer` agent; `debug-gate` skill         |
| Plaintext secrets / token-at-rest / PII                                                    | `secret-leak-reviewer` agent; `security-review` skill   |
| KG AGE migration / audit-log schema mismatch / migrations                                  | `migration-auditor` agent                               |
| New/fixed platform integrations (competitor scraper, CRM endpoints, adapters)              | `add-platform-integration` skill                        |
| Signal-health drops / EMQ contribution                                                     | `signal-auditor` agent; `check-signal` skill            |
| New trust-gated automations                                                                | `add-automation` skill                                  |
| Frontend wiring (embed widgets, route mismatches, mock fallbacks)                          | `frontend-reviewer` agent                               |
| Pre-deploy verification (lint/tests/migrations/thresholds)                                 | `deploy-check` skill                                    |
| Production incidents (queue, gate stuck, pool)                                             | `incident-response` skill                               |

---

## 7. What I Could NOT Verify (honesty log)

- **Live external API behavior** — OAuth token exchange, platform sync field mappings, WhatsApp/Stripe/SendGrid against real services (all tests mock the SDKs).
- **Whether `.pkl` ML models ship in the deploy image** — ROAS/simulator/predictions fall back to constants if absent.
- **Whether fact tables are populated** — `FactSignalHealthDaily`, `FactAttributionVarianceDaily`, `DailyProfitMetrics`, `DailyPipelineMetrics` are read everywhere but the populating pipelines weren't all located.
- **Production env configuration** — which secrets/keys are actually set in the deployed environment.
- **Test pass rate** — the 1,867 tests were inventoried, not executed in this audit.
- **Test coverage** for GDPR, Compliance, SuperAdmin, Webhooks, Feature Flags, Changelog (none found in the named suites).
- **Whether `claude-haiku-4-5-20251001` is reachable** from the deploy environment.
- **CMS scheduled-publish beat task**, embed loader.js serving endpoint, onboarding-agent `complete` provisioning — not located.

These are tractable to close with environment access and a test run; flag any you want investigated next.
