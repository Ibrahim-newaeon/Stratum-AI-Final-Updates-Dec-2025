# =============================================================================
# Stratum AI - Mock Ad Network Client
# =============================================================================
"""
Mock ad network client that generates realistic, varied time-series data.
Used for development and demo purposes without requiring real API keys.

Implements Module B: Data Integration.
"""

import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.models import AdPlatform, CampaignStatus

logger = get_logger(__name__)


# =============================================================================
# Location Coordinates for Heatmap (Demo Data)
# =============================================================================
LOCATION_COORDINATES = {
    "US": {"lat": 39.8283, "lng": -98.5795},
    "US-CA": {"lat": 36.7783, "lng": -119.4179},
    "US-TX": {"lat": 31.9686, "lng": -99.9018},
    "US-NY": {"lat": 43.2994, "lng": -74.2179},
    "US-FL": {"lat": 27.6648, "lng": -81.5158},
    "US-IL": {"lat": 40.6331, "lng": -89.3985},
    "UK": {"lat": 51.5074, "lng": -0.1278},
    "UK-London": {"lat": 51.5074, "lng": -0.1278},
    "UK-Manchester": {"lat": 53.4808, "lng": -2.2426},
    "CA": {"lat": 56.1304, "lng": -106.3468},
    "CA-ON": {"lat": 51.2538, "lng": -85.3232},
    "DE": {"lat": 51.1657, "lng": 10.4515},
    "FR": {"lat": 46.2276, "lng": 2.2137},
    "AU": {"lat": -25.2744, "lng": 133.7751},
    "JP": {"lat": 36.2048, "lng": 138.2529},
    "BR": {"lat": -14.2350, "lng": -51.9253},
    "IN": {"lat": 20.5937, "lng": 78.9629},
    "MX": {"lat": 23.6345, "lng": -102.5528},
    "ES": {"lat": 40.4637, "lng": -3.7492},
    "IT": {"lat": 41.8719, "lng": 12.5674},
}


# =============================================================================
# Campaign Templates for Realistic Names
# =============================================================================
CAMPAIGN_TEMPLATES = {
    AdPlatform.META: {
        "prefixes": ["FB", "IG", "Meta"],
        "objectives": ["Conversions", "Traffic", "Engagement", "Lead Gen", "Brand Awareness", "App Install"],
        "audiences": ["Lookalike 1%", "Lookalike 3%", "Interest - Tech", "Interest - Fashion", "Retargeting", "Broad"],
    },
    AdPlatform.GOOGLE: {
        "prefixes": ["GGL", "Search", "Display", "YT", "PMax"],
        "objectives": ["Search - Brand", "Search - NonBrand", "Display - Prospecting", "YouTube - Awareness", "PMax - Sales"],
        "audiences": ["Keywords - Exact", "Keywords - Phrase", "In-Market", "Custom Intent", "Remarketing"],
    },
    AdPlatform.TIKTOK: {
        "prefixes": ["TT", "TikTok"],
        "objectives": ["Video Views", "Conversions", "Traffic", "App Install", "Lead Gen"],
        "audiences": ["GenZ Interest", "Trend Followers", "Lookalike", "Custom Audience", "Broad"],
    },
    AdPlatform.SNAPCHAT: {
        "prefixes": ["SNAP", "Snapchat"],
        "objectives": ["Story Ads", "Collection Ads", "Commercials", "App Install"],
        "audiences": ["18-24 Interest", "Lifestyle", "Lookalike", "Web Visitors"],
    },
}

AGE_RANGES = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
GENDERS = ["male", "female", "unknown"]
LOCATIONS = ["US-CA", "US-TX", "US-NY", "US-FL", "US-IL", "UK-London", "CA-ON", "DE", "AU", "FR"]


@dataclass
class MockCampaignData:
    """Generated mock campaign data."""
    external_id: str
    account_id: str
    name: str
    platform: AdPlatform
    status: CampaignStatus
    objective: str
    daily_budget_cents: int
    lifetime_budget_cents: Optional[int]
    start_date: date
    end_date: Optional[date]
    targeting_age_min: int
    targeting_age_max: int
    targeting_genders: List[str]
    targeting_locations: List[Dict]
    metrics: Dict[str, Any]
    demographics: Dict[str, Any]


class MockAdNetwork:
    """
    Mock ad network that generates realistic campaign data.

    Features:
    - Varied campaign performance based on platform and objective
    - Realistic time-series with trends, seasonality, and noise
    - Correlated metrics (higher spend -> more impressions -> more clicks)
    - Demographics distribution that varies by campaign
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the mock ad network.

        Args:
            seed: Random seed for reproducible data generation
        """
        self.seed = seed or 42
        self._rng = random.Random(self.seed)

    def _seeded_random(self, identifier: str) -> random.Random:
        """Get a seeded random generator based on identifier."""
        hash_val = int(hashlib.md5(f"{self.seed}:{identifier}".encode()).hexdigest()[:8], 16)
        return random.Random(hash_val)

    def generate_campaigns(
        self,
        tenant_id: int,
        count: int = 20,
        platforms: Optional[List[AdPlatform]] = None,
    ) -> List[MockCampaignData]:
        """
        Generate mock campaigns for a tenant.

        Args:
            tenant_id: Tenant ID for seeding
            count: Number of campaigns to generate
            platforms: List of platforms (default: all)

        Returns:
            List of MockCampaignData objects
        """
        platforms = platforms or list(AdPlatform)
        rng = self._seeded_random(f"campaigns:{tenant_id}")

        campaigns = []
        for i in range(count):
            platform = rng.choice(platforms)
            campaign = self._generate_single_campaign(tenant_id, i, platform, rng)
            campaigns.append(campaign)

        return campaigns

    def _generate_single_campaign(
        self,
        tenant_id: int,
        index: int,
        platform: AdPlatform,
        rng: random.Random,
    ) -> MockCampaignData:
        """Generate a single campaign with all its data."""

        templates = CAMPAIGN_TEMPLATES[platform]
        prefix = rng.choice(templates["prefixes"])
        objective = rng.choice(templates["objectives"])
        audience = rng.choice(templates["audiences"])

        # Generate campaign name
        name = f"{prefix} | {objective} | {audience} | Q{rng.randint(1, 4)}-2024"

        # Status distribution: 60% active, 20% paused, 15% completed, 5% draft
        status_weights = [0.6, 0.2, 0.15, 0.05]
        status = rng.choices(
            [CampaignStatus.ACTIVE, CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.DRAFT],
            weights=status_weights,
        )[0]

        # Budget based on platform (Meta/Google higher, TikTok/Snap lower on average)
        budget_multiplier = {
            AdPlatform.META: 1.2,
            AdPlatform.GOOGLE: 1.5,
            AdPlatform.TIKTOK: 0.8,
            AdPlatform.SNAPCHAT: 0.6,
        }

        daily_budget = int(rng.gauss(5000, 2000) * budget_multiplier[platform])
        daily_budget = max(1000, min(50000, daily_budget))  # $10-$500/day

        # Date range
        days_ago_start = rng.randint(30, 180)
        start_date = date.today() - timedelta(days=days_ago_start)

        if status == CampaignStatus.COMPLETED:
            campaign_length = rng.randint(14, 60)
            end_date = start_date + timedelta(days=campaign_length)
        elif rng.random() < 0.3:  # 30% have end dates
            end_date = start_date + timedelta(days=rng.randint(30, 90))
        else:
            end_date = None

        # Targeting
        age_min = rng.choice([18, 21, 25, 30, 35])
        age_max = age_min + rng.choice([10, 15, 20, 30, 47])

        genders = rng.sample(GENDERS[:2], k=rng.randint(1, 2))
        if rng.random() < 0.3:  # Sometimes all genders
            genders = GENDERS

        locations = rng.sample(LOCATIONS, k=rng.randint(1, 5))
        targeting_locations = [
            {"code": loc, "name": loc.replace("-", " - ")}
            for loc in locations
        ]

        # Generate performance metrics
        metrics = self._generate_metrics(tenant_id, index, platform, daily_budget, start_date, end_date, rng)

        # Generate demographics
        demographics = self._generate_demographics(metrics["impressions"], rng)

        return MockCampaignData(
            external_id=f"{platform.value}_{tenant_id}_{index:04d}",
            account_id=f"act_{tenant_id}_{platform.value[:2].upper()}001",
            name=name,
            platform=platform,
            status=status,
            objective=objective,
            daily_budget_cents=daily_budget,
            lifetime_budget_cents=daily_budget * 30 if rng.random() < 0.4 else None,
            start_date=start_date,
            end_date=end_date,
            targeting_age_min=age_min,
            targeting_age_max=age_max,
            targeting_genders=genders,
            targeting_locations=targeting_locations,
            metrics=metrics,
            demographics=demographics,
        )

    def _generate_metrics(
        self,
        tenant_id: int,
        campaign_index: int,
        platform: AdPlatform,
        daily_budget: int,
        start_date: date,
        end_date: Optional[date],
        rng: random.Random,
    ) -> Dict[str, Any]:
        """Generate realistic performance metrics."""

        # Platform-specific performance characteristics
        platform_params = {
            AdPlatform.META: {"cpm_base": 800, "ctr_base": 1.2, "cvr_base": 2.5, "cpm_var": 200, "performance_var": 0.3},
            AdPlatform.GOOGLE: {"cpm_base": 1200, "ctr_base": 3.5, "cvr_base": 4.0, "cpm_var": 400, "performance_var": 0.25},
            AdPlatform.TIKTOK: {"cpm_base": 600, "ctr_base": 0.8, "cvr_base": 1.5, "cpm_var": 150, "performance_var": 0.4},
            AdPlatform.SNAPCHAT: {"cpm_base": 500, "ctr_base": 0.6, "cvr_base": 1.2, "cpm_var": 100, "performance_var": 0.35},
        }

        params = platform_params[platform]

        # Campaign-specific performance modifier
        campaign_modifier = rng.gauss(1.0, params["performance_var"])
        campaign_modifier = max(0.3, min(2.0, campaign_modifier))

        # Calculate days active
        actual_end = end_date or date.today()
        days_active = (actual_end - start_date).days
        days_active = max(1, min(days_active, 180))

        # Base metrics from budget
        total_spend_cents = int(daily_budget * days_active * rng.uniform(0.7, 1.0))

        # CPM determines impressions
        cpm_cents = int(params["cpm_base"] * campaign_modifier + rng.gauss(0, params["cpm_var"]))
        cpm_cents = max(100, cpm_cents)
        impressions = int((total_spend_cents / cpm_cents) * 1000)

        # CTR determines clicks
        ctr = params["ctr_base"] * campaign_modifier * rng.uniform(0.7, 1.3) / 100
        clicks = int(impressions * ctr)

        # CVR determines conversions
        cvr = params["cvr_base"] * campaign_modifier * rng.uniform(0.5, 1.5) / 100
        conversions = int(clicks * cvr)

        # Revenue (with some variance in AOV)
        aov_cents = int(rng.gauss(8000, 3000))  # $80 average order value
        aov_cents = max(2000, min(50000, aov_cents))
        revenue_cents = conversions * aov_cents

        # ROAS
        roas = revenue_cents / total_spend_cents if total_spend_cents > 0 else 0

        # Video metrics (if applicable)
        video_views = None
        video_completions = None
        if platform in [AdPlatform.META, AdPlatform.TIKTOK, AdPlatform.SNAPCHAT]:
            if rng.random() < 0.6:  # 60% of campaigns have video
                video_views = int(impressions * rng.uniform(0.3, 0.7))
                video_completions = int(video_views * rng.uniform(0.15, 0.45))

        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "total_spend_cents": total_spend_cents,
            "revenue_cents": revenue_cents,
            "ctr": round(ctr * 100, 2),
            "cpc_cents": int(total_spend_cents / clicks) if clicks > 0 else 0,
            "cpm_cents": cpm_cents,
            "cpa_cents": int(total_spend_cents / conversions) if conversions > 0 else 0,
            "roas": round(roas, 2),
            "video_views": video_views,
            "video_completions": video_completions,
        }

    def _generate_demographics(
        self,
        total_impressions: int,
        rng: random.Random,
    ) -> Dict[str, Any]:
        """Generate demographic breakdown."""

        # Age distribution (weighted towards 25-44)
        age_weights = [0.12, 0.28, 0.25, 0.18, 0.10, 0.07]
        # Add some randomness
        age_weights = [w * rng.uniform(0.7, 1.3) for w in age_weights]
        total_weight = sum(age_weights)
        age_weights = [w / total_weight for w in age_weights]

        age_data = {}
        for i, age_range in enumerate(AGE_RANGES):
            imp = int(total_impressions * age_weights[i])
            ctr = rng.uniform(0.8, 1.5)
            cvr = rng.uniform(0.5, 2.0)
            clicks = int(imp * ctr / 100)
            conversions = int(clicks * cvr / 100)

            age_data[age_range] = {
                "impressions": imp,
                "clicks": clicks,
                "conversions": conversions,
            }

        # Gender distribution
        gender_weights = [0.48, 0.48, 0.04]  # Male, Female, Unknown
        gender_weights = [w * rng.uniform(0.8, 1.2) for w in gender_weights]
        total_weight = sum(gender_weights)
        gender_weights = [w / total_weight for w in gender_weights]

        gender_data = {}
        for i, gender in enumerate(GENDERS):
            imp = int(total_impressions * gender_weights[i])
            ctr = rng.uniform(0.8, 1.4)
            clicks = int(imp * ctr / 100)

            gender_data[gender] = {
                "impressions": imp,
                "clicks": clicks,
            }

        # Location distribution
        location_weights = [0.25, 0.15, 0.12, 0.10, 0.08, 0.08, 0.07, 0.06, 0.05, 0.04]
        location_weights = [w * rng.uniform(0.7, 1.3) for w in location_weights]
        total_weight = sum(location_weights)
        location_weights = [w / total_weight for w in location_weights]

        location_data = {}
        for i, location in enumerate(LOCATIONS):
            imp = int(total_impressions * location_weights[i])
            location_data[location] = {
                "impressions": imp,
                "clicks": int(imp * rng.uniform(0.8, 1.5) / 100),
            }

        return {
            "age": age_data,
            "gender": gender_data,
            "location": location_data,
        }

    def generate_time_series(
        self,
        campaign_id: str,
        start_date: date,
        end_date: date,
        base_metrics: Dict[str, Any],
        rng: Optional[random.Random] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate daily time-series data for a campaign.

        Includes:
        - Day of week patterns
        - Gradual trends
        - Random noise
        """
        rng = rng or self._seeded_random(f"ts:{campaign_id}")

        days = (end_date - start_date).days + 1
        daily_metrics = []

        # Calculate daily averages from totals
        daily_avg = {
            "impressions": base_metrics["impressions"] / days,
            "clicks": base_metrics["clicks"] / days,
            "conversions": base_metrics["conversions"] / days,
            "spend_cents": base_metrics["total_spend_cents"] / days,
            "revenue_cents": base_metrics["revenue_cents"] / days,
        }

        # Generate a trend (slight increase or decrease over time)
        trend_direction = rng.choice([0.001, -0.001, 0.002, -0.002, 0])

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)

            # Day of week modifier (weekends typically different)
            dow = current_date.weekday()
            dow_modifier = 1.0
            if dow == 5:  # Saturday
                dow_modifier = rng.uniform(0.7, 0.9)
            elif dow == 6:  # Sunday
                dow_modifier = rng.uniform(0.75, 0.95)
            elif dow == 0:  # Monday
                dow_modifier = rng.uniform(1.05, 1.15)

            # Trend component
            trend_modifier = 1.0 + (trend_direction * day_offset)

            # Random noise
            noise = rng.gauss(1.0, 0.15)
            noise = max(0.5, min(1.5, noise))

            # Combined modifier
            modifier = dow_modifier * trend_modifier * noise

            day_data = {
                "date": current_date,
                "impressions": max(0, int(daily_avg["impressions"] * modifier)),
                "clicks": max(0, int(daily_avg["clicks"] * modifier)),
                "conversions": max(0, int(daily_avg["conversions"] * modifier * rng.uniform(0.7, 1.3))),
                "spend_cents": max(0, int(daily_avg["spend_cents"] * modifier)),
                "revenue_cents": max(0, int(daily_avg["revenue_cents"] * modifier * rng.uniform(0.8, 1.2))),
            }

            # Add video metrics if present
            if base_metrics.get("video_views"):
                day_data["video_views"] = int(day_data["impressions"] * rng.uniform(0.3, 0.6))
                day_data["video_completions"] = int(day_data["video_views"] * rng.uniform(0.2, 0.4))

            daily_metrics.append(day_data)

        return daily_metrics


class MockAdNetworkManager:
    """
    Manager for coordinating mock data across multiple ad platforms.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.network = MockAdNetwork(seed=tenant_id)

    async def sync_all_platforms(self) -> Dict[str, Any]:
        """Simulate syncing data from all platforms."""

        campaigns = self.network.generate_campaigns(
            self.tenant_id,
            count=25,
            platforms=list(AdPlatform),
        )

        logger.info(
            "mock_sync_completed",
            tenant_id=self.tenant_id,
            campaigns_generated=len(campaigns),
        )

        return {
            "campaigns": campaigns,
            "synced_at": datetime.now(timezone.utc),
            "platform_status": {
                platform.value: "success" for platform in AdPlatform
            },
        }

    async def get_campaign_details(self, external_id: str) -> Optional[MockCampaignData]:
        """Get details for a specific campaign."""
        # In a real implementation, this would call the actual API
        # For mock, we regenerate based on the ID
        campaigns = self.network.generate_campaigns(self.tenant_id, count=30)
        for campaign in campaigns:
            if campaign.external_id == external_id:
                return campaign
        return None
