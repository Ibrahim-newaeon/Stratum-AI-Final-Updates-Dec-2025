import pytest
from cryptography.fernet import Fernet
from app.core import pii_keys
from app.core.security import decrypt_pii, encrypt_pii


def test_totp_secret_roundtrips_under_tenant_dek():
    pii_keys._clear_cache()
    pii_keys._DEK_CACHE[55] = Fernet.generate_key()
    enc = encrypt_pii("JBSWY3DPEHPK3PXP", 55)
    assert decrypt_pii(enc, 55) == "JBSWY3DPEHPK3PXP"
    # not decodable under the global key path (no DEK for tenant 999)
    with pytest.raises(ValueError):
        decrypt_pii(enc, 999)
    pii_keys._clear_cache()
