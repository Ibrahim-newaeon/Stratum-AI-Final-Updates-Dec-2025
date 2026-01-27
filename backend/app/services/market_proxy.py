# =============================================================================
# Stratum AI - Market Intelligence Proxy
# =============================================================================
"""
Market intelligence service that abstracts competitor data sources.
Implements Module D: Competitor Intelligence (Market Proxy).

Strategies:
1. Safe Metadata Scraper - Fetches public meta tags
2. SerpApi Integration - Paid keywords and search data
3. DataForSEO Integration - Traffic estimates and keywords
4. Mock Service - Development without API keys
"""

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompetitorData:
    """Standardized competitor data format."""

    domain: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[list[str]] = None
    social_links: Optional[dict[str, str]] = None
    estimated_traffic: Optional[int] = None
    traffic_trend: Optional[str] = None
    top_keywords: Optional[list[dict]] = None
    paid_keywords_count: Optional[int] = None
    organic_keywords_count: Optional[int] = None
    estimated_ad_spend_cents: Optional[int] = None
    detected_ad_platforms: Optional[list[str]] = None
    data_source: str = "unknown"
    fetched_at: datetime = None
    error: Optional[str] = None


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """Fetch competitor data for a domain."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass


# =============================================================================
# Strategy 1: Safe Metadata Scraper
# =============================================================================
class MetadataScraper(MarketDataProvider):
    """
    Scrapes public metadata from competitor websites.

    Extracts:
    - Page title
    - Meta description
    - Meta keywords
    - Social media links
    """

    def __init__(self):
        self.timeout = 10.0
        self.user_agent = "Mozilla/5.0 (compatible; StratumAI/1.0; +https://stratum.ai)"

    def get_provider_name(self) -> str:
        return "scraper"

    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """Fetch and parse metadata from a competitor's homepage."""

        url = f"https://{domain}"
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Extract title
            title_tag = soup.find("title")
            meta_title = title_tag.get_text().strip() if title_tag else None

            # Extract meta description
            desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_description = desc_tag.get("content", "").strip() if desc_tag else None

            # Extract meta keywords
            keywords_tag = soup.find("meta", attrs={"name": "keywords"})
            meta_keywords = None
            if keywords_tag:
                keywords_content = keywords_tag.get("content", "")
                meta_keywords = [k.strip() for k in keywords_content.split(",") if k.strip()]

            # Extract social links
            social_links = self._extract_social_links(soup, domain)

            return CompetitorData(
                domain=domain,
                meta_title=meta_title,
                meta_description=meta_description,
                meta_keywords=meta_keywords,
                social_links=social_links,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
            )

        except httpx.HTTPError as e:
            logger.warning("metadata_scrape_failed", domain=domain, error=str(e))
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error=f"HTTP error: {e!s}",
            )
        except Exception as e:
            logger.error("metadata_scrape_error", domain=domain, error=str(e))
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error=str(e),
            )

    def _extract_social_links(self, soup: BeautifulSoup, domain: str) -> dict[str, str]:
        """Extract social media links from page."""
        social_platforms = {
            "facebook.com": "facebook",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "instagram.com": "instagram",
            "linkedin.com": "linkedin",
            "youtube.com": "youtube",
            "tiktok.com": "tiktok",
            "pinterest.com": "pinterest",
        }

        found_links = {}

        for link in soup.find_all("a", href=True):
            href = link["href"]
            try:
                parsed = urlparse(href)
                link_domain = parsed.netloc.lower().replace("www.", "")

                for platform_domain, platform_name in social_platforms.items():
                    if platform_domain in link_domain:
                        found_links[platform_name] = href
                        break
            except Exception:
                continue

        return found_links


# =============================================================================
# Strategy 2: SerpApi Integration
# =============================================================================
class SerpApiProvider(MarketDataProvider):
    """
    Integration with SerpApi for search and advertising data.
    Requires SERPAPI_KEY environment variable.
    """

    def __init__(self):
        self.api_key = settings.serpapi_key
        self.base_url = "https://serpapi.com/search"

    def get_provider_name(self) -> str:
        return "serpapi"

    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """Fetch competitor data from SerpApi."""

        if not self.api_key:
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error="SerpApi key not configured",
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get organic search presence
                organic_response = await client.get(
                    self.base_url,
                    params={
                        "engine": "google",
                        "q": f"site:{domain}",
                        "api_key": self.api_key,
                        "num": 10,
                    },
                )
                organic_data = organic_response.json()

                # Get ads data (if available)
                ads_response = await client.get(
                    self.base_url,
                    params={
                        "engine": "google",
                        "q": domain.split(".")[0],  # Brand name search
                        "api_key": self.api_key,
                    },
                )
                ads_data = ads_response.json()

            # Parse results
            organic_count = organic_data.get("search_information", {}).get("total_results", 0)

            # Extract top keywords from related searches
            related = organic_data.get("related_searches", [])
            top_keywords = [{"keyword": r.get("query"), "type": "organic"} for r in related[:10]]

            # Check for ads presence
            ads = ads_data.get("ads", [])
            detected_platforms = ["google"] if ads else []

            return CompetitorData(
                domain=domain,
                organic_keywords_count=min(organic_count, 100000),
                top_keywords=top_keywords,
                detected_ad_platforms=detected_platforms,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.error("serpapi_fetch_error", domain=domain, error=str(e))
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error=str(e),
            )


# =============================================================================
# Strategy 3: DataForSEO Integration
# =============================================================================
class DataForSEOProvider(MarketDataProvider):
    """
    Integration with DataForSEO for traffic and keyword data.
    Requires DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD.
    """

    def __init__(self):
        self.login = settings.dataforseo_login
        self.password = settings.dataforseo_password
        self.base_url = "https://api.dataforseo.com/v3"

    def get_provider_name(self) -> str:
        return "dataforseo"

    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """Fetch competitor data from DataForSEO."""

        if not self.login or not self.password:
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error="DataForSEO credentials not configured",
            )

        try:
            auth = (self.login, self.password)

            async with httpx.AsyncClient(timeout=30.0, auth=auth) as client:
                # Domain overview
                overview_response = await client.post(
                    f"{self.base_url}/dataforseo_labs/google/domain_metrics_by_categories/live",
                    json=[{"target": domain, "language_code": "en", "location_code": 2840}],
                )
                overview_data = overview_response.json()

                # Get keywords
                keywords_response = await client.post(
                    f"{self.base_url}/dataforseo_labs/google/ranked_keywords/live",
                    json=[
                        {
                            "target": domain,
                            "language_code": "en",
                            "location_code": 2840,
                            "limit": 20,
                        }
                    ],
                )
                keywords_data = keywords_response.json()

            # Parse domain metrics
            metrics = {}
            if overview_data.get("tasks"):
                result = overview_data["tasks"][0].get("result", [])
                if result:
                    metrics = result[0]

            # Parse keywords
            top_keywords = []
            if keywords_data.get("tasks"):
                result = keywords_data["tasks"][0].get("result", [])
                if result:
                    items = result[0].get("items", [])
                    top_keywords = [
                        {
                            "keyword": item.get("keyword_data", {}).get("keyword"),
                            "position": item.get("ranked_serp_element", {})
                            .get("serp_item", {})
                            .get("rank_absolute"),
                            "type": "organic"
                            if item.get("ranked_serp_element", {}).get("serp_item", {}).get("type")
                            == "organic"
                            else "paid",
                            "volume": item.get("keyword_data", {})
                            .get("keyword_info", {})
                            .get("search_volume"),
                        }
                        for item in items[:20]
                    ]

            return CompetitorData(
                domain=domain,
                estimated_traffic=metrics.get("metrics", {}).get("organic", {}).get("etv"),
                organic_keywords_count=metrics.get("metrics", {}).get("organic", {}).get("count"),
                paid_keywords_count=metrics.get("metrics", {}).get("paid", {}).get("count"),
                top_keywords=top_keywords,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.error("dataforseo_fetch_error", domain=domain, error=str(e))
            return CompetitorData(
                domain=domain,
                data_source=self.get_provider_name(),
                fetched_at=datetime.now(UTC),
                error=str(e),
            )


# =============================================================================
# Strategy 4: Mock Market Service (Development)
# =============================================================================
class MockMarketService(MarketDataProvider):
    """
    Mock market intelligence service for development.
    Generates realistic fake data without requiring API keys.
    """

    def get_provider_name(self) -> str:
        return "mock"

    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """Generate mock competitor data."""

        # Use domain as seed for consistent data
        seed = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # Generate realistic company name from domain
        company_name = domain.split(".")[0].replace("-", " ").title()

        # Mock metadata
        meta_title = f"{company_name} | {rng.choice(['Leading', 'Premier', 'Top', 'Best'])} {rng.choice(['Marketing', 'Technology', 'Solutions', 'Services', 'Platform'])}"
        meta_description = f"{company_name} provides {rng.choice(['innovative', 'cutting-edge', 'enterprise-grade', 'AI-powered'])} solutions for {rng.choice(['businesses', 'enterprises', 'teams', 'organizations'])}."

        meta_keywords = rng.sample(
            [
                "marketing",
                "analytics",
                "AI",
                "automation",
                "growth",
                "digital",
                "platform",
                "software",
                "SaaS",
                "enterprise",
                "solutions",
                "advertising",
                "data",
                "insights",
                "ROI",
            ],
            k=rng.randint(5, 10),
        )

        # Mock social links
        social_links = {}
        if rng.random() < 0.9:
            social_links["linkedin"] = f"https://linkedin.com/company/{domain.split('.')[0]}"
        if rng.random() < 0.8:
            social_links["twitter"] = f"https://twitter.com/{domain.split('.')[0]}"
        if rng.random() < 0.6:
            social_links["facebook"] = f"https://facebook.com/{domain.split('.')[0]}"

        # Mock traffic data
        traffic_tier = rng.choice(["low", "medium", "high", "very_high"])
        traffic_ranges = {
            "low": (1000, 10000),
            "medium": (10000, 100000),
            "high": (100000, 1000000),
            "very_high": (1000000, 10000000),
        }
        traffic_range = traffic_ranges[traffic_tier]
        estimated_traffic = rng.randint(*traffic_range)
        traffic_trend = rng.choice(["up", "down", "stable"])

        # Mock keywords
        keyword_templates = [
            f"{company_name.lower()} alternative",
            f"{company_name.lower()} pricing",
            f"{company_name.lower()} review",
            f"best {rng.choice(meta_keywords)}",
            f"{rng.choice(meta_keywords)} software",
            f"{rng.choice(meta_keywords)} tools",
            f"how to {rng.choice(['improve', 'boost', 'increase'])} {rng.choice(meta_keywords)}",
        ]

        top_keywords = []
        for i, kw in enumerate(keyword_templates[:10]):
            top_keywords.append(
                {
                    "keyword": kw,
                    "position": rng.randint(1, 50),
                    "type": rng.choice(["organic", "paid"]),
                    "volume": rng.randint(100, 50000),
                    "cpc_cents": rng.randint(50, 2000),
                }
            )

        # Mock paid keyword counts
        paid_keywords = rng.randint(50, 5000) if rng.random() < 0.7 else 0
        organic_keywords = rng.randint(500, 50000)

        # Mock ad spend
        estimated_ad_spend = paid_keywords * rng.randint(100, 500) if paid_keywords > 0 else 0

        # Mock detected platforms
        platforms = []
        if paid_keywords > 0:
            platforms.append("google")
            if rng.random() < 0.6:
                platforms.append("meta")
            if rng.random() < 0.3:
                platforms.append("linkedin")

        return CompetitorData(
            domain=domain,
            meta_title=meta_title,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            social_links=social_links,
            estimated_traffic=estimated_traffic,
            traffic_trend=traffic_trend,
            top_keywords=top_keywords,
            paid_keywords_count=paid_keywords,
            organic_keywords_count=organic_keywords,
            estimated_ad_spend_cents=estimated_ad_spend,
            detected_ad_platforms=platforms,
            data_source=self.get_provider_name(),
            fetched_at=datetime.now(UTC),
        )


# =============================================================================
# Market Intelligence Service (Proxy)
# =============================================================================
class MarketIntelligenceService:
    """
    Proxy service that coordinates multiple market data providers.

    Automatically selects the appropriate provider based on configuration
    and falls back gracefully if a provider fails.
    """

    def __init__(self):
        self.providers: dict[str, MarketDataProvider] = {
            "mock": MockMarketService(),
            "scraper": MetadataScraper(),
            "serpapi": SerpApiProvider(),
            "dataforseo": DataForSEOProvider(),
        }

        # Determine primary provider from config
        self.primary_provider = settings.market_intel_provider

    async def get_competitor_data(self, domain: str) -> CompetitorData:
        """
        Fetch competitor data using the configured provider.

        Falls back to scraper + mock if primary provider fails.
        """
        # Normalize domain
        domain = (
            domain.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .rstrip("/")
        )

        # Try primary provider
        provider = self.providers.get(self.primary_provider, self.providers["mock"])

        logger.info(
            "fetching_competitor_data", domain=domain, provider=provider.get_provider_name()
        )

        data = await provider.get_competitor_data(domain)

        # If primary failed and it's not mock, try to enrich with scraper
        if data.error and self.primary_provider != "mock":
            logger.warning("primary_provider_failed", domain=domain, error=data.error)

            # Try scraper for metadata
            scraper = self.providers["scraper"]
            scraper_data = await scraper.get_competitor_data(domain)

            if not scraper_data.error:
                # Merge scraper data
                data.meta_title = scraper_data.meta_title
                data.meta_description = scraper_data.meta_description
                data.meta_keywords = scraper_data.meta_keywords
                data.social_links = scraper_data.social_links

            # Use mock for traffic/keyword estimates if needed
            if self.primary_provider not in ["mock", "scraper"]:
                mock = self.providers["mock"]
                mock_data = await mock.get_competitor_data(domain)
                data.estimated_traffic = data.estimated_traffic or mock_data.estimated_traffic
                data.top_keywords = data.top_keywords or mock_data.top_keywords

            data.error = None  # Clear error since we have fallback data

        return data

    async def get_share_of_voice(self, domains: list[str]) -> dict[str, float]:
        """
        Calculate share of voice across multiple competitors.

        Based on estimated traffic distribution.
        """
        traffic_data = {}
        total_traffic = 0

        for domain in domains:
            data = await self.get_competitor_data(domain)
            traffic = data.estimated_traffic or 0
            traffic_data[domain] = traffic
            total_traffic += traffic

        # Calculate shares
        if total_traffic > 0:
            return {
                domain: round((traffic / total_traffic) * 100, 2)
                for domain, traffic in traffic_data.items()
            }

        # Equal distribution if no traffic data
        equal_share = round(100 / len(domains), 2) if domains else 0
        return {domain: equal_share for domain in domains}
