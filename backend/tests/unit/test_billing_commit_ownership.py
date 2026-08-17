# =============================================================================
# Stratum AI - Billing Transaction Ownership
# =============================================================================
"""Who commits the tenant's plan change.

``sync_tenant_subscription`` committed its own UPDATE. The Stripe webhook wraps
every handler in commit-on-success / rollback-on-failure (``stripe_webhook.py``
lines 218 and 241), so that inner commit made the rollback a no-op for the
plan: it was already durable while everything else the handler did got
discarded.

``handle_checkout_completed`` shows the window plainly. It writes
``stripe_customer_id``, then calls ``sync_tenant_subscription`` — whose commit
persists both writes before the wrapper has decided the event even succeeded.
A failure after that point asks Stripe to retry an event whose plan change is
already applied.

The transaction belongs to the caller. The service issues the UPDATE and
nothing more; the webhook wrapper commits it, and each payments.py endpoint
commits its own.
"""

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import payments
from app.core.tiers import SubscriptionTier
from app.services.stripe_service import (
    StripeSubscription,
    SubscriptionState,
    sync_tenant_subscription,
)

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _subscription(status=SubscriptionState.ACTIVE):
    """One subscription that satisfies all three endpoint filters.

    ``upgrade`` and ``cancel`` want status active/trialing; ``reactivate``
    additionally wants ``cancel_at_period_end``.
    """
    return StripeSubscription(
        id="sub_test",
        customer_id="cus_test",
        status=status,
        tier=SubscriptionTier.PROFESSIONAL,
        price_id="price_test",
        current_period_start=_NOW,
        current_period_end=_NOW + timedelta(days=30),
        cancel_at_period_end=True,
        canceled_at=None,
        trial_end=None,
    )


def _db():
    """AsyncSession double that records commits and UPDATEs."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    return db


class TestServiceLeavesTheTransactionOpen:
    """The service writes; it does not decide the outcome."""

    async def test_sync_issues_the_update_but_does_not_commit(self):
        db = _db()

        await sync_tenant_subscription(db, 1, _subscription())

        assert db.execute.await_count == 1, "the UPDATE must still be issued"
        db.commit.assert_not_awaited()


def _patched_stripe(stack, sub):
    """Patch every Stripe touchpoint the three endpoints reach."""
    stack.enter_context(
        patch.object(payments.stripe_service, "STRIPE_CONFIGURED", True)
    )
    tenant = MagicMock()
    tenant.id = 1
    tenant.stripe_customer_id = "cus_test"
    stack.enter_context(
        patch.object(
            payments,
            "get_tenant_from_request",
            AsyncMock(return_value=tenant),
        )
    )
    for name in (
        "get_customer_subscriptions",
        "update_subscription_tier",
        "cancel_subscription",
        "reactivate_subscription",
        "sync_tenant_subscription",
    ):
        value = [sub] if name == "get_customer_subscriptions" else sub
        if name == "sync_tenant_subscription":
            value = None
        stack.enter_context(
            patch.object(payments.stripe_service, name, AsyncMock(return_value=value))
        )


async def _call(endpoint: str, db):
    sub = _subscription()
    request = MagicMock()
    with ExitStack() as stack:
        _patched_stripe(stack, sub)
        if endpoint == "upgrade":
            body = MagicMock()
            body.new_tier = "professional"
            body.prorate = True
            await payments.upgrade_subscription(
                body=body, request=request, db=db, _=None
            )
        elif endpoint == "cancel":
            await payments.cancel_subscription(request=request, db=db, _=None)
        else:
            await payments.reactivate_subscription(request=request, db=db, _=None)


class TestEndpointsCommitTheirOwnTransaction:
    """No webhook wrapper here, so the endpoint must commit or the plan
    change is discarded when the session closes."""

    @pytest.mark.parametrize("endpoint", ["upgrade", "cancel", "reactivate"])
    async def test_endpoint_commits_after_syncing(self, endpoint):
        db = _db()

        await _call(endpoint, db)

        db.commit.assert_awaited_once()
