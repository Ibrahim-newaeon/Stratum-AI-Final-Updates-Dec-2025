# =============================================================================
# Stratum AI - Error Handler Middleware Tests
# =============================================================================
"""
Tests for the last-resort error handler middleware that catches unhandled
exceptions and returns structured JSON 500 responses.

Covers:
- Successful request passthrough (no interference)
- Unhandled exception → JSON 500 response
- Error response structure validation
- CORS headers included when origin present
- CORS headers omitted when no origin
- Request ID propagation into error response
- Exception type and details logged
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.middleware.error_handler import ErrorHandlerMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    path: str = "/api/v1/campaigns",
    method: str = "GET",
    origin: str = "",
    request_id: str = "req-abc123",
) -> MagicMock:
    """Build a minimal mock Request."""
    req = MagicMock()
    req.url = MagicMock()
    req.url.path = path
    req.method = method
    req.headers = MagicMock()
    req.headers.get = MagicMock(side_effect=lambda key, default="": {
        "origin": origin,
    }.get(key, default))

    state = MagicMock()
    state.request_id = request_id
    req.state = state
    return req


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# Tests: Passthrough
# ---------------------------------------------------------------------------

class TestPassthrough:
    """Successful requests should pass through unchanged."""

    @pytest.mark.asyncio
    async def test_successful_request_returns_original_response(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        expected = _make_response(200)
        call_next = AsyncMock(return_value=expected)
        req = _make_request()

        response = await mw.dispatch(req, call_next)

        assert response is expected
        call_next.assert_awaited_once_with(req)

    @pytest.mark.asyncio
    async def test_4xx_response_passes_through(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        expected = _make_response(404)
        call_next = AsyncMock(return_value=expected)
        req = _make_request()

        response = await mw.dispatch(req, call_next)
        assert response is expected


# ---------------------------------------------------------------------------
# Tests: Exception handling
# ---------------------------------------------------------------------------

class TestExceptionHandling:
    """Unhandled exceptions should be caught and returned as JSON 500."""

    @pytest.mark.asyncio
    async def test_exception_returns_json_500(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("something broke"))
        req = _make_request()

        response = await mw.dispatch(req, call_next)

        assert response.status_code == 500
        body = response.body.decode("utf-8")
        import json
        data = json.loads(body)
        assert data["error"] == "INTERNAL_ERROR"
        assert data["message"] == "An unexpected error occurred"
        assert data["request_id"] == "req-abc123"

    @pytest.mark.asyncio
    async def test_value_error_returns_json_500(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=ValueError("bad value"))
        req = _make_request()

        response = await mw.dispatch(req, call_next)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_type_error_returns_json_500(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=TypeError("wrong type"))
        req = _make_request()

        response = await mw.dispatch(req, call_next)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Tests: CORS headers
# ---------------------------------------------------------------------------

class TestCorsHeaders:
    """CORS headers should NOT be added by the error handler.

    FastAPI's CORSMiddleware is responsible for setting the correct
    Access-Control-Allow-Origin.  The error handler must not hard-code
    a wildcard ``*`` because that would bypass the allow-list and expose
    error details to any origin.
    """

    @pytest.mark.asyncio
    async def test_no_cors_headers_even_with_origin(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("fail"))
        req = _make_request(origin="http://localhost:5173")

        response = await mw.dispatch(req, call_next)

        assert response.status_code == 500
        # Error handler delegates CORS to the CORSMiddleware — no manual headers
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.asyncio
    async def test_no_cors_headers_without_origin(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("fail"))
        req = _make_request(origin="")

        response = await mw.dispatch(req, call_next)

        assert response.status_code == 500
        assert "access-control-allow-origin" not in response.headers


# ---------------------------------------------------------------------------
# Tests: Request ID propagation
# ---------------------------------------------------------------------------

class TestRequestIdPropagation:
    """Error responses should include the original request ID."""

    @pytest.mark.asyncio
    async def test_request_id_in_error_response(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("boom"))
        req = _make_request(request_id="custom-req-id-999")

        response = await mw.dispatch(req, call_next)

        import json
        data = json.loads(response.body.decode("utf-8"))
        assert data["request_id"] == "custom-req-id-999"

    @pytest.mark.asyncio
    async def test_missing_request_id_defaults_to_unknown(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("boom"))
        req = _make_request()
        # Simulate missing request_id on state
        del req.state.request_id

        response = await mw.dispatch(req, call_next)

        import json
        data = json.loads(response.body.decode("utf-8"))
        assert data["request_id"] == "unknown"


# ---------------------------------------------------------------------------
# Tests: Logging
# ---------------------------------------------------------------------------

class TestLogging:
    """Exceptions should be logged with appropriate metadata."""

    @pytest.mark.asyncio
    async def test_exception_is_logged(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("log this"))
        req = _make_request(path="/api/v1/users", method="POST")

        with patch("app.middleware.error_handler.logger") as mock_logger:
            await mw.dispatch(req, call_next)

            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args
            # Check that error details are in the log
            assert "log this" in str(call_kwargs)
            assert "RuntimeError" in str(call_kwargs)


# ---------------------------------------------------------------------------
# Tests: Error response content
# ---------------------------------------------------------------------------

class TestErrorResponseContent:
    """The error response should never leak internal details."""

    @pytest.mark.asyncio
    async def test_no_stack_trace_in_response(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("secret internal error details"))
        req = _make_request()

        response = await mw.dispatch(req, call_next)

        body = response.body.decode("utf-8")
        assert "secret internal error details" not in body
        assert "Traceback" not in body

    @pytest.mark.asyncio
    async def test_error_response_has_required_fields(self) -> None:
        mw = ErrorHandlerMiddleware(MagicMock())
        call_next = AsyncMock(side_effect=RuntimeError("fail"))
        req = _make_request()

        response = await mw.dispatch(req, call_next)

        import json
        data = json.loads(response.body.decode("utf-8"))
        assert "error" in data
        assert "message" in data
        assert "request_id" in data
