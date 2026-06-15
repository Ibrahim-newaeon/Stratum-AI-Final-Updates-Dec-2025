# =============================================================================
# Stratum AI - Sync Orchestrator Env-Credential Unit Tests
# =============================================================================
"""Unit tests for ``PlatformSyncOrchestrator._get_env_credentials`` in
``app.services.sync.orchestrator`` — the pure staticmethod that resolves a
platform's access token + account IDs from environment / settings,
including Meta's ``act_`` account-id prefixing. The DB-backed sync pipeline
is out of scope here.
"""

import pytest

from app.base_models import AdPlatform
from app.services.sync.orchestrator import PlatformSyncOrchestrator, SyncResult

pytestmark = pytest.mark.unit

_get = PlatformSyncOrchestrator._get_env_credentials


# =============================================================================
# Meta
# =============================================================================
class TestMeta:
    def test_prefixes_account_ids_with_act(self, monkeypatch):
        monkeypatch.setenv("META_ACCESS_TOKEN", "tok123")
        monkeypatch.setenv("META_AD_ACCOUNT_IDS", "111, 222")
        token, accounts = _get(AdPlatform.META)
        assert token == "tok123"
        assert accounts == ["act_111", "act_222"]

    def test_keeps_existing_act_prefix(self, monkeypatch):
        monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("META_AD_ACCOUNT_IDS", "act_999")
        _token, accounts = _get(AdPlatform.META)
        assert accounts == ["act_999"]

    def test_empty_accounts(self, monkeypatch):
        monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
        monkeypatch.delenv("META_AD_ACCOUNT_IDS", raising=False)
        _token, accounts = _get(AdPlatform.META)
        assert accounts == []


# =============================================================================
# Other platforms / unknown
# =============================================================================
class TestOtherPlatforms:
    def test_unknown_platform_returns_empty(self):
        # GOOGLE has no env branch in this resolver -> (None, []).
        token, accounts = _get(AdPlatform.GOOGLE)
        assert token is None
        assert accounts == []


# =============================================================================
# SyncResult dataclass
# =============================================================================
class TestSyncResult:
    def test_defaults(self):
        r = SyncResult(platform="meta", tenant_id=1)
        assert r.campaigns_synced == 0
        assert r.metrics_upserted == 0
        assert r.errors == []
        assert r.duration_seconds == 0.0

    def test_independent_error_lists(self):
        a = SyncResult(platform="meta", tenant_id=1)
        b = SyncResult(platform="google", tenant_id=1)
        a.errors.append("boom")
        # Default-factory lists must not be shared between instances.
        assert b.errors == []
