# =============================================================================
# Stratum AI - Payments / Billing Endpoint Integration Tests
# =============================================================================
"""Integration tests for the billing reads under ``/api/v1/payments/...``:
billing overview and subscription. For a tenant with no Stripe customer these
short-circuit to a 'no customer / no subscription' envelope without calling
Stripe, so they're harness-safe.

NOTE: run with the session-scoped event loop CI uses.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/payments"


class TestBillingOverview:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/overview")
        assert resp.status_code in {401, 403}

    async def test_overview_no_customer(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/overview")
        assert resp.status_code == 200, resp.text
        assert resp.json()["has_customer"] is False


class TestSubscription:
    async def test_subscription_no_customer_or_unconfigured(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(f"{_BASE}/subscription")
        # 200 (no Stripe customer -> no subscription) when Stripe is configured,
        # else a graceful 503 when STRIPE_SECRET_KEY is absent (the test env).
        assert resp.status_code in {200, 503}, resp.text
        if resp.status_code == 200:
            assert resp.json()["has_subscription"] is False
