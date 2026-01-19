# =============================================================================
# Stratum AI - Token Encryption Service
# =============================================================================
"""
Encryption utilities for OAuth tokens and sensitive credentials.
Wraps core security functions for token-specific operations.
"""

from app.core.security import encrypt_pii, decrypt_pii


def encrypt_token(token: str) -> str:
    """
    Encrypt an OAuth token or other sensitive credential.

    Args:
        token: The plaintext token to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    if not token:
        return ""
    return encrypt_pii(token)


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an OAuth token or other sensitive credential.

    Args:
        encrypted_token: The encrypted token to decrypt

    Returns:
        The plaintext token
    """
    if not encrypted_token:
        return ""
    return decrypt_pii(encrypted_token)
