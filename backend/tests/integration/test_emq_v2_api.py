# =============================================================================
# Stratum AI - EMQ v2 Playbook Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed EMQ playbook item-state endpoints
under ``/tenants/{tenant_id}/emq/playbook``. The router is guarded by
get_current_user and validate_tenant_access; the read-only EMQ score /
incident routes are out of scope here.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ITEM = "enhanced_conversions"


def _base(test_tenant) -> str:
    return f"/api/v1/tenants/{test_tenant['id']}/emq/playbook"


class TestAuth:
    async def test_patch_requires_auth(self, client, test_tenant):
        resp = await client.patch(
            f"{_base(test_tenant)}/{_ITEM}", json={"status": "in_progress"}
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_forbidden(self, authenticated_client):
        resp = await authenticated_client.patch(
            "/api/v1/tenants/9999999/emq/playbook/enhanced_conversions",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 403


class TestPlaybookItemState:
    async def test_patch_upserts_status(self, authenticated_client, test_tenant):
        resp = await authenticated_client.patch(
            f"{_base(test_tenant)}/{_ITEM}", json={"status": "in_progress"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "in_progress"

    async def test_unknown_item_404(self, authenticated_client, test_tenant):
        resp = await authenticated_client.patch(
            f"{_base(test_tenant)}/not_a_real_item", json={"status": "completed"}
        )
        assert resp.status_code == 404

    async def test_state_persists_across_requests(
        self, authenticated_client, test_tenant
    ):
        # First set the owner ...
        first = await authenticated_client.patch(
            f"{_base(test_tenant)}/{_ITEM}", json={"owner": "alice"}
        )
        assert first.status_code == 200
        assert first.json()["data"]["owner"] == "alice"

        # ... then update only the status; the owner must survive (read from DB).
        second = await authenticated_client.patch(
            f"{_base(test_tenant)}/{_ITEM}", json={"status": "completed"}
        )
        assert second.status_code == 200
        body = second.json()["data"]
        assert body["status"] == "completed"
        assert body["owner"] == "alice"

    async def test_invalid_status_422(self, authenticated_client, test_tenant):
        resp = await authenticated_client.patch(
            f"{_base(test_tenant)}/{_ITEM}", json={"status": "bogus"}
        )
        assert resp.status_code == 422


class TestPlaybookList:
    async def test_get_playbook_returns_list(self, authenticated_client, test_tenant):
        resp = await authenticated_client.get(_base(test_tenant))
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
