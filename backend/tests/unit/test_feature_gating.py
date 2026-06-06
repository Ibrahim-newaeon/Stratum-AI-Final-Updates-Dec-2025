# =============================================================================
# Stratum AI - Feature Gating Tests
# =============================================================================
"""
Tests for tier-based feature gating (P0-5).

Before this, FeatureGate/TierGate/require_feature were applied to zero
endpoints — a free tenant could call enterprise features. These tests pin
the gate behaviour against the real TIER_FEATURES matrix.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import feature_gate as fg
from app.core.tiers import Feature, SubscriptionTier


def _request(tenant_id=5):
    return SimpleNamespace(state=SimpleNamespace(tenant_id=tenant_id))


async def test_starter_blocked_from_enterprise_feature(monkeypatch):
    async def fake_tier(_tenant_id):
        return SubscriptionTier.STARTER

    monkeypatch.setattr(fg, "get_tenant_tier", fake_tier)
    gate = fg.FeatureGate(Feature.WHAT_IF_SIMULATOR, check_subscription=False)

    with pytest.raises(HTTPException) as exc:
        await gate(_request())
    assert exc.value.status_code == 403


async def test_enterprise_allowed(monkeypatch):
    async def fake_tier(_tenant_id):
        return SubscriptionTier.ENTERPRISE

    monkeypatch.setattr(fg, "get_tenant_tier", fake_tier)
    gate = fg.FeatureGate(Feature.WHAT_IF_SIMULATOR, check_subscription=False)

    # Should not raise for an enterprise tenant.
    assert await gate(_request()) is None


async def test_gdpr_tools_gated_to_enterprise(monkeypatch):
    async def fake_tier(_tenant_id):
        return SubscriptionTier.PROFESSIONAL

    monkeypatch.setattr(fg, "get_tenant_tier", fake_tier)
    gate = fg.FeatureGate(Feature.GDPR_TOOLS, check_subscription=False)

    with pytest.raises(HTTPException) as exc:
        await gate(_request())
    assert exc.value.status_code == 403


def test_gated_features_are_not_in_starter_tier():
    """Guard: the features we gate must genuinely be non-Starter."""
    from app.core.tiers import has_feature

    for feature in (Feature.WHAT_IF_SIMULATOR, Feature.GDPR_TOOLS):
        assert not has_feature(SubscriptionTier.STARTER, feature)
        assert has_feature(SubscriptionTier.ENTERPRISE, feature)
