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


class TestRegisterPasswordPolicy:
    @pytest.mark.parametrize(
        "weak",
        [
            "alllowercase1",  # no uppercase
            "ALLUPPERCASE1",  # no lowercase
            "NoDigitsHere",  # no digit
        ],
    )
    async def test_weak_password_rejected(self, client, weak):
        # Pydantic validator rejects before any token/DB work happens.
        resp = await client.post(_URL, json=_payload("junk-token", password=weak))
        assert resp.status_code == 422


class TestRegisterFailureModes:
    async def test_redis_down_500(self, client, monkeypatch):
        import app.api.v1.endpoints.auth as auth_module

        async def _boom():
            raise ConnectionError("redis down (test)")

        monkeypatch.setattr(auth_module, "get_redis_client", _boom)

        resp = await client.post(_URL, json=_payload("any-token"))
        assert resp.status_code == 500

    async def test_welcome_email_failure_does_not_block(
        self, client, verification_token, monkeypatch
    ):
        import app.api.v1.endpoints.auth as auth_module

        class _BoomEmailService:
            def send_welcome_email(self, **kwargs):
                raise ConnectionError("smtp down (test)")

        monkeypatch.setattr(
            auth_module, "get_email_service", lambda: _BoomEmailService()
        )

        resp = await client.post(_URL, json=_payload(verification_token))
        assert resp.status_code == 200, resp.text
