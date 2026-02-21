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

            # Do NOT add manual CORS headers here.  FastAPI's CORSMiddleware
            # is responsible for setting the correct Access-Control-Allow-Origin
            # (matching the request Origin against the configured allow list).
            # Hard-coding "*" would bypass the allow-list and expose error
            # details to any origin.
            cors_headers: dict[str, str] = {}

            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
                headers=cors_headers,
            )
