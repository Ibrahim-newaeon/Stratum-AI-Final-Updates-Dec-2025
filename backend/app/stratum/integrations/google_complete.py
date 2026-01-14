"""
Stratum AI: Google Ads Complete Integration
===========================================

Google Ads is fundamentally different from Meta/TikTok/Snapchat:

1. NO WEBHOOKS - Google doesn't push data, you must poll
2. GAQL - Google Ads Query Language (SQL-like) for data fetching
3. Multiple conversion methods with different use cases
4. Protobuf-based API (strongly typed)

This module provides:
- Change History polling (detect campaign/ad changes)
- Offline Conversion Import (for CRM/phone sales)
- Enhanced Conversions (for better web attribution)
- GA4 Measurement Protocol (real-time event streaming)

Google Conversion Methods Comparison
------------------------------------

| Method | Use Case | Latency | EMQ Equivalent |
|--------|----------|---------|----------------|
| gtag (browser) | Standard web tracking | Real-time | Low-Medium |
| Enhanced Conversions | Web with user data | Real-time | High |
| Offline Conversion Import | CRM, phone sales | Up to 24h | High |
| GA4 Measurement Protocol | Server-side events | Real-time | Medium-High |
| Store Sales Direct | In-store purchases | 1-3 days | High |

For Stratum's Trust-Gated Autopilot, we primarily use:
1. Enhanced Conversions - for web purchases
2. Offline Conversion Import - for WhatsApp/phone orders
3. GA4 Measurement Protocol - for real-time funnel events
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger("stratum.google")


# =============================================================================
# GOOGLE ADS CHANGE HISTORY (Replaces Webhooks)
# =============================================================================

class ChangeEventType(str, Enum):
    """Types of changes tracked in Google Ads."""
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    CAMPAIGN_UPDATED = "CAMPAIGN_UPDATED"
    CAMPAIGN_REMOVED = "CAMPAIGN_REMOVED"
    AD_GROUP_CREATED = "AD_GROUP_CREATED"
    AD_GROUP_UPDATED = "AD_GROUP_UPDATED"
    AD_GROUP_REMOVED = "AD_GROUP_REMOVED"
    AD_CREATED = "AD_CREATED"
    AD_UPDATED = "AD_UPDATED"
    AD_REMOVED = "AD_REMOVED"
    BUDGET_UPDATED = "BUDGET_UPDATED"
    BID_UPDATED = "BID_UPDATED"
    STATUS_CHANGED = "STATUS_CHANGED"


@dataclass
class ChangeEvent:
    """A detected change in Google Ads."""
    change_type: ChangeEventType
    resource_type: str  # campaign, ad_group, ad, etc.
    resource_id: str
    resource_name: str
    changed_fields: List[str]
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    change_time: datetime = field(default_factory=datetime.utcnow)
    user_email: Optional[str] = None  # Who made the change


class GoogleAdsChangeHistory:
    """
    Poll Google Ads Change History to detect account changes.

    This replaces webhooks - run on a schedule (every 5-15 minutes).

    Usage:
        poller = GoogleAdsChangeHistory(google_ads_client, customer_id)

        # Get changes since last poll
        changes = await poller.get_changes(since=last_poll_time)

        for change in changes:
            if change.change_type == ChangeEventType.BUDGET_UPDATED:
                await handle_budget_change(change)
    """

    def __init__(self, client: Any, customer_id: str):
        """
        Initialize Change History poller.

        Args:
            client: Initialized GoogleAdsClient
            customer_id: Google Ads customer ID (no dashes)
        """
        self.client = client
        self.customer_id = customer_id.replace("-", "")
        self._last_poll_time: Optional[datetime] = None

    async def get_changes(
        self,
        since: Optional[datetime] = None,
        resource_types: Optional[List[str]] = None
    ) -> List[ChangeEvent]:
        """
        Get account changes since a given time.

        Args:
            since: Start time (default: last poll time or 1 hour ago)
            resource_types: Filter by resource type (campaign, ad_group, ad)

        Returns:
            List of ChangeEvent objects
        """
        if since is None:
            since = self._last_poll_time or (datetime.utcnow() - timedelta(hours=1))

        # Build GAQL query for change_event
        query = f"""
            SELECT
                change_event.change_date_time,
                change_event.change_resource_type,
                change_event.change_resource_name,
                change_event.changed_fields,
                change_event.client_type,
                change_event.feed,
                change_event.new_resource,
                change_event.old_resource,
                change_event.resource_change_operation,
                change_event.user_email
            FROM change_event
            WHERE change_event.change_date_time >= '{since.strftime("%Y-%m-%d %H:%M:%S")}'
            ORDER BY change_event.change_date_time DESC
            LIMIT 1000
        """

        ga_service = self.client.get_service("GoogleAdsService")

        changes = []

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)

            for row in response:
                event = row.change_event

                # Filter by resource type if specified
                resource_type = str(event.change_resource_type).split(".")[-1].lower()
                if resource_types and resource_type not in resource_types:
                    continue

                # Determine change type
                operation = str(event.resource_change_operation).split(".")[-1]
                change_type = self._map_change_type(resource_type, operation)

                change = ChangeEvent(
                    change_type=change_type,
                    resource_type=resource_type,
                    resource_id=self._extract_id(event.change_resource_name),
                    resource_name=event.change_resource_name,
                    changed_fields=list(event.changed_fields.paths) if event.changed_fields else [],
                    change_time=datetime.fromisoformat(str(event.change_date_time).replace(" ", "T")),
                    user_email=event.user_email if event.user_email else None
                )

                changes.append(change)

            self._last_poll_time = datetime.utcnow()
            logger.info(f"Google Ads: Found {len(changes)} changes since {since}")

        except Exception as e:
            logger.error(f"Error polling Google Ads changes: {e}")

        return changes

    def _map_change_type(self, resource_type: str, operation: str) -> ChangeEventType:
        """Map Google's change operation to our enum."""
        type_map = {
            ("campaign", "CREATE"): ChangeEventType.CAMPAIGN_CREATED,
            ("campaign", "UPDATE"): ChangeEventType.CAMPAIGN_UPDATED,
            ("campaign", "REMOVE"): ChangeEventType.CAMPAIGN_REMOVED,
            ("ad_group", "CREATE"): ChangeEventType.AD_GROUP_CREATED,
            ("ad_group", "UPDATE"): ChangeEventType.AD_GROUP_UPDATED,
            ("ad_group", "REMOVE"): ChangeEventType.AD_GROUP_REMOVED,
            ("ad", "CREATE"): ChangeEventType.AD_CREATED,
            ("ad", "UPDATE"): ChangeEventType.AD_UPDATED,
            ("ad", "REMOVE"): ChangeEventType.AD_REMOVED,
        }
        return type_map.get((resource_type, operation), ChangeEventType.CAMPAIGN_UPDATED)

    def _extract_id(self, resource_name: str) -> str:
        """Extract ID from resource name like 'customers/123/campaigns/456'."""
        parts = resource_name.split("/")
        return parts[-1] if parts else ""

    async def watch_for_changes(
        self,
        callback,
        poll_interval: int = 300,  # 5 minutes
        resource_types: Optional[List[str]] = None
    ):
        """
        Continuously poll for changes and call callback.

        Args:
            callback: Async function to call with changes
            poll_interval: Seconds between polls
            resource_types: Filter by resource type
        """
        import asyncio

        logger.info(f"Starting Google Ads change watcher (interval: {poll_interval}s)")

        while True:
            try:
                changes = await self.get_changes(resource_types=resource_types)

                if changes:
                    await callback(changes)

            except Exception as e:
                logger.error(f"Change watcher error: {e}")

            await asyncio.sleep(poll_interval)


# =============================================================================
# OFFLINE CONVERSION IMPORT
# =============================================================================

@dataclass
class OfflineConversion:
    """
    An offline conversion to upload to Google Ads.

    Use for:
    - CRM conversions (lead became customer)
    - Phone orders
    - WhatsApp orders
    - In-store purchases (if you have customer data)
    """
    # Required
    conversion_action_id: str
    conversion_time: datetime

    # User identification (at least one required)
    gclid: Optional[str] = None  # Best - from ?gclid= URL parameter
    gbraid: Optional[str] = None  # iOS app tracking
    wbraid: Optional[str] = None  # Web-to-app

    # Enhanced Conversions data (hashed)
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Conversion details
    conversion_value: Optional[float] = None
    currency_code: str = "USD"
    order_id: Optional[str] = None

    # Your internal ID
    external_attribution_data: Optional[str] = None


class GoogleOfflineConversions:
    """
    Upload offline conversions to Google Ads.

    This is CRITICAL for:
    1. WhatsApp orders (no gclid but have phone/email)
    2. Phone orders
    3. CRM conversions (lead → customer)
    4. In-store with loyalty data

    Example:
        uploader = GoogleOfflineConversions(client, customer_id)

        # Upload a WhatsApp purchase
        result = await uploader.upload_conversion(OfflineConversion(
            conversion_action_id="123456789",
            conversion_time=datetime.utcnow(),
            email="customer@example.com",
            phone="+966501234567",
            conversion_value=4500.0,
            currency_code="SAR",
            order_id="ORD-12345"
        ))
    """

    def __init__(self, client: Any, customer_id: str):
        """
        Initialize offline conversions uploader.

        Args:
            client: Initialized GoogleAdsClient
            customer_id: Google Ads customer ID
        """
        self.client = client
        self.customer_id = customer_id.replace("-", "")

    async def upload_conversion(
        self,
        conversion: OfflineConversion
    ) -> Dict[str, Any]:
        """
        Upload a single offline conversion.

        Returns:
            Dict with upload result
        """
        return await self.upload_conversions([conversion])

    async def upload_conversions(
        self,
        conversions: List[OfflineConversion]
    ) -> Dict[str, Any]:
        """
        Upload multiple offline conversions in batch.

        Google recommends batching for efficiency.
        Maximum 2,000 conversions per request.
        """
        conversion_upload_service = self.client.get_service("ConversionUploadService")

        click_conversions = []

        for conv in conversions:
            click_conversion = self.client.get_type("ClickConversion")

            # Conversion action
            click_conversion.conversion_action = (
                f"customers/{self.customer_id}/conversionActions/{conv.conversion_action_id}"
            )

            # Conversion time (required format)
            click_conversion.conversion_date_time = conv.conversion_time.strftime(
                "%Y-%m-%d %H:%M:%S+00:00"
            )

            # Click identifier (best match)
            if conv.gclid:
                click_conversion.gclid = conv.gclid
            elif conv.gbraid:
                click_conversion.gbraid = conv.gbraid
            elif conv.wbraid:
                click_conversion.wbraid = conv.wbraid

            # Value
            if conv.conversion_value is not None:
                click_conversion.conversion_value = conv.conversion_value
            click_conversion.currency_code = conv.currency_code

            # Order ID (for deduplication)
            if conv.order_id:
                click_conversion.order_id = conv.order_id

            # Enhanced Conversions - User Identifiers
            user_identifiers = self._build_user_identifiers(conv)
            if user_identifiers:
                click_conversion.user_identifiers.extend(user_identifiers)

            click_conversions.append(click_conversion)

        # Upload request
        request = self.client.get_type("UploadClickConversionsRequest")
        request.customer_id = self.customer_id
        request.conversions.extend(click_conversions)
        request.partial_failure = True

        try:
            response = conversion_upload_service.upload_click_conversions(request=request)

            result = {
                "uploaded": len(response.results),
                "errors": [],
                "partial_failure": None
            }

            # Check for partial failures
            if response.partial_failure_error:
                result["partial_failure"] = str(response.partial_failure_error)

                # Parse individual errors
                failure_error = response.partial_failure_error
                for error in getattr(failure_error, "errors", []):
                    result["errors"].append({
                        "message": str(error.message),
                        "location": str(error.location) if error.location else None
                    })

            logger.info(f"Google Offline Conversions: Uploaded {result['uploaded']}")
            return result

        except Exception as e:
            logger.error(f"Offline conversion upload failed: {e}")
            return {"uploaded": 0, "errors": [str(e)]}

    def _build_user_identifiers(
        self,
        conv: OfflineConversion
    ) -> List[Any]:
        """Build user identifier objects for Enhanced Conversions."""
        identifiers = []

        # Email (hashed)
        if conv.email:
            identifier = self.client.get_type("UserIdentifier")
            identifier.hashed_email = self._hash_value(conv.email.lower().strip())
            identifiers.append(identifier)

        # Phone (hashed, E.164 format)
        if conv.phone:
            identifier = self.client.get_type("UserIdentifier")
            phone_normalized = self._normalize_phone(conv.phone)
            identifier.hashed_phone_number = self._hash_value(phone_normalized)
            identifiers.append(identifier)

        # Address (hashed)
        if conv.first_name or conv.last_name or conv.street_address:
            identifier = self.client.get_type("UserIdentifier")
            address = identifier.address_info

            if conv.first_name:
                address.hashed_first_name = self._hash_value(conv.first_name.lower().strip())
            if conv.last_name:
                address.hashed_last_name = self._hash_value(conv.last_name.lower().strip())
            if conv.street_address:
                address.hashed_street_address = self._hash_value(conv.street_address.lower().strip())
            if conv.city:
                address.city = conv.city
            if conv.state:
                address.state = conv.state
            if conv.postal_code:
                address.postal_code = conv.postal_code
            if conv.country:
                address.country_code = conv.country

            identifiers.append(identifier)

        return identifiers

    def _hash_value(self, value: str) -> str:
        """SHA256 hash a value."""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to E.164 format."""
        import re
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:  # US without country code
            digits = '1' + digits
        return '+' + digits


# =============================================================================
# GA4 MEASUREMENT PROTOCOL (Real-time Events)
# =============================================================================

class GA4MeasurementProtocol:
    """
    Send events to GA4 in real-time via Measurement Protocol.

    This is for server-side tracking of web events when you can't use gtag.
    Events are sent directly to Google Analytics, which then flows to
    Google Ads for conversion tracking (if linked).

    Use Cases:
    - Server-side event tracking
    - Mobile app events (when Firebase isn't available)
    - IoT/offline device events
    - Hybrid tracking (supplement browser data)

    Note: For conversion attribution in Google Ads, Enhanced Conversions
    or Offline Import provides better match rates than MP.

    Example:
        mp = GA4MeasurementProtocol(
            measurement_id="G-XXXXXXXXXX",
            api_secret="your_secret"
        )

        await mp.send_event(
            client_id="user_123",
            event_name="purchase",
            params={
                "currency": "SAR",
                "value": 4500.0,
                "transaction_id": "ORD-12345",
                "items": [{"item_id": "SKU123", "item_name": "Sofa"}]
            }
        )
    """

    ENDPOINT = "https://www.google-analytics.com/mp/collect"
    DEBUG_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"

    def __init__(
        self,
        measurement_id: str,
        api_secret: str,
        debug: bool = False
    ):
        """
        Initialize Measurement Protocol client.

        Args:
            measurement_id: GA4 Measurement ID (G-XXXXXXXXXX)
            api_secret: MP API secret (from GA4 Admin)
            debug: Use debug endpoint for validation
        """
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.endpoint = self.DEBUG_ENDPOINT if debug else self.ENDPOINT

    async def send_event(
        self,
        client_id: str,
        event_name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        timestamp_micros: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a single event to GA4.

        Args:
            client_id: Unique client identifier (required)
            event_name: Event name (e.g., 'purchase', 'add_to_cart')
            params: Event parameters
            user_id: Your internal user ID (for cross-device)
            user_properties: User-scoped properties
            timestamp_micros: Event timestamp in microseconds
        """
        import requests

        url = f"{self.endpoint}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

        payload = {
            "client_id": client_id,
            "events": [{
                "name": event_name,
                "params": params or {}
            }]
        }

        if user_id:
            payload["user_id"] = user_id

        if user_properties:
            payload["user_properties"] = {
                k: {"value": v} for k, v in user_properties.items()
            }

        if timestamp_micros:
            payload["timestamp_micros"] = timestamp_micros

        try:
            response = requests.post(url, json=payload)

            # MP returns 204 on success, 200 with validation on debug
            if response.status_code == 204:
                logger.debug(f"GA4 MP: Event '{event_name}' sent")
                return {"success": True}
            elif response.status_code == 200:
                # Debug endpoint returns validation info
                return {"success": True, "validation": response.json()}
            else:
                logger.warning(f"GA4 MP: Unexpected status {response.status_code}")
                return {"success": False, "status": response.status_code}

        except Exception as e:
            logger.error(f"GA4 MP error: {e}")
            return {"success": False, "error": str(e)}

    async def send_purchase(
        self,
        client_id: str,
        transaction_id: str,
        value: float,
        currency: str,
        items: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method for purchase events."""
        return await self.send_event(
            client_id=client_id,
            event_name="purchase",
            params={
                "transaction_id": transaction_id,
                "value": value,
                "currency": currency,
                "items": items
            },
            user_id=user_id
        )

    async def send_add_to_cart(
        self,
        client_id: str,
        items: List[Dict[str, Any]],
        value: Optional[float] = None,
        currency: str = "USD",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method for add_to_cart events."""
        params = {"items": items, "currency": currency}
        if value is not None:
            params["value"] = value

        return await self.send_event(
            client_id=client_id,
            event_name="add_to_cart",
            params=params,
            user_id=user_id
        )

    async def send_view_item(
        self,
        client_id: str,
        items: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method for view_item events."""
        return await self.send_event(
            client_id=client_id,
            event_name="view_item",
            params={"items": items},
            user_id=user_id
        )


# =============================================================================
# UNIFIED GOOGLE INTEGRATION
# =============================================================================

class GoogleAdsIntegration:
    """
    Unified Google Ads integration combining all methods.

    This class provides a single interface for:
    1. Polling changes (replaces webhooks)
    2. Uploading offline conversions
    3. Sending GA4 events
    4. Enhanced conversions (via adapter)

    Example:
        google = GoogleAdsIntegration(
            client=google_ads_client,
            customer_id="1234567890",
            ga4_measurement_id="G-XXXXXXXXXX",
            ga4_api_secret="secret"
        )

        # Start change watcher
        await google.start_change_watcher(callback=handle_changes)

        # Upload WhatsApp conversion
        await google.track_conversion(
            conversion_action_id="123",
            email="customer@example.com",
            phone="+966501234567",
            value=4500.0,
            currency="SAR",
            order_id="ORD-123"
        )

        # Send real-time event
        await google.track_event(
            client_id="user_123",
            event_name="add_to_cart",
            params={"items": [...]}
        )
    """

    def __init__(
        self,
        client: Any,
        customer_id: str,
        ga4_measurement_id: Optional[str] = None,
        ga4_api_secret: Optional[str] = None
    ):
        self.client = client
        self.customer_id = customer_id.replace("-", "")

        # Initialize components
        self.change_history = GoogleAdsChangeHistory(client, customer_id)
        self.offline_conversions = GoogleOfflineConversions(client, customer_id)

        if ga4_measurement_id and ga4_api_secret:
            self.ga4 = GA4MeasurementProtocol(ga4_measurement_id, ga4_api_secret)
        else:
            self.ga4 = None

    async def start_change_watcher(
        self,
        callback,
        poll_interval: int = 300
    ):
        """Start watching for account changes."""
        await self.change_history.watch_for_changes(
            callback=callback,
            poll_interval=poll_interval
        )

    async def get_recent_changes(
        self,
        hours: int = 1
    ) -> List[ChangeEvent]:
        """Get recent account changes."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return await self.change_history.get_changes(since=since)

    async def track_conversion(
        self,
        conversion_action_id: str,
        value: float,
        currency: str = "USD",
        order_id: Optional[str] = None,
        gclid: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        conversion_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Track an offline conversion.

        Use for WhatsApp orders, phone orders, CRM conversions.
        """
        conversion = OfflineConversion(
            conversion_action_id=conversion_action_id,
            conversion_time=conversion_time or datetime.utcnow(),
            gclid=gclid,
            email=email,
            phone=phone,
            conversion_value=value,
            currency_code=currency,
            order_id=order_id
        )

        return await self.offline_conversions.upload_conversion(conversion)

    async def track_event(
        self,
        client_id: str,
        event_name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send real-time event to GA4.

        Use for funnel events (view_item, add_to_cart, etc.)
        """
        if not self.ga4:
            logger.warning("GA4 not configured, skipping event")
            return {"success": False, "error": "GA4 not configured"}

        return await self.ga4.send_event(
            client_id=client_id,
            event_name=event_name,
            params=params,
            user_id=user_id
        )


# =============================================================================
# GOOGLE ADS RECOMMENDATIONS (Bonus - AI Suggestions)
# =============================================================================

class GoogleAdsRecommendations:
    """
    Fetch Google Ads recommendations (AI-powered suggestions).

    Google provides automated recommendations for:
    - Budget changes
    - Bid adjustments
    - New keywords
    - Ad improvements
    - Targeting expansions

    These can feed into Stratum's Trust Gate for approval.
    """

    def __init__(self, client: Any, customer_id: str):
        self.client = client
        self.customer_id = customer_id.replace("-", "")

    async def get_recommendations(
        self,
        recommendation_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch active recommendations.

        Args:
            recommendation_types: Filter by type (e.g., "CAMPAIGN_BUDGET")

        Returns:
            List of recommendation details
        """
        ga_service = self.client.get_service("GoogleAdsService")

        query = """
            SELECT
                recommendation.resource_name,
                recommendation.type,
                recommendation.impact.base_metrics.impressions,
                recommendation.impact.base_metrics.clicks,
                recommendation.impact.base_metrics.cost_micros,
                recommendation.impact.potential_metrics.impressions,
                recommendation.impact.potential_metrics.clicks,
                recommendation.impact.potential_metrics.cost_micros,
                recommendation.campaign_budget_recommendation.current_budget_amount_micros,
                recommendation.campaign_budget_recommendation.recommended_budget_amount_micros,
                recommendation.campaign
            FROM recommendation
            WHERE recommendation.dismissed = FALSE
        """

        recommendations = []

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)

            for row in response:
                rec = row.recommendation
                rec_type = str(rec.type).split(".")[-1]

                if recommendation_types and rec_type not in recommendation_types:
                    continue

                rec_data = {
                    "resource_name": rec.resource_name,
                    "type": rec_type,
                    "campaign": rec.campaign,
                    "impact": {
                        "current": {
                            "impressions": rec.impact.base_metrics.impressions,
                            "clicks": rec.impact.base_metrics.clicks,
                            "cost": rec.impact.base_metrics.cost_micros / 1_000_000
                        },
                        "potential": {
                            "impressions": rec.impact.potential_metrics.impressions,
                            "clicks": rec.impact.potential_metrics.clicks,
                            "cost": rec.impact.potential_metrics.cost_micros / 1_000_000
                        }
                    }
                }

                # Budget recommendation details
                if rec.campaign_budget_recommendation.current_budget_amount_micros:
                    rec_data["budget_recommendation"] = {
                        "current": rec.campaign_budget_recommendation.current_budget_amount_micros / 1_000_000,
                        "recommended": rec.campaign_budget_recommendation.recommended_budget_amount_micros / 1_000_000
                    }

                recommendations.append(rec_data)

            logger.info(f"Google Ads: Found {len(recommendations)} recommendations")

        except Exception as e:
            logger.error(f"Error fetching recommendations: {e}")

        return recommendations

    async def apply_recommendation(
        self,
        recommendation_resource_name: str
    ) -> Dict[str, Any]:
        """
        Apply a recommendation (requires Trust Gate approval in Stratum).

        Args:
            recommendation_resource_name: The recommendation to apply
        """
        recommendation_service = self.client.get_service("RecommendationService")

        operation = self.client.get_type("ApplyRecommendationOperation")
        operation.resource_name = recommendation_resource_name

        try:
            response = recommendation_service.apply_recommendation(
                customer_id=self.customer_id,
                operations=[operation]
            )

            logger.info(f"Applied recommendation: {recommendation_resource_name}")
            return {"success": True, "results": len(response.results)}

        except Exception as e:
            logger.error(f"Failed to apply recommendation: {e}")
            return {"success": False, "error": str(e)}
