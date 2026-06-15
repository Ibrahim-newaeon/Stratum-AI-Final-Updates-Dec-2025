# =============================================================================
# Stratum AI - API Keys Endpoint Integration Tests
# =============================================================================
"""Integration tests for the ``/api-keys`` CRUD endpoints.

All routes are superadmin-gated and read ``request.state.user_id`` /
``tenant_id``; the superadmin JWT carries the role + subject and the
TenantMiddleware accepts an ``X-Tenant-ID`` header for a superadmin caller,
so requests run against the superadmin's own tenant.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/api-keys"


def _headers(superadmin_user) -> dict:
    from app.core.security import create_access_token

    token = create_access_token(
        subject=superadmin_user["id"],
        additional_claims={
            "email": superadmin_user["email"],
            "role": superadmin_user["role"],
            "tenant_id": superadmin_user["tenant_id"],
        },
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(superadmin_user["tenant_id"]),
    }


class TestAuth:
    async def test_requires_authentication(self, client):
        resp = await client.get(_BASE)
        assert resp.status_code == 401

    async def test_non_superadmin_forbidden(self, authenticated_client):
        # authenticated_client is an ADMIN, not a superadmin.
        resp = await authenticated_client.get(_BASE)
        assert resp.status_code == 403


class TestCrud:
    async def test_create_then_list(self, client, superadmin_user):
        headers = _headers(superadmin_user)

        created = await client.post(
            _BASE, json={"name": "CI Key", "scopes": ["read"]}, headers=headers
        )
        assert created.status_code == 201, created.text
        body = created.json()["data"]
        assert body["name"] == "CI Key"
        # Full key is returned exactly once and starts with the live prefix.
        assert body["key"].startswith("strat_live_")
        key_id = body["id"]

        listed = await client.get(_BASE, headers=headers)
        assert listed.status_code == 200
        items = listed.json()["data"]
        assert any(k["id"] == key_id for k in items)
        # Listing never exposes the raw key — only a masked prefix.
        match = next(k for k in items if k["id"] == key_id)
        assert "•" in match["masked_key"]
        assert match["is_active"] is True

    async def test_create_with_expiry(self, client, superadmin_user):
        headers = _headers(superadmin_user)
        resp = await client.post(
            _BASE,
            json={"name": "Expiring", "scopes": ["read"], "expires_in_days": 30},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["expires_at"] is not None

    async def test_regenerate_changes_key(self, client, superadmin_user):
        headers = _headers(superadmin_user)
        created = await client.post(_BASE, json={"name": "Rotate"}, headers=headers)
        key_id = created.json()["data"]["id"]
        original = created.json()["data"]["key"]

        regen = await client.post(f"{_BASE}/{key_id}/regenerate", headers=headers)
        assert regen.status_code == 200
        assert regen.json()["data"]["key"] != original

    async def test_deactivate(self, client, superadmin_user):
        headers = _headers(superadmin_user)
        created = await client.post(
            _BASE, json={"name": "Deactivate me"}, headers=headers
        )
        key_id = created.json()["data"]["id"]

        resp = await client.patch(f"{_BASE}/{key_id}/deactivate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False

    async def test_delete(self, client, superadmin_user):
        headers = _headers(superadmin_user)
        created = await client.post(_BASE, json={"name": "Delete me"}, headers=headers)
        key_id = created.json()["data"]["id"]

        resp = await client.delete(f"{_BASE}/{key_id}", headers=headers)
        assert resp.status_code == 204

        # A second delete now 404s.
        again = await client.delete(f"{_BASE}/{key_id}", headers=headers)
        assert again.status_code == 404

    async def test_regenerate_missing_key_404(self, client, superadmin_user):
        headers = _headers(superadmin_user)
        resp = await client.post(f"{_BASE}/99999999/regenerate", headers=headers)
        assert resp.status_code == 404
