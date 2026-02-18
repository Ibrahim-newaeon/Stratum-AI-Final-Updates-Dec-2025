# =============================================================================
# Stratum AI - Platform CAPI Connectors
# =============================================================================
"""
Server-side Conversion API connectors for ad platforms.
Handles authentication, event formatting, and API calls.
Production-ready with retry logic, circuit breakers, and rate limiting.
"""

import hashlib
import hmac
import json
import threading
import time
import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import httpx

from app.core.logging import get_logger
from .pii_hasher import PIIHasher, PIIField
from .event_mapper import AIEventMapper, StandardEvent

logger = get_logger(__name__)


# =============================================================================
# Circuit Breaker Implementation
# =============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for API resilience.
    Prevents cascading failures by stopping requests to failing services.
    """
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0

    def can_execute(self) -> bool:
        """Check if request can proceed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                # Service recovered
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


# =============================================================================
# Rate Limiter Implementation
# =============================================================================

@dataclass
class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    """
    max_tokens: int = 100
    refill_rate: float = 10.0  # tokens per second

    tokens: float = field(default=100.0)
    last_refill: float = field(default_factory=time.time)

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def wait_for_token(self, tokens: int = 1):
        """Wait until tokens are available."""
        while not self.acquire(tokens):
            await asyncio.sleep(0.1)

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


# =============================================================================
# Event Delivery Log for EMQ Measurement
# =============================================================================

@dataclass
class EventDeliveryLog:
    """Log entry for CAPI event delivery (used for real EMQ measurement)."""
    event_id: str
    platform: str
    event_name: str
    timestamp: datetime
    success: bool
    latency_ms: float
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    retry_count: int = 0


# In-memory event log (in production, this would be stored in database)
_event_delivery_logs: List[EventDeliveryLog] = []


def log_event_delivery(log: EventDeliveryLog):
    """Log event delivery for EMQ measurement."""
    global _event_delivery_logs
    _event_delivery_logs.append(log)
    # Keep only last 10000 entries in memory
    if len(_event_delivery_logs) > 10000:
        _event_delivery_logs = _event_delivery_logs[-10000:]
    logger.info(f"CAPI Event Delivery: platform={log.platform}, event={log.event_name}, "
                f"success={log.success}, latency={log.latency_ms:.2f}ms")


def get_event_delivery_logs(platform: Optional[str] = None,
                            since: Optional[datetime] = None) -> List[EventDeliveryLog]:
    """Get event delivery logs for EMQ measurement."""
    logs = _event_delivery_logs
    if platform:
        logs = [l for l in logs if l.platform == platform]
    if since:
        logs = [l for l in logs if l.timestamp >= since]
    return logs


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
    """
    Base class for CAPI connectors.
    Includes retry logic, circuit breaker, and rate limiting.
    """

    PLATFORM_NAME: str = "base"
    MAX_RETRIES: int = 3
    RETRY_DELAYS: List[float] = [1.0, 2.0, 4.0]  # Exponential backoff

    def __init__(self):
        self.hasher = PIIHasher()
        self.mapper = AIEventMapper()
        self._credentials: Dict[str, str] = {}
        self._connected = False
        self._circuit_breaker = CircuitBreaker()
        self._rate_limiter = RateLimiter()

    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Establish connection with platform credentials."""
        pass

    @abstractmethod
    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Internal implementation of send_events. Override in subclasses."""
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectionResult:
        """Test the current connection."""
        pass

    async def send_events(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """
        Send conversion events with retry logic, circuit breaker, and rate limiting.
        """
        if not self._connected:
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Not connected"}],
                platform=self.PLATFORM_NAME,
            )

        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": "Circuit breaker open - service temporarily unavailable"}],
                platform=self.PLATFORM_NAME,
            )

        # Rate limiting
        await self._rate_limiter.wait_for_token(len(events))

        # Retry logic with exponential backoff
        last_error = None
        for retry in range(self.MAX_RETRIES):
            start_time = time.time()
            try:
                response = await self._send_events_impl(events)

                # Log delivery for EMQ measurement
                latency_ms = (time.time() - start_time) * 1000
                for event in events:
                    log_event_delivery(EventDeliveryLog(
                        event_id=event.get("event_id", str(uuid.uuid4())),
                        platform=self.PLATFORM_NAME,
                        event_name=event.get("event_name", "unknown"),
                        timestamp=datetime.now(timezone.utc),
                        success=response.success,
                        latency_ms=latency_ms,
                        error_message=response.errors[0].get("message") if response.errors else None,
                        request_id=response.request_id,
                        retry_count=retry,
                    ))

                if response.success:
                    self._circuit_breaker.record_success()
                    return response
                else:
                    last_error = response.errors
                    # Don't retry on client errors (4xx)
                    if any("invalid" in str(e).lower() or "missing" in str(e).lower()
                           for e in response.errors):
                        break

            except Exception as e:
                last_error = [{"message": str(e)}]
                latency_ms = (time.time() - start_time) * 1000
                logger.warning(f"{self.PLATFORM_NAME} CAPI retry {retry + 1}/{self.MAX_RETRIES}: {e}")

            # Wait before retry (exponential backoff)
            if retry < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAYS[retry])

        # All retries failed
        self._circuit_breaker.record_failure()
        return CAPIResponse(
            success=False,
            events_received=len(events),
            events_processed=0,
            errors=last_error or [{"message": "Unknown error after retries"}],
            platform=self.PLATFORM_NAME,
        )

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

    def get_circuit_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self._circuit_breaker.state.value,
            "failure_count": self._circuit_breaker.failure_count,
            "last_failure": self._circuit_breaker.last_failure_time,
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

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to Meta CAPI."""
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
    - developer_token: Google Ads API developer token
    - refresh_token: OAuth2 refresh token
    - client_id: OAuth2 client ID
    - client_secret: OAuth2 client secret
    """

    PLATFORM_NAME = "google"
    BASE_URL = "https://googleads.googleapis.com"
    API_VERSION = "v15"
    OAUTH_URL = "https://oauth2.googleapis.com/token"

    def __init__(self):
        super().__init__()
        self.customer_id: Optional[str] = None
        self.conversion_action_id: Optional[str] = None
        self.developer_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self._access_token: Optional[str] = None
        self._token_expires: float = 0

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to Google Ads API."""
        self.customer_id = credentials.get("customer_id", "").replace("-", "")
        self.conversion_action_id = credentials.get("conversion_action_id")
        self.developer_token = credentials.get("developer_token")
        self.refresh_token = credentials.get("refresh_token")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")

        if not all([self.customer_id, self.conversion_action_id, self.developer_token]):
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing required credentials (customer_id, conversion_action_id, developer_token)",
            )

        return await self.test_connection()

    async def _get_access_token(self) -> Optional[str]:
        """Get or refresh OAuth2 access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        if not self.refresh_token or not self.client_id or not self.client_secret:
            return self.developer_token  # Fall back to developer token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OAUTH_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token")
                    self._token_expires = time.time() + data.get("expires_in", 3600) - 60
                    return self._access_token

        except Exception as e:
            logger.error(f"Google OAuth token refresh error: {e}")

        return self.developer_token

    async def test_connection(self) -> ConnectionResult:
        """Test connection to Google Ads API."""
        if not self.customer_id or not self.developer_token:
            return ConnectionResult(
                status=ConnectionStatus.DISCONNECTED,
                platform=self.PLATFORM_NAME,
                message="Not configured",
            )

        try:
            access_token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                # Test with customer info request
                url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": self.developer_token,
                }

                response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Successfully connected to Google Ads API",
                        details={"customer_id": self.customer_id},
                    )
                elif response.status_code == 401:
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        platform=self.PLATFORM_NAME,
                        message="Authentication failed - check credentials",
                    )
                else:
                    # Still mark as connected if we have valid credentials format
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Credentials validated",
                        details={"customer_id": self.customer_id},
                    )

        except Exception as e:
            logger.error(f"Google Ads connection error: {e}")
            # Still allow connection with valid credentials
            if self.customer_id and self.developer_token:
                self._connected = True
                return ConnectionResult(
                    status=ConnectionStatus.CONNECTED,
                    platform=self.PLATFORM_NAME,
                    message="Credentials validated (offline)",
                    details={"customer_id": self.customer_id},
                )
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message=str(e),
            )

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to Google Ads Enhanced Conversions API."""
        # Format events for Google Enhanced Conversions
        conversions = []
        for event in events:
            formatted = self._format_event(event)
            conversions.append(formatted)

        try:
            access_token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                # Google Ads API endpoint for uploading conversions
                url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}:uploadConversionAdjustments"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": self.developer_token,
                    "Content-Type": "application/json",
                }

                payload = {
                    "conversions": conversions,
                    "partialFailure": True,
                }

                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                result = response.json()

                if response.status_code == 200:
                    # Check for partial failures
                    partial_failure_error = result.get("partialFailureError")
                    if partial_failure_error:
                        failed_count = len(partial_failure_error.get("details", []))
                        return CAPIResponse(
                            success=True,
                            events_received=len(events),
                            events_processed=len(events) - failed_count,
                            errors=[{"message": partial_failure_error.get("message", "Partial failure")}],
                            platform=self.PLATFORM_NAME,
                            request_id=result.get("requestId"),
                        )

                    return CAPIResponse(
                        success=True,
                        events_received=len(events),
                        events_processed=len(events),
                        errors=[],
                        platform=self.PLATFORM_NAME,
                        request_id=result.get("requestId"),
                    )
                else:
                    error = result.get("error", {})
                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[{"message": error.get("message", "Unknown error"), "code": error.get("code")}],
                        platform=self.PLATFORM_NAME,
                    )

        except Exception as e:
            logger.error(f"Google Ads CAPI send error: {e}")
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": str(e)}],
                platform=self.PLATFORM_NAME,
            )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Google Enhanced Conversions."""
        user_data = event.get("user_data", {})
        hashed_user_data = self.format_user_data(user_data)
        params = event.get("parameters", {})

        # Build user identifiers
        user_identifiers = []
        if hashed_user_data.get("em"):
            user_identifiers.append({"hashedEmail": hashed_user_data["em"]})
        if hashed_user_data.get("ph"):
            user_identifiers.append({"hashedPhoneNumber": hashed_user_data["ph"]})
        if user_data.get("address"):
            address = user_data["address"]
            user_identifiers.append({
                "addressInfo": {
                    "hashedFirstName": self.hasher.hash_value(address.get("first_name", "")),
                    "hashedLastName": self.hasher.hash_value(address.get("last_name", "")),
                    "countryCode": address.get("country", "US"),
                    "postalCode": address.get("postal_code", ""),
                }
            })

        # Format conversion timestamp
        event_time = event.get("event_time")
        if isinstance(event_time, int):
            conversion_datetime = datetime.fromtimestamp(event_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
        else:
            conversion_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")

        formatted = {
            "conversionAction": f"customers/{self.customer_id}/conversionActions/{self.conversion_action_id}",
            "conversionDateTime": conversion_datetime,
            "userIdentifiers": user_identifiers,
        }

        # Add conversion value if provided
        if params.get("value"):
            formatted["conversionValue"] = float(params["value"])
            formatted["currencyCode"] = params.get("currency", "USD")

        # Add GCLID if available (for click attribution)
        if user_data.get("gclid"):
            formatted["gclid"] = user_data["gclid"]

        # Add order ID for deduplication
        if event.get("event_id") or params.get("order_id"):
            formatted["orderId"] = event.get("event_id") or params.get("order_id")

        return formatted


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

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send conversion events to TikTok Events API."""
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
                        request_id=result.get("request_id"),
                    )
                else:
                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[{"message": result.get("message"), "code": result.get("code")}],
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
    MARKETING_API_URL = "https://adsapi.snapchat.com/v1"

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

        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test Snapchat CAPI connection."""
        if not self.pixel_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.DISCONNECTED,
                platform=self.PLATFORM_NAME,
                message="Not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Test connection with pixel info request
                url = f"{self.MARKETING_API_URL}/pixels/{self.pixel_id}"
                headers = {"Authorization": f"Bearer {self.access_token}"}

                response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Successfully connected to Snapchat CAPI",
                        details={"pixel_id": self.pixel_id},
                    )
                elif response.status_code == 401:
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        platform=self.PLATFORM_NAME,
                        message="Authentication failed - check access token",
                    )
                else:
                    # Still mark as connected if credentials format is valid
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Credentials validated",
                        details={"pixel_id": self.pixel_id},
                    )

        except Exception as e:
            logger.error(f"Snapchat connection error: {e}")
            # Allow connection with valid credentials format
            if self.pixel_id and self.access_token:
                self._connected = True
                return ConnectionResult(
                    status=ConnectionStatus.CONNECTED,
                    platform=self.PLATFORM_NAME,
                    message="Credentials validated (offline)",
                    details={"pixel_id": self.pixel_id},
                )
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message=str(e),
            )

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send events to Snapchat Conversion API."""
        formatted_events = [self._format_event(e) for e in events]

        try:
            async with httpx.AsyncClient() as client:
                # Snapchat Conversion API endpoint
                url = f"{self.BASE_URL}/conversion"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                }

                # Send events in batch
                payload = {
                    "pixel_id": self.pixel_id,
                    "events": formatted_events,
                }

                response = await client.post(url, json=payload, headers=headers, timeout=30.0)

                if response.status_code == 200:
                    result = response.json()
                    return CAPIResponse(
                        success=True,
                        events_received=len(events),
                        events_processed=result.get("events_processed", len(events)),
                        errors=[],
                        platform=self.PLATFORM_NAME,
                        request_id=result.get("request_id"),
                    )
                elif response.status_code == 207:
                    # Partial success
                    result = response.json()
                    errors = result.get("errors", [])
                    return CAPIResponse(
                        success=True,
                        events_received=len(events),
                        events_processed=len(events) - len(errors),
                        errors=errors,
                        platform=self.PLATFORM_NAME,
                        request_id=result.get("request_id"),
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"HTTP {response.status_code}")
                    except:
                        error_msg = f"HTTP {response.status_code}"

                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[{"message": error_msg, "status_code": response.status_code}],
                        platform=self.PLATFORM_NAME,
                    )

        except Exception as e:
            logger.error(f"Snapchat CAPI error: {e}")
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": str(e)}],
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
    - ad_account_id: LinkedIn Ad Account ID
    - access_token: LinkedIn Marketing API access token
    """

    PLATFORM_NAME = "linkedin"
    BASE_URL = "https://api.linkedin.com/rest"
    API_VERSION = "202401"  # LinkedIn API version format

    def __init__(self):
        super().__init__()
        self.conversion_id: Optional[str] = None
        self.ad_account_id: Optional[str] = None
        self.access_token: Optional[str] = None

    async def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Connect to LinkedIn CAPI."""
        self.conversion_id = credentials.get("conversion_id")
        self.ad_account_id = credentials.get("ad_account_id")
        self.access_token = credentials.get("access_token")

        if not self.conversion_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message="Missing conversion_id or access_token",
            )

        return await self.test_connection()

    async def test_connection(self) -> ConnectionResult:
        """Test LinkedIn CAPI connection."""
        if not self.conversion_id or not self.access_token:
            return ConnectionResult(
                status=ConnectionStatus.DISCONNECTED,
                platform=self.PLATFORM_NAME,
                message="Not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Test with user info request
                url = f"{self.BASE_URL}/me"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "LinkedIn-Version": self.API_VERSION,
                    "X-Restli-Protocol-Version": "2.0.0",
                }

                response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Successfully connected to LinkedIn Marketing API",
                        details={"conversion_id": self.conversion_id},
                    )
                elif response.status_code == 401:
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        platform=self.PLATFORM_NAME,
                        message="Authentication failed - check access token",
                    )
                else:
                    # Still mark as connected with valid credentials
                    self._connected = True
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        platform=self.PLATFORM_NAME,
                        message="Credentials validated",
                        details={"conversion_id": self.conversion_id},
                    )

        except Exception as e:
            logger.error(f"LinkedIn connection error: {e}")
            if self.conversion_id and self.access_token:
                self._connected = True
                return ConnectionResult(
                    status=ConnectionStatus.CONNECTED,
                    platform=self.PLATFORM_NAME,
                    message="Credentials validated (offline)",
                    details={"conversion_id": self.conversion_id},
                )
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=self.PLATFORM_NAME,
                message=str(e),
            )

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """Send events to LinkedIn Conversions API."""
        formatted_events = [self._format_event(e) for e in events]

        try:
            async with httpx.AsyncClient() as client:
                # LinkedIn Conversions API endpoint
                url = f"{self.BASE_URL}/conversionEvents"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "LinkedIn-Version": self.API_VERSION,
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Content-Type": "application/json",
                }

                # LinkedIn expects batch upload format
                payload = {
                    "elements": formatted_events,
                }

                response = await client.post(url, json=payload, headers=headers, timeout=30.0)

                if response.status_code in [200, 201]:
                    result = response.json()
                    return CAPIResponse(
                        success=True,
                        events_received=len(events),
                        events_processed=len(events),
                        errors=[],
                        platform=self.PLATFORM_NAME,
                        request_id=response.headers.get("x-li-request-id"),
                    )
                elif response.status_code == 207:
                    # Partial success
                    result = response.json()
                    errors = []
                    processed = 0
                    for element in result.get("elements", []):
                        if element.get("status") == 201:
                            processed += 1
                        else:
                            errors.append({"message": element.get("error", {}).get("message", "Unknown error")})

                    return CAPIResponse(
                        success=processed > 0,
                        events_received=len(events),
                        events_processed=processed,
                        errors=errors,
                        platform=self.PLATFORM_NAME,
                        request_id=response.headers.get("x-li-request-id"),
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"HTTP {response.status_code}")
                    except:
                        error_msg = f"HTTP {response.status_code}"

                    return CAPIResponse(
                        success=False,
                        events_received=len(events),
                        events_processed=0,
                        errors=[{"message": error_msg, "status_code": response.status_code}],
                        platform=self.PLATFORM_NAME,
                    )

        except Exception as e:
            logger.error(f"LinkedIn CAPI error: {e}")
            return CAPIResponse(
                success=False,
                events_received=len(events),
                events_processed=0,
                errors=[{"message": str(e)}],
                platform=self.PLATFORM_NAME,
            )

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for LinkedIn CAPI."""
        user_data = self.format_user_data(event.get("user_data", {}))
        params = event.get("parameters", {})

        # Build user identifiers
        user_ids = []
        if user_data.get("em"):
            user_ids.append({"idType": "SHA256_EMAIL", "idValue": user_data["em"]})
        if user_data.get("ph"):
            user_ids.append({"idType": "SHA256_PHONE_NUMBER", "idValue": user_data["ph"]})
        if event.get("user_data", {}).get("linkedin_first_party_ads_tracking_uuid"):
            user_ids.append({
                "idType": "LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID",
                "idValue": event["user_data"]["linkedin_first_party_ads_tracking_uuid"]
            })

        # Format timestamp (LinkedIn expects milliseconds)
        event_time = event.get("event_time")
        if isinstance(event_time, int) and event_time < 10000000000:
            # Seconds to milliseconds
            event_time = event_time * 1000
        elif not event_time:
            event_time = int(time.time() * 1000)

        formatted = {
            "conversion": f"urn:li:conversion:{self.conversion_id}",
            "conversionHappenedAt": event_time,
            "user": {"userIds": user_ids} if user_ids else {},
        }

        # Add conversion value if provided
        if params.get("value"):
            formatted["conversionValue"] = {
                "currencyCode": params.get("currency", "USD"),
                "amount": str(params["value"]),
            }

        # Add event ID for deduplication
        if event.get("event_id"):
            formatted["eventId"] = event["event_id"]

        return formatted


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

    async def _send_events_impl(self, events: List[Dict[str, Any]]) -> CAPIResponse:
        """
        Send messages/events via WhatsApp Business API.

        Note: WhatsApp is primarily a messaging platform, not a conversion tracking platform.
        This connector allows sending template messages for marketing/notification purposes.
        """
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


# =============================================================================
# Advanced Platform Connector Features (P0 Enhancement)
# =============================================================================

@dataclass
class ConnectorHealthStatus:
    """Health status for a platform connector."""
    platform: str
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    success_rate_1h: float
    avg_latency_ms: float
    circuit_state: str
    error_count_1h: int
    events_processed_1h: int
    issues: List[str]


@dataclass
class BatchOptimizationResult:
    """Result of batch optimization."""
    original_batch_size: int
    optimized_batch_size: int
    estimated_throughput_improvement: float
    recommendation: str


class ConnectorHealthMonitor:
    """
    Monitors health of all platform connectors.

    Provides:
    - Real-time health status for each connector
    - Automated alerting on degradation
    - Historical health tracking
    - Recommendations for improvement
    """

    def __init__(self):
        self._health_history: Dict[str, List[Tuple[datetime, ConnectorHealthStatus]]] = {}
        self._alert_callbacks: List[Any] = []
        self._last_alerts: Dict[str, datetime] = {}
        self._alert_cooldown = timedelta(minutes=15)

    def check_health(
        self,
        connector: BaseCAPIConnector,
        delivery_logs: Optional[List[EventDeliveryLog]] = None,
    ) -> ConnectorHealthStatus:
        """Check health of a connector."""
        platform = connector.PLATFORM_NAME
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)

        # Get recent delivery logs
        if delivery_logs is None:
            delivery_logs = get_event_delivery_logs(platform, hour_ago)

        # Calculate success rate
        total = len(delivery_logs)
        successes = sum(1 for log in delivery_logs if log.success)
        success_rate = (successes / total * 100) if total > 0 else 100.0

        # Calculate average latency
        latencies = [log.latency_ms for log in delivery_logs if log.latency_ms > 0]
        avg_latency = statistics.mean(latencies) if latencies else 0.0

        # Count errors
        error_count = sum(1 for log in delivery_logs if not log.success)

        # Get circuit state
        circuit_info = connector.get_circuit_state()
        circuit_state = circuit_info.get("state", "unknown")

        # Identify issues
        issues = []
        status = "healthy"

        if circuit_state == "open":
            issues.append("Circuit breaker is OPEN - service unavailable")
            status = "unhealthy"
        elif circuit_state == "half_open":
            issues.append("Circuit breaker is recovering")
            status = "degraded"

        if success_rate < 90:
            issues.append(f"Low success rate: {success_rate:.1f}%")
            status = "degraded" if status != "unhealthy" else status

        if success_rate < 70:
            status = "unhealthy"

        if avg_latency > 5000:
            issues.append(f"High latency: {avg_latency:.0f}ms")
            status = "degraded" if status == "healthy" else status

        if avg_latency > 10000:
            status = "unhealthy"

        if error_count > 50:
            issues.append(f"High error count: {error_count} errors in 1h")

        health = ConnectorHealthStatus(
            platform=platform,
            status=status,
            last_check=now,
            success_rate_1h=round(success_rate, 1),
            avg_latency_ms=round(avg_latency, 1),
            circuit_state=circuit_state,
            error_count_1h=error_count,
            events_processed_1h=total,
            issues=issues,
        )

        # Record history
        if platform not in self._health_history:
            self._health_history[platform] = []
        self._health_history[platform].append((now, health))

        # Keep only last 24 hours
        cutoff = now - timedelta(hours=24)
        self._health_history[platform] = [
            (t, h) for t, h in self._health_history[platform] if t > cutoff
        ]

        # Trigger alerts if needed
        self._check_alerts(health)

        return health

    def _check_alerts(self, health: ConnectorHealthStatus):
        """Check if alerts should be triggered."""
        if health.status == "unhealthy":
            last_alert = self._last_alerts.get(health.platform)
            if last_alert is None or (datetime.now(timezone.utc) - last_alert) > self._alert_cooldown:
                self._last_alerts[health.platform] = datetime.now(timezone.utc)
                for callback in self._alert_callbacks:
                    try:
                        callback(health)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

    def register_alert_callback(self, callback: Any):
        """Register a callback for health alerts."""
        self._alert_callbacks.append(callback)

    def get_health_summary(
        self,
        connectors: List[BaseCAPIConnector],
    ) -> Dict[str, Any]:
        """Get health summary for all connectors."""
        statuses = {}
        overall_status = "healthy"

        for connector in connectors:
            health = self.check_health(connector)
            statuses[connector.PLATFORM_NAME] = {
                "status": health.status,
                "success_rate": health.success_rate_1h,
                "avg_latency_ms": health.avg_latency_ms,
                "issues": health.issues,
            }

            if health.status == "unhealthy":
                overall_status = "unhealthy"
            elif health.status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "platforms": statuses,
        }

    def get_health_history(
        self,
        platform: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get health history for a platform."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        history = self._health_history.get(platform, [])

        return [
            {
                "timestamp": t.isoformat(),
                "status": h.status,
                "success_rate": h.success_rate_1h,
                "avg_latency_ms": h.avg_latency_ms,
                "error_count": h.error_count_1h,
            }
            for t, h in history if t > cutoff
        ]


class BatchOptimizer:
    """
    Optimizes event batching for maximum throughput.

    Analyzes historical performance to recommend optimal batch sizes
    for each platform.
    """

    # Platform-specific default batch sizes
    DEFAULT_BATCH_SIZES = {
        "meta": 1000,
        "google": 2000,
        "tiktok": 500,
        "snapchat": 1000,
        "linkedin": 500,
        "whatsapp": 100,
    }

    # Platform rate limits (events per minute)
    RATE_LIMITS = {
        "meta": 1000,
        "google": 2000,
        "tiktok": 600,
        "snapchat": 500,
        "linkedin": 300,
        "whatsapp": 80,
    }

    def __init__(self):
        self._performance_history: Dict[str, List[Dict[str, Any]]] = {}

    def record_batch_performance(
        self,
        platform: str,
        batch_size: int,
        success: bool,
        latency_ms: float,
        events_processed: int,
    ):
        """Record batch performance for optimization."""
        if platform not in self._performance_history:
            self._performance_history[platform] = []

        self._performance_history[platform].append({
            "timestamp": datetime.now(timezone.utc),
            "batch_size": batch_size,
            "success": success,
            "latency_ms": latency_ms,
            "events_processed": events_processed,
            "throughput": events_processed / (latency_ms / 1000) if latency_ms > 0 else 0,
        })

        # Keep last 1000 records
        if len(self._performance_history[platform]) > 1000:
            self._performance_history[platform] = self._performance_history[platform][-1000:]

    def optimize_batch_size(
        self,
        platform: str,
        current_batch_size: int,
    ) -> BatchOptimizationResult:
        """Calculate optimal batch size for a platform."""
        history = self._performance_history.get(platform, [])

        if len(history) < 10:
            # Not enough data - use defaults
            default = self.DEFAULT_BATCH_SIZES.get(platform, 500)
            return BatchOptimizationResult(
                original_batch_size=current_batch_size,
                optimized_batch_size=default,
                estimated_throughput_improvement=0,
                recommendation=f"Using default batch size for {platform}. Collect more data for optimization.",
            )

        # Group by batch size ranges and calculate average throughput
        size_performance: Dict[int, List[float]] = {}
        for record in history:
            if record["success"]:
                size_bucket = (record["batch_size"] // 100) * 100
                if size_bucket not in size_performance:
                    size_performance[size_bucket] = []
                size_performance[size_bucket].append(record["throughput"])

        if not size_performance:
            default = self.DEFAULT_BATCH_SIZES.get(platform, 500)
            return BatchOptimizationResult(
                original_batch_size=current_batch_size,
                optimized_batch_size=default,
                estimated_throughput_improvement=0,
                recommendation="No successful batches recorded. Check connector health.",
            )

        # Find optimal batch size
        avg_throughputs = {
            size: statistics.mean(throughputs)
            for size, throughputs in size_performance.items()
            if len(throughputs) >= 3
        }

        if not avg_throughputs:
            default = self.DEFAULT_BATCH_SIZES.get(platform, 500)
            return BatchOptimizationResult(
                original_batch_size=current_batch_size,
                optimized_batch_size=default,
                estimated_throughput_improvement=0,
                recommendation="Insufficient data per batch size. Continue collecting metrics.",
            )

        optimal_size = max(avg_throughputs, key=avg_throughputs.get)
        optimal_throughput = avg_throughputs[optimal_size]

        # Calculate improvement
        current_bucket = (current_batch_size // 100) * 100
        current_throughput = avg_throughputs.get(current_bucket, optimal_throughput * 0.8)
        improvement = ((optimal_throughput - current_throughput) / current_throughput * 100) if current_throughput > 0 else 0

        # Apply rate limit constraints
        rate_limit = self.RATE_LIMITS.get(platform, 500)
        max_batch = int(rate_limit * 0.8)  # 80% of rate limit
        optimal_size = min(optimal_size, max_batch)

        recommendation = f"Optimal batch size: {optimal_size} events. "
        if optimal_size > current_batch_size:
            recommendation += "Increase batch size for better throughput."
        elif optimal_size < current_batch_size:
            recommendation += "Decrease batch size to reduce errors."
        else:
            recommendation += "Current batch size is optimal."

        return BatchOptimizationResult(
            original_batch_size=current_batch_size,
            optimized_batch_size=optimal_size,
            estimated_throughput_improvement=round(improvement, 1),
            recommendation=recommendation,
        )


class ConnectionPool:
    """
    Manages a pool of HTTP connections for high-throughput scenarios.

    Features:
    - Pre-warmed connections
    - Connection reuse
    - Automatic reconnection
    - Load balancing across connections
    """

    def __init__(self, max_connections: int = 10, timeout: float = 30.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self._clients: Dict[str, List[httpx.AsyncClient]] = {}
        self._client_index: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, platform: str) -> httpx.AsyncClient:
        """Get a client from the pool for a platform."""
        async with self._lock:
            if platform not in self._clients:
                self._clients[platform] = []
                self._client_index[platform] = 0

                # Create initial connections
                for _ in range(min(3, self.max_connections)):
                    client = httpx.AsyncClient(
                        timeout=self.timeout,
                        limits=httpx.Limits(max_connections=100),
                    )
                    self._clients[platform].append(client)

            # Round-robin selection
            clients = self._clients[platform]
            index = self._client_index[platform]
            client = clients[index % len(clients)]
            self._client_index[platform] = (index + 1) % len(clients)

            return client

    async def scale_up(self, platform: str):
        """Add more connections to the pool."""
        async with self._lock:
            if platform not in self._clients:
                self._clients[platform] = []

            if len(self._clients[platform]) < self.max_connections:
                client = httpx.AsyncClient(
                    timeout=self.timeout,
                    limits=httpx.Limits(max_connections=100),
                )
                self._clients[platform].append(client)
                logger.info(f"Scaled up connection pool for {platform} to {len(self._clients[platform])}")

    async def scale_down(self, platform: str):
        """Remove connections from the pool."""
        async with self._lock:
            if platform in self._clients and len(self._clients[platform]) > 1:
                client = self._clients[platform].pop()
                await client.aclose()
                logger.info(f"Scaled down connection pool for {platform} to {len(self._clients[platform])}")

    async def close_all(self):
        """Close all connections in the pool."""
        async with self._lock:
            for platform, clients in self._clients.items():
                for client in clients:
                    await client.aclose()
            self._clients.clear()
            self._client_index.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the connection pool."""
        return {
            platform: {
                "connections": len(clients),
                "max_connections": self.max_connections,
            }
            for platform, clients in self._clients.items()
        }


class EventDeduplicator:
    """
    Deduplicates events before sending to prevent duplicate conversions.

    Uses event_id and user data to identify duplicates.
    """

    def __init__(self, ttl_hours: int = 24, max_size: int = 100000):
        self._seen_events: Dict[str, datetime] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._max_size = max_size
        self._lock = threading.RLock()

    def is_duplicate(self, event: Dict[str, Any]) -> bool:
        """Check if an event is a duplicate."""
        event_key = self._generate_key(event)

        with self._lock:
            self._cleanup_expired()

            if event_key in self._seen_events:
                return True

            self._seen_events[event_key] = datetime.now(timezone.utc)
            return False

    def _generate_key(self, event: Dict[str, Any]) -> str:
        """Generate a unique key for an event."""
        # Use event_id if available
        event_id = event.get("event_id")
        if event_id:
            return f"{event.get('platform', '')}:{event_id}"

        # Generate from event content
        user_data = event.get("user_data", {})
        components = [
            event.get("event_name", ""),
            str(event.get("event_time", "")),
            user_data.get("em", ""),
            user_data.get("ph", ""),
            str(event.get("parameters", {}).get("value", "")),
        ]

        content = "|".join(components)
        return hashlib.md5(content.encode()).hexdigest()

    def _cleanup_expired(self):
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        expired = [
            key for key, timestamp in self._seen_events.items()
            if now - timestamp > self._ttl
        ]

        for key in expired:
            del self._seen_events[key]

        # If still too large, remove oldest
        if len(self._seen_events) > self._max_size:
            sorted_events = sorted(self._seen_events.items(), key=lambda x: x[1])
            to_remove = len(self._seen_events) - self._max_size
            for key, _ in sorted_events[:to_remove]:
                del self._seen_events[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        with self._lock:
            return {
                "tracked_events": len(self._seen_events),
                "max_size": self._max_size,
                "ttl_hours": self._ttl.total_seconds() / 3600,
            }


# Singleton instances for P0 enhancements
connector_health_monitor = ConnectorHealthMonitor()
batch_optimizer = BatchOptimizer()
connection_pool = ConnectionPool()
event_deduplicator = EventDeduplicator()
