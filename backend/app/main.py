# =============================================================================
# Stratum AI - FastAPI Main Application
# =============================================================================
"""
Main FastAPI application entry point.
Configures routers, middleware, and application lifecycle events.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import sentry_sdk
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from sse_starlette.sse import EventSourceResponse
from starlette.responses import Response
import structlog

from app.core.config import settings
from app.core.exceptions import StratumError
from app.core.logging import get_logger, setup_logging
from app.core.websocket import ws_manager
from app.db.session import async_engine, check_database_health
from app.middleware.audit import AuditMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.api.v1 import api_router

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Number of active connections",
)
ACTIVE_WEBSOCKETS = Gauge(
    "active_websocket_connections",
    "Number of active WebSocket connections",
)

# Integration-specific metrics
CAPI_REQUESTS = Counter(
    "capi_requests_total",
    "Total CAPI requests to external platforms",
    ["platform", "status"],
)
CAPI_LATENCY = Histogram(
    "capi_request_duration_seconds",
    "CAPI request latency in seconds",
    ["platform"],
)
CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution time in seconds",
    ["task_name", "status"],
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifecycle manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
        debug=settings.debug,
    )

    # Initialize Sentry (production and staging)
    if settings.sentry_dsn and settings.app_env in ("production", "staging"):
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        def _before_send(event: dict, hint: dict) -> dict | None:
            """Strip PII from Sentry events before transmission."""
            if "request" in event and "data" in event["request"]:
                data = event["request"]["data"]
                if isinstance(data, dict):
                    for key in list(data.keys()):
                        if any(
                            s in key.lower()
                            for s in ("password", "token", "secret", "ssn", "credit_card")
                        ):
                            data[key] = "[REDACTED]"
            return event

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=settings.sentry_release,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            send_default_pii=False,
            before_send=_before_send,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                CeleryIntegration(monitor_beat_tasks=True),
                RedisIntegration(),
                LoggingIntegration(level=None, event_level="ERROR"),
            ],
        )
        logger.info(
            "sentry_initialized",
            environment=settings.app_env,
            release=settings.sentry_release,
        )

    # Verify database connection (with timeout to prevent blocking startup)
    try:
        db_health = await asyncio.wait_for(check_database_health(), timeout=10.0)
        if db_health["status"] != "healthy":
            logger.error("database_connection_failed", **db_health)
        else:
            logger.info("database_connected")
    except asyncio.TimeoutError:
        logger.error(
            "database_health_check_timeout",
            detail="Database health check timed out after 10s",
        )

    # Start WebSocket manager (graceful degradation if Redis unavailable)
    try:
        await ws_manager.start()
        logger.info("websocket_manager_started")
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.warning(
            "websocket_manager_start_failed",
            error=str(e),
            detail="App will run without real-time WebSocket support",
        )

    # Auto-train ML models if none exist (e.g., fresh Railway deploy)
    try:
        from pathlib import Path
        models_path = Path(settings.ml_models_path)
        if not models_path.exists() or not list(models_path.glob("*.pkl")):
            logger.info("ml_models_not_found", path=str(models_path), detail="Training from sample data")
            from app.ml.train import ModelTrainer
            from app.ml.data_loader import TrainingDataLoader
            df = TrainingDataLoader.generate_sample_data(num_campaigns=100, days_per_campaign=30)
            trainer = ModelTrainer(str(models_path))
            trainer.train_all(df, include_platform_models=False)
            logger.info("ml_models_auto_trained", models=list(str(p.name) for p in models_path.glob("*.pkl")))
    except (OSError, ValueError, ImportError, RuntimeError) as e:
        logger.warning("ml_auto_train_failed", error=str(e), detail="ML predictions will be unavailable")

    # Auto-seed superadmin if not exists or update password
    try:
        from scripts.seed_superadmin import create_superadmin
        await create_superadmin()
        logger.info("superadmin_seed_completed")
    except Exception as e:
        logger.warning("superadmin_seed_failed", error=str(e))

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Stop WebSocket manager
    await ws_manager.stop()
    logger.info("websocket_manager_stopped")

    await async_engine.dispose()
    logger.info("database_connections_closed")


# =============================================================================
# Application Factory
# =============================================================================
def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise Marketing Intelligence Platform - Unified analytics across Meta, Google, TikTok & Snapchat",
        version="1.0.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
        default_response_class=JSONResponse,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Middleware Stack
    # -------------------------------------------------------------------------
    # Starlette's add_middleware uses insert(0, ...) so the LAST call
    # becomes the OUTERMOST middleware.  Order below is innermost → outermost.
    # Execution: CORS → timing → Security → Audit → Tenant → RateLimit
    #            → Gzip → prometheus → ExceptionMiddleware → Router
    # -------------------------------------------------------------------------

    # Log allowed CORS origins at startup for easier debugging
    logger.info(
        "cors_origins_configured",
        origins=settings.cors_origins_list,
        frontend_url=settings.frontend_url,
    )

    # Prometheus request metrics (innermost — closest to the route handlers)
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Track request count and latency for Prometheus."""
        start_time = time.time()
        ACTIVE_CONNECTIONS.inc()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).inc()
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)
            return response
        finally:
            ACTIVE_CONNECTIONS.dec()

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        burst_size=settings.rate_limit_burst,
    )

    # CSRF protection for state-changing requests
    app.add_middleware(CSRFMiddleware)

    # Tenant extraction and validation
    app.add_middleware(TenantMiddleware)

    # Audit logging for state-changing requests
    app.add_middleware(AuditMiddleware)

    # Security headers (CSP, HSTS, X-Frame-Options, etc.)
    app.add_middleware(SecurityHeadersMiddleware)

    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        """Add request timing and request ID headers."""
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

        # Log request completion
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(process_time, 2),
        )

        return response

    # CORS — MUST be last add_middleware call so it is the outermost
    # middleware.  This ensures Access-Control-Allow-Origin is set on
    # ALL responses, including early 401s from TenantMiddleware.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID", "Accept", "Origin"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    @app.exception_handler(StratumError)
    async def stratum_error_handler(request: Request, exc: StratumError):
        """Handle all Stratum domain exceptions with structured response."""
        logger.warning(
            "domain_error",
            error_code=exc.error_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
            context=exc.context,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "context": exc.context if settings.debug else {},
                },
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors."""
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )

        if settings.is_development:
            import traceback

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "An unexpected error occurred",
                "message": "Please contact support if this persists",
            },
        )

    # -------------------------------------------------------------------------
    # Include Routers
    # -------------------------------------------------------------------------
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # -------------------------------------------------------------------------
    # Health Check Endpoints
    # -------------------------------------------------------------------------
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for load balancers and orchestrators.
        Returns service status and dependencies health.
        """
        import redis.asyncio as redis

        db_health = await check_database_health()

        # Check Redis
        try:
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            redis_status = "healthy"
            await redis_client.close()
        except (ConnectionError, TimeoutError, OSError) as e:
            redis_status = f"unhealthy: {str(e)}"

        overall_status = "healthy" if db_health["status"] == "healthy" and redis_status == "healthy" else "unhealthy"

        return {
            "status": overall_status,
            "version": "1.0.0",
            "environment": settings.app_env,
            "database": db_health["status"],
            "redis": redis_status,
        }

    @app.get("/health/ready", tags=["Health"])
    async def readiness_check():
        """Readiness probe - returns 200 when ready to serve traffic."""
        db_health = await check_database_health()
        if db_health["status"] != "healthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "reason": "database_unavailable"},
            )
        return {"status": "ready"}

    @app.get("/health/live", tags=["Health"])
    async def liveness_check():
        """Liveness probe - returns 200 if the service is alive."""
        return {"status": "alive"}

    # -------------------------------------------------------------------------
    # Prometheus Metrics Endpoint
    # -------------------------------------------------------------------------
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # -------------------------------------------------------------------------
    # Server-Sent Events for Real-Time Updates
    # -------------------------------------------------------------------------
    @app.get("/api/v1/events/stream", tags=["Real-Time"])
    async def event_stream(request: Request):
        """
        Server-Sent Events endpoint for real-time dashboard updates.
        Clients connect here to receive live notifications.

        NOTE: Auth is handled via the Authorization header (processed by
        TenantMiddleware). Do NOT add a query-string token parameter —
        tokens in URLs leak via server logs, Referer headers, and
        browser history.
        """
        import asyncio
        import redis.asyncio as redis

        async def event_generator():
            redis_client = redis.from_url(settings.redis_url)
            pubsub = redis_client.pubsub()

            # Get tenant from request context
            tenant_id = getattr(request.state, "tenant_id", None)
            channel = f"events:tenant:{tenant_id}" if tenant_id else "events:global"

            await pubsub.subscribe(channel)
            logger.info("sse_client_connected", channel=channel)

            try:
                while True:
                    if await request.is_disconnected():
                        break

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )

                    if message and message["type"] == "message":
                        yield {
                            "event": "update",
                            "data": message["data"].decode("utf-8"),
                        }

                    # Send heartbeat every 30 seconds
                    yield {"event": "heartbeat", "data": "ping"}
                    await asyncio.sleep(30)
            finally:
                await pubsub.unsubscribe(channel)
                await redis_client.close()
                logger.info("sse_client_disconnected", channel=channel)

        return EventSourceResponse(event_generator())

    # -------------------------------------------------------------------------
    # WebSocket Endpoint for Real-Time Updates
    # -------------------------------------------------------------------------
    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        tenant_id: Optional[int] = Query(default=None),
        token: Optional[str] = Query(default=None),
    ):
        """
        WebSocket endpoint for real-time dashboard updates.

        Query params:
        - tenant_id: Optional tenant ID for tenant-scoped messages
        - token: Optional auth token for authenticated connections

        Message types:
        - emq_update: EMQ score changes
        - incident_opened/closed: Incident notifications
        - autopilot_mode_change: Autopilot mode updates
        - action_status_update: Action queue status changes
        - action_recommendation: New action recommendations
        - platform_status: Platform health updates
        """
        # SECURITY: Require a valid token for WebSocket connections.
        # Anonymous connections could receive tenant-scoped data without auth.
        user_id = None
        if token:
            try:
                from jose import jwt as jose_jwt, JWTError
                payload = jose_jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
                user_id = payload.get("sub")
                if not tenant_id:
                    tenant_id = payload.get("tenant_id")
            except (JWTError, ValueError, TypeError, KeyError) as _jwt_err:
                # Invalid/expired token — reject the connection
                await websocket.close(code=4001, reason="Invalid or expired token")
                return
        else:
            # No token provided — reject unauthenticated connections
            await websocket.close(code=4001, reason="Authentication required")
            return

        # Connect the client
        client_id = await ws_manager.connect(
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        logger.info(
            "websocket_connection_established",
            client_id=client_id,
            tenant_id=tenant_id,
        )

        try:
            while True:
                # Receive and handle messages from client
                data = await websocket.receive_text()
                await ws_manager.handle_client_message(client_id, data)

        except WebSocketDisconnect:
            await ws_manager.disconnect(client_id)
            logger.info(
                "websocket_connection_closed",
                client_id=client_id,
                reason="client_disconnect",
            )

        except (ConnectionError, OSError, RuntimeError) as e:
            await ws_manager.disconnect(client_id)
            logger.error(
                "websocket_connection_error",
                client_id=client_id,
                error=str(e),
            )

    @app.get("/ws/stats", tags=["Real-Time"])
    async def websocket_stats():
        """Get WebSocket connection statistics."""
        return ws_manager.get_stats()

    return app


# Create the application instance
app = create_application()


# =============================================================================
# Development Server Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=settings.is_development,
        log_level="info",
    )
