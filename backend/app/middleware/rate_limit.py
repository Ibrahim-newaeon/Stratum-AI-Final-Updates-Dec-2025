# =============================================================================
# Stratum AI - Rate Limiting Middleware
# =============================================================================
"""
Token bucket rate limiting implementation.
Prevents API abuse and ensures fair resource usage.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Allows burst traffic while enforcing average rate limits.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens per second to add
            capacity: Maximum bucket size (burst limit)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)  # type: ignore[assignment]

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def remaining(self) -> int:
        """Get remaining tokens (rounded down)."""
        return int(self.tokens)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Features:
    - Per-IP rate limiting
    - Per-user rate limiting (when authenticated)
    - Configurable limits and burst sizes
    - Rate limit headers in responses
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 100,
        burst_size: int = 20,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.rate_per_second = requests_per_minute / 60.0
        self.buckets: dict[str, TokenBucket] = {}
        self.bucket_cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to the request."""

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Get or create bucket for this client
        bucket = self._get_bucket(client_id)

        # Try to consume a token
        if not bucket.consume():
            logger.warning(
                "rate_limit_exceeded",
                client_id=client_id,
                path=request.url.path,
            )
            return self._rate_limit_response(bucket)

        # Process the request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(bucket.remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + int((self.burst_size - bucket.remaining) / self.rate_per_second)
        )

        # Periodic cleanup of old buckets
        self._maybe_cleanup()

        return response

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the client.

        Uses user_id if authenticated, otherwise IP address.
        """
        # Try user_id from JWT (set by tenant middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create a token bucket for the client."""
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                rate=self.rate_per_second,
                capacity=self.burst_size,
            )
        return self.buckets[client_id]

    def _rate_limit_response(self, bucket: TokenBucket) -> JSONResponse:
        """Create rate limit exceeded response."""
        retry_after = int((1 - bucket.tokens) / self.rate_per_second) + 1

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please retry after {retry_after} seconds.",
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )

    def _maybe_cleanup(self) -> None:
        """Periodically clean up old buckets to prevent memory leaks."""
        now = time.monotonic()
        if now - self.last_cleanup > self.bucket_cleanup_interval:
            self.last_cleanup = now

            # Remove buckets that have been at full capacity for a while
            # (indicates inactive clients)
            to_remove = []
            for client_id, bucket in self.buckets.items():
                if bucket.tokens >= self.burst_size:
                    to_remove.append(client_id)

            for client_id in to_remove:
                del self.buckets[client_id]

            if to_remove:
                logger.debug("rate_limit_cleanup", removed_count=len(to_remove))
