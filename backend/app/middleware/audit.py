# =============================================================================
# Stratum AI - Audit Logging Middleware
# =============================================================================
"""
Middleware that records all state-changing API requests to the audit log.
Implements Module F: Security & Governance requirements.
"""

import json
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.models import AuditAction

logger = get_logger(__name__)

# HTTP methods that change state
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints to exclude from audit logging
EXCLUDED_ENDPOINTS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures state-changing requests for audit logging.

    Records:
    - User ID (from JWT)
    - Tenant ID
    - Resource type and ID
    - Action type (CREATE, UPDATE, DELETE)
    - Old and new values (where available)
    - Request metadata (IP, User-Agent, etc.)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit trail for state changes."""

        # Skip non-state-changing methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)

        # Skip excluded endpoints
        if request.url.path in EXCLUDED_ENDPOINTS:
            return await call_next(request)

        # Capture request body for audit
        request_body = None
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    request_body = json.loads(body_bytes.decode("utf-8"))
                # Reconstruct the request body for downstream handlers
                request._body = body_bytes
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_body = None

        # Process the request
        response = await call_next(request)

        # Only log successful state changes
        if response.status_code in range(200, 300):
            try:
                await self._log_audit_event(request, request_body, response)
            except Exception as e:
                # Audit logging must never break the request
                logger.error("audit_dispatch_failed", error=str(e))

        return response

    async def _log_audit_event(
        self, request: Request, request_body: Optional[dict], response: Response
    ) -> None:
        """Create audit log entry for the request."""
        try:
            # Extract user and tenant from request state (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            tenant_id = getattr(request.state, "tenant_id", None)

            # Parse resource type and ID from path
            resource_type, resource_id = self._parse_resource_from_path(request.url.path)

            # Determine action type
            action = self._determine_action(request.method)

            # Get request metadata
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "")[:500]
            request_id = request.headers.get("X-Request-ID", "")

            # Create audit log entry
            audit_entry = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": action.value,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "new_value": self._sanitize_for_audit(request_body),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_id": request_id,
                "endpoint": request.url.path,
                "http_method": request.method,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Log the audit event (in production, this would write to the database)
            logger.info("audit_event", **audit_entry)

            # Queue for async database write
            await self._queue_audit_write(audit_entry)

        except Exception as e:
            logger.error("audit_logging_failed", error=str(e))

    def _parse_resource_from_path(self, path: str) -> tuple[str, Optional[str]]:
        """
        Parse resource type and ID from URL path.

        Examples:
            /api/v1/campaigns/123 -> ('campaigns', '123')
            /api/v1/campaigns -> ('campaigns', None)
            /api/v1/users/456/settings -> ('users', '456')
        """
        parts = [p for p in path.split("/") if p and p != "api" and p != "v1"]

        if not parts:
            return ("unknown", None)

        resource_type = parts[0]
        resource_id = parts[1] if len(parts) > 1 and parts[1].isdigit() else None

        return (resource_type, resource_id)

    def _determine_action(self, method: str) -> AuditAction:
        """Map HTTP method to audit action type."""
        method_to_action = {
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE,
        }
        return method_to_action.get(method, AuditAction.UPDATE)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address, handling proxies."""
        # Check for forwarded headers (behind load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _sanitize_for_audit(self, data: Optional[dict]) -> Optional[dict]:
        """
        Remove sensitive fields from audit log data.
        PII and credentials should not be stored in plain text.
        """
        if data is None:
            return None

        if not data:
            return {}

        # Fields to redact
        sensitive_fields = {
            "password",
            "password_hash",
            "secret",
            "token",
            "access_token",
            "refresh_token",
            "api_key",
            "credit_card",
            "ssn",
            "social_security",
        }

        sanitized = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_for_audit(value)
            else:
                sanitized[key] = value

        return sanitized

    async def _queue_audit_write(self, audit_entry: dict) -> None:
        """
        Queue audit entry for async database write.
        Uses Redis to decouple audit logging from request processing.
        """
        try:
            import redis.asyncio as redis
            from app.core.config import settings

            client = redis.from_url(settings.redis_url)
            try:
                await client.lpush("audit_log_queue", json.dumps(audit_entry))
            finally:
                await client.close()
        except Exception as e:
            # Audit logging should never break the request
            logger.warning("audit_queue_failed", error=str(e))
