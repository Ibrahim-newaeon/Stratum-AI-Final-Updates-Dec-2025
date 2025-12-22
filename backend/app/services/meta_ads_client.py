# =============================================================================
# Stratum AI - Meta (Facebook) Ads API Client
# =============================================================================
"""
Meta Marketing API client for fetching campaign data and insights.
Used to sync real campaign performance data for ML training.

API Documentation: https://developers.facebook.com/docs/marketing-apis
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger
from app.models import AdPlatform, CampaignStatus

logger = get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class MetaCampaign:
    """Represents a Meta campaign with its data."""

    id: str
    account_id: str
    name: str
    status: str
    objective: str
    daily_budget: Optional[int]  # in cents
    lifetime_budget: Optional[int]  # in cents
    created_time: datetime
    updated_time: datetime
    start_time: Optional[datetime]
    stop_time: Optional[datetime]


@dataclass
class MetaInsights:
    """Campaign insights/metrics from Meta."""

    campaign_id: str
    date_start: date
    date_stop: date
    impressions: int
    clicks: int
    spend: float  # in account currency
    reach: int
    frequency: float
    cpc: float
    cpm: float
    ctr: float
    conversions: int
    conversion_value: float
    actions: Dict[str, int]
    cost_per_action: Dict[str, float]


# =============================================================================
# Meta Ads API Client
# =============================================================================
class MetaAdsClient:
    """
    Client for Meta Marketing API.

    Fetches:
    - Ad accounts
    - Campaigns with targeting
    - Daily insights/metrics
    - Demographics breakdown
    """

    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    def __init__(self, access_token: str):
        """
        Initialize the Meta Ads client.

        Args:
            access_token: Meta system user access token with ads_read permission
        """
        self.access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _url(self, endpoint: str) -> str:
        """Build API URL."""
        return f"{self.BASE_URL}/{self.API_VERSION}/{endpoint}"

    async def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make GET request to Meta API."""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        params = params or {}
        params["access_token"] = self.access_token

        response = await self._client.get(self._url(endpoint), params=params)

        if response.status_code != 200:
            error = response.json().get("error", {})
            logger.error(
                "meta_api_error",
                endpoint=endpoint,
                status=response.status_code,
                error=error,
            )
            raise MetaAPIError(
                error.get("message", "Unknown error"),
                error.get("code"),
                error.get("error_subcode"),
            )

        return response.json()

    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all ad accounts accessible by this token.

        Returns:
            List of ad account dictionaries with id, name, currency, etc.
        """
        data = await self._get(
            "me/adaccounts",
            params={
                "fields": "id,name,account_id,currency,timezone_name,account_status,amount_spent,balance",
                "limit": 100,
            },
        )
        return data.get("data", [])

    async def get_campaigns(
        self,
        account_id: str,
        limit: int = 100,
    ) -> List[MetaCampaign]:
        """
        Get campaigns for an ad account.

        Args:
            account_id: Ad account ID (with or without 'act_' prefix)
            limit: Maximum campaigns to fetch

        Returns:
            List of MetaCampaign objects
        """
        # Ensure account_id has act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        data = await self._get(
            f"{account_id}/campaigns",
            params={
                "fields": ",".join([
                    "id",
                    "name",
                    "status",
                    "effective_status",
                    "objective",
                    "daily_budget",
                    "lifetime_budget",
                    "created_time",
                    "updated_time",
                    "start_time",
                    "stop_time",
                    "buying_type",
                    "special_ad_categories",
                ]),
                "limit": limit,
            },
        )

        campaigns = []
        for c in data.get("data", []):
            campaigns.append(MetaCampaign(
                id=c["id"],
                account_id=account_id,
                name=c["name"],
                status=c.get("effective_status", c.get("status", "UNKNOWN")),
                objective=c.get("objective", "UNKNOWN"),
                daily_budget=int(c["daily_budget"]) if c.get("daily_budget") else None,
                lifetime_budget=int(c["lifetime_budget"]) if c.get("lifetime_budget") else None,
                created_time=datetime.fromisoformat(c["created_time"].replace("+0000", "+00:00")),
                updated_time=datetime.fromisoformat(c["updated_time"].replace("+0000", "+00:00")),
                start_time=datetime.fromisoformat(c["start_time"].replace("+0000", "+00:00")) if c.get("start_time") else None,
                stop_time=datetime.fromisoformat(c["stop_time"].replace("+0000", "+00:00")) if c.get("stop_time") else None,
            ))

        return campaigns

    async def get_campaign_insights(
        self,
        campaign_id: str,
        date_start: date,
        date_stop: date,
        time_increment: int = 1,  # 1 = daily, 7 = weekly, etc.
    ) -> List[MetaInsights]:
        """
        Get insights for a campaign.

        Args:
            campaign_id: Campaign ID
            date_start: Start date for insights
            date_stop: End date for insights
            time_increment: Days per row (1 for daily)

        Returns:
            List of MetaInsights objects (one per day/period)
        """
        data = await self._get(
            f"{campaign_id}/insights",
            params={
                "fields": ",".join([
                    "campaign_id",
                    "campaign_name",
                    "impressions",
                    "clicks",
                    "spend",
                    "reach",
                    "frequency",
                    "cpc",
                    "cpm",
                    "ctr",
                    "actions",
                    "action_values",
                    "cost_per_action_type",
                    "conversions",
                    "conversion_values",
                ]),
                "time_range": f'{{"since":"{date_start.isoformat()}","until":"{date_stop.isoformat()}"}}',
                "time_increment": time_increment,
                "level": "campaign",
            },
        )

        insights = []
        for row in data.get("data", []):
            # Parse actions to get conversions
            actions = {}
            conversions = 0
            for action in row.get("actions", []):
                actions[action["action_type"]] = int(action["value"])
                if action["action_type"] in ["purchase", "complete_registration", "lead", "add_to_cart"]:
                    conversions += int(action["value"])

            # Parse action values for conversion value
            conversion_value = 0.0
            for av in row.get("action_values", []):
                if av["action_type"] in ["purchase", "omni_purchase"]:
                    conversion_value += float(av["value"])

            # Parse cost per action
            cost_per_action = {}
            for cpa in row.get("cost_per_action_type", []):
                cost_per_action[cpa["action_type"]] = float(cpa["value"])

            insights.append(MetaInsights(
                campaign_id=row.get("campaign_id", campaign_id),
                date_start=date.fromisoformat(row["date_start"]),
                date_stop=date.fromisoformat(row["date_stop"]),
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                spend=float(row.get("spend", 0)),
                reach=int(row.get("reach", 0)),
                frequency=float(row.get("frequency", 0)),
                cpc=float(row.get("cpc", 0)),
                cpm=float(row.get("cpm", 0)),
                ctr=float(row.get("ctr", 0)),
                conversions=conversions,
                conversion_value=conversion_value,
                actions=actions,
                cost_per_action=cost_per_action,
            ))

        return insights

    async def get_campaign_demographics(
        self,
        campaign_id: str,
        date_start: date,
        date_stop: date,
    ) -> Dict[str, Any]:
        """
        Get demographic breakdown for a campaign.

        Args:
            campaign_id: Campaign ID
            date_start: Start date
            date_stop: End date

        Returns:
            Dictionary with age, gender, and location breakdowns
        """
        demographics = {
            "age": {},
            "gender": {},
            "location": {},
        }

        # Get age and gender breakdown
        try:
            age_gender_data = await self._get(
                f"{campaign_id}/insights",
                params={
                    "fields": "impressions,clicks,spend,actions",
                    "time_range": f'{{"since":"{date_start.isoformat()}","until":"{date_stop.isoformat()}"}}',
                    "breakdowns": "age,gender",
                },
            )

            for row in age_gender_data.get("data", []):
                age = row.get("age", "unknown")
                gender = row.get("gender", "unknown")

                # Aggregate by age
                if age not in demographics["age"]:
                    demographics["age"][age] = {"impressions": 0, "clicks": 0, "spend": 0}
                demographics["age"][age]["impressions"] += int(row.get("impressions", 0))
                demographics["age"][age]["clicks"] += int(row.get("clicks", 0))
                demographics["age"][age]["spend"] += float(row.get("spend", 0))

                # Aggregate by gender
                if gender not in demographics["gender"]:
                    demographics["gender"][gender] = {"impressions": 0, "clicks": 0, "spend": 0}
                demographics["gender"][gender]["impressions"] += int(row.get("impressions", 0))
                demographics["gender"][gender]["clicks"] += int(row.get("clicks", 0))
                demographics["gender"][gender]["spend"] += float(row.get("spend", 0))

        except MetaAPIError as e:
            logger.warning(f"Could not fetch age/gender breakdown: {e}")

        # Get location breakdown
        try:
            location_data = await self._get(
                f"{campaign_id}/insights",
                params={
                    "fields": "impressions,clicks,spend",
                    "time_range": f'{{"since":"{date_start.isoformat()}","until":"{date_stop.isoformat()}"}}',
                    "breakdowns": "country",
                },
            )

            for row in location_data.get("data", []):
                country = row.get("country", "unknown")
                demographics["location"][country] = {
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                }

        except MetaAPIError as e:
            logger.warning(f"Could not fetch location breakdown: {e}")

        return demographics

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection and token validity.

        Returns:
            Dictionary with connection status and account info
        """
        try:
            # Get token info
            data = await self._get(
                "me",
                params={"fields": "id,name"},
            )

            # Get ad accounts count
            accounts = await self.get_ad_accounts()

            return {
                "success": True,
                "user_id": data.get("id"),
                "user_name": data.get("name"),
                "ad_accounts_count": len(accounts),
                "ad_accounts": [
                    {"id": a["id"], "name": a["name"]}
                    for a in accounts[:5]  # First 5 accounts
                ],
            }

        except MetaAPIError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# =============================================================================
# Meta API Error
# =============================================================================
class MetaAPIError(Exception):
    """Exception for Meta API errors."""

    def __init__(self, message: str, code: Optional[int] = None, subcode: Optional[int] = None):
        self.message = message
        self.code = code
        self.subcode = subcode
        super().__init__(message)

    def __str__(self):
        if self.code:
            return f"Meta API Error {self.code}: {self.message}"
        return f"Meta API Error: {self.message}"


# =============================================================================
# Campaign Status Mapping
# =============================================================================
def map_meta_status(meta_status: str) -> CampaignStatus:
    """Map Meta campaign status to internal status."""
    status_map = {
        "ACTIVE": CampaignStatus.ACTIVE,
        "PAUSED": CampaignStatus.PAUSED,
        "DELETED": CampaignStatus.ARCHIVED,
        "ARCHIVED": CampaignStatus.ARCHIVED,
        "IN_PROCESS": CampaignStatus.DRAFT,
        "WITH_ISSUES": CampaignStatus.PAUSED,
        "CAMPAIGN_PAUSED": CampaignStatus.PAUSED,
        "ADSET_PAUSED": CampaignStatus.PAUSED,
        "PENDING_REVIEW": CampaignStatus.DRAFT,
        "DISAPPROVED": CampaignStatus.PAUSED,
        "PREAPPROVED": CampaignStatus.DRAFT,
        "PENDING_BILLING_INFO": CampaignStatus.PAUSED,
    }
    return status_map.get(meta_status, CampaignStatus.DRAFT)
