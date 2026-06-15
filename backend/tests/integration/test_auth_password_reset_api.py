# =============================================================================
# Stratum AI - Auth Password-Reset Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/forgot-password`` and
``POST /auth/reset-password`` — the DB + Redis password-reset flow. The
reset token is normally emailed; here it's seeded directly into Redis
(hashed, as the endpoint stores it) to drive the reset half.
"""

import hashlib

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_FORGOT = "/api/v1/auth/forgot-password"
_RESET = "/api/v1/auth/reset-password"
_EMAIL = "reset-flow@example.com"
_OLD = "Oldpassword123"
_NEW = "Newpassword456"


@pytest_asyncio.fixture
async def reset_user(db_session, test_tenant) -> dict:
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(_EMAIL),
        email_hash=hash_pii_for_lookup(_EMAIL),
        password_hash=get_password_hash(_OLD),
        full_name=encrypt_pii("Reset User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id}


async def _seed_reset_token(user_id: int) -> str:
    """Store a hashed reset token -> user_id in Redis, mirroring the endpoint."""
    import secrets

    from app.api.v1.endpoints.auth import PASSWORD_RESET_PREFIX, get_redis_client

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis = await get_redis_client()
    await redis.setex(f"{PASSWORD_RESET_PREFIX}{token_hash}", 600, str(user_id))
    await redis.close()
    return token


class TestForgotPassword:
    async def test_known_email_succeeds(self, client, reset_user):
        resp = await client.post(_FORGOT, json={"email": _EMAIL})
        assert resp.status_code == 200, resp.text

    async def test_unknown_email_does_not_enumerate(self, client):
        # Unknown emails must return the same success shape (no account
        # enumeration), not a 404.
        resp = await client.post(_FORGOT, json={"email": "nobody-here@example.com"})
        assert resp.status_code == 200


class TestResetPassword:
    async def test_valid_token_resets_password(self, client, reset_user):
        token = await _seed_reset_token(reset_user["id"])
        resp = await client.post(_RESET, json={"token": token, "password": _NEW})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["success"] is True

    async def test_token_is_single_use(self, client, reset_user):
        token = await _seed_reset_token(reset_user["id"])
        first = await client.post(_RESET, json={"token": token, "password": _NEW})
        assert first.status_code == 200
        # The token was consumed on first use -> second attempt is rejected.
        second = await client.post(_RESET, json={"token": token, "password": _NEW})
        assert second.status_code == 400

    async def test_invalid_token_rejected(self, client):
        resp = await client.post(
            _RESET, json={"token": "never-seeded", "password": _NEW}
        )
        assert resp.status_code == 400
