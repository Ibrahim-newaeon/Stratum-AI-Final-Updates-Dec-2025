# Stratum AI Project Guide

This guide records durable architecture, safety rules, and verified workflows for contributors and coding agents. Keep volatile counts, generated audit results, endpoint inventories, and detailed runbooks out of this file.

## Product and safety model

Stratum AI is a multi-tenant revenue operating system with Trust-Gated Autopilot. Automated actions must fail closed unless signal health, authorization, policy, and audit requirements all pass.

| Signal health | Gate | Behavior |
|---|---|---|
| `>= 70` | PASS | Automation may execute after all other checks pass |
| `40-69` | HOLD | Alert and hold; never auto-execute |
| `< 40` | BLOCK | Require manual intervention |

- Never bypass the trust gate, including for quick fixes.
- Treat missing or stale signal data as blocked.
- Preserve tenant scope, authorization, enforcement limits, idempotency, and audit logging for every mutation.
- `backend/app/autopilot/gate.py` currently uses `70` and `40` directly, while tenant settings also store thresholds. Do not assume all paths honor per-tenant values; trace every consumer before changing threshold behavior and do not add more copies.
- `backend/app/stratum/core/signal_health.py` weights EMQ 40%, freshness 25%, variance 20%, and anomaly 15%. With CDP enabled, base weights are proportionally reduced and CDP contributes 10%. Keep the total at `1.0` and test both modes.

## Sources of truth

When files disagree, prefer:

1. Registered implementation paths and tests
2. `.github/workflows/ci.yml`
3. Makefiles, Dockerfiles, Compose, and deployment configuration
4. Environment examples and application settings
5. Focused documents under `backend/docs/`, `docs/`, and the deployment guide

Dated audits, checkpoints, generated HTML, datasets, and experiments are historical evidence, not runtime truth. A module existing on disk is not proof that it is registered or launch-ready; check its router, worker, registry, import, and feature-gate paths.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, and structlog
- Data: PostgreSQL 16 with pgvector and Apache AGE, plus Redis 7
- Frontend: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, and Zustand; CI uses Node 24
- Billing: Paddle Billing through the shared payment-gateway abstraction
- Quality: pytest, Ruff, Black, isort, mypy, Bandit, pip-audit, Vitest, Playwright, Trivy, and gitleaks

Update CI, Docker, lock, and deployment files together when changing runtime versions.

## Repository map

```text
backend/
  app/
    api/v1/endpoints/   FastAPI routers
    analytics/          analytics and signal logic
    autopilot/          trust-gate enforcement
    auth/               authentication and permissions
    core/               settings, security, and shared concerns
    middleware/         tenant, audit, and request controls
    models/             SQLAlchemy models
    schemas/            Pydantic schemas
    services/           integrations and business services
    stratum/            core domain implementation
    workers/            Celery tasks
  migrations/           Alembic revisions
  tests/                unit and integration tests
  docs/                 architecture, feature, and operations docs
frontend/
  src/                   API, components, contexts, hooks, stores, and views
  e2e/                   Playwright tests
infrastructure/          infrastructure configuration
monitoring/              observability configuration
nginx/                   reverse-proxy configuration
scripts/                 repository and deployment helpers
tests/load/              k6 scenarios
```

## Working locally

Prepare required database, Redis, application, and encryption values before starting:

```bash
cp .env.example .env
docker compose config
docker compose up -d
```

Never commit `.env` or real credentials. The root Makefile delegates to `backend/Makefile`:

```bash
make dev
make test
make test-all
make test-cov
make lint
make format
make migrate
make migration msg="description"
make check
```

`make check` is a fast backend check, not the complete release gate.

Frontend validation, from `frontend/`:

```bash
npm ci --legacy-peer-deps
npm run lint
npx tsc --noEmit
npm run test:coverage
npm run build
npm run test:e2e -- --project=chromium
```

GitHub Actions aggregates backend quality, tests, coverage, dependency/security checks, frontend checks, E2E, secret scanning, and deployment validation into a blocking release gate. A step using `continue-on-error` may still be blocking through its aggregator.

Respect `fail_under` in `backend/.coveragerc`. Never lower the ratchet to make a change pass.

## Engineering conventions

### Backend

- Keep HTTP transport in `api/v1/endpoints/` and reusable logic in services or domain modules.
- Use Pydantic API models and preserve the repository's standard response envelopes.
- Follow existing async I/O and SQLAlchemy session patterns; do not block the event loop.
- Derive tenant scope from authenticated context and existing middleware. Client-provided tenant IDs are not authorization.
- Preserve row-level security, role checks, rate limits, audit records, idempotency, and transaction ownership.
- Add type hints and focused docstrings to new or modified public code.
- Use timezone-aware UTC datetimes, `secrets` for security tokens, and `hmac.compare_digest()` for secret comparisons.
- Encrypt PII and credentials; never place PII in JWT claims or sensitive values in logs.

### Frontend

- Reuse the shared API client, query hooks, contexts, stores, and primitive components.
- Keep TypeScript types aligned with backend schemas and do not hardcode production hosts.
- Update loading, empty, error, authorization, responsive, English/Arabic, and RTL behavior together.
- ARIA semantics and keyboard interaction are required behavior.

## Database and migrations

- Append Alembic revisions; do not rewrite migrations that may have been applied.
- PostgreSQL requires pgvector and Apache AGE. Use the repository image when validating integration tests.
- Generate and apply revisions with `make migration msg="description"` and `make migrate`.
- Ensure new models are registered in Alembic's metadata import path.
- Never run destructive resets, downgrades, or production data fixes without explicit authorization and a recovery plan.

## Integrations and billing

- Use existing factories, adapters, registries, feature gates, and credential patterns for platform integrations.
- Confirm router and worker registration, feature gates, tests, and launch-scope decisions before treating an integration as live.
- **Paddle is the only supported payment provider.** Production and development configuration must select `PAYMENT_GATEWAY=paddle`.
- Shared billing flows must continue through `backend/app/services/payment_gateway.py` while legacy provider code is being removed.
- Existing Stripe code, dependencies, routes, and configuration are migration remnants. Do not select, configure, document, extend, or build new features on them. Remove them only in a separate tested cleanup that preserves historical billing data and safely handles in-flight events.
- Preserve Paddle signature verification, replay/idempotency protection, transaction boundaries, tenant synchronization, retry-safe failures, and provider identifiers.
- Follow `backend/docs/05-operations/paddle-cutover.md` for the cutover. Do not improvise from code inspection alone.
- Keep OAuth state, API tokens, service credentials, signing secrets, and billing configuration out of frontend source and logs.

## Design contract

Stratum should feel bold, intelligent, premium, and restrained: high information density, clear hierarchy, quiet authority, and action-first workflows.

- Use the ink-and-ember theme and Geist/Geist Mono defined in `backend/docs/03-frontend/figma-theme.md`.
- Dark, light, and system themes are first-class; so are RTL and accessibility.
- Avoid generic enterprise gray, decorative glassmorphism, and one-off visual systems.
- Reuse `frontend/src/components/primitives/` before creating bespoke cards, KPIs, statuses, charts, tables, drawers, navigation, or theme controls.
- Prefer intervention queues and clear next actions over passive decoration.

## Git and delivery

- Use conventional commits: `feat|fix|refactor|test|docs(scope): message`.
- When work has a ticket, use `feature/STRAT-123-description` and include the ticket in commit or pull-request context.
- Keep changes scoped, include focused tests, and pass the full release gate before merge.
- Update focused documentation when behavior, configuration, security boundaries, deployment, or operator workflows change.

## Focused documentation

- [Trust Engine](backend/docs/architecture/trust-engine.md)
- [Integration guide](backend/docs/integrations/README.md)
- [Glossary](backend/docs/00-overview/glossary.md)
- [Frontend theme](backend/docs/03-frontend/figma-theme.md)
- [Launch scope](backend/docs/06-deploy/launch-scope-decisions.md)
- [Paddle cutover](backend/docs/05-operations/paddle-cutover.md)
- [Server deployment](SERVER_DEPLOYMENT_GUIDE.md)
- [Security policy](SECURITY.md)

Read these as needed; do not duplicate their detailed inventories or runbooks here.
