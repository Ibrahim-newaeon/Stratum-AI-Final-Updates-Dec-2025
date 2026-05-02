# Stratum AI Platform

## Overview

Revenue Operating System with Trust-Gated Autopilot architecture.
Automation executes ONLY when signal health passes safety thresholds.

## Core Concept

```
Signal Health Check → Trust Gate → Automation Decision
       ↓                  ↓              ↓
   [HEALTHY]         [PASS]         [EXECUTE]
   [DEGRADED]        [HOLD]         [ALERT ONLY]
   [UNHEALTHY]       [BLOCK]        [MANUAL REQUIRED]
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI 0.109, Pydantic 2.x, SQLAlchemy 2.x (async)
- **Database**: PostgreSQL 16, Redis 7 (caching/queues)
- **Queue**: Celery 5.3 + Redis + Celery Beat
- **ORM**: SQLAlchemy 2.0 with asyncpg driver
- **Auth**: JWT + OAuth2 + MFA (TOTP)
- **Frontend**: React 18, TypeScript 5.3, Vite 5.1, Tailwind CSS 3.4
- **UI**: shadcn/ui + Radix UI, Recharts, Tremor, Framer Motion
- **State**: Zustand + React Query (TanStack)
- **Infra**: Docker, AWS (ECS, RDS, ElastiCache)
- **Monitoring**: Prometheus, Grafana, Sentry, structlog
- **Migrations**: Alembic

## Project Structure

```
/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI routes (50+ endpoints)
│   │   ├── analytics/logic/    # Signal health, EMQ, attribution, anomalies
│   │   ├── autopilot/          # Trust gate enforcement engine
│   │   ├── auth/               # JWT, MFA, permissions
│   │   ├── core/               # Config, security, logging, websocket
│   │   ├── db/                 # Database session management
│   │   ├── middleware/         # Tenant, audit, rate limiting
│   │   ├── models/             # SQLAlchemy models (19 files)
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # External integrations & business logic
│   │   │   ├── oauth/          # OAuth provider factory
│   │   │   ├── pacing/         # Budget forecasting
│   │   │   ├── profit/         # COGS & profit tracking
│   │   │   ├── reporting/      # Report generation & scheduling
│   │   │   └── crm/            # CRM integrations
│   │   ├── stratum/            # Core domain models
│   │   └── workers/            # Celery tasks
│   ├── migrations/             # Alembic migrations (41 revisions)
│   ├── tests/                  # pytest suite (21 test files)
│   ├── Makefile                # Build automation
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                # API client wrappers
│   │   ├── components/         # React components (50+ TSX files)
│   │   ├── contexts/           # React context providers
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # Zustand stores
│   │   ├── views/              # Page views & routes
│   │   └── styles/             # Tailwind CSS + custom styles
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml          # 8 services (db, redis, api, worker, scheduler, frontend, flower)
├── docs/                       # 60+ documentation files
└── CLAUDE.md
```

## Key Features (14)

| #   | Feature               | Key Files                                                        |
| --- | --------------------- | ---------------------------------------------------------------- |
| 1   | Trust Engine          | `analytics/logic/signal_health.py`, `stratum/core/trust_gate.py` |
| 2   | CDP                   | `models/cdp.py`, `analytics/logic/emq_calculation.py`            |
| 3   | Autopilot Enforcement | `autopilot/enforcer.py`, `autopilot/service.py`                  |
| 4   | Campaign Builder      | `models/campaign_builder.py`                                     |
| 5   | Audience Sync         | `services/cdp/audience_sync/`                                    |
| 6   | Authentication        | `auth/`, `core/security.py`, `services/mfa_service.py`           |
| 7   | Analytics             | `analytics/logic/` (8 modules)                                   |
| 8   | Integrations          | `services/oauth/` (Meta, Google, TikTok, Snapchat)               |
| 9   | CMS                   | `models/cms.py`, frontend CMS editor                             |
| 10  | WhatsApp              | `services/whatsapp_service.py`                                   |
| 11  | Payments              | Stripe webhooks & subscriptions                                  |
| 12  | Multi-tenancy         | `middleware/tenant.py`, row-level security                       |
| 13  | Reporting             | `services/reporting/` (PDF, Slack, email)                        |
| 14  | SuperAdmin            | `endpoints/superadmin.py`                                        |

## Key Commands

```bash
# Backend
make dev              # Start FastAPI with hot reload (port 8000)
make test             # Run pytest
make test-all         # Run all tests with verbose output
make test-cov         # Tests with coverage report
make lint             # Ruff + mypy
make format           # Auto-format with ruff, black, isort
make migrate          # Run Alembic migrations
make migration msg="description"  # Create new migration
make check            # Lint + type check + test

# Docker
docker compose up -d              # Full stack (8 services)
docker compose --profile monitoring up -d  # Include Flower

# Frontend
cd frontend && npm run dev        # Vite dev server (port 5173)
cd frontend && npm run build      # Production build
cd frontend && npm run test       # Vitest
```

## Code Standards

- Type hints REQUIRED on all functions
- Pydantic models for all API I/O
- Async/await for all I/O operations
- 90%+ test coverage for core/
- Docstrings on public functions
- Use `datetime.now(timezone.utc)` (NOT `datetime.utcnow()`)
- Use `secrets` module for security tokens (NOT `random`)
- Use `hmac.compare_digest()` for constant-time comparisons
- Encrypt PII with Fernet before storage
- Structured logging via structlog (JSON format)

## Domain Terminology

| Term             | Definition                                     |
| ---------------- | ---------------------------------------------- |
| Signal           | Input data point (metric, event, webhook)      |
| Signal Health    | Composite score (0-100) of signal reliability  |
| Trust Gate       | Decision checkpoint before automation          |
| Autopilot        | Automated action when trust passes             |
| EMQ              | Event Match Quality - signal fidelity score    |
| CDP              | Customer Data Platform - profile & event store |
| Enforcement Mode | Advisory / Soft-Block / Hard-Block             |
| ROAS             | Return on Ad Spend                             |
| Pacing           | Budget spend velocity tracking                 |
| Tenant           | Isolated customer workspace (multi-tenant)     |

## Trust Engine Rules

```python
# Thresholds are configurable per tenant (see TrustGateConfig)
HEALTHY_THRESHOLD = 70      # Green - autopilot enabled
DEGRADED_THRESHOLD = 40     # Yellow - alert + hold
# Never auto-execute when signal_health < 70

# Signal Health Components (weighted):
# EMQ: 35%, API Health: 25%, Event Loss: 20%,
# Platform Stability: 10%, Data Quality: 10%
```

## Do NOT

- Skip trust gate checks for "quick fixes"
- Hardcode thresholds (use config)
- Execute automations without audit logging
- Merge without passing CI
- Use `random` for security tokens (use `secrets`)
- Put PII in JWT claims (use encrypted DB fields)
- Store plaintext credentials in frontend code
- Commit `.env` files or API credentials

## Testing

```bash
make test                    # Quick test run
make test-cov                # With coverage
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
```

Test files: `backend/tests/unit/` and `backend/tests/integration/`
Coverage target: 90%+ for `core/`, `autopilot/`, `analytics/`

## Git Workflow

- Branch: `feature/STRAT-123-description`
- Commit: `feat(signals): add anomaly detection [STRAT-123]`
- Conventional commits: `feat|fix|refactor|test|docs(scope): message`

## Docker Services

| Service   | Port | Description                     |
| --------- | ---- | ------------------------------- |
| db        | 5432 | PostgreSQL 16                   |
| redis     | 6379 | Redis 7 (cache + Celery broker) |
| api       | 8000 | FastAPI backend                 |
| worker    | -    | Celery worker (4 concurrency)   |
| scheduler | -    | Celery Beat                     |
| frontend  | 5173 | React Vite dev server           |
| flower    | 5555 | Celery monitoring (optional)    |

## Design Context

### Users

Marketing agencies managing multiple client accounts across ad platforms. Extended sessions, professional setting, data-heavy workflows.

### Brand Personality

**Bold, intelligent, premium.** Sophisticated power through restraint. Bloomberg terminal meets luxury brand.

### Aesthetic Direction

- **Reference**: Apple / Porsche Design — premium materials, restrained palette, obsessive detail
- **Anti-reference**: Enterprise gray (Salesforce/SAP); 2024-default violet/cyan glassmorphism (Linear, Vercel, every YC AI startup).
- **Theme**: Dual mode — figma dark (default) + designed-coherent figma light. Both first-class.
- **Palette**: Ink + ember — see `docs/03-frontend/figma-theme.md` for full token table.
  - Dark: ink `#0B0B0B` bg · surface `#141414` · line `#1F1F1F` · ember `#FF5A1F` accent · cyan `#06B6D4` info.
  - Light: warm off-white `#FAFAF7` bg · `#FFFFFF` surface · `#E8E8E0` line · desaturated ember `#E84F1F` accent.
- **Typography**: Geist (sans + display) + Geist Mono. No Satoshi, no Clash Display, no Inter.
- **Surfaces**: Hairline borders (1px), subtle inner highlights, ember radial bleeds for emphasis. No glassmorphism.

### Design Principles

1. **Quiet authority** — Power through precision, not noise
2. **Information density without clutter** — Strong hierarchy, not hidden data
3. **Premium materiality** — Tinted neutrals, subtle depth, no flat gray
4. **Decisive contrast** — Bold type hierarchy, 1.5x+ ratio between steps
5. **Earn every pixel** — Every element serves the user's task
6. **Action-first home** — The dashboard is a triage queue, not a dashboard. Sort by intervention required.

### Component contract

The dashboard composes from typed primitives, not bespoke surfaces. Reuse before building:

- `frontend/src/components/primitives/Card.tsx` — surface (default / elevated / glow variants)
- `frontend/src/components/primitives/KPI.tsx` — composed Card + label + value + delta + status
- `frontend/src/components/primitives/StatusPill.tsx` — figma signature pill
- `frontend/src/components/primitives/Chart.tsx` — themed recharts wrapper (LineChart / AreaChart)
- `frontend/src/components/primitives/DataTable.tsx` — headless table with sort / loading / empty
- `frontend/src/components/primitives/ConfirmDrawer.tsx` — destructive-action gate
- `frontend/src/components/primitives/nav/Sidebar.tsx` — collapsible-group nav
- `frontend/src/components/primitives/nav/Topbar.tsx` — search + theme toggle + profile
- `frontend/src/components/primitives/theme/ThemeProvider.tsx` — dark/light/system

Each ships with a vitest. ARIA + keyboard support are first-class, not afterthoughts.

## Imports

@docs/architecture/trust-engine.md
@docs/integrations/README.md
@docs/00-overview/glossary.md
@docs/03-frontend/figma-theme.md
