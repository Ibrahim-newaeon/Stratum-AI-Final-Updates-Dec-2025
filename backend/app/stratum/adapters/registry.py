# =============================================================================
# Stratum AI - Adapter Registry
# =============================================================================
"""
Adapter Registry for Platform Integration.

Provides a factory pattern for creating platform adapters based on
platform type. This enables dynamic adapter selection at runtime.
"""

import logging
from typing import Dict, Type, Optional

from app.stratum.models import Platform
from app.stratum.adapters.base import BaseAdapter, AdapterError


logger = logging.getLogger("stratum.adapters.registry")


class AdapterRegistry:
    """
    Registry for platform adapters.

    Usage:
        registry = AdapterRegistry()

        # Register adapters
        registry.register(Platform.META, MetaAdapter)
        registry.register(Platform.GOOGLE, GoogleAdsAdapter)

        # Get adapter for a platform
        adapter = registry.get_adapter(Platform.META, credentials)
        await adapter.initialize()
    """

    _instance: Optional["AdapterRegistry"] = None
    _adapters: Dict[Platform, Type[BaseAdapter]] = {}

    def __new__(cls) -> "AdapterRegistry":
        """Singleton pattern for global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, platform: Platform, adapter_class: Type[BaseAdapter]) -> None:
        """
        Register an adapter class for a platform.

        Args:
            platform: The platform this adapter handles
            adapter_class: The adapter class (not instance)
        """
        cls._adapters[platform] = adapter_class
        logger.info(f"Registered adapter for {platform.value}: {adapter_class.__name__}")

    @classmethod
    def get_adapter(
        cls,
        platform: Platform,
        credentials: Dict[str, str],
    ) -> BaseAdapter:
        """
        Get an adapter instance for a platform.

        Args:
            platform: The target platform
            credentials: Platform-specific credentials

        Returns:
            Initialized adapter instance

        Raises:
            AdapterError: If no adapter is registered for the platform
        """
        if platform not in cls._adapters:
            raise AdapterError(f"No adapter registered for platform: {platform.value}")

        adapter_class = cls._adapters[platform]
        return adapter_class(credentials)

    @classmethod
    def list_registered(cls) -> Dict[str, str]:
        """List all registered adapters."""
        return {
            platform.value: adapter_class.__name__
            for platform, adapter_class in cls._adapters.items()
        }

    @classmethod
    def is_registered(cls, platform: Platform) -> bool:
        """Check if a platform has a registered adapter."""
        return platform in cls._adapters


def get_adapter(platform: Platform, credentials: Dict[str, str]) -> BaseAdapter:
    """
    Convenience function to get an adapter.

    Args:
        platform: Target platform
        credentials: Platform credentials

    Returns:
        Adapter instance
    """
    return AdapterRegistry.get_adapter(platform, credentials)


def register_default_adapters() -> None:
    """
    Register the default platform adapters.

    This should be called during application startup.
    """
    from app.stratum.adapters.meta_adapter import MetaAdapter
    from app.stratum.adapters.google_adapter import GoogleAdsAdapter
    from app.stratum.adapters.tiktok_adapter import TikTokAdapter
    from app.stratum.adapters.snapchat_adapter import SnapchatAdapter

    AdapterRegistry.register(Platform.META, MetaAdapter)
    AdapterRegistry.register(Platform.GOOGLE, GoogleAdsAdapter)
    AdapterRegistry.register(Platform.TIKTOK, TikTokAdapter)
    AdapterRegistry.register(Platform.SNAPCHAT, SnapchatAdapter)

    logger.info("Default platform adapters registered")
