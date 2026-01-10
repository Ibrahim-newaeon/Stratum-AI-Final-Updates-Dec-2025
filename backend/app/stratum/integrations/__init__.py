"""
Stratum AI: Platform-Specific Integrations
==========================================

This module contains deep integrations for platforms that require
special handling beyond the standard adapter pattern.

Google Complete Integration
---------------------------
Google Ads doesn't support webhooks. Instead, we provide:
- Change History polling (detects account changes)
- Offline Conversion Import (for CRM/phone/WhatsApp sales)
- GA4 Measurement Protocol (real-time event streaming)
- Recommendations API (AI-powered optimization suggestions)

Usage:
    from app.stratum.integrations.google_complete import GoogleAdsIntegration

    google = GoogleAdsIntegration(
        client=google_ads_client,
        customer_id="1234567890",
        ga4_measurement_id="G-XXXXXXXXXX",
        ga4_api_secret="secret"
    )

    # Poll for changes (replaces webhooks)
    changes = await google.get_recent_changes(hours=1)

    # Upload WhatsApp conversion
    await google.track_conversion(
        conversion_action_id="123",
        email="customer@example.com",
        phone="+966501234567",
        value=4500.0,
        currency="SAR"
    )
"""

from app.stratum.integrations.google_complete import (
    GoogleAdsIntegration,
    GoogleAdsChangeHistory,
    GoogleOfflineConversions,
    GA4MeasurementProtocol,
    GoogleAdsRecommendations,
    ChangeEvent,
    ChangeEventType,
    OfflineConversion,
)

__all__ = [
    "GoogleAdsIntegration",
    "GoogleAdsChangeHistory",
    "GoogleOfflineConversions",
    "GA4MeasurementProtocol",
    "GoogleAdsRecommendations",
    "ChangeEvent",
    "ChangeEventType",
    "OfflineConversion",
]
