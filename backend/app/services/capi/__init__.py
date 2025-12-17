# =============================================================================
# Stratum AI - Conversion API (CAPI) Service
# =============================================================================
"""
Server-side Conversion API integration for streaming first-party data
to ad platforms (Meta, Google, TikTok, Snapchat, LinkedIn).

Features:
- No-code platform connection via API tokens
- AI-powered event mapping
- Automatic PII hashing (SHA256)
- Event Match Quality scoring
- Data gap analysis and recommendations
"""

from .capi_service import CAPIService
from .event_mapper import AIEventMapper
from .pii_hasher import PIIHasher
from .data_quality import DataQualityAnalyzer
from .platform_connectors import (
    MetaCAPIConnector,
    GoogleCAPIConnector,
    TikTokCAPIConnector,
    SnapchatCAPIConnector,
    LinkedInCAPIConnector,
)

__all__ = [
    "CAPIService",
    "AIEventMapper",
    "PIIHasher",
    "DataQualityAnalyzer",
    "MetaCAPIConnector",
    "GoogleCAPIConnector",
    "TikTokCAPIConnector",
    "SnapchatCAPIConnector",
    "LinkedInCAPIConnector",
]
