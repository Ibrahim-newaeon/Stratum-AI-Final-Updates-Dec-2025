# =============================================================================
# Stratum AI - Subscription Entitlement
# =============================================================================
"""Which Stripe subscription states actually grant the paid plan.

sync_tenant_subscription assigned the plan before it looked at status:

    plan = subscription.tier.value          # always the paid tier
    if status in [ACTIVE, TRIALING]: ...    # only chose an expiry date
    else: plan_expires_at = current_period_end

so `incomplete`, `unpaid`, `incomplete_expired` and `paused` all wrote the
paid tier onto the tenant. `incomplete` is the one that leaks money: Stripe
emits customer.subscription.created with status=incomplete as soon as
checkout finishes, whether or not the first payment succeeded — so starting a
checkout and never paying granted the plan until current_period_end.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.tiers import SubscriptionTier
from app.services.stripe_service import (
    ENTITLING_STATES,
    StripeSubscription,
    SubscriptionState,
    sync_tenant_subscription,
)

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 8, 16, tzinfo=UTC)


def _subscription(status, tier=SubscriptionTier.ENTERPRISE, canceled_at=None):
    return StripeSubscription(
        id="sub_test",
        customer_id="cus_test",
        status=status,
        tier=tier,
        price_id="price_test",
        current_period_start=_NOW,
        current_period_end=_NOW + timedelta(days=30),
        cancel_at_period_end=False,
        canceled_at=canceled_at,
        trial_end=None,
    )


def _capture_db():
    """AsyncSession double that records the values() of each UPDATE."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    return db


def _written_plan(db):
    """Pull the `plan` column out of the UPDATE statement handed to execute().

    SQLAlchemy wraps each literal in a BindParameter, so unwrap to the value
    it carries rather than comparing against the wrapper.
    """
    assert db.execute.await_count == 1, "expected exactly one UPDATE"
    stmt = db.execute.await_args.args[0]
    values = {c.name: v for c, v in stmt._values.items()}
    plan = values["plan"]
    return getattr(plan, "value", plan)


class TestEntitlingStatesGrantThePlan:
    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionState.ACTIVE,
            SubscriptionState.TRIALING,
            SubscriptionState.PAST_DUE,
        ],
    )
    async def test_paid_tier_is_written(self, status):
        db = _capture_db()
        await sync_tenant_subscription(db, 1, _subscription(status))
        assert _written_plan(db) == "enterprise"

    async def test_past_due_keeps_access_during_dunning(self):
        """Stripe is still retrying; cutting access off on a failed charge is
        the wrong trade, and GRACE_PERIOD_DAYS exists for this window."""
        db = _capture_db()
        await sync_tenant_subscription(db, 1, _subscription(SubscriptionState.PAST_DUE))
        assert _written_plan(db) == "enterprise"


class TestNonEntitlingStatesDowngrade:
    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionState.INCOMPLETE,
            SubscriptionState.INCOMPLETE_EXPIRED,
            SubscriptionState.UNPAID,
            SubscriptionState.PAUSED,
            SubscriptionState.CANCELED,
        ],
    )
    async def test_downgrades_to_free(self, status):
        db = _capture_db()
        await sync_tenant_subscription(db, 1, _subscription(status))
        assert _written_plan(db) == "free"

    async def test_incomplete_never_grants_the_paid_plan(self):
        """The revenue leak, stated on its own.

        Checkout completes, payment does not, Stripe fires
        customer.subscription.created with status=incomplete.
        """
        db = _capture_db()
        await sync_tenant_subscription(
            db, 1, _subscription(SubscriptionState.INCOMPLETE)
        )
        assert _written_plan(db) == "free"

    async def test_every_state_is_classified(self):
        """A state absent from ENTITLING_STATES must downgrade, not error.

        Guards the fail-closed property: if Stripe adds a status and the enum
        grows, the new one lands in the non-entitling branch by default.
        """
        for status in SubscriptionState:
            db = _capture_db()
            await sync_tenant_subscription(db, 1, _subscription(status))
            expected = "enterprise" if status in ENTITLING_STATES else "free"
            assert _written_plan(db) == expected, status


class TestUnmappedPrice:
    """tier is None when the price is not one of the configured price IDs.

    get_tier_for_price_id returns None on no match, and the old code then did
    `subscription.tier.value` -> AttributeError. That is not in the webhook's
    `except (ValueError, KeyError, TypeError)`, so Stripe received a 500 and
    retried the same event indefinitely. With none of STRIPE_*_PRICE_ID set —
    which is the current production state — every real subscription would have
    hit it.
    """

    async def test_entitling_state_with_unknown_price_changes_nothing(self):
        db = _capture_db()
        await sync_tenant_subscription(
            db, 1, _subscription(SubscriptionState.ACTIVE, tier=None)
        )
        db.execute.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_non_entitling_state_with_unknown_price_still_downgrades(self):
        """Entitlement does not depend on knowing which tier was bought."""
        db = _capture_db()
        await sync_tenant_subscription(
            db, 1, _subscription(SubscriptionState.INCOMPLETE, tier=None)
        )
        assert _written_plan(db) == "free"
