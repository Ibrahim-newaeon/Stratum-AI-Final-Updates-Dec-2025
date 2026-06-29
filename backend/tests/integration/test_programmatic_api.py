# =============================================================================
# Stratum AI - Programmatic (API-key) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the API-key-authenticated surface under
``/api/v1/programmatic/...``.

``GET /programmatic/whoami`` resolves the inbound ``X-API-Key`` header to a
principal via ``get_api_key_principal`` (which uses the harness-overridden
``get_async_session`` and looks the SHA-256 key hash up in the ``api_keys``
table). The route self-authenticates, so ``TenantMiddleware`` bypasses JWT-based
tenant extraction for ``/programmatic/*`` and the api-key dependency populates
``request.state.tenant_id`` from the validated key.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/programmatic"
_PLAINTEXT_KEY = "stratum-test-key-abc123"


@pytest_asyncio.fixture
async def seeded_api_key(db_session, test_tenant, test_user) -> dict:
    """Persist an active API key whose hash matches ``_PLAINTEXT_KEY``."""
    from app.core.security import hash_api_key
    from app.models import APIKey

    key = APIKey(
        tenant_id=test_tenant["id"],
        user_id=test_user["id"],
        name="test-key",
        key_hash=hash_api_key(_PLAINTEXT_KEY),
        key_prefix=_PLAINTEXT_KEY[:8],
        scopes=["read"],
        is_active=True,
    )
    db_session.add(key)
    await db_session.flush()
    return {"id": key.id, "tenant_id": key.tenant_id, "user_id": key.user_id}


class TestWhoami:
    async def test_missing_key_401(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/whoami")
        assert resp.status_code == 401, resp.text

    async def test_unknown_key_401(self, client: AsyncClient):
        resp = await client.get(
            f"{_BASE}/whoami", headers={"X-API-Key": "not-a-real-key"}
        )
        assert resp.status_code == 401, resp.text

    async def test_valid_key_returns_identity(
        self, client: AsyncClient, seeded_api_key: dict
    ):
        resp = await client.get(
            f"{_BASE}/whoami", headers={"X-API-Key": _PLAINTEXT_KEY}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["key_id"] == seeded_api_key["id"]
        assert data["tenant_id"] == seeded_api_key["tenant_id"]
        assert data["scopes"] == ["read"]

    async def test_inactive_key_401(
        self, client: AsyncClient, db_session, seeded_api_key: dict
    ):
        from sqlalchemy import update

        from app.models import APIKey

        await db_session.execute(
            update(APIKey)
            .where(APIKey.id == seeded_api_key["id"])
            .values(is_active=False)
        )
        await db_session.flush()

        resp = await client.get(
            f"{_BASE}/whoami", headers={"X-API-Key": _PLAINTEXT_KEY}
        )
        assert resp.status_code == 401, resp.text
