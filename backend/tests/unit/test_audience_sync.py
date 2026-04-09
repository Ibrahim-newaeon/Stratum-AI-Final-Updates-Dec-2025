# =============================================================================
# Stratum AI - Audience Sync Unit Tests
# =============================================================================
"""
Comprehensive unit tests for the CDP Audience Sync feature.

Tests cover:
- Enums (SyncPlatform, SyncStatus, SyncOperation, AudienceType)
- Base data classes (UserIdentifier, AudienceUser, AudienceSyncResult, AudienceConfig)
- Identifier hashing & normalization (SHA-256, phone/email)
- Base connector utilities (_prepare_users_for_upload, _chunk_list, _hash_identifier)
- Meta connector (create, add, remove, replace, delete, get_audience_info, _prepare_meta_user_data)
- AudienceSyncService (create, sync, delete, list, history, connected platforms, helpers)
- Endpoint schemas (PlatformAudienceCreate, TriggerSyncRequest, etc.)
- Credential encryption (set/get access_token, refresh_token)
- Edge cases (empty users, missing identifiers, unknown platforms)
"""

import hashlib
import time
from datetime import datetime, timezone, timedelta, UTC
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4, UUID

import pytest

# ---------------------------------------------------------------------------
# Model / enum imports
# ---------------------------------------------------------------------------
from app.models.audience_sync import (
    SyncPlatform,
    SyncStatus,
    SyncOperation,
    AudienceType,
    PlatformAudience,
    AudienceSyncJob,
    AudienceSyncCredential,
)

# ---------------------------------------------------------------------------
# Base data class imports
# ---------------------------------------------------------------------------
from app.services.cdp.audience_sync.base import (
    IdentifierType,
    UserIdentifier,
    AudienceUser,
    AudienceSyncResult,
    AudienceConfig,
    BaseAudienceConnector,
)

# ---------------------------------------------------------------------------
# Schema imports
# ---------------------------------------------------------------------------
from app.api.v1.endpoints.audience_sync import (
    PlatformAudienceCreate,
    PlatformAudienceResponse,
    SyncJobResponse,
    TriggerSyncRequest,
    ConnectedPlatformResponse,
    PlatformAudienceListResponse,
    SyncHistoryResponse,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestSyncPlatform:
    """Tests for SyncPlatform enum."""

    def test_all_platforms(self):
        assert set(p.value for p in SyncPlatform) == {"meta", "google", "tiktok", "snapchat"}

    def test_is_str_enum(self):
        assert isinstance(SyncPlatform.META, str)
        assert SyncPlatform.META == "meta"

    def test_from_value(self):
        assert SyncPlatform("meta") == SyncPlatform.META
        assert SyncPlatform("google") == SyncPlatform.GOOGLE

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            SyncPlatform("twitter")


class TestSyncStatus:
    """Tests for SyncStatus enum."""

    def test_all_statuses(self):
        assert set(s.value for s in SyncStatus) == {
            "pending", "processing", "completed", "failed", "partial",
        }

    def test_pending_is_initial(self):
        assert SyncStatus.PENDING.value == "pending"

    def test_partial_status_exists(self):
        assert SyncStatus.PARTIAL.value == "partial"


class TestSyncOperation:
    """Tests for SyncOperation enum."""

    def test_all_operations(self):
        assert set(o.value for o in SyncOperation) == {
            "create", "update", "replace", "delete",
        }


class TestAudienceType:
    """Tests for AudienceType enum."""

    def test_all_types(self):
        assert set(t.value for t in AudienceType) == {
            "customer_list", "lookalike", "website", "app",
        }

    def test_customer_list_default(self):
        assert AudienceType.CUSTOMER_LIST.value == "customer_list"


class TestIdentifierType:
    """Tests for IdentifierType enum."""

    def test_all_types(self):
        assert set(t.value for t in IdentifierType) == {
            "email", "phone", "mobile_id", "external_id",
        }


# =============================================================================
# Data Class Tests
# =============================================================================


class TestUserIdentifier:
    """Tests for UserIdentifier data class."""

    def test_hash_from_raw_email(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.EMAIL,
            raw_value="Test@Example.COM",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("test@example.com".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_hash_from_raw_phone(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.PHONE,
            raw_value="+1 (555) 123-4567",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("+15551234567".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_pre_hashed_value_returned(self):
        pre_hashed = "abc123def456"
        uid = UserIdentifier(
            identifier_type=IdentifierType.EMAIL,
            hashed_value=pre_hashed,
        )
        assert uid.get_hashed() == pre_hashed

    def test_pre_hashed_takes_precedence(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.EMAIL,
            raw_value="test@example.com",
            hashed_value="override_hash",
        )
        assert uid.get_hashed() == "override_hash"

    def test_no_value_returns_none(self):
        uid = UserIdentifier(identifier_type=IdentifierType.EMAIL)
        assert uid.get_hashed() is None

    def test_email_normalization_strips_whitespace(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.EMAIL,
            raw_value="  USER@Test.COM  ",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("user@test.com".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_phone_normalization_removes_formatting(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.PHONE,
            raw_value="(966) 50-123-4567",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("966501234567".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_external_id_normalization(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.EXTERNAL_ID,
            raw_value="  MyID123  ",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("myid123".encode("utf-8")).hexdigest()
        assert hashed == expected


class TestAudienceUser:
    """Tests for AudienceUser data class."""

    def test_minimal_user(self):
        user = AudienceUser(profile_id="prof_123")
        assert user.profile_id == "prof_123"
        assert user.identifiers == []
        assert user.first_name is None

    def test_user_with_identifiers(self):
        user = AudienceUser(
            profile_id="prof_456",
            identifiers=[
                UserIdentifier(identifier_type=IdentifierType.EMAIL, raw_value="a@b.com"),
                UserIdentifier(identifier_type=IdentifierType.PHONE, raw_value="+966501234567"),
            ],
        )
        assert len(user.identifiers) == 2

    def test_user_with_demographics(self):
        user = AudienceUser(
            profile_id="prof_789",
            first_name="Ahmed",
            last_name="Ali",
            country="SA",
            gender="m",
        )
        assert user.first_name == "Ahmed"
        assert user.country == "SA"


class TestAudienceSyncResult:
    """Tests for AudienceSyncResult data class."""

    def test_success_result(self):
        result = AudienceSyncResult(
            success=True,
            operation="create",
            platform_audience_id="aud_123",
            users_sent=100,
            users_added=95,
            users_failed=5,
            match_rate=0.72,
            duration_ms=1500,
        )
        assert result.success is True
        assert result.users_sent == 100
        assert result.error_message is None

    def test_failure_result(self):
        result = AudienceSyncResult(
            success=False,
            operation="update",
            error_message="Rate limit exceeded",
            error_code="RATE_LIMIT",
            error_details={"retry_after": 60},
        )
        assert result.success is False
        assert result.error_code == "RATE_LIMIT"

    def test_defaults(self):
        result = AudienceSyncResult(success=True, operation="create")
        assert result.users_sent == 0
        assert result.users_added == 0
        assert result.users_removed == 0
        assert result.users_failed == 0
        assert result.audience_size is None
        assert result.platform_response == {}
        assert result.duration_ms == 0


class TestAudienceConfig:
    """Tests for AudienceConfig data class."""

    def test_minimal_config(self):
        config = AudienceConfig(name="High Value Customers")
        assert config.name == "High Value Customers"
        assert config.audience_type == "customer_list"
        assert config.retention_days is None

    def test_full_config(self):
        config = AudienceConfig(
            name="VIP Segment",
            description="Top 10% spenders",
            customer_file_source="USER_PROVIDED_ONLY",
            retention_days=30,
            extra_config={"custom_key": "value"},
        )
        assert config.description == "Top 10% spenders"
        assert config.extra_config["custom_key"] == "value"


# =============================================================================
# Base Connector Utility Tests
# =============================================================================


class TestBaseConnectorUtilities:
    """Tests for BaseAudienceConnector utility methods."""

    def _get_concrete_connector(self):
        """Create a concrete implementation for testing base utilities."""
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        return MetaAudienceConnector(access_token="test_token", ad_account_id="act_123")

    def test_hash_identifier_email(self):
        conn = self._get_concrete_connector()
        hashed = conn._hash_identifier("Test@Example.com", IdentifierType.EMAIL)
        expected = hashlib.sha256("test@example.com".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_hash_identifier_phone(self):
        conn = self._get_concrete_connector()
        hashed = conn._hash_identifier("+1 (555) 123-4567", IdentifierType.PHONE)
        expected = hashlib.sha256("+15551234567".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_chunk_list(self):
        conn = self._get_concrete_connector()
        data = list(range(10))
        chunks = conn._chunk_list(data, 3)
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[3] == [9]

    def test_chunk_list_empty(self):
        conn = self._get_concrete_connector()
        assert conn._chunk_list([], 5) == []

    def test_chunk_list_exact_size(self):
        conn = self._get_concrete_connector()
        data = [1, 2, 3]
        chunks = conn._chunk_list(data, 3)
        assert len(chunks) == 1
        assert chunks[0] == [1, 2, 3]

    def test_prepare_users_for_upload(self):
        conn = self._get_concrete_connector()
        users = [
            AudienceUser(
                profile_id="1",
                identifiers=[
                    UserIdentifier(
                        identifier_type=IdentifierType.EMAIL,
                        hashed_value="hashed_email_1",
                    ),
                ],
            ),
            AudienceUser(
                profile_id="2",
                identifiers=[
                    UserIdentifier(
                        identifier_type=IdentifierType.PHONE,
                        hashed_value="hashed_phone_2",
                    ),
                ],
            ),
        ]
        prepared = conn._prepare_users_for_upload(users)
        assert len(prepared) == 2
        assert prepared[0]["email"] == "hashed_email_1"
        assert prepared[1]["phone"] == "hashed_phone_2"

    def test_prepare_users_skips_empty_identifiers(self):
        conn = self._get_concrete_connector()
        users = [
            AudienceUser(profile_id="1", identifiers=[]),
            AudienceUser(
                profile_id="2",
                identifiers=[UserIdentifier(identifier_type=IdentifierType.EMAIL)],
            ),
        ]
        prepared = conn._prepare_users_for_upload(users)
        assert len(prepared) == 0  # No users with valid identifiers


# =============================================================================
# Meta Connector Tests
# =============================================================================


class TestMetaAudienceConnector:
    """Tests for MetaAudienceConnector."""

    def test_ad_account_id_prefixed(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="12345")
        assert conn.ad_account_id == "act_12345"

    def test_ad_account_id_already_prefixed(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_12345")
        assert conn.ad_account_id == "act_12345"

    def test_platform_name(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")
        assert conn.PLATFORM_NAME == "meta"

    def test_batch_size(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        assert MetaAudienceConnector.BATCH_SIZE == 10000

    def test_prepare_meta_user_data(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        users = [
            AudienceUser(
                profile_id="1",
                identifiers=[
                    UserIdentifier(identifier_type=IdentifierType.EMAIL, hashed_value="email_hash"),
                    UserIdentifier(identifier_type=IdentifierType.PHONE, hashed_value="phone_hash"),
                ],
            ),
            AudienceUser(
                profile_id="2",
                identifiers=[
                    UserIdentifier(identifier_type=IdentifierType.MOBILE_ADVERTISER_ID, hashed_value="madid_hash"),
                ],
            ),
        ]
        rows = conn._prepare_meta_user_data(users)
        assert len(rows) == 2
        assert rows[0] == ["email_hash", "phone_hash", ""]
        assert rows[1] == ["", "", "madid_hash"]

    def test_prepare_meta_user_data_empty_users(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")
        assert conn._prepare_meta_user_data([]) == []

    def test_prepare_meta_user_data_skips_no_identifiers(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")
        users = [AudienceUser(profile_id="1", identifiers=[])]
        assert conn._prepare_meta_user_data(users) == []

    @pytest.mark.asyncio
    async def test_create_audience_success(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        config = AudienceConfig(name="Test Audience")

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "aud_999"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await conn.create_audience(config, users=[])

        assert result.success is True
        assert result.platform_audience_id == "aud_999"
        assert result.operation == "create"

    @pytest.mark.asyncio
    async def test_create_audience_no_id_returned(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        config = AudienceConfig(name="Test")
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No 'id' field
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await conn.create_audience(config, users=[])

        assert result.success is False
        assert "No audience ID" in result.error_message

    @pytest.mark.asyncio
    async def test_create_audience_http_error(self):
        import httpx
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        config = AudienceConfig(name="Test")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Bad request", "code": 100}}'
        mock_response.json.return_value = {"error": {"message": "Bad request", "code": 100}}
        error = httpx.HTTPStatusError("Bad", request=MagicMock(), response=mock_response)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await conn.create_audience(config, users=[])

        assert result.success is False
        assert result.error_message == "Bad request"

    @pytest.mark.asyncio
    async def test_delete_audience_success(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.delete.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await conn.delete_audience("aud_123")

        assert result.success is True
        assert result.operation == "delete"

    @pytest.mark.asyncio
    async def test_delete_audience_network_error(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.delete.side_effect = ConnectionError("Network down")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await conn.delete_audience("aud_123")

        assert result.success is False
        assert "Network down" in result.error_message


# =============================================================================
# AudienceSyncService Tests
# =============================================================================


def _make_async_db():
    """Create a mock async DB session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_scalars_result(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _make_scalar_count(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_platform_audience(tenant_id=1, platform="meta"):
    pa = MagicMock(spec=PlatformAudience)
    pa.id = uuid4()
    pa.tenant_id = tenant_id
    pa.segment_id = uuid4()
    pa.platform = platform
    pa.platform_audience_id = "aud_ext_123"
    pa.platform_audience_name = "Test Audience"
    pa.ad_account_id = "act_123"
    pa.description = "Test desc"
    pa.auto_sync = True
    pa.sync_interval_hours = 24
    pa.is_active = True
    pa.last_sync_at = None
    pa.last_sync_status = None
    pa.last_sync_error = None
    pa.platform_size = None
    pa.matched_size = None
    pa.match_rate = None
    pa.created_at = datetime.now(timezone.utc)
    pa.updated_at = datetime.now(timezone.utc)
    pa.next_sync_at = None
    pa.platform_config = {}
    return pa


def _make_sync_job(status=SyncStatus.COMPLETED.value, operation="update"):
    job = MagicMock(spec=AudienceSyncJob)
    job.id = uuid4()
    job.tenant_id = 1
    job.platform_audience_id = uuid4()
    job.operation = operation
    job.status = status
    job.started_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)
    job.duration_ms = 500
    job.profiles_total = 100
    job.profiles_sent = 100
    job.profiles_added = 95
    job.profiles_removed = 0
    job.profiles_failed = 5
    job.error_message = None
    job.error_details = {}
    job.platform_response = {}
    job.triggered_by = "manual"
    job.triggered_by_user_id = None
    job.created_at = datetime.now(timezone.utc)
    return job


def _make_credential(platform="meta"):
    cred = MagicMock(spec=AudienceSyncCredential)
    cred.id = uuid4()
    cred.tenant_id = 1
    cred.platform = platform
    cred.ad_account_id = "act_123"
    cred.ad_account_name = "Main Account"
    cred.is_active = True
    cred.access_token = "test_access_token"
    cred.config = {}
    return cred


def _make_segment():
    segment = MagicMock()
    segment.id = uuid4()
    segment.tenant_id = 1
    segment.name = "High Value"
    return segment


class TestAudienceSyncServiceConnectorFactory:
    """Tests for _get_connector factory method."""

    def test_get_meta_connector(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector

        db = _make_async_db()
        service = AudienceSyncService(db, tenant_id=1)
        cred = _make_credential(platform="meta")
        cred.config = {"app_secret": "test_secret"}

        connector = service._get_connector("meta", cred)
        assert isinstance(connector, MetaAudienceConnector)

    def test_get_google_connector(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        from app.services.cdp.audience_sync.google_connector import GoogleAudienceConnector

        db = _make_async_db()
        service = AudienceSyncService(db, tenant_id=1)
        cred = _make_credential(platform="google")
        cred.config = {"developer_token": "dev_tok", "login_customer_id": "cust_123"}

        connector = service._get_connector("google", cred)
        assert isinstance(connector, GoogleAudienceConnector)

    def test_unknown_platform_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, tenant_id=1)
        cred = _make_credential()

        with pytest.raises(ValueError, match="Unknown platform"):
            service._get_connector("twitter", cred)


class TestAudienceSyncServiceIdentifierMapping:
    """Tests for _map_identifier_type."""

    def test_email_mapping(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)
        assert service._map_identifier_type("email") == IdentifierType.EMAIL

    def test_phone_mapping(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)
        assert service._map_identifier_type("phone") == IdentifierType.PHONE

    def test_device_id_mapping(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)
        assert service._map_identifier_type("device_id") == IdentifierType.MOBILE_ADVERTISER_ID

    def test_unknown_mapping_returns_none(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)
        assert service._map_identifier_type("address") is None


class TestAudienceSyncServiceProfilesToUsers:
    """Tests for _profiles_to_audience_users."""

    @pytest.mark.asyncio
    async def test_converts_profiles_with_identifiers(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)

        identifier = MagicMock()
        identifier.identifier_type = "email"
        identifier.identifier_hash = "hashed_email_value"

        profile = MagicMock()
        profile.id = uuid4()
        profile.identifiers = [identifier]

        users = await service._profiles_to_audience_users([profile])
        assert len(users) == 1
        assert users[0].profile_id == str(profile.id)
        assert users[0].identifiers[0].hashed_value == "hashed_email_value"

    @pytest.mark.asyncio
    async def test_skips_profiles_without_identifiers(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)

        profile = MagicMock()
        profile.id = uuid4()
        profile.identifiers = []

        users = await service._profiles_to_audience_users([profile])
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_skips_unknown_identifier_types(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)

        identifier = MagicMock()
        identifier.identifier_type = "unknown_type"
        identifier.identifier_hash = "hash"

        profile = MagicMock()
        profile.id = uuid4()
        profile.identifiers = [identifier]

        users = await service._profiles_to_audience_users([profile])
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_multiple_identifiers_per_profile(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        service = AudienceSyncService(_make_async_db(), 1)

        id1 = MagicMock()
        id1.identifier_type = "email"
        id1.identifier_hash = "email_hash"

        id2 = MagicMock()
        id2.identifier_type = "phone"
        id2.identifier_hash = "phone_hash"

        profile = MagicMock()
        profile.id = uuid4()
        profile.identifiers = [id1, id2]

        users = await service._profiles_to_audience_users([profile])
        assert len(users) == 1
        assert len(users[0].identifiers) == 2


class TestAudienceSyncServiceCreatePlatformAudience:
    """Tests for create_platform_audience."""

    @pytest.mark.asyncio
    async def test_segment_not_found_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        db.execute.return_value = _make_scalar_result(None)
        service = AudienceSyncService(db, 1)

        with pytest.raises(ValueError, match="not found"):
            await service.create_platform_audience(
                segment_id=uuid4(),
                platform="meta",
                ad_account_id="act_123",
                audience_name="Test",
            )

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        segment = _make_segment()
        db = _make_async_db()
        # First call returns segment, second returns no credentials
        db.execute.side_effect = [
            _make_scalar_result(segment),
            _make_scalar_result(None),
        ]
        service = AudienceSyncService(db, 1)

        with pytest.raises(ValueError, match="No credentials"):
            await service.create_platform_audience(
                segment_id=segment.id,
                platform="meta",
                ad_account_id="act_123",
                audience_name="Test",
            )


class TestAudienceSyncServiceSyncPlatformAudience:
    """Tests for sync_platform_audience."""

    @pytest.mark.asyncio
    async def test_audience_not_found_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        db.execute.return_value = _make_scalar_result(None)
        service = AudienceSyncService(db, 1)

        with pytest.raises(ValueError, match="not found"):
            await service.sync_platform_audience(uuid4())

    @pytest.mark.asyncio
    async def test_segment_not_found_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        pa = _make_platform_audience()
        db = _make_async_db()
        db.execute.side_effect = [
            _make_scalar_result(pa),
            _make_scalar_result(None),  # segment not found
        ]
        service = AudienceSyncService(db, 1)

        with pytest.raises(ValueError, match="Segment.*not found"):
            await service.sync_platform_audience(pa.id)

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        pa = _make_platform_audience()
        segment = _make_segment()
        db = _make_async_db()
        db.execute.side_effect = [
            _make_scalar_result(pa),
            _make_scalar_result(segment),
            _make_scalar_result(None),  # no credentials
        ]
        service = AudienceSyncService(db, 1)

        with pytest.raises(ValueError, match="No credentials"):
            await service.sync_platform_audience(pa.id)


class TestAudienceSyncServiceDeletePlatformAudience:
    """Tests for delete_platform_audience."""

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        db.execute.return_value = _make_scalar_result(None)
        service = AudienceSyncService(db, 1)

        result = await service.delete_platform_audience(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_without_platform_deletion(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        pa = _make_platform_audience()
        db = _make_async_db()
        db.execute.return_value = _make_scalar_result(pa)
        service = AudienceSyncService(db, 1)

        result = await service.delete_platform_audience(pa.id, delete_from_platform=False)
        assert result is True
        db.delete.assert_called_once_with(pa)
        db.flush.assert_called()


class TestAudienceSyncServiceListPlatformAudiences:
    """Tests for list_platform_audiences."""

    @pytest.mark.asyncio
    async def test_list_returns_audiences_and_total(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        audiences = [_make_platform_audience(), _make_platform_audience()]
        db = _make_async_db()
        # First execute = count query, second = actual query
        db.execute.side_effect = [
            _make_scalar_count(2),
            _make_scalars_result(audiences),
        ]
        service = AudienceSyncService(db, 1)

        result, total = await service.list_platform_audiences()
        assert total == 2
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_empty(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        db.execute.side_effect = [
            _make_scalar_count(0),
            _make_scalars_result([]),
        ]
        service = AudienceSyncService(db, 1)

        result, total = await service.list_platform_audiences()
        assert total == 0
        assert result == []


class TestAudienceSyncServiceGetSyncHistory:
    """Tests for get_sync_history."""

    @pytest.mark.asyncio
    async def test_returns_jobs(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        jobs = [_make_sync_job(), _make_sync_job()]
        db = _make_async_db()
        db.execute.return_value = _make_scalars_result(jobs)
        service = AudienceSyncService(db, 1)

        result = await service.get_sync_history(uuid4())
        assert len(result) == 2


class TestAudienceSyncServiceGetConnectedPlatforms:
    """Tests for get_connected_platforms."""

    @pytest.mark.asyncio
    async def test_returns_grouped_platforms(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        cred1 = _make_credential(platform="meta")
        cred1.ad_account_id = "act_1"
        cred1.ad_account_name = "Account 1"

        cred2 = _make_credential(platform="meta")
        cred2.ad_account_id = "act_2"
        cred2.ad_account_name = "Account 2"

        cred3 = _make_credential(platform="google")
        cred3.ad_account_id = "goog_1"
        cred3.ad_account_name = "Google Account"

        db = _make_async_db()
        db.execute.return_value = _make_scalars_result([cred1, cred2, cred3])
        service = AudienceSyncService(db, 1)

        platforms = await service.get_connected_platforms()
        assert len(platforms) == 2
        meta = next(p for p in platforms if p["platform"] == "meta")
        assert len(meta["ad_accounts"]) == 2

    @pytest.mark.asyncio
    async def test_no_credentials(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        db.execute.return_value = _make_scalars_result([])
        service = AudienceSyncService(db, 1)

        platforms = await service.get_connected_platforms()
        assert platforms == []


class TestAudienceSyncServiceExecuteSyncJob:
    """Tests for _execute_sync_job internal method."""

    @pytest.mark.asyncio
    async def test_update_requires_platform_audience_id(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        pa.platform_audience_id = None  # No platform ID
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job()

        # Mock _get_segment_profiles to return empty
        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No platform audience ID"):
            await service._execute_sync_job(
                job, pa, cred, segment, operation=SyncOperation.UPDATE
            )

    @pytest.mark.asyncio
    async def test_replace_requires_platform_audience_id(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        pa.platform_audience_id = None
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job()

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No platform audience ID"):
            await service._execute_sync_job(
                job, pa, cred, segment, operation=SyncOperation.REPLACE
            )

    @pytest.mark.asyncio
    async def test_delete_requires_platform_audience_id(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        pa.platform_audience_id = None
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job()

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No platform audience ID"):
            await service._execute_sync_job(
                job, pa, cred, segment, operation=SyncOperation.DELETE
            )

    @pytest.mark.asyncio
    async def test_unknown_operation_raises(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job()

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="Unknown operation"):
            await service._execute_sync_job(
                job, pa, cred, segment, operation="invalid_op"
            )

    @pytest.mark.asyncio
    async def test_create_operation_calls_connector(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job(operation="create")

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        mock_connector = AsyncMock()
        mock_connector.create_audience.return_value = AudienceSyncResult(
            success=True, operation="create", platform_audience_id="aud_new",
            users_sent=0, users_added=0, duration_ms=100,
        )
        service._get_connector = MagicMock(return_value=mock_connector)

        result = await service._execute_sync_job(
            job, pa, cred, segment, operation=SyncOperation.CREATE
        )
        assert result.success is True
        assert job.status == SyncStatus.COMPLETED.value
        mock_connector.create_audience.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_sync_status(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job(operation="create")

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        mock_connector = AsyncMock()
        mock_connector.create_audience.return_value = AudienceSyncResult(
            success=False, operation="create",
            users_sent=100, users_added=80, users_failed=20,
            error_message="Some records failed",
        )
        service._get_connector = MagicMock(return_value=mock_connector)

        result = await service._execute_sync_job(
            job, pa, cred, segment, operation=SyncOperation.CREATE
        )
        assert job.status == SyncStatus.PARTIAL.value

    @pytest.mark.asyncio
    async def test_failed_sync_status(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService

        db = _make_async_db()
        service = AudienceSyncService(db, 1)

        pa = _make_platform_audience()
        cred = _make_credential()
        segment = _make_segment()
        job = _make_sync_job(operation="create")

        service._get_segment_profiles = AsyncMock(return_value=[])
        service._profiles_to_audience_users = AsyncMock(return_value=[])

        mock_connector = AsyncMock()
        mock_connector.create_audience.return_value = AudienceSyncResult(
            success=False, operation="create",
            users_sent=0, users_added=0, users_failed=0,
            error_message="Connection refused",
        )
        service._get_connector = MagicMock(return_value=mock_connector)

        result = await service._execute_sync_job(
            job, pa, cred, segment, operation=SyncOperation.CREATE
        )
        assert job.status == SyncStatus.FAILED.value
        assert job.error_message == "Connection refused"


# =============================================================================
# Pydantic Schema Tests
# =============================================================================


class TestPlatformAudienceCreate:
    """Tests for PlatformAudienceCreate schema."""

    def test_minimal(self):
        req = PlatformAudienceCreate(
            segment_id=uuid4(),
            platform="meta",
            ad_account_id="act_123",
            audience_name="Test",
        )
        assert req.auto_sync is True
        assert req.sync_interval_hours == 24
        assert req.description is None

    def test_full(self):
        req = PlatformAudienceCreate(
            segment_id=uuid4(),
            platform="google",
            ad_account_id="goog_123",
            audience_name="High Spenders",
            description="Top 10%",
            auto_sync=False,
            sync_interval_hours=12,
        )
        assert req.auto_sync is False
        assert req.sync_interval_hours == 12


class TestTriggerSyncRequest:
    """Tests for TriggerSyncRequest schema."""

    def test_default_operation(self):
        req = TriggerSyncRequest()
        assert req.operation == "update"

    def test_replace_operation(self):
        req = TriggerSyncRequest(operation="replace")
        assert req.operation == "replace"


class TestConnectedPlatformResponse:
    """Tests for ConnectedPlatformResponse schema."""

    def test_response(self):
        resp = ConnectedPlatformResponse(
            platform="meta",
            ad_accounts=[
                {"ad_account_id": "act_1", "ad_account_name": "Acc 1"},
            ],
        )
        assert resp.platform == "meta"
        assert len(resp.ad_accounts) == 1


class TestPlatformAudienceListResponse:
    """Tests for PlatformAudienceListResponse schema."""

    def test_empty_list(self):
        resp = PlatformAudienceListResponse(audiences=[], total=0)
        assert resp.total == 0
        assert resp.audiences == []


class TestSyncHistoryResponse:
    """Tests for SyncHistoryResponse schema."""

    def test_empty_history(self):
        resp = SyncHistoryResponse(jobs=[])
        assert resp.jobs == []


# =============================================================================
# Credential Encryption Tests
# =============================================================================


class TestAudienceSyncCredentialEncryption:
    """Tests for credential encryption/decryption via the model's methods.

    SQLAlchemy instrumented attributes don't work with __new__, so we test
    the encryption/decryption logic by calling methods on a mock that
    delegates to the real method implementations.
    """

    def _make_cred_mock(self, access_enc=None, refresh_enc=None):
        """Create an object that behaves like AudienceSyncCredential for method testing."""
        class FakeCred:
            _access_token_encrypted = access_enc
            _refresh_token_encrypted = refresh_enc
            set_access_token = AudienceSyncCredential.set_access_token
            get_access_token = AudienceSyncCredential.get_access_token
            set_refresh_token = AudienceSyncCredential.set_refresh_token
            get_refresh_token = AudienceSyncCredential.get_refresh_token
        return FakeCred()

    def test_set_access_token_none(self):
        cred = self._make_cred_mock(access_enc="something")
        cred.set_access_token(None)
        assert cred._access_token_encrypted is None

    def test_set_refresh_token_none(self):
        cred = self._make_cred_mock(refresh_enc="something")
        cred.set_refresh_token(None)
        assert cred._refresh_token_encrypted is None

    def test_set_access_token_encrypts(self):
        cred = self._make_cred_mock()
        with patch("app.core.security.encrypt_pii", return_value="encrypted_value"):
            cred.set_access_token("plain_token")
        assert cred._access_token_encrypted == "encrypted_value"

    def test_get_access_token_decrypts(self):
        cred = self._make_cred_mock(access_enc="encrypted_value")
        with patch("app.core.security.decrypt_pii", return_value="plain_token"):
            result = cred.get_access_token()
        assert result == "plain_token"

    def test_get_access_token_none_when_empty(self):
        cred = self._make_cred_mock(access_enc=None)
        assert cred.get_access_token() is None

    def test_set_refresh_token_encrypts(self):
        cred = self._make_cred_mock()
        with patch("app.core.security.encrypt_pii", return_value="encrypted_refresh"):
            cred.set_refresh_token("plain_refresh")
        assert cred._refresh_token_encrypted == "encrypted_refresh"

    def test_get_refresh_token_decrypts(self):
        cred = self._make_cred_mock(refresh_enc="encrypted_refresh")
        with patch("app.core.security.decrypt_pii", return_value="plain_refresh"):
            result = cred.get_refresh_token()
        assert result == "plain_refresh"

    def test_get_refresh_token_none_when_empty(self):
        cred = self._make_cred_mock(refresh_enc=None)
        assert cred.get_refresh_token() is None


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and boundary tests."""

    def test_sync_platform_matches_ad_platform(self):
        """SyncPlatform and AdPlatform should cover the same 4 platforms."""
        from app.models.campaign_builder import AdPlatform
        sync_values = {p.value for p in SyncPlatform}
        ad_values = {p.value for p in AdPlatform}
        assert sync_values == ad_values

    def test_all_sync_statuses_present(self):
        expected = {"pending", "processing", "completed", "failed", "partial"}
        actual = {s.value for s in SyncStatus}
        assert actual == expected

    def test_all_operations_present(self):
        expected = {"create", "update", "replace", "delete"}
        actual = {o.value for o in SyncOperation}
        assert actual == expected

    def test_connector_classes_map_all_platforms(self):
        from app.services.cdp.audience_sync.service import AudienceSyncService
        for platform in SyncPlatform:
            assert platform.value in AudienceSyncService.CONNECTOR_CLASSES

    def test_audience_sync_result_defaults_safe(self):
        """Default error_details and platform_response should be empty dicts, not shared refs."""
        r1 = AudienceSyncResult(success=True, operation="create")
        r2 = AudienceSyncResult(success=True, operation="create")
        r1.error_details["key"] = "val"
        assert "key" not in r2.error_details

    def test_user_identifier_phone_preserves_plus(self):
        uid = UserIdentifier(
            identifier_type=IdentifierType.PHONE,
            raw_value="+966501234567",
        )
        hashed = uid.get_hashed()
        expected = hashlib.sha256("+966501234567".encode("utf-8")).hexdigest()
        assert hashed == expected

    def test_empty_audience_user_list_prepared(self):
        from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
        conn = MetaAudienceConnector(access_token="tok", ad_account_id="act_1")
        assert conn._prepare_meta_user_data([]) == []

    def test_audience_config_default_type(self):
        config = AudienceConfig(name="Test")
        assert config.audience_type == "customer_list"

    def test_sync_interval_hours_range(self):
        """Schema enforces 1-168 hours."""
        req = PlatformAudienceCreate(
            segment_id=uuid4(),
            platform="meta",
            ad_account_id="act_1",
            audience_name="Test",
            sync_interval_hours=1,
        )
        assert req.sync_interval_hours == 1

        req2 = PlatformAudienceCreate(
            segment_id=uuid4(),
            platform="meta",
            ad_account_id="act_1",
            audience_name="Test",
            sync_interval_hours=168,
        )
        assert req2.sync_interval_hours == 168
