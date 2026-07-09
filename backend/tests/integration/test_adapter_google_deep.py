# =============================================================================
# Stratum AI - Google Ads Adapter Deep Coverage Tests (#342 Batch 5+6)
# =============================================================================
"""
Deep integration tests for ``app.stratum.adapters.google_adapter``.

The Google Ads SDK (``google-ads``) is a gRPC/protobuf client, NOT an httpx
client, so we mock at the SDK boundary: ``GoogleAdsClient.load_from_dict`` is
patched in the adapter's namespace, service objects returned by
``client.get_service(...)`` are MagicMocks, and GAQL search responses are
lists of SimpleNamespace rows shaped like proto-plus messages.

Covered surface:
- credential validation + client config building (OAuth vs service account)
- initialize() error mapping (auth vs generic) + the initialize-order bug
- get_accounts (MCC + single-account branches) and error mapping
- get_campaigns / get_adsets / get_ads GAQL building + row conversion
- get_metrics for campaign/adset/ad entity types + derived metrics
- get_emq_scores heuristic scoring + swallow-error path
- execute_action: update_budget / update_bid / update_status /
  create_campaign / unsupported action + failure paths
- upload_image / upload_video, cleanup, status mapping helpers

KNOWN PRODUCTION BUGS PINNED HERE (do not "fix" the tests):

BUG-1 (high): ``GoogleAdsAdapter.initialize()`` calls ``get_accounts()`` to
    verify credentials BEFORE setting ``self._initialized = True``
    (google_adapter.py:263 vs :272). ``get_accounts`` calls
    ``_ensure_initialized`` (:304), which raises
    ``AdapterError("Adapter not initialized...")`` because the flag is still
    False. Result: initialize() can NEVER succeed. See
    ``test_initialize_order_bug_always_raises``.

BUG-2 (medium): ``_get_single_account`` (google_adapter.py:365-405) is only
    reachable from ``get_accounts`` when ``login_customer_id`` is falsy, but
    it immediately returns ``[]`` in that case (:371-373), so its GAQL query
    path (:375-405) is dead code in production. Covered here by direct call.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.ads.googleads.errors import GoogleAdsException

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    PlatformError,
)
from app.stratum.adapters.google_adapter import GoogleAdsAdapter
from app.stratum.models import (
    AutomationAction,
    BiddingStrategy,
    EntityStatus,
    Platform,
)

pytestmark = pytest.mark.integration

GOOGLE_ADAPTER_NS = "app.stratum.adapters.google_adapter"

OAUTH_CREDS = {
    "developer_token": "dev-token",
    "client_id": "cid.apps.googleusercontent.com",
    "client_secret": "shh",
    "refresh_token": "1//refresh",
    "login_customer_id": "1234567890",
}


# =============================================================================
# Helpers
# =============================================================================


def make_google_error(
    code: str = "INTERNAL_ERROR", message: str = "boom", empty: bool = False
) -> GoogleAdsException:
    """Build a GoogleAdsException shaped like the real gRPC failure."""
    errors = [] if empty else [SimpleNamespace(error_code=code, message=message)]
    failure = SimpleNamespace(errors=errors)
    return GoogleAdsException(None, None, failure, "request-123")


def make_client() -> tuple[MagicMock, dict[str, MagicMock]]:
    """Mock GoogleAdsClient with per-name memoized services and fresh types."""
    client = MagicMock()
    services: dict[str, MagicMock] = {}
    client.get_service.side_effect = lambda name: services.setdefault(name, MagicMock())
    client.get_type.side_effect = lambda name: MagicMock()
    return client, services


def make_adapter(
    credentials: dict[str, str] | None = None,
    client: MagicMock | None = None,
) -> tuple[GoogleAdsAdapter, MagicMock, dict[str, MagicMock]]:
    """Adapter wired to a mock client, marked initialized (BUG-1 workaround)."""
    adapter = GoogleAdsAdapter(dict(credentials or OAUTH_CREDS))
    if client is None:
        client, services = make_client()
    else:
        services = {}
    adapter.client = client
    adapter._initialized = True
    adapter.rate_limiter = AsyncMock()
    return adapter, client, services


def campaign_row(
    *,
    campaign_id: int = 111,
    status: str = "ENABLED",
    strategy: str = "TARGET_CPA",
    target_cpa_micros: int = 5_000_000,
    target_roas: float = 0.0,
    amount_micros: int = 25_000_000,
    total_amount_micros: int = 0,
    channel: str | None = "SEARCH",
) -> SimpleNamespace:
    campaign = SimpleNamespace(
        id=campaign_id,
        name=f"Campaign {campaign_id}",
        status=SimpleNamespace(name=status),
        advertising_channel_type=(SimpleNamespace(name=channel) if channel else None),
        bidding_strategy_type=(SimpleNamespace(name=strategy) if strategy else None),
        target_cpa=SimpleNamespace(target_cpa_micros=target_cpa_micros),
        target_roas=SimpleNamespace(target_roas=target_roas),
        campaign_budget="customers/1234567890/campaignBudgets/222",
    )
    budget = SimpleNamespace(
        id=222,
        amount_micros=amount_micros,
        total_amount_micros=total_amount_micros,
        period=None,
    )
    return SimpleNamespace(campaign=campaign, campaign_budget=budget)


def adset_row(
    *,
    adgroup_id: int = 333,
    campaign_resource: str = "customers/1234567890/campaigns/111",
    status: str = "PAUSED",
    cpc_bid_micros: int = 2_500_000,
) -> SimpleNamespace:
    return SimpleNamespace(
        ad_group=SimpleNamespace(
            id=adgroup_id,
            name=f"AdGroup {adgroup_id}",
            campaign=campaign_resource,
            status=SimpleNamespace(name=status),
            cpc_bid_micros=cpc_bid_micros,
            target_cpa_micros=0,
        )
    )


def ad_row(
    *,
    ad_id: int = 444,
    name: str | None = "My RSA",
    with_rsa: bool = True,
    headline_text: str = "H1",
    final_urls: list[str] | None = None,
    status: str = "ENABLED",
) -> SimpleNamespace:
    rsa = None
    if with_rsa:
        rsa = SimpleNamespace(
            headlines=[SimpleNamespace(text=headline_text)],
            descriptions=[SimpleNamespace(text="D1")],
        )
    ad = SimpleNamespace(
        id=ad_id,
        name=name,
        type_=SimpleNamespace(name="RESPONSIVE_SEARCH_AD"),
        final_urls=final_urls if final_urls is not None else ["https://x.example"],
        responsive_search_ad=rsa,
    )
    return SimpleNamespace(
        ad_group_ad=SimpleNamespace(
            ad=ad,
            ad_group="customers/1234567890/adGroups/333",
            status=SimpleNamespace(name=status),
        )
    )


def metrics_ns(*, with_video: bool = True, zeros: bool = False) -> SimpleNamespace:
    if zeros:
        m = SimpleNamespace(
            impressions=0,
            clicks=0,
            cost_micros=0,
            ctr=0.0,
            average_cpc=0,
            conversions=0.0,
            conversions_value=0.0,
            cost_per_conversion=0,
        )
    else:
        m = SimpleNamespace(
            impressions=1000,
            clicks=50,
            cost_micros=50_000_000,
            ctr=5.0,
            average_cpc=1_000_000,
            conversions=10.0,
            conversions_value=200.0,
            cost_per_conversion=5_000_000,
        )
    if with_video:
        m.video_views = 30
    return m


# =============================================================================
# Constructor / credential validation
# =============================================================================


class TestConstructor:
    def test_missing_developer_token_raises_value_error(self):
        with pytest.raises(ValueError, match="developer_token"):
            GoogleAdsAdapter({"client_id": "x"})

    def test_oauth_credentials_stored(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        assert adapter.developer_token == "dev-token"
        assert adapter.login_customer_id == "1234567890"
        assert adapter.client_id == OAUTH_CREDS["client_id"]
        assert adapter.refresh_token == OAUTH_CREDS["refresh_token"]
        assert adapter.client is None
        assert adapter._initialized is False

    def test_platform_property(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        assert adapter.platform == Platform.GOOGLE

    def test_rate_limiter_conservative_daily_budget(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        assert adapter.rate_limiter.calls_per_minute == 6
        assert adapter.rate_limiter.burst_size == 10


# =============================================================================
# initialize() / cleanup()
# =============================================================================


class TestInitialize:
    async def test_initialize_order_bug_always_raises(self):
        """BUG-1: initialize() verifies auth via get_accounts() before setting
        _initialized=True, so _ensure_initialized always raises AdapterError
        and initialize() can never complete successfully."""
        client, _services = make_client()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = []
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))

        with patch(f"{GOOGLE_ADAPTER_NS}.GoogleAdsClient") as mock_cls:
            mock_cls.load_from_dict.return_value = client
            with pytest.raises(AdapterError, match="not initialized"):
                await adapter.initialize()

        assert adapter._initialized is False

    async def test_initialize_oauth_config_and_mcc_verification(self):
        """Pre-setting _initialized (BUG-1 workaround) lets initialize()
        complete; it must build an OAuth config and verify via MCC query."""
        client, _services = make_client()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(
                customer_client=SimpleNamespace(
                    id=9876543210,
                    descriptive_name="Client One",
                    currency_code="USD",
                    time_zone="America/New_York",
                    manager=False,
                    status=SimpleNamespace(name="ENABLED"),
                )
            )
        ]
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        adapter._initialized = True  # BUG-1 workaround

        with patch(f"{GOOGLE_ADAPTER_NS}.GoogleAdsClient") as mock_cls:
            mock_cls.load_from_dict.return_value = client
            await adapter.initialize()

        config = mock_cls.load_from_dict.call_args[0][0]
        assert config["developer_token"] == "dev-token"
        assert config["use_proto_plus"] is True
        assert config["login_customer_id"] == "1234567890"
        assert config["client_id"] == OAUTH_CREDS["client_id"]
        assert config["client_secret"] == OAUTH_CREDS["client_secret"]
        assert config["refresh_token"] == OAUTH_CREDS["refresh_token"]
        assert "json_key_file_path" not in config
        assert adapter._initialized is True

    async def test_initialize_service_account_config_no_accounts_warning(self):
        """Service-account credentials select the json_key_file_path branch;
        an empty account list hits the 'no accounts' warning branch."""
        creds = {
            "developer_token": "dev-token",
            "json_key_file_path": "/keys/svc.json",
            "impersonated_email": "robot@example.com",
        }
        client, _services = make_client()
        adapter = GoogleAdsAdapter(creds)
        adapter._initialized = True  # BUG-1 workaround

        with patch(f"{GOOGLE_ADAPTER_NS}.GoogleAdsClient") as mock_cls:
            mock_cls.load_from_dict.return_value = client
            await adapter.initialize()

        config = mock_cls.load_from_dict.call_args[0][0]
        assert config["json_key_file_path"] == "/keys/svc.json"
        assert config["impersonated_email"] == "robot@example.com"
        assert "login_customer_id" not in config
        assert "client_id" not in config
        # No login_customer_id -> _get_single_account early-return [] (BUG-2)
        assert adapter._initialized is True

    async def test_initialize_authentication_error_mapped(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        with patch(f"{GOOGLE_ADAPTER_NS}.GoogleAdsClient") as mock_cls:
            mock_cls.load_from_dict.side_effect = make_google_error(
                code="AUTHENTICATION_ERROR", message="invalid grant"
            )
            with pytest.raises(AuthenticationError, match="authentication failed"):
                await adapter.initialize()

    async def test_initialize_generic_google_error_mapped(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        with patch(f"{GOOGLE_ADAPTER_NS}.GoogleAdsClient") as mock_cls:
            mock_cls.load_from_dict.side_effect = make_google_error(
                code="QUOTA_ERROR", message="too many requests"
            )
            with pytest.raises(AdapterError, match="QUOTA_ERROR: too many requests"):
                await adapter.initialize()

    async def test_cleanup_resets_state(self):
        adapter, _client, _ = make_adapter()
        await adapter.cleanup()
        assert adapter._initialized is False
        assert adapter.client is None

    async def test_calls_require_initialization(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await adapter.get_campaigns("1234567890")


# =============================================================================
# get_accounts
# =============================================================================


class TestGetAccounts:
    async def test_mcc_accounts_mapped(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(
                customer_client=SimpleNamespace(
                    id=9876543210,
                    descriptive_name="Client One",
                    currency_code="EUR",
                    time_zone="Europe/Berlin",
                    manager=False,
                    status=SimpleNamespace(name="ENABLED"),
                )
            ),
            SimpleNamespace(
                customer_client=SimpleNamespace(
                    id=5555555555,
                    descriptive_name="",
                    currency_code="USD",
                    time_zone="UTC",
                    manager=False,
                    status=SimpleNamespace(name="ENABLED"),
                )
            ),
        ]

        accounts = await adapter.get_accounts()

        assert len(accounts) == 2
        first = accounts[0]
        assert first.platform == Platform.GOOGLE.value
        assert first.account_id == "9876543210"
        assert first.account_name == "Client One"
        assert first.business_id == "1234567890"
        assert first.currency == "EUR"
        assert first.timezone == "Europe/Berlin"
        assert first.raw_data["currency"] == "EUR"
        # Empty descriptive_name falls back to "Account <id>"
        assert accounts[1].account_name == "Account 5555555555"
        # GAQL targets customer_client on the MCC id
        kwargs = ga.search.call_args.kwargs
        assert kwargs["customer_id"] == "1234567890"
        assert "FROM customer_client" in kwargs["query"]
        assert "customer_client.manager = false" in kwargs["query"]

    async def test_no_login_customer_id_returns_empty(self):
        creds = {k: v for k, v in OAUTH_CREDS.items() if k != "login_customer_id"}
        adapter, client, _ = make_adapter(credentials=creds)
        accounts = await adapter.get_accounts()
        assert accounts == []
        client.get_service("GoogleAdsService").search.assert_not_called()

    async def test_single_account_query_direct_call(self):
        """BUG-2: _get_single_account's GAQL path is dead in production
        (only invoked when login_customer_id is falsy, where it early-returns
        []). Exercise it directly to pin the mapping."""
        creds = {k: v for k, v in OAUTH_CREDS.items() if k != "login_customer_id"}
        adapter, client, _ = make_adapter(credentials=creds)
        adapter.login_customer_id = "1234567890"  # simulate the intended path
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(
                customer=SimpleNamespace(
                    id=1234567890,
                    descriptive_name=None,
                    currency_code="GBP",
                    time_zone="Europe/London",
                )
            )
        ]

        accounts = await adapter._get_single_account()

        assert len(accounts) == 1
        assert accounts[0].account_id == "1234567890"
        assert accounts[0].account_name == "Account 1234567890"
        assert accounts[0].currency == "GBP"
        assert "FROM customer" in ga.search.call_args.kwargs["query"]

    async def test_google_error_maps_to_platform_error(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(
            code="PERMISSION_DENIED", message="no access"
        )
        with pytest.raises(PlatformError, match="PERMISSION_DENIED: no access"):
            await adapter.get_accounts()


# =============================================================================
# get_campaigns
# =============================================================================


class TestGetCampaigns:
    async def test_campaigns_mapped_target_cpa(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [campaign_row()]

        campaigns = await adapter.get_campaigns("123-456-7890")

        assert len(campaigns) == 1
        c = campaigns[0]
        assert c.campaign_id == "111"
        assert c.campaign_name == "Campaign 111"
        assert c.status == EntityStatus.ACTIVE.value
        assert c.daily_budget == 25.0
        assert c.lifetime_budget is None
        assert c.bidding_strategy == BiddingStrategy.TARGET_CPA.value
        assert c.target_cpa == 5.0
        assert c.target_roas is None
        assert c.raw_data["channel_type"] == "SEARCH"
        assert c.raw_data["budget_id"] == 222
        # Dashes stripped from the customer id; no WHERE without filter
        kwargs = ga.search.call_args.kwargs
        assert kwargs["customer_id"] == "1234567890"
        assert "WHERE" not in kwargs["query"]

    async def test_status_filter_builds_where_clause(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = []

        await adapter.get_campaigns(
            "1234567890",
            status_filter=[EntityStatus.PAUSED, EntityStatus.ARCHIVED],
        )

        query = ga.search.call_args.kwargs["query"]
        # PAUSED maps directly; ARCHIVED has no Google mapping -> ENABLED
        assert "WHERE campaign.status IN ('PAUSED', 'ENABLED')" in query

    async def test_bidding_strategy_variants(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            campaign_row(
                campaign_id=1,
                strategy="TARGET_ROAS",
                target_roas=3.5,
                status="PAUSED",
            ),
            campaign_row(campaign_id=2, strategy="MAXIMIZE_CONVERSIONS"),
            campaign_row(
                campaign_id=3,
                strategy="MAXIMIZE_CONVERSION_VALUE",
                total_amount_micros=900_000_000,
            ),
            campaign_row(campaign_id=4, strategy=None, status="REMOVED"),
            campaign_row(campaign_id=5, status="UNSPECIFIED"),
        ]

        campaigns = await adapter.get_campaigns("1234567890")

        by_id = {c.campaign_id: c for c in campaigns}
        assert by_id["1"].bidding_strategy == BiddingStrategy.TARGET_ROAS.value
        assert by_id["1"].target_roas == 3.5
        assert by_id["1"].status == EntityStatus.PAUSED.value
        assert by_id["2"].bidding_strategy == BiddingStrategy.MAXIMIZE_CONVERSIONS.value
        assert by_id["3"].bidding_strategy == BiddingStrategy.MAXIMIZE_VALUE.value
        assert by_id["3"].lifetime_budget == 900.0
        # No strategy type -> MANUAL_CPC default
        assert by_id["4"].bidding_strategy == BiddingStrategy.MANUAL_CPC.value
        assert by_id["4"].status == EntityStatus.DELETED.value
        assert by_id["5"].status == EntityStatus.ACTIVE.value

    async def test_google_error_maps_to_platform_error(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(empty=True)
        with pytest.raises(PlatformError, match="Failed to fetch campaigns"):
            await adapter.get_campaigns("1234567890")


# =============================================================================
# get_adsets (ad groups)
# =============================================================================


class TestGetAdsets:
    async def test_adsets_mapped(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [adset_row()]

        adsets = await adapter.get_adsets("1234567890")

        assert len(adsets) == 1
        a = adsets[0]
        assert a.adset_id == "333"
        assert a.adset_name == "AdGroup 333"
        assert a.campaign_id == "111"  # parsed from resource name
        assert a.status == EntityStatus.PAUSED.value
        assert a.bid_amount == 2.5
        assert "WHERE" not in ga.search.call_args.kwargs["query"]

    async def test_campaign_filter_and_zero_bid(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            adset_row(campaign_resource="", cpc_bid_micros=0, status="ENABLED")
        ]

        adsets = await adapter.get_adsets("1234567890", campaign_id="111")

        query = ga.search.call_args.kwargs["query"]
        assert "ad_group.campaign = 'customers/1234567890/campaigns/111'" in query
        assert adsets[0].campaign_id == ""
        assert adsets[0].bid_amount is None
        assert adsets[0].status == EntityStatus.ACTIVE.value

    async def test_google_error_maps_to_platform_error(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(message="bad ad group")
        with pytest.raises(PlatformError, match="Failed to fetch ad groups"):
            await adapter.get_adsets("1234567890")


# =============================================================================
# get_ads
# =============================================================================


class TestGetAds:
    async def test_ads_mapped_with_rsa_content(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [ad_row()]

        ads = await adapter.get_ads("1234567890")

        assert len(ads) == 1
        ad = ads[0]
        assert ad.ad_id == "444"
        assert ad.ad_name == "My RSA"
        assert ad.adset_id == "333"
        assert ad.headline == "H1"
        assert ad.description == "D1"
        assert ad.destination_url == "https://x.example"
        assert ad.status == EntityStatus.ACTIVE.value
        assert ad.raw_data["type"] == "RESPONSIVE_SEARCH_AD"

    async def test_adset_filter_and_fallbacks(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            ad_row(
                ad_id=445,
                name=None,
                with_rsa=False,
                final_urls=[],
                status="PAUSED",
            ),
            ad_row(ad_id=446, headline_text=""),
        ]

        ads = await adapter.get_ads("1234567890", adset_id="333")

        query = ga.search.call_args.kwargs["query"]
        assert "ad_group_ad.ad_group = 'customers/1234567890/adGroups/333'" in query
        bare = ads[0]
        assert bare.ad_name == "Ad 445"  # name fallback
        assert bare.headline == ""
        assert bare.description == ""
        assert bare.destination_url == ""
        assert bare.status == EntityStatus.PAUSED.value
        # Empty headline text falls back to ""
        assert ads[1].headline == ""

    async def test_google_error_maps_to_platform_error(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(message="no ads for you")
        with pytest.raises(PlatformError, match="Failed to fetch ads"):
            await adapter.get_ads("1234567890")


# =============================================================================
# get_metrics
# =============================================================================


class TestGetMetrics:
    DATE_START = datetime(2026, 6, 1, tzinfo=UTC)
    DATE_END = datetime(2026, 6, 30, tzinfo=UTC)

    async def test_campaign_metrics_with_derived_values(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(campaign=SimpleNamespace(id=111), metrics=metrics_ns())
        ]

        result = await adapter.get_metrics(
            "123-456-7890",
            "campaign",
            ["111"],
            self.DATE_START,
            self.DATE_END,
        )

        assert set(result.keys()) == {"111"}
        m = result["111"]
        assert m.impressions == 1000
        assert m.clicks == 50
        assert m.spend == 50.0
        assert m.cpc == 1.0
        assert m.conversions == 10
        assert m.conversion_value == 200.0
        assert m.cpa == 5.0
        assert m.roas == 4.0  # 200 / 50
        assert m.video_views == 30
        assert m.date_start == self.DATE_START
        # GAQL includes date range + id filter, dashes stripped
        kwargs = ga.search.call_args.kwargs
        assert kwargs["customer_id"] == "1234567890"
        assert "BETWEEN '2026-06-01'" in kwargs["query"]
        assert "'2026-06-30'" in kwargs["query"]
        assert "campaign.id IN (111)" in kwargs["query"]
        assert "FROM campaign" in kwargs["query"]

    async def test_adset_metrics_resource_and_key(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(
                ad_group=SimpleNamespace(id=333),
                metrics=metrics_ns(with_video=False),
            )
        ]

        result = await adapter.get_metrics(
            "1234567890", "adset", [], self.DATE_START, self.DATE_END
        )

        assert set(result.keys()) == {"333"}
        assert result["333"].video_views is None  # hasattr False branch
        query = ga.search.call_args.kwargs["query"]
        assert "FROM ad_group" in query
        assert "IN (" not in query  # no entity filter for empty ids

    async def test_ad_metrics_zero_row(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            SimpleNamespace(
                ad_group_ad=SimpleNamespace(ad=SimpleNamespace(id=444)),
                metrics=metrics_ns(zeros=True),
            )
        ]

        result = await adapter.get_metrics(
            "1234567890", "ad", ["444"], self.DATE_START, self.DATE_END
        )

        m = result["444"]
        assert m.impressions == 0
        assert m.spend == 0
        assert m.ctr is None
        assert m.cpc is None
        assert m.conversions is None
        assert m.roas is None
        assert "FROM ad_group_ad" in ga.search.call_args.kwargs["query"]

    async def test_google_error_maps_to_platform_error(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(message="metric meltdown")
        with pytest.raises(PlatformError, match="Failed to fetch metrics"):
            await adapter.get_metrics(
                "1234567890", "campaign", [], self.DATE_START, self.DATE_END
            )


# =============================================================================
# get_emq_scores
# =============================================================================


class TestGetEmqScores:
    @staticmethod
    def _conversion_row(name: str, type_name: str) -> SimpleNamespace:
        return SimpleNamespace(
            conversion_action=SimpleNamespace(
                id=1,
                name=name,
                type_=SimpleNamespace(name=type_name),
                status=SimpleNamespace(name="ENABLED"),
            )
        )

    async def test_scores_by_conversion_type(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.return_value = [
            self._conversion_row("offline_purchase", "UPLOAD_CLICKS"),
            self._conversion_row("call_lead", "UPLOAD_CALLS"),
            self._conversion_row("web_purchase", "WEBPAGE"),
            self._conversion_row("app_install", "GOOGLE_PLAY"),
        ]

        scores = await adapter.get_emq_scores("1234567890")

        by_event = {s.event_name: s.score for s in scores}
        assert by_event == {
            "offline_purchase": 7.0,
            "call_lead": 7.0,
            "web_purchase": 6.0,
            "app_install": 5.0,
        }
        assert all(s.platform == Platform.GOOGLE.value for s in scores)
        assert all(s.last_updated is not None for s in scores)
        assert "FROM conversion_action" in ga.search.call_args.kwargs["query"]

    async def test_google_error_swallowed_returns_empty(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        ga.search.side_effect = make_google_error(message="diag unavailable")
        assert await adapter.get_emq_scores("1234567890") == []


# =============================================================================
# execute_action
# =============================================================================


def make_action(
    action_type: str,
    entity_type: str = "campaign",
    entity_id: str = "111",
    parameters: dict | None = None,
    account_id: str = "123-456-7890",
) -> AutomationAction:
    return AutomationAction(
        platform=Platform.GOOGLE,
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action_type,
        parameters=parameters or {},
    )


class TestExecuteActionUpdateBudget:
    async def test_update_budget_success(self):
        adapter, client, _ = make_adapter()
        ga = client.get_service("GoogleAdsService")
        budget_rn = "customers/1234567890/campaignBudgets/222"
        ga.search.return_value = [
            SimpleNamespace(campaign=SimpleNamespace(campaign_budget=budget_rn))
        ]
        budget_svc = client.get_service("CampaignBudgetService")

        action = make_action("update_budget", parameters={"daily_budget": 50.0})
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        assert result.executed_at is not None
        assert result.result == {"updated_budget": budget_rn}
        # Budget lookup GAQL targets the campaign id, dashes stripped
        kwargs = ga.search.call_args.kwargs
        assert kwargs["customer_id"] == "1234567890"
        assert "campaign.id = 111" in kwargs["query"]
        # Mutation payload: micros conversion + field mask
        mutate_kwargs = budget_svc.mutate_campaign_budgets.call_args.kwargs
        assert mutate_kwargs["customer_id"] == "1234567890"
        op = mutate_kwargs["operations"][0]
        assert op.update.resource_name == budget_rn
        assert op.update.amount_micros == 50_000_000
        mask = op.update_mask.CopyFrom.call_args[0][0]
        assert list(mask.paths) == ["amount_micros"]

    async def test_update_budget_missing_budget_fails_action(self):
        adapter, client, _ = make_adapter()
        client.get_service("GoogleAdsService").search.return_value = []

        action = make_action("update_budget", parameters={"daily_budget": 50.0})
        result = await adapter.execute_action(action)

        assert result.status == "failed"
        assert "Could not find budget for campaign 111" in result.error_message
        assert result.executed_at is None

    async def test_update_budget_google_error_fails_action(self):
        adapter, client, _ = make_adapter()
        client.get_service("GoogleAdsService").search.side_effect = make_google_error(
            code="RATE_LIMIT", message="slow down"
        )

        action = make_action("update_budget", parameters={"daily_budget": 50.0})
        result = await adapter.execute_action(action)

        assert result.status == "failed"
        assert result.error_message == "RATE_LIMIT: slow down"


class TestExecuteActionUpdateBid:
    async def test_campaign_bid_target_cpa_and_roas(self):
        adapter, client, _ = make_adapter()
        campaign_svc = client.get_service("CampaignService")

        action = make_action(
            "update_bid",
            entity_type="campaign",
            parameters={"target_cpa": 12.5, "target_roas": 4.2},
        )
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        assert sorted(result.result["updated_fields"]) == [
            "target_cpa",
            "target_roas",
        ]
        op = campaign_svc.mutate_campaigns.call_args.kwargs["operations"][0]
        assert op.update.resource_name == "customers/1234567890/campaigns/111"
        assert op.update.target_cpa.target_cpa_micros == 12_500_000
        assert op.update.target_roas.target_roas == 4.2
        mask = op.update_mask.CopyFrom.call_args[0][0]
        assert list(mask.paths) == [
            "target_cpa.target_cpa_micros",
            "target_roas.target_roas",
        ]

    async def test_adgroup_bid_amount(self):
        adapter, client, _ = make_adapter()
        ag_svc = client.get_service("AdGroupService")

        action = make_action(
            "update_bid",
            entity_type="adset",
            entity_id="333",
            parameters={"bid_amount": 2.75},
        )
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        op = ag_svc.mutate_ad_groups.call_args.kwargs["operations"][0]
        assert op.update.resource_name == "customers/1234567890/adGroups/333"
        assert op.update.cpc_bid_micros == 2_750_000
        mask = op.update_mask.CopyFrom.call_args[0][0]
        assert list(mask.paths) == ["cpc_bid_micros"]


class TestExecuteActionUpdateStatus:
    async def test_campaign_pause(self):
        adapter, client, _ = make_adapter()
        campaign_svc = client.get_service("CampaignService")

        action = make_action("update_status", parameters={"status": "paused"})
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        assert result.result == {"new_status": "PAUSED"}
        op = campaign_svc.mutate_campaigns.call_args.kwargs["operations"][0]
        assert op.update.resource_name == "customers/1234567890/campaigns/111"
        mask = op.update_mask.CopyFrom.call_args[0][0]
        assert list(mask.paths) == ["status"]
        client.enums.CampaignStatusEnum.__getitem__.assert_called_with("PAUSED")

    async def test_adset_enable(self):
        adapter, client, _ = make_adapter()
        ag_svc = client.get_service("AdGroupService")

        action = make_action(
            "update_status",
            entity_type="adset",
            entity_id="333",
            parameters={"status": "active"},
        )
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        assert result.result == {"new_status": "ENABLED"}
        op = ag_svc.mutate_ad_groups.call_args.kwargs["operations"][0]
        assert op.update.resource_name == "customers/1234567890/adGroups/333"
        client.enums.AdGroupStatusEnum.__getitem__.assert_called_with("ENABLED")

    async def test_invalid_status_value_fails_action(self):
        adapter, _client, _ = make_adapter()
        action = make_action("update_status", parameters={"status": "not-a-status"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "not-a-status" in result.error_message


class TestExecuteActionCreateCampaign:
    async def test_create_campaign_maximize_conversions(self):
        adapter, client, _ = make_adapter()
        budget_svc = client.get_service("CampaignBudgetService")
        budget_rn = "customers/1234567890/campaignBudgets/900"
        budget_svc.mutate_campaign_budgets.return_value.results = [
            SimpleNamespace(resource_name=budget_rn)
        ]
        campaign_svc = client.get_service("CampaignService")
        campaign_rn = "customers/1234567890/campaigns/901"
        campaign_svc.mutate_campaigns.return_value.results = [
            SimpleNamespace(resource_name=campaign_rn)
        ]

        action = make_action(
            "create_campaign",
            entity_id="new",
            parameters={
                "name": "Summer Push",
                "daily_budget": 40.0,
                "bidding_strategy": "maximize_conversions",
            },
        )
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        assert result.result == {"campaign_resource_name": campaign_rn}
        budget_op = budget_svc.mutate_campaign_budgets.call_args.kwargs["operations"][0]
        assert budget_op.create.name == "Summer Push Budget"
        assert budget_op.create.amount_micros == 40_000_000
        campaign_op = campaign_svc.mutate_campaigns.call_args.kwargs["operations"][0]
        assert campaign_op.create.name == "Summer Push"
        assert campaign_op.create.campaign_budget == budget_rn
        assert campaign_op.create.maximize_conversions.target_cpa_micros == 0
        # Default channel type SEARCH
        client.enums.AdvertisingChannelTypeEnum.__getitem__.assert_called_with("SEARCH")

    async def test_create_campaign_target_cpa_custom_channel(self):
        adapter, client, _ = make_adapter()
        budget_svc = client.get_service("CampaignBudgetService")
        budget_svc.mutate_campaign_budgets.return_value.results = [
            SimpleNamespace(resource_name="customers/1/campaignBudgets/1")
        ]
        campaign_svc = client.get_service("CampaignService")
        campaign_svc.mutate_campaigns.return_value.results = [
            SimpleNamespace(resource_name="customers/1/campaigns/2")
        ]

        action = make_action(
            "create_campaign",
            entity_id="new",
            parameters={
                "name": "Display Reach",
                "channel_type": "DISPLAY",
                "bidding_strategy": "target_cpa",
                "target_cpa": 8.0,
            },
        )
        result = await adapter.execute_action(action)

        assert result.status == "completed"
        campaign_op = campaign_svc.mutate_campaigns.call_args.kwargs["operations"][0]
        assert campaign_op.create.target_cpa.target_cpa_micros == 8_000_000
        client.enums.AdvertisingChannelTypeEnum.__getitem__.assert_called_with(
            "DISPLAY"
        )

    async def test_create_campaign_missing_name_fails_action(self):
        adapter, client, _ = make_adapter()
        client.get_service("CampaignBudgetService")
        action = make_action("create_campaign", entity_id="new", parameters={})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "'name'" in result.error_message


class TestExecuteActionDispatch:
    async def test_unsupported_action_type_fails(self):
        adapter, _client, _ = make_adapter()
        action = make_action("delete_everything")
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Unsupported action type: delete_everything" in result.error_message

    async def test_requires_initialization(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await adapter.execute_action(make_action("update_budget"))


# =============================================================================
# Creative operations
# =============================================================================


class TestCreativeOperations:
    async def test_upload_image_returns_asset_resource_name(self):
        adapter, client, _ = make_adapter()
        asset_svc = client.get_service("AssetService")
        asset_rn = "customers/1234567890/assets/777"
        asset_svc.mutate_assets.return_value.results = [
            SimpleNamespace(resource_name=asset_rn)
        ]

        result = await adapter.upload_image(
            "123-456-7890", b"\x89PNG-bytes", "hero.png"
        )

        assert result == asset_rn
        mutate_kwargs = asset_svc.mutate_assets.call_args.kwargs
        assert mutate_kwargs["customer_id"] == "1234567890"
        op = mutate_kwargs["operations"][0]
        assert op.create.name == "hero.png"
        assert op.create.image_asset.data == b"\x89PNG-bytes"

    async def test_upload_video_unsupported_returns_empty(self):
        adapter, _client, _ = make_adapter()
        result = await adapter.upload_video("1234567890", b"video", "clip.mp4")
        assert result == ""


# =============================================================================
# Helper / mapping methods
# =============================================================================


class TestHelpers:
    def test_parse_google_error_joins_all_errors(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        exc = GoogleAdsException(
            None,
            None,
            SimpleNamespace(
                errors=[
                    SimpleNamespace(error_code="A", message="first"),
                    SimpleNamespace(error_code="B", message="second"),
                ]
            ),
            "req-1",
        )
        assert adapter._parse_google_error(exc) == "A: first; B: second"

    def test_parse_google_error_empty_falls_back_to_str(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        exc = make_google_error(empty=True)
        assert adapter._parse_google_error(exc) == str(exc)

    def test_status_mapping_round_trip(self):
        adapter = GoogleAdsAdapter(dict(OAUTH_CREDS))
        assert adapter._map_status_to_platform(EntityStatus.PAUSED) == "PAUSED"
        assert adapter._map_status_to_platform(EntityStatus.ACTIVE) == "ENABLED"
        # Unmapped unified status defaults to ENABLED
        assert adapter._map_status_to_platform(EntityStatus.ARCHIVED) == "ENABLED"
        assert adapter._map_status_from_platform("REMOVED") == EntityStatus.DELETED
        assert adapter._map_status_from_platform("UNKNOWN") == EntityStatus.ACTIVE
        # Unmapped platform status defaults to ACTIVE
        assert adapter._map_status_from_platform("WEIRD") == EntityStatus.ACTIVE
