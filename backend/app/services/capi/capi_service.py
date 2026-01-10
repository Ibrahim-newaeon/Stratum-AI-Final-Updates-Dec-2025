# =============================================================================
# Stratum AI - CAPI Service
# =============================================================================
"""
Main Conversion API service that orchestrates platform connections,
event streaming, and data quality analysis.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass

from app.core.logging import get_logger
from .platform_connectors import (
    BaseCAPIConnector,
    MetaCAPIConnector,
    GoogleCAPIConnector,
    TikTokCAPIConnector,
    SnapchatCAPIConnector,
    WhatsAppCAPIConnector,
    ConnectionStatus,
    CAPIResponse,
    ConnectionResult,
)
from .pii_hasher import PIIHasher
from .event_mapper import AIEventMapper
from .data_quality import DataQualityAnalyzer, QualityReport

logger = get_logger(__name__)


@dataclass
class StreamResult:
    """Result of streaming events to platforms."""
    total_events: int
    platforms_sent: int
    platform_results: Dict[str, CAPIResponse]
    failed_platforms: List[str]
    data_quality_score: float


class CAPIService:
    """
    Main service for managing Conversion API integrations.

    Features:
    - Multi-platform connection management
    - Automatic PII hashing
    - AI-powered event mapping
    - Real-time data quality analysis
    - Streaming to multiple platforms simultaneously
    """

    # Platform connector classes
    PLATFORM_CONNECTORS: Dict[str, Type[BaseCAPIConnector]] = {
        "meta": MetaCAPIConnector,
        "google": GoogleCAPIConnector,
        "tiktok": TikTokCAPIConnector,
        "snapchat": SnapchatCAPIConnector,
        "whatsapp": WhatsAppCAPIConnector,
    }

    def __init__(self):
        """Initialize the CAPI service."""
        self.connectors: Dict[str, BaseCAPIConnector] = {}
        self.hasher = PIIHasher()
        self.mapper = AIEventMapper()
        self.analyzer = DataQualityAnalyzer()
        self._event_buffer: List[Dict[str, Any]] = []

    async def connect_platform(
        self, platform: str, credentials: Dict[str, str]
    ) -> ConnectionResult:
        """
        Connect to a platform with the provided credentials.

        Args:
            platform: Platform name (meta, google, tiktok, snapchat)
            credentials: Platform-specific credentials

        Returns:
            ConnectionResult with status and details
        """
        platform = platform.lower()

        if platform not in self.PLATFORM_CONNECTORS:
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=platform,
                message=f"Unsupported platform: {platform}",
            )

        try:
            # Create connector instance
            connector_class = self.PLATFORM_CONNECTORS[platform]
            connector = connector_class()

            # Attempt connection
            result = await connector.connect(credentials)

            if result.status == ConnectionStatus.CONNECTED:
                self.connectors[platform] = connector
                logger.info(f"Successfully connected to {platform} CAPI")

            return result

        except Exception as e:
            logger.error(f"Error connecting to {platform}: {e}")
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                platform=platform,
                message=str(e),
            )

    async def disconnect_platform(self, platform: str) -> bool:
        """Disconnect from a platform."""
        platform = platform.lower()
        if platform in self.connectors:
            del self.connectors[platform]
            logger.info(f"Disconnected from {platform} CAPI")
            return True
        return False

    def get_connected_platforms(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connected platforms."""
        return {
            platform: {
                "connected": True,
                "platform_name": platform.title(),
            }
            for platform in self.connectors.keys()
        }

    async def test_all_connections(self) -> Dict[str, ConnectionResult]:
        """Test connections to all configured platforms."""
        results = {}

        for platform, connector in self.connectors.items():
            try:
                result = await connector.test_connection()
                results[platform] = result
            except Exception as e:
                results[platform] = ConnectionResult(
                    status=ConnectionStatus.ERROR,
                    platform=platform,
                    message=str(e),
                )

        return results

    async def stream_event(
        self,
        event_name: str,
        user_data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
        platforms: List[str] = None,
        event_time: int = None,
        event_source_url: str = None,
        event_id: str = None,
    ) -> StreamResult:
        """
        Stream a single conversion event to configured platforms.

        Args:
            event_name: Name of the conversion event
            user_data: User identification data (will be hashed)
            parameters: Event parameters (value, currency, etc.)
            platforms: Specific platforms to send to (default: all connected)
            event_time: Unix timestamp (default: now)
            event_source_url: URL where event occurred
            event_id: Unique event ID for deduplication

        Returns:
            StreamResult with results from each platform
        """
        parameters = parameters or {}
        platforms = platforms or list(self.connectors.keys())
        event_time = event_time or int(datetime.now(timezone.utc).timestamp())

        # Build event object
        event = {
            "event_name": event_name,
            "user_data": user_data,
            "parameters": parameters,
            "event_time": event_time,
            "event_source_url": event_source_url,
            "event_id": event_id,
        }

        # Stream to platforms
        return await self.stream_events([event], platforms)

    async def stream_events(
        self,
        events: List[Dict[str, Any]],
        platforms: List[str] = None,
    ) -> StreamResult:
        """
        Stream multiple events to platforms simultaneously.

        Args:
            events: List of event dictionaries
            platforms: Platforms to send to (default: all connected)

        Returns:
            StreamResult with combined results
        """
        platforms = platforms or list(self.connectors.keys())

        if not events:
            return StreamResult(
                total_events=0,
                platforms_sent=0,
                platform_results={},
                failed_platforms=[],
                data_quality_score=0,
            )

        # Analyze data quality
        quality_report = self.analyzer.analyze_batch(events, platforms)

        # Send to platforms concurrently
        async def send_to_platform(platform: str) -> tuple:
            connector = self.connectors.get(platform)
            if not connector:
                return platform, CAPIResponse(
                    success=False,
                    events_received=len(events),
                    events_processed=0,
                    errors=[{"message": "Platform not connected"}],
                    platform=platform,
                )
            try:
                result = await connector.send_events(events)
                return platform, result
            except Exception as e:
                logger.error(f"Error sending to {platform}: {e}")
                return platform, CAPIResponse(
                    success=False,
                    events_received=len(events),
                    events_processed=0,
                    errors=[{"message": str(e)}],
                    platform=platform,
                )

        # Execute concurrently
        tasks = [send_to_platform(p) for p in platforms]
        results = await asyncio.gather(*tasks)

        # Compile results
        platform_results = {p: r for p, r in results}
        failed_platforms = [p for p, r in results if not r.success]
        successful_platforms = len(platforms) - len(failed_platforms)

        # Add to event buffer for analysis
        self._event_buffer.extend(events)
        if len(self._event_buffer) > 1000:
            self._event_buffer = self._event_buffer[-1000:]

        return StreamResult(
            total_events=len(events),
            platforms_sent=successful_platforms,
            platform_results=platform_results,
            failed_platforms=failed_platforms,
            data_quality_score=quality_report.overall_score,
        )

    def analyze_data_quality(
        self, user_data: Dict[str, Any], platform: str = None
    ) -> Dict[str, Any]:
        """
        Analyze data quality for user data.

        Args:
            user_data: User identification data to analyze
            platform: Specific platform (default: all)

        Returns:
            Data quality analysis with scores and recommendations
        """
        event = {"user_data": user_data}
        analysis = self.analyzer.analyze_event(event)

        if platform:
            platform_result = analysis["platform_scores"].get(platform)
            if platform_result:
                return {
                    "platform": platform,
                    **platform_result,
                    "overall_score": analysis["overall_score"],
                }

        return analysis

    def get_data_quality_report(
        self, platforms: List[str] = None
    ) -> Optional[QualityReport]:
        """
        Get comprehensive data quality report from recent events.

        Args:
            platforms: Platforms to analyze (default: all connected)

        Returns:
            QualityReport with detailed analysis
        """
        if not self._event_buffer:
            return None

        platforms = platforms or list(self.connectors.keys())
        return self.analyzer.analyze_batch(self._event_buffer, platforms)

    def get_live_insights(self, platform: str = "meta") -> Dict[str, Any]:
        """
        Get live insights from recent events.

        Args:
            platform: Platform to get insights for

        Returns:
            Live insights with real-time recommendations
        """
        return self.analyzer.get_live_insights(self._event_buffer[-100:], platform)

    def map_event(self, event_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Map a custom event to standard platform events.

        Args:
            event_name: Custom event name
            parameters: Event parameters

        Returns:
            Event mapping with platform translations
        """
        validation = self.mapper.validate_event_data(event_name, parameters or {})
        return validation

    def hash_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hash user data for CAPI transmission.

        Args:
            user_data: Raw user data

        Returns:
            Hashed user data ready for platforms
        """
        return self.hasher.hash_data(user_data)

    def detect_pii_fields(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect PII fields in data.

        Args:
            data: Data to analyze

        Returns:
            List of detected PII fields with types
        """
        detections = self.hasher.detect_pii_fields(data)
        return [
            {
                "field": d.field_name,
                "original_key": d.original_key,
                "type": d.detected_type.value,
                "confidence": d.confidence,
                "needs_hashing": d.needs_hashing,
                "is_hashed": d.is_hashed,
            }
            for d in detections
        ]

    async def get_platform_requirements(self, platform: str) -> Dict[str, Any]:
        """
        Get requirements and setup instructions for a platform.

        Args:
            platform: Platform name

        Returns:
            Platform requirements and setup guide
        """
        requirements = {
            "meta": {
                "name": "Meta (Facebook) Conversion API",
                "credentials_needed": [
                    {"field": "pixel_id", "label": "Pixel ID", "help": "Found in Events Manager > Data Sources"},
                    {"field": "access_token", "label": "Access Token", "help": "System User Token from Business Settings"},
                ],
                "documentation": "https://developers.facebook.com/docs/marketing-api/conversions-api",
                "key_fields": ["email", "phone", "external_id", "fbc", "fbp"],
                "events_supported": ["Purchase", "Lead", "AddToCart", "InitiateCheckout", "ViewContent"],
            },
            "google": {
                "name": "Google Ads Enhanced Conversions",
                "credentials_needed": [
                    {"field": "customer_id", "label": "Customer ID", "help": "Google Ads Customer ID (without dashes)"},
                    {"field": "conversion_action_id", "label": "Conversion Action ID", "help": "From Tools > Conversions"},
                    {"field": "api_key", "label": "API Key", "help": "OAuth token or Developer token"},
                ],
                "documentation": "https://developers.google.com/google-ads/api/docs/conversions/upload-offline",
                "key_fields": ["email", "phone", "gclid", "first_name", "last_name"],
                "events_supported": ["purchase", "sign_up", "generate_lead", "add_to_cart"],
            },
            "tiktok": {
                "name": "TikTok Events API",
                "credentials_needed": [
                    {"field": "pixel_code", "label": "Pixel Code", "help": "Found in TikTok Ads Manager > Events"},
                    {"field": "access_token", "label": "Access Token", "help": "Long-lived access token from TikTok Marketing API"},
                ],
                "documentation": "https://ads.tiktok.com/marketing_api/docs?id=1701890973258754",
                "key_fields": ["email", "phone", "ttclid", "external_id"],
                "events_supported": ["CompletePayment", "AddToCart", "SubmitForm", "ViewContent"],
            },
            "snapchat": {
                "name": "Snapchat Conversion API",
                "credentials_needed": [
                    {"field": "pixel_id", "label": "Pixel ID", "help": "Found in Snap Pixel setup"},
                    {"field": "access_token", "label": "Access Token", "help": "From Snapchat Business Manager"},
                ],
                "documentation": "https://marketingapi.snapchat.com/docs/conversion.html",
                "key_fields": ["email", "phone", "external_id", "ip_address"],
                "events_supported": ["PURCHASE", "SIGN_UP", "ADD_CART", "VIEW_CONTENT"],
            },
            "whatsapp": {
                "name": "WhatsApp Business Cloud API",
                "credentials_needed": [
                    {"field": "phone_number_id", "label": "Phone Number ID", "help": "From WhatsApp Business Manager > Phone Numbers"},
                    {"field": "business_account_id", "label": "Business Account ID", "help": "WhatsApp Business Account ID from Meta Business Suite"},
                    {"field": "access_token", "label": "Access Token", "help": "Permanent token from System User in Business Settings"},
                    {"field": "webhook_verify_token", "label": "Webhook Verify Token", "help": "Custom token for webhook verification"},
                ],
                "documentation": "https://developers.facebook.com/docs/whatsapp/cloud-api",
                "key_fields": ["phone"],
                "events_supported": ["template_message", "text_message", "media_message"],
            },
        }

        return requirements.get(platform.lower(), {
            "error": f"Unknown platform: {platform}",
            "supported_platforms": list(requirements.keys()),
        })

    def get_setup_status(self) -> Dict[str, Any]:
        """Get overall CAPI setup status."""
        connected = list(self.connectors.keys())
        available = list(self.PLATFORM_CONNECTORS.keys())

        return {
            "connected_platforms": connected,
            "available_platforms": available,
            "setup_complete": len(connected) > 0,
            "events_processed": len(self._event_buffer),
            "data_quality_score": self._event_buffer and self.get_data_quality_report().overall_score or 0,
        }
