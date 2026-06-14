# =============================================================================
# Stratum AI - Subscription Logic Unit Tests
# =============================================================================
"""Unit tests for the pure functions of ``app.core.subscription``.

Covers status calculation across the active / expiring / grace / expired
bands, validity and access checks, and next-billing-date math. The
DB-backed get_subscription_info and the FastAPI guards are covered
elsewhere.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.subscription import (
    SubscriptionStatus,
    calculate_next_billing_date,
    calculate_subscription_status,
    is_access_allowed,
    is_subscription_valid,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


# =============================================================================
# calculate_subscription_status
# =============================================================================
class TestCalculateStatus:
    def test_free_plan_never_expires(self):
        status, until, grace = calculate_subscription_status("free", None, now=_NOW)
        assert status == SubscriptionStatus.FREE
        assert until is None and grace is None

    def test_no_expiry_is_active(self):
        status, until, grace = calculate_subscription_status(
            "professional", None, now=_NOW
        )
        assert status == SubscriptionStatus.ACTIVE
        assert until is None and grace is None

    def test_far_future_is_active(self):
        status, until, _ = calculate_subscription_status(
            "professional", _NOW + timedelta(days=30), now=_NOW
        )
        assert status == SubscriptionStatus.ACTIVE
        assert until == 30

    def test_expiring_soon(self):
        status, until, _ = calculate_subscription_status(
            "professional", _NOW + timedelta(days=10), now=_NOW
        )
        assert status == SubscriptionStatus.EXPIRING_SOON
        assert until == 10

    def test_grace_period(self):
        status, until, grace = calculate_subscription_status(
            "professional", _NOW - timedelta(days=3), now=_NOW
        )
        assert status == SubscriptionStatus.GRACE_PERIOD
        assert until == 0
        assert grace == 3

    def test_fully_expired(self):
        status, until, grace = calculate_subscription_status(
            "professional", _NOW - timedelta(days=20), now=_NOW
        )
        assert status == SubscriptionStatus.EXPIRED
        assert until == 0
        assert grace == 20

    def test_naive_expiry_is_treated_as_utc(self):
        # A naive datetime must not raise; it's coerced to UTC.
        naive = (_NOW + timedelta(days=30)).replace(tzinfo=None)
        status, _, _ = calculate_subscription_status("professional", naive, now=_NOW)
        assert status == SubscriptionStatus.ACTIVE


# =============================================================================
# validity / access
# =============================================================================
class TestValidityAndAccess:
    def test_is_subscription_valid(self):
        assert is_subscription_valid(SubscriptionStatus.ACTIVE)
        assert is_subscription_valid(SubscriptionStatus.EXPIRING_SOON)
        assert is_subscription_valid(SubscriptionStatus.FREE)
        assert not is_subscription_valid(SubscriptionStatus.GRACE_PERIOD)
        assert not is_subscription_valid(SubscriptionStatus.EXPIRED)

    def test_access_allows_grace_only_when_flagged(self):
        assert is_access_allowed(SubscriptionStatus.GRACE_PERIOD, allow_grace=True)
        assert not is_access_allowed(SubscriptionStatus.GRACE_PERIOD, allow_grace=False)

    def test_expired_never_allowed(self):
        assert not is_access_allowed(SubscriptionStatus.EXPIRED, allow_grace=True)


# =============================================================================
# next billing date
# =============================================================================
class TestNextBillingDate:
    def test_yearly(self):
        assert calculate_next_billing_date(_NOW, "yearly") == _NOW + timedelta(days=365)

    def test_quarterly(self):
        assert calculate_next_billing_date(_NOW, "quarterly") == _NOW + timedelta(
            days=90
        )

    def test_monthly_default(self):
        assert calculate_next_billing_date(_NOW) == _NOW + timedelta(days=30)
