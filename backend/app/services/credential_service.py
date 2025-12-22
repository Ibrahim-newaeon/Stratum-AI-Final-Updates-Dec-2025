# =============================================================================
# Stratum AI - Credential Encryption Service
# =============================================================================
"""
Service for encrypting and decrypting platform credentials.
Uses Fernet symmetric encryption with tenant-specific keys.
"""

import base64
import hashlib
import json
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CredentialEncryptionService:
    """
    Encrypts and decrypts platform credentials.

    Uses Fernet symmetric encryption with a key derived from:
    - Application secret key
    - Tenant ID (for tenant isolation)
    """

    def __init__(self):
        """Initialize with base secret from settings."""
        self._base_secret = settings.secret_key

    def _derive_key(self, tenant_id: int) -> bytes:
        """
        Derive a Fernet key from the base secret and tenant ID.

        Args:
            tenant_id: Tenant ID for key derivation

        Returns:
            32-byte key suitable for Fernet
        """
        # Combine base secret with tenant ID
        combined = f"{self._base_secret}:{tenant_id}"

        # Use SHA-256 to get 32 bytes, then base64 encode for Fernet
        key_bytes = hashlib.sha256(combined.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    def encrypt(self, credentials: Dict[str, Any], tenant_id: int) -> str:
        """
        Encrypt credentials dictionary.

        Args:
            credentials: Dictionary of credentials to encrypt
            tenant_id: Tenant ID for key derivation

        Returns:
            Base64-encoded encrypted string
        """
        key = self._derive_key(tenant_id)
        fernet = Fernet(key)

        # Convert to JSON and encrypt
        json_bytes = json.dumps(credentials).encode("utf-8")
        encrypted = fernet.encrypt(json_bytes)

        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_data: str, tenant_id: int) -> Dict[str, Any]:
        """
        Decrypt credentials string back to dictionary.

        Args:
            encrypted_data: Base64-encoded encrypted string
            tenant_id: Tenant ID for key derivation

        Returns:
            Original credentials dictionary

        Raises:
            ValueError: If decryption fails
        """
        try:
            key = self._derive_key(tenant_id)
            fernet = Fernet(key)

            # Decrypt and parse JSON
            decrypted = fernet.decrypt(encrypted_data.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))

        except Exception as e:
            logger.error(f"Credential decryption failed: {e}")
            raise ValueError("Failed to decrypt credentials")


# Global instance
_credential_service: Optional[CredentialEncryptionService] = None


def get_credential_service() -> CredentialEncryptionService:
    """Get or create the credential encryption service."""
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialEncryptionService()
    return _credential_service
