# Backend Overview

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastAPI | Latest | Async REST API framework |
| Language | Python | 3.11+ | Type hints, performance |
| ORM | SQLAlchemy | 2.x | Async database operations |
| Validation | Pydantic | 2.x | Request/response schemas |
| Task Queue | Celery | 5.x | Background job processing |
| Scheduler | Celery Beat | 5.x | Periodic task scheduling |
| Database | PostgreSQL | 16 | Primary data store |
| Cache | Redis | 7 | Caching, message broker |
| Logging | Structlog | Latest | Structured JSON logging |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── base_models.py          # SQLAlchemy ORM models
│   │
│   ├── core/                   # Core application modules
│   │   ├── config.py           # Settings (Pydantic BaseSettings)
│   │   ├── logging.py          # Structured logging setup
│   │   ├── metrics.py          # Prometheus metrics
│   │   ├── websocket.py        # WebSocket connection manager
│   │   └── security.py         # Security utilities
│   │
│   ├── api/                    # API layer
│   │   └── v1/
│   │       ├── __init__.py     # Router aggregation
│   │       └── endpoints/      # 51+ endpoint modules
│   │           ├── auth.py
│   │           ├── campaigns.py
│   │           ├── cdp.py
│   │           └── ...
│   │
│   ├── auth/                   # Authentication
│   │   ├── jwt.py              # JWT token handling
│   │   ├── mfa.py              # Multi-factor authentication
│   │   ├── permissions.py      # RBAC implementation
│   │   └── deps.py             # FastAPI dependencies
│   │
│   ├── db/                     # Database
│   │   ├── session.py          # Connection management
│   │   ├── base.py             # SQLAlchemy base classes
│   │   └── utils.py            # Database utilities
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── auth.py             # Auth request/response
│   │   ├── campaign.py         # Campaign schemas
│   │   └── ...
│   │
│   ├── services/               # Business logic layer
│   │   ├── cdp/                # Customer Data Platform
│   │   │   ├── profile_service.py
│   │   │   ├── segment_service.py
│   │   │   └── audience_sync/
│   │   ├── trust_engine/       # Trust gate logic
│   │   ├── integrations/       # External API integrations
│   │   └── ...
│   │
│   ├── workers/                # Background tasks
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Task definitions
│   │   └── ...
│   │
│   └── middleware/             # Request middleware
│       ├── audit.py            # Audit logging
│       ├── tenant.py           # Tenant extraction
│       └── rate_limit.py       # Rate limiting
│
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
│
├── tests/                      # Test suite
│   ├── conftest.py             # Pytest fixtures
│   ├── test_auth.py
│   └── ...
│
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── Dockerfile                  # Container definition
└── alembic.ini                 # Alembic configuration
```

---

## Application Lifecycle

### Startup Sequence

```python
# From app/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Sentry (if configured)
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, ...)

    # 2. Verify database connection
    db_health = await check_database_health()

    # 3. Start WebSocket manager
    await ws_manager.start()

    # 4. Prometheus metrics ready
    logger.info("prometheus_metrics_ready")

    yield  # Application running

    # Shutdown
    await ws_manager.stop()
    await async_engine.dispose()
```

### Request Processing Flow

1. **Load Balancer** → Routes request to backend
2. **Middleware Stack** (executed in reverse order):
   - Request Timing (adds X-Request-ID, X-Process-Time-Ms)
   - Audit Middleware (logs state-changing requests)
   - Tenant Middleware (extracts tenant context)
   - Rate Limit Middleware (throttles requests)
   - GZip Middleware (compresses responses)
   - CORS Middleware (handles cross-origin)
3. **Router** → Routes to appropriate endpoint
4. **Endpoint** → Executes business logic
5. **Response** → Returns JSON via ORJSONResponse

---

## Key Modules

### Authentication (`app/auth/`)

| File | Purpose |
|------|---------|
| `jwt.py` | JWT token creation/validation |
| `mfa.py` | TOTP-based 2FA |
| `permissions.py` | Role-based access control |
| `deps.py` | FastAPI dependency injection |

### Services (`app/services/`)

| Directory | Purpose |
|-----------|---------|
| `cdp/` | Customer Data Platform logic |
| `trust_engine/` | Signal health & trust gate |
| `integrations/` | External API clients |
| `notifications/` | Email, Slack, WhatsApp |

### Workers (`app/workers/`)

| File | Purpose |
|------|---------|
| `celery_app.py` | Celery configuration |
| `tasks.py` | Background task definitions |
| `campaign_builder_tasks.py` | Campaign publishing tasks |
| `crm_sync_tasks.py` | CRM synchronization |

---

## API Versioning

All API endpoints are versioned under `/api/v1/`:

```python
# Configuration in main.py
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Default prefix
api_v1_prefix: str = "/api/v1"
```

### URL Examples

| Endpoint | URL |
|----------|-----|
| Authentication | `/api/v1/auth/login` |
| Campaigns | `/api/v1/campaigns` |
| CDP Profiles | `/api/v1/cdp/profiles` |
| Trust Layer | `/api/v1/trust/health` |

---

## Configuration Management

Configuration is managed via Pydantic Settings (`app/core/config.py`):

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Stratum AI"
    app_env: Literal["development", "staging", "production"]
    debug: bool = True

    # Database
    database_url: str
    db_pool_size: int = 10

    # Security
    secret_key: str
    jwt_secret_key: str
```

**Access settings anywhere:**
```python
from app.core.config import settings

print(settings.app_env)
print(settings.is_production)
```

---

## Middleware Stack

### Order of Execution

Middleware is added in order, but executed in **reverse** (last added = first executed):

```python
# 1. CORS (first executed, last added)
app.add_middleware(CORSMiddleware, ...)

# 2. GZip compression
app.add_middleware(GZipMiddleware, ...)

# 3. Rate limiting
app.add_middleware(RateLimitMiddleware, ...)

# 4. Tenant extraction
app.add_middleware(TenantMiddleware)

# 5. Audit logging
app.add_middleware(AuditMiddleware)

# 6. Request timing (inline middleware)
@app.middleware("http")
async def add_timing_header(request, call_next):
    ...
```

### Custom Middleware

| Middleware | Purpose | Location |
|------------|---------|----------|
| AuditMiddleware | Logs POST/PUT/PATCH/DELETE | `middleware/audit.py` |
| TenantMiddleware | Extracts tenant from JWT | `middleware/tenant.py` |
| RateLimitMiddleware | Request throttling | `middleware/rate_limit.py` |

---

## Error Handling

### Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), ...)

    # Capture in Sentry
    if settings.sentry_dsn:
        sentry_sdk.capture_exception(exc)

    # Development: Return full traceback
    if settings.is_development:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    # Production: Generic error message
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected error occurred",
        }
    )
```

### Common HTTP Exceptions

```python
from fastapi import HTTPException, status

# 401 Unauthorized
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials"
)

# 403 Forbidden
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions"
)

# 404 Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Full health check (DB + Redis) |
| `GET /health/ready` | Kubernetes readiness probe |
| `GET /health/live` | Kubernetes liveness probe |

### Response Example

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "database": "healthy",
  "redis": "healthy"
}
```

---

## Real-Time Features

### WebSocket Endpoint

```
WS /ws?tenant_id=1&token=jwt_token
```

**Message Types:**
- `emq_update` - EMQ score changes
- `incident_opened/closed` - Incident notifications
- `autopilot_mode_change` - Autopilot status
- `action_status_update` - Action queue changes
- `platform_status` - Platform health

### Server-Sent Events

```
GET /api/v1/events/stream
```

Unidirectional server-to-client streaming for dashboard updates.

---

## Logging

### Structured Logging

All logs are JSON-formatted with consistent fields:

```python
logger.info(
    "request_completed",
    method=request.method,
    path=request.url.path,
    status_code=response.status_code,
    duration_ms=process_time,
)
```

**Output:**
```json
{
  "event": "request_completed",
  "method": "GET",
  "path": "/api/v1/campaigns",
  "status_code": 200,
  "duration_ms": 45.23,
  "request_id": "abc-123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Detailed debugging information |
| INFO | General operational events |
| WARNING | Non-critical issues |
| ERROR | Errors that need attention |
| CRITICAL | System failures |

---

## Dependencies

### Key Dependencies

```
# Framework
fastapi[all]>=0.109.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# Redis & Celery
redis>=5.0.0
celery>=5.3.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
pyotp>=2.9.0

# HTTP
httpx>=0.26.0
aiohttp>=3.9.0

# Observability
structlog>=24.1.0
sentry-sdk>=1.39.0
prometheus-fastapi-instrumentator>=6.1.0
```
