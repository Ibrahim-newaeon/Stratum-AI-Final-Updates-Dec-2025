# =============================================================================
# Stratum AI - License Validation Service
# =============================================================================
"""
License key validation and management for self-hosted deployments.

Supports:
- Online license validation (phone home)
- Offline license validation (signed JWT)
- License heartbeat for usage tracking
- Grace period handling for expired licenses
"""

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tiers import SubscriptionTier

logger = get_logger(__name__)


class LicenseStatus(str, Enum):
    """License validation status."""
    VALID = "valid"
    EXPIRED = "expired"
    GRACE_PERIOD = "grace_period"
    INVALID = "invalid"
    REVOKED = "revoked"
    DOMAIN_MISMATCH = "domain_mismatch"


@dataclass
class LicenseInfo:
    """Information about a validated license."""
    status: LicenseStatus
    tier: SubscriptionTier
    tenant_id: Optional[int]
    customer_id: str
    allowed_domains: list[str]
    max_users: int
    features: list[str]
    expires_at: Optional[datetime]
    grace_period_ends_at: Optional[datetime]
    is_trial: bool = False
    message: Optional[str] = None


class LicenseValidationService:
    """
    Service for validating and managing software licenses.

    Supports both online (API) and offline (JWT) validation modes.
    """

    # License server URL (configure in production)
    LICENSE_SERVER_URL = os.getenv(
        "LICENSE_SERVER_URL",
        "https://license.stratum.ai/api/v1"
    )

    # Public key for offline JWT validation
    LICENSE_PUBLIC_KEY = os.getenv("LICENSE_PUBLIC_KEY", "")

    # Grace period after expiration (days)
    GRACE_PERIOD_DAYS = 7

    # Cache duration for valid licenses (seconds)
    CACHE_DURATION = 3600  # 1 hour

    def __init__(self):
        self._cache: dict[str, tuple[LicenseInfo, datetime]] = {}

    async def validate_license(
        self,
        license_key: str,
        current_domain: Optional[str] = None,
    ) -> LicenseInfo:
        """
        Validate a license key.

        Args:
            license_key: The license key to validate
            current_domain: The domain making the request (for domain locking)

        Returns:
            LicenseInfo with validation results

        Raises:
            LicenseValidationError: If validation fails completely
        """
        # Check cache first
        cached = self._get_cached_license(license_key)
        if cached:
            return cached

        # Try online validation first
        try:
            license_info = await self._validate_online(license_key, current_domain)
            self._cache_license(license_key, license_info)
            return license_info
        except Exception as e:
            logger.warning("online_license_validation_failed", error=str(e))

        # Fall back to offline validation
        try:
            license_info = self._validate_offline(license_key, current_domain)
            self._cache_license(license_key, license_info)
            return license_info
        except Exception as e:
            logger.error("offline_license_validation_failed", error=str(e))
            return LicenseInfo(
                status=LicenseStatus.INVALID,
                tier=SubscriptionTier.STARTER,
                tenant_id=None,
                customer_id="",
                allowed_domains=[],
                max_users=0,
                features=[],
                expires_at=None,
                grace_period_ends_at=None,
                message="License validation failed",
            )

    async def _validate_online(
        self,
        license_key: str,
        current_domain: Optional[str],
    ) -> LicenseInfo:
        """Validate license by calling the license server."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.LICENSE_SERVER_URL}/validate",
                json={
                    "license_key": license_key,
                    "domain": current_domain,
                    "product": "stratum-ai",
                    "version": settings.app_version if hasattr(settings, 'app_version') else "1.0.0",
                },
                headers={
                    "X-Product-ID": "stratum-ai",
                },
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_license_response(data, current_domain)
            elif response.status_code == 404:
                return LicenseInfo(
                    status=LicenseStatus.INVALID,
                    tier=SubscriptionTier.STARTER,
                    tenant_id=None,
                    customer_id="",
                    allowed_domains=[],
                    max_users=0,
                    features=[],
                    expires_at=None,
                    grace_period_ends_at=None,
                    message="License key not found",
                )
            else:
                raise Exception(f"License server returned {response.status_code}")

    def _validate_offline(
        self,
        license_key: str,
        current_domain: Optional[str],
    ) -> LicenseInfo:
        """
        Validate license offline using signed JWT.

        License key format: STRAT-{TIER}-{ENCODED_JWT}
        The JWT contains all license information and is signed with our private key.
        """
        # Parse license key format
        parts = license_key.split("-", 2)
        if len(parts) < 3 or parts[0] != "STRAT":
            raise ValueError("Invalid license key format")

        tier_code = parts[1]
        encoded_data = parts[2]

        # Map tier code to enum
        tier_map = {
            "ST": SubscriptionTier.STARTER,
            "PRO": SubscriptionTier.PROFESSIONAL,
            "ENT": SubscriptionTier.ENTERPRISE,
        }
        tier = tier_map.get(tier_code, SubscriptionTier.STARTER)

        # Decode and verify JWT
        try:
            if self.LICENSE_PUBLIC_KEY:
                payload = jwt.decode(
                    encoded_data,
                    self.LICENSE_PUBLIC_KEY,
                    algorithms=["RS256"],
                )
            else:
                # Fallback: verify signature using HMAC
                payload = self._verify_hmac_license(encoded_data)
        except JWTError as e:
            raise ValueError(f"Invalid license signature: {e}")

        # Check expiration
        expires_at = None
        if "exp" in payload:
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        grace_period_ends_at = None
        status = LicenseStatus.VALID

        if expires_at:
            now = datetime.now(timezone.utc)
            if now > expires_at:
                grace_period_ends_at = expires_at + timedelta(days=self.GRACE_PERIOD_DAYS)
                if now > grace_period_ends_at:
                    status = LicenseStatus.EXPIRED
                else:
                    status = LicenseStatus.GRACE_PERIOD

        # Check domain
        allowed_domains = payload.get("domains", [])
        if current_domain and allowed_domains:
            if not self._domain_matches(current_domain, allowed_domains):
                status = LicenseStatus.DOMAIN_MISMATCH

        return LicenseInfo(
            status=status,
            tier=tier,
            tenant_id=payload.get("tenant_id"),
            customer_id=payload.get("customer_id", ""),
            allowed_domains=allowed_domains,
            max_users=payload.get("max_users", 3),
            features=payload.get("features", []),
            expires_at=expires_at,
            grace_period_ends_at=grace_period_ends_at,
            is_trial=payload.get("is_trial", False),
        )

    def _verify_hmac_license(self, encoded_data: str) -> dict:
        """Verify HMAC-signed license data."""
        # Simple HMAC verification for development
        # In production, use RSA/EC signatures
        secret = os.getenv("LICENSE_SIGNING_SECRET", "dev-secret-change-me")

        parts = encoded_data.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError("Invalid license format")

        data_b64, signature = parts

        # Verify signature
        import base64
        expected_sig = hmac.new(
            secret.encode(),
            data_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")

        # Decode data
        data = base64.urlsafe_b64decode(data_b64 + "==").decode()
        return json.loads(data)

    def _parse_license_response(
        self,
        data: dict,
        current_domain: Optional[str],
    ) -> LicenseInfo:
        """Parse license server response into LicenseInfo."""
        status_map = {
            "valid": LicenseStatus.VALID,
            "expired": LicenseStatus.EXPIRED,
            "grace_period": LicenseStatus.GRACE_PERIOD,
            "revoked": LicenseStatus.REVOKED,
            "invalid": LicenseStatus.INVALID,
        }

        tier_map = {
            "starter": SubscriptionTier.STARTER,
            "professional": SubscriptionTier.PROFESSIONAL,
            "enterprise": SubscriptionTier.ENTERPRISE,
        }

        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        grace_period_ends_at = None
        if data.get("grace_period_ends_at"):
            grace_period_ends_at = datetime.fromisoformat(
                data["grace_period_ends_at"].replace("Z", "+00:00")
            )

        return LicenseInfo(
            status=status_map.get(data.get("status", "invalid"), LicenseStatus.INVALID),
            tier=tier_map.get(data.get("tier", "starter"), SubscriptionTier.STARTER),
            tenant_id=data.get("tenant_id"),
            customer_id=data.get("customer_id", ""),
            allowed_domains=data.get("allowed_domains", []),
            max_users=data.get("max_users", 3),
            features=data.get("features", []),
            expires_at=expires_at,
            grace_period_ends_at=grace_period_ends_at,
            is_trial=data.get("is_trial", False),
            message=data.get("message"),
        )

    def _domain_matches(self, current: str, allowed: list[str]) -> bool:
        """Check if current domain matches any allowed domain."""
        current = current.lower().strip()

        for domain in allowed:
            domain = domain.lower().strip()
            # Exact match
            if current == domain:
                return True
            # Wildcard subdomain match (*.example.com)
            if domain.startswith("*."):
                base = domain[2:]
                if current.endswith(base) or current == base:
                    return True

        return False

    def _get_cached_license(self, license_key: str) -> Optional[LicenseInfo]:
        """Get license from cache if valid."""
        if license_key in self._cache:
            info, cached_at = self._cache[license_key]
            if datetime.now(timezone.utc) - cached_at < timedelta(seconds=self.CACHE_DURATION):
                return info
            del self._cache[license_key]
        return None

    def _cache_license(self, license_key: str, info: LicenseInfo) -> None:
        """Cache a validated license."""
        self._cache[license_key] = (info, datetime.now(timezone.utc))

    async def send_heartbeat(
        self,
        license_key: str,
        metrics: Optional[dict] = None,
    ) -> bool:
        """
        Send heartbeat to license server with usage metrics.

        This allows tracking usage and detecting unauthorized deployments.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.LICENSE_SERVER_URL}/heartbeat",
                    json={
                        "license_key": license_key,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metrics": metrics or {},
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("heartbeat_failed", error=str(e))
            return False


# Convenience alias
LicenseValidator = LicenseValidationService


# Singleton instance
_license_service: Optional[LicenseValidationService] = None


def get_license_service() -> LicenseValidationService:
    """Get the singleton license validation service."""
    global _license_service
    if _license_service is None:
        _license_service = LicenseValidationService()
    return _license_service
