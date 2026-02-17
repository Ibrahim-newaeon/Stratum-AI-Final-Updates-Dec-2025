# =============================================================================
# Stratum AI - Error Handler Middleware
# =============================================================================
"""
Last-resort middleware that catches any unhandled exception escaping the
middleware stack and returns a structured JSON error response.

IMPORTANT: CORS headers are added directly here because Starlette's
CORSMiddleware send_wrapper can be bypassed when exceptions propagate
through multiple stacked BaseHTTPMiddleware instances.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return a structured JSON 500 response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            origin = request.headers.get("origin", "")

            logger.error(
                "unhandled_middleware_exception",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                request_id=request_id,
            )

            # Include CORS headers directly so browsers can read the error.
            # CORSMiddleware's send_wrapper is bypassed when exceptions
            # propagate through stacked BaseHTTPMiddleware layers.
            cors_headers = {}
            if origin:
                cors_headers = {
                    "access-control-allow-origin": "*",
                    "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "access-control-allow-headers": "Content-Type, Authorization, X-Request-ID, X-Tenant-ID, Accept, Origin, Cache-Control",
                    "access-control-expose-headers": "X-Request-ID, X-Rate-Limit-Remaining",
                }

            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
                headers=cors_headers,
            )
