# =============================================================================
# Stratum AI - Profit / COGS Endpoint Integration Tests
# =============================================================================
"""Integration tests for the profit surface under ``/api/v1/profit/...``:
product-catalog CRUD, COGS coverage, and profit-ROAS reads.

These endpoints depend on ``app.tenancy.deps.get_db`` (overridden by the harness
alongside ``get_async_session``), so they share the test's savepoint-scoped
session and tenant. The profit tables are created via ``create_all``.

With no orders/spend seeded, the profit-ROAS math runs against an empty series
and returns a graceful envelope — that's the contract these reads pin.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

from datetime import date

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/profit"


def _product_payload(**overrides) -> dict:
    payload = {
        "sku": "SKU-001",
        "name": "Test Widget",
        "category": "widgets",
        "brand": "acme",
        "base_price": 49.99,
    }
    payload.update(overrides)
    return payload


async def _create_product(client: AsyncClient, **overrides) -> str:
    resp = await client.post(_BASE + "/products", json=_product_payload(**overrides))
    assert resp.status_code == 200, resp.text
    return resp.json()["product"]["id"]


class TestAuth:
    async def test_list_products_requires_auth(self, client: AsyncClient):
        resp = await client.get(_BASE + "/products")
        assert resp.status_code in {401, 403}

    async def test_roas_requires_auth(self, client: AsyncClient):
        resp = await client.get(
            _BASE + "/profit/roas",
            params={
                "start_date": date(2026, 1, 1).isoformat(),
                "end_date": date(2026, 1, 31).isoformat(),
            },
        )
        assert resp.status_code in {401, 403}


class TestProductCatalog:
    async def test_create_and_get(self, authenticated_client: AsyncClient):
        product_id = await _create_product(authenticated_client)
        got = await authenticated_client.get(f"{_BASE}/products/{product_id}")
        assert got.status_code == 200, got.text
        assert got.json()["status"] == "success"

    async def test_list_includes_created(self, authenticated_client: AsyncClient):
        product_id = await _create_product(authenticated_client, sku="SKU-LIST")
        listed = await authenticated_client.get(_BASE + "/products")
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["status"] == "success"
        assert any(p["id"] == product_id for p in body["products"])

    async def test_list_search_filter(self, authenticated_client: AsyncClient):
        await _create_product(authenticated_client, sku="SKU-FIND", name="Findable")
        resp = await authenticated_client.get(
            _BASE + "/products", params={"search": "Findable"}
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json()["products"], list)

    async def test_get_unknown_product_404(self, authenticated_client: AsyncClient):
        from uuid import uuid4

        resp = await authenticated_client.get(f"{_BASE}/products/{uuid4()}")
        assert resp.status_code == 404

    async def test_create_validation_error(self, authenticated_client: AsyncClient):
        # sku is required and must be non-empty.
        resp = await authenticated_client.post(
            _BASE + "/products", json={"name": "no sku"}
        )
        assert resp.status_code == 422

    async def test_set_cogs(self, authenticated_client: AsyncClient):
        product_id = await _create_product(authenticated_client, sku="SKU-COGS")
        resp = await authenticated_client.post(
            f"{_BASE}/products/{product_id}/cogs",
            json={"cogs": 12.50, "shipping_cost": 2.0},
        )
        assert resp.status_code in {200, 404}, resp.text


class TestCogsCoverage:
    async def test_categories(self, authenticated_client: AsyncClient):
        await _create_product(authenticated_client, sku="SKU-CAT", category="gadgets")
        resp = await authenticated_client.get(_BASE + "/products/categories")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "success"
        assert isinstance(resp.json()["categories"], list)

    async def test_coverage(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(_BASE + "/products/coverage")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "success"

    async def test_missing_cogs(self, authenticated_client: AsyncClient):
        await _create_product(authenticated_client, sku="SKU-NOCOGS")
        resp = await authenticated_client.get(_BASE + "/products/missing-cogs")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "success"
        assert isinstance(resp.json()["products"], list)


class TestProfitReads:
    _range = {
        "start_date": date(2026, 1, 1).isoformat(),
        "end_date": date(2026, 1, 31).isoformat(),
    }

    async def test_roas_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            _BASE + "/profit/roas", params=self._range
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_trend_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            _BASE + "/profit/trend",
            params={**self._range, "granularity": "weekly"},
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_by_product_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            _BASE + "/profit/by-product", params=self._range
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_by_campaign_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            _BASE + "/profit/by-campaign", params=self._range
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_roas_validation_error(self, authenticated_client: AsyncClient):
        # Missing required start_date/end_date.
        resp = await authenticated_client.get(_BASE + "/profit/roas")
        assert resp.status_code == 422
