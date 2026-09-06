# Launch Scope Decisions

Decisions taken 2026-07-05 on the subsystems that existed in code but were
never wired (recorded in the 2026-07-02 audit). Each was either wired
before launch or explicitly cut to the post-launch backlog.

## Wired for launch

| Subsystem | Status |
| --------- | ------ |
| **Audience auto-sync** | `tasks.audience_auto_sync` sweep runs every 15 min from Celery Beat, executing due `PlatformAudience` schedules (`auto_sync` + `next_sync_at`) with `triggered_by="schedule"`. Failures back off 1h instead of retrying every sweep. |
| **CRM sync history** (`_log_sync`) | Fixed: the log row was flushed after the sync's own commit and rolled back on session close, so history was forever empty. Now committed. (Applied to the Salesforce/Pipedrive services too; Salesforce has since been deleted — see below — and the fix also covers the failure path.) |

## Cut from launch

Superseded 2026-09-05. The 2026-07-05 table described these subsystems as
"exists in code, needs wiring". Two of them no longer exist, and two are now
wired, so that table is replaced rather than annotated.

| Subsystem | Decision (2026-09-05) |
| --------- | --------------------- |
| **Zoho** | **Removed, not deferred.** Deleted in #721. Product owner confirmed no prospect has asked for it and it is not a deal-blocker in the Gulf pipeline. Do not rebuild without new demand evidence. |
| **Salesforce** | **Removed, not deferred.** Deleted in #721. Product owner confirmed it is out of launch scope and belongs to a later enterprise motion, if ever. |
| **Pipedrive** | **Wired** in #722 — five routes under `/api/v1/integrations/pipedrive/*` plus Celery tasks. Needs `PIPEDRIVE_CLIENT_ID`/`PIPEDRIVE_CLIENT_SECRET` only. See the open defect below before treating scheduled sync as working. |
| **Identity-resolution pipeline** | **Wired.** `IdentityResolutionService` is invoked by the live CDP endpoint (`api/v1/endpoints/cdp.py`) and by `pipedrive_sync.py`. The 2026-07-05 "nothing invokes it" no longer holds. |

Zoho and Salesforce were removed because their clients read config fields
(`zoho_client_id`, `zoho_region`, `salesforce_client_id`) that were never
defined in `config.py`. `Settings` is declared `extra="ignore"`, so exporting
the environment variables did not create them either — every connection
attempt raised `AttributeError` before reaching the network.

The Postgres `crm_connections.provider` enum still accepts `'salesforce'` and
`'zoho'`; dropping a value requires rewriting the type and an unused value is
harmless. Before a production deploy, confirm no rows depend on the deleted
code:

```sql
SELECT provider, count(*) FROM crm_connections GROUP BY 1;
```

### Open defect: CRM background tasks never register

`app/workers/crm_sync_tasks.py` defines seven `@shared_task` functions
(`sync_hubspot_data`, `writeback_hubspot_attribution`, `sync_pipedrive_data`,
`writeback_pipedrive_attribution`, `sync_all_crm_connections`,
`run_scheduled_writebacks`, `run_identity_matching`). The module is **absent
from the `include` list in `app/workers/celery_app.py`**, and neither sweep has
a Celery Beat entry. None of these tasks register with the worker, so no CRM
sync or attribution writeback ever runs on a schedule — **for HubSpot as well
as Pipedrive**.

The manual endpoints are unaffected: `POST /integrations/{hubspot,pipedrive}/sync`
call `sync_service.sync_all()` synchronously and do not go through Celery.

This is the same registration gap already fixed four times for other task
families (see the annotated `include` list). Fixing it means adding the module
to `include`, adding beat entries for the two sweeps, and un-omitting the
Pipedrive modules and `crm_sync_tasks.py` from `backend/.coveragerc`.

### Open defect: the tenant CRM view calls routes that do not exist

`frontend/src/api/crm.ts` targets `/integrations/crm/*`. **No backend route
contains `crm`** — the integrations router is mounted at `/integrations` and
its paths are `/contacts`, `/deals`, `/pipeline/summary`, `/hubspot/*`,
`/pipedrive/*`. Every call in that module therefore 404s.

It is not dead code: `api/hooks.ts` re-exports its hooks, and
`views/tenant/Integrations.tsx` and `views/tenant/IntegrationsHub.tsx` consume
them. IntegrationsHub renders from Settings > Integrations, so this is a
user-reachable view whose data calls cannot succeed.

Of the 15 paths it calls, four differ from a real route only by the extra
`/crm` segment (`contacts`, `deals`, `pipeline/summary`, `hubspot/connect`);
two exist but are provider-scoped (`writeback/config` and `writeback/history`
live under `/hubspot/`); and nine have no backend at all, including
`/integrations/crm/connections`, which is what `useCRMConnections()` — the
primary call on both views — depends on.

Fixing it is a decision, not a rename: either build the missing endpoints
(notably a provider-agnostic connections list) or rework the views onto the
per-provider routes that exist. `CRMConnection` also has no `sync_enabled` or
`sync_frequency_minutes` column, though the module's `CRMConnection` type
declares both, so some of this describes a backend that was never built.

### Closed: reachable Pipedrive code is back inside the coverage gate

The `salesforce_*` and `zoho_*` entries in `backend/.coveragerc` named files
deleted in #721 and omitted nothing; they were removed on 2026-09-05.

The three `pipedrive_*` modules and `crm_sync_tasks.py` were omitted on the
grounds that they were post-launch and unreachable. That stopped being true
once #722 wired the routes and #739 registered and scheduled the CRM tasks, at
which point reachable production code was sitting outside the gate.

They stayed omitted only because the impact could not be measured locally: the
figure `fail_under` gates is the combined unit+integration total, and the
integration suite needs Postgres with pgvector and Apache AGE plus Redis. The
arithmetic recorded here — 778 statements, ~1.25% of the denominator, ~0.92pp
worst case — assumed none of it was covered, which was already untrue;
`test_pipedrive_client_pure.py` and `test_celery_beat_registration.py` both
exercise these modules.

The entries were removed on 2026-09-06 and CI was used as the instrument: it
runs both suites with `--cov-append` and enforces the floor, so it measures
what no local environment could. **The ratchet was not lowered**, and must not
be to absorb these lines — if the combined total does not hold, the answer is
tests.

The `memory_debug` endpoint that used to be listed here was deleted on
2026-08-17. Its router was never included in the API router *and*
`init_debug_endpoints()` was never called, so all 14 endpoints were
unreachable and would have returned 503 even if mounted. `monitoring/`
survives because the standalone `backend/run_memory_audit.py` still uses
`memory_audit.py` and `visualizations.py`; `monitoring/middleware.py` and
`monitoring/celery_hooks.py` lost their last consumer with that deletion and
are candidates for removal.

## Production deploy prerequisites (from PR #517)

- Set `METRICS_API_KEY` in the production environment — `/metrics` is
  tenant-auth-exempt and carries tenant-labeled series; unset means open.
- Give the Prometheus scraper the same key (see the commented
  `authorization` block in `infrastructure/prometheus/prometheus.yml`).
