# =============================================================================
# Stratum AI - Competitor Scraper Pure-Logic Unit Tests
# =============================================================================
"""Unit tests for the pure helpers in ``app.services.competitor_scraper``:

- ``SocialLinks`` / ``AdLibraryResult`` / ``CompetitorScanResult`` to_dict
  serialization (including the 10-ad cap and nested composition)
- ``_extract_social_link`` regex matching + trailing-slash cleanup
- ``get_meta_ad_library_search_url`` query-string building

Network scraping (httpx / BeautifulSoup paths) is out of scope here.
"""

import pytest

from app.services.competitor_scraper import (
    FB_PATTERNS,
    TIKTOK_PATTERNS,
    AdLibraryResult,
    CompetitorScanResult,
    SocialLinks,
    _extract_social_link,
    get_meta_ad_library_search_url,
)

pytestmark = pytest.mark.unit


# =============================================================================
# to_dict serializers
# =============================================================================
class TestSerializers:
    def test_social_links_defaults_all_none(self):
        d = SocialLinks().to_dict()
        assert set(d) == {
            "facebook",
            "instagram",
            "twitter",
            "linkedin",
            "tiktok",
            "youtube",
        }
        assert all(v is None for v in d.values())

    def test_ad_library_caps_ads_at_ten(self):
        result = AdLibraryResult()
        result.has_ads = True
        result.ads = [{"id": i} for i in range(25)]
        d = result.to_dict()
        assert len(d["ads"]) == 10
        assert d["has_ads"] is True

    def test_scan_result_composes_nested_dicts(self):
        scan = CompetitorScanResult("acme.com")
        scan.social_links.facebook = "https://facebook.com/acme"
        scan.meta_title = "Acme"
        d = scan.to_dict()
        assert d["domain"] == "acme.com"
        assert d["social_links"]["facebook"] == "https://facebook.com/acme"
        assert d["meta_title"] == "Acme"
        # ad_library is the nested AdLibraryResult serialization.
        assert "has_ads" in d["ad_library"]
        assert "scanned_at" in d


# =============================================================================
# _extract_social_link
# =============================================================================
class TestExtractSocialLink:
    def test_matches_and_strips_trailing_slash(self):
        url = "Visit https://www.facebook.com/AcmeCorp/ today"
        assert _extract_social_link(url, FB_PATTERNS) == (
            "https://www.facebook.com/AcmeCorp"
        )

    def test_no_match_returns_none(self):
        assert _extract_social_link("https://example.com/about", FB_PATTERNS) is None

    def test_tiktok_at_handle(self):
        assert (
            _extract_social_link("https://www.tiktok.com/@acme.brand", TIKTOK_PATTERNS)
            == "https://www.tiktok.com/@acme.brand"
        )


# =============================================================================
# get_meta_ad_library_search_url
# =============================================================================
class TestAdLibraryUrl:
    def test_contains_query_and_country(self):
        url = get_meta_ad_library_search_url("Nike Shoes", country="GB")
        assert url.startswith("https://www.facebook.com/ads/library/")
        assert "country=GB" in url
        assert "q=Nike Shoes" in url
        assert "search_type=keyword_unordered" in url

    def test_default_country_is_sa(self):
        assert "country=SA" in get_meta_ad_library_search_url("Acme")
