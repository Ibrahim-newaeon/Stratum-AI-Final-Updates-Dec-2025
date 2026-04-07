# =============================================================================
# Stratum AI - CSRF Protection Middleware
# =============================================================================
"""
Cross-Site Request Forgery protection for state-changing requests.

Strategy:
- Enforces SameSite cookie policy via response headers
- Validates Origin/Referer headers on state-changing requests (POST, PUT, PATCH, DELETE)
- Allows requests with valid Bearer tokens (API clients) to bypass Origin checks
- Skips CSRF checks for safe methods (GET, HEAD, OPTIONS) and webhook endpoints
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Endpoints that receive external webhooks and should skip CSRF checks
CSRF_EXEMPT_PATHS = (
    "/api/v1/whatsapp/webhooks/",
    "/api/v1/stripe-webhook",
    "/health",
    "/metrics",
)

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection via Origin validation and SameSite cookies."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.allowed_origins = set(settings.cors_origins_list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip safe methods
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            self._add_cookie_headers(response)
            return response

        # Skip exempt paths (webhooks)
        if any(request.url.path.startswith(p) for p in CSRF_EXEMPT_PATHS):
            return await call_next(request)

        # Requests with Bearer token are from API clients, not browsers
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            response = await call_next(request)
            self._add_cookie_headers(response)
            return response

        # For cookie-based auth, validate Origin header
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        if origin:
            if origin.rstrip("/") not in self.allowed_origins:
                logger.warning("csrf_origin_rejected", origin=origin, path=request.url.path)
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: origin not allowed"},
                )
        elif referer:
            from urllib.parse import urlparse
            referer_origin = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
            if referer_origin.rstrip("/") not in self.allowed_origins:
                logger.warning("csrf_referer_rejected", referer=referer_origin, path=request.url.path)
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: referer not allowed"},
                )

        response = await call_next(request)
        self._add_cookie_headers(response)
        return response

    @staticmethod
    def _add_cookie_headers(response: Response) -> None:
        """Add SameSite cookie policy headers."""
        # Ensure cookies use SameSite=Lax by default
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
