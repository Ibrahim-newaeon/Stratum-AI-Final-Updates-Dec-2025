# =============================================================================
# Stratum AI - Token Encryption Service
# =============================================================================
"""
Encryption utilities for OAuth tokens and sensitive credentials.
Wraps core security functions for token-specific operations.
"""

from app.core.security import decrypt_pii, encrypt_pii


def encrypt_token(token: str, tenant_id: int) -> str:
    """
    Encrypt an OAuth token or other sensitive credential.

    ``tenant_id`` is required, not optional: omitting it silently selects the
    single global-derived key, which is how platform credentials came to sit
    outside the per-tenant key scheme (AUTH-05) that user PII already uses.
    Every caller has it — the encrypted column and ``tenant_id`` live on the
    same row.

    Args:
        token: The plaintext token to encrypt
        tenant_id: Owning tenant, used to select the data-encryption key

    Returns:
        Base64-encoded encrypted string
    """
    if not token:
        return ""
    return encrypt_pii(token, tenant_id)


def decrypt_token(encrypted_token: str, tenant_id: int) -> str:
    """
    Decrypt an OAuth token or other sensitive credential.

    Safe for tokens written before the tenant was threaded through:
    ``decrypt_pii`` dual-reads the tenant DEK, the tenant-salted key, then the
    true-global key.

    Args:
        encrypted_token: The encrypted token to decrypt
        tenant_id: Owning tenant, used to select the data-encryption key

    Returns:
        The plaintext token
    """
    if not encrypted_token:
        return ""
    return decrypt_pii(encrypted_token, tenant_id)
