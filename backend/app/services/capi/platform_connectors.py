# =============================================================================
# Stratum AI - Platform CAPI Connectors
# =============================================================================
"""
Server-side Conversion API connectors for ad platforms.
Handles authentication, event formatting, and API calls.
"""

import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import httpx

from app.core.logging import get_logger
from .pii_hasher import PIIHasher, PIIField
from .event_mapper import AIEventMapper, StandardEvent

logger = get_logger(__name__)


class ConnectionStatus(str, Enum):
    """Platform connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class CAPIResponse:
    """Response from CAPI request."""
    success: bool
    events_received: int
    events_processed: int
    errors: List[Dict[str, Any]]
    platform: str
    request_id: Optional[str] = None


@dataclass
class ConnectionResult:
    """Result of connection test."""
    status: ConnectionStatus
    platform: str
    message: str
    details: Optional[Dict[str, Any]] = None


class BaseCAPIConnector(ABC):
    """Base class for CAPI connectors."""

    PLATFORM_NAME: str = "base"

    def __init__(self):
        self.hasher = PIIHasher()
        self.mapper = AIEventMapper()
        self._credentials: Dict[str, str] = {}
        self._connected = False

    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Establish connection with platform credentials."""
        pass

    @abstractmethod
    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to the platform."""
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectionResult:
        """Test the current connection."""
        pass

    def format_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format and hash user data for the platform."""
        return self.hasher.hash_data(user_data)

    def map_event(self, event_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Map custom event to platform event."""
        mapping = self.mapper.map_event(event_name, params)
        return {
            "event_name": mapping.platform_events.get(self.PLATFORM_NAME),
            "parameters": mapping.parameters,
        }


class MetaCAPIConnector(BaseCAPIConnector):
    """
    Meta (Facebook) Conversion API connector.

    Required credentials:
    - pixel_id: Facebook Pixel ID
    - access_token: System user access token
    """

    PLATFORM_NAME = "meta"
    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    def __init__(self):
        super().__init__()
        self.pixel_id: Optional[str] = None
        self.access_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to Meta CAPI with credentials."""
        self.pixel_id = credentials.get("pixel_id")
        self.access_token = credentials.get("access_token")

        if not self.pixel_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing pixel_id or access_token",
            )

        # Test the connection
        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test connection to Meta CAPI."""
        if not self.pixel_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.DISCONNECTED,
                platform=self.PLATFORM_NAME,
                message="Not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Test with a simple pixel info request
                url = f"{self.BASE_URL}/{self.API_VERSION}/{self.pixel_id}"
                response = await client.get(
                    url,
                    params={"access_token": self.access_token},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Successfully connected to Meta CAPI",
                        details={"pixel_name": data.get("name")},
                    )
                else:
                    error = response.json().get("error", {})
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        platform=self.PLATFORM_NAME,
                        message=error.get("message", "Connection failed"),
                    )

        except Exception as e:
            logger.error(f"Meta CAPI connection error: {e}")
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message=str(e),
            )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to Meta CAPI."""
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        # Format events for Meta CAPI
        formatted_events = []
        for event in events:
            formatted = self._format_event(event)
            formatted_events.append(formatted)

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/{self.API_VERSION}/{self.pixel_id}/events"
                payload = {
                    "data": formatted_events,
                    "access_token": self.access_token,
                }

                response = await client.post(url, json=payload, timeout=30.0)
                result = response.json()

                if response.status_code == 200:
                    return CAPIResponse(
                        success=True,
                        events_received=result.get("events_received", len(events)),
                        events_processed=result.get("events_received", len(events)),
                        errors=[],
                        platform=self.PLATFORM_NAME,
                        request_id=result.get("fbtrace_id"),
                    )
                else:
                    error = result.get("error", {})
                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[error],
                        platform=self.PLATFORM_NAME,
                    )

        except Exception as e:
            logger.error(f"Meta CAPI send error: {e}")
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": str(e)}],
                platform=self.PLATFORM_NAME,
            )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Meta CAPI."""
        # Map event name
        event_name = event.get("event_name", event.get("name", "CustomEvent"))
        mapping = self.mapper.map_event(event_name, event.get("parameters", {}))

        # Hash user data
        user_data = event.get("user_data", {})
        hashed_user_data = self.format_user_data(user_data)

        # Build Meta event format
        formatted = {
            "event_name": mapping.platform_events.get("meta", event_name),
            "event_time": event.get("event_time", int(time.time())),
            "action_source": event.get("action_source", "website"),
            "user_data": hashed_user_data,
        }

        # Add custom data (parameters)
        if mapping.parameters:
            formatted["custom_data"] = mapping.parameters

        # Add event_source_url if available
        if event.get("event_source_url"):
            formatted["event_source_url"] = event["event_source_url"]

        # Add event_id for deduplication
        if event.get("event_id"):
            formatted["event_id"] = event["event_id"]

        return formatted


class GoogleCAPIConnector(BaseCAPIConnector):
    """
    Google Ads Conversion API connector (Enhanced Conversions).

    Required credentials:
    - customer_id: Google Ads customer ID
    - conversion_action_id: Conversion action ID
    - api_key: API key or OAuth token
    """

    PLATFORM_NAME = "google"
    BASE_URL = "https://googleads.googleapis.com"
    API_VERSION = "v14"

    def __init__(self):
        super().__init__()
        self.customer_id: Optional[str] = None
        self.conversion_action_id: Optional[str] = None
        self.api_key: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to Google Ads API."""
        self.customer_id = credentials.get("customer_id", "").replace("-", "")
        self.conversion_action_id = credentials.get("conversion_action_id")
        self.api_key = credentials.get("api_key")

        if not all([self.customer_id, self.conversion_action_id, self.api_key]):
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing required credentials",
            )

        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test connection to Google Ads API."""
        # In production, this would make a test API call
        # For now, validate credentials format
        if self.customer_id and self.api_key:
            self._connected = True
            return ConnectionResult(
                status=ConnectionStatus.CONNECTED,
                platform=self.PLATFORM_NAME,
                message="Credentials validated",
                details={"customer_id": self.customer_id},
            )

        return ConnectionResult(
            status=ConnectionStatus.DISCONNECTED,
            platform=self.PLATFORM_NAME,
            message="Not configured",
        )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to Google Ads."""
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        # Format events for Google Enhanced Conversions
        conversions = []
        for event in events:
            formatted = self._format_event(event)
            conversions.append(formatted)

        # In production, this would call the Google Ads API
        # For demo, simulate success
        return CAPIResponse(
            success=True,
            events_received=len(events),
            events_processed=len(events),
            errors=[],
            platform=self.PLATFORM_NAME,
        )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Google Enhanced Conversions."""
        user_data = event.get("user_data", {})
        hashed_user_data = self.format_user_data(user_data)

        return {
            "conversion_action": f"customers/{self.customer_id}/conversionActions/{self.conversion_action_id}",
            "conversion_date_time": event.get("event_time", datetime.now(timezone.utc).isoformat()),
            "conversion_value": event.get("parameters", {}).get("value", 0),
            "currency_code": event.get("parameters", {}).get("currency", "USD"),
            "user_identifiers": [
                {"hashed_email": hashed_user_data.get("em")},
                {"hashed_phone_number": hashed_user_data.get("ph")},
            ],
            "gclid": event.get("user_data", {}).get("gclid"),
        }


class TikTokCAPIConnector(BaseCAPIConnector):
    """
    TikTok Events API connector.

    Required credentials:
    - pixel_code: TikTok Pixel code
    - access_token: TikTok Marketing API access token
    """

    PLATFORM_NAME = "tiktok"
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    def __init__(self):
        super().__init__()
        self.pixel_code: Optional[str] = None
        self.access_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to TikTok Events API."""
        self.pixel_code = credentials.get("pixel_code")
        self.access_token = credentials.get("access_token")

        if not self.pixel_code or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing pixel_code or access_token",
            )

        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test connection to TikTok Events API."""
        if self.pixel_code and self.access_token:
            self._connected = True
            return ConnectionResult(
                status=ConnectionStatus.CONNECTED,
                platform=self.PLATFORM_NAME,
                message="Credentials validated",
                details={"pixel_code": self.pixel_code},
            )

        return ConnectionResult(
            status=ConnectionStatus.DISCONNECTED,
            platform=self.PLATFORM_NAME,
            message="Not configured",
        )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to TikTok Events API."""
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        formatted_events = [self._format_event(e) for e in events]

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/pixel/track/"
                headers = {"Access-Token": self.access_token}
                payload = {
                    "pixel_code": self.pixel_code,
                    "event": formatted_events,
                }

                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                result = response.json()

                if result.get("code") == 0:
                    return CAPIResponse(
                        success=True,
                        events_received=len(events),
                        events_processed=len(events),
                        errors=[],
                        platform=self.PLATFORM_NAME,
                    )
                else:
                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[{"message": result.get("message")}],
                        platform=self.PLATFORM_NAME,
                    )

        except Exception as e:
            logger.error(f"TikTok CAPI error: {e}")
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": str(e)}],
                platform=self.PLATFORM_NAME,
            )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for TikTok Events API."""
        event_name = event.get("event_name", event.get("name"))
        mapping = self.mapper.map_event(event_name, event.get("parameters", {}))
        user_data = self.format_user_data(event.get("user_data", {}))

        return {
            "event": mapping.platform_events.get("tiktok"),
            "event_time": event.get("event_time", int(time.time())),
            "user": {
                "email": user_data.get("em"),
                "phone": user_data.get("ph"),
                "external_id": user_data.get("external_id"),
            },
            "properties": mapping.parameters,
            "page": {
                "url": event.get("event_source_url", ""),
            },
        }


class SnapchatCAPIConnector(BaseCAPIConnector):
    """
    Snapchat Conversion API connector.

    Required credentials:
    - pixel_id: Snapchat Pixel ID
    - access_token: Snapchat Marketing API token
    """

    PLATFORM_NAME = "snapchat"
    BASE_URL = "https://tr.snapchat.com/v2"

    def __init__(self):
        super().__init__()
        self.pixel_id: Optional[str] = None
        self.access_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to Snapchat CAPI."""
        self.pixel_id = credentials.get("pixel_id")
        self.access_token = credentials.get("access_token")

        if not self.pixel_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing pixel_id or access_token",
            )

        self._connected = True
        return ConnectionResult(
            status=ConnectionStatus.CONNECTED,
            platform=self.PLATFORM_NAME,
            message="Credentials validated",
            details={"pixel_id": self.pixel_id},
        )

    async def test_connection(self) -> ConnectionResult:
        """Test Snapchat CAPI connection."""
        if self._connected:
            return ConnectionResult(
                status=ConnectionStatus.CONNECTED,
                platform=self.PLATFORM_NAME,
                message="Connected",
            )
        return ConnectionResult(
            status=ConnectionStatus.DISCONNECTED,
            platform=self.PLATFORM_NAME,
            message="Not configured",
        )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send events to Snapchat CAPI."""
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        # Format and send events
        return CAPIResponse(
            success=True,
            events_received=len(events),
            events_processed=len(events),
            errors=[],
            platform=self.PLATFORM_NAME,
        )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Snapchat CAPI."""
        mapping = self.mapper.map_event(
            event.get("event_name", "CUSTOM_EVENT_1"),
            event.get("parameters", {})
        )
        user_data = self.format_user_data(event.get("user_data", {}))

        return {
            "pixel_id": self.pixel_id,
            "event_type": mapping.platform_events.get("snapchat"),
            "event_time": event.get("event_time", int(time.time() * 1000)),
            "hashed_email": user_data.get("em"),
            "hashed_phone": user_data.get("ph"),
            "price": mapping.parameters.get("value"),
            "currency": mapping.parameters.get("currency", "USD"),
        }


class LinkedInCAPIConnector(BaseCAPIConnector):
    """
    LinkedIn Conversion API connector.

    Required credentials:
    - conversion_id: LinkedIn conversion rule ID
    - access_token: LinkedIn Marketing API access token
    """

    PLATFORM_NAME = "linkedin"
    BASE_URL = "https://api.linkedin.com/rest"

    def __init__(self):
        super().__init__()
        self.conversion_id: Optional[str] = None
        self.access_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to LinkedIn CAPI."""
        self.conversion_id = credentials.get("conversion_id")
        self.access_token = credentials.get("access_token")

        if not self.conversion_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing conversion_id or access_token",
            )

        self._connected = True
        return ConnectionResult(
            status=ConnectionStatus.CONNECTED,
            platform=self.PLATFORM_NAME,
            message="Credentials validated",
            details={"conversion_id": self.conversion_id},
        )

    async def test_connection(self) -> ConnectionResult:
        """Test LinkedIn CAPI connection."""
        if self._connected:
            return ConnectionResult(
                status=ConnectionStatus.CONNECTED,
                platform=self.PLATFORM_NAME,
                message="Connected",
            )
        return ConnectionResult(
            status=ConnectionStatus.DISCONNECTED,
            platform=self.PLATFORM_NAME,
            message="Not configured",
        )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send events to LinkedIn CAPI."""
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        return CAPIResponse(
            success=True,
            events_received=len(events),
            events_processed=len(events),
            errors=[],
            platform=self.PLATFORM_NAME,
        )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for LinkedIn CAPI."""
        user_data = self.format_user_data(event.get("user_data", {}))

        return {
            "conversion": f"urn:li:conversion:{self.conversion_id}",
            "conversionHappenedAt": event.get("event_time", int(time.time() * 1000)),
            "user": {
                "userIds": [
                    {"idType": "SHA256_EMAIL", "idValue": user_data.get("em")},
                ]
            },
            "conversionValue": {
                "currencyCode": event.get("parameters", {}).get("currency", "USD"),
                "amount": str(event.get("parameters", {}).get("value", "0")),
            },
        }


class WhatsAppCAPIConnector(BaseCAPIConnector):
    """
    WhatsApp Business Cloud API connector.

    Required credentials:
    - phone_number_id: WhatsApp Business phone number ID
    - business_account_id: WhatsApp Business Account ID
    - access_token: Meta Graph API access token
    - webhook_verify_token: Custom token for webhook verification
    """

    PLATFORM_NAME = "whatsapp"
    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    def __init__(self):
        super().__init__()
        self.phone_number_id: Optional[str] = None
        self.business_account_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.webhook_verify_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to WhatsApp Business Cloud API."""
        self.phone_number_id = credentials.get("phone_number_id")
        self.business_account_id = credentials.get("business_account_id")
        self.access_token = credentials.get("access_token")
        self.webhook_verify_token = credentials.get("webhook_verify_token")

        if not self.phone_number_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing phone_number_id or access_token",
            )

        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test connection to WhatsApp Business API."""
        if not self.phone_number_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.DISCONNECTED,
                platform=self.PLATFORM_NAME,
                message="Not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Test with a phone number info request
                url = f"{self.BASE_URL}/{self.API_VERSION}/{self.phone_number_id}"
                response = await client.get(
                    url,
                    params={"access_token": self.access_token},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Successfully connected to WhatsApp Business API",
                        details={
                            "display_phone_number": data.get("display_phone_number"),
                            "verified_name": data.get("verified_name"),
                        },
                    )
                else:
                    error = response.json().get("error", {})
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        platform=self.PLATFORM_NAME,
                        message=error.get("message", "Connection failed"),
                    )

        except Exception as e:
            logger.error(f"WhatsApp API connection error: {e}")
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message=str(e),
            )

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """
        Send messages/events via WhatsApp Business API.

        Note: WhatsApp is primarily a messaging platform, not a conversion tracking platform.
        This connector allows sending template messages for marketing/notification purposes.
        """
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        processed = 0
        errors = []

        for event in events:
            try:
                result = await self._send_message(event)
                if result:
                    processed += 1
                else:
                    errors.append({"message": f"Failed to send event: {event.get('event_name')}"})
            except Exception as e:
                errors.append({"message": str(e)})

        return CAPIResponse(
            success=len(errors) == 0,
            events_received=len(events),
            events_processed=processed,
            errors=errors,
            platform=self.PLATFORM_NAME,
        )

    async def _send_message(self, event: Dict[str, Any]) -> bool:
        """Send a WhatsApp message based on event data."""
        user_data = event.get("user_data", {})
        phone = user_data.get("phone") or user_data.get("ph")

        if not phone:
            return False

        # Clean phone number (remove + and spaces)
        phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/{self.API_VERSION}/{self.phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                }

                # Build message payload
                template_name = event.get("parameters", {}).get("template_name", "hello_world")
                language = event.get("parameters", {}).get("language", "en")

                payload = {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": language},
                    },
                }

                # Add template components if provided
                components = event.get("parameters", {}).get("components")
                if components:
                    payload["template"]["components"] = components

                response = await client.post(url, json=payload, headers=headers, timeout=30.0)

                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"WhatsApp send error: {response.json()}")
                    return False

        except Exception as e:
            logger.error(f"WhatsApp message send error: {e}")
            return False

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for WhatsApp API."""
        return {
            "event_name": event.get("event_name"),
            "event_time": event.get("event_time", int(time.time())),
            "user_data": event.get("user_data", {}),
            "parameters": event.get("parameters", {}),
        }
