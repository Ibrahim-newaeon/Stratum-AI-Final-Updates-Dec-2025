# =============================================================================
# Stratum AI - Request Logging Middleware Tests
# =============================================================================
"""
Tests for the request logging middleware that assigns request IDs,
measures timing, and emits structured access logs.

Covers:
- Request ID assignment (auto-generated and client-supplied)
- Request ID bound in structlog context
- Response headers (X-Request-ID, X-Process-Time-Ms)
- Noisy path skipping (/health, /docs, etc.)
- Normal paths are logged
- Structured log fields (method, path, status_code, duration_ms)
- structlog context is cleaned up after request
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import structlog

from app.middleware.request_logging import (
    RequestLoggingMiddleware,
    _SKIP_PATHS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    path: str = "/api/v1/campaigns",
    method: str = "GET",
    request_id: str | None = None,
) -> MagicMock:
    """Build a minimal mock Request."""
    req = MagicMock()
    req.url = MagicMock()
    req.url.path = path
    req.method = method

    headers: dict[str, str] = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    req.headers = MagicMock()
    req.headers.get = MagicMock(side_effect=lambda key, default=None: headers.get(key, default))

    req.state = MagicMock()
    return req


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# Tests: Request ID assignment
# ---------------------------------------------------------------------------

class TestRequestIdAssignment:
    """Middleware should assign a request ID to every request."""

    @pytest.mark.asyncio
    async def test_auto_generated_request_id(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        resp = _make_response()
        call_next = AsyncMock(return_value=resp)
        req = _make_request()

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            await mw.dispatch(req, call_next)

        # request_id should be set on state
        assert hasattr(req.state, "request_id")
        # Auto-generated IDs are 12 hex chars
        rid = req.state.request_id
        assert isinstance(rid, str)
        assert len(rid) == 12

    @pytest.mark.asyncio
    async def test_client_supplied_request_id_preserved(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        resp = _make_response()
        call_next = AsyncMock(return_value=resp)
        req = _make_request(request_id="client-req-42")

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            await mw.dispatch(req, call_next)

        assert req.state.request_id == "client-req-42"


# ---------------------------------------------------------------------------
# Tests: Response headers
# ---------------------------------------------------------------------------

class TestResponseHeaders:
    """Middleware should inject X-Request-ID and X-Process-Time-Ms headers."""

    @pytest.mark.asyncio
    async def test_x_request_id_header_set(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        resp = _make_response()
        call_next = AsyncMock(return_value=resp)
        req = _make_request(request_id="my-id")

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            result = await mw.dispatch(req, call_next)

        assert result.headers["X-Request-ID"] == "my-id"

    @pytest.mark.asyncio
    async def test_x_process_time_header_set(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        resp = _make_response()
        call_next = AsyncMock(return_value=resp)
        req = _make_request()

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            result = await mw.dispatch(req, call_next)

        assert "X-Process-Time-Ms" in result.headers
        # Value should be a float-like string
        val = float(result.headers["X-Process-Time-Ms"])
        assert val >= 0


# ---------------------------------------------------------------------------
# Tests: Noisy path skipping
# ---------------------------------------------------------------------------

class TestNoisyPathSkipping:
    """Health checks, docs, and other noisy paths should not be logged."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", list(_SKIP_PATHS))
    async def test_skip_paths_not_logged(self, path: str) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(path=path)

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"), \
             patch("app.middleware.request_logging.logger") as mock_logger:
            await mw.dispatch(req, call_next)
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_path_is_logged(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(path="/api/v1/users")

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"), \
             patch("app.middleware.request_logging.logger") as mock_logger:
            await mw.dispatch(req, call_next)
            mock_logger.info.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Structured log fields
# ---------------------------------------------------------------------------

class TestStructuredLogFields:
    """Log output should include method, path, status_code, duration_ms."""

    @pytest.mark.asyncio
    async def test_log_includes_required_fields(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(201))
        req = _make_request(path="/api/v1/campaigns", method="POST")

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"), \
             patch("app.middleware.request_logging.logger") as mock_logger:
            await mw.dispatch(req, call_next)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            kwargs = call_args.kwargs if call_args.kwargs else {}
            # If called as positional: info("request_completed", method=..., ...)
            if not kwargs:
                kwargs = {k: v for k, v in call_args[1].items()} if len(call_args) > 1 else {}
                # Try keyword args from call_args
                kwargs = call_args.kwargs

            assert call_args[0][0] == "request_completed"
            assert kwargs["method"] == "POST"
            assert kwargs["path"] == "/api/v1/campaigns"
            assert kwargs["status_code"] == 201
            assert "duration_ms" in kwargs
            assert isinstance(kwargs["duration_ms"], (int, float))


# ---------------------------------------------------------------------------
# Tests: structlog context cleanup
# ---------------------------------------------------------------------------

class TestStructlogContextCleanup:
    """request_id should be unbound after each request to prevent leaks."""

    @pytest.mark.asyncio
    async def test_context_bound_and_unbound(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(request_id="ctx-test")

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars") as mock_bind, \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars") as mock_unbind:
            await mw.dispatch(req, call_next)

            mock_bind.assert_called_once_with(request_id="ctx-test")
            mock_unbind.assert_called_once_with("request_id")


# ---------------------------------------------------------------------------
# Tests: Timing accuracy
# ---------------------------------------------------------------------------

class TestTimingAccuracy:
    """Process time should reflect actual request duration."""

    @pytest.mark.asyncio
    async def test_slow_request_has_longer_duration(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())

        async def slow_next(req: MagicMock) -> MagicMock:
            import asyncio
            await asyncio.sleep(0.05)  # 50ms
            return _make_response()

        req = _make_request()

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            result = await mw.dispatch(req, slow_next)

        duration = float(result.headers["X-Process-Time-Ms"])
        assert duration >= 40  # Allow some tolerance


# ---------------------------------------------------------------------------
# Tests: Response passthrough
# ---------------------------------------------------------------------------

class TestResponsePassthrough:
    """The middleware should not modify the response object itself."""

    @pytest.mark.asyncio
    async def test_response_status_unchanged(self) -> None:
        mw = RequestLoggingMiddleware(MagicMock())
        resp = _make_response(404)
        call_next = AsyncMock(return_value=resp)
        req = _make_request()

        with patch("app.middleware.request_logging.structlog.contextvars.bind_contextvars"), \
             patch("app.middleware.request_logging.structlog.contextvars.unbind_contextvars"):
            result = await mw.dispatch(req, call_next)

        assert result.status_code == 404
