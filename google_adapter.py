"""
Stratum AI: Google Ads API Adapter
==================================

This adapter provides bi-directional integration with Google's Ads API, enabling
Stratum to manage Search, Display, Shopping, Performance Max, and Video campaigns
programmatically. Google's API is particularly powerful for automation because it
exposes nearly every setting available in the Google Ads web interface.

Understanding Google's API Architecture
---------------------------------------

Google Ads API differs from Meta's approach in several important ways. First, Google
uses a strongly-typed Protocol Buffer (protobuf) system rather than JSON. This means
requests and responses are defined by strict schemas, which catches errors at compile
time rather than runtime. The Python client library handles the protobuf translation
automatically, but you'll sometimes see references to "message types" and "field masks"
that reflect this underlying structure.

Second, Google uses a query language called GAQL (Google Ads Query Language) for
fetching data. GAQL looks similar to SQL but operates on Google Ads' resource types.
For example, to get campaigns with their budgets:

    SELECT campaign.id, campaign.name, campaign.campaign_budget
    FROM campaign
    WHERE campaign.status = 'ENABLED'

This query-based approach gives you precise control over what data you fetch, which
is important for staying within rate limits on large accounts.

Third, Google has a concept of "customer IDs" (also called CIDs) that represent the
10-digit account identifiers. When operating through a Manager Account (MCC), you
authenticate with the MCC but specify which customer ID to operate on. This makes
managing hundreds of client accounts from a single credential set straightforward.

Authentication Options
----------------------

Google Ads API supports three authentication flows:

1. Service Account (Recommended for automation): Create a service account in Google
   Cloud Console, download the JSON key file, and add the service account's email
   to your Google Ads account. This provides non-expiring credentials ideal for
   server-side automation.

2. OAuth Web Flow: For applications where users authorize their own accounts. The
   user goes through Google's OAuth consent screen, and you receive tokens to act
   on their behalf. Tokens need periodic refresh.

3. OAuth Desktop Flow: Similar to web flow but designed for installed applications.
   Uses a local redirect to capture the authorization code.

For Stratum's automated operations, we recommend the service account approach because
it eliminates token refresh complexity and works reliably for long-running processes.

Rate Limits
-----------

Google Ads API has daily operation limits based on your developer token tier:

- Basic Access: 10,000 operations per day (default for new tokens)
- Standard Access: 15,000 operations per day (after review)
- Advanced Access: Custom limits (requires business relationship)

Operations include both reads and writes. A single GAQL query counts as one operation
regardless of how many rows it returns. Batch operations count as one operation per
entity modified.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import os

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2

from stratum.adapters.base import (
    BaseAdapter,
    AdapterError,
    AuthenticationError,
    RateLimitError,
    PlatformError,
    RateLimiter
)
from stratum.models import (
    Platform,
    UnifiedAccount,
    UnifiedCampaign,
    UnifiedAdSet,
    UnifiedAd,
    PerformanceMetrics,
    EMQScore,
    AutomationAction,
    EntityStatus,
    BiddingStrategy
)


logger = logging.getLogger("stratum.adapters.google")


class GoogleAdsAdapter(BaseAdapter):
    """
    Google Ads API adapter for Search, Display, Shopping, and Video campaigns.
    
    This adapter handles the complexity of Google's protobuf-based API, translating
    between Stratum's unified models and Google's strongly-typed resource messages.
    It supports all standard campaign types and provides access to Google's powerful
    automated bidding strategies.
    
    Required Credentials:
        developer_token: Your Google Ads API developer token
        client_id: OAuth client ID from Google Cloud Console
        client_secret: OAuth client secret
        refresh_token: OAuth refresh token for the authorized user
        
    OR for Service Account authentication:
        developer_token: Your Google Ads API developer token
        json_key_file_path: Path to service account JSON key file
        impersonated_email: Email of user to impersonate
        
    Optional:
        login_customer_id: MCC account ID if using manager account
    
    Example Usage:
    
        credentials = {
            "developer_token": "XXXXXXXX",
            "client_id": "123456.apps.googleusercontent.com",
            "client_secret": "abcdef...",
            "refresh_token": "1//xxxxx",
            "login_customer_id": "1234567890"
        }
        
        adapter = GoogleAdsAdapter(credentials)
        await adapter.initialize()
        
        # Get campaigns
        campaigns = await adapter.get_campaigns("9876543210")
        
        # Update budget using GAQL-style operations
        action = AutomationAction(
            platform=Platform.GOOGLE,
            account_id="9876543210",
            entity_type="campaign",
            entity_id="12345",
            action_type="update_budget",
            parameters={"daily_budget": 50.00}
        )
        await adapter.execute_action(action)
    """
    
    # Status mapping between Stratum's unified status and Google's enum values
    # Google uses protobuf enums, but the Python client exposes them as integers
    STATUS_TO_GOOGLE = {
        EntityStatus.ACTIVE: "ENABLED",
        EntityStatus.PAUSED: "PAUSED",
        EntityStatus.DELETED: "REMOVED",
    }
    
    STATUS_FROM_GOOGLE = {
        "ENABLED": EntityStatus.ACTIVE,
        "PAUSED": EntityStatus.PAUSED,
        "REMOVED": EntityStatus.DELETED,
        "UNKNOWN": EntityStatus.ACTIVE,
        "UNSPECIFIED": EntityStatus.ACTIVE,
    }
    
    # Bidding strategy mapping
    # Google has many bidding strategies; these are the most common for automation
    BIDDING_TO_GOOGLE = {
        BiddingStrategy.TARGET_CPA: "TARGET_CPA",
        BiddingStrategy.TARGET_ROAS: "TARGET_ROAS",
        BiddingStrategy.MAXIMIZE_CONVERSIONS: "MAXIMIZE_CONVERSIONS",
        BiddingStrategy.MAXIMIZE_VALUE: "MAXIMIZE_CONVERSION_VALUE",
        BiddingStrategy.MANUAL_CPC: "MANUAL_CPC",
    }
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize the Google Ads adapter with authentication credentials.
        
        The credentials dictionary should contain either OAuth credentials
        (client_id, client_secret, refresh_token) or service account credentials
        (json_key_file_path, impersonated_email). Both require a developer_token.
        
        The login_customer_id is optional but recommended when working with
        multiple accounts through a Manager Account (MCC).
        """
        super().__init__(credentials)
        
        # Validate required credentials
        if "developer_token" not in credentials:
            raise ValueError("developer_token is required for Google Ads API")
        
        self.developer_token = credentials["developer_token"]
        self.login_customer_id = credentials.get("login_customer_id")
        
        # Store authentication details for client initialization
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.refresh_token = credentials.get("refresh_token")
        self.json_key_file_path = credentials.get("json_key_file_path")
        self.impersonated_email = credentials.get("impersonated_email")
        
        # Client instance (initialized in initialize())
        self.client: Optional[GoogleAdsClient] = None
        
        # Configure rate limiter for Google's daily limits
        # We use a conservative per-minute rate that stays within daily quotas
        self.rate_limiter = RateLimiter(
            calls_per_minute=6,   # ~8640/day, well under 10k limit
            burst_size=10
        )
    
    @property
    def platform(self) -> Platform:
        """Return the platform identifier."""
        return Platform.GOOGLE
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    async def initialize(self) -> None:
        """
        Initialize the Google Ads API client and verify authentication.
        
        This method builds the GoogleAdsClient using either OAuth or service
        account credentials, then makes a test API call to verify everything
        is configured correctly. The client is thread-safe and can be reused
        for all subsequent operations.
        """
        logger.info("Initializing Google Ads API adapter")
        
        try:
            # Build configuration dictionary for the client
            # The Google Ads client accepts configuration as a dict
            config = {
                "developer_token": self.developer_token,
                "use_proto_plus": True,  # Use the modern proto-plus library
            }
            
            if self.login_customer_id:
                config["login_customer_id"] = self.login_customer_id
            
            # Choose authentication method
            if self.json_key_file_path:
                # Service account authentication
                config["json_key_file_path"] = self.json_key_file_path
                if self.impersonated_email:
                    config["impersonated_email"] = self.impersonated_email
            else:
                # OAuth authentication
                config["client_id"] = self.client_id
                config["client_secret"] = self.client_secret
                config["refresh_token"] = self.refresh_token
            
            # Create the client
            self.client = GoogleAdsClient.load_from_dict(config)
            
            # Verify authentication by listing accessible accounts
            await self.rate_limiter.acquire()
            accounts = await self.get_accounts()
            
            if not accounts:
                logger.warning("No ad accounts accessible with provided credentials")
            else:
                logger.info(f"Successfully authenticated, found {len(accounts)} accounts")
            
            self._initialized = True
            
        except GoogleAdsException as e:
            error_msg = self._parse_google_error(e)
            if "AUTHENTICATION_ERROR" in error_msg:
                raise AuthenticationError(
                    "Google Ads authentication failed. Verify your credentials "
                    "and ensure the user has access to the specified accounts."
                )
            raise AdapterError(f"Google Ads API error: {error_msg}")
    
    async def cleanup(self) -> None:
        """Release adapter resources."""
        self._initialized = False
        self.client = None
        logger.info("Google Ads adapter cleanup complete")
    
    # ========================================================================
    # READ OPERATIONS
    # ========================================================================
    
    async def get_accounts(self) -> List[UnifiedAccount]:
        """
        Fetch all advertising accounts accessible with current credentials.
        
        When using a Manager Account (MCC), this returns all client accounts
        under that manager. When using direct account credentials, this returns
        just that single account.
        
        The method uses GAQL to query the customer resource, which contains
        account-level settings like currency and timezone.
        """
        self._ensure_initialized()
        
        try:
            # If we have a login_customer_id (MCC), list client accounts
            if self.login_customer_id:
                return await self._get_mcc_accounts()
            else:
                # Otherwise, get info about the single authenticated account
                return await self._get_single_account()
                
        except GoogleAdsException as e:
            raise PlatformError(
                f"Failed to fetch accounts: {self._parse_google_error(e)}"
            )
    
    async def _get_mcc_accounts(self) -> List[UnifiedAccount]:
        """Fetch client accounts from a Manager Account."""
        ga_service = self.client.get_service("GoogleAdsService")
        customer_service = self.client.get_service("CustomerService")
        
        # Use GAQL to query customer clients (child accounts of the MCC)
        query = """
            SELECT
                customer_client.id,
                customer_client.descriptive_name,
                customer_client.currency_code,
                customer_client.time_zone,
                customer_client.manager,
                customer_client.status
            FROM customer_client
            WHERE customer_client.status = 'ENABLED'
              AND customer_client.manager = false
        """
        
        await self.rate_limiter.acquire()
        response = ga_service.search(
            customer_id=str(self.login_customer_id),
            query=query
        )
        
        accounts = []
        for row in response:
            cc = row.customer_client
            account = UnifiedAccount(
                platform=Platform.GOOGLE,
                account_id=str(cc.id),
                account_name=cc.descriptive_name or f"Account {cc.id}",
                business_id=str(self.login_customer_id),
                timezone=cc.time_zone,
                currency=cc.currency_code,
                last_synced=datetime.utcnow(),
                raw_data={
                    "id": cc.id,
                    "name": cc.descriptive_name,
                    "currency": cc.currency_code,
                    "timezone": cc.time_zone,
                }
            )
            accounts.append(account)
        
        return accounts
    
    async def _get_single_account(self) -> List[UnifiedAccount]:
        """Get info about a single directly-authenticated account."""
        customer_service = self.client.get_service("CustomerService")
        
        # When no MCC, we need to know which customer ID to use
        # This is typically passed as login_customer_id even for single accounts
        if not self.login_customer_id:
            logger.warning("No customer_id specified, cannot fetch account info")
            return []
        
        await self.rate_limiter.acquire()
        
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone
            FROM customer
            LIMIT 1
        """
        
        response = ga_service.search(
            customer_id=str(self.login_customer_id),
            query=query
        )
        
        accounts = []
        for row in response:
            c = row.customer
            account = UnifiedAccount(
                platform=Platform.GOOGLE,
                account_id=str(c.id),
                account_name=c.descriptive_name or f"Account {c.id}",
                timezone=c.time_zone,
                currency=c.currency_code,
                last_synced=datetime.utcnow(),
            )
            accounts.append(account)
        
        return accounts
    
    async def get_campaigns(
        self,
        account_id: str,
        status_filter: Optional[List[EntityStatus]] = None
    ) -> List[UnifiedCampaign]:
        """
        Fetch campaigns for the specified Google Ads account.
        
        This method uses GAQL to query campaigns with their associated budgets
        and bidding strategies. Google Ads separates budgets into their own
        resource (CampaignBudget), so we join that data in the query.
        
        The status_filter works slightly differently than Meta because Google
        uses enum names rather than arbitrary strings.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            # Build the GAQL query
            # We join campaign with campaign_budget to get budget info in one call
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.bidding_strategy_type,
                    campaign.target_cpa.target_cpa_micros,
                    campaign.target_roas.target_roas,
                    campaign_budget.id,
                    campaign_budget.amount_micros,
                    campaign_budget.total_amount_micros,
                    campaign_budget.period
                FROM campaign
            """
            
            # Add status filter if specified
            if status_filter:
                google_statuses = [
                    self.STATUS_TO_GOOGLE.get(s, "ENABLED")
                    for s in status_filter
                ]
                status_str = ", ".join(f"'{s}'" for s in google_statuses)
                query += f" WHERE campaign.status IN ({status_str})"
            
            response = ga_service.search(
                customer_id=str(account_id).replace("-", ""),
                query=query
            )
            
            campaigns = []
            for row in response:
                campaign = self._convert_campaign(row, account_id)
                campaigns.append(campaign)
            
            logger.info(f"Fetched {len(campaigns)} campaigns from account {account_id}")
            return campaigns
            
        except GoogleAdsException as e:
            raise PlatformError(
                f"Failed to fetch campaigns: {self._parse_google_error(e)}"
            )
    
    async def get_adsets(
        self,
        account_id: str,
        campaign_id: Optional[str] = None
    ) -> List[UnifiedAdSet]:
        """
        Fetch ad groups for the specified account.
        
        Google calls the middle tier "Ad Groups" rather than "Ad Sets" (Meta's term).
        Ad groups contain targeting settings at the group level, though much targeting
        in Google Ads is also specified at the campaign level (audience segments,
        location targeting, etc.).
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.campaign,
                    ad_group.status,
                    ad_group.cpc_bid_micros,
                    ad_group.target_cpa_micros
                FROM ad_group
            """
            
            if campaign_id:
                query += f" WHERE ad_group.campaign = 'customers/{account_id}/campaigns/{campaign_id}'"
            
            response = ga_service.search(
                customer_id=str(account_id).replace("-", ""),
                query=query
            )
            
            adsets = []
            for row in response:
                adset = self._convert_adset(row, account_id)
                adsets.append(adset)
            
            return adsets
            
        except GoogleAdsException as e:
            raise PlatformError(
                f"Failed to fetch ad groups: {self._parse_google_error(e)}"
            )
    
    async def get_ads(
        self,
        account_id: str,
        adset_id: Optional[str] = None
    ) -> List[UnifiedAd]:
        """
        Fetch ads for the specified account.
        
        In Google Ads, the ad entity is called "AdGroupAd" and contains both
        the ad itself and its relationship to the ad group. The actual creative
        content is in the nested "ad" field.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad_group,
                    ad_group_ad.status,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions
                FROM ad_group_ad
            """
            
            if adset_id:
                query += f" WHERE ad_group_ad.ad_group = 'customers/{account_id}/adGroups/{adset_id}'"
            
            response = ga_service.search(
                customer_id=str(account_id).replace("-", ""),
                query=query
            )
            
            ads = []
            for row in response:
                ad = self._convert_ad(row, account_id)
                ads.append(ad)
            
            return ads
            
        except GoogleAdsException as e:
            raise PlatformError(
                f"Failed to fetch ads: {self._parse_google_error(e)}"
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
        Fetch performance metrics using GAQL.
        
        Google Ads stores metrics in separate "segments" that can be added to
        queries. By including metrics.* fields, we get performance data aggregated
        across the specified date range.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            # Build resource name based on entity type
            resource_map = {
                "campaign": "campaign",
                "adset": "ad_group",
                "ad": "ad_group_ad"
            }
            resource = resource_map.get(entity_type, "campaign")
            
            # Build ID field based on entity type
            id_field_map = {
                "campaign": "campaign.id",
                "adset": "ad_group.id",
                "ad": "ad_group_ad.ad.id"
            }
            id_field = id_field_map.get(entity_type, "campaign.id")
            
            query = f"""
                SELECT
                    {id_field},
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.cost_per_conversion,
                    metrics.video_views,
                    metrics.video_quartile_p25_rate,
                    metrics.video_quartile_p50_rate,
                    metrics.video_quartile_p75_rate,
                    metrics.video_quartile_p100_rate
                FROM {resource}
                WHERE segments.date BETWEEN '{date_start.strftime('%Y-%m-%d')}' 
                    AND '{date_end.strftime('%Y-%m-%d')}'
            """
            
            # Add entity filter if specific IDs requested
            if entity_ids:
                ids_str = ", ".join(str(id) for id in entity_ids)
                query += f" AND {id_field} IN ({ids_str})"
            
            response = ga_service.search(
                customer_id=str(account_id).replace("-", ""),
                query=query
            )
            
            metrics_map = {}
            for row in response:
                # Extract entity ID
                if entity_type == "campaign":
                    entity_id = str(row.campaign.id)
                elif entity_type == "adset":
                    entity_id = str(row.ad_group.id)
                else:
                    entity_id = str(row.ad_group_ad.ad.id)
                
                metrics = self._convert_metrics(row.metrics, date_start, date_end)
                metrics_map[entity_id] = metrics
            
            return metrics_map
            
        except GoogleAdsException as e:
            raise PlatformError(
                f"Failed to fetch metrics: {self._parse_google_error(e)}"
            )
    
    async def get_emq_scores(self, account_id: str) -> List[EMQScore]:
        """
        Fetch conversion matching diagnostics from Google Ads.
        
        Google doesn't have a direct EMQ score like Meta, but they do provide
        conversion diagnostics that indicate data quality. We query the
        conversion_action resource to get match rate information.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            # Query conversion actions with their diagnostics
            query = """
                SELECT
                    conversion_action.id,
                    conversion_action.name,
                    conversion_action.type,
                    conversion_action.status
                FROM conversion_action
                WHERE conversion_action.status = 'ENABLED'
            """
            
            response = ga_service.search(
                customer_id=str(account_id).replace("-", ""),
                query=query
            )
            
            emq_scores = []
            for row in response:
                ca = row.conversion_action
                
                # Google doesn't expose a direct EMQ score, but we can estimate
                # based on the conversion action type and configuration
                # Enhanced conversions (which require user data) score higher
                base_score = 5.0
                if ca.type_.name in ["UPLOAD_CALLS", "UPLOAD_CLICKS"]:
                    base_score = 7.0  # Offline conversions typically have better data
                elif ca.type_.name == "WEBPAGE":
                    base_score = 6.0  # Standard web conversions
                
                emq = EMQScore(
                    platform=Platform.GOOGLE,
                    event_name=ca.name,
                    score=base_score,
                    last_updated=datetime.utcnow()
                )
                emq_scores.append(emq)
            
            return emq_scores
            
        except GoogleAdsException as e:
            logger.warning(f"Failed to fetch conversion diagnostics: {self._parse_google_error(e)}")
            return []
    
    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================
    
    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        """
        Execute an automation action on Google Ads.
        
        Google Ads API uses a "mutate" pattern for all write operations. You
        create an operation object that specifies what to create/update/remove,
        then send it to the appropriate service's mutate method.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            action.status = "executing"
            
            if action.action_type == "update_budget":
                result = await self._update_budget(action)
            elif action.action_type == "update_bid":
                result = await self._update_bid(action)
            elif action.action_type == "update_status":
                result = await self._update_status(action)
            elif action.action_type == "create_campaign":
                result = await self._create_campaign(action)
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")
            
            action.status = "completed"
            action.executed_at = datetime.utcnow()
            action.result = result
            
            logger.info(f"Successfully executed {action.action_type} on {action.entity_id}")
            return action
            
        except GoogleAdsException as e:
            action.status = "failed"
            action.error_message = self._parse_google_error(e)
            logger.error(f"Action failed: {action.error_message}")
            return action
        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            logger.error(f"Action failed with unexpected error: {e}")
            return action
    
    async def _update_budget(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Update campaign budget in Google Ads.
        
        Google Ads budgets are separate resources linked to campaigns. To update
        a campaign's budget, we need to first get the campaign's budget resource
        name, then update that budget resource.
        """
        params = action.parameters
        account_id = str(action.account_id).replace("-", "")
        
        # First, get the campaign's budget resource name
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT campaign.campaign_budget
            FROM campaign
            WHERE campaign.id = {action.entity_id}
        """
        
        response = ga_service.search(customer_id=account_id, query=query)
        budget_resource_name = None
        for row in response:
            budget_resource_name = row.campaign.campaign_budget
            break
        
        if not budget_resource_name:
            raise ValueError(f"Could not find budget for campaign {action.entity_id}")
        
        # Now update the budget
        campaign_budget_service = self.client.get_service("CampaignBudgetService")
        campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
        
        campaign_budget = campaign_budget_operation.update
        campaign_budget.resource_name = budget_resource_name
        
        # Google uses micros (millionths), so multiply by 1,000,000
        if "daily_budget" in params:
            campaign_budget.amount_micros = int(params["daily_budget"] * 1_000_000)
        
        # Set the field mask to specify which fields we're updating
        field_mask = field_mask_pb2.FieldMask()
        field_mask.paths.append("amount_micros")
        campaign_budget_operation.update_mask.CopyFrom(field_mask)
        
        response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=account_id,
            operations=[campaign_budget_operation]
        )
        
        return {"updated_budget": budget_resource_name}
    
    async def _update_bid(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Update bidding configuration for a campaign or ad group.
        
        Google's bidding updates depend on the entity type and current strategy.
        For campaigns, we update the bidding strategy. For ad groups, we update
        the CPC bid or target CPA at the ad group level.
        """
        params = action.parameters
        account_id = str(action.account_id).replace("-", "")
        
        if action.entity_type == "campaign":
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            
            campaign = campaign_operation.update
            campaign.resource_name = f"customers/{account_id}/campaigns/{action.entity_id}"
            
            # Set target CPA if specified
            if "target_cpa" in params:
                campaign.target_cpa.target_cpa_micros = int(params["target_cpa"] * 1_000_000)
            
            # Set target ROAS if specified
            if "target_roas" in params:
                campaign.target_roas.target_roas = params["target_roas"]
            
            field_mask = field_mask_pb2.FieldMask()
            if "target_cpa" in params:
                field_mask.paths.append("target_cpa.target_cpa_micros")
            if "target_roas" in params:
                field_mask.paths.append("target_roas.target_roas")
            campaign_operation.update_mask.CopyFrom(field_mask)
            
            response = campaign_service.mutate_campaigns(
                customer_id=account_id,
                operations=[campaign_operation]
            )
            
        else:  # ad_group
            ad_group_service = self.client.get_service("AdGroupService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            
            ad_group = ad_group_operation.update
            ad_group.resource_name = f"customers/{account_id}/adGroups/{action.entity_id}"
            
            if "bid_amount" in params:
                ad_group.cpc_bid_micros = int(params["bid_amount"] * 1_000_000)
            
            field_mask = field_mask_pb2.FieldMask()
            field_mask.paths.append("cpc_bid_micros")
            ad_group_operation.update_mask.CopyFrom(field_mask)
            
            response = ad_group_service.mutate_ad_groups(
                customer_id=account_id,
                operations=[ad_group_operation]
            )
        
        return {"updated_fields": list(params.keys())}
    
    async def _update_status(self, action: AutomationAction) -> Dict[str, Any]:
        """Update the status of a campaign, ad group, or ad."""
        params = action.parameters
        account_id = str(action.account_id).replace("-", "")
        new_status = EntityStatus(params["status"])
        google_status = self.STATUS_TO_GOOGLE.get(new_status, "ENABLED")
        
        if action.entity_type == "campaign":
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            
            campaign = campaign_operation.update
            campaign.resource_name = f"customers/{account_id}/campaigns/{action.entity_id}"
            campaign.status = self.client.enums.CampaignStatusEnum[google_status].value
            
            field_mask = field_mask_pb2.FieldMask()
            field_mask.paths.append("status")
            campaign_operation.update_mask.CopyFrom(field_mask)
            
            response = campaign_service.mutate_campaigns(
                customer_id=account_id,
                operations=[campaign_operation]
            )
            
        elif action.entity_type == "adset":
            ad_group_service = self.client.get_service("AdGroupService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            
            ad_group = ad_group_operation.update
            ad_group.resource_name = f"customers/{account_id}/adGroups/{action.entity_id}"
            ad_group.status = self.client.enums.AdGroupStatusEnum[google_status].value
            
            field_mask = field_mask_pb2.FieldMask()
            field_mask.paths.append("status")
            ad_group_operation.update_mask.CopyFrom(field_mask)
            
            response = ad_group_service.mutate_ad_groups(
                customer_id=account_id,
                operations=[ad_group_operation]
            )
        
        return {"new_status": google_status}
    
    async def _create_campaign(self, action: AutomationAction) -> Dict[str, Any]:
        """
        Create a new campaign in Google Ads.
        
        Campaign creation in Google requires creating the budget first as a
        separate resource, then creating the campaign that references it.
        """
        params = action.parameters
        account_id = str(action.account_id).replace("-", "")
        
        # First, create the budget
        campaign_budget_service = self.client.get_service("CampaignBudgetService")
        campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
        
        campaign_budget = campaign_budget_operation.create
        campaign_budget.name = f"{params['name']} Budget"
        campaign_budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD
        
        if "daily_budget" in params:
            campaign_budget.amount_micros = int(params["daily_budget"] * 1_000_000)
        
        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=account_id,
            operations=[campaign_budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name
        
        # Now create the campaign
        campaign_service = self.client.get_service("CampaignService")
        campaign_operation = self.client.get_type("CampaignOperation")
        
        campaign = campaign_operation.create
        campaign.name = params["name"]
        campaign.campaign_budget = budget_resource_name
        campaign.status = self.client.enums.CampaignStatusEnum.PAUSED
        
        # Set advertising channel type
        channel_type = params.get("channel_type", "SEARCH")
        campaign.advertising_channel_type = (
            self.client.enums.AdvertisingChannelTypeEnum[channel_type].value
        )
        
        # Set bidding strategy
        if "bidding_strategy" in params:
            strategy = BiddingStrategy(params["bidding_strategy"])
            if strategy == BiddingStrategy.MAXIMIZE_CONVERSIONS:
                campaign.maximize_conversions.target_cpa_micros = 0
            elif strategy == BiddingStrategy.TARGET_CPA:
                campaign.target_cpa.target_cpa_micros = int(
                    params.get("target_cpa", 10) * 1_000_000
                )
        
        response = campaign_service.mutate_campaigns(
            customer_id=account_id,
            operations=[campaign_operation]
        )
        
        return {"campaign_resource_name": response.results[0].resource_name}
    
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
        Upload an image to Google Ads asset library.
        
        Google Ads stores images as "Asset" resources. Once uploaded, the asset
        can be referenced in ad creatives by its resource name.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        account_id = str(account_id).replace("-", "")
        
        asset_service = self.client.get_service("AssetService")
        asset_operation = self.client.get_type("AssetOperation")
        
        asset = asset_operation.create
        asset.name = filename
        asset.type_ = self.client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = image_data
        
        response = asset_service.mutate_assets(
            customer_id=account_id,
            operations=[asset_operation]
        )
        
        return response.results[0].resource_name
    
    async def upload_video(
        self,
        account_id: str,
        video_data: bytes,
        filename: str
    ) -> str:
        """
        Upload a video reference to Google Ads.
        
        Unlike Meta, Google Ads doesn't host videos directly. Videos must first
        be uploaded to YouTube, and then referenced by their YouTube video ID.
        This method creates the asset reference assuming the video is already
        on YouTube.
        """
        # Note: Google Ads requires videos to be on YouTube
        # This would need YouTube API integration for full functionality
        logger.warning(
            "Google Ads requires videos on YouTube. "
            "Please upload to YouTube first and use the video ID."
        )
        return ""
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _ensure_initialized(self) -> None:
        """Verify adapter is initialized before making API calls."""
        if not self._initialized or not self.client:
            raise AdapterError("Adapter not initialized. Call initialize() first.")
    
    def _parse_google_error(self, exception: GoogleAdsException) -> str:
        """Extract a readable error message from Google Ads exceptions."""
        errors = []
        for error in exception.failure.errors:
            errors.append(f"{error.error_code}: {error.message}")
        return "; ".join(errors) if errors else str(exception)
    
    def _convert_campaign(self, row: Any, account_id: str) -> UnifiedCampaign:
        """Convert Google Ads campaign row to unified model."""
        c = row.campaign
        b = row.campaign_budget
        
        # Determine budget type and value
        daily_budget = None
        lifetime_budget = None
        
        if b.amount_micros:
            daily_budget = b.amount_micros / 1_000_000
        if b.total_amount_micros:
            lifetime_budget = b.total_amount_micros / 1_000_000
        
        # Determine bidding strategy
        bidding_strategy = BiddingStrategy.MANUAL_CPC
        target_cpa = None
        target_roas = None
        
        if c.bidding_strategy_type:
            strategy_name = c.bidding_strategy_type.name
            if "TARGET_CPA" in strategy_name:
                bidding_strategy = BiddingStrategy.TARGET_CPA
                if c.target_cpa and c.target_cpa.target_cpa_micros:
                    target_cpa = c.target_cpa.target_cpa_micros / 1_000_000
            elif "TARGET_ROAS" in strategy_name:
                bidding_strategy = BiddingStrategy.TARGET_ROAS
                if c.target_roas and c.target_roas.target_roas:
                    target_roas = c.target_roas.target_roas
            elif "MAXIMIZE_CONVERSIONS" in strategy_name:
                bidding_strategy = BiddingStrategy.MAXIMIZE_CONVERSIONS
            elif "MAXIMIZE_CONVERSION_VALUE" in strategy_name:
                bidding_strategy = BiddingStrategy.MAXIMIZE_VALUE
        
        return UnifiedCampaign(
            platform=Platform.GOOGLE,
            account_id=account_id,
            campaign_id=str(c.id),
            campaign_name=c.name,
            status=self.STATUS_FROM_GOOGLE.get(c.status.name, EntityStatus.ACTIVE),
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
            bidding_strategy=bidding_strategy,
            target_cpa=target_cpa,
            target_roas=target_roas,
            last_synced=datetime.utcnow(),
            raw_data={
                "campaign_id": c.id,
                "name": c.name,
                "status": c.status.name,
                "channel_type": c.advertising_channel_type.name if c.advertising_channel_type else None,
                "budget_id": b.id if b.id else None,
            }
        )
    
    def _convert_adset(self, row: Any, account_id: str) -> UnifiedAdSet:
        """Convert Google Ads ad group row to unified model."""
        ag = row.ad_group
        
        # Extract campaign ID from resource name
        campaign_id = ""
        if ag.campaign:
            parts = ag.campaign.split("/")
            campaign_id = parts[-1] if parts else ""
        
        bid_amount = None
        if ag.cpc_bid_micros:
            bid_amount = ag.cpc_bid_micros / 1_000_000
        
        return UnifiedAdSet(
            platform=Platform.GOOGLE,
            account_id=account_id,
            campaign_id=campaign_id,
            adset_id=str(ag.id),
            adset_name=ag.name,
            status=self.STATUS_FROM_GOOGLE.get(ag.status.name, EntityStatus.ACTIVE),
            bid_amount=bid_amount,
            last_synced=datetime.utcnow(),
            raw_data={
                "ad_group_id": ag.id,
                "name": ag.name,
                "status": ag.status.name,
            }
        )
    
    def _convert_ad(self, row: Any, account_id: str) -> UnifiedAd:
        """Convert Google Ads ad row to unified model."""
        aga = row.ad_group_ad
        ad = aga.ad
        
        # Extract ad group ID from resource name
        adset_id = ""
        if aga.ad_group:
            parts = aga.ad_group.split("/")
            adset_id = parts[-1] if parts else ""
        
        # Get headline and description from responsive search ad
        headline = ""
        description = ""
        if ad.responsive_search_ad:
            headlines = ad.responsive_search_ad.headlines
            if headlines:
                headline = headlines[0].text if headlines[0].text else ""
            descriptions = ad.responsive_search_ad.descriptions
            if descriptions:
                description = descriptions[0].text if descriptions[0].text else ""
        
        # Get destination URL
        destination_url = ""
        if ad.final_urls:
            destination_url = ad.final_urls[0]
        
        return UnifiedAd(
            platform=Platform.GOOGLE,
            account_id=account_id,
            campaign_id="",  # Would need separate query to get this
            adset_id=adset_id,
            ad_id=str(ad.id),
            ad_name=ad.name if ad.name else f"Ad {ad.id}",
            status=self.STATUS_FROM_GOOGLE.get(aga.status.name, EntityStatus.ACTIVE),
            headline=headline,
            description=description,
            destination_url=destination_url,
            last_synced=datetime.utcnow(),
            raw_data={
                "ad_id": ad.id,
                "type": ad.type_.name if ad.type_ else None,
            }
        )
    
    def _convert_metrics(
        self,
        m: Any,
        date_start: datetime,
        date_end: datetime
    ) -> PerformanceMetrics:
        """Convert Google Ads metrics to unified model."""
        metrics = PerformanceMetrics(
            impressions=m.impressions if m.impressions else 0,
            clicks=m.clicks if m.clicks else 0,
            spend=m.cost_micros / 1_000_000 if m.cost_micros else 0,
            ctr=m.ctr if m.ctr else None,
            cpc=m.average_cpc / 1_000_000 if m.average_cpc else None,
            conversions=int(m.conversions) if m.conversions else None,
            conversion_value=m.conversions_value if m.conversions_value else None,
            cpa=m.cost_per_conversion / 1_000_000 if m.cost_per_conversion else None,
            video_views=m.video_views if hasattr(m, 'video_views') else None,
            date_start=date_start,
            date_end=date_end,
        )
        
        # Calculate ROAS
        if metrics.conversion_value and metrics.spend > 0:
            metrics.roas = metrics.conversion_value / metrics.spend
        
        # Compute any missing derived metrics
        metrics.compute_derived_metrics()
        
        return metrics
    
    def _map_status_to_platform(self, status: EntityStatus) -> str:
        """Convert unified status to Google's status enum name."""
        return self.STATUS_TO_GOOGLE.get(status, "ENABLED")
    
    def _map_status_from_platform(self, platform_status: str) -> EntityStatus:
        """Convert Google's status enum name to unified status."""
        return self.STATUS_FROM_GOOGLE.get(platform_status, EntityStatus.ACTIVE)
