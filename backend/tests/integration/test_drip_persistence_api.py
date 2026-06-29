# =============================================================================
# Stratum AI - Drip Campaigns Persistence Integration Tests
# =============================================================================
"""Integration tests for the DB-backed drip-campaign behavior.

These exercise the persistence layer added when drip sequences moved off
the per-process in-memory store onto PostgreSQL: the manual trigger →
execution-log → analytics flow, and the status filter on the list
endpoint. Complements ``test_drip_campaigns_api.py`` (CRUD + lifecycle).
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _sequence(name="Persisted series", **extra):
    body = {
        "name": name,
        "description": "",
        "trigger_type": "manual",
        "trigger_config": {},
        "nodes": [
            {"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}},
        ],
        "edges": [],
        "status": "draft",
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/drip-campaigns", json=_sequence(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestTriggerLogsAnalytics:
    @pytest.mark.asyncio
    async def test_trigger_records_execution_and_logs(
        self, authenticated_client: AsyncClient
    ):
        seq = await _create(authenticated_client, name="Trigger Seq")
        sid = seq["id"]

        triggered = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{sid}/trigger",
            params={"recipient_email": "buyer@example.com"},
        )
        assert triggered.status_code == 200
        assert triggered.json()["data"]["status"] == "triggered"

        # The execution log is persisted and returned.
        logs = await authenticated_client.get(f"/api/v1/drip-campaigns/{sid}/logs")
        assert logs.status_code == 200
        entries = logs.json()["data"]
        assert len(entries) == 1
        assert entries[0]["recipient_email"] == "buyer@example.com"
        assert entries[0]["node_type"] == "trigger"

    @pytest.mark.asyncio
    async def test_analytics_reflects_triggers(self, authenticated_client: AsyncClient):
        seq = await _create(authenticated_client, name="Analytics Seq")
        sid = seq["id"]
        for email in ("a@example.com", "b@example.com"):
            await authenticated_client.post(
                f"/api/v1/drip-campaigns/{sid}/trigger",
                params={"recipient_email": email},
            )

        resp = await authenticated_client.get(f"/api/v1/drip-campaigns/{sid}/analytics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["sequence_id"] == sid
        assert data["total_entries"] == 2
        assert data["emails_sent"] == 2

    @pytest.mark.asyncio
    async def test_logs_not_found_for_unknown_sequence(
        self, authenticated_client: AsyncClient
    ):
        # Logs for an unknown sequence are simply empty (no execution rows).
        resp = await authenticated_client.get(
            "/api/v1/drip-campaigns/drip_unknown/logs"
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_analytics_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/drip-campaigns/drip_unknown/analytics"
        )
        assert resp.status_code == 404


class TestStatusFilter:
    @pytest.mark.asyncio
    async def test_list_status_filter(self, authenticated_client: AsyncClient):
        draft = await _create(authenticated_client, name="Stays Draft")
        active_seq = await _create(authenticated_client, name="Goes Active")
        await authenticated_client.post(
            f"/api/v1/drip-campaigns/{active_seq['id']}/activate"
        )

        resp = await authenticated_client.get(
            "/api/v1/drip-campaigns", params={"status_filter": "active"}
        )
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()["data"]}
        assert "Goes Active" in names
        assert "Stays Draft" not in names
        assert draft["name"] == "Stays Draft"
