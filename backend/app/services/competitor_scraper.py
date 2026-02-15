# =============================================================================
# Stratum AI - Competitor Intelligence Scraper
# =============================================================================
"""
Scrapes competitor websites to extract social media links (Facebook, Instagram),
then queries the Meta Ad Library to check for active ads.

Flow:
  1. Scrape competitor's website → extract FB/IG social links
  2. Search Meta Ad Library by competitor name + country
  3. Return results: social links + ad presence (has_ads / no_ads)
"""

import re
from datetime import UTC, datetime
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Timeouts & headers ────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# ── Types ─────────────────────────────────────────────────────────────────────
class SocialLinks:
    """Extracted social media links from a website."""

    def __init__(self) -> None:
        self.facebook: Optional[str] = None
        self.instagram: Optional[str] = None
        self.twitter: Optional[str] = None
        self.linkedin: Optional[str] = None
        self.tiktok: Optional[str] = None
        self.youtube: Optional[str] = None

    def to_dict(self) -> dict[str, Optional[str]]:
        return {
            "facebook": self.facebook,
            "instagram": self.instagram,
            "twitter": self.twitter,
            "linkedin": self.linkedin,
            "tiktok": self.tiktok,
            "youtube": self.youtube,
        }


class AdLibraryResult:
    """Result from Meta Ad Library search."""

    def __init__(self) -> None:
        self.has_ads: bool = False
        self.ad_count: int = 0
        self.ads: list[dict[str, Any]] = []
        self.search_url: str = ""
        self.search_query: Optional[str] = None
        self.page_id: Optional[str] = None
        self.page_name: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_ads": self.has_ads,
            "ad_count": self.ad_count,
            "ads": self.ads[:10],  # Limit to first 10
            "search_url": self.search_url,
            "search_query": self.search_query,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "error": self.error,
        }


class CompetitorScanResult:
    """Complete scan result for a competitor."""

    def __init__(self, domain: str) -> None:
        self.domain = domain
        self.social_links = SocialLinks()
        self.meta_title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.fb_page_name: Optional[str] = None
        self.ig_account_name: Optional[str] = None
        self.ad_library_result = AdLibraryResult()
        self.scanned_at = datetime.now(UTC).isoformat()
        self.scrape_error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "social_links": self.social_links.to_dict(),
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "fb_page_name": self.fb_page_name,
            "ig_account_name": self.ig_account_name,
            "ad_library": self.ad_library_result.to_dict(),
            "scanned_at": self.scanned_at,
            "scrape_error": self.scrape_error,
        }


# ── Regex patterns for social media links ─────────────────────────────────────
FB_PATTERNS = [
    re.compile(r"https?://(?:www\.)?facebook\.com/[\w.\-]+/?", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?fb\.com/[\w.\-]+/?", re.IGNORECASE),
]

IG_PATTERNS = [
    re.compile(r"https?://(?:www\.)?instagram\.com/[\w.\-]+/?", re.IGNORECASE),
]

TWITTER_PATTERNS = [
    re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[\w.\-]+/?", re.IGNORECASE),
]

LINKEDIN_PATTERNS = [
    re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w.\-]+/?", re.IGNORECASE),
]

TIKTOK_PATTERNS = [
    re.compile(r"https?://(?:www\.)?tiktok\.com/@[\w.\-]+/?", re.IGNORECASE),
]

YOUTUBE_PATTERNS = [
    re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)[\w.\-]+/?", re.IGNORECASE),
]


def _extract_social_link(url: str, patterns: list[re.Pattern]) -> Optional[str]:
    """Extract a cleaned social media URL if it matches any pattern."""
    for pattern in patterns:
        match = pattern.search(url)
        if match:
            return match.group(0).rstrip("/")
    return None


# ── Website Scraper ───────────────────────────────────────────────────────────
async def scrape_website(domain: str) -> CompetitorScanResult:
    """
    Scrape a competitor's website to extract social media links and metadata.

    Args:
        domain: The competitor's domain (e.g., 'example.com')

    Returns:
        CompetitorScanResult with extracted social links and metadata
    """
    result = CompetitorScanResult(domain)

    # Normalize domain to URL
    if not domain.startswith("http"):
        url = f"https://{domain}"
    else:
        url = domain

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            verify=False,  # Some sites have cert issues
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Extract metadata
            title_tag = soup.find("title")
            if title_tag:
                result.meta_title = title_tag.get_text(strip=True)[:500]

            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                result.meta_description = str(meta_desc.get("content", ""))[:1000]

            # Extract all links from the page
            all_links: set[str] = set()
            for a_tag in soup.find_all("a", href=True):
                href = str(a_tag["href"])
                # Resolve relative URLs
                if href.startswith("/"):
                    href = urljoin(url, href)
                if href.startswith("http"):
                    all_links.add(href)

            # Also check common footer/social containers
            social_containers = soup.find_all(
                ["div", "section", "footer", "nav", "ul"],
                class_=re.compile(r"social|footer|follow", re.IGNORECASE),
            )
            for container in social_containers:
                for a_tag in container.find_all("a", href=True):
                    href = str(a_tag["href"])
                    if href.startswith("/"):
                        href = urljoin(url, href)
                    if href.startswith("http"):
                        all_links.add(href)

            # Match social media links
            for link in all_links:
                if not result.social_links.facebook:
                    fb = _extract_social_link(link, FB_PATTERNS)
                    if fb:
                        result.social_links.facebook = fb

                if not result.social_links.instagram:
                    ig = _extract_social_link(link, IG_PATTERNS)
                    if ig:
                        result.social_links.instagram = ig

                if not result.social_links.twitter:
                    tw = _extract_social_link(link, TWITTER_PATTERNS)
                    if tw:
                        result.social_links.twitter = tw

                if not result.social_links.linkedin:
                    li = _extract_social_link(link, LINKEDIN_PATTERNS)
                    if li:
                        result.social_links.linkedin = li

                if not result.social_links.tiktok:
                    tt = _extract_social_link(link, TIKTOK_PATTERNS)
                    if tt:
                        result.social_links.tiktok = tt

                if not result.social_links.youtube:
                    yt = _extract_social_link(link, YOUTUBE_PATTERNS)
                    if yt:
                        result.social_links.youtube = yt

            logger.info(
                "website_scraped",
                domain=domain,
                facebook=result.social_links.facebook,
                instagram=result.social_links.instagram,
            )

    except httpx.HTTPStatusError as e:
        result.scrape_error = f"HTTP {e.response.status_code}"
        logger.warning("scrape_http_error", domain=domain, status=e.response.status_code)
    except httpx.TimeoutException:
        result.scrape_error = "Timeout"
        logger.warning("scrape_timeout", domain=domain)
    except Exception as e:
        result.scrape_error = str(e)[:200]
        logger.error("scrape_failed", domain=domain, error=str(e))

    return result


# ── Meta Ad Library API Search ────────────────────────────────────────────────
def get_meta_ad_library_search_url(query: str, country: str = "SA") -> str:
    """Generate the Meta Ad Library search URL."""
    return (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all"
        f"&country={country}"
        f"&q={query}"
        f"&search_type=keyword_unordered"
    )


async def search_meta_ad_library(
    query: str,
    country: str = "SA",
    access_token: Optional[str] = None,
) -> AdLibraryResult:
    """
    Search Meta Ad Library for active ads.

    Uses the Meta Ad Library API (Graph API endpoint) if an access_token is
    provided.  Falls back to generating a manual search URL so the user can
    check themselves.

    Args:
        query: Search query (competitor name or page name)
        country: ISO country code (e.g., 'SA', 'AE', 'US')
        access_token: Meta Graph API access token (optional)

    Returns:
        AdLibraryResult with ad presence info
    """
    result = AdLibraryResult()
    result.search_url = get_meta_ad_library_search_url(query, country)
    result.search_query = query

    if not access_token:
        # Without a token, we can only provide the search URL
        result.error = "no_access_token"
        logger.info("ad_library_no_token", query=query, country=country)
        return result

    try:
        # Use Meta Graph API Ad Library endpoint
        api_url = "https://graph.facebook.com/v21.0/ads_archive"
        params = {
            "search_terms": query,
            "ad_reached_countries": f'["{country}"]',
            "ad_active_status": "ACTIVE",
            "fields": (
                "id,ad_creation_time,ad_creative_bodies,"
                "ad_creative_link_titles,ad_creative_link_captions,"
                "ad_delivery_start_time,ad_snapshot_url,"
                "page_id,page_name,publisher_platforms,"
                "estimated_audience_size,impressions"
            ),
            "limit": 25,
            "access_token": access_token,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(api_url, params=params)

            if response.status_code == 200:
                data = response.json()
                ads_data = data.get("data", [])

                result.ad_count = len(ads_data)
                result.has_ads = result.ad_count > 0

                # Extract ad details
                for ad in ads_data:
                    result.ads.append({
                        "id": ad.get("id"),
                        "page_name": ad.get("page_name"),
                        "page_id": ad.get("page_id"),
                        "creative_body": (ad.get("ad_creative_bodies") or [""])[0][:300],
                        "link_title": (ad.get("ad_creative_link_titles") or [""])[0][:200],
                        "start_date": ad.get("ad_delivery_start_time"),
                        "snapshot_url": ad.get("ad_snapshot_url"),
                        "platforms": ad.get("publisher_platforms", []),
                        "impressions": ad.get("impressions"),
                    })

                    # Capture page info from first ad
                    if not result.page_id and ad.get("page_id"):
                        result.page_id = ad["page_id"]
                        result.page_name = ad.get("page_name")

                # Check if there are more pages
                paging = data.get("paging", {})
                if paging.get("next"):
                    # There are more ads — update count estimate
                    result.ad_count = max(result.ad_count, 25)  # At least 25+

                logger.info(
                    "ad_library_searched",
                    query=query,
                    country=country,
                    has_ads=result.has_ads,
                    ad_count=result.ad_count,
                )
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                result.error = error_msg
                logger.warning(
                    "ad_library_api_error",
                    query=query,
                    status=response.status_code,
                    error=error_msg,
                )

    except httpx.TimeoutException:
        result.error = "API timeout"
        logger.warning("ad_library_timeout", query=query)
    except Exception as e:
        result.error = str(e)[:200]
        logger.error("ad_library_failed", query=query, error=str(e))

    return result


# ── Full Competitor Scan ──────────────────────────────────────────────────────
async def scan_competitor(
    domain: str,
    name: str,
    country: str = "SA",
    access_token: Optional[str] = None,
) -> dict[str, Any]:
    """
    Full competitor scan: scrape website + search Meta Ad Library.

    Args:
        domain: Competitor's website domain
        name: Competitor's name (for ad library search)
        country: Country code for ad library filtering
        access_token: Meta Graph API token (optional)

    Returns:
        Dict with social_links, ad_library results, and metadata
    """
    # Step 1: Scrape the website for social links
    scan_result = await scrape_website(domain)

    # Step 2: Search Meta Ad Library using FB page name or IG business account
    # Priority: FB business page name > IG business account > competitor name
    search_query = name
    fb_page_name: Optional[str] = None
    ig_account_name: Optional[str] = None

    if scan_result.social_links.facebook:
        # Extract page name from Facebook URL (e.g., facebook.com/MyBrand → "MyBrand")
        fb_url = scan_result.social_links.facebook
        parsed = urlparse(fb_url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if path_parts:
            fb_page_name = path_parts[0]
            # Use FB business page name as the primary search query
            search_query = fb_page_name

    if scan_result.social_links.instagram:
        # Extract IG business account name (e.g., instagram.com/mybrand → "mybrand")
        ig_url = scan_result.social_links.instagram
        parsed = urlparse(ig_url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if path_parts:
            ig_account_name = path_parts[0]
            # If no FB page found, use IG account name
            if not fb_page_name:
                search_query = ig_account_name

    logger.info(
        "ad_library_search_query",
        domain=domain,
        fb_page=fb_page_name,
        ig_account=ig_account_name,
        search_query=search_query,
    )

    # Search Ad Library with the best available query
    ad_result = await search_meta_ad_library(
        query=search_query,
        country=country,
        access_token=access_token,
    )

    # If no ads found with FB page name, try IG account as fallback
    if not ad_result.has_ads and ig_account_name and fb_page_name and ig_account_name != fb_page_name:
        logger.info("ad_library_fallback_ig", ig_account=ig_account_name)
        ig_result = await search_meta_ad_library(
            query=ig_account_name,
            country=country,
            access_token=access_token,
        )
        if ig_result.has_ads:
            ad_result = ig_result

    # If still no ads, try the original competitor name as last resort
    if not ad_result.has_ads and search_query != name:
        logger.info("ad_library_fallback_name", name=name)
        name_result = await search_meta_ad_library(
            query=name,
            country=country,
            access_token=access_token,
        )
        if name_result.has_ads:
            ad_result = name_result

    scan_result.ad_library_result = ad_result
    scan_result.fb_page_name = fb_page_name
    scan_result.ig_account_name = ig_account_name

    return scan_result.to_dict()
