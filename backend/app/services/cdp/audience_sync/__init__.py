# =============================================================================
# Stratum AI - CDP Audience Sync Module
# =============================================================================
"""
Audience sync services for pushing CDP segments to ad platforms.

Supported Platforms:
- Meta (Facebook/Instagram) Custom Audiences
- Google Ads Customer Match
- TikTok Custom Audiences
- Snapchat Audience Match
"""

from .service import AudienceSyncService
from .base import BaseAudienceConnector, AudienceSyncResult
from .meta_connector import MetaAudienceConnector
from .google_connector import GoogleAudienceConnector
from .tiktok_connector import TikTokAudienceConnector
from .snapchat_connector import SnapchatAudienceConnector

__all__ = [
    "AudienceSyncService",
    "BaseAudienceConnector",
    "AudienceSyncResult",
    "MetaAudienceConnector",
    "GoogleAudienceConnector",
    "TikTokAudienceConnector",
    "SnapchatAudienceConnector",
]
