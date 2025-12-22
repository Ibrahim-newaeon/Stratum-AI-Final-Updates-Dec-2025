# =============================================================================
# Stratum AI - LinkedIn Ads API Client
# =============================================================================
"""
LinkedIn Marketing API client for managing ad campaigns,
fetching analytics, and handling authentication with LinkedIn Ads.

LinkedIn Marketing API Documentation:
https://learn.microsoft.com/en-us/linkedin/marketing/
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class LinkedInAdsClient:
    """
    LinkedIn Marketing API client.

    Handles:
    - OAuth 2.0 authentication
    - Campaign management (CRUD)
    - Ad account management
    - Analytics and reporting
    - Audience targeting
    """

    BASE_URL = "https://api.linkedin.com/rest"
    AUTH_URL = "https://www.linkedin.com/oauth/v2"
    API_VERSION = "202401"  # LinkedIn API versioning

    def __init__(
        self,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize LinkedIn Ads client.

        Args:
            access_token: OAuth 2.0 access token
            client_id: LinkedIn App Client ID
            client_secret: LinkedIn App Client Secret
        """
        self.access_token = access_token or settings.linkedin_access_token
        self.client_id = client_id or settings.linkedin_client_id
        self.client_secret = client_secret or settings.linkedin_client_secret

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self.API_VERSION,
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the LinkedIn API."""
        url = f"{self.BASE_URL}/{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(
                        url, headers=self._get_headers(), params=params
                    )
                elif method == "POST":
                    response = await client.post(
                        url, headers=self._get_headers(), json=payload
                    )
                elif method == "PATCH":
                    response = await client.patch(
                        url, headers=self._get_headers(), json=payload
                    )
                elif method == "DELETE":
                    response = await client.delete(
                        url, headers=self._get_headers()
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                if response.status_code == 204:
                    return {"success": True}

                return response.json()

            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except Exception:
                    pass

                logger.error(
                    f"LinkedIn API error: {error_data.get('message', str(e))}",
                    extra={
                        "status_code": e.response.status_code,
                        "error_code": error_data.get("code"),
                    },
                )
                raise LinkedInAPIError(
                    message=error_data.get("message", str(e)),
                    status_code=e.response.status_code,
                    error_code=error_data.get("code"),
                )

    # -------------------------------------------------------------------------
    # OAuth Methods
    # -------------------------------------------------------------------------

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authorization
            state: Random state for CSRF protection

        Returns:
            Authorization URL
        """
        scopes = [
            "r_ads",
            "r_ads_reporting",
            "rw_ads",
            "r_organization_social",
            "w_organization_social",
        ]

        return (
            f"{self.AUTH_URL}/authorization?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope={' '.join(scopes)}"
        )

    async def exchange_code_for_token(
        self, code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Token response with access_token and refresh_token
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.AUTH_URL}/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New token response
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.AUTH_URL}/accessToken",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()

    # -------------------------------------------------------------------------
    # Ad Account Methods
    # -------------------------------------------------------------------------

    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all ad accounts the user has access to.

        Returns:
            List of ad accounts
        """
        response = await self._make_request("GET", "adAccounts")
        return response.get("elements", [])

    async def get_ad_account(self, account_id: str) -> Dict[str, Any]:
        """
        Get details of a specific ad account.

        Args:
            account_id: LinkedIn ad account ID

        Returns:
            Ad account details
        """
        return await self._make_request("GET", f"adAccounts/{account_id}")

    # -------------------------------------------------------------------------
    # Campaign Group Methods
    # -------------------------------------------------------------------------

    async def get_campaign_groups(
        self, account_id: str, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get campaign groups for an ad account.

        Args:
            account_id: LinkedIn ad account ID
            search: Optional search query

        Returns:
            List of campaign groups
        """
        params = {"q": "search", "account": f"urn:li:sponsoredAccount:{account_id}"}
        if search:
            params["name"] = search

        response = await self._make_request("GET", "adCampaignGroups", params=params)
        return response.get("elements", [])

    async def create_campaign_group(
        self,
        account_id: str,
        name: str,
        status: str = "ACTIVE",
        run_schedule: Optional[Dict] = None,
        total_budget: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Create a new campaign group.

        Args:
            account_id: LinkedIn ad account ID
            name: Campaign group name
            status: ACTIVE, PAUSED, ARCHIVED, DRAFT, CANCELED
            run_schedule: Optional schedule with start/end dates
            total_budget: Optional total budget configuration

        Returns:
            Created campaign group
        """
        payload = {
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "name": name,
            "status": status,
        }

        if run_schedule:
            payload["runSchedule"] = run_schedule

        if total_budget:
            payload["totalBudget"] = total_budget

        return await self._make_request("POST", "adCampaignGroups", payload)

    # -------------------------------------------------------------------------
    # Campaign Methods
    # -------------------------------------------------------------------------

    async def get_campaigns(
        self,
        account_id: str,
        campaign_group_id: Optional[str] = None,
        status: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get campaigns for an ad account.

        Args:
            account_id: LinkedIn ad account ID
            campaign_group_id: Optional campaign group filter
            status: Optional status filter

        Returns:
            List of campaigns
        """
        params = {"q": "search", "account": f"urn:li:sponsoredAccount:{account_id}"}

        if campaign_group_id:
            params["campaignGroup"] = f"urn:li:sponsoredCampaignGroup:{campaign_group_id}"

        if status:
            params["status"] = ",".join(status)

        response = await self._make_request("GET", "adCampaigns", params=params)
        return response.get("elements", [])

    async def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get details of a specific campaign.

        Args:
            campaign_id: LinkedIn campaign ID

        Returns:
            Campaign details
        """
        return await self._make_request("GET", f"adCampaigns/{campaign_id}")

    async def create_campaign(
        self,
        account_id: str,
        campaign_group_id: str,
        name: str,
        objective_type: str,
        daily_budget: Dict[str, Any],
        targeting: Dict[str, Any],
        creative_selection: str = "OPTIMIZED",
        status: str = "PAUSED",
        locale: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new campaign.

        Args:
            account_id: LinkedIn ad account ID
            campaign_group_id: Parent campaign group ID
            name: Campaign name
            objective_type: BRAND_AWARENESS, ENGAGEMENT, VIDEO_VIEWS, LEAD_GENERATION, WEBSITE_VISITS, WEBSITE_CONVERSIONS, JOB_APPLICANTS
            daily_budget: Budget configuration with amount and currency
            targeting: Targeting criteria
            creative_selection: OPTIMIZED or ROUND_ROBIN
            status: Campaign status
            locale: Locale configuration

        Returns:
            Created campaign
        """
        payload = {
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "campaignGroup": f"urn:li:sponsoredCampaignGroup:{campaign_group_id}",
            "name": name,
            "objectiveType": objective_type,
            "dailyBudget": daily_budget,
            "targeting": targeting,
            "creativeSelection": creative_selection,
            "status": status,
            "locale": locale or {"country": "US", "language": "en"},
            "type": "SPONSORED_UPDATES",
            "costType": "CPM",
            "unitCost": {"amount": "10", "currencyCode": "USD"},
        }

        return await self._make_request("POST", "adCampaigns", payload)

    async def update_campaign(
        self, campaign_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a campaign.

        Args:
            campaign_id: LinkedIn campaign ID
            updates: Fields to update

        Returns:
            Updated campaign
        """
        return await self._make_request("PATCH", f"adCampaigns/{campaign_id}", updates)

    async def update_campaign_status(
        self, campaign_id: str, status: str
    ) -> Dict[str, Any]:
        """
        Update campaign status.

        Args:
            campaign_id: LinkedIn campaign ID
            status: New status (ACTIVE, PAUSED, ARCHIVED, DRAFT, CANCELED)

        Returns:
            Updated campaign
        """
        return await self.update_campaign(campaign_id, {"status": status})

    # -------------------------------------------------------------------------
    # Creative/Ad Methods
    # -------------------------------------------------------------------------

    async def get_creatives(
        self, campaign_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get creatives for a campaign.

        Args:
            campaign_id: LinkedIn campaign ID

        Returns:
            List of creatives
        """
        params = {
            "q": "criteria",
            "campaigns": f"urn:li:sponsoredCampaign:{campaign_id}",
        }
        response = await self._make_request("GET", "adCreatives", params=params)
        return response.get("elements", [])

    async def create_creative(
        self,
        campaign_id: str,
        reference_share: str,
        status: str = "ACTIVE",
    ) -> Dict[str, Any]:
        """
        Create a new creative (ad).

        Args:
            campaign_id: LinkedIn campaign ID
            reference_share: URN of the share (content) to promote
            status: Creative status

        Returns:
            Created creative
        """
        payload = {
            "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
            "reference": reference_share,
            "status": status,
            "type": "SPONSORED_STATUS_UPDATE",
        }

        return await self._make_request("POST", "adCreatives", payload)

    # -------------------------------------------------------------------------
    # Analytics Methods
    # -------------------------------------------------------------------------

    async def get_campaign_analytics(
        self,
        campaign_ids: List[str],
        start_date: date,
        end_date: date,
        time_granularity: str = "DAILY",
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get analytics for campaigns.

        Args:
            campaign_ids: List of campaign IDs
            start_date: Start date for analytics
            end_date: End date for analytics
            time_granularity: DAILY, MONTHLY, ALL
            fields: Specific fields to fetch

        Returns:
            Analytics data
        """
        default_fields = [
            "externalWebsiteConversions",
            "externalWebsitePostClickConversions",
            "externalWebsitePostViewConversions",
            "impressions",
            "clicks",
            "costInLocalCurrency",
            "costInUsd",
            "dateRange",
            "landingPageClicks",
            "likes",
            "comments",
            "shares",
            "follows",
            "videoStarts",
            "videoFirstQuartileCompletions",
            "videoMidpointCompletions",
            "videoThirdQuartileCompletions",
            "videoCompletions",
            "leadGenerationMailInterestedClicks",
            "oneClickLeads",
            "opens",
            "sends",
        ]

        campaigns_param = ",".join([
            f"urn:li:sponsoredCampaign:{cid}" for cid in campaign_ids
        ])

        params = {
            "q": "analytics",
            "pivot": "CAMPAIGN",
            "dateRange": (
                f"(start:(day:{start_date.day},month:{start_date.month},year:{start_date.year}),"
                f"end:(day:{end_date.day},month:{end_date.month},year:{end_date.year}))"
            ),
            "timeGranularity": time_granularity,
            "campaigns": f"List({campaigns_param})",
            "fields": ",".join(fields or default_fields),
        }

        response = await self._make_request("GET", "adAnalytics", params=params)
        return response.get("elements", [])

    async def get_account_analytics(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
        time_granularity: str = "DAILY",
    ) -> List[Dict[str, Any]]:
        """
        Get account-level analytics.

        Args:
            account_id: LinkedIn ad account ID
            start_date: Start date
            end_date: End date
            time_granularity: DAILY, MONTHLY, ALL

        Returns:
            Account analytics data
        """
        params = {
            "q": "analytics",
            "pivot": "ACCOUNT",
            "dateRange": (
                f"(start:(day:{start_date.day},month:{start_date.month},year:{start_date.year}),"
                f"end:(day:{end_date.day},month:{end_date.month},year:{end_date.year}))"
            ),
            "timeGranularity": time_granularity,
            "accounts": f"List(urn:li:sponsoredAccount:{account_id})",
        }

        response = await self._make_request("GET", "adAnalytics", params=params)
        return response.get("elements", [])

    # -------------------------------------------------------------------------
    # Audience/Targeting Methods
    # -------------------------------------------------------------------------

    async def get_targeting_facets(self) -> Dict[str, Any]:
        """
        Get available targeting facets.

        Returns:
            Available targeting options
        """
        return await self._make_request("GET", "adTargetingFacets")

    async def search_companies(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for companies for targeting.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching companies
        """
        params = {"q": "typeahead", "query": query, "count": limit}
        response = await self._make_request("GET", "organizationsTypeahead", params=params)
        return response.get("elements", [])

    async def get_audience_counts(
        self, targeting_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get estimated audience size for targeting criteria.

        Args:
            targeting_criteria: Targeting configuration

        Returns:
            Audience count estimates
        """
        payload = {"targetingCriteria": targeting_criteria}
        return await self._make_request("POST", "adTargetingAnalytics", payload)

    # -------------------------------------------------------------------------
    # Conversion Tracking Methods
    # -------------------------------------------------------------------------

    async def get_conversions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get conversion actions for an account.

        Args:
            account_id: LinkedIn ad account ID

        Returns:
            List of conversion actions
        """
        params = {
            "q": "account",
            "account": f"urn:li:sponsoredAccount:{account_id}",
        }
        response = await self._make_request("GET", "conversions", params=params)
        return response.get("elements", [])

    async def create_conversion(
        self,
        account_id: str,
        name: str,
        conversion_type: str,
        attribution_type: str = "LAST_TOUCH_BY_CAMPAIGN",
        post_click_window: int = 30,
        post_view_window: int = 7,
    ) -> Dict[str, Any]:
        """
        Create a conversion action.

        Args:
            account_id: LinkedIn ad account ID
            name: Conversion name
            conversion_type: Type (e.g., PURCHASE, SIGN_UP, LEAD)
            attribution_type: Attribution model
            post_click_window: Days for post-click attribution
            post_view_window: Days for post-view attribution

        Returns:
            Created conversion action
        """
        payload = {
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "name": name,
            "type": conversion_type,
            "attributionType": attribution_type,
            "postClickAttributionWindowSize": post_click_window,
            "viewThroughAttributionWindowSize": post_view_window,
            "enabled": True,
        }

        return await self._make_request("POST", "conversions", payload)


# Singleton instance factory
def get_linkedin_client() -> LinkedInAdsClient:
    """Get a configured LinkedIn Ads client instance."""
    return LinkedInAdsClient()
