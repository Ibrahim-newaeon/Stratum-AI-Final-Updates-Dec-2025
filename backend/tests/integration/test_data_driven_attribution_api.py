# =============================================================================
# Stratum AI - Data-Driven Attribution Endpoint Integration Tests
# =============================================================================
"""Integration tests for the data-driven attribution surface under
``/api/v1/attribution/data-driven/...``: model-type catalog, training-data
readiness, model_type validation, and batch attribution.

The Markov/Shapley training paths need a large CRM journey corpus and ML
machinery, so the heavy ``/train`` routes are out of scope here. These tests
target the read/validation surface plus a regression guard for a
``NameError`` in ``/batch-attribute``.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/attribution/data-driven"


class TestModelTypes:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/model-types")
        assert resp.status_code in {401, 403}

    async def test_lists_model_types(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/model-types")
        assert resp.status_code == 200, resp.text
        values = {m["value"] for m in resp.json()["model_types"]}
        assert values == {"markov_chain", "shapley_value"}


class TestTrainingRequirements:
    async def test_empty_data_not_ready(self, authenticated_client: AsyncClient):
        # No CRM deals/touchpoints seeded -> insufficient data, not ready.
        resp = await authenticated_client.get(
            f"{_BASE}/training-requirements",
            params={
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-06-01T00:00:00Z",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["is_ready"] is False
        assert body["data_availability"]["won_deals"] == 0


class TestTrainValidation:
    async def test_invalid_model_type_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/train",
            json={
                "model_type": "not_a_real_model",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-06-01T00:00:00Z",
            },
        )
        assert resp.status_code == 400


class TestBatchAttribute:
    async def test_empty_batch_returns_zero_totals(
        self, authenticated_client: AsyncClient
    ):
        # Regression: the handler computed `len(deal_ids)` (undefined name)
        # instead of `len(request.deal_ids)`, raising NameError -> 500 on every
        # call, including an empty batch. An empty list must return zeroed
        # totals without error.
        resp = await authenticated_client.post(
            f"{_BASE}/batch-attribute",
            json={
                "model_type": "markov_chain",
                "model_data": {},
                "deal_ids": [],
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 0
        assert body["successful"] == 0
        assert body["failed"] == 0

    async def test_invalid_model_type_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/batch-attribute",
            json={"model_type": "bogus", "model_data": {}, "deal_ids": []},
        )
        assert resp.status_code == 400
