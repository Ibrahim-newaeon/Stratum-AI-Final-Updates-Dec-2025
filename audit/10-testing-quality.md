# Phase 10 — Testing & Quality

## 1. Backend Tests

| Suite | Location | CI floor |
|-------|----------|----------|
| Unit | `backend/tests/unit/` | ≥3000 ran tests (`ci.yml:227`) |
| Integration | `backend/tests/integration/` | ≥600 ran tests (`ci.yml:227`) |
| Total test files | 318 | glob count |

CI comment at time of writing: ~3561 unit / ~706 integration (`ci.yml:221-222`).

## 2. Coverage

```258:258:backend/.coveragerc
fail_under = 74.0
```

Combined unit + integration with `--cov-append` (`ci.yml:295-306`, `.coveragerc:167-173`).

Omitted from measurement: `main.py`, `celery_app.py`, shelved CRM clients, dead `stratum/workers`, `monitoring/*` (`.coveragerc:15-46`).

Greenlet concurrency enabled for async SQLAlchemy accuracy (`.coveragerc:14`, comments 9-13).

## 3. Vacuous-Pass Guards

CI fails if:
- Ran test count below floor (`ci.yml:214-293`)
- Any test file contributes zero collected tests (`ci.yml:245-291`)

This directly addresses prior issue where modules lacked `pytestmark` and silently deselected (`ci.yml:249-255`).

## 4. Frontend Tests

| Type | Runner | CI step |
|------|--------|---------|
| Unit/component | Vitest + Testing Library | `npm run test:coverage` (`ci.yml:441-442`) |
| E2E | Playwright (10 specs) | `e2e` job (`ci.yml:508-509`) |
| Lint | ESLint max-warnings 0 | `ci.yml:436` |
| Types | tsc --noEmit | `ci.yml:438-439` |

## 5. Security Testing

| Tool | Scope |
|------|-------|
| Bandit | Python SAST (`ci.yml:373-378`) |
| pip-audit | Dependency CVEs strict (`ci.yml:380-385`) |
| npm audit gate | `scripts/audit-gate.mjs` with allowlist (`ci.yml:427-433`) |
| Trivy | FS + container image (`ci.yml:537-601`) |
| gitleaks | Secret scan (`ci.yml:637-641`) |

## 6. Load Testing

k6 smoke on main push only (`ci.yml:760-854`):
- Script: `tests/load/autopilot-enforcement-load-test.js`
- Scenario: smoke against local uvicorn

**Missing data:** RPS targets, p95 latency SLOs — **UNKNOWN — not present in available evidence**.

## 7. Quality Gate Gaps

| Gap | Severity | Evidence |
|-----|----------|----------|
| E2E not in release gate | P2 | `ci.yml:732` vs `479` |
| `main.py` uncovered | P3 | `.coveragerc:20` |
| mypy/ruff continue-on-error pattern aggregated | P3 | `ci.yml:79-116` — still fails aggregate |

## 8. Testing Findings

| ID | Sev | Title |
|----|-----|-------|
| F-006 | P2 | E2E not blocking merge |
| F-015 | P3 | Application entry main.py omitted from coverage |

## 9. Positive Controls

- 74% combined coverage ratchet with extensive history (`.coveragerc:63-257`)
- Integration tests run real Postgres + pgvector + Redis (`ci.yml:143-169`)
- Per-file collection guard prevents silent test loss
- Frontend build fails without VITE_API_URL in CI (`ci.yml:465-467`)
- Load tests on main branch

## 10. Searches Run

```
glob backend/tests/**/*.py                    → 318
glob frontend/e2e/*.ts                        → 10
glob frontend/src/**/*.test.tsx               → many (primitives each have vitest)
read .coveragerc fail_under line 258
read ci.yml backend-tests + gate jobs
grep "pytestmark" backend/tests/integration   → spot-check modules marked integration
```

## 11. Recommended Pre-Release Test Plan

1. Full CI green on `main` including e2e (manual if gate unchanged)
2. `alembic upgrade head` on staging clone
3. Stripe webhook replay in test mode
4. Trust gate hold/block scenarios with degraded signal health
5. MFA login + token revocation flow
6. k6 smoke or higher scenario if traffic estimate available
