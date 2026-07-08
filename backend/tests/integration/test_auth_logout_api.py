# =============================================================================
# Stratum AI - Auth Logout Endpoint Integration Tests
# =============================================================================
"""Integration tests for ``POST /auth/logout`` — access-token blacklisting,
optional refresh-token revocation, audit logging, and Redis-degradation
tolerance. Uses the shared ``authenticated_client`` (bearer + tenant header)
since the logout route sits behind TenantMiddleware.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_LOGOUT = "/api/v1/auth/logout"
_REFRESH = "/api/v1/auth/refresh"


class TestLogout:
    async def test_logout_without_body_succeeds(self, authenticated_client):
        resp = await authenticated_client.post(_LOGOUT)
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    async def test_logout_revokes_refresh_token(self, authenticated_client, test_user):
        from app.core.security import create_refresh_token

        refresh = create_refresh_token(subject=test_user["id"])

        resp = await authenticated_client.post(_LOGOUT, json={"refresh_token": refresh})
        assert resp.status_code == 200, resp.text

        # The revoked refresh token can no longer be exchanged.
        reuse = await authenticated_client.post(
            _REFRESH, json={"refresh_token": refresh}
        )
        assert reuse.status_code == 401
        assert "revoked" in reuse.json()["detail"].lower()

    async def test_logout_with_garbage_refresh_token_still_succeeds(
        self, authenticated_client
    ):
        # An undecodable refresh token is ignored, not an error.
        resp = await authenticated_client.post(
            _LOGOUT, json={"refresh_token": "not.a.jwt"}
        )
        assert resp.status_code == 200

    async def test_logout_writes_audit_log(
        self, authenticated_client, db_session, test_user
    ):
        resp = await authenticated_client.post(_LOGOUT)
        assert resp.status_code == 200

        from sqlalchemy import select

        from app.models import AuditAction, AuditLog

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.user_id == test_user["id"],
                        AuditLog.action == AuditAction.LOGOUT,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) >= 1

    async def test_logout_redis_down_still_succeeds(
        self, authenticated_client, test_user, monkeypatch
    ):
        # Blacklisting is best-effort: tokens expire naturally via their exp.
        import app.api.v1.endpoints.auth as auth_module
        from app.core.security import create_refresh_token

        async def _boom(token, payload):
            raise ConnectionError("redis down (test)")

        monkeypatch.setattr(auth_module, "blacklist_token", _boom)

        refresh = create_refresh_token(subject=test_user["id"])
        resp = await authenticated_client.post(_LOGOUT, json={"refresh_token": refresh})
        assert resp.status_code == 200
