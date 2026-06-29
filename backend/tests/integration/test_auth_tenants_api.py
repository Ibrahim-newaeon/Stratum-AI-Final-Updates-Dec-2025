# =============================================================================
# Stratum AI - Auth Multi-Tenant (list / switch) Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``GET /auth/tenants`` and
``POST /auth/switch-tenant`` — the multi-tenant membership surface. The
authenticated test user is given memberships in two tenants so listing and
switching can be exercised; switching to a non-member tenant is rejected.
"""

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_LIST = "/api/v1/auth/tenants"
_SWITCH = "/api/v1/auth/switch-tenant"


@pytest_asyncio.fixture
async def memberships(db_session, test_user, test_tenant) -> dict:
    """Give the test user a default membership in test_tenant + a 2nd tenant."""
    from app.base_models import Tenant, UserRole, UserTenantMembership

    db_session.add(
        UserTenantMembership(
            user_id=test_user["id"],
            tenant_id=test_tenant["id"],
            role=UserRole.ADMIN,
            is_default=True,
            is_active=True,
        )
    )

    second = Tenant(
        name="Second Tenant",
        slug="second-tenant",
        plan="professional",
        max_users=10,
        max_campaigns=100,
    )
    db_session.add(second)
    await db_session.flush()

    db_session.add(
        UserTenantMembership(
            user_id=test_user["id"],
            tenant_id=second.id,
            role=UserRole.ADMIN,
            is_default=False,
            is_active=True,
        )
    )
    await db_session.flush()
    return {"primary": test_tenant["id"], "second": second.id}


class TestListTenants:
    async def test_requires_auth(self, client):
        resp = await client.get(_LIST)
        assert resp.status_code == 401

    async def test_lists_member_tenants(self, authenticated_client, memberships):
        resp = await authenticated_client.get(_LIST)
        assert resp.status_code == 200, resp.text
        ids = {t["tenant_id"] for t in resp.json()["data"]}
        assert memberships["primary"] in ids
        assert memberships["second"] in ids


class TestSwitchTenant:
    async def test_switch_to_member_tenant_issues_token(
        self, authenticated_client, memberships
    ):
        resp = await authenticated_client.post(
            _SWITCH, json={"tenant_id": memberships["second"]}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["access_token"]

    async def test_switch_to_non_member_tenant_forbidden(
        self, authenticated_client, memberships
    ):
        resp = await authenticated_client.post(_SWITCH, json={"tenant_id": 99999999})
        assert resp.status_code == 403
