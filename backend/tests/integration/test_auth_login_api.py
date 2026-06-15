# =============================================================================
# Stratum AI - Auth Login Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/login`` — password verification and
access/refresh token issuance. A dedicated user fixture is created with the
real ``hash_pii_for_lookup`` email hash (the shared ``test_user`` fixture
uses a simplified literal hash that login's lookup can't match).
"""

import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_URL = "/api/v1/auth/login"
_EMAIL = "login-user@example.com"
_PASSWORD = "Testpassword123"


@pytest_asyncio.fixture
async def login_user(db_session, test_tenant) -> dict:
    """Create an active, verified user that login's email-hash lookup resolves."""
    from app.base_models import User, UserRole
    from app.core.security import (
        encrypt_pii,
        get_password_hash,
        hash_pii_for_lookup,
    )

    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(_EMAIL),
        email_hash=hash_pii_for_lookup(_EMAIL),
        password_hash=get_password_hash(_PASSWORD),
        full_name=encrypt_pii("Login User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        totp_enabled=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "tenant_id": test_tenant["id"]}


class TestLogin:
    async def test_success_issues_tokens(self, client, login_user):
        resp = await client.post(_URL, json={"email": _EMAIL, "password": _PASSWORD})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]

    async def test_wrong_password_401(self, client, login_user):
        resp = await client.post(
            _URL, json={"email": _EMAIL, "password": "WrongPassword9"}
        )
        assert resp.status_code == 401

    async def test_unknown_email_401(self, client, login_user):
        resp = await client.post(
            _URL, json={"email": "nobody@example.com", "password": _PASSWORD}
        )
        assert resp.status_code == 401
