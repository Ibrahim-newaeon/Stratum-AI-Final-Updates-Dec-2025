"""
Stratum AI: Conversions API Module
==================================

This module handles server-side conversion event passing to advertising platforms.
Server-side tracking (also known as CAPI - Conversions API) is CRITICAL for:

1. **Improving EMQ Scores**: By sending hashed user data (email, phone) with events,
   platforms can better match conversions to ad interactions.

2. **iOS 14+ Resilience**: Browser-based pixels are blocked by iOS ATT and browser
   privacy features. Server-side events bypass these restrictions.

3. **Data Accuracy**: Server-side events don't rely on JavaScript execution,
   eliminating issues with ad blockers and slow page loads.

Platform-Specific APIs
----------------------

- **Meta**: Conversions API (CAPI) - Most mature, sends to /pixel_id/events
- **Google**: Enhanced Conversions - Uses gtag or Measurement Protocol
- **TikTok**: Events API - Similar to Meta CAPI
- **Snapchat**: Conversions API - REST-based event submission
- **WhatsApp**: Conversions flow through Meta CAPI with special parameters

Data Requirements for High EMQ
------------------------------

To achieve EMQ scores of 8+, you should pass:
- Hashed email (SHA256, lowercase, trimmed)
- Hashed phone (SHA256, E.164 format)
- Client IP address
- User agent
- Click ID (fbclid, gclid, ttclid, etc.)
- External ID (your customer ID)

The more identifiers you pass, the higher your match rate will be.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import requests

logger = logging.getLogger("stratum.conversions")


class EventType(str, Enum):
    """Standard conversion event types across platforms."""

    PAGE_VIEW = "PageView"
    VIEW_CONTENT = "ViewContent"
    ADD_TO_CART = "AddToCart"
    INITIATE_CHECKOUT = "InitiateCheckout"
    ADD_PAYMENT_INFO = "AddPaymentInfo"
    PURCHASE = "Purchase"
    LEAD = "Lead"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    CONTACT = "Contact"
    SUBSCRIBE = "Subscribe"
    CUSTOM = "Custom"


@dataclass
class UserData:
    """
    User identification data for conversion matching.

    All PII fields are automatically hashed before being sent to platforms.
    Pass raw values - hashing is handled internally.

    For best EMQ scores, provide as many fields as possible:
    - email + phone = ~70% match rate
    - email + phone + external_id = ~85% match rate
    - All fields = ~95% match rate
    """

    # PII fields (will be hashed)
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYYMMDD format
    gender: Optional[str] = None  # 'm' or 'f'

    # Non-PII identifiers
    external_id: Optional[str] = None  # Your customer ID
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None

    # Click IDs from URL parameters
    fbc: Optional[str] = None  # Facebook click ID (fbclid)
    fbp: Optional[str] = None  # Facebook browser ID (_fbp cookie)
    gclid: Optional[str] = None  # Google click ID
    ttclid: Optional[str] = None  # TikTok click ID
    sccid: Optional[str] = None  # Snapchat click ID

    def get_hashed(self, field_name: str) -> Optional[str]:
        """Get SHA256 hash of a field value."""
        value = getattr(self, field_name, None)
        if not value:
            return None

        # Normalize before hashing
        normalized = self._normalize(field_name, value)
        if not normalized:
            return None

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _normalize(self, field_name: str, value: str) -> str:
        """Normalize field values before hashing."""
        value = value.strip().lower()

        if field_name == "email":
            # Remove dots from gmail local part, lowercase
            return value

        elif field_name == "phone":
            # Remove all non-digits, ensure E.164 format
            digits = re.sub(r"\D", "", value)
            # Add country code if missing (assume US)
            if len(digits) == 10:
                digits = "1" + digits
            return digits

        elif field_name in ["first_name", "last_name", "city"]:
            # Lowercase, remove special characters
            return re.sub(r"[^a-z]", "", value)

        elif field_name == "state":
            # Two-letter state code
            return value[:2]

        elif field_name == "zip_code":
            # First 5 digits only
            return re.sub(r"\D", "", value)[:5]

        elif field_name == "country":
            # Two-letter country code
            return value[:2]

        return value


@dataclass
class ConversionEvent:
    """
    A conversion event to be sent to advertising platforms.

    Example:
        event = ConversionEvent(
            event_name=EventType.PURCHASE,
            event_time=datetime.utcnow(),
            user_data=UserData(
                email="customer@example.com",
                phone="+1234567890",
                external_id="cust_123"
            ),
            custom_data={
                "currency": "USD",
                "value": 99.99,
                "content_ids": ["SKU123"],
                "content_type": "product"
            },
            event_source_url="https://mysite.com/checkout/success"
        )
    """

    event_name: EventType
    event_time: datetime
    user_data: UserData

    # Event details
    custom_data: dict[str, Any] = field(default_factory=dict)
    event_source_url: Optional[str] = None
    event_id: Optional[str] = None  # For deduplication
    action_source: str = "website"  # website, app, email, phone_call, chat, etc.

    # Platform-specific
    opt_out: bool = False  # User opted out of tracking

    def __post_init__(self):
        """Generate event_id if not provided."""
        if not self.event_id:
            # Create deterministic ID for deduplication
            id_string = f"{self.event_name.value}_{self.event_time.isoformat()}_{self.user_data.external_id or ''}"
            self.event_id = hashlib.md5(id_string.encode()).hexdigest()[:16]


class MetaConversionsAPI:
    """
    Meta (Facebook/Instagram) Conversions API client.

    The Meta CAPI is the most mature server-side tracking solution. Events
    sent through CAPI are matched against Meta's user database to attribute
    conversions to ad interactions.

    Setup Requirements:
    1. Create a Pixel in Events Manager
    2. Generate a CAPI access token
    3. Configure event deduplication with browser pixel

    Usage:
        capi = MetaConversionsAPI(
            pixel_id="123456789",
            access_token="EAAxxxxxxx"
        )

        result = await capi.send_event(event)
        print(f"Events received: {result['events_received']}")
    """

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, pixel_id: str, access_token: str, test_event_code: Optional[str] = None):
        """
        Initialize Meta CAPI client.

        Args:
            pixel_id: Your Meta Pixel ID
            access_token: CAPI access token from Events Manager
            test_event_code: Optional test code for Events Manager testing
        """
        self.pixel_id = pixel_id
        self.access_token = access_token
        self.test_event_code = test_event_code

    async def send_event(self, event: ConversionEvent) -> dict[str, Any]:
        """Send a single conversion event to Meta."""
        return await self.send_events([event])

    async def send_events(self, events: list[ConversionEvent]) -> dict[str, Any]:
        """
        Send multiple conversion events to Meta CAPI.

        Returns:
            Dict with 'events_received' count and any errors
        """
        payload = {
            "data": [self._format_event(e) for e in events],
            "access_token": self.access_token,
        }

        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code

        url = f"{self.BASE_URL}/{self.pixel_id}/events"

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Meta CAPI: {result.get('events_received', 0)} events received")
            return result

        except requests.RequestException as e:
            logger.error(f"Meta CAPI error: {e}")
            raise

    def _format_event(self, event: ConversionEvent) -> dict[str, Any]:
        """Format event for Meta CAPI."""
        data = {
            "event_name": event.event_name.value,
            "event_time": int(event.event_time.timestamp()),
            "event_id": event.event_id,
            "action_source": event.action_source,
            "user_data": self._format_user_data(event.user_data),
        }

        if event.event_source_url:
            data["event_source_url"] = event.event_source_url

        if event.custom_data:
            data["custom_data"] = event.custom_data

        if event.opt_out:
            data["opt_out"] = True

        return data

    def _format_user_data(self, user_data: UserData) -> dict[str, Any]:
        """Format and hash user data for Meta."""
        data = {}

        # Hashed PII fields
        hash_fields = [
            ("em", "email"),
            ("ph", "phone"),
            ("fn", "first_name"),
            ("ln", "last_name"),
            ("ct", "city"),
            ("st", "state"),
            ("zp", "zip_code"),
            ("country", "country"),
            ("db", "date_of_birth"),
            ("ge", "gender"),
        ]

        for api_name, field_name in hash_fields:
            hashed = user_data.get_hashed(field_name)
            if hashed:
                data[api_name] = hashed

        # Non-hashed fields
        if user_data.external_id:
            data["external_id"] = user_data.external_id
        if user_data.client_ip_address:
            data["client_ip_address"] = user_data.client_ip_address
        if user_data.client_user_agent:
            data["client_user_agent"] = user_data.client_user_agent
        if user_data.fbc:
            data["fbc"] = user_data.fbc
        if user_data.fbp:
            data["fbp"] = user_data.fbp

        return data

    async def get_emq_score(self) -> dict[str, Any]:
        """
        Fetch Event Match Quality scores from Meta.

        This returns ACTUAL EMQ scores calculated by Meta based on
        the events you've sent and how well they matched.
        """
        url = f"{self.BASE_URL}/{self.pixel_id}/server_events_quality"
        params = {"access_token": self.access_token}

        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()


class GoogleEnhancedConversions:
    """
    Google Ads Enhanced Conversions client.

    Enhanced Conversions improve conversion measurement by sending hashed
    first-party data (email, phone, address) to Google. This supplements
    the data collected by the Google tag.

    There are two methods:
    1. Enhanced Conversions for Web (via gtag)
    2. Enhanced Conversions for Leads (via API)

    This class implements the API method using the Google Ads API.

    Setup Requirements:
    1. Enable Enhanced Conversions in Google Ads
    2. Create a conversion action
    3. Use the Google Ads API to upload conversions
    """

    def __init__(
        self,
        customer_id: str,
        conversion_action_id: str,
        google_ads_client: Any,  # GoogleAdsClient from google-ads library
    ):
        """
        Initialize Enhanced Conversions client.

        Args:
            customer_id: Google Ads customer ID (without dashes)
            conversion_action_id: ID of the conversion action to report to
            google_ads_client: Initialized GoogleAdsClient
        """
        self.customer_id = customer_id.replace("-", "")
        self.conversion_action_id = conversion_action_id
        self.client = google_ads_client

    async def upload_conversion(self, event: ConversionEvent) -> dict[str, Any]:
        """
        Upload a conversion with enhanced data to Google Ads.

        Google Enhanced Conversions uses the OfflineUserDataJob or
        ConversionUpload service depending on the conversion type.
        """
        conversion_upload_service = self.client.get_service("ConversionUploadService")

        # Build the conversion
        click_conversion = self.client.get_type("ClickConversion")

        # Set conversion action resource name
        click_conversion.conversion_action = (
            f"customers/{self.customer_id}/conversionActions/{self.conversion_action_id}"
        )

        # Set conversion time
        click_conversion.conversion_date_time = event.event_time.strftime("%Y-%m-%d %H:%M:%S+00:00")

        # Set conversion value if provided
        if "value" in event.custom_data:
            click_conversion.conversion_value = float(event.custom_data["value"])
        if "currency" in event.custom_data:
            click_conversion.currency_code = event.custom_data["currency"]

        # Set GCLID if available
        if event.user_data.gclid:
            click_conversion.gclid = event.user_data.gclid

        # Add user identifiers for enhanced conversions
        user_identifiers = []

        if event.user_data.email:
            identifier = self.client.get_type("UserIdentifier")
            identifier.hashed_email = event.user_data.get_hashed("email")
            user_identifiers.append(identifier)

        if event.user_data.phone:
            identifier = self.client.get_type("UserIdentifier")
            identifier.hashed_phone_number = event.user_data.get_hashed("phone")
            user_identifiers.append(identifier)

        if user_identifiers:
            click_conversion.user_identifiers.extend(user_identifiers)

        # Upload the conversion
        request = self.client.get_type("UploadClickConversionsRequest")
        request.customer_id = self.customer_id
        request.conversions.append(click_conversion)
        request.partial_failure = True

        response = conversion_upload_service.upload_click_conversions(request=request)

        # Process response
        result = {"uploaded": len(response.results), "errors": []}

        if response.partial_failure_error:
            result["errors"].append(str(response.partial_failure_error))

        logger.info(f"Google Enhanced Conversions: {result['uploaded']} uploaded")
        return result


class TikTokEventsAPI:
    """
    TikTok Events API client.

    TikTok's Events API is similar to Meta CAPI, allowing server-side
    event tracking to improve attribution and targeting.

    Setup Requirements:
    1. Create a TikTok Pixel
    2. Generate an Events API access token
    3. Configure event parameters
    """

    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3/event/track"

    def __init__(self, pixel_code: str, access_token: str, test_event_code: Optional[str] = None):
        """
        Initialize TikTok Events API client.

        Args:
            pixel_code: Your TikTok Pixel code
            access_token: Events API access token
            test_event_code: Optional test code for debugging
        """
        self.pixel_code = pixel_code
        self.access_token = access_token
        self.test_event_code = test_event_code

    async def send_event(self, event: ConversionEvent) -> dict[str, Any]:
        """Send a conversion event to TikTok."""
        return await self.send_events([event])

    async def send_events(self, events: list[ConversionEvent]) -> dict[str, Any]:
        """Send multiple events to TikTok Events API."""

        # Map event types to TikTok's naming
        event_mapping = {
            EventType.PAGE_VIEW: "ViewContent",
            EventType.VIEW_CONTENT: "ViewContent",
            EventType.ADD_TO_CART: "AddToCart",
            EventType.INITIATE_CHECKOUT: "InitiateCheckout",
            EventType.PURCHASE: "CompletePayment",
            EventType.LEAD: "SubmitForm",
            EventType.COMPLETE_REGISTRATION: "CompleteRegistration",
        }

        payload = {
            "pixel_code": self.pixel_code,
            "event_source": "web",
            "event_source_id": self.pixel_code,
            "data": [],
        }

        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code

        for event in events:
            tiktok_event = {
                "event": event_mapping.get(event.event_name, event.event_name.value),
                "event_time": int(event.event_time.timestamp()),
                "event_id": event.event_id,
                "user": self._format_user_data(event.user_data),
                "properties": event.custom_data or {},
            }

            if event.event_source_url:
                tiktok_event["page"] = {"url": event.event_source_url}

            payload["data"].append(tiktok_event)

        headers = {"Access-Token": self.access_token, "Content-Type": "application/json"}

        try:
            response = requests.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            logger.info(f"TikTok Events API: {len(events)} events sent")
            return result

        except requests.RequestException as e:
            logger.error(f"TikTok Events API error: {e}")
            raise

    def _format_user_data(self, user_data: UserData) -> dict[str, Any]:
        """Format user data for TikTok."""
        data = {}

        # TikTok accepts both hashed and unhashed - we always hash
        if user_data.email:
            data["email"] = user_data.get_hashed("email")
        if user_data.phone:
            data["phone"] = user_data.get_hashed("phone")

        # Non-PII
        if user_data.external_id:
            data["external_id"] = user_data.external_id
        if user_data.client_ip_address:
            data["ip"] = user_data.client_ip_address
        if user_data.client_user_agent:
            data["user_agent"] = user_data.client_user_agent
        if user_data.ttclid:
            data["ttclid"] = user_data.ttclid

        return data


class SnapchatConversionsAPI:
    """
    Snapchat Conversions API client.

    Snapchat's CAPI allows server-side event tracking to improve
    measurement accuracy and support privacy-safe attribution.

    Setup Requirements:
    1. Create a Snap Pixel
    2. Enable Conversions API in Business Manager
    3. Generate an access token
    """

    BASE_URL = "https://tr.snapchat.com/v2/conversion"

    def __init__(self, pixel_id: str, access_token: str):
        """
        Initialize Snapchat CAPI client.

        Args:
            pixel_id: Your Snapchat Pixel ID
            access_token: Conversions API access token
        """
        self.pixel_id = pixel_id
        self.access_token = access_token

    async def send_event(self, event: ConversionEvent) -> dict[str, Any]:
        """Send a conversion event to Snapchat."""

        # Map event types to Snapchat's naming
        event_mapping = {
            EventType.PAGE_VIEW: "PAGE_VIEW",
            EventType.VIEW_CONTENT: "VIEW_CONTENT",
            EventType.ADD_TO_CART: "ADD_CART",
            EventType.INITIATE_CHECKOUT: "START_CHECKOUT",
            EventType.PURCHASE: "PURCHASE",
            EventType.LEAD: "SIGN_UP",
        }

        payload = {
            "pixel_id": self.pixel_id,
            "timestamp": int(event.event_time.timestamp() * 1000),  # milliseconds
            "event_type": event_mapping.get(event.event_name, "CUSTOM_EVENT_1"),
            "event_conversion_type": "WEB",
            "hashed_email": event.user_data.get_hashed("email"),
            "hashed_phone_number": event.user_data.get_hashed("phone"),
        }

        # Add optional fields
        if event.user_data.client_ip_address:
            payload["hashed_ip_address"] = hashlib.sha256(
                event.user_data.client_ip_address.encode()
            ).hexdigest()

        if event.user_data.sccid:
            payload["click_id"] = event.user_data.sccid

        # Add purchase data
        if event.event_name == EventType.PURCHASE:
            if "value" in event.custom_data:
                payload["price"] = str(event.custom_data["value"])
            if "currency" in event.custom_data:
                payload["currency"] = event.custom_data["currency"]
            if "transaction_id" in event.custom_data:
                payload["transaction_id"] = event.custom_data["transaction_id"]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()

            logger.info("Snapchat CAPI: Event sent successfully")
            return {"status": "success"}

        except requests.RequestException as e:
            logger.error(f"Snapchat CAPI error: {e}")
            raise


class UnifiedConversionsAPI:
    """
    Unified interface for sending conversions to all platforms.

    This class provides a single entry point for sending conversion events
    to multiple platforms simultaneously. It handles the mapping between
    unified event format and platform-specific requirements.

    Usage:
        api = UnifiedConversionsAPI()
        api.add_platform("meta", MetaConversionsAPI(...))
        api.add_platform("tiktok", TikTokEventsAPI(...))

        results = await api.send_event(event, platforms=["meta", "tiktok"])
    """

    def __init__(self):
        """Initialize with no platforms configured."""
        self.platforms: dict[str, Any] = {}

    def add_platform(self, name: str, client: Any) -> None:
        """Add a platform client."""
        self.platforms[name] = client
        logger.info(f"Added {name} to UnifiedConversionsAPI")

    async def send_event(
        self, event: ConversionEvent, platforms: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Send a conversion event to specified platforms.

        Args:
            event: The conversion event to send
            platforms: List of platform names, or None for all

        Returns:
            Dict mapping platform names to their results
        """
        target_platforms = platforms or list(self.platforms.keys())
        results = {}

        for platform_name in target_platforms:
            if platform_name not in self.platforms:
                results[platform_name] = {"error": "Platform not configured"}
                continue

            try:
                client = self.platforms[platform_name]
                result = await client.send_event(event)
                results[platform_name] = result
            except Exception as e:
                results[platform_name] = {"error": str(e)}
                logger.error(f"Error sending to {platform_name}: {e}")

        return results

    async def send_events_batch(
        self, events: list[ConversionEvent], platforms: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Send multiple events to specified platforms."""
        target_platforms = platforms or list(self.platforms.keys())
        results = {}

        for platform_name in target_platforms:
            if platform_name not in self.platforms:
                results[platform_name] = {"error": "Platform not configured"}
                continue

            try:
                client = self.platforms[platform_name]
                if hasattr(client, "send_events"):
                    result = await client.send_events(events)
                else:
                    # Fallback to individual sends
                    result = {"sent": 0, "errors": []}
                    for event in events:
                        try:
                            await client.send_event(event)
                            result["sent"] += 1
                        except Exception as e:
                            result["errors"].append(str(e))

                results[platform_name] = result
            except Exception as e:
                results[platform_name] = {"error": str(e)}

        return results


# Exports
__all__ = [
    "EventType",
    "UserData",
    "ConversionEvent",
    "MetaConversionsAPI",
    "GoogleEnhancedConversions",
    "TikTokEventsAPI",
    "SnapchatConversionsAPI",
    "UnifiedConversionsAPI",
]
