# =============================================================================
# Stratum AI - Auth Registration Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/register`` — the verified-signup flow
that auto-provisions a tenant + admin user + membership on a 14-day Starter
trial. Registration consumes a one-time signup-verification token from
Redis (seeded here to stand in for the prior email/WhatsApp OTP step).
"""

import uuid

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_URL = "/api/v1/auth/register"


@pytest_asyncio.fixture
async def verification_token():
    """Seed a one-time signup-verification token in Redis (consumed by register)."""
    import redis.asyncio as aioredis

    from app.api.v1.endpoints.auth import SIGNUP_VERIFY_PREFIX
    from app.core.config import settings

    token = uuid.uuid4().hex
    client = aioredis.from_url(settings.redis_url)
    await client.set(f"{SIGNUP_VERIFY_PREFIX}{token}", "verified", ex=600)
    try:
        yield token
    finally:
        await client.delete(f"{SIGNUP_VERIFY_PREFIX}{token}")
        await client.close()


def _payload(token: str, **overrides) -> dict:
    body = {
        "email": f"signup_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Testpassword123",
        "full_name": "New User",
        "verification_token": token,
    }
    body.update(overrides)
    return body


class TestRegister:
    async def test_invalid_token_rejected(self, client):
        # No Redis token seeded -> the verification check fails.
        resp = await client.post(_URL, json=_payload("does-not-exist"))
        assert resp.status_code == 400

    async def test_register_provisions_user_and_tenant(
        self, client, verification_token
    ):
        payload = _payload(verification_token)
        resp = await client.post(_URL, json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["email"] == payload["email"]
        assert data["role"] == "admin"
        assert data["is_verified"] is True
        assert data["tenant_id"]

    async def test_duplicate_email_rejected(self, client, verification_token):
        payload = _payload(verification_token)

        first = await client.post(_URL, json=payload)
        assert first.status_code == 200

        # A second registration with the same email is rejected (the token was
        # already consumed, so reseed via the same value is gone — seed a fresh
        # one to reach the duplicate-email check rather than the token check).
        import redis.asyncio as aioredis

        from app.api.v1.endpoints.auth import SIGNUP_VERIFY_PREFIX
        from app.core.config import settings

        token2 = uuid.uuid4().hex
        rc = aioredis.from_url(settings.redis_url)
        await rc.set(f"{SIGNUP_VERIFY_PREFIX}{token2}", "verified", ex=600)
        await rc.close()

        payload["verification_token"] = token2
        second = await client.post(_URL, json=payload)
        assert second.status_code == 400
        assert "already registered" in second.json()["detail"].lower()
