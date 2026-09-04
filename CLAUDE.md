# Stratum AI Project Guide

This is the working guide for contributors and coding agents. Keep it focused on durable invariants, verified workflows, and repository-specific risks. Do not add volatile feature counts, test totals, migration totals, or generated audit results.

## Product and safety model

Stratum AI is a multi-tenant revenue operating system with Trust-Gated Autopilot. Automated actions must fail closed unless signal health, authorization, policy, and audit requirements all pass.

| Signal health | Gate | Allowed behavior |
|---|---|---|
| `>= 70` | PASS | Automation may execute after all other checks pass |
| `40-69` | HOLD | Alert and hold; never auto-execute |
| `< 40` | BLOCK | Require manual intervention |

Core safety rules:

- Never bypass the trust gate for a quick fix.
- Treat missing or stale signal data as blocked, not healthy.
- Preserve tenant scope, authorization, enforcement limits, idempotency, and audit logging for every mutation.
- An automated action is not complete until its decision and outcome are auditable.

`backend/app/autopilot/gate.py` currently uses the `70` and `40` constants directly, while onboarding and tenant settings also store threshold values. Do not assume every execution path honors tenant-configured thresholds. Before changing threshold behavior, trace every backend and frontend consumer and update code, tests, and documentation together. Do not introduce additional copies of the constants.

The calculator in `backend/app/stratum/core/signal_health.py` uses EMQ 40%, freshness 25%, variance 20%, and anomaly 15%. When CDP data is included, the base weights are proportionally reduced and CDP contributes 10%. Preserve a total weight of `1.0` and test both modes.

## Sources of truth

When files disagree, use this order:

1. Registered implementation paths and tests
2. `.github/workflows/ci.yml` for required validation and toolchain versions
3. Makefiles, Dockerfiles, `docker-compose*.yml`, and deployment configuration
4. `.env.example` files and application settings for configuration names
5. Focused documents under `backend/docs/`, `docs/`, and the deployment guide

The repository contains dated audits, generated HTML reports, checkpoints, datasets, and experiments. They are evidence or historical context, not the source of current runtime behavior. A module existing on disk also does not prove it is registered or in launch scope; check its import, router, worker, registry, or feature-gate path.

## Technology

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, and structlog
- Data: PostgreSQL 16 with pgvector and Apache AGE, plus Redis 7
- Frontend: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, and Zustand
- Frontend CI runtime: Node 24; keep it aligned with `frontend/Dockerfile`
- Quality and security: pytest, Ruff, Black, isort, mypy, Bandit, pip-audit, Vitest, Playwright, Trivy, and gitleaks
- Billing: runtime-selectable Stripe or Paddle behind the payment-gateway abstraction

Do not change Python, Node, database, or extension versions based only on this summary. Update the relevant CI, Docker, lock, and deployment files together.

## Repository map

```text
backend/
  app/
    api/v1/endpoints/   FastAPI routers
    analytics/          analytics queries and signal logic
    autopilot/          trust-gate enforcement
    auth/               authentication and permissions
    core/               settings, security, logging, and shared concerns
    db/                 sessions and database infrastructure
    middleware/         tenant, audit, rate-limit, and request controls
    models/             SQLAlchemy model modules
    schemas/            Pydantic request and response models
    services/           integrations and business services
    stratum/            core domain implementation
    workers/            Celery application and tasks
  migrations/           Alembic revisions
  tests/unit/           unit and boundary tests
  tests/integration/    database-backed integration tests
  docs/                 product, architecture, feature, and operations docs
frontend/
  src/
    api/                 API clients and query hooks
    components/          shared, feature, and primitive components
    contexts/            React context providers
    hooks/               reusable hooks
    stores/              Zustand state
    views/               routed views
    styles/              theme and global styling
  e2e/                   Playwright tests
infrastructure/          infrastructure configuration
monitoring/              observability configuration
nginx/                   reverse-proxy configuration
scripts/                 repository and deployment helpers
tests/load/              k6 load-test scenarios
```

## Local development

Prepare an environment before starting Compose:

```bash
cp .env.example .env
# Set the required database, Redis, application, and encryption values.
docker compose config
docker compose up -d
```

Never commit `.env` files or real credentials. The base Compose stack defines PostgreSQL, Redis, API, worker, scheduler, frontend, and Flower; Flower is enabled through the `monitoring` profile.

### Backend commands

The root Makefile delegates to `backend/Makefile`:

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

`make check` is a convenient backend lint-and-unit-test check; it is not equivalent to the complete release gate.

### Frontend commands

From `frontend/`:

```bash
npm ci --legacy-peer-deps
npm run lint
npx tsc --noEmit
npm run test:coverage
npm run build
npm run test:e2e -- --project=chromium
```

GitHub Actions aggregates backend quality, unit and integration tests, the configured coverage ratchet, backend dependency/security checks, frontend checks, E2E, Trivy, secret scanning, and deployment-config validation. Every required job feeds the release gate. Do not describe a reporting step as optional merely because its individual command uses `continue-on-error`; the aggregator can still make it blocking.

Respect the current `fail_under` value in `backend/.coveragerc`. Never lower the coverage ratchet to make a change pass. Add focused tests and raise the ratchet only after measuring the complete CI-equivalent suite.

## Engineering conventions

### Backend

- Put HTTP transport in `backend/app/api/v1/endpoints/`; keep reusable business and integration logic in services or domain modules.
- Use Pydantic models for API input and output and preserve the repository's standard response envelopes.
- Follow existing asynchronous I/O and SQLAlchemy session patterns. Do not block the event loop with synchronous network or database work.
- Derive tenant scope from authenticated context and existing middleware or dependencies. Never accept a client-provided tenant identifier as authorization.
- Preserve row-level security, role checks, rate limits, audit records, and transaction ownership.
- Add type hints and focused docstrings to new or modified public Python code.
- Use timezone-aware UTC datetimes; do not introduce `datetime.utcnow()`.
- Use `secrets` for security tokens and `hmac.compare_digest()` for secret comparisons; never use `random` for security-sensitive values.
- Encrypt PII and integration credentials before storage. Never place PII in JWT claims or logs.
- Use structured logging and avoid logging tokens, secrets, raw credentials, or sensitive webhook bodies.

### Frontend

- Use the shared API client, query hooks, contexts, and stores instead of adding ad hoc request or state layers.
- Keep TypeScript types aligned with backend response schemas.
- Do not hardcode production API or WebSocket hosts; use the existing environment and proxy configuration.
- Update loading, empty, error, authorization, and responsive states with feature changes.
- Keep English and Arabic copy, RTL behavior, routes, and navigation aligned.
- ARIA semantics and keyboard interaction are required behavior, not follow-up polish.

## Database and migrations

- Append normal Alembic revisions; do not rewrite or renumber migrations that may have been applied.
- The database requires both pgvector and Apache AGE. Use the repository's PostgreSQL image and CI setup when validating integration tests.
- Generate and apply revisions through `make migration msg="description"` and `make migrate`.
- Ensure new model modules are registered in the metadata/import path used by Alembic.
- Test upgrades from the preceding revision as well as empty-database creation when schema risk is material.
- Never run destructive resets, downgrades, or production data fixes without explicit authorization and a documented recovery path.

## Integrations and billing

- This repository intentionally supports multiple advertising, messaging, analytics, and CRM integrations. Use the existing factory, adapter, registry, feature-gate, and credential patterns rather than branching on a platform throughout the codebase.
- Do not infer that an integration is launch-ready merely because its client exists. Confirm router registration, worker registration, feature gates, tests, and the launch-scope decision document.
- Shared payment endpoints must resolve the active provider through `backend/app/services/payment_gateway.py`; do not couple shared billing flows directly to Stripe or Paddle.
- `PAYMENT_GATEWAY` selects `stripe` or `paddle` at runtime. Both webhook routes remain mounted so gateway switches do not strand in-flight events.
- Preserve webhook signature verification, replay/idempotency protection, transaction boundaries, tenant synchronization, retry-safe failures, and provider-specific identifier handling.
- Follow `backend/docs/05-operations/paddle-cutover.md` for switching gateways. Do not improvise a cutover from code inspection alone.
- Keep OAuth state, API tokens, service credentials, signing secrets, and payment configuration out of frontend source and logs.

## Design contract

Stratum's interface should feel bold, intelligent, premium, and restrained: high information density with clear hierarchy, quiet authority, and action-first workflows.

- Use the ink-and-ember theme and the Geist/Geist Mono typography defined in `backend/docs/03-frontend/figma-theme.md`.
- Dark, light, and system themes are first-class. Do not treat light mode or RTL as a later adaptation.
- Avoid generic enterprise gray, decorative glassmorphism, and unsupported one-off visual systems.
- Reuse `frontend/src/components/primitives/` before creating bespoke cards, KPIs, status indicators, charts, tables, drawers, navigation, or theme controls.
- Prefer intervention queues and clear next actions over passive dashboard decoration.
- Every visual element must support comprehension, state, navigation, or action.

## Git and delivery workflow

- Use conventional commit subjects: `feat|fix|refactor|test|docs(scope): message`.
- When work has a ticket, use the documented `feature/STRAT-123-description` branch and include the ticket in the commit or pull-request context.
- Keep changes scoped and include tests for the changed behavior.
- Pass the full release gate before merge.
- Update focused documentation when behavior, configuration, security boundaries, deployment procedures, or operator workflows change.

## Focused documentation

- [Trust Engine](backend/docs/architecture/trust-engine.md)
- [Integration guide](backend/docs/integrations/README.md)
- [Glossary](backend/docs/00-overview/glossary.md)
- [Frontend theme](backend/docs/03-frontend/figma-theme.md)
- [Launch-scope decisions](backend/docs/06-deploy/launch-scope-decisions.md)
- [Paddle cutover](backend/docs/05-operations/paddle-cutover.md)
- [Server deployment](SERVER_DEPLOYMENT_GUIDE.md)
- [Security policy](SECURITY.md)

Read these as needed. Do not automatically duplicate their endpoint lists, configuration matrices, schedules, palettes, or runbooks in this file.
