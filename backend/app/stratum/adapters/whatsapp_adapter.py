"""
Stratum AI: WhatsApp Business API Adapter
=========================================

This adapter provides integration with Meta's WhatsApp Business API (Cloud API),
enabling automated messaging, conversation tracking, and conversion attribution.

WhatsApp in the Advertising Ecosystem
-------------------------------------

WhatsApp is unique among Stratum's platforms - it's primarily a messaging channel
rather than an advertising platform. However, it plays a critical role in the
customer journey:

1. **Lead Capture**: Click-to-WhatsApp ads on Meta drive users to WhatsApp
2. **Conversation**: Automated and human conversations nurture leads
3. **Conversion**: Orders placed via WhatsApp need attribution tracking
4. **Support**: Post-purchase support and upselling

WhatsApp conversions feed back into Meta Ads through:
- Click-to-WhatsApp ad tracking (automatic via Meta)
- WhatsApp Conversions API (manual - this adapter helps)
- Message quality signals (affects ad delivery)

API Versions
------------

Meta offers two WhatsApp API options:

1. **Cloud API** (Recommended): Hosted by Meta, easier setup
   - This adapter uses Cloud API
   - Base URL: graph.facebook.com

2. **On-Premises API**: Self-hosted, more control
   - Requires your own infrastructure
   - Not covered by this adapter

Message Types
-------------

- **Template Messages**: Pre-approved messages for business-initiated conversations
- **Session Messages**: Free-form replies within 24-hour window
- **Interactive Messages**: Buttons, lists, product catalogs

Rate Limits
-----------

- Template messages: Varies by tier (1K to 100K+ per day)
- Session messages: Unlimited within 24-hour window
- API calls: 80 calls/second for Cloud API
"""

import hashlib
import hmac
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import requests

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    BaseAdapter,
    PlatformError,
    RateLimiter,
)
from app.stratum.models import Platform

logger = logging.getLogger("stratum.adapters.whatsapp")


class MessageType(str, Enum):
    """Types of WhatsApp messages."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    REACTION = "reaction"


class MessageStatus(str, Enum):
    """Status of sent messages."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ConversationType(str, Enum):
    """Types of WhatsApp conversations for billing."""

    MARKETING = "marketing"  # Business-initiated promotional
    UTILITY = "utility"  # Business-initiated transactional
    AUTHENTICATION = "authentication"  # OTP/verification
    SERVICE = "service"  # User-initiated


@dataclass
class Contact:
    """WhatsApp contact information."""

    wa_id: str  # WhatsApp ID (phone number)
    profile_name: Optional[str] = None

    # Additional data from your CRM
    external_id: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Message:
    """A WhatsApp message (sent or received)."""

    message_id: str
    wa_id: str  # Recipient/sender WhatsApp ID
    message_type: MessageType
    timestamp: datetime

    # Content (depends on message_type)
    text: Optional[str] = None
    media_id: Optional[str] = None
    media_url: Optional[str] = None
    template_name: Optional[str] = None
    template_params: dict[str, Any] = field(default_factory=dict)
    interactive_data: dict[str, Any] = field(default_factory=dict)

    # Status
    status: MessageStatus = MessageStatus.PENDING
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    # Direction
    is_outbound: bool = True

    # Tracking
    context_message_id: Optional[str] = None  # Reply-to message
    conversation_id: Optional[str] = None


@dataclass
class Conversation:
    """A WhatsApp conversation with a contact."""

    conversation_id: str
    wa_id: str
    contact: Optional[Contact] = None

    # Conversation window
    started_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    conversation_type: ConversationType = ConversationType.SERVICE

    # Messages
    messages: list[Message] = field(default_factory=list)

    # Attribution
    entry_point: Optional[str] = None  # How they started (ad, organic, etc.)
    ad_id: Optional[str] = None  # If from Click-to-WhatsApp ad
    campaign_id: Optional[str] = None

    # Conversion tracking
    is_converted: bool = False
    conversion_value: Optional[float] = None
    conversion_time: Optional[datetime] = None


@dataclass
class Template:
    """A WhatsApp message template."""

    name: str
    language: str
    category: str  # MARKETING, UTILITY, AUTHENTICATION
    status: str  # APPROVED, PENDING, REJECTED

    # Components
    header: Optional[dict[str, Any]] = None
    body: str = ""
    footer: Optional[str] = None
    buttons: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    id: Optional[str] = None
    quality_score: Optional[str] = None  # GREEN, YELLOW, RED


class WhatsAppAdapter(BaseAdapter):
    """
    WhatsApp Business API adapter for messaging and conversation management.

    This adapter connects to Meta's WhatsApp Cloud API to enable:
    - Sending template messages (business-initiated)
    - Sending session messages (within 24hr window)
    - Receiving and processing incoming messages
    - Tracking conversations and conversions
    - Managing message templates

    Required Credentials:
        phone_number_id: Your WhatsApp Business Phone Number ID
        access_token: Permanent access token or system user token
        business_account_id: WhatsApp Business Account ID

    Optional:
        app_secret: For webhook signature verification
        verify_token: Your webhook verification token

    Example Usage:

        adapter = WhatsAppAdapter({
            "phone_number_id": "123456789",
            "access_token": "EAAxxxxxxx",
            "business_account_id": "987654321"
        })
        await adapter.initialize()

        # Send a template message
        result = await adapter.send_template_message(
            to="+1234567890",
            template_name="order_confirmation",
            language="en",
            components=[
                {"type": "body", "parameters": [
                    {"type": "text", "text": "John"},
                    {"type": "text", "text": "ORD-12345"}
                ]}
            ]
        )
    """

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, credentials: dict[str, str]):
        """
        Initialize the WhatsApp adapter.

        Args:
            credentials: Dictionary containing:
                - phone_number_id: WhatsApp phone number ID
                - access_token: API access token
                - business_account_id: WABA ID
                - app_secret: (optional) For webhook verification
                - verify_token: (optional) Webhook verify token
        """
        super().__init__(credentials)

        required = ["phone_number_id", "access_token", "business_account_id"]
        missing = [k for k in required if k not in credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {missing}")

        self.phone_number_id = credentials["phone_number_id"]
        self.access_token = credentials["access_token"]
        self.business_account_id = credentials["business_account_id"]
        self.app_secret = credentials.get("app_secret")
        self.verify_token = credentials.get("verify_token")

        # Rate limiter (80 calls/sec for Cloud API)
        self.rate_limiter = RateLimiter(
            calls_per_minute=4000,  # Conservative
            burst_size=80,
        )

        # Conversation tracking
        self._conversations: dict[str, Conversation] = {}

        # Webhook handlers
        self._message_handlers: list[Callable] = []
        self._status_handlers: list[Callable] = []

    @property
    def platform(self) -> Platform:
        """Return platform identifier."""
        # WhatsApp is part of Meta ecosystem but distinct
        return Platform.META

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def initialize(self) -> None:
        """Initialize and verify WhatsApp API connection."""
        logger.info("Initializing WhatsApp Business API adapter")

        try:
            # Verify credentials by fetching phone number info
            await self.rate_limiter.acquire()
            response = self._make_request(
                "GET",
                f"/{self.phone_number_id}",
                params={"fields": "display_phone_number,verified_name,quality_rating"},
            )

            phone_number = response.get("display_phone_number", "Unknown")
            verified_name = response.get("verified_name", "Unknown")
            quality = response.get("quality_rating", "Unknown")

            logger.info(
                f"Connected to WhatsApp: {verified_name} ({phone_number}), " f"Quality: {quality}"
            )

            self._initialized = True

        except Exception as e:
            raise AuthenticationError(f"Failed to initialize WhatsApp: {e}")

    async def cleanup(self) -> None:
        """Clean up adapter resources."""
        self._initialized = False
        self._conversations.clear()
        logger.info("WhatsApp adapter cleanup complete")

    # ========================================================================
    # MESSAGING - SEND
    # ========================================================================

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False, reply_to: Optional[str] = None
    ) -> Message:
        """
        Send a text message (session message - requires 24hr window).

        Args:
            to: Recipient phone number (E.164 format)
            text: Message text (max 4096 characters)
            preview_url: Whether to show URL previews
            reply_to: Message ID to reply to

        Returns:
            Message object with send status
        """
        self._ensure_initialized()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "text",
            "text": {"preview_url": preview_url, "body": text},
        }

        if reply_to:
            payload["context"] = {"message_id": reply_to}

        await self.rate_limiter.acquire()
        response = self._make_request("POST", f"/{self.phone_number_id}/messages", data=payload)

        message_id = response.get("messages", [{}])[0].get("id", "")

        message = Message(
            message_id=message_id,
            wa_id=to,
            message_type=MessageType.TEXT,
            timestamp=datetime.utcnow(),
            text=text,
            status=MessageStatus.SENT,
            is_outbound=True,
            context_message_id=reply_to,
        )

        self._track_message(message)
        logger.info(f"Sent text message to {to}: {message_id}")

        return message

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language: str = "en",
        components: Optional[list[dict]] = None,
    ) -> Message:
        """
        Send a template message (can start new conversations).

        Template messages are pre-approved by Meta and can be sent
        outside the 24-hour window. They're used for:
        - Order confirmations
        - Shipping updates
        - Appointment reminders
        - Marketing campaigns

        Args:
            to: Recipient phone number
            template_name: Name of the approved template
            language: Template language code
            components: Template variable substitutions

        Returns:
            Message object with send status
        """
        self._ensure_initialized()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "template",
            "template": {"name": template_name, "language": {"code": language}},
        }

        if components:
            payload["template"]["components"] = components

        await self.rate_limiter.acquire()
        response = self._make_request("POST", f"/{self.phone_number_id}/messages", data=payload)

        message_id = response.get("messages", [{}])[0].get("id", "")

        message = Message(
            message_id=message_id,
            wa_id=to,
            message_type=MessageType.TEMPLATE,
            timestamp=datetime.utcnow(),
            template_name=template_name,
            template_params={"components": components},
            status=MessageStatus.SENT,
            is_outbound=True,
        )

        self._track_message(message)
        logger.info(f"Sent template '{template_name}' to {to}: {message_id}")

        return message

    async def send_interactive_message(
        self,
        to: str,
        interactive_type: str,
        body_text: str,
        action: dict[str, Any],
        header: Optional[dict] = None,
        footer: Optional[str] = None,
    ) -> Message:
        """
        Send an interactive message with buttons or lists.

        Interactive messages provide rich UI elements:
        - Reply buttons (up to 3 buttons)
        - List messages (up to 10 rows)
        - Product messages (from catalog)

        Args:
            to: Recipient phone number
            interactive_type: "button", "list", "product", "product_list"
            body_text: Main message text
            action: Buttons or list configuration
            header: Optional header (text, image, video, document)
            footer: Optional footer text
        """
        self._ensure_initialized()

        interactive = {"type": interactive_type, "body": {"text": body_text}, "action": action}

        if header:
            interactive["header"] = header
        if footer:
            interactive["footer"] = {"text": footer}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "interactive",
            "interactive": interactive,
        }

        await self.rate_limiter.acquire()
        response = self._make_request("POST", f"/{self.phone_number_id}/messages", data=payload)

        message_id = response.get("messages", [{}])[0].get("id", "")

        message = Message(
            message_id=message_id,
            wa_id=to,
            message_type=MessageType.INTERACTIVE,
            timestamp=datetime.utcnow(),
            interactive_data=interactive,
            status=MessageStatus.SENT,
            is_outbound=True,
        )

        self._track_message(message)
        return message

    async def send_media_message(
        self,
        to: str,
        media_type: str,
        media_id: Optional[str] = None,
        media_url: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Message:
        """
        Send a media message (image, video, audio, document).

        Args:
            to: Recipient phone number
            media_type: "image", "video", "audio", "document"
            media_id: WhatsApp media ID (from upload)
            media_url: Public URL of media (alternative to media_id)
            caption: Optional caption (images and videos only)
            filename: Required for documents
        """
        self._ensure_initialized()

        media_object = {}
        if media_id:
            media_object["id"] = media_id
        elif media_url:
            media_object["link"] = media_url
        else:
            raise ValueError("Either media_id or media_url required")

        if caption and media_type in ["image", "video"]:
            media_object["caption"] = caption

        if filename and media_type == "document":
            media_object["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": media_type,
            media_type: media_object,
        }

        await self.rate_limiter.acquire()
        response = self._make_request("POST", f"/{self.phone_number_id}/messages", data=payload)

        message_id = response.get("messages", [{}])[0].get("id", "")

        return Message(
            message_id=message_id,
            wa_id=to,
            message_type=MessageType(media_type.upper()),
            timestamp=datetime.utcnow(),
            media_id=media_id,
            media_url=media_url,
            text=caption,
            status=MessageStatus.SENT,
            is_outbound=True,
        )

    # ========================================================================
    # MEDIA MANAGEMENT
    # ========================================================================

    async def upload_media(self, file_path: str, media_type: str) -> str:
        """
        Upload media to WhatsApp servers.

        Returns the media_id to use when sending messages.

        Supported types:
        - image: JPEG, PNG (max 5MB)
        - video: MP4, 3GPP (max 16MB)
        - audio: AAC, MP3, OGG, AMR (max 16MB)
        - document: PDF, DOC, etc. (max 100MB)
        - sticker: WebP (max 100KB)
        """
        self._ensure_initialized()

        mime_types = {
            "image": "image/jpeg",
            "video": "video/mp4",
            "audio": "audio/mpeg",
            "document": "application/pdf",
            "sticker": "image/webp",
        }

        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, mime_types.get(media_type, "application/octet-stream"))}
            data = {"messaging_product": "whatsapp", "type": mime_types.get(media_type)}

            url = f"{self.BASE_URL}/{self.phone_number_id}/media"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.post(url, data=data, files=files, headers=headers)
            response.raise_for_status()

            return response.json().get("id", "")

    # ========================================================================
    # TEMPLATE MANAGEMENT
    # ========================================================================

    async def get_templates(self) -> list[Template]:
        """Fetch all message templates for the business account."""
        self._ensure_initialized()

        await self.rate_limiter.acquire()
        response = self._make_request(
            "GET", f"/{self.business_account_id}/message_templates", params={"limit": 100}
        )

        templates = []
        for t in response.get("data", []):
            components = t.get("components", [])

            header = next((c for c in components if c.get("type") == "HEADER"), None)
            body = next((c for c in components if c.get("type") == "BODY"), {})
            footer = next((c for c in components if c.get("type") == "FOOTER"), None)
            buttons = [c for c in components if c.get("type") == "BUTTONS"]

            template = Template(
                name=t.get("name", ""),
                language=t.get("language", "en"),
                category=t.get("category", ""),
                status=t.get("status", ""),
                id=t.get("id"),
                header=header,
                body=body.get("text", ""),
                footer=footer.get("text") if footer else None,
                buttons=buttons[0].get("buttons", []) if buttons else [],
                quality_score=t.get("quality_score", {}).get("score"),
            )
            templates.append(template)

        return templates

    async def create_template(
        self, name: str, category: str, language: str, components: list[dict]
    ) -> dict[str, Any]:
        """
        Create a new message template.

        Templates must be approved by Meta before use (usually 24-48 hours).

        Args:
            name: Template name (lowercase, underscores only)
            category: MARKETING, UTILITY, or AUTHENTICATION
            language: Language code (e.g., "en", "ar")
            components: Template structure (HEADER, BODY, FOOTER, BUTTONS)
        """
        self._ensure_initialized()

        payload = {
            "name": name,
            "category": category,
            "language": language,
            "components": components,
        }

        await self.rate_limiter.acquire()
        response = self._make_request(
            "POST", f"/{self.business_account_id}/message_templates", data=payload
        )

        logger.info(f"Created template '{name}', pending approval")
        return response

    # ========================================================================
    # WEBHOOK HANDLING
    # ========================================================================

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription from Meta.

        This is called when Meta sends a verification request to your webhook URL.

        Args:
            mode: Should be "subscribe"
            token: Your verify_token
            challenge: Challenge string to return

        Returns:
            Challenge string if verified, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verified successfully")
            return challenge

        logger.warning(f"Webhook verification failed: mode={mode}")
        return None

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook payload signature.

        Meta signs webhook payloads with your app secret. Always verify
        before processing to prevent spoofed requests.
        """
        if not self.app_secret:
            logger.warning("No app_secret configured, skipping signature verification")
            return True

        expected = hmac.new(self.app_secret.encode(), payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def process_webhook(self, payload: dict[str, Any]) -> None:
        """
        Process incoming webhook events from WhatsApp.

        This handles:
        - Incoming messages
        - Message status updates (sent, delivered, read)
        - Errors

        Args:
            payload: Webhook payload from Meta
        """
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Handle incoming messages
                if "messages" in value:
                    for msg_data in value["messages"]:
                        message = self._parse_incoming_message(msg_data, value)
                        self._track_message(message)

                        for handler in self._message_handlers:
                            try:
                                await handler(message)
                            except Exception as e:
                                logger.error(f"Message handler error: {e}")

                # Handle status updates
                if "statuses" in value:
                    for status_data in value["statuses"]:
                        await self._handle_status_update(status_data)

    def on_message(self, handler: Callable) -> None:
        """Register a handler for incoming messages."""
        self._message_handlers.append(handler)

    def on_status_update(self, handler: Callable) -> None:
        """Register a handler for message status updates."""
        self._status_handlers.append(handler)

    def _parse_incoming_message(self, msg_data: dict, value: dict) -> Message:
        """Parse incoming message from webhook payload."""
        msg_type = msg_data.get("type", "text")

        message = Message(
            message_id=msg_data.get("id", ""),
            wa_id=msg_data.get("from", ""),
            message_type=MessageType(msg_type.upper())
            if msg_type in [m.value for m in MessageType]
            else MessageType.TEXT,
            timestamp=datetime.fromtimestamp(int(msg_data.get("timestamp", 0))),
            status=MessageStatus.DELIVERED,
            is_outbound=False,
        )

        # Extract content based on type
        if msg_type == "text":
            message.text = msg_data.get("text", {}).get("body", "")
        elif msg_type in ["image", "video", "audio", "document", "sticker"]:
            media_data = msg_data.get(msg_type, {})
            message.media_id = media_data.get("id")
            message.text = media_data.get("caption")
        elif msg_type == "interactive":
            interactive = msg_data.get("interactive", {})
            int_type = interactive.get("type")
            if int_type == "button_reply":
                message.interactive_data = interactive.get("button_reply", {})
            elif int_type == "list_reply":
                message.interactive_data = interactive.get("list_reply", {})

        # Context (reply-to)
        if "context" in msg_data:
            message.context_message_id = msg_data["context"].get("id")

        # Contact info
        contacts = value.get("contacts", [])
        if contacts:
            contact = contacts[0]
            message.wa_id = contact.get("wa_id", message.wa_id)

        return message

    async def _handle_status_update(self, status_data: dict) -> None:
        """Handle message status webhook."""
        message_id = status_data.get("id", "")
        status = status_data.get("status", "")

        status_map = {
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "read": MessageStatus.READ,
            "failed": MessageStatus.FAILED,
        }

        new_status = status_map.get(status, MessageStatus.PENDING)

        # Update tracked message
        for conv in self._conversations.values():
            for msg in conv.messages:
                if msg.message_id == message_id:
                    msg.status = new_status

                    if status == "failed":
                        errors = status_data.get("errors", [])
                        if errors:
                            msg.error_code = errors[0].get("code")
                            msg.error_message = errors[0].get("message")

                    for handler in self._status_handlers:
                        try:
                            await handler(message_id, new_status)
                        except Exception as e:
                            logger.error(f"Status handler error: {e}")
                    return

    # ========================================================================
    # CONVERSATION TRACKING
    # ========================================================================

    def _track_message(self, message: Message) -> None:
        """Track message in conversation history."""
        wa_id = message.wa_id

        if wa_id not in self._conversations:
            self._conversations[wa_id] = Conversation(
                conversation_id=f"conv_{wa_id}_{datetime.utcnow().timestamp()}",
                wa_id=wa_id,
                started_at=message.timestamp,
                expires_at=message.timestamp + timedelta(hours=24),
            )

        conv = self._conversations[wa_id]
        conv.messages.append(message)

        # Update expiry on user message
        if not message.is_outbound:
            conv.expires_at = message.timestamp + timedelta(hours=24)

    def get_conversation(self, wa_id: str) -> Optional[Conversation]:
        """Get conversation history for a contact."""
        return self._conversations.get(wa_id)

    async def mark_conversion(
        self, wa_id: str, value: float, currency: str = "USD", event_name: str = "Purchase"
    ) -> dict[str, Any]:
        """
        Mark a WhatsApp conversation as converted.

        This tracks the conversion locally AND sends it to Meta CAPI
        for attribution to Click-to-WhatsApp ads.

        Args:
            wa_id: WhatsApp ID of the converted user
            value: Conversion value
            currency: Currency code
            event_name: Conversion event type

        Returns:
            Result from Meta CAPI
        """
        conv = self._conversations.get(wa_id)
        if conv:
            conv.is_converted = True
            conv.conversion_value = value
            conv.conversion_time = datetime.utcnow()

        # Send to Meta CAPI for attribution
        # This requires the Meta Pixel ID in credentials
        pixel_id = self.credentials.get("pixel_id")
        if not pixel_id:
            logger.warning("No pixel_id configured, conversion not sent to CAPI")
            return {"tracked_locally": True, "sent_to_capi": False}

        # Build CAPI payload
        capi_payload = {
            "data": [
                {
                    "event_name": event_name,
                    "event_time": int(datetime.utcnow().timestamp()),
                    "action_source": "chat",  # Special source for WhatsApp
                    "messaging_channel": "whatsapp",
                    "user_data": {
                        "ph": hashlib.sha256(self._normalize_phone(wa_id).encode()).hexdigest()
                    },
                    "custom_data": {"value": value, "currency": currency},
                }
            ]
        }

        # Add attribution data if available
        if conv and conv.ad_id:
            capi_payload["data"][0]["user_data"]["fbc"] = f"fb.1.{conv.ad_id}"

        url = f"{self.BASE_URL}/{pixel_id}/events"
        params = {"access_token": self.access_token}

        try:
            response = requests.post(url, params=params, json=capi_payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"WhatsApp conversion tracked: {wa_id} = {currency} {value}")
            return {
                "tracked_locally": True,
                "sent_to_capi": True,
                "events_received": result.get("events_received", 0),
            }

        except requests.RequestException as e:
            logger.error(f"Failed to send WhatsApp conversion to CAPI: {e}")
            return {"tracked_locally": True, "sent_to_capi": False, "error": str(e)}

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    async def get_analytics(
        self, start_date: datetime, end_date: datetime, granularity: str = "DAY"
    ) -> dict[str, Any]:
        """
        Fetch WhatsApp Business analytics.

        Returns metrics like:
        - Messages sent/delivered/read
        - Conversations by type
        - Cost per conversation
        """
        self._ensure_initialized()

        await self.rate_limiter.acquire()
        response = self._make_request(
            "GET",
            f"/{self.business_account_id}/analytics",
            params={
                "start": int(start_date.timestamp()),
                "end": int(end_date.timestamp()),
                "granularity": granularity,
                "metric_types": "SENT,DELIVERED,READ,CONVERSATION",
            },
        )

        return response

    async def get_conversation_analytics(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """
        Fetch conversation-based analytics for billing insights.

        Returns breakdown by conversation category:
        - Marketing conversations
        - Utility conversations
        - Service conversations
        - Total cost
        """
        self._ensure_initialized()

        await self.rate_limiter.acquire()
        response = self._make_request(
            "GET",
            f"/{self.business_account_id}/conversation_analytics",
            params={
                "start": int(start_date.timestamp()),
                "end": int(end_date.timestamp()),
                "granularity": "DAILY",
                "dimension": "CONVERSATION_CATEGORY",
            },
        )

        return response

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _ensure_initialized(self) -> None:
        """Verify adapter is ready."""
        if not self._initialized:
            raise AdapterError("WhatsApp adapter not initialized")

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to WhatsApp format."""
        import re

        # Remove all non-digits
        digits = re.sub(r"\D", "", phone)
        # WhatsApp expects no leading +
        return digits

    def _make_request(
        self, method: str, endpoint: str, params: Optional[dict] = None, data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make HTTP request to WhatsApp API."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, params=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                response = requests.request(method, url, headers=headers, json=data)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            error_data = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                except (json.JSONDecodeError, ValueError):
                    pass

            error_msg = error_data.get("error", {}).get("message", str(e))
            raise PlatformError(f"WhatsApp API error: {error_msg}")

    # ========================================================================
    # BaseAdapter INTERFACE (Partial - WhatsApp is different)
    # ========================================================================

    async def get_accounts(self):
        """Not applicable for WhatsApp."""
        return []

    async def get_campaigns(self, account_id, status_filter=None):
        """Not applicable for WhatsApp."""
        return []

    async def get_adsets(self, account_id, campaign_id=None):
        """Not applicable for WhatsApp."""
        return []

    async def get_ads(self, account_id, adset_id=None):
        """Not applicable for WhatsApp."""
        return []

    async def get_metrics(
        self, account_id, entity_type, entity_ids, date_start, date_end, breakdown=None
    ):
        """Use get_analytics() instead."""
        return await self.get_analytics(date_start, date_end)

    async def get_emq_scores(self, account_id):
        """Not directly applicable - WhatsApp quality is in template quality scores."""
        templates = await self.get_templates()
        return [{"template": t.name, "quality": t.quality_score} for t in templates]

    async def execute_action(self, action):
        """Not applicable for WhatsApp."""
        raise NotImplementedError("WhatsApp doesn't support ad automation actions")
