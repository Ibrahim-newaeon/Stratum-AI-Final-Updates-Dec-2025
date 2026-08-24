# =============================================================================
# Stratum AI - Drip Campaigns Persistence Integration Tests
# =============================================================================
"""Integration tests for the DB-backed drip-campaign behavior.

These exercise the persistence layer added when drip sequences moved off the
per-process in-memory store onto PostgreSQL: the manual trigger → enrollment →
analytics flow, and the status filter on the list endpoint. Complements
``test_drip_campaigns_api.py`` (CRUD + lifecycle).

**The trigger contract changed when the execution engine landed.** It used to
write a ``DripExecutionRecord`` marked *simulated* and return success, so these
tests asserted that a log row appeared the instant someone was triggered. That
log row was the whole illusion: nothing had been sent, and nothing ever would
be. A trigger now creates an *enrollment*, and a log row appears only once the
worker actually sends something — so the assertions here moved from "a log
exists" to "an enrollment exists and no mail has gone out yet", which is what is
really true at that moment.
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _enable_drip(monkeypatch):
    """Drip ships gated off; enable the flag so the API is reachable here."""
    monkeypatch.setattr(settings, "feature_drip_campaigns", True)


def _sequence(name="Persisted series", **extra):
    """A publishable graph.

    This used to be a lone trigger node with no edges. `activate` accepted it,
    because `activate` accepted anything. It now validates, and a trigger that
    goes nowhere is not a sequence.
    """
    body = {
        "name": name,
        "description": "",
        "trigger_type": "manual",
        "trigger_config": {},
        "nodes": [
            {"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}},
            {
                "id": "n2",
                "type": "email",
                "position": {"x": 0, "y": 1},
                "data": {"subject": "Hello", "html": "<p>Hi</p>"},
            },
            {"id": "n3", "type": "end", "position": {"x": 0, "y": 2}, "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
        ],
        "status": "draft",
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/drip-campaigns", json=_sequence(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_active(client: AsyncClient, **extra) -> str:
    """Create a sequence and publish it. Returns the sequence id.

    Enrollment needs a published version — there is nowhere to put a recipient
    otherwise — so every trigger test goes through here.
    """
    created = await _create(client, **extra)
    resp = await client.post(f"/api/v1/drip-campaigns/{created['id']}/activate")
    assert resp.status_code == 200, resp.text
    return created["id"]


class TestTriggerLogsAnalytics:
    @pytest.mark.asyncio
    async def test_trigger_creates_an_enrollment(
        self, authenticated_client: AsyncClient
    ):
        sid = await _create_active(authenticated_client, name="Trigger Seq")

        triggered = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{sid}/trigger",
            params={"recipient_email": "buyer@example.com"},
        )
        assert triggered.status_code == 200
        data = triggered.json()["data"]
        assert data["status"] == "enrolled"
        assert data["enrollment_id"].startswith("enroll_")

        # And no mail has gone out yet, because no worker has run. The old
        # behaviour wrote a log row here and called it sent.
        logs = await authenticated_client.get(f"/api/v1/drip-campaigns/{sid}/logs")
        assert logs.status_code == 200
        assert logs.json()["data"] == []

    @pytest.mark.asyncio
    async def test_trigger_before_activation_is_refused(
        self, authenticated_client: AsyncClient
    ):
        """There is nowhere to put a recipient without a published version."""
        seq = await _create(authenticated_client, name="Unpublished Seq")
        resp = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{seq['id']}/trigger",
            params={"recipient_email": "buyer@example.com"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["reason"] == "not_active"

    @pytest.mark.asyncio
    async def test_triggering_the_same_recipient_twice_is_idempotent(
        self, authenticated_client: AsyncClient
    ):
        """The partial unique index makes double enrollment impossible; the
        endpoint reports it rather than erroring."""
        sid = await _create_active(authenticated_client, name="Dedupe Seq")
        params = {"recipient_email": "buyer@example.com"}

        first = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{sid}/trigger", params=params
        )
        second = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{sid}/trigger", params=params
        )
        assert first.json()["data"]["status"] == "enrolled"
        assert second.status_code == 200
        assert second.json()["data"]["status"] == "already_enrolled"

    @pytest.mark.asyncio
    async def test_analytics_reflects_triggers(self, authenticated_client: AsyncClient):
        sid = await _create_active(authenticated_client, name="Analytics Seq")
        for email in ("a@example.com", "b@example.com"):
            await authenticated_client.post(
                f"/api/v1/drip-campaigns/{sid}/trigger",
                params={"recipient_email": email},
            )

        resp = await authenticated_client.get(f"/api/v1/drip-campaigns/{sid}/analytics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["sequence_id"] == sid
        # Two people entered...
        assert data["total_entries"] == 2
        # ...and nothing has been sent to either of them yet. This assertion
        # used to read `== 2`, which was counting the simulated records.
        assert data["emails_sent"] == 0

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
        await _create_active(authenticated_client, name="Goes Active")

        resp = await authenticated_client.get(
            "/api/v1/drip-campaigns", params={"status_filter": "active"}
        )
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()["data"]}
        assert "Goes Active" in names
        assert "Stays Draft" not in names
        assert draft["name"] == "Stays Draft"
