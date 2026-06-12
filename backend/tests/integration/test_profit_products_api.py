# =============================================================================
# Stratum AI - Profit / Products API Integration Tests
# =============================================================================
"""Integration tests for the profit/products catalog API.

Exercises the real ASGI app against Postgres + Redis: product creation,
listing, detail (200/404), COGS-coverage reporting, and auth enforcement.
Relies on the get_db dependency override (added in the pacing batch) so
these get_db-based endpoints share the test savepoint session.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _product(sku="SKU-1", name="Widget", **extra):
    body = {"sku": sku, "name": name}
    body.update(extra)
    return body


# =============================================================================
# Create
# =============================================================================
class TestCreateProduct:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/profit/products", json=_product())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/profit/products", json=_product(sku="SKU-A", name="Alpha Widget")
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["product"]["sku"] == "SKU-A"

    @pytest.mark.asyncio
    async def test_missing_required_field(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/profit/products", json={"name": "No SKU"}
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail + coverage
# =============================================================================
class TestListDetailCoverage:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/profit/products", json=_product(sku="L1", name="One")
        )
        await authenticated_client.post(
            "/api/v1/profit/products", json=_product(sku="L2", name="Two")
        )
        resp = await authenticated_client.get("/api/v1/profit/products")
        assert resp.status_code == 200
        body = resp.json()
        skus = {p["sku"] for p in body.get("products", body.get("data", []))}
        assert {"L1", "L2"} <= skus

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/profit/products", json=_product(sku="D1", name="Detail")
        )
        product_id = created.json()["product"]["id"]
        resp = await authenticated_client.get(f"/api/v1/profit/products/{product_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/profit/products/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_coverage_endpoint(self, authenticated_client: AsyncClient):
        # COGS-coverage report should respond for a tenant (even with no products)
        resp = await authenticated_client.get("/api/v1/profit/products/coverage")
        assert resp.status_code == 200
