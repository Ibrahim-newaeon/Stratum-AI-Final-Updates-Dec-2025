# =============================================================================
# Stratum AI - FastAPI Main Application
# =============================================================================
"""
Main FastAPI application entry point.
Configures routers, middleware, and application lifecycle events.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

import sentry_sdk
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from sse_starlette.sse import EventSourceResponse

from app.api.v1 import api_router
from app.api.v1.endpoints.memory_debug import init_debug_endpoints, router as memory_debug_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.metrics import setup_metrics
from app.core.websocket import ws_manager
from app.db.session import async_engine, check_database_health
from app.middleware.audit import AuditMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
from app.monitoring.memory_audit import MemoryAuditor
from app.monitoring.middleware import MemoryProfilingMiddleware

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

    # Initialize Sentry for error tracking
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release="stratum-backend@1.0.0",
            # Performance monitoring
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            # Profile sampling for performance insights
            profiles_sample_rate=0.1 if settings.is_production else 0.0,
            # Capture HTTP headers and request body
            send_default_pii=False,
            # Additional integrations
            integrations=[],
            # Filter out health check endpoints from traces
            traces_sampler=lambda ctx: 0.0  # type: ignore[arg-type, return-value]
            if ctx.get("wsgi_environ", {}).get("PATH_INFO", "").startswith("/health")
            else None,
        )
        logger.info("sentry_initialized", environment=settings.app_env)

    # Verify database connection
    db_health = await check_database_health()
    if db_health["status"] != "healthy":
        logger.error("database_connection_failed", **db_health)
    else:
        logger.info("database_connected")

    # Start WebSocket manager (graceful - don't crash if Redis unavailable)
    try:
        await ws_manager.start()
        logger.info("websocket_manager_started")
    except Exception as e:
        logger.error("websocket_manager_failed", error=str(e))
        logger.warning("websocket_features_disabled_redis_unavailable")

    # Note: Prometheus metrics are initialized in create_application()
    logger.info("prometheus_metrics_ready", endpoint="/metrics")

    # Start Memory Auditor (non-production or when explicitly enabled)
    if not settings.is_production or settings.debug:
        memory_auditor = app.state.memory_auditor
        memory_auditor.start_tracking()
        memory_auditor.take_snapshot(label="app_startup")
        logger.info("memory_auditor_started", pid=memory_auditor.get_process_info().pid)

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Stop memory tracking
    if hasattr(app.state, "memory_auditor") and app.state.memory_auditor.is_tracking:
        app.state.memory_auditor.take_snapshot(label="app_shutdown")
        app.state.memory_auditor.stop_tracking()
        logger.info("memory_auditor_stopped")

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
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Prometheus Metrics Instrumentation
    # -------------------------------------------------------------------------
    # Setup Prometheus metrics before middleware so we capture all requests
    # This instruments the app and exposes /metrics endpoint
    instrumentator = setup_metrics(app)
    logger.info("prometheus_instrumentator_initialized")

    # -------------------------------------------------------------------------
    # Middleware (Starlette add_middleware PREPENDS — last added = outermost)
    # Execution order: CORS → ErrorHandler → GZip → RequestLogging →
    #                  RateLimit → Tenant → Audit → SecurityHeaders → Router
    # -------------------------------------------------------------------------

    # Innermost middleware (added first, closest to the router)
    app.add_middleware(SecurityHeadersMiddleware)

    # Audit logging for state-changing requests
    app.add_middleware(AuditMiddleware)

    # Tenant extraction and validation
    app.add_middleware(TenantMiddleware)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        burst_size=settings.rate_limit_burst,
    )

    # Request logging middleware (request ID, timing, structured access logs)
    app.add_middleware(RequestLoggingMiddleware)

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Error handler - catches exceptions from inner middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # CORS - MUST be outermost (added LAST) so it handles OPTIONS preflight
    # before any other middleware can reject the request
    cors_origins = settings.cors_origins_list
    logger.info("cors_origins_configured", origins=cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Tenant-ID",
            "Accept",
            "Origin",
            "Cache-Control",
        ],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    def _cors_headers(request: Request) -> dict:
        """Build CORS headers for error responses so browsers can read them."""
        origin = request.headers.get("origin", "")
        if origin:
            return {
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "access-control-allow-headers": "Content-Type, Authorization, X-Request-ID, X-Tenant-ID",
            }
        return {}

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle structured application exceptions."""
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "app_exception",
            error_code=exc.error_code,
            status_code=exc.status_code,
            message=exc.message,
            path=request.url.path,
            request_id=request_id,
        )
        payload = exc.to_dict()
        if request_id:
            payload["request_id"] = request_id
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers=_cors_headers(request),
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

        # Capture exception in Sentry
        if settings.sentry_dsn:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("path", request.url.path)
                scope.set_tag("method", request.method)
                scope.set_context(
                    "request",
                    {
                        "url": str(request.url),
                        "method": request.method,
                        "headers": dict(request.headers),
                    },
                )
                sentry_sdk.capture_exception(exc)

        headers = _cors_headers(request)

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
                headers=headers,
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "An unexpected error occurred",
                "message": "Please contact support if this persists",
            },
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # Memory Profiling (non-production or debug mode)
    # -------------------------------------------------------------------------
    if not settings.is_production or settings.debug:
        auditor = MemoryAuditor()
        app.state.memory_auditor = auditor

        # NOTE: MemoryProfilingMiddleware is NOT added via add_middleware here
        # because that would place it OUTSIDE CORSMiddleware (breaking CORS).
        # Instead we only create a standalone tracker for debug endpoints.
        memory_profiling_tracker = MemoryProfilingMiddleware(app, enabled=True)
        app.state.memory_profiling_tracker = memory_profiling_tracker

        # Initialize debug endpoints with auditor + middleware references
        init_debug_endpoints(
            auditor=auditor,
            middleware=memory_profiling_tracker,
        )

        # Mount debug routes (outside /api/v1 prefix for easy access)
        app.include_router(memory_debug_router)
        logger.info("memory_profiling_enabled", endpoints="/debug/memory/*")

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
        except Exception as e:
            redis_status = f"unhealthy: {e!s}"

        overall_status = (
            "healthy"
            if db_health["status"] == "healthy" and redis_status == "healthy"
            else "unhealthy"
        )

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
    # Server-Sent Events for Real-Time Updates
    # -------------------------------------------------------------------------
    @app.get("/api/v1/events/stream", tags=["Real-Time"])
    async def event_stream(request: Request):
        """
        Server-Sent Events endpoint for real-time dashboard updates.
        Clients connect here to receive live notifications.
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

                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

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
        # Validate token if provided (simplified - in production, verify JWT)
        user_id = None
        if token:
            try:
                from app.auth.jwt import decode_token

                payload = decode_token(token)
                user_id = payload.get("sub")
                if not tenant_id:
                    tenant_id = payload.get("tenant_id")
            except Exception:
                # Invalid token - allow anonymous connection
                pass

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

        except Exception as e:
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
        host="0.0.0.0",  # noqa: S104 - Intentional for Docker/dev access
        port=8000,
        reload=settings.is_development,
        log_level="info",
    )
