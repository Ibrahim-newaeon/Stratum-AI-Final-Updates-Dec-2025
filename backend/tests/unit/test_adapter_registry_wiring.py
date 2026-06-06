# =============================================================================
# Stratum AI - Adapter Registry Wiring Tests
# =============================================================================
"""
Tests for wiring the platform adapter registry (P1-5).

`register_default_adapters()` was defined but never called at startup, so
`AdapterRegistry` was always empty and the stratum action layer could not
resolve any platform adapter. It's now invoked in the app lifespan.
"""

import pytest

from app.stratum.adapters.base import BaseAdapter
from app.stratum.adapters.registry import AdapterRegistry, register_default_adapters
from app.stratum.models import Platform


class _DummyAdapter(BaseAdapter):
    """Bare adapter subclass for exercising the registry mechanism."""


def test_register_and_list_mechanism():
    AdapterRegistry.register(Platform.META, _DummyAdapter)
    assert AdapterRegistry.list_registered().get("meta") == "_DummyAdapter"


def test_register_default_adapters_registers_all_platforms():
    # The real adapters import platform SDKs (google-ads, facebook-business…)
    # which may be absent locally; the call is import-guarded at startup, so
    # skip cleanly here and let CI exercise the full path.
    try:
        register_default_adapters()
    except ImportError:
        pytest.skip("platform SDKs not installed in this environment")

    registered = AdapterRegistry.list_registered()
    for platform in ("meta", "google", "tiktok", "snapchat"):
        assert platform in registered
