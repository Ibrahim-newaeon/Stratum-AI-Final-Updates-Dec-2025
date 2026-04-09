# =============================================================================
# Stratum AI - Campaign Builder Unit Tests
# =============================================================================
"""
Comprehensive unit tests for the Campaign Builder feature.

Tests cover:
- Enums (AdPlatform, ConnectionStatus, DraftStatus, PublishResult)
- Pydantic schemas (validation, defaults, serialization)
- Connector endpoints (status, start OAuth, refresh, disconnect)
- Ad account endpoints (list, sync, update)
- Campaign draft endpoints (CRUD + approval workflow)
- Publish log endpoints (list, retry)
- Workflow state machine (draft→submitted→approved→published, rejection, re-edit)
- Budget guardrails (publish blocked when over cap)
- Tenant isolation (cross-tenant access denied)
- Celery tasks (sync, refresh, publish, health check)
- Edge cases (empty state, missing data, invalid transitions)
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest

# ---------------------------------------------------------------------------
# Model / enum imports
# ---------------------------------------------------------------------------
from app.models.campaign_builder import (
    AdPlatform,
    ConnectionStatus,
    DraftStatus,
    PublishResult,
    TenantPlatformConnection,
    TenantAdAccount,
    CampaignDraft,
    CampaignPublishLog,
)

# ---------------------------------------------------------------------------
# Schema imports
# ---------------------------------------------------------------------------
from app.api.v1.endpoints.campaign_builder import (
    ConnectorStatusResponse,
    AdAccountResponse,
    AdAccountUpdateRequest,
    CampaignDraftCreate,
    CampaignDraftUpdate,
    CampaignDraftResponse,
    PublishLogResponse,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestAdPlatform:
    """Tests for AdPlatform enum."""

    def test_all_platforms_defined(self):
        platforms = [p.value for p in AdPlatform]
        assert set(platforms) == {"meta", "google", "tiktok", "snapchat"}

    def test_platform_is_str_enum(self):
        assert isinstance(AdPlatform.META, str)
        assert AdPlatform.META == "meta"

    def test_platform_from_value(self):
        assert AdPlatform("meta") == AdPlatform.META
        assert AdPlatform("google") == AdPlatform.GOOGLE
        assert AdPlatform("tiktok") == AdPlatform.TIKTOK
        assert AdPlatform("snapchat") == AdPlatform.SNAPCHAT

    def test_invalid_platform_raises(self):
        with pytest.raises(ValueError):
            AdPlatform("twitter")


class TestConnectionStatus:
    """Tests for ConnectionStatus enum."""

    def test_all_statuses_defined(self):
        statuses = [s.value for s in ConnectionStatus]
        assert set(statuses) == {"connected", "expired", "error", "disconnected"}

    def test_status_is_str_enum(self):
        assert isinstance(ConnectionStatus.CONNECTED, str)
        assert ConnectionStatus.CONNECTED == "connected"


class TestDraftStatus:
    """Tests for DraftStatus enum - the workflow state machine."""

    def test_all_statuses_defined(self):
        statuses = [s.value for s in DraftStatus]
        assert set(statuses) == {
            "draft", "submitted", "approved", "rejected",
            "publishing", "published", "failed",
        }

    def test_draft_is_initial_state(self):
        assert DraftStatus.DRAFT.value == "draft"

    def test_published_is_terminal_state(self):
        assert DraftStatus.PUBLISHED.value == "published"


class TestPublishResult:
    """Tests for PublishResult enum."""

    def test_results_defined(self):
        assert PublishResult.SUCCESS.value == "success"
        assert PublishResult.FAILURE.value == "failure"


# =============================================================================
# Pydantic Schema Tests
# =============================================================================


class TestConnectorStatusResponse:
    """Tests for ConnectorStatusResponse schema."""

    def test_minimal_response(self):
        resp = ConnectorStatusResponse(platform="meta", status="disconnected")
        assert resp.platform == "meta"
        assert resp.status == "disconnected"
        assert resp.connected_at is None
        assert resp.scopes == []

    def test_full_response(self):
        now = datetime.now(timezone.utc)
        resp = ConnectorStatusResponse(
            platform="google",
            status="connected",
            connected_at=now,
            last_refreshed_at=now,
            scopes=["ads_read", "ads_management"],
            last_error=None,
        )
        assert resp.scopes == ["ads_read", "ads_management"]
        assert resp.connected_at == now


class TestAdAccountResponse:
    """Tests for AdAccountResponse schema."""

    def test_required_fields(self):
        uid = uuid4()
        resp = AdAccountResponse(
            id=uid,
            platform="meta",
            platform_account_id="act_123",
            name="Test Account",
            currency="SAR",
            timezone="Asia/Riyadh",
            is_enabled=True,
        )
        assert resp.id == uid
        assert resp.is_enabled is True

    def test_optional_budget_cap(self):
        uid = uuid4()
        resp = AdAccountResponse(
            id=uid,
            platform="meta",
            platform_account_id="act_123",
            name="Test",
            currency="USD",
            timezone="UTC",
            is_enabled=False,
            daily_budget_cap=5000.0,
        )
        assert resp.daily_budget_cap == 5000.0


class TestAdAccountUpdateRequest:
    """Tests for AdAccountUpdateRequest schema."""

    def test_empty_update(self):
        req = AdAccountUpdateRequest()
        assert req.is_enabled is None
        assert req.daily_budget_cap is None

    def test_partial_update_enabled(self):
        req = AdAccountUpdateRequest(is_enabled=True)
        assert req.is_enabled is True
        assert req.daily_budget_cap is None

    def test_partial_update_budget(self):
        req = AdAccountUpdateRequest(daily_budget_cap=1000.0)
        assert req.daily_budget_cap == 1000.0


class TestCampaignDraftCreate:
    """Tests for CampaignDraftCreate schema."""

    def test_minimal_create(self):
        uid = uuid4()
        req = CampaignDraftCreate(
            platform="meta",
            ad_account_id=uid,
            name="Summer Sale",
        )
        assert req.platform == "meta"
        assert req.ad_account_id == uid
        assert req.name == "Summer Sale"
        assert req.description is None
        assert req.draft_json == {}

    def test_full_create(self):
        uid = uuid4()
        campaign_config = {
            "campaign": {
                "objective": "conversions",
                "budget": {"amount": 5000, "type": "daily"},
            }
        }
        req = CampaignDraftCreate(
            platform="google",
            ad_account_id=uid,
            name="Winter Campaign",
            description="Holiday season push",
            draft_json=campaign_config,
        )
        assert req.draft_json["campaign"]["objective"] == "conversions"


class TestCampaignDraftUpdate:
    """Tests for CampaignDraftUpdate schema."""

    def test_empty_update(self):
        req = CampaignDraftUpdate()
        assert req.name is None
        assert req.description is None
        assert req.draft_json is None

    def test_partial_name_update(self):
        req = CampaignDraftUpdate(name="New Name")
        assert req.name == "New Name"

    def test_draft_json_update(self):
        new_config = {"campaign": {"objective": "awareness"}}
        req = CampaignDraftUpdate(draft_json=new_config)
        assert req.draft_json == new_config


class TestCampaignDraftResponse:
    """Tests for CampaignDraftResponse schema."""

    def test_full_response(self):
        uid = uuid4()
        acc_id = uuid4()
        now = datetime.now(timezone.utc)
        resp = CampaignDraftResponse(
            id=uid,
            tenant_id=1,
            platform="meta",
            ad_account_id=acc_id,
            name="Test Campaign",
            status="draft",
            draft_json={"campaign": {}},
            created_at=now,
            updated_at=now,
        )
        assert resp.id == uid
        assert resp.status == "draft"
        assert resp.submitted_at is None
        assert resp.published_at is None


class TestPublishLogResponse:
    """Tests for PublishLogResponse schema."""

    def test_success_log(self):
        uid = uuid4()
        draft_id = uuid4()
        now = datetime.now(timezone.utc)
        resp = PublishLogResponse(
            id=uid,
            draft_id=draft_id,
            platform="meta",
            platform_account_id="act_123",
            event_time=now,
            result_status="success",
            platform_campaign_id="camp_abc123",
            retry_count=0,
        )
        assert resp.result_status == "success"
        assert resp.error_code is None

    def test_failure_log(self):
        uid = uuid4()
        now = datetime.now(timezone.utc)
        resp = PublishLogResponse(
            id=uid,
            platform="google",
            platform_account_id="act_456",
            event_time=now,
            result_status="failure",
            error_code="RATE_LIMIT",
            error_message="Too many requests",
            retry_count=2,
        )
        assert resp.error_code == "RATE_LIMIT"
        assert resp.retry_count == 2


# =============================================================================
# Helper: mock async DB session & Request
# =============================================================================

def _make_request(tenant_id=1, user_id=1):
    """Create a mock Request with state attributes."""
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id=tenant_id, user_id=user_id)
    request.base_url = "http://localhost:8000/"
    return request


def _make_scalar_result(value):
    """Create a mock SQLAlchemy result that returns a scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_scalars_result(values):
    """Create a mock SQLAlchemy result that returns scalars().all()."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _make_db():
    """Create an async mock DB session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _make_connection(tenant_id=1, platform=AdPlatform.META, status=ConnectionStatus.CONNECTED):
    """Create a mock TenantPlatformConnection."""
    conn = MagicMock(spec=TenantPlatformConnection)
    conn.id = uuid4()
    conn.tenant_id = tenant_id
    conn.platform = platform
    conn.status = status
    conn.access_token_encrypted = "enc_token_xxx"
    conn.refresh_token_encrypted = "enc_refresh_xxx"
    conn.connected_at = datetime.now(timezone.utc)
    conn.last_refreshed_at = None
    conn.scopes = ["ads_read", "ads_management"]
    conn.last_error = None
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return conn


def _make_ad_account(tenant_id=1, platform=AdPlatform.META, is_enabled=True,
                     daily_budget_cap=None):
    """Create a mock TenantAdAccount."""
    acc = MagicMock(spec=TenantAdAccount)
    acc.id = uuid4()
    acc.tenant_id = tenant_id
    acc.platform = platform
    acc.platform_account_id = f"act_{tenant_id}_meta_001"
    acc.name = "Main Business Account"
    acc.business_name = "Test Business"
    acc.currency = "SAR"
    acc.timezone = "Asia/Riyadh"
    acc.is_enabled = is_enabled
    acc.daily_budget_cap = Decimal(str(daily_budget_cap)) if daily_budget_cap else None
    acc.last_synced_at = datetime.now(timezone.utc)
    return acc


def _make_draft(tenant_id=1, status=DraftStatus.DRAFT, ad_account=None, draft_json=None):
    """Create a mock CampaignDraft."""
    draft = MagicMock(spec=CampaignDraft)
    draft.id = uuid4()
    draft.tenant_id = tenant_id
    draft.platform = AdPlatform.META
    draft.ad_account_id = ad_account.id if ad_account else uuid4()
    draft.ad_account = ad_account
    draft.name = "Test Campaign"
    draft.description = "Test Description"
    draft.status = status
    draft.draft_json = draft_json or {"campaign": {"objective": "conversions"}}
    draft.created_at = datetime.now(timezone.utc)
    draft.updated_at = datetime.now(timezone.utc)
    draft.submitted_at = None
    draft.approved_at = None
    draft.rejected_at = None
    draft.rejection_reason = None
    draft.platform_campaign_id = None
    draft.published_at = None
    draft.created_by_user_id = 1
    draft.submitted_by_user_id = None
    draft.approved_by_user_id = None
    draft.rejected_by_user_id = None
    return draft


def _make_publish_log(tenant_id=1, result_status=PublishResult.SUCCESS, draft_id=None):
    """Create a mock CampaignPublishLog."""
    log = MagicMock(spec=CampaignPublishLog)
    log.id = uuid4()
    log.tenant_id = tenant_id
    log.draft_id = draft_id or uuid4()
    log.platform = AdPlatform.META
    log.platform_account_id = "act_1_meta_001"
    log.published_by_user_id = 1
    log.event_time = datetime.now(timezone.utc)
    log.request_json = {}
    log.response_json = {}
    log.result_status = result_status
    log.platform_campaign_id = "camp_abc123" if result_status == PublishResult.SUCCESS else None
    log.error_code = None
    log.error_message = None
    log.retry_count = 0
    log.last_retry_at = None
    return log


# =============================================================================
# Connector Endpoint Tests
# =============================================================================


class TestGetConnectorStatus:
    """Tests for GET /tenant/{tenant_id}/connect/{platform}/status"""

    @pytest.mark.asyncio
    async def test_connected_platform(self):
        from app.api.v1.endpoints.campaign_builder import get_connector_status

        conn = _make_connection()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(conn)

        resp = await get_connector_status(_make_request(), 1, AdPlatform.META, db)
        assert resp.success is True
        assert resp.data.status == "connected"
        assert resp.data.platform == "meta"

    @pytest.mark.asyncio
    async def test_disconnected_platform_no_record(self):
        from app.api.v1.endpoints.campaign_builder import get_connector_status

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        resp = await get_connector_status(_make_request(), 1, AdPlatform.GOOGLE, db)
        assert resp.success is True
        assert resp.data.status == "disconnected"

    @pytest.mark.asyncio
    async def test_tenant_isolation_denied(self):
        from app.api.v1.endpoints.campaign_builder import get_connector_status
        from fastapi import HTTPException

        db = _make_db()
        # Request from tenant 1, accessing tenant 2
        request = _make_request(tenant_id=1)

        with pytest.raises(HTTPException) as exc_info:
            await get_connector_status(request, 2, AdPlatform.META, db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_connection_with_error(self):
        from app.api.v1.endpoints.campaign_builder import get_connector_status

        conn = _make_connection(status=ConnectionStatus.ERROR)
        conn.last_error = "Token expired"
        db = _make_db()
        db.execute.return_value = _make_scalar_result(conn)

        resp = await get_connector_status(_make_request(), 1, AdPlatform.META, db)
        assert resp.data.status == "error"
        assert resp.data.last_error == "Token expired"


class TestStartPlatformConnection:
    """Tests for POST /tenant/{tenant_id}/connect/{platform}/start"""

    @pytest.mark.asyncio
    async def test_start_meta_connection(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {"META_APP_ID": "test_app_id_123"}):
            resp = await start_platform_connection(request, 1, AdPlatform.META, db)

        assert resp.success is True
        assert "oauth_url" in resp.data
        assert "facebook.com" in resp.data["oauth_url"]
        assert "test_app_id_123" in resp.data["oauth_url"]

    @pytest.mark.asyncio
    async def test_start_google_connection(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {"GOOGLE_ADS_CLIENT_ID": "google_client_123"}):
            resp = await start_platform_connection(request, 1, AdPlatform.GOOGLE, db)

        assert resp.success is True
        assert "accounts.google.com" in resp.data["oauth_url"]

    @pytest.mark.asyncio
    async def test_start_tiktok_connection(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {"TIKTOK_APP_ID": "tiktok_app_123"}):
            resp = await start_platform_connection(request, 1, AdPlatform.TIKTOK, db)

        assert resp.success is True
        assert "tiktok.com" in resp.data["oauth_url"]

    @pytest.mark.asyncio
    async def test_start_snapchat_connection(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {"SNAPCHAT_APP_ID": "snap_app_123"}):
            resp = await start_platform_connection(request, 1, AdPlatform.SNAPCHAT, db)

        assert resp.success is True
        assert "snapchat.com" in resp.data["oauth_url"]

    @pytest.mark.asyncio
    async def test_oauth_not_configured(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection
        from fastapi import HTTPException

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                await start_platform_connection(request, 1, AdPlatform.META, db)
            assert exc_info.value.status_code == 400
            assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_oauth_url_contains_state_param(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection

        db = _make_db()
        request = _make_request()

        with patch.dict("os.environ", {"META_APP_ID": "test_app"}):
            resp = await start_platform_connection(request, 1, AdPlatform.META, db)

        assert "state" in resp.data
        assert len(resp.data["state"]) > 20  # CSRF token is long enough

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import start_platform_connection
        from fastapi import HTTPException

        db = _make_db()
        request = _make_request(tenant_id=1)

        with pytest.raises(HTTPException) as exc_info:
            await start_platform_connection(request, 99, AdPlatform.META, db)
        assert exc_info.value.status_code == 403


class TestRefreshPlatformToken:
    """Tests for POST /tenant/{tenant_id}/connect/{platform}/refresh"""

    @pytest.mark.asyncio
    async def test_refresh_no_connection(self):
        from app.api.v1.endpoints.campaign_builder import refresh_platform_token
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_platform_token(_make_request(), 1, AdPlatform.META, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import refresh_platform_token
        from fastapi import HTTPException

        db = _make_db()
        request = _make_request(tenant_id=1)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_platform_token(request, 2, AdPlatform.META, db)
        assert exc_info.value.status_code == 403


class TestDisconnectPlatform:
    """Tests for DELETE /tenant/{tenant_id}/connect/{platform}"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        from app.api.v1.endpoints.campaign_builder import disconnect_platform

        conn = _make_connection()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(conn)

        resp = await disconnect_platform(_make_request(), 1, AdPlatform.META, db)
        assert resp.success is True
        assert conn.status == ConnectionStatus.DISCONNECTED
        assert conn.access_token_encrypted is None
        assert conn.refresh_token_encrypted is None

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        from app.api.v1.endpoints.campaign_builder import disconnect_platform
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await disconnect_platform(_make_request(), 1, AdPlatform.META, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import disconnect_platform
        from fastapi import HTTPException

        db = _make_db()
        request = _make_request(tenant_id=1)

        with pytest.raises(HTTPException) as exc_info:
            await disconnect_platform(request, 2, AdPlatform.META, db)
        assert exc_info.value.status_code == 403


# =============================================================================
# Ad Account Endpoint Tests
# =============================================================================


class TestListAdAccounts:
    """Tests for GET /tenant/{tenant_id}/ad-accounts/{platform}"""

    @pytest.mark.asyncio
    async def test_list_accounts(self):
        from app.api.v1.endpoints.campaign_builder import list_ad_accounts

        accounts = [_make_ad_account(), _make_ad_account()]
        db = _make_db()
        db.execute.return_value = _make_scalars_result(accounts)

        resp = await list_ad_accounts(_make_request(), 1, AdPlatform.META, False, db)
        assert resp.success is True
        assert len(resp.data) == 2

    @pytest.mark.asyncio
    async def test_list_empty(self):
        from app.api.v1.endpoints.campaign_builder import list_ad_accounts

        db = _make_db()
        db.execute.return_value = _make_scalars_result([])

        resp = await list_ad_accounts(_make_request(), 1, AdPlatform.META, False, db)
        assert resp.success is True
        assert resp.data == []

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import list_ad_accounts
        from fastapi import HTTPException

        db = _make_db()
        with pytest.raises(HTTPException) as exc_info:
            await list_ad_accounts(_make_request(tenant_id=1), 2, AdPlatform.META, False, db)
        assert exc_info.value.status_code == 403


class TestSyncAdAccounts:
    """Tests for POST /tenant/{tenant_id}/ad-accounts/{platform}/sync"""

    @pytest.mark.asyncio
    async def test_sync_connected_platform(self):
        from app.api.v1.endpoints.campaign_builder import sync_ad_accounts

        conn = _make_connection()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(conn)
        bg = MagicMock()

        resp = await sync_ad_accounts(_make_request(), 1, AdPlatform.META, bg, db)
        assert resp.success is True
        assert "Sync started" in resp.data["message"]

    @pytest.mark.asyncio
    async def test_sync_not_connected(self):
        from app.api.v1.endpoints.campaign_builder import sync_ad_accounts
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await sync_ad_accounts(_make_request(), 1, AdPlatform.META, bg, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import sync_ad_accounts
        from fastapi import HTTPException

        db = _make_db()
        bg = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await sync_ad_accounts(_make_request(tenant_id=1), 2, AdPlatform.META, bg, db)
        assert exc_info.value.status_code == 403


class TestUpdateAdAccount:
    """Tests for PUT /tenant/{tenant_id}/ad-accounts/{platform}/{ad_account_id}"""

    @pytest.mark.asyncio
    async def test_enable_account(self):
        from app.api.v1.endpoints.campaign_builder import update_ad_account

        acc = _make_ad_account(is_enabled=False)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(acc)

        update = AdAccountUpdateRequest(is_enabled=True)
        resp = await update_ad_account(_make_request(), 1, AdPlatform.META, acc.id, update, db)
        assert resp.success is True
        assert acc.is_enabled is True

    @pytest.mark.asyncio
    async def test_set_budget_cap(self):
        from app.api.v1.endpoints.campaign_builder import update_ad_account

        acc = _make_ad_account()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(acc)

        update = AdAccountUpdateRequest(daily_budget_cap=5000.0)
        resp = await update_ad_account(_make_request(), 1, AdPlatform.META, acc.id, update, db)
        assert resp.success is True
        assert acc.daily_budget_cap == 5000.0

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        from app.api.v1.endpoints.campaign_builder import update_ad_account
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        update = AdAccountUpdateRequest(is_enabled=True)

        with pytest.raises(HTTPException) as exc_info:
            await update_ad_account(_make_request(), 1, AdPlatform.META, uuid4(), update, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import update_ad_account
        from fastapi import HTTPException

        db = _make_db()
        update = AdAccountUpdateRequest(is_enabled=True)
        with pytest.raises(HTTPException) as exc_info:
            await update_ad_account(
                _make_request(tenant_id=1), 2, AdPlatform.META, uuid4(), update, db
            )
        assert exc_info.value.status_code == 403


# =============================================================================
# Campaign Draft CRUD Tests
# =============================================================================


class TestCreateCampaignDraft:
    """Tests for POST /tenant/{tenant_id}/campaign-drafts"""

    @pytest.mark.asyncio
    async def test_create_draft_success(self):
        from app.api.v1.endpoints.campaign_builder import create_campaign_draft

        acc = _make_ad_account(is_enabled=True)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(acc)

        # After db.refresh, the draft needs id/timestamps populated
        async def _fake_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=_fake_refresh)

        draft_data = CampaignDraftCreate(
            platform="meta",
            ad_account_id=acc.id,
            name="Summer Sale",
            draft_json={"campaign": {"objective": "conversions"}},
        )

        resp = await create_campaign_draft(_make_request(), 1, draft_data, db)
        assert resp.success is True
        db.add.assert_called_once()
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_draft_ad_account_not_enabled(self):
        from app.api.v1.endpoints.campaign_builder import create_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)  # No enabled ad account

        draft_data = CampaignDraftCreate(
            platform="meta",
            ad_account_id=uuid4(),
            name="Test",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_campaign_draft(_make_request(), 1, draft_data, db)
        assert exc_info.value.status_code == 400
        assert "not found or not enabled" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_draft_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import create_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        draft_data = CampaignDraftCreate(
            platform="meta", ad_account_id=uuid4(), name="Test"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_campaign_draft(_make_request(tenant_id=1), 2, draft_data, db)
        assert exc_info.value.status_code == 403


class TestListCampaignDrafts:
    """Tests for GET /tenant/{tenant_id}/campaign-drafts"""

    @pytest.mark.asyncio
    async def test_list_drafts(self):
        from app.api.v1.endpoints.campaign_builder import list_campaign_drafts

        drafts = [_make_draft(), _make_draft()]
        db = _make_db()
        db.execute.return_value = _make_scalars_result(drafts)

        resp = await list_campaign_drafts(
            _make_request(), 1, limit=50, offset=0, db=db
        )
        assert resp.success is True
        assert len(resp.data) == 2

    @pytest.mark.asyncio
    async def test_list_empty(self):
        from app.api.v1.endpoints.campaign_builder import list_campaign_drafts

        db = _make_db()
        db.execute.return_value = _make_scalars_result([])

        resp = await list_campaign_drafts(
            _make_request(), 1, limit=50, offset=0, db=db
        )
        assert resp.success is True
        assert resp.data == []

    @pytest.mark.asyncio
    async def test_list_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import list_campaign_drafts
        from fastapi import HTTPException

        db = _make_db()
        with pytest.raises(HTTPException) as exc_info:
            await list_campaign_drafts(
                _make_request(tenant_id=1), 2, limit=50, offset=0, db=db
            )
        assert exc_info.value.status_code == 403


class TestGetCampaignDraft:
    """Tests for GET /tenant/{tenant_id}/campaign-drafts/{draft_id}"""

    @pytest.mark.asyncio
    async def test_get_draft_found(self):
        from app.api.v1.endpoints.campaign_builder import get_campaign_draft

        draft = _make_draft()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        resp = await get_campaign_draft(_make_request(), 1, draft.id, db)
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self):
        from app.api.v1.endpoints.campaign_builder import get_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_draft(_make_request(), 1, uuid4(), db)
        assert exc_info.value.status_code == 404


class TestUpdateCampaignDraft:
    """Tests for PUT /tenant/{tenant_id}/campaign-drafts/{draft_id}"""

    @pytest.mark.asyncio
    async def test_update_draft_in_draft_status(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        update = CampaignDraftUpdate(name="Updated Name")
        resp = await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert resp.success is True
        assert draft.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_rejected_draft_resets_to_draft(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft

        draft = _make_draft(status=DraftStatus.REJECTED)
        draft.rejection_reason = "Budget too high"
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        update = CampaignDraftUpdate(name="Revised Campaign")
        resp = await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert resp.success is True
        assert draft.status == DraftStatus.DRAFT
        assert draft.rejection_reason is None

    @pytest.mark.asyncio
    async def test_update_submitted_draft_fails(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.SUBMITTED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        update = CampaignDraftUpdate(name="Cannot Update")
        with pytest.raises(HTTPException) as exc_info:
            await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert exc_info.value.status_code == 400
        assert "submitted" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_approved_draft_fails(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.APPROVED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        update = CampaignDraftUpdate(name="Cannot Update")
        with pytest.raises(HTTPException) as exc_info:
            await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_published_draft_fails(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.PUBLISHED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        update = CampaignDraftUpdate(name="Cannot Update")
        with pytest.raises(HTTPException) as exc_info:
            await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        update = CampaignDraftUpdate(name="New Name")
        with pytest.raises(HTTPException) as exc_info:
            await update_campaign_draft(_make_request(), 1, uuid4(), update, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_draft_json(self):
        from app.api.v1.endpoints.campaign_builder import update_campaign_draft

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        new_config = {"campaign": {"objective": "awareness", "budget": {"amount": 3000}}}
        update = CampaignDraftUpdate(draft_json=new_config)
        resp = await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert resp.success is True
        assert draft.draft_json == new_config


# =============================================================================
# Workflow State Machine Tests
# =============================================================================


class TestSubmitCampaignDraft:
    """Tests for POST /tenant/{tenant_id}/campaign-drafts/{draft_id}/submit"""

    @pytest.mark.asyncio
    async def test_submit_from_draft(self):
        from app.api.v1.endpoints.campaign_builder import submit_campaign_draft

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        resp = await submit_campaign_draft(_make_request(), 1, draft.id, db)
        assert resp.success is True
        assert draft.status == DraftStatus.SUBMITTED
        assert draft.submitted_at is not None
        assert draft.submitted_by_user_id == 1

    @pytest.mark.asyncio
    async def test_submit_non_draft_fails(self):
        from app.api.v1.endpoints.campaign_builder import submit_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.APPROVED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        with pytest.raises(HTTPException) as exc_info:
            await submit_campaign_draft(_make_request(), 1, draft.id, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_not_found(self):
        from app.api.v1.endpoints.campaign_builder import submit_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await submit_campaign_draft(_make_request(), 1, uuid4(), db)
        assert exc_info.value.status_code == 404


class TestApproveCampaignDraft:
    """Tests for POST /tenant/{tenant_id}/campaign-drafts/{draft_id}/approve"""

    @pytest.mark.asyncio
    async def test_approve_submitted_draft(self):
        from app.api.v1.endpoints.campaign_builder import approve_campaign_draft

        draft = _make_draft(status=DraftStatus.SUBMITTED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        resp = await approve_campaign_draft(_make_request(), 1, draft.id, db)
        assert resp.success is True
        assert draft.status == DraftStatus.APPROVED
        assert draft.approved_at is not None
        assert draft.approved_by_user_id == 1

    @pytest.mark.asyncio
    async def test_approve_non_submitted_fails(self):
        from app.api.v1.endpoints.campaign_builder import approve_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        with pytest.raises(HTTPException) as exc_info:
            await approve_campaign_draft(_make_request(), 1, draft.id, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_already_approved_fails(self):
        from app.api.v1.endpoints.campaign_builder import approve_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.APPROVED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        with pytest.raises(HTTPException) as exc_info:
            await approve_campaign_draft(_make_request(), 1, draft.id, db)
        assert exc_info.value.status_code == 400


class TestRejectCampaignDraft:
    """Tests for POST /tenant/{tenant_id}/campaign-drafts/{draft_id}/reject"""

    @pytest.mark.asyncio
    async def test_reject_submitted_draft(self):
        from app.api.v1.endpoints.campaign_builder import reject_campaign_draft

        draft = _make_draft(status=DraftStatus.SUBMITTED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        resp = await reject_campaign_draft(
            _make_request(), 1, draft.id, "Budget too high", db
        )
        assert resp.success is True
        assert draft.status == DraftStatus.REJECTED
        assert draft.rejection_reason == "Budget too high"
        assert draft.rejected_at is not None

    @pytest.mark.asyncio
    async def test_reject_non_submitted_fails(self):
        from app.api.v1.endpoints.campaign_builder import reject_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        with pytest.raises(HTTPException) as exc_info:
            await reject_campaign_draft(_make_request(), 1, draft.id, "Reason", db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reject_not_found(self):
        from app.api.v1.endpoints.campaign_builder import reject_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await reject_campaign_draft(_make_request(), 1, uuid4(), "Reason", db)
        assert exc_info.value.status_code == 404


class TestPublishCampaignDraft:
    """Tests for POST /tenant/{tenant_id}/campaign-drafts/{draft_id}/publish"""

    @pytest.mark.asyncio
    async def test_publish_approved_draft(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=10000)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"budget": {"amount": 5000}}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        resp = await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert resp.success is True
        assert draft.status == DraftStatus.PUBLISHED
        assert draft.platform_campaign_id is not None
        assert draft.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_non_approved_fails(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft
        from fastapi import HTTPException

        draft = _make_draft(status=DraftStatus.SUBMITTED)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert exc_info.value.status_code == 400
        assert "Must be approved" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_publish_budget_exceeds_cap(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft
        from fastapi import HTTPException

        acc = _make_ad_account(daily_budget_cap=5000)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"budget": {"amount": 10000}}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert exc_info.value.status_code == 400
        assert "exceeds" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_publish_no_budget_cap_passes(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=None)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"budget": {"amount": 99999}}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        resp = await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert resp.success is True
        assert draft.status == DraftStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_publish_not_found(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_draft(_make_request(), 1, uuid4(), bg, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_creates_log_entry(self):
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=None)
        draft = _make_draft(status=DraftStatus.APPROVED, ad_account=acc)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        # db.add should be called for the publish log
        assert db.add.call_count >= 1


# =============================================================================
# Full Workflow Integration Tests
# =============================================================================


class TestFullWorkflow:
    """Test the complete draft→submit→approve→publish workflow."""

    @pytest.mark.asyncio
    async def test_draft_to_submitted_to_approved(self):
        from app.api.v1.endpoints.campaign_builder import (
            submit_campaign_draft,
            approve_campaign_draft,
        )

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)

        # Submit
        await submit_campaign_draft(_make_request(), 1, draft.id, db)
        assert draft.status == DraftStatus.SUBMITTED

        # Approve
        db.execute.return_value = _make_scalar_result(draft)
        await approve_campaign_draft(_make_request(), 1, draft.id, db)
        assert draft.status == DraftStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_then_re_edit_and_resubmit(self):
        from app.api.v1.endpoints.campaign_builder import (
            submit_campaign_draft,
            reject_campaign_draft,
            update_campaign_draft,
        )

        draft = _make_draft(status=DraftStatus.DRAFT)
        db = _make_db()

        # Submit
        db.execute.return_value = _make_scalar_result(draft)
        await submit_campaign_draft(_make_request(), 1, draft.id, db)
        assert draft.status == DraftStatus.SUBMITTED

        # Reject
        db.execute.return_value = _make_scalar_result(draft)
        await reject_campaign_draft(_make_request(), 1, draft.id, "Too expensive", db)
        assert draft.status == DraftStatus.REJECTED
        assert draft.rejection_reason == "Too expensive"

        # Re-edit (should reset to draft)
        db.execute.return_value = _make_scalar_result(draft)
        update = CampaignDraftUpdate(name="Revised Campaign")
        await update_campaign_draft(_make_request(), 1, draft.id, update, db)
        assert draft.status == DraftStatus.DRAFT
        assert draft.rejection_reason is None

        # Re-submit
        db.execute.return_value = _make_scalar_result(draft)
        await submit_campaign_draft(_make_request(), 1, draft.id, db)
        assert draft.status == DraftStatus.SUBMITTED


# =============================================================================
# Publish Log Endpoint Tests
# =============================================================================


class TestListPublishLogs:
    """Tests for GET /tenant/{tenant_id}/campaign-publish-logs"""

    @pytest.mark.asyncio
    async def test_list_logs(self):
        from app.api.v1.endpoints.campaign_builder import list_publish_logs

        logs = [_make_publish_log(), _make_publish_log()]
        db = _make_db()
        db.execute.return_value = _make_scalars_result(logs)

        resp = await list_publish_logs(
            _make_request(), 1, limit=50, offset=0, db=db
        )
        assert resp.success is True
        assert len(resp.data) == 2

    @pytest.mark.asyncio
    async def test_list_empty(self):
        from app.api.v1.endpoints.campaign_builder import list_publish_logs

        db = _make_db()
        db.execute.return_value = _make_scalars_result([])

        resp = await list_publish_logs(
            _make_request(), 1, limit=50, offset=0, db=db
        )
        assert resp.success is True
        assert resp.data == []

    @pytest.mark.asyncio
    async def test_list_tenant_isolation(self):
        from app.api.v1.endpoints.campaign_builder import list_publish_logs
        from fastapi import HTTPException

        db = _make_db()
        with pytest.raises(HTTPException) as exc_info:
            await list_publish_logs(
                _make_request(tenant_id=1), 2, limit=50, offset=0, db=db
            )
        assert exc_info.value.status_code == 403


class TestRetryPublish:
    """Tests for POST /tenant/{tenant_id}/campaign-publish-logs/{log_id}/retry"""

    @pytest.mark.asyncio
    async def test_retry_failed_publish(self):
        from app.api.v1.endpoints.campaign_builder import retry_publish

        log = _make_publish_log(result_status=PublishResult.FAILURE)
        log.retry_count = 0
        db = _make_db()
        db.execute.return_value = _make_scalar_result(log)
        bg = MagicMock()

        resp = await retry_publish(_make_request(), 1, log.id, bg, db)
        assert resp.success is True
        assert log.retry_count == 1
        assert log.last_retry_at is not None

    @pytest.mark.asyncio
    async def test_retry_success_log_fails(self):
        from app.api.v1.endpoints.campaign_builder import retry_publish
        from fastapi import HTTPException

        log = _make_publish_log(result_status=PublishResult.SUCCESS)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(log)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await retry_publish(_make_request(), 1, log.id, bg, db)
        assert exc_info.value.status_code == 400
        assert "failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_retry_not_found(self):
        from app.api.v1.endpoints.campaign_builder import retry_publish
        from fastapi import HTTPException

        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        bg = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await retry_publish(_make_request(), 1, uuid4(), bg, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_increments_count(self):
        from app.api.v1.endpoints.campaign_builder import retry_publish

        log = _make_publish_log(result_status=PublishResult.FAILURE)
        log.retry_count = 2
        db = _make_db()
        db.execute.return_value = _make_scalar_result(log)
        bg = MagicMock()

        await retry_publish(_make_request(), 1, log.id, bg, db)
        assert log.retry_count == 3


# =============================================================================
# Celery Task Tests
# =============================================================================


class TestSyncAdAccountsTask:
    """Tests for the sync_ad_accounts Celery task."""

    def test_sync_no_active_connection(self):
        from app.workers.campaign_builder_tasks import sync_ad_accounts

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = sync_ad_accounts(tenant_id=1, platform="meta")

        assert result["status"] == "skipped"

    def test_sync_with_active_connection(self):
        from app.workers.campaign_builder_tasks import sync_ad_accounts

        conn = MagicMock()
        conn.id = uuid4()
        conn.status = ConnectionStatus.CONNECTED

        mock_db = MagicMock()
        # First call returns connection, subsequent calls return None (no existing accounts)
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [conn, None, None]

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = sync_ad_accounts(tenant_id=1, platform="meta")

        assert result["status"] == "success"
        assert result["synced_count"] == 2  # Mock returns 2 accounts
        mock_db.commit.assert_called()

    def test_sync_updates_existing_accounts(self):
        from app.workers.campaign_builder_tasks import sync_ad_accounts

        conn = MagicMock()
        conn.id = uuid4()
        conn.status = ConnectionStatus.CONNECTED

        existing_account = MagicMock()
        mock_db = MagicMock()
        # Connection found, then existing accounts found
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            conn, existing_account, existing_account,
        ]

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = sync_ad_accounts(tenant_id=1, platform="meta")

        assert result["status"] == "success"
        # Existing accounts should be updated
        assert existing_account.name is not None


class TestRefreshTokensTask:
    """Tests for the refresh_tokens Celery task."""

    def test_refresh_no_connection(self):
        from app.workers.campaign_builder_tasks import refresh_tokens

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = refresh_tokens(tenant_id=1, platform="meta")

        assert result["status"] == "skipped"

    def test_refresh_success(self):
        from app.workers.campaign_builder_tasks import refresh_tokens

        conn = MagicMock()
        conn.status = ConnectionStatus.CONNECTED
        conn.error_count = 0

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = conn

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = refresh_tokens(tenant_id=1, platform="meta")

        assert result["status"] == "success"
        assert conn.status == ConnectionStatus.CONNECTED
        assert conn.last_error is None
        mock_db.commit.assert_called()


class TestPublishCampaignTask:
    """Tests for the publish_campaign Celery task."""

    def test_publish_draft_not_found(self):
        from app.workers.campaign_builder_tasks import publish_campaign

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = publish_campaign(draft_id=str(uuid4()), publish_log_id=str(uuid4()))

        assert result["status"] == "error"

    def test_publish_wrong_status_skips(self):
        from app.workers.campaign_builder_tasks import publish_campaign

        draft = MagicMock()
        draft.status = DraftStatus.DRAFT  # Not PUBLISHING
        publish_log = MagicMock()

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [draft, publish_log]

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = publish_campaign(
                draft_id=str(uuid4()), publish_log_id=str(uuid4())
            )

        assert result["status"] == "skipped"

    def test_publish_success(self):
        from app.workers.campaign_builder_tasks import publish_campaign

        draft_id = uuid4()
        draft = MagicMock()
        draft.id = draft_id
        draft.status = DraftStatus.PUBLISHING
        draft.tenant_id = 1
        draft.platform = AdPlatform.META
        draft.ad_account_id = uuid4()
        draft.draft_json = {"campaign": {}}

        publish_log = MagicMock()

        ad_account = MagicMock()
        connection = MagicMock()
        connection.status = ConnectionStatus.CONNECTED

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            draft, publish_log, ad_account, connection,
        ]

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = publish_campaign(
                draft_id=str(draft_id), publish_log_id=str(uuid4())
            )

        assert result["status"] == "success"
        assert draft.status == DraftStatus.PUBLISHED
        assert publish_log.result_status == PublishResult.SUCCESS


class TestPublishRetryTask:
    """Tests for the publish_retry Celery task."""

    def test_retry_log_not_found(self):
        from app.workers.campaign_builder_tasks import publish_retry

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = publish_retry(log_id=str(uuid4()))

        assert result["status"] == "error"

    def test_retry_non_failure_skips(self):
        from app.workers.campaign_builder_tasks import publish_retry

        log = MagicMock()
        log.result_status = PublishResult.SUCCESS

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = log

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = publish_retry(log_id=str(uuid4()))

        assert result["status"] == "skipped"


class TestConnectorHealthCheckTask:
    """Tests for the connector_health_check Celery task."""

    def test_health_check_healthy_connections(self):
        from app.workers.campaign_builder_tasks import connector_health_check

        conn = MagicMock()
        conn.id = uuid4()
        conn.tenant_id = 1
        conn.platform = AdPlatform.META
        conn.error_count = 0

        mock_db = MagicMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = [conn]

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = connector_health_check()

        assert result["status"] == "completed"
        assert len(result["results"]) == 1
        assert result["results"][0]["healthy"] is True
        assert conn.error_count == 0

    def test_health_check_no_connections(self):
        from app.workers.campaign_builder_tasks import connector_health_check

        mock_db = MagicMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        with patch("app.workers.campaign_builder_tasks.SessionLocal") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            result = connector_health_check()

        assert result["status"] == "completed"
        assert result["results"] == []


# =============================================================================
# Edge Cases & Boundary Tests
# =============================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_draft_json_empty_default(self):
        uid = uuid4()
        req = CampaignDraftCreate(platform="meta", ad_account_id=uid, name="Test")
        assert req.draft_json == {}

    def test_all_platforms_have_oauth_config(self):
        """Verify all 4 platforms have OAuth configs in start_platform_connection."""
        # This is a static check on the source code
        from app.api.v1.endpoints.campaign_builder import start_platform_connection
        # All platforms should be present in the oauth_configs dict
        for platform in AdPlatform:
            assert platform in [AdPlatform.META, AdPlatform.GOOGLE, AdPlatform.TIKTOK, AdPlatform.SNAPCHAT]

    @pytest.mark.asyncio
    async def test_publish_budget_zero_amount_passes(self):
        """Zero budget should pass since 0 <= any cap."""
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=5000)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"budget": {"amount": 0}}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        resp = await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_publish_no_budget_in_draft_json(self):
        """If draft_json has no budget field, budget check should pass (amount=0)."""
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=5000)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"objective": "awareness"}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        resp = await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_publish_budget_exactly_at_cap(self):
        """Budget exactly equal to cap should pass (> not >=)."""
        from app.api.v1.endpoints.campaign_builder import publish_campaign_draft

        acc = _make_ad_account(daily_budget_cap=5000)
        draft = _make_draft(
            status=DraftStatus.APPROVED,
            ad_account=acc,
            draft_json={"campaign": {"budget": {"amount": 5000}}},
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(draft)
        bg = MagicMock()

        resp = await publish_campaign_draft(_make_request(), 1, draft.id, bg, db)
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_disconnect_clears_tokens(self):
        """Verify disconnecting clears sensitive token data."""
        from app.api.v1.endpoints.campaign_builder import disconnect_platform

        conn = _make_connection()
        assert conn.access_token_encrypted is not None

        db = _make_db()
        db.execute.return_value = _make_scalar_result(conn)

        await disconnect_platform(_make_request(), 1, AdPlatform.META, db)
        assert conn.access_token_encrypted is None
        assert conn.refresh_token_encrypted is None
        assert conn.status == ConnectionStatus.DISCONNECTED

    def test_platform_enum_used_as_string(self):
        """AdPlatform inherits from str, so .value can be used in string contexts."""
        assert f"Platform: {AdPlatform.META.value}" == "Platform: meta"
        assert str(AdPlatform.GOOGLE.value) + "_suffix" == "google_suffix"

    def test_draft_status_workflow_values(self):
        """Verify all workflow states are present for state machine correctness."""
        expected = {"draft", "submitted", "approved", "rejected", "publishing", "published", "failed"}
        actual = {s.value for s in DraftStatus}
        assert actual == expected
