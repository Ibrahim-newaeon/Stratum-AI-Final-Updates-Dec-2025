---
name: incident-response
description: Use when responding to a production incident — trust gate stuck on HOLD/BLOCK, OAuth token expired, Celery queue backed up, signal health degraded, database connection pool exhausted, or 5xx spike. Encodes the diagnostic commands and triage steps so any engineer (or Claude) can stabilize at 3 AM. Trigger when the user says "incident", "outage", "alert firing", "stuck", "queue backed up", "5xx", or names a specific failure mode.
---

# Incident Response

A runbook. Pick the matching scenario, run the diagnostics, propose the fix.

## General first 5 minutes

1. **Acknowledge the alert** in PagerDuty/Slack so dupes stop.
2. **Establish blast radius** — one tenant or all? One platform integration or all?
3. **Check recent deploys** — `git log --oneline -10 main` and look at deployment timestamps. Most outages correlate with a recent change.
4. **Open Sentry / Grafana / Flower** to see what the system thinks is happening.
5. **Decide: stabilize first, root-cause second.** Roll back or feature-flag off if the fix isn't obvious in 10 minutes.

---

## Scenario 1: Trust gate stuck on HOLD or BLOCK

**Symptoms**: autopilot not executing, dashboard shows yellow/red, customer reports "nothing happening".

**Diagnose**

```bash
# Check signal health for the tenant
grep -rn "signal_health" backend/app/analytics/logic/

# Latest health score per signal
psql $DATABASE_URL -c "
  SELECT signal_name, health_score, computed_at
  FROM signal_health
  WHERE tenant_id = <ID>
  ORDER BY computed_at DESC LIMIT 20;
"

# Trust gate evaluation log
psql $DATABASE_URL -c "
  SELECT decision, reason, created_at
  FROM trust_gate_decisions
  WHERE tenant_id = <ID>
  ORDER BY created_at DESC LIMIT 10;
"
```

Then delegate to the `debug-gate` slash command or `signal-auditor` agent for deep dive.

**Common causes**

- One signal flat-lined → check collector logs for that platform.
- Threshold misconfigured (someone bumped HEALTHY_THRESHOLD).
- Anomaly detector tripped on legitimate traffic spike → tune anomaly bounds.

**Mitigation**

- Customer-facing: explain the hold and ETA.
- Engineering: identify the failing signal, restart its collector or extend its freshness window temporarily via `TrustGateConfig`. NEVER lower the global HEALTHY_THRESHOLD — that bypasses the safety floor.

---

## Scenario 2: OAuth tokens expired for a platform

**Symptoms**: collectors for one platform (Meta/Google/TikTok/Snap) failing 401, signal health for that platform dropping, "reconnect required" alerts.

**Diagnose**

```bash
# Find affected tenants
psql $DATABASE_URL -c "
  SELECT tenant_id, platform, expires_at, refresh_attempts
  FROM oauth_credentials
  WHERE expires_at < now() OR last_refresh_error IS NOT NULL
  ORDER BY expires_at ASC LIMIT 50;
"
```

**Common causes**

- Refresh token revoked by user.
- Provider rotated client credentials and we didn't update env.
- Refresh job stopped running (check Celery beat).
- Provider returned new error code we don't handle.

**Mitigation**

- If our refresh job is broken: redeploy after fixing the refresh logic.
- If user revoked: notify the user via in-app + email; mark integration as "reconnect required".
- Never automatically retry indefinitely — backoff and require manual reconnect after N failures.

---

## Scenario 3: Celery queue backed up

**Symptoms**: tasks taking a long time to start, Flower shows N active + huge "scheduled" or "reserved" count, worker CPU pegged.

**Diagnose**

```bash
# Open Flower
open http://localhost:5555  # or production URL

# Queue depth via Redis
redis-cli -h $REDIS_HOST llen celery

# Worker count
docker compose ps worker

# Recent task durations
# In Flower: Tasks > sort by Runtime descending
```

**Common causes**

- A slow task (often: large signal payload, runaway DB query) is hogging workers.
- Worker concurrency too low for current load.
- A poison-pill task that always fails and retries.
- Beat scheduling too aggressively.

**Mitigation**

- **Stabilize first**: scale workers up (`docker compose up -d --scale worker=N`) or kill the queue (`celery -A app purge -Q <queue>`) only if data loss is acceptable.
- **Find the slow task**: in Flower, sort by runtime; identify the culprit task name.
- **Find the poison pill**: if one task is retrying endlessly, ack it manually or push to dead-letter:
  ```bash
  celery -A app inspect reserved | grep <task_name>
  ```
- **Long term**: add per-queue isolation so one slow task doesn't block fast ones.

---

## Scenario 4: Signal health degraded for many tenants at once

**Symptoms**: cross-tenant degradation in EMQ or platform stability components.

**Diagnose**

```bash
# Per-platform error rate in last hour
psql $DATABASE_URL -c "
  SELECT platform,
         count(*) FILTER (WHERE status = 'error') AS errors,
         count(*) AS total
  FROM platform_api_calls
  WHERE created_at > now() - interval '1 hour'
  GROUP BY platform;
"
```

**Common causes**

- Upstream platform outage (check Meta/Google status pages).
- We deployed a change to the collector or mapper that's failing.
- Network/DNS issue from our infra.
- Rate limit hit globally (using the wrong API tier).

**Mitigation**

- If upstream: communicate to customers, monitor for recovery, do not retry-storm them.
- If our deploy: roll back the collector change.
- If rate limit: throttle collectors, request quota increase.

---

## Scenario 5: Database connection pool exhausted

**Symptoms**: 5xx errors with "QueuePool limit reached" or "asyncpg pool full"; latency spike across the board.

**Diagnose**

```bash
psql $DATABASE_URL -c "
  SELECT count(*) AS conns, state
  FROM pg_stat_activity
  WHERE datname = 'stratum'
  GROUP BY state;
"

# Long-running queries
psql $DATABASE_URL -c "
  SELECT pid, now() - query_start AS duration, state, query
  FROM pg_stat_activity
  WHERE state != 'idle' AND now() - query_start > interval '30 seconds'
  ORDER BY duration DESC;
"
```

**Common causes**

- A code path holding a session across an `await` of an external call (very common — see `celery-task-reviewer` rule 5).
- A slow query holding a transaction open (kill it, then fix the query).
- Pool size too small for current load.
- Migration ran in business hours and acquired an exclusive lock (see `migration-auditor`).

**Mitigation**

- Kill long queries: `SELECT pg_cancel_backend(<pid>);`
- Bump pool size temporarily if not the root cause.
- Roll back recent code change if a session-leak fix is possible.

---

## Scenario 6: 5xx spike

**Diagnose**

```bash
# Sentry: filter to last 30 minutes, group by error
# Logs:
docker compose logs --since 30m api | grep -E "ERROR|CRITICAL|500" | head -50
```

**Common causes**

- Recent deploy.
- Downstream dependency (DB, Redis, ad platform) flapping.
- Specific endpoint blowing up on edge-case data.

**Mitigation**

- Identify the top error, fix or roll back.
- Open a status page / customer comm if affecting many tenants.

---

## After every incident

- [ ] Write a postmortem (blameless) within 24 hours.
- [ ] Add a regression test that would have caught this.
- [ ] Add monitoring/alert for the root cause.
- [ ] Update this skill with the new scenario if it's a new failure mode.
- [ ] If the bug pattern is a class (e.g., another async-session leak), update the relevant `*-reviewer` agent so the next one is caught at PR time.
