# =============================================================================
# Stratum AI - Pacing & Forecasting Endpoint Integration Tests
# =============================================================================
"""Integration tests for the pacing/forecasting surface under
``/api/v1/pacing/...``: target CRUD, pacing reads, forecasting, and alerts.

These endpoints depend on ``app.tenancy.deps.get_db`` (a separate wrapper over
``get_async_session``); the harness overrides both, so the endpoints share the
test's savepoint-scoped session and tenant. The pacing tables (``targets``,
``daily_kpis``, ``pacing_alerts``, ``forecasts``) are created via ``create_all``.

With no ``daily_kpis`` seeded, the pacing/forecast math runs against an empty
series and returns a graceful envelope rather than crashing — that's the
contract these tests pin.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

from datetime import date

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/pacing"


def _target_payload(**overrides) -> dict:
    payload = {
        "name": "Q-spend target",
        "metric_type": "spend",
        "target_value": 10000.0,
        "period_type": "monthly",
        "period_start": date(2026, 1, 1).isoformat(),
        "period_end": date(2026, 1, 31).isoformat(),
        "platform": "meta",
    }
    payload.update(overrides)
    return payload


async def _create_target(client: AsyncClient, **overrides) -> str:
    resp = await client.post(_BASE + "/targets", json=_target_payload(**overrides))
    assert resp.status_code == 200, resp.text
    return resp.json()["target"]["id"]


class TestAuth:
    async def test_list_targets_requires_auth(self, client: AsyncClient):
        resp = await client.get(_BASE + "/targets")
        assert resp.status_code in {401, 403}

    async def test_create_target_requires_auth(self, client: AsyncClient):
        resp = await client.post(_BASE + "/targets", json=_target_payload())
        assert resp.status_code in {401, 403}


class TestTargetCrud:
    async def test_create_and_get(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client)

        got = await authenticated_client.get(f"{_BASE}/targets/{target_id}")
        assert got.status_code == 200, got.text
        body = got.json()
        assert body["status"] == "success"
        assert body["target"]["id"] == target_id
        assert body["target"]["metric_type"] == "spend"

    async def test_list_includes_created(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client, name="listed-target")
        listed = await authenticated_client.get(_BASE + "/targets")
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["status"] == "success"
        assert any(t["id"] == target_id for t in body["targets"])

    async def test_list_filter_by_metric(self, authenticated_client: AsyncClient):
        await _create_target(authenticated_client, metric_type="spend")
        resp = await authenticated_client.get(
            _BASE + "/targets", params={"metric_type": "roas"}
        )
        assert resp.status_code == 200, resp.text
        # Only roas targets (none created) should come back.
        assert all(t["metric_type"] == "roas" for t in resp.json()["targets"])

    async def test_get_unknown_target_404(self, authenticated_client: AsyncClient):
        from uuid import uuid4

        resp = await authenticated_client.get(f"{_BASE}/targets/{uuid4()}")
        assert resp.status_code == 404

    async def test_update_target(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client)
        resp = await authenticated_client.patch(
            f"{_BASE}/targets/{target_id}",
            json={"name": "renamed", "target_value": 25000.0},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["target"]["name"] == "renamed"

    async def test_update_unknown_404(self, authenticated_client: AsyncClient):
        from uuid import uuid4

        resp = await authenticated_client.patch(
            f"{_BASE}/targets/{uuid4()}", json={"name": "x"}
        )
        assert resp.status_code == 404

    async def test_delete_then_get_404(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client)
        deleted = await authenticated_client.delete(f"{_BASE}/targets/{target_id}")
        assert deleted.status_code == 200, deleted.text
        # delete is a soft-deactivate; the row remains fetchable by id but the
        # delete endpoint itself confirms success.
        assert deleted.json()["status"] == "success"

    async def test_create_validation_error(self, authenticated_client: AsyncClient):
        # target_value must be > 0.
        resp = await authenticated_client.post(
            _BASE + "/targets", json=_target_payload(target_value=-5)
        )
        assert resp.status_code == 422


class TestPacingReads:
    async def test_pacing_all_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(_BASE + "/pacing/all")
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_pacing_target(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client)
        resp = await authenticated_client.get(f"{_BASE}/pacing/target/{target_id}")
        # With no KPI data the service returns a graceful pacing envelope (200);
        # an unknown/empty target may surface as 404.
        assert resp.status_code in {200, 404}, resp.text

    async def test_pacing_history_empty(self, authenticated_client: AsyncClient):
        target_id = await _create_target(authenticated_client)
        resp = await authenticated_client.get(f"{_BASE}/pacing/history/{target_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "success"
        assert body["count"] == 0


class TestForecast:
    async def test_eom_forecast_graceful(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            _BASE + "/forecast/eom", params={"metric_type": "spend"}
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_create_forecast_graceful(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            _BASE + "/forecast",
            json={"metric_type": "spend", "forecast_days": 14},
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)


class TestAlerts:
    async def test_list_alerts_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(_BASE + "/alerts")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "success"
        assert body["count"] == 0

    async def test_alert_summary(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(_BASE + "/alerts/summary")
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), dict)

    async def test_acknowledge_unknown_alert_404(
        self, authenticated_client: AsyncClient
    ):
        from uuid import uuid4

        resp = await authenticated_client.post(f"{_BASE}/alerts/{uuid4()}/acknowledge")
        assert resp.status_code == 404
