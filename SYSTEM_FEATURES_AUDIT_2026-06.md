# Stratum AI — Enterprise System Features Audit (Re-Audit)

**Date:** 2026-06-03
**Branch:** `claude/system-features-audit-DiYfj`
**Base commit:** `c348db1` (current `main`)
**Supersedes:** `SYSTEM_FEATURES_AUDIT_2026-05.md` (2026-05-30, commit `1589a42`)
**Scope:** Re-verification of every cross-cutting blocker and affected feature after the four remediation PRs merged (#292 audit, #293 security, #294 crash fixes, #295 lint/type). Every status below is re-checked against current `file:line` evidence by parallel domain auditors; the highest-severity claims were independently confirmed (✅).

---

## 0. What Changed Since 2026-05 (delta summary)

Four PRs merged into `main` since the prior audit:

| PR   | Title                                          | Net effect on this audit                                                                  |
| ---- | ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| #292 | docs: enterprise system features audit         | The prior audit document itself (no code).                                                |
| #293 | fix(security): close P0 cross-tenant isolation | **Partially** closes P0-2 — see below. 3 named endpoints fixed; the bug _class_ survives. |
| #294 | fix: repair 7 runtime crash bugs               | **Fully** closes P1-3. All 7 NameError/SyntaxError paths verified fixed. ✅               |
| #295 | chore(ci): lint + type gates (ruff/black/mypy) | Backend CI lint + type-check gates now green; one real bug fixed (`secrets` import).      |

**Headline:** Real, verifiable progress — the crash-bug class is gone and the codebase is now lint/type-clean — **but the marquee security blocker (cross-tenant tenant-`1` fallback) was only partially remediated.** The exact same `or 1` fallback pattern that #293 removed from `predictions/analytics_ai/copilot` **still exists in 10 `dashboard.py` endpoints**, so a customer with a null `tenant_id` JWT still reads tenant 1's data. Net security posture on P0-2 is improved but **not closed**.

### Readiness movement

**Overall platform readiness: ~62% → ~64% ("late beta").** The increment reflects: P1-3 fully resolved (+), CI hygiene/type-safety (+), three IDOR endpoints fixed (+) — offset by the discovery that the IDOR class persists elsewhere (the number didn't move more because the most dangerous blocker is only half-fixed, and four of five P0s are untouched).

| Cross-cutting blocker              | 2026-05 | 2026-06         | Evidence (current)                                                                              |
| ---------------------------------- | ------- | --------------- | ----------------------------------------------------------------------------------------------- |
| P0-1 MFA not enforced at login     | 🔴 open | 🔴 **open**     | `auth.py:644-654` issues tokens with no TOTP step; `mfa.py:349` never called                    |
| P0-2 Cross-tenant IDOR             | 🔴 open | 🟡 **partial**  | 3 endpoints fixed; **new**: `dashboard.py` 10× `or 1`, + 4 more (§2)                            |
| P0-3 Audit log key mismatch        | 🔴 open | 🔴 **open**     | `middleware/audit.py:258` `audit_log_queue` vs `workers/tasks/audit.py:40` `audit:log:queue` ✅ |
| P0-4 API keys authenticate nothing | 🔴 open | 🔴 **open**     | `security.py:291` `verify_api_key` — 0 call sites in `app/api/`                                 |
| P0-5 Feature/tier gating inert     | 🔴 open | 🔴 **open**     | `require_feature`/`FeatureGate`/`TierGate` — 0 usages in `app/api/`                             |
| P0-6 Plaintext secrets             | 🔴 open | 🔴 **open**     | `settings.py:330` plaintext `webhook_url`; `licensing.py:265` `dev-secret-change-me` unguarded  |
| P1-1 Route-prefix 404s             | 🔴 open | 🟡 **partial**  | autopilot/trust-layer/CRM still mismatch; pacing + competitors now MATCH                        |
| P1-2 Orphaned workers              | 🔴 open | 🔴 **open**     | reporting, drip, profit writer, campaign-builder beat, CAPI DLQ all unwired                     |
| P1-3 Runtime crash bugs            | 🔴 open | 🟢 **resolved** | All 7 verified fixed (§1) ✅                                                                    |
| P1-5 Built-but-unwired             | 🔴 open | 🔴 **open**     | `register_default_adapters()` never called; `EmbedWidgets.tsx` 0 network calls                  |
| P1-6 Knowledge Graph (AGE)         | 🔴 open | 🔴 **open**     | `CREATE EXTENSION age` only in inactive `alembic/` tree; not in image/reqs                      |

---

## 1. P1-3 — Runtime Crash Bugs: RESOLVED ✅

All seven crash paths from the prior audit now parse and import clean (`ast.parse`/`py_compile` pass on every file).

| #   | Bug (2026-05)                                    | Status   | Current evidence                                                        |
| --- | ------------------------------------------------ | -------- | ----------------------------------------------------------------------- |
| 1   | `competitor_scraper.py:243` SyntaxError          | resolved | `competitor_scraper.py:258` — now a valid inline comment; module parses |
| 2   | `emq_v2.py:302` `status` not imported            | resolved | `emq_v2.py:23` imports `status`; used at `:313`                         |
| 3   | `offline_conversion_service.py:983` `statistics` | resolved | `offline_conversion_service.py:31` `import statistics`                  |
| 4   | `cogs_service.py:97` `timedelta` not imported    | resolved | `cogs_service.py:14` imports `timedelta`; used `:100`                   |
| 5   | `campaign_builder.py:301` `logger` undefined     | resolved | `campaign_builder.py:39` `logger = get_logger(__name__)`                |
| 6   | `trust_layer.py:58` `.limit()` on HTTPException  | resolved | `trust_layer.py:58` clean `raise HTTPException(403, …)`                 |
| 7   | `stratum/core/autopilot.py:697` reversed args    | resolved | `autopilot.py:707` `evaluate(signal_health, action)` matches signature  |

**Consequence for feature grades:** Competitors, EMQ, CAPI, Profit, Campaign Builder, and Trust each lose their "won't import / crashes on real path" deduction (see §3).

---

## 2. P0-2 — Cross-Tenant Isolation: PARTIAL (the important caveat)

### What #293 actually fixed (verified RESOLVED)

| Endpoint cluster                            | Status   | Current evidence                                                                                                                                |
| ------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `predictions.py` tenant-`1` fallback        | resolved | `predictions.py:141-146` — raises `401 "Tenant context required"` on missing ctx                                                                |
| `analytics_ai.py` tenant-`1` fallback       | resolved | `analytics_ai.py:274-279` — raises `401`                                                                                                        |
| `copilot.py` tenant-`1` fallback            | resolved | `copilot.py:219-224` — raises `401`                                                                                                             |
| `tenants.py` admin-route caller-match       | resolved | Every mutating route is `require_superadmin`; `PATCH /{id}` blocks non-superadmin cross-tenant at `:313`                                        |
| `newsletter.py` campaigns/templates scoping | resolved | All `NewsletterCampaign`/`NewsletterTemplate` queries filter `tenant_id == current_user.tenant_id` (`:743,772,795,815` campaign/template paths) |

### What is STILL OPEN — the same bug class, different files (NEW P0-2b)

> **The `tenant_id = getattr(user, "tenant_id", None) or 1` pattern that #293 removed from three endpoints still lives, unremediated, in `dashboard.py` across 10 authenticated endpoints.** Any user whose JWT/DB `tenant_id` is `NULL`/`0` silently receives **tenant 1's** campaigns, predictions, and budget data.

| Finding                                                               | Severity    | Evidence                                                                  | Note                                                                                                                                                                                                                                                                        |
| --------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P0-2b** `dashboard.py` 10× `or 1` tenant fallback                   | 🔴 BLOCKING | `dashboard.py:1903, 2180, 2302, 2480, 2603, 2700, 2809, 2955, 3058, 3242` | morning-briefing, anomaly-narratives, signal-recovery, predictive-budget, ai-report, churn-prevention, notifications-prioritized, cross-platform-optimizer, audience-lifecycle, goal-tracking — each feeds `tenant_id` into a `*.tenant_id == tenant_id` query              |
| **P0-2c** `advanced_analytics.py` raw-SQL tenant injection incomplete | 🔴 BLOCKING | `advanced_analytics.py:561-568`                                           | `/advanced-analytics/sql` auto-injects `tenant_id` **only** for `campaigns`/`campaign_metrics`; queries against `audit_logs`, `rules`, `fact_*` tables run unscoped                                                                                                         |
| **P0-2d** Newsletter Celery task unscoped                             | 🟠 HIGH     | `newsletter.py:557` `send_newsletter_campaign(self, campaign_id)`         | loads campaign by id with **no** tenant filter — a guessable/forced id can send another tenant's campaign                                                                                                                                                                   |
| **P0-2e** Newsletter subscriber endpoints unscoped PII                | 🟠 HIGH     | `newsletter.py:743,772,795,815`                                           | `LandingPageSubscriber` has **no `tenant_id` column** (platform-global lead table); any authenticated tenant user can enumerate (email/name/phone/company) and unsubscribe/resubscribe any lead. _Design-intent question_ — but currently bulk-PII-readable by every tenant |
| **P0-2f** `cms.py` hardcoded `tenant_id=1`                            | 🟡 MODERATE | `cms.py:3265`                                                             | CMS user-creation flow ties new CMS users to tenant 1 (not a query leak, but wrong scoping)                                                                                                                                                                                 |

**Verdict:** P0-2 is **downgraded from 🔴 to 🟡**, not closed. The fix was applied per-endpoint rather than as a shared dependency, so the pattern recurred. **Recommended structural fix:** replace every `getattr(..., "tenant_id", None) or 1` and ad-hoc `request.state.tenant_id` read with a single `TenantContextDep` that raises `401` when context is absent, and apply it uniformly. (Skill: `add-api-endpoint`; agent: `tenancy-auditor`, `db-query-review`.)

---

## 3. Master Grading Table — Updated Rows Only

Only rows whose grade changed since 2026-05 are shown; all others stand as in the prior audit.

| Feature                         | 2026-05     | 2026-06         | Why it moved                                                                         |
| ------------------------------- | ----------- | --------------- | ------------------------------------------------------------------------------------ |
| Competitor Intel / Benchmarking | D (25)      | **C- (40)**     | Real scraper no longer a SyntaxError (imports clean); worker still mock + routes 404 |
| EMQ Calculation / Measurement   | C+ (65)     | **B- (70)**     | `status` NameError fixed; still no-op mode write + in-memory store                   |
| CAPI Delivery + PII Hash + DLQ  | D+ (45)     | **C (52)**      | `offline_conversion` import fixed; DLQ/logger still dead code, in-memory state       |
| Profit / COGS                   | C (45)      | **C+ (58)**     | COGS-update crash (`timedelta`) fixed; source table still never written              |
| Campaign Builder (publish)      | D (30)      | **D+ (35)**     | `logger` crash fixed; still fakes publish success                                    |
| Trust Gate                      | C (55)      | **C+ (62)**     | Reversed-arg bug fixed; still bypassed by live path + route mismatch                 |
| Predictions / LTV / Churn       | B (68)      | **B (72)**      | tenant-`1` leak closed here; LTV/churn still heuristic                               |
| AI Copilot (RAG)                | A- (80/0\*) | **A- (82/0\*)** | tenant-`1` leak closed; still ships off (no keys/flags/index)                        |
| Newsletter                      | C+ (55)     | **C (52)**      | campaigns now scoped, **but** subscriber endpoints + unscoped Celery task surfaced   |
| Dashboard Overview              | B+ (75)     | **C+ (60)**     | **Downgraded** — 10 endpoints carry the `or 1` cross-tenant fallback (P0-2b)         |

> Net: six features improve on the crash fixes; **Dashboard and Newsletter are downgraded** because re-verification exposed live cross-tenant fallbacks the prior pass attributed only to the three now-fixed endpoints.

The remaining ~55 feature grades are unchanged — no code touched their paths.

---

## 4. Remaining Cross-Cutting Blockers (unchanged status, re-confirmed)

### P0 — still open (none of these were in #293/#294/#295 scope)

- **P0-1 MFA at login** — `auth.py:644-654` issues access+refresh tokens immediately after `verify_password`; zero `mfa`/`totp` references in `auth.py`; `mfa.py:349 /validate` has no caller. The MFA subsystem remains unreachable.
- **P0-3 Audit log dropped** — writer `middleware/audit.py:258` → `lpush("audit_log_queue", …)`; reader `workers/tasks/audit.py:33,40` → `lpop("audit:log:queue")`. Keys still differ; every audited mutation is silently discarded. (The lint PR reformatted this file but left the string.) ✅
- **P0-4 API keys** — `security.py:291 verify_api_key` referenced only in tests; 0 dependency wiring in `app/api/`.
- **P0-5 Feature/tier gating** — `require_feature`/`FeatureGate`/`TierGate` applied to 0 endpoints; a free/expired tenant can call enterprise features.
- **P0-6 Plaintext secrets** — `settings.py:330` Slack `webhook_url` is a plain `String(2048)` (comment says "encrypted"; no Fernet); `licensing.py:265` `os.getenv("LICENSE_SIGNING_SECRET", "dev-secret-change-me")` with no production guard.

### P1 — still open

- **P1-1 Route mismatches** — `autopilot.ts` → `/autopilot/status` vs backend effective `/autopilot/tenant/{id}/autopilot/status` (doubled prefix + tenant path param); `trustLayer.ts` `/trust-layer/*` vs backend `/trust/tenant/{id}/*`; `crm.ts` `/integrations/crm/*` vs backend `/integrations/*` (no `/crm` segment). **Now matching:** pacing, competitors. KG prefix matches but some sub-paths (`/revenue`, `/channels`) have no backend route.
- **P1-2 Orphaned workers** — confirmed unwired: reporting `process_due_schedules()` (no beat entry), drip (no worker at all), `DailyProfitMetrics` (0 constructor call sites — read-only), campaign-builder beat (still commented `campaign_builder_tasks.py:453-469`), CAPI `delivery_logger.py`/`dead_letter_queue.py` (0 importers). `celery_app.py:67` beat covers rules/sync/competitors/forecasts/fatigue/audit/cost/usage/pipeline/scores/predictions/whatsapp only.
- **P1-5 Built-but-unwired** — `register_default_adapters()` (`registry.py:112`) never called in `main.py` lifespan; `EmbedWidgets.tsx` (643 lines) makes 0 network calls despite `endpoints/embed_widgets.py` existing.
- **P1-6 Knowledge Graph** — `CREATE EXTENSION age` only at `alembic/versions/2026_02_07_knowledge_graph_age.py:55` (inactive tree; `alembic.ini:7 script_location = migrations`); not in `requirements-prod.txt`; db image `postgres:16-alpine` has no AGE. Undeployable as configured.

### P2 — test & coverage debt (unchanged)

No new test suites were added by the remediation PRs (which were security/crash/lint only). The ~20 untested features from the prior audit (Payments/Stripe, Tier, WhatsApp, Slack, Push, Profit, Newsletter, Drip, GDPR, Compliance, SuperAdmin, Markov/Shapley core math, ML output, Rules, Pacing…) remain untested. **New test gaps introduced:** the #293 tenant-context guards and #294 crash fixes shipped without regression tests — add tests asserting `401` on missing tenant context and import-smoke tests for the seven repaired modules.

---

## 5. Updated Go-Live Roadmap

**Phase 0 — Security & data integrity (still blocking):**

1. **Finish P0-2** — replace all `or 1` / ad-hoc `request.state.tenant_id` reads with a uniform `TenantContextDep` (covers `dashboard.py` ×10, `advanced_analytics.py` SQL injector, `newsletter` task, `cms.py:3265`). _This is the single highest-value remaining fix and is now well-scoped._
2. **P0-1** Enforce MFA at login (gate token issuance behind `mfa.py /validate` when the user has MFA enabled).
3. **P0-3** Align the audit Redis key (`audit_log_queue` ↔ `audit:log:queue`) — a one-line fix that restores all compliance logging; add a hash chain for tamper-evidence.
4. **P0-4** Wire an inbound API-key authenticator dependency.
5. **P0-5** Apply feature/tier gates to premium endpoints.
6. **P0-6** Encrypt Slack `webhook_url`; guard the license HMAC secret in prod.

**Phase 1 — Make claimed features function:** P1-1 route alignment (one client path convention), P1-2 wire the 5 orphaned workers, real campaign publish, replace in-memory state (P1-4), provision/shelve KG (P1-6), wire EmbedWidgets frontend (P1-5).

**Phase 2 — Coverage & ops:** tests for the ~20 untested features + regression tests for the #293/#294 fixes; set operational keys (Anthropic/OpenAI for Copilot, Stripe, OAuth apps, SendGrid, S3); reconcile dual implementations.

**Phase 3 — Scale hardening:** move synchronous batch jobs to Celery; Postgres RLS behind the app-level tenant filters (would have caught P0-2b at the DB layer).

---

## 6. Verification Method & Honesty Log

- **Method:** three parallel auditors against `main@c348db1` — (a) `tenancy-auditor` re-verifying P0-2 + fresh tenant-leak sweep, (b) crash-bug + open-P0 verification, (c) P1 structural verification. Every status carries a current `file:line`; STILL-OPEN items quote current code.
- **Confirmed by re-running locally:** #295's lint/type gate (`ruff 0.15.12`, `black 26.3.1`, `isort 8.0.1`, `mypy 1.20.2` → 0 errors / 356 files).
- **Still UNVERIFIED (carried from 2026-05, unchanged):** live external API behavior; whether `.pkl` models ship in the image; whether `Fact*`/`DailyProfitMetrics` fact tables are populated in prod; deployed-env secret configuration; full test pass-rate (suites inventoried, not executed end-to-end); reachability of `claude-haiku-4-5-20251001` from deploy.
- **New since 2026-05:** the cross-tenant fallback class was found to be broader than the prior audit located (dashboard/advanced-analytics/newsletter/cms) — treat "P0-2 fixed" claims with the §2 caveat.

**Bottom line:** Genuine progress (crash-free, type-clean, three IDOR endpoints closed), but the platform is **~64% — late beta**. The most dangerous blocker is now _half_-fixed; closing P0-2 properly (one shared dependency) plus the four untouched P0s is the critical path to production.
