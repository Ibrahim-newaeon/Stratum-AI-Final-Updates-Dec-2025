# =============================================================================
# Stratum AI - Per-Tenant PII Key + Dual-Read Unit Tests [AUTH-05]
# =============================================================================
"""
Covers the envelope-encryption primitives (wrap/unwrap, DEK cache) and, most
importantly, the dual-read guarantees in ``encrypt_pii`` / ``decrypt_pii``:

- data written with a tenant's DEK round-trips,
- data written with the legacy global key STILL decrypts after the tenant gets
  a DEK (so no mass re-encryption is needed),
- corrupted ciphertext raises rather than leaking.
"""

import pytest
from cryptography.fernet import Fernet

from app.core import pii_keys
from app.core.security import decrypt_pii, encrypt_pii


@pytest.fixture(autouse=True)
def _clean_cache():
    pii_keys._clear_cache()
    yield
    pii_keys._clear_cache()


# ---------------------------------------------------------------------------
# Envelope primitives
# ---------------------------------------------------------------------------


def test_wrap_unwrap_roundtrip():
    dek = Fernet.generate_key()
    assert pii_keys.unwrap_dek(pii_keys.wrap_dek(dek)) == dek


def test_wrapped_dek_is_not_plaintext():
    dek = Fernet.generate_key()
    wrapped = pii_keys.wrap_dek(dek)
    assert dek.decode() not in wrapped


def test_get_cached_dek_none_when_absent():
    assert pii_keys.get_cached_dek(None) is None
    assert pii_keys.get_cached_dek(999) is None


# ---------------------------------------------------------------------------
# Dual-read encrypt/decrypt
# ---------------------------------------------------------------------------


def _seed_dek(tenant_id: int) -> bytes:
    dek = Fernet.generate_key()
    pii_keys._DEK_CACHE[tenant_id] = dek
    return dek


def test_encrypt_decrypt_with_tenant_dek_roundtrips():
    _seed_dek(5)
    ct = encrypt_pii("alice@example.com", tenant_id=5)
    assert decrypt_pii(ct, tenant_id=5) == "alice@example.com"


def test_encryption_actually_uses_the_tenant_dek():
    # Encrypt with the DEK cached, then drop the cache: the legacy global key
    # must NOT be able to decrypt it — proving the DEK (not the global key) was
    # used for encryption.
    _seed_dek(5)
    ct = encrypt_pii("secret", tenant_id=5)
    pii_keys._clear_cache()
    with pytest.raises(ValueError):
        decrypt_pii(ct, tenant_id=5)


def test_dual_read_decrypts_legacy_global_ciphertext():
    # Written before the tenant had a DEK (cache empty -> global key)...
    ct = encrypt_pii("legacy@example.com", tenant_id=7)
    # ...then the tenant gets provisioned a DEK. Existing data must still decrypt.
    _seed_dek(7)
    assert decrypt_pii(ct, tenant_id=7) == "legacy@example.com"


def test_dual_read_decrypts_dek_ciphertext_when_dek_present():
    dek = _seed_dek(7)
    ct = encrypt_pii("new@example.com", tenant_id=7)
    # Sanity: the cached key is the one used.
    assert pii_keys.get_cached_dek(7) == dek
    assert decrypt_pii(ct, tenant_id=7) == "new@example.com"


def test_no_tenant_id_uses_global_and_roundtrips():
    ct = encrypt_pii("t@example.com")
    assert decrypt_pii(ct) == "t@example.com"


def test_empty_string_passthrough():
    assert encrypt_pii("", tenant_id=5) == ""
    assert decrypt_pii("", tenant_id=5) == ""


def test_corrupted_ciphertext_raises():
    with pytest.raises(ValueError):
        decrypt_pii("not-valid-ciphertext", tenant_id=5)
