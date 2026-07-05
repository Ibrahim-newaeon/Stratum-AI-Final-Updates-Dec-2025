# Launch Scope Decisions

Decisions taken 2026-07-05 on the subsystems that existed in code but were
never wired (recorded in the 2026-07-02 audit). Each was either wired
before launch or explicitly cut to the post-launch backlog.

## Wired for launch

| Subsystem | Status |
| --------- | ------ |
| **Audience auto-sync** | `tasks.audience_auto_sync` sweep runs every 15 min from Celery Beat, executing due `PlatformAudience` schedules (`auto_sync` + `next_sync_at`) with `triggered_by="schedule"`. Failures back off 1h instead of retrying every sweep. |
| **CRM sync history** (`_log_sync`) | Fixed: the log row was flushed after the sync's own commit and rolled back on session close, so history was forever empty. Now committed. (Applies to the Salesforce/Pipedrive services even though those integrations are post-launch — the fix also covers the failure path.) |

## Cut from launch (post-launch backlog)

| Subsystem | State at cut | What wiring would take |
| --------- | ------------ | ---------------------- |
| **Identity-resolution pipeline** | CDP identity stitching exists as code; nothing invokes it | Hook into the event-ingestion path |
| **Zoho OAuth** | Zoho CRM sync service exists; no OAuth endpoint, unreachable in product | One OAuth flow via the existing provider factory |
| **Salesforce / Pipedrive** | Adapters exist; not registered/reachable | Registration + OAuth + productization; largest effort, least-proven demand |

Do not present these three in the product UI as available integrations
until wired.

The cut modules (and verified-dead code: `stratum/workers/`,
`monitoring/`, the unregistered `memory_debug` endpoint) are omitted from
the coverage denominator in `backend/.coveragerc` so the CI gate measures
only reachable code — **un-omit each family when wiring it post-launch**.

## Production deploy prerequisites (from PR #517)

- Set `METRICS_API_KEY` in the production environment — `/metrics` is
  tenant-auth-exempt and carries tenant-labeled series; unset means open.
- Give the Prometheus scraper the same key (see the commented
  `authorization` block in `infrastructure/prometheus/prometheus.yml`).
