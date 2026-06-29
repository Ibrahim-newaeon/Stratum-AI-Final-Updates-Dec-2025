# =============================================================================
# Stratum AI - Reporting Schedules API Integration Tests
# =============================================================================
"""Integration tests for the reporting/schedules API.

Exercises the real ASGI app against Postgres + Redis: scheduled-report
creation (linked to a real template), listing, detail (200/404), update,
pause/resume lifecycle, history, and delete (200/404), plus auth and
validation. The run-now / generate paths kick off real report rendering,
so they are left to service-level tests.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


async def _make_template(client: AsyncClient, name="Sched Template") -> str:
    resp = await client.post(
        "/api/v1/reporting/templates",
        json={"name": name, "report_type": "campaign_performance"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _schedule(template_id, name="Weekly exec", frequency="weekly", **extra):
    body = {
        "template_id": template_id,
        "name": name,
        "frequency": frequency,
        "day_of_week": 1,
        "hour": 8,
        "delivery_channels": ["email"],
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    name = extra.get("name", "Weekly exec")
    # Template names are unique per tenant, so derive a distinct one per call.
    template_id = extra.pop("template_id", None) or await _make_template(
        client, name=f"Tmpl for {name}"
    )
    resp = await client.post(
        "/api/v1/reporting/schedules", json=_schedule(template_id, **extra)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# =============================================================================
# Create
# =============================================================================
class TestCreateSchedule:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/reporting/schedules", json=_schedule(_MISSING)
        )
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="Monday digest")
        assert data["name"] == "Monday digest"
        assert data["frequency"] == "weekly"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_invalid_frequency_rejected(self, authenticated_client: AsyncClient):
        template_id = await _make_template(authenticated_client, name="Tmpl Freq")
        resp = await authenticated_client.post(
            "/api/v1/reporting/schedules",
            json=_schedule(template_id, frequency="hourly"),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_template_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/reporting/schedules", json=_schedule(_MISSING)
        )
        # Scheduler raises ValueError for a missing template → 400.
        assert resp.status_code == 400


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Sched A")
        await _create(authenticated_client, name="Sched B")
        resp = await authenticated_client.get("/api/v1/reporting/schedules")
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()}
        assert {"Sched A", "Sched B"} <= names

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail Sched")
        resp = await authenticated_client.get(
            f"/api/v1/reporting/schedules/{created['id']}"
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Sched"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/reporting/schedules/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Update + lifecycle + delete
# =============================================================================
class TestMutationsAndLifecycle:
    @pytest.mark.asyncio
    async def test_update_name(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/reporting/schedules/{created['id']}", json={"name": "After"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    @pytest.mark.asyncio
    async def test_pause_then_resume(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Toggle Sched")
        sid = created["id"]
        paused = await authenticated_client.post(
            f"/api/v1/reporting/schedules/{sid}/pause"
        )
        assert paused.status_code == 200
        assert paused.json()["is_paused"] is True

        resumed = await authenticated_client.post(
            f"/api/v1/reporting/schedules/{sid}/resume"
        )
        assert resumed.status_code == 200
        assert resumed.json()["is_paused"] is False

    @pytest.mark.asyncio
    async def test_history_for_new_schedule(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="History Sched")
        resp = await authenticated_client.get(
            f"/api/v1/reporting/schedules/{created['id']}/history"
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed Sched")
        sid = created["id"]
        deleted = await authenticated_client.delete(
            f"/api/v1/reporting/schedules/{sid}"
        )
        assert deleted.status_code == 200
        gone = await authenticated_client.get(f"/api/v1/reporting/schedules/{sid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            f"/api/v1/reporting/schedules/{_MISSING}"
        )
        assert resp.status_code == 404
