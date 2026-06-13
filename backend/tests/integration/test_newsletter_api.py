# =============================================================================
# Stratum AI - Newsletter API Integration Tests
# =============================================================================
"""Integration tests for the newsletter API.

Exercises the real ASGI app against Postgres + Redis: template CRUD,
campaign CRUD (draft lifecycle), duplicate, listing, validation, 404s,
and auth. The send / schedule / send-test routes dispatch real email, so
they are left to service-level tests.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = 99999999


# =============================================================================
# Templates
# =============================================================================
def _template(name="Monthly Digest", **extra):
    body = {"name": name, "subject": "Hello", "content_html": "<p>Hi</p>"}
    body.update(extra)
    return body


async def _make_template(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/newsletter/templates", json=_template(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestTemplates:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/newsletter/templates", json=_template())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_and_list(self, authenticated_client: AsyncClient):
        await _make_template(authenticated_client, name="Tmpl One")
        await _make_template(authenticated_client, name="Tmpl Two")
        resp = await authenticated_client.get("/api/v1/newsletter/templates")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()}
        assert {"Tmpl One", "Tmpl Two"} <= names

    @pytest.mark.asyncio
    async def test_missing_name_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/newsletter/templates", json={"subject": "No name"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update(self, authenticated_client: AsyncClient):
        created = await _make_template(authenticated_client, name="Before")
        resp = await authenticated_client.put(
            f"/api/v1/newsletter/templates/{created['id']}",
            json={"name": "After"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.put(
            f"/api/v1/newsletter/templates/{_MISSING}", json={"name": "Nope"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete(self, authenticated_client: AsyncClient):
        created = await _make_template(authenticated_client, name="Doomed Tmpl")
        resp = await authenticated_client.delete(
            f"/api/v1/newsletter/templates/{created['id']}"
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# =============================================================================
# Campaigns
# =============================================================================
def _campaign(name="Spring Sale", **extra):
    body = {"name": name, "subject": "Big news", "content_html": "<p>Sale</p>"}
    body.update(extra)
    return body


async def _make_campaign(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/newsletter/campaigns", json=_campaign(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestCampaigns:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/newsletter/campaigns", json=_campaign())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_draft(self, authenticated_client: AsyncClient):
        data = await _make_campaign(authenticated_client, name="Launch")
        assert data["name"] == "Launch"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_missing_subject_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/newsletter/campaigns", json={"name": "No subject"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_envelope(self, authenticated_client: AsyncClient):
        await _make_campaign(authenticated_client, name="C One")
        await _make_campaign(authenticated_client, name="C Two")
        resp = await authenticated_client.get("/api/v1/newsletter/campaigns")
        assert resp.status_code == 200
        body = resp.json()
        names = {c["name"] for c in body["campaigns"]}
        assert {"C One", "C Two"} <= names
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _make_campaign(authenticated_client, name="Detail C")
        resp = await authenticated_client.get(
            f"/api/v1/newsletter/campaigns/{created['id']}"
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail C"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/newsletter/campaigns/{_MISSING}"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_draft(self, authenticated_client: AsyncClient):
        created = await _make_campaign(authenticated_client, name="Before")
        resp = await authenticated_client.put(
            f"/api/v1/newsletter/campaigns/{created['id']}",
            json={"name": "After"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    @pytest.mark.asyncio
    async def test_duplicate(self, authenticated_client: AsyncClient):
        created = await _make_campaign(authenticated_client, name="Source C")
        resp = await authenticated_client.post(
            f"/api/v1/newsletter/campaigns/{created['id']}/duplicate"
        )
        assert resp.status_code in {200, 201}
        clone = resp.json()
        assert clone["id"] != created["id"]
        assert clone["status"] == "draft"

    @pytest.mark.asyncio
    async def test_delete_draft(self, authenticated_client: AsyncClient):
        created = await _make_campaign(authenticated_client, name="Doomed C")
        cid = created["id"]
        deleted = await authenticated_client.delete(
            f"/api/v1/newsletter/campaigns/{cid}"
        )
        assert deleted.status_code == 200
        gone = await authenticated_client.get(f"/api/v1/newsletter/campaigns/{cid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            f"/api/v1/newsletter/campaigns/{_MISSING}"
        )
        assert resp.status_code == 404
