# =============================================================================
# Stratum AI - TikTok Adapter Deep Integration Tests
# =============================================================================
"""Deep coverage tests for ``app.stratum.adapters.tiktok_adapter``.

The TikTok adapter speaks to TikTok's Business API through a synchronous
``requests.Session`` (NOT httpx), so these tests stub the session boundary
with an in-memory fake instead of respx. Covers: credential validation,
initialize/cleanup lifecycle, account/campaign/adgroup/ad fetch + unified
model mapping, reporting metrics parsing, EMQ estimation, budget/status/create
mutations via ``execute_action``, creative uploads, ``_make_request`` error
mapping, and datetime/status helpers.

Behaviors pinned here (fixed under #540):

* ``execute_action`` catches ``PlatformError`` (an API rejection where
  ``code != 0``) and marks the action ``status="failed"`` with the error
  message, instead of letting it propagate and stick in ``"executing"`` (see
  ``TestExecuteAction.test_platform_error_*``).
* ``_update_budget`` maps an ``adset`` entity to TikTok's native ``adgroup_id``
  payload key (see ``test_update_budget_adset_uses_adgroup_id_key``).
* Passing more than one status in ``status_filter`` applies the first mapped
  status server-side (TikTok's ``primary_status`` is single-valued) rather than
  collapsing to ``null`` and disabling filtering.
"""

from datetime import UTC, datetime

import pytest
import requests

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    PlatformError,
)
from app.stratum.adapters.tiktok_adapter import TikTokAdapter
from app.stratum.models import AutomationAction, EntityStatus, Platform

pytestmark = pytest.mark.integration


# =============================================================================
# Fakes for the requests.Session transport boundary
# =============================================================================


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Queue-driven fake of requests.Session recording every call."""

    def __init__(self, queue=None):
        self.queue = list(queue or [])
        self.calls = []
        self.headers = {}
        self.closed = False

    def _next(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.queue:
            raise AssertionError(f"No queued response for {method} {url}")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def get(self, url, params=None, **kwargs):
        return self._next("GET", url, params=params)

    def post(self, url, json=None, **kwargs):
        return self._next("POST", url, json=json)

    def close(self):
        self.closed = True


CREDS = {
    "app_id": "app-1",
    "secret": "shh",
    "access_token": "tok-123",
    "advertiser_id": "adv-1",
}


def ok(data=None):
    """A code=0 TikTok envelope."""
    return FakeResponse({"code": 0, "message": "OK", "data": data or {}})


def err(code=40001, message="boom"):
    return FakeResponse({"code": code, "message": message})


def make_adapter(queue=None, creds=None):
    """Build an already-initialized adapter with a fake session."""
    adapter = TikTokAdapter(dict(creds or CREDS))
    adapter.session = FakeSession(queue)
    adapter._initialized = True
    return adapter


# =============================================================================
# Construction & lifecycle
# =============================================================================


class TestInitAndLifecycle:
    def test_missing_access_token_raises(self):
        with pytest.raises(ValueError, match="access_token"):
            TikTokAdapter({"app_id": "x"})

    def test_credential_defaults(self):
        adapter = TikTokAdapter({"access_token": "t"})
        assert adapter.app_id == ""
        assert adapter.secret == ""
        assert adapter.default_advertiser_id is None
        assert adapter.session is None

    def test_platform_property(self):
        assert TikTokAdapter(CREDS).platform == Platform.TIKTOK

    async def test_initialize_success(self, monkeypatch):
        fake = FakeSession([ok({"list": [{"advertiser_id": "adv-1"}]})])
        monkeypatch.setattr(
            "app.stratum.adapters.tiktok_adapter.requests.Session", lambda: fake
        )
        adapter = TikTokAdapter(dict(CREDS))
        await adapter.initialize()
        assert adapter._initialized is True
        assert fake.headers["Access-Token"] == "tok-123"
        assert fake.headers["Content-Type"] == "application/json"
        call = fake.calls[0]
        assert call["url"].endswith("/advertiser/info/")
        assert "adv-1" in call["params"]["advertiser_ids"]

    async def test_initialize_bad_token_raises_authentication_error(self, monkeypatch):
        fake = FakeSession([err(40105, "invalid token")])
        monkeypatch.setattr(
            "app.stratum.adapters.tiktok_adapter.requests.Session", lambda: fake
        )
        adapter = TikTokAdapter(dict(CREDS))
        with pytest.raises(AuthenticationError, match="invalid token"):
            await adapter.initialize()
        assert adapter._initialized is False

    async def test_initialize_http_error_becomes_authentication_error(
        self, monkeypatch
    ):
        # raise_for_status -> RequestException -> _make_request maps to
        # {"code": -1} -> AuthenticationError (not a network AdapterError).
        fake = FakeSession([FakeResponse({}, status_code=401)])
        monkeypatch.setattr(
            "app.stratum.adapters.tiktok_adapter.requests.Session", lambda: fake
        )
        adapter = TikTokAdapter(dict(CREDS))
        with pytest.raises(AuthenticationError):
            await adapter.initialize()

    async def test_initialize_without_advertiser_id_warns_and_succeeds(
        self, monkeypatch
    ):
        fake = FakeSession([])
        monkeypatch.setattr(
            "app.stratum.adapters.tiktok_adapter.requests.Session", lambda: fake
        )
        creds = {k: v for k, v in CREDS.items() if k != "advertiser_id"}
        adapter = TikTokAdapter(creds)
        await adapter.initialize()
        assert adapter._initialized is True
        assert fake.calls == []

    async def test_initialize_session_failure_raises_adapter_error(self, monkeypatch):
        def boom():
            raise requests.ConnectionError("no route")

        monkeypatch.setattr(
            "app.stratum.adapters.tiktok_adapter.requests.Session", boom
        )
        adapter = TikTokAdapter(dict(CREDS))
        with pytest.raises(AdapterError, match="Failed to connect"):
            await adapter.initialize()

    async def test_cleanup_closes_session(self):
        adapter = make_adapter([])
        session = adapter.session
        await adapter.cleanup()
        assert session.closed is True
        assert adapter.session is None
        assert adapter._initialized is False

    async def test_cleanup_without_session_is_noop(self):
        adapter = TikTokAdapter(dict(CREDS))
        await adapter.cleanup()
        assert adapter._initialized is False

    async def test_ensure_initialized_guard(self):
        adapter = TikTokAdapter(dict(CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await adapter.get_accounts()


# =============================================================================
# Accounts
# =============================================================================


class TestGetAccounts:
    async def test_no_advertiser_id_returns_empty(self):
        creds = {k: v for k, v in CREDS.items() if k != "advertiser_id"}
        adapter = make_adapter([], creds=creds)
        assert await adapter.get_accounts() == []

    async def test_success_maps_unified_account(self):
        raw = {
            "advertiser_id": 999,
            "name": "Acme TikTok",
            "timezone": "America/New_York",
            "currency": "EUR",
        }
        adapter = make_adapter([ok({"list": [raw]})])
        accounts = await adapter.get_accounts()
        assert len(accounts) == 1
        acc = accounts[0]
        assert acc.platform == Platform.TIKTOK.value
        assert acc.account_id == "999"
        assert acc.account_name == "Acme TikTok"
        assert acc.timezone == "America/New_York"
        assert acc.currency == "EUR"
        assert acc.raw_data == raw
        assert acc.last_synced is not None

    async def test_defaults_for_missing_fields(self):
        adapter = make_adapter([ok({"list": [{}]})])
        acc = (await adapter.get_accounts())[0]
        assert acc.account_name == "Unknown"
        assert acc.timezone == "UTC"
        assert acc.currency == "USD"

    async def test_api_error_raises_platform_error(self):
        adapter = make_adapter([err(message="denied")])
        with pytest.raises(PlatformError, match="denied"):
            await adapter.get_accounts()

    async def test_network_error_raises_platform_error(self):
        # builtin TimeoutError bypasses _make_request's RequestException net.
        adapter = make_adapter([TimeoutError("socket timeout")])
        with pytest.raises(PlatformError, match="Failed to fetch accounts"):
            await adapter.get_accounts()

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([ok({"list": 5})])
        with pytest.raises(PlatformError, match="Failed to parse account data"):
            await adapter.get_accounts()


# =============================================================================
# Campaigns
# =============================================================================


class TestGetCampaigns:
    async def test_success_maps_unified_campaign(self):
        raw = {
            "campaign_id": 111,
            "campaign_name": "Summer Push",
            "operation_status": "DISABLE",
            "budget": 5000,  # cents -> 50.0
            "create_time": "2026-01-15 10:30:00",
            "modify_time": "2026-02-01T08:00:00Z",
        }
        adapter = make_adapter([ok({"list": [raw]})])
        campaigns = await adapter.get_campaigns("adv-1")
        assert len(campaigns) == 1
        c = campaigns[0]
        assert c.campaign_id == "111"
        assert c.campaign_name == "Summer Push"
        assert c.status == EntityStatus.PAUSED.value
        assert c.daily_budget == 50.0
        assert c.created_at == datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        assert c.updated_at == datetime(2026, 2, 1, 8, 0, tzinfo=UTC)
        assert c.raw_data == raw
        params = adapter.session.calls[0]["params"]
        assert params["advertiser_id"] == "adv-1"
        assert params["page_size"] == 100
        assert "filtering" not in params

    async def test_zero_budget_maps_to_none(self):
        raw = {"campaign_id": 1, "campaign_name": "x", "budget": 0}
        adapter = make_adapter([ok({"list": [raw]})])
        c = (await adapter.get_campaigns("adv-1"))[0]
        assert c.daily_budget is None
        assert c.status == EntityStatus.ACTIVE.value  # default ENABLE

    async def test_single_status_filter_sets_primary_status(self):
        adapter = make_adapter([ok({"list": []})])
        await adapter.get_campaigns("adv-1", status_filter=[EntityStatus.PAUSED])
        params = adapter.session.calls[0]["params"]
        assert '"primary_status": "DISABLE"' in params["filtering"]

    async def test_multi_status_filter_applies_first_status(self):
        # FIXED (#540): TikTok's primary_status is single-valued, so a
        # multi-status filter applies the first mapped status server-side
        # (ACTIVE -> "ENABLE") instead of collapsing to null and disabling it.
        adapter = make_adapter([ok({"list": []})])
        await adapter.get_campaigns(
            "adv-1", status_filter=[EntityStatus.ACTIVE, EntityStatus.PAUSED]
        )
        params = adapter.session.calls[0]["params"]
        assert '"primary_status": "ENABLE"' in params["filtering"]

    async def test_api_error_raises_platform_error(self):
        adapter = make_adapter([err(message="no access")])
        with pytest.raises(PlatformError, match="no access"):
            await adapter.get_campaigns("adv-1")

    async def test_parse_error_raises_platform_error(self):
        raw = {"campaign_id": 1, "campaign_name": "x", "budget": "not-a-number"}
        adapter = make_adapter([ok({"list": [raw]})])
        with pytest.raises(PlatformError, match="Failed to parse campaign data"):
            await adapter.get_campaigns("adv-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([ConnectionError("reset")])
        with pytest.raises(PlatformError, match="Failed to fetch campaigns"):
            await adapter.get_campaigns("adv-1")


# =============================================================================
# Ad groups (adsets)
# =============================================================================


class TestGetAdsets:
    async def test_success_maps_unified_adset(self):
        raw = {
            "adgroup_id": 222,
            "adgroup_name": "AG One",
            "campaign_id": 111,
            "operation_status": "ADGROUP_STATUS_DELIVERY_OK",
            "budget": 2500,
            "bid": 150,
        }
        adapter = make_adapter([ok({"list": [raw]})])
        adsets = await adapter.get_adsets("adv-1")
        assert len(adsets) == 1
        a = adsets[0]
        assert a.adset_id == "222"
        assert a.adset_name == "AG One"
        assert a.campaign_id == "111"
        assert a.status == EntityStatus.ACTIVE.value
        assert a.daily_budget == 25.0
        assert a.bid_amount == 1.5
        params = adapter.session.calls[0]["params"]
        assert "filtering" not in params

    async def test_campaign_filter_applied(self):
        adapter = make_adapter([ok({"list": []})])
        await adapter.get_adsets("adv-1", campaign_id="111")
        params = adapter.session.calls[0]["params"]
        assert '"campaign_ids": ["111"]' in params["filtering"]
        assert adapter.session.calls[0]["url"].endswith("/adgroup/get/")

    async def test_api_error_raises_platform_error(self):
        adapter = make_adapter([err()])
        with pytest.raises(PlatformError, match="TikTok API error"):
            await adapter.get_adsets("adv-1")

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([ok({"list": [{"budget": "x"}]})])
        with pytest.raises(PlatformError, match="Failed to parse ad group data"):
            await adapter.get_adsets("adv-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([TimeoutError()])
        with pytest.raises(PlatformError, match="Failed to fetch ad groups"):
            await adapter.get_adsets("adv-1")


# =============================================================================
# Ads
# =============================================================================


class TestGetAds:
    async def test_success_maps_unified_ad(self):
        raw = {
            "ad_id": 333,
            "ad_name": "Video Ad",
            "campaign_id": 111,
            "adgroup_id": 222,
            "operation_status": "ENABLE",
            "ad_text": "Buy now!",
            "landing_page_url": "https://example.com",
            "call_to_action": "SHOP_NOW",
        }
        adapter = make_adapter([ok({"list": [raw]})])
        ads = await adapter.get_ads("adv-1")
        assert len(ads) == 1
        ad = ads[0]
        assert ad.ad_id == "333"
        assert ad.ad_name == "Video Ad"
        assert ad.campaign_id == "111"
        assert ad.adset_id == "222"
        assert ad.status == EntityStatus.ACTIVE.value
        assert ad.headline == "Buy now!"
        assert ad.destination_url == "https://example.com"
        assert ad.call_to_action == "SHOP_NOW"

    async def test_adset_filter_applied(self):
        adapter = make_adapter([ok({"list": []})])
        await adapter.get_ads("adv-1", adset_id="222")
        params = adapter.session.calls[0]["params"]
        assert '"adgroup_ids": ["222"]' in params["filtering"]
        assert adapter.session.calls[0]["url"].endswith("/ad/get/")

    async def test_api_error_raises_platform_error(self):
        adapter = make_adapter([err()])
        with pytest.raises(PlatformError, match="TikTok API error"):
            await adapter.get_ads("adv-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([OSError("io")])
        with pytest.raises(PlatformError, match="Failed to fetch ads"):
            await adapter.get_ads("adv-1")

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([ok({"list": 5})])
        with pytest.raises(PlatformError, match="Failed to parse ad data"):
            await adapter.get_ads("adv-1")


# =============================================================================
# Metrics / reporting
# =============================================================================

DATE_START = datetime(2026, 6, 1, tzinfo=UTC)
DATE_END = datetime(2026, 6, 30, tzinfo=UTC)


def report_row(dim_key, dim_val, metrics):
    return {"dimensions": {dim_key: dim_val}, "metrics": metrics}


class TestGetMetrics:
    async def test_campaign_metrics_full_parse(self):
        row = report_row(
            "campaign_id",
            111,
            {
                "impressions": "1000",
                "clicks": "50",
                "spend": "123.45",
                "ctr": "5.0",
                "cpc": "2.47",
                "cpm": "12.3",
                "conversion": "10",
                "cost_per_conversion": "12.35",
                "video_play_actions": "800",
            },
        )
        adapter = make_adapter([ok({"list": [row]})])
        result = await adapter.get_metrics(
            "adv-1", "campaign", ["111"], DATE_START, DATE_END
        )
        assert set(result) == {"111"}
        m = result["111"]
        assert m.impressions == 1000
        assert m.clicks == 50
        assert m.spend == 123.45
        assert m.ctr == 5.0
        assert m.cpc == 2.47
        assert m.cpm == 12.3
        assert m.conversions == 10
        assert m.cpa == 12.35
        assert m.video_views == 800
        assert m.date_start == DATE_START and m.date_end == DATE_END

        params = adapter.session.calls[0]["params"]
        assert params["data_level"] == "AUCTION_CAMPAIGN"
        assert params["dimensions"] == '["campaign_id"]'
        assert '"campaign_ids": ["111"]' in params["filtering"]
        assert params["start_date"] == "2026-06-01"
        assert params["end_date"] == "2026-06-30"

    async def test_derived_metrics_computed_when_absent(self):
        row = report_row(
            "campaign_id",
            111,
            {"impressions": "1000", "clicks": "50", "spend": "100"},
        )
        adapter = make_adapter([ok({"list": [row]})])
        m = (await adapter.get_metrics("adv-1", "campaign", [], DATE_START, DATE_END))[
            "111"
        ]
        assert m.ctr == pytest.approx(5.0)
        assert m.cpc == pytest.approx(2.0)
        assert m.cpm == pytest.approx(100.0)
        assert m.conversions is None
        assert m.cpa is None
        assert m.video_views is None
        # No entity_ids -> no filtering param sent
        assert "filtering" not in adapter.session.calls[0]["params"]

    async def test_adset_metrics_use_adgroup_dimension(self):
        row = report_row("adgroup_id", 222, {"impressions": "10", "clicks": "1"})
        adapter = make_adapter([ok({"list": [row]})])
        result = await adapter.get_metrics(
            "adv-1", "adset", ["222"], DATE_START, DATE_END
        )
        assert "222" in result
        params = adapter.session.calls[0]["params"]
        assert params["data_level"] == "AUCTION_ADGROUP"
        assert params["dimensions"] == '["adgroup_id"]'
        assert '"adgroup_ids": ["222"]' in params["filtering"]

    async def test_ad_metrics_use_ad_dimension(self):
        row = report_row("ad_id", 333, {"impressions": "10", "clicks": "0"})
        adapter = make_adapter([ok({"list": [row]})])
        result = await adapter.get_metrics("adv-1", "ad", ["333"], DATE_START, DATE_END)
        assert "333" in result
        params = adapter.session.calls[0]["params"]
        assert params["data_level"] == "AUCTION_AD"
        assert params["dimensions"] == '["ad_id"]'
        assert '"ad_ids": ["333"]' in params["filtering"]

    async def test_unknown_entity_type_falls_back_to_campaign_level(self):
        adapter = make_adapter([ok({"list": []})])
        await adapter.get_metrics("adv-1", "weird", [], DATE_START, DATE_END)
        params = adapter.session.calls[0]["params"]
        assert params["data_level"] == "AUCTION_CAMPAIGN"

    async def test_api_error_raises_platform_error(self):
        adapter = make_adapter([err(message="report fail")])
        with pytest.raises(PlatformError, match="report fail"):
            await adapter.get_metrics("adv-1", "campaign", [], DATE_START, DATE_END)

    async def test_parse_error_raises_platform_error(self):
        row = report_row("campaign_id", 111, {"impressions": "not-a-number"})
        adapter = make_adapter([ok({"list": [row]})])
        with pytest.raises(PlatformError, match="Failed to parse metrics data"):
            await adapter.get_metrics("adv-1", "campaign", [], DATE_START, DATE_END)

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([TimeoutError()])
        with pytest.raises(PlatformError, match="Failed to fetch metrics"):
            await adapter.get_metrics("adv-1", "campaign", [], DATE_START, DATE_END)


# =============================================================================
# EMQ scores
# =============================================================================


class TestGetEmqScores:
    async def test_success_estimates_default_scores(self):
        pixels = {"pixels": [{"pixel_id": "px1"}, {"pixel_id": "px2"}]}
        adapter = make_adapter([ok(pixels)])
        scores = await adapter.get_emq_scores("adv-1")
        assert len(scores) == 2
        assert {s.event_name for s in scores} == {"pixel_px1", "pixel_px2"}
        assert all(s.score == 6.0 for s in scores)
        assert all(s.platform == Platform.TIKTOK.value for s in scores)

    async def test_api_error_returns_empty_list(self):
        adapter = make_adapter([err(message="pixel scope missing")])
        assert await adapter.get_emq_scores("adv-1") == []

    async def test_http_error_returns_empty_list(self):
        # raise_for_status -> code -1 envelope -> warning path -> []
        adapter = make_adapter([FakeResponse({}, status_code=500)])
        assert await adapter.get_emq_scores("adv-1") == []

    async def test_parse_error_returns_empty_list(self):
        adapter = make_adapter([ok({"pixels": 5})])
        assert await adapter.get_emq_scores("adv-1") == []

    async def test_network_error_returns_empty_list(self):
        adapter = make_adapter([TimeoutError()])
        assert await adapter.get_emq_scores("adv-1") == []


# =============================================================================
# execute_action (mutations)
# =============================================================================


def make_action(action_type, entity_type="campaign", parameters=None):
    return AutomationAction(
        platform=Platform.TIKTOK,
        account_id="adv-1",
        entity_type=entity_type,
        entity_id="111",
        action_type=action_type,
        parameters=parameters or {},
    )


class TestExecuteAction:
    async def test_update_budget_campaign(self):
        adapter = make_adapter([ok()])
        action = make_action("update_budget", parameters={"daily_budget": 75.5})
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.executed_at is not None
        assert result.result == {"updated": True}
        call = adapter.session.calls[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/campaign/update/")
        assert call["json"]["advertiser_id"] == "adv-1"
        assert call["json"]["campaign_id"] == "111"
        assert call["json"]["budget"] == 7550  # dollars -> cents
        assert call["json"]["budget_mode"] == "BUDGET_MODE_DAY"

    async def test_update_budget_adset_uses_adgroup_id_key(self):
        """FIXED (#540): the ad-group budget payload maps Stratum's ``adset``
        entity to TikTok's native ``adgroup_id`` key, so real ad-group budget
        updates are accepted by the API."""
        adapter = make_adapter([ok()])
        action = make_action(
            "update_budget", entity_type="adset", parameters={"daily_budget": 10}
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        call = adapter.session.calls[0]
        assert call["url"].endswith("/adgroup/update/")
        assert call["json"]["adgroup_id"] == "111"
        assert "adset_id" not in call["json"]

    async def test_update_budget_without_budget_param_sends_bare_payload(self):
        adapter = make_adapter([ok()])
        action = make_action("update_budget", parameters={})
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert "budget" not in adapter.session.calls[0]["json"]

    async def test_update_status_campaign_pause(self):
        adapter = make_adapter([ok()])
        action = make_action("update_status", parameters={"status": "paused"})
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.result == {"new_status": "DISABLE"}
        call = adapter.session.calls[0]
        assert call["url"].endswith("/campaign/update/status/")
        assert call["json"]["campaign_ids"] == ["111"]
        assert call["json"]["operation_status"] == "DISABLE"

    async def test_update_status_adset_enable(self):
        adapter = make_adapter([ok()])
        action = make_action(
            "update_status", entity_type="adset", parameters={"status": "active"}
        )
        result = await adapter.execute_action(action)
        assert result.result == {"new_status": "ENABLE"}
        call = adapter.session.calls[0]
        assert call["url"].endswith("/adgroup/update/status/")
        assert call["json"]["adgroup_ids"] == ["111"]

    async def test_update_status_ad(self):
        adapter = make_adapter([ok()])
        action = make_action(
            "update_status", entity_type="ad", parameters={"status": "paused"}
        )
        await adapter.execute_action(action)
        call = adapter.session.calls[0]
        assert call["url"].endswith("/ad/update/status/")
        assert call["json"]["ad_ids"] == ["111"]

    async def test_update_status_unknown_entity_falls_back_to_campaign(self):
        adapter = make_adapter([ok()])
        action = make_action(
            "update_status", entity_type="mystery", parameters={"status": "active"}
        )
        await adapter.execute_action(action)
        call = adapter.session.calls[0]
        assert call["url"].endswith("/campaign/update/status/")
        assert call["json"]["campaign_ids"] == ["111"]

    async def test_create_campaign_created_paused_for_safety(self):
        adapter = make_adapter([ok({"campaign_id": "new-1"})])
        action = make_action(
            "create_campaign",
            parameters={"name": "New C", "daily_budget": 20},
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.result == {"campaign_id": "new-1"}
        call = adapter.session.calls[0]
        assert call["url"].endswith("/campaign/create/")
        body = call["json"]
        assert body["campaign_name"] == "New C"
        assert body["objective_type"] == "CONVERSIONS"
        assert body["operation_status"] == "DISABLE"  # safety: create paused
        assert body["budget"] == 2000

    async def test_create_campaign_without_budget(self):
        adapter = make_adapter([ok({"campaign_id": "new-2"})])
        action = make_action(
            "create_campaign",
            parameters={"name": "No Budget", "objective": "TRAFFIC"},
        )
        result = await adapter.execute_action(action)
        assert result.result == {"campaign_id": "new-2"}
        body = adapter.session.calls[0]["json"]
        assert body["objective_type"] == "TRAFFIC"
        assert "budget" not in body

    async def test_unsupported_action_type_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("delete_everything")
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Unsupported action type" in result.error_message

    async def test_invalid_status_value_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("update_status", parameters={"status": "sideways"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert result.error_message

    async def test_missing_required_param_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("create_campaign", parameters={})  # no "name"
        result = await adapter.execute_action(action)
        assert result.status == "failed"

    async def test_platform_error_marks_action_failed(self):
        """FIXED (#540): a code!=0 platform rejection raises PlatformError which
        execute_action now catches — the action is marked failed with the error
        message instead of being left stuck in status='executing'."""
        adapter = make_adapter([err(message="budget too low")])
        action = make_action("update_budget", parameters={"daily_budget": 1})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "budget too low" in result.error_message

    async def test_update_status_platform_error_marks_failed(self):
        adapter = make_adapter([err(message="status locked")])
        action = make_action("update_status", parameters={"status": "paused"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "status locked" in result.error_message

    async def test_create_campaign_platform_error_marks_failed(self):
        adapter = make_adapter([err(message="quota exceeded")])
        action = make_action("create_campaign", parameters={"name": "X"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "quota exceeded" in result.error_message

    async def test_network_error_marks_failed(self, monkeypatch):
        adapter = make_adapter([])

        async def _boom(action):
            raise TimeoutError("net down")

        monkeypatch.setattr(adapter, "_update_budget", _boom)
        action = make_action("update_budget", parameters={"daily_budget": 5})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "net down" in result.error_message


# =============================================================================
# Creative uploads
# =============================================================================


class TestUploads:
    async def test_upload_image_success(self):
        adapter = make_adapter([ok({"image_id": "img-1"})])
        image_id = await adapter.upload_image("adv-1", b"\x89PNG", "logo.png")
        assert image_id == "img-1"
        call = adapter.session.calls[0]
        assert call["url"].endswith("/file/image/ad/upload/")
        assert call["json"]["file_name"] == "logo.png"
        assert call["json"]["image_data"]  # base64 payload present

    async def test_upload_image_failure_raises_platform_error(self):
        adapter = make_adapter([err(message="bad image")])
        with pytest.raises(PlatformError, match="Image upload failed"):
            await adapter.upload_image("adv-1", b"junk", "x.png")

    async def test_upload_video_success(self):
        adapter = make_adapter([ok({"video_id": "vid-1"})])
        video_id = await adapter.upload_video("adv-1", b"\x00vid", "clip.mp4")
        assert video_id == "vid-1"
        call = adapter.session.calls[0]
        assert call["url"].endswith("/file/video/ad/upload/")
        assert call["json"]["file_name"] == "clip.mp4"

    async def test_upload_video_failure_raises_platform_error(self):
        adapter = make_adapter([err(message="bad video")])
        with pytest.raises(PlatformError, match="Video upload failed"):
            await adapter.upload_video("adv-1", b"junk", "x.mp4")


# =============================================================================
# Low-level helpers
# =============================================================================


class TestHelpers:
    def test_make_request_maps_request_exception_to_error_envelope(self):
        adapter = make_adapter([requests.ConnectionError("dns fail")])
        result = adapter._make_request("GET", "/campaign/get/")
        assert result["code"] == -1
        assert "dns fail" in result["message"]

    def test_make_request_post_uses_json_body(self):
        adapter = make_adapter([ok()])
        adapter._make_request("POST", "/x/", data={"a": 1})
        call = adapter.session.calls[0]
        assert call["method"] == "POST"
        assert call["json"] == {"a": 1}

    def test_parse_datetime_supported_formats(self):
        adapter = TikTokAdapter(dict(CREDS))
        assert adapter._parse_datetime("2026-03-01 12:00:00") == datetime(
            2026, 3, 1, 12, tzinfo=UTC
        )
        assert adapter._parse_datetime("2026-03-01T12:00:00Z") == datetime(
            2026, 3, 1, 12, tzinfo=UTC
        )
        assert adapter._parse_datetime("2026-03-01") == datetime(2026, 3, 1, tzinfo=UTC)

    def test_parse_datetime_edge_cases(self):
        adapter = TikTokAdapter(dict(CREDS))
        assert adapter._parse_datetime(None) is None
        assert adapter._parse_datetime("") is None
        assert adapter._parse_datetime("not-a-date") is None
        assert adapter._parse_datetime(12345) is None  # non-str -> TypeError

    def test_status_mapping_round_trip(self):
        adapter = TikTokAdapter(dict(CREDS))
        assert adapter._map_status_to_platform(EntityStatus.ACTIVE) == "ENABLE"
        assert adapter._map_status_to_platform(EntityStatus.PAUSED) == "DISABLE"
        assert adapter._map_status_to_platform(EntityStatus.DELETED) == "DELETE"
        # Unmapped statuses default to ENABLE
        assert adapter._map_status_to_platform(EntityStatus.ARCHIVED) == "ENABLE"

        assert adapter._map_status_from_platform("DISABLE") == EntityStatus.PAUSED
        assert (
            adapter._map_status_from_platform("CAMPAIGN_STATUS_ENABLE")
            == EntityStatus.ACTIVE
        )
        assert (
            adapter._map_status_from_platform("ADGROUP_STATUS_CAMPAIGN_DISABLE")
            == EntityStatus.PAUSED
        )
        assert adapter._map_status_from_platform("SOMETHING_NEW") == EntityStatus.ACTIVE
