# =============================================================================
# Stratum AI - Clients API Integration Tests
# =============================================================================
"""Integration tests for the client-management CRUD API.

Exercises the real ASGI app against Postgres + Redis: client creation
(201), duplicate-slug conflict (409), tenant-scoped listing, detail
(200/404), and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _payload(slug="acme", name="Acme Corp", **extra):
    body = {"name": name, "slug": slug}
    body.update(extra)
    return body


# =============================================================================
# Create
# =============================================================================
class TestCreateClient:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/clients", json=_payload())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/clients",
            json=_payload(slug="acme", name="Acme Corp", currency="USD"),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Acme Corp"
        assert data["slug"] == "acme"

    @pytest.mark.asyncio
    async def test_duplicate_slug_conflict(self, authenticated_client: AsyncClient):
        first = await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="dup", name="First")
        )
        assert first.status_code == 201
        second = await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="dup", name="Second")
        )
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_payload_rejected(self, authenticated_client: AsyncClient):
        # slug must match ^[a-z0-9-]+$ (schema validator)
        resp = await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="Has Spaces")
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created_clients(
        self, authenticated_client: AsyncClient
    ):
        await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="one", name="One")
        )
        await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="two", name="Two")
        )
        resp = await authenticated_client.get("/api/v1/clients")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert {c["name"] for c in items} >= {"One", "Two"}

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/clients", json=_payload(slug="detail", name="Detail Co")
        )
        client_id = created.json()["data"]["id"]
        resp = await authenticated_client.get(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["slug"] == "detail"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/clients/999999")
        assert resp.status_code == 404
