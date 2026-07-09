# =============================================================================
# Stratum AI - CAPI Service Deep Integration Tests (#342 Batch 5)
# =============================================================================
"""Deep integration tests for ``app.services.capi.capi_service.CAPIService``.

Drives the service layer directly (the ``/api/v1/capi`` endpoint tests in
``test_capi_api.py`` only touch the read-only surface): platform connection
lifecycle, multi-platform event streaming with retry exhaustion, the event
buffer, data-quality analysis wrappers, event mapping, and PII hashing.

Platform connectors normally call platform HTTP APIs (Meta graph, Google Ads,
etc.); those are mocked at the connector boundary (``connect`` /
``test_connection`` / ``send_events``) so no network traffic happens. The
real ``DataQualityAnalyzer`` / ``AIEventMapper`` / ``PIIHasher`` run unmocked.
"""

from datetime import datetime, timezone
from unittest import mock

import pytest
import tenacity

from app.services.capi.capi_service import CAPIService, StreamResult
from app.services.capi.data_quality import QualityReport
from app.services.capi.platform_connectors import (
    CAPIResponse,
    ConnectionResult,
    ConnectionStatus,
    MetaCAPIConnector,
)

# NOTE: no module-level asyncio mark — this file mixes async and sync tests
# and pytest.ini sets asyncio_mode=auto, which picks up the async ones.
pytestmark = [pytest.mark.integration]


# =============================================================================
# Helpers
# =============================================================================


def _ok_response(platform: str, n: int = 1) -> CAPIResponse:
    return CAPIResponse(
        success=True,
        events_received=n,
        events_processed=n,
        errors=[],
        platform=platform,
        request_id="req-123",
    )


def _fail_response(platform: str, n: int = 1) -> CAPIResponse:
    return CAPIResponse(
        success=False,
        events_received=n,
        events_processed=0,
        errors=[{"message": "platform rejected batch"}],
        platform=platform,
    )


class _FakeConnector:
    """Stands in for a connected platform connector.

    Only the surface CAPIService touches is implemented: ``send_events``
    and ``test_connection``.
    """

    def __init__(
        self,
        platform: str = "meta",
        send_response: CAPIResponse = None,
        send_exc: Exception = None,
        test_result: ConnectionResult = None,
        test_exc: Exception = None,
    ):
        self.platform = platform
        self._send_response = send_response
        self._send_exc = send_exc
        self._test_result = test_result
        self._test_exc = test_exc
        self.send_calls = 0
        self.seen_events = []

    async def send_events(self, events):
        self.send_calls += 1
        self.seen_events.append(events)
        if self._send_exc is not None:
            raise self._send_exc
        return self._send_response or _ok_response(self.platform, len(events))

    async def test_connection(self):
        if self._test_exc is not None:
            raise self._test_exc
        return self._test_result or ConnectionResult(
            status=ConnectionStatus.CONNECTED,
            platform=self.platform,
            message="ok",
        )


def _event(name: str = "Purchase", **overrides) -> dict:
    base = {
        "event_name": name,
        "user_data": {"email": "buyer@example.com", "phone": "+15551234567"},
        "parameters": {"value": 42.0, "currency": "USD"},
        "event_time": int(datetime.now(timezone.utc).timestamp()),
        "event_id": "evt-1",
    }
    base.update(overrides)
    return base


@pytest.fixture
def service() -> CAPIService:
    return CAPIService()


# =============================================================================
# connect_platform / disconnect_platform
# =============================================================================


class TestConnectPlatform:
    async def test_unsupported_platform_returns_error(self, service):
        result = await service.connect_platform("myspace", {"token": "x"})
        assert result.status == ConnectionStatus.ERROR
        assert "Unsupported platform" in result.message
        assert service.connectors == {}

    async def test_successful_connect_registers_connector(self, service):
        connected = ConnectionResult(
            status=ConnectionStatus.CONNECTED, platform="meta", message="ok"
        )
        with mock.patch.object(
            MetaCAPIConnector, "connect", mock.AsyncMock(return_value=connected)
        ):
            # Case-insensitive platform names
            result = await service.connect_platform(
                "META", {"pixel_id": "1", "access_token": "t"}
            )

        assert result.status == ConnectionStatus.CONNECTED
        assert "meta" in service.connectors
        assert isinstance(service.connectors["meta"], MetaCAPIConnector)

    async def test_failed_connect_not_registered(self, service):
        failed = ConnectionResult(
            status=ConnectionStatus.ERROR, platform="meta", message="bad creds"
        )
        with mock.patch.object(
            MetaCAPIConnector, "connect", mock.AsyncMock(return_value=failed)
        ):
            result = await service.connect_platform(
                "meta", {"pixel_id": "1", "access_token": "bad"}
            )

        assert result.status == ConnectionStatus.ERROR
        assert "meta" not in service.connectors

    async def test_connect_exception_returns_error_result(self, service):
        with mock.patch.object(
            MetaCAPIConnector,
            "connect",
            mock.AsyncMock(side_effect=ValueError("boom")),
        ):
            result = await service.connect_platform("meta", {})

        assert result.status == ConnectionStatus.ERROR
        assert result.message == "boom"
        assert "meta" not in service.connectors

    async def test_disconnect_connected_platform(self, service):
        service.connectors["meta"] = _FakeConnector("meta")
        assert await service.disconnect_platform("Meta") is True
        assert "meta" not in service.connectors

    async def test_disconnect_unknown_platform_returns_false(self, service):
        assert await service.disconnect_platform("meta") is False

    async def test_get_connected_platforms(self, service):
        service.connectors["meta"] = _FakeConnector("meta")
        service.connectors["tiktok"] = _FakeConnector("tiktok")

        status = service.get_connected_platforms()

        assert status["meta"] == {"connected": True, "platform_name": "Meta"}
        assert status["tiktok"]["connected"] is True


# =============================================================================
# test_all_connections
# =============================================================================


class TestTestAllConnections:
    async def test_mixed_results(self, service):
        service.connectors["meta"] = _FakeConnector("meta")
        service.connectors["google"] = _FakeConnector(
            "google", test_exc=TimeoutError("api timeout")
        )

        results = await service.test_all_connections()

        assert results["meta"].status == ConnectionStatus.CONNECTED
        assert results["google"].status == ConnectionStatus.ERROR
        assert results["google"].message == "api timeout"

    async def test_empty_when_no_connectors(self, service):
        assert await service.test_all_connections() == {}


# =============================================================================
# stream_event / stream_events
# =============================================================================


class TestStreamEvents:
    async def test_empty_events_short_circuits(self, service):
        result = await service.stream_events([])
        assert isinstance(result, StreamResult)
        assert result.total_events == 0
        assert result.platforms_sent == 0
        assert result.platform_results == {}
        assert result.failed_platforms == []
        assert result.data_quality_score == 0

    async def test_successful_stream_to_connected_platform(self, service):
        fake = _FakeConnector("meta")
        service.connectors["meta"] = fake

        result = await service.stream_events([_event(), _event(name="Lead")])

        assert result.total_events == 2
        assert result.platforms_sent == 1
        assert result.failed_platforms == []
        assert result.platform_results["meta"].success is True
        # Events buffered for later quality reporting
        assert len(service._event_buffer) == 2
        # Connector saw the raw event batch once (no retries on success)
        assert fake.send_calls == 1
        # Real analyzer produced a score for events carrying email+phone
        assert result.data_quality_score > 0

    async def test_platform_not_connected_is_failed(self, service):
        service.connectors["meta"] = _FakeConnector("meta")

        result = await service.stream_events([_event()], platforms=["meta", "google"])

        assert result.platforms_sent == 1
        assert result.failed_platforms == ["google"]
        google = result.platform_results["google"]
        assert google.success is False
        assert google.errors == [{"message": "Platform not connected"}]

    async def test_unsuccessful_response_marks_platform_failed(self, service):
        fake = _FakeConnector("meta", send_response=_fail_response("meta"))
        service.connectors["meta"] = fake

        result = await service.stream_events([_event()])

        assert result.platforms_sent == 0
        assert result.failed_platforms == ["meta"]
        # A failed *response* (no exception) is not retried by the service
        assert fake.send_calls == 1

    async def test_connection_error_retries_then_fails(self, service):
        """Retry decorator exhausts 4 attempts on ConnectionError, then the
        service returns a failure CAPIResponse (no exception escapes)."""
        fake = _FakeConnector("meta", send_exc=ConnectionError("conn reset"))
        service.connectors["meta"] = fake

        # Collapse the exponential backoff so the test doesn't sleep ~7s.
        with mock.patch(
            "app.services.capi.capi_service.wait_exponential",
            lambda **kw: tenacity.wait_fixed(0),
        ):
            result = await service.stream_events([_event()])

        assert fake.send_calls == 4  # stop_after_attempt(4)
        assert result.failed_platforms == ["meta"]
        meta = result.platform_results["meta"]
        assert meta.success is False
        assert "Failed after retries" in meta.errors[0]["message"]
        assert "conn reset" in meta.errors[0]["message"]

    async def test_retry_recovers_after_transient_error(self, service):
        fake = _FakeConnector("meta")
        responses = [TimeoutError("blip"), _ok_response("meta")]

        async def flaky(events):
            fake.send_calls += 1
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        fake.send_events = flaky
        service.connectors["meta"] = fake

        with mock.patch(
            "app.services.capi.capi_service.wait_exponential",
            lambda **kw: tenacity.wait_fixed(0),
        ):
            result = await service.stream_events([_event()])

        assert fake.send_calls == 2
        assert result.platforms_sent == 1
        assert result.failed_platforms == []

    async def test_event_buffer_trims_to_1000(self, service):
        service.connectors["meta"] = _FakeConnector("meta")
        service._event_buffer = [{"user_data": {}, "seq": i} for i in range(995)]

        await service.stream_events([_event(event_id=f"e-{i}") for i in range(10)])

        assert len(service._event_buffer) == 1000
        # Oldest entries were dropped, newest kept
        assert service._event_buffer[-1]["event_id"] == "e-9"
        assert service._event_buffer[0]["seq"] == 5

    async def test_stream_event_builds_event_and_defaults(self, service):
        fake = _FakeConnector("meta")
        service.connectors["meta"] = fake

        result = await service.stream_event(
            event_name="Purchase",
            user_data={"email": "a@b.com"},
            parameters={"value": 10.0},
            event_source_url="https://shop.example.com/checkout",
            event_id="dedup-1",
        )

        assert result.total_events == 1
        assert result.platforms_sent == 1
        sent = fake.seen_events[0][0]
        assert sent["event_name"] == "Purchase"
        assert sent["event_id"] == "dedup-1"
        assert sent["event_source_url"] == "https://shop.example.com/checkout"
        assert isinstance(sent["event_time"], int)

    async def test_stream_event_minimal_defaults(self, service):
        """parameters/platforms/event_time default paths (None args)."""
        fake = _FakeConnector("meta")
        service.connectors["meta"] = fake

        result = await service.stream_event(
            event_name="Lead", user_data={"email": "a@b.com"}
        )

        assert result.total_events == 1
        sent = fake.seen_events[0][0]
        assert sent["parameters"] == {}
        assert sent["event_id"] is None


# =============================================================================
# Data quality wrappers
# =============================================================================


class TestDataQuality:
    def test_analyze_data_quality_all_platforms(self, service):
        analysis = service.analyze_data_quality(
            {"email": "buyer@example.com", "phone": "+15551234567"}
        )
        assert "overall_score" in analysis
        assert set(analysis["platform_scores"]) >= {"meta", "google"}
        assert analysis["overall_score"] > 0

    def test_analyze_data_quality_single_platform(self, service):
        analysis = service.analyze_data_quality(
            {"email": "buyer@example.com"}, platform="meta"
        )
        assert analysis["platform"] == "meta"
        assert "overall_score" in analysis
        assert "score" in analysis

    def test_analyze_data_quality_unknown_platform_falls_back(self, service):
        # "whatsapp" has no FIELD_WEIGHTS entry -> full analysis returned
        analysis = service.analyze_data_quality(
            {"email": "buyer@example.com"}, platform="whatsapp"
        )
        assert "platform_scores" in analysis
        assert "platform" not in analysis

    def test_quality_report_none_when_no_events(self, service):
        assert service.get_data_quality_report() is None

    def test_quality_report_from_buffer(self, service):
        service._event_buffer = [_event(), _event(name="Lead")]
        report = service.get_data_quality_report(platforms=["meta"])
        assert isinstance(report, QualityReport)
        assert report.overall_score > 0
        assert "meta" in report.platform_scores

    def test_live_insights_no_data(self, service):
        insights = service.get_live_insights()
        assert insights["status"] == "no_data"

    def test_live_insights_with_events(self, service):
        service._event_buffer = [_event(event_id=f"e-{i}") for i in range(12)]
        insights = service.get_live_insights(platform="meta")
        assert insights["status"] == "active"
        assert insights["events_analyzed"] == 12
        assert "current_score" in insights


# =============================================================================
# map_event / hash_user_data / detect_pii_fields
# =============================================================================


class TestMappingAndHashing:
    def test_map_event_returns_validation(self, service):
        result = service.map_event("Purchase", {"value": 10.0, "currency": "USD"})
        assert isinstance(result, dict)
        assert "valid" in result or "issues" in result or "mapping" in result

    def test_map_event_defaults_parameters(self, service):
        result = service.map_event("Purchase")
        assert isinstance(result, dict)

    def test_hash_user_data_hashes_email(self, service):
        hashed = service.hash_user_data({"email": "Buyer@Example.com "})
        # PIIHasher normalizes then SHA-256 hashes; a 64-char hex digest
        # lands under the platform-standard field name.
        values = [v for v in hashed.values() if isinstance(v, str)]
        assert any(
            len(v) == 64 and all(c in "0123456789abcdef" for c in v) for v in values
        )
        assert "Buyer@Example.com " not in hashed.values()

    def test_detect_pii_fields_shape(self, service):
        detections = service.detect_pii_fields(
            {"email": "buyer@example.com", "phone": "+15551234567"}
        )
        assert len(detections) >= 2
        for d in detections:
            assert {"field", "original_key", "type", "confidence"} <= set(d)


# =============================================================================
# get_platform_requirements / get_setup_status
# =============================================================================


class TestRequirementsAndStatus:
    async def test_requirements_known_platform(self, service):
        req = await service.get_platform_requirements("Meta")
        assert req["name"].startswith("Meta")
        assert any(c["field"] == "pixel_id" for c in req["credentials_needed"])

    async def test_requirements_unknown_platform(self, service):
        req = await service.get_platform_requirements("myspace")
        assert "error" in req
        assert "meta" in req["supported_platforms"]

    def test_setup_status_empty(self, service):
        status = service.get_setup_status()
        assert status["connected_platforms"] == []
        assert status["setup_complete"] is False
        assert status["events_processed"] == 0
        assert status["data_quality_score"] == 0

    def test_setup_status_with_connection_and_events(self, service):
        service.connectors["meta"] = _FakeConnector("meta")
        service._event_buffer = [_event()]

        status = service.get_setup_status()

        assert status["connected_platforms"] == ["meta"]
        assert status["setup_complete"] is True
        assert status["events_processed"] == 1
        assert isinstance(status["data_quality_score"], float)
