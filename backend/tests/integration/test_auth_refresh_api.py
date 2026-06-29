# =============================================================================
# Stratum AI - Auth Token-Refresh Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/refresh`` — refresh-token validation,
user re-resolution, and rotated access/refresh token issuance. The old
refresh token is blacklisted on rotation (Redis; best-effort).
"""

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_URL = "/api/v1/auth/refresh"


@pytest_asyncio.fixture
async def active_user(db_session, test_tenant) -> dict:
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "refresh-user@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash("Testpassword123"),
        full_name=encrypt_pii("Refresh User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id}


class TestRefresh:
    async def test_valid_refresh_rotates_tokens(self, client, active_user):
        from app.core.security import create_refresh_token

        token = create_refresh_token(subject=active_user["id"])
        resp = await client.post(_URL, json={"refresh_token": token})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]

    async def test_access_token_rejected_as_refresh(self, client, active_user):
        # An access token (type != "refresh") must not be accepted here.
        from app.core.security import create_access_token

        access = create_access_token(subject=active_user["id"])
        resp = await client.post(_URL, json={"refresh_token": access})
        assert resp.status_code == 401

    async def test_garbage_token_rejected(self, client):
        resp = await client.post(_URL, json={"refresh_token": "not.a.jwt"})
        assert resp.status_code == 401

    async def test_unknown_user_rejected(self, client):
        # Well-formed refresh token for a user id that doesn't exist.
        from app.core.security import create_refresh_token

        token = create_refresh_token(subject=99999999)
        resp = await client.post(_URL, json={"refresh_token": token})
        assert resp.status_code == 401
