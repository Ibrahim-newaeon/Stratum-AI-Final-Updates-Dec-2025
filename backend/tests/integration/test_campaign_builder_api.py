# =============================================================================
# Stratum AI - Campaign Builder (Drafts) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed campaign-draft CRUD under
``/tenant/{tenant_id}/campaign-drafts``. The OAuth connect/refresh routes
(external API calls) are out of scope here.
"""

import uuid

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def ad_account(db_session, test_tenant) -> dict:
    """Seed an enabled ad account (with its platform connection) for drafts."""
    from app.models.campaign_builder import (
        TenantAdAccount,
        TenantPlatformConnection,
    )

    connection = TenantPlatformConnection(
        tenant_id=test_tenant["id"],
        platform="meta",
        status="connected",
    )
    db_session.add(connection)
    await db_session.flush()

    account = TenantAdAccount(
        tenant_id=test_tenant["id"],
        connection_id=connection.id,
        platform="meta",
        platform_account_id="act_123456",
        name="Test Ad Account",
        currency="USD",
        timezone="UTC",
        is_enabled=True,
    )
    db_session.add(account)
    await db_session.flush()

    return {"id": str(account.id), "platform": "meta"}


def _base(test_tenant) -> str:
    return f"/api/v1/campaign-builder/tenant/{test_tenant['id']}/campaign-drafts"


def _payload(ad_account, **overrides) -> dict:
    body = {
        "platform": "meta",
        "ad_account_id": ad_account["id"],
        "name": "Spring Sale Draft",
        "draft_json": {"objective": "conversions", "daily_budget": 100.0},
    }
    body.update(overrides)
    return body


class TestAuth:
    async def test_create_requires_auth(self, client, test_tenant, ad_account):
        resp = await client.post(_base(test_tenant), json=_payload(ad_account))
        assert resp.status_code in (401, 403)

    async def test_wrong_tenant_forbidden(self, authenticated_client, ad_account):
        # Path tenant_id differs from the caller's tenant.
        resp = await authenticated_client.get(
            "/api/v1/campaign-builder/tenant/9999999/campaign-drafts"
        )
        assert resp.status_code == 403


class TestCrud:
    async def test_create_then_get(self, authenticated_client, test_tenant, ad_account):
        created = await authenticated_client.post(
            _base(test_tenant), json=_payload(ad_account)
        )
        assert created.status_code == 200, created.text
        data = created.json()["data"]
        assert data["name"] == "Spring Sale Draft"
        assert data["status"] == "draft"
        assert data["platform"] == "meta"
        draft_id = data["id"]

        got = await authenticated_client.get(f"{_base(test_tenant)}/{draft_id}")
        assert got.status_code == 200
        assert got.json()["data"]["id"] == draft_id

    async def test_create_with_unknown_ad_account_400(
        self, authenticated_client, test_tenant, ad_account
    ):
        resp = await authenticated_client.post(
            _base(test_tenant),
            json=_payload(ad_account, ad_account_id=str(uuid.uuid4())),
        )
        assert resp.status_code == 400

    async def test_list_includes_created(
        self, authenticated_client, test_tenant, ad_account
    ):
        created = await authenticated_client.post(
            _base(test_tenant), json=_payload(ad_account, name="Listed Draft")
        )
        draft_id = created.json()["data"]["id"]

        listed = await authenticated_client.get(_base(test_tenant))
        assert listed.status_code == 200
        assert any(d["id"] == draft_id for d in listed.json()["data"])

    async def test_update(self, authenticated_client, test_tenant, ad_account):
        created = await authenticated_client.post(
            _base(test_tenant), json=_payload(ad_account)
        )
        draft_id = created.json()["data"]["id"]

        resp = await authenticated_client.put(
            f"{_base(test_tenant)}/{draft_id}",
            json={"name": "Renamed Draft"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Renamed Draft"

    async def test_get_missing_404(self, authenticated_client, test_tenant):
        resp = await authenticated_client.get(f"{_base(test_tenant)}/{uuid.uuid4()}")
        assert resp.status_code == 404
