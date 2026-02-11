# =============================================================================
# Stratum AI - Request Logging Middleware
# =============================================================================
"""
Middleware that assigns a unique request ID, measures request duration,
and emits structured log lines for every HTTP request.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

# Paths that generate high-frequency, low-value log noise
_SKIP_PATHS: set[str] = {
    "/health",
    "/health/ready",
    "/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add request ID, timing headers, and structured access logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Prefer a client-supplied request ID; fall back to a short UUID4
        request_id = request.headers.get(
            "X-Request-ID", uuid.uuid4().hex[:12]
        )
        request.state.request_id = request_id

        # Bind request_id into structlog context for downstream loggers
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Inject response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        # Log unless the path is noisy
        if request.url.path not in _SKIP_PATHS:
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        # Clear structlog context so it doesn't leak to the next request
        structlog.contextvars.unbind_contextvars("request_id")

        return response
