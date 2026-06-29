# =============================================================================
# Stratum AI - Embed Widgets Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed ``/embed-widgets/widgets`` CRUD
surface (now backed by an async EmbedWidgetService). Token issuance, which
needs EMBED_SIGNING_KEY, is out of scope here.
"""

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/embed-widgets/widgets"


def _payload(**overrides) -> dict:
    body = {"name": "Signal Health Widget", "widget_type": "signal_health"}
    body.update(overrides)
    return body


class TestAuth:
    async def test_create_requires_tenant(self, client):
        resp = await client.post(_BASE, json=_payload())
        assert resp.status_code == 401


class TestCrud:
    async def test_create_then_get(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["name"] == "Signal Health Widget"
        assert body["widget_type"] == "signal_health"
        widget_id = body["id"]

        got = await authenticated_client.get(f"{_BASE}/{widget_id}")
        assert got.status_code == 200
        assert got.json()["id"] == widget_id

    async def test_list_includes_created(self, authenticated_client):
        created = await authenticated_client.post(
            _BASE, json=_payload(name="Listed Widget")
        )
        widget_id = created.json()["id"]

        listed = await authenticated_client.get(_BASE)
        assert listed.status_code == 200
        assert any(w["id"] == widget_id for w in listed.json())

    async def test_list_filter_by_type(self, authenticated_client):
        await authenticated_client.post(
            _BASE, json=_payload(widget_type="roas_display")
        )
        resp = await authenticated_client.get(
            _BASE, params={"widget_type": "roas_display"}
        )
        assert resp.status_code == 200
        assert all(w["widget_type"] == "roas_display" for w in resp.json())

    async def test_update(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        widget_id = created.json()["id"]

        resp = await authenticated_client.patch(
            f"{_BASE}/{widget_id}", json={"name": "Renamed Widget"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Widget"

    async def test_delete_then_404(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        widget_id = created.json()["id"]

        deleted = await authenticated_client.delete(f"{_BASE}/{widget_id}")
        assert deleted.status_code == 204

        gone = await authenticated_client.get(f"{_BASE}/{widget_id}")
        assert gone.status_code == 404

    async def test_get_missing_404(self, authenticated_client):
        resp = await authenticated_client.get(f"{_BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestValidation:
    async def test_invalid_widget_type_422(self, authenticated_client):
        resp = await authenticated_client.post(
            _BASE, json=_payload(widget_type="not_a_widget")
        )
        assert resp.status_code == 422
