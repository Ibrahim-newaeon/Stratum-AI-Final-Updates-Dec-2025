# =============================================================================
# Stratum AI - Reporting Endpoint Integration Tests
# =============================================================================
"""Integration tests for the reporting surface under ``/api/v1/reporting/...``:
report-template CRUD and scheduled-report CRUD + lifecycle (pause/resume).

These endpoints depend on ``app.tenancy.deps.get_db`` (overridden by the harness
alongside ``get_async_session``) and ``get_current_user``, so they share the
test's savepoint-scoped session and tenant. The reporting tables are created via
``create_all``.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/reporting"


def _template_payload(**overrides) -> dict:
    payload = {
        "name": "Weekly performance",
        "description": "Campaign performance rollup",
        "report_type": "campaign_performance",
        "config": {"metrics": ["spend", "roas"]},
        "default_format": "pdf",
        "available_formats": ["pdf", "csv"],
    }
    payload.update(overrides)
    return payload


async def _create_template(client: AsyncClient, **overrides) -> str:
    resp = await client.post(_BASE + "/templates", json=_template_payload(**overrides))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _schedule_payload(template_id: str, **overrides) -> dict:
    payload = {
        "template_id": template_id,
        "name": "Monday digest",
        "frequency": "weekly",
        "timezone": "UTC",
        "day_of_week": 0,
        "hour": 8,
        "minute": 0,
        "delivery_channels": ["email"],
        "delivery_config": {"recipients": ["ops@example.com"]},
    }
    payload.update(overrides)
    return payload


class TestAuth:
    async def test_list_templates_requires_auth(self, client: AsyncClient):
        resp = await client.get(_BASE + "/templates")
        assert resp.status_code in {401, 403}

    async def test_create_template_requires_auth(self, client: AsyncClient):
        resp = await client.post(_BASE + "/templates", json=_template_payload())
        assert resp.status_code in {401, 403}


class TestTemplateCrud:
    async def test_create_and_get(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client)
        got = await authenticated_client.get(f"{_BASE}/templates/{template_id}")
        assert got.status_code == 200, got.text
        body = got.json()
        assert body["id"] == template_id
        assert body["report_type"] == "campaign_performance"

    async def test_list_includes_created(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client, name="listed-tmpl")
        listed = await authenticated_client.get(_BASE + "/templates")
        assert listed.status_code == 200, listed.text
        assert any(t["id"] == template_id for t in listed.json())

    async def test_list_filter_by_type(self, authenticated_client: AsyncClient):
        await _create_template(authenticated_client, report_type="campaign_performance")
        resp = await authenticated_client.get(
            _BASE + "/templates", params={"report_type": "profit_roas"}
        )
        assert resp.status_code == 200, resp.text
        assert all(t["report_type"] == "profit_roas" for t in resp.json())

    async def test_get_unknown_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/templates/{uuid4()}")
        assert resp.status_code == 404

    async def test_update_template(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client)
        resp = await authenticated_client.patch(
            f"{_BASE}/templates/{template_id}",
            json={"name": "renamed", "description": "updated"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "renamed"

    async def test_create_validation_error(self, authenticated_client: AsyncClient):
        # Invalid report_type enum value.
        resp = await authenticated_client.post(
            _BASE + "/templates", json=_template_payload(report_type="nonsense")
        )
        assert resp.status_code == 422


class TestScheduleCrud:
    async def test_create_and_get(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client, name="sched-tmpl")
        created = await authenticated_client.post(
            _BASE + "/schedules", json=_schedule_payload(template_id)
        )
        assert created.status_code == 200, created.text
        schedule_id = created.json()["id"]

        got = await authenticated_client.get(f"{_BASE}/schedules/{schedule_id}")
        assert got.status_code == 200, got.text
        assert got.json()["id"] == schedule_id

    async def test_list_schedules(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client, name="sched-tmpl-2")
        created = await authenticated_client.post(
            _BASE + "/schedules",
            json=_schedule_payload(template_id, name="listed-schedule"),
        )
        assert created.status_code == 200, created.text
        schedule_id = created.json()["id"]

        listed = await authenticated_client.get(_BASE + "/schedules")
        assert listed.status_code == 200, listed.text
        assert any(s["id"] == schedule_id for s in listed.json())

    async def test_pause_then_resume(self, authenticated_client: AsyncClient):
        template_id = await _create_template(authenticated_client, name="sched-tmpl-3")
        created = await authenticated_client.post(
            _BASE + "/schedules", json=_schedule_payload(template_id)
        )
        assert created.status_code == 200, created.text
        schedule_id = created.json()["id"]

        paused = await authenticated_client.post(
            f"{_BASE}/schedules/{schedule_id}/pause"
        )
        assert paused.status_code == 200, paused.text

        resumed = await authenticated_client.post(
            f"{_BASE}/schedules/{schedule_id}/resume"
        )
        assert resumed.status_code == 200, resumed.text

    async def test_get_unknown_schedule_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/schedules/{uuid4()}")
        assert resp.status_code == 404

    async def test_create_schedule_unknown_template(
        self, authenticated_client: AsyncClient
    ):
        # Scheduler should reject a template_id that doesn't exist (400) rather
        # than 500.
        resp = await authenticated_client.post(
            _BASE + "/schedules", json=_schedule_payload(str(uuid4()))
        )
        assert resp.status_code in {400, 404}, resp.text
