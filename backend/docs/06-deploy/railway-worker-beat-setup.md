# Railway — Celery Worker & Beat Services [INF-009]

## Why this exists

Production Railway ran a **single service (the API)**. Celery had no home, so
in production **nothing on the background pipeline ran**:

- **Autopilot execution** — approved actions dispatch to `apply_actions_queue`
  and are never applied. The trust-gated-autopilot value prop is dead.
- **Signal-health rollup** — `FactSignalHealthDaily` is never populated, so the
  trust gate / dashboard trust layer / execution-path health check see no data
  (and, post fail-closed, freeze).
- **ROAS alerts, attribution-variance rollup, audience auto-sync, newsletter
  sends** — all silently do nothing.
- **`worker-heartbeat` (INF-003)** — never written, so `/health` reports the
  worker as down.

This is fixed by running **two more Railway services** off the same backend
image: a **worker** and a **beat** (scheduler), configured by
`backend/railway.worker.toml` and `backend/railway.beat.toml`.

## How the image supports it

`backend/Dockerfile`'s `ENTRYPOINT` is `start.sh`, which runs `exec "$@"` when a
command is passed (`start.sh:9-16`). So a service whose start command is a
`celery …` invocation runs Celery directly and **skips migrations/casts/seeds**
— only the API service owns schema changes. No `-Q` flag is needed: because
`task_queues` is defined, a worker consumes **all** configured queues by default
(`default, sync, rules, intel, ml, dead_letter` — verified via
`celery … inspect active_queues`).

## One-time setup in the Railway dashboard

For **each** of the two new services (Worker, Beat), in the `stratum-ai` project:

1. **New Service → GitHub Repo** → `Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025`, branch `main` (same repo/branch as the API service; auto-deploys on merge).
2. **Settings → Root Directory:** `backend`
3. **Settings → Config-as-code → Config Path:**
   - Worker service → `railway.worker.toml`
   - Beat service → `railway.beat.toml`
   (Paths are relative to the root directory, i.e. `backend/`.)
4. **Variables** — the worker and beat need the **same environment as the API
   service** (they import the full app). At minimum:
   - `DATABASE_URL` (and `DATABASE_URL_SYNC` if you set it explicitly on the API)
   - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL`
   - `PII_ENCRYPTION_KEY`, `SECRET_KEY`, and any platform/API credentials tasks use
   - `APP_ENV=production`
   Use Railway **shared variables** or reference the managed Postgres/Redis the
   same way the API service does, so the three services stay in sync. Do **not**
   set `SEED_SUPERADMIN` / `SEED_CMS_PAGES` on worker/beat (seeds are the API's job).

## Critical constraints

- **Beat must be exactly ONE replica.** `railway.beat.toml` pins
  `numReplicas = 1`. Two schedulers double-fire every `beat_schedule` entry
  (duplicate rollups, alerts, syncs). Never scale the beat service, and never
  embed beat in a scaled worker via `worker --beat`.
- **Worker concurrency is conservative** (`--concurrency=2`) because the image
  bakes the ML models and each prefork child imports the full app — memory
  scales with concurrency. Raise it, or add worker replicas, once you know the
  instance size. `--max-tasks-per-child=200` recycles children to bound ML
  memory growth.

## Verifying it works

After both services deploy:

1. **Worker liveness:** `GET https://backend-production-81fa.up.railway.app/health`
   — the worker heartbeat (INF-003) should report the worker alive within ~1 min.
2. **Beat is scheduling:** check the Beat service logs for
   `Scheduler: Sending due task worker-heartbeat` (fires every minute) and
   `process-audit-logs` (every minute).
3. **Rollups populate:** after the next `signal_health_rollup` run, the
   dashboard trust layer / `/trust` endpoints return data instead of `no_data`.
4. **Autopilot end-to-end:** approve an autopilot action and confirm it
   transitions `APPROVED → APPLYING → APPLIED` (worker logs + the action's status).

## Scheduled tasks that come alive (static `beat_schedule`)

| Task | Cadence |
| --- | --- |
| `sync-all-campaigns` | hourly (:00) |
| `generate-daily-forecasts` | 06:00 UTC |
| `calculate-fatigue-scores` | 03:00 UTC |
| `process-audit-logs` | every minute |
| `calculate-cost-allocation` | 02:00 UTC |
| `calculate-usage-rollup` | 01:00 UTC |
| `check-pipeline-health` | hourly (:30) |
| `worker-heartbeat` (INF-003) | every minute |
| signal-health / ROAS-alert / attribution-variance / audience-sync rollups | see `celery_app.py` |

Feature-flag-gated tasks (`evaluate-active-rules`, `refresh-competitor-data`)
remain shelved off for launch per `celery_app.py:92-96`.

## Related, NOT covered here

- **INF-011** — the API `start.sh` runs migrations on boot, which races scaled
  API *replicas*. Worker/beat are unaffected (they skip migrations via the
  command-override path), but scaling the API past one replica still needs a
  release-phase migration step or an advisory lock. Separate item.
