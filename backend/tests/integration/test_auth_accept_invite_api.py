# =============================================================================
# Stratum AI - Invite Accept Endpoint Integration Tests
# =============================================================================
"""Integration tests for the invite flow: ``POST /users/invite`` persists a
hashed invitation token in Redis, and ``POST /auth/accept-invite`` redeems
it — setting the invited user's password/name and marking them verified.

The accept half is driven by seeding a token directly into Redis (hashed,
exactly as the invite endpoint stores it); the full round trip captures the
token from a stubbed email service.
"""

import hashlib

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def _reset_security_redis_pool():
    """app.core.security caches its Redis pool on the first event loop that
    touches it (fine in prod — one long-lived loop per worker). Each test
    here runs on a fresh loop, so a pool cached by an earlier test's login
    would raise 'Event loop is closed'. Drop the cache between tests."""
    yield
    import app.core.security as security

    security._redis_pool = None
    security._redis_pool_lock = None


_INVITE = "/api/v1/users/invite"
_ACCEPT = "/api/v1/auth/accept-invite"
_LOGIN = "/api/v1/auth/login"
_EMAIL = "invited-user@example.com"
_PASSWORD = "Chosenpassword123"


@pytest_asyncio.fixture
async def invited_user(db_session, test_tenant) -> dict:
    """An invited-but-not-yet-accepted user, as /users/invite creates them."""
    import secrets

    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(_EMAIL),
        email_hash=hash_pii_for_lookup(_EMAIL),
        password_hash=get_password_hash(secrets.token_urlsafe(16)),
        full_name=None,
        role=UserRole.ANALYST,
        is_active=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id}


async def _seed_invite_token(user_id: int) -> str:
    """Store a hashed invite token -> user_id in Redis, mirroring /users/invite."""
    import secrets

    from app.api.v1.endpoints.auth import INVITE_TOKEN_PREFIX, get_redis_client

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis = await get_redis_client()
    await redis.setex(f"{INVITE_TOKEN_PREFIX}{token_hash}", 600, str(user_id))
    await redis.close()
    return token


class TestAcceptInvite:
    async def test_valid_token_activates_account(
        self, client, db_session, invited_user
    ):
        token = await _seed_invite_token(invited_user["id"])
        resp = await client.post(
            _ACCEPT,
            json={"token": token, "full_name": "Invited User", "password": _PASSWORD},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["success"] is True

        # The account is now verified with the chosen password
        from sqlalchemy import select

        from app.base_models import User
        from app.core.security import verify_password

        user = (
            await db_session.execute(select(User).where(User.id == invited_user["id"]))
        ).scalar_one()
        await db_session.refresh(user)
        assert user.is_verified is True
        assert verify_password(_PASSWORD, user.password_hash)

    async def test_activated_user_can_log_in(self, client, invited_user):
        token = await _seed_invite_token(invited_user["id"])
        resp = await client.post(
            _ACCEPT,
            json={"token": token, "full_name": "Invited User", "password": _PASSWORD},
        )
        assert resp.status_code == 200, resp.text

        login = await client.post(_LOGIN, json={"email": _EMAIL, "password": _PASSWORD})
        assert login.status_code == 200, login.text

    async def test_token_is_single_use(self, client, invited_user):
        token = await _seed_invite_token(invited_user["id"])
        first = await client.post(
            _ACCEPT,
            json={"token": token, "full_name": "Invited User", "password": _PASSWORD},
        )
        assert first.status_code == 200
        second = await client.post(
            _ACCEPT,
            json={"token": token, "full_name": "Invited User", "password": _PASSWORD},
        )
        assert second.status_code == 400

    async def test_invalid_token_rejected(self, client):
        resp = await client.post(
            _ACCEPT,
            json={
                "token": "never-seeded",
                "full_name": "Nobody",
                "password": _PASSWORD,
            },
        )
        assert resp.status_code == 400

    async def test_weak_password_rejected(self, client, invited_user):
        token = await _seed_invite_token(invited_user["id"])
        resp = await client.post(
            _ACCEPT,
            json={
                "token": token,
                "full_name": "Invited User",
                "password": "alllowercase1",  # no uppercase
            },
        )
        assert resp.status_code == 422


class TestInviteRoundTrip:
    @pytest.fixture
    def captured_invites(self, monkeypatch) -> list:
        """Stub the email service and capture the invite tokens it would send."""
        captured: list = []

        class _StubEmailService:
            def send_user_invite_email(self, **kwargs):
                captured.append(kwargs)

        import app.api.v1.endpoints.users as users_module

        monkeypatch.setattr(
            users_module, "get_email_service", lambda: _StubEmailService()
        )
        return captured

    async def test_invite_then_accept_then_login(
        self, authenticated_client, captured_invites
    ):
        resp = await authenticated_client.post(
            _INVITE,
            json={"email": _EMAIL, "full_name": "Round Trip", "role": "analyst"},
        )
        assert resp.status_code == 200, resp.text
        assert len(captured_invites) == 1
        token = captured_invites[0]["invite_token"]

        accept = await authenticated_client.post(
            _ACCEPT,
            json={"token": token, "full_name": "Round Trip", "password": _PASSWORD},
        )
        assert accept.status_code == 200, accept.text

        login = await authenticated_client.post(
            _LOGIN, json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.status_code == 200, login.text

    async def test_reinvite_pending_user_reissues_token(
        self, authenticated_client, captured_invites
    ):
        first = await authenticated_client.post(
            _INVITE,
            json={"email": _EMAIL, "full_name": "Round Trip", "role": "analyst"},
        )
        assert first.status_code == 200, first.text

        # Same email, invite never accepted -> re-invite must succeed with a
        # fresh token (a lost email must be resendable), not 400.
        second = await authenticated_client.post(
            _INVITE,
            json={"email": _EMAIL, "full_name": "Round Trip", "role": "analyst"},
        )
        assert second.status_code == 200, second.text
        assert len(captured_invites) == 2
        assert (
            captured_invites[0]["invite_token"] != captured_invites[1]["invite_token"]
        )

        # The refreshed token works
        accept = await authenticated_client.post(
            _ACCEPT,
            json={
                "token": captured_invites[1]["invite_token"],
                "full_name": "Round Trip",
                "password": _PASSWORD,
            },
        )
        assert accept.status_code == 200, accept.text

    async def test_accepted_user_cannot_be_reinvited(
        self, authenticated_client, captured_invites
    ):
        resp = await authenticated_client.post(
            _INVITE,
            json={"email": _EMAIL, "full_name": "Round Trip", "role": "analyst"},
        )
        assert resp.status_code == 200
        accept = await authenticated_client.post(
            _ACCEPT,
            json={
                "token": captured_invites[0]["invite_token"],
                "full_name": "Round Trip",
                "password": _PASSWORD,
            },
        )
        assert accept.status_code == 200

        # Now the account is active -> inviting the same email is a real conflict
        again = await authenticated_client.post(
            _INVITE,
            json={"email": _EMAIL, "full_name": "Round Trip", "role": "analyst"},
        )
        assert again.status_code == 400
