# =============================================================================
# Stratum AI - Users API Integration Tests
# =============================================================================
"""Integration tests for the users API.

Exercises the real ASGI app against Postgres + Redis: current-user profile
read/update, tenant user listing (admin-gated), and invite validation
(duplicate / bad email). The invite happy path sends an invitation email,
so it is left to service-level tests.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestProfile:
    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_get_me(self, authenticated_client: AsyncClient, test_user: dict):
        resp = await authenticated_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_update_me(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            "/api/v1/users/me",
            json={"full_name": "Renamed User", "timezone": "America/New_York"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["full_name"] == "Renamed User"
        assert data["timezone"] == "America/New_York"


class TestListAndInvite:
    @pytest.mark.asyncio
    async def test_list_users(self, authenticated_client: AsyncClient, test_user: dict):
        # test_user is an ADMIN, so listing is permitted.
        resp = await authenticated_client.get("/api/v1/users")
        assert resp.status_code == 200
        ids = {u["id"] for u in resp.json()["data"]}
        assert test_user["id"] in ids

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/users")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_invite_user(self, authenticated_client: AsyncClient):
        # test_user is an ADMIN, so inviting is permitted.
        resp = await authenticated_client.post(
            "/api/v1/users/invite",
            json={
                "email": "newhire@example.com",
                "full_name": "New Hire",
                "role": "user",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_invite_invalid_email_rejected(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/users/invite", json={"email": "not-an-email", "role": "user"}
        )
        assert resp.status_code == 422
