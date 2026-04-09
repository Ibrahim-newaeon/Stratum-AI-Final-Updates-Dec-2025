# =============================================================================
# Stratum AI - Deep Endpoint Tests: Features 13 & 14
# =============================================================================
"""
Deep endpoint tests for:
  Feature 13 -- Automated Reporting (templates, schedules, executions)
  Feature 14 -- SuperAdmin dashboard & SuperAdmin Analytics

Each test exercises the FULL request/response cycle via httpx.AsyncClient,
passing through TenantMiddleware (real JWT decode + tenant extraction) while
mocking services / DB at the endpoint-handler level.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.unit.conftest import (
    make_auth_headers,
    make_scalar_result,
    make_scalars_result,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_UUID1 = uuid.uuid4()
_UUID2 = uuid.uuid4()
_UUID3 = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_user(*, user_id: int = 1, tenant_id: int = 1, role: str = "admin") -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.tenant_id = tenant_id
    u.role = role
    u.email = "test@example.com"
    u.is_deleted = False
    return u


def _fake_template(
    *,
    template_id: uuid.UUID | None = None,
    tenant_id: int = 1,
    name: str = "Monthly Perf",
    is_system: bool = False,
    is_active: bool = True,
) -> MagicMock:
    tpl = MagicMock()
    tpl.id = template_id or _UUID1
    tpl.tenant_id = tenant_id
    tpl.name = name
    tpl.description = "Test template"
    tpl.report_type = "campaign_performance"
    tpl.config = {}
    tpl.default_format = "pdf"
    tpl.available_formats = ["pdf", "csv"]
    tpl.is_active = is_active
    tpl.is_system = is_system
    tpl.created_at = _NOW
    tpl.updated_at = _NOW
    tpl.__dict__.update({
        "id": tpl.id, "tenant_id": tpl.tenant_id, "name": tpl.name,
        "description": tpl.description, "report_type": tpl.report_type,
        "config": tpl.config, "default_format": tpl.default_format,
        "available_formats": tpl.available_formats, "is_active": tpl.is_active,
        "is_system": tpl.is_system, "created_at": tpl.created_at,
        "updated_at": tpl.updated_at,
    })
    return tpl


def _fake_schedule(
    *,
    schedule_id: uuid.UUID | None = None,
    template_id: uuid.UUID | None = None,
    tenant_id: int = 1,
) -> MagicMock:
    s = MagicMock()
    s.id = schedule_id or _UUID2
    s.template_id = template_id or _UUID1
    s.tenant_id = tenant_id
    s.name = "Weekly report"
    s.description = None
    s.frequency = "weekly"
    s.timezone = "UTC"
    s.day_of_week = 1
    s.day_of_month = None
    s.hour = 8
    s.minute = 0
    s.cron_expression = None
    s.format_override = None
    s.date_range_type = "last_7_days"
    s.delivery_channels = ["email"]
    s.is_active = True
    s.is_paused = False
    s.last_run_at = None
    s.last_run_status = None
    s.next_run_at = None
    s.run_count = 0
    s.failure_count = 0
    s.created_at = _NOW
    s.__dict__.update({
        "id": s.id, "template_id": s.template_id, "name": s.name,
        "description": s.description, "frequency": s.frequency,
        "timezone": s.timezone, "day_of_week": s.day_of_week,
        "day_of_month": s.day_of_month, "hour": s.hour, "minute": s.minute,
        "cron_expression": s.cron_expression, "format_override": s.format_override,
        "date_range_type": s.date_range_type, "delivery_channels": s.delivery_channels,
        "is_active": s.is_active, "is_paused": s.is_paused,
        "last_run_at": s.last_run_at, "last_run_status": s.last_run_status,
        "next_run_at": s.next_run_at, "run_count": s.run_count,
        "failure_count": s.failure_count, "created_at": s.created_at,
    })
    return s


def _fake_execution(
    *,
    execution_id: uuid.UUID | None = None,
    tenant_id: int = 1,
    status: str = "completed",
) -> MagicMock:
    e = MagicMock()
    e.id = execution_id or _UUID3
    e.tenant_id = tenant_id
    e.template_id = _UUID1
    e.schedule_id = _UUID2
    e.execution_type = "manual"
    e.status = status
    e.started_at = _NOW
    e.completed_at = _NOW
    e.duration_seconds = 3.5
    e.report_type = "campaign_performance"
    e.format = "pdf"
    e.date_range_start = date(2026, 1, 1)
    e.date_range_end = date(2026, 1, 31)
    e.file_url = "https://s3.example.com/report.pdf"
    e.file_size_bytes = 102400
    e.row_count = 50
    e.metrics_summary = {"total_spend": 5000}
    e.error_message = None
    e.__dict__.update({
        "id": e.id, "tenant_id": e.tenant_id, "template_id": e.template_id,
        "schedule_id": e.schedule_id, "execution_type": e.execution_type,
        "status": e.status, "started_at": e.started_at,
        "completed_at": e.completed_at, "duration_seconds": e.duration_seconds,
        "report_type": e.report_type, "format": e.format,
        "date_range_start": e.date_range_start, "date_range_end": e.date_range_end,
        "file_url": e.file_url, "file_size_bytes": e.file_size_bytes,
        "row_count": e.row_count, "metrics_summary": e.metrics_summary,
        "error_message": e.error_message,
    })
    return e


def _fake_tenant(
    *,
    tid: int = 1,
    name: str = "Acme Inc",
    plan: str = "professional",
) -> MagicMock:
    t = MagicMock()
    t.id = tid
    t.name = name
    t.slug = name.lower().replace(" ", "-")
    t.plan = plan
    t.is_deleted = False
    t.status = "active"
    t.mrr_cents = 9900
    t.max_users = 10
    t.created_at = _NOW
    t.health_score = 90
    t.churn_risk_score = 0.1
    t.last_admin_login_at = _NOW
    t.last_activity_at = _NOW
    t.onboarding_completed = True
    t.trial_ends_at = None
    return t


# ---------------------------------------------------------------------------
# Fixtures: reporting endpoints need overrides for tenancy.deps functions
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def reporting_client(test_app, mock_db):
    """
    httpx.AsyncClient with overrides for BOTH app.db.session AND
    app.tenancy.deps dependency functions used by reporting endpoints.
    """
    from app.db.session import get_async_session, get_db as db_session_get_db
    from app.tenancy.deps import get_db as tenancy_get_db, get_current_user

    fake_user = _fake_user()

    async def override_session():
        yield mock_db

    async def override_current_user():
        return fake_user

    test_app.dependency_overrides[get_async_session] = override_session
    test_app.dependency_overrides[db_session_get_db] = override_session
    test_app.dependency_overrides[tenancy_get_db] = override_session
    test_app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def reporting_client_factory(test_app, mock_db):
    """
    Factory that lets each test supply its own fake_user to the
    get_current_user override.
    """
    from app.db.session import get_async_session, get_db as db_session_get_db
    from app.tenancy.deps import get_db as tenancy_get_db, get_current_user

    class _Factory:
        def __init__(self):
            self.client = None

        async def build(self, fake_user=None):
            if fake_user is None:
                fake_user = _fake_user()

            async def override_session():
                yield mock_db

            async def override_current_user():
                return fake_user

            test_app.dependency_overrides[get_async_session] = override_session
            test_app.dependency_overrides[db_session_get_db] = override_session
            test_app.dependency_overrides[tenancy_get_db] = override_session
            test_app.dependency_overrides[get_current_user] = override_current_user

            self.client = AsyncClient(
                transport=ASGITransport(app=test_app),
                base_url="http://testserver",
            )
            return self.client

    factory = _Factory()
    yield factory
    if factory.client:
        await factory.client.aclose()
    test_app.dependency_overrides.clear()


# ============================================================================
# FEATURE 13 -- REPORTING
# ============================================================================

class TestReportingTemplatesNoAuth:
    """Reporting endpoints must reject unauthenticated requests."""

    async def test_list_templates_no_auth(self, api_client):
        r = await api_client.get("/api/v1/reporting/templates")
        assert r.status_code == 401

    async def test_create_template_no_auth(self, api_client):
        r = await api_client.post("/api/v1/reporting/templates", json={
            "name": "X", "report_type": "campaign_performance",
        })
        assert r.status_code == 401

    async def test_get_template_no_auth(self, api_client):
        r = await api_client.get(f"/api/v1/reporting/templates/{_UUID1}")
        assert r.status_code == 401

    async def test_patch_template_no_auth(self, api_client):
        r = await api_client.patch(
            f"/api/v1/reporting/templates/{_UUID1}", json={"name": "X"},
        )
        assert r.status_code == 401

    async def test_delete_template_no_auth(self, api_client):
        r = await api_client.delete(f"/api/v1/reporting/templates/{_UUID1}")
        assert r.status_code == 401


class TestReportingTemplatesCRUD:
    """CRUD operations on report templates (authenticated)."""

    async def test_create_template_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template()

        async def _refresh(obj, *a, **kw):
            for attr, val in tpl.__dict__.items():
                if not attr.startswith("_"):
                    setattr(obj, attr, val)

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        r = await reporting_client.post(
            "/api/v1/reporting/templates",
            json={
                "name": "Monthly Perf",
                "report_type": "campaign_performance",
                "config": {},
                "default_format": "pdf",
            },
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Monthly Perf"
        assert body["is_active"] is True

    async def test_list_templates_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template()
        mock_db.execute = AsyncMock(return_value=make_scalars_result([tpl]))

        r = await reporting_client.get(
            "/api/v1/reporting/templates", headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["name"] == "Monthly Perf"

    async def test_list_templates_empty(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await reporting_client.get(
            "/api/v1/reporting/templates", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_templates_with_report_type_filter(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await reporting_client.get(
            "/api/v1/reporting/templates?report_type=pacing_status",
            headers=admin_headers,
        )
        assert r.status_code == 200

    async def test_get_template_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template()
        mock_db.get = AsyncMock(return_value=tpl)

        r = await reporting_client.get(
            f"/api/v1/reporting/templates/{_UUID1}", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Monthly Perf"

    async def test_get_template_not_found(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.get = AsyncMock(return_value=None)
        r = await reporting_client.get(
            f"/api/v1/reporting/templates/{uuid.uuid4()}", headers=admin_headers,
        )
        assert r.status_code == 404

    async def test_get_template_wrong_tenant(
        self, reporting_client_factory, mock_db, admin_headers,
    ):
        user = _fake_user(tenant_id=1)
        client = await reporting_client_factory.build(fake_user=user)
        tpl = _fake_template(tenant_id=999)
        mock_db.get = AsyncMock(return_value=tpl)

        r = await client.get(
            f"/api/v1/reporting/templates/{_UUID1}", headers=admin_headers,
        )
        assert r.status_code == 404

    async def test_update_template_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template()
        mock_db.get = AsyncMock(return_value=tpl)

        async def _refresh(obj, *a, **kw):
            obj.name = "Updated Name"
        mock_db.refresh = AsyncMock(side_effect=_refresh)

        r = await reporting_client.patch(
            f"/api/v1/reporting/templates/{_UUID1}",
            json={"name": "Updated Name"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    async def test_update_system_template_blocked(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template(is_system=True)
        mock_db.get = AsyncMock(return_value=tpl)

        r = await reporting_client.patch(
            f"/api/v1/reporting/templates/{_UUID1}",
            json={"name": "Hacked"},
            headers=admin_headers,
        )
        assert r.status_code == 400
        assert "system" in r.json()["detail"].lower()

    async def test_update_template_not_found(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.get = AsyncMock(return_value=None)
        r = await reporting_client.patch(
            f"/api/v1/reporting/templates/{uuid.uuid4()}",
            json={"name": "X"},
            headers=admin_headers,
        )
        assert r.status_code == 404

    async def test_delete_template_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template()
        mock_db.get = AsyncMock(return_value=tpl)

        r = await reporting_client.delete(
            f"/api/v1/reporting/templates/{_UUID1}", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    async def test_delete_system_template_blocked(
        self, reporting_client, mock_db, admin_headers,
    ):
        tpl = _fake_template(is_system=True)
        mock_db.get = AsyncMock(return_value=tpl)

        r = await reporting_client.delete(
            f"/api/v1/reporting/templates/{_UUID1}", headers=admin_headers,
        )
        assert r.status_code == 400


class TestReportingSchedules:
    """Scheduled report CRUD tests."""

    async def test_create_schedule_no_auth(self, api_client):
        r = await api_client.post("/api/v1/reporting/schedules", json={
            "template_id": str(_UUID1), "name": "Weekly", "frequency": "weekly",
        })
        assert r.status_code == 401

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_create_schedule_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        sched = _fake_schedule()
        instance = MockScheduler.return_value
        instance.create_schedule = AsyncMock(return_value=sched)

        r = await reporting_client.post(
            "/api/v1/reporting/schedules",
            json={
                "template_id": str(_UUID1),
                "name": "Weekly report",
                "frequency": "weekly",
                "day_of_week": 1,
                "hour": 8,
                "minute": 0,
            },
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Weekly report"

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_create_schedule_invalid_template(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.create_schedule = AsyncMock(side_effect=ValueError("Template not found"))

        r = await reporting_client.post(
            "/api/v1/reporting/schedules",
            json={
                "template_id": str(uuid.uuid4()),
                "name": "Bad",
                "frequency": "daily",
            },
            headers=admin_headers,
        )
        assert r.status_code == 400

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_list_schedules_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        sched = _fake_schedule()
        instance = MockScheduler.return_value
        instance.list_schedules = AsyncMock(return_value=([sched], 1))

        r = await reporting_client.get(
            "/api/v1/reporting/schedules", headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 1

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_get_schedule_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        sched = _fake_schedule()
        instance = MockScheduler.return_value
        instance.get_schedule = AsyncMock(return_value=sched)

        r = await reporting_client.get(
            f"/api/v1/reporting/schedules/{_UUID2}", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["frequency"] == "weekly"

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_get_schedule_not_found(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.get_schedule = AsyncMock(return_value=None)

        r = await reporting_client.get(
            f"/api/v1/reporting/schedules/{uuid.uuid4()}", headers=admin_headers,
        )
        assert r.status_code == 404

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_update_schedule_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        sched = _fake_schedule()
        sched.name = "Renamed"
        sched.__dict__["name"] = "Renamed"
        instance = MockScheduler.return_value
        instance.update_schedule = AsyncMock(return_value=sched)

        r = await reporting_client.patch(
            f"/api/v1/reporting/schedules/{_UUID2}",
            json={"name": "Renamed"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_update_schedule_not_found(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.update_schedule = AsyncMock(
            side_effect=ValueError("Schedule not found"),
        )

        r = await reporting_client.patch(
            f"/api/v1/reporting/schedules/{uuid.uuid4()}",
            json={"name": "X"},
            headers=admin_headers,
        )
        assert r.status_code == 404

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_run_schedule_now_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        exe = _fake_execution()
        instance = MockScheduler.return_value
        instance.run_now = AsyncMock(return_value=exe)

        r = await reporting_client.post(
            f"/api/v1/reporting/schedules/{_UUID2}/run-now", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_run_schedule_now_not_found(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.run_now = AsyncMock(side_effect=ValueError("Schedule not found"))

        r = await reporting_client.post(
            f"/api/v1/reporting/schedules/{uuid.uuid4()}/run-now",
            headers=admin_headers,
        )
        assert r.status_code == 404

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_delete_schedule_happy(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.delete_schedule = AsyncMock(return_value=True)

        r = await reporting_client.delete(
            f"/api/v1/reporting/schedules/{_UUID2}", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    @patch("app.api.v1.endpoints.reporting.ReportScheduler")
    async def test_delete_schedule_not_found(
        self, MockScheduler, reporting_client, mock_db, admin_headers,
    ):
        instance = MockScheduler.return_value
        instance.delete_schedule = AsyncMock(return_value=False)

        r = await reporting_client.delete(
            f"/api/v1/reporting/schedules/{uuid.uuid4()}", headers=admin_headers,
        )
        assert r.status_code == 404


class TestReportingExecutions:
    """Execution history and detail tests."""

    async def test_list_executions_no_auth(self, api_client):
        r = await api_client.get("/api/v1/reporting/executions")
        assert r.status_code == 401

    async def test_list_executions_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        exe = _fake_execution()
        mock_db.execute = AsyncMock(return_value=make_scalars_result([exe]))

        r = await reporting_client.get(
            "/api/v1/reporting/executions", headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 1

    async def test_list_executions_empty(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await reporting_client.get(
            "/api/v1/reporting/executions", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_executions_with_status_filter(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await reporting_client.get(
            "/api/v1/reporting/executions?status=completed", headers=admin_headers,
        )
        assert r.status_code == 200

    async def test_get_execution_happy(
        self, reporting_client, mock_db, admin_headers,
    ):
        exe = _fake_execution()
        mock_db.get = AsyncMock(return_value=exe)

        r = await reporting_client.get(
            f"/api/v1/reporting/executions/{_UUID3}", headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["execution_type"] == "manual"

    async def test_get_execution_not_found(
        self, reporting_client, mock_db, admin_headers,
    ):
        mock_db.get = AsyncMock(return_value=None)
        r = await reporting_client.get(
            f"/api/v1/reporting/executions/{uuid.uuid4()}", headers=admin_headers,
        )
        assert r.status_code == 404

    async def test_get_execution_wrong_tenant(
        self, reporting_client, mock_db, admin_headers,
    ):
        exe = _fake_execution(tenant_id=999)
        mock_db.get = AsyncMock(return_value=exe)

        r = await reporting_client.get(
            f"/api/v1/reporting/executions/{_UUID3}", headers=admin_headers,
        )
        assert r.status_code == 404


class TestReportingReportTypes:
    """The /report-types info endpoint."""

    async def test_report_types_no_auth(self, api_client):
        r = await api_client.get("/api/v1/reporting/report-types")
        assert r.status_code == 401

    async def test_report_types_happy(
        self, reporting_client, admin_headers,
    ):
        r = await reporting_client.get(
            "/api/v1/reporting/report-types", headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "report_types" in body
        assert "formats" in body
        assert "frequencies" in body
        assert "delivery_channels" in body
        assert len(body["report_types"]) >= 5


# ============================================================================
# FEATURE 14 -- SUPER ADMIN DASHBOARD
# ============================================================================

class TestSuperAdminRevenue:
    """GET /api/v1/superadmin/revenue and /revenue/breakdown."""

    async def test_revenue_no_auth(self, api_client):
        r = await api_client.get("/api/v1/superadmin/revenue")
        assert r.status_code == 401

    async def test_revenue_non_superadmin(self, api_client, admin_headers):
        r = await api_client.get("/api/v1/superadmin/revenue", headers=admin_headers)
        assert r.status_code == 403

    async def test_revenue_happy(self, api_client, mock_db, superadmin_headers):
        tenant = _fake_tenant()
        mock_db.execute = AsyncMock(return_value=make_scalars_result([tenant]))

        r = await api_client.get(
            "/api/v1/superadmin/revenue", headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert "mrr" in data
        assert "arr" in data
        assert data["total_tenants"] == 1

    async def test_revenue_multiple_tenants(self, api_client, mock_db, superadmin_headers):
        t1 = _fake_tenant(tid=1, plan="professional")
        t2 = _fake_tenant(tid=2, plan="starter", name="Beta Co")
        t2.mrr_cents = 4900
        mock_db.execute = AsyncMock(return_value=make_scalars_result([t1, t2]))

        r = await api_client.get(
            "/api/v1/superadmin/revenue", headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_tenants"] == 2
        assert data["mrr"] == (9900 + 4900) / 100

    async def test_revenue_breakdown_no_auth(self, api_client):
        r = await api_client.get("/api/v1/superadmin/revenue/breakdown")
        assert r.status_code == 401

    async def test_revenue_breakdown_non_superadmin(self, api_client, admin_headers):
        r = await api_client.get(
            "/api/v1/superadmin/revenue/breakdown", headers=admin_headers,
        )
        assert r.status_code == 403

    async def test_revenue_breakdown_happy(self, api_client, mock_db, superadmin_headers):
        t1 = _fake_tenant(tid=1, plan="professional")
        t2 = _fake_tenant(tid=2, plan="starter", name="Beta Co")
        mock_db.execute = AsyncMock(return_value=make_scalars_result([t1, t2]))

        r = await api_client.get(
            "/api/v1/superadmin/revenue/breakdown", headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert "by_plan" in data
        assert "total_mrr" in data


class TestSuperAdminTenantPortfolio:
    """GET /api/v1/superadmin/tenants/portfolio."""

    async def test_portfolio_no_auth(self, api_client):
        r = await api_client.get("/api/v1/superadmin/tenants/portfolio")
        assert r.status_code == 401

    async def test_portfolio_non_superadmin(self, api_client, admin_headers):
        r = await api_client.get(
            "/api/v1/superadmin/tenants/portfolio", headers=admin_headers,
        )
        assert r.status_code == 403

    async def test_portfolio_happy(self, api_client, mock_db, superadmin_headers):
        tenant = _fake_tenant()
        user_count_result = make_scalar_result(3)
        campaign_count_result = make_scalar_result(5)
        mock_db.execute = AsyncMock(
            side_effect=[
                make_scalars_result([tenant]),
                user_count_result,
                campaign_count_result,
            ]
        )

        r = await api_client.get(
            "/api/v1/superadmin/tenants/portfolio", headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert "tenants" in data
        assert data["total"] == 1
        assert data["tenants"][0]["name"] == "Acme Inc"
        assert data["tenants"][0]["users_count"] == 3

    async def test_portfolio_empty(self, api_client, mock_db, superadmin_headers):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await api_client.get(
            "/api/v1/superadmin/tenants/portfolio", headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["tenants"] == []
        assert data["total"] == 0

    async def test_portfolio_pagination_params(self, api_client, mock_db, superadmin_headers):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await api_client.get(
            "/api/v1/superadmin/tenants/portfolio?skip=0&limit=10",
            headers=superadmin_headers,
        )
        assert r.status_code == 200

    async def test_portfolio_sort_by_name(self, api_client, mock_db, superadmin_headers):
        mock_db.execute = AsyncMock(return_value=make_scalars_result([]))
        r = await api_client.get(
            "/api/v1/superadmin/tenants/portfolio?sort_by=name&sort_order=asc",
            headers=superadmin_headers,
        )
        assert r.status_code == 200


class TestSuperAdminSystemHealth:
    """GET /api/v1/superadmin/system/health."""

    async def test_health_no_auth(self, api_client):
        r = await api_client.get("/api/v1/superadmin/system/health")
        assert r.status_code == 401

    async def test_health_non_superadmin(self, api_client, admin_headers):
        r = await api_client.get(
            "/api/v1/superadmin/system/health", headers=admin_headers,
        )
        assert r.status_code == 403

    async def test_health_happy(self, api_client, mock_db, superadmin_headers):
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(return_value=5)
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            r = await api_client.get(
                "/api/v1/superadmin/system/health", headers=superadmin_headers,
            )
        assert r.status_code == 200
        data = r.json()["data"]
        assert "services" in data
        assert "queue" in data
        assert data["services"]["redis"] == "healthy"


class TestSuperAdminChurnRisks:
    """GET /api/v1/superadmin/churn/risks."""

    async def test_churn_no_auth(self, api_client):
        r = await api_client.get("/api/v1/superadmin/churn/risks")
        assert r.status_code == 401

    async def test_churn_non_superadmin(self, api_client, admin_headers):
        r = await api_client.get(
            "/api/v1/superadmin/churn/risks", headers=admin_headers,
        )
        assert r.status_code == 403

    async def test_churn_happy_with_risky_tenant(self, api_client, mock_db, superadmin_headers):
        tenant = _fake_tenant()
        tenant.last_activity_at = None
        tenant.onboarding_completed = False
        mock_db.execute = AsyncMock(return_value=make_scalars_result([tenant]))

        r = await api_client.get(
            "/api/v1/superadmin/churn/risks?min_risk=0.1",
            headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert "at_risk_tenants" in data
        assert "total_mrr_at_risk" in data
        assert data["total_count"] >= 1

    async def test_churn_empty_with_high_threshold(self, api_client, mock_db, superadmin_headers):
        tenant = _fake_tenant()
        tenant.last_activity_at = _NOW
        tenant.health_score = 95
        tenant.onboarding_completed = True
        mock_db.execute = AsyncMock(return_value=make_scalars_result([tenant]))

        r = await api_client.get(
            "/api/v1/superadmin/churn/risks?min_risk=0.99",
            headers=superadmin_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_count"] == 0


# ============================================================================
# FEATURE 14 -- SUPER ADMIN ANALYTICS
# ============================================================================
#
# superadmin_analytics.py router has prefix="/superadmin" and is mounted
# at /api/v1/superadmin/analytics, giving:
#   /api/v1/superadmin/analytics/superadmin/<endpoint>
#
# Auth check: getattr(request.state, "is_superadmin", False)
# TenantMiddleware sets request.state.role but NOT is_superadmin.
# Non-superadmin users get 403. Even superadmin users get 403 because
# is_superadmin is never set. We test auth-rejection behavior and also
# test with a patched is_superadmin flag.

class TestSuperAdminAnalyticsPlatformOverview:
    """GET /api/v1/superadmin/analytics/superadmin/platform-overview."""

    _URL = "/api/v1/superadmin/analytics/superadmin/platform-overview"

    async def test_no_auth(self, api_client):
        r = await api_client.get(self._URL)
        assert r.status_code == 401

    async def test_non_superadmin_forbidden(self, api_client, admin_headers):
        r = await api_client.get(self._URL, headers=admin_headers)
        assert r.status_code == 403

    async def test_superadmin_access_allowed(
        self, api_client, superadmin_headers, mock_db,
    ):
        """
        Middleware now sets is_superadmin=True for role=superadmin,
        so the endpoint is reachable and returns 200.
        """
        from unittest.mock import MagicMock

        row = MagicMock(total=0, applied=0, failed=0)
        scalar_r = MagicMock(); scalar_r.scalar.return_value = 0
        first_r = MagicMock(); first_r.first.return_value = row
        empty_iter = MagicMock(); empty_iter.__iter__ = lambda s: iter([])
        mock_db.execute.side_effect = [scalar_r, first_r, empty_iter, empty_iter]

        r = await api_client.get(self._URL, headers=superadmin_headers)
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestSuperAdminAnalyticsTenantProfitability:
    """GET /api/v1/superadmin/analytics/superadmin/tenant-profitability."""

    _URL = "/api/v1/superadmin/analytics/superadmin/tenant-profitability"

    async def test_no_auth(self, api_client):
        r = await api_client.get(self._URL)
        assert r.status_code == 401

    async def test_non_superadmin_forbidden(self, api_client, admin_headers):
        r = await api_client.get(self._URL, headers=admin_headers)
        assert r.status_code == 403

    async def test_superadmin_access_allowed(
        self, api_client, superadmin_headers, mock_db,
    ):
        """Superadmin can access tenant profitability."""
        from unittest.mock import MagicMock
        empty_iter = MagicMock(); empty_iter.__iter__ = lambda s: iter([])
        mock_db.execute.side_effect = [empty_iter, empty_iter]

        r = await api_client.get(self._URL, headers=superadmin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_tenants"] == 0
        assert data["tenants"] == []


class TestSuperAdminAnalyticsSignalHealthTrends:
    """GET /api/v1/superadmin/analytics/superadmin/signal-health-trends."""

    _URL = "/api/v1/superadmin/analytics/superadmin/signal-health-trends"

    async def test_no_auth(self, api_client):
        r = await api_client.get(self._URL)
        assert r.status_code == 401

    async def test_non_superadmin_forbidden(self, api_client, admin_headers):
        r = await api_client.get(self._URL, headers=admin_headers)
        assert r.status_code == 403

    async def test_superadmin_access_allowed(
        self, api_client, superadmin_headers, mock_db,
    ):
        """Superadmin can access signal health trends."""
        from unittest.mock import MagicMock
        empty_iter = MagicMock(); empty_iter.__iter__ = lambda s: iter([])
        mock_db.execute.return_value = empty_iter

        r = await api_client.get(self._URL, headers=superadmin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["trend_direction"] == "insufficient_data"


class TestSuperAdminAnalyticsActionsAnalytics:
    """GET /api/v1/superadmin/analytics/superadmin/actions-analytics."""

    _URL = "/api/v1/superadmin/analytics/superadmin/actions-analytics"

    async def test_no_auth(self, api_client):
        r = await api_client.get(self._URL)
        assert r.status_code == 401

    async def test_non_superadmin_forbidden(self, api_client, admin_headers):
        r = await api_client.get(self._URL, headers=admin_headers)
        assert r.status_code == 403

    async def test_superadmin_access_allowed(
        self, api_client, superadmin_headers, mock_db,
    ):
        """Superadmin can access actions analytics."""
        from unittest.mock import MagicMock
        empty_iter = MagicMock(); empty_iter.__iter__ = lambda s: iter([])
        mock_db.execute.return_value = empty_iter

        r = await api_client.get(self._URL, headers=superadmin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_actions"] == 0


# ============================================================================
# Unit tests for helper functions (Feature 14)
# ============================================================================

class TestCalculateHealthScore:
    """Unit tests for superadmin_analytics.calculate_health_score."""

    def test_both_none(self):
        from app.api.v1.endpoints.superadmin_analytics import calculate_health_score
        assert calculate_health_score(None, None) == 0

    def test_only_emq(self):
        from app.api.v1.endpoints.superadmin_analytics import calculate_health_score
        score = calculate_health_score(80.0, None)
        assert score == round(80.0 * 0.7, 1)

    def test_only_event_loss(self):
        from app.api.v1.endpoints.superadmin_analytics import calculate_health_score
        score = calculate_health_score(None, 10.0)
        assert score == round((100 - 10.0) * 0.3, 1)

    def test_both_present(self):
        from app.api.v1.endpoints.superadmin_analytics import calculate_health_score
        score = calculate_health_score(90.0, 5.0)
        expected = round(90.0 * 0.7 + (100 - 5.0) * 0.3, 1)
        assert score == expected

    def test_zero_values(self):
        from app.api.v1.endpoints.superadmin_analytics import calculate_health_score
        score = calculate_health_score(0.0, 0.0)
        expected = round(0.0 * 0.7 + (100 - 0.0) * 0.3, 1)
        assert score == expected


class TestCalculateChurnRisk:
    """Unit tests for superadmin.calculate_churn_risk."""

    def test_healthy_tenant(self):
        from app.api.v1.endpoints.superadmin import calculate_churn_risk
        t = _fake_tenant()
        t.last_activity_at = _NOW
        t.health_score = 95
        t.onboarding_completed = True
        risk, factors = calculate_churn_risk(t)
        assert risk < 0.3
        assert isinstance(factors, list)

    def test_inactive_tenant(self):
        from app.api.v1.endpoints.superadmin import calculate_churn_risk
        t = _fake_tenant()
        t.last_activity_at = None
        t.health_score = 60
        t.onboarding_completed = False
        risk, factors = calculate_churn_risk(t)
        assert risk > 0.3
        assert len(factors) >= 2

    def test_past_due_tenant(self):
        from app.api.v1.endpoints.superadmin import calculate_churn_risk
        t = _fake_tenant()
        t.status = "past_due"
        t.last_activity_at = _NOW
        t.health_score = 90
        t.onboarding_completed = True
        risk, factors = calculate_churn_risk(t)
        assert risk >= 0.25
        assert any("past due" in f.lower() for f in factors)

    def test_cancelled_tenant(self):
        from app.api.v1.endpoints.superadmin import calculate_churn_risk
        t = _fake_tenant()
        t.status = "cancelled"
        t.last_activity_at = _NOW
        t.health_score = 90
        t.onboarding_completed = True
        risk, factors = calculate_churn_risk(t)
        assert risk >= 0.5
        assert any("cancelled" in f.lower() for f in factors)

    def test_risk_clamped_to_1(self):
        from app.api.v1.endpoints.superadmin import calculate_churn_risk
        t = _fake_tenant()
        t.status = "cancelled"
        t.last_activity_at = None
        t.health_score = 30
        t.onboarding_completed = False
        risk, _ = calculate_churn_risk(t)
        assert risk <= 1.0


class TestGetChurnActions:
    """Unit tests for superadmin.get_churn_actions."""

    def test_activity_factor(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Low activity (20 days since last login)"])
        assert any("check-in" in a.lower() or "engagement" in a.lower() for a in actions)

    def test_data_quality_factor(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Data quality issues (health score: 55)"])
        assert any("pipeline" in a.lower() or "support" in a.lower() for a in actions)

    def test_onboarding_factor(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Onboarding not completed"])
        assert any("onboarding" in a.lower() for a in actions)

    def test_trial_factor(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Trial ending in 3 days"])
        assert any("trial" in a.lower() for a in actions)

    def test_payment_factor(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Payment past due"])
        assert any("dunning" in a.lower() or "payment" in a.lower() for a in actions)

    def test_no_matching_factors(self):
        from app.api.v1.endpoints.superadmin import get_churn_actions
        actions = get_churn_actions(["Some unknown factor"])
        assert actions == ["Monitor and gather more data"]
