# =============================================================================
# Stratum AI - Stripe Price/Tier Mapping Unit Tests
# =============================================================================
"""Unit tests for the pure helpers in ``app.services.stripe_service``:

- ``get_price_id_for_tier`` / ``get_tier_for_price_id`` tier<->price-id
  round-trip mapping (driven by settings)
- ``configure_stripe`` secret-key gating

The Stripe-SDK-backed customer/subscription calls are out of scope here.
"""

import pytest

from app.core.config import settings
from app.core.tiers import SubscriptionTier
from app.services import stripe_service
from app.services.stripe_service import (
    configure_stripe,
    get_price_id_for_tier,
    get_tier_for_price_id,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def price_ids(monkeypatch):
    monkeypatch.setattr(settings, "stripe_starter_price_id", "price_starter")
    monkeypatch.setattr(settings, "stripe_professional_price_id", "price_pro")
    monkeypatch.setattr(settings, "stripe_enterprise_price_id", "price_ent")


# =============================================================================
# get_price_id_for_tier
# =============================================================================
class TestPriceIdForTier:
    @pytest.mark.parametrize(
        "tier,price_id",
        [
            (SubscriptionTier.STARTER, "price_starter"),
            (SubscriptionTier.PROFESSIONAL, "price_pro"),
            (SubscriptionTier.ENTERPRISE, "price_ent"),
        ],
    )
    def test_maps_each_tier(self, price_ids, tier, price_id):
        assert get_price_id_for_tier(tier) == price_id


# =============================================================================
# get_tier_for_price_id
# =============================================================================
class TestTierForPriceId:
    @pytest.mark.parametrize(
        "price_id,tier",
        [
            ("price_starter", SubscriptionTier.STARTER),
            ("price_pro", SubscriptionTier.PROFESSIONAL),
            ("price_ent", SubscriptionTier.ENTERPRISE),
        ],
    )
    def test_reverse_mapping(self, price_ids, price_id, tier):
        assert get_tier_for_price_id(price_id) == tier

    def test_empty_price_id_is_none(self, price_ids):
        assert get_tier_for_price_id("") is None

    def test_unknown_price_id_is_none(self, price_ids):
        assert get_tier_for_price_id("price_unknown") is None

    def test_round_trip(self, price_ids):
        for tier in (
            SubscriptionTier.STARTER,
            SubscriptionTier.PROFESSIONAL,
            SubscriptionTier.ENTERPRISE,
        ):
            assert get_tier_for_price_id(get_price_id_for_tier(tier)) == tier


# =============================================================================
# configure_stripe
# =============================================================================
class TestConfigureStripe:
    def test_returns_false_without_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "stripe_secret_key", "")
        assert configure_stripe() is False

    def test_returns_true_and_sets_api_key(self, monkeypatch):
        monkeypatch.setattr(
            settings, "stripe_secret_key", "sk_test_x"
        )  # gitleaks:allow
        assert configure_stripe() is True
        assert stripe_service.stripe.api_key == "sk_test_x"  # gitleaks:allow
