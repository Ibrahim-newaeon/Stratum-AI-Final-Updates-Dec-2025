# =============================================================================
# Stratum AI - Platform Executor Unit Tests
# =============================================================================
"""
Comprehensive unit tests for the platform executors in apply_actions_queue.

Tests cover:
- PlatformExecutor base class dispatches to _mock_execute when use_mock_ad_data=True
- PlatformExecutor base class dispatches to _live_execute when use_mock_ad_data=False
- MetaExecutor._mock_execute returns expected structure for all action types
- GoogleExecutor._mock_execute returns expected structure for all action types
- TikTokExecutor._mock_execute returns expected structure for all action types
- PLATFORM_EXECUTORS dict has all expected platforms
- Each executor handles errors gracefully (mock exceptions)
- Each executor's _live_execute against a respx-mocked platform API
  (Graph API, Google Ads REST, TikTok Business, Snapchat Marketing):
  happy paths per action type, non-2xx platform errors, missing-credential
  guards, read-before-write fallbacks, and the standardized result contract.
  _live_execute is invoked directly, so the global settings.use_mock_ad_data
  switch is irrelevant for those tests.
"""

import json
from typing import Any, Dict
from unittest.mock import patch

import httpx
import pytest
import respx

from app.autopilot.service import ActionType
from app.core.config import settings
from app.tasks.apply_actions_queue import (
    PLATFORM_EXECUTORS,
    GoogleExecutor,
    MetaExecutor,
    PlatformExecutor,
    SnapchatExecutor,
    TikTokExecutor,
)

# =============================================================================
# Expected Result Keys
# =============================================================================

EXPECTED_RESULT_KEYS = {
    "success",
    "before_value",
    "after_value",
    "platform_response",
    "error",
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def meta_executor():
    """Create a MetaExecutor instance."""
    return MetaExecutor()


@pytest.fixture
def google_executor():
    """Create a GoogleExecutor instance."""
    return GoogleExecutor()


@pytest.fixture
def tiktok_executor():
    """Create a TikTokExecutor instance."""
    return TikTokExecutor()


# =============================================================================
# PlatformExecutor Base Class Tests
# =============================================================================


class TestPlatformExecutorDispatch:
    """Tests for PlatformExecutor.execute_action dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatches_to_mock_execute_when_mock_enabled(self):
        """execute_action should call _mock_execute when use_mock_ad_data=True."""
        executor = MetaExecutor()

        with patch("app.tasks.apply_actions_queue.settings") as mock_settings:
            mock_settings.use_mock_ad_data = True
            result = await executor.execute_action(
                action_type=ActionType.BUDGET_INCREASE.value,
                entity_type="campaign",
                entity_id="camp_001",
                action_details={"amount": 500},
            )

        assert result["success"] is True
        assert set(result.keys()) == EXPECTED_RESULT_KEYS

    @pytest.mark.asyncio
    async def test_dispatches_to_live_execute_when_mock_disabled(self):
        """execute_action should call _live_execute when use_mock_ad_data=False."""

        class SpyExecutor(PlatformExecutor):
            """Executor that records which method was called."""

            def __init__(self):
                self.mock_called = False
                self.live_called = False

            def _mock_execute(
                self, action_type, entity_type, entity_id, action_details
            ):
                self.mock_called = True
                return {
                    "success": True,
                    "before_value": None,
                    "after_value": None,
                    "platform_response": None,
                    "error": None,
                }

            async def _live_execute(
                self, action_type, entity_type, entity_id, action_details
            ):
                self.live_called = True
                return {
                    "success": True,
                    "before_value": None,
                    "after_value": None,
                    "platform_response": None,
                    "error": None,
                }

        executor = SpyExecutor()

        with patch("app.tasks.apply_actions_queue.settings") as mock_settings:
            mock_settings.use_mock_ad_data = False
            await executor.execute_action(
                action_type=ActionType.BUDGET_INCREASE.value,
                entity_type="campaign",
                entity_id="camp_001",
                action_details={"amount": 500},
            )

        assert executor.live_called is True
        assert executor.mock_called is False

    @pytest.mark.asyncio
    async def test_base_class_mock_execute_raises_not_implemented(self):
        """Base PlatformExecutor._mock_execute should raise NotImplementedError."""
        executor = PlatformExecutor()

        with pytest.raises(NotImplementedError):
            executor._mock_execute("budget_increase", "campaign", "camp_001", {})

    @pytest.mark.asyncio
    async def test_base_class_live_execute_raises_not_implemented(self):
        """Base PlatformExecutor._live_execute should raise NotImplementedError."""
        executor = PlatformExecutor()

        with pytest.raises(NotImplementedError):
            await executor._live_execute("budget_increase", "campaign", "camp_001", {})


# =============================================================================
# MetaExecutor Mock Tests
# =============================================================================


class TestMetaExecutorMock:
    """Tests for MetaExecutor._mock_execute."""

    def test_budget_increase_returns_expected_structure(self, meta_executor):
        """Budget increase should return success with increased daily_budget."""
        result = meta_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_meta_001",
            action_details={"amount": 2000},
        )

        assert result["success"] is True
        assert result["error"] is None
        assert set(result.keys()) == EXPECTED_RESULT_KEYS
        assert result["before_value"]["daily_budget"] == 10000
        assert result["after_value"]["daily_budget"] == 12000
        assert result["platform_response"]["request_id"] == "meta_mock_123"

    def test_budget_decrease_returns_expected_structure(self, meta_executor):
        """Budget decrease should return success with decreased daily_budget."""
        result = meta_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_meta_002",
            action_details={"amount": 3000},
        )

        assert result["success"] is True
        assert result["after_value"]["daily_budget"] == 7000

    def test_budget_decrease_does_not_go_below_zero(self, meta_executor):
        """Budget decrease should clamp at zero, not go negative."""
        result = meta_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_meta_003",
            action_details={"amount": 50000},
        )

        assert result["after_value"]["daily_budget"] == 0

    def test_pause_campaign_sets_status_paused(self, meta_executor):
        """Pause campaign should set status to PAUSED."""
        result = meta_executor._mock_execute(
            action_type=ActionType.PAUSE_CAMPAIGN.value,
            entity_type="campaign",
            entity_id="camp_meta_004",
            action_details={},
        )

        assert result["success"] is True
        assert result["before_value"]["status"] == "ACTIVE"
        assert result["after_value"]["status"] == "PAUSED"

    def test_pause_adset_sets_status_paused(self, meta_executor):
        """Pause adset should set status to PAUSED."""
        result = meta_executor._mock_execute(
            action_type=ActionType.PAUSE_ADSET.value,
            entity_type="adset",
            entity_id="adset_meta_001",
            action_details={},
        )

        assert result["after_value"]["status"] == "PAUSED"

    def test_pause_creative_sets_status_paused(self, meta_executor):
        """Pause creative should set status to PAUSED."""
        result = meta_executor._mock_execute(
            action_type=ActionType.PAUSE_CREATIVE.value,
            entity_type="creative",
            entity_id="creative_meta_001",
            action_details={},
        )

        assert result["after_value"]["status"] == "PAUSED"

    def test_enable_campaign_sets_status_active(self, meta_executor):
        """Enable campaign should set status to ACTIVE."""
        result = meta_executor._mock_execute(
            action_type=ActionType.ENABLE_CAMPAIGN.value,
            entity_type="campaign",
            entity_id="camp_meta_005",
            action_details={},
        )

        assert result["after_value"]["status"] == "ACTIVE"

    def test_enable_adset_sets_status_active(self, meta_executor):
        """Enable adset should set status to ACTIVE."""
        result = meta_executor._mock_execute(
            action_type=ActionType.ENABLE_ADSET.value,
            entity_type="adset",
            entity_id="adset_meta_002",
            action_details={},
        )

        assert result["after_value"]["status"] == "ACTIVE"

    def test_enable_creative_sets_status_active(self, meta_executor):
        """Enable creative should set status to ACTIVE."""
        result = meta_executor._mock_execute(
            action_type=ActionType.ENABLE_CREATIVE.value,
            entity_type="creative",
            entity_id="creative_meta_002",
            action_details={},
        )

        assert result["after_value"]["status"] == "ACTIVE"

    def test_budget_increase_with_zero_amount(self, meta_executor):
        """Budget increase with zero amount should leave budget unchanged."""
        result = meta_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_meta_006",
            action_details={"amount": 0},
        )

        assert (
            result["before_value"]["daily_budget"]
            == result["after_value"]["daily_budget"]
        )


# =============================================================================
# GoogleExecutor Mock Tests
# =============================================================================


class TestGoogleExecutorMock:
    """Tests for GoogleExecutor._mock_execute."""

    def test_budget_increase_returns_expected_structure(self, google_executor):
        """Budget increase should return success with increased budget_micros."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_google_001",
            action_details={"amount": 5},
        )

        assert result["success"] is True
        assert result["error"] is None
        assert set(result.keys()) == EXPECTED_RESULT_KEYS
        assert result["before_value"]["budget_micros"] == 10000000
        assert result["after_value"]["budget_micros"] == 15000000  # +5 * 1_000_000
        assert result["platform_response"]["status"] == "DONE"

    def test_budget_decrease_returns_expected_structure(self, google_executor):
        """Budget decrease should return success with decreased budget_micros."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_google_002",
            action_details={"amount": 3},
        )

        assert result["after_value"]["budget_micros"] == 7000000

    def test_budget_decrease_does_not_go_below_zero(self, google_executor):
        """Budget decrease should clamp at zero."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_google_003",
            action_details={"amount": 500},
        )

        assert result["after_value"]["budget_micros"] == 0

    def test_pause_campaign_sets_status_paused(self, google_executor):
        """Pause campaign should set status to PAUSED."""
        result = google_executor._mock_execute(
            action_type=ActionType.PAUSE_CAMPAIGN.value,
            entity_type="campaign",
            entity_id="camp_google_004",
            action_details={},
        )

        assert result["success"] is True
        assert result["before_value"]["status"] == "ENABLED"
        assert result["after_value"]["status"] == "PAUSED"

    def test_enable_campaign_sets_status_enabled(self, google_executor):
        """Enable campaign should set status to ENABLED."""
        result = google_executor._mock_execute(
            action_type=ActionType.ENABLE_CAMPAIGN.value,
            entity_type="campaign",
            entity_id="camp_google_005",
            action_details={},
        )

        assert result["after_value"]["status"] == "ENABLED"

    def test_pause_adset_sets_status_paused(self, google_executor):
        """Pause adset should set status to PAUSED (Google uses ad groups)."""
        result = google_executor._mock_execute(
            action_type=ActionType.PAUSE_ADSET.value,
            entity_type="adset",
            entity_id="adgroup_google_001",
            action_details={},
        )

        assert result["after_value"]["status"] == "PAUSED"

    def test_google_mock_response_includes_operation_name(self, google_executor):
        """Google mock response should include operation_name."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_google_006",
            action_details={"amount": 1},
        )

        assert "operation_name" in result["platform_response"]


# =============================================================================
# TikTokExecutor Mock Tests
# =============================================================================


class TestTikTokExecutorMock:
    """Tests for TikTokExecutor._mock_execute."""

    def test_budget_increase_returns_expected_structure(self, tiktok_executor):
        """Budget increase should return success with increased budget."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_tiktok_001",
            action_details={"amount": 50},
        )

        assert result["success"] is True
        assert result["error"] is None
        assert set(result.keys()) == EXPECTED_RESULT_KEYS
        assert result["before_value"]["budget"] == 100.00
        assert result["after_value"]["budget"] == 150.00
        assert result["platform_response"]["code"] == 0

    def test_budget_decrease_returns_expected_structure(self, tiktok_executor):
        """Budget decrease should return success with decreased budget."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_tiktok_002",
            action_details={"amount": 30},
        )

        assert result["after_value"]["budget"] == 70.00

    def test_budget_decrease_does_not_go_below_zero(self, tiktok_executor):
        """Budget decrease should clamp at zero."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.BUDGET_DECREASE.value,
            entity_type="campaign",
            entity_id="camp_tiktok_003",
            action_details={"amount": 5000},
        )

        assert result["after_value"]["budget"] == 0

    def test_pause_campaign_sets_operation_status_disable(self, tiktok_executor):
        """Pause campaign should set operation_status to DISABLE."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.PAUSE_CAMPAIGN.value,
            entity_type="campaign",
            entity_id="camp_tiktok_004",
            action_details={},
        )

        assert result["success"] is True
        assert result["before_value"]["operation_status"] == "ENABLE"
        assert result["after_value"]["operation_status"] == "DISABLE"

    def test_pause_adset_sets_operation_status_disable(self, tiktok_executor):
        """Pause adset should set operation_status to DISABLE."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.PAUSE_ADSET.value,
            entity_type="adset",
            entity_id="adgroup_tiktok_001",
            action_details={},
        )

        assert result["after_value"]["operation_status"] == "DISABLE"

    def test_tiktok_mock_response_has_success_code(self, tiktok_executor):
        """TikTok mock response should use code=0 for success."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_tiktok_005",
            action_details={"amount": 10},
        )

        assert result["platform_response"]["code"] == 0
        assert result["platform_response"]["message"] == "success"


# =============================================================================
# PLATFORM_EXECUTORS Registry Tests
# =============================================================================


class TestPlatformExecutorsRegistry:
    """Tests for the PLATFORM_EXECUTORS dict."""

    def test_has_meta_executor(self):
        """Registry should contain a 'meta' executor."""
        assert "meta" in PLATFORM_EXECUTORS
        assert isinstance(PLATFORM_EXECUTORS["meta"], MetaExecutor)

    def test_has_google_executor(self):
        """Registry should contain a 'google' executor."""
        assert "google" in PLATFORM_EXECUTORS
        assert isinstance(PLATFORM_EXECUTORS["google"], GoogleExecutor)

    def test_has_tiktok_executor(self):
        """Registry should contain a 'tiktok' executor."""
        assert "tiktok" in PLATFORM_EXECUTORS
        assert isinstance(PLATFORM_EXECUTORS["tiktok"], TikTokExecutor)

    def test_has_snapchat_executor(self):
        """Registry should contain a 'snapchat' executor."""
        assert "snapchat" in PLATFORM_EXECUTORS
        # Snapchat currently uses MetaExecutor
        assert isinstance(PLATFORM_EXECUTORS["snapchat"], PlatformExecutor)

    def test_all_expected_platforms_present(self):
        """Registry should contain all expected platform keys."""
        expected = {"meta", "google", "tiktok", "snapchat"}
        assert set(PLATFORM_EXECUTORS.keys()) == expected

    def test_all_executors_are_platform_executor_subclasses(self):
        """All executors in the registry should be PlatformExecutor instances."""
        for platform, executor in PLATFORM_EXECUTORS.items():
            assert isinstance(
                executor, PlatformExecutor
            ), f"Executor for '{platform}' is not a PlatformExecutor instance"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestExecutorErrorHandling:
    """Tests for graceful error handling in executors."""

    @pytest.mark.asyncio
    async def test_meta_executor_handles_mock_exception_gracefully(self):
        """MetaExecutor should handle exceptions during mock execution."""
        executor = MetaExecutor()

        # Patch _mock_execute to raise an exception
        with patch.object(
            executor, "_mock_execute", side_effect=Exception("Mock failure")
        ):
            with patch("app.tasks.apply_actions_queue.settings") as mock_settings:
                mock_settings.use_mock_ad_data = True

                with pytest.raises(Exception, match="Mock failure"):
                    await executor.execute_action(
                        action_type=ActionType.BUDGET_INCREASE.value,
                        entity_type="campaign",
                        entity_id="camp_001",
                        action_details={"amount": 100},
                    )

    @pytest.mark.asyncio
    async def test_google_executor_handles_mock_exception_gracefully(self):
        """GoogleExecutor should handle exceptions during mock execution."""
        executor = GoogleExecutor()

        with patch.object(
            executor, "_mock_execute", side_effect=ValueError("Bad value")
        ):
            with patch("app.tasks.apply_actions_queue.settings") as mock_settings:
                mock_settings.use_mock_ad_data = True

                with pytest.raises(ValueError, match="Bad value"):
                    await executor.execute_action(
                        action_type=ActionType.BUDGET_INCREASE.value,
                        entity_type="campaign",
                        entity_id="camp_001",
                        action_details={"amount": 100},
                    )

    @pytest.mark.asyncio
    async def test_tiktok_executor_handles_mock_exception_gracefully(self):
        """TikTokExecutor should handle exceptions during mock execution."""
        executor = TikTokExecutor()

        with patch.object(
            executor, "_mock_execute", side_effect=RuntimeError("Runtime issue")
        ):
            with patch("app.tasks.apply_actions_queue.settings") as mock_settings:
                mock_settings.use_mock_ad_data = True

                with pytest.raises(RuntimeError, match="Runtime issue"):
                    await executor.execute_action(
                        action_type=ActionType.BUDGET_INCREASE.value,
                        entity_type="campaign",
                        entity_id="camp_001",
                        action_details={"amount": 100},
                    )

    def test_meta_mock_with_missing_amount_defaults_to_zero(self, meta_executor):
        """Missing 'amount' in action_details should default to 0."""
        result = meta_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_001",
            action_details={},  # No amount
        )

        assert result["success"] is True
        assert (
            result["after_value"]["daily_budget"]
            == result["before_value"]["daily_budget"]
        )

    def test_google_mock_with_missing_amount_defaults_to_zero(self, google_executor):
        """Missing 'amount' in action_details should default to 0."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_001",
            action_details={},
        )

        assert result["success"] is True
        assert (
            result["after_value"]["budget_micros"]
            == result["before_value"]["budget_micros"]
        )

    def test_tiktok_mock_with_missing_amount_defaults_to_zero(self, tiktok_executor):
        """Missing 'amount' in action_details should default to 0."""
        result = tiktok_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_001",
            action_details={},
        )

        assert result["success"] is True
        assert result["after_value"]["budget"] == result["before_value"]["budget"]

    def test_unknown_action_type_does_not_crash_meta(self, meta_executor):
        """Unknown action types should not crash MetaExecutor mock."""
        result = meta_executor._mock_execute(
            action_type="unknown_action",
            entity_type="campaign",
            entity_id="camp_001",
            action_details={},
        )

        # Should still return a valid result dict (no change applied)
        assert result["success"] is True
        assert set(result.keys()) == EXPECTED_RESULT_KEYS


# =============================================================================
# Live Execution Tests (_live_execute via respx-mocked httpx routes)
# =============================================================================

META_BASE = "https://graph.facebook.com/v25.0"
GOOGLE_BASE = "https://googleads.googleapis.com/v18"
GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/token"
TIKTOK_BASE = "https://business-api.tiktok.com/open_api/v1.3"
SNAP_BASE = "https://adsapi.snapchat.com/v1"


def assert_result_contract(result: Dict[str, Any]) -> None:
    """Every executor must return the standardized result dict shape."""
    assert set(result.keys()) == EXPECTED_RESULT_KEYS


@pytest.fixture
def meta_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Meta Graph API credentials on settings."""
    monkeypatch.setattr(settings, "meta_access_token", "meta-token")
    monkeypatch.setattr(settings, "meta_api_version", "v25.0")


@pytest.fixture
def google_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Google Ads credentials on settings."""
    monkeypatch.setattr(settings, "google_ads_developer_token", "dev-tok")
    monkeypatch.setattr(settings, "google_ads_client_id", "client-id")
    monkeypatch.setattr(settings, "google_ads_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_ads_refresh_token", "refresh-tok")
    monkeypatch.setattr(settings, "google_ads_customer_id", "123-456-7890")


@pytest.fixture
def tiktok_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure TikTok Business API credentials on settings."""
    monkeypatch.setattr(settings, "tiktok_access_token", "tt-token")
    monkeypatch.setattr(settings, "tiktok_advertiser_id", "adv-1")


@pytest.fixture
def snap_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Snapchat Marketing API credentials on settings."""
    monkeypatch.setattr(settings, "snapchat_access_token", "snap-token")


def _mock_google_oauth() -> respx.Route:
    """Register a successful Google OAuth token-refresh route."""
    return respx.post(GOOGLE_OAUTH_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "g-access"})
    )


class TestMetaExecutorLive:
    """MetaExecutor._live_execute against a respx-mocked Graph API."""

    async def test_missing_access_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configured token short-circuits before any HTTP call."""
        monkeypatch.setattr(settings, "meta_access_token", None)
        result = await MetaExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 10}
        )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Meta access token is not configured"
        assert result["before_value"] is None
        assert result["platform_response"] is None

    async def test_get_entity_failure(self, meta_creds: None) -> None:
        """A non-200 on the before-read aborts without mutating anything."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(400, text="bad token")
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Failed to fetch entity state: HTTP 400"
        assert result["platform_response"] == {"status_code": 400, "body": "bad token"}
        assert result["before_value"] is None

    async def test_budget_increase_success(self, meta_creds: None) -> None:
        """GET before -> POST cents delta -> GET after; $10 becomes 1000 cents."""
        with respx.mock:
            get_route = respx.get(f"{META_BASE}/c1").mock(
                side_effect=[
                    httpx.Response(
                        200, json={"status": "ACTIVE", "daily_budget": "5000"}
                    ),
                    httpx.Response(
                        200, json={"status": "ACTIVE", "daily_budget": "6000"}
                    ),
                ]
            )
            post_route = respx.post(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            result = await MetaExecutor()._live_execute(
                "budget_increase", "campaign", "c1", {"amount": 10}
            )
        assert_result_contract(result)
        assert result["success"] is True
        assert result["before_value"] == {"status": "ACTIVE", "daily_budget": "5000"}
        assert result["after_value"] == {"status": "ACTIVE", "daily_budget": "6000"}
        assert result["platform_response"] == {"success": True}
        assert result["error"] is None
        body = post_route.calls.last.request.content.decode()
        assert "daily_budget=6000" in body
        assert get_route.call_count == 2

    async def test_budget_decrease_floors_at_zero(self, meta_creds: None) -> None:
        """A decrease larger than the current budget clamps at 0 cents."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                side_effect=[
                    httpx.Response(
                        200, json={"status": "ACTIVE", "daily_budget": "500"}
                    ),
                    httpx.Response(200, json={"status": "ACTIVE", "daily_budget": "0"}),
                ]
            )
            post_route = respx.post(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            result = await MetaExecutor()._live_execute(
                "budget_decrease", "campaign", "c1", {"amount": 10}
            )
        assert result["success"] is True
        assert "daily_budget=0" in post_route.calls.last.request.content.decode()

    async def test_pause_campaign(self, meta_creds: None) -> None:
        """Pause actions POST status=PAUSED."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                side_effect=[
                    httpx.Response(200, json={"status": "ACTIVE"}),
                    httpx.Response(200, json={"status": "PAUSED"}),
                ]
            )
            post_route = respx.post(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["after_value"] == {"status": "PAUSED"}
        assert "status=PAUSED" in post_route.calls.last.request.content.decode()

    async def test_enable_adset(self, meta_creds: None) -> None:
        """Enable actions POST status=ACTIVE."""
        with respx.mock:
            respx.get(f"{META_BASE}/as1").mock(
                side_effect=[
                    httpx.Response(200, json={"status": "PAUSED"}),
                    httpx.Response(200, json={"status": "ACTIVE"}),
                ]
            )
            post_route = respx.post(f"{META_BASE}/as1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            result = await MetaExecutor()._live_execute(
                "enable_adset", "adset", "as1", {}
            )
        assert result["success"] is True
        assert result["after_value"] == {"status": "ACTIVE"}
        assert "status=ACTIVE" in post_route.calls.last.request.content.decode()

    async def test_unsupported_action_type(self, meta_creds: None) -> None:
        """Bid actions are not supported; before_value is still captured."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"status": "ACTIVE"})
            )
            result = await MetaExecutor()._live_execute(
                "bid_increase", "campaign", "c1", {"amount": 1}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Unsupported action type for Meta: bid_increase"
        assert result["before_value"] == {"status": "ACTIVE"}

    async def test_post_update_failure(self, meta_creds: None) -> None:
        """A non-200 on the update POST surfaces status code and body."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"status": "ACTIVE"})
            )
            respx.post(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(500, text="server error")
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is False
        assert result["error"] == "Failed to update entity: HTTP 500"
        assert result["platform_response"] == {
            "status_code": 500,
            "body": "server error",
        }
        assert result["before_value"] == {"status": "ACTIVE"}
        assert result["after_value"] is None

    async def test_after_get_failure_falls_back_to_payload(
        self, meta_creds: None
    ) -> None:
        """When the post-update GET fails, after_value falls back to the
        update payload with the ``access_token`` stripped.

        The token must never appear in after_value: it is persisted to
        ``fact_actions_queue.after_value`` and served by the actions API
        (#522).
        """
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                side_effect=[
                    httpx.Response(200, json={"status": "ACTIVE"}),
                    httpx.Response(500, text="flaky"),
                ]
            )
            respx.post(f"{META_BASE}/c1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["after_value"] == {"status": "PAUSED"}
        assert "access_token" not in result["after_value"]

    async def test_builtin_connection_error_returns_error_dict(
        self, meta_creds: None
    ) -> None:
        """Builtin ConnectionError (an OSError) is caught and reported."""
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                side_effect=ConnectionError("connection refused")
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "connection refused"

    async def test_httpx_transport_error_returns_error_dict(
        self, meta_creds: None
    ) -> None:
        """httpx transport errors are caught and reported as an error dict.

        ``httpx.HTTPError`` inherits from Exception (not OSError), so it
        must be listed explicitly in the executor's except clause — a real
        network failure fails the one action instead of crashing the whole
        sweep iteration (#522).
        """
        with respx.mock:
            respx.get(f"{META_BASE}/c1").mock(
                side_effect=httpx.ConnectError("dns failure")
            )
            result = await MetaExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "dns failure"


class TestGoogleAccessToken:
    """GoogleExecutor._get_access_token OAuth refresh helper."""

    async def test_no_refresh_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No refresh token means no refresh attempt."""
        monkeypatch.setattr(settings, "google_ads_refresh_token", None)
        assert await GoogleExecutor()._get_access_token() is None

    async def test_missing_client_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Refresh token without client ID/secret cannot refresh."""
        monkeypatch.setattr(settings, "google_ads_refresh_token", "refresh-tok")
        monkeypatch.setattr(settings, "google_ads_client_id", None)
        monkeypatch.setattr(settings, "google_ads_client_secret", None)
        assert await GoogleExecutor()._get_access_token() is None

    async def test_refresh_success(self, google_creds: None) -> None:
        """A 200 from the token endpoint yields the access token."""
        with respx.mock:
            route = _mock_google_oauth()
            token = await GoogleExecutor()._get_access_token()
        assert token == "g-access"
        body = route.calls.last.request.content.decode()
        assert "grant_type=refresh_token" in body
        assert "refresh_token=refresh-tok" in body

    async def test_refresh_http_error(self, google_creds: None) -> None:
        """A non-200 from the token endpoint yields None."""
        with respx.mock:
            respx.post(GOOGLE_OAUTH_URL).mock(
                return_value=httpx.Response(400, json={"error": "invalid_grant"})
            )
            assert await GoogleExecutor()._get_access_token() is None

    async def test_refresh_network_error(self, google_creds: None) -> None:
        """A connection failure during refresh yields None."""
        with respx.mock:
            respx.post(GOOGLE_OAUTH_URL).mock(
                side_effect=ConnectionError("no route to host")
            )
            assert await GoogleExecutor()._get_access_token() is None


class TestGoogleExecutorLive:
    """GoogleExecutor._live_execute against a respx-mocked Google Ads REST API."""

    async def test_missing_developer_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No developer token short-circuits before any HTTP call."""
        monkeypatch.setattr(settings, "google_ads_developer_token", None)
        result = await GoogleExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 10}
        )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Google Ads developer token is not configured"

    async def test_access_token_refresh_failure(
        self, google_creds: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed OAuth refresh aborts execution."""
        monkeypatch.setattr(settings, "google_ads_refresh_token", None)
        result = await GoogleExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 10}
        )
        assert result["success"] is False
        assert result["error"] == "Failed to obtain Google Ads access token"

    async def test_missing_customer_id(
        self, google_creds: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No customer ID in settings or action_details aborts execution."""
        monkeypatch.setattr(settings, "google_ads_customer_id", None)
        with respx.mock:
            _mock_google_oauth()
            result = await GoogleExecutor()._live_execute(
                "budget_increase", "campaign", "c1", {"amount": 10}
            )
        assert result["success"] is False
        assert result["error"] == "Google Ads customer ID is not configured"

    async def test_budget_increase_success(self, google_creds: None) -> None:
        """Reads current micros via GAQL searchStream, PATCHes the budget.

        Also proves the hyphenated settings customer ID is stripped to plain
        digits in the API URLs.
        """
        with respx.mock:
            _mock_google_oauth()
            respx.post(
                f"{GOOGLE_BASE}/customers/1234567890/googleAds:searchStream"
            ).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        {"results": [{"campaignBudget": {"amountMicros": "5000000"}}]}
                    ],
                )
            )
            patch_route = respx.patch(
                f"{GOOGLE_BASE}/customers/1234567890/campaignBudgets/b1"
            ).mock(
                return_value=httpx.Response(
                    200,
                    json={"resourceName": "customers/1234567890/campaignBudgets/b1"},
                )
            )
            result = await GoogleExecutor()._live_execute(
                "budget_increase", "campaign", "b1", {"amount": 10}
            )
        assert_result_contract(result)
        assert result["success"] is True
        assert result["before_value"] == {"budget_micros": 5000000}
        assert result["after_value"] == {"budget_micros": 15000000}
        assert result["error"] is None
        request = patch_route.calls.last.request
        assert json.loads(request.content) == {"amount_micros": "15000000"}
        assert "updateMask=amount_micros" in str(request.url)

    async def test_budget_decrease_with_search_failure(
        self, google_creds: None
    ) -> None:
        """A failed GAQL read leaves before_value at 0 but still proceeds."""
        with respx.mock:
            _mock_google_oauth()
            respx.post(
                f"{GOOGLE_BASE}/customers/1234567890/googleAds:searchStream"
            ).mock(return_value=httpx.Response(403, text="denied"))
            patch_route = respx.patch(
                f"{GOOGLE_BASE}/customers/1234567890/campaignBudgets/b1"
            ).mock(return_value=httpx.Response(200, json={}))
            result = await GoogleExecutor()._live_execute(
                "budget_decrease", "campaign", "b1", {"amount": 10}
            )
        assert result["success"] is True
        assert result["before_value"] == {"budget_micros": 0}
        # max(0, 0 - 10_000_000) floors at zero.
        assert result["after_value"] == {"budget_micros": 0}
        assert json.loads(patch_route.calls.last.request.content) == {
            "amount_micros": "0"
        }

    async def test_budget_patch_failure(self, google_creds: None) -> None:
        """A non-2xx budget PATCH surfaces status code and body."""
        with respx.mock:
            _mock_google_oauth()
            respx.post(
                f"{GOOGLE_BASE}/customers/1234567890/googleAds:searchStream"
            ).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        {"results": [{"campaignBudget": {"amountMicros": "5000000"}}]}
                    ],
                )
            )
            respx.patch(f"{GOOGLE_BASE}/customers/1234567890/campaignBudgets/b1").mock(
                return_value=httpx.Response(400, text="invalid budget")
            )
            result = await GoogleExecutor()._live_execute(
                "budget_increase", "campaign", "b1", {"amount": 10}
            )
        assert result["success"] is False
        assert result["error"] == "Budget update failed: HTTP 400"
        assert result["before_value"] == {"budget_micros": 5000000}
        assert result["platform_response"] == {
            "status_code": 400,
            "body": "invalid budget",
        }

    async def test_pause_campaign_with_empty_patch_body(
        self, google_creds: None
    ) -> None:
        """A 204 empty PATCH response yields the {'status': 'OK'} fallback."""
        with respx.mock:
            _mock_google_oauth()
            patch_route = respx.patch(
                f"{GOOGLE_BASE}/customers/1234567890/campaigns/camp1"
            ).mock(return_value=httpx.Response(204))
            result = await GoogleExecutor()._live_execute(
                "pause_campaign", "campaign", "camp1", {}
            )
        assert_result_contract(result)
        assert result["success"] is True
        assert result["before_value"] == {"status": "ENABLED"}
        assert result["after_value"] == {"status": "PAUSED"}
        assert result["platform_response"] == {"status": "OK"}
        assert json.loads(patch_route.calls.last.request.content) == {
            "status": "PAUSED"
        }

    async def test_enable_campaign_with_customer_id_override(
        self, google_creds: None
    ) -> None:
        """action_details.customer_id wins over settings and is de-hyphenated."""
        with respx.mock:
            _mock_google_oauth()
            respx.patch(f"{GOOGLE_BASE}/customers/555/campaigns/camp1").mock(
                return_value=httpx.Response(200, json={"done": True})
            )
            result = await GoogleExecutor()._live_execute(
                "enable_campaign", "campaign", "camp1", {"customer_id": "55-5"}
            )
        assert result["success"] is True
        assert result["before_value"] == {"status": "PAUSED"}
        assert result["after_value"] == {"status": "ENABLED"}
        assert result["platform_response"] == {"done": True}

    async def test_status_patch_failure(self, google_creds: None) -> None:
        """A non-2xx status PATCH surfaces status code and body."""
        with respx.mock:
            _mock_google_oauth()
            respx.patch(f"{GOOGLE_BASE}/customers/1234567890/campaigns/camp1").mock(
                return_value=httpx.Response(403, text="forbidden")
            )
            result = await GoogleExecutor()._live_execute(
                "pause_campaign", "campaign", "camp1", {}
            )
        assert result["success"] is False
        assert result["error"] == "Status update failed: HTTP 403"
        assert result["platform_response"] == {
            "status_code": 403,
            "body": "forbidden",
        }

    async def test_unsupported_action_type(self, google_creds: None) -> None:
        """Bid actions are not supported by the Google executor."""
        with respx.mock:
            _mock_google_oauth()
            result = await GoogleExecutor()._live_execute(
                "bid_increase", "campaign", "c1", {"amount": 1}
            )
        assert result["success"] is False
        assert result["error"] == "Unsupported action type for Google: bid_increase"

    async def test_network_error_returns_error_dict(self, google_creds: None) -> None:
        """Builtin connection errors inside the client are caught."""
        with respx.mock:
            _mock_google_oauth()
            respx.post(
                f"{GOOGLE_BASE}/customers/1234567890/googleAds:searchStream"
            ).mock(side_effect=ConnectionError("reset by peer"))
            result = await GoogleExecutor()._live_execute(
                "budget_increase", "campaign", "b1", {"amount": 10}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "reset by peer"


class TestTikTokExecutorLive:
    """TikTokExecutor._live_execute against a respx-mocked TikTok Business API."""

    async def test_missing_access_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configured token short-circuits before any HTTP call."""
        monkeypatch.setattr(settings, "tiktok_access_token", None)
        result = await TikTokExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 10}
        )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "TikTok access token is not configured"

    async def test_missing_advertiser_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No advertiser ID in settings or action_details aborts execution."""
        monkeypatch.setattr(settings, "tiktok_access_token", "tt-token")
        monkeypatch.setattr(settings, "tiktok_advertiser_id", None)
        result = await TikTokExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 10}
        )
        assert result["success"] is False
        assert result["error"] == "TikTok advertiser ID is not configured"

    async def test_budget_increase_success(self, tiktok_creds: None) -> None:
        """Reads current budget via campaign/get, POSTs the new absolute budget."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "list": [{"operation_status": "ENABLE", "budget": 100.0}]
                        },
                    },
                )
            )
            post_route = respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(
                    200, json={"code": 0, "message": "OK", "data": {}}
                )
            )
            result = await TikTokExecutor()._live_execute(
                "budget_increase", "campaign", "c1", {"amount": 50}
            )
        assert_result_contract(result)
        assert result["success"] is True
        assert result["before_value"] == {
            "operation_status": "ENABLE",
            "budget": 100.0,
        }
        assert result["after_value"]["budget"] == 150.0
        assert result["error"] is None
        payload = json.loads(post_route.calls.last.request.content)
        assert payload == {
            "advertiser_id": "adv-1",
            "campaign_id": "c1",
            "budget": 150.0,
        }
        assert post_route.calls.last.request.headers["Access-Token"] == "tt-token"

    async def test_budget_decrease_floors_at_zero(self, tiktok_creds: None) -> None:
        """A decrease larger than the current budget clamps at 0."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "list": [{"operation_status": "ENABLE", "budget": 10.0}]
                        },
                    },
                )
            )
            post_route = respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "budget_decrease", "campaign", "c1", {"amount": 50}
            )
        assert result["success"] is True
        assert result["after_value"]["budget"] == 0
        assert json.loads(post_route.calls.last.request.content)["budget"] == 0

    async def test_info_fetch_failure_uses_default_before_value(
        self, tiktok_creds: None
    ) -> None:
        """A failed campaign/get read falls back to a zero-budget baseline."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(500, text="oops")
            )
            respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "budget_increase", "campaign", "c1", {"amount": 25}
            )
        assert result["success"] is True
        assert result["before_value"] == {"operation_status": "ENABLE", "budget": 0}
        assert result["after_value"]["budget"] == 25.0

    async def test_info_error_code_uses_default_before_value(
        self, tiktok_creds: None
    ) -> None:
        """A non-zero API code on campaign/get also falls back to defaults."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(
                    200, json={"code": 40001, "message": "no permission"}
                )
            )
            respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["before_value"] == {"operation_status": "ENABLE", "budget": 0}

    async def test_pause_campaign_sets_disable(self, tiktok_creds: None) -> None:
        """Pause maps to operation_status=DISABLE."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "list": [{"operation_status": "ENABLE", "budget": 100.0}]
                        },
                    },
                )
            )
            post_route = respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["after_value"]["operation_status"] == "DISABLE"
        payload = json.loads(post_route.calls.last.request.content)
        assert payload["operation_status"] == "DISABLE"

    async def test_enable_adset_sets_enable(self, tiktok_creds: None) -> None:
        """Enable maps to operation_status=ENABLE."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "list": [{"operation_status": "DISABLE", "budget": 100.0}]
                        },
                    },
                )
            )
            post_route = respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "enable_adset", "adset", "ag1", {}
            )
        assert result["success"] is True
        assert result["before_value"]["operation_status"] == "DISABLE"
        assert result["after_value"]["operation_status"] == "ENABLE"
        payload = json.loads(post_route.calls.last.request.content)
        assert payload["operation_status"] == "ENABLE"

    async def test_unsupported_action_type(self, tiktok_creds: None) -> None:
        """Bid actions are not supported; before_value defaults are kept."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
            )
            result = await TikTokExecutor()._live_execute(
                "bid_increase", "campaign", "c1", {"amount": 1}
            )
        assert result["success"] is False
        assert result["error"] == "Unsupported action type for TikTok: bid_increase"
        assert result["before_value"] == {"operation_status": "ENABLE", "budget": 0}

    async def test_update_api_error_code(self, tiktok_creds: None) -> None:
        """TikTok signals failure with a 200 + non-zero body code."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
            )
            respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(
                    200, json={"code": 40100, "message": "Insufficient permissions"}
                )
            )
            result = await TikTokExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is False
        assert result["error"] == "Insufficient permissions"
        assert result["platform_response"]["code"] == 40100
        assert result["after_value"] is None

    async def test_advertiser_id_from_action_details(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """action_details.advertiser_id wins when settings has none."""
        monkeypatch.setattr(settings, "tiktok_access_token", "tt-token")
        monkeypatch.setattr(settings, "tiktok_advertiser_id", None)
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
            )
            post_route = respx.post(f"{TIKTOK_BASE}/campaign/update/").mock(
                return_value=httpx.Response(200, json={"code": 0, "message": "OK"})
            )
            result = await TikTokExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {"advertiser_id": "adv-9"}
            )
        assert result["success"] is True
        payload = json.loads(post_route.calls.last.request.content)
        assert payload["advertiser_id"] == "adv-9"

    async def test_network_error_returns_error_dict(self, tiktok_creds: None) -> None:
        """Builtin connection errors inside the client are caught."""
        with respx.mock:
            respx.get(f"{TIKTOK_BASE}/campaign/get/").mock(
                side_effect=ConnectionError("timed out")
            )
            result = await TikTokExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "timed out"


def _snap_campaign_body(**entity: Any) -> Dict[str, Any]:
    """Snapchat wraps entities: {'campaigns': [{'campaign': {...}}]}."""
    return {"campaigns": [{"campaign": entity}]}


class TestSnapchatExecutorLive:
    """SnapchatExecutor._live_execute against a respx-mocked Marketing API."""

    async def test_missing_access_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configured token short-circuits before any HTTP call."""
        monkeypatch.setattr(settings, "snapchat_access_token", None)
        result = await SnapchatExecutor()._live_execute(
            "budget_increase", "campaign", "c1", {"amount": 5}
        )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Snapchat access token is not configured"

    async def test_get_entity_failure(self, snap_creds: None) -> None:
        """A non-200 on the before-read aborts without mutating anything."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(404, text="not found")
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is False
        assert result["error"] == "Failed to fetch entity state: HTTP 404"
        assert result["platform_response"] == {"status_code": 404, "body": "not found"}

    async def test_budget_increase_success(self, snap_creds: None) -> None:
        """GET before -> PUT full entity with micro-currency budget delta."""
        with respx.mock:
            get_route = respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        id="c1", status="ACTIVE", daily_budget_micro=10_000_000
                    ),
                )
            )
            put_route = respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "budget_increase", "campaign", "c1", {"amount": 5}
            )
        assert_result_contract(result)
        assert result["success"] is True
        assert result["before_value"] == {
            "status": "ACTIVE",
            "daily_budget_micro": 10_000_000,
        }
        assert result["after_value"] == {
            "status": "ACTIVE",
            "daily_budget_micro": 15_000_000,
        }
        assert result["platform_response"] == {"request_status": "SUCCESS"}
        auth = get_route.calls.last.request.headers["Authorization"]
        assert auth == "Bearer snap-token"
        put_body = json.loads(put_route.calls.last.request.content)
        assert put_body["campaigns"][0]["campaign"]["daily_budget_micro"] == 15_000_000

    async def test_budget_decrease_floors_at_zero(self, snap_creds: None) -> None:
        """A decrease larger than the current budget clamps at 0 micro."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        status="ACTIVE", daily_budget_micro=2_000_000
                    ),
                )
            )
            respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "budget_decrease", "campaign", "c1", {"amount": 5}
            )
        assert result["success"] is True
        assert result["after_value"]["daily_budget_micro"] == 0

    async def test_pause_campaign(self, snap_creds: None) -> None:
        """Pause PUTs status=PAUSED on the full entity payload."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        status="ACTIVE", daily_budget_micro=1_000_000
                    ),
                )
            )
            put_route = respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["before_value"]["status"] == "ACTIVE"
        assert result["after_value"]["status"] == "PAUSED"
        put_body = json.loads(put_route.calls.last.request.content)
        assert put_body["campaigns"][0]["campaign"]["status"] == "PAUSED"

    async def test_enable_adset_uses_adsquads_resource(self, snap_creds: None) -> None:
        """entity_type adset maps onto the /adsquads resource path."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/adsquads/as1").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "adsquads": [
                            {
                                "adsquad": {
                                    "status": "PAUSED",
                                    "daily_budget_micro": 1_000_000,
                                }
                            }
                        ]
                    },
                )
            )
            put_route = respx.put(f"{SNAP_BASE}/adsquads/as1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "enable_adset", "adset", "as1", {}
            )
        assert result["success"] is True
        assert result["before_value"]["status"] == "PAUSED"
        assert result["after_value"]["status"] == "ACTIVE"
        put_body = json.loads(put_route.calls.last.request.content)
        assert put_body["adsquads"][0]["adsquad"]["status"] == "ACTIVE"

    async def test_unknown_entity_type_falls_back_to_campaigns(
        self, snap_creds: None
    ) -> None:
        """Unmapped entity types default to the /campaigns resource."""
        with respx.mock:
            get_route = respx.get(f"{SNAP_BASE}/campaigns/x1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        status="ACTIVE", daily_budget_micro=1_000_000
                    ),
                )
            )
            respx.put(f"{SNAP_BASE}/campaigns/x1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "creative", "x1", {}
            )
        assert result["success"] is True
        assert get_route.called

    async def test_put_update_failure(self, snap_creds: None) -> None:
        """A non-200 PUT surfaces the raw body and an HTTP error message."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        status="ACTIVE", daily_budget_micro=1_000_000
                    ),
                )
            )
            respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(400, text="invalid payload")
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is False
        assert result["error"] == "Failed to update entity: HTTP 400"
        assert result["platform_response"] == {"body": "invalid payload"}
        assert result["after_value"] is None

    async def test_empty_entity_list_defaults(self, snap_creds: None) -> None:
        """An empty wrapper list produces a None-status baseline."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"campaigns": []})
            )
            respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert result["success"] is True
        assert result["before_value"] == {"status": None, "daily_budget_micro": 0}
        assert result["after_value"]["status"] == "PAUSED"

    async def test_unsupported_action_returns_error_without_put(
        self, snap_creds: None
    ) -> None:
        """Unknown action types return the standard error dict before any
        PUT is made, matching the Meta/Google/TikTok guard (#522).
        """
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(
                    200,
                    json=_snap_campaign_body(
                        status="ACTIVE", daily_budget_micro=1_000_000
                    ),
                )
            )
            put_route = respx.put(f"{SNAP_BASE}/campaigns/c1").mock(
                return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
            )
            result = await SnapchatExecutor()._live_execute(
                "bid_increase", "campaign", "c1", {"amount": 1}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "Unsupported action type for Snapchat: bid_increase"
        assert result["before_value"] == {
            "status": "ACTIVE",
            "daily_budget_micro": 1_000_000,
        }
        assert result["after_value"] is None
        assert not put_route.called

    async def test_network_error_returns_error_dict(self, snap_creds: None) -> None:
        """Builtin connection errors inside the client are caught."""
        with respx.mock:
            respx.get(f"{SNAP_BASE}/campaigns/c1").mock(
                side_effect=ConnectionError("broken pipe")
            )
            result = await SnapchatExecutor()._live_execute(
                "pause_campaign", "campaign", "c1", {}
            )
        assert_result_contract(result)
        assert result["success"] is False
        assert result["error"] == "broken pipe"
