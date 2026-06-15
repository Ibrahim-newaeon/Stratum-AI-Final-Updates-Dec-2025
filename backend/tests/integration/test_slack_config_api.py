# =============================================================================
# Stratum AI - Slack Integration Config Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed Slack-integration config CRUD under
``/slack`` (get / configure-upsert / toggle / disconnect). The ``/test`` and
``/notify`` routes call the Slack webhook and are out of scope here.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/slack"
_HOOK = "https://hooks.slack.com/services/T000/B000/xxxxxxxx"


def _payload(**overrides) -> dict:
    body = {
        "webhook_url": _HOOK,
        "channel_name": "#alerts",
        "notify_trust_gate": True,
        "notify_anomalies": True,
        "notify_signal_health": False,
        "notify_daily_summary": False,
    }
    body.update(overrides)
    return body


class TestAuth:
    async def test_get_requires_auth(self, client):
        resp = await client.get(_BASE)
        assert resp.status_code == 401


class TestConfig:
    async def test_get_when_unconfigured_is_null(self, authenticated_client):
        resp = await authenticated_client.get(_BASE)
        assert resp.status_code == 200
        assert resp.json()["data"] is None

    async def test_configure_then_get_masks_webhook(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        assert created.status_code == 200, created.text
        data = created.json()["data"]
        assert data["channel_name"] == "#alerts"
        assert data["is_active"] is True
        # The raw webhook URL is never echoed back — only a masked form.
        assert data["webhook_url_masked"] != _HOOK

        got = await authenticated_client.get(_BASE)
        assert got.json()["data"]["channel_name"] == "#alerts"

    async def test_configure_rejects_non_slack_url(self, authenticated_client):
        resp = await authenticated_client.post(
            _BASE, json=_payload(webhook_url="https://evil.example.com/hook")
        )
        assert resp.status_code == 400

    async def test_configure_upserts(self, authenticated_client):
        await authenticated_client.post(_BASE, json=_payload(channel_name="#first"))
        # Second POST updates the same tenant row rather than creating a new one.
        resp = await authenticated_client.post(
            _BASE, json=_payload(channel_name="#second")
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["channel_name"] == "#second"

    async def test_toggle_active(self, authenticated_client):
        await authenticated_client.post(_BASE, json=_payload())
        resp = await authenticated_client.patch(
            f"{_BASE}/toggle", params={"is_active": False}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False

    async def test_toggle_without_config_404(self, authenticated_client):
        resp = await authenticated_client.patch(
            f"{_BASE}/toggle", params={"is_active": True}
        )
        assert resp.status_code == 404

    async def test_disconnect_then_404(self, authenticated_client):
        await authenticated_client.post(_BASE, json=_payload())

        deleted = await authenticated_client.delete(_BASE)
        assert deleted.status_code == 204

        # Config is gone; GET reports null and a second disconnect 404s.
        assert (await authenticated_client.get(_BASE)).json()["data"] is None
        again = await authenticated_client.delete(_BASE)
        assert again.status_code == 404
