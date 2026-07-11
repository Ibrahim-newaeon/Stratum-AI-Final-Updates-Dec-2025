# =============================================================================
# Stratum AI - Webhook Signature Verification Unit Tests
# =============================================================================
"""Unit tests for the pure HMAC signature verifiers in
``app.stratum.webhooks``:

- ``verify_meta_signature`` (``sha256=<hmac>`` format)
- ``verify_tiktok_signature`` (bare hmac hex)
- ``verify_internal_signature`` (uses ``config.WEBHOOK_SECRET``)

All three use ``hmac.compare_digest`` for constant-time comparison.
``verify_meta_signature`` fails *closed* (rejects) when no secret or no
signature is present (CAPI-003); ``verify_tiktok_signature`` and
``verify_internal_signature`` still fail *open* when unconfigured. Those
contracts are covered here. The FastAPI webhook routes are out of scope.
"""

import hashlib
import hmac

import pytest

from app.stratum import webhooks
from app.stratum.webhooks import (
    verify_internal_signature,
    verify_meta_signature,
    verify_tiktok_signature,
)

pytestmark = pytest.mark.unit

PAYLOAD = b'{"event":"lead","id":42}'
SECRET = "s3cr3t"  # gitleaks:allow


def _hexsig(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# =============================================================================
# verify_meta_signature
# =============================================================================
class TestMetaSignature:
    def test_valid_signature(self):
        sig = f"sha256={_hexsig(SECRET, PAYLOAD)}"
        assert verify_meta_signature(PAYLOAD, sig, SECRET) is True

    def test_bare_hex_without_prefix_rejected(self):
        # Meta requires the "sha256=" prefix; a bare hex must not match.
        assert verify_meta_signature(PAYLOAD, _hexsig(SECRET, PAYLOAD), SECRET) is False

    def test_wrong_secret_rejected(self):
        sig = f"sha256={_hexsig('other', PAYLOAD)}"
        assert verify_meta_signature(PAYLOAD, sig, SECRET) is False

    def test_tampered_payload_rejected(self):
        sig = f"sha256={_hexsig(SECRET, PAYLOAD)}"
        assert verify_meta_signature(b"tampered", sig, SECRET) is False

    def test_missing_secret_fails_closed(self):
        # CAPI-003: an unverifiable payload (no configured secret) is rejected,
        # not trusted.
        assert verify_meta_signature(PAYLOAD, "anything", "") is False

    def test_missing_signature_fails_closed(self):
        # CAPI-003: an absent/empty signature header cannot be trusted.
        assert verify_meta_signature(PAYLOAD, "", SECRET) is False


# =============================================================================
# verify_tiktok_signature
# =============================================================================
class TestTikTokSignature:
    def test_valid_signature(self):
        assert (
            verify_tiktok_signature(PAYLOAD, _hexsig(SECRET, PAYLOAD), SECRET) is True
        )

    def test_wrong_signature_rejected(self):
        assert verify_tiktok_signature(PAYLOAD, "deadbeef", SECRET) is False

    def test_missing_secret_fails_open(self):
        assert verify_tiktok_signature(PAYLOAD, "anything", "") is True


# =============================================================================
# verify_internal_signature
# =============================================================================
class TestInternalSignature:
    def test_valid_signature(self, monkeypatch):
        monkeypatch.setattr(webhooks.config, "WEBHOOK_SECRET", SECRET)
        assert verify_internal_signature(PAYLOAD, _hexsig(SECRET, PAYLOAD)) is True

    def test_wrong_signature_rejected(self, monkeypatch):
        monkeypatch.setattr(webhooks.config, "WEBHOOK_SECRET", SECRET)
        assert verify_internal_signature(PAYLOAD, "nope") is False

    def test_no_secret_fails_open(self, monkeypatch):
        monkeypatch.setattr(webhooks.config, "WEBHOOK_SECRET", "")
        assert verify_internal_signature(PAYLOAD, "anything") is True
