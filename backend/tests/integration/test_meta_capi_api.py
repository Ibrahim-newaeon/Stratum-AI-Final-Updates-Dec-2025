# =============================================================================
# Stratum AI - Meta CAPI Endpoint Integration Tests
# =============================================================================
"""Integration tests for the Meta Conversions API surface under
``/api/v1/meta-capi/...``: health, event-payload validation (no external send),
and tenant-scoped data-quality metrics.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/meta-capi"

_GOOD_EVENT = {
    "event_name": "Purchase",
    "event_time": 1_750_000_000,
    "user_data": {"em": "a" * 64, "ph": "b" * 64},  # hashed email + phone
    "custom_data": {"value": 99.99, "currency": "USD"},
    "event_source_url": "https://shop.example.com/checkout",
    "action_source": "website",
}

_SPARSE_EVENT = {
    "event_name": "PageView",
    "event_time": 1_750_000_000,
    "user_data": {},
}


class TestHealth:
    async def test_health(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/health")
        assert resp.status_code == 200


class TestValidate:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{_BASE}/events/validate", json={"events": [_GOOD_EVENT]}
        )
        assert resp.status_code in {401, 403}

    async def test_validate_scores_and_ranks_events(
        self, authenticated_client: AsyncClient
    ):
        # Both events validated in one request (the endpoint takes a list): a
        # fully-populated Purchase must out-score a bare PageView, and each
        # score stays within bounds.
        resp = await authenticated_client.post(
            f"{_BASE}/events/validate",
            json={"events": [_GOOD_EVENT, _SPARSE_EVENT]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total_events"] == 2
        scores = {v["event_name"]: v["quality_score"] for v in data["validations"]}
        assert all(0 <= s <= 100 for s in scores.values())
        assert scores["Purchase"] >= scores["PageView"]


class TestQuality:
    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/quality/{test_tenant['id'] + 99999}"
        )
        assert resp.status_code == 403

    async def test_quality_empty_fallback(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(f"{_BASE}/quality/{test_tenant['id']}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # No events sent yet -> graceful fallback envelope.
        assert "overall_score" in data
        assert isinstance(data["platform_scores"], dict)
