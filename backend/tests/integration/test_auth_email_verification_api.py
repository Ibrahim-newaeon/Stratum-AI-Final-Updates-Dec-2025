# =============================================================================
# Stratum AI - Email Verification Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/verify-email`` and
``POST /auth/resend-verification`` — Redis-backed verification tokens,
one-time use, enumeration-safe resends, and the welcome-email seam.
Verification tokens are seeded directly into Redis (plain, exactly as
resend-verification stores them); the resend round trip captures the token
from a stubbed email service and drives it through verify-email.
"""

import secrets

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_VERIFY = "/api/v1/auth/verify-email"
_RESEND = "/api/v1/auth/resend-verification"
_EMAIL = "verify-me@example.com"


@pytest_asyncio.fixture
async def unverified_user(db_session, test_tenant) -> dict:
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(_EMAIL),
        email_hash=hash_pii_for_lookup(_EMAIL),
        password_hash=get_password_hash("Testpassword123"),
        full_name=encrypt_pii("Verify User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id}


@pytest_asyncio.fixture
async def plain_name_user(db_session, test_tenant) -> dict:
    """Unverified user whose full_name is NOT encrypted → decrypt_pii fails
    and the endpoints fall back to the 'there' display name."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "plain-name@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash("Testpassword123"),
        full_name="Plain Name",  # deliberately not Fernet-encrypted
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": email}


async def _seed_verify_token(user_id: int) -> str:
    """Store a verification token -> user_id, as resend-verification does."""
    from app.api.v1.endpoints.auth import (
        EMAIL_VERIFICATION_PREFIX,
        get_redis_client,
    )

    token = secrets.token_urlsafe(32)
    rc = await get_redis_client()
    try:
        await rc.setex(f"{EMAIL_VERIFICATION_PREFIX}{token}", 600, str(user_id))
    finally:
        await rc.close()
    return token


class _StubEmailService:
    def __init__(self):
        self.welcomes: list = []
        self.verifications: list = []
        self.raise_exc: Exception | None = None

    def send_welcome_email(self, **kwargs):
        if self.raise_exc:
            raise self.raise_exc
        self.welcomes.append(kwargs)
        return True

    def send_verification_email(self, **kwargs):
        if self.raise_exc:
            raise self.raise_exc
        self.verifications.append(kwargs)
        return True


@pytest.fixture
def email_stub(monkeypatch) -> _StubEmailService:
    import app.api.v1.endpoints.auth as auth_module

    stub = _StubEmailService()
    monkeypatch.setattr(auth_module, "get_email_service", lambda: stub)
    return stub


@pytest.fixture
def redis_down(monkeypatch):
    import app.api.v1.endpoints.auth as auth_module

    async def _boom():
        raise ConnectionError("redis down (test)")

    monkeypatch.setattr(auth_module, "get_redis_client", _boom)


class TestVerifyEmail:
    async def test_valid_token_verifies_and_welcomes(
        self, client, db_session, unverified_user, email_stub
    ):
        token = await _seed_verify_token(unverified_user["id"])
        resp = await client.post(_VERIFY, json={"token": token})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["success"] is True

        from sqlalchemy import select

        from app.base_models import User

        user = (
            await db_session.execute(
                select(User).where(User.id == unverified_user["id"])
            )
        ).scalar_one()
        await db_session.refresh(user)
        assert user.is_verified is True

        assert len(email_stub.welcomes) == 1
        assert email_stub.welcomes[0]["to_email"] == _EMAIL

    async def test_token_is_single_use(self, client, unverified_user, email_stub):
        token = await _seed_verify_token(unverified_user["id"])
        first = await client.post(_VERIFY, json={"token": token})
        assert first.status_code == 200
        second = await client.post(_VERIFY, json={"token": token})
        assert second.status_code == 400

    async def test_invalid_token_400(self, client):
        resp = await client.post(_VERIFY, json={"token": "never-seeded"})
        assert resp.status_code == 400

    async def test_token_for_unknown_user_404(self, client):
        token = await _seed_verify_token(99999999)
        resp = await client.post(_VERIFY, json={"token": token})
        assert resp.status_code == 404

    async def test_already_verified_short_circuits(
        self, client, db_session, unverified_user, email_stub
    ):
        from sqlalchemy import update

        from app.base_models import User

        await db_session.execute(
            update(User)
            .where(User.id == unverified_user["id"])
            .values(is_verified=True)
        )
        await db_session.flush()

        token = await _seed_verify_token(unverified_user["id"])
        resp = await client.post(_VERIFY, json={"token": token})
        assert resp.status_code == 200
        assert "already verified" in resp.json()["data"]["message"].lower()
        assert email_stub.welcomes == []

    async def test_welcome_email_failure_does_not_block(
        self, client, unverified_user, email_stub
    ):
        email_stub.raise_exc = ConnectionError("smtp down")
        token = await _seed_verify_token(unverified_user["id"])
        resp = await client.post(_VERIFY, json={"token": token})
        assert resp.status_code == 200

    async def test_redis_down_500(self, client, redis_down):
        resp = await client.post(_VERIFY, json={"token": "whatever"})
        assert resp.status_code == 500


class TestResendVerification:
    async def test_unknown_email_does_not_enumerate(self, client):
        resp = await client.post(_RESEND, json={"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert resp.json()["data"]["success"] is True

    async def test_already_verified_short_circuits(
        self, client, db_session, unverified_user, email_stub
    ):
        from sqlalchemy import update

        from app.base_models import User

        await db_session.execute(
            update(User)
            .where(User.id == unverified_user["id"])
            .values(is_verified=True)
        )
        await db_session.flush()

        resp = await client.post(_RESEND, json={"email": _EMAIL})
        assert resp.status_code == 200
        assert "already verified" in resp.json()["data"]["message"].lower()
        assert email_stub.verifications == []

    async def test_resend_then_verify_round_trip(
        self, client, unverified_user, email_stub
    ):
        resp = await client.post(_RESEND, json={"email": _EMAIL})
        assert resp.status_code == 200, resp.text

        assert len(email_stub.verifications) == 1
        sent = email_stub.verifications[0]
        assert sent["to_email"] == _EMAIL
        assert sent["user_name"] == "Verify User"

        verify = await client.post(_VERIFY, json={"token": sent["token"]})
        assert verify.status_code == 200, verify.text

    async def test_undecryptable_name_falls_back(
        self, client, plain_name_user, email_stub
    ):
        resp = await client.post(_RESEND, json={"email": plain_name_user["email"]})
        assert resp.status_code == 200
        assert len(email_stub.verifications) == 1
        assert email_stub.verifications[0]["user_name"] == "there"

    async def test_redis_down_500(self, client, unverified_user, redis_down):
        resp = await client.post(_RESEND, json={"email": _EMAIL})
        assert resp.status_code == 500
