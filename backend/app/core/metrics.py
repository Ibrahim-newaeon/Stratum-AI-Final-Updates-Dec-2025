# =============================================================================
# Stratum AI - Prometheus Metrics Configuration
# =============================================================================
"""
Prometheus metrics for Stratum AI backend.

Exposes:
- Standard HTTP metrics (request count, latency histograms)
- Custom business metrics (EMQ scores, trust gate decisions)
- System health metrics

Integration:
- Uses prometheus-fastapi-instrumentator for HTTP metrics
- Custom collectors for business-specific metrics
"""

from typing import Callable, Optional
from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info as MetricInfo
from fastapi import FastAPI


# =============================================================================
# Custom Business Metrics
# =============================================================================

# EMQ (Event Measurement Quality) Metrics
emq_score_gauge = Gauge(
    name="stratum_emq_score",
    documentation="Current EMQ score by tenant and platform",
    labelnames=["tenant_id", "platform"],
)

emq_driver_gauge = Gauge(
    name="stratum_emq_driver_score",
    documentation="EMQ driver component scores",
    labelnames=["tenant_id", "platform", "driver"],
)

emq_confidence_band = Gauge(
    name="stratum_emq_confidence_band",
    documentation="EMQ confidence band (0=unsafe, 1=directional, 2=reliable)",
    labelnames=["tenant_id"],
)

# Trust Gate Metrics
trust_gate_decisions_total = Counter(
    name="stratum_trust_gate_decisions_total",
    documentation="Total trust gate decisions by outcome",
    labelnames=["decision", "action_type", "platform"],
)

trust_gate_evaluation_duration = Histogram(
    name="stratum_trust_gate_evaluation_duration_seconds",
    documentation="Time spent evaluating trust gate decisions",
    labelnames=["platform"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Autopilot Metrics
autopilot_mode_gauge = Gauge(
    name="stratum_autopilot_mode",
    documentation="Current autopilot mode (0=frozen, 1=cuts_only, 2=limited, 3=normal)",
    labelnames=["tenant_id"],
)

autopilot_actions_total = Counter(
    name="stratum_autopilot_actions_total",
    documentation="Total autopilot actions executed",
    labelnames=["tenant_id", "action_type", "platform", "status"],
)

autopilot_budget_at_risk = Gauge(
    name="stratum_autopilot_budget_at_risk_usd",
    documentation="Budget at risk due to signal health issues",
    labelnames=["tenant_id"],
)

# Signal Health Metrics
signal_health_score = Gauge(
    name="stratum_signal_health_score",
    documentation="Overall signal health score",
    labelnames=["tenant_id", "platform"],
)

signal_health_component = Gauge(
    name="stratum_signal_health_component",
    documentation="Signal health component scores",
    labelnames=["tenant_id", "platform", "component"],
)

signal_volatility_index = Gauge(
    name="stratum_signal_volatility_index",
    documentation="Signal Volatility Index (SVI)",
    labelnames=["tenant_id"],
)

# Platform Integration Metrics
platform_api_requests_total = Counter(
    name="stratum_platform_api_requests_total",
    documentation="Total API requests to ad platforms",
    labelnames=["platform", "endpoint", "status"],
)

platform_api_latency = Histogram(
    name="stratum_platform_api_latency_seconds",
    documentation="Latency for ad platform API calls",
    labelnames=["platform", "endpoint"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

platform_sync_status = Gauge(
    name="stratum_platform_sync_status",
    documentation="Platform data sync status (0=failed, 1=success)",
    labelnames=["tenant_id", "platform"],
)

platform_sync_last_success = Gauge(
    name="stratum_platform_sync_last_success_timestamp",
    documentation="Timestamp of last successful platform sync",
    labelnames=["tenant_id", "platform"],
)

# Conversion API (CAPI) Metrics
capi_events_sent_total = Counter(
    name="stratum_capi_events_sent_total",
    documentation="Total conversion events sent via CAPI",
    labelnames=["platform", "event_type", "status"],
)

capi_match_rate = Gauge(
    name="stratum_capi_match_rate",
    documentation="CAPI event match rate percentage",
    labelnames=["tenant_id", "platform"],
)

capi_latency = Histogram(
    name="stratum_capi_latency_seconds",
    documentation="Latency for CAPI event delivery",
    labelnames=["platform"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Attribution Metrics
attribution_variance = Gauge(
    name="stratum_attribution_variance_pct",
    documentation="Attribution variance between platform and GA4",
    labelnames=["tenant_id", "platform"],
)

# Incident Metrics
incidents_total = Counter(
    name="stratum_incidents_total",
    documentation="Total incidents by severity",
    labelnames=["tenant_id", "severity", "platform"],
)

incidents_open = Gauge(
    name="stratum_incidents_open",
    documentation="Currently open incidents",
    labelnames=["tenant_id", "severity"],
)

incident_mttr_seconds = Histogram(
    name="stratum_incident_mttr_seconds",
    documentation="Mean time to resolution for incidents",
    labelnames=["severity"],
    buckets=(300, 900, 1800, 3600, 7200, 14400, 28800, 86400),
)

# Tenant Metrics
active_tenants = Gauge(
    name="stratum_active_tenants",
    documentation="Number of active tenants",
)

tenant_api_requests_total = Counter(
    name="stratum_tenant_api_requests_total",
    documentation="API requests per tenant",
    labelnames=["tenant_id", "endpoint_group"],
)

# Celery Task Metrics
celery_task_duration = Histogram(
    name="stratum_celery_task_duration_seconds",
    documentation="Duration of Celery task execution",
    labelnames=["task_name", "status"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
)

celery_tasks_total = Counter(
    name="stratum_celery_tasks_total",
    documentation="Total Celery tasks by name and status",
    labelnames=["task_name", "status"],
)


# =============================================================================
# Helper Functions for Recording Metrics
# =============================================================================

def record_emq_score(
    tenant_id: int,
    platform: str,
    score: float,
    drivers: Optional[dict] = None,
) -> None:
    """
    Record EMQ score metrics.

    Args:
        tenant_id: Tenant identifier
        platform: Ad platform (meta, google, tiktok, snapchat)
        score: EMQ score (0-100)
        drivers: Optional dict of driver scores
    """
    emq_score_gauge.labels(
        tenant_id=str(tenant_id),
        platform=platform.lower(),
    ).set(score)

    if drivers:
        for driver_name, driver_score in drivers.items():
            emq_driver_gauge.labels(
                tenant_id=str(tenant_id),
                platform=platform.lower(),
                driver=driver_name,
            ).set(driver_score)


def record_trust_gate_decision(
    decision: str,
    action_type: str,
    platform: str,
    evaluation_time: float,
) -> None:
    """
    Record trust gate decision metrics.

    Args:
        decision: Gate decision (pass, hold, block)
        action_type: Type of automation action
        platform: Ad platform
        evaluation_time: Time taken to evaluate (seconds)
    """
    trust_gate_decisions_total.labels(
        decision=decision.lower(),
        action_type=action_type,
        platform=platform.lower(),
    ).inc()

    trust_gate_evaluation_duration.labels(
        platform=platform.lower(),
    ).observe(evaluation_time)


def record_autopilot_action(
    tenant_id: int,
    action_type: str,
    platform: str,
    status: str,
) -> None:
    """
    Record autopilot action execution.

    Args:
        tenant_id: Tenant identifier
        action_type: Type of action executed
        platform: Ad platform
        status: Execution status (success, failed, blocked)
    """
    autopilot_actions_total.labels(
        tenant_id=str(tenant_id),
        action_type=action_type,
        platform=platform.lower(),
        status=status.lower(),
    ).inc()


def record_signal_health(
    tenant_id: int,
    platform: str,
    overall_score: float,
    components: Optional[dict] = None,
) -> None:
    """
    Record signal health metrics.

    Args:
        tenant_id: Tenant identifier
        platform: Ad platform
        overall_score: Overall health score (0-100)
        components: Optional dict of component scores (emq, freshness, variance, anomaly)
    """
    signal_health_score.labels(
        tenant_id=str(tenant_id),
        platform=platform.lower(),
    ).set(overall_score)

    if components:
        for component_name, component_score in components.items():
            signal_health_component.labels(
                tenant_id=str(tenant_id),
                platform=platform.lower(),
                component=component_name,
            ).set(component_score)


def record_platform_api_call(
    platform: str,
    endpoint: str,
    status: str,
    latency: float,
) -> None:
    """
    Record platform API call metrics.

    Args:
        platform: Ad platform name
        endpoint: API endpoint called
        status: Response status (success, error, timeout)
        latency: Request latency in seconds
    """
    platform_api_requests_total.labels(
        platform=platform.lower(),
        endpoint=endpoint,
        status=status.lower(),
    ).inc()

    platform_api_latency.labels(
        platform=platform.lower(),
        endpoint=endpoint,
    ).observe(latency)


def record_capi_event(
    platform: str,
    event_type: str,
    status: str,
    latency: Optional[float] = None,
) -> None:
    """
    Record CAPI event metrics.

    Args:
        platform: Ad platform name
        event_type: Type of conversion event
        status: Delivery status (sent, failed, deduplicated)
        latency: Optional delivery latency in seconds
    """
    capi_events_sent_total.labels(
        platform=platform.lower(),
        event_type=event_type,
        status=status.lower(),
    ).inc()

    if latency is not None:
        capi_latency.labels(
            platform=platform.lower(),
        ).observe(latency)


def record_incident(
    tenant_id: int,
    severity: str,
    platform: str,
    resolved: bool = False,
    resolution_time: Optional[float] = None,
) -> None:
    """
    Record incident metrics.

    Args:
        tenant_id: Tenant identifier
        severity: Incident severity (critical, high, medium, low)
        platform: Affected platform
        resolved: Whether incident is resolved
        resolution_time: Optional time to resolution in seconds
    """
    incidents_total.labels(
        tenant_id=str(tenant_id),
        severity=severity.lower(),
        platform=platform.lower(),
    ).inc()

    if resolution_time is not None:
        incident_mttr_seconds.labels(
            severity=severity.lower(),
        ).observe(resolution_time)


# =============================================================================
# Custom Instrumentator Metrics
# =============================================================================

def request_by_tenant_instrumentation() -> Callable[[MetricInfo], None]:
    """
    Custom instrumentation to track requests by tenant.
    Extracts tenant_id from request state.
    """
    def instrumentation(info: MetricInfo) -> None:
        if info.modified_handler:
            # Extract tenant from request state if available
            tenant_id = getattr(info.request.state, "tenant_id", None)
            if tenant_id:
                # Determine endpoint group from path
                path = info.request.url.path
                if "/emq" in path:
                    endpoint_group = "emq"
                elif "/trust" in path or "/autopilot" in path:
                    endpoint_group = "trust"
                elif "/analytics" in path or "/insights" in path:
                    endpoint_group = "analytics"
                elif "/campaigns" in path or "/ads" in path:
                    endpoint_group = "campaigns"
                elif "/auth" in path:
                    endpoint_group = "auth"
                else:
                    endpoint_group = "other"

                tenant_api_requests_total.labels(
                    tenant_id=str(tenant_id),
                    endpoint_group=endpoint_group,
                ).inc()

    return instrumentation


# =============================================================================
# Instrumentator Setup
# =============================================================================

def create_instrumentator() -> Instrumentator:
    """
    Create and configure the Prometheus instrumentator.

    Returns:
        Configured Instrumentator instance
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[
            "/health",
            "/health/ready",
            "/health/live",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
        env_var_name="ENABLE_METRICS",
        inprogress_name="stratum_http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics (latency histogram)
    instrumentator.add(
        metrics.latency(
            metric_namespace="stratum",
            metric_subsystem="http",
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 7.5, 10.0, 30.0, 60.0),
        )
    )

    # Add request size metrics
    instrumentator.add(
        metrics.request_size(
            metric_namespace="stratum",
            metric_subsystem="http",
        )
    )

    # Add response size metrics
    instrumentator.add(
        metrics.response_size(
            metric_namespace="stratum",
            metric_subsystem="http",
        )
    )

    return instrumentator


def setup_metrics(app: FastAPI) -> Instrumentator:
    """
    Setup Prometheus metrics for the FastAPI application.

    This function:
    1. Creates the instrumentator with default HTTP metrics
    2. Instruments the app
    3. Exposes the /metrics endpoint

    Args:
        app: FastAPI application instance

    Returns:
        Configured Instrumentator instance
    """
    instrumentator = create_instrumentator()

    # Instrument the app
    instrumentator.instrument(app)

    # Expose the /metrics endpoint
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=True,
        tags=["Monitoring"],
    )

    return instrumentator


# =============================================================================
# Autopilot Mode Mapping
# =============================================================================

AUTOPILOT_MODE_VALUES = {
    "frozen": 0,
    "cuts_only": 1,
    "limited": 2,
    "normal": 3,
}

CONFIDENCE_BAND_VALUES = {
    "unsafe": 0,
    "directional": 1,
    "reliable": 2,
}


def set_autopilot_mode_metric(tenant_id: int, mode: str) -> None:
    """
    Set the autopilot mode gauge for a tenant.

    Args:
        tenant_id: Tenant identifier
        mode: Autopilot mode (frozen, cuts_only, limited, normal)
    """
    mode_value = AUTOPILOT_MODE_VALUES.get(mode.lower(), 2)
    autopilot_mode_gauge.labels(tenant_id=str(tenant_id)).set(mode_value)


def set_confidence_band_metric(tenant_id: int, band: str) -> None:
    """
    Set the EMQ confidence band gauge for a tenant.

    Args:
        tenant_id: Tenant identifier
        band: Confidence band (unsafe, directional, reliable)
    """
    band_value = CONFIDENCE_BAND_VALUES.get(band.lower(), 1)
    emq_confidence_band.labels(tenant_id=str(tenant_id)).set(band_value)
