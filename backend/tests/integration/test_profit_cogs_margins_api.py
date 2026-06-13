# =============================================================================
# Stratum AI - Profit COGS + Margin Rules API Integration Tests
# =============================================================================
"""Integration tests for the profit COGS-setting and margin-rules APIs.

Exercises the real ASGI app against Postgres + Redis: setting per-product
COGS (with validation), reading COGS history, and the margin-rule CRUD
lifecycle (create / list / update / delete, with 404 + validation paths).

Complements ``test_profit_products_api.py`` (product catalog) by covering
the cost/margin surfaces it does not touch. The ``/cogs/upload`` route
takes a multipart CSV, so it is left to service-level tests.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


async def _make_product(client: AsyncClient, sku="COGS-1", name="Widget") -> str:
    resp = await client.post("/api/v1/profit/products", json={"sku": sku, "name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()["product"]["id"]


# =============================================================================
# Product COGS
# =============================================================================
class TestProductCOGS:
    @pytest.mark.asyncio
    async def test_set_cogs_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            f"/api/v1/profit/products/{_MISSING}/cogs", json={"cogs": 5.0}
        )
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_set_cogs_success(self, authenticated_client: AsyncClient):
        product_id = await _make_product(authenticated_client, sku="COGS-A")
        resp = await authenticated_client.post(
            f"/api/v1/profit/products/{product_id}/cogs",
            json={"cogs": 12.50, "shipping_cost": 2.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["margin_id"]

    @pytest.mark.asyncio
    async def test_set_cogs_requires_value(self, authenticated_client: AsyncClient):
        product_id = await _make_product(authenticated_client, sku="COGS-B")
        # Neither cogs nor cogs_percentage provided → 400.
        resp = await authenticated_client.post(
            f"/api/v1/profit/products/{product_id}/cogs",
            json={"shipping_cost": 1.0},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cogs_history_after_set(self, authenticated_client: AsyncClient):
        product_id = await _make_product(authenticated_client, sku="COGS-C")
        await authenticated_client.post(
            f"/api/v1/profit/products/{product_id}/cogs",
            json={"cogs_percentage": 30.0},
        )
        resp = await authenticated_client.get(
            f"/api/v1/profit/products/{product_id}/cogs/history"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert len(body["history"]) >= 1


# =============================================================================
# Margin rules
# =============================================================================
def _rule(name="Default 40% margin", **extra):
    body = {"name": name, "default_margin_percentage": 40.0}
    body.update(extra)
    return body


async def _create_rule(client: AsyncClient, **extra) -> str:
    resp = await client.post("/api/v1/profit/margin-rules", json=_rule(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()["rule_id"]


class TestMarginRules:
    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/profit/margin-rules", json=_rule())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        rule_id = await _create_rule(authenticated_client, name="Premium tier")
        assert rule_id

    @pytest.mark.asyncio
    async def test_create_requires_a_percentage(
        self, authenticated_client: AsyncClient
    ):
        # Neither margin nor cogs percentage → 400.
        resp = await authenticated_client.post(
            "/api/v1/profit/margin-rules", json={"name": "Empty rule"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_invalid_percentage_rejected(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/profit/margin-rules",
            json=_rule(default_margin_percentage=150.0),  # bounded 0..100
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create_rule(authenticated_client, name="Rule One")
        await _create_rule(authenticated_client, name="Rule Two")
        resp = await authenticated_client.get("/api/v1/profit/margin-rules")
        assert resp.status_code == 200
        names = {r["name"] for r in resp.json()["rules"]}
        assert {"Rule One", "Rule Two"} <= names

    @pytest.mark.asyncio
    async def test_update_rule(self, authenticated_client: AsyncClient):
        rule_id = await _create_rule(authenticated_client, name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/profit/margin-rules/{rule_id}",
            json={"priority": 50},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/profit/margin-rules/{_MISSING}", json={"priority": 10}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        rule_id = await _create_rule(authenticated_client, name="Doomed rule")
        deleted = await authenticated_client.delete(
            f"/api/v1/profit/margin-rules/{rule_id}"
        )
        assert deleted.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            f"/api/v1/profit/margin-rules/{_MISSING}"
        )
        assert resp.status_code == 404
