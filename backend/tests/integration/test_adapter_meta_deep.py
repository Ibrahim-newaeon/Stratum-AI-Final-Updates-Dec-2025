# =============================================================================
# Stratum AI - Meta Adapter Deep Integration Tests
# =============================================================================
"""Deep coverage tests for ``app.stratum.adapters.meta_adapter`` (#342 Batch 5+6).

The adapter wraps Meta's ``facebook_business`` SDK (not httpx), so all tests
mock at the SDK boundary: ``AdAccount`` / ``Campaign`` / ``AdSet`` / ``Ad`` /
``FacebookAdsApi`` and the server-side CAPI objects are patched in the
``meta_adapter`` namespace, and error paths raise *real*
``FacebookRequestError`` instances so the adapter's except clauses match.

Covered surface:
- credential validation, ``initialize`` (success / empty accounts / auth
  error 190 / generic API error), ``cleanup``.
- ``get_accounts`` / ``get_campaigns`` / ``get_adsets`` / ``get_ads`` mapping
  contracts (act_ prefix, cents->dollars, status mapping, targeting summary,
  filter param construction) plus PlatformError wrapping.
- ``get_metrics`` insights parsing at campaign/adset/ad level, breakdown
  param, ROAS/CPA derivation, video funnel metrics.
- ``get_emq_scores`` happy path, missing pixel, HTTP failure, network error,
  and parse-error fallbacks.
- ``execute_action`` routing for update_budget / update_bid / update_status /
  create_campaign / create_adset, unsupported action, and SDK failure paths.
- ``upload_image`` / ``upload_video`` creative operations.
- ``send_conversion_event`` CAPI flow including SHA-256 user-data hashing.
- helper functions (_cents_to_dollars, _parse_datetime, status maps).

No database fixtures are used: the adapter never persists rows.
"""

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from facebook_business.exceptions import FacebookRequestError

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    PlatformError,
)
from app.stratum.adapters.meta_adapter import MetaAdapter
from app.stratum.models import (
    AutomationAction,
    BiddingStrategy,
    EntityStatus,
    Platform,
)

# NOTE: no module-level asyncio mark — asyncio_mode=auto picks up async tests,
# and marking sync tests (helpers) emits PytestWarning noise.
pytestmark = [pytest.mark.integration]

MODULE = "app.stratum.adapters.meta_adapter"

FULL_CREDS = {
    "app_id": "123456",
    "app_secret": "shh-secret",
    "access_token": "EAAB-token",
    "business_id": "biz-987",
    "pixel_id": "px-555",
}

MIN_CREDS = {
    "app_id": "123456",
    "app_secret": "shh-secret",
    "access_token": "EAAB-token",
}


def make_fb_error(code: int = 100, message: str = "boom") -> FacebookRequestError:
    """Build a real FacebookRequestError so adapter except-clauses match."""
    return FacebookRequestError(
        message=message,
        request_context={},
        http_status=400,
        http_headers={},
        body={"error": {"message": message, "code": code}},
    )


@pytest.fixture
def adapter() -> MetaAdapter:
    """Adapter with full credentials, marked initialized (SDK is mocked)."""
    a = MetaAdapter(FULL_CREDS)
    a._initialized = True
    return a


@pytest.fixture
def adapter_no_pixel() -> MetaAdapter:
    a = MetaAdapter(MIN_CREDS)
    a._initialized = True
    return a


def _mock_ad_account():
    """Patch AdAccount in the adapter namespace, returning (patcher target ctx)."""
    return patch(f"{MODULE}.AdAccount")


def _action(**overrides) -> AutomationAction:
    base = dict(
        platform=Platform.META,
        account_id="act_111",
        entity_type="campaign",
        entity_id="c-1",
        action_type="update_budget",
        parameters={},
    )
    base.update(overrides)
    return AutomationAction(**base)


# =============================================================================
# Construction & lifecycle
# =============================================================================


class TestInit:
    def test_missing_credentials_raises_value_error(self):
        with pytest.raises(ValueError) as exc:
            MetaAdapter({"app_id": "1"})
        assert "app_secret" in str(exc.value)
        assert "access_token" in str(exc.value)

    def test_credentials_stored(self):
        a = MetaAdapter(FULL_CREDS)
        assert a.app_id == "123456"
        assert a.app_secret == "shh-secret"
        assert a.access_token == "EAAB-token"
        assert a.business_id == "biz-987"
        assert a.pixel_id == "px-555"
        assert a.api is None
        assert a._initialized is False

    def test_optional_credentials_default_none(self):
        a = MetaAdapter(MIN_CREDS)
        assert a.business_id is None
        assert a.pixel_id is None

    def test_rate_limiter_configured_for_meta(self):
        a = MetaAdapter(MIN_CREDS)
        assert a.rate_limiter.calls_per_minute == 60
        assert a.rate_limiter.burst_size == 20

    def test_platform_property(self):
        assert MetaAdapter(MIN_CREDS).platform == Platform.META


class TestInitialize:
    async def test_initialize_success(self):
        a = MetaAdapter(FULL_CREDS)
        with patch(f"{MODULE}.FacebookAdsApi") as mock_api:
            mock_api.get_default_api.return_value = "the-api"
            with patch.object(
                a, "_fetch_ad_accounts", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.return_value = [{"id": "act_1"}]
                await a.initialize()

        mock_api.init.assert_called_once_with(
            app_id="123456", app_secret="shh-secret", access_token="EAAB-token"
        )
        assert a.api == "the-api"
        assert a._initialized is True

    async def test_initialize_no_accounts_still_succeeds(self):
        a = MetaAdapter(FULL_CREDS)
        with patch(f"{MODULE}.FacebookAdsApi"):
            with patch.object(
                a, "_fetch_ad_accounts", new_callable=AsyncMock, return_value=[]
            ):
                await a.initialize()
        assert a._initialized is True

    async def test_initialize_auth_error_190(self):
        a = MetaAdapter(FULL_CREDS)
        with patch(f"{MODULE}.FacebookAdsApi"):
            with patch.object(
                a,
                "_fetch_ad_accounts",
                new_callable=AsyncMock,
                side_effect=make_fb_error(code=190, message="token expired"),
            ):
                with pytest.raises(AuthenticationError):
                    await a.initialize()
        assert a._initialized is False

    async def test_initialize_generic_api_error(self):
        a = MetaAdapter(FULL_CREDS)
        with patch(f"{MODULE}.FacebookAdsApi"):
            with patch.object(
                a,
                "_fetch_ad_accounts",
                new_callable=AsyncMock,
                side_effect=make_fb_error(code=1, message="unknown"),
            ):
                with pytest.raises(AdapterError) as exc:
                    await a.initialize()
        assert "unknown" in str(exc.value)

    async def test_cleanup_resets_state(self, adapter):
        adapter.api = "something"
        await adapter.cleanup()
        assert adapter._initialized is False
        assert adapter.api is None

    def test_ensure_initialized_guard(self):
        a = MetaAdapter(MIN_CREDS)
        with pytest.raises(AdapterError, match="not initialized"):
            a._ensure_initialized()


# =============================================================================
# Account fetching
# =============================================================================


class TestFetchAdAccounts:
    async def test_business_path(self, adapter):
        raw = [{"id": "act_1", "name": "A"}]
        with patch("facebook_business.adobjects.business.Business") as mock_biz:
            mock_biz.return_value.get_owned_ad_accounts.return_value = raw
            result = await adapter._fetch_ad_accounts()
        mock_biz.assert_called_once_with("biz-987")
        fields = mock_biz.return_value.get_owned_ad_accounts.call_args.kwargs["fields"]
        assert "spend_cap" in fields and "currency" in fields
        assert result == raw

    async def test_user_path_when_no_business_id(self, adapter_no_pixel):
        raw = [{"id": "act_2"}]
        with patch("facebook_business.adobjects.user.User") as mock_user:
            mock_user.return_value.get_ad_accounts.return_value = raw
            result = await adapter_no_pixel._fetch_ad_accounts()
        mock_user.assert_called_once_with(fbid="me")
        assert result == raw


class TestGetAccounts:
    async def test_requires_initialization(self):
        a = MetaAdapter(MIN_CREDS)
        with pytest.raises(AdapterError, match="not initialized"):
            await a.get_accounts()

    async def test_mapping_contract(self, adapter):
        raw = [
            {
                "id": "act_1",
                "name": "Main",
                "business": {"id": "biz-9"},
                "timezone_name": "Asia/Dubai",
                "currency": "AED",
                "spend_cap": "500000",
            },
            {"id": "act_2"},  # minimal: defaults everywhere
        ]
        with patch.object(
            adapter, "_fetch_ad_accounts", new_callable=AsyncMock, return_value=raw
        ):
            accounts = await adapter.get_accounts()

        a1, a2 = accounts
        assert a1.account_id == "act_1"
        assert a1.account_name == "Main"
        assert a1.business_id == "biz-9"
        assert a1.timezone == "Asia/Dubai"
        assert a1.currency == "AED"
        assert a1.daily_spend_limit == 5000.0  # cents -> dollars
        assert a1.raw_data == raw[0]

        assert a2.account_name == "Unknown Account"
        assert a2.business_id is None
        assert a2.timezone == "UTC"
        assert a2.currency == "USD"
        assert a2.daily_spend_limit is None

    async def test_error_wrapped_as_platform_error(self, adapter):
        with patch.object(
            adapter,
            "_fetch_ad_accounts",
            new_callable=AsyncMock,
            side_effect=make_fb_error(code=17, message="rate limited"),
        ):
            with pytest.raises(PlatformError) as exc:
                await adapter.get_accounts()
        assert exc.value.platform_code == "17"
        assert "rate limited" in str(exc.value)


# =============================================================================
# Campaigns / AdSets / Ads
# =============================================================================

RAW_CAMPAIGN = {
    "id": "camp-1",
    "name": "Summer Sale",
    "effective_status": "WITH_ISSUES",  # maps to ACTIVE (still delivering)
    "daily_budget": "10000",
    "lifetime_budget": None,
    "budget_remaining": "2550",
    "created_time": "2026-01-01T00:00:00+00:00",
    "updated_time": "2026-06-01T12:30:00+00:00",
}


class TestGetCampaigns:
    async def test_mapping_and_prefix(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_campaigns.return_value = [RAW_CAMPAIGN]
            campaigns = await adapter.get_campaigns("111")  # no act_ prefix

        mock_acct_cls.assert_called_once_with("act_111")
        assert len(campaigns) == 1
        c = campaigns[0]
        assert c.campaign_id == "camp-1"
        assert c.campaign_name == "Summer Sale"
        assert c.status == EntityStatus.ACTIVE.value  # WITH_ISSUES -> ACTIVE
        assert c.daily_budget == 100.0
        assert c.lifetime_budget is None
        assert c.budget_remaining == 25.5
        assert c.created_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert c.last_synced is not None
        assert c.raw_data == RAW_CAMPAIGN
        # No status filter -> no filtering param
        params = mock_acct.get_campaigns.call_args.kwargs["params"]
        assert params == {}

    async def test_status_filter_builds_filtering_param(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_campaigns.return_value = []
            await adapter.get_campaigns(
                "act_111",
                status_filter=[EntityStatus.ACTIVE, EntityStatus.PAUSED],
            )
        params = mock_acct.get_campaigns.call_args.kwargs["params"]
        assert params["filtering"] == [
            {
                "field": "effective_status",
                "operator": "IN",
                "value": ["ACTIVE", "PAUSED"],
            }
        ]

    async def test_error_wrapped(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_campaigns.side_effect = make_fb_error(
                code=80004, message="too many calls"
            )
            with pytest.raises(PlatformError) as exc:
                await adapter.get_campaigns("act_111")
        assert exc.value.platform_code == "80004"


class TestGetAdsets:
    async def test_mapping_with_targeting_summary(self, adapter):
        raw = {
            "id": "as-1",
            "name": "US 21-45",
            "campaign_id": "camp-1",
            "effective_status": "PAUSED",
            "daily_budget": "5000",
            "bid_amount": "250",
            "targeting": {
                "geo_locations": {"countries": ["US", "AE"]},
                "age_min": 21,
                "age_max": 45,
            },
            "start_time": "2026-05-01T00:00:00+00:00",
            "end_time": None,
        }
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_ad_sets.return_value = [raw]
            adsets = await adapter.get_adsets("222")

        mock_acct_cls.assert_called_once_with("act_222")
        a = adsets[0]
        assert a.adset_id == "as-1"
        assert a.campaign_id == "camp-1"
        assert a.status == EntityStatus.PAUSED.value
        assert a.daily_budget == 50.0
        assert a.bid_amount == 2.5
        assert a.targeting_summary == "Countries: US, AE; Age: 21-45"
        assert a.start_time == datetime(2026, 5, 1, tzinfo=UTC)
        assert a.end_time is None

    async def test_no_targeting_gives_none_summary(self, adapter):
        raw = {"id": "as-2", "name": "bare", "campaign_id": "camp-1"}
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_ad_sets.return_value = [raw]
            adsets = await adapter.get_adsets("act_222")
        assert adsets[0].targeting_summary is None
        # missing effective_status defaults to ACTIVE
        assert adsets[0].status == EntityStatus.ACTIVE.value

    async def test_campaign_filter_param(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_ad_sets.return_value = []
            await adapter.get_adsets("act_222", campaign_id="camp-9")
        params = mock_acct.get_ad_sets.call_args.kwargs["params"]
        assert params["filtering"] == [
            {"field": "campaign.id", "operator": "EQUAL", "value": "camp-9"}
        ]

    async def test_error_wrapped(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_ad_sets.side_effect = make_fb_error(
                code=200, message="perm denied"
            )
            with pytest.raises(PlatformError) as exc:
                await adapter.get_adsets("act_222")
        assert exc.value.platform_code == "200"


class TestGetAds:
    async def test_mapping_with_creative(self, adapter):
        raw = {
            "id": "ad-1",
            "name": "Video Ad",
            "adset_id": "as-1",
            "campaign_id": "camp-1",
            "effective_status": "IN_PROCESS",
            "creative": {"id": "cr-77"},
        }
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_ads.return_value = [raw]
            ads = await adapter.get_ads("333")

        mock_acct_cls.assert_called_once_with("act_333")
        ad = ads[0]
        assert ad.ad_id == "ad-1"
        assert ad.adset_id == "as-1"
        assert ad.campaign_id == "camp-1"
        assert ad.status == EntityStatus.PENDING_REVIEW.value
        assert ad.creative_id == "cr-77"

    async def test_non_dict_creative_gives_none(self, adapter):
        raw = {"id": "ad-2", "name": "x", "creative": "not-a-dict"}
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_ads.return_value = [raw]
            ads = await adapter.get_ads("act_333")
        assert ads[0].creative_id is None

    async def test_adset_filter_param(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_ads.return_value = []
            await adapter.get_ads("act_333", adset_id="as-5")
        params = mock_acct.get_ads.call_args.kwargs["params"]
        assert params["filtering"] == [
            {"field": "adset.id", "operator": "EQUAL", "value": "as-5"}
        ]

    async def test_error_wrapped(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_ads.side_effect = make_fb_error(
                code=10, message="nope"
            )
            with pytest.raises(PlatformError) as exc:
                await adapter.get_ads("act_333")
        assert exc.value.platform_code == "10"


# =============================================================================
# Insights / metrics
# =============================================================================

DATE_START = datetime(2026, 6, 1, tzinfo=UTC)
DATE_END = datetime(2026, 6, 30, tzinfo=UTC)


def _insight(id_field: str, entity_id: str) -> dict:
    return {
        id_field: entity_id,
        "impressions": "10000",
        "clicks": "500",
        "spend": "250.0",
        "ctr": "5.0",
        "cpc": "0.5",
        "cpm": "25.0",
        "actions": [
            {"action_type": "link_click", "value": "480"},
            {"action_type": "purchase", "value": "10"},
        ],
        "action_values": [{"action_type": "purchase", "value": "1000.0"}],
        "video_p25_watched_actions": [{"value": "400"}],
        "video_p50_watched_actions": [{"value": "300"}],
        "video_p75_watched_actions": [{"value": "200"}],
        "video_p100_watched_actions": [{"value": "100"}],
    }


class TestGetMetrics:
    async def test_campaign_level_parsing(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_insights.return_value = [_insight("campaign_id", "camp-1")]
            metrics_map = await adapter.get_metrics(
                "444", "campaign", ["camp-1"], DATE_START, DATE_END
            )

        mock_acct_cls.assert_called_once_with("act_444")
        params = mock_acct.get_insights.call_args.kwargs["params"]
        assert params["level"] == "campaign"
        assert params["time_range"] == {"since": "2026-06-01", "until": "2026-06-30"}
        assert params["filtering"] == [
            {"field": "campaign.id", "operator": "IN", "value": ["camp-1"]}
        ]
        assert "breakdowns" not in params

        m = metrics_map["camp-1"]
        assert m.impressions == 10000
        assert m.clicks == 500
        assert m.spend == 250.0
        assert m.ctr == 5.0
        assert m.cpc == 0.5
        assert m.cpm == 25.0
        assert m.conversions == 10
        assert m.conversion_value == 1000.0
        assert m.roas == pytest.approx(4.0)
        assert m.cpa == pytest.approx(25.0)
        assert (m.video_p25, m.video_p50, m.video_p75, m.video_p100) == (
            400,
            300,
            200,
            100,
        )
        assert m.date_start == DATE_START
        assert m.date_end == DATE_END

    async def test_adset_level_uses_adset_id(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_insights.return_value = [_insight("adset_id", "as-1")]
            metrics_map = await adapter.get_metrics(
                "act_444", "adset", ["as-1"], DATE_START, DATE_END
            )
        assert "as-1" in metrics_map
        params = mock_acct.get_insights.call_args.kwargs["params"]
        assert params["level"] == "adset"

    async def test_ad_level_uses_ad_id_and_breakdown(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_insights.return_value = [_insight("ad_id", "ad-1")]
            metrics_map = await adapter.get_metrics(
                "act_444", "ad", ["ad-1"], DATE_START, DATE_END, breakdown="age"
            )
        assert "ad-1" in metrics_map
        params = mock_acct.get_insights.call_args.kwargs["params"]
        assert params["level"] == "ad"
        assert params["breakdowns"] == ["age"]

    async def test_unknown_entity_type_defaults_to_campaign(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.get_insights.return_value = []
            await adapter.get_metrics("act_444", "weird", ["x"], DATE_START, DATE_END)
        params = mock_acct.get_insights.call_args.kwargs["params"]
        assert params["level"] == "campaign"

    async def test_minimal_insight_no_derived_metrics(self, adapter):
        raw = {"campaign_id": "camp-2"}
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_insights.return_value = [raw]
            metrics_map = await adapter.get_metrics(
                "act_444", "campaign", ["camp-2"], DATE_START, DATE_END
            )
        m = metrics_map["camp-2"]
        assert m.impressions == 0
        assert m.spend == 0.0
        assert m.ctr is None and m.cpc is None and m.cpm is None
        assert m.conversions is None
        assert m.roas is None and m.cpa is None
        assert m.video_p25 is None

    async def test_error_wrapped(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.get_insights.side_effect = make_fb_error(
                code=2, message="service temporarily unavailable"
            )
            with pytest.raises(PlatformError) as exc:
                await adapter.get_metrics(
                    "act_444", "campaign", ["c"], DATE_START, DATE_END
                )
        assert exc.value.platform_code == "2"


# =============================================================================
# EMQ scores
# =============================================================================


class TestGetEmqScores:
    async def test_no_pixel_returns_empty(self, adapter_no_pixel):
        assert await adapter_no_pixel.get_emq_scores("act_1") == []

    async def test_parses_scores_for_each_event_type(self, adapter):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "event_match_quality": 8.2,
                    "match_rate": 75.0,
                    "em_match_rate": 80.0,
                    "ph_match_rate": 60.0,
                }
            ]
        }
        with patch("requests.get", return_value=response) as mock_get:
            scores = await adapter.get_emq_scores("act_1")

        assert mock_get.call_count == 5  # Purchase, AddToCart, ViewContent, ...
        url = mock_get.call_args_list[0].args[0]
        assert "px-555/server_events_quality" in url
        first_params = mock_get.call_args_list[0].kwargs["params"]
        assert first_params["event_name"] == "Purchase"
        assert first_params["access_token"] == "EAAB-token"

        assert len(scores) == 5
        s = scores[0]
        assert s.event_name == "Purchase"
        assert s.score == 8.2
        assert s.match_rate == 75.0
        assert s.email_match_rate == 80.0
        assert s.phone_match_rate == 60.0

    async def test_non_200_responses_skipped(self, adapter):
        response = MagicMock()
        response.status_code = 500
        with patch("requests.get", return_value=response):
            assert await adapter.get_emq_scores("act_1") == []

    async def test_empty_data_skipped(self, adapter):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        with patch("requests.get", return_value=response):
            assert await adapter.get_emq_scores("act_1") == []

    async def test_network_error_returns_empty(self, adapter):
        with patch("requests.get", side_effect=ConnectionError("dns fail")):
            assert await adapter.get_emq_scores("act_1") == []

    async def test_parse_error_returns_empty(self, adapter):
        # EMQScore validates score <= 10; an out-of-range value raises
        # pydantic ValidationError (a ValueError) -> caught -> []
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": [{"event_match_quality": 55}]}
        with patch("requests.get", return_value=response):
            assert await adapter.get_emq_scores("act_1") == []


# =============================================================================
# execute_action routing + write operations
# =============================================================================


class TestExecuteAction:
    async def test_update_budget_campaign(self, adapter):
        action = _action(
            action_type="update_budget",
            entity_type="campaign",
            parameters={"daily_budget": 150.0, "lifetime_budget": 5000.0},
        )
        with patch(f"{MODULE}.Campaign") as mock_campaign_cls:
            result = await adapter.execute_action(action)

        mock_campaign_cls.assert_called_once_with("c-1")
        update_params = mock_campaign_cls.return_value.api_update.call_args.kwargs[
            "params"
        ]
        assert update_params == {"daily_budget": 15000, "lifetime_budget": 500000}
        assert result.status == "completed"
        assert result.executed_at is not None
        assert result.executed_at.tzinfo is not None
        assert set(result.result["updated_fields"]) == {
            "daily_budget",
            "lifetime_budget",
        }

    async def test_update_budget_adset(self, adapter):
        action = _action(
            action_type="update_budget",
            entity_type="adset",
            entity_id="as-9",
            parameters={"daily_budget": 42.5},
        )
        with patch(f"{MODULE}.AdSet") as mock_adset_cls:
            result = await adapter.execute_action(action)
        mock_adset_cls.assert_called_once_with("as-9")
        update_params = mock_adset_cls.return_value.api_update.call_args.kwargs[
            "params"
        ]
        assert update_params == {"daily_budget": 4250}
        assert result.status == "completed"

    async def test_update_bid_amount_and_strategy(self, adapter):
        action = _action(
            action_type="update_bid",
            entity_type="adset",
            entity_id="as-3",
            parameters={"bid_amount": 2.5, "bid_strategy": "cost_cap"},
        )
        with patch(f"{MODULE}.AdSet") as mock_adset_cls:
            result = await adapter.execute_action(action)
        update_params = mock_adset_cls.return_value.api_update.call_args.kwargs[
            "params"
        ]
        assert update_params == {"bid_amount": 250, "bid_strategy": "COST_CAP"}
        assert result.status == "completed"

    async def test_update_bid_campaign_unmapped_strategy_skipped(self, adapter):
        # TARGET_CPA has no Meta mapping -> bid_strategy key omitted
        action = _action(
            action_type="update_bid",
            entity_type="campaign",
            parameters={"bid_strategy": BiddingStrategy.TARGET_CPA.value},
        )
        with patch(f"{MODULE}.Campaign") as mock_campaign_cls:
            result = await adapter.execute_action(action)
        update_params = mock_campaign_cls.return_value.api_update.call_args.kwargs[
            "params"
        ]
        assert update_params == {}
        assert result.status == "completed"

    @pytest.mark.parametrize(
        "entity_type,patched",
        [("campaign", "Campaign"), ("adset", "AdSet"), ("ad", "Ad")],
    )
    async def test_update_status_entity_routing(self, adapter, entity_type, patched):
        action = _action(
            action_type="update_status",
            entity_type=entity_type,
            entity_id="e-1",
            parameters={"status": "paused"},
        )
        with patch(f"{MODULE}.{patched}") as mock_cls:
            result = await adapter.execute_action(action)
        mock_cls.assert_called_once_with("e-1")
        mock_cls.return_value.api_update.assert_called_once_with(
            params={"status": "PAUSED"}
        )
        assert result.status == "completed"
        assert result.result == {"new_status": "PAUSED"}

    async def test_update_status_unmapped_status_sends_none(self, adapter):
        """PINNED BUG (low severity): _update_status with a unified status that
        has no Meta mapping (e.g. ``pending_review``) does not fail validation —
        ``STATUS_TO_META.get()`` returns None and the adapter calls
        ``api_update(params={"status": None})``, pushing a null status to Meta
        instead of raising. See meta_adapter.py:795-805.
        """
        action = _action(
            action_type="update_status",
            entity_type="campaign",
            parameters={"status": "pending_review"},
        )
        with patch(f"{MODULE}.Campaign") as mock_cls:
            result = await adapter.execute_action(action)
        mock_cls.return_value.api_update.assert_called_once_with(
            params={"status": None}
        )
        # Current (buggy) contract: reported as success with a null status
        assert result.status == "completed"
        assert result.result == {"new_status": None}

    async def test_create_campaign_daily_budget_and_bidding(self, adapter):
        action = _action(
            action_type="create_campaign",
            account_id="555",  # exercises act_ prefixing
            parameters={
                "name": "New Campaign",
                "objective": "OUTCOME_LEADS",
                "daily_budget": 200.0,
                "bid_strategy": "lowest_cost",
                "special_ad_categories": ["HOUSING"],
            },
        )
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.create_campaign.return_value = {"id": "camp-new"}
            result = await adapter.execute_action(action)

        mock_acct_cls.assert_called_once_with("act_555")
        params = mock_acct.create_campaign.call_args.kwargs["params"]
        assert params["name"] == "New Campaign"
        assert params["objective"] == "OUTCOME_LEADS"
        assert params["status"] == "PAUSED"  # always created paused for safety
        assert params["special_ad_categories"] == ["HOUSING"]
        assert params["daily_budget"] == 20000
        assert params["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
        assert result.status == "completed"
        assert result.result == {"campaign_id": "camp-new"}

    async def test_create_campaign_lifetime_budget_defaults(self, adapter):
        action = _action(
            action_type="create_campaign",
            parameters={"name": "LT", "lifetime_budget": 1000.0},
        )
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.create_campaign.return_value = {"id": "camp-lt"}
            result = await adapter.execute_action(action)
        params = mock_acct.create_campaign.call_args.kwargs["params"]
        assert params["objective"] == "OUTCOME_SALES"  # default
        assert params["lifetime_budget"] == 100000
        assert "daily_budget" not in params
        assert result.status == "completed"

    async def test_create_adset(self, adapter):
        action = _action(
            action_type="create_adset",
            account_id="666",  # exercises act_ prefixing in _create_adset
            parameters={
                "name": "New AdSet",
                "campaign_id": "camp-1",
                "daily_budget": 75.0,
                "bid_amount": 1.5,
                "targeting": {"geo_locations": {"countries": ["US"]}},
            },
        )
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.create_ad_set.return_value = {"id": "as-new"}
            result = await adapter.execute_action(action)

        mock_acct_cls.assert_called_once_with("act_666")
        params = mock_acct.create_ad_set.call_args.kwargs["params"]
        assert params["name"] == "New AdSet"
        assert params["campaign_id"] == "camp-1"
        assert params["status"] == "PAUSED"
        assert params["billing_event"] == "IMPRESSIONS"
        assert params["optimization_goal"] == "OFFSITE_CONVERSIONS"
        assert params["targeting"] == {"geo_locations": {"countries": ["US"]}}
        assert params["daily_budget"] == 7500
        assert params["bid_amount"] == 150
        assert result.result == {"adset_id": "as-new"}

    async def test_unsupported_action_type_marks_failed(self, adapter):
        action = _action(action_type="delete_everything")
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Unsupported action type" in result.error_message
        assert result.executed_at is None

    async def test_facebook_error_marks_failed(self, adapter):
        action = _action(action_type="update_budget", parameters={"daily_budget": 10.0})
        with patch(f"{MODULE}.Campaign") as mock_campaign_cls:
            mock_campaign_cls.return_value.api_update.side_effect = make_fb_error(
                code=100, message="Invalid parameter"
            )
            result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert result.error_message == "Invalid parameter"

    async def test_missing_required_param_marks_failed(self, adapter):
        # update_status without "status" -> KeyError -> generic failure branch
        action = _action(action_type="update_status", parameters={})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert result.error_message is not None

    async def test_requires_initialization(self):
        a = MetaAdapter(MIN_CREDS)
        with pytest.raises(AdapterError, match="not initialized"):
            await a.execute_action(_action())


# =============================================================================
# Creative operations
# =============================================================================


class TestCreativeOperations:
    async def test_upload_image_returns_hash(self, adapter):
        import base64

        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.create_ad_image.return_value = {
                "images": {"banner.png": {"hash": "abc123hash"}}
            }
            result = await adapter.upload_image("777", b"\x89PNG-bytes", "banner.png")

        mock_acct_cls.assert_called_once_with("act_777")
        params = mock_acct.create_ad_image.call_args.kwargs["params"]
        assert params["name"] == "banner.png"
        assert base64.b64decode(params["bytes"]) == b"\x89PNG-bytes"
        assert result == "abc123hash"

    async def test_upload_image_missing_filename_returns_empty(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct_cls.return_value.create_ad_image.return_value = {"images": {}}
            result = await adapter.upload_image("act_777", b"x", "missing.png")
        assert result == ""

    async def test_upload_video_returns_id(self, adapter):
        with _mock_ad_account() as mock_acct_cls:
            mock_acct = mock_acct_cls.return_value
            mock_acct.create_ad_video.return_value = {"id": "vid-42"}
            result = await adapter.upload_video("888", b"video-bytes", "promo.mp4")

        mock_acct_cls.assert_called_once_with("act_888")
        params = mock_acct.create_ad_video.call_args.kwargs["params"]
        assert params["name"] == "promo.mp4"
        assert params["source_file"].endswith(".mp4")
        assert result == "vid-42"

    async def test_setup_webhooks_returns_true(self, adapter):
        assert await adapter.setup_webhooks("https://cb.example.com", ["ads"]) is True


# =============================================================================
# Conversions API (CAPI)
# =============================================================================


class TestSendConversionEvent:
    async def test_requires_pixel_id(self, adapter_no_pixel):
        with pytest.raises(ValueError, match="pixel_id"):
            await adapter_no_pixel.send_conversion_event(
                "Purchase", datetime.now(UTC), {"email": "a@b.com"}
            )

    async def test_full_event_flow_with_hashing(self, adapter):
        event_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        user_data = {
            "email": "  User@Example.COM ",
            "phone": "+1 (555) 123-4567",
            "client_ip_address": "1.2.3.4",
            "client_user_agent": "UA/1.0",
            "fbc": "fb.1.click",
            "fbp": "fb.1.browser",
        }
        custom_data = {
            "currency": "AED",
            "value": 99.5,
            "content_ids": ["sku-1"],
            "content_type": "product",
        }

        with (
            patch(f"{MODULE}.UserData") as mock_user_data,
            patch(f"{MODULE}.CustomData") as mock_custom_data,
            patch(f"{MODULE}.Event") as mock_event,
            patch(f"{MODULE}.EventRequest") as mock_request,
        ):
            mock_request.return_value.execute.return_value = {"events_received": 1}
            ok = await adapter.send_conversion_event(
                "Purchase",
                event_time,
                user_data,
                custom_data=custom_data,
                event_source_url="https://shop.example.com/checkout",
            )

        assert ok is True

        expected_em = hashlib.sha256(b"user@example.com").hexdigest()
        expected_ph = hashlib.sha256(b"15551234567").hexdigest()
        ud_kwargs = mock_user_data.call_args.kwargs
        assert ud_kwargs["email"] == expected_em
        assert ud_kwargs["phone"] == expected_ph
        assert ud_kwargs["client_ip_address"] == "1.2.3.4"
        assert ud_kwargs["client_user_agent"] == "UA/1.0"
        assert ud_kwargs["fbc"] == "fb.1.click"
        assert ud_kwargs["fbp"] == "fb.1.browser"

        cd_kwargs = mock_custom_data.call_args.kwargs
        assert cd_kwargs["currency"] == "AED"
        assert cd_kwargs["value"] == 99.5
        assert cd_kwargs["content_ids"] == ["sku-1"]
        assert cd_kwargs["content_type"] == "product"

        ev_kwargs = mock_event.call_args.kwargs
        assert ev_kwargs["event_name"] == "Purchase"
        assert ev_kwargs["event_time"] == int(event_time.timestamp())
        assert ev_kwargs["action_source"] == "website"
        assert ev_kwargs["event_source_url"] == "https://shop.example.com/checkout"

        req_kwargs = mock_request.call_args.kwargs
        assert req_kwargs["pixel_id"] == "px-555"
        assert req_kwargs["events"] == [mock_event.return_value]

    async def test_no_custom_data_and_zero_received(self, adapter):
        with (
            patch(f"{MODULE}.UserData"),
            patch(f"{MODULE}.CustomData") as mock_custom_data,
            patch(f"{MODULE}.Event") as mock_event,
            patch(f"{MODULE}.EventRequest") as mock_request,
        ):
            mock_request.return_value.execute.return_value = {"events_received": 0}
            ok = await adapter.send_conversion_event(
                "Lead", datetime.now(UTC), {"email": "a@b.com"}
            )
        assert ok is False
        mock_custom_data.assert_not_called()
        assert mock_event.call_args.kwargs["custom_data"] is None


# =============================================================================
# Helpers
# =============================================================================


class TestHelpers:
    def test_cents_to_dollars(self, adapter):
        assert adapter._cents_to_dollars(None) is None
        assert adapter._cents_to_dollars("12345") == 123.45
        assert adapter._cents_to_dollars(500) == 5.0
        assert adapter._cents_to_dollars("not-a-number") is None

    def test_parse_datetime(self, adapter):
        assert adapter._parse_datetime(None) is None
        assert adapter._parse_datetime("") is None
        assert adapter._parse_datetime("garbage") is None
        parsed = adapter._parse_datetime("2026-06-15T10:30:00Z")
        assert parsed == datetime(2026, 6, 15, 10, 30, tzinfo=UTC)
        parsed2 = adapter._parse_datetime("2026-06-15T10:30:00+04:00")
        assert parsed2 is not None and parsed2.utcoffset().total_seconds() == 4 * 3600

    def test_prepare_user_data_for_capi(self, adapter):
        hashed = adapter._prepare_user_data_for_capi(
            {"email": " Foo@Bar.COM ", "phone": "+971-50-123-4567"}
        )
        assert hashed["em"] == hashlib.sha256(b"foo@bar.com").hexdigest()
        assert hashed["ph"] == hashlib.sha256(b"971501234567").hexdigest()

    def test_prepare_user_data_empty(self, adapter):
        assert adapter._prepare_user_data_for_capi({}) == {}

    def test_map_status_to_platform(self, adapter):
        assert adapter._map_status_to_platform(EntityStatus.PAUSED) == "PAUSED"
        assert adapter._map_status_to_platform(EntityStatus.DELETED) == "DELETED"
        # Unmapped status falls back to ACTIVE
        assert adapter._map_status_to_platform(EntityStatus.PENDING_REVIEW) == "ACTIVE"

    def test_map_status_from_platform(self, adapter):
        assert (
            adapter._map_status_from_platform("IN_PROCESS")
            == EntityStatus.PENDING_REVIEW
        )
        assert adapter._map_status_from_platform("WITH_ISSUES") == EntityStatus.ACTIVE
        assert adapter._map_status_from_platform("ARCHIVED") == EntityStatus.ARCHIVED
        # Unknown platform status falls back to ACTIVE
        assert adapter._map_status_from_platform("BOGUS") == EntityStatus.ACTIVE
