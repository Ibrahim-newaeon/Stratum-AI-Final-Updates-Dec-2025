# =============================================================================
# Stratum AI - OAuth Services
# =============================================================================
"""
OAuth service implementations for ad platform integrations.
Supports Meta, Google, TikTok, and Snapchat.
"""

from app.services.oauth.base import OAuthService, OAuthState, OAuthTokens, AdAccountInfo
from app.services.oauth.meta import MetaOAuthService
from app.services.oauth.google import GoogleOAuthService
from app.services.oauth.tiktok import TikTokOAuthService
from app.services.oauth.snapchat import SnapchatOAuthService
from app.services.oauth.factory import get_oauth_service

__all__ = [
    "OAuthService",
    "OAuthState",
    "OAuthTokens",
    "AdAccountInfo",
    "MetaOAuthService",
    "GoogleOAuthService",
    "TikTokOAuthService",
    "SnapchatOAuthService",
    "get_oauth_service",
]
