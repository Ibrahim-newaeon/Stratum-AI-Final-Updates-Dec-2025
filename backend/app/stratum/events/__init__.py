# =============================================================================
# Stratum AI - Full-Funnel Server-Side Events
# =============================================================================
"""
This module handles server-side event tracking for the COMPLETE customer journey,
not just conversions. Sending all standard events is critical for:

Why Track ALL Events (Not Just Conversions)?
--------------------------------------------

1. **Funnel Optimization**: Platforms optimize campaigns based on event signals.
   If you only send Purchase events, Meta can't optimize for AddToCart or
   ViewContent objectives effectively.

2. **Audience Building**: Retargeting audiences are built from events.
   - ViewContent -> Show related products
   - AddToCart -> Cart abandonment campaigns
   - InitiateCheckout -> Checkout abandonment recovery

3. **EMQ Across Full Funnel**: EMQ is calculated PER EVENT TYPE.
   Low ViewContent EMQ = Poor upper-funnel optimization.
   You need high EMQ at every stage.

4. **Attribution Modeling**: More touchpoints = better attribution.
   Platforms need the full picture to credit the right ads.

5. **Lookalike Audiences**: Higher-quality seed audiences when you have
   complete behavioral data.

Standard Events by Funnel Stage
-------------------------------

AWARENESS (Top of Funnel):
- PageView: User visits any page
- ViewContent: User views a product/content
- Search: User searches for something

CONSIDERATION (Middle of Funnel):
- AddToCart: User adds item to cart
- AddToWishlist: User saves item for later
- InitiateCheckout: User starts checkout
- AddPaymentInfo: User enters payment details

CONVERSION (Bottom of Funnel):
- Purchase: User completes purchase
- Subscribe: User subscribes to service
- Lead: User submits lead form
- CompleteRegistration: User creates account

POST-PURCHASE:
- Contact: User contacts support
- CustomizeProduct: User customizes order
- FindLocation: User looks for store
- Schedule: User books appointment

Platform Event Mapping
----------------------

Each platform has slightly different event names. This module handles
the mapping automatically:

| Standard Event    | Meta           | Google          | TikTok           | Snapchat        |
|-------------------|----------------|-----------------|------------------|-----------------|
| PageView          | PageView       | page_view       | Pageview         | PAGE_VIEW       |
| ViewContent       | ViewContent    | view_item       | ViewContent      | VIEW_CONTENT    |
| Search            | Search         | search          | Search           | SEARCH          |
| AddToCart         | AddToCart      | add_to_cart     | AddToCart        | ADD_CART        |
| AddToWishlist     | AddToWishlist  | add_to_wishlist | AddToWishlist    | ADD_TO_WISHLIST |
| InitiateCheckout  | InitiateCheckout| begin_checkout | InitiateCheckout | START_CHECKOUT  |
| AddPaymentInfo    | AddPaymentInfo | add_payment_info| AddPaymentInfo   | ADD_BILLING     |
| Purchase          | Purchase       | purchase        | CompletePayment  | PURCHASE        |
| Lead              | Lead           | generate_lead   | SubmitForm       | SIGN_UP         |
| CompleteRegistration| CompleteRegistration | sign_up | CompleteRegistration | SIGN_UP     |
| Subscribe         | Subscribe      | subscribe       | Subscribe        | SUBSCRIBE       |
| Contact           | Contact        | contact         | Contact          | -               |
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

import requests

logger = logging.getLogger("app.stratum.events")


# =============================================================================
# STANDARD EVENT TYPES (Full Funnel)
# =============================================================================


class StandardEvent(str, Enum):
    """
    All standard events supported across platforms.

    These map to platform-specific event names automatically.
    Use these for consistency across your tracking implementation.
    """

    # Awareness / Discovery
    PAGE_VIEW = "PageView"
    VIEW_CONTENT = "ViewContent"
    SEARCH = "Search"

    # Consideration
    ADD_TO_CART = "AddToCart"
    ADD_TO_WISHLIST = "AddToWishlist"
    INITIATE_CHECKOUT = "InitiateCheckout"
    ADD_PAYMENT_INFO = "AddPaymentInfo"

    # Conversion
    PURCHASE = "Purchase"
    LEAD = "Lead"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    SUBSCRIBE = "Subscribe"
    START_TRIAL = "StartTrial"

    # Post-Purchase / Engagement
    CONTACT = "Contact"
    CUSTOMIZE_PRODUCT = "CustomizeProduct"
    DONATE = "Donate"
    FIND_LOCATION = "FindLocation"
    SCHEDULE = "Schedule"
    SUBMIT_APPLICATION = "SubmitApplication"

    # Custom (for non-standard events)
    CUSTOM = "Custom"


# Platform-specific event name mappings
EVENT_MAPPING = {
    "meta": {
        StandardEvent.PAGE_VIEW: "PageView",
        StandardEvent.VIEW_CONTENT: "ViewContent",
        StandardEvent.SEARCH: "Search",
        StandardEvent.ADD_TO_CART: "AddToCart",
        StandardEvent.ADD_TO_WISHLIST: "AddToWishlist",
        StandardEvent.INITIATE_CHECKOUT: "InitiateCheckout",
        StandardEvent.ADD_PAYMENT_INFO: "AddPaymentInfo",
        StandardEvent.PURCHASE: "Purchase",
        StandardEvent.LEAD: "Lead",
        StandardEvent.COMPLETE_REGISTRATION: "CompleteRegistration",
        StandardEvent.SUBSCRIBE: "Subscribe",
        StandardEvent.START_TRIAL: "StartTrial",
        StandardEvent.CONTACT: "Contact",
        StandardEvent.CUSTOMIZE_PRODUCT: "CustomizeProduct",
        StandardEvent.DONATE: "Donate",
        StandardEvent.FIND_LOCATION: "FindLocation",
        StandardEvent.SCHEDULE: "Schedule",
        StandardEvent.SUBMIT_APPLICATION: "SubmitApplication",
    },
    "google": {
        StandardEvent.PAGE_VIEW: "page_view",
        StandardEvent.VIEW_CONTENT: "view_item",
        StandardEvent.SEARCH: "search",
        StandardEvent.ADD_TO_CART: "add_to_cart",
        StandardEvent.ADD_TO_WISHLIST: "add_to_wishlist",
        StandardEvent.INITIATE_CHECKOUT: "begin_checkout",
        StandardEvent.ADD_PAYMENT_INFO: "add_payment_info",
        StandardEvent.PURCHASE: "purchase",
        StandardEvent.LEAD: "generate_lead",
        StandardEvent.COMPLETE_REGISTRATION: "sign_up",
        StandardEvent.SUBSCRIBE: "subscribe",
        StandardEvent.START_TRIAL: "start_trial",
        StandardEvent.CONTACT: "contact",
    },
    "tiktok": {
        StandardEvent.PAGE_VIEW: "Pageview",
        StandardEvent.VIEW_CONTENT: "ViewContent",
        StandardEvent.SEARCH: "Search",
        StandardEvent.ADD_TO_CART: "AddToCart",
        StandardEvent.ADD_TO_WISHLIST: "AddToWishlist",
        StandardEvent.INITIATE_CHECKOUT: "InitiateCheckout",
        StandardEvent.ADD_PAYMENT_INFO: "AddPaymentInfo",
        StandardEvent.PURCHASE: "CompletePayment",
        StandardEvent.LEAD: "SubmitForm",
        StandardEvent.COMPLETE_REGISTRATION: "CompleteRegistration",
        StandardEvent.SUBSCRIBE: "Subscribe",
        StandardEvent.CONTACT: "Contact",
    },
    "snapchat": {
        StandardEvent.PAGE_VIEW: "PAGE_VIEW",
        StandardEvent.VIEW_CONTENT: "VIEW_CONTENT",
        StandardEvent.SEARCH: "SEARCH",
        StandardEvent.ADD_TO_CART: "ADD_CART",
        StandardEvent.ADD_TO_WISHLIST: "ADD_TO_WISHLIST",
        StandardEvent.INITIATE_CHECKOUT: "START_CHECKOUT",
        StandardEvent.ADD_PAYMENT_INFO: "ADD_BILLING",
        StandardEvent.PURCHASE: "PURCHASE",
        StandardEvent.LEAD: "SIGN_UP",
        StandardEvent.COMPLETE_REGISTRATION: "SIGN_UP",
        StandardEvent.SUBSCRIBE: "SUBSCRIBE",
    },
}


# =============================================================================
# USER DATA (Enhanced for Full Funnel)
# =============================================================================


@dataclass
class UserData:
    """
    User identification data for event matching.

    More data = Higher EMQ = Better optimization.

    Matching Priority (by platform):
    1. Click IDs (fbc, gclid, ttclid) - Best match
    2. Email - Very strong match
    3. Phone - Very strong match (especially Gulf markets)
    4. External ID - Good for cross-device
    5. IP + User Agent - Weak but helpful
    6. Location data - Supplementary

    All PII is automatically SHA256 hashed before sending.
    """

    # Core PII (hashed automatically)
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Location (hashed)
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    # Demographics (hashed)
    date_of_birth: Optional[str] = None  # YYYYMMDD
    gender: Optional[str] = None  # 'm' or 'f'

    # Identifiers (not hashed)
    external_id: Optional[str] = None  # Your CRM/customer ID
    subscription_id: Optional[str] = None
    lead_id: Optional[str] = None

    # Browser/Device (not hashed)
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None

    # Click IDs from URL (not hashed) - CRITICAL for matching
    fbc: Optional[str] = None  # Facebook: ?fbclid=... -> fb.1.timestamp.fbclid
    fbp: Optional[str] = None  # Facebook browser ID: _fbp cookie
    gclid: Optional[str] = None  # Google: ?gclid=...
    gbraid: Optional[str] = None  # Google: iOS app tracking
    wbraid: Optional[str] = None  # Google: web-to-app
    ttclid: Optional[str] = None  # TikTok: ?ttclid=...
    sccid: Optional[str] = None  # Snapchat: ?sccid=...

    def hash_value(self, value: str) -> str:
        """SHA256 hash a value."""
        return hashlib.sha256(value.lower().strip().encode("utf-8")).hexdigest()

    def get_hashed(self, field_name: str) -> Optional[str]:
        """Get normalized and hashed value for a field."""
        value = getattr(self, field_name, None)
        if not value:
            return None

        value = str(value).strip().lower()

        # Special normalization
        if field_name == "phone":
            import re

            value = re.sub(r"\D", "", value)
            if len(value) == 10:  # US number without country code
                value = "1" + value
        elif field_name == "email":
            # Remove dots from gmail local part for consistency
            if "@gmail.com" in value:
                local, domain = value.split("@")
                local = local.replace(".", "")
                value = f"{local}@{domain}"

        return self.hash_value(value)

    def match_quality_score(self) -> int:
        """
        Estimate match quality based on available data.

        Returns score 0-100 indicating likely EMQ.
        """
        score = 0

        # Click IDs are best
        if self.fbc or self.fbp:
            score += 30
        if self.gclid:
            score += 30
        if self.ttclid:
            score += 30

        # Email and phone are strong
        if self.email:
            score += 25
        if self.phone:
            score += 25

        # External ID helps
        if self.external_id:
            score += 10

        # IP/UA are weak but contribute
        if self.client_ip_address:
            score += 5
        if self.client_user_agent:
            score += 5

        return min(score, 100)


# =============================================================================
# EVENT DATA CLASSES
# =============================================================================


@dataclass
class ContentItem:
    """
    A product or content item in an event.

    Used for ViewContent, AddToCart, Purchase, etc.
    """

    id: str  # SKU or product ID
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    quantity: int = 1

    def to_dict(self) -> dict[str, Any]:
        data = {"id": self.id, "quantity": self.quantity}
        if self.name:
            data["item_name"] = self.name
        if self.category:
            data["item_category"] = self.category
        if self.brand:
            data["item_brand"] = self.brand
        if self.price:
            data["price"] = self.price
        return data


@dataclass
class ServerEvent:
    """
    A server-side event to be sent to advertising platforms.

    This is the core event object that works across all platforms.
    Create one event, send to multiple platforms with proper mapping.

    Example - ViewContent:
        event = ServerEvent(
            event_name=StandardEvent.VIEW_CONTENT,
            user_data=UserData(email="...", phone="..."),
            contents=[ContentItem(id="SKU123", name="Leather Sofa", price=2500)],
            value=2500.0,
            currency="SAR"
        )

    Example - AddToCart:
        event = ServerEvent(
            event_name=StandardEvent.ADD_TO_CART,
            user_data=user_data,
            contents=[ContentItem(id="SKU123", quantity=1)],
            value=2500.0,
            currency="SAR"
        )

    Example - Purchase:
        event = ServerEvent(
            event_name=StandardEvent.PURCHASE,
            user_data=user_data,
            contents=cart_items,
            value=4500.0,
            currency="SAR",
            order_id="ORD-12345"
        )
    """

    event_name: StandardEvent
    event_time: datetime = field(default_factory=datetime.utcnow)
    user_data: UserData = field(default_factory=UserData)

    # Content data
    contents: list[ContentItem] = field(default_factory=list)
    content_type: str = "product"  # product, product_group, destination, flight, hotel

    # Value data
    value: Optional[float] = None
    currency: str = "USD"

    # Order/Transaction data
    order_id: Optional[str] = None
    transaction_id: Optional[str] = None

    # Search data
    search_string: Optional[str] = None

    # Lead data
    lead_id: Optional[str] = None
    lead_type: Optional[str] = None  # form, chat, phone, etc.

    # Page data
    event_source_url: Optional[str] = None
    referrer_url: Optional[str] = None

    # Action source
    action_source: str = "website"  # website, app, email, phone_call, chat, system, other

    # Deduplication
    event_id: Optional[str] = None  # For browser/server dedup

    # Custom parameters
    custom_data: dict[str, Any] = field(default_factory=dict)

    # Opt-out
    opt_out: bool = False

    def __post_init__(self):
        """Generate event_id if not provided."""
        if not self.event_id:
            # Deterministic ID for deduplication (MD5 for consistency, not security)
            unique_string = f"{self.event_name.value}_{self.event_time.isoformat()}_{self.user_data.external_id or uuid.uuid4()}"
            self.event_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]  # noqa: S324

    def get_content_ids(self) -> list[str]:
        """Extract content IDs for platform formatting."""
        return [c.id for c in self.contents]

    def get_num_items(self) -> int:
        """Get total number of items."""
        return sum(c.quantity for c in self.contents)


# =============================================================================
# PLATFORM-SPECIFIC SENDERS
# =============================================================================


class MetaEventsSender:
    """
    Send events to Meta (Facebook/Instagram) via Conversions API.

    Supports all standard Meta events plus custom events.
    """

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, pixel_id: str, access_token: str, test_event_code: Optional[str] = None):
        self.pixel_id = pixel_id
        self.access_token = access_token
        self.test_event_code = test_event_code

    async def send(self, events: list[ServerEvent]) -> dict[str, Any]:
        """Send events to Meta CAPI."""
        payload = {
            "data": [self._format_event(e) for e in events],
            "access_token": self.access_token,
        }

        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code

        url = f"{self.BASE_URL}/{self.pixel_id}/events"

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        logger.info(
            f"Meta CAPI: Sent {len(events)} events, received {result.get('events_received', 0)}"
        )
        return result

    def _format_event(self, event: ServerEvent) -> dict[str, Any]:
        """Format event for Meta CAPI."""
        # Get Meta-specific event name
        event_name = EVENT_MAPPING["meta"].get(event.event_name, event.event_name.value)

        data = {
            "event_name": event_name,
            "event_time": int(event.event_time.timestamp()),
            "event_id": event.event_id,
            "action_source": event.action_source,
            "user_data": self._format_user_data(event.user_data),
        }

        if event.event_source_url:
            data["event_source_url"] = event.event_source_url

        if event.opt_out:
            data["opt_out"] = True

        # Custom data
        custom_data = dict(event.custom_data)

        if event.value is not None:
            custom_data["value"] = event.value
        if event.currency:
            custom_data["currency"] = event.currency
        if event.contents:
            custom_data["contents"] = [c.to_dict() for c in event.contents]
            custom_data["content_ids"] = event.get_content_ids()
            custom_data["content_type"] = event.content_type
            custom_data["num_items"] = event.get_num_items()
        if event.order_id:
            custom_data["order_id"] = event.order_id
        if event.search_string:
            custom_data["search_string"] = event.search_string

        if custom_data:
            data["custom_data"] = custom_data

        return data

    def _format_user_data(self, user: UserData) -> dict[str, Any]:
        """Format user data with hashing."""
        data = {}

        # Hashed fields
        hash_map = [
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

        for api_key, field_name in hash_map:
            hashed = user.get_hashed(field_name)
            if hashed:
                data[api_key] = hashed

        # Non-hashed
        if user.external_id:
            data["external_id"] = user.external_id
        if user.client_ip_address:
            data["client_ip_address"] = user.client_ip_address
        if user.client_user_agent:
            data["client_user_agent"] = user.client_user_agent
        if user.fbc:
            data["fbc"] = user.fbc
        if user.fbp:
            data["fbp"] = user.fbp

        return data

    async def get_emq_scores(self) -> dict[str, Any]:
        """Fetch actual EMQ scores from Meta."""
        url = f"{self.BASE_URL}/{self.pixel_id}/server_events_quality"
        params = {"access_token": self.access_token}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


class GoogleEventsSender:
    """
    Send events to Google Ads via Measurement Protocol / Enhanced Conversions.

    Supports GA4 Measurement Protocol for real-time event streaming.
    """

    MP_URL = "https://www.google-analytics.com/mp/collect"

    def __init__(
        self,
        measurement_id: str,  # G-XXXXXXX
        api_secret: str,
        client_id: Optional[str] = None,
    ):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.default_client_id = client_id or str(uuid.uuid4())

    async def send(self, events: list[ServerEvent]) -> dict[str, Any]:
        """Send events via GA4 Measurement Protocol."""
        url = f"{self.MP_URL}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

        for event in events:
            payload = self._format_event(event)
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code != 204:
                logger.warning(
                    f"Google MP: Event may not have been recorded: {response.status_code}"
                )

        logger.info(f"Google MP: Sent {len(events)} events")
        return {"sent": len(events)}

    def _format_event(self, event: ServerEvent) -> dict[str, Any]:
        """Format event for GA4 Measurement Protocol."""
        event_name = EVENT_MAPPING["google"].get(event.event_name, event.event_name.value.lower())

        params = {}

        if event.value is not None:
            params["value"] = event.value
        if event.currency:
            params["currency"] = event.currency
        if event.contents:
            params["items"] = [
                {
                    "item_id": c.id,
                    "item_name": c.name,
                    "item_category": c.category,
                    "item_brand": c.brand,
                    "price": c.price,
                    "quantity": c.quantity,
                }
                for c in event.contents
            ]
        if event.transaction_id or event.order_id:
            params["transaction_id"] = event.transaction_id or event.order_id
        if event.search_string:
            params["search_term"] = event.search_string

        # User identification
        user_id = event.user_data.external_id
        client_id = self.default_client_id

        # User properties for enhanced matching
        user_properties = {}
        if event.user_data.email:
            user_properties["email"] = {"value": event.user_data.get_hashed("email")}
        if event.user_data.phone:
            user_properties["phone"] = {"value": event.user_data.get_hashed("phone")}

        payload = {"client_id": client_id, "events": [{"name": event_name, "params": params}]}

        if user_id:
            payload["user_id"] = user_id
        if user_properties:
            payload["user_properties"] = user_properties

        return payload


class TikTokEventsSender:
    """
    Send events to TikTok via Events API.
    """

    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3/event/track"

    def __init__(self, pixel_code: str, access_token: str, test_event_code: Optional[str] = None):
        self.pixel_code = pixel_code
        self.access_token = access_token
        self.test_event_code = test_event_code

    async def send(self, events: list[ServerEvent]) -> dict[str, Any]:
        """Send events to TikTok Events API."""
        payload = {
            "pixel_code": self.pixel_code,
            "event_source": "web",
            "event_source_id": self.pixel_code,
            "data": [self._format_event(e) for e in events],
        }

        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code

        headers = {"Access-Token": self.access_token, "Content-Type": "application/json"}

        response = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        logger.info(f"TikTok Events: Sent {len(events)} events")
        return result

    def _format_event(self, event: ServerEvent) -> dict[str, Any]:
        """Format event for TikTok."""
        event_name = EVENT_MAPPING["tiktok"].get(event.event_name, event.event_name.value)

        data = {
            "event": event_name,
            "event_time": int(event.event_time.timestamp()),
            "event_id": event.event_id,
            "user": {},
        }

        # User data
        user = event.user_data
        if user.email:
            data["user"]["email"] = user.get_hashed("email")
        if user.phone:
            data["user"]["phone"] = user.get_hashed("phone")
        if user.external_id:
            data["user"]["external_id"] = user.external_id
        if user.client_ip_address:
            data["user"]["ip"] = user.client_ip_address
        if user.client_user_agent:
            data["user"]["user_agent"] = user.client_user_agent
        if user.ttclid:
            data["user"]["ttclid"] = user.ttclid

        # Properties
        props = {}
        if event.value is not None:
            props["value"] = event.value
        if event.currency:
            props["currency"] = event.currency
        if event.contents:
            props["contents"] = [
                {
                    "content_id": c.id,
                    "content_name": c.name,
                    "price": c.price,
                    "quantity": c.quantity,
                }
                for c in event.contents
            ]
        if event.search_string:
            props["query"] = event.search_string

        if props:
            data["properties"] = props

        if event.event_source_url:
            data["page"] = {"url": event.event_source_url}

        return data


class SnapchatEventsSender:
    """
    Send events to Snapchat via Conversions API.
    """

    BASE_URL = "https://tr.snapchat.com/v2/conversion"

    def __init__(self, pixel_id: str, access_token: str):
        self.pixel_id = pixel_id
        self.access_token = access_token

    async def send(self, events: list[ServerEvent]) -> dict[str, Any]:
        """Send events to Snapchat CAPI."""
        results = []

        for event in events:
            payload = self._format_event(event)
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            results.append(response.json())

        logger.info(f"Snapchat CAPI: Sent {len(events)} events")
        return {"sent": len(events), "results": results}

    def _format_event(self, event: ServerEvent) -> dict[str, Any]:
        """Format event for Snapchat."""
        event_name = EVENT_MAPPING["snapchat"].get(event.event_name, "CUSTOM_EVENT_1")

        user = event.user_data

        payload = {
            "pixel_id": self.pixel_id,
            "timestamp": int(event.event_time.timestamp() * 1000),
            "event_type": event_name,
            "event_conversion_type": "WEB",
        }

        # User data (hashed)
        if user.email:
            payload["hashed_email"] = user.get_hashed("email")
        if user.phone:
            payload["hashed_phone_number"] = user.get_hashed("phone")
        if user.client_ip_address:
            payload["hashed_ip_address"] = hashlib.sha256(
                user.client_ip_address.encode()
            ).hexdigest()
        if user.sccid:
            payload["click_id"] = user.sccid

        # Purchase-specific
        if event.event_name == StandardEvent.PURCHASE:
            if event.value is not None:
                payload["price"] = str(event.value)
            if event.currency:
                payload["currency"] = event.currency
            if event.order_id:
                payload["transaction_id"] = event.order_id

        # Item data
        if event.contents:
            payload["item_ids"] = event.get_content_ids()
            payload["number_items"] = str(event.get_num_items())

        return payload


# =============================================================================
# UNIFIED EVENTS API
# =============================================================================


class UnifiedEventsAPI:
    """
    Unified interface for sending events to ALL platforms simultaneously.

    This is the recommended way to implement server-side tracking.
    One event object -> Multiple platforms with proper formatting.

    Example:

        api = UnifiedEventsAPI()

        # Configure platforms
        api.add_sender("meta", MetaEventsSender(pixel_id="...", access_token="..."))
        api.add_sender("google", GoogleEventsSender(measurement_id="...", api_secret="..."))
        api.add_sender("tiktok", TikTokEventsSender(pixel_code="...", access_token="..."))
        api.add_sender("snapchat", SnapchatEventsSender(pixel_id="...", access_token="..."))

        # Track a ViewContent event
        event = ServerEvent(
            event_name=StandardEvent.VIEW_CONTENT,
            user_data=UserData(email="...", fbc="..."),
            contents=[ContentItem(id="SKU123", name="Leather Sofa", price=2500)],
            value=2500.0,
            currency="SAR"
        )

        # Send to all platforms
        results = await api.send(event)
        # {"meta": {...}, "google": {...}, "tiktok": {...}, "snapchat": {...}}
    """

    def __init__(self):
        self.senders: dict[str, Any] = {}

    def add_sender(self, platform: str, sender: Any) -> None:
        """Add a platform sender."""
        self.senders[platform] = sender
        logger.info(f"Added {platform} to UnifiedEventsAPI")

    async def send(
        self, event: Union[ServerEvent, list[ServerEvent]], platforms: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Send event(s) to specified platforms (or all configured).

        Args:
            event: Single event or list of events
            platforms: Platforms to send to (default: all)

        Returns:
            Dict with results per platform
        """
        events = [event] if isinstance(event, ServerEvent) else event
        target_platforms = platforms or list(self.senders.keys())

        results = {}

        for platform in target_platforms:
            if platform not in self.senders:
                results[platform] = {"error": f"Platform '{platform}' not configured"}
                continue

            try:
                sender = self.senders[platform]
                result = await sender.send(events)
                results[platform] = result
            except Exception as e:
                logger.error(f"Error sending to {platform}: {e}")
                results[platform] = {"error": str(e)}

        return results

    async def track_page_view(
        self,
        user_data: UserData,
        page_url: str,
        page_title: Optional[str] = None,
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for PageView events."""
        event = ServerEvent(
            event_name=StandardEvent.PAGE_VIEW,
            user_data=user_data,
            event_source_url=page_url,
            custom_data={"page_title": page_title} if page_title else {},
        )
        return await self.send(event, platforms)

    async def track_view_content(
        self,
        user_data: UserData,
        content: ContentItem,
        page_url: Optional[str] = None,
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for ViewContent events."""
        event = ServerEvent(
            event_name=StandardEvent.VIEW_CONTENT,
            user_data=user_data,
            contents=[content],
            value=content.price,
            event_source_url=page_url,
        )
        return await self.send(event, platforms)

    async def track_add_to_cart(
        self,
        user_data: UserData,
        contents: list[ContentItem],
        currency: str = "USD",
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for AddToCart events."""
        total_value = sum((c.price or 0) * c.quantity for c in contents)
        event = ServerEvent(
            event_name=StandardEvent.ADD_TO_CART,
            user_data=user_data,
            contents=contents,
            value=total_value,
            currency=currency,
        )
        return await self.send(event, platforms)

    async def track_initiate_checkout(
        self,
        user_data: UserData,
        contents: list[ContentItem],
        currency: str = "USD",
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for InitiateCheckout events."""
        total_value = sum((c.price or 0) * c.quantity for c in contents)
        event = ServerEvent(
            event_name=StandardEvent.INITIATE_CHECKOUT,
            user_data=user_data,
            contents=contents,
            value=total_value,
            currency=currency,
        )
        return await self.send(event, platforms)

    async def track_purchase(
        self,
        user_data: UserData,
        contents: list[ContentItem],
        order_id: str,
        value: float,
        currency: str = "USD",
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for Purchase events."""
        event = ServerEvent(
            event_name=StandardEvent.PURCHASE,
            user_data=user_data,
            contents=contents,
            order_id=order_id,
            value=value,
            currency=currency,
        )
        return await self.send(event, platforms)

    async def track_lead(
        self,
        user_data: UserData,
        lead_type: str = "form",
        value: Optional[float] = None,
        platforms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Convenience method for Lead events."""
        event = ServerEvent(
            event_name=StandardEvent.LEAD, user_data=user_data, lead_type=lead_type, value=value
        )
        return await self.send(event, platforms)

    async def track_search(
        self, user_data: UserData, search_string: str, platforms: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Convenience method for Search events."""
        event = ServerEvent(
            event_name=StandardEvent.SEARCH, user_data=user_data, search_string=search_string
        )
        return await self.send(event, platforms)


# =============================================================================
# E-COMMERCE TRACKER (High-Level Integration)
# =============================================================================


class EcommerceTracker:
    """
    High-level tracker for e-commerce sites.

    Provides a simple interface for tracking the full customer journey
    from page view to purchase, automatically sending to all platforms.

    Example:

        tracker = EcommerceTracker(
            meta_pixel_id="123...",
            meta_access_token="EAA...",
            google_measurement_id="G-XXX",
            google_api_secret="...",
            # ... other platform credentials
        )

        # On product page load
        await tracker.product_viewed(
            user={"email": "...", "phone": "..."},
            product={"id": "SKU123", "name": "Sofa", "price": 2500}
        )

        # On add to cart
        await tracker.added_to_cart(
            user={"email": "...", "phone": "..."},
            products=[{"id": "SKU123", "quantity": 1}]
        )

        # On purchase
        await tracker.purchase_completed(
            user={"email": "...", "phone": "..."},
            order_id="ORD-123",
            products=[...],
            total=2500.0,
            currency="SAR"
        )
    """

    def __init__(
        self,
        meta_pixel_id: Optional[str] = None,
        meta_access_token: Optional[str] = None,
        google_measurement_id: Optional[str] = None,
        google_api_secret: Optional[str] = None,
        tiktok_pixel_code: Optional[str] = None,
        tiktok_access_token: Optional[str] = None,
        snapchat_pixel_id: Optional[str] = None,
        snapchat_access_token: Optional[str] = None,
    ):
        self.api = UnifiedEventsAPI()

        if meta_pixel_id and meta_access_token:
            self.api.add_sender("meta", MetaEventsSender(meta_pixel_id, meta_access_token))

        if google_measurement_id and google_api_secret:
            self.api.add_sender(
                "google", GoogleEventsSender(google_measurement_id, google_api_secret)
            )

        if tiktok_pixel_code and tiktok_access_token:
            self.api.add_sender(
                "tiktok", TikTokEventsSender(tiktok_pixel_code, tiktok_access_token)
            )

        if snapchat_pixel_id and snapchat_access_token:
            self.api.add_sender(
                "snapchat", SnapchatEventsSender(snapchat_pixel_id, snapchat_access_token)
            )

    def _make_user_data(self, user: dict[str, Any]) -> UserData:
        """Create UserData from dict."""
        return UserData(
            email=user.get("email"),
            phone=user.get("phone"),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            external_id=user.get("customer_id") or user.get("external_id"),
            client_ip_address=user.get("ip"),
            client_user_agent=user.get("user_agent"),
            fbc=user.get("fbc"),
            fbp=user.get("fbp"),
            gclid=user.get("gclid"),
            ttclid=user.get("ttclid"),
        )

    def _make_content_item(self, product: dict[str, Any]) -> ContentItem:
        """Create ContentItem from dict."""
        return ContentItem(
            id=product.get("id", product.get("sku", "")),
            name=product.get("name"),
            category=product.get("category"),
            brand=product.get("brand"),
            price=product.get("price"),
            quantity=product.get("quantity", 1),
        )

    async def page_viewed(
        self, user: dict[str, Any], page_url: str, page_title: Optional[str] = None
    ) -> dict[str, Any]:
        """Track page view."""
        return await self.api.track_page_view(self._make_user_data(user), page_url, page_title)

    async def product_viewed(
        self, user: dict[str, Any], product: dict[str, Any], page_url: Optional[str] = None
    ) -> dict[str, Any]:
        """Track product view."""
        return await self.api.track_view_content(
            self._make_user_data(user), self._make_content_item(product), page_url
        )

    async def products_searched(self, user: dict[str, Any], search_query: str) -> dict[str, Any]:
        """Track search."""
        return await self.api.track_search(self._make_user_data(user), search_query)

    async def added_to_cart(
        self, user: dict[str, Any], products: list[dict[str, Any]], currency: str = "USD"
    ) -> dict[str, Any]:
        """Track add to cart."""
        contents = [self._make_content_item(p) for p in products]
        return await self.api.track_add_to_cart(self._make_user_data(user), contents, currency)

    async def checkout_started(
        self, user: dict[str, Any], products: list[dict[str, Any]], currency: str = "USD"
    ) -> dict[str, Any]:
        """Track checkout initiation."""
        contents = [self._make_content_item(p) for p in products]
        return await self.api.track_initiate_checkout(
            self._make_user_data(user), contents, currency
        )

    async def purchase_completed(
        self,
        user: dict[str, Any],
        order_id: str,
        products: list[dict[str, Any]],
        total: float,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Track purchase."""
        contents = [self._make_content_item(p) for p in products]
        return await self.api.track_purchase(
            self._make_user_data(user), contents, order_id, total, currency
        )

    async def lead_submitted(
        self, user: dict[str, Any], lead_type: str = "form", value: Optional[float] = None
    ) -> dict[str, Any]:
        """Track lead submission."""
        return await self.api.track_lead(self._make_user_data(user), lead_type, value)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Standard event types
    "StandardEvent",
    "EVENT_MAPPING",
    # Data classes
    "UserData",
    "ContentItem",
    "ServerEvent",
    # Platform senders
    "MetaEventsSender",
    "GoogleEventsSender",
    "TikTokEventsSender",
    "SnapchatEventsSender",
    # Unified API
    "UnifiedEventsAPI",
    # High-level tracker
    "EcommerceTracker",
]
