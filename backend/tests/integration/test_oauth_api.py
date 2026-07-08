# =============================================================================
# Stratum AI - OAuth Endpoint Integration Tests
# =============================================================================
"""Integration tests for the ad-platform OAuth flow under ``/api/v1/oauth``.

Covers ``backend/app/api/v1/endpoints/oauth.py``:

- POST /{platform}/authorize    - auth-URL initiation (real Redis state)
- GET  /{platform}/callback     - token exchange, CSRF/state validation,
                                  connection create/update, error redirects
- GET  /{platform}/status       - single-platform connection status
- GET  /status                  - all-platform statuses
- GET  /{platform}/accounts     - ad-account listing + auto token refresh
- POST /{platform}/accounts/connect - connect/enable selected accounts
- POST /{platform}/refresh      - explicit token refresh (+ error path)
- DELETE /{platform}/disconnect - revoke + local teardown
- _auto_sync_after_oauth        - fire-and-forget post-OAuth sync helper

Mocking strategy: the provider services (Meta/Google/TikTok/Snapchat) make
their outbound HTTP calls with **aiohttp**, which respx cannot intercept
(respx patches httpx only). Provider HTTP is therefore stubbed at the
service-method boundary on the factory singletons
(``exchange_code_for_tokens`` / ``refresh_access_token`` /
``fetch_ad_accounts`` / ``revoke_access``) — the provider internals have
dedicated aiohttp-mocked unit tests in
``tests/unit/test_oauth_integrations.py``. Everything else is real:
Postgres, Redis-backed OAuth state (create/validate/CSRF), Fernet token
encryption, JWT auth, and the admin role gate.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

import app.api.v1.endpoints.oauth as oauth_ep
from app.models.campaign_builder import (
    AdPlatform,
    ConnectionStatus,
    TenantAdAccount,
    TenantPlatformConnection,
)
from app.services.oauth import get_oauth_service
from app.services.oauth.base import AdAccountInfo, OAuthTokens

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/oauth"

_REDIRECT_CODES = {302, 307}


# =============================================================================
# Helpers & fixtures
# =============================================================================


def _tokens(
    access: str = "new-access-token",
    refresh: str | None = "new-refresh-token",
    expires_in: int = 3600,
) -> OAuthTokens:
    return OAuthTokens(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        scopes=["ads_read"],
    )


def _account(account_id: str = "act_100", name: str = "Acct 100") -> AdAccountInfo:
    return AdAccountInfo(
        account_id=account_id,
        name=name,
        business_name="Acme Inc",
        currency="USD",
        timezone="UTC",
        status="active",
        spend_cap=500.0,
    )


@pytest.fixture
def oauth_creds(monkeypatch):
    """Set fake app credentials on the factory singletons so config checks pass."""
    meta = get_oauth_service("meta")
    monkeypatch.setattr(meta, "app_id", "test_meta_app_id")
    monkeypatch.setattr(meta, "app_secret", "test_meta_app_secret")

    google = get_oauth_service("google")
    monkeypatch.setattr(google, "client_id", "test_google_client_id")
    monkeypatch.setattr(google, "client_secret", "test_google_client_secret")
    monkeypatch.setattr(google, "developer_token", "test_google_dev_token")

    tiktok = get_oauth_service("tiktok")
    monkeypatch.setattr(tiktok, "app_id", "test_tiktok_app_id")
    monkeypatch.setattr(tiktok, "app_secret", "test_tiktok_app_secret")

    snapchat = get_oauth_service("snapchat")
    monkeypatch.setattr(snapchat, "client_id", "test_snap_client_id")
    monkeypatch.setattr(snapchat, "client_secret", "test_snap_client_secret")


@pytest.fixture
def no_auto_sync(monkeypatch):
    """Replace the fire-and-forget post-OAuth sync with a no-op coroutine."""

    async def _noop(tenant_id, platform):
        return None

    monkeypatch.setattr(oauth_ep, "_auto_sync_after_oauth", _noop)


async def _make_connection(
    db_session,
    tenant_id: int,
    platform: AdPlatform = AdPlatform.META,
    *,
    status: ConnectionStatus = ConnectionStatus.CONNECTED,
    access_token: str | None = "stored-access-token",
    refresh_token: str | None = "stored-refresh-token",
    expires_delta: timedelta | None = timedelta(days=30),
) -> TenantPlatformConnection:
    svc = get_oauth_service(platform.value)
    now = datetime.now(UTC)
    conn = TenantPlatformConnection(
        tenant_id=tenant_id,
        platform=platform,
        status=status,
        access_token_encrypted=(
            svc.encrypt_token(access_token) if access_token else None
        ),
        refresh_token_encrypted=(
            svc.encrypt_token(refresh_token) if refresh_token else None
        ),
        token_expires_at=(now + expires_delta) if expires_delta else None,
        scopes=["ads_read"],
        connected_at=now,
        last_refreshed_at=now,
    )
    db_session.add(conn)
    await db_session.flush()
    return conn


@pytest.fixture
async def meta_connection(db_session, test_tenant) -> TenantPlatformConnection:
    """A healthy connected Meta connection for the test tenant."""
    return await _make_connection(db_session, test_tenant["id"])


async def _make_ad_account(
    db_session,
    tenant_id: int,
    connection_id,
    account_id: str = "act_100",
    *,
    is_enabled: bool = True,
) -> TenantAdAccount:
    account = TenantAdAccount(
        tenant_id=tenant_id,
        connection_id=connection_id,
        platform=AdPlatform.META,
        platform_account_id=account_id,
        name=f"Account {account_id}",
        currency="USD",
        timezone="UTC",
        account_status="active",
        is_enabled=is_enabled,
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest.fixture
async def viewer_headers(db_session, test_tenant) -> dict:
    """Auth headers for a non-admin (viewer) user of the test tenant."""
    from app.base_models import User, UserRole
    from app.core.security import create_access_token, get_password_hash

    user = User(
        tenant_id=test_tenant["id"],
        email="viewer@example.com",
        email_hash="viewer@example.com",
        password_hash=get_password_hash("viewerpassword123"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        subject=user.id,
        additional_claims={
            "email": user.email,
            "tenant_id": test_tenant["id"],
            "role": user.role.value,
        },
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(test_tenant["id"]),
    }


# =============================================================================
# Auth gate
# =============================================================================


class TestGate:
    async def test_authorize_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/meta/authorize", json={})
        assert resp.status_code in {401, 403}

    async def test_status_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/status")
        assert resp.status_code in {401, 403}

    async def test_non_admin_denied(self, client: AsyncClient, viewer_headers):
        resp = await client.post(
            f"{_BASE}/meta/authorize", json={}, headers=viewer_headers
        )
        assert resp.status_code == 403

    async def test_invalid_platform_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/twitter/authorize", json={})
        assert resp.status_code == 422


# =============================================================================
# POST /{platform}/authorize
# =============================================================================


class TestAuthorize:
    @pytest.mark.parametrize(
        "platform,url_marker",
        [
            ("meta", "facebook.com"),
            ("google", "accounts.google.com"),
            ("tiktok", "tiktok.com"),
            ("snapchat", "snapchat.com"),
        ],
    )
    async def test_authorize_returns_url_per_platform(
        self, authenticated_client: AsyncClient, oauth_creds, platform, url_marker
    ):
        resp = await authenticated_client.post(f"{_BASE}/{platform}/authorize", json={})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["platform"] == platform
        assert url_marker in data["authorization_url"]
        assert data["state"] in data["authorization_url"]
        assert len(data["state"]) > 20

    async def test_authorize_custom_scopes(
        self, authenticated_client: AsyncClient, oauth_creds
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/meta/authorize", json={"scopes": ["ads_read"]}
        )
        assert resp.status_code == 200, resp.text
        url = resp.json()["data"]["authorization_url"]
        assert "ads_read" in url
        assert "business_management" not in url

    async def test_authorize_unconfigured_platform_400(
        self, authenticated_client: AsyncClient, monkeypatch
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(meta, "app_id", None)
        resp = await authenticated_client.post(f"{_BASE}/meta/authorize", json={})
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"]

    async def test_authorize_state_storage_failure_500(
        self, authenticated_client: AsyncClient, oauth_creds, monkeypatch
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "create_state",
            AsyncMock(side_effect=ConnectionError("redis down")),
        )
        resp = await authenticated_client.post(f"{_BASE}/meta/authorize", json={})
        assert resp.status_code == 500
        assert "Failed to initialize OAuth flow" in resp.json()["detail"]


# =============================================================================
# GET /{platform}/callback
# =============================================================================


class TestCallback:
    """Callback behavior.

    ``/api/v1/oauth/{platform}/callback`` is exempt from TenantMiddleware
    (#534): real platform redirects arrive as browser navigations with no
    JWT or X-Tenant-ID header, and tenant context comes from the
    Redis-stored state token the endpoint validates. All callback requests
    here are therefore sent UNAUTHENTICATED — the production contract.
    """

    async def test_callback_platform_error_redirects(self, client: AsyncClient):
        resp = await client.get(
            f"{_BASE}/meta/callback",
            params={"error": "access_denied", "error_description": "User said no"},
        )
        assert resp.status_code in _REDIRECT_CODES
        location = resp.headers["location"]
        assert "error=access_denied" in location
        assert "platform=meta" in location

    async def test_callback_missing_params_redirects(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/meta/callback")
        assert resp.status_code in _REDIRECT_CODES
        assert "error=invalid_request" in resp.headers["location"]

    async def test_callback_invalid_state_redirects(self, client: AsyncClient):
        # State token that was never stored in Redis -> CSRF check fails.
        resp = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": "bogus-state-token"},
        )
        assert resp.status_code in _REDIRECT_CODES
        assert "error=invalid_state" in resp.headers["location"]

    async def test_callback_state_platform_mismatch(
        self, client: AsyncClient, test_tenant, test_user
    ):
        # State created for meta but presented on the google callback.
        meta = get_oauth_service("meta")
        state = await meta.create_state(
            tenant_id=test_tenant["id"],
            user_id=test_user["id"],
            redirect_uri="http://localhost:5173",
        )
        resp = await client.get(
            f"{_BASE}/google/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert resp.status_code in _REDIRECT_CODES
        assert "error=invalid_state" in resp.headers["location"]

    async def test_callback_token_exchange_failure_redirects(
        self,
        client: AsyncClient,
        test_tenant,
        test_user,
        oauth_creds,
        no_auto_sync,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        state = await meta.create_state(
            tenant_id=test_tenant["id"],
            user_id=test_user["id"],
            redirect_uri="http://localhost:5173",
        )
        monkeypatch.setattr(
            meta,
            "exchange_code_for_tokens",
            AsyncMock(side_effect=ConnectionError("provider unreachable")),
        )
        resp = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert resp.status_code in _REDIRECT_CODES
        assert "error=token_exchange_failed" in resp.headers["location"]

    async def test_callback_success_creates_connection(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        oauth_creds,
        no_auto_sync,
        monkeypatch,
    ):
        """Full flow: authorize endpoint -> Redis state -> callback -> DB row."""
        from sqlalchemy import and_, select

        start = await authenticated_client.post(
            f"{_BASE}/meta/authorize",
            json={"frontend_callback_url": "http://myapp.example.com"},
        )
        assert start.status_code == 200, start.text
        state_token = start.json()["data"]["state"]

        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "exchange_code_for_tokens",
            AsyncMock(return_value=_tokens(access="meta-long-lived")),
        )

        # The callback is a browser redirect from the platform: no JWT, no
        # X-Tenant-ID (authenticated_client and client share one instance,
        # so strip its headers for the unauthenticated leg).
        authenticated_client.headers.pop("Authorization", None)
        authenticated_client.headers.pop("X-Tenant-ID", None)
        resp = await authenticated_client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state_token},
        )
        assert resp.status_code in _REDIRECT_CODES
        location = resp.headers["location"]
        # Redirects to the frontend_callback_url captured in the state.
        assert location.startswith("http://myapp.example.com/connect")
        assert "status=success" in location

        result = await db_session.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.tenant_id == test_tenant["id"],
                    TenantPlatformConnection.platform == AdPlatform.META,
                )
            )
        )
        conn = result.scalar_one()
        assert conn.status == ConnectionStatus.CONNECTED
        # Tokens are stored encrypted, roundtrip through the service decrypt.
        assert conn.access_token_encrypted != "meta-long-lived"
        assert meta.decrypt_token(conn.access_token_encrypted) == "meta-long-lived"
        assert meta.decrypt_token(conn.refresh_token_encrypted) == "new-refresh-token"

    async def test_callback_state_single_use(
        self,
        client: AsyncClient,
        test_tenant,
        test_user,
        oauth_creds,
        no_auto_sync,
        monkeypatch,
    ):
        """A consumed state token cannot be replayed (getdel semantics)."""
        meta = get_oauth_service("meta")
        state = await meta.create_state(
            tenant_id=test_tenant["id"],
            user_id=test_user["id"],
            redirect_uri="http://localhost:5173",
        )
        monkeypatch.setattr(
            meta, "exchange_code_for_tokens", AsyncMock(return_value=_tokens())
        )

        first = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert "status=success" in first.headers["location"]

        replay = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert "error=invalid_state" in replay.headers["location"]

    async def test_callback_updates_existing_connection(
        self,
        client: AsyncClient,
        db_session,
        test_tenant,
        test_user,
        oauth_creds,
        no_auto_sync,
        monkeypatch,
    ):
        conn = await _make_connection(
            db_session,
            test_tenant["id"],
            status=ConnectionStatus.EXPIRED,
        )
        conn.last_error = "token expired"
        conn.error_count = 3
        await db_session.flush()

        meta = get_oauth_service("meta")
        state = await meta.create_state(
            tenant_id=test_tenant["id"],
            user_id=test_user["id"],
            redirect_uri="http://localhost:5173",
        )
        monkeypatch.setattr(
            meta,
            "exchange_code_for_tokens",
            AsyncMock(return_value=_tokens(access="reconnected-token")),
        )

        resp = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert "status=success" in resp.headers["location"]

        assert conn.status == ConnectionStatus.CONNECTED
        assert conn.last_error is None
        assert conn.error_count == 0
        assert meta.decrypt_token(conn.access_token_encrypted) == "reconnected-token"
        assert conn.granted_by_user_id == test_user["id"]

    async def test_callback_storage_failure_redirects(
        self,
        client: AsyncClient,
        test_tenant,
        test_user,
        oauth_creds,
        no_auto_sync,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        state = await meta.create_state(
            tenant_id=test_tenant["id"],
            user_id=test_user["id"],
            redirect_uri="http://localhost:5173",
        )
        monkeypatch.setattr(
            meta, "exchange_code_for_tokens", AsyncMock(return_value=_tokens())
        )
        monkeypatch.setattr(
            meta,
            "encrypt_token",
            lambda token: (_ for _ in ()).throw(ValueError("bad key")),
        )
        resp = await client.get(
            f"{_BASE}/meta/callback",
            params={"code": "authcode", "state": state.state_token},
        )
        assert resp.status_code in _REDIRECT_CODES
        assert "error=storage_failed" in resp.headers["location"]


# =============================================================================
# GET /{platform}/status and GET /status
# =============================================================================


class TestConnectionStatus:
    async def test_status_not_connected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/meta/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["platform"] == "meta"
        assert data["status"] == "disconnected"
        assert data["ad_accounts_count"] == 0

    async def test_status_connected_with_accounts(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        meta_connection,
    ):
        await _make_ad_account(
            db_session, test_tenant["id"], meta_connection.id, "act_1"
        )
        await _make_ad_account(
            db_session,
            test_tenant["id"],
            meta_connection.id,
            "act_2",
            is_enabled=False,
        )

        resp = await authenticated_client.get(f"{_BASE}/meta/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "connected"
        assert data["scopes"] == ["ads_read"]
        assert data["connected_at"] is not None
        assert data["token_expires_at"] is not None
        # Only enabled accounts are counted.
        assert data["ad_accounts_count"] == 1

    async def test_all_statuses_include_every_platform(
        self, authenticated_client: AsyncClient, meta_connection
    ):
        resp = await authenticated_client.get(f"{_BASE}/status")
        assert resp.status_code == 200, resp.text
        statuses = {s["platform"]: s["status"] for s in resp.json()["data"]}
        assert statuses["meta"] == "connected"
        for platform in ("google", "tiktok", "snapchat"):
            assert statuses[platform] == "disconnected"
        assert len(statuses) == 4

    async def test_status_survives_fresh_load_from_db(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        """Regression (#534): platform/status are plain String(50) columns.

        Rows loaded fresh from Postgres hold str, and the old ``.value``
        access raised AttributeError -> 500 on every status read. The other
        status tests never caught this because the session identity map
        returned the fixture-created instance still holding the assigned
        enums — so commit and expunge to force a fresh load in the endpoint.
        """
        await _make_connection(db_session, test_tenant["id"])
        await db_session.commit()
        db_session.expunge_all()

        single = await authenticated_client.get(f"{_BASE}/meta/status")
        assert single.status_code == 200, single.text
        data = single.json()["data"]
        assert data["platform"] == "meta"
        assert data["status"] == "connected"

        combined = await authenticated_client.get(f"{_BASE}/status")
        assert combined.status_code == 200, combined.text
        statuses = {s["platform"]: s["status"] for s in combined.json()["data"]}
        assert statuses["meta"] == "connected"
        for platform in ("google", "tiktok", "snapchat"):
            assert statuses[platform] == "disconnected"


# =============================================================================
# GET /{platform}/accounts
# =============================================================================


class TestListAdAccounts:
    async def test_accounts_not_connected_400(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 400
        assert "not connected" in resp.json()["detail"]

    async def test_accounts_disconnected_status_400(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        await _make_connection(
            db_session, test_tenant["id"], status=ConnectionStatus.DISCONNECTED
        )
        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 400

    async def test_accounts_merges_local_state(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        meta_connection,
        monkeypatch,
    ):
        local = await _make_ad_account(
            db_session, test_tenant["id"], meta_connection.id, "act_1"
        )
        meta = get_oauth_service("meta")
        fetch = AsyncMock(
            return_value=[_account("act_1", "Connected"), _account("act_2", "Fresh")]
        )
        monkeypatch.setattr(meta, "fetch_ad_accounts", fetch)

        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 200, resp.text
        accounts = {a["platform_account_id"]: a for a in resp.json()["data"]}
        assert len(accounts) == 2
        assert accounts["act_1"]["is_connected"] is True
        assert accounts["act_1"]["is_enabled"] is True
        assert accounts["act_1"]["id"] == str(local.id)
        assert accounts["act_2"]["is_connected"] is False
        assert accounts["act_2"]["id"] is None
        # The stored token was decrypted and passed to the provider fetch.
        fetch.assert_awaited_once_with("stored-access-token")

    async def test_accounts_expired_token_auto_refreshes(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        monkeypatch,
    ):
        conn = await _make_connection(
            db_session, test_tenant["id"], expires_delta=timedelta(hours=-1)
        )
        meta = get_oauth_service("meta")
        refresh = AsyncMock(return_value=_tokens(access="refreshed-access"))
        monkeypatch.setattr(meta, "refresh_access_token", refresh)
        fetch = AsyncMock(return_value=[_account()])
        monkeypatch.setattr(meta, "fetch_ad_accounts", fetch)

        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 200, resp.text
        refresh.assert_awaited_once_with("stored-refresh-token")
        # Fetch used the refreshed token, and the new token was persisted.
        fetch.assert_awaited_once_with("refreshed-access")
        assert meta.decrypt_token(conn.access_token_encrypted) == "refreshed-access"
        assert conn.token_expires_at > datetime.now(UTC)

    async def test_accounts_expired_token_refresh_fails_401(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        monkeypatch,
    ):
        conn = await _make_connection(
            db_session, test_tenant["id"], expires_delta=timedelta(hours=-1)
        )
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "refresh_access_token",
            AsyncMock(side_effect=ConnectionError("refresh rejected")),
        )
        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 401
        assert "reconnect" in resp.json()["detail"].lower()
        assert conn.status == ConnectionStatus.EXPIRED
        assert conn.last_error == "refresh rejected"

    async def test_accounts_expired_without_refresh_token_401(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
    ):
        conn = await _make_connection(
            db_session,
            test_tenant["id"],
            refresh_token=None,
            expires_delta=timedelta(hours=-1),
        )
        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 401
        assert conn.status == ConnectionStatus.EXPIRED

    async def test_accounts_platform_fetch_failure_502(
        self,
        authenticated_client: AsyncClient,
        meta_connection,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "fetch_ad_accounts",
            AsyncMock(side_effect=ConnectionError("graph API down")),
        )
        resp = await authenticated_client.get(f"{_BASE}/meta/accounts")
        assert resp.status_code == 502


# =============================================================================
# POST /{platform}/accounts/connect
# =============================================================================


class TestConnectAdAccounts:
    async def test_connect_not_connected_400(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": ["act_1"]}
        )
        assert resp.status_code == 400

    async def test_connect_empty_account_ids_422(
        self, authenticated_client: AsyncClient, meta_connection
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": []}
        )
        assert resp.status_code == 422

    async def test_connect_new_account(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        meta_connection,
        monkeypatch,
    ):
        from sqlalchemy import and_, select

        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "fetch_ad_accounts",
            AsyncMock(return_value=[_account("act_new", "Brand New")]),
        )
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": ["act_new"]}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["connected_count"] == 1
        acct = data["accounts"][0]
        assert acct["platform_account_id"] == "act_new"
        assert acct["is_connected"] is True
        assert acct["is_enabled"] is True
        assert acct["id"] is not None

        result = await db_session.execute(
            select(TenantAdAccount).where(
                and_(
                    TenantAdAccount.tenant_id == test_tenant["id"],
                    TenantAdAccount.platform_account_id == "act_new",
                )
            )
        )
        row = result.scalar_one()
        assert row.is_enabled is True
        assert row.name == "Brand New"
        assert row.connection_id == meta_connection.id

    async def test_connect_existing_account_re_enables(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        meta_connection,
        monkeypatch,
    ):
        existing = await _make_ad_account(
            db_session,
            test_tenant["id"],
            meta_connection.id,
            "act_exist",
            is_enabled=False,
        )
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "fetch_ad_accounts",
            AsyncMock(return_value=[_account("act_exist", "Renamed Upstream")]),
        )
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": ["act_exist"]}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["connected_count"] == 1
        assert existing.is_enabled is True
        assert existing.name == "Renamed Upstream"
        assert existing.last_synced_at is not None

    async def test_connect_unknown_account_400(
        self,
        authenticated_client: AsyncClient,
        meta_connection,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "fetch_ad_accounts",
            AsyncMock(return_value=[_account("act_real")]),
        )
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": ["act_fake"]}
        )
        assert resp.status_code == 400
        assert "act_fake" in resp.json()["detail"]

    async def test_connect_validation_fetch_failure_502(
        self,
        authenticated_client: AsyncClient,
        meta_connection,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "fetch_ad_accounts",
            AsyncMock(side_effect=TimeoutError("slow provider")),
        )
        resp = await authenticated_client.post(
            f"{_BASE}/meta/accounts/connect", json={"account_ids": ["act_1"]}
        )
        assert resp.status_code == 502


# =============================================================================
# POST /{platform}/refresh
# =============================================================================


class TestRefreshToken:
    async def test_refresh_no_connection_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/meta/refresh")
        assert resp.status_code == 404

    async def test_refresh_without_refresh_token_400(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        await _make_connection(db_session, test_tenant["id"], refresh_token=None)
        resp = await authenticated_client.post(f"{_BASE}/meta/refresh")
        assert resp.status_code == 400
        assert "No refresh token" in resp.json()["detail"]

    async def test_refresh_success(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        monkeypatch,
    ):
        conn = await _make_connection(
            db_session, test_tenant["id"], status=ConnectionStatus.EXPIRED
        )
        conn.last_error = "was expired"
        conn.error_count = 2
        await db_session.flush()

        meta = get_oauth_service("meta")
        refresh = AsyncMock(
            return_value=_tokens(access="post-refresh", refresh="rotated-refresh")
        )
        monkeypatch.setattr(meta, "refresh_access_token", refresh)

        resp = await authenticated_client.post(f"{_BASE}/meta/refresh")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["success"] is True
        assert data["expires_at"] is not None
        refresh.assert_awaited_once_with("stored-refresh-token")

        assert conn.status == ConnectionStatus.CONNECTED
        assert conn.last_error is None
        assert conn.error_count == 0
        assert meta.decrypt_token(conn.access_token_encrypted) == "post-refresh"
        assert meta.decrypt_token(conn.refresh_token_encrypted) == "rotated-refresh"

    async def test_refresh_provider_failure_502(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        monkeypatch,
    ):
        conn = await _make_connection(db_session, test_tenant["id"])
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "refresh_access_token",
            AsyncMock(side_effect=ConnectionError("invalid_grant")),
        )
        resp = await authenticated_client.post(f"{_BASE}/meta/refresh")
        assert resp.status_code == 502
        assert "invalid_grant" in resp.json()["detail"]
        assert conn.status == ConnectionStatus.ERROR
        assert conn.last_error == "invalid_grant"
        assert conn.error_count == 1


# =============================================================================
# DELETE /{platform}/disconnect
# =============================================================================


class TestDisconnect:
    async def test_disconnect_no_connection_404(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.delete(f"{_BASE}/meta/disconnect")
        assert resp.status_code == 404

    async def test_disconnect_revokes_and_tears_down(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        meta_connection,
        monkeypatch,
    ):
        account = await _make_ad_account(
            db_session, test_tenant["id"], meta_connection.id, "act_1"
        )
        meta = get_oauth_service("meta")
        revoke = AsyncMock(return_value=True)
        monkeypatch.setattr(meta, "revoke_access", revoke)

        resp = await authenticated_client.delete(f"{_BASE}/meta/disconnect")
        assert resp.status_code == 200, resp.text
        assert "meta" in resp.json()["data"]["message"]

        revoke.assert_awaited_once_with("stored-access-token")
        assert meta_connection.status == ConnectionStatus.DISCONNECTED
        assert meta_connection.access_token_encrypted is None
        assert meta_connection.refresh_token_encrypted is None
        assert meta_connection.token_expires_at is None
        assert account.is_enabled is False

    async def test_disconnect_succeeds_when_revoke_fails(
        self,
        authenticated_client: AsyncClient,
        meta_connection,
        monkeypatch,
    ):
        meta = get_oauth_service("meta")
        monkeypatch.setattr(
            meta,
            "revoke_access",
            AsyncMock(side_effect=ConnectionError("revoke endpoint down")),
        )
        resp = await authenticated_client.delete(f"{_BASE}/meta/disconnect")
        assert resp.status_code == 200, resp.text
        assert meta_connection.status == ConnectionStatus.DISCONNECTED


# =============================================================================
# Tenant isolation
# =============================================================================


class TestTenantIsolation:
    async def test_other_tenant_connection_invisible(
        self, authenticated_client: AsyncClient, db_session
    ):
        """A connection belonging to another tenant must not leak into status."""
        from app.base_models import Tenant

        other = Tenant(
            name="Other Tenant",
            slug="other-tenant-oauth",
            plan="professional",
            max_users=10,
            max_campaigns=100,
        )
        db_session.add(other)
        await db_session.flush()
        await _make_connection(db_session, other.id)

        resp = await authenticated_client.get(f"{_BASE}/meta/status")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "disconnected"


# =============================================================================
# _auto_sync_after_oauth helper
# =============================================================================


class TestAutoSyncHelper:
    async def test_auto_sync_success_path(self, test_tenant, monkeypatch):
        import app.services.sync.orchestrator as orch_mod

        calls = {}

        class FakeOrchestrator:
            def __init__(self, db):
                calls["db"] = db

            async def sync_platform(self, tenant_id, platform, days_back=30):
                calls["args"] = (tenant_id, platform, days_back)
                return SimpleNamespace(
                    campaigns_synced=3, metrics_upserted=12, errors=[]
                )

        monkeypatch.setattr(orch_mod, "PlatformSyncOrchestrator", FakeOrchestrator)

        await oauth_ep._auto_sync_after_oauth(test_tenant["id"], AdPlatform.META)
        assert calls["args"] == (test_tenant["id"], AdPlatform.META, 30)

    async def test_auto_sync_swallows_errors(self, test_tenant, monkeypatch):
        import app.services.sync.orchestrator as orch_mod

        class ExplodingOrchestrator:
            def __init__(self, db):
                pass

            async def sync_platform(self, tenant_id, platform, days_back=30):
                raise ValueError("sync blew up")

        monkeypatch.setattr(orch_mod, "PlatformSyncOrchestrator", ExplodingOrchestrator)

        # Must not raise — the helper is fire-and-forget.
        await oauth_ep._auto_sync_after_oauth(test_tenant["id"], AdPlatform.META)
