# =============================================================================
# Stratum AI - Inbound Webhook Endpoint Integration Tests
# =============================================================================
"""Integration tests for the unauthenticated inbound webhook receivers:

- ``POST /api/v1/webhooks/stripe`` — Stripe event receiver. Verifies the
  ``stripe-signature`` header against ``stripe_webhook_secret``. In the test env
  Stripe is unconfigured (503); patching ``STRIPE_CONFIGURED`` + the secret
  exposes the missing-signature and invalid-signature 400 branches.
- ``POST /api/v1/webhooks/sendgrid`` — SendGrid Event Webhook. Verified by a URL
  ``?token=`` matched (constant-time) against ``sendgrid_webhook_token``.

These pin the signature/token verification contracts — the security-critical
branches — without needing live Stripe/SendGrid credentials.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_STRIPE = "/api/v1/webhooks/stripe"
_SENDGRID = "/api/v1/webhooks/sendgrid"


class TestStripeWebhook:
    async def test_unconfigured_503(self, client: AsyncClient, monkeypatch):
        # Default test env: Stripe not configured -> 503 before any parsing.
        from app.services import stripe_service

        monkeypatch.setattr(stripe_service, "STRIPE_CONFIGURED", False)
        resp = await client.post(_STRIPE, content=b"{}")
        assert resp.status_code == 503, resp.text

    async def test_missing_signature_400(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings
        from app.services import stripe_service

        monkeypatch.setattr(stripe_service, "STRIPE_CONFIGURED", True)
        monkeypatch.setattr(
            settings, "stripe_webhook_secret", "whsec_test", raising=False
        )

        resp = await client.post(_STRIPE, content=b"{}")
        assert resp.status_code == 400, resp.text
        assert "signature" in resp.json()["detail"].lower()

    async def test_invalid_signature_400(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings
        from app.services import stripe_service

        monkeypatch.setattr(stripe_service, "STRIPE_CONFIGURED", True)
        monkeypatch.setattr(
            settings, "stripe_webhook_secret", "whsec_test", raising=False
        )

        resp = await client.post(
            _STRIPE,
            content=b'{"id": "evt_1", "type": "ping"}',
            headers={"stripe-signature": "t=123,v1=deadbeef"},
        )
        assert resp.status_code == 400, resp.text

    async def test_secret_not_configured_503(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings
        from app.services import stripe_service

        monkeypatch.setattr(stripe_service, "STRIPE_CONFIGURED", True)
        monkeypatch.setattr(settings, "stripe_webhook_secret", "", raising=False)

        resp = await client.post(
            _STRIPE,
            content=b"{}",
            headers={"stripe-signature": "t=123,v1=deadbeef"},
        )
        assert resp.status_code == 503, resp.text


class TestSendgridWebhook:
    async def test_wrong_token_401(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(
            settings, "sendgrid_webhook_token", "sg_secret", raising=False
        )
        # No token query param -> verification fails.
        resp = await client.post(_SENDGRID, json=[])
        assert resp.status_code == 401, resp.text

    async def test_valid_token_empty_batch_ok(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(
            settings, "sendgrid_webhook_token", "sg_secret", raising=False
        )
        resp = await client.post(f"{_SENDGRID}?token=sg_secret", json=[])
        assert resp.status_code == 200, resp.text

    async def test_valid_token_non_list_400(self, client: AsyncClient, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(
            settings, "sendgrid_webhook_token", "sg_secret", raising=False
        )
        # SendGrid posts a JSON array; an object should be rejected.
        resp = await client.post(f"{_SENDGRID}?token=sg_secret", json={"not": "a list"})
        assert resp.status_code == 400, resp.text
