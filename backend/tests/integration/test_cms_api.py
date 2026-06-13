# =============================================================================
# Stratum AI - CMS Admin API Integration Tests
# =============================================================================
"""Integration tests for the CMS admin API.

Exercises the real ASGI app against Postgres + Redis: admin post CRUD and
category create/list, gated by the CMS role-permission system. A
``cms_client`` fixture issues a token carrying a ``cms_role`` claim so the
``check_cms_permission`` gate passes; a plain admin (no ``cms_role``) is
rejected with 403.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


@pytest_asyncio.fixture
async def cms_client(client, test_user, test_tenant) -> AsyncClient:
    """An authenticated client whose JWT carries a CMS super_admin role."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=test_user["id"],
        additional_claims={
            "email": test_user["email"],
            "tenant_id": test_tenant["id"],
            "role": test_user["role"],
            "cms_role": "super_admin",
        },
    )
    client.headers["Authorization"] = f"Bearer {token}"
    client.headers["X-Tenant-ID"] = str(test_tenant["id"])
    return client


def _post(title="Launch announcement", **extra):
    body = {"title": title, "content": "<p>Big news.</p>", "status": "draft"}
    body.update(extra)
    return body


async def _create_post(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cms/admin/posts", json=_post(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# =============================================================================
# Posts
# =============================================================================
class TestAdminPosts:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cms/admin/posts", json=_post())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_requires_cms_permission(self, authenticated_client: AsyncClient):
        # Plain ADMIN without a cms_role claim is rejected by the CMS gate.
        resp = await authenticated_client.post("/api/v1/cms/admin/posts", json=_post())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_post(self, cms_client: AsyncClient):
        data = await _create_post(cms_client, title="Hello CMS")
        assert data["title"] == "Hello CMS"
        assert data["slug"]

    @pytest.mark.asyncio
    async def test_create_generates_unique_slug(self, cms_client: AsyncClient):
        a = await _create_post(cms_client, title="Same Title")
        b = await _create_post(cms_client, title="Same Title")
        assert a["slug"] != b["slug"]

    @pytest.mark.asyncio
    async def test_list_posts(self, cms_client: AsyncClient):
        await _create_post(cms_client, title="Listed Post")
        resp = await cms_client.get("/api/v1/cms/admin/posts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, cms_client: AsyncClient):
        created = await _create_post(cms_client, title="Detail Post")
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Detail Post"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_post(self, cms_client: AsyncClient):
        created = await _create_post(cms_client, title="Doomed Post")
        resp = await cms_client.delete(f"/api/v1/cms/admin/posts/{created['id']}")
        assert resp.status_code in {200, 204}


# =============================================================================
# Categories
# =============================================================================
class TestAdminCategories:
    @pytest.mark.asyncio
    async def test_create_category(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/categories", json={"name": "Product Updates"}
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Product Updates"

    @pytest.mark.asyncio
    async def test_create_category_invalid_color(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/categories",
            json={"name": "Bad Color", "color": "notahex"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_categories(self, cms_client: AsyncClient):
        await cms_client.post(
            "/api/v1/cms/admin/categories", json={"name": "Listed Cat"}
        )
        resp = await cms_client.get("/api/v1/cms/admin/categories")
        assert resp.status_code == 200
