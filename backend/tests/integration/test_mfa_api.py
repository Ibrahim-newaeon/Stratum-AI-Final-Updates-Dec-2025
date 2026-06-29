# =============================================================================
# Stratum AI - MFA (TOTP) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed MFA endpoints under ``/mfa``:
status, verify-and-enable, and disable. The QR-generating ``/setup`` route
needs Pillow and is out of scope here; instead the user is seeded with a
known (encrypted) TOTP secret and driven with real pyotp codes.
"""

import pyotp
import pytest
import pytest_asyncio

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_STATUS = "/api/v1/mfa/status"
_VERIFY = "/api/v1/mfa/verify"
_DISABLE = "/api/v1/mfa/disable"
_SECRET = "JBSWY3DPEHPK3PXP"  # a fixed base32 TOTP secret for deterministic codes


def _auth(user: dict) -> dict:
    from app.core.security import create_access_token

    token = create_access_token(
        subject=user["id"],
        additional_claims={
            "email": "mfa-user@example.com",
            "role": "admin",
            "tenant_id": user["tenant_id"],
        },
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(user["tenant_id"])}


@pytest_asyncio.fixture
async def mfa_user(db_session, test_tenant) -> dict:
    """A user with a stored-but-not-yet-enabled TOTP secret."""
    from app.base_models import User, UserRole
    from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

    email = "mfa-user@example.com"
    user = User(
        tenant_id=test_tenant["id"],
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash("Testpassword123"),
        full_name=encrypt_pii("MFA User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        totp_secret=encrypt_pii(_SECRET),
        totp_enabled=False,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "tenant_id": test_tenant["id"]}


class TestStatus:
    async def test_requires_auth(self, client):
        assert (await client.get(_STATUS)).status_code == 401

    async def test_status_initially_disabled(self, client, mfa_user):
        resp = await client.get(_STATUS, headers=_auth(mfa_user))
        assert resp.status_code == 200, resp.text
        assert resp.json()["enabled"] is False


class TestVerifyEnable:
    async def test_valid_code_enables_with_backup_codes(self, client, mfa_user):
        code = pyotp.TOTP(_SECRET).now()
        resp = await client.post(_VERIFY, json={"code": code}, headers=_auth(mfa_user))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert len(body["backup_codes"]) > 0

        # Status now reflects MFA enabled.
        status = await client.get(_STATUS, headers=_auth(mfa_user))
        assert status.json()["enabled"] is True

    async def test_invalid_code_does_not_enable(self, client, mfa_user):
        resp = await client.post(
            _VERIFY, json={"code": "000000"}, headers=_auth(mfa_user)
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestDisable:
    async def test_disable_after_enable(self, client, mfa_user):
        totp = pyotp.TOTP(_SECRET)
        # Enable first ...
        enabled = await client.post(
            _VERIFY, json={"code": totp.now()}, headers=_auth(mfa_user)
        )
        assert enabled.json()["success"] is True

        # ... then disable with a fresh valid code.
        resp = await client.post(
            _DISABLE, json={"code": totp.now()}, headers=_auth(mfa_user)
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
