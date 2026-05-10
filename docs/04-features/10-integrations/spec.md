# Platform Integrations Specification

## Overview

The Platform Integrations module provides unified connectivity to advertising platforms (Meta, Google, TikTok, Snapchat) via their Conversion APIs (CAPI). It includes resilience patterns, PII hashing, event mapping, and health monitoring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 PLATFORM INTEGRATIONS ARCHITECTURE              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  APPLICATION LAYER                        │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │              CAPI Event Router                    │   │  │
│  │  │  • Routes events to appropriate connectors       │   │  │
│  │  │  • Handles deduplication                         │   │  │
│  │  │  • Batches events for throughput                 │   │  │
│  │  └────────────────────┬─────────────────────────────┘   │  │
│  └───────────────────────┼──────────────────────────────────┘  │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  RESILIENCE LAYER                         │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ Circuit  │ │  Rate    │ │  Retry   │ │Connection│   │  │
│  │  │ Breaker  │ │ Limiter  │ │  Logic   │ │   Pool   │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  CONNECTOR LAYER                          │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   Meta   │ │  Google  │ │  TikTok  │ │ Snapchat │   │  │
│  │  │   CAPI   │ │Enhanced  │ │ Events   │ │   CAPI   │   │  │
│  │  │Connector │ │Conversions│ │   API   │ │Connector │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  └───────┼────────────┼────────────┼────────────┼───────────┘  │
│          ▼            ▼            ▼            ▼              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  PLATFORM APIs                            │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ graph.   │ │googleads.│ │business- │ │   tr.    │   │  │
│  │  │facebook. │ │googleapis│ │api.tiktok│ │snapchat. │   │  │
│  │  │  .com    │ │   .com   │ │   .com   │ │   .com   │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### ConnectionStatus

```python
class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"
```

### ConnectionResult

```python
class ConnectionResult:
    status: ConnectionStatus
    platform: str
    message: str
    details: dict | None
```

### CAPIResponse

```python
class CAPIResponse:
    success: bool
    events_received: int
    events_processed: int
    errors: list[dict]
    platform: str
    request_id: str | None
```

### EventDeliveryLog

```python
class EventDeliveryLog:
    event_id: str
    platform: str
    event_name: str
    timestamp: datetime
    success: bool
    latency_ms: float
    error_message: str | None
    request_id: str | None
    retry_count: int
```

### ConnectorHealthStatus

```python
class ConnectorHealthStatus:
    platform: str
    status: str                    # healthy, degraded, unhealthy
    last_check: datetime
    success_rate_1h: float
    avg_latency_ms: float
    circuit_state: str
    error_count_1h: int
    events_processed_1h: int
    issues: list[str]
```

---

## Platform Connectors

### Base Connector

Abstract base class with common functionality.

```python
class BaseCAPIConnector(ABC):
    PLATFORM_NAME: str
    MAX_RETRIES: int = 3
    RETRY_DELAYS: list[float] = [1.0, 2.0, 4.0]

    # Components
    hasher: PIIHasher
    mapper: AIEventMapper
    circuit_breaker: CircuitBreaker
    rate_limiter: RateLimiter

    # Abstract methods
    async def connect(credentials: dict) -> ConnectionResult
    async def test_connection() -> ConnectionResult
    async def _send_events_impl(events: list[dict]) -> CAPIResponse

    # Concrete methods
    async def send_events(events: list[dict]) -> CAPIResponse
    def format_user_data(user_data: dict) -> dict
    def map_event(event_name: str, params: dict) -> dict
```

### Meta CAPI Connector

```python
class MetaCAPIConnector(BaseCAPIConnector):
    PLATFORM_NAME = "meta"
    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    # Required credentials
    pixel_id: str
    access_token: str
```

### Google Enhanced Conversions Connector

```python
class GoogleCAPIConnector(BaseCAPIConnector):
    PLATFORM_NAME = "google"
    API_VERSION = "v15"

    # Required credentials
    customer_id: str
    conversion_action_id: str
    developer_token: str
    refresh_token: str
    client_id: str
    client_secret: str
```

### TikTok Events API Connector

```python
class TikTokCAPIConnector(BaseCAPIConnector):
    PLATFORM_NAME = "tiktok"
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    # Required credentials
    pixel_code: str
    access_token: str
```

### Snapchat CAPI Connector

```python
class SnapchatCAPIConnector(BaseCAPIConnector):
    PLATFORM_NAME = "snapchat"
    BASE_URL = "https://tr.snapchat.com/v2"

    # Required credentials
    pixel_id: str
    access_token: str
```

---

## Resilience Patterns

### Circuit Breaker

Prevents cascading failures by stopping requests to failing services.

```python
class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

    def can_execute() -> bool
    def record_success()
    def record_failure()
```

### Rate Limiter

Token bucket algorithm for API call rate limiting.

```python
class RateLimiter:
    max_tokens: int = 100
    refill_rate: float = 10.0  # tokens per second

    def acquire(tokens: int = 1) -> bool
    async def wait_for_token(tokens: int = 1)
```

### Platform Rate Limits

| Platform | Events/Minute | Recommended Batch Size |
|----------|---------------|------------------------|
| Meta | 1000 | 1000 |
| Google | 2000 | 2000 |
| TikTok | 600 | 500 |
| Snapchat | 500 | 1000 |
| WhatsApp | 80 | 100 |

---

## PII Hashing

### PIIHasher

Hashes personally identifiable information before sending to platforms.

```python
class PIIHasher:
    def hash_value(value: str) -> str
    def hash_data(user_data: dict) -> dict
    def normalize_email(email: str) -> str
    def normalize_phone(phone: str) -> str
```

### Hashed Fields

| Field | Hash Algorithm | Normalization |
|-------|----------------|---------------|
| `email` → `em` | SHA-256 | Lowercase, trim |
| `phone` → `ph` | SHA-256 | E.164 format |
| `first_name` → `fn` | SHA-256 | Lowercase, trim |
| `last_name` → `ln` | SHA-256 | Lowercase, trim |
| `city` → `ct` | SHA-256 | Lowercase, trim |
| `state` → `st` | SHA-256 | Two-letter code |
| `zip` → `zp` | SHA-256 | First 5 digits |
| `country` → `country` | SHA-256 | Two-letter code |

---

## Event Mapping

### AIEventMapper

Maps custom events to platform-specific event names.

```python
class EventMapping:
    source_event: str
    platform_events: dict[str, str]
    parameters: dict

class AIEventMapper:
    def map_event(event_name: str, params: dict) -> EventMapping
```

### Standard Event Mappings

| Custom Event | Meta | Google | TikTok | Snapchat |
|--------------|------|--------|--------|----------|
| `purchase` | Purchase | purchase | CompletePayment | PURCHASE |
| `add_to_cart` | AddToCart | add_to_cart | AddToCart | ADD_CART |
| `lead` | Lead | generate_lead | SubmitForm | SIGN_UP |
| `page_view` | PageView | page_view | PageView | PAGE_VIEW |
| `sign_up` | CompleteRegistration | sign_up | CompleteRegistration | SIGN_UP |
| `search` | Search | search | Search | SEARCH |

---

## Health Monitoring

### ConnectorHealthMonitor

Monitors health of all platform connectors.

```python
class ConnectorHealthMonitor:
    def check_health(connector: BaseCAPIConnector) -> ConnectorHealthStatus
    def get_health_summary(connectors: list) -> dict
    def get_health_history(platform: str, hours: int = 24) -> list[dict]
    def register_alert_callback(callback)
```

### Health Thresholds

| Metric | Healthy | Degraded | Unhealthy |
|--------|---------|----------|-----------|
| Success Rate | ≥90% | 70-89% | <70% |
| Latency | <5s | 5-10s | >10s |
| Circuit State | CLOSED | HALF_OPEN | OPEN |

---

## Batch Optimization

### BatchOptimizer

Optimizes event batching for maximum throughput.

```python
class BatchOptimizer:
    def record_batch_performance(platform, batch_size, success, latency_ms, events_processed)
    def optimize_batch_size(platform: str, current_batch_size: int) -> BatchOptimizationResult
```

### BatchOptimizationResult

```python
class BatchOptimizationResult:
    original_batch_size: int
    optimized_batch_size: int
    estimated_throughput_improvement: float
    recommendation: str
```

---

## Connection Pool

### ConnectionPool

Manages HTTP connections for high-throughput scenarios.

```python
class ConnectionPool:
    max_connections: int = 10
    timeout: float = 30.0

    async def get_client(platform: str) -> httpx.AsyncClient
    async def scale_up(platform: str)
    async def scale_down(platform: str)
    async def close_all()
    def get_pool_stats() -> dict
```

---

## Event Deduplication

### EventDeduplicator

Prevents duplicate conversion events.

```python
class EventDeduplicator:
    ttl_hours: int = 24
    max_size: int = 100000

    def is_duplicate(event: dict) -> bool
    def get_stats() -> dict
```

---

## Credential Storage

### Required Credentials by Platform

| Platform | Credentials |
|----------|-------------|
| Meta | `pixel_id`, `access_token` |
| Google | `customer_id`, `conversion_action_id`, `developer_token`, `refresh_token`, `client_id`, `client_secret` |
| TikTok | `pixel_code`, `access_token` |
| Snapchat | `pixel_id`, `access_token` |
| WhatsApp | `phone_number_id`, `access_token`, `webhook_verify_token` |

### Security

- Credentials encrypted at rest
- Stored in environment variables or secrets manager
- Never logged or exposed in responses
- Rotated on schedule

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
