# =============================================================================
# Stratum AI - Circuit Breaker for External API Calls
# =============================================================================
"""
Simple circuit breaker to prevent cascading failures when external APIs are down.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit tripped, requests fail fast without calling the API
- HALF_OPEN: After cooldown, allow one test request to check if API recovered

Usage:
    breaker = CircuitBreaker("meta_api", failure_threshold=5, cooldown_seconds=120)

    if not breaker.allow_request():
        raise ServiceUnavailableError("Meta API circuit breaker is open")

    try:
        result = await call_meta_api(...)
        breaker.record_success()
    except Exception:
        breaker.record_failure()
        raise
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """In-memory circuit breaker for external service calls."""

    name: str
    failure_threshold: int = 5
    cooldown_seconds: int = 120

    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return True if the request should proceed."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True  # Allow one test request
        return False  # OPEN — fail fast

    def record_success(self) -> None:
        """Record a successful call — reset the breaker."""
        if self._state != CircuitState.CLOSED:
            logger.info("circuit_breaker_closed", name=self.name)
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call — trip the breaker if threshold exceeded."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.warning(
                    "circuit_breaker_opened",
                    name=self.name,
                    failures=self._failure_count,
                    cooldown=self.cooldown_seconds,
                )
            self._state = CircuitState.OPEN


# =============================================================================
# Global breaker registry — one breaker per external service
# =============================================================================
_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    cooldown_seconds: int = 120,
) -> CircuitBreaker:
    """Get or create a circuit breaker for the named service."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
        )
    return _breakers[name]
