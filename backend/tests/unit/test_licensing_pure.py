# =============================================================================
# Stratum AI - License Validation Pure-Logic Unit Tests
# =============================================================================
"""Unit tests for the pure logic in
``app.services.tenant.licensing.LicenseValidationService``.

Covers offline HMAC license verification, domain matching (exact +
wildcard), the STRAT-{TIER}-{...} offline parse path, license-server
response parsing, in-memory cache TTL, and the fail-closed signing-secret
resolver. Network/online validation and heartbeats are out of scope here.
"""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.tiers import SubscriptionTier
from app.services.tenant.licensing import (
    LicenseInfo,
    LicenseStatus,
    LicenseValidationService,
    _license_signing_secret,
)

pytestmark = pytest.mark.unit


def _encode_payload(payload: dict, secret: str) -> str:
    """Build an HMAC-signed ``{data_b64}.{signature}`` blob the service can verify."""
    data = json.dumps(payload).encode()
    # The verifier appends "==" before urlsafe_b64decode, so strip padding here.
    data_b64 = base64.urlsafe_b64encode(data).decode().rstrip("=")
    signature = hmac.new(secret.encode(), data_b64.encode(), hashlib.sha256).hexdigest()
    return f"{data_b64}.{signature}"


@pytest.fixture
def service() -> LicenseValidationService:
    # No-arg constructor; only the in-memory cache is touched by pure helpers.
    return LicenseValidationService()


@pytest.fixture
def secret() -> str:
    return _license_signing_secret()


# =============================================================================
# _license_signing_secret
# =============================================================================
class TestSigningSecret:
    def test_returns_nonempty_in_dev(self):
        # Test env is not production/staging, so a usable secret is returned.
        assert _license_signing_secret()


# =============================================================================
# _verify_hmac_license
# =============================================================================
class TestVerifyHmac:
    def test_round_trips_payload(self, service, secret):
        payload = {"customer_id": "cust_1", "max_users": 9}
        encoded = _encode_payload(payload, secret)
        assert service._verify_hmac_license(encoded) == payload

    def test_bad_signature_rejected(self, service, secret):
        encoded = _encode_payload({"customer_id": "x"}, secret)
        data_b64, _sig = encoded.rsplit(".", 1)
        tampered = f"{data_b64}.{'0' * 64}"
        with pytest.raises(ValueError, match="Invalid signature"):
            service._verify_hmac_license(tampered)

    def test_missing_separator_rejected(self, service):
        with pytest.raises(ValueError, match="Invalid license format"):
            service._verify_hmac_license("no-dot-separator")


# =============================================================================
# _domain_matches
# =============================================================================
class TestDomainMatches:
    def test_exact_match_case_insensitive(self, service):
        assert service._domain_matches("App.Example.COM", ["app.example.com"])

    def test_no_match(self, service):
        assert not service._domain_matches("evil.com", ["app.example.com"])

    def test_wildcard_subdomain(self, service):
        assert service._domain_matches("api.example.com", ["*.example.com"])

    def test_wildcard_matches_base(self, service):
        assert service._domain_matches("example.com", ["*.example.com"])

    def test_empty_allowed_is_no_match(self, service):
        assert not service._domain_matches("example.com", [])


# =============================================================================
# _validate_offline
# =============================================================================
class TestValidateOffline:
    def test_valid_professional_license(self, service, secret):
        future = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
        key = "STRAT-PRO-" + _encode_payload(
            {"exp": future, "customer_id": "c1", "tenant_id": 7, "max_users": 25},
            secret,
        )
        info = service._validate_offline(key, current_domain=None)
        assert info.status == LicenseStatus.VALID
        assert info.tier == SubscriptionTier.PROFESSIONAL
        assert info.tenant_id == 7
        assert info.max_users == 25

    def test_grace_period_when_recently_expired(self, service, secret):
        expired = int((datetime.now(UTC) - timedelta(days=2)).timestamp())
        key = "STRAT-ST-" + _encode_payload(
            {"exp": expired, "customer_id": "c"}, secret
        )
        info = service._validate_offline(key, current_domain=None)
        assert info.status == LicenseStatus.GRACE_PERIOD
        assert info.grace_period_ends_at is not None

    def test_expired_past_grace(self, service, secret):
        expired = int((datetime.now(UTC) - timedelta(days=30)).timestamp())
        key = "STRAT-ST-" + _encode_payload(
            {"exp": expired, "customer_id": "c"}, secret
        )
        info = service._validate_offline(key, current_domain=None)
        assert info.status == LicenseStatus.EXPIRED

    def test_domain_mismatch(self, service, secret):
        future = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
        key = "STRAT-ENT-" + _encode_payload(
            {"exp": future, "domains": ["app.example.com"]}, secret
        )
        info = service._validate_offline(key, current_domain="evil.com")
        assert info.status == LicenseStatus.DOMAIN_MISMATCH
        assert info.tier == SubscriptionTier.ENTERPRISE

    def test_malformed_key_raises(self, service):
        with pytest.raises(ValueError, match="Invalid license key format"):
            service._validate_offline("NOTSTRAT-PRO-abc", current_domain=None)

    def test_unknown_tier_code_defaults_to_starter(self, service, secret):
        future = int((datetime.now(UTC) + timedelta(days=10)).timestamp())
        key = "STRAT-XX-" + _encode_payload({"exp": future}, secret)
        info = service._validate_offline(key, current_domain=None)
        assert info.tier == SubscriptionTier.STARTER


# =============================================================================
# _parse_license_response
# =============================================================================
class TestParseResponse:
    def test_maps_status_tier_and_dates(self, service):
        info = service._parse_license_response(
            {
                "status": "valid",
                "tier": "enterprise",
                "tenant_id": 3,
                "customer_id": "acme",
                "max_users": 50,
                "expires_at": "2026-12-31T00:00:00Z",
            },
            current_domain=None,
        )
        assert info.status == LicenseStatus.VALID
        assert info.tier == SubscriptionTier.ENTERPRISE
        assert info.tenant_id == 3
        assert info.expires_at.year == 2026

    def test_unknown_status_falls_back_to_invalid(self, service):
        info = service._parse_license_response({"status": "weird"}, current_domain=None)
        assert info.status == LicenseStatus.INVALID
        assert info.tier == SubscriptionTier.STARTER


# =============================================================================
# in-memory cache
# =============================================================================
class TestCache:
    def _info(self) -> LicenseInfo:
        return LicenseInfo(
            status=LicenseStatus.VALID,
            tier=SubscriptionTier.PROFESSIONAL,
            tenant_id=1,
            customer_id="c",
            allowed_domains=[],
            max_users=5,
            features=[],
            expires_at=None,
            grace_period_ends_at=None,
        )

    def test_miss_returns_none(self, service):
        assert service._get_cached_license("absent") is None

    def test_hit_returns_cached(self, service):
        info = self._info()
        service._cache_license("k", info)
        assert service._get_cached_license("k") is info

    def test_expired_entry_is_evicted(self, service):
        info = self._info()
        stale = datetime.now(UTC) - timedelta(seconds=service.CACHE_DURATION + 10)
        service._cache["k"] = (info, stale)
        assert service._get_cached_license("k") is None
        assert "k" not in service._cache
