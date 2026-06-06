# Stratum AI Platform

**A Revenue Operating System with Trust-Gated Autopilot.**
Automation executes **only when signal health passes safety thresholds** — never on degraded data.

[![Backend](https://img.shields.io/badge/backend-FastAPI%200.136-009688.svg)](#tech-stack)
[![Frontend](https://img.shields.io/badge/frontend-React%2018%20%2B%20TS-3178c6.svg)](#tech-stack)
[![DB](https://img.shields.io/badge/db-PostgreSQL%2016-336791.svg)](#tech-stack)
[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](#license)
[![Status](https://img.shields.io/badge/status-late%20beta-orange.svg)](#status--maturity)

---

## Table of contents

- [What it is](#what-it-is)
- [Core concept — the Trust Gate](#core-concept--the-trust-gate)
- [Feature map](#feature-map)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Common commands](#common-commands)
- [Configuration](#configuration)
- [API documentation](#api-documentation)
- [Security model](#security-model)
- [December 2025 hardening](#december-2025-hardening)
- [Status & maturity](#status--maturity)
- [Documentation](#documentation)
- [License](#license)

---

## What it is

Stratum AI helps marketing agencies manage many client accounts across ad
platforms (Meta, Google, TikTok, Snapchat). It pairs a **Customer Data
Platform (CDP)** and a real analytics/attribution engine with an
**Autopilot** that can adjust budgets, bids, and campaign state — but only
behind a **Trust Gate** that continuously scores the reliability of the
underlying data and refuses to act when that signal is degraded.

The platform is large and substantially built: **68 API endpoint modules**,
**~167 frontend views**, **20 SQLAlchemy model modules**, **49 Alembic
migrations**, and **~1,900 test functions** across 51 test files.

---

## Core concept — the Trust Gate

```
Signal Health Check  →  Trust Gate  →  Automation Decision
       │                    │                 │
   [HEALTHY  ≥70]       [PASS]            [EXECUTE]
   [DEGRADED 40–69]     [HOLD]            [ALERT ONLY]
   [UNHEALTHY <40]      [BLOCK]           [MANUAL REQUIRED]
```

**Signal Health** is a composite score (0–100) computed from weighted
components:

| Component                 | Weight |
| ------------------------- | ------ |
| EMQ (Event Match Quality) | 35%    |
| API Health                | 25%    |
| Event Loss                | 20%    |
| Platform Stability        | 10%    |
| Data Quality              | 10%    |

Thresholds are **per-tenant configurable** (`TrustGateConfig`); the defaults
above are the safe baseline. Enforcement runs in one of three modes —
**Advisory**, **Soft-Block**, or **Hard-Block**.

Key implementation:
`backend/app/analytics/logic/signal_health.py`,
`backend/app/stratum/core/trust_gate.py`,
`backend/app/autopilot/enforcer.py`.

---

## Feature map

| #   | Domain                          | Highlights                                                                   |
| --- | ------------------------------- | ---------------------------------------------------------------------------- |
| 1   | **Trust Engine**                | Weighted signal-health scoring, trust gate, three enforcement modes          |
| 2   | **CDP**                         | Event ingestion (batch ≤1000), identity resolution, EMQ, consent (GDPR/PDPL) |
| 3   | **Autopilot**                   | DB-backed budget/bid/state actions gated by trust + audit                    |
| 4   | **Campaign Builder**            | Multi-step wizard, approval workflow, platform connectors                    |
| 5   | **Audience Sync**               | Hashed-PII custom audiences → Meta / Google / TikTok / Snapchat              |
| 6   | **Authentication**              | JWT + refresh rotation + blacklist, **MFA (TOTP) enforced at login**, RBAC   |
| 7   | **Analytics**                   | Metrics, anomalies (Z-score), funnels/cohorts, AI insights                   |
| 8   | **Attribution**                 | First/last/linear/time-decay/position + **Markov & Shapley** data-driven     |
| 9   | **Integrations**                | OAuth for 4 ad platforms; CRM: HubSpot, Pipedrive, Salesforce, Zoho          |
| 10  | **Pacing**                      | Budget forecasting, EOM projections, pacing alerts                           |
| 11  | **Payments**                    | Stripe subscriptions + signature-verified webhooks                           |
| 12  | **Multi-tenancy**               | App-level tenant isolation, fail-closed tenant context                       |
| 13  | **Reporting**                   | PDF / Slack / email delivery, scheduling                                     |
| 14  | **CMS / WhatsApp / Newsletter** | Content, WhatsApp Business API, campaign sends                               |

A full, evidence-graded inventory of all 65 features lives in
[`SYSTEM_FEATURES_AUDIT_2026-06.md`](SYSTEM_FEATURES_AUDIT_2026-06.md).

---

## Tech stack

**Backend** — Python 3.11 · FastAPI 0.136 · Pydantic 2.13 · SQLAlchemy 2.0
(async, asyncpg) · Alembic · Celery 5.6 + Redis (broker) + Celery Beat ·
WebSocket (Starlette) + SSE (sse-starlette).

**Data** — PostgreSQL 16 · Redis 7.4 (cache, queues, rate-limit, pub/sub).

**ML / analytics** — scikit-learn, XGBoost, SHAP, NumPy/Pandas; optional
Vertex AI provider.

**Frontend** — React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 ·
shadcn/ui + Radix · Recharts/Tremor · Zustand + TanStack Query.

**Infra / ops** — Docker Compose (8 services) · AWS-ready (ECS/RDS/
ElastiCache) · Prometheus · Grafana · Sentry · structlog (JSON).

---

## Repository layout

```
/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI routes (68 modules)
│   │   ├── analytics/logic/    # Signal health, EMQ, attribution, anomalies
│   │   ├── autopilot/          # Trust-gate enforcement engine
│   │   ├── auth/               # JWT, MFA, RBAC, dependencies
│   │   ├── core/               # Config, security, logging, websocket, tiers
│   │   ├── db/                 # Async/sync sessions, custom column types
│   │   ├── middleware/         # Tenant, audit, rate limiting, security headers
│   │   ├── models/             # SQLAlchemy 2.0 models (20 modules)
│   │   ├── schemas/            # Pydantic I/O schemas
│   │   ├── services/           # Integrations & business logic
│   │   │   ├── oauth/          # Meta · Google · TikTok · Snapchat
│   │   │   ├── crm/            # HubSpot · Pipedrive · Salesforce · Zoho
│   │   │   ├── cdp/ pacing/ profit/ reporting/ tenant/
│   │   ├── stratum/            # Core domain: trust gate, adapters, autopilot
│   │   └── workers/            # Celery tasks + beat schedule
│   ├── migrations/             # Alembic (49 revisions)
│   ├── tests/                  # pytest: unit/ + integration/ (~1,900 tests)
│   └── docs/                   # Curated docs (shipped for the Copilot RAG indexer)
├── frontend/
│   └── src/                    # views/ (167) · components/ (177) · api/ · hooks/ · stores/
├── docker-compose.yml          # db · redis · api · worker · scheduler · frontend · flower
├── SYSTEM_FEATURES_AUDIT_2026-06.md   # current feature audit
└── CLAUDE.md                   # engineering conventions
```

---

## Quick start

```bash
git clone https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025.git
cd Stratum-AI-Final-Updates-Dec-2025

# Full stack via Docker (db, redis, api, worker, scheduler, frontend)
docker compose up -d

# App
open http://localhost:5173            # frontend
open http://localhost:8000/docs       # API docs (local: no auth)
curl http://localhost:8000/health     # health check

# Optional: Celery monitoring
docker compose --profile monitoring up -d   # Flower at :5555
```

### Local backend (without Docker)

```bash
cd backend
make dev            # FastAPI with hot reload on :8000
make migrate        # apply Alembic migrations
make test           # run pytest
make check          # lint + type-check + test
```

### Local frontend

```bash
cd frontend
npm install
npm run dev         # Vite dev server on :5173
npm run build       # production build (tsc + vite)
npm run test        # vitest
```

---

## Common commands

| Command (in `backend/`)       | Purpose                   |
| ----------------------------- | ------------------------- |
| `make dev`                    | FastAPI hot-reload server |
| `make test` / `make test-cov` | pytest / with coverage    |
| `make lint` / `make format`   | ruff + mypy / auto-format |
| `make migrate`                | run Alembic migrations    |
| `make migration msg="..."`    | create a new migration    |
| `make check`                  | lint + type-check + test  |

**Pinned dev toolchain** (CI-enforced): ruff 0.15.15 · black 26.5.1 ·
isort 8.0.1 · mypy 1.20.2. Run these exact versions locally to match CI.

---

## Configuration

All configuration is environment-driven (`backend/app/core/config.py`,
Pydantic Settings). Secrets are **never** committed; dev defaults are
auto-generated per process and rejected in production/staging.

Notable feature flags (default values shown):

| Flag                           | Default | Effect                                             |
| ------------------------------ | ------- | -------------------------------------------------- |
| `feature_knowledge_graph`      | `false` | Knowledge Graph is shelved until Apache AGE exists |
| `enable_campaign_builder_beat` | `false` | Opt-in connector sync / token-refresh beat tasks   |
| `feature_what_if_simulator`    | `true`  | Enterprise-tier what-if simulator                  |
| `feature_gdpr_compliance`      | `true`  | GDPR tooling                                       |

Required in non-dev environments: `SECRET_KEY`, `JWT_SECRET_KEY`,
`PII_ENCRYPTION_KEY`, `LICENSE_SIGNING_SECRET`, plus per-platform OAuth
credentials and Stripe / SendGrid keys. See
[`backend/docs/ENVIRONMENT_VARIABLES.md`](backend/docs/ENVIRONMENT_VARIABLES.md).

---

## API documentation

FastAPI serves interactive docs from the live OpenAPI schema:

```bash
# Local (no auth)
open http://localhost:8000/docs        # Swagger UI
open http://localhost:8000/redoc       # ReDoc

# Protected environments require an API key (constant-time compared)
curl "https://<host>/docs?api_key=$DOCS_API_KEY"
curl "https://<host>/openapi.json?api_key=$DOCS_API_KEY"
```

See also [`backend/docs/API_REFERENCE.md`](backend/docs/API_REFERENCE.md)
and [`backend/docs/API_EXPLORER.md`](backend/docs/API_EXPLORER.md).

---

## Security model

- **Auth** — bcrypt (72-byte truncation), JWT HS256 with refresh rotation +
  Redis blacklist, login lockout, no PII in JWT claims.
- **MFA** — TOTP enforced at login via a stateless challenge-exchange
  (`/auth/login` → `/auth/login/mfa`); backup codes supported.
- **Tenant isolation** — a shared, fail-closed tenant-context dependency
  (`require_tenant_id`) raises `401` instead of defaulting to a tenant.
- **API keys** — inbound `X-API-Key` authenticator with scopes, hashed at
  rest, `last_used` tracking.
- **Tier gating** — `FeatureGate` / `TierGate` enforce subscription tier +
  active-subscription checks on premium routers.
- **Secrets at rest** — Fernet-encrypted PII and connector secrets
  (`EncryptedString` column type); production guards on signing secrets.
- **Audit** — state-changing requests are queued to Redis and persisted by
  a Celery worker; constant-time comparisons via `hmac.compare_digest`.
- **Transport / app** — security headers, CSRF middleware, webhook
  signature verification (Stripe, WhatsApp), SSRF guard on outbound webhooks.

Vulnerability reporting: see [`SECURITY.md`](SECURITY.md).

---

## December 2025 hardening

This release folds in a focused security & reliability pass driven by the
[2026-06 features audit](SYSTEM_FEATURES_AUDIT_2026-06.md). Highlights:

| Area                       | Change                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **MFA at login**           | Token issuance now gated behind a TOTP/backup-code second factor (backend + frontend).                                                |
| **Cross-tenant isolation** | Removed silent `tenant_id → 1` fallbacks; shared fail-closed `TenantContextDep`; raw-SQL & global-list endpoints gated to superadmin. |
| **Audit pipeline**         | Fixed a producer/consumer Redis-key mismatch that was silently dropping every audit event; aligned field names.                       |
| **API-key auth**           | Added the missing inbound authenticator + `/programmatic/whoami`; keys now authenticate something.                                    |
| **Tier gating**            | Wired `FeatureGate` onto Enterprise routers (subscription-expiry + tier checks).                                                      |
| **Secrets at rest**        | Slack webhook URL encrypted; license HMAC secret fails closed in prod/staging.                                                        |
| **Crash fixes**            | Repaired 7 import/syntax bugs on real request paths.                                                                                  |
| **Knowledge Graph**        | Shelved behind a feature flag (requires Apache AGE) — returns `503` instead of crashing.                                              |
| **Orphaned workers**       | Campaign-builder connector beat tasks wired (opt-in) and the stratum adapter registry populated at startup.                           |
| **CI hygiene**             | Pinned-toolchain formatting drift and an ESLint 10 / `eslint-plugin-react` crash fixed; backend lint + type-check green.              |

---

## Status & maturity

**Honest assessment: ~64% production-ready ("late beta").**

The algorithmic cores are real implementations, not stubs — Markov/Shapley
attribution, sklearn ML, EMQ math, signal-health scoring, identity
resolution, OAuth token exchange, audience PII hashing, autopilot
enforcement, and Stripe billing all function. The recurring gap is
**wiring, enforcement, and persistence** rather than missing logic.

Recent work closed the headline security blockers (MFA, tenant isolation,
audit logging, API-key auth, tier gating, secrets) and the runtime crash
bugs. Known remaining work is tracked in the audit and includes
frontend↔backend route-prefix alignment, several still-orphaned workers
(reporting/drip/profit), in-memory state that should be durable, and
broader test coverage.

> The full, `file:line`-grounded breakdown — per-feature grades, security
> findings, and a phased go-live roadmap — is in
> [`SYSTEM_FEATURES_AUDIT_2026-06.md`](SYSTEM_FEATURES_AUDIT_2026-06.md).

---

## Documentation

| Doc                                                                                      | What's in it                                                                |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [`CLAUDE.md`](CLAUDE.md)                                                                 | Engineering conventions, design system, trust-engine rules                  |
| [`SYSTEM_FEATURES_AUDIT_2026-06.md`](SYSTEM_FEATURES_AUDIT_2026-06.md)                   | Current feature audit (supersedes 2026-05)                                  |
| [`backend/docs/`](backend/docs/)                                                         | Setup, backend, frontend, features, operations, deploy, technical reference |
| [`backend/docs/architecture/trust-engine.md`](backend/docs/architecture/trust-engine.md) | Trust Engine architecture                                                   |
| [`backend/docs/00-overview/glossary.md`](backend/docs/00-overview/glossary.md)           | Domain glossary                                                             |
| [`SECURITY.md`](SECURITY.md) · [`CHANGELOG.md`](CHANGELOG.md)                            | Disclosure policy · version history                                         |

---

## License

Proprietary. All rights reserved.
