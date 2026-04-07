# Monitoring & Observability

## Overview

This document covers the monitoring stack, metrics collection, alerting configuration, and dashboards for the Stratum AI platform.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   MONITORING ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  APPLICATION LAYER                        │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   API    │ │  Celery  │ │  React   │ │  Workers │   │  │
│  │  │ FastAPI  │ │  Tasks   │ │ Frontend │ │          │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  └───────┼────────────┼────────────┼────────────┼──────────┘  │
│          │            │            │            │              │
│          └────────────┴─────┬──────┴────────────┘              │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  COLLECTION LAYER                         │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │Prometheus│ │ Loki     │ │ Jaeger   │ │ Sentry   │   │  │
│  │  │ Metrics  │ │ Logs     │ │ Traces   │ │ Errors   │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  └───────┼────────────┼────────────┼────────────┼──────────┘  │
│          │            │            │            │              │
│          └────────────┴─────┬──────┴────────────┘              │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  VISUALIZATION                            │  │
│  │                                                          │  │
│  │  ┌───────────────────────────────────────────────────┐  │  │
│  │  │                    GRAFANA                         │  │  │
│  │  │  Dashboards | Alerts | Annotations                │  │  │
│  │  └───────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Metrics

### Application Metrics

#### API Metrics

```python
# Endpoint latency histogram
api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    labelnames=["method", "endpoint", "status_code"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Request counter
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    labelnames=["method", "endpoint", "status_code"]
)

# Active connections gauge
api_active_connections = Gauge(
    "api_active_connections",
    "Active WebSocket connections"
)
```

#### Trust Engine Metrics

```python
# Signal health distribution
signal_health_score = Histogram(
    "signal_health_score",
    "Signal health score distribution",
    labelnames=["signal_type", "tenant_id"],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

# Trust gate decisions
trust_gate_decisions = Counter(
    "trust_gate_decisions_total",
    "Trust gate decision outcomes",
    labelnames=["decision", "tenant_id"]  # pass, hold, block
)

# Automation executions
automation_executions = Counter(
    "automation_executions_total",
    "Automation execution outcomes",
    labelnames=["automation_type", "status", "tenant_id"]
)
```

#### CDP Metrics

```python
# Profile operations
cdp_profile_operations = Counter(
    "cdp_profile_operations_total",
    "CDP profile operations",
    labelnames=["operation", "tenant_id"]  # create, update, merge
)

# Event ingestion rate
cdp_events_ingested = Counter(
    "cdp_events_ingested_total",
    "CDP events ingested",
    labelnames=["event_type", "tenant_id"]
)

# Segment evaluation time
cdp_segment_evaluation = Histogram(
    "cdp_segment_evaluation_seconds",
    "Segment evaluation duration",
    labelnames=["segment_id", "tenant_id"]
)
```

### Infrastructure Metrics

#### Database

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `pg_connections_active` | Active connections | > 80% of max |
| `pg_replication_lag_seconds` | Replica lag | > 30 seconds |
| `pg_deadlocks_total` | Deadlock count | > 0 |
| `pg_slow_queries_total` | Queries > 1s | > 10/min |

#### Redis

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `redis_memory_used_bytes` | Memory usage | > 80% of max |
| `redis_connected_clients` | Client connections | > 1000 |
| `redis_keyspace_hits_ratio` | Cache hit ratio | < 90% |
| `redis_commands_processed_total` | Commands/sec | Baseline +50% |

#### Celery

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `celery_workers_active` | Active workers | < expected |
| `celery_queue_length` | Queue depth | > 1000 |
| `celery_task_duration_seconds` | Task execution time | > SLA |
| `celery_task_failures_total` | Failed tasks | > 1% |

---

## Logging

### Log Levels

| Level | Usage |
|-------|-------|
| `ERROR` | Unhandled exceptions, service failures |
| `WARNING` | Degraded conditions, retry attempts |
| `INFO` | Request/response, business events |
| `DEBUG` | Detailed debugging (dev only) |

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Request logging
logger.info(
    "api_request",
    method=request.method,
    path=request.url.path,
    tenant_id=current_tenant.id,
    user_id=current_user.id,
    duration_ms=duration * 1000,
    status_code=response.status_code,
)

# Business event logging
logger.info(
    "automation_executed",
    automation_id=automation.id,
    tenant_id=automation.tenant_id,
    signal_health=signal_health,
    decision="pass",
    actions_taken=["pause_campaign", "send_alert"],
)

# Error logging
logger.error(
    "integration_failure",
    platform="meta",
    tenant_id=tenant_id,
    error_code=error.code,
    error_message=str(error),
    retry_attempt=attempt,
    exc_info=True,
)
```

### Log Aggregation

```yaml
# Loki configuration
loki:
  ingestion:
    - job: stratum-api
      labels:
        app: stratum
        component: api
      pipeline_stages:
        - json:
            expressions:
              level: level
              tenant_id: tenant_id
              request_id: request_id
        - labels:
            level:
            tenant_id:
```

---

## Alerting

### Alert Rules

#### Critical Alerts (Page Immediately)

```yaml
groups:
  - name: critical
    rules:
      - alert: APIDown
        expr: up{job="stratum-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API service is down"

      - alert: HighErrorRate
        expr: rate(api_requests_total{status_code=~"5.."}[5m]) / rate(api_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Error rate exceeds 5%"

      - alert: DatabaseDown
        expr: pg_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is unreachable"
```

#### Warning Alerts (Notify)

```yaml
groups:
  - name: warning
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency exceeds 1 second"

      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog exceeds 1000"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage exceeds 80%"
```

#### Business Alerts

```yaml
groups:
  - name: business
    rules:
      - alert: SignalHealthDegraded
        expr: avg(signal_health_score) by (tenant_id) < 40
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Tenant {{ $labels.tenant_id }} signal health degraded"

      - alert: IntegrationFailureSpike
        expr: rate(integration_failures_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Integration failure rate spike"
```

### Alert Routing

```yaml
# Alertmanager configuration
route:
  receiver: default
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true

    - match:
        severity: warning
      receiver: slack-warnings

    - match:
        alertname: SignalHealthDegraded
      receiver: customer-success

receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: ${PAGERDUTY_KEY}

  - name: slack-warnings
    slack_configs:
      - channel: '#platform-alerts'

  - name: customer-success
    slack_configs:
      - channel: '#customer-health'
```

---

## Dashboards

### API Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  API Overview                                     Last 24h     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Requests/min          Error Rate           P95 Latency        │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │  12,450  │         │   0.02%  │         │   89ms   │        │
│  │  +5% ▲   │         │  Normal  │         │  Normal  │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│                                                                 │
│  Request Rate (24h)                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   ▃▄▅▆▇█▇▆▅▄▃▂▃▄▅▆▇█▇▆▅▄▃▂▃▄▅▆▇█▇▆▅▄▃              │   │
│  │   00:00        06:00        12:00        18:00         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Top Endpoints by Latency                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ /api/v1/cdp/profiles/search      P95: 245ms  Calls: 45K │   │
│  │ /api/v1/analytics/dashboard      P95: 189ms  Calls: 12K │   │
│  │ /api/v1/campaigns                P95: 78ms   Calls: 8K  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Trust Engine Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  Trust Engine                                     Last 24h     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Decisions             Avg Health           Automations        │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │ Pass: 85%│         │    72    │         │  1,245   │        │
│  │ Hold: 12%│         │  Healthy │         │ Executed │        │
│  │ Block: 3%│         └──────────┘         └──────────┘        │
│  └──────────┘                                                   │
│                                                                 │
│  Signal Health Distribution                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ██░░░░░░░░ 0-20                                        │   │
│  │  ███░░░░░░░ 21-40                                       │   │
│  │  █████░░░░░ 41-60                                       │   │
│  │  ███████░░░ 61-80                                       │   │
│  │  ██████████ 81-100                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Gate Decisions by Tenant                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Tenant    | Pass   | Hold   | Block  | Avg Health      │   │
│  │ Acme      | 92%    | 6%     | 2%     | 78              │   │
│  │ TechCo    | 88%    | 10%    | 2%     | 71              │   │
│  │ RetailX   | 75%    | 18%    | 7%     | 58              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  Infrastructure                                   Last 24h     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Database              Redis                Celery              │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │ ● Healthy│         │ ● Healthy│         │ ● Healthy│        │
│  │ 45/100   │         │ 2.1/8 GB │         │ 8/8      │        │
│  │ Conns    │         │ Memory   │         │ Workers  │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│                                                                 │
│  Database Connections                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   ▄▄▄▄▅▅▅▅▆▆▆▆▅▅▅▅▄▄▄▄▃▃▃▃▄▄▄▄▅▅▅▅                    │   │
│  │   ─────────────── Max: 100 ───────────────             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Celery Queue Depth                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   ▂▂▃▃▄▄▅▅▄▄▃▃▂▂▃▃▄▄▅▅▄▄▃▃▂▂▃▃▄▄▅▅                    │   │
│  │   ─────────────── Threshold: 1000 ────────────────     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Health Checks

### Endpoint Configuration

```python
@router.get("/health")
async def health_check():
    """Basic health check for load balancers"""
    return {"status": "healthy"}

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for monitoring"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "celery": await check_celery(),
    }

    overall = "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }

@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    # Check if service can handle requests
    if not await is_ready():
        raise HTTPException(status_code=503, detail="Not ready")
    return {"ready": True}

@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"alive": True}
```

---

## Tracing

### Distributed Tracing Setup

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

# Example traced operation
@tracer.start_as_current_span("process_automation")
async def process_automation(automation_id: int):
    span = trace.get_current_span()
    span.set_attribute("automation_id", automation_id)

    with tracer.start_as_current_span("evaluate_signal"):
        signal_health = await evaluate_signal_health()
        span.set_attribute("signal_health", signal_health)

    with tracer.start_as_current_span("make_decision"):
        decision = await trust_gate_decision(signal_health)
        span.set_attribute("decision", decision)

    return decision
```

---

## SLIs and SLOs

### Service Level Indicators

| SLI | Measurement | Target |
|-----|-------------|--------|
| Availability | Successful requests / Total requests | 99.9% |
| Latency P95 | 95th percentile response time | < 500ms |
| Error Rate | 5xx errors / Total requests | < 0.1% |
| Throughput | Requests per second capacity | > 1000 RPS |

### Service Level Objectives

```yaml
slos:
  - name: API Availability
    indicator: availability
    target: 99.9
    window: 30d
    budget: 43.2m  # 30 days * 24h * 60m * 0.001

  - name: API Latency
    indicator: latency_p95
    target: 500ms
    window: 30d

  - name: Trust Engine Accuracy
    indicator: automation_success_rate
    target: 99.5
    window: 30d
```

---

## Related Documentation

- [Runbooks](./runbooks.md) - Operational procedures
- [Incidents](./incidents.md) - Incident management
- [Security](../06-appendix/security.md) - Security practices
