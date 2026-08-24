# =============================================================================
# Stratum AI - Multi-Tenant Middleware
# =============================================================================
"""
Middleware that extracts and validates tenant context from requests.
Implements Row-Level Security at the application level.
"""

import re
from typing import Callable, Optional

import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jwt.exceptions import PyJWTError as JWTError
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
    # Prometheus scrapes without auth (see infrastructure/prometheus). Keep
    # /metrics blocked from the public internet at the ingress/ALB layer.
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    # MFA second step: the client only holds the challenge mfa_token from the
    # login response body (no tenant-scoped bearer yet) — the endpoint
    # self-authenticates by decoding that token.
    "/api/v1/auth/login/mfa",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/accept-invite",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification",
    "/api/v1/auth/email/send-otp",
    "/api/v1/auth/email/verify-otp",
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

        # Decode JWT once and cache the payload on request.state
        jwt_payload = self._decode_jwt_once(request)

        # SECURITY (AUTH-001): a decoded token is not enough — it must be an
        # *access* token and must not have been revoked (logout / password
        # reset / forced sign-out add the token's jti to the Redis blacklist).
        # Without this, a revoked or refresh token sails through until it
        # naturally expires. Reject before any tenant context is established.
        if jwt_payload is not None:
            if jwt_payload.get("type") != "access":
                return self._reject(
                    "Invalid token type",
                    "This endpoint requires an access token",
                )
            try:
                revoked = await self._is_revoked(jwt_payload, request)
            except (ConnectionError, TimeoutError, OSError) as exc:
                # Fail closed, matching app.auth.deps.get_current_user. A 503
                # says "try again", where allowing the request would silently
                # stop enforcing revocation.
                logger.error(
                    "token_blacklist_check_unavailable",
                    error=str(exc),
                    detail="Rejecting request; revocation cannot be verified",
                )
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "success": False,
                        "error": "Authentication service temporarily unavailable",
                        "message": "Please retry in a moment.",
                    },
                )

            if revoked:
                return self._reject(
                    "Token revoked",
                    "Your session has ended. Please sign in again.",
                )

        request.state._jwt_payload = jwt_payload

        # Try to extract tenant context
        tenant_id = await self._extract_tenant_id(request)
        user_id = jwt_payload.get("sub") if jwt_payload else None
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                user_id = None
        role = jwt_payload.get("role") if jwt_payload else None
        cms_role = jwt_payload.get("cms_role") if jwt_payload else None

        if tenant_id is None:
            # Superadmins operate across all tenants and may not carry a
            # tenant_id in their JWT.  Let them through so platform-wide
            # endpoints (e.g. /superadmin/*, /emq/benchmarks) can be reached.
            if role == "superadmin":
                logger.debug("superadmin_bypass_tenant_check", user_id=user_id)
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
        request.state.is_superadmin = role == "superadmin"
        request.state.cms_role = cms_role  # CMS role (None if not a CMS user)

        # Bind to structured logging context
        import structlog

        structlog.contextvars.bind_contextvars(
            tenant_id=tenant_id, user_id=user_id, role=role
        )

        return await call_next(request)

    def _decode_jwt_once(self, request: Request) -> Optional[dict]:
        """Decode the JWT token once and return the payload dict, or None."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            return jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            return None

    @staticmethod
    def _reject(error: str, message: str) -> JSONResponse:
        """Build a 401 for a token that decoded but is not usable."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "error": error, "message": message},
        )

    async def _is_revoked(self, payload: dict, request: Request) -> bool:
        """Return True if this token has been blacklisted (AUTH-001).

        Fails CLOSED on Redis unavailability by letting the error propagate;
        the caller turns it into a 503.

        This used to fail open, reasoning that a blacklist outage must not
        become a total auth outage. That reasoning did not hold, because
        ``app.auth.deps.get_current_user`` already fails closed with a 503 on
        the same error. Endpoints are split between the two: roughly 345 routes
        take that dependency, while roughly 422 authenticate from
        ``request.state`` alone — including the autopilot endpoints that
        approve and execute budget changes, since there is no router-level auth
        dependency.

        So failing open bought no availability the system actually got: a Redis
        outage already 503s half the API. What it bought was a window in which
        a revoked access token kept working on the endpoints where that matters
        most, for up to ``access_token_expire_minutes`` (30). Offboard a user,
        force a sign-out, have Redis blip, and they could still approve
        autopilot actions.

        Both enforcement points now agree: no revocation check, no request.
        """
        from app.core.security import is_token_blacklisted

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ", 1)[1] if " " in auth_header else ""
        return await is_token_blacklisted(payload, token)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the endpoint is public (no tenant context needed)."""
        if path in PUBLIC_ENDPOINTS:
            return True
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        # OAuth provider callbacks arrive as browser redirects from the ad
        # platform with no JWT/X-Tenant-ID header; tenant context comes from
        # the Redis-stored state token the endpoint validates (CSRF check).
        if re.fullmatch(r"/api/v1/oauth/[^/]+/callback", path):
            return True
        # Allow webhook endpoints (they authenticate via signature/verify-token, not JWT)
        # Platform webhooks live under /api/v1/<platform>/webhooks/, generic ones under
        # /api/v1/webhooks/. Each handler is responsible for verifying the request
        # (HMAC signature for Meta/Stripe/SendGrid, hub.verify_token for WhatsApp).
        if path.startswith("/api/v1/webhooks/"):
            return True
        if path.startswith("/api/v1/whatsapp/webhooks/"):
            return True
        if path.startswith("/api/v1/stripe/webhooks/"):
            return True
        # HubSpot calls these directly: the OAuth callback arrives as a browser
        # redirect carrying no JWT, and webhooks are POSTed by HubSpot's
        # servers. Without this both 401'd here, so the integration could never
        # complete a connection or receive an event.
        #
        # Exact paths, not a /api/v1/integrations/ prefix or a provider
        # wildcard. The rest of that router is superadmin-gated management, and
        # a wildcard would silently exempt the next provider's callback before
        # anyone had checked that it validates its state server-side — an
        # exempt callback authenticates itself, so that is a decision to make
        # per route rather than a pattern to inherit.
        if path in (
            "/api/v1/integrations/hubspot/callback",
            "/api/v1/integrations/hubspot/webhook",
        ):
            return True
        # Programmatic API — authenticates via the X-API-Key header, not a JWT.
        # The api-key dependency (get_api_key_principal) validates the key and
        # sets request.state.tenant_id from the key's tenant, so JWT-based tenant
        # extraction here would only ever 401 a legitimate key before auth runs.
        # Every /programmatic/* route MUST depend on APIKeyPrincipalDep /
        # require_api_key_scope so tenant context is always established downstream.
        if path.startswith("/api/v1/programmatic/"):
            return True
        # Drip open-pixel, click and unsubscribe. These URLs are inside emails
        # already sitting in recipients' inboxes: the request is a mail client
        # fetching an image or a person clicking a link, so there is no JWT and
        # never will be. Left un-exempt, every unsubscribe click 401s — refusing
        # an opt-out is the one failure this surface cannot have.
        #
        # Tenant context comes from the request itself, not from the caller:
        # the unsubscribe token is HMAC-signed and carries the tenant, and the
        # tracking routes address an execution record by its own id. Enumerated
        # exactly rather than by prefix, so the rest of /drip-campaigns/ (the
        # tenant-scoped product surface) stays authenticated.
        if path in ("/api/v1/drip-campaigns/unsubscribe",):
            return True
        if re.fullmatch(r"/api/v1/drip-campaigns/track/(open|click)/[^/]+", path):
            return True
        # CMS public endpoints — content is global, not tenant-scoped
        if path.startswith("/api/v1/cms/") and "/admin/" not in path:
            return True
        # Landing CMS — public, read-only published marketing content
        if path.startswith("/api/v1/landing-cms"):
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

        # Try X-Tenant-ID header ONLY when a VALID JWT token is present.
        # SECURITY: Never trust X-Tenant-ID without a successfully decoded JWT,
        # as an unauthenticated client could spoof any tenant.
        tenant_header = request.headers.get("X-Tenant-ID")
        jwt_payload = getattr(request.state, "_jwt_payload", None)
        if tenant_header and jwt_payload is not None:
            try:
                header_tenant_id = int(tenant_header)
                jwt_tenant_id = jwt_payload.get("tenant_id")
                # Allow if the header tenant matches the JWT tenant claim,
                # or if the user is a superadmin (cross-tenant access).
                if jwt_tenant_id and header_tenant_id == jwt_tenant_id:
                    return header_tenant_id
                if jwt_payload.get("role") == "superadmin":
                    return header_tenant_id
            except ValueError:
                pass

        # Try subdomain
        return self._extract_from_subdomain(request)

    async def _extract_from_jwt(self, request: Request) -> Optional[int]:
        """Extract tenant_id from the cached JWT payload."""
        payload = getattr(request.state, "_jwt_payload", None)
        if payload is None:
            return None
        return payload.get("tenant_id")

    # _extract_user_id, _extract_role, _extract_cms_role are now handled
    # inline in dispatch() using the cached JWT payload from _decode_jwt_once().

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
