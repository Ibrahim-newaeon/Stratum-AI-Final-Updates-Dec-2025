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


class AppException(Exception):
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
