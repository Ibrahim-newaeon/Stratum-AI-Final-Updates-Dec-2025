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
from fastapi.responses import JSONResponse, ORJSONResponse
from sse_starlette.sse import EventSourceResponse
import structlog

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.websocket import ws_manager
from app.db.session import async_engine, check_database_health
from app.middleware.audit import AuditMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1 import api_router

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

    # Initialize Sentry (production only)
    if settings.sentry_dsn and settings.is_production:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1,
        )
        logger.info("sentry_initialized")

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
    except Exception as e:
        logger.warning(
            "websocket_manager_start_failed",
            error=str(e),
            detail="App will run without real-time WebSocket support",
        )

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
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Middleware (order matters - executed in reverse order)
    # -------------------------------------------------------------------------

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID", "Accept", "Origin"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"],
    )

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        burst_size=settings.rate_limit_burst,
    )

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

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
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
        except Exception as e:
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
                from jose import jwt as jose_jwt
                payload = jose_jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
                user_id = payload.get("sub")
                if not tenant_id:
                    tenant_id = payload.get("tenant_id")
            except Exception:
                # Invalid token — reject the connection
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
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info",
    )
