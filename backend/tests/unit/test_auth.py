# =============================================================================
# Stratum AI - Authentication & Security Test Suite
# =============================================================================
"""
Comprehensive authentication and authorization test suite.

Tests cover:
- Password hashing and verification (bcrypt)
- JWT access token creation, decoding, and expiry
- JWT refresh token creation, decoding, jti, and expiry
- PII encryption/decryption (Fernet + PBKDF2HMAC)
- PII hashing and anonymization
- API key generation, hashing, and verification
"""

import time
from datetime import timedelta

import pytest

from app.core.security import (
    anonymize_pii,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_pii,
    encrypt_pii,
    generate_api_key,
    get_password_hash,
    hash_api_key,
    hash_pii_for_lookup,
    verify_api_key,
    verify_password,
)

# ---------------------------------------------------------------------------
# 1. Password hashing and verification (bcrypt)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPasswordHashing:
    """Tests for bcrypt password hashing and verification."""

    def test_hash_and_verify_correct_password(self) -> None:
        """Hashing a password then verifying with the same plaintext succeeds."""
        password = "SecureP@ssw0rd!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_rejects_wrong_password(self) -> None:
        """Verification fails when the wrong plaintext is provided."""
        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        """bcrypt uses a random salt, so two hashes of the same password differ."""
        password = "SamePassword123"
        hash_a = get_password_hash(password)
        hash_b = get_password_hash(password)
        assert hash_a != hash_b
        # Both must still verify correctly
        assert verify_password(password, hash_a) is True
        assert verify_password(password, hash_b) is True

    def test_empty_password_handling(self) -> None:
        """An empty string can be hashed and verified like any other password."""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_unicode_password_support(self) -> None:
        """Unicode characters in passwords are handled correctly."""
        password = "\u00e9\u00e0\u00fc\u00f1\u2603\u2764\ufe0f\U0001f511"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("plain-ascii", hashed) is False

    def test_long_password(self) -> None:
        """A reasonably long password can be hashed and verified."""
        password = "A" * 200
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


# ---------------------------------------------------------------------------
# 2. JWT Access Token Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJWTAccessToken:
    """Tests for JWT access token creation and decoding."""

    def test_create_and_decode_token(self) -> None:
        """A freshly created access token can be decoded successfully."""
        token = create_access_token(subject="user-123")
        payload = decode_token(token)
        assert payload is not None

    def test_token_contains_correct_subject(self) -> None:
        """The decoded payload 'sub' field matches the subject used at creation."""
        subject = "tenant-42::user-7"
        token = create_access_token(subject=subject)
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("sub") == subject

    def test_token_contains_access_type(self) -> None:
        """Access tokens carry type='access' in their payload."""
        token = create_access_token(subject="user-1")
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("type") == "access"

    def test_token_with_additional_claims(self) -> None:
        """Extra claims passed at creation appear in the decoded payload."""
        extra = {"role": "admin", "tenant_id": 5}
        token = create_access_token(subject="user-1", additional_claims=extra)
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("role") == "admin"
        assert payload.get("tenant_id") == 5

    def test_expired_token_returns_none(self) -> None:
        """A token created with a negative expiry is already expired."""
        token = create_access_token(
            subject="user-1",
            expires_delta=timedelta(seconds=-1),
        )
        time.sleep(0.1)
        payload = decode_token(token)
        assert payload is None

    def test_malformed_token_returns_none(self) -> None:
        """Completely invalid token strings return None on decode."""
        assert decode_token("not.a.valid.jwt") is None
        assert decode_token("") is None
        assert decode_token("abc123") is None


# ---------------------------------------------------------------------------
# 3. JWT Refresh Token Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJWTRefreshToken:
    """Tests for JWT refresh token creation and decoding."""

    def test_create_and_decode_refresh_token(self) -> None:
        """A freshly created refresh token can be decoded successfully."""
        token = create_refresh_token(subject="user-99")
        payload = decode_token(token)
        assert payload is not None

    def test_refresh_token_has_refresh_type(self) -> None:
        """Refresh tokens carry type='refresh' in their payload."""
        token = create_refresh_token(subject="user-99")
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("type") == "refresh"

    def test_refresh_token_has_jti(self) -> None:
        """Refresh tokens include a 'jti' (JWT ID) field for revocation support."""
        token = create_refresh_token(subject="user-99")
        payload = decode_token(token)
        assert payload is not None
        assert "jti" in payload
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) > 0

    def test_refresh_token_jti_is_unique(self) -> None:
        """Each refresh token gets a distinct jti."""
        token_a = create_refresh_token(subject="user-1")
        token_b = create_refresh_token(subject="user-1")
        payload_a = decode_token(token_a)
        payload_b = decode_token(token_b)
        assert payload_a is not None and payload_b is not None
        assert payload_a["jti"] != payload_b["jti"]

    def test_expired_refresh_token_returns_none(self) -> None:
        """An expired refresh token decodes to None."""
        token = create_refresh_token(
            subject="user-1",
            expires_delta=timedelta(seconds=-1),
        )
        time.sleep(0.1)
        payload = decode_token(token)
        assert payload is None


# ---------------------------------------------------------------------------
# 4. PII Encryption Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPIIEncryption:
    """Tests for Fernet-based PII encryption, hashing, and anonymization."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        """Encrypting then decrypting returns the original plaintext."""
        plaintext = "john.doe@example.com"
        ciphertext = encrypt_pii(plaintext)
        assert ciphertext != plaintext
        decrypted = decrypt_pii(ciphertext)
        assert decrypted == plaintext

    def test_different_ciphertexts_for_same_plaintext(self) -> None:
        """Fernet uses a unique nonce each time, producing different ciphertexts."""
        plaintext = "sensitive-data"
        ct_a = encrypt_pii(plaintext)
        ct_b = encrypt_pii(plaintext)
        assert ct_a != ct_b
        # Both must decrypt to the same value
        assert decrypt_pii(ct_a) == plaintext
        assert decrypt_pii(ct_b) == plaintext

    def test_empty_string_returns_empty(self) -> None:
        """An empty string returns empty without encryption."""
        assert encrypt_pii("") == ""
        assert decrypt_pii("") == ""

    def test_unicode_data_handling(self) -> None:
        """Unicode PII data survives the encrypt/decrypt round-trip."""
        plaintext = "\u00c9milie Br\u00f6nt\u00eb \u2014 \u4e2d\u6587\u540d\u5b57"
        ciphertext = encrypt_pii(plaintext)
        assert decrypt_pii(ciphertext) == plaintext

    def test_hash_pii_for_lookup_is_deterministic(self) -> None:
        """The same value always produces the same SHA-256 hash."""
        value = "user@stratum.ai"
        hash_a = hash_pii_for_lookup(value)
        hash_b = hash_pii_for_lookup(value)
        assert hash_a == hash_b
        # Different input produces a different hash
        hash_c = hash_pii_for_lookup("other@stratum.ai")
        assert hash_a != hash_c

    def test_anonymize_pii_returns_anonymized_prefix(self) -> None:
        """anonymize_pii returns a value prefixed with ANONYMIZED_ that hides the original."""
        original = "jane.smith@example.com"
        anonymized = anonymize_pii(original)
        assert anonymized.startswith("ANONYMIZED_")
        assert original not in anonymized

    def test_anonymize_pii_is_random(self) -> None:
        """Each call to anonymize_pii produces a unique value (random suffix)."""
        original = "jane.smith@example.com"
        a1 = anonymize_pii(original)
        a2 = anonymize_pii(original)
        assert a1 != a2  # secrets.token_hex(8) is random each time


# ---------------------------------------------------------------------------
# 5. API Key Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAPIKey:
    """Tests for API key generation, hashing, and verification."""

    def test_generate_key_has_prefix(self) -> None:
        """Generated keys start with sk_test or sk_live depending on environment."""
        key = generate_api_key()
        assert key.startswith("sk_test") or key.startswith("sk_live")

    def test_hash_and_verify_key(self) -> None:
        """A generated key can be hashed and then successfully verified."""
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert verify_api_key(key, hashed) is True

    def test_verify_rejects_wrong_key(self) -> None:
        """Verification fails when a different key is checked against the hash."""
        key_a = generate_api_key()
        key_b = generate_api_key()
        hashed_a = hash_api_key(key_a)
        assert verify_api_key(key_b, hashed_a) is False

    def test_key_uniqueness(self) -> None:
        """Multiple generated keys are all distinct."""
        keys = {generate_api_key() for _ in range(20)}
        assert len(keys) == 20, "Expected 20 unique API keys"

    def test_hash_api_key_is_deterministic(self) -> None:
        """Hashing the same key twice produces the same hash (SHA-256, no salt)."""
        key = generate_api_key()
        assert hash_api_key(key) == hash_api_key(key)
