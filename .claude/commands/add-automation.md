---
description: Scaffold a new trust-gated automation with schema, task, endpoint, and tests
argument-hint: <automation_name>
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(make:*), Bash(pytest:*)
---

Create new automation for: $ARGUMENTS

## Checklist

1. Define automation in `backend/app/autopilot/` (or `backend/app/stratum/core/automations/`)
2. Create Pydantic schema in `backend/app/schemas/`
3. Implement trust gate conditions (signal health threshold, freshness, anomaly tolerance)
4. Add Celery task in `backend/app/workers/`
5. Create API endpoint in `backend/app/api/v1/endpoints/`
6. Write tests (90%+ coverage) in `backend/tests/unit/`
7. Add integration test in `backend/tests/integration/`

## Trust Requirements (MUST be enforced)

- Minimum signal health threshold (default: 70, configurable per tenant via `TrustGateConfig`)
- Data freshness requirement (per-signal SLA)
- Anomaly tolerance (max stddev or % drift)
- Manual override capability — admin-only, audit-logged
- Audit logging on every execution path
- Honor enforcement mode: Advisory / Soft-Block / Hard-Block

## Definition of Done

- [ ] All 7 checklist items complete
- [ ] `make lint` clean
- [ ] `make test` passes
- [ ] No hardcoded thresholds
- [ ] Audit log entry on every `execute()` call
- [ ] Trust-gate-reviewer agent passes review
