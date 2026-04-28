---
description: Pre-deployment verification — lint, tests, migrations, threshold review
allowed-tools: Bash(make:*), Bash(pytest:*), Bash(alembic:*), Bash(git diff:*), Bash(git log:*), Read, Grep
---

Pre-deployment verification.

## Checklist

1. `make lint` — ruff + mypy clean
2. `make test` — full pytest suite passes
3. `cd backend && alembic upgrade head --sql > /tmp/migration.sql` — migrations dry-run reviewed (delegate to `migration-auditor` agent if any new migrations)
4. Threshold changes reviewed (`TrustGateConfig`, `signal_health.py`) — delegate to `trust-gate-reviewer` agent if any
5. Monitoring alerts configured for new signals
6. CHANGELOG.md updated
7. `.env.example` updated for any new env vars
8. No secrets in diff: `git diff main...HEAD | grep -iE "secret|token|password|key="`

## Output

- Per-item PASS/FAIL with evidence
- Blocking issues listed first
- Deploy recommendation: GO | OFF-HOURS | NO-GO
