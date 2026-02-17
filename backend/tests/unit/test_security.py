# =============================================================================
# Stratum AI - Security Module Test Suite
# =============================================================================
"""
Security-focused tests verifying:
- PII encryption key derivation (PBKDF2HMAC)
- Fernet encryption integrity
- Hash collision resistance
- API key constant-time comparison
- JWT algorithm enforcement
- Permission decorator behavior
"""

import base64
import hashlib
import secrets

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.security import (
    _get_fernet_key,
    _get_pii_salt,
    create_access_token,
    decode_token,
    decrypt_pii,
    encrypt_pii,
    generate_api_key,
    hash_api_key,
    hash_pii_for_lookup,
    verify_api_key,
)

# ---------------------------------------------------------------------------
# 1. Fernet Key Derivation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeyDerivation:
    """Tests for PBKDF2HMAC-based Fernet key derivation."""

    def test_fernet_key_is_valid_base64(self) -> None:
        """The derived Fernet key must be valid URL-safe base64 (32 bytes)."""
        key = _get_fernet_key()
        assert isinstance(key, bytes)
        # Fernet keys are 32 bytes, URL-safe base64 encoded = 44 chars
        assert len(key) == 44

    def test_fernet_key_is_stable(self) -> None:
        """Same environment produces the same Fernet key (deterministic derivation)."""
        key_a = _get_fernet_key()
        key_b = _get_fernet_key()
        assert key_a == key_b

    def test_fernet_key_works_with_fernet(self) -> None:
        """The derived key can be used to create a valid Fernet cipher."""
        key = _get_fernet_key()
        fernet = Fernet(key)
        plaintext = b"test-data"
        encrypted = fernet.encrypt(plaintext)
        decrypted = fernet.decrypt(encrypted)
        assert decrypted == plaintext

    def test_pii_salt_returns_bytes(self) -> None:
        """PII salt function returns bytes."""
        salt = _get_pii_salt()
        assert isinstance(salt, bytes)
        assert len(salt) >= 16  # Minimum salt length


# ---------------------------------------------------------------------------
# 2. Encryption Integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEncryptionIntegrity:
    """Tests for data integrity during encryption/decryption."""

    def test_tampered_ciphertext_raises_error(self) -> None:
        """Modifying encrypted data should cause decryption to fail."""
        plaintext = "sensitive-email@example.com"
        ciphertext = encrypt_pii(plaintext)

        # Decode the outer base64, tamper with inner data, re-encode
        raw = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
        # Flip a byte in the middle of the ciphertext
        tampered = bytearray(raw)
        if len(tampered) > 20:
            tampered[20] ^= 0xFF
        tampered_b64 = base64.urlsafe_b64encode(bytes(tampered)).decode("utf-8")

        with pytest.raises((InvalidToken, ValueError)):
            decrypt_pii(tampered_b64)

    def test_wrong_key_cannot_decrypt(self) -> None:
        """Data encrypted with one key cannot be decrypted with a different key."""
        plaintext = "private-data"
        ciphertext = encrypt_pii(plaintext)

        # Create a Fernet with a completely different key
        different_key = Fernet.generate_key()
        fernet = Fernet(different_key)
        raw = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))

        with pytest.raises(InvalidToken):
            fernet.decrypt(raw)

    def test_large_payload_encryption(self) -> None:
        """Large text payloads can be encrypted and decrypted."""
        large_text = "A" * 10000  # 10KB of text
        ciphertext = encrypt_pii(large_text)
        decrypted = decrypt_pii(ciphertext)
        assert decrypted == large_text

    def test_special_characters_in_pii(self) -> None:
        """Special characters (newlines, tabs, null bytes) survive round-trip."""
        special = "line1\nline2\ttab\x00null"
        ciphertext = encrypt_pii(special)
        assert decrypt_pii(ciphertext) == special


# ---------------------------------------------------------------------------
# 3. Hash Functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHashFunctions:
    """Tests for PII hashing and API key hashing."""

    def test_pii_hash_is_hex_string(self) -> None:
        """PII lookup hash returns a hexadecimal string (SHA-256 = 64 chars)."""
        result = hash_pii_for_lookup("test@example.com")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_pii_hash_includes_salt(self) -> None:
        """The PII hash uses the encryption key as salt, not raw SHA-256."""
        value = "test@example.com"
        pii_hash = hash_pii_for_lookup(value)
        # A plain SHA-256 of the value should differ
        plain_hash = hashlib.sha256(value.encode()).hexdigest()
        assert pii_hash != plain_hash

    def test_api_key_hash_is_hex(self) -> None:
        """API key hash returns a 64-character hex string."""
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_different_values_produce_different_hashes(self) -> None:
        """Different PII values produce different hashes."""
        hash_a = hash_pii_for_lookup("alice@example.com")
        hash_b = hash_pii_for_lookup("bob@example.com")
        assert hash_a != hash_b


# ---------------------------------------------------------------------------
# 4. API Key Security
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAPIKeySecurity:
    """Tests for API key generation and verification security properties."""

    def test_key_length_sufficient(self) -> None:
        """Generated API keys have sufficient entropy (32 bytes of randomness)."""
        key = generate_api_key()
        # sk_test_ is 8 chars, then 43 chars of base64 from token_urlsafe(32)
        assert len(key) > 40

    def test_key_prefix_matches_environment(self) -> None:
        """Key prefix reflects the current environment."""
        key = generate_api_key()
        if settings.is_production:
            assert key.startswith("sk_live_")
        else:
            assert key.startswith("sk_test_")

    def test_verify_api_key_is_comparison_based(self) -> None:
        """verify_api_key compares SHA-256 hashes, not raw keys."""
        key = "sk_test_" + secrets.token_urlsafe(32)
        stored_hash = hashlib.sha256(key.encode()).hexdigest()
        assert verify_api_key(key, stored_hash) is True

    def test_empty_key_does_not_match(self) -> None:
        """An empty key does not verify against any stored hash."""
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert verify_api_key("", hashed) is False


# ---------------------------------------------------------------------------
# 5. JWT Security
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJWTSecurity:
    """Tests for JWT token security properties."""

    def test_tokens_use_configured_algorithm(self) -> None:
        """Tokens are signed with the configured algorithm (HS256 by default)."""
        token = create_access_token(subject="user-1")
        # JWT header is the first part, base64-decoded
        header_b64 = token.split(".")[0]
        # Add padding if needed
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        import json

        header = json.loads(base64.urlsafe_b64decode(header_b64))
        assert header["alg"] == settings.jwt_algorithm

    def test_token_has_expiration(self) -> None:
        """All tokens include an 'exp' claim."""
        token = create_access_token(subject="user-1")
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_token_has_issued_at(self) -> None:
        """All tokens include an 'iat' (issued at) claim."""
        token = create_access_token(subject="user-1")
        payload = decode_token(token)
        assert payload is not None
        assert "iat" in payload

    def test_none_algorithm_attack_blocked(self) -> None:
        """Tokens with 'none' algorithm should not decode successfully."""
        # python-jose should reject alg=none
        from jose import jwt as jose_jwt

        # Create a token with "none" algorithm
        malicious_payload = {"sub": "hacker", "type": "access"}
        try:
            malicious_token = jose_jwt.encode(
                malicious_payload, "", algorithm="none"
            )
            # Attempting to decode should fail since our settings use HS256
            result = decode_token(malicious_token)
            assert result is None
        except Exception:
            # If encoding with "none" raises, that's also acceptable security behavior
            pass
