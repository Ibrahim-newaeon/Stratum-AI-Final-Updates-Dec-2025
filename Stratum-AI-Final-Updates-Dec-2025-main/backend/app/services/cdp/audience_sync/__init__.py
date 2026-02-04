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

from .base import AudienceSyncResult, BaseAudienceConnector
from .google_connector import GoogleAudienceConnector
from .meta_connector import MetaAudienceConnector
from .service import AudienceSyncService
from .snapchat_connector import SnapchatAudienceConnector
from .tiktok_connector import TikTokAudienceConnector

__all__ = [
    "AudienceSyncService",
    "BaseAudienceConnector",
    "AudienceSyncResult",
    "MetaAudienceConnector",
    "GoogleAudienceConnector",
    "TikTokAudienceConnector",
    "SnapchatAudienceConnector",
]
