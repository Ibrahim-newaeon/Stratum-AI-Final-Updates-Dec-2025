"""
Stratum AI: Snapchat Marketing API Adapter
==========================================

This adapter provides bi-directional integration with Snapchat's Marketing API,
enabling Stratum to manage advertising campaigns on Snapchat's unique visual platform.
Snapchat's audience skews younger and the platform excels at augmented reality (AR)
experiences, making it particularly valuable for brands targeting Gen Z.

Understanding Snapchat's Advertising Structure
----------------------------------------------

Snapchat organizes advertising in a hierarchy similar to other platforms but with
some unique terminology. The hierarchy is: Organization → Ad Account → Campaign →
Ad Squad → Ad. Note that Snapchat uses "Ad Squad" instead of "Ad Set" or "Ad Group".

Ad Squads are where you define targeting, bid, and budget settings. Snapchat offers
several ad formats unique to the platform, including Snap Ads (full-screen video),
Story Ads, Collection Ads, AR Lenses, and Filters. This adapter focuses on the
standard auction-based ad formats.

Authentication
--------------

Snapchat uses OAuth 2.0 for authentication. The flow involves creating an OAuth app
in Snapchat's Business Manager, then directing users through Snapchat's authorization
URL to obtain an authorization code. This code is exchanged for access and refresh
tokens.

Key points about Snapchat OAuth:
- Access tokens expire after 30 minutes (1800 seconds)
- Refresh tokens can be used to obtain new access tokens
- Refresh tokens themselves eventually expire and require re-authorization
- This adapter handles automatic token refresh

Rate Limits
-----------

Snapchat's API has rate limits of approximately 1000 requests per 5 minutes. The
API returns rate limit information in response headers (X-RateLimit-Remaining,
X-RateLimit-Reset). This adapter monitors these headers to avoid hitting limits.

API Base URL
------------

Production: https://adsapi.snapchat.com/v1
The API version is included in the URL path.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    BaseAdapter,
    PlatformError,
    RateLimiter,
    RateLimitError,
)
from app.stratum.models import (
    AutomationAction,
    EMQScore,
    EntityStatus,
    PerformanceMetrics,
    Platform,
    UnifiedAccount,
    UnifiedAd,
    UnifiedAdSet,
    UnifiedCampaign,
)

logger = logging.getLogger("stratum.adapters.snapchat")


class SnapchatAdapter(BaseAdapter):
    """
    Snapchat Marketing API adapter for Snap advertising campaigns.

    This adapter handles REST API calls to Snapchat's Marketing API, translating
    between Stratum's unified models and Snapchat's native formats. Snapchat's API
    is well-documented and follows RESTful conventions.

    Required Credentials:
        client_id: Your Snapchat OAuth app client ID
        client_secret: Your Snapchat OAuth app client secret
        refresh_token: OAuth refresh token for the authorized user

    Optional:
        organization_id: Default organization ID
        ad_account_id: Default ad account ID

    Example Usage:

        credentials = {
            "client_id": "abc123...",
            "client_secret": "xyz789...",
            "refresh_token": "32eb12f0...",
            "ad_account_id": "8adc3db7-..."
        }

        adapter = SnapchatAdapter(credentials)
        await adapter.initialize()

        campaigns = await adapter.get_campaigns("8adc3db7-...")
    """

    # Snapchat API endpoints
    BASE_URL = "https://adsapi.snapchat.com/v1"
    AUTH_URL = "https://accounts.snapchat.com/login/oauth2/access_token"

    # Status mapping
    STATUS_TO_SNAPCHAT = {
        EntityStatus.ACTIVE: "ACTIVE",
        EntityStatus.PAUSED: "PAUSED",
    }

    STATUS_FROM_SNAPCHAT = {
        "ACTIVE": EntityStatus.ACTIVE,
        "PAUSED": EntityStatus.PAUSED,
        "PENDING": EntityStatus.PENDING_REVIEW,
        "PENDING_REVIEW": EntityStatus.PENDING_REVIEW,
    }

    def __init__(self, credentials: dict[str, str]):
        """
        Initialize the Snapchat adapter with OAuth credentials.

        Snapchat requires OAuth tokens for all API access. The refresh_token
        is used to obtain new access tokens when they expire.
        """
        super().__init__(credentials)

        # Validate required credentials
        required = ["client_id", "client_secret", "refresh_token"]
        missing = [k for k in required if k not in credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {missing}")

        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.refresh_token = credentials["refresh_token"]
        self.organization_id = credentials.get("organization_id")
        self.default_ad_account_id = credentials.get("ad_account_id")

        # Access token management
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # HTTP session
        self.session: Optional[requests.Session] = None

        # Rate limiter for Snapchat's limits (1000/5min = ~3.3/sec)
        self.rate_limiter = RateLimiter(
            calls_per_minute=180,  # Conservative limit
            burst_size=30,
        )

    @property
    def platform(self) -> Platform:
        """Return the platform identifier."""
        return Platform.SNAPCHAT

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def initialize(self) -> None:
        """
        Initialize the Snapchat API client and obtain access token.

        This method exchanges the refresh token for an access token and
        verifies the connection by fetching organization info.
        """
        logger.info("Initializing Snapchat Marketing API adapter")

        try:
            # Create session
            self.session = requests.Session()

            # Get initial access token
            await self._refresh_access_token()

            # Verify authentication
            await self.rate_limiter.acquire()
            response = self._make_request("GET", "/me")

            if "me" not in response:
                raise AuthenticationError("Failed to verify Snapchat authentication")

            # Get organization info if available
            me_data = response.get("me", {})
            if not self.organization_id and me_data.get("organization_id"):
                self.organization_id = me_data["organization_id"]

            logger.info("Successfully authenticated with Snapchat API")
            self._initialized = True

        except requests.RequestException as e:
            raise AdapterError(f"Failed to connect to Snapchat API: {e}")

    async def cleanup(self) -> None:
        """Clean up adapter resources."""
        if self.session:
            self.session.close()
            self.session = None
        self._initialized = False
        self.access_token = None
        logger.info("Snapchat adapter cleanup complete")

    async def _refresh_access_token(self) -> None:
        """
        Obtain a new access token using the refresh token.

        Snapchat access tokens expire after 30 minutes. This method
        exchanges the refresh token for a new access token.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        response = requests.post(self.AUTH_URL, data=data, timeout=30)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]

        # Calculate expiry time (Snapchat returns expires_in in seconds)
        expires_in = token_data.get("expires_in", 1800)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)

        # Update refresh token if a new one was provided
        if "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]

        logger.debug("Snapchat access token refreshed")

    async def _ensure_valid_token(self) -> None:
        """Ensure the access token is valid, refreshing if needed."""
        if not self.access_token or (
            self.token_expires_at and datetime.utcnow() >= self.token_expires_at
        ):
            await self._refresh_access_token()

    # ========================================================================
    # READ OPERATIONS
    # ========================================================================

    async def get_accounts(self) -> list[UnifiedAccount]:
        """
        Fetch ad accounts accessible with current credentials.

        Snapchat organizes accounts under organizations. This method fetches
        all ad accounts the authenticated user can access.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()

        try:
            # First get organizations if we don't have one
            if not self.organization_id:
                response = self._make_request("GET", "/me/organizations")
                orgs = response.get("organizations", [])
                if orgs:
                    self.organization_id = orgs[0].get("organization", {}).get("id")

            if not self.organization_id:
                logger.warning("No organization found")
                return []

            # Get ad accounts for the organization
            await self.rate_limiter.acquire()
            response = self._make_request(
                "GET", f"/organizations/{self.organization_id}/adaccounts"
            )

            accounts = []
            for item in response.get("adaccounts", []):
                aa = item.get("adaccount", {})
                account = UnifiedAccount(
                    platform=Platform.SNAPCHAT,
                    account_id=aa.get("id", ""),
                    account_name=aa.get("name", "Unknown"),
                    business_id=self.organization_id,
                    timezone=aa.get("timezone", "UTC"),
                    currency=aa.get("currency", "USD"),
                    last_synced=datetime.utcnow(),
                    raw_data=aa,
                )
                accounts.append(account)

            return accounts

        except Exception as e:
            raise PlatformError(f"Failed to fetch accounts: {e}")

    async def get_campaigns(
        self, account_id: str, status_filter: Optional[list[EntityStatus]] = None
    ) -> list[UnifiedCampaign]:
        """
        Fetch campaigns for the specified Snapchat ad account.

        Snapchat campaigns define the objective and can optionally have
        daily or lifetime spending limits.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()

        try:
            response = self._make_request("GET", f"/adaccounts/{account_id}/campaigns")

            campaigns = []
            for item in response.get("campaigns", []):
                c = item.get("campaign", {})

                # Apply status filter if specified
                status = self.STATUS_FROM_SNAPCHAT.get(
                    c.get("status", "ACTIVE"), EntityStatus.ACTIVE
                )
                if status_filter and status not in status_filter:
                    continue

                campaign = UnifiedCampaign(
                    platform=Platform.SNAPCHAT,
                    account_id=account_id,
                    campaign_id=c.get("id", ""),
                    campaign_name=c.get("name", ""),
                    status=status,
                    daily_budget=self._micros_to_dollars(c.get("daily_budget_micro")),
                    lifetime_budget=self._micros_to_dollars(c.get("lifetime_spend_cap_micro")),
                    created_at=self._parse_datetime(c.get("created_at")),
                    updated_at=self._parse_datetime(c.get("updated_at")),
                    last_synced=datetime.utcnow(),
                    raw_data=c,
                )
                campaigns.append(campaign)

            logger.info(f"Fetched {len(campaigns)} campaigns from Snapchat account {account_id}")
            return campaigns

        except Exception as e:
            raise PlatformError(f"Failed to fetch campaigns: {e}")

    async def get_adsets(
        self, account_id: str, campaign_id: Optional[str] = None
    ) -> list[UnifiedAdSet]:
        """
        Fetch ad squads (Snapchat's term for ad sets) for the account.

        Ad Squads contain targeting, bid, and budget configuration.
        Snapchat requires fetching ad squads per campaign.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()

        try:
            # If campaign_id provided, fetch directly
            if campaign_id:
                await self.rate_limiter.acquire()
                response = self._make_request("GET", f"/campaigns/{campaign_id}/adsquads")
                return self._parse_adsquads(response, account_id, campaign_id)

            # Otherwise, get all campaigns first and fetch ad squads for each
            campaigns = await self.get_campaigns(account_id)
            all_adsets = []

            for campaign in campaigns:
                await self.rate_limiter.acquire()
                response = self._make_request("GET", f"/campaigns/{campaign.campaign_id}/adsquads")
                adsets = self._parse_adsquads(response, account_id, campaign.campaign_id)
                all_adsets.extend(adsets)

            return all_adsets

        except Exception as e:
            raise PlatformError(f"Failed to fetch ad squads: {e}")

    def _parse_adsquads(
        self, response: dict[str, Any], account_id: str, campaign_id: str
    ) -> list[UnifiedAdSet]:
        """Parse ad squads from API response."""
        adsets = []
        for item in response.get("adsquads", []):
            sq = item.get("adsquad", {})
            adset = UnifiedAdSet(
                platform=Platform.SNAPCHAT,
                account_id=account_id,
                campaign_id=campaign_id,
                adset_id=sq.get("id", ""),
                adset_name=sq.get("name", ""),
                status=self.STATUS_FROM_SNAPCHAT.get(
                    sq.get("status", "ACTIVE"), EntityStatus.ACTIVE
                ),
                daily_budget=self._micros_to_dollars(sq.get("daily_budget_micro")),
                lifetime_budget=self._micros_to_dollars(sq.get("lifetime_budget_micro")),
                bid_amount=self._micros_to_dollars(sq.get("bid_micro")),
                start_time=self._parse_datetime(sq.get("start_time")),
                end_time=self._parse_datetime(sq.get("end_time")),
                last_synced=datetime.utcnow(),
                raw_data=sq,
            )
            adsets.append(adset)
        return adsets

    async def get_ads(self, account_id: str, adset_id: Optional[str] = None) -> list[UnifiedAd]:
        """
        Fetch ads for the specified account.

        Snapchat ads contain creative references and are linked to ad squads.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()

        try:
            if adset_id:
                await self.rate_limiter.acquire()
                response = self._make_request("GET", f"/adsquads/{adset_id}/ads")
                return self._parse_ads(response, account_id, "", adset_id)

            # Get all ad squads and their ads
            adsets = await self.get_adsets(account_id)
            all_ads = []

            for adset in adsets:
                await self.rate_limiter.acquire()
                response = self._make_request("GET", f"/adsquads/{adset.adset_id}/ads")
                ads = self._parse_ads(response, account_id, adset.campaign_id, adset.adset_id)
                all_ads.extend(ads)

            return all_ads

        except Exception as e:
            raise PlatformError(f"Failed to fetch ads: {e}")

    def _parse_ads(
        self, response: dict[str, Any], account_id: str, campaign_id: str, adset_id: str
    ) -> list[UnifiedAd]:
        """Parse ads from API response."""
        ads = []
        for item in response.get("ads", []):
            ad_data = item.get("ad", {})
            ad = UnifiedAd(
                platform=Platform.SNAPCHAT,
                account_id=account_id,
                campaign_id=campaign_id,
                adset_id=adset_id,
                ad_id=ad_data.get("id", ""),
                ad_name=ad_data.get("name", ""),
                status=self.STATUS_FROM_SNAPCHAT.get(
                    ad_data.get("status", "ACTIVE"), EntityStatus.ACTIVE
                ),
                creative_id=ad_data.get("creative_id"),
                review_status=ad_data.get("review_status"),
                last_synced=datetime.utcnow(),
                raw_data=ad_data,
            )
            ads.append(ad)
        return ads

    async def get_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        date_start: datetime,
        date_end: datetime,
        breakdown: Optional[str] = None,
    ) -> dict[str, PerformanceMetrics]:
        """
        Fetch performance metrics from Snapchat's stats API.

        Snapchat provides stats at various granularities. We request
        aggregate metrics over the specified date range.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()

        try:
            # Map entity type to Snapchat's stats endpoint
            endpoint_map = {
                "campaign": f"/adaccounts/{account_id}/stats",
                "adset": f"/adaccounts/{account_id}/stats",
                "ad": f"/adaccounts/{account_id}/stats",
            }

            granularity_map = {"campaign": "CAMPAIGN", "adset": "ADSQUAD", "ad": "AD"}

            params = {
                "granularity": "TOTAL",
                "breakdown": granularity_map.get(entity_type, "CAMPAIGN"),
                "start_time": date_start.strftime("%Y-%m-%dT00:00:00.000-00:00"),
                "end_time": date_end.strftime("%Y-%m-%dT23:59:59.999-00:00"),
                "fields": "impressions,swipes,spend,video_views,quartile_1,quartile_2,quartile_3,view_completion,conversion_purchases,conversion_purchases_value",
            }

            if entity_ids:
                if entity_type == "campaign":
                    params["campaign_id"] = entity_ids
                elif entity_type == "adset":
                    params["adsquad_id"] = entity_ids
                else:
                    params["ad_id"] = entity_ids

            response = self._make_request(
                "GET",
                endpoint_map.get(entity_type, f"/adaccounts/{account_id}/stats"),
                params=params,
            )

            metrics_map = {}

            # Parse stats from response
            for item in response.get("timeseries_stats", []):
                stats = item.get("timeseries_stat", {})

                # Get entity ID based on type
                if entity_type == "campaign" or entity_type == "adset":
                    entity_id = stats.get("id", "")
                else:
                    entity_id = stats.get("id", "")

                # Parse stats values (they're in nested timeseries)
                timeseries = stats.get("timeseries", [])
                if not timeseries:
                    continue

                # Aggregate all time periods
                total_stats = {}
                for ts in timeseries:
                    ts_stats = ts.get("stats", {})
                    for key, value in ts_stats.items():
                        if key not in total_stats:
                            total_stats[key] = 0
                        if isinstance(value, (int, float)):
                            total_stats[key] += value

                metrics = PerformanceMetrics(
                    impressions=int(total_stats.get("impressions", 0)),
                    clicks=int(total_stats.get("swipes", 0)),  # Snapchat calls clicks "swipes"
                    spend=self._micros_to_dollars(total_stats.get("spend", 0)) or 0,
                    video_views=int(total_stats.get("video_views", 0))
                    if total_stats.get("video_views")
                    else None,
                    video_p25=int(total_stats.get("quartile_1", 0))
                    if total_stats.get("quartile_1")
                    else None,
                    video_p50=int(total_stats.get("quartile_2", 0))
                    if total_stats.get("quartile_2")
                    else None,
                    video_p75=int(total_stats.get("quartile_3", 0))
                    if total_stats.get("quartile_3")
                    else None,
                    video_p100=int(total_stats.get("view_completion", 0))
                    if total_stats.get("view_completion")
                    else None,
                    conversions=int(total_stats.get("conversion_purchases", 0))
                    if total_stats.get("conversion_purchases")
                    else None,
                    conversion_value=self._micros_to_dollars(
                        total_stats.get("conversion_purchases_value", 0)
                    ),
                    date_start=date_start,
                    date_end=date_end,
                )

                # Compute derived metrics
                metrics.compute_derived_metrics()
                metrics_map[entity_id] = metrics

            return metrics_map

        except Exception as e:
            raise PlatformError(f"Failed to fetch metrics: {e}")

    async def get_emq_scores(self, account_id: str) -> list[EMQScore]:
        """
        Fetch event matching data from Snapchat.

        Snapchat's Conversions API provides match rate information, though
        it's less detailed than Meta's EMQ. We query pixel/CAPI configuration
        to estimate data quality.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()

        try:
            # Snapchat doesn't have a direct EMQ score endpoint
            # We return a default based on pixel configuration
            await self.rate_limiter.acquire()

            # Try to get pixel info
            response = self._make_request("GET", f"/adaccounts/{account_id}/pixels")

            emq_scores = []
            for item in response.get("pixels", []):
                pixel = item.get("pixel", {})

                # Estimate EMQ based on pixel status
                score = 5.0  # Default moderate score
                if pixel.get("effective_status") == "ACTIVE":
                    score = 6.0

                emq = EMQScore(
                    platform=Platform.SNAPCHAT,
                    event_name=f"pixel_{pixel.get('id', 'unknown')}",
                    score=score,
                    last_updated=datetime.utcnow(),
                )
                emq_scores.append(emq)

            return emq_scores

        except Exception as e:
            logger.warning(f"Failed to fetch Snapchat EMQ data: {e}")
            return []

    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================

    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        """Execute an automation action on Snapchat."""
        self._ensure_initialized()
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()

        try:
            action.status = "executing"

            if action.action_type == "update_budget":
                result = await self._update_budget(action)
            elif action.action_type == "update_status":
                result = await self._update_status(action)
            elif action.action_type == "create_campaign":
                result = await self._create_campaign(action)
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")

            action.status = "completed"
            action.executed_at = datetime.utcnow()
            action.result = result

            logger.info(f"Successfully executed {action.action_type} on Snapchat")
            return action

        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            logger.error(f"Action failed: {e}")
            return action

    async def _update_budget(self, action: AutomationAction) -> dict[str, Any]:
        """Update campaign or ad squad budget."""
        params = action.parameters

        endpoint_map = {
            "campaign": f"/campaigns/{action.entity_id}",
            "adset": f"/adsquads/{action.entity_id}",
        }

        endpoint = endpoint_map.get(action.entity_type, f"/campaigns/{action.entity_id}")

        data = {}
        if "daily_budget" in params:
            data["daily_budget_micro"] = int(params["daily_budget"] * 1_000_000)
        if "lifetime_budget" in params:
            if action.entity_type == "campaign":
                data["lifetime_spend_cap_micro"] = int(params["lifetime_budget"] * 1_000_000)
            else:
                data["lifetime_budget_micro"] = int(params["lifetime_budget"] * 1_000_000)

        # Snapchat uses PUT for updates
        wrapper_key = "campaigns" if action.entity_type == "campaign" else "adsquads"
        body = {wrapper_key: [data]}

        response = self._make_request("PUT", endpoint, data=body)

        return {"updated": True}

    async def _update_status(self, action: AutomationAction) -> dict[str, Any]:
        """Update entity status."""
        params = action.parameters
        new_status = EntityStatus(params["status"])
        snap_status = self.STATUS_TO_SNAPCHAT.get(new_status, "ACTIVE")

        endpoint_map = {
            "campaign": f"/campaigns/{action.entity_id}",
            "adset": f"/adsquads/{action.entity_id}",
            "ad": f"/ads/{action.entity_id}",
        }

        endpoint = endpoint_map.get(action.entity_type, f"/campaigns/{action.entity_id}")

        wrapper_map = {"campaign": "campaigns", "adset": "adsquads", "ad": "ads"}
        wrapper_key = wrapper_map.get(action.entity_type, "campaigns")

        body = {wrapper_key: [{"id": action.entity_id, "status": snap_status}]}

        response = self._make_request("PUT", endpoint, data=body)

        return {"new_status": snap_status}

    async def _create_campaign(self, action: AutomationAction) -> dict[str, Any]:
        """Create a new campaign."""
        params = action.parameters

        data = {
            "ad_account_id": action.account_id,
            "name": params["name"],
            "objective": params.get("objective", "WEB_CONVERSION"),
            "status": "PAUSED",  # Create paused for safety
        }

        if "daily_budget" in params:
            data["daily_budget_micro"] = int(params["daily_budget"] * 1_000_000)

        if "lifetime_budget" in params:
            data["lifetime_spend_cap_micro"] = int(params["lifetime_budget"] * 1_000_000)

        body = {"campaigns": [data]}

        response = self._make_request(
            "POST", f"/adaccounts/{action.account_id}/campaigns", data=body
        )

        campaigns = response.get("campaigns", [])
        campaign_id = campaigns[0].get("campaign", {}).get("id") if campaigns else None

        return {"campaign_id": campaign_id}

    # ========================================================================
    # CREATIVE OPERATIONS
    # ========================================================================

    async def upload_image(self, account_id: str, image_data: bytes, filename: str) -> str:
        """
        Upload an image to Snapchat's media library.

        Snapchat requires media to be uploaded before it can be used in creatives.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()

        import base64

        data = {
            "media": [
                {
                    "name": filename,
                    "type": "IMAGE",
                    "ad_account_id": account_id,
                    "media_data": base64.b64encode(image_data).decode("utf-8"),
                }
            ]
        }

        response = self._make_request("POST", f"/adaccounts/{account_id}/media", data=data)

        media_list = response.get("media", [])
        if media_list:
            return media_list[0].get("media", {}).get("id", "")
        return ""

    async def upload_video(self, account_id: str, video_data: bytes, filename: str) -> str:
        """
        Upload a video to Snapchat's media library.

        Video is the primary creative format on Snapchat. Videos should be
        vertical (9:16) for best performance.
        """
        self._ensure_initialized()
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()

        import base64

        data = {
            "media": [
                {
                    "name": filename,
                    "type": "VIDEO",
                    "ad_account_id": account_id,
                    "media_data": base64.b64encode(video_data).decode("utf-8"),
                }
            ]
        }

        response = self._make_request("POST", f"/adaccounts/{account_id}/media", data=data)

        media_list = response.get("media", [])
        if media_list:
            return media_list[0].get("media", {}).get("id", "")
        return ""

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _ensure_initialized(self) -> None:
        """Verify adapter is ready."""
        if not self._initialized or not self.session:
            raise AdapterError("Adapter not initialized. Call initialize() first.")

    def _make_request(
        self, method: str, endpoint: str, params: Optional[dict] = None, data: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Make an HTTP request to Snapchat's API.

        Handles authentication headers and error responses.
        """
        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            else:
                response = self.session.request(method, url, headers=headers, json=data)

            # Check for rate limiting
            if response.status_code == 429:
                reset_time = response.headers.get("X-RateLimit-Reset", "60")
                raise RateLimitError(f"Rate limited, reset in {reset_time}s")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise PlatformError(f"Snapchat API request failed: {e}")

    def _micros_to_dollars(self, micros: Optional[int]) -> Optional[float]:
        """Convert Snapchat's micro-currency to dollars."""
        if micros is None:
            return None
        return micros / 1_000_000

    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse Snapchat's datetime format."""
        if not dt_string:
            return None
        try:
            # Snapchat uses ISO format
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _map_status_to_platform(self, status: EntityStatus) -> str:
        """Convert unified status to Snapchat's status string."""
        return self.STATUS_TO_SNAPCHAT.get(status, "ACTIVE")

    def _map_status_from_platform(self, platform_status: str) -> EntityStatus:
        """Convert Snapchat's status string to unified status."""
        return self.STATUS_FROM_SNAPCHAT.get(platform_status, EntityStatus.ACTIVE)
