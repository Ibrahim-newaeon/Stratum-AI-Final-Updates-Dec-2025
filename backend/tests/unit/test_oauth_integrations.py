# =============================================================================
# Stratum AI - OAuth Integrations Test Suite
# =============================================================================
"""
Comprehensive tests for OAuth integrations (Feature #8):

1. OAuth Data Models (OAuthState, OAuthTokens, AdAccountInfo)
2. OAuthService base class (token encryption, build_url, get_redirect_uri)
3. OAuth Factory (get_oauth_service, get_supported_platforms, singleton caching)
4. Platform-specific services (Meta, Google, TikTok, Snapchat):
   - Authorization URL generation
   - Platform identity & scopes
   - Token exchange (mocked HTTP)
   - Token refresh (mocked HTTP)
   - Ad account fetching (mocked HTTP)
   - Access revocation (mocked HTTP)
5. State management (create_state, validate_state with mocked Redis)
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.oauth.base import (
    OAUTH_STATE_EXPIRY,
    OAUTH_STATE_PREFIX,
    AdAccountInfo,
    OAuthService,
    OAuthState,
    OAuthTokens,
)
from app.services.oauth.factory import (
    _OAUTH_SERVICES,
    get_oauth_service,
    get_supported_platforms,
)
from app.services.oauth.google import (
    GOOGLE_AUTH_URL,
    GOOGLE_DEFAULT_SCOPES,
    GoogleOAuthService,
)
from app.services.oauth.meta import (
    META_DEFAULT_SCOPES,
    MetaOAuthService,
)
from app.services.oauth.snapchat import (
    SNAPCHAT_AUTH_URL,
    SNAPCHAT_DEFAULT_SCOPES,
    SnapchatOAuthService,
)
from app.services.oauth.tiktok import (
    TIKTOK_AUTH_URL,
    TIKTOK_DEFAULT_SCOPES,
    TikTokOAuthService,
)


# =============================================================================
# Helpers
# =============================================================================

NOW = datetime(2026, 4, 9, 12, 0, 0, tzinfo=UTC)


def _make_state(platform: str = "meta", **kw) -> OAuthState:
    defaults = dict(
        state_token="test_state_abc123",
        tenant_id=1,
        user_id=42,
        platform=platform,
        redirect_uri="https://app.stratum.ai/oauth/callback",
        created_at=NOW,
    )
    defaults.update(kw)
    return OAuthState(**defaults)


def _mock_redis() -> AsyncMock:
    """Create a mock Redis client."""
    r = AsyncMock()
    r.setex = AsyncMock()
    r.getdel = AsyncMock()
    r.close = AsyncMock()
    return r


def _mock_response(status: int = 200, json_data: dict = None) -> AsyncMock:
    """Create a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _set_test_credentials(svc) -> None:
    """Set fake credentials on a service instance so config checks pass."""
    if isinstance(svc, MetaOAuthService):
        svc.app_id = "test_meta_app_id"
        svc.app_secret = "test_meta_app_secret"
        svc.api_version = "v18.0"
    elif isinstance(svc, GoogleOAuthService):
        svc.client_id = "test_google_client_id"
        svc.client_secret = "test_google_client_secret"
        svc.developer_token = "test_dev_token"
    elif isinstance(svc, TikTokOAuthService):
        svc.app_id = "test_tiktok_app_id"
        svc.app_secret = "test_tiktok_secret"
    elif isinstance(svc, SnapchatOAuthService):
        svc.client_id = "test_snap_client_id"
        svc.client_secret = "test_snap_secret"


def _mock_session(*responses) -> MagicMock:
    """Create a mock aiohttp.ClientSession with pre-configured responses."""
    session = MagicMock()
    call_count = [0]

    def make_context(*args, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    session.get = MagicMock(side_effect=make_context)
    session.post = MagicMock(side_effect=make_context)
    session.delete = MagicMock(side_effect=make_context)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# #############################################################################
#
#  PART 1: DATA MODELS
#
# #############################################################################


@pytest.mark.unit
class TestOAuthState:

    def test_create_state(self) -> None:
        state = _make_state()
        assert state.state_token == "test_state_abc123"
        assert state.tenant_id == 1
        assert state.user_id == 42
        assert state.platform == "meta"

    def test_to_json_roundtrip(self) -> None:
        state = _make_state()
        json_str = state.to_json()
        parsed = json.loads(json_str)
        assert parsed["state_token"] == state.state_token
        assert parsed["tenant_id"] == 1

    def test_from_json_roundtrip(self) -> None:
        original = _make_state()
        json_str = original.to_json()
        restored = OAuthState.from_json(json_str)
        assert restored.state_token == original.state_token
        assert restored.tenant_id == original.tenant_id
        assert restored.user_id == original.user_id
        assert restored.platform == original.platform
        assert restored.redirect_uri == original.redirect_uri

    def test_default_created_at(self) -> None:
        state = OAuthState(
            state_token="abc", tenant_id=1, user_id=1,
            platform="meta", redirect_uri="http://test",
        )
        assert state.created_at is not None


@pytest.mark.unit
class TestOAuthTokens:

    def test_not_expired_when_no_expiry(self) -> None:
        tokens = OAuthTokens(access_token="tok123")
        assert tokens.is_expired() is False

    def test_not_expired_when_future(self) -> None:
        tokens = OAuthTokens(
            access_token="tok123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert tokens.is_expired() is False

    def test_expired_when_past(self) -> None:
        tokens = OAuthTokens(
            access_token="tok123",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert tokens.is_expired() is True

    def test_default_fields(self) -> None:
        tokens = OAuthTokens(access_token="tok")
        assert tokens.refresh_token is None
        assert tokens.token_type == "Bearer"
        assert tokens.scopes == []
        assert tokens.raw_response == {}

    def test_full_token(self) -> None:
        tokens = OAuthTokens(
            access_token="at", refresh_token="rt",
            token_type="Bearer", expires_in=3600,
            scopes=["ads_read"], raw_response={"extra": 1},
        )
        assert tokens.refresh_token == "rt"
        assert tokens.expires_in == 3600
        assert "ads_read" in tokens.scopes


@pytest.mark.unit
class TestAdAccountInfo:

    def test_defaults(self) -> None:
        info = AdAccountInfo(account_id="act_123", name="Test Account")
        assert info.currency == "USD"
        assert info.timezone == "UTC"
        assert info.status == "active"
        assert info.spend_cap is None
        assert info.permissions == []

    def test_full_info(self) -> None:
        info = AdAccountInfo(
            account_id="act_123", name="Biz Account",
            business_name="Acme Inc", currency="EUR",
            timezone="America/New_York", status="disabled",
            spend_cap=5000.0, amount_spent=1234.56,
            permissions=["MANAGE", "ANALYZE"],
        )
        assert info.business_name == "Acme Inc"
        assert info.spend_cap == 5000.0
        assert len(info.permissions) == 2


# #############################################################################
#
#  PART 2: OAUTH BASE SERVICE
#
# #############################################################################


@pytest.mark.unit
class TestOAuthServiceBase:

    def test_encrypt_decrypt_token(self) -> None:
        svc = MetaOAuthService()
        token = "EAABsbCS1ZAoIBO..."
        encrypted = svc.encrypt_token(token)
        assert encrypted != token
        decrypted = svc.decrypt_token(encrypted)
        assert decrypted == token

    def test_build_url_with_params(self) -> None:
        svc = MetaOAuthService()
        url = svc.build_url("https://example.com/auth", {"a": "1", "b": "2"})
        assert url.startswith("https://example.com/auth?")
        assert "a=1" in url
        assert "b=2" in url

    def test_build_url_filters_none(self) -> None:
        svc = MetaOAuthService()
        url = svc.build_url("https://example.com/auth", {"a": "1", "b": None})
        assert "b=" not in url
        assert "a=1" in url

    def test_build_url_no_params(self) -> None:
        svc = MetaOAuthService()
        url = svc.build_url("https://example.com/auth", {})
        assert url == "https://example.com/auth"

    def test_get_redirect_uri(self) -> None:
        svc = MetaOAuthService()
        uri = svc.get_redirect_uri()
        assert "/api/v1/oauth/meta/callback" in uri

    def test_state_expiry_constant(self) -> None:
        assert OAUTH_STATE_EXPIRY == 600


# #############################################################################
#
#  PART 3: STATE MANAGEMENT (mocked Redis)
#
# #############################################################################


@pytest.mark.unit
class TestOAuthStateManagement:

    @pytest.mark.asyncio
    async def test_create_state(self) -> None:
        svc = MetaOAuthService()
        mock_redis = _mock_redis()

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            state = await svc.create_state(tenant_id=1, user_id=42, redirect_uri="http://test")

        assert state.tenant_id == 1
        assert state.user_id == 42
        assert state.platform == "meta"
        assert len(state.state_token) > 20
        mock_redis.setex.assert_awaited_once()
        mock_redis.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validate_state_success(self) -> None:
        svc = MetaOAuthService()
        original = _make_state(platform="meta")
        mock_redis = _mock_redis()
        mock_redis.getdel.return_value = original.to_json()

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            result = await svc.validate_state("test_state_abc123")

        assert result is not None
        assert result.tenant_id == 1
        assert result.platform == "meta"
        mock_redis.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validate_state_expired(self) -> None:
        svc = MetaOAuthService()
        mock_redis = _mock_redis()
        mock_redis.getdel.return_value = None  # expired/not found

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            result = await svc.validate_state("expired_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_state_platform_mismatch(self) -> None:
        svc = MetaOAuthService()
        wrong_platform = _make_state(platform="google")
        mock_redis = _mock_redis()
        mock_redis.getdel.return_value = wrong_platform.to_json()

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            result = await svc.validate_state("test_state_abc123")

        assert result is None  # platform mismatch

    @pytest.mark.asyncio
    async def test_create_state_redis_error(self) -> None:
        svc = MetaOAuthService()
        mock_redis = _mock_redis()
        mock_redis.setex.side_effect = ConnectionError("Redis down")

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            with pytest.raises(ConnectionError):
                await svc.create_state(tenant_id=1, user_id=1, redirect_uri="http://test")

    @pytest.mark.asyncio
    async def test_validate_state_redis_error_returns_none(self) -> None:
        svc = MetaOAuthService()
        mock_redis = _mock_redis()
        mock_redis.getdel.side_effect = ConnectionError("Redis down")

        with patch.object(svc, "_get_redis_client", return_value=mock_redis):
            result = await svc.validate_state("some_token")

        assert result is None


# #############################################################################
#
#  PART 4: FACTORY
#
# #############################################################################


@pytest.mark.unit
class TestOAuthFactory:

    def test_supported_platforms(self) -> None:
        platforms = get_supported_platforms()
        assert set(platforms) == {"meta", "google", "tiktok", "snapchat"}

    def test_get_meta_service(self) -> None:
        svc = get_oauth_service("meta")
        assert isinstance(svc, MetaOAuthService)
        assert svc.platform == "meta"

    def test_get_google_service(self) -> None:
        svc = get_oauth_service("google")
        assert isinstance(svc, GoogleOAuthService)
        assert svc.platform == "google"

    def test_get_tiktok_service(self) -> None:
        svc = get_oauth_service("tiktok")
        assert isinstance(svc, TikTokOAuthService)
        assert svc.platform == "tiktok"

    def test_get_snapchat_service(self) -> None:
        svc = get_oauth_service("snapchat")
        assert isinstance(svc, SnapchatOAuthService)
        assert svc.platform == "snapchat"

    def test_case_insensitive(self) -> None:
        svc = get_oauth_service("META")
        assert isinstance(svc, MetaOAuthService)

    def test_unsupported_platform_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_oauth_service("twitter")

    def test_singleton_caching(self) -> None:
        svc1 = get_oauth_service("meta")
        svc2 = get_oauth_service("meta")
        assert svc1 is svc2

    def test_registry_has_four_platforms(self) -> None:
        assert len(_OAUTH_SERVICES) == 4


# #############################################################################
#
#  PART 5: META OAUTH SERVICE
#
# #############################################################################


@pytest.mark.unit
class TestMetaOAuthService:

    def test_platform_is_meta(self) -> None:
        svc = MetaOAuthService()
        assert svc.platform == "meta"

    def test_default_scopes(self) -> None:
        assert "ads_management" in META_DEFAULT_SCOPES
        assert "ads_read" in META_DEFAULT_SCOPES
        assert "business_management" in META_DEFAULT_SCOPES

    def test_auth_url_contains_required_params(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="meta")
        url = svc.get_authorization_url(state)
        assert "facebook.com" in url
        assert "client_id=" in url
        assert "state=test_state_abc123" in url
        assert "response_type=code" in url
        assert "scope=" in url

    def test_auth_url_custom_scopes(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="meta")
        url = svc.get_authorization_url(state, scopes=["ads_read"])
        assert "ads_read" in url
        assert "ads_management" not in url

    def test_redirect_uri_includes_meta(self) -> None:
        svc = MetaOAuthService()
        uri = svc.get_redirect_uri()
        assert "/oauth/meta/callback" in uri

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        short_resp = _mock_response(200, {"access_token": "short_tok", "expires_in": 3600})
        long_resp = _mock_response(200, {
            "access_token": "long_tok", "expires_in": 5184000, "token_type": "Bearer",
        })
        session = _mock_session(short_resp, long_resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            tokens = await svc.exchange_code_for_tokens("code123", "http://redirect")

        assert tokens.access_token == "long_tok"
        assert tokens.expires_in == 5184000

    @pytest.mark.asyncio
    async def test_exchange_fallback_to_short_lived(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        short_resp = _mock_response(200, {"access_token": "short_tok", "expires_in": 3600})
        long_fail = _mock_response(400, {"error": {"message": "Failed"}})
        session = _mock_session(short_resp, long_fail)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            tokens = await svc.exchange_code_for_tokens("code123", "http://redirect")

        assert tokens.access_token == "short_tok"

    @pytest.mark.asyncio
    async def test_exchange_first_step_fails(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        fail_resp = _mock_response(400, {"error": {"message": "Invalid code"}})
        session = _mock_session(fail_resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            with pytest.raises(Exception, match="Token exchange failed"):
                await svc.exchange_code_for_tokens("bad_code", "http://redirect")

    @pytest.mark.asyncio
    async def test_refresh_access_token(self) -> None:
        svc = MetaOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "access_token": "refreshed_tok", "expires_in": 5184000, "token_type": "Bearer",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            tokens = await svc.refresh_access_token("old_token")

        assert tokens.access_token == "refreshed_tok"

    @pytest.mark.asyncio
    async def test_fetch_ad_accounts(self) -> None:
        svc = MetaOAuthService()
        resp = _mock_response(200, {
            "data": [
                {
                    "id": "act_123",
                    "name": "Test Account",
                    "business_name": "Acme",
                    "currency": "USD",
                    "timezone_name": "US/Eastern",
                    "account_status": 1,
                    "spend_cap": "500000",  # in cents
                    "amount_spent": "123456",
                },
            ],
            "paging": {},
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            accounts = await svc.fetch_ad_accounts("token123")

        assert len(accounts) == 1
        assert accounts[0].account_id == "act_123"
        assert accounts[0].status == "active"
        assert accounts[0].spend_cap == 5000.0  # 500000 / 100
        assert accounts[0].amount_spent == 1234.56

    @pytest.mark.asyncio
    async def test_meta_account_status_mapping(self) -> None:
        svc = MetaOAuthService()
        resp = _mock_response(200, {
            "data": [
                {"id": "act_1", "name": "Active", "account_status": 1},
                {"id": "act_2", "name": "Disabled", "account_status": 2},
                {"id": "act_3", "name": "Unsettled", "account_status": 3},
                {"id": "act_4", "name": "Unknown", "account_status": 999},
            ],
            "paging": {},
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            accounts = await svc.fetch_ad_accounts("tok")

        assert accounts[0].status == "active"
        assert accounts[1].status == "disabled"
        assert accounts[2].status == "unsettled"
        assert accounts[3].status == "unknown"

    @pytest.mark.asyncio
    async def test_revoke_access_success(self) -> None:
        svc = MetaOAuthService()
        resp = _mock_response(200, {"success": True})
        session = _mock_session(resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            result = await svc.revoke_access("token123")

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_access_failure(self) -> None:
        svc = MetaOAuthService()
        resp = _mock_response(400, {"error": {"message": "Invalid token"}})
        session = _mock_session(resp)

        with patch("app.services.oauth.meta.aiohttp.ClientSession", return_value=session):
            result = await svc.revoke_access("bad_token")

        assert result is False


# #############################################################################
#
#  PART 6: GOOGLE OAUTH SERVICE
#
# #############################################################################


@pytest.mark.unit
class TestGoogleOAuthService:

    def test_platform_is_google(self) -> None:
        svc = GoogleOAuthService()
        assert svc.platform == "google"

    def test_default_scopes(self) -> None:
        assert "https://www.googleapis.com/auth/adwords" in GOOGLE_DEFAULT_SCOPES

    def test_auth_url_contains_required_params(self) -> None:
        svc = GoogleOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="google")
        url = svc.get_authorization_url(state)
        assert "accounts.google.com" in url
        assert "client_id=" in url
        assert "state=test_state_abc123" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    def test_auth_url_custom_scopes(self) -> None:
        svc = GoogleOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="google")
        url = svc.get_authorization_url(state, scopes=["custom_scope"])
        assert "custom_scope" in url

    def test_redirect_uri_includes_google(self) -> None:
        svc = GoogleOAuthService()
        uri = svc.get_redirect_uri()
        assert "/oauth/google/callback" in uri

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self) -> None:
        svc = GoogleOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "access_token": "google_tok",
            "refresh_token": "google_refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/adwords",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.google.aiohttp.ClientSession", return_value=session):
            tokens = await svc.exchange_code_for_tokens("code123", "http://redirect")

        assert tokens.access_token == "google_tok"
        assert tokens.refresh_token == "google_refresh"
        assert tokens.expires_in == 3600

    @pytest.mark.asyncio
    async def test_refresh_access_token(self) -> None:
        svc = GoogleOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "access_token": "new_google_tok", "expires_in": 3600,
            "token_type": "Bearer",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.google.aiohttp.ClientSession", return_value=session):
            tokens = await svc.refresh_access_token("refresh_tok")

        assert tokens.access_token == "new_google_tok"

    @pytest.mark.asyncio
    async def test_revoke_access(self) -> None:
        svc = GoogleOAuthService()
        resp = _mock_response(200, {})
        session = _mock_session(resp)

        with patch("app.services.oauth.google.aiohttp.ClientSession", return_value=session):
            result = await svc.revoke_access("token123")

        assert result is True


# #############################################################################
#
#  PART 7: TIKTOK OAUTH SERVICE
#
# #############################################################################


@pytest.mark.unit
class TestTikTokOAuthService:

    def test_platform_is_tiktok(self) -> None:
        svc = TikTokOAuthService()
        assert svc.platform == "tiktok"

    def test_default_scopes(self) -> None:
        assert "advertiser.read" in TIKTOK_DEFAULT_SCOPES
        assert "campaign.read" in TIKTOK_DEFAULT_SCOPES
        assert "report.read" in TIKTOK_DEFAULT_SCOPES

    def test_auth_url_contains_required_params(self) -> None:
        svc = TikTokOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="tiktok")
        url = svc.get_authorization_url(state)
        assert "tiktok.com" in url
        assert "app_id=" in url
        assert "state=test_state_abc123" in url

    def test_redirect_uri_includes_tiktok(self) -> None:
        svc = TikTokOAuthService()
        uri = svc.get_redirect_uri()
        assert "/oauth/tiktok/callback" in uri

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self) -> None:
        svc = TikTokOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "code": 0,
            "data": {
                "access_token": "tiktok_tok",
                "refresh_token": "tiktok_refresh",
                "advertiser_ids": ["adv_123"],
            },
            "message": "OK",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.tiktok.aiohttp.ClientSession", return_value=session):
            tokens = await svc.exchange_code_for_tokens("code123", "http://redirect")

        assert tokens.access_token == "tiktok_tok"

    @pytest.mark.asyncio
    async def test_refresh_access_token(self) -> None:
        svc = TikTokOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "code": 0,
            "data": {
                "access_token": "new_tiktok_tok",
                "refresh_token": "new_tiktok_refresh",
            },
            "message": "OK",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.tiktok.aiohttp.ClientSession", return_value=session):
            tokens = await svc.refresh_access_token("old_refresh")

        assert tokens.access_token == "new_tiktok_tok"

    @pytest.mark.asyncio
    async def test_revoke_access_returns_true(self) -> None:
        """TikTok has no revoke endpoint; service returns True (let expire)."""
        svc = TikTokOAuthService()
        result = await svc.revoke_access("token123")
        assert result is True


# #############################################################################
#
#  PART 8: SNAPCHAT OAUTH SERVICE
#
# #############################################################################


@pytest.mark.unit
class TestSnapchatOAuthService:

    def test_platform_is_snapchat(self) -> None:
        svc = SnapchatOAuthService()
        assert svc.platform == "snapchat"

    def test_default_scopes(self) -> None:
        assert "snapchat-marketing-api" in SNAPCHAT_DEFAULT_SCOPES

    def test_auth_url_contains_required_params(self) -> None:
        svc = SnapchatOAuthService()
        _set_test_credentials(svc)
        state = _make_state(platform="snapchat")
        url = svc.get_authorization_url(state)
        assert "snapchat.com" in url
        assert "client_id=" in url
        assert "state=test_state_abc123" in url
        assert "response_type=code" in url

    def test_redirect_uri_includes_snapchat(self) -> None:
        svc = SnapchatOAuthService()
        uri = svc.get_redirect_uri()
        assert "/oauth/snapchat/callback" in uri

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self) -> None:
        svc = SnapchatOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "access_token": "snap_tok",
            "refresh_token": "snap_refresh",
            "expires_in": 1800,
            "token_type": "Bearer",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.snapchat.aiohttp.ClientSession", return_value=session):
            tokens = await svc.exchange_code_for_tokens("code123", "http://redirect")

        assert tokens.access_token == "snap_tok"
        assert tokens.refresh_token == "snap_refresh"
        assert tokens.expires_in == 1800

    @pytest.mark.asyncio
    async def test_refresh_access_token(self) -> None:
        svc = SnapchatOAuthService()
        _set_test_credentials(svc)
        resp = _mock_response(200, {
            "access_token": "new_snap_tok",
            "refresh_token": "new_snap_refresh",
            "expires_in": 1800,
            "token_type": "Bearer",
        })
        session = _mock_session(resp)

        with patch("app.services.oauth.snapchat.aiohttp.ClientSession", return_value=session):
            tokens = await svc.refresh_access_token("old_refresh")

        assert tokens.access_token == "new_snap_tok"

    @pytest.mark.asyncio
    async def test_revoke_access_returns_true(self) -> None:
        """Snapchat has no revoke endpoint; service returns True."""
        svc = SnapchatOAuthService()
        result = await svc.revoke_access("token123")
        assert result is True


# #############################################################################
#
#  PART 9: CROSS-PLATFORM CONSISTENCY
#
# #############################################################################


@pytest.mark.unit
class TestCrossPlatformConsistency:

    @pytest.mark.parametrize("platform_cls,platform_name", [
        (MetaOAuthService, "meta"),
        (GoogleOAuthService, "google"),
        (TikTokOAuthService, "tiktok"),
        (SnapchatOAuthService, "snapchat"),
    ])
    def test_platform_attribute(self, platform_cls, platform_name) -> None:
        svc = platform_cls()
        assert svc.platform == platform_name

    @pytest.mark.parametrize("platform_cls", [
        MetaOAuthService, GoogleOAuthService, TikTokOAuthService, SnapchatOAuthService,
    ])
    def test_inherits_oauth_service(self, platform_cls) -> None:
        assert issubclass(platform_cls, OAuthService)

    @pytest.mark.parametrize("platform_cls,platform_name", [
        (MetaOAuthService, "meta"),
        (GoogleOAuthService, "google"),
        (TikTokOAuthService, "tiktok"),
        (SnapchatOAuthService, "snapchat"),
    ])
    def test_redirect_uri_format(self, platform_cls, platform_name) -> None:
        svc = platform_cls()
        uri = svc.get_redirect_uri()
        assert f"/api/v1/oauth/{platform_name}/callback" in uri

    @pytest.mark.parametrize("platform_cls", [
        MetaOAuthService, GoogleOAuthService, TikTokOAuthService, SnapchatOAuthService,
    ])
    def test_encrypt_decrypt_roundtrip(self, platform_cls) -> None:
        svc = platform_cls()
        token = "test_token_12345"
        enc = svc.encrypt_token(token)
        assert enc != token
        assert svc.decrypt_token(enc) == token

    @pytest.mark.parametrize("platform_cls,platform_name", [
        (MetaOAuthService, "meta"),
        (GoogleOAuthService, "google"),
        (TikTokOAuthService, "tiktok"),
        (SnapchatOAuthService, "snapchat"),
    ])
    def test_auth_url_generation(self, platform_cls, platform_name) -> None:
        svc = platform_cls()
        _set_test_credentials(svc)
        state = _make_state(platform=platform_name)
        url = svc.get_authorization_url(state)
        assert "state=test_state_abc123" in url
        assert len(url) > 50
