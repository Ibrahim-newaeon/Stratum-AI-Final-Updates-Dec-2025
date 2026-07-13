# =============================================================================
# Stratum AI - _safe_decrypt fail-closed tests [AUTH-05]
# =============================================================================
"""Undecryptable ciphertext must never be echoed into API responses; genuine
legacy plaintext (pre-encryption rows) must still display as-is."""

from cryptography.fernet import Fernet

from app.api.v1.endpoints.users import _safe_decrypt
from app.core import pii_keys
from app.core.security import encrypt_pii, looks_like_pii_ciphertext


class TestLooksLikePiiCiphertext:
    def test_real_ciphertext_matches(self):
        assert looks_like_pii_ciphertext(encrypt_pii("alice@example.com")) is True

    def test_tenant_dek_ciphertext_matches(self):
        pii_keys._clear_cache()
        pii_keys._DEK_CACHE[42] = Fernet.generate_key()
        assert looks_like_pii_ciphertext(encrypt_pii("bob@example.com", 42)) is True
        pii_keys._clear_cache()

    def test_plaintext_name_does_not_match(self):
        assert looks_like_pii_ciphertext("John Smith") is False

    def test_plaintext_email_does_not_match(self):
        assert looks_like_pii_ciphertext("john@example.com") is False

    def test_empty_and_invalid_base64_do_not_match(self):
        assert looks_like_pii_ciphertext("") is False
        assert looks_like_pii_ciphertext("!!!not-base64!!!") is False


class TestSafeDecryptFailClosed:
    def test_valid_ciphertext_decrypts(self):
        pii_keys._clear_cache()
        assert _safe_decrypt(encrypt_pii("Jane Doe"), None) == "Jane Doe"

    def test_undecryptable_ciphertext_returns_none(self):
        # Encrypted under a DEK that is no longer cached -> decrypt fails.
        # The ciphertext must NOT leak into the response.
        pii_keys._clear_cache()
        pii_keys._DEK_CACHE[7] = Fernet.generate_key()
        blob = encrypt_pii("secret", 7)
        pii_keys._clear_cache()  # key gone -> undecryptable
        assert _safe_decrypt(blob, 7) is None

    def test_legacy_plaintext_is_echoed(self):
        # Pre-encryption rows hold raw values; they should still display.
        assert _safe_decrypt("Legacy User", None) == "Legacy User"

    def test_empty_returns_none(self):
        assert _safe_decrypt("", None) is None
        assert _safe_decrypt(None, None) is None
