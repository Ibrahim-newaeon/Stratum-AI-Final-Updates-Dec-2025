# =============================================================================
# Stratum AI - Adapter Registry Deep Coverage Tests (#342 Batch 5+6)
# =============================================================================
"""
Deep tests for ``app.stratum.adapters.registry``.

Covers the singleton mechanism, register/lookup/duplicate-registration paths,
the unknown-platform error, listing/is_registered helpers, the module-level
``get_adapter`` convenience function, and ``register_default_adapters``.

``AdapterRegistry._adapters`` is a class-level dict shared process-wide (the
app lifespan registers defaults), so every test snapshots and restores it to
avoid leaking state into sibling test files.
"""

from datetime import datetime
from typing import Optional

import pytest

from app.stratum.adapters.base import AdapterError, BaseAdapter
from app.stratum.adapters.google_adapter import GoogleAdsAdapter
from app.stratum.adapters.registry import (
    AdapterRegistry,
    get_adapter,
    register_default_adapters,
)
from app.stratum.models import EntityStatus, Platform

pytestmark = pytest.mark.integration


class _StubAdapter(BaseAdapter):
    """Concrete adapter implementing the full abstract surface for lookup tests."""

    @property
    def platform(self) -> Platform:
        return Platform.META

    async def initialize(self) -> None:
        self._initialized = True

    async def cleanup(self) -> None:
        self._initialized = False

    async def get_accounts(self):
        return []

    async def get_campaigns(
        self, account_id: str, status_filter: Optional[list[EntityStatus]] = None
    ):
        return []

    async def get_adsets(self, account_id: str, campaign_id: Optional[str] = None):
        return []

    async def get_ads(self, account_id: str, adset_id: Optional[str] = None):
        return []

    async def get_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        date_start: datetime,
        date_end: datetime,
        breakdown: Optional[str] = None,
    ):
        return {}

    async def get_emq_scores(self, account_id: str):
        return []

    async def execute_action(self, action):
        return action

    async def upload_image(
        self, account_id: str, image_data: bytes, filename: str
    ) -> str:
        return "img-1"

    async def upload_video(
        self, account_id: str, video_data: bytes, filename: str
    ) -> str:
        return "vid-1"


class _OtherStubAdapter(_StubAdapter):
    """Second concrete adapter for duplicate-registration tests."""


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Snapshot/restore the shared class-level registry state around each test."""
    saved_adapters = dict(AdapterRegistry._adapters)
    saved_instance = AdapterRegistry._instance
    AdapterRegistry._adapters.clear()
    yield
    AdapterRegistry._adapters.clear()
    AdapterRegistry._adapters.update(saved_adapters)
    AdapterRegistry._instance = saved_instance


class TestSingleton:
    def test_new_creates_and_reuses_single_instance(self):
        AdapterRegistry._instance = None
        first = AdapterRegistry()
        second = AdapterRegistry()
        assert first is second
        assert AdapterRegistry._instance is first


class TestRegisterAndLookup:
    def test_register_then_get_adapter_instantiates_class(self):
        AdapterRegistry.register(Platform.META, _StubAdapter)

        credentials = {"access_token": "tok-1"}
        adapter = AdapterRegistry.get_adapter(Platform.META, credentials)

        assert isinstance(adapter, _StubAdapter)
        assert adapter.credentials == credentials
        assert adapter._initialized is False

    def test_get_adapter_unknown_platform_raises_adapter_error(self):
        with pytest.raises(
            AdapterError, match="No adapter registered for platform: whatsapp"
        ):
            AdapterRegistry.get_adapter(Platform.WHATSAPP, {})

    def test_duplicate_registration_last_wins(self):
        AdapterRegistry.register(Platform.META, _StubAdapter)
        AdapterRegistry.register(Platform.META, _OtherStubAdapter)

        adapter = AdapterRegistry.get_adapter(Platform.META, {})
        assert isinstance(adapter, _OtherStubAdapter)
        assert AdapterRegistry.list_registered() == {"meta": "_OtherStubAdapter"}

    def test_list_registered_maps_platform_values_to_class_names(self):
        assert AdapterRegistry.list_registered() == {}
        AdapterRegistry.register(Platform.META, _StubAdapter)
        AdapterRegistry.register(Platform.TIKTOK, _OtherStubAdapter)

        assert AdapterRegistry.list_registered() == {
            "meta": "_StubAdapter",
            "tiktok": "_OtherStubAdapter",
        }

    def test_is_registered(self):
        assert AdapterRegistry.is_registered(Platform.META) is False
        AdapterRegistry.register(Platform.META, _StubAdapter)
        assert AdapterRegistry.is_registered(Platform.META) is True
        assert AdapterRegistry.is_registered(Platform.GOOGLE) is False


class TestModuleLevelConvenience:
    def test_get_adapter_function_delegates_to_registry(self):
        AdapterRegistry.register(Platform.META, _StubAdapter)
        adapter = get_adapter(Platform.META, {"access_token": "tok-2"})
        assert isinstance(adapter, _StubAdapter)
        assert adapter.credentials == {"access_token": "tok-2"}

    def test_get_adapter_function_propagates_unknown_platform_error(self):
        with pytest.raises(AdapterError, match="No adapter registered"):
            get_adapter(Platform.SNAPCHAT, {})


class TestRegisterDefaultAdapters:
    def test_registers_all_four_ad_platforms(self):
        register_default_adapters()

        registered = AdapterRegistry.list_registered()
        assert registered == {
            "meta": "MetaAdapter",
            "google": "GoogleAdsAdapter",
            "tiktok": "TikTokAdapter",
            "snapchat": "SnapchatAdapter",
        }
        # WhatsApp is intentionally not an ads adapter
        assert AdapterRegistry.is_registered(Platform.WHATSAPP) is False

    def test_default_google_adapter_resolvable_and_constructible(self):
        register_default_adapters()
        adapter = get_adapter(Platform.GOOGLE, {"developer_token": "dev-token"})
        assert isinstance(adapter, GoogleAdsAdapter)
        assert adapter.platform == Platform.GOOGLE
