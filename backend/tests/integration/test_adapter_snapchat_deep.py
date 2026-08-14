# =============================================================================
# Stratum AI - Snapchat Adapter Deep Integration Tests
# =============================================================================
"""Deep coverage tests for ``app.stratum.adapters.snapchat_adapter``.

The Snapchat adapter holds a long-lived ``httpx.AsyncClient`` on ``self.session``
and opens a second, short-lived one for the OAuth token refresh, so these tests
stub the client boundary with an in-memory async fake instead of respx. Both
usages resolve the same ``httpx.AsyncClient`` symbol, so ``FakeAsyncClient``
doubles as an async context manager and ``fake_client_factory`` hands out the
session client first and the token client second — the order ``initialize``
constructs them. Covers: credential validation, token refresh
and expiry handling, initialize/cleanup lifecycle, account/campaign/adsquad/ad
fetch + unified model mapping, stats aggregation, EMQ estimation,
budget/status/create mutations via ``execute_action``, media uploads,
``_make_request`` error mapping (429 -> RateLimitError), and helpers.

Behaviors pinned here (fixed under #540):

* ``execute_action`` catches ``PlatformError`` / ``RateLimitError`` raised by
  ``_make_request`` and marks the action ``status="failed"`` with the error
  message, instead of letting it propagate and stick in ``"executing"``.
* ``get_emq_scores`` degrades gracefully to ``[]`` when ``_make_request`` wraps
  an HTTP failure into ``PlatformError`` (or ``RateLimitError`` on 429).
* ``_update_budget`` bodies carry the entity ``id`` field (consistent with
  ``_update_status``). Note ``get_ads(adset_id=...)`` still yields ads with an
  empty ``campaign_id`` (the direct-adset path has no campaign context).
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    PlatformError,
    RateLimitError,
)
from app.stratum.adapters.snapchat_adapter import SnapchatAdapter
from app.stratum.models import AutomationAction, EntityStatus, Platform

pytestmark = pytest.mark.integration


# =============================================================================
# Fakes for the httpx transport boundary
# =============================================================================


class FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    """Queue-driven fake of httpx.AsyncClient recording every call.

    Serves both ways the adapter uses the class: assigned to ``self.session``
    for the lifetime of the adapter, and entered as ``async with`` in the token
    refresh path — hence both ``aclose`` and the async context-manager methods.
    """

    def __init__(self, queue=None, **kwargs):
        self.queue = list(queue or [])
        self.calls = []
        self.headers = {}
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def _next(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.queue:
            raise AssertionError(f"No queued response for {method} {url}")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def get(self, url, headers=None, params=None, **kwargs):
        return self._next("GET", url, headers=headers, params=params)

    async def post(self, url, headers=None, json=None, data=None, **kwargs):
        return self._next("POST", url, headers=headers, json=json, data=data)

    async def put(self, url, headers=None, json=None, **kwargs):
        return self._next("PUT", url, headers=headers, json=json)

    async def request(self, method, url, headers=None, json=None, **kwargs):
        return self._next(method, url, headers=headers, json=json)

    async def aclose(self):
        self.closed = True


# Backwards-compatible alias: the tests below were written against the
# requests.Session-era name.
FakeSession = FakeAsyncClient


def fake_client_factory(session_client, token_handler=None):
    """Stand in for the ``httpx.AsyncClient`` symbol during ``initialize``.

    ``initialize`` constructs the class twice — first for ``self.session``,
    then inside ``_refresh_access_token`` — so hand out the session client on
    the first call and a token client on every call after it.

    Pass ``session_client=None`` when the test drives ``_refresh_access_token``
    directly: there is no session to build, so every construction is a token
    client.
    """

    class _TokenClient(FakeAsyncClient):
        async def post(self, url, headers=None, json=None, data=None, **kwargs):
            self.calls.append({"method": "POST", "url": url, "data": data})
            if token_handler is None:
                return token_response()
            return token_handler(url, data)

    state = {"n": 0}

    def _make(*args, **kwargs):
        state["n"] += 1
        if session_client is not None and state["n"] == 1:
            return session_client
        return _TokenClient()

    return _make


CREDS = {
    "client_id": "cid-1",
    "client_secret": "csecret",
    "refresh_token": "rtok-1",
    "organization_id": "org-1",
    "ad_account_id": "acct-1",
}


def make_adapter(queue=None, creds=None):
    """Build an already-initialized adapter with a valid token + fake session."""
    adapter = SnapchatAdapter(dict(creds or CREDS))
    adapter.session = FakeSession(queue)
    adapter._initialized = True
    adapter.access_token = "tok-abc"
    adapter.token_expires_at = datetime.now(UTC) + timedelta(hours=1)
    return adapter


def token_response(access="tok-new", expires_in=3600, refresh=None):
    payload = {"access_token": access, "expires_in": expires_in}
    if refresh:
        payload["refresh_token"] = refresh
    return FakeResponse(payload)


# =============================================================================
# Construction, OAuth, lifecycle
# =============================================================================


class TestInitAndAuth:
    def test_missing_credentials_raise_value_error(self):
        with pytest.raises(ValueError, match="client_secret"):
            SnapchatAdapter({"client_id": "x", "refresh_token": "y"})

    def test_all_missing_credentials_listed(self):
        with pytest.raises(ValueError) as exc:
            SnapchatAdapter({})
        msg = str(exc.value)
        assert "client_id" in msg
        assert "client_secret" in msg
        assert "refresh_token" in msg

    def test_platform_property(self):
        assert SnapchatAdapter(CREDS).platform == Platform.SNAPCHAT

    async def test_refresh_access_token_success(self, monkeypatch):
        posts = []

        def fake_post(url, data=None):
            posts.append({"url": url, "data": data})
            return token_response(access="tok-1", expires_in=1800, refresh="rtok-2")

        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(None, fake_post),
        )
        adapter = SnapchatAdapter(dict(CREDS))
        before = datetime.now(UTC)
        await adapter._refresh_access_token()

        assert adapter.access_token == "tok-1"
        assert adapter.refresh_token == "rtok-2"  # rotated
        # Expiry has the 60s safety margin applied
        assert adapter.token_expires_at <= before + timedelta(seconds=1800)
        assert adapter.token_expires_at >= before + timedelta(seconds=1700)

        call = posts[0]
        assert call["url"] == SnapchatAdapter.AUTH_URL
        assert call["data"]["grant_type"] == "refresh_token"
        assert call["data"]["client_id"] == "cid-1"
        assert call["data"]["refresh_token"] == "rtok-1"

    async def test_refresh_defaults_expiry_when_missing(self, monkeypatch):
        def fake_post(url, data=None):
            return FakeResponse({"access_token": "tok-2"})  # no expires_in

        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(None, fake_post),
        )
        adapter = SnapchatAdapter(dict(CREDS))
        await adapter._refresh_access_token()
        assert adapter.access_token == "tok-2"
        assert adapter.refresh_token == "rtok-1"  # unchanged
        assert adapter.token_expires_at is not None

    async def test_ensure_valid_token_refreshes_when_expired(self, monkeypatch):
        adapter = make_adapter([])
        adapter.token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        calls = []

        async def fake_refresh():
            calls.append(1)

        monkeypatch.setattr(adapter, "_refresh_access_token", fake_refresh)
        await adapter._ensure_valid_token()
        assert calls == [1]

    async def test_ensure_valid_token_refreshes_when_no_token(self, monkeypatch):
        adapter = make_adapter([])
        adapter.access_token = None
        calls = []

        async def fake_refresh():
            calls.append(1)

        monkeypatch.setattr(adapter, "_refresh_access_token", fake_refresh)
        await adapter._ensure_valid_token()
        assert calls == [1]

    async def test_ensure_valid_token_noop_when_valid(self, monkeypatch):
        adapter = make_adapter([])

        async def fake_refresh():  # pragma: no cover - must not run
            raise AssertionError("should not refresh")

        monkeypatch.setattr(adapter, "_refresh_access_token", fake_refresh)
        await adapter._ensure_valid_token()

    async def test_initialize_success_adopts_org_from_me(self, monkeypatch):
        fake = FakeSession([FakeResponse({"me": {"organization_id": "org-9"}})])
        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(fake),
        )
        creds = {k: v for k, v in CREDS.items() if k != "organization_id"}
        adapter = SnapchatAdapter(creds)
        await adapter.initialize()
        assert adapter._initialized is True
        assert adapter.access_token == "tok-new"
        assert adapter.organization_id == "org-9"
        # Bearer header sent on the /me verification call
        assert fake.calls[0]["headers"]["Authorization"] == "Bearer tok-new"
        assert fake.calls[0]["url"].endswith("/me")

    async def test_initialize_keeps_configured_org(self, monkeypatch):
        fake = FakeSession([FakeResponse({"me": {"organization_id": "org-9"}})])
        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(fake),
        )
        adapter = SnapchatAdapter(dict(CREDS))
        await adapter.initialize()
        assert adapter.organization_id == "org-1"

    async def test_initialize_auth_failure_raises(self, monkeypatch):
        fake = FakeSession([FakeResponse({"request_status": "ERROR"})])
        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(fake),
        )
        adapter = SnapchatAdapter(dict(CREDS))
        with pytest.raises(AuthenticationError, match="verify"):
            await adapter.initialize()
        assert adapter._initialized is False

    async def test_initialize_token_network_failure_raises_adapter_error(
        self, monkeypatch
    ):
        def boom(url, data=None):
            raise httpx.ConnectError("no route")

        monkeypatch.setattr(
            "app.stratum.adapters.snapchat_adapter.httpx.AsyncClient",
            fake_client_factory(FakeAsyncClient([]), boom),
        )
        adapter = SnapchatAdapter(dict(CREDS))
        with pytest.raises(AdapterError, match="Failed to connect"):
            await adapter.initialize()

    async def test_cleanup_resets_state(self):
        adapter = make_adapter([])
        session = adapter.session
        await adapter.cleanup()
        assert session.closed is True
        assert adapter.session is None
        assert adapter.access_token is None
        assert adapter._initialized is False

    async def test_cleanup_without_session_is_noop(self):
        adapter = SnapchatAdapter(dict(CREDS))
        await adapter.cleanup()
        assert adapter._initialized is False

    async def test_ensure_initialized_guard(self):
        adapter = SnapchatAdapter(dict(CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await adapter.get_campaigns("acct-1")


# =============================================================================
# Accounts
# =============================================================================


class TestGetAccounts:
    async def test_success_with_known_org(self):
        aa = {
            "id": "acct-1",
            "name": "Snap Acme",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
        }
        adapter = make_adapter([FakeResponse({"adaccounts": [{"adaccount": aa}]})])
        accounts = await adapter.get_accounts()
        assert len(accounts) == 1
        acc = accounts[0]
        assert acc.platform == Platform.SNAPCHAT.value
        assert acc.account_id == "acct-1"
        assert acc.account_name == "Snap Acme"
        assert acc.business_id == "org-1"
        assert acc.timezone == "Europe/Berlin"
        assert acc.currency == "EUR"
        assert acc.raw_data == aa
        assert adapter.session.calls[0]["url"].endswith(
            "/organizations/org-1/adaccounts"
        )

    async def test_discovers_org_when_missing(self):
        adapter = make_adapter(
            [
                FakeResponse({"organizations": [{"organization": {"id": "org-7"}}]}),
                FakeResponse({"adaccounts": [{"adaccount": {"id": "a2"}}]}),
            ]
        )
        adapter.organization_id = None
        accounts = await adapter.get_accounts()
        assert adapter.organization_id == "org-7"
        assert accounts[0].account_id == "a2"
        assert accounts[0].account_name == "Unknown"
        assert adapter.session.calls[0]["url"].endswith("/me/organizations")

    async def test_no_org_found_returns_empty(self):
        adapter = make_adapter([FakeResponse({"organizations": []})])
        adapter.organization_id = None
        assert await adapter.get_accounts() == []

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([FakeResponse({"adaccounts": 3})])
        with pytest.raises(PlatformError, match="Failed to parse account data"):
            await adapter.get_accounts()

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([TimeoutError("socket timeout")])
        with pytest.raises(PlatformError, match="Failed to fetch accounts"):
            await adapter.get_accounts()

    async def test_http_error_surfaces_as_make_request_platform_error(self):
        # HTTPError is wrapped by _make_request itself; the outer except in
        # get_accounts never sees a RequestException.
        adapter = make_adapter([FakeResponse({}, status_code=500)])
        with pytest.raises(PlatformError, match="Snapchat API request failed"):
            await adapter.get_accounts()


# =============================================================================
# Campaigns
# =============================================================================


def campaign_item(**overrides):
    c = {
        "id": "c-1",
        "name": "Summer Snap",
        "status": "PAUSED",
        "daily_budget_micro": 50_000_000,
        "lifetime_spend_cap_micro": 900_000_000,
        "created_at": "2026-01-15T10:30:00.000Z",
        "updated_at": "2026-02-01T08:00:00.000Z",
    }
    c.update(overrides)
    return {"campaign": c}


class TestGetCampaigns:
    async def test_success_maps_unified_campaign(self):
        adapter = make_adapter([FakeResponse({"campaigns": [campaign_item()]})])
        campaigns = await adapter.get_campaigns("acct-1")
        assert len(campaigns) == 1
        c = campaigns[0]
        assert c.campaign_id == "c-1"
        assert c.campaign_name == "Summer Snap"
        assert c.status == EntityStatus.PAUSED.value
        assert c.daily_budget == 50.0
        assert c.lifetime_budget == 900.0
        assert c.created_at == datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        assert c.updated_at == datetime(2026, 2, 1, 8, 0, tzinfo=UTC)
        assert adapter.session.calls[0]["url"].endswith("/adaccounts/acct-1/campaigns")

    async def test_status_filter_excludes_non_matching(self):
        adapter = make_adapter(
            [
                FakeResponse(
                    {
                        "campaigns": [
                            campaign_item(id="c-1", status="PAUSED"),
                            campaign_item(id="c-2", status="ACTIVE"),
                            campaign_item(id="c-3", status="PENDING"),
                        ]
                    }
                )
            ]
        )
        campaigns = await adapter.get_campaigns(
            "acct-1", status_filter=[EntityStatus.ACTIVE]
        )
        assert [c.campaign_id for c in campaigns] == ["c-2"]

    async def test_pending_status_maps_to_pending_review(self):
        adapter = make_adapter(
            [FakeResponse({"campaigns": [campaign_item(status="PENDING")]})]
        )
        c = (await adapter.get_campaigns("acct-1"))[0]
        assert c.status == EntityStatus.PENDING_REVIEW.value

    async def test_missing_budgets_map_to_none(self):
        item = {"campaign": {"id": "c-9", "name": "bare"}}
        adapter = make_adapter([FakeResponse({"campaigns": [item]})])
        c = (await adapter.get_campaigns("acct-1"))[0]
        assert c.daily_budget is None
        assert c.lifetime_budget is None
        assert c.created_at is None

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter(
            [FakeResponse({"campaigns": [campaign_item(daily_budget_micro="abc")]})]
        )
        with pytest.raises(PlatformError, match="Failed to parse campaign data"):
            await adapter.get_campaigns("acct-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([ConnectionError("reset")])
        with pytest.raises(PlatformError, match="Failed to fetch campaigns"):
            await adapter.get_campaigns("acct-1")


# =============================================================================
# Ad squads (adsets)
# =============================================================================


def adsquad_item(**overrides):
    sq = {
        "id": "sq-1",
        "name": "Squad One",
        "status": "ACTIVE",
        "daily_budget_micro": 25_000_000,
        "lifetime_budget_micro": 100_000_000,
        "bid_micro": 1_500_000,
        "start_time": "2026-06-01T00:00:00.000Z",
        "end_time": "2026-06-30T00:00:00.000Z",
    }
    sq.update(overrides)
    return {"adsquad": sq}


class TestGetAdsets:
    async def test_with_campaign_id_fetches_directly(self):
        adapter = make_adapter([FakeResponse({"adsquads": [adsquad_item()]})])
        adsets = await adapter.get_adsets("acct-1", campaign_id="c-1")
        assert len(adsets) == 1
        a = adsets[0]
        assert a.adset_id == "sq-1"
        assert a.adset_name == "Squad One"
        assert a.campaign_id == "c-1"
        assert a.status == EntityStatus.ACTIVE.value
        assert a.daily_budget == 25.0
        assert a.lifetime_budget == 100.0
        assert a.bid_amount == 1.5
        assert a.start_time == datetime(2026, 6, 1, tzinfo=UTC)
        assert a.end_time == datetime(2026, 6, 30, tzinfo=UTC)
        assert adapter.session.calls[0]["url"].endswith("/campaigns/c-1/adsquads")

    async def test_without_campaign_id_walks_all_campaigns(self):
        adapter = make_adapter(
            [
                FakeResponse(
                    {
                        "campaigns": [
                            campaign_item(id="c-1"),
                            campaign_item(id="c-2"),
                        ]
                    }
                ),
                FakeResponse({"adsquads": [adsquad_item(id="sq-1")]}),
                FakeResponse({"adsquads": [adsquad_item(id="sq-2")]}),
            ]
        )
        adsets = await adapter.get_adsets("acct-1")
        assert [a.adset_id for a in adsets] == ["sq-1", "sq-2"]
        assert [a.campaign_id for a in adsets] == ["c-1", "c-2"]
        assert len(adapter.session.calls) == 3

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([FakeResponse({"adsquads": 5})])
        with pytest.raises(PlatformError, match="Failed to parse ad squad data"):
            await adapter.get_adsets("acct-1", campaign_id="c-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([TimeoutError()])
        with pytest.raises(PlatformError, match="Failed to fetch ad squads"):
            await adapter.get_adsets("acct-1", campaign_id="c-1")


# =============================================================================
# Ads
# =============================================================================


def ad_item(**overrides):
    ad = {
        "id": "ad-1",
        "name": "Snap Ad",
        "status": "PAUSED",
        "creative_id": "cr-1",
        "review_status": "APPROVED",
    }
    ad.update(overrides)
    return {"ad": ad}


class TestGetAds:
    async def test_with_adset_id_fetches_directly(self):
        adapter = make_adapter([FakeResponse({"ads": [ad_item()]})])
        ads = await adapter.get_ads("acct-1", adset_id="sq-1")
        assert len(ads) == 1
        ad = ads[0]
        assert ad.ad_id == "ad-1"
        assert ad.ad_name == "Snap Ad"
        assert ad.adset_id == "sq-1"
        # Pinned: campaign_id is unknown (empty) on the direct-adset path
        assert ad.campaign_id == ""
        assert ad.status == EntityStatus.PAUSED.value
        assert ad.creative_id == "cr-1"
        assert ad.review_status == "APPROVED"
        assert adapter.session.calls[0]["url"].endswith("/adsquads/sq-1/ads")

    async def test_without_adset_id_walks_full_hierarchy(self):
        adapter = make_adapter(
            [
                FakeResponse({"campaigns": [campaign_item(id="c-1")]}),
                FakeResponse({"adsquads": [adsquad_item(id="sq-1")]}),
                FakeResponse({"ads": [ad_item(id="ad-1"), ad_item(id="ad-2")]}),
            ]
        )
        ads = await adapter.get_ads("acct-1")
        assert [a.ad_id for a in ads] == ["ad-1", "ad-2"]
        assert all(a.campaign_id == "c-1" for a in ads)
        assert all(a.adset_id == "sq-1" for a in ads)

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([FakeResponse({"ads": 5})])
        with pytest.raises(PlatformError, match="Failed to parse ad data"):
            await adapter.get_ads("acct-1", adset_id="sq-1")

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([OSError("io")])
        with pytest.raises(PlatformError, match="Failed to fetch ads"):
            await adapter.get_ads("acct-1", adset_id="sq-1")


# =============================================================================
# Metrics / stats
# =============================================================================

DATE_START = datetime(2026, 6, 1, tzinfo=UTC)
DATE_END = datetime(2026, 6, 30, tzinfo=UTC)


def stats_response(entity_id="c-1", buckets=None):
    return FakeResponse(
        {
            "timeseries_stats": [
                {
                    "timeseries_stat": {
                        "id": entity_id,
                        "timeseries": [{"stats": b} for b in (buckets or [])],
                    }
                }
            ]
        }
    )


class TestGetMetrics:
    async def test_campaign_stats_aggregated_across_buckets(self):
        buckets = [
            {
                "impressions": 1000,
                "swipes": 40,
                "spend": 10_000_000,  # micros
                "video_views": 500,
                "quartile_1": 400,
                "quartile_2": 300,
                "quartile_3": 200,
                "view_completion": 100,
                "conversion_purchases": 4,
                "conversion_purchases_value": 20_000_000,
            },
            {
                "impressions": 500,
                "swipes": 10,
                "spend": 5_000_000,
                "video_views": 250,
                "quartile_1": 100,
                "quartile_2": 50,
                "quartile_3": 25,
                "view_completion": 10,
                "conversion_purchases": 1,
                "conversion_purchases_value": 10_000_000,
            },
        ]
        adapter = make_adapter([stats_response("c-1", buckets)])
        result = await adapter.get_metrics(
            "acct-1", "campaign", ["c-1"], DATE_START, DATE_END
        )
        assert set(result) == {"c-1"}
        m = result["c-1"]
        assert m.impressions == 1500
        assert m.clicks == 50  # swipes -> clicks
        assert m.spend == 15.0  # micros -> dollars
        assert m.video_views == 750
        assert m.video_p25 == 500
        assert m.video_p50 == 350
        assert m.video_p75 == 225
        assert m.video_p100 == 110
        assert m.conversions == 5
        assert m.conversion_value == 30.0
        assert m.roas == pytest.approx(2.0)  # derived
        assert m.ctr == pytest.approx(50 / 1500 * 100)

        call = adapter.session.calls[0]
        assert call["url"].endswith("/adaccounts/acct-1/stats")
        params = call["params"]
        assert params["granularity"] == "TOTAL"
        assert params["breakdown"] == "CAMPAIGN"
        assert params["campaign_id"] == ["c-1"]
        assert params["start_time"].startswith("2026-06-01T00:00:00")
        assert params["end_time"].startswith("2026-06-30T23:59:59")

    async def test_adset_and_ad_param_keys(self):
        adapter = make_adapter(
            [
                stats_response("sq-1", [{"impressions": 1}]),
                stats_response("ad-1", [{"impressions": 1}]),
            ]
        )
        await adapter.get_metrics("acct-1", "adset", ["sq-1"], DATE_START, DATE_END)
        await adapter.get_metrics("acct-1", "ad", ["ad-1"], DATE_START, DATE_END)
        p_adset = adapter.session.calls[0]["params"]
        p_ad = adapter.session.calls[1]["params"]
        assert p_adset["breakdown"] == "ADSQUAD"
        assert p_adset["adsquad_id"] == ["sq-1"]
        assert p_ad["breakdown"] == "AD"
        assert p_ad["ad_id"] == ["ad-1"]

    async def test_empty_timeseries_entity_skipped(self):
        adapter = make_adapter([stats_response("c-1", buckets=[])])
        result = await adapter.get_metrics(
            "acct-1", "campaign", [], DATE_START, DATE_END
        )
        assert result == {}

    async def test_non_numeric_values_ignored_in_aggregation(self):
        buckets = [{"impressions": 10, "note": "not-a-number"}]
        adapter = make_adapter([stats_response("c-1", buckets)])
        result = await adapter.get_metrics(
            "acct-1", "campaign", [], DATE_START, DATE_END
        )
        assert result["c-1"].impressions == 10

    async def test_parse_error_raises_platform_error(self):
        adapter = make_adapter([FakeResponse({"timeseries_stats": 5})])
        with pytest.raises(PlatformError, match="Failed to parse metrics data"):
            await adapter.get_metrics("acct-1", "campaign", [], DATE_START, DATE_END)

    async def test_network_error_raises_platform_error(self):
        adapter = make_adapter([TimeoutError()])
        with pytest.raises(PlatformError, match="Failed to fetch metrics"):
            await adapter.get_metrics("acct-1", "campaign", [], DATE_START, DATE_END)

    async def test_rate_limit_propagates_as_rate_limit_error(self):
        adapter = make_adapter(
            [FakeResponse({}, status_code=429, headers={"X-RateLimit-Reset": "42"})]
        )
        with pytest.raises(RateLimitError, match="reset in 42s"):
            await adapter.get_metrics("acct-1", "campaign", [], DATE_START, DATE_END)


# =============================================================================
# EMQ scores
# =============================================================================


class TestGetEmqScores:
    async def test_active_pixel_scores_higher(self):
        adapter = make_adapter(
            [
                FakeResponse(
                    {
                        "pixels": [
                            {"pixel": {"id": "p1", "effective_status": "ACTIVE"}},
                            {"pixel": {"id": "p2", "effective_status": "PAUSED"}},
                            {"pixel": {}},
                        ]
                    }
                )
            ]
        )
        scores = await adapter.get_emq_scores("acct-1")
        by_name = {s.event_name: s.score for s in scores}
        assert by_name == {
            "pixel_p1": 6.0,
            "pixel_p2": 5.0,
            "pixel_unknown": 5.0,
        }
        assert all(s.platform == Platform.SNAPCHAT.value for s in scores)

    async def test_parse_error_returns_empty_list(self):
        adapter = make_adapter([FakeResponse({"pixels": 5})])
        assert await adapter.get_emq_scores("acct-1") == []

    async def test_network_error_returns_empty_list(self):
        adapter = make_adapter([TimeoutError()])
        assert await adapter.get_emq_scores("acct-1") == []

    async def test_http_error_degrades_to_empty_list(self):
        """FIXED (#540): get_emq_scores degrades gracefully — an HTTP failure
        wrapped into PlatformError by _make_request is now caught and yields
        ``[]`` instead of propagating."""
        adapter = make_adapter([FakeResponse({}, status_code=500)])
        assert await adapter.get_emq_scores("acct-1") == []

    async def test_rate_limit_degrades_to_empty_list(self):
        """FIXED (#540): a 429 -> RateLimitError is also caught and degrades."""
        adapter = make_adapter(
            [FakeResponse({}, status_code=429, headers={"X-RateLimit-Reset": "5"})]
        )
        assert await adapter.get_emq_scores("acct-1") == []


# =============================================================================
# execute_action (mutations)
# =============================================================================


def make_action(action_type, entity_type="campaign", parameters=None):
    return AutomationAction(
        platform=Platform.SNAPCHAT,
        account_id="acct-1",
        entity_type=entity_type,
        entity_id="e-1",
        action_type=action_type,
        parameters=parameters or {},
    )


class TestExecuteAction:
    async def test_update_budget_campaign(self):
        adapter = make_adapter([FakeResponse({})])
        action = make_action(
            "update_budget",
            parameters={"daily_budget": 20.0, "lifetime_budget": 100.0},
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.executed_at is not None
        assert result.result == {"updated": True}
        call = adapter.session.calls[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith("/campaigns/e-1")
        body = call["json"]["campaigns"][0]
        assert body["daily_budget_micro"] == 20_000_000
        assert body["lifetime_spend_cap_micro"] == 100_000_000
        # FIXED (#540): update body carries the entity id (as _update_status does)
        assert body["id"] == "e-1"

    async def test_update_budget_adset_uses_lifetime_budget_micro(self):
        adapter = make_adapter([FakeResponse({})])
        action = make_action(
            "update_budget",
            entity_type="adset",
            parameters={"lifetime_budget": 50.0},
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        call = adapter.session.calls[0]
        assert call["url"].endswith("/adsquads/e-1")
        body = call["json"]["adsquads"][0]
        assert body["lifetime_budget_micro"] == 50_000_000
        assert "lifetime_spend_cap_micro" not in body

    async def test_update_status_ad(self):
        adapter = make_adapter([FakeResponse({})])
        action = make_action(
            "update_status", entity_type="ad", parameters={"status": "paused"}
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.result == {"new_status": "PAUSED"}
        call = adapter.session.calls[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith("/ads/e-1")
        assert call["json"] == {"ads": [{"id": "e-1", "status": "PAUSED"}]}

    async def test_update_status_unknown_entity_defaults_to_campaign(self):
        adapter = make_adapter([FakeResponse({})])
        action = make_action(
            "update_status", entity_type="mystery", parameters={"status": "active"}
        )
        result = await adapter.execute_action(action)
        assert result.result == {"new_status": "ACTIVE"}
        call = adapter.session.calls[0]
        assert call["url"].endswith("/campaigns/e-1")
        assert "campaigns" in call["json"]

    async def test_create_campaign_created_paused_for_safety(self):
        adapter = make_adapter(
            [FakeResponse({"campaigns": [{"campaign": {"id": "new-1"}}]})]
        )
        action = make_action(
            "create_campaign",
            parameters={
                "name": "New Snap C",
                "daily_budget": 15.0,
                "lifetime_budget": 60.0,
            },
        )
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.result == {"campaign_id": "new-1"}
        call = adapter.session.calls[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/adaccounts/acct-1/campaigns")
        body = call["json"]["campaigns"][0]
        assert body["name"] == "New Snap C"
        assert body["objective"] == "WEB_CONVERSION"
        assert body["status"] == "PAUSED"  # safety: create paused
        assert body["daily_budget_micro"] == 15_000_000
        assert body["lifetime_spend_cap_micro"] == 60_000_000

    async def test_create_campaign_empty_response_returns_none_id(self):
        adapter = make_adapter([FakeResponse({"campaigns": []})])
        action = make_action("create_campaign", parameters={"name": "X"})
        result = await adapter.execute_action(action)
        assert result.status == "completed"
        assert result.result == {"campaign_id": None}

    async def test_unsupported_action_type_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("nuke_account")
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Unsupported action type" in result.error_message

    async def test_invalid_status_value_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("update_status", parameters={"status": "sideways"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"

    async def test_missing_name_param_marks_failed(self):
        adapter = make_adapter([])
        action = make_action("create_campaign", parameters={})
        result = await adapter.execute_action(action)
        assert result.status == "failed"

    async def test_platform_error_marks_action_failed(self):
        """FIXED (#540): an HTTP failure raises PlatformError from
        _make_request; execute_action now catches it and marks the action
        failed with the error message instead of leaving it in 'executing'."""
        adapter = make_adapter([FakeResponse({}, status_code=500)])
        action = make_action("update_budget", parameters={"daily_budget": 5})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Snapchat API request failed" in result.error_message

    async def test_rate_limit_marks_action_failed(self):
        """FIXED (#540): a RateLimitError on HTTP 429 is caught and marks the
        action failed with the rate-limit message."""
        adapter = make_adapter(
            [FakeResponse({}, status_code=429, headers={"X-RateLimit-Reset": "9"})]
        )
        action = make_action("update_status", parameters={"status": "paused"})
        result = await adapter.execute_action(action)
        assert result.status == "failed"
        assert "Rate limited" in result.error_message

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
# Media uploads
# =============================================================================


class TestUploads:
    async def test_upload_image_success(self):
        adapter = make_adapter([FakeResponse({"media": [{"media": {"id": "m-1"}}]})])
        media_id = await adapter.upload_image("acct-1", b"\x89PNG", "logo.png")
        assert media_id == "m-1"
        call = adapter.session.calls[0]
        assert call["url"].endswith("/adaccounts/acct-1/media")
        media = call["json"]["media"][0]
        assert media["name"] == "logo.png"
        assert media["type"] == "IMAGE"
        assert media["ad_account_id"] == "acct-1"
        assert media["media_data"]  # base64 payload present

    async def test_upload_image_empty_response_returns_empty_string(self):
        adapter = make_adapter([FakeResponse({"media": []})])
        assert await adapter.upload_image("acct-1", b"x", "a.png") == ""

    async def test_upload_video_success(self):
        adapter = make_adapter([FakeResponse({"media": [{"media": {"id": "v-1"}}]})])
        media_id = await adapter.upload_video("acct-1", b"\x00vid", "clip.mp4")
        assert media_id == "v-1"
        media = adapter.session.calls[0]["json"]["media"][0]
        assert media["type"] == "VIDEO"

    async def test_upload_video_empty_response_returns_empty_string(self):
        adapter = make_adapter([FakeResponse({"media": []})])
        assert await adapter.upload_video("acct-1", b"x", "a.mp4") == ""


# =============================================================================
# Low-level helpers
# =============================================================================


class TestHelpers:
    async def test_make_request_sends_bearer_header(self):
        adapter = make_adapter([FakeResponse({"ok": True})])
        result = await adapter._make_request("GET", "/me")
        assert result == {"ok": True}
        headers = adapter.session.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer tok-abc"
        assert headers["Content-Type"] == "application/json"

    async def test_make_request_other_method_uses_session_request(self):
        adapter = make_adapter([FakeResponse({"ok": 1})])
        await adapter._make_request("DELETE", "/ads/x", data={"a": 1})
        call = adapter.session.calls[0]
        assert call["method"] == "DELETE"
        assert call["json"] == {"a": 1}

    async def test_make_request_429_raises_rate_limit_error(self):
        adapter = make_adapter(
            [FakeResponse({}, status_code=429, headers={"X-RateLimit-Reset": "30"})]
        )
        with pytest.raises(RateLimitError, match="reset in 30s"):
            await adapter._make_request("GET", "/me")

    async def test_make_request_429_defaults_reset_to_60(self):
        adapter = make_adapter([FakeResponse({}, status_code=429)])
        with pytest.raises(RateLimitError, match="reset in 60s"):
            await adapter._make_request("GET", "/me")

    async def test_make_request_request_exception_becomes_platform_error(self):
        adapter = make_adapter([httpx.ConnectError("dns fail")])
        with pytest.raises(PlatformError, match="Snapchat API request failed"):
            await adapter._make_request("GET", "/me")

    def test_micros_to_dollars(self):
        adapter = SnapchatAdapter(dict(CREDS))
        assert adapter._micros_to_dollars(None) is None
        assert adapter._micros_to_dollars(2_500_000) == 2.5
        assert adapter._micros_to_dollars(0) == 0.0

    def test_parse_datetime(self):
        adapter = SnapchatAdapter(dict(CREDS))
        assert adapter._parse_datetime("2026-01-02T03:04:05Z") == datetime(
            2026, 1, 2, 3, 4, 5, tzinfo=UTC
        )
        assert adapter._parse_datetime(None) is None
        assert adapter._parse_datetime("") is None
        assert adapter._parse_datetime("not-a-date") is None

    def test_status_mapping(self):
        adapter = SnapchatAdapter(dict(CREDS))
        assert adapter._map_status_to_platform(EntityStatus.ACTIVE) == "ACTIVE"
        assert adapter._map_status_to_platform(EntityStatus.PAUSED) == "PAUSED"
        # Unmapped statuses default to ACTIVE
        assert adapter._map_status_to_platform(EntityStatus.DELETED) == "ACTIVE"

        assert adapter._map_status_from_platform("PAUSED") == EntityStatus.PAUSED
        assert (
            adapter._map_status_from_platform("PENDING") == EntityStatus.PENDING_REVIEW
        )
        assert adapter._map_status_from_platform("SOMETHING") == EntityStatus.ACTIVE
