# Phase 0 — Repository Inventory

**Audit date:** 2026-08-18  
**Repo:** `Stratum-AI-Final-Updates-Dec-2025`  
**Latest commit:** `17d40c3a984c194e4c3f8f72d7378ad8d3f04af1` — `ci: test on the Node version we actually ship (20 -> 26)` (2026-08-18)  
**Remote:** `https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025.git`  
**Current branch:** `chore/ci-node-26`

## 1. Product Summary

Revenue Operating System with Trust-Gated Autopilot. Automation executes only when signal health passes configurable thresholds (PASS ≥70, HOLD 40–69, BLOCK <40). Documented in `CLAUDE.md:1-16`.

## 2. Top-Level Layout

| Path | Purpose | Evidence |
|------|---------|----------|
| `backend/` | FastAPI API, Celery workers, Alembic migrations, pytest | `CLAUDE.md:22-44` |
| `frontend/` | React 19 + Vite 8 + TypeScript SPA | `frontend/package.json:1-17` |
| `docker-compose*.yml` | 11 compose variants (dev, prod, staging, hetzner, observability) | glob: `docker-compose*.yml` |
| `.github/workflows/` | CI, Docker publish, Dependabot | `ci.yml`, `docker.yml`, `dependabot.yml` |
| `backend/docs/` | 60+ internal docs (Copilot RAG subset in image) | `CLAUDE.md:57` |
| `audit/` | Prior audit tooling + this audit output | `audit/run-audit.ts`, `audit/setup_audit.py` |
| `editions/` | Starter / Professional / Enterprise edition bundles | `editions/*/docker-compose.yml` |
| `nginx/` | Production reverse-proxy configs | validated in CI `deploy-config` job |
| `scripts/` | Backup, seed, deployment helpers | CI shell-syntax check |

**Total tracked files (glob `**/*`):** 1857 (includes datasets, scratch, HTML reports).

## 3. Backend Inventory

| Metric | Count | Search |
|--------|-------|--------|
| API endpoint modules | 68 | `backend/app/api/v1/endpoints/*.py` |
| Router registrations | 67 | `grep include_router backend/app/api/v1/__init__.py` → 67 |
| SQLAlchemy model modules | 25 | `backend/app/models/*.py` |
| Alembic migrations | 64 | `backend/migrations/versions/*.py` |
| Test files | 318 | `backend/tests/**/*.py` |
| Python deps (pinned) | ~80 lines | `backend/requirements.txt` |

**Runtime:** Python 3.12 (CI), FastAPI 0.141.1, SQLAlchemy 2.0.52, Celery 5.6.3, PostgreSQL 16 + pgvector.

## 4. Frontend Inventory

| Metric | Count | Search |
|--------|-------|--------|
| View/page TSX files | 181 | `frontend/src/views/**/*.tsx` |
| E2E specs (Playwright) | 10 | `frontend/e2e/*.ts` |
| i18n locales on disk | 3 (en, ar, uk) | `frontend/src/i18n/locales/*/translation.json` |
| i18n locales registered | 2 (en, ar) | `frontend/src/i18n.ts:6-16` |

**Runtime:** React 19.2.8, Vite 8.2.1, TanStack Query 5, Zustand 5, Tailwind 3.

## 5. Docker Services (default stack)

From `docker-compose.yml`:

| Service | Image / build | Port |
|---------|---------------|------|
| db | pgvector/pgvector:pg16 | 5432 |
| redis | redis:7-alpine (password required) | 6379 |
| api | `./backend` Dockerfile | 8000 |
| worker | Celery concurrency=4 | — |
| scheduler | Celery beat | — |
| frontend | Vite dev target | 5173 |
| flower | profile `monitoring` | 5555 |

## 6. Environment Templates

| File | Notes |
|------|-------|
| `.env.example` | Root compose-oriented; includes `METRICS_API_KEY` | `.env.example:14-17` |
| `backend/.env.example` | Backend-only; `USE_MOCK_AD_DATA=true` default | `backend/.env.example:38-39` |
| `.env.production.template` | Production template | present |
| `.env.hetzner.template` | Hetzner deploy | CI `deploy-config` uses this |
| `frontend/.env.example` | Vite vars | present |
| `editions/*/.env.example` | Per-edition | 3 files |

**Conflict:** `needs_human_review: true` — root vs backend `.env.example` disagree on mock-data default and variable naming. See `06-auth-security.md` / `08-infra-devops.md`.

## 7. CI Pipeline Jobs

From `.github/workflows/ci.yml`:

| Job | Gates |
|-----|-------|
| backend-quality | ruff, black, isort, mypy |
| backend-tests | unit + integration pytest, vacuous-pass guard, coverage ratchet 74% |
| backend-security | bandit, pip-audit |
| frontend | npm audit gate, lint, tsc, vitest coverage, build |
| e2e | Playwright chromium — **not in release gate** |
| security | Trivy FS + container |
| secrets | gitleaks |
| deploy-config | nginx -t, compose config, shell syntax |
| gate | Aggregates 7 jobs (excludes e2e) |
| load-tests | main push only, k6 smoke |

## 8. Prior Audit Artifacts (in repo)

| Path | Type |
|------|------|
| `audit/outputs/master-audit.md` | Prior automated audit output |
| `FULL_PROJECT_AUDIT.md` | Markdown report |
| `STRATUM_AI_AUDIT_REPORT_ALIGNED.html` | HTML report |
| `AUDIT_FIXES_CHECKPOINT*.md` | Fix tracking |

These are **not** substitutes for this evidence-backed audit.

## 9. Open Questions

1. **Production host / traffic:** UNKNOWN — not present in available evidence.
2. **Which compose file is canonical for prod deploy:** ASSUMPTION: `docker-compose.yml` + `docker-compose.prod.yml` (CI validates this stack) — confidence MEDIUM.
3. **Stripe live vs test mode in prod:** UNKNOWN — depends on env at deploy time.

## 10. Phase 0 Findings

0 blocker findings in inventory itself. Configuration conflicts flagged for human review in later phases.
