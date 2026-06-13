# =============================================================================
# Stratum AI - GDPR / Compliance API Integration Tests
# =============================================================================
"""Integration tests for the GDPR compliance API.

Exercises the real ASGI app against Postgres + Redis: data export (right
to portability), anonymization (right to be forgotten) with the required
confirmation token, consent updates, and the audit-log read — plus auth
and not-found paths.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = 99999999


@pytest.fixture
def enterprise_plan(monkeypatch):
    """Elevate the test tenant to Enterprise so the GDPR FeatureGate passes.

    GDPR tools are gated behind ``FeatureGate(Feature.GDPR_TOOLS)`` (Enterprise
    only). The conftest autouse fixture reports a Professional subscription;
    requesting this fixture explicitly re-patches the lookup afterwards so the
    gate sees Enterprise. Subscription status stays ACTIVE.
    """
    from app.core import subscription as sub_mod
    from app.core.tiers import SubscriptionTier

    async def _enterprise(tenant_id: int) -> "sub_mod.SubscriptionInfo":
        return sub_mod.SubscriptionInfo(
            tenant_id=tenant_id,
            plan="enterprise",
            tier=SubscriptionTier.ENTERPRISE,
            status=sub_mod.SubscriptionStatus.ACTIVE,
            expires_at=None,
            days_until_expiry=None,
            days_in_grace=None,
            is_access_restricted=False,
            restriction_reason=None,
        )

    monkeypatch.setattr(sub_mod, "get_subscription_info", _enterprise)


# =============================================================================
# Export (right to data portability)
# =============================================================================
class TestExport:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/gdpr/export", json={"user_id": 1})
        assert resp.status_code in {401, 403}

    # Note: the export happy path decrypts the user's Fernet-encrypted PII;
    # the shared test fixtures store plaintext, so the full export payload is
    # exercised at the unit level. Here we cover the route's auth + not-found
    # contract (the not-found check runs before any decryption).

    @pytest.mark.asyncio
    async def test_export_user_not_found(
        self, authenticated_client: AsyncClient, enterprise_plan
    ):
        resp = await authenticated_client.post(
            "/api/v1/gdpr/export", json={"user_id": _MISSING}
        )
        assert resp.status_code == 404


# =============================================================================
# Anonymize (right to be forgotten)
# =============================================================================
class TestAnonymize:
    @pytest.mark.asyncio
    async def test_invalid_confirmation_rejected(
        self, authenticated_client: AsyncClient, test_user: dict, enterprise_plan
    ):
        # confirmation must match the CONFIRM_DELETE pattern → 422.
        resp = await authenticated_client.post(
            "/api/v1/gdpr/anonymize",
            json={"user_id": test_user["id"], "confirmation": "nope"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_anonymize_user_not_found(
        self, authenticated_client: AsyncClient, enterprise_plan
    ):
        resp = await authenticated_client.post(
            "/api/v1/gdpr/anonymize",
            json={"user_id": _MISSING, "confirmation": "CONFIRM_DELETE"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_anonymize_success(
        self, authenticated_client: AsyncClient, test_user: dict, enterprise_plan
    ):
        resp = await authenticated_client.post(
            "/api/v1/gdpr/anonymize",
            json={"user_id": test_user["id"], "confirmation": "CONFIRM_DELETE"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == test_user["id"]
        assert isinstance(data["tables_affected"], list)


# =============================================================================
# Consent + audit logs
# =============================================================================
class TestConsentAndAudit:
    @pytest.mark.asyncio
    async def test_update_consent(
        self, authenticated_client: AsyncClient, enterprise_plan
    ):
        resp = await authenticated_client.post(
            "/api/v1/gdpr/consent",
            params={"consent_marketing": True, "consent_analytics": False},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["consent_marketing"] is True
        assert data["consent_analytics"] is False

    @pytest.mark.asyncio
    async def test_consent_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/gdpr/consent", params={"consent_marketing": True}
        )
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_audit_logs_paginated(
        self, authenticated_client: AsyncClient, enterprise_plan
    ):
        resp = await authenticated_client.get("/api/v1/gdpr/audit-logs")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
