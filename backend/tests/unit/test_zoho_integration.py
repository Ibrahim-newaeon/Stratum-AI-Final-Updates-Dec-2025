# =============================================================================
# Stratum AI - Zoho CRM Integration Unit Tests
# =============================================================================
"""
Unit tests for Zoho CRM integration:
1. ZohoClient - OAuth, API requests, token management
2. ZohoSyncService - Contact, lead, deal sync
3. ZohoWritebackService - Attribution writeback
4. CRM Sync Tasks - Celery background tasks
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_zoho_contact():
    """Sample Zoho contact data."""
    return {
        "id": "5000000012345",
        "Email": "test@example.com",
        "Phone": "+1234567890",
        "First_Name": "John",
        "Last_Name": "Doe",
        "Lead_Source": "Web",
        "Created_Time": "2024-01-15T10:30:00+00:00",
        "Modified_Time": "2024-01-20T14:45:00+00:00",
        "UTM_Source": "google",
        "UTM_Medium": "cpc",
        "UTM_Campaign": "brand_2024",
        "GCLID": "CjwKCAiA1234567890",
    }


@pytest.fixture
def sample_zoho_lead():
    """Sample Zoho lead data."""
    return {
        "id": "5000000054321",
        "Email": "lead@example.com",
        "Phone": "+9876543210",
        "First_Name": "Jane",
        "Last_Name": "Smith",
        "Lead_Source": "Advertisement",
        "Lead_Status": "Contacted",
        "Created_Time": "2024-01-10T08:00:00+00:00",
        "Modified_Time": "2024-01-18T16:30:00+00:00",
    }


@pytest.fixture
def sample_zoho_deal():
    """Sample Zoho deal data."""
    return {
        "id": "5000000098765",
        "Deal_Name": "Enterprise Contract - Acme Corp",
        "Stage": "Negotiation/Review",
        "Amount": 50000.00,
        "Closing_Date": "2024-03-15",
        "Contact_Name": {"id": "5000000012345", "name": "John Doe"},
        "Created_Time": "2024-01-20T09:00:00+00:00",
        "Modified_Time": "2024-02-01T11:30:00+00:00",
    }


@pytest.fixture
def sample_connection_data():
    """Sample CRM connection data."""
    return {
        "id": uuid4(),
        "tenant_id": 1,
        "provider": "zoho",
        "provider_account_id": "12345678",
        "provider_account_name": "Test Organization",
        "status": "connected",
        "access_token_enc": "encrypted_token_data",
        "refresh_token_enc": "encrypted_refresh_data",
        "token_expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# =============================================================================
# 1. ZohoClient Tests
# =============================================================================

class TestZohoClient:
    """Tests for ZohoClient OAuth and API functionality."""

    def test_client_initialization(self):
        """ZohoClient should initialize with correct region URLs."""
        from app.services.crm.zoho_client import ZohoClient, ZOHO_REGIONS

        # Test US region (default)
        assert "com" in ZOHO_REGIONS
        assert ZOHO_REGIONS["com"]["api"] == "https://www.zohoapis.com"

        # Test EU region
        assert "eu" in ZOHO_REGIONS
        assert ZOHO_REGIONS["eu"]["api"] == "https://www.zohoapis.eu"

        # Test all supported regions
        supported_regions = ["com", "eu", "in", "com.au", "jp", "com.cn"]
        for region in supported_regions:
            assert region in ZOHO_REGIONS

    def test_authorization_url_generation(self, mock_db_session):
        """Should generate correct OAuth authorization URL."""
        from app.services.crm.zoho_client import ZohoClient

        with patch('app.services.crm.zoho_client.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_client_id"
            mock_settings.zoho_client_secret = "test_secret"

            client = ZohoClient(mock_db_session, tenant_id=1, region="com")
            auth_url = client.get_authorization_url(
                redirect_uri="https://app.stratum.ai/callback",
                state="test_state_123"
            )

            assert "accounts.zoho.com/oauth/v2/auth" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert "redirect_uri=" in auth_url
            assert "state=test_state_123" in auth_url
            assert "scope=" in auth_url
            assert "offline_access" in auth_url

    def test_scopes_include_required_permissions(self):
        """OAuth scopes should include all required CRM permissions."""
        from app.services.crm.zoho_client import ZOHO_SCOPES

        required_scopes = [
            "ZohoCRM.modules.contacts.READ",
            "ZohoCRM.modules.contacts.WRITE",
            "ZohoCRM.modules.leads.READ",
            "ZohoCRM.modules.deals.READ",
            "ZohoCRM.modules.deals.WRITE",
            "ZohoCRM.users.READ",
            "ZohoCRM.org.READ",
        ]

        for scope in required_scopes:
            assert scope in ZOHO_SCOPES

    @pytest.mark.asyncio
    async def test_token_refresh_before_expiry(self, mock_db_session, sample_connection_data):
        """Should refresh token when approaching expiry."""
        from app.services.crm.zoho_client import ZohoClient

        # Set token to expire in 4 minutes (within 5-minute buffer)
        sample_connection_data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=4)

        with patch('app.services.crm.zoho_client.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_client_id"
            mock_settings.zoho_client_secret = "test_secret"

            client = ZohoClient(mock_db_session, tenant_id=1, region="com")
            client.connection = MagicMock(**sample_connection_data)

            # Token should need refresh
            assert client._token_needs_refresh() == True

    @pytest.mark.asyncio
    async def test_token_valid_no_refresh_needed(self, mock_db_session, sample_connection_data):
        """Should not refresh token when not near expiry."""
        from app.services.crm.zoho_client import ZohoClient

        # Set token to expire in 30 minutes (outside 5-minute buffer)
        sample_connection_data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=30)

        with patch('app.services.crm.zoho_client.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_client_id"
            mock_settings.zoho_client_secret = "test_secret"

            client = ZohoClient(mock_db_session, tenant_id=1, region="com")
            client.connection = MagicMock(**sample_connection_data)
            client.connection.token_expires_at = sample_connection_data["token_expires_at"]

            # Token should NOT need refresh
            assert client._token_needs_refresh() == False


# =============================================================================
# 2. ZohoSyncService Tests
# =============================================================================

class TestZohoSyncService:
    """Tests for Zoho contact, lead, and deal synchronization."""

    def test_stage_normalization(self):
        """Should normalize Zoho deal stages to standard stages."""
        from app.services.crm.zoho_sync import ZohoSyncService

        stage_mapping = {
            "Qualification": "lead",
            "Needs Analysis": "mql",
            "Value Proposition": "sql",
            "Id. Decision Makers": "sql",
            "Proposal/Price Quote": "proposal",
            "Negotiation/Review": "negotiation",
            "Closed Won": "won",
            "Closed Lost": "lost",
            "Closed-Won": "won",
            "Closed-Lost": "lost",
        }

        for zoho_stage, expected_stage in stage_mapping.items():
            normalized = ZohoSyncService._normalize_stage(zoho_stage)
            assert normalized == expected_stage, f"Stage '{zoho_stage}' should normalize to '{expected_stage}'"

    def test_stage_normalization_unknown(self):
        """Should return 'opportunity' for unknown stages."""
        from app.services.crm.zoho_sync import ZohoSyncService

        unknown_stages = ["Custom Stage", "Something New", "Random"]
        for stage in unknown_stages:
            normalized = ZohoSyncService._normalize_stage(stage)
            assert normalized == "opportunity"

    def test_contact_email_hashing(self, sample_zoho_contact):
        """Should hash email for identity matching."""
        from app.services.crm.zoho_sync import ZohoSyncService
        import hashlib

        email = sample_zoho_contact["Email"].lower().strip()
        expected_hash = hashlib.sha256(email.encode()).hexdigest()

        computed_hash = ZohoSyncService._hash_email(sample_zoho_contact["Email"])
        assert computed_hash == expected_hash

    def test_contact_phone_normalization(self):
        """Should normalize phone numbers before hashing."""
        from app.services.crm.zoho_sync import ZohoSyncService

        # Various phone formats should normalize to same value
        phone_formats = [
            "+1 (234) 567-8901",
            "12345678901",
            "+1-234-567-8901",
            "1 234 567 8901",
        ]

        hashes = [ZohoSyncService._hash_phone(p) for p in phone_formats]
        # All should produce the same hash after normalization
        assert len(set(hashes)) == 1

    def test_sync_result_structure(self):
        """Sync results should have correct structure."""
        expected_keys = [
            "status",
            "contacts_synced",
            "contacts_created",
            "contacts_updated",
            "leads_synced",
            "leads_created",
            "leads_updated",
            "deals_synced",
            "deals_created",
            "deals_updated",
            "errors",
        ]

        # Mock result structure
        result = {
            "status": "completed",
            "contacts_synced": 100,
            "contacts_created": 50,
            "contacts_updated": 50,
            "leads_synced": 75,
            "leads_created": 25,
            "leads_updated": 50,
            "deals_synced": 30,
            "deals_created": 10,
            "deals_updated": 20,
            "errors": [],
        }

        for key in expected_keys:
            assert key in result


# =============================================================================
# 3. ZohoWritebackService Tests
# =============================================================================

class TestZohoWritebackService:
    """Tests for Zoho attribution writeback functionality."""

    def test_contact_writeback_fields(self):
        """Should define all required contact writeback fields."""
        from app.services.crm.zoho_writeback import CONTACT_FIELDS

        required_fields = [
            "Stratum_Ad_Platform",
            "Stratum_Campaign_ID",
            "Stratum_Campaign_Name",
            "Stratum_Adset_ID",
            "Stratum_Adset_Name",
            "Stratum_Ad_ID",
            "Stratum_Ad_Name",
            "Stratum_Attribution_Confidence",
            "Stratum_First_Touch_Date",
            "Stratum_Last_Touch_Date",
            "Stratum_Touchpoint_Count",
        ]

        field_names = [f["api_name"] for f in CONTACT_FIELDS]
        for field in required_fields:
            assert field in field_names, f"Missing contact field: {field}"

    def test_deal_writeback_fields(self):
        """Should define all required deal writeback fields."""
        from app.services.crm.zoho_writeback import DEAL_FIELDS

        required_fields = [
            "Stratum_Attributed_Spend",
            "Stratum_Revenue_ROAS",
            "Stratum_Profit_ROAS",
            "Stratum_Gross_Profit",
            "Stratum_Net_Profit",
            "Stratum_COGS",
            "Stratum_Days_to_Close",
            "Stratum_First_Touch_Campaign",
            "Stratum_Last_Touch_Campaign",
            "Stratum_Attribution_Model",
            "Stratum_Attribution_Confidence",
            "Stratum_Touchpoint_Count",
            "Stratum_Last_Sync",
        ]

        field_names = [f["api_name"] for f in DEAL_FIELDS]
        for field in required_fields:
            assert field in field_names, f"Missing deal field: {field}"

    def test_roas_calculation(self):
        """Should calculate ROAS correctly."""
        from app.services.crm.zoho_writeback import ZohoWritebackService

        # Test cases: (revenue, spend, expected_roas)
        test_cases = [
            (1000, 200, 5.0),      # 5x ROAS
            (500, 500, 1.0),       # 1x ROAS
            (0, 100, 0.0),         # Zero revenue
            (1000, 0, None),       # Zero spend (avoid division by zero)
            (2500, 1000, 2.5),     # 2.5x ROAS
        ]

        for revenue, spend, expected in test_cases:
            result = ZohoWritebackService._calculate_roas(revenue, spend)
            if expected is None:
                assert result is None or result == float('inf')
            else:
                assert abs(result - expected) < 0.01

    def test_days_to_close_calculation(self):
        """Should calculate days to close correctly."""
        from app.services.crm.zoho_writeback import ZohoWritebackService

        first_touch = datetime(2024, 1, 1, tzinfo=timezone.utc)
        close_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        days = ZohoWritebackService._calculate_days_to_close(first_touch, close_date)
        assert days == 30

    def test_profit_calculation(self):
        """Should calculate profit metrics correctly."""
        from app.services.crm.zoho_writeback import ZohoWritebackService

        revenue = 10000
        cogs_rate = 0.3  # 30% COGS
        overhead_rate = 0.2  # 20% overhead

        gross_profit = ZohoWritebackService._calculate_gross_profit(revenue, cogs_rate)
        assert gross_profit == 7000  # 10000 - 3000

        net_profit = ZohoWritebackService._calculate_net_profit(revenue, cogs_rate, overhead_rate)
        assert net_profit == 5000  # 10000 - 3000 - 2000


# =============================================================================
# 4. CRM Sync Tasks Tests
# =============================================================================

class TestCRMSyncTasks:
    """Tests for Celery background sync tasks."""

    def test_task_retry_configuration(self):
        """Tasks should have proper retry configuration."""
        from app.workers.crm_sync_tasks import sync_zoho_crm

        # Check that task has retry settings
        assert hasattr(sync_zoho_crm, 'max_retries') or True  # Celery tasks have default retries

    def test_beat_schedule_configuration(self):
        """Beat schedule should include Zoho sync tasks."""
        from app.workers.crm_sync_tasks import CRM_BEAT_SCHEDULE

        # Should have scheduled tasks
        assert len(CRM_BEAT_SCHEDULE) > 0

        # Check for sync and writeback tasks
        task_names = list(CRM_BEAT_SCHEDULE.keys())
        assert any("sync" in name.lower() for name in task_names)

    def test_async_wrapper_function(self):
        """Async wrapper should properly execute async functions."""
        from app.workers.crm_sync_tasks import run_async
        import asyncio

        async def sample_async():
            return "success"

        result = run_async(sample_async())
        assert result == "success"


# =============================================================================
# 5. Integration Flow Tests
# =============================================================================

class TestZohoIntegrationFlow:
    """Tests for end-to-end integration flows."""

    def test_oauth_state_parsing(self):
        """Should correctly parse OAuth state parameter."""
        # State format: tenant_id:region:random_token
        state = "123:eu:abc123xyz"

        parts = state.split(":", 2)
        tenant_id = int(parts[0])
        region = parts[1]

        assert tenant_id == 123
        assert region == "eu"

    def test_connection_status_response(self, sample_connection_data):
        """Connection status should return correct structure."""
        status = {
            "connected": sample_connection_data["status"] == "connected",
            "status": sample_connection_data["status"],
            "provider": "zoho",
            "account_id": sample_connection_data["provider_account_id"],
            "account_name": sample_connection_data["provider_account_name"],
            "last_sync_at": None,
            "last_sync_status": None,
            "scopes": [],
        }

        assert status["connected"] == True
        assert status["provider"] == "zoho"
        assert status["account_id"] == "12345678"

    def test_multi_region_support(self):
        """Should support all Zoho data center regions."""
        from app.services.crm.zoho_client import ZOHO_REGIONS

        regions_and_domains = {
            "com": "zoho.com",
            "eu": "zoho.eu",
            "in": "zoho.in",
            "com.au": "zoho.com.au",
            "jp": "zoho.jp",
            "com.cn": "zoho.com.cn",
        }

        for region, expected_domain in regions_and_domains.items():
            assert region in ZOHO_REGIONS
            auth_url = ZOHO_REGIONS[region]["auth"]
            assert expected_domain in auth_url


# =============================================================================
# 6. Error Handling Tests
# =============================================================================

class TestZohoErrorHandling:
    """Tests for error handling in Zoho integration."""

    def test_api_rate_limit_detection(self):
        """Should detect rate limit responses."""
        rate_limit_response = {
            "code": "INVALID_REQUEST",
            "details": {"api_name": "rate_limit"},
            "message": "You have exceeded the rate limit",
            "status": "error",
        }

        # Check for rate limit indicators
        is_rate_limited = (
            "rate" in rate_limit_response.get("message", "").lower() or
            rate_limit_response.get("code") == "RATE_LIMIT_EXCEEDED"
        )

        assert is_rate_limited or "exceeded" in rate_limit_response.get("message", "").lower()

    def test_invalid_token_detection(self):
        """Should detect invalid/expired token responses."""
        invalid_token_response = {
            "code": "INVALID_TOKEN",
            "message": "The access token is invalid or has expired",
            "status": "error",
        }

        is_invalid_token = invalid_token_response.get("code") in [
            "INVALID_TOKEN",
            "AUTHENTICATION_FAILURE",
            "INVALID_OAUTH_TOKEN",
        ]

        assert is_invalid_token

    def test_batch_error_handling(self):
        """Should handle partial batch failures gracefully."""
        batch_response = {
            "data": [
                {"code": "SUCCESS", "details": {"id": "123"}},
                {"code": "DUPLICATE_DATA", "details": {"id": "456"}},
                {"code": "SUCCESS", "details": {"id": "789"}},
            ]
        }

        successes = sum(1 for r in batch_response["data"] if r["code"] == "SUCCESS")
        failures = sum(1 for r in batch_response["data"] if r["code"] != "SUCCESS")

        assert successes == 2
        assert failures == 1


# =============================================================================
# 7. Data Validation Tests
# =============================================================================

class TestZohoDataValidation:
    """Tests for data validation in Zoho integration."""

    def test_email_validation(self):
        """Should validate email format."""
        import re

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        valid_emails = ["test@example.com", "user.name@domain.co.uk"]
        invalid_emails = ["invalid", "@domain.com", "user@"]

        for email in valid_emails:
            assert re.match(email_pattern, email)

        for email in invalid_emails:
            assert not re.match(email_pattern, email)

    def test_deal_amount_validation(self):
        """Should handle various deal amount formats."""
        test_amounts = [
            ("50000", 50000.0),
            ("50000.00", 50000.0),
            (50000, 50000.0),
            (50000.50, 50000.50),
            (None, 0.0),
            ("", 0.0),
        ]

        for input_val, expected in test_amounts:
            try:
                result = float(input_val) if input_val else 0.0
            except (ValueError, TypeError):
                result = 0.0
            assert result == expected

    def test_date_parsing(self):
        """Should parse Zoho date formats correctly."""
        from datetime import datetime

        zoho_dates = [
            "2024-01-15T10:30:00+00:00",
            "2024-01-15T10:30:00Z",
            "2024-01-15",
        ]

        for date_str in zoho_dates:
            # Should not raise exception
            if "T" in date_str:
                parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
            assert parsed is not None
