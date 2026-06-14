# =============================================================================
# Stratum AI - Feature Gate (pure helpers) Unit Tests
# =============================================================================
"""Unit tests for the I/O-free helpers of ``app.core.feature_gate``.

Covers tier resolution and the settings-fallback feature/limit checks:
``get_required_tier``, ``get_current_tier``, ``check_feature``,
``check_limit``, and ``get_tier_features_response``. The DB- and
request-backed paths (FeatureGate/TierGate, *_for_tenant) are covered by
the integration suite.
"""

import pytest

from app.core.feature_gate import (
    check_feature,
    check_limit,
    get_current_tier,
    get_required_tier,
    get_tier_features_response,
)
from app.core.tiers import Feature, SubscriptionTier

pytestmark = pytest.mark.unit

_ALL_TIERS = set(SubscriptionTier)


class TestGetRequiredTier:
    def test_returns_a_tier_or_none(self):
        for feature in Feature:
            result = get_required_tier(feature)
            assert result is None or result in _ALL_TIERS

    def test_enterprise_feature_requires_enterprise(self):
        # GDPR tooling is an Enterprise-only feature.
        assert get_required_tier(Feature.GDPR_TOOLS) == SubscriptionTier.ENTERPRISE


class TestCurrentTier:
    def test_returns_valid_tier(self):
        assert get_current_tier() in _ALL_TIERS


class TestCheckFeature:
    def test_returns_bool(self):
        assert isinstance(check_feature(Feature.GDPR_TOOLS), bool)


class TestCheckLimit:
    def test_below_limit_is_true(self):
        # A negative/zero count is always within any positive limit.
        assert check_limit("max_users", -1) is True

    def test_absurdly_high_count_exceeds_limit(self):
        assert check_limit("max_users", 1_000_000_000) is False


class TestTierFeaturesResponse:
    def test_has_pricing_and_is_dict(self):
        resp = get_tier_features_response()
        assert isinstance(resp, dict)
        assert "pricing" in resp
