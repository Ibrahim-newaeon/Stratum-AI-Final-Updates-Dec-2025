# =============================================================================
# Stratum AI - Enterprise Compliance Endpoint Integration Tests
# =============================================================================
"""Integration tests for the compliance surface under
``/api/v1/compliance/admin/compliance/...``: audit-log search/summary, RBAC
role listing, and GDPR retention-policy + purge preview.

The audit-log endpoints query the real ``audit_logs`` table. They previously
SELECT/filter/GROUP-BY'd columns (``user_email``/``details``/``severity``)
that don't exist on the table (per migration 001) and 500'd on every call;
the handlers now read the actual change columns and derive severity from the
action. These tests seed real ``AuditLog`` rows and assert that behaviour.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/compliance/admin/compliance"


async def _seed_audit(
    db: AsyncSession,
    tenant_id: int,
    *,
    action,
    resource_type: str = "campaign",
    resource_id: str = "1",
    new_value: dict | None = None,
):
    from app.base_models import AuditLog

    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        new_value=new_value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return entry


# =============================================================================
# Audit log search
# =============================================================================
class TestAuditLogSearch:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/audit-log/search", json={})
        assert resp.status_code == 401

    async def test_search_returns_seeded_entry(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        from app.base_models import AuditAction

        await _seed_audit(
            db_session,
            test_tenant["id"],
            action=AuditAction.DELETE,
            resource_type="campaign",
            new_value={"name": "Removed Campaign"},
        )
        resp = await authenticated_client.post(f"{_BASE}/audit-log/search", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] >= 1
        entry = data["entries"][0]
        # DELETE -> derived "critical"; details composed from new_value.
        assert entry["severity"] == "critical"
        assert entry["details"]["new_value"] == {"name": "Removed Campaign"}
        assert entry["user_email"] is None

    async def test_severity_filter_maps_to_actions(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        from app.base_models import AuditAction

        await _seed_audit(
            db_session, test_tenant["id"], action=AuditAction.DELETE, resource_id="d1"
        )
        await _seed_audit(
            db_session, test_tenant["id"], action=AuditAction.LOGIN, resource_id="l1"
        )

        crit = await authenticated_client.post(
            f"{_BASE}/audit-log/search", json={"severity": ["critical"]}
        )
        assert crit.status_code == 200, crit.text
        crit_actions = {e["action"] for e in crit.json()["data"]["entries"]}
        assert crit_actions == {"delete"}

        info = await authenticated_client.post(
            f"{_BASE}/audit-log/search", json={"severity": ["info"]}
        )
        assert info.status_code == 200, info.text
        info_actions = {e["action"] for e in info.json()["data"]["entries"]}
        assert "login" in info_actions
        assert "delete" not in info_actions


# =============================================================================
# Audit log summary
# =============================================================================
class TestAuditLogSummary:
    async def test_summary_buckets_by_derived_severity(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        from app.base_models import AuditAction

        await _seed_audit(
            db_session, test_tenant["id"], action=AuditAction.DELETE, resource_id="s1"
        )
        await _seed_audit(
            db_session, test_tenant["id"], action=AuditAction.CREATE, resource_id="s2"
        )
        resp = await authenticated_client.get(f"{_BASE}/audit-log/summary")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["severity_breakdown"].get("critical", 0) >= 1
        assert data["action_breakdown"].get("delete", 0) >= 1
        assert data["total_events"] >= 2


# =============================================================================
# RBAC
# =============================================================================
class TestRBAC:
    async def test_requires_auth(self, client: AsyncClient):
        assert (await client.get(f"{_BASE}/rbac/roles")).status_code == 401

    async def test_lists_built_in_roles(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/rbac/roles")
        assert resp.status_code == 200, resp.text
        ids = {r["id"] for r in resp.json()["data"]}
        assert "super_admin" in ids


# =============================================================================
# GDPR retention + purge preview
# =============================================================================
class TestGDPR:
    async def test_get_retention_policy_defaults(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(f"{_BASE}/gdpr/retention-policy")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["tenant_id"] == test_tenant["id"]
        assert data["profile_retention_days"] == 365

    async def test_update_retention_policy_echoes_tenant(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.put(
            f"{_BASE}/gdpr/retention-policy",
            json={
                "tenant_id": 99,  # must be overridden by server to the real tenant
                "profile_retention_days": 400,
                "event_retention_days": 200,
                "audit_log_retention_days": 2000,
                "campaign_metric_retention_days": 800,
                "auto_purge_enabled": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["tenant_id"] == test_tenant["id"]
        assert data["profile_retention_days"] == 400

    async def test_purge_preview_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/gdpr/purge-preview")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["profiles_to_purge"] == 0
        assert data["audit_logs_to_purge"] == 0
