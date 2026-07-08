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

    async def test_token_for_unknown_user_404(self, client):
        token = await _seed_reset_token(99999999)
        resp = await client.post(_RESET, json={"token": token, "password": _NEW})
        assert resp.status_code == 404

    async def test_redis_down_500(self, client, monkeypatch):
        import app.api.v1.endpoints.auth as auth_module

        async def _boom():
            raise ConnectionError("redis down (test)")

        monkeypatch.setattr(auth_module, "get_redis_client", _boom)
        resp = await client.post(_RESET, json={"token": "whatever", "password": _NEW})
        assert resp.status_code == 500


@pytest_asyncio.fixture
async def nameless_user(db_session, test_tenant) -> dict:
    """Reset-eligible user with no full_name (skips the display-name decrypt)."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "nameless-reset@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash(_OLD),
        full_name=None,
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": email}


@pytest_asyncio.fixture
async def plain_name_user(db_session, test_tenant) -> dict:
    """User whose full_name is NOT Fernet-encrypted → decrypt_pii raises and
    the endpoint falls back to the 'there' display name."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "plain-name-reset@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash(_OLD),
        full_name="Plain Name",  # deliberately not encrypted
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": email}


class _StubEmailService:
    def __init__(self):
        self.resets: list = []
        self.raise_exc: Exception | None = None

    def send_password_reset_email(self, **kwargs):
        if self.raise_exc:
            raise self.raise_exc
        self.resets.append(kwargs)
        return True


@pytest.fixture
def email_stub(monkeypatch) -> _StubEmailService:
    import app.api.v1.endpoints.auth as auth_module

    stub = _StubEmailService()
    monkeypatch.setattr(auth_module, "get_email_service", lambda: stub)
    return stub


class TestForgotPasswordDelivery:
    async def test_email_delivery_carries_display_name(
        self, client, reset_user, email_stub
    ):
        resp = await client.post(_FORGOT, json={"email": _EMAIL})
        assert resp.status_code == 200, resp.text
        assert len(email_stub.resets) == 1
        sent = email_stub.resets[0]
        assert sent["to_email"] == _EMAIL
        assert sent["user_name"] == "Reset User"
        assert sent["token"]

    async def test_undecryptable_name_falls_back(
        self, client, plain_name_user, email_stub
    ):
        resp = await client.post(_FORGOT, json={"email": plain_name_user["email"]})
        assert resp.status_code == 200
        assert email_stub.resets[0]["user_name"] == "there"

    async def test_user_without_name_gets_empty_name(
        self, client, nameless_user, email_stub
    ):
        resp = await client.post(_FORGOT, json={"email": nameless_user["email"]})
        assert resp.status_code == 200
        assert email_stub.resets[0]["user_name"] == ""

    async def test_email_send_failure_does_not_block(
        self, client, reset_user, email_stub
    ):
        email_stub.raise_exc = ConnectionError("smtp down (test)")
        resp = await client.post(_FORGOT, json={"email": _EMAIL})
        assert resp.status_code == 200

    async def test_whatsapp_delivery_not_configured_still_succeeds(
        self, client, reset_user
    ):
        # WhatsApp creds are absent in the test env → the background sender
        # logs and returns; the request itself must still succeed.
        resp = await client.post(
            _FORGOT,
            json={
                "email": _EMAIL,
                "delivery_method": "whatsapp",
                "phone_number": "+15550001111",
            },
        )
        assert resp.status_code == 200

    async def test_whatsapp_delivery_sends_reset_link(
        self, client, reset_user, monkeypatch
    ):
        import app.api.v1.endpoints.auth as auth_module

        sent: list = []

        class _StubWhatsAppClient:
            async def send_text_message(self, **kwargs):
                sent.append(kwargs)

        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
        monkeypatch.setattr(
            auth_module, "get_whatsapp_client", lambda: _StubWhatsAppClient()
        )

        resp = await client.post(
            _FORGOT,
            json={
                "email": _EMAIL,
                "delivery_method": "whatsapp",
                "phone_number": "+15550001111",
            },
        )
        assert resp.status_code == 200, resp.text
        assert len(sent) == 1
        assert "reset-password?token=" in sent[0]["message"]
        assert sent[0]["recipient_phone"] == "15550001111"

    async def test_whatsapp_send_failure_does_not_block(
        self, client, reset_user, monkeypatch
    ):
        import app.api.v1.endpoints.auth as auth_module

        class _BoomWhatsAppClient:
            async def send_text_message(self, **kwargs):
                raise ConnectionError("network down (test)")

        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
        monkeypatch.setattr(
            auth_module, "get_whatsapp_client", lambda: _BoomWhatsAppClient()
        )

        resp = await client.post(
            _FORGOT,
            json={
                "email": _EMAIL,
                "delivery_method": "whatsapp",
                "phone_number": "+15550001111",
            },
        )
        assert resp.status_code == 200

    async def test_redis_down_500(self, client, reset_user, monkeypatch):
        # Token storage fails hard (unlike delivery, which is best-effort).
        import app.api.v1.endpoints.auth as auth_module

        async def _boom():
            raise ConnectionError("redis down (test)")

        monkeypatch.setattr(auth_module, "get_redis_client", _boom)
        resp = await client.post(_FORGOT, json={"email": _EMAIL})
        assert resp.status_code == 500
