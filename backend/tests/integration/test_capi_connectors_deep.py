# =============================================================================
# Stratum AI - Platform CAPI Connectors Deep Integration Tests (#342 Batch 5+6)
# =============================================================================
"""Contract tests for ``app.services.capi.platform_connectors``.

All platform HTTP is intercepted with respx (the module uses httpx), so every
test asserts BOTH the outbound request contract (URL, auth header/param
injection, payload field mapping, PII hashing) and the response handling
(200 / 4xx / 5xx / timeout / malformed body / partial success).

Also covers the base ``send_events`` orchestration (retry with exponential
backoff, no-retry on client errors, circuit breaker wiring, EMQ delivery
logging), plus the P0 helpers: ConnectionPool and EventDeduplicator.

Known production behaviors pinned here (NOT fixed, per #342 rules):

1. Malformed (non-JSON) platform responses raise ``json.JSONDecodeError``
   out of ``_send_events_impl``; the retry loop in ``send_events`` only
   catches (ConnectionError, TimeoutError, OSError, httpx.HTTPError), so the
   exception escapes ``send_events`` entirely — no retry, no circuit-breaker
   failure recording. See ``test_meta_malformed_json_response_escapes``.
2. ``ConnectionPool.scale_up`` on a platform never seen by ``get_client``
   leaves ``_client_index`` unpopulated, so a subsequent ``get_client``
   raises KeyError. See ``test_scale_up_before_get_client_breaks_pool``.
3. Google/Snapchat ``test_connection`` report CONNECTED on arbitrary non-401
   errors and even on network failure ("Credentials validated (offline)") —
   credentials are effectively never verified beyond presence.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.services.capi.platform_connectors import (
    CircuitState,
    ConnectionPool,
    ConnectionStatus,
    EventDeduplicator,
    EventDeliveryLog,
    GoogleCAPIConnector,
    MetaCAPIConnector,
    SnapchatCAPIConnector,
    TikTokCAPIConnector,
    WhatsAppCAPIConnector,
    get_event_delivery_logs,
    log_event_delivery,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _isolate_delivery_logs():
    """Snapshot/restore the module-global EMQ delivery log store.

    ``send_events`` appends to ``_event_delivery_logs`` on every attempt;
    without isolation those entries leak into any later test that reads the
    global store (e.g. ConnectorHealthMonitor summaries without explicit
    logs) when suites share a process.
    """
    import app.services.capi.platform_connectors as mod

    saved = mod._event_delivery_logs
    mod._event_delivery_logs = list(saved)
    yield
    mod._event_delivery_logs = saved


def sha256_of(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


NO_DELAYS = [0.0, 0.0, 0.0]


# =============================================================================
# Meta connector
# =============================================================================

META_PIXEL_URL = "https://graph.facebook.com/v18.0/pix123"
META_EVENTS_URL = "https://graph.facebook.com/v18.0/pix123/events"


def make_meta(connected: bool = False) -> MetaCAPIConnector:
    c = MetaCAPIConnector()
    c.pixel_id = "pix123"
    c.access_token = "tok-abc"
    c.RETRY_DELAYS = NO_DELAYS
    if connected:
        c._connected = True
    return c


class TestMetaConnect:
    async def test_connect_missing_credentials_errors(self):
        result = await MetaCAPIConnector().connect({"pixel_id": "only-pixel"})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing pixel_id or access_token" in result.message

    async def test_connect_success_returns_pixel_details(self):
        connector = MetaCAPIConnector()
        with respx.mock(assert_all_called=True) as router:
            route = router.get(META_PIXEL_URL).mock(
                return_value=httpx.Response(200, json={"name": "My Pixel"})
            )
            result = await connector.connect(
                {"pixel_id": "pix123", "access_token": "tok-abc"}
            )

        assert result.status == ConnectionStatus.CONNECTED
        assert result.platform == "meta"
        assert result.details == {"pixel_name": "My Pixel"}
        assert connector._connected is True
        # Auth is injected as a query param on the test request
        sent = route.calls.last.request
        assert "access_token=tok-abc" in str(sent.url)

    async def test_test_connection_unconfigured_is_disconnected(self):
        result = await MetaCAPIConnector().test_connection()
        assert result.status == ConnectionStatus.DISCONNECTED
        assert result.message == "Not configured"

    async def test_test_connection_api_error_surfaces_platform_message(self):
        connector = make_meta()
        with respx.mock:
            respx.get(META_PIXEL_URL).mock(
                return_value=httpx.Response(
                    400, json={"error": {"message": "Invalid OAuth token"}}
                )
            )
            result = await connector.test_connection()

        assert result.status == ConnectionStatus.ERROR
        assert result.message == "Invalid OAuth token"
        assert connector._connected is False

    async def test_test_connection_network_error_is_error(self):
        connector = make_meta()
        with respx.mock:
            respx.get(META_PIXEL_URL).mock(side_effect=httpx.ConnectError("refused"))
            result = await connector.test_connection()

        assert result.status == ConnectionStatus.ERROR
        assert "refused" in result.message


class TestMetaSendEvents:
    async def test_send_events_payload_contract(self):
        """The outbound Meta payload maps/normalizes every field."""
        connector = make_meta(connected=True)
        event = {
            "event_id": "evt-1",
            "event_name": "purchase",
            "event_time": 1700000000,
            "event_source_url": "https://shop.example/checkout",
            "action_source": "app",
            "user_data": {"email": "Jane@Example.COM", "phone": "+1 555-123-4567"},
            "parameters": {"amount": "42.5", "currency": "USD"},
        }

        with respx.mock(assert_all_called=True) as router:
            route = router.post(META_EVENTS_URL).mock(
                return_value=httpx.Response(
                    200, json={"events_received": 1, "fbtrace_id": "fbtr-9"}
                )
            )
            response = await connector.send_events([event])

        assert response.success is True
        assert response.events_received == 1
        assert response.events_processed == 1
        assert response.request_id == "fbtr-9"
        assert response.platform == "meta"

        payload = json.loads(route.calls.last.request.content)
        assert payload["access_token"] == "tok-abc"
        (formatted,) = payload["data"]
        assert formatted["event_name"] == "Purchase"  # mapped from "purchase"
        assert formatted["event_time"] == 1700000000
        assert formatted["action_source"] == "app"
        assert formatted["event_source_url"] == "https://shop.example/checkout"
        assert formatted["event_id"] == "evt-1"
        # PII hashed with SHA256 after normalization, raw keys removed
        assert formatted["user_data"]["em"] == sha256_of("jane@example.com")
        assert formatted["user_data"]["ph"] == sha256_of("15551234567")
        assert "email" not in formatted["user_data"]
        assert "phone" not in formatted["user_data"]
        # amount -> value (float) via parameter mapping
        assert formatted["custom_data"]["value"] == 42.5
        assert formatted["custom_data"]["currency"] == "USD"

    async def test_send_events_not_connected_short_circuits(self):
        connector = make_meta(connected=False)
        with respx.mock(assert_all_called=False) as router:
            route = router.post(META_EVENTS_URL)
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors == [{"message": "Not connected"}]
        assert route.call_count == 0

    async def test_send_events_client_error_does_not_retry(self):
        """Errors containing 'invalid' are treated as permanent (single call)."""
        connector = make_meta(connected=True)
        with respx.mock as router:
            route = respx.post(META_EVENTS_URL).mock(
                return_value=httpx.Response(
                    400,
                    json={"error": {"message": "Invalid parameter", "code": 100}},
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors[0]["message"] == "Invalid parameter"
        assert route.call_count == 1
        # A single permanent failure records one circuit-breaker failure
        assert connector._circuit_breaker.failure_count == 1

    async def test_send_events_server_error_retries_then_fails(self):
        connector = make_meta(connected=True)
        with respx.mock:
            route = respx.post(META_EVENTS_URL).mock(
                return_value=httpx.Response(
                    500, json={"error": {"message": "Service unavailable"}}
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert route.call_count == connector.MAX_RETRIES
        assert connector._circuit_breaker.failure_count == 1

    async def test_send_events_timeout_retries_then_recovers(self):
        connector = make_meta(connected=True)
        with respx.mock:
            route = respx.post(META_EVENTS_URL).mock(
                side_effect=[
                    httpx.ConnectTimeout("timed out"),
                    httpx.Response(500, json={"error": {"message": "flaky"}}),
                    httpx.Response(200, json={"events_received": 1}),
                ]
            )
            response = await connector.send_events(
                [{"event_name": "purchase", "event_id": "evt-retry"}]
            )

        assert response.success is True
        assert route.call_count == 3
        # Success resets the closed-state failure count
        assert connector._circuit_breaker.failure_count == 0
        assert connector._circuit_breaker.state == CircuitState.CLOSED

    async def test_send_events_all_timeouts_reports_exception_message(self):
        connector = make_meta(connected=True)
        with respx.mock:
            route = respx.post(META_EVENTS_URL).mock(
                side_effect=httpx.ConnectTimeout("dead upstream")
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert route.call_count == connector.MAX_RETRIES
        assert "dead upstream" in response.errors[0]["message"]

    async def test_send_events_circuit_open_rejects_without_http(self):
        connector = make_meta(connected=True)
        connector._circuit_breaker.state = CircuitState.OPEN
        connector._circuit_breaker.last_failure_time = time.time()

        with respx.mock(assert_all_called=False) as router:
            route = router.post(META_EVENTS_URL)
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert "Circuit breaker open" in response.errors[0]["message"]
        assert route.call_count == 0

    async def test_meta_malformed_json_response_escapes(self):
        """PINNED BUG (do not fix here): a non-JSON body (e.g. an HTML 502
        page from a proxy) raises json.JSONDecodeError out of send_events —
        it is not caught by the retry loop, so there is no retry and the
        circuit breaker never records the failure."""
        connector = make_meta(connected=True)
        with respx.mock:
            respx.post(META_EVENTS_URL).mock(
                return_value=httpx.Response(200, content=b"<html>Bad Gateway</html>")
            )
            with pytest.raises(json.JSONDecodeError):
                await connector.send_events([{"event_name": "purchase"}])

        assert connector._circuit_breaker.failure_count == 0

    async def test_send_events_impl_exception_caught_by_outer_retry_loop(self):
        """If _send_events_impl itself raises a transport error (rather than
        catching it internally), the base retry loop absorbs it and returns a
        failure response after MAX_RETRIES attempts."""
        connector = make_meta(connected=True)
        calls = {"n": 0}

        async def boom(events):
            calls["n"] += 1
            raise ConnectionError("socket exploded")

        connector._send_events_impl = boom
        response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert calls["n"] == connector.MAX_RETRIES
        assert "socket exploded" in response.errors[0]["message"]
        assert connector._circuit_breaker.failure_count == 1

    async def test_send_events_logs_delivery_for_emq(self):
        connector = make_meta(connected=True)
        started = datetime.now(timezone.utc)
        with respx.mock:
            respx.post(META_EVENTS_URL).mock(
                return_value=httpx.Response(200, json={"events_received": 1})
            )
            await connector.send_events(
                [{"event_name": "purchase", "event_id": "evt-emq-log"}]
            )

        logs = [
            log
            for log in get_event_delivery_logs(platform="meta", since=started)
            if log.event_id == "evt-emq-log"
        ]
        assert len(logs) == 1
        assert logs[0].success is True
        assert logs[0].event_name == "purchase"
        assert logs[0].latency_ms >= 0
        assert logs[0].retry_count == 0


class TestMetaFormatEvent:
    def test_unknown_event_maps_to_custom_event_with_defaults(self):
        connector = make_meta()
        before = int(time.time())
        formatted = connector._format_event({"event_name": "frobnicate_widget"})
        assert formatted["event_name"] == "CustomEvent"
        assert formatted["action_source"] == "website"
        assert before <= formatted["event_time"] <= int(time.time())
        assert "custom_data" not in formatted
        assert "event_source_url" not in formatted
        assert "event_id" not in formatted

    def test_base_helpers_map_event_and_circuit_state(self):
        connector = make_meta()
        mapped = connector.map_event("add_to_cart", {"price": "9.99"})
        assert mapped["event_name"] == "AddToCart"
        assert mapped["parameters"]["value"] == 9.99

        state = connector.get_circuit_state()
        assert state == {"state": "closed", "failure_count": 0, "last_failure": None}


# =============================================================================
# Google connector
# =============================================================================

GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CUSTOMER_URL = "https://googleads.googleapis.com/v15/customers/1234567890"
GOOGLE_UPLOAD_URL = (
    "https://googleads.googleapis.com/v15/customers/1234567890"
    ":uploadConversionAdjustments"
)

GOOGLE_CREDS = {
    "customer_id": "123-456-7890",
    "conversion_action_id": "987",
    "developer_token": "dev-tok",
    "refresh_token": "refresh-tok",
    "client_id": "client-id",
    "client_secret": "client-secret",
}


def make_google(connected: bool = False, oauth: bool = True) -> GoogleCAPIConnector:
    c = GoogleCAPIConnector()
    c.customer_id = "1234567890"
    c.conversion_action_id = "987"
    c.developer_token = "dev-tok"
    if oauth:
        c.refresh_token = "refresh-tok"
        c.client_id = "client-id"
        c.client_secret = "client-secret"
    c.RETRY_DELAYS = NO_DELAYS
    if connected:
        c._connected = True
    return c


class TestGoogleConnect:
    async def test_connect_missing_required_credentials_errors(self):
        result = await GoogleCAPIConnector().connect({"customer_id": "123"})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing required credentials" in result.message

    async def test_connect_strips_dashes_and_sends_auth_headers(self):
        connector = GoogleCAPIConnector()
        with respx.mock(assert_all_called=True) as router:
            router.post(GOOGLE_OAUTH_URL).mock(
                return_value=httpx.Response(
                    200, json={"access_token": "oauth-tok", "expires_in": 3600}
                )
            )
            customer_route = router.get(GOOGLE_CUSTOMER_URL).mock(
                return_value=httpx.Response(200, json={"resourceName": "customers/1"})
            )
            result = await connector.connect(GOOGLE_CREDS)

        assert result.status == ConnectionStatus.CONNECTED
        assert connector.customer_id == "1234567890"  # dashes stripped
        assert result.details == {"customer_id": "1234567890"}
        headers = customer_route.calls.last.request.headers
        assert headers["authorization"] == "Bearer oauth-tok"
        assert headers["developer-token"] == "dev-tok"

    async def test_access_token_cached_until_expiry(self):
        connector = make_google()
        with respx.mock:
            oauth_route = respx.post(GOOGLE_OAUTH_URL).mock(
                return_value=httpx.Response(
                    200, json={"access_token": "oauth-tok", "expires_in": 3600}
                )
            )
            token1 = await connector._get_access_token()
            token2 = await connector._get_access_token()

        assert token1 == token2 == "oauth-tok"
        assert oauth_route.call_count == 1

        # Force expiry -> refresh happens again
        connector._token_expires = time.time() - 1
        with respx.mock:
            oauth_route = respx.post(GOOGLE_OAUTH_URL).mock(
                return_value=httpx.Response(
                    200, json={"access_token": "oauth-tok-2", "expires_in": 3600}
                )
            )
            assert await connector._get_access_token() == "oauth-tok-2"

    async def test_access_token_without_oauth_uses_developer_token(self):
        connector = make_google(oauth=False)
        assert await connector._get_access_token() == "dev-tok"

    async def test_access_token_oauth_http_error_falls_back(self):
        connector = make_google()
        with respx.mock:
            respx.post(GOOGLE_OAUTH_URL).mock(
                return_value=httpx.Response(400, json={"error": "invalid_grant"})
            )
            assert await connector._get_access_token() == "dev-tok"

    async def test_access_token_oauth_network_error_falls_back(self):
        connector = make_google()
        with respx.mock:
            respx.post(GOOGLE_OAUTH_URL).mock(side_effect=httpx.ConnectError("refused"))
            assert await connector._get_access_token() == "dev-tok"

    async def test_test_connection_unconfigured_is_disconnected(self):
        result = await GoogleCAPIConnector().test_connection()
        assert result.status == ConnectionStatus.DISCONNECTED

    async def test_test_connection_401_is_auth_error(self):
        connector = make_google(oauth=False)
        with respx.mock:
            respx.get(GOOGLE_CUSTOMER_URL).mock(return_value=httpx.Response(401))
            result = await connector.test_connection()

        assert result.status == ConnectionStatus.ERROR
        assert "Authentication failed" in result.message
        assert connector._connected is False

    async def test_test_connection_other_error_still_connects(self):
        """Pinned behavior: any non-401 error is treated as validated."""
        connector = make_google(oauth=False)
        with respx.mock:
            respx.get(GOOGLE_CUSTOMER_URL).mock(return_value=httpx.Response(403))
            result = await connector.test_connection()

        assert result.status == ConnectionStatus.CONNECTED
        assert result.message == "Credentials validated"
        assert connector._connected is True

    async def test_test_connection_network_error_connects_offline(self):
        """Pinned behavior: network failure with creds -> CONNECTED offline."""
        connector = make_google(oauth=False)
        with respx.mock:
            respx.get(GOOGLE_CUSTOMER_URL).mock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await connector.test_connection()

        assert result.status == ConnectionStatus.CONNECTED
        assert result.message == "Credentials validated (offline)"
        assert connector._connected is True


class TestGoogleSendEvents:
    async def test_send_events_payload_contract(self):
        connector = make_google(connected=True, oauth=False)
        event = {
            "event_id": "order-77",
            "event_name": "purchase",
            "event_time": 1700000000,
            "user_data": {
                "email": "jane@example.com",
                "phone": "+15551234567",
                "gclid": "gclid-xyz",
                "address": {
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "country": "GB",
                    "postal_code": "SW1A",
                },
            },
            "parameters": {"value": "99.5", "currency": "EUR"},
        }

        with respx.mock(assert_all_called=True) as router:
            route = router.post(GOOGLE_UPLOAD_URL).mock(
                return_value=httpx.Response(200, json={"requestId": "req-1"})
            )
            response = await connector.send_events([event])

        assert response.success is True
        assert response.events_processed == 1
        assert response.request_id == "req-1"

        request = route.calls.last.request
        assert request.headers["authorization"] == "Bearer dev-tok"
        assert request.headers["developer-token"] == "dev-tok"

        payload = json.loads(request.content)
        assert payload["partialFailure"] is True
        (conv,) = payload["conversions"]
        assert conv["conversionAction"] == (
            "customers/1234567890/conversionActions/987"
        )
        assert conv["conversionDateTime"] == "2023-11-14 22:13:20+0000"
        assert conv["conversionValue"] == 99.5
        assert conv["currencyCode"] == "EUR"
        assert conv["gclid"] == "gclid-xyz"
        assert conv["orderId"] == "order-77"

        identifiers = conv["userIdentifiers"]
        assert {"hashedEmail": sha256_of("jane@example.com")} in identifiers
        assert {"hashedPhoneNumber": sha256_of("15551234567")} in identifiers
        address_info = next(i for i in identifiers if "addressInfo" in i)["addressInfo"]
        assert address_info["hashedFirstName"] == sha256_of("jane")
        assert address_info["hashedLastName"] == sha256_of("doe")
        assert address_info["countryCode"] == "GB"
        assert address_info["postalCode"] == "SW1A"

    async def test_send_events_partial_failure_counts_failed_rows(self):
        connector = make_google(connected=True, oauth=False)
        with respx.mock:
            respx.post(GOOGLE_UPLOAD_URL).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "requestId": "req-2",
                        "partialFailureError": {
                            "message": "2 conversions rejected",
                            "details": [{"idx": 0}, {"idx": 1}],
                        },
                    },
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}] * 3)

        assert response.success is True
        assert response.events_received == 3
        assert response.events_processed == 1
        assert response.errors[0]["message"] == "2 conversions rejected"

    async def test_send_events_api_error_returns_code_and_retries(self):
        connector = make_google(connected=True, oauth=False)
        with respx.mock:
            route = respx.post(GOOGLE_UPLOAD_URL).mock(
                return_value=httpx.Response(
                    500,
                    json={"error": {"message": "Internal error", "code": 500}},
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors[0] == {"message": "Internal error", "code": 500}
        assert route.call_count == connector.MAX_RETRIES

    async def test_send_events_invalid_error_is_permanent(self):
        connector = make_google(connected=True, oauth=False)
        with respx.mock:
            route = respx.post(GOOGLE_UPLOAD_URL).mock(
                return_value=httpx.Response(
                    400,
                    json={"error": {"message": "Invalid customer ID", "code": 3}},
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert route.call_count == 1

    async def test_send_events_network_error_message(self):
        connector = make_google(connected=True, oauth=False)
        with respx.mock:
            respx.post(GOOGLE_UPLOAD_URL).mock(
                side_effect=httpx.ReadTimeout("read timeout")
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert "read timeout" in response.errors[0]["message"]

    def test_format_event_without_time_or_extras_uses_now(self):
        connector = make_google(oauth=False)
        before = datetime.now(timezone.utc)
        formatted = connector._format_event(
            {"event_name": "purchase", "parameters": {"order_id": "ord-1"}}
        )
        parsed = datetime.strptime(
            formatted["conversionDateTime"], "%Y-%m-%d %H:%M:%S%z"
        )
        assert abs((parsed - before).total_seconds()) < 5
        assert formatted["userIdentifiers"] == []
        assert "conversionValue" not in formatted
        assert "gclid" not in formatted
        assert formatted["orderId"] == "ord-1"  # falls back to parameters.order_id


# =============================================================================
# TikTok connector
# =============================================================================

TIKTOK_TRACK_URL = "https://business-api.tiktok.com/open_api/v1.3/pixel/track/"


def make_tiktok(connected: bool = False) -> TikTokCAPIConnector:
    c = TikTokCAPIConnector()
    c.pixel_code = "pxc-1"
    c.access_token = "tt-tok"
    c.RETRY_DELAYS = NO_DELAYS
    if connected:
        c._connected = True
    return c


class TestTikTokConnector:
    async def test_connect_missing_credentials_errors(self):
        result = await TikTokCAPIConnector().connect({"pixel_code": "pxc-1"})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing pixel_code or access_token" in result.message

    async def test_connect_validates_presence_only_no_http(self):
        connector = TikTokCAPIConnector()
        with respx.mock(assert_all_called=False):
            result = await connector.connect(
                {"pixel_code": "pxc-1", "access_token": "tt-tok"}
            )
        assert result.status == ConnectionStatus.CONNECTED
        assert result.details == {"pixel_code": "pxc-1"}
        assert connector._connected is True

    async def test_test_connection_unconfigured_is_disconnected(self):
        result = await TikTokCAPIConnector().test_connection()
        assert result.status == ConnectionStatus.DISCONNECTED

    async def test_send_events_payload_contract(self):
        connector = make_tiktok(connected=True)
        event = {
            "event_name": "purchase",
            "event_time": 1700000000,
            "event_source_url": "https://shop.example/done",
            "user_data": {"email": "jane@example.com"},
            "parameters": {"value": 10, "currency": "USD"},
        }

        with respx.mock(assert_all_called=True) as router:
            route = router.post(TIKTOK_TRACK_URL).mock(
                return_value=httpx.Response(
                    200, json={"code": 0, "request_id": "tt-req-1"}
                )
            )
            response = await connector.send_events([event])

        assert response.success is True
        assert response.request_id == "tt-req-1"

        request = route.calls.last.request
        assert request.headers["access-token"] == "tt-tok"
        payload = json.loads(request.content)
        assert payload["pixel_code"] == "pxc-1"
        (formatted,) = payload["event"]
        assert formatted["event"] == "CompletePayment"  # TikTok purchase name
        assert formatted["event_time"] == 1700000000
        assert formatted["user"]["email"] == sha256_of("jane@example.com")
        assert formatted["user"]["phone"] is None
        assert formatted["properties"]["value"] == 10.0
        assert formatted["page"]["url"] == "https://shop.example/done"

    async def test_send_events_business_error_code_fails(self):
        """TikTok signals errors via body code with HTTP 200."""
        connector = make_tiktok(connected=True)
        with respx.mock:
            route = respx.post(TIKTOK_TRACK_URL).mock(
                return_value=httpx.Response(
                    200, json={"code": 40001, "message": "Invalid pixel code"}
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors[0] == {"message": "Invalid pixel code", "code": 40001}
        # "invalid" in the error -> permanent, no retry
        assert route.call_count == 1

    async def test_send_events_retryable_error_retries(self):
        connector = make_tiktok(connected=True)
        with respx.mock:
            route = respx.post(TIKTOK_TRACK_URL).mock(
                return_value=httpx.Response(
                    200, json={"code": 50002, "message": "Rate limit exceeded"}
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert route.call_count == connector.MAX_RETRIES

    async def test_send_events_network_error(self):
        connector = make_tiktok(connected=True)
        with respx.mock:
            respx.post(TIKTOK_TRACK_URL).mock(
                side_effect=httpx.ConnectError("conn reset")
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert "conn reset" in response.errors[0]["message"]


# =============================================================================
# Snapchat connector
# =============================================================================

SNAP_PIXEL_URL = "https://adsapi.snapchat.com/v1/pixels/snap-pix"
SNAP_CONVERSION_URL = "https://tr.snapchat.com/v2/conversion"


def make_snapchat(connected: bool = False) -> SnapchatCAPIConnector:
    c = SnapchatCAPIConnector()
    c.pixel_id = "snap-pix"
    c.access_token = "snap-tok"
    c.RETRY_DELAYS = NO_DELAYS
    if connected:
        c._connected = True
    return c


class TestSnapchatConnect:
    async def test_connect_missing_credentials_errors(self):
        result = await SnapchatCAPIConnector().connect({"pixel_id": "snap-pix"})
        assert result.status == ConnectionStatus.ERROR

    async def test_connect_success_via_marketing_api(self):
        connector = SnapchatCAPIConnector()
        with respx.mock(assert_all_called=True) as router:
            route = router.get(SNAP_PIXEL_URL).mock(
                return_value=httpx.Response(200, json={"pixel": {}})
            )
            result = await connector.connect(
                {"pixel_id": "snap-pix", "access_token": "snap-tok"}
            )

        assert result.status == ConnectionStatus.CONNECTED
        assert result.message == "Successfully connected to Snapchat CAPI"
        headers = route.calls.last.request.headers
        assert headers["authorization"] == "Bearer snap-tok"

    async def test_test_connection_401_is_auth_error(self):
        connector = make_snapchat()
        with respx.mock:
            respx.get(SNAP_PIXEL_URL).mock(return_value=httpx.Response(401))
            result = await connector.test_connection()
        assert result.status == ConnectionStatus.ERROR
        assert "Authentication failed" in result.message

    async def test_test_connection_other_error_still_connects(self):
        connector = make_snapchat()
        with respx.mock:
            respx.get(SNAP_PIXEL_URL).mock(return_value=httpx.Response(500))
            result = await connector.test_connection()
        assert result.status == ConnectionStatus.CONNECTED
        assert result.message == "Credentials validated"

    async def test_test_connection_network_error_connects_offline(self):
        connector = make_snapchat()
        with respx.mock:
            respx.get(SNAP_PIXEL_URL).mock(side_effect=httpx.ConnectError("refused"))
            result = await connector.test_connection()
        assert result.status == ConnectionStatus.CONNECTED
        assert result.message == "Credentials validated (offline)"

    async def test_test_connection_unconfigured_is_disconnected(self):
        result = await SnapchatCAPIConnector().test_connection()
        assert result.status == ConnectionStatus.DISCONNECTED


class TestSnapchatSendEvents:
    async def test_send_events_payload_contract(self):
        connector = make_snapchat(connected=True)
        event = {
            "event_name": "purchase",
            "event_time": 1700000000,  # seconds -> converted to ms
            "user_data": {"email": "jane@example.com", "phone": "+15551234567"},
            "parameters": {"value": 25, "currency": "GBP"},
        }

        with respx.mock(assert_all_called=True) as router:
            route = router.post(SNAP_CONVERSION_URL).mock(
                return_value=httpx.Response(
                    200, json={"events_processed": 1, "request_id": "snap-req"}
                )
            )
            response = await connector.send_events([event])

        assert response.success is True
        assert response.events_processed == 1
        assert response.request_id == "snap-req"

        request = route.calls.last.request
        assert request.headers["authorization"] == "Bearer snap-tok"
        payload = json.loads(request.content)
        assert payload["pixel_id"] == "snap-pix"
        (formatted,) = payload["events"]
        assert formatted["event_type"] == "PURCHASE"
        assert formatted["event_time"] == 1700000000 * 1000
        assert formatted["hashed_email"] == sha256_of("jane@example.com")
        assert formatted["hashed_phone"] == sha256_of("15551234567")
        assert formatted["price"] == 25.0
        assert formatted["currency"] == "GBP"

    async def test_send_events_207_partial_success(self):
        connector = make_snapchat(connected=True)
        with respx.mock:
            respx.post(SNAP_CONVERSION_URL).mock(
                return_value=httpx.Response(
                    207,
                    json={"errors": [{"message": "row 1 bad"}], "request_id": "r"},
                )
            )
            response = await connector.send_events([{"event_name": "purchase"}] * 3)

        assert response.success is True
        assert response.events_received == 3
        assert response.events_processed == 2
        assert response.errors == [{"message": "row 1 bad"}]

    async def test_send_events_error_with_json_body(self):
        connector = make_snapchat(connected=True)
        with respx.mock:
            route = respx.post(SNAP_CONVERSION_URL).mock(
                return_value=httpx.Response(400, json={"message": "Invalid pixel_id"})
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors[0]["message"] == "Invalid pixel_id"
        assert response.errors[0]["status_code"] == 400
        assert route.call_count == 1  # "invalid" -> permanent

    async def test_send_events_error_with_non_json_body(self):
        """Snapchat's error branch tolerates malformed bodies (unlike 200s)."""
        connector = make_snapchat(connected=True)
        with respx.mock:
            respx.post(SNAP_CONVERSION_URL).mock(
                return_value=httpx.Response(503, content=b"Service Unavailable")
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert response.errors[0]["message"] == "HTTP 503"

    async def test_send_events_network_error(self):
        connector = make_snapchat(connected=True)
        with respx.mock:
            respx.post(SNAP_CONVERSION_URL).mock(
                side_effect=httpx.ConnectError("refused")
            )
            response = await connector.send_events([{"event_name": "purchase"}])

        assert response.success is False
        assert "refused" in response.errors[0]["message"]

    def test_format_event_time_handling(self):
        connector = make_snapchat()
        # Already in milliseconds -> passthrough
        formatted = connector._format_event(
            {"event_name": "purchase", "event_time": 1700000000000}
        )
        assert formatted["event_time"] == 1700000000000

        # Missing -> now in ms
        before_ms = int(time.time() * 1000)
        formatted = connector._format_event({"event_name": "purchase"})
        assert before_ms <= formatted["event_time"] <= int(time.time() * 1000) + 1000

        # Default event name -> CUSTOM_EVENT_1, default currency USD
        formatted = connector._format_event({})
        assert formatted["event_type"] == "CUSTOM_EVENT_1"
        assert formatted["currency"] == "USD"
        assert formatted["hashed_email"] is None


# =============================================================================
# WhatsApp connector
# =============================================================================

WA_PHONE_URL = "https://graph.facebook.com/v18.0/wa-num-1"
WA_MESSAGES_URL = "https://graph.facebook.com/v18.0/wa-num-1/messages"


def make_whatsapp(connected: bool = False) -> WhatsAppCAPIConnector:
    c = WhatsAppCAPIConnector()
    c.phone_number_id = "wa-num-1"
    c.access_token = "wa-tok"
    c.RETRY_DELAYS = NO_DELAYS
    if connected:
        c._connected = True
    return c


class TestWhatsAppConnector:
    async def test_connect_missing_credentials_errors(self):
        result = await WhatsAppCAPIConnector().connect({"phone_number_id": "wa-num-1"})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing phone_number_id or access_token" in result.message

    async def test_connect_success_returns_phone_details(self):
        connector = WhatsAppCAPIConnector()
        with respx.mock(assert_all_called=True) as router:
            route = router.get(WA_PHONE_URL).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "display_phone_number": "+1 555 000 1111",
                        "verified_name": "Stratum",
                    },
                )
            )
            result = await connector.connect(
                {"phone_number_id": "wa-num-1", "access_token": "wa-tok"}
            )

        assert result.status == ConnectionStatus.CONNECTED
        assert result.details == {
            "display_phone_number": "+1 555 000 1111",
            "verified_name": "Stratum",
        }
        assert "access_token=wa-tok" in str(route.calls.last.request.url)

    async def test_test_connection_api_error(self):
        connector = make_whatsapp()
        with respx.mock:
            respx.get(WA_PHONE_URL).mock(
                return_value=httpx.Response(
                    401, json={"error": {"message": "Bad token"}}
                )
            )
            result = await connector.test_connection()
        assert result.status == ConnectionStatus.ERROR
        assert result.message == "Bad token"

    async def test_test_connection_network_error(self):
        connector = make_whatsapp()
        with respx.mock:
            respx.get(WA_PHONE_URL).mock(side_effect=httpx.ConnectError("refused"))
            result = await connector.test_connection()
        assert result.status == ConnectionStatus.ERROR

    async def test_test_connection_unconfigured_is_disconnected(self):
        result = await WhatsAppCAPIConnector().test_connection()
        assert result.status == ConnectionStatus.DISCONNECTED

    async def test_send_events_template_message_contract(self):
        connector = make_whatsapp(connected=True)
        event = {
            "event_name": "order_shipped",
            "user_data": {"phone": "+1 555-000 2222"},
            "parameters": {
                "template_name": "order_update",
                "language": "ar",
                "components": [{"type": "body", "parameters": []}],
            },
        }

        with respx.mock(assert_all_called=True) as router:
            route = router.post(WA_MESSAGES_URL).mock(
                return_value=httpx.Response(200, json={"messages": [{"id": "m1"}]})
            )
            response = await connector.send_events([event])

        assert response.success is True
        assert response.events_processed == 1
        assert response.errors == []

        request = route.calls.last.request
        assert request.headers["authorization"] == "Bearer wa-tok"
        payload = json.loads(request.content)
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "15550002222"  # +, spaces, dashes stripped
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_update"
        assert payload["template"]["language"] == {"code": "ar"}
        assert payload["template"]["components"] == [{"type": "body", "parameters": []}]

    async def test_send_events_defaults_to_hello_world_template(self):
        connector = make_whatsapp(connected=True)
        with respx.mock:
            route = respx.post(WA_MESSAGES_URL).mock(
                return_value=httpx.Response(200, json={"messages": [{"id": "m1"}]})
            )
            await connector.send_events(
                [{"event_name": "ping", "user_data": {"ph": "15550003333"}}]
            )

        payload = json.loads(route.calls.last.request.content)
        assert payload["template"]["name"] == "hello_world"
        assert payload["template"]["language"] == {"code": "en"}
        assert "components" not in payload["template"]

    async def test_send_events_missing_phone_is_counted_as_error(self):
        connector = make_whatsapp(connected=True)
        with respx.mock(assert_all_called=False):
            response = await connector.send_events(
                [{"event_name": "no_phone", "user_data": {}}]
            )

        assert response.success is False
        assert response.events_processed == 0
        assert "Failed to send event: no_phone" in response.errors[0]["message"]

    async def test_send_events_partial_batch_retries_and_zeroes_processed(self):
        """PINNED BEHAVIOR: a partially-failing WhatsApp batch is retried
        wholesale (the already-delivered message is re-sent on every retry)
        and the final synthesized response reports events_processed=0 even
        though one message was delivered — the retry-exhausted branch of
        ``send_events`` hardcodes processed=0 and keeps only last_error."""
        connector = make_whatsapp(connected=True)
        with respx.mock:
            route = respx.post(WA_MESSAGES_URL).mock(
                return_value=httpx.Response(200, json={"messages": [{"id": "m1"}]})
            )
            response = await connector.send_events(
                [
                    {"event_name": "ok", "user_data": {"phone": "15550004444"}},
                    {"event_name": "bad", "user_data": {}},
                ]
            )

        assert response.success is False
        assert response.events_received == 2
        assert response.events_processed == 0  # delivered message not counted
        assert response.errors == [{"message": "Failed to send event: bad"}]
        # The deliverable message was sent MAX_RETRIES times (duplicates!)
        assert route.call_count == connector.MAX_RETRIES

    async def test_send_message_api_error_returns_false(self):
        connector = make_whatsapp(connected=True)
        with respx.mock:
            route = respx.post(WA_MESSAGES_URL).mock(
                return_value=httpx.Response(
                    400, json={"error": {"message": "invalid template"}}
                )
            )
            response = await connector.send_events(
                [{"event_name": "evt", "user_data": {"phone": "15550005555"}}]
            )

        assert response.success is False
        # "invalid" not in the *reported* message, so all retries are used
        assert "Failed to send event: evt" in response.errors[0]["message"]
        assert route.call_count == connector.MAX_RETRIES

    async def test_send_message_network_error_returns_false(self):
        connector = make_whatsapp(connected=True)
        with respx.mock:
            respx.post(WA_MESSAGES_URL).mock(side_effect=httpx.ConnectError("refused"))
            response = await connector.send_events(
                [{"event_name": "evt", "user_data": {"phone": "15550006666"}}]
            )

        assert response.success is False
        assert response.events_processed == 0

    async def test_send_events_impl_catches_send_message_transport_error(self):
        """A transport error raised by _send_message (not returned as False)
        is recorded per-event in the impl's error list."""
        connector = make_whatsapp(connected=True)

        async def boom(event):
            raise TimeoutError("wa timeout")

        connector._send_message = boom
        response = await connector._send_events_impl(
            [{"event_name": "evt", "user_data": {"phone": "15550007777"}}]
        )

        assert response.success is False
        assert response.events_processed == 0
        assert response.errors == [{"message": "wa timeout"}]

    def test_format_event_passthrough(self):
        connector = make_whatsapp()
        formatted = connector._format_event(
            {
                "event_name": "evt",
                "event_time": 123,
                "user_data": {"phone": "1"},
                "parameters": {"a": 1},
            }
        )
        assert formatted == {
            "event_name": "evt",
            "event_time": 123,
            "user_data": {"phone": "1"},
            "parameters": {"a": 1},
        }


# =============================================================================
# Event delivery log helpers
# =============================================================================


class TestEventDeliveryLogHelpers:
    def _log(self, platform: str, when: datetime) -> EventDeliveryLog:
        return EventDeliveryLog(
            event_id="e",
            platform=platform,
            event_name="purchase",
            timestamp=when,
            success=True,
            latency_ms=10.0,
        )

    def test_filters_by_platform_and_since(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=3)
        log_event_delivery(self._log("filter-test-a", old))
        log_event_delivery(self._log("filter-test-a", now))
        log_event_delivery(self._log("filter-test-b", now))

        platform_logs = get_event_delivery_logs(platform="filter-test-a")
        assert len(platform_logs) == 2

        recent = get_event_delivery_logs(
            platform="filter-test-a", since=now - timedelta(hours=1)
        )
        assert len(recent) == 1
        assert recent[0].timestamp == now

    def test_log_buffer_trimmed_to_last_10000(self, monkeypatch):
        import app.services.capi.platform_connectors as mod

        now = datetime.now(timezone.utc)
        filler = [self._log("trim-filler", now) for _ in range(10000)]
        monkeypatch.setattr(mod, "_event_delivery_logs", filler)

        log_event_delivery(self._log("trim-newest", now))

        assert len(mod._event_delivery_logs) == 10000
        # Oldest entry dropped, newest retained
        assert mod._event_delivery_logs[-1].platform == "trim-newest"


# =============================================================================
# ConnectionPool
# =============================================================================


class TestConnectionPool:
    async def test_get_client_prewarms_and_round_robins(self):
        pool = ConnectionPool(max_connections=10)
        try:
            c1 = await pool.get_client("meta")
            assert len(pool._clients["meta"]) == 3  # pre-warmed
            c2 = await pool.get_client("meta")
            c3 = await pool.get_client("meta")
            c4 = await pool.get_client("meta")
            assert c1 is not c2
            assert c2 is not c3
            assert c4 is c1  # wrapped around

            stats = pool.get_pool_stats()
            assert stats == {"meta": {"connections": 3, "max_connections": 10}}
        finally:
            await pool.close_all()

    async def test_scale_up_respects_max_connections(self):
        pool = ConnectionPool(max_connections=4)
        try:
            await pool.get_client("meta")  # 3 clients
            await pool.scale_up("meta")
            assert len(pool._clients["meta"]) == 4
            await pool.scale_up("meta")  # at max -> no-op
            assert len(pool._clients["meta"]) == 4
        finally:
            await pool.close_all()

    async def test_scale_down_stops_at_one_client(self):
        pool = ConnectionPool(max_connections=4)
        try:
            await pool.get_client("tiktok")  # 3 clients
            await pool.scale_down("tiktok")
            assert len(pool._clients["tiktok"]) == 2
            await pool.scale_down("tiktok")
            assert len(pool._clients["tiktok"]) == 1
            await pool.scale_down("tiktok")  # never below 1
            assert len(pool._clients["tiktok"]) == 1
        finally:
            await pool.close_all()

    async def test_close_all_clears_pool(self):
        pool = ConnectionPool()
        await pool.get_client("meta")
        await pool.get_client("google")
        await pool.close_all()
        assert pool.get_pool_stats() == {}
        assert pool._client_index == {}

    async def test_scale_up_before_get_client_breaks_pool(self):
        """PINNED BUG (do not fix here): scale_up on an unseen platform
        creates the client list but never seeds _client_index, so the next
        get_client raises KeyError instead of returning a client."""
        pool = ConnectionPool(max_connections=4)
        try:
            await pool.scale_up("snapchat")
            assert len(pool._clients["snapchat"]) == 1
            with pytest.raises(KeyError):
                await pool.get_client("snapchat")
        finally:
            await pool.close_all()


# =============================================================================
# EventDeduplicator
# =============================================================================


class TestEventDeduplicator:
    def test_event_id_key_includes_platform(self):
        dedup = EventDeduplicator()
        key = dedup._generate_key({"platform": "meta", "event_id": "abc"})
        assert key == "meta:abc"

    def test_content_key_is_md5_and_deterministic(self):
        dedup = EventDeduplicator()
        event = {
            "event_name": "purchase",
            "event_time": 1700000000,
            "user_data": {"em": "h1", "ph": "h2"},
            "parameters": {"value": 10},
        }
        key1 = dedup._generate_key(event)
        key2 = dedup._generate_key(dict(event))
        assert key1 == key2
        assert (
            key1
            == hashlib.md5(
                b"purchase|1700000000|h1|h2|10", usedforsecurity=False
            ).hexdigest()
        )

    def test_first_seen_then_duplicate(self):
        dedup = EventDeduplicator()
        event = {"event_id": "dup-1", "platform": "meta"}
        assert dedup.is_duplicate(event) is False
        assert dedup.is_duplicate(event) is True

    def test_distinct_events_are_not_duplicates(self):
        dedup = EventDeduplicator()
        assert dedup.is_duplicate({"event_id": "a", "platform": "meta"}) is False
        assert dedup.is_duplicate({"event_id": "a", "platform": "tiktok"}) is False
        assert dedup.is_duplicate({"event_name": "purchase"}) is False

    def test_expired_entries_are_cleaned_up(self):
        dedup = EventDeduplicator(ttl_hours=1)
        event = {"event_id": "ttl-1", "platform": "meta"}
        assert dedup.is_duplicate(event) is False

        # Age the entry beyond the TTL
        for key in list(dedup._seen_events):
            dedup._seen_events[key] = datetime.now(timezone.utc) - timedelta(hours=2)

        assert dedup.is_duplicate(event) is False  # expired -> fresh again
        assert dedup.is_duplicate(event) is True

    def test_max_size_evicts_oldest(self):
        dedup = EventDeduplicator(ttl_hours=24, max_size=3)
        for i in range(5):
            assert dedup.is_duplicate({"event_id": f"ev-{i}", "platform": "m"}) is False

        # Oldest entry (ev-0) was evicted during the size-cap sweep, so it is
        # no longer considered a duplicate.
        assert dedup.is_duplicate({"event_id": "ev-0", "platform": "m"}) is False
        # The most recent entry is still tracked.
        assert dedup.is_duplicate({"event_id": "ev-4", "platform": "m"}) is True

    def test_get_stats_shape(self):
        dedup = EventDeduplicator(ttl_hours=12, max_size=50)
        dedup.is_duplicate({"event_id": "s-1", "platform": "meta"})
        stats = dedup.get_stats()
        assert stats == {"tracked_events": 1, "max_size": 50, "ttl_hours": 12.0}
