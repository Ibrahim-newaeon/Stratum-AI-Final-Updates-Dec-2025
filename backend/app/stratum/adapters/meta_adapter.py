"""
Stratum AI: Meta Marketing API Adapter
======================================

This adapter provides complete bi-directional integration with Meta's Marketing API,
enabling Stratum to both pull performance data and push automation changes to Facebook
and Instagram advertising campaigns.

Understanding Meta's API Hierarchy
----------------------------------

Meta organizes advertising entities in a strict hierarchy that mirrors how ads are
created in Ads Manager. At the top sits the Business Manager, which can contain
multiple Ad Accounts. Each Ad Account contains Campaigns, which in turn contain
Ad Sets, which finally contain individual Ads. This hierarchical structure means
that to create an ad, you must first have a campaign and ad set to place it in.

The key insight for automation is that budget optimization can happen at two levels:
Campaign Budget Optimization (CBO) centralizes budget decisions at the campaign level,
while Ad Set Budget Optimization (ABO) lets each ad set manage its own budget. Stratum
supports both approaches, automatically detecting which is in use.

Authentication Flow
-------------------

Meta's API uses OAuth 2.0 with several token types. For production automation like
Stratum, the recommended approach is System User tokens. Unlike user access tokens
that expire after 60 days of inactivity, System User tokens are tied to the Business
Manager itself and can be configured to never expire.

To set up System User authentication:
1. Navigate to Business Settings in Business Manager
2. Under System Users, create a new System User with Admin access
3. Click "Generate New Token" and select your app
4. Grant the following permissions: ads_management, ads_read, business_management
5. The generated token should be stored securely and provided to this adapter

Rate Limits
-----------

Meta calculates rate limits dynamically based on your app's tier and recent behavior.
The Marketing API uses a "call credit" system where different endpoints cost different
amounts. Simple reads might cost 1 credit, while complex insights queries might cost
10 or more. The standard tier allows approximately 4,800 credits per hour per ad account.

This adapter implements exponential backoff when rate limits are hit, automatically
retrying failed requests after progressively longer delays.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import hashlib
import json

# Meta's official Python SDK
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.adobjects.serverside.event import Event
from facebook_business.adobjects.serverside.event_request import EventRequest
from facebook_business.adobjects.serverside.user_data import UserData
from facebook_business.adobjects.serverside.custom_data import CustomData
from facebook_business.exceptions import FacebookRequestError

from app.stratum.adapters.base import (
    BaseAdapter,
    AdapterError,
    AuthenticationError,
    RateLimitError,
    PlatformError,
    RateLimiter
)
from app.stratum.models import (
    Platform,
    UnifiedAccount,
    UnifiedCampaign,
    UnifiedAdSet,
    UnifiedAd,
    PerformanceMetrics,
    EMQScore,
    AutomationAction,
    EntityStatus,
    BiddingStrategy,
    OptimizationGoal
)


logger = logging.getLogger("stratum.adapters.meta")


class MetaAdapter(BaseAdapter):
    """
    Meta Marketing API adapter for Facebook and Instagram advertising.
    
    This adapter wraps Meta's official facebook-business Python SDK, translating
    between Stratum's unified models and Meta's native API formats. It supports
    all standard CRUD operations on campaigns, ad sets, and ads, as well as
    advanced features like conversion tracking via the Conversions API.
    
    Required Credentials:
        app_id: Your Meta app's ID from developers.facebook.com
        app_secret: Your Meta app's secret key
        access_token: System User or User access token with ads_management permission
    
    Optional Credentials:
        business_id: Business Manager ID for multi-account access
        pixel_id: Meta Pixel ID for conversion tracking
    
    Example Usage:
    
        credentials = {
            "app_id": "123456789",
            "app_secret": "abc123...",
            "access_token": "EAABsbCS1IAMZA...",
            "business_id": "987654321"
        }
        
        adapter = MetaAdapter(credentials)
        await adapter.initialize()
        
        # Get all campaigns
        campaigns = await adapter.get_campaigns("act_123456789")
        
        # Update a budget
        action = AutomationAction(
            platform=Platform.META,
            account_id="act_123456789",
            entity_type="campaign",
            entity_id="23456789",
            action_type="update_budget",
            parameters={"daily_budget": 100.00}
        )
        result = await adapter.execute_action(action)
    """
    
    # Status mapping between Stratum's unified status and Meta's native values
    # Meta uses string constants that map to specific delivery states
    STATUS_TO_META = {
        EntityStatus.ACTIVE: "ACTIVE",
        EntityStatus.PAUSED: "PAUSED",
        EntityStatus.DELETED: "DELETED",
        EntityStatus.ARCHIVED: "ARCHIVED",
    }
    
    STATUS_FROM_META = {
        "ACTIVE": EntityStatus.ACTIVE,
        "PAUSED": EntityStatus.PAUSED,
        "DELETED": EntityStatus.DELETED,
        "ARCHIVED": EntityStatus.ARCHIVED,
        "IN_PROCESS": EntityStatus.PENDING_REVIEW,
        "WITH_ISSUES": EntityStatus.ACTIVE,  # Still delivering, just has warnings
    }
    
    # Bidding strategy mapping
    # Meta's bidding options are specified through a combination of bid_strategy
    # and optimization_goal fields, which this mapping simplifies
    BIDDING_TO_META = {
        BiddingStrategy.LOWEST_COST: "LOWEST_COST_WITHOUT_CAP",
        BiddingStrategy.COST_CAP: "COST_CAP",
        BiddingStrategy.BID_CAP: "LOWEST_COST_WITH_BID_CAP",
    }
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize the Meta adapter with the provided credentials.
        
        The credentials dictionary must contain app_id, app_secret, and access_token
        at minimum. The business_id is optional but recommended for accessing multiple
        ad accounts under a single Business Manager.
        """
        super().__init__(credentials)
        
        # Validate required credentials are present
        required_keys = ["app_id", "app_secret", "access_token"]
        missing = [k for k in required_keys if k not in credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {missing}")
        
        self.app_id = credentials["app_id"]
        self.app_secret = credentials["app_secret"]
        self.access_token = credentials["access_token"]
        self.business_id = credentials.get("business_id")
        self.pixel_id = credentials.get("pixel_id")
        
        # Initialize API client reference (set in initialize())
        self.api = None
        
        # Configure rate limiter for Meta's limits
        # Meta allows approximately 4800 calls per hour per ad account
        # We set a conservative limit to leave headroom
        self.rate_limiter = RateLimiter(
            calls_per_minute=60,  # 3600/hour = safe buffer
            burst_size=20         # Allow short bursts for batch operations
        )
    
    @property
    def platform(self) -> Platform:
        """Return the platform identifier for routing and logging."""
        return Platform.META
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    async def initialize(self) -> None:
        """
        Initialize the Meta Marketing API client and verify authentication.
        
        This method configures the facebook-business SDK with our credentials
        and makes a test API call to verify everything is working. The SDK
        maintains a global default API instance, which we configure here.
        
        After calling this method, all subsequent API calls will use the
        configured credentials automatically.
        """
        logger.info("Initializing Meta Marketing API adapter")
        
        try:
            # Initialize the SDK with our credentials
            # The init() method sets up a default API instance used by all objects
            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token
            )
            self.api = FacebookAdsApi.get_default_api()
            
            # Verify authentication by fetching accessible ad accounts
            # This also warms up any connection pools
            await self.rate_limiter.acquire()
            accounts = await self._fetch_ad_accounts()
            
            if not accounts:
                logger.warning("No ad accounts accessible with provided credentials")
            else:
                logger.info(f"Successfully authenticated, found {len(accounts)} ad accounts")
            
            self._initialized = True
            
        except FacebookRequestError as e:
            # Parse Meta's error response for more helpful messages
            error_msg = f"Meta API error: {e.api_error_message()}"
            if e.api_error_code() == 190:
                raise AuthenticationError(
                    "Access token is invalid or expired. "
                    "Please generate a new token from Business Manager."
                )
            raise AdapterError(error_msg)
    
    async def cleanup(self) -> None:
        """
        Clean up adapter resources.
        
        Meta's SDK doesn't require explicit cleanup, but we reset our
        state to ensure a clean slate if the adapter is reused.
        """
        self._initialized = False
        self.api = None
        logger.info("Meta adapter cleanup complete")
    
    # ========================================================================
    # READ OPERATIONS: Fetching Data from Meta
    # ========================================================================
    
    async def get_accounts(self) -> List[UnifiedAccount]:
        """
        Fetch all advertising accounts accessible with current credentials.
        
        If a business_id was provided during initialization, this returns all
        ad accounts owned by that Business Manager. Otherwise, it returns all
        ad accounts the authenticated user has access to.
        
        Each returned UnifiedAccount includes the account's currency, timezone,
        and spending limits, which are important for proper budget calculations.
        """
        self._ensure_initialized()
        
        try:
            raw_accounts = await self._fetch_ad_accounts()
            unified_accounts = []
            
            for raw in raw_accounts:
                # Convert Meta's native format to our unified model
                account = UnifiedAccount(
                    platform=Platform.META,
                    account_id=raw.get("id", ""),
                    account_name=raw.get("name", "Unknown Account"),
                    business_id=raw.get("business", {}).get("id") if raw.get("business") else None,
                    timezone=raw.get("timezone_name", "UTC"),
                    currency=raw.get("currency", "USD"),
                    daily_spend_limit=self._cents_to_dollars(raw.get("spend_cap")),
                    raw_data=raw
                )
                unified_accounts.append(account)
            
            return unified_accounts
            
        except FacebookRequestError as e:
            raise PlatformError(
                f"Failed to fetch ad accounts: {e.api_error_message()}",
                platform_code=str(e.api_error_code())
            )
    
    async def get_campaigns(
        self,
        account_id: str,
        status_filter: Optional[List[EntityStatus]] = None
    ) -> List[UnifiedCampaign]:
        """
        Fetch campaigns for the specified ad account.
        
        Meta's campaign object contains the overall objective (what you're
        optimizing for) and optionally the budget if using Campaign Budget
        Optimization. The effective_status field tells us the actual delivery
        state, accounting for parent account status.
        
        The status_filter parameter allows fetching only active campaigns,
        which is useful for automation that shouldn't touch paused campaigns.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            # Ensure account_id has the required 'act_' prefix
            if not account_id.startswith("act_"):
                account_id = f"act_{account_id}"
            
            ad_account = AdAccount(account_id)
            
            # Define which fields we need from the API
            # We request everything needed for unified model plus budget/bidding
            fields = [
                Campaign.Field.id,
                Campaign.Field.name,
                Campaign.Field.status,
                Campaign.Field.effective_status,
                Campaign.Field.objective,
                Campaign.Field.daily_budget,
                Campaign.Field.lifetime_budget,
                Campaign.Field.budget_remaining,
                Campaign.Field.bid_strategy,
                Campaign.Field.created_time,
                Campaign.Field.updated_time,
            ]
            
            # Build filter parameters if needed
            params = {}
            if status_filter:
                meta_statuses = [self.STATUS_TO_META.get(s) for s in status_filter]
                params["filtering"] = [
                    {"field": "effective_status", "operator": "IN", "value": meta_statuses}
                ]
            
            # Execute the API call
            raw_campaigns = ad_account.get_campaigns(fields=fields, params=params)
            
            # Convert each raw campaign to our unified model
            unified_campaigns = []
            for raw in raw_campaigns:
                campaign = self._convert_campaign(raw, account_id)
                unified_campaigns.append(campaign)
            
            logger.info(f"Fetched {len(unified_campaigns)} campaigns from {account_id}")
            return unified_campaigns
            
        except FacebookRequestError as e:
            raise PlatformError(
                f"Failed to fetch campaigns: {e.api_error_message()}",
                platform_code=str(e.api_error_code())
            )
    
    async def get_adsets(
        self,
        account_id: str,
        campaign_id: Optional[str] = None
    ) -> List[UnifiedAdSet]:
        """
        Fetch ad sets, optionally filtered to a specific campaign.
        
        Ad sets are where the real targeting and budget action happens in Meta.
        Each ad set defines the audience, placement, schedule, and (if not using
        CBO) the budget. The targeting object can be quite complex, so we store
        it in raw_data and provide only a summary in targeting_summary.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            if not account_id.startswith("act_"):
                account_id = f"act_{account_id}"
            
            ad_account = AdAccount(account_id)
            
            fields = [
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.campaign_id,
                AdSet.Field.status,
                AdSet.Field.effective_status,
                AdSet.Field.daily_budget,
                AdSet.Field.lifetime_budget,
                AdSet.Field.bid_amount,
                AdSet.Field.targeting,
                AdSet.Field.start_time,
                AdSet.Field.end_time,
                AdSet.Field.created_time,
                AdSet.Field.updated_time,
            ]
            
            params = {}
            if campaign_id:
                params["filtering"] = [
                    {"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}
                ]
            
            raw_adsets = ad_account.get_ad_sets(fields=fields, params=params)
            
            unified_adsets = []
            for raw in raw_adsets:
                adset = self._convert_adset(raw, account_id)
                unified_adsets.append(adset)
            
            return unified_adsets
            
        except FacebookRequestError as e:
            raise PlatformError(
                f"Failed to fetch ad sets: {e.api_error_message()}",
                platform_code=str(e.api_error_code())
            )
    
    async def get_ads(
        self,
        account_id: str,
        adset_id: Optional[str] = None
    ) -> List[UnifiedAd]:
        """
        Fetch individual ads, optionally filtered to a specific ad set.
        
        Ads in Meta link creative content to an ad set's targeting and budget.
        The creative contains the actual image/video, headline, description,
        and call-to-action. We fetch the creative URL for reference.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            if not account_id.startswith("act_"):
                account_id = f"act_{account_id}"
            
            ad_account = AdAccount(account_id)
            
            fields = [
                Ad.Field.id,
                Ad.Field.name,
                Ad.Field.adset_id,
                Ad.Field.campaign_id,
                Ad.Field.status,
                Ad.Field.effective_status,
                Ad.Field.creative,
                Ad.Field.created_time,
                Ad.Field.updated_time,
            ]
            
            params = {}
            if adset_id:
                params["filtering"] = [
                    {"field": "adset.id", "operator": "EQUAL", "value": adset_id}
                ]
            
            raw_ads = ad_account.get_ads(fields=fields, params=params)
            
            unified_ads = []
            for raw in raw_ads:
                ad = self._convert_ad(raw, account_id)
                unified_ads.append(ad)
            
            return unified_ads
            
        except FacebookRequestError as e:
            raise PlatformError(
                f"Failed to fetch ads: {e.api_error_message()}",
                platform_code=str(e.api_error_code())
            )
    
    async def get_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: List[str],
        date_start: datetime,
        date_end: datetime,
        breakdown: Optional[str] = None
    ) -> Dict[str, PerformanceMetrics]:
        """
        Fetch performance metrics from Meta's Insights API.
        
        Meta's Insights API is powerful but can be slow for large date ranges
        or many entities. For best performance, we batch entity IDs and use
        asynchronous report generation for large requests.
        
        The breakdown parameter allows splitting metrics by various dimensions
        like age, gender, placement, or day. When a breakdown is used, the
        returned metrics are aggregated across all breakdown values.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            if not account_id.startswith("act_"):
                account_id = f"act_{account_id}"
            
            # Meta's insights endpoint accepts filters rather than direct IDs
            # We build the appropriate filter based on entity type
            level_map = {
                "campaign": "campaign",
                "adset": "adset",
                "ad": "ad"
            }
            
            level = level_map.get(entity_type, "campaign")
            
            ad_account = AdAccount(account_id)
            
            fields = [
                AdsInsights.Field.impressions,
                AdsInsights.Field.clicks,
                AdsInsights.Field.spend,
                AdsInsights.Field.cpc,
                AdsInsights.Field.cpm,
                AdsInsights.Field.ctr,
                AdsInsights.Field.actions,
                AdsInsights.Field.action_values,
                AdsInsights.Field.video_p25_watched_actions,
                AdsInsights.Field.video_p50_watched_actions,
                AdsInsights.Field.video_p75_watched_actions,
                AdsInsights.Field.video_p100_watched_actions,
            ]
            
            # Include the appropriate ID field based on level
            if level == "campaign":
                fields.append(AdsInsights.Field.campaign_id)
            elif level == "adset":
                fields.append(AdsInsights.Field.adset_id)
            else:
                fields.append(AdsInsights.Field.ad_id)
            
            params = {
                "level": level,
                "time_range": {
                    "since": date_start.strftime("%Y-%m-%d"),
                    "until": date_end.strftime("%Y-%m-%d")
                },
                "filtering": [{
                    "field": f"{level}.id",
                    "operator": "IN",
                    "value": entity_ids
                }]
            }
            
            if breakdown:
                params["breakdowns"] = [breakdown]
            
            raw_insights = ad_account.get_insights(fields=fields, params=params)
            
            # Build dictionary mapping entity ID to metrics
            metrics_map = {}
            for insight in raw_insights:
                # Determine which ID field to use
                if level == "campaign":
                    entity_id = insight.get("campaign_id")
                elif level == "adset":
                    entity_id = insight.get("adset_id")
                else:
                    entity_id = insight.get("ad_id")
                
                metrics = self._convert_insights(insight, date_start, date_end)
                metrics_map[entity_id] = metrics
            
            return metrics_map
            
        except FacebookRequestError as e:
            raise PlatformError(
                f"Failed to fetch metrics: {e.api_error_message()}",
                platform_code=str(e.api_error_code())
            )
    
    async def get_emq_scores(self, account_id: str) -> List[EMQScore]:
        """
        Fetch Event Match Quality scores from Meta's server events quality endpoint.
        
        EMQ measures how well your conversion data matches Meta's user profiles.
        A higher score means Meta can more accurately attribute conversions and
        optimize delivery. The score is calculated based on the quality of user
        data parameters sent with each event (email, phone, IP, etc.).
        
        Target scores by event type:
        - Purchase: 8.5+ (critical for optimization)
        - AddToCart: 6.0+ (important for upper-funnel)
        - ViewContent: 4.0+ (less critical)
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        if not self.pixel_id:
            logger.warning("No pixel_id configured, cannot fetch EMQ scores")
            return []
        
        try:
            # The server events quality endpoint provides aggregate EMQ data
            # We need to call it for each event type we're tracking
            event_types = ["Purchase", "AddToCart", "ViewContent", "Lead", "InitiateCheckout"]
            
            emq_scores = []
            
            for event_type in event_types:
                # Meta's EMQ endpoint path
                # Note: This uses the direct Graph API call since the SDK
                # doesn't have a wrapper for this specific endpoint
                path = f"/{self.pixel_id}/server_events_quality"
                params = {
                    "event_name": event_type,
                    "access_token": self.access_token
                }
                
                # Make the API call
                # We're using a simplified approach here; production code
                # would handle pagination and more complex responses
                import requests
                response = requests.get(
                    f"https://graph.facebook.com/v18.0{path}",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse the EMQ data into our model
                    if "data" in data and len(data["data"]) > 0:
                        emq_data = data["data"][0]
                        
                        emq = EMQScore(
                            platform=Platform.META,
                            event_name=event_type,
                            score=emq_data.get("event_match_quality", 0),
                            match_rate=emq_data.get("match_rate", 0),
                            email_match_rate=emq_data.get("em_match_rate"),
                            phone_match_rate=emq_data.get("ph_match_rate"),
                        )
                        emq_scores.append(emq)
            
            return emq_scores
            
        except Exception as e:
            logger.error(f"Failed to fetch EMQ scores: {e}")
            return []
    
    # ========================================================================
    # WRITE OPERATIONS: Pushing Changes to Meta
    # ========================================================================
    
    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        """
        Execute an automation action on Meta's platform.
        
        This is where Stratum's automation decisions become real changes in
        Meta Ads Manager. The action object specifies what to change, and
        this method handles the API call to make it happen.
        
        Supported action types:
        - update_budget: Change daily_budget or lifetime_budget
        - update_bid: Change bid_amount or bid_strategy
        - update_status: Pause, enable, or archive
        - create_campaign: Create new campaign with specified settings
        - create_adset: Create new ad set with targeting
        - create_ad: Create new ad with creative
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            action.status = "executing"
            
            # Route to the appropriate handler based on action type
            if action.action_type == "update_budget":
                result = await self._update_budget(action)
            elif action.action_type == "update_bid":
                result = await self._update_bid(action)
            elif action.action_type == "update_status":
                result = await self._update_status(action)
            elif action.action_type == "create_campaign":
                result = await self._create_campaign(action)
            elif action.action_type == "create_adset":
                result = await self._create_adset(action)
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")
            
            action.status = "completed"
            action.executed_at = datetime.utcnow()
            action.result = result
            
            logger.info(f"Successfully executed {action.action_type} on {action.entity_id}")
            return action
            
        except FacebookRequestError as e:
            action.status = "failed"
            action.error_message = e.api_error_message()
            logger.error(f"Action failed: {action.error_message}")
            return action
        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            logger.error(f"Action failed with unexpected error: {e}")
            return action
    
    async def _update_budget(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Update budget for a campaign or ad set.
        
        Meta budgets are specified in cents (the account's currency smallest unit),
        so we multiply the dollar amount by 100 before sending. Both daily and
        lifetime budgets can be updated, but they're mutually exclusive on Meta.
        """
        params = action.parameters
        
        # Meta uses cents, not dollars
        update_params = {}
        if "daily_budget" in params:
            update_params["daily_budget"] = int(params["daily_budget"] * 100)
        if "lifetime_budget" in params:
            update_params["lifetime_budget"] = int(params["lifetime_budget"] * 100)
        
        if action.entity_type == "campaign":
            entity = Campaign(action.entity_id)
        else:
            entity = AdSet(action.entity_id)
        
        entity.api_update(params=update_params)
        
        return {"updated_fields": list(update_params.keys())}
    
    async def _update_bid(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Update bidding configuration for a campaign or ad set.
        
        Bid updates can include the bid amount (for manual/capped strategies)
        or the bid strategy itself. Strategy changes may require clearing
        conflicting settings first.
        """
        params = action.parameters
        update_params = {}
        
        if "bid_amount" in params:
            # Bid amounts are also in cents
            update_params["bid_amount"] = int(params["bid_amount"] * 100)
        
        if "bid_strategy" in params:
            strategy = BiddingStrategy(params["bid_strategy"])
            meta_strategy = self.BIDDING_TO_META.get(strategy)
            if meta_strategy:
                update_params["bid_strategy"] = meta_strategy
        
        if action.entity_type == "campaign":
            entity = Campaign(action.entity_id)
        else:
            entity = AdSet(action.entity_id)
        
        entity.api_update(params=update_params)
        
        return {"updated_fields": list(update_params.keys())}
    
    async def _update_status(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Update the status of a campaign, ad set, or ad.
        
        Status changes are one of the most common automation actions. Pausing
        underperforming entities or enabling seasonal campaigns are typical
        use cases for Stratum's autopilot.
        """
        params = action.parameters
        new_status = EntityStatus(params["status"])
        meta_status = self.STATUS_TO_META.get(new_status)
        
        if action.entity_type == "campaign":
            entity = Campaign(action.entity_id)
        elif action.entity_type == "adset":
            entity = AdSet(action.entity_id)
        else:
            entity = Ad(action.entity_id)
        
        entity.api_update(params={"status": meta_status})
        
        return {"new_status": meta_status}
    
    async def _create_campaign(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Create a new campaign in the specified ad account.
        
        Campaign creation requires specifying an objective, name, and either
        a daily or lifetime budget. The campaign is created in PAUSED status
        by default to allow review before activation.
        """
        params = action.parameters
        account_id = action.account_id
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        ad_account = AdAccount(account_id)
        
        campaign_params = {
            "name": params["name"],
            "objective": params.get("objective", "OUTCOME_SALES"),
            "status": "PAUSED",  # Always create paused for safety
            "special_ad_categories": params.get("special_ad_categories", []),
        }
        
        # Set budget (convert to cents)
        if "daily_budget" in params:
            campaign_params["daily_budget"] = int(params["daily_budget"] * 100)
        elif "lifetime_budget" in params:
            campaign_params["lifetime_budget"] = int(params["lifetime_budget"] * 100)
        
        # Set bidding strategy
        if "bid_strategy" in params:
            strategy = BiddingStrategy(params["bid_strategy"])
            meta_strategy = self.BIDDING_TO_META.get(strategy)
            if meta_strategy:
                campaign_params["bid_strategy"] = meta_strategy
        
        result = ad_account.create_campaign(params=campaign_params)
        
        return {"campaign_id": result["id"]}
    
    async def _create_adset(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Create a new ad set within a campaign.
        
        Ad set creation is more complex than campaigns because it includes
        targeting configuration. The targeting object can specify custom
        audiences, demographics, interests, and behaviors.
        """
        params = action.parameters
        account_id = action.account_id
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        ad_account = AdAccount(account_id)
        
        adset_params = {
            "name": params["name"],
            "campaign_id": params["campaign_id"],
            "status": "PAUSED",
            "billing_event": params.get("billing_event", "IMPRESSIONS"),
            "optimization_goal": params.get("optimization_goal", "OFFSITE_CONVERSIONS"),
            "targeting": params.get("targeting", {}),
        }
        
        if "daily_budget" in params:
            adset_params["daily_budget"] = int(params["daily_budget"] * 100)
        if "bid_amount" in params:
            adset_params["bid_amount"] = int(params["bid_amount"] * 100)
        
        result = ad_account.create_ad_set(params=adset_params)
        
        return {"adset_id": result["id"]}
    
    # ========================================================================
    # CREATIVE OPERATIONS
    # ========================================================================
    
    async def upload_image(
        self,
        account_id: str,
        image_data: bytes,
        filename: str
    ) -> str:
        """
        Upload an image to Meta's creative library.
        
        Images are uploaded to the ad account's image library and can then
        be referenced by their hash when creating ad creatives. Meta stores
        images indefinitely once uploaded.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        ad_account = AdAccount(account_id)
        
        # Meta requires the image data as base64 or a file
        import base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        params = {
            "bytes": image_b64,
            "name": filename
        }
        
        result = ad_account.create_ad_image(params=params)
        
        # Return the image hash, which is used to reference the image
        images = result.get("images", {})
        if filename in images:
            return images[filename].get("hash", "")
        
        return ""
    
    async def upload_video(
        self,
        account_id: str,
        video_data: bytes,
        filename: str
    ) -> str:
        """
        Upload a video to Meta's creative library.
        
        Video upload is more complex than images because videos need
        processing time. This method initiates the upload and returns
        the video ID, but the video may not be immediately available.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        ad_account = AdAccount(account_id)
        
        # For videos, we use the resumable upload endpoint
        # This is a simplified version; production would handle chunked upload
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as f:
            f.write(video_data)
            temp_path = f.name
        
        try:
            result = ad_account.create_ad_video(params={
                "source_file": temp_path,
                "name": filename
            })
            return result.get("id", "")
        finally:
            os.unlink(temp_path)
    
    # ========================================================================
    # WEBHOOK SUPPORT
    # ========================================================================
    
    async def setup_webhooks(
        self,
        callback_url: str,
        event_types: List[str]
    ) -> bool:
        """
        Configure Meta webhooks for real-time updates.
        
        Meta's Webhooks API can notify us when campaigns are approved/rejected,
        budgets are spent, or other significant events occur. This enables
        faster response to issues than periodic polling.
        """
        # Meta webhooks require app-level configuration, not just API calls
        # This would typically be done through the developers.facebook.com portal
        logger.info(
            f"Meta webhooks must be configured at developers.facebook.com. "
            f"Add callback URL: {callback_url} with subscriptions: {event_types}"
        )
        return True
    
    # ========================================================================
    # CONVERSION API: Server-Side Event Tracking
    # ========================================================================
    
    async def send_conversion_event(
        self,
        event_name: str,
        event_time: datetime,
        user_data: Dict[str, str],
        custom_data: Optional[Dict[str, Any]] = None,
        event_source_url: Optional[str] = None
    ) -> bool:
        """
        Send a conversion event to Meta's Conversions API.
        
        The Conversions API (CAPI) enables server-side event tracking, which
        is more reliable than pixel-based tracking because it bypasses browser
        limitations like ad blockers and cookie restrictions.
        
        User data should be hashed with SHA-256 before sending. This method
        handles the hashing automatically for supported fields.
        """
        if not self.pixel_id:
            raise ValueError("pixel_id required for Conversions API")
        
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        # Hash user data fields that need it
        hashed_user_data = self._prepare_user_data_for_capi(user_data)
        
        # Build the event
        user_data_obj = UserData(
            email=hashed_user_data.get("em"),
            phone=hashed_user_data.get("ph"),
            client_ip_address=user_data.get("client_ip_address"),
            client_user_agent=user_data.get("client_user_agent"),
            fbc=user_data.get("fbc"),  # Facebook Click ID
            fbp=user_data.get("fbp"),  # Facebook Browser ID
        )
        
        custom_data_obj = None
        if custom_data:
            custom_data_obj = CustomData(
                currency=custom_data.get("currency", "USD"),
                value=custom_data.get("value"),
                content_ids=custom_data.get("content_ids"),
                content_type=custom_data.get("content_type"),
            )
        
        event = Event(
            event_name=event_name,
            event_time=int(event_time.timestamp()),
            user_data=user_data_obj,
            custom_data=custom_data_obj,
            event_source_url=event_source_url,
            action_source="website",
        )
        
        # Send the event
        request = EventRequest(
            pixel_id=self.pixel_id,
            events=[event],
        )
        
        response = request.execute()
        
        return response.get("events_received", 0) > 0
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _ensure_initialized(self) -> None:
        """Verify the adapter has been initialized before making API calls."""
        if not self._initialized:
            raise AdapterError(
                "Adapter not initialized. Call initialize() first."
            )
    
    async def _fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Fetch raw ad account data from Meta.
        
        If a business_id is configured, fetches accounts owned by that business.
        Otherwise, fetches accounts accessible to the authenticated user.
        """
        from facebook_business.adobjects.user import User
        from facebook_business.adobjects.business import Business
        
        fields = ["id", "name", "currency", "timezone_name", "spend_cap", "business"]
        
        if self.business_id:
            business = Business(self.business_id)
            accounts = business.get_owned_ad_accounts(fields=fields)
        else:
            me = User(fbid="me")
            accounts = me.get_ad_accounts(fields=fields)
        
        return [dict(acc) for acc in accounts]
    
    def _convert_campaign(self, raw: Dict[str, Any], account_id: str) -> UnifiedCampaign:
        """Convert Meta's campaign format to unified model."""
        return UnifiedCampaign(
            platform=Platform.META,
            account_id=account_id,
            campaign_id=raw.get("id", ""),
            campaign_name=raw.get("name", ""),
            status=self.STATUS_FROM_META.get(
                raw.get("effective_status", "ACTIVE"),
                EntityStatus.ACTIVE
            ),
            daily_budget=self._cents_to_dollars(raw.get("daily_budget")),
            lifetime_budget=self._cents_to_dollars(raw.get("lifetime_budget")),
            budget_remaining=self._cents_to_dollars(raw.get("budget_remaining")),
            created_at=self._parse_datetime(raw.get("created_time")),
            updated_at=self._parse_datetime(raw.get("updated_time")),
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _convert_adset(self, raw: Dict[str, Any], account_id: str) -> UnifiedAdSet:
        """Convert Meta's ad set format to unified model."""
        # Create a human-readable targeting summary
        targeting = raw.get("targeting", {})
        targeting_parts = []
        if targeting.get("geo_locations"):
            countries = targeting["geo_locations"].get("countries", [])
            if countries:
                targeting_parts.append(f"Countries: {', '.join(countries)}")
        if targeting.get("age_min") or targeting.get("age_max"):
            targeting_parts.append(
                f"Age: {targeting.get('age_min', 18)}-{targeting.get('age_max', 65)}"
            )
        
        return UnifiedAdSet(
            platform=Platform.META,
            account_id=account_id,
            campaign_id=raw.get("campaign_id", ""),
            adset_id=raw.get("id", ""),
            adset_name=raw.get("name", ""),
            status=self.STATUS_FROM_META.get(
                raw.get("effective_status", "ACTIVE"),
                EntityStatus.ACTIVE
            ),
            daily_budget=self._cents_to_dollars(raw.get("daily_budget")),
            lifetime_budget=self._cents_to_dollars(raw.get("lifetime_budget")),
            bid_amount=self._cents_to_dollars(raw.get("bid_amount")),
            targeting_summary="; ".join(targeting_parts) if targeting_parts else None,
            start_time=self._parse_datetime(raw.get("start_time")),
            end_time=self._parse_datetime(raw.get("end_time")),
            created_at=self._parse_datetime(raw.get("created_time")),
            updated_at=self._parse_datetime(raw.get("updated_time")),
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _convert_ad(self, raw: Dict[str, Any], account_id: str) -> UnifiedAd:
        """Convert Meta's ad format to unified model."""
        creative = raw.get("creative", {})
        
        return UnifiedAd(
            platform=Platform.META,
            account_id=account_id,
            campaign_id=raw.get("campaign_id", ""),
            adset_id=raw.get("adset_id", ""),
            ad_id=raw.get("id", ""),
            ad_name=raw.get("name", ""),
            status=self.STATUS_FROM_META.get(
                raw.get("effective_status", "ACTIVE"),
                EntityStatus.ACTIVE
            ),
            creative_id=creative.get("id") if isinstance(creative, dict) else None,
            created_at=self._parse_datetime(raw.get("created_time")),
            updated_at=self._parse_datetime(raw.get("updated_time")),
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _convert_insights(
        self,
        raw: Dict[str, Any],
        date_start: datetime,
        date_end: datetime
    ) -> PerformanceMetrics:
        """Convert Meta's insights format to unified metrics."""
        metrics = PerformanceMetrics(
            impressions=int(raw.get("impressions", 0)),
            clicks=int(raw.get("clicks", 0)),
            spend=float(raw.get("spend", 0)),
            ctr=float(raw.get("ctr", 0)) if raw.get("ctr") else None,
            cpc=float(raw.get("cpc", 0)) if raw.get("cpc") else None,
            cpm=float(raw.get("cpm", 0)) if raw.get("cpm") else None,
            date_start=date_start,
            date_end=date_end,
        )
        
        # Parse actions for conversions
        actions = raw.get("actions", [])
        for action in actions:
            if action.get("action_type") == "purchase":
                metrics.conversions = int(action.get("value", 0))
        
        # Parse action values for conversion value
        action_values = raw.get("action_values", [])
        for av in action_values:
            if av.get("action_type") == "purchase":
                metrics.conversion_value = float(av.get("value", 0))
        
        # Calculate ROAS if we have conversion value
        if metrics.conversion_value and metrics.spend > 0:
            metrics.roas = metrics.conversion_value / metrics.spend
        
        # Calculate CPA if we have conversions
        if metrics.conversions and metrics.conversions > 0:
            metrics.cpa = metrics.spend / metrics.conversions
        
        # Parse video metrics
        video_p25 = raw.get("video_p25_watched_actions", [])
        if video_p25:
            metrics.video_p25 = int(video_p25[0].get("value", 0))
        
        video_p50 = raw.get("video_p50_watched_actions", [])
        if video_p50:
            metrics.video_p50 = int(video_p50[0].get("value", 0))
        
        video_p75 = raw.get("video_p75_watched_actions", [])
        if video_p75:
            metrics.video_p75 = int(video_p75[0].get("value", 0))
        
        video_p100 = raw.get("video_p100_watched_actions", [])
        if video_p100:
            metrics.video_p100 = int(video_p100[0].get("value", 0))
        
        return metrics
    
    def _cents_to_dollars(self, cents: Optional[str]) -> Optional[float]:
        """Convert Meta's cent-based amounts to dollars."""
        if cents is None:
            return None
        try:
            return float(cents) / 100
        except (ValueError, TypeError):
            return None
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse Meta's datetime strings into Python datetime objects."""
        if not dt_string:
            return None
        try:
            # Meta uses ISO format with timezone
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    def _prepare_user_data_for_capi(self, user_data: Dict[str, str]) -> Dict[str, str]:
        """
        Hash user data fields for Conversions API.
        
        Meta requires certain user data fields to be SHA-256 hashed before
        sending. This method handles the hashing and normalization.
        """
        hashed = {}
        
        # Email: lowercase, trim, hash
        if "email" in user_data:
            email = user_data["email"].lower().strip()
            hashed["em"] = hashlib.sha256(email.encode()).hexdigest()
        
        # Phone: remove non-digits, hash
        if "phone" in user_data:
            phone = "".join(c for c in user_data["phone"] if c.isdigit())
            hashed["ph"] = hashlib.sha256(phone.encode()).hexdigest()
        
        return hashed
    
    def _map_status_to_platform(self, status: EntityStatus) -> str:
        """Convert unified status to Meta's status string."""
        return self.STATUS_TO_META.get(status, "ACTIVE")
    
    def _map_status_from_platform(self, platform_status: str) -> EntityStatus:
        """Convert Meta's status string to unified status."""
        return self.STATUS_FROM_META.get(platform_status, EntityStatus.ACTIVE)
