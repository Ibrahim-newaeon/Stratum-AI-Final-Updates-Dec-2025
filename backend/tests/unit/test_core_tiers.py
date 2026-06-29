# =============================================================================
# Stratum AI - Subscription Tiers unit tests
# =============================================================================
"""Unit tests for app.core.tiers.

Foundational subscription-tier limits + feature gating, pure logic. Covers the
tier hierarchy, limit lookups (incl. TierLimits dataclass), feature gating, and
tier-info assembly.
"""

import pytest

from app.core.tiers import (
    Feature,
    SubscriptionTier,
    TierLimits,
    get_available_features,
    get_tier_features,
    get_tier_info,
    get_tier_limit,
    get_tier_limits,
    has_feature,
    tier_at_least,
)

pytestmark = pytest.mark.unit

S = SubscriptionTier.STARTER
P = SubscriptionTier.PROFESSIONAL
E = SubscriptionTier.ENTERPRISE


# =============================================================================
# Hierarchy
# =============================================================================
class TestHierarchy:
    def test_higher_tier_at_least_lower(self):
        assert tier_at_least(E, S) is True
        assert tier_at_least(P, S) is True

    def test_lower_tier_not_at_least_higher(self):
        assert tier_at_least(S, E) is False

    def test_same_tier_qualifies(self):
        assert tier_at_least(P, P) is True


# =============================================================================
# Limits
# =============================================================================
class TestLimits:
    def test_limits_are_monotonic(self):
        s, e = get_tier_limits(S), get_tier_limits(E)
        assert isinstance(s, TierLimits)
        assert e.max_users >= s.max_users
        assert e.max_ad_accounts >= s.max_ad_accounts

    def test_specific_limit_lookup(self):
        assert get_tier_limit(E, "max_users") > 0

    def test_unknown_limit_returns_zero(self):
        assert get_tier_limit(S, "definitely_not_a_limit") == 0

    def test_tierlimits_from_dict_defaults_missing_to_zero(self):
        tl = TierLimits.from_dict({"max_users": 5})
        assert tl.max_users == 5
        assert tl.max_ad_accounts == 0  # missing key -> default


# =============================================================================
# Features
# =============================================================================
class TestFeatures:
    def test_features_are_cumulative(self):
        starter = set(get_tier_features(S))
        enterprise = set(get_tier_features(E))
        assert starter  # starter has at least some features
        assert starter.issubset(enterprise)  # higher tiers include lower ones

    def test_has_feature_consistency(self):
        # any feature the starter tier has, enterprise must also have
        starter_feats = get_available_features(S)
        assert starter_feats
        feat = Feature(starter_feats[0])
        assert has_feature(S, feat) is True
        assert has_feature(E, feat) is True

    def test_available_features_are_strings(self):
        feats = get_available_features(P)
        assert all(isinstance(f, str) for f in feats)


# =============================================================================
# Tier info
# =============================================================================
class TestTierInfo:
    def test_info_shape(self):
        info = get_tier_info(P)
        assert info["tier"] == "professional"
        assert isinstance(info["features"], list)
        assert isinstance(info["limits"], dict)
