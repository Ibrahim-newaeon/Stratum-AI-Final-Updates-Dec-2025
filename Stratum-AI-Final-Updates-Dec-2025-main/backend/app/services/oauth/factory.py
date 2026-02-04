# =============================================================================
# Stratum AI - OAuth Service Factory
# =============================================================================
"""
Factory function to get the appropriate OAuth service for a platform.
"""

from app.services.oauth.base import OAuthService
from app.services.oauth.google import GoogleOAuthService
from app.services.oauth.meta import MetaOAuthService
from app.services.oauth.snapchat import SnapchatOAuthService
from app.services.oauth.tiktok import TikTokOAuthService

# Registry of OAuth services by platform
_OAUTH_SERVICES: dict[str, type[OAuthService]] = {
    "meta": MetaOAuthService,
    "google": GoogleOAuthService,
    "tiktok": TikTokOAuthService,
    "snapchat": SnapchatOAuthService,
}

# Singleton instances
_oauth_instances: dict[str, OAuthService] = {}


def get_oauth_service(platform: str) -> OAuthService:
    """
    Get OAuth service for a platform.

    Args:
        platform: Platform identifier (meta, google, tiktok, snapchat)

    Returns:
        OAuthService instance for the platform

    Raises:
        ValueError: If platform is not supported
    """
    platform_lower = platform.lower()

    if platform_lower not in _OAUTH_SERVICES:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: {', '.join(_OAUTH_SERVICES.keys())}"
        )

    # Return cached instance or create new one
    if platform_lower not in _oauth_instances:
        service_class = _OAUTH_SERVICES[platform_lower]
        _oauth_instances[platform_lower] = service_class()

    return _oauth_instances[platform_lower]


def get_supported_platforms() -> list[str]:
    """Get list of supported OAuth platforms."""
    return list(_OAUTH_SERVICES.keys())
