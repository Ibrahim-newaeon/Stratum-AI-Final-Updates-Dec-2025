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
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.apply_actions_queue import (
    GoogleExecutor,
    MetaExecutor,
    PLATFORM_EXECUTORS,
    PlatformExecutor,
    TikTokExecutor,
)
from app.autopilot.service import ActionType


# =============================================================================
# Expected Result Keys
# =============================================================================

EXPECTED_RESULT_KEYS = {"success", "before_value", "after_value", "platform_response", "error"}


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

            def _mock_execute(self, action_type, entity_type, entity_id, action_details):
                self.mock_called = True
                return {"success": True, "before_value": None, "after_value": None, "platform_response": None, "error": None}

            async def _live_execute(self, action_type, entity_type, entity_id, action_details):
                self.live_called = True
                return {"success": True, "before_value": None, "after_value": None, "platform_response": None, "error": None}

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

        assert result["before_value"]["daily_budget"] == result["after_value"]["daily_budget"]


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
            assert isinstance(executor, PlatformExecutor), (
                f"Executor for '{platform}' is not a PlatformExecutor instance"
            )


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
        with patch.object(executor, "_mock_execute", side_effect=Exception("Mock failure")):
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

        with patch.object(executor, "_mock_execute", side_effect=ValueError("Bad value")):
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

        with patch.object(executor, "_mock_execute", side_effect=RuntimeError("Runtime issue")):
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
        assert result["after_value"]["daily_budget"] == result["before_value"]["daily_budget"]

    def test_google_mock_with_missing_amount_defaults_to_zero(self, google_executor):
        """Missing 'amount' in action_details should default to 0."""
        result = google_executor._mock_execute(
            action_type=ActionType.BUDGET_INCREASE.value,
            entity_type="campaign",
            entity_id="camp_001",
            action_details={},
        )

        assert result["success"] is True
        assert result["after_value"]["budget_micros"] == result["before_value"]["budget_micros"]

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
