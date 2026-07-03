# =============================================================================
# Stratum AI - Core Logging Unit Tests
# =============================================================================
"""Unit tests for ``app.core.logging``.

Covers ``get_logger``, the ``log_context`` / ``LoggerContextManager``
contextvars binding, and the ``log_execution_time`` decorator for sync and
async functions across success and failure paths.

``setup_logging`` is intentionally not unit-tested: it mutates the root
logging handlers and the global structlog configuration (with logger
caching), which cannot be restored cleanly without risking cross-test
pollution — it is exercised at app startup in integration runs.
"""

import pytest
import structlog

from app.core.logging import (
    LoggerContextManager,
    get_logger,
    log_context,
    log_execution_time,
)

pytestmark = pytest.mark.unit


# =============================================================================
# get_logger
# =============================================================================


class TestGetLogger:
    def test_returns_usable_structlog_logger(self) -> None:
        """The logger exposes the structlog BoundLogger interface and logs."""
        logger = get_logger("stratum.test")

        assert callable(logger.info)
        assert callable(logger.error)
        assert callable(logger.bind)
        # Must not raise when actually used.
        logger.info("test_event", key="value")


# =============================================================================
# log_context / LoggerContextManager
# =============================================================================


class TestLogContext:
    def test_binds_context_inside_block_and_unbinds_after(self) -> None:
        """Context keys exist inside the block and are removed on exit."""
        with log_context(request_id="req-1", user_id=7) as cm:
            assert isinstance(cm, LoggerContextManager)
            ctx = structlog.contextvars.get_contextvars()
            assert ctx["request_id"] == "req-1"
            assert ctx["user_id"] == 7

        ctx_after = structlog.contextvars.get_contextvars()
        assert "request_id" not in ctx_after
        assert "user_id" not in ctx_after

    def test_unbinds_even_when_block_raises(self) -> None:
        """Exceptions propagate and the context is still cleaned up."""
        with pytest.raises(RuntimeError, match="boom"):
            with log_context(request_id="req-2"):
                raise RuntimeError("boom")

        assert "request_id" not in structlog.contextvars.get_contextvars()

    def test_empty_context_is_a_noop(self) -> None:
        """No keys means nothing to bind — and nothing to unbind on exit."""
        with log_context():
            pass  # must not raise on enter or exit


# =============================================================================
# log_execution_time
# =============================================================================


class TestLogExecutionTime:
    def test_sync_success_returns_value(self) -> None:
        """A wrapped sync function returns its value and keeps its name."""

        @log_execution_time
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        assert add(2, 3) == 5
        assert add.__name__ == "add"

    def test_sync_failure_reraises(self) -> None:
        """A failing sync function re-raises after logging."""

        @log_execution_time
        def explode() -> None:
            raise ValueError("sync boom")

        with pytest.raises(ValueError, match="sync boom"):
            explode()

    async def test_async_success_returns_value(self) -> None:
        """A wrapped coroutine returns its value and keeps its name."""

        @log_execution_time
        async def multiply(a: int, b: int) -> int:
            """Multiply two numbers."""
            return a * b

        assert await multiply(4, 5) == 20
        assert multiply.__name__ == "multiply"

    async def test_async_failure_reraises(self) -> None:
        """A failing coroutine re-raises after logging."""

        @log_execution_time
        async def explode() -> None:
            raise KeyError("async boom")

        with pytest.raises(KeyError, match="async boom"):
            await explode()
