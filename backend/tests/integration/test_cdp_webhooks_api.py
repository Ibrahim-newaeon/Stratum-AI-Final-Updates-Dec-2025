# =============================================================================
# Stratum AI - CDP Webhooks API Integration Tests
# =============================================================================
"""Integration tests for the CDP webhook-destinations API.

Exercises the real ASGI app against Postgres + Redis: webhook creation
(with one-time secret_key return), listing, detail (200/404), update,
delete (204/404), validation (non-HTTPS URL, bad event type), and auth.

The ``/test`` route performs an outbound HTTP request to the webhook
URL, so it is exercised with ``httpx.AsyncClient`` mocked (no network).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


def _webhook(name="Profile sink", url="https://example.com/hook", **extra):
    body = {"name": name, "url": url, "event_types": ["profile.created"]}
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cdp/webhooks", json=_webhook(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()


# =============================================================================
# Create
# =============================================================================
class TestCreateWebhook:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cdp/webhooks", json=_webhook())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_returns_secret_once(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="Created hook")
        assert data["name"] == "Created hook"
        assert data["event_types"] == ["profile.created"]
        # secret_key is returned only on creation, for HMAC validation.
        assert data.get("secret_key")

    @pytest.mark.asyncio
    async def test_non_https_url_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/webhooks", json=_webhook(url="ftp://example.com/hook")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_event_type_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/webhooks", json=_webhook(event_types=["not.an.event"])
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Hook A")
        await _create(authenticated_client, name="Hook B")
        resp = await authenticated_client.get("/api/v1/cdp/webhooks")
        assert resp.status_code == 200
        body = resp.json()
        names = {w["name"] for w in body["webhooks"]}
        assert {"Hook A", "Hook B"} <= names
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_omits_secret(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Secretive")
        resp = await authenticated_client.get("/api/v1/cdp/webhooks")
        # secret_key must never appear in list responses.
        assert all(w.get("secret_key") is None for w in resp.json()["webhooks"])

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail hook")
        resp = await authenticated_client.get(f"/api/v1/cdp/webhooks/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail hook"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/cdp/webhooks/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Update + delete
# =============================================================================
class TestMutations:
    @pytest.mark.asyncio
    async def test_update_fields(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/webhooks/{created['id']}",
            json={"name": "After", "timeout_seconds": 60},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "After"
        assert body["timeout_seconds"] == 60

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/webhooks/{_MISSING}", json={"name": "Nope"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed hook")
        wid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/cdp/webhooks/{wid}")
        assert deleted.status_code == 204
        gone = await authenticated_client.get(f"/api/v1/cdp/webhooks/{wid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/cdp/webhooks/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Secret rotation (issue #342 batch 2)
# =============================================================================
class TestRotateSecret:
    @pytest.mark.asyncio
    async def test_rotate_returns_new_secret(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Rotating hook")
        old_secret = created["secret_key"]

        resp = await authenticated_client.post(
            f"/api/v1/cdp/webhooks/{created['id']}/rotate-secret"
        )

        assert resp.status_code == 200
        new_secret = resp.json()["secret_key"]
        assert new_secret
        assert new_secret != old_secret

    @pytest.mark.asyncio
    async def test_rotate_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"/api/v1/cdp/webhooks/{_MISSING}/rotate-secret"
        )
        assert resp.status_code == 404


# =============================================================================
# Webhook /test endpoint (outbound HTTP mocked -- no network)
# =============================================================================
class TestWebhookTestEndpoint:
    @pytest.mark.asyncio
    async def test_test_webhook_success(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Testable hook")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = mock_cls.return_value.__aenter__.return_value
            mock_http.post = AsyncMock(return_value=MagicMock(status_code=200))

            resp = await authenticated_client.post(
                f"/api/v1/cdp/webhooks/{created['id']}/test"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["status_code"] == 200
        assert body["error"] is None
        # Signature headers were sent to the destination
        _, kwargs = mock_http.post.call_args
        assert kwargs["headers"]["X-Stratum-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_test_webhook_non_2xx_reported(
        self, authenticated_client: AsyncClient
    ):
        created = await _create(authenticated_client, name="Failing hook")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = mock_cls.return_value.__aenter__.return_value
            mock_http.post = AsyncMock(return_value=MagicMock(status_code=500))

            resp = await authenticated_client.post(
                f"/api/v1/cdp/webhooks/{created['id']}/test"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"] == "HTTP 500"

    @pytest.mark.asyncio
    async def test_test_webhook_timeout(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Timeout hook")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = mock_cls.return_value.__aenter__.return_value
            mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

            resp = await authenticated_client.post(
                f"/api/v1/cdp/webhooks/{created['id']}/test"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["status_code"] is None
        assert "timed out" in body["error"]

    @pytest.mark.asyncio
    async def test_test_webhook_connection_error(
        self, authenticated_client: AsyncClient
    ):
        created = await _create(authenticated_client, name="Unreachable hook")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = mock_cls.return_value.__aenter__.return_value
            mock_http.post = AsyncMock(side_effect=ConnectionError("refused"))

            resp = await authenticated_client.post(
                f"/api/v1/cdp/webhooks/{created['id']}/test"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"] == "refused"

    @pytest.mark.asyncio
    async def test_test_webhook_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"/api/v1/cdp/webhooks/{_MISSING}/test")
        assert resp.status_code == 404
