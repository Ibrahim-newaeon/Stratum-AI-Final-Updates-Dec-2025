# Stratum AI - Service Level Objectives (SLOs)

## Overview

This document defines the Service Level Objectives (SLOs) for the Stratum AI
platform. These targets guide operational decisions, alerting thresholds, and
capacity planning.

**Error Budget Policy:** When an SLO is breached, the team freezes non-critical
feature work and focuses on reliability improvements until the error budget
recovers.

---

## 1. API Availability

| Metric | Target | Measurement Window | Source |
|--------|--------|--------------------|--------|
| Uptime (all requests) | 99.9% | 30-day rolling | Prometheus `up{job="stratum-api"}` |
| Health endpoint (`/health`) | 99.95% | 30-day rolling | External uptime monitor |

**Error Budget:** 0.1% = ~43 minutes/month of total downtime

**Calculation:**
```
Availability = 1 - (failed_requests / total_requests)
```

Where `failed_requests` = any HTTP 5xx response or connection timeout.

---

## 2. API Latency

| Metric | Target | Measurement | Source |
|--------|--------|-------------|--------|
| p50 latency (all endpoints) | < 100ms | 5-min rolling | `stratum_http_latency_seconds` |
| p95 latency (all endpoints) | < 500ms | 5-min rolling | `stratum_http_latency_seconds` |
| p99 latency (all endpoints) | < 2s | 5-min rolling | `stratum_http_latency_seconds` |
| p95 latency (auth endpoints) | < 300ms | 5-min rolling | `stratum_http_latency_seconds{handler=~"/api/v1/auth/.*"}` |
| p95 latency (dashboard endpoints) | < 1s | 5-min rolling | `stratum_http_latency_seconds{handler=~"/api/v1/dashboard/.*"}` |

**Error Budget:** < 0.1% of requests may exceed the p99 target.

---

## 3. Error Rate

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| 5xx error rate (overall) | < 0.1% | 5-min rolling | `stratum_http_latency_seconds_count{status=~"5.."}` |
| 5xx error rate (critical paths) | < 0.01% | 5-min rolling | Auth, dashboard, campaigns endpoints |
| 4xx error rate (overall) | < 5% | 1-hour rolling | Client errors (expected but monitored) |

---

## 4. Trust Gate Performance

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| Trust gate evaluation p95 | < 100ms | 5-min rolling | `stratum_trust_gate_evaluation_duration_seconds` |
| Trust gate availability | 99.99% | 30-day rolling | Gate evaluations that complete without error |
| False block rate | < 1% | 7-day rolling | Manual review of blocked actions |

**Rationale:** Trust gate decisions are on the critical path for all automation.
Slow or unavailable gate evaluations directly impact revenue operations.

---

## 5. Platform Integration (Ad APIs)

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| Platform API success rate | > 95% | 1-hour rolling | `stratum_platform_api_requests_total` |
| Platform API p95 latency | < 5s | 5-min rolling | `stratum_platform_api_latency_seconds` |
| Data sync freshness | < 2 hours | Continuous | `stratum_platform_sync_last_success_timestamp` |
| CAPI event delivery rate | > 99% | 1-hour rolling | `stratum_capi_events_sent_total` |
| CAPI match rate | > 50% | 24-hour rolling | `stratum_capi_match_rate` |

**Note:** Platform API targets depend on third-party providers (Meta, Google,
TikTok, Snapchat). SLOs reflect what we can control (retries, circuit breakers).

---

## 6. Background Jobs (Celery)

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| Task success rate | > 99% | 1-hour rolling | `stratum_celery_tasks_total` |
| Task p95 duration | < 60s (standard) | 5-min rolling | `stratum_celery_task_duration_seconds` |
| Task p95 duration | < 300s (sync jobs) | 5-min rolling | Platform sync tasks |
| Queue depth | < 1000 pending | Continuous | Celery/Redis queue length |

---

## 7. Data Integrity

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| EMQ score accuracy | +/- 5% of validated score | Weekly audit | Manual validation |
| Attribution variance | < 15% vs GA4 | 7-day rolling | `stratum_attribution_variance_pct` |
| PII encryption coverage | 100% of PII fields | Continuous | Code audit + tests |

---

## 8. Incident Management

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| MTTD (Mean Time to Detect) | < 5 minutes (critical) | 30-day rolling | Alert → acknowledge time |
| MTTR (Mean Time to Resolve) - Critical | < 1 hour | 30-day rolling | `stratum_incident_mttr_seconds` |
| MTTR (Mean Time to Resolve) - High | < 4 hours | 30-day rolling | `stratum_incident_mttr_seconds` |
| MTTR (Mean Time to Resolve) - Medium | < 24 hours | 30-day rolling | `stratum_incident_mttr_seconds` |
| Incident recurrence rate | < 10% | 90-day rolling | Post-mortem tracking |

---

## 9. Security

| Metric | Target | Window | Source |
|--------|--------|--------|--------|
| Vulnerability remediation (critical) | < 24 hours | Continuous | Trivy + pip-audit |
| Vulnerability remediation (high) | < 7 days | Continuous | Trivy + pip-audit |
| Secret leak detection | 0 leaked secrets | Continuous | gitleaks CI scan |
| Failed login attempt response | Block after 5 attempts | Continuous | Rate limiter + MFA lockout |

---

## Alerting Thresholds

SLO thresholds map to Prometheus alerting rules in
`monitoring/prometheus/alerting_rules.yml`.

| SLO | Warning Threshold | Critical Threshold |
|-----|-------------------|--------------------|
| Availability | < 99.95% (1h window) | < 99.9% (1h window) |
| p95 latency | > 500ms for 5m | > 2s for 5m |
| Error rate | > 1% for 5m | > 5% for 5m |
| Trust gate block rate | > 30% for 15m | > 50% for 15m |
| Signal health | < 40 for 15m | < 20 for 10m |
| Celery task failure | > 5% for 10m | > 10% for 10m |
| Platform sync staleness | > 2h | > 4h |

---

## Dashboard Queries (Grafana)

### Availability
```promql
1 - (
  sum(rate(stratum_http_latency_seconds_count{status=~"5.."}[5m]))
  /
  sum(rate(stratum_http_latency_seconds_count[5m]))
)
```

### p95 Latency
```promql
histogram_quantile(0.95,
  sum(rate(stratum_http_latency_seconds_bucket[5m])) by (le)
)
```

### Error Rate
```promql
sum(rate(stratum_http_latency_seconds_count{status=~"5.."}[5m]))
/
sum(rate(stratum_http_latency_seconds_count[5m]))
```

### Trust Gate Decision Distribution
```promql
sum(rate(stratum_trust_gate_decisions_total[5m])) by (decision)
```

### Active Tenants
```promql
stratum_active_tenants
```

---

## Review Cadence

| Review | Frequency | Attendees |
|--------|-----------|-----------|
| SLO dashboard review | Weekly | Engineering Lead, SRE |
| Error budget review | Monthly | Engineering, Product, SRE |
| SLO target adjustment | Quarterly | Engineering, Product, Leadership |
| Post-mortem (SLO breach) | Per incident | Engineering, SRE, impacted team |
