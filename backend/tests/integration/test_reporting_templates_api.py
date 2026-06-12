# =============================================================================
# Stratum AI - Reporting Templates API Integration Tests
# =============================================================================
"""Integration tests for the reporting/templates API.

Exercises the real ASGI app against Postgres + Redis: report-template
creation, listing, detail (200/404), validation, and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _template(name="Weekly Performance", report_type="campaign_performance", **extra):
    body = {"name": name, "report_type": report_type}
    body.update(extra)
    return body


class TestCreateTemplate:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/reporting/templates", json=_template())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/reporting/templates",
            json=_template(name="Exec Summary", report_type="executive_summary"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Exec Summary"
        assert data["report_type"] == "executive_summary"

    @pytest.mark.asyncio
    async def test_invalid_report_type(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/reporting/templates", json=_template(report_type="not_a_type")
        )
        assert resp.status_code == 422


class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/reporting/templates", json=_template(name="Tmpl One")
        )
        await authenticated_client.post(
            "/api/v1/reporting/templates",
            json=_template(name="Tmpl Two", report_type="profit_roas"),
        )
        resp = await authenticated_client.get("/api/v1/reporting/templates")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()}
        assert {"Tmpl One", "Tmpl Two"} <= names

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/reporting/templates", json=_template(name="Detail Tmpl")
        )
        template_id = created.json()["id"]
        resp = await authenticated_client.get(
            f"/api/v1/reporting/templates/{template_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Tmpl"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/reporting/templates/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
