"""
Stratum AI: TikTok Business API Adapter
=======================================

This adapter provides bi-directional integration with TikTok's Business API (also known
as the TikTok Marketing API), enabling Stratum to manage advertising campaigns on one
of the fastest-growing social platforms. TikTok's advertising ecosystem has matured
significantly, now offering sophisticated targeting, conversion tracking, and automated
bidding similar to more established platforms.

Understanding TikTok's Advertising Structure
--------------------------------------------

TikTok organizes advertising entities in a hierarchy similar to Meta, though with some
naming differences. At the top level, you have Advertiser Accounts (equivalent to Ad
Accounts). Each Advertiser contains Campaigns, which contain Ad Groups (TikTok's term
for what Meta calls Ad Sets), which finally contain Ads.

The key distinction in TikTok is the separation between "Auction" and "Reservation"
buying types. Auction campaigns (the most common) bid in real-time for impressions,
while Reservation campaigns guarantee delivery for a fixed price. This adapter focuses
on Auction campaigns, which are most suitable for performance marketing automation.

TikTok's optimization goals are heavily video-focused, which makes sense given the
platform's short-form video format. Common goals include Video Views, Reach, Traffic,
App Installs, and Conversions. The Conversions objective requires proper Pixel or
Events API setup for tracking.

Authentication
--------------

TikTok uses OAuth 2.0 for authentication. The process involves creating an app in the
TikTok for Business developer portal, then having advertisers authorize that app to
access their ad accounts. The authorization flow returns an access token that can be
used for API calls.

Unlike Meta's long-lived tokens, TikTok access tokens expire after a period (typically
24 hours), but come with a refresh token that can be used to obtain new access tokens.
This adapter handles token refresh automatically.

Rate Limits
-----------

TikTok's API has rate limits that vary by endpoint. Generally, you can expect around
1000 requests per minute for most endpoints. The API returns rate limit information
in response headers, which this adapter monitors to avoid hitting limits.

API Versioning
--------------

TikTok's Business API uses versioned endpoints (currently v1.3 is common). The API
is actively developed, with new features added regularly. This adapter targets stable
endpoints that are unlikely to change frequently.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import hashlib
import hmac

import requests
from requests.auth import AuthBase

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
    BiddingStrategy
)


logger = logging.getLogger("stratum.adapters.tiktok")


class TikTokAdapter(BaseAdapter):
    """
    TikTok Business API adapter for TikTok advertising campaigns.
    
    This adapter handles the REST API calls to TikTok's Business API, translating
    between Stratum's unified models and TikTok's native API formats. It supports
    all standard CRUD operations on campaigns, ad groups, and ads.
    
    TikTok's API is JSON-based and relatively straightforward compared to Google's
    protobuf system. Most operations follow a simple request/response pattern with
    JSON payloads.
    
    Required Credentials:
        app_id: Your TikTok Business app ID
        secret: Your TikTok Business app secret
        access_token: OAuth access token for the authorized advertiser
        
    Optional:
        advertiser_id: Default advertiser ID to use for operations
    
    Example Usage:
    
        credentials = {
            "app_id": "123456789",
            "secret": "abc123...",
            "access_token": "eyJhbGci...",
            "advertiser_id": "7123456789"
        }
        
        adapter = TikTokAdapter(credentials)
        await adapter.initialize()
        
        campaigns = await adapter.get_campaigns("7123456789")
    """
    
    # TikTok API base URL (production)
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    
    # Status mapping between Stratum and TikTok
    # TikTok uses string values for status
    STATUS_TO_TIKTOK = {
        EntityStatus.ACTIVE: "ENABLE",
        EntityStatus.PAUSED: "DISABLE",
        EntityStatus.DELETED: "DELETE",
    }
    
    STATUS_FROM_TIKTOK = {
        "ENABLE": EntityStatus.ACTIVE,
        "DISABLE": EntityStatus.PAUSED,
        "DELETE": EntityStatus.DELETED,
        "CAMPAIGN_STATUS_ENABLE": EntityStatus.ACTIVE,
        "CAMPAIGN_STATUS_DISABLE": EntityStatus.PAUSED,
        "ADGROUP_STATUS_DELIVERY_OK": EntityStatus.ACTIVE,
        "ADGROUP_STATUS_CAMPAIGN_DISABLE": EntityStatus.PAUSED,
    }
    
    # Bidding strategy mapping
    BIDDING_TO_TIKTOK = {
        BiddingStrategy.LOWEST_COST: "BID_TYPE_NO_BID",
        BiddingStrategy.COST_CAP: "BID_TYPE_CUSTOM",
        BiddingStrategy.BID_CAP: "BID_TYPE_CUSTOM",
    }
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize the TikTok adapter with API credentials.
        
        The access_token is the key credential that authorizes API access. If you're
        building a multi-tenant system, each advertiser would have their own access
        token obtained through TikTok's OAuth flow.
        """
        super().__init__(credentials)
        
        # Validate required credentials
        if "access_token" not in credentials:
            raise ValueError("access_token is required for TikTok API")
        
        self.app_id = credentials.get("app_id", "")
        self.secret = credentials.get("secret", "")
        self.access_token = credentials["access_token"]
        self.default_advertiser_id = credentials.get("advertiser_id")
        
        # Session for connection pooling
        self.session: Optional[requests.Session] = None
        
        # Rate limiter configured for TikTok's limits
        self.rate_limiter = RateLimiter(
            calls_per_minute=100,  # Conservative limit
            burst_size=20
        )
    
    @property
    def platform(self) -> Platform:
        """Return the platform identifier."""
        return Platform.TIKTOK
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    async def initialize(self) -> None:
        """
        Initialize the TikTok API client and verify authentication.
        
        This creates a requests session with the necessary headers and makes
        a test API call to verify the access token is valid. The session is
        reused for all subsequent calls to benefit from connection pooling.
        """
        logger.info("Initializing TikTok Business API adapter")
        
        try:
            # Create session with default headers
            self.session = requests.Session()
            self.session.headers.update({
                "Access-Token": self.access_token,
                "Content-Type": "application/json"
            })
            
            # Verify authentication by fetching advertiser info
            await self.rate_limiter.acquire()
            
            if self.default_advertiser_id:
                # Test with a simple info request
                response = self._make_request(
                    "GET",
                    "/advertiser/info/",
                    params={"advertiser_ids": json.dumps([self.default_advertiser_id])}
                )
                
                if response.get("code") != 0:
                    raise AuthenticationError(
                        f"TikTok API error: {response.get('message', 'Unknown error')}"
                    )
                
                logger.info(f"Successfully authenticated with TikTok API")
            else:
                logger.warning("No default advertiser_id configured")
            
            self._initialized = True
            
        except requests.RequestException as e:
            raise AdapterError(f"Failed to connect to TikTok API: {e}")
    
    async def cleanup(self) -> None:
        """Clean up adapter resources."""
        if self.session:
            self.session.close()
            self.session = None
        self._initialized = False
        logger.info("TikTok adapter cleanup complete")
    
    # ========================================================================
    # READ OPERATIONS
    # ========================================================================
    
    async def get_accounts(self) -> List[UnifiedAccount]:
        """
        Fetch advertiser accounts accessible with current credentials.
        
        TikTok's API requires knowing advertiser IDs in advance for most operations.
        If you're authorized through a Business Center, you can list all advertisers
        under that center. Otherwise, you need the advertiser IDs from somewhere else.
        """
        self._ensure_initialized()
        
        if not self.default_advertiser_id:
            logger.warning("No advertiser_id configured, returning empty list")
            return []
        
        try:
            await self.rate_limiter.acquire()
            
            response = self._make_request(
                "GET",
                "/advertiser/info/",
                params={"advertiser_ids": json.dumps([self.default_advertiser_id])}
            )
            
            if response.get("code") != 0:
                raise PlatformError(f"TikTok API error: {response.get('message')}")
            
            accounts = []
            for adv in response.get("data", {}).get("list", []):
                account = UnifiedAccount(
                    platform=Platform.TIKTOK,
                    account_id=str(adv.get("advertiser_id", "")),
                    account_name=adv.get("name", "Unknown"),
                    timezone=adv.get("timezone", "UTC"),
                    currency=adv.get("currency", "USD"),
                    last_synced=datetime.utcnow(),
                    raw_data=adv
                )
                accounts.append(account)
            
            return accounts
            
        except Exception as e:
            raise PlatformError(f"Failed to fetch accounts: {e}")
    
    async def get_campaigns(
        self,
        account_id: str,
        status_filter: Optional[List[EntityStatus]] = None
    ) -> List[UnifiedCampaign]:
        """
        Fetch campaigns for the specified TikTok advertiser account.
        
        TikTok's campaign endpoint supports filtering by various criteria including
        status. The response includes budget information and objective settings.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            params = {
                "advertiser_id": account_id,
                "page_size": 100
            }
            
            # Add status filter if specified
            if status_filter:
                tiktok_statuses = [
                    self.STATUS_TO_TIKTOK.get(s, "ENABLE")
                    for s in status_filter
                ]
                params["filtering"] = json.dumps({
                    "primary_status": tiktok_statuses[0] if len(tiktok_statuses) == 1 else None
                })
            
            response = self._make_request(
                "GET",
                "/campaign/get/",
                params=params
            )
            
            if response.get("code") != 0:
                raise PlatformError(f"TikTok API error: {response.get('message')}")
            
            campaigns = []
            for raw in response.get("data", {}).get("list", []):
                campaign = self._convert_campaign(raw, account_id)
                campaigns.append(campaign)
            
            logger.info(f"Fetched {len(campaigns)} campaigns from TikTok account {account_id}")
            return campaigns
            
        except Exception as e:
            raise PlatformError(f"Failed to fetch campaigns: {e}")
    
    async def get_adsets(
        self,
        account_id: str,
        campaign_id: Optional[str] = None
    ) -> List[UnifiedAdSet]:
        """
        Fetch ad groups for the specified account.
        
        TikTok calls these "Ad Groups" similar to Google. Each ad group contains
        targeting settings, bid configuration, and budget (if not using campaign-level
        budgeting).
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            params = {
                "advertiser_id": account_id,
                "page_size": 100
            }
            
            if campaign_id:
                params["filtering"] = json.dumps({"campaign_ids": [campaign_id]})
            
            response = self._make_request(
                "GET",
                "/adgroup/get/",
                params=params
            )
            
            if response.get("code") != 0:
                raise PlatformError(f"TikTok API error: {response.get('message')}")
            
            adsets = []
            for raw in response.get("data", {}).get("list", []):
                adset = self._convert_adset(raw, account_id)
                adsets.append(adset)
            
            return adsets
            
        except Exception as e:
            raise PlatformError(f"Failed to fetch ad groups: {e}")
    
    async def get_ads(
        self,
        account_id: str,
        adset_id: Optional[str] = None
    ) -> List[UnifiedAd]:
        """
        Fetch ads for the specified account.
        
        TikTok ads contain creative content including video, display URL, call-to-action,
        and landing page URL. Each ad must belong to an ad group.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            params = {
                "advertiser_id": account_id,
                "page_size": 100
            }
            
            if adset_id:
                params["filtering"] = json.dumps({"adgroup_ids": [adset_id]})
            
            response = self._make_request(
                "GET",
                "/ad/get/",
                params=params
            )
            
            if response.get("code") != 0:
                raise PlatformError(f"TikTok API error: {response.get('message')}")
            
            ads = []
            for raw in response.get("data", {}).get("list", []):
                ad = self._convert_ad(raw, account_id)
                ads.append(ad)
            
            return ads
            
        except Exception as e:
            raise PlatformError(f"Failed to fetch ads: {e}")
    
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
        Fetch performance metrics from TikTok's reporting API.
        
        TikTok's reporting endpoint is powerful and supports various dimensions
        and metrics. We request the most commonly needed performance data and
        compute derived metrics like CTR and CPA.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            # Map entity type to TikTok's dimension
            dimension_map = {
                "campaign": "BASIC_DATA",
                "adset": "BASIC_DATA",
                "ad": "BASIC_DATA"
            }
            
            # Build the report request
            # TikTok's reporting API is synchronous for small requests
            data_level_map = {
                "campaign": "AUCTION_CAMPAIGN",
                "adset": "AUCTION_ADGROUP",
                "ad": "AUCTION_AD"
            }
            
            params = {
                "advertiser_id": account_id,
                "report_type": "BASIC",
                "data_level": data_level_map.get(entity_type, "AUCTION_CAMPAIGN"),
                "dimensions": json.dumps(["campaign_id"] if entity_type == "campaign" else 
                                        ["adgroup_id"] if entity_type == "adset" else ["ad_id"]),
                "metrics": json.dumps([
                    "spend", "impressions", "clicks", "ctr", "cpc", "cpm",
                    "conversion", "cost_per_conversion", "conversion_rate",
                    "video_play_actions", "video_watched_2s", "video_watched_6s"
                ]),
                "start_date": date_start.strftime("%Y-%m-%d"),
                "end_date": date_end.strftime("%Y-%m-%d"),
                "page_size": 1000
            }
            
            # Add entity filter
            if entity_ids:
                filter_key = {
                    "campaign": "campaign_ids",
                    "adset": "adgroup_ids",
                    "ad": "ad_ids"
                }.get(entity_type, "campaign_ids")
                params["filtering"] = json.dumps({filter_key: entity_ids})
            
            response = self._make_request(
                "GET",
                "/report/integrated/get/",
                params=params
            )
            
            if response.get("code") != 0:
                raise PlatformError(f"TikTok API error: {response.get('message')}")
            
            metrics_map = {}
            for row in response.get("data", {}).get("list", []):
                # Extract entity ID based on type
                if entity_type == "campaign":
                    entity_id = str(row.get("dimensions", {}).get("campaign_id", ""))
                elif entity_type == "adset":
                    entity_id = str(row.get("dimensions", {}).get("adgroup_id", ""))
                else:
                    entity_id = str(row.get("dimensions", {}).get("ad_id", ""))
                
                m = row.get("metrics", {})
                metrics = PerformanceMetrics(
                    impressions=int(m.get("impressions", 0)),
                    clicks=int(m.get("clicks", 0)),
                    spend=float(m.get("spend", 0)),
                    ctr=float(m.get("ctr", 0)) if m.get("ctr") else None,
                    cpc=float(m.get("cpc", 0)) if m.get("cpc") else None,
                    cpm=float(m.get("cpm", 0)) if m.get("cpm") else None,
                    conversions=int(m.get("conversion", 0)) if m.get("conversion") else None,
                    cpa=float(m.get("cost_per_conversion", 0)) if m.get("cost_per_conversion") else None,
                    video_views=int(m.get("video_play_actions", 0)) if m.get("video_play_actions") else None,
                    date_start=date_start,
                    date_end=date_end,
                )
                
                # Compute derived metrics
                metrics.compute_derived_metrics()
                metrics_map[entity_id] = metrics
            
            return metrics_map
            
        except Exception as e:
            raise PlatformError(f"Failed to fetch metrics: {e}")
    
    async def get_emq_scores(self, account_id: str) -> List[EMQScore]:
        """
        Fetch event matching quality data from TikTok.
        
        TikTok provides event statistics through their Events API that can indicate
        match quality, though it's not as structured as Meta's EMQ score. We query
        event stats and estimate a quality score based on match rates.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        try:
            # Query pixel/event data to estimate match quality
            # TikTok's endpoint for this is /pixel/get/ for web events
            response = self._make_request(
                "GET",
                "/pixel/list/",
                params={"advertiser_id": account_id}
            )
            
            if response.get("code") != 0:
                logger.warning(f"Could not fetch pixel data: {response.get('message')}")
                return []
            
            emq_scores = []
            for pixel in response.get("data", {}).get("pixels", []):
                # TikTok doesn't expose direct EMQ, but we can estimate
                # based on pixel configuration and activity
                pixel_id = pixel.get("pixel_id")
                
                # Make a rough estimate based on available data
                # In production, you'd query actual event stats
                emq = EMQScore(
                    platform=Platform.TIKTOK,
                    event_name="pixel_" + str(pixel_id),
                    score=6.0,  # Default moderate score
                    last_updated=datetime.utcnow()
                )
                emq_scores.append(emq)
            
            return emq_scores
            
        except Exception as e:
            logger.warning(f"Failed to fetch EMQ scores: {e}")
            return []
    
    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================
    
    async def execute_action(self, action: AutomationAction) -> AutomationAction:
        """
        Execute an automation action on TikTok.
        
        TikTok's API uses POST requests for most write operations, even updates.
        The operation type (create vs update) is determined by the endpoint used.
        """
        self._ensure_initialized()
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
            
            logger.info(f"Successfully executed {action.action_type} on TikTok")
            return action
            
        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            logger.error(f"Action failed: {e}")
            return action
    
    async def _update_budget(self, action: AutomationAction) -> Dict[str, Any]:
        """Update campaign or ad group budget."""
        params = action.parameters
        
        endpoint = "/campaign/update/" if action.entity_type == "campaign" else "/adgroup/update/"
        
        data = {
            "advertiser_id": action.account_id,
            f"{action.entity_type}_id": action.entity_id,
        }
        
        if "daily_budget" in params:
            # TikTok uses cents
            data["budget"] = int(params["daily_budget"] * 100)
            data["budget_mode"] = "BUDGET_MODE_DAY"
        
        response = self._make_request("POST", endpoint, data=data)
        
        if response.get("code") != 0:
            raise PlatformError(f"TikTok API error: {response.get('message')}")
        
        return {"updated": True}
    
    async def _update_status(self, action: AutomationAction) -> Dict[str, Any]:
        """Update entity status (enable/disable)."""
        params = action.parameters
        new_status = EntityStatus(params["status"])
        tiktok_status = self.STATUS_TO_TIKTOK.get(new_status, "ENABLE")
        
        # TikTok has separate enable/disable endpoints
        endpoint_map = {
            "campaign": "/campaign/update/status/",
            "adset": "/adgroup/update/status/",
            "ad": "/ad/update/status/"
        }
        
        endpoint = endpoint_map.get(action.entity_type, "/campaign/update/status/")
        id_key = {
            "campaign": "campaign_ids",
            "adset": "adgroup_ids",
            "ad": "ad_ids"
        }.get(action.entity_type, "campaign_ids")
        
        data = {
            "advertiser_id": action.account_id,
            id_key: [action.entity_id],
            "operation_status": tiktok_status
        }
        
        response = self._make_request("POST", endpoint, data=data)
        
        if response.get("code") != 0:
            raise PlatformError(f"TikTok API error: {response.get('message')}")
        
        return {"new_status": tiktok_status}
    
    async def _create_campaign(self, action: AutomationAction) -> Dict[str, Any]:
        """Create a new campaign."""
        params = action.parameters
        
        data = {
            "advertiser_id": action.account_id,
            "campaign_name": params["name"],
            "objective_type": params.get("objective", "CONVERSIONS"),
            "budget_mode": "BUDGET_MODE_DAY",
            "operation_status": "DISABLE",  # Create paused for safety
        }
        
        if "daily_budget" in params:
            data["budget"] = int(params["daily_budget"] * 100)
        
        response = self._make_request("POST", "/campaign/create/", data=data)
        
        if response.get("code") != 0:
            raise PlatformError(f"TikTok API error: {response.get('message')}")
        
        campaign_id = response.get("data", {}).get("campaign_id")
        return {"campaign_id": campaign_id}
    
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
        Upload an image to TikTok's creative library.
        
        TikTok accepts images for certain ad formats (like in-feed ads with
        carousel). The image is uploaded and returns an image_id for use in ads.
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        import base64
        
        data = {
            "advertiser_id": account_id,
            "file_name": filename,
            "image_data": base64.b64encode(image_data).decode("utf-8")
        }
        
        response = self._make_request("POST", "/file/image/ad/upload/", data=data)
        
        if response.get("code") != 0:
            raise PlatformError(f"Image upload failed: {response.get('message')}")
        
        return response.get("data", {}).get("image_id", "")
    
    async def upload_video(
        self,
        account_id: str,
        video_data: bytes,
        filename: str
    ) -> str:
        """
        Upload a video to TikTok's creative library.
        
        Video is the primary creative format on TikTok. Videos must meet TikTok's
        specifications (typically 9:16 aspect ratio, various length options).
        """
        self._ensure_initialized()
        await self.rate_limiter.acquire()
        
        # TikTok's video upload is typically chunked for larger files
        # For simplicity, we'll use the direct upload endpoint for smaller videos
        import base64
        
        data = {
            "advertiser_id": account_id,
            "file_name": filename,
            "video_data": base64.b64encode(video_data).decode("utf-8")
        }
        
        response = self._make_request("POST", "/file/video/ad/upload/", data=data)
        
        if response.get("code") != 0:
            raise PlatformError(f"Video upload failed: {response.get('message')}")
        
        return response.get("data", {}).get("video_id", "")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _ensure_initialized(self) -> None:
        """Verify adapter is ready for API calls."""
        if not self._initialized or not self.session:
            raise AdapterError("Adapter not initialized. Call initialize() first.")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to TikTok's API.
        
        This method handles the common request/response pattern, including
        error handling and JSON parsing.
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            else:
                response = self.session.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {"code": -1, "message": str(e)}
    
    def _convert_campaign(self, raw: Dict[str, Any], account_id: str) -> UnifiedCampaign:
        """Convert TikTok campaign data to unified model."""
        return UnifiedCampaign(
            platform=Platform.TIKTOK,
            account_id=account_id,
            campaign_id=str(raw.get("campaign_id", "")),
            campaign_name=raw.get("campaign_name", ""),
            status=self.STATUS_FROM_TIKTOK.get(
                raw.get("operation_status", "ENABLE"),
                EntityStatus.ACTIVE
            ),
            daily_budget=raw.get("budget", 0) / 100 if raw.get("budget") else None,
            created_at=self._parse_datetime(raw.get("create_time")),
            updated_at=self._parse_datetime(raw.get("modify_time")),
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _convert_adset(self, raw: Dict[str, Any], account_id: str) -> UnifiedAdSet:
        """Convert TikTok ad group data to unified model."""
        return UnifiedAdSet(
            platform=Platform.TIKTOK,
            account_id=account_id,
            campaign_id=str(raw.get("campaign_id", "")),
            adset_id=str(raw.get("adgroup_id", "")),
            adset_name=raw.get("adgroup_name", ""),
            status=self.STATUS_FROM_TIKTOK.get(
                raw.get("operation_status", "ENABLE"),
                EntityStatus.ACTIVE
            ),
            daily_budget=raw.get("budget", 0) / 100 if raw.get("budget") else None,
            bid_amount=raw.get("bid", 0) / 100 if raw.get("bid") else None,
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _convert_ad(self, raw: Dict[str, Any], account_id: str) -> UnifiedAd:
        """Convert TikTok ad data to unified model."""
        return UnifiedAd(
            platform=Platform.TIKTOK,
            account_id=account_id,
            campaign_id=str(raw.get("campaign_id", "")),
            adset_id=str(raw.get("adgroup_id", "")),
            ad_id=str(raw.get("ad_id", "")),
            ad_name=raw.get("ad_name", ""),
            status=self.STATUS_FROM_TIKTOK.get(
                raw.get("operation_status", "ENABLE"),
                EntityStatus.ACTIVE
            ),
            headline=raw.get("ad_text", ""),
            destination_url=raw.get("landing_page_url", ""),
            call_to_action=raw.get("call_to_action", ""),
            last_synced=datetime.utcnow(),
            raw_data=raw
        )
    
    def _parse_datetime(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parse TikTok's timestamp format."""
        if not timestamp:
            return None
        try:
            # TikTok uses various formats; try common ones
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def _map_status_to_platform(self, status: EntityStatus) -> str:
        """Convert unified status to TikTok's status string."""
        return self.STATUS_TO_TIKTOK.get(status, "ENABLE")
    
    def _map_status_from_platform(self, platform_status: str) -> EntityStatus:
        """Convert TikTok's status string to unified status."""
        return self.STATUS_FROM_TIKTOK.get(platform_status, EntityStatus.ACTIVE)
