# =============================================================================
# Stratum AI - Rate Limiting Middleware
# =============================================================================
"""
Sliding-window rate limiting using Redis (distributed) with in-memory fallback.

Uses Redis INCR + EXPIRE for accurate, distributed counting across multiple
API workers. Falls back to a local in-memory token bucket when Redis is
unavailable so the middleware never blocks startup.
"""

import time
from typing import Callable, Optional

import redis.asyncio as aioredis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# In-Memory Fallback (used when Redis is unavailable)
# =============================================================================

class TokenBucket:
    """Token bucket implementation for local fallback rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def remaining(self) -> int:
        return int(self.tokens)


# =============================================================================
# Rate Limit Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting middleware.

    Strategy:
    - **Redis available** → sliding-window counter via INCR + EXPIRE.
      Shared across all workers / containers.
    - **Redis unavailable** → per-process token bucket (graceful degradation).

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
        self.window_seconds = 60  # 1-minute sliding window

        # Redis client (lazy-init on first request)
        self._redis: Optional[aioredis.Redis] = None
        self._redis_available: Optional[bool] = None  # None = not yet tested

        # Fallback: in-memory buckets
        self._buckets: dict[str, TokenBucket] = {}
        self._bucket_cleanup_interval = 300
        self._last_cleanup = time.monotonic()

    # --------------------------------------------------------------------- #
    # Redis helpers
    # --------------------------------------------------------------------- #
    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Return a working Redis connection, or None."""
        if self._redis_available is False:
            return None

        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1,
                )
                await self._redis.ping()
                self._redis_available = True
                logger.info("rate_limiter_redis_connected")
            except Exception as exc:
                logger.warning(
                    "rate_limiter_redis_unavailable",
                    error=str(exc),
                    detail="Falling back to in-memory rate limiter",
                )
                self._redis = None
                self._redis_available = False
                return None

        return self._redis

    async def _check_redis(self, client_id: str) -> tuple[bool, int]:
        """
        Sliding-window counter in Redis.

        Returns (allowed: bool, remaining: int).
        """
        redis_client = await self._get_redis()
        if redis_client is None:
            raise ConnectionError("Redis not available")

        key = f"rl:{client_id}"
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_seconds)
        results = await pipe.execute()

        current_count: int = results[0]
        remaining = max(0, self.requests_per_minute - current_count)
        allowed = current_count <= self.requests_per_minute

        return allowed, remaining

    # --------------------------------------------------------------------- #
    # In-memory fallback helpers
    # --------------------------------------------------------------------- #
    def _get_bucket(self, client_id: str) -> TokenBucket:
        if client_id not in self._buckets:
            self._buckets[client_id] = TokenBucket(
                rate=self.rate_per_second,
                capacity=self.burst_size,
            )
        return self._buckets[client_id]

    def _maybe_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup > self._bucket_cleanup_interval:
            self._last_cleanup = now
            to_remove = [
                cid for cid, b in self._buckets.items()
                if b.tokens >= self.burst_size
            ]
            for cid in to_remove:
                del self._buckets[cid]
            if to_remove:
                logger.debug("rate_limit_cleanup", removed_count=len(to_remove))

    # --------------------------------------------------------------------- #
    # Dispatch
    # --------------------------------------------------------------------- #
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to the request."""
        client_id = self._get_client_identifier(request)

        # Try Redis first, fall back to in-memory
        try:
            allowed, remaining = await self._check_redis(client_id)
        except Exception:
            # Redis unavailable — use local token bucket
            bucket = self._get_bucket(client_id)
            allowed = bucket.consume()
            remaining = bucket.remaining
            self._maybe_cleanup()

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_id=client_id,
                path=request.url.path,
            )
            return self._rate_limit_response(remaining)

        response = await call_next(request)

        # Add standard rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.window_seconds
        )

        return response

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _get_client_identifier(self, request: Request) -> str:
        """Uses user_id if authenticated, otherwise IP address."""
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
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

    def _rate_limit_response(self, remaining: int) -> JSONResponse:
        """Create rate limit exceeded response."""
        retry_after = self.window_seconds

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
