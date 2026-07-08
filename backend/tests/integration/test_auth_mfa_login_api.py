# =============================================================================
# Stratum AI - MFA-Gated Login Integration Tests
# =============================================================================
"""Integration tests for the two-step MFA login flow:

1. ``POST /auth/login`` for a TOTP-enabled user returns an ``mfa_challenge``
   token instead of real tokens.
2. ``POST /auth/login/mfa`` exchanges that challenge + a TOTP code for
   access/refresh tokens.

The user is seeded with a fixed (encrypted) TOTP secret and driven with real
pyotp codes, mirroring test_mfa_api.py.

NOTE: ``/api/v1/auth/login/mfa`` is missing from TenantMiddleware's
PUBLIC_ENDPOINTS, so an unauthenticated exchange (the real-world flow —
the user has no bearer token yet) is rejected by the middleware before the
endpoint runs. Tests here attach a tenant-scoped bearer purely to get past
the middleware; the endpoint itself authenticates via ``body.mfa_token``.
This is reported as a production bug, not asserted as correct behavior.
"""

import pyotp
import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_LOGIN = "/api/v1/auth/login"
_MFA = "/api/v1/auth/login/mfa"
_SECRET = "JBSWY3DPEHPK3PXP"  # fixed base32 secret for deterministic codes
_EMAIL = "mfa-login@example.com"
_PASSWORD = "Testpassword123"


def _bearer(user: dict) -> dict:
    """Tenant-scoped access token to satisfy TenantMiddleware (see NOTE above)."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=user["id"],
        additional_claims={"tenant_id": user["tenant_id"], "role": "admin"},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def mfa_user(db_session, test_tenant) -> dict:
    """An active, verified user with TOTP MFA fully enabled."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(_EMAIL),
        email_hash=hash_pii_for_lookup(_EMAIL),
        password_hash=get_password_hash(_PASSWORD),
        full_name=encrypt_pii("MFA Login User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        totp_secret=encrypt_pii(_SECRET),
        totp_enabled=True,
        failed_totp_attempts=0,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "tenant_id": test_tenant["id"]}


@pytest_asyncio.fixture
async def plain_user(db_session, test_tenant) -> dict:
    """A user WITHOUT MFA, for challenge-token misuse tests."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "no-mfa-login@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash(_PASSWORD),
        full_name=encrypt_pii("No MFA User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        totp_enabled=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "tenant_id": test_tenant["id"]}


def _challenge_for(user_id: int) -> str:
    """Mint an mfa_challenge token the way /login does."""
    from datetime import timedelta

    from app.core.security import create_access_token

    return create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=5),
        additional_claims={"type": "mfa_challenge"},
    )


class TestLoginMfaChallenge:
    async def test_login_returns_challenge_not_tokens(self, client, mfa_user):
        resp = await client.post(_LOGIN, json={"email": _EMAIL, "password": _PASSWORD})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["mfa_required"] is True
        assert data["mfa_token"]
        assert data["token_type"] == "mfa_challenge"
        assert not data.get("access_token")
        assert not data.get("refresh_token")


class TestLoginMfaExchange:
    async def test_valid_code_issues_tokens(self, client, mfa_user):
        login = await client.post(_LOGIN, json={"email": _EMAIL, "password": _PASSWORD})
        mfa_token = login.json()["data"]["mfa_token"]

        code = pyotp.TOTP(_SECRET).now()
        resp = await client.post(
            _MFA,
            json={"mfa_token": mfa_token, "code": code},
            headers=_bearer(mfa_user),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]
        assert "available_tenants" in data

    async def test_wrong_code_401(self, client, mfa_user):
        login = await client.post(_LOGIN, json={"email": _EMAIL, "password": _PASSWORD})
        mfa_token = login.json()["data"]["mfa_token"]

        resp = await client.post(
            _MFA,
            json={"mfa_token": mfa_token, "code": "000000"},
            headers=_bearer(mfa_user),
        )
        assert resp.status_code == 401
        assert "attempts remaining" in resp.json()["detail"].lower()

    async def test_garbage_challenge_token_401(self, client, mfa_user):
        resp = await client.post(
            _MFA,
            json={"mfa_token": "not.a.jwt", "code": "000000"},
            headers=_bearer(mfa_user),
        )
        assert resp.status_code == 401

    async def test_access_token_rejected_as_challenge(self, client, mfa_user):
        # A regular access token (no type=mfa_challenge claim) must not work.
        from app.core.security import create_access_token

        access = create_access_token(subject=mfa_user["id"])
        resp = await client.post(
            _MFA,
            json={"mfa_token": access, "code": "000000"},
            headers=_bearer(mfa_user),
        )
        assert resp.status_code == 401

    async def test_challenge_for_non_mfa_user_401(self, client, plain_user):
        # A challenge minted for a user without MFA enabled is invalid.
        challenge = _challenge_for(plain_user["id"])
        resp = await client.post(
            _MFA,
            json={"mfa_token": challenge, "code": "000000"},
            headers=_bearer(plain_user),
        )
        assert resp.status_code == 401

    async def test_challenge_for_unknown_user_401(self, client, mfa_user):
        challenge = _challenge_for(99999999)
        resp = await client.post(
            _MFA,
            json={"mfa_token": challenge, "code": "000000"},
            headers=_bearer(mfa_user),
        )
        assert resp.status_code == 401
