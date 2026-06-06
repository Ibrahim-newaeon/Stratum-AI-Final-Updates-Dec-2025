# =============================================================================
# Stratum AI - Secrets-at-Rest Tests
# =============================================================================
"""
Tests for P0-6:
- Slack webhook URL is encrypted at rest (EncryptedString).
- License HMAC signing secret fails closed in production/staging.
"""

import pytest

from app.db.types import EncryptedString
from app.services.tenant import licensing


# ---------------------------------------------------------------------------
# EncryptedString
# ---------------------------------------------------------------------------
def test_encrypted_string_round_trips():
    col = EncryptedString()
    plaintext = "https://hooks.slack.com/services/T000/B000/XXXXXXXX"

    stored = col.process_bind_param(plaintext, None)
    assert stored is not None
    assert stored != plaintext  # actually encrypted at rest

    loaded = col.process_result_value(stored, None)
    assert loaded == plaintext


def test_encrypted_string_reads_legacy_plaintext():
    """Rows written before encryption must still read (graceful fallback)."""
    col = EncryptedString()
    legacy = "https://hooks.slack.com/legacy-plaintext"
    assert col.process_result_value(legacy, None) == legacy


def test_encrypted_string_handles_none():
    col = EncryptedString()
    assert col.process_bind_param(None, None) is None
    assert col.process_result_value(None, None) is None


# ---------------------------------------------------------------------------
# License signing secret guard
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("env", ["production", "staging"])
def test_license_secret_required_in_prod(monkeypatch, env):
    monkeypatch.setattr(licensing.settings, "app_env", env)
    monkeypatch.delenv("LICENSE_SIGNING_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        licensing._license_signing_secret()


@pytest.mark.parametrize("env", ["production", "staging"])
def test_license_default_rejected_in_prod(monkeypatch, env):
    monkeypatch.setattr(licensing.settings, "app_env", env)
    monkeypatch.setenv("LICENSE_SIGNING_SECRET", "dev-secret-change-me")
    with pytest.raises(RuntimeError):
        licensing._license_signing_secret()


def test_license_secret_used_when_set_in_prod(monkeypatch):
    monkeypatch.setattr(licensing.settings, "app_env", "production")
    monkeypatch.setenv("LICENSE_SIGNING_SECRET", "a-real-strong-secret")
    assert licensing._license_signing_secret() == "a-real-strong-secret"


def test_license_dev_default_allowed_in_development(monkeypatch):
    monkeypatch.setattr(licensing.settings, "app_env", "development")
    monkeypatch.delenv("LICENSE_SIGNING_SECRET", raising=False)
    assert licensing._license_signing_secret() == "dev-secret-change-me"
