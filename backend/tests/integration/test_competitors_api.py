# =============================================================================
# Stratum AI - Competitor Intelligence API Integration Tests
# =============================================================================
"""Integration tests for the competitor-intelligence API.

Exercises the real ASGI app against Postgres + Redis: competitor
tracking (add/list/detail/update/remove), duplicate-domain guard,
share-of-voice, keywords, manual refresh enqueue, validation, and auth.
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.integration

_MISSING = 99999999


@pytest.fixture(autouse=True)
def _enable_competitor_intel(monkeypatch):
    """Competitor Intel ships gated off; enable the flag so the API is reachable."""
    monkeypatch.setattr(settings, "feature_competitor_intel", True)


def _competitor(domain="rival.com", name="Rival Co", **extra):
    body = {"domain": domain, "name": name}
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/competitors", json=_competitor(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# =============================================================================
# Create
# =============================================================================
class TestAddCompetitor:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/competitors", json=_competitor())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, domain="Acme.COM", name="Acme")
        # Domain is normalized to lowercase on store.
        assert data["domain"] == "acme.com"
        assert data["name"] == "Acme"

    @pytest.mark.asyncio
    async def test_duplicate_domain_rejected(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, domain="dupe.com")
        resp = await authenticated_client.post(
            "/api/v1/competitors", json=_competitor(domain="dupe.com")
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_domain_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/competitors", json={"name": "No Domain"}
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail + share-of-voice + keywords
# =============================================================================
class TestReadSurfaces:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, domain="one.com")
        await _create(authenticated_client, domain="two.com")
        resp = await authenticated_client.get("/api/v1/competitors")
        assert resp.status_code == 200
        domains = {c["domain"] for c in resp.json()["data"]}
        assert {"one.com", "two.com"} <= domains

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, domain="detail.com")
        resp = await authenticated_client.get(f"/api/v1/competitors/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["domain"] == "detail.com"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/competitors/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_share_of_voice_is_gone(self, authenticated_client: AsyncClient):
        """It summed a column nothing writes and called the result a market.

        ``total_market = sum(c.estimated_traffic or 0)`` over a column no code
        path populates, so it reported a market size of 0 as a measurement.
        Removed rather than fixed: share of voice needs a paid ad-intelligence
        provider, and there is nothing to serve until one is wired.

        422, not 404 — the path now falls through to ``/{competitor_id}`` and
        fails to parse "share-of-voice" as an int.
        """
        await _create(authenticated_client, domain="sov.com")
        resp = await authenticated_client.get("/api/v1/competitors/share-of-voice")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_keywords_is_gone(self, authenticated_client: AsyncClient):
        """``top_keywords`` is never written, so this only ever returned [].

        An empty keyword list is indistinguishable from "this competitor buys
        no keywords", which is a claim we cannot make.
        """
        created = await _create(authenticated_client, domain="kw.com")
        resp = await authenticated_client.get(
            f"/api/v1/competitors/{created['id']}/keywords"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_response_omits_metrics_no_source_fills(
        self, authenticated_client: AsyncClient
    ):
        """A null that reaches a dashboard becomes a zero, so they are absent.

        The frontend proved it: ``Number(c.shareOfVoice ?? 0)`` rendered
        "0% share of voice" on every card.
        """
        created = await _create(authenticated_client, domain="lean.com")
        resp = await authenticated_client.get(f"/api/v1/competitors/{created['id']}")

        assert resp.status_code == 200
        body = resp.json()["data"]
        for absent in (
            "estimated_traffic",
            "traffic_trend",
            "top_keywords",
            "paid_keywords_count",
            "organic_keywords_count",
            "share_of_voice",
            "category_rank",
            "estimated_ad_spend_cents",
        ):
            assert absent not in body, f"{absent} is served but nothing fills it"

        # What the scanner does source stays.
        for present in ("data_source", "ad_creatives_count", "detected_ad_platforms"):
            assert present in body


# =============================================================================
# Update + refresh + delete
# =============================================================================
class TestMutations:
    @pytest.mark.asyncio
    async def test_update_fields(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, domain="upd.com", name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/competitors/{created['id']}",
            json={"name": "After", "is_primary": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "After"
        assert data["is_primary"] is True

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/competitors/{_MISSING}", json={"name": "Nope"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_refresh_enqueues(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, domain="refresh.com")
        resp = await authenticated_client.post(
            f"/api/v1/competitors/{created['id']}/refresh"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["task_id"]

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, domain="doomed.com")
        cid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/competitors/{cid}")
        assert deleted.status_code == 204
        gone = await authenticated_client.get(f"/api/v1/competitors/{cid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/competitors/{_MISSING}")
        assert resp.status_code == 404
