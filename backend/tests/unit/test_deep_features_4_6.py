# =============================================================================
# Stratum AI - Deep Endpoint Tests: Features 4-6
# =============================================================================
"""
Deep endpoint tests for:
  Feature 4 - Campaign Builder  (prefix /api/v1/campaign-builder/tenant/{tenant_id}/...)
  Feature 5 - Audience Sync     (prefix /api/v1/cdp/audience-sync/...)
  Feature 6 - Authentication    (prefix /api/v1/auth/... and /api/v1/mfa/...)

Each test goes through the full ASGI request/response cycle
(middleware -> route -> handler -> response) via httpx.AsyncClient,
while mocking services and DB at the handler level.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Re-usable helpers from conftest
from tests.unit.conftest import make_auth_headers, make_scalar_result, make_scalars_result

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CAMPAIGN_BUILDER_PREFIX = "/api/v1/campaign-builder/tenant"
AUDIENCE_SYNC_PREFIX = "/api/v1/cdp/audience-sync"
AUTH_PREFIX = "/api/v1/auth"
MFA_PREFIX = "/api/v1/mfa"

FAKE_UUID = "00000000-0000-0000-0000-000000000001"
FAKE_UUID2 = "00000000-0000-0000-0000-000000000002"

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers for building mock ORM objects
# ---------------------------------------------------------------------------

def _mock_connection(*, platform="meta", status="connected", tenant_id=1):
    """Build a mock TenantPlatformConnection row."""
    conn = MagicMock()
    conn.platform = MagicMock(value=platform)
    conn.status = MagicMock(value=status)
    conn.connected_at = NOW
    conn.last_refreshed_at = NOW
    conn.scopes = ["ads_read", "ads_management"]
    conn.last_error = None
    conn.refresh_token_encrypted = "encrypted_refresh_token"
    conn.access_token_encrypted = "encrypted_access_token"
    conn.tenant_id = tenant_id
    return conn


def _mock_ad_account(*, platform="meta", is_enabled=True, tenant_id=1):
    """Build a mock TenantAdAccount row."""
    acc = MagicMock()
    acc.id = uuid.UUID(FAKE_UUID)
    acc.tenant_id = tenant_id
    acc.platform = platform
    acc.platform_account_id = "act_123456"
    acc.name = "Test Ad Account"
    acc.business_name = "Test Business"
    acc.currency = "USD"
    acc.timezone = "America/New_York"
    acc.is_enabled = is_enabled
    acc.daily_budget_cap = 500.0
    acc.last_synced_at = NOW
    return acc


def _mock_campaign_draft(*, status="draft", tenant_id=1):
    """Build a mock CampaignDraft row."""
    from app.models.campaign_builder import DraftStatus
    draft = MagicMock()
    draft.id = uuid.UUID(FAKE_UUID)
    draft.tenant_id = tenant_id
    draft.platform = MagicMock(value="meta")
    draft.ad_account_id = uuid.UUID(FAKE_UUID)
    draft.name = "Test Campaign"
    draft.description = "Test description"
    draft.status = DraftStatus(status)
    draft.draft_json = {"campaign": {"name": "Test"}}
    draft.created_at = NOW
    draft.updated_at = NOW
    draft.submitted_at = None
    draft.approved_at = None
    draft.rejected_at = None
    draft.rejection_reason = None
    draft.platform_campaign_id = None
    draft.published_at = None
    draft.ad_account = _mock_ad_account()
    return draft


def _mock_publish_log(*, result_status="failure"):
    """Build a mock CampaignPublishLog row."""
    from app.models.campaign_builder import PublishResult
    log = MagicMock()
    log.id = uuid.UUID(FAKE_UUID2)
    log.draft_id = uuid.UUID(FAKE_UUID)
    log.tenant_id = 1
    log.platform = MagicMock(value="meta")
    log.platform_account_id = "act_123456"
    log.event_time = NOW
    log.result_status = PublishResult(result_status)
    log.platform_campaign_id = None
    log.error_code = "API_ERROR"
    log.error_message = "Something went wrong"
    log.retry_count = 0
    log.last_retry_at = None
    return log


def _mock_user(*, user_id=1, tenant_id=1, role_value="admin"):
    """Build a mock User ORM object for auth dependency overrides."""
    user = MagicMock()
    user.id = user_id
    user.tenant_id = tenant_id
    user.role = MagicMock(value=role_value)
    user.cms_role = "admin"
    user.is_active = True
    user.is_deleted = False
    user.is_verified = True
    user.email = "encrypted_email"
    user.email_hash = "abc123hash"
    user.full_name = None
    user.permissions = {}
    user.password_hash = "hashed_pw"
    user.last_login_at = NOW
    user.avatar_url = None
    user.locale = "en"
    user.timezone = "UTC"
    user.created_at = NOW
    user.updated_at = NOW
    return user


# ============================================================================
# FEATURE 4: CAMPAIGN BUILDER
# ============================================================================

class TestCampaignBuilderConnectors:
    """Tests for campaign builder connector (OAuth) endpoints."""

    # ---- No auth -> 401 ----

    @pytest.mark.asyncio
    async def test_get_connector_status_no_auth(self, api_client):
        """GET connector status without JWT returns 401."""
        r = await api_client.get(f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta/status")
        assert r.status_code == 401

    # ---- Wrong tenant -> 403 ----

    @pytest.mark.asyncio
    async def test_get_connector_status_wrong_tenant(self, api_client, tenant2_headers):
        """GET connector status for tenant 1 with tenant-2 token returns 403."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta/status",
            headers=tenant2_headers,
        )
        assert r.status_code == 403

    # ---- Happy path: status (no connection) ----

    @pytest.mark.asyncio
    async def test_get_connector_status_disconnected(self, api_client, admin_headers, mock_db):
        """GET connector status returns disconnected when no connection exists."""
        # Default mock_db.execute returns None for scalar_one_or_none
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta/status",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["status"] == "disconnected"
        assert body["data"]["platform"] == "meta"

    # ---- Happy path: status (connected) ----

    @pytest.mark.asyncio
    async def test_get_connector_status_connected(self, api_client, admin_headers, mock_db):
        """GET connector status returns connection details when connected."""
        conn = _mock_connection()
        mock_db.execute.return_value = make_scalar_result(conn)
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta/status",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["status"] == "connected"

    # ---- Disconnect: not found ----

    @pytest.mark.asyncio
    async def test_disconnect_platform_not_found(self, api_client, admin_headers, mock_db):
        """DELETE disconnect returns 404 when platform is not connected."""
        r = await api_client.delete(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta",
            headers=admin_headers,
        )
        assert r.status_code == 404

    # ---- Disconnect: happy path ----

    @pytest.mark.asyncio
    async def test_disconnect_platform_success(self, api_client, admin_headers, mock_db):
        """DELETE disconnect succeeds when connection exists."""
        conn = _mock_connection()
        mock_db.execute.return_value = make_scalar_result(conn)
        r = await api_client.delete(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/meta",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    # ---- Invalid platform -> 422 ----

    @pytest.mark.asyncio
    async def test_get_connector_status_invalid_platform(self, api_client, admin_headers):
        """GET connector status with invalid platform returns 422."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/connect/invalid_platform/status",
            headers=admin_headers,
        )
        assert r.status_code == 422


class TestCampaignBuilderAdAccounts:
    """Tests for ad account endpoints."""

    @pytest.mark.asyncio
    async def test_list_ad_accounts_no_auth(self, api_client):
        """GET ad accounts without JWT returns 401."""
        r = await api_client.get(f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_ad_accounts_wrong_tenant(self, api_client, tenant2_headers):
        """GET ad accounts for tenant 1 with tenant-2 token returns 403."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta",
            headers=tenant2_headers,
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_list_ad_accounts_empty(self, api_client, admin_headers, mock_db):
        """GET ad accounts returns empty list when none exist."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"] == []

    @pytest.mark.asyncio
    async def test_sync_ad_accounts_not_connected(self, api_client, admin_headers, mock_db):
        """POST sync returns 400 when platform not connected."""
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta/sync",
            headers=admin_headers,
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_ad_accounts_connected(self, api_client, admin_headers, mock_db):
        """POST sync returns 200 when platform is connected."""
        conn = _mock_connection()
        mock_db.execute.return_value = make_scalar_result(conn)
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta/sync",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert "Sync started" in r.json()["data"]["message"]

    @pytest.mark.asyncio
    async def test_update_ad_account_not_found(self, api_client, admin_headers, mock_db):
        """PUT update returns 404 when ad account not found."""
        r = await api_client.put(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/ad-accounts/meta/{FAKE_UUID}",
            headers=admin_headers,
            json={"is_enabled": False},
        )
        assert r.status_code == 404


class TestCampaignBuilderDrafts:
    """Tests for campaign draft CRUD and workflow endpoints."""

    @pytest.mark.asyncio
    async def test_list_drafts_no_auth(self, api_client):
        """GET campaign drafts without JWT returns 401."""
        r = await api_client.get(f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_drafts_wrong_tenant(self, api_client, tenant2_headers):
        """GET campaign drafts for tenant 1 with tenant-2 token returns 403."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts",
            headers=tenant2_headers,
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_list_drafts_empty(self, api_client, admin_headers, mock_db):
        """GET campaign drafts returns empty list when none exist."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["data"] == []

    @pytest.mark.asyncio
    async def test_create_draft_ad_account_not_found(self, api_client, admin_headers, mock_db):
        """POST create draft returns 400 when ad account not found/enabled."""
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts",
            headers=admin_headers,
            json={
                "platform": "meta",
                "ad_account_id": FAKE_UUID,
                "name": "My Campaign",
                "draft_json": {},
            },
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_create_draft_validation_error(self, api_client, admin_headers):
        """POST create draft with missing fields returns 422."""
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts",
            headers=admin_headers,
            json={"platform": "meta"},  # Missing required fields
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self, api_client, admin_headers, mock_db):
        """GET single draft returns 404 when not found."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts/{FAKE_UUID}",
            headers=admin_headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_draft_not_found(self, api_client, admin_headers, mock_db):
        """POST submit draft returns 404 when draft not found."""
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts/{FAKE_UUID}/submit",
            headers=admin_headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_draft_wrong_status(self, api_client, admin_headers, mock_db):
        """POST submit draft returns 400 when draft is already submitted."""
        draft = _mock_campaign_draft(status="submitted")
        mock_db.execute.return_value = make_scalar_result(draft)
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts/{FAKE_UUID}/submit",
            headers=admin_headers,
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_draft_not_submitted(self, api_client, admin_headers, mock_db):
        """POST approve draft returns 400 when draft is not in submitted status."""
        draft = _mock_campaign_draft(status="draft")
        mock_db.execute.return_value = make_scalar_result(draft)
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts/{FAKE_UUID}/approve",
            headers=admin_headers,
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_reject_draft_requires_reason(self, api_client, admin_headers, mock_db):
        """POST reject draft requires a reason query parameter."""
        draft = _mock_campaign_draft(status="submitted")
        mock_db.execute.return_value = make_scalar_result(draft)
        # No reason query param -> 422
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-drafts/{FAKE_UUID}/reject",
            headers=admin_headers,
        )
        assert r.status_code == 422


class TestCampaignBuilderPublishLogs:
    """Tests for publish log endpoints."""

    @pytest.mark.asyncio
    async def test_list_publish_logs_no_auth(self, api_client):
        """GET publish logs without JWT returns 401."""
        r = await api_client.get(f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-publish-logs")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_publish_logs_empty(self, api_client, admin_headers, mock_db):
        """GET publish logs returns empty list when none exist."""
        r = await api_client.get(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-publish-logs",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["data"] == []

    @pytest.mark.asyncio
    async def test_retry_publish_not_found(self, api_client, admin_headers, mock_db):
        """POST retry publish returns 404 when log not found."""
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-publish-logs/{FAKE_UUID2}/retry",
            headers=admin_headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_publish_not_failed(self, api_client, admin_headers, mock_db):
        """POST retry publish returns 400 when log is not in failure status."""
        log = _mock_publish_log(result_status="success")
        mock_db.execute.return_value = make_scalar_result(log)
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-publish-logs/{FAKE_UUID2}/retry",
            headers=admin_headers,
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_publish_success(self, api_client, admin_headers, mock_db):
        """POST retry publish succeeds when log is in failure status."""
        log = _mock_publish_log(result_status="failure")
        mock_db.execute.return_value = make_scalar_result(log)
        r = await api_client.post(
            f"{CAMPAIGN_BUILDER_PREFIX}/1/campaign-publish-logs/{FAKE_UUID2}/retry",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


# ============================================================================
# FEATURE 5: AUDIENCE SYNC
# ============================================================================

class TestAudienceSyncPlatforms:
    """Tests for audience sync platform listing."""

    @pytest.mark.asyncio
    async def test_get_platforms_no_auth(self, api_client):
        """GET connected platforms without JWT returns 401."""
        r = await api_client.get(f"{AUDIENCE_SYNC_PREFIX}/platforms")
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_get_platforms_happy_path(
        self, MockService, api_client, admin_headers, mock_db
    ):
        """GET connected platforms returns list from service."""
        mock_svc = MagicMock()
        mock_svc.get_connected_platforms = AsyncMock(return_value=[
            {"platform": "meta", "ad_accounts": [{"id": "act_1", "name": "Main"}]},
        ])
        MockService.return_value = mock_svc

        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/platforms",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["platform"] == "meta"


class TestAudienceSyncAudiences:
    """Tests for audience CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_audiences_no_auth(self, api_client):
        """GET audiences without JWT returns 401."""
        r = await api_client.get(f"{AUDIENCE_SYNC_PREFIX}/audiences")
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_list_audiences_happy_path(
        self, MockService, api_client, admin_headers, mock_db
    ):
        """GET audiences returns list from service."""
        mock_svc = MagicMock()
        mock_svc.list_platform_audiences = AsyncMock(return_value=([], 0))
        MockService.return_value = mock_svc

        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/audiences",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["audiences"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_create_audience_invalid_platform(
        self, MockService, api_client, admin_headers, mock_db, test_app
    ):
        """POST create audience with invalid platform returns 400."""
        # Override get_current_user from auth.deps to avoid DB lookup
        from app.auth.deps import get_current_user as auth_get_current_user

        mock_user = _mock_user()
        from app.auth.deps import CurrentUser
        cu = MagicMock(spec=CurrentUser)
        cu.id = 1
        cu.user = mock_user
        cu.role = mock_user.role
        cu.is_active = True

        test_app.dependency_overrides[auth_get_current_user] = lambda: cu

        r = await api_client.post(
            f"{AUDIENCE_SYNC_PREFIX}/audiences",
            headers=admin_headers,
            json={
                "segment_id": FAKE_UUID,
                "platform": "nonexistent_platform",
                "ad_account_id": "act_123",
                "audience_name": "Test Audience",
            },
        )
        assert r.status_code == 400

        # Cleanup override
        test_app.dependency_overrides.pop(auth_get_current_user, None)

    @pytest.mark.asyncio
    @patch("app.auth.deps.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    async def test_create_audience_validation_error(
        self, _mock_bl, api_client, admin_headers, mock_db
    ):
        """POST create audience with missing fields returns 422."""
        # The create endpoint depends on get_current_user (auth.deps) which
        # calls is_token_blacklisted -> Redis.  We mock it out and also
        # make the DB return a mock user so get_current_user succeeds,
        # letting FastAPI reach the request-body validation stage.
        user = _mock_user()
        mock_db.execute.return_value = make_scalar_result(user)

        r = await api_client.post(
            f"{AUDIENCE_SYNC_PREFIX}/audiences",
            headers=admin_headers,
            json={"platform": "meta"},  # Missing required fields
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_get_audience_not_found(
        self, MockService, api_client, admin_headers, mock_db
    ):
        """GET single audience returns 404 when not found."""
        mock_svc = MagicMock()
        mock_svc.list_platform_audiences = AsyncMock(return_value=([], 0))
        MockService.return_value = mock_svc

        # The endpoint also does a direct DB query that returns None
        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/audiences/{FAKE_UUID}",
            headers=admin_headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_get_sync_history_happy_path(
        self, MockService, api_client, admin_headers, mock_db
    ):
        """GET sync history returns empty jobs list."""
        mock_svc = MagicMock()
        mock_svc.get_sync_history = AsyncMock(return_value=[])
        MockService.return_value = mock_svc

        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/audiences/{FAKE_UUID}/history",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["jobs"] == []

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_delete_audience_not_found(
        self, MockService, api_client, admin_headers, mock_db, test_app
    ):
        """DELETE audience returns 404 when not found."""
        from app.auth.deps import get_current_user as auth_get_current_user

        mock_user = _mock_user()
        from app.auth.deps import CurrentUser
        cu = MagicMock(spec=CurrentUser)
        cu.id = 1
        cu.user = mock_user
        cu.role = mock_user.role
        cu.is_active = True

        test_app.dependency_overrides[auth_get_current_user] = lambda: cu

        mock_svc = MagicMock()
        mock_svc.delete_platform_audience = AsyncMock(return_value=False)
        MockService.return_value = mock_svc

        r = await api_client.delete(
            f"{AUDIENCE_SYNC_PREFIX}/audiences/{FAKE_UUID}",
            headers=admin_headers,
        )
        assert r.status_code == 404

        test_app.dependency_overrides.pop(auth_get_current_user, None)


class TestAudienceSyncSegments:
    """Tests for segment convenience endpoints."""

    @pytest.mark.asyncio
    async def test_get_segment_audiences_no_auth(self, api_client):
        """GET segment audiences without JWT returns 401."""
        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/segments/{FAKE_UUID}/audiences"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.audience_sync.AudienceSyncService")
    async def test_get_segment_audiences_empty(
        self, MockService, api_client, admin_headers, mock_db
    ):
        """GET segment audiences returns empty when no audiences linked."""
        mock_svc = MagicMock()
        mock_svc.list_platform_audiences = AsyncMock(return_value=([], 0))
        MockService.return_value = mock_svc

        r = await api_client.get(
            f"{AUDIENCE_SYNC_PREFIX}/segments/{FAKE_UUID}/audiences",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["audiences"] == []
        assert body["total"] == 0


# ============================================================================
# FEATURE 6: AUTHENTICATION
# ============================================================================

class TestAuthLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.check_login_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.auth.record_failed_login", new_callable=AsyncMock)
    async def test_login_invalid_credentials(
        self, mock_record, mock_rate_limit, api_client, mock_db
    ):
        """POST /login with bad credentials returns 401."""
        mock_rate_limit.return_value = (True, 0)  # Not rate-limited
        mock_record.return_value = 1

        r = await api_client.post(
            f"{AUTH_PREFIX}/login",
            json={"email": "wrong@example.com", "password": "WrongPass1"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.check_login_rate_limit", new_callable=AsyncMock)
    async def test_login_rate_limited(self, mock_rate_limit, api_client, mock_db):
        """POST /login when rate-limited returns 429."""
        mock_rate_limit.return_value = (False, 300)  # Locked for 300s

        r = await api_client.post(
            f"{AUTH_PREFIX}/login",
            json={"email": "user@example.com", "password": "TestPass1"},
        )
        assert r.status_code == 429

    @pytest.mark.asyncio
    async def test_login_validation_error(self, api_client):
        """POST /login with invalid email returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/login",
            json={"email": "not-an-email", "password": "short"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.check_login_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.auth.clear_login_attempts", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.auth.verify_password")
    @patch("app.api.v1.endpoints.auth.hash_pii_for_lookup")
    async def test_login_success(
        self,
        mock_hash,
        mock_verify,
        mock_clear,
        mock_rate_limit,
        api_client,
        mock_db,
    ):
        """POST /login with valid credentials returns tokens."""
        mock_rate_limit.return_value = (True, 0)
        mock_hash.return_value = "hashed_email"
        mock_verify.return_value = True

        user = _mock_user()
        user.password_hash = "hashed_pw"

        # First execute: find user by email_hash -> returns user list
        # Second execute: audit log commit -> doesn't matter
        # Third execute: membership lookup -> return empty
        call_count = 0
        results = []

        # Result for user lookup (scalars().all())
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [user]
        results.append(user_result)

        # Result for membership lookup (.all())
        membership_result = MagicMock()
        membership_result.all.return_value = []
        results.append(membership_result)

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            idx = min(call_count, len(results) - 1)
            call_count += 1
            return results[idx]

        mock_db.execute = AsyncMock(side_effect=side_effect)

        r = await api_client.post(
            f"{AUTH_PREFIX}/login",
            json={"email": "user@example.com", "password": "ValidPass1"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]


class TestAuthRegister:
    """Tests for registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_validation_error_weak_password(self, api_client):
        """POST /register with weak password returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/register",
            json={
                "email": "new@example.com",
                "password": "alllower1",  # No uppercase
                "tenant_id": 1,
            },
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_register_validation_error_short_password(self, api_client):
        """POST /register with short password returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/register",
            json={
                "email": "new@example.com",
                "password": "Ab1",
                "tenant_id": 1,
            },
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_tenant(self, api_client, mock_db):
        """POST /register with non-existent tenant returns 400."""
        # mock_db.execute returns None for scalar_one_or_none by default
        r = await api_client.post(
            f"{AUTH_PREFIX}/register",
            json={
                "email": "new@example.com",
                "password": "ValidPass1",
                "tenant_id": 9999,
            },
        )
        assert r.status_code == 400
        assert "Invalid tenant" in r.json()["detail"]


class TestAuthRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, api_client):
        """POST /refresh with invalid token returns 401."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/refresh",
            json={"refresh_token": "invalid_token_string"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_validation_error(self, api_client):
        """POST /refresh with missing token returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/refresh",
            json={},
        )
        assert r.status_code == 422


class TestAuthLogout:
    """Tests for logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_no_auth(self, api_client):
        """POST /logout without token still returns 200 (graceful)."""
        # Logout is on a non-public path, so middleware will reject with 401
        r = await api_client.post(f"{AUTH_PREFIX}/logout")
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.blacklist_token", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.auth.decode_token")
    async def test_logout_with_auth(
        self, mock_decode, mock_blacklist, api_client, admin_headers, mock_db
    ):
        """POST /logout with valid token returns 200."""
        mock_decode.return_value = {"sub": "1", "type": "access", "exp": 9999999999}

        r = await api_client.post(
            f"{AUTH_PREFIX}/logout",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestAuthForgotPassword:
    """Tests for forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_unknown_email(self, api_client, mock_db):
        """POST /forgot-password with unknown email still returns 200 (anti-enumeration)."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/forgot-password",
            json={"email": "unknown@example.com"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_validation_error(self, api_client):
        """POST /forgot-password with missing email returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/forgot-password",
            json={},
        )
        assert r.status_code == 422


class TestAuthPasswordReset:
    """Tests for reset-password endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.get_redis_client", new_callable=AsyncMock)
    async def test_reset_password_invalid_token(self, mock_redis_factory, api_client, mock_db):
        """POST /reset-password with expired/invalid token returns 400."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()
        mock_redis_factory.return_value = mock_redis

        r = await api_client.post(
            f"{AUTH_PREFIX}/reset-password",
            json={"token": "invalid_token", "password": "NewPass1!"},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_validation_error(self, api_client):
        """POST /reset-password with short password returns 422."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/reset-password",
            json={"token": "sometoken", "password": "short"},
        )
        assert r.status_code == 422


class TestAuthTenants:
    """Tests for tenant listing/switching endpoints."""

    @pytest.mark.asyncio
    async def test_list_tenants_no_auth(self, api_client):
        """GET /tenants without JWT returns 401."""
        r = await api_client.get(f"{AUTH_PREFIX}/tenants")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_tenants_with_auth(self, api_client, admin_headers, mock_db):
        """GET /tenants with valid JWT returns 200."""
        # Default mock_db.execute -> empty result.all()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        r = await api_client.get(
            f"{AUTH_PREFIX}/tenants",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_switch_tenant_no_auth(self, api_client):
        """POST /switch-tenant without JWT returns 401."""
        r = await api_client.post(
            f"{AUTH_PREFIX}/switch-tenant",
            json={"tenant_id": 2},
        )
        assert r.status_code == 401


# ============================================================================
# FEATURE 6: MFA ENDPOINTS
# ============================================================================

class TestMFAStatus:
    """Tests for MFA status endpoint."""

    @pytest.mark.asyncio
    async def test_mfa_status_no_auth(self, api_client):
        """GET /mfa/status without JWT returns 401."""
        r = await api_client.get(f"{MFA_PREFIX}/status")
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.mfa.MFAService")
    @patch("app.api.v1.endpoints.mfa.is_token_blacklisted", create=True)
    async def test_mfa_status_with_auth(
        self, _mock_blacklist, MockMFAService, api_client, admin_headers, mock_db, test_app
    ):
        """GET /mfa/status with valid JWT returns MFA status."""
        from app.auth.deps import get_current_user as auth_get_current_user

        mock_user = _mock_user()
        from app.auth.deps import CurrentUser
        cu = MagicMock(spec=CurrentUser)
        cu.id = 1
        cu.user = mock_user
        cu.role = mock_user.role
        cu.is_active = True

        test_app.dependency_overrides[auth_get_current_user] = lambda: cu

        from app.services.mfa_service import MFAStatus
        mock_svc = MagicMock()
        mock_svc.get_mfa_status = AsyncMock(return_value=MFAStatus(
            enabled=False,
            verified_at=None,
            backup_codes_remaining=0,
            is_locked=False,
            lockout_until=None,
        ))
        MockMFAService.return_value = mock_svc

        r = await api_client.get(
            f"{MFA_PREFIX}/status",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["enabled"] is False

        test_app.dependency_overrides.pop(auth_get_current_user, None)


class TestMFASetup:
    """Tests for MFA setup endpoint."""

    @pytest.mark.asyncio
    async def test_mfa_setup_no_auth(self, api_client):
        """POST /mfa/setup without JWT returns 401."""
        r = await api_client.post(f"{MFA_PREFIX}/setup")
        assert r.status_code == 401


class TestMFAVerify:
    """Tests for MFA verify endpoint."""

    @pytest.mark.asyncio
    async def test_mfa_verify_no_auth(self, api_client):
        """POST /mfa/verify without JWT returns 401."""
        r = await api_client.post(
            f"{MFA_PREFIX}/verify",
            json={"code": "123456"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    @patch("app.auth.deps.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    async def test_mfa_verify_validation_error(
        self, _mock_bl, api_client, admin_headers, mock_db
    ):
        """POST /mfa/verify with short code returns 422."""
        # /mfa/verify depends on get_current_user (auth.deps) which calls
        # is_token_blacklisted -> Redis.  Mock it out and provide a user.
        user = _mock_user()
        mock_db.execute.return_value = make_scalar_result(user)

        r = await api_client.post(
            f"{MFA_PREFIX}/verify",
            headers=admin_headers,
            json={"code": "12"},  # Too short
        )
        assert r.status_code == 422


class TestMFADisable:
    """Tests for MFA disable endpoint."""

    @pytest.mark.asyncio
    async def test_mfa_disable_no_auth(self, api_client):
        """POST /mfa/disable without JWT returns 401."""
        r = await api_client.post(
            f"{MFA_PREFIX}/disable",
            json={"code": "123456"},
        )
        assert r.status_code == 401


class TestMFAValidate:
    """Tests for MFA validate (login flow) endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.mfa.is_user_locked", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.mfa.MFAService")
    async def test_mfa_validate_invalid_code(
        self, MockMFAService, mock_locked, api_client, mock_db
    ):
        """POST /mfa/validate with invalid code returns valid=false."""
        mock_locked.return_value = (False, None)
        mock_svc = MagicMock()
        mock_svc.verify_code = AsyncMock(return_value=(False, "Invalid code"))
        MockMFAService.return_value = mock_svc

        # /mfa/validate is a public-ish endpoint (no JWT needed, part of login flow)
        # But TenantMiddleware will block it. We need auth headers.
        r = await api_client.post(
            f"{MFA_PREFIX}/validate",
            headers=make_auth_headers(subject=1, tenant_id=1, role="admin"),
            json={"user_id": 1, "code": "000000"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.mfa.is_user_locked", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.mfa.MFAService")
    async def test_mfa_validate_success(
        self, MockMFAService, mock_locked, api_client, mock_db
    ):
        """POST /mfa/validate with valid code returns valid=true."""
        mock_locked.return_value = (False, None)
        mock_svc = MagicMock()
        mock_svc.verify_code = AsyncMock(return_value=(True, "Code verified"))
        MockMFAService.return_value = mock_svc

        r = await api_client.post(
            f"{MFA_PREFIX}/validate",
            headers=make_auth_headers(subject=1, tenant_id=1, role="admin"),
            json={"user_id": 1, "code": "123456"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True

    @pytest.mark.asyncio
    async def test_mfa_validate_validation_error(self, api_client, admin_headers):
        """POST /mfa/validate with missing fields returns 422."""
        r = await api_client.post(
            f"{MFA_PREFIX}/validate",
            headers=admin_headers,
            json={},
        )
        assert r.status_code == 422


class TestMFACheck:
    """Tests for MFA check (is MFA required) endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.mfa.check_mfa_required", new_callable=AsyncMock)
    async def test_mfa_check_not_required(
        self, mock_check, api_client, admin_headers, mock_db
    ):
        """GET /mfa/check/{user_id} returns mfa_required=false."""
        mock_check.return_value = False

        r = await api_client.get(
            f"{MFA_PREFIX}/check/1",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["mfa_required"] is False

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.mfa.is_user_locked", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.mfa.check_mfa_required", new_callable=AsyncMock)
    async def test_mfa_check_required(
        self, mock_check, mock_locked, api_client, admin_headers, mock_db
    ):
        """GET /mfa/check/{user_id} returns mfa_required=true."""
        mock_check.return_value = True
        mock_locked.return_value = (False, None)

        r = await api_client.get(
            f"{MFA_PREFIX}/check/1",
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["mfa_required"] is True

    @pytest.mark.asyncio
    async def test_mfa_check_invalid_user_id(self, api_client, admin_headers):
        """GET /mfa/check/0 returns 400 for invalid user ID."""
        r = await api_client.get(
            f"{MFA_PREFIX}/check/0",
            headers=admin_headers,
        )
        assert r.status_code == 400
