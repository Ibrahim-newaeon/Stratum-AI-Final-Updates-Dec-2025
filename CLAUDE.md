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
- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Database**: PostgreSQL 15, Redis (caching/queues)
- **Queue**: Celery + Redis
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Infra**: Docker, AWS (ECS, RDS, ElastiCache)
- **Monitoring**: Prometheus, Grafana, Sentry

## Project Structure
```
/stratum-ai/
├── api/              # FastAPI routes
├── core/             # Business logic, trust engine
│   ├── signals/      # Signal collectors & processors
│   ├── gates/        # Trust gate evaluators
│   └── automations/  # Automation executors
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # External integrations
├── workers/          # Celery tasks
└── tests/
```

## Key Commands
```bash
make dev              # Start local env
make test             # Run pytest
make lint             # Ruff + mypy
make migrate          # Alembic migrations
docker compose up -d  # Full stack
```

## Code Standards
- Type hints REQUIRED on all functions
- Pydantic models for all API I/O
- Async/await for all I/O operations
- 90%+ test coverage for core/
- Docstrings on public functions

## Domain Terminology
| Term | Definition |
|------|------------|
| Signal | Input data point (metric, event, webhook) |
| Signal Health | Composite score (0-100) of signal reliability |
| Trust Gate | Decision checkpoint before automation |
| Autopilot | Automated action when trust passes |

## Trust Engine Rules
```python
HEALTHY_THRESHOLD = 70      # Green - autopilot enabled
DEGRADED_THRESHOLD = 40     # Yellow - alert + hold
# Never auto-execute when signal_health < 70
```

## Do NOT
- Skip trust gate checks for "quick fixes"
- Hardcode thresholds (use config)
- Execute automations without audit logging
- Merge without passing CI

## Git Workflow
- Branch: `feature/STRAT-123-description`
- Commit: `feat(signals): add anomaly detection [STRAT-123]`

## Imports
@docs/architecture/trust-engine.md
@docs/integrations/README.md
