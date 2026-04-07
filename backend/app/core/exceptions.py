# =============================================================================
# Stratum AI - Application Exception Hierarchy
# =============================================================================
"""
Structured exception classes for consistent error handling across the API.

All exceptions inherit from AppException, which provides:
- HTTP status code mapping
- Machine-readable error codes
- Optional detail payloads for debugging

Usage:
    from app.core.exceptions import NotFoundError, ValidationError

    raise NotFoundError("Campaign not found", details={"campaign_id": 123})
    raise ValidationError("Invalid date range", error_code="INVALID_DATE_RANGE")
"""

from typing import Any, Optional


class AppException(Exception):  # noqa: N818 — intentional base class name
    """Base exception for all Stratum AI application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to a JSON-compatible dict."""
        payload: dict[str, Any] = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class BadRequestError(AppException):
    """400 - The request is malformed or contains invalid parameters."""

    status_code = 400
    error_code = "BAD_REQUEST"


class UnauthorizedError(AppException):
    """401 - Authentication is required or has failed."""

    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    """403 - The caller does not have permission for this action."""

    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundError(AppException):
    """404 - The requested resource does not exist."""

    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppException):
    """409 - The request conflicts with current resource state."""

    status_code = 409
    error_code = "CONFLICT"


class ValidationError(AppException):
    """422 - The request body failed validation."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class RateLimitError(AppException):
    """429 - The caller has exceeded the rate limit."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class ServiceUnavailableError(AppException):
    """503 - A downstream service is unavailable."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"


class TierLimitError(AppException):
    """403 - The requested feature is not available on the current subscription tier."""

    status_code = 403
    error_code = "TIER_LIMIT_EXCEEDED"

    def __init__(
        self,
        message: str = "This feature requires a higher subscription tier",
        required_tier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if required_tier:
            details["required_tier"] = required_tier
        super().__init__(message=message, details=details, **kwargs)


# =============================================================================
# Stratum AI — Domain Exception Classes
# =============================================================================
"""
Standardized exceptions with error codes for API consumers.
All exceptions inherit from StratumError and include an error_code
that maps to a documented error in the API reference.
"""


class StratumError(Exception):
    """Base exception for all Stratum AI domain errors."""

    error_code: str = "STRATUM_ERROR"
    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(
        self,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        self.context = context or {}
        super().__init__(self.detail)


# === Authentication & Authorization ===

class AuthenticationError(StratumError):
    error_code = "AUTH_FAILED"
    status_code = 401
    detail = "Authentication failed"


class TokenExpiredError(AuthenticationError):
    error_code = "TOKEN_EXPIRED"
    detail = "Access token has expired"


class InvalidTokenError(AuthenticationError):
    error_code = "TOKEN_INVALID"
    detail = "Invalid or malformed token"


class AuthorizationError(StratumError):
    error_code = "FORBIDDEN"
    status_code = 403
    detail = "You do not have permission to perform this action"


class CMSPermissionError(AuthorizationError):
    error_code = "CMS_PERMISSION_DENIED"
    detail = "CMS permission denied"


# === Validation ===

class StratumValidationError(StratumError):
    error_code = "VALIDATION_ERROR"
    status_code = 422
    detail = "Request validation failed"


class ConfigurationError(StratumError):
    error_code = "CONFIG_ERROR"
    status_code = 500
    detail = "Server configuration error"


# === Resources ===

class ResourceNotFoundError(StratumError):
    error_code = "NOT_FOUND"
    status_code = 404
    detail = "Resource not found"


class ResourceConflictError(StratumError):
    error_code = "CONFLICT"
    status_code = 409
    detail = "Resource conflict"


class ResourceExhaustedError(StratumError):
    error_code = "RATE_LIMITED"
    status_code = 429
    detail = "Rate limit exceeded"


# === Trust Engine ===

class TrustGateError(StratumError):
    error_code = "TRUST_GATE_BLOCKED"
    status_code = 403
    detail = "Action blocked by trust gate — signal health below threshold"


class SignalDegradedError(TrustGateError):
    error_code = "SIGNAL_DEGRADED"
    detail = "Signal health is degraded — automation held"


class SignalUnhealthyError(TrustGateError):
    error_code = "SIGNAL_UNHEALTHY"
    detail = "Signal health is unhealthy — manual intervention required"


# === Platform Integration ===

class PlatformError(StratumError):
    error_code = "PLATFORM_ERROR"
    status_code = 502
    detail = "External platform API error"


class PlatformAuthError(PlatformError):
    error_code = "PLATFORM_AUTH_FAILED"
    detail = "Platform authentication failed — check credentials"


class PlatformRateLimitError(PlatformError):
    error_code = "PLATFORM_RATE_LIMITED"
    status_code = 429
    detail = "Platform API rate limit exceeded"


class PlatformTimeoutError(PlatformError):
    error_code = "PLATFORM_TIMEOUT"
    status_code = 504
    detail = "Platform API request timed out"


# === Data ===

class DataIntegrityError(StratumError):
    error_code = "DATA_INTEGRITY"
    status_code = 500
    detail = "Data integrity violation"


class TenantIsolationError(StratumError):
    error_code = "TENANT_ISOLATION"
    status_code = 403
    detail = "Cross-tenant data access denied"


# === Error Code Registry ===

ERROR_CODES: dict[str, dict[str, Any]] = {
    cls.error_code: {
        "status_code": cls.status_code,
        "detail": cls.detail,
        "exception_class": cls.__name__,
    }
    for cls in [
        StratumError, AuthenticationError, TokenExpiredError, InvalidTokenError,
        AuthorizationError, CMSPermissionError, StratumValidationError, ConfigurationError,
        ResourceNotFoundError, ResourceConflictError, ResourceExhaustedError,
        TrustGateError, SignalDegradedError, SignalUnhealthyError,
        PlatformError, PlatformAuthError, PlatformRateLimitError, PlatformTimeoutError,
        DataIntegrityError, TenantIsolationError,
    ]
}
