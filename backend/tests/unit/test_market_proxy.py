# =============================================================================
# Stratum AI - Market Intelligence Proxy unit tests
# =============================================================================
"""Unit tests for app.services.market_proxy.

Covers the pure logic only — the seeded MockMarketService, social-link
extraction from parsed HTML, domain normalization in the proxy service,
and share-of-voice math. No HTTP is issued (the proxy is pinned to the
mock provider).
"""

import asyncio

import pytest
from bs4 import BeautifulSoup

from app.services.market_proxy import (
    MarketIntelligenceService,
    MetadataScraper,
    MockMarketService,
)

pytestmark = pytest.mark.unit


# =============================================================================
# MockMarketService
# =============================================================================
class TestMockMarketService:
    def test_deterministic_per_domain(self):
        a = asyncio.run(MockMarketService().get_competitor_data("acme.com"))
        b = asyncio.run(MockMarketService().get_competitor_data("acme.com"))
        assert a.meta_title == b.meta_title
        assert a.estimated_traffic == b.estimated_traffic
        assert a.top_keywords == b.top_keywords

    def test_different_domains_differ(self):
        a = asyncio.run(MockMarketService().get_competitor_data("acme.com"))
        b = asyncio.run(MockMarketService().get_competitor_data("globex.com"))
        assert a.estimated_traffic != b.estimated_traffic

    def test_company_name_derived_from_domain(self):
        data = asyncio.run(MockMarketService().get_competitor_data("acme-widgets.com"))
        assert data.meta_title.startswith("Acme Widgets |")
        assert "Acme Widgets" in data.meta_description

    def test_data_shape(self):
        data = asyncio.run(MockMarketService().get_competitor_data("acme.com"))
        assert data.data_source == "mock"
        assert data.error is None
        assert 1000 <= data.estimated_traffic <= 10_000_000
        assert data.traffic_trend in {"up", "down", "stable"}
        assert 5 <= len(data.meta_keywords) <= 10
        assert len(data.top_keywords) <= 10
        for kw in data.top_keywords:
            assert 1 <= kw["position"] <= 50
            assert kw["type"] in {"organic", "paid"}

    def test_ad_platforms_consistent_with_paid_keywords(self):
        data = asyncio.run(MockMarketService().get_competitor_data("acme.com"))
        if data.paid_keywords_count > 0:
            assert "google" in data.detected_ad_platforms
            assert data.estimated_ad_spend_cents > 0
        else:
            assert data.detected_ad_platforms == []
            assert data.estimated_ad_spend_cents == 0


# =============================================================================
# Social link extraction (pure HTML parsing)
# =============================================================================
class TestSocialLinkExtraction:
    def _extract(self, html):
        # html.parser keeps the test free of the optional lxml dependency;
        # _extract_social_links is parser-agnostic
        soup = BeautifulSoup(html, "html.parser")
        return MetadataScraper()._extract_social_links(soup, "acme.com")

    def test_known_platforms_found(self):
        html = """
        <html><body>
        <a href="https://www.facebook.com/acme">FB</a>
        <a href="https://x.com/acme">X</a>
        <a href="https://www.linkedin.com/company/acme">LI</a>
        <a href="https://acme.com/about">About</a>
        </body></html>
        """
        links = self._extract(html)
        assert links["facebook"] == "https://www.facebook.com/acme"
        assert links["twitter"] == "https://x.com/acme"  # x.com maps to twitter
        assert links["linkedin"] == "https://www.linkedin.com/company/acme"
        assert "about" not in str(links)

    def test_no_social_links(self):
        assert self._extract("<html><body><a href='/home'>Home</a></body></html>") == {}

    def test_malformed_hrefs_ignored(self):
        html = (
            '<a href="not a url at all">x</a><a href="https://tiktok.com/@acme">t</a>'
        )
        links = self._extract(html)
        assert links == {"tiktok": "https://tiktok.com/@acme"}


# =============================================================================
# MarketIntelligenceService (pinned to mock provider)
# =============================================================================
@pytest.fixture()
def proxy():
    svc = MarketIntelligenceService()
    svc.primary_provider = "mock"
    return svc


class TestProxyService:
    def test_domain_normalization(self, proxy):
        raw = asyncio.run(proxy.get_competitor_data("https://www.ACME.com/"))
        clean = asyncio.run(proxy.get_competitor_data("acme.com"))
        assert raw.domain == clean.domain == "acme.com"
        assert raw.meta_title == clean.meta_title  # same seed after normalization

    def test_unknown_provider_falls_back_to_mock(self):
        svc = MarketIntelligenceService()
        svc.primary_provider = "does_not_exist"
        data = asyncio.run(svc.get_competitor_data("acme.com"))
        assert data.data_source == "mock"
        assert data.error is None

    def test_share_of_voice_proportional(self, proxy):
        shares = asyncio.run(proxy.get_share_of_voice(["acme.com", "globex.com"]))
        assert set(shares) == {"acme.com", "globex.com"}
        assert sum(shares.values()) == pytest.approx(100.0, abs=0.1)
        assert all(s > 0 for s in shares.values())

    def test_share_of_voice_empty(self, proxy):
        assert asyncio.run(proxy.get_share_of_voice([])) == {}
