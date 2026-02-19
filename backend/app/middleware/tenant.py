# =============================================================================
# Stratum AI - Multi-Tenant Middleware
# =============================================================================
"""
Middleware that extracts and validates tenant context from requests.
Implements Row-Level Security at the application level.
"""

from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Endpoints that don't require tenant context
PUBLIC_ENDPOINTS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification",
    "/api/v1/auth/whatsapp/send-otp",
    "/api/v1/auth/whatsapp/verify-otp",
}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures tenant isolation for all requests.

    Extracts tenant_id from:
    1. JWT token claims
    2. X-Tenant-ID header (for API key auth)
    3. Subdomain (e.g., acme.stratum.ai)

    Sets request.state.tenant_id for downstream handlers.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract and validate tenant context."""

        # Always allow CORS preflight requests through (they carry no auth)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Try to extract tenant context
        tenant_id = await self._extract_tenant_id(request)
        user_id = await self._extract_user_id(request)
        role = await self._extract_role(request)

        if tenant_id is None:
            # For development, use a default tenant
            if settings.is_development:
                tenant_id = 1
                logger.debug("using_default_tenant", tenant_id=tenant_id)
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "error": "Tenant context required",
                        "message": "Please provide a valid authentication token",
                    },
                )

        # Set tenant, user, and role context on request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.role = role or "analyst"  # Default role if not in token

        # Bind to structured logging context
        import structlog

        structlog.contextvars.bind_contextvars(
            tenant_id=tenant_id, user_id=user_id, role=role
        )

        return await call_next(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the endpoint is public (no tenant context needed)."""
        if path in PUBLIC_ENDPOINTS:
            return True
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        # Allow webhook endpoints (they authenticate via signature)
        if path.startswith("/api/v1/webhooks/"):
            return True
        return False

    async def _extract_tenant_id(self, request: Request) -> Optional[int]:
        """
        Extract tenant_id from various sources.

        Priority:
        1. JWT token claims
        2. X-Tenant-ID header
        3. Subdomain
        """
        # Try JWT token first
        tenant_id = await self._extract_from_jwt(request)
        if tenant_id:
            return tenant_id

        # Try header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                return int(tenant_header)
            except ValueError:
                pass

        # Try subdomain
        return self._extract_from_subdomain(request)

    async def _extract_from_jwt(self, request: Request) -> Optional[int]:
        """Extract tenant_id from JWT token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload.get("tenant_id")
        except JWTError:
            return None

    async def _extract_user_id(self, request: Request) -> Optional[int]:
        """Extract user_id from JWT token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            return int(sub) if sub else None
        except (JWTError, ValueError):
            return None

    async def _extract_role(self, request: Request) -> Optional[str]:
        """Extract role from JWT token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload.get("role")
        except JWTError:
            return None

    def _extract_from_subdomain(self, request: Request) -> Optional[int]:
        """
        Extract tenant from subdomain.

        Example: acme.stratum.ai -> lookup tenant by slug 'acme'
        """
        host = request.headers.get("Host", "")
        parts = host.split(".")

        # Expecting format: {tenant}.stratum.ai or {tenant}.localhost
        if len(parts) >= 2:
            subdomain = parts[0]
            if subdomain not in {"www", "api", "app"}:
                # In production, this would lookup the tenant by slug
                # For now, we'll return None and rely on JWT
                logger.debug("subdomain_detected", subdomain=subdomain)

        return None


class TenantContext:
    """
    Context manager for tenant-scoped database operations.
    Ensures all queries are filtered by tenant_id.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def filter_query(self, query, model):
        """Add tenant filter to a SQLAlchemy query."""
        if hasattr(model, "tenant_id"):
            return query.filter(model.tenant_id == self.tenant_id)
        return query

    def set_tenant_on_model(self, instance):
        """Set tenant_id on a model instance before insert."""
        if hasattr(instance, "tenant_id"):
            instance.tenant_id = self.tenant_id
        return instance


def get_tenant_context(request: Request) -> TenantContext:
    """
    FastAPI dependency to get the current tenant context.

    Usage:
        @router.get("/items")
        async def get_items(tenant: TenantContext = Depends(get_tenant_context)):
            ...
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not found",
        )
    return TenantContext(tenant_id)
