# =============================================================================
# Stratum AI - Base Adapter Deep Integration Tests
# =============================================================================
"""Deep coverage tests for ``app.stratum.adapters.base`` (#342 Batch 5+6).

Covers the shared adapter contract directly via a minimal concrete subclass:

- ``RateLimiter``: construction, token consumption, token regeneration with
  burst cap, and the exhausted-bucket wait branch (``asyncio.sleep`` mocked).
- ``BaseAdapter.__init__`` state (credentials, default rate limiter).
- ``health_check`` success / empty-account / exception branches.
- ``execute_actions_batch`` sequential fan-out.
- Default ``setup_webhooks`` / ``process_webhook`` implementations.
- ``_map_status_*`` NotImplementedError contract.
- Exception hierarchy including ``PlatformError.platform_code``.

No database access is required: the base adapter never persists rows.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    BaseAdapter,
    PlatformError,
    RateLimiter,
    RateLimitError,
    ValidationError,
)
from app.stratum.models import (
    AutomationAction,
    EMQScore,
    EntityStatus,
    PerformanceMetrics,
    Platform,
    UnifiedAccount,
    UnifiedAd,
    UnifiedAdSet,
    UnifiedCampaign,
    WebhookEvent,
)

# NOTE: no module-level asyncio mark — asyncio_mode=auto picks up async tests,
# and marking sync tests (helpers/exceptions) emits PytestWarning noise.
pytestmark = [pytest.mark.integration]


class DummyAdapter(BaseAdapter):
    """Minimal concrete adapter used to exercise BaseAdapter's own code."""

    def __init__(
        self,
        credentials: dict[str, str],
        accounts: Optional[list[UnifiedAccount]] = None,
        accounts_error: Optional[Exception] = None,
    ):
        super().__init__(credentials)
        self._accounts = accounts or []
        self._accounts_error = accounts_error
        self.executed: list[AutomationAction] = []

    @property
    def platform(self) -> Platform:
        return Platform.META

    async def initialize(self) -> None:
        self._initialized = True

    async def cleanup(self) -> None:
        self._initialized = False

    async def get_accounts(self) -> list[UnifiedAccount]:
        if self._accounts_error is not None:
            raise self._accounts_error
        return self._accounts

    async def get_campaigns(
        self, account_id: str, status_filter: Optional[list[EntityStatus]] = None
    ) -> list[UnifiedCampaign]:
        return []

    async def get_adsets(
        self, account_id: str, campaign_id: Optional[str] = None
    ) -> list[UnifiedAdSet]:
        return []

    async def get_ads(
        self, account_id: str, adset_id: Optional[str] = None
    ) -> list[UnifiedAd]:
        return []

    async def get_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        date_start: datetime,
        date_end: datetime,
        breakdown: Optional[str] = None,
    ) -> dict[str, PerformanceMetrics]:
        return {}

    async def get_emq_scores(self, account_id: str) -> list[EMQScore]:
        return []

    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        action.status = "completed"
        self.executed.append(action)
        return action

    async def upload_image(
        self, account_id: str, image_data: bytes, filename: str
    ) -> str:
        return "img-1"

    async def upload_video(
        self, account_id: str, video_data: bytes, filename: str
    ) -> str:
        return "vid-1"


def _account(account_id: str = "act_1") -> UnifiedAccount:
    return UnifiedAccount(
        platform=Platform.META, account_id=account_id, account_name="Acct"
    )


def _action(action_type: str = "update_budget") -> AutomationAction:
    return AutomationAction(
        platform=Platform.META,
        account_id="act_1",
        entity_type="campaign",
        entity_id="c1",
        action_type=action_type,
    )


# =============================================================================
# RateLimiter
# =============================================================================


class TestRateLimiter:
    def test_init_defaults(self):
        rl = RateLimiter()
        assert rl.calls_per_minute == 60
        assert rl.burst_size == 10
        assert rl.tokens == 10.0
        assert rl.last_update.tzinfo is not None

    def test_init_custom(self):
        rl = RateLimiter(calls_per_minute=120, burst_size=5)
        assert rl.calls_per_minute == 120
        assert rl.burst_size == 5
        assert rl.tokens == 5.0

    async def test_acquire_consumes_token(self):
        rl = RateLimiter(calls_per_minute=60, burst_size=10)
        await rl.acquire()
        # One token consumed (a tiny amount may regenerate between init/acquire)
        assert 8.9 < rl.tokens < 9.1

    async def test_acquire_regenerates_tokens_capped_at_burst(self):
        rl = RateLimiter(calls_per_minute=60, burst_size=10)
        rl.tokens = 0.0
        # 60 seconds elapsed at 60/min would regenerate 60 tokens -> cap at 10
        rl.last_update = datetime.now(UTC) - timedelta(seconds=60)
        await rl.acquire()
        assert 8.9 < rl.tokens < 9.1  # capped at 10, minus 1 consumed

    async def test_acquire_waits_when_exhausted(self):
        rl = RateLimiter(calls_per_minute=60, burst_size=10)
        rl.tokens = 0.0
        rl.last_update = datetime.now(UTC)
        with patch(
            "app.stratum.adapters.base.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await rl.acquire()
        mock_sleep.assert_awaited_once()
        wait_time = mock_sleep.await_args.args[0]
        # ~(1 - 0) * 60 / 60 = ~1 second
        assert 0.9 < wait_time <= 1.0
        # After the wait branch: tokens set to 1, then 1 consumed
        assert rl.tokens == 0


# =============================================================================
# BaseAdapter lifecycle + defaults
# =============================================================================


class TestBaseAdapterInit:
    def test_init_state(self):
        creds = {"token": "abc"}
        adapter = DummyAdapter(creds)
        assert adapter.credentials is creds
        assert isinstance(adapter.rate_limiter, RateLimiter)
        assert adapter._initialized is False

    def test_platform_property(self):
        adapter = DummyAdapter({})
        assert adapter.platform == Platform.META

    async def test_initialize_and_cleanup(self):
        adapter = DummyAdapter({})
        await adapter.initialize()
        assert adapter._initialized is True
        await adapter.cleanup()
        assert adapter._initialized is False


class TestHealthCheck:
    async def test_healthy_when_accounts_exist(self):
        adapter = DummyAdapter({}, accounts=[_account()])
        assert await adapter.health_check() is True

    async def test_unhealthy_when_no_accounts(self):
        adapter = DummyAdapter({}, accounts=[])
        assert await adapter.health_check() is False

    @pytest.mark.parametrize(
        "exc",
        [
            ConnectionError("down"),
            TimeoutError("slow"),
            OSError("socket"),
            ValueError("bad"),
            RuntimeError("boom"),
        ],
    )
    async def test_unhealthy_on_exception(self, exc):
        adapter = DummyAdapter({}, accounts_error=exc)
        assert await adapter.health_check() is False


class TestExecuteActionsBatch:
    async def test_batch_executes_all_in_order(self):
        adapter = DummyAdapter({})
        actions = [_action("update_budget"), _action("update_status")]
        results = await adapter.execute_actions_batch(actions)
        assert len(results) == 2
        assert all(a.status == "completed" for a in results)
        assert [a.action_type for a in adapter.executed] == [
            "update_budget",
            "update_status",
        ]

    async def test_batch_empty_list(self):
        adapter = DummyAdapter({})
        assert await adapter.execute_actions_batch([]) == []


class TestWebhookDefaults:
    async def test_setup_webhooks_not_implemented_returns_false(self):
        adapter = DummyAdapter({})
        assert await adapter.setup_webhooks("https://cb.example.com", ["x"]) is False

    async def test_process_webhook_wraps_payload(self):
        adapter = DummyAdapter({})
        payload: dict[str, Any] = {"change": "budget", "id": "c1"}
        event = await adapter.process_webhook(payload)
        assert isinstance(event, WebhookEvent)
        assert event.platform == Platform.META.value
        assert event.event_type == "unknown"
        assert event.payload == payload
        assert event.received_at.tzinfo is not None


class TestStatusMappingContract:
    def test_map_status_to_platform_not_implemented(self):
        adapter = DummyAdapter({})
        with pytest.raises(NotImplementedError):
            adapter._map_status_to_platform(EntityStatus.ACTIVE)

    def test_map_status_from_platform_not_implemented(self):
        adapter = DummyAdapter({})
        with pytest.raises(NotImplementedError):
            adapter._map_status_from_platform("ACTIVE")


# =============================================================================
# Exceptions
# =============================================================================


class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(AuthenticationError, AdapterError)
        assert issubclass(RateLimitError, AdapterError)
        assert issubclass(ValidationError, AdapterError)
        assert issubclass(PlatformError, AdapterError)
        assert issubclass(AdapterError, Exception)

    def test_platform_error_with_code(self):
        err = PlatformError("meta exploded", platform_code="190")
        assert str(err) == "meta exploded"
        assert err.platform_code == "190"

    def test_platform_error_default_code(self):
        err = PlatformError("no code")
        assert err.platform_code is None

    def test_platform_error_is_catchable_as_adapter_error(self):
        with pytest.raises(AdapterError):
            raise PlatformError("x", platform_code="1")
