# =============================================================================
# Stratum AI - Paddle Gateway
# =============================================================================
"""What the Paddle gateway must get right to be trusted with billing.

Three properties, each of which fails silently if broken:

1. **Signature verification.** A wrong HMAC scheme rejects every delivery and
   billing stops with no error from Paddle. A too-permissive one accepts forged
   events. Both are invisible without a test.
2. **Price mapping.** Paddle attaches trials to the price, so each paid tier has
   two price IDs. If only the base price maps back to its tier, every tenant who
   started on a trial gets their plan silently left unchanged the moment the
   subscription syncs.
3. **Transaction ownership.** ``sync_tenant_subscription`` must issue its UPDATE
   without committing, or the webhook wrapper's rollback becomes a no-op for the
   plan — the same defect ``test_billing_commit_ownership.py`` pins for Stripe.
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.core.tiers import SubscriptionTier
from app.services import paddle_service
from app.services.paddle_service import (
    ENTITLING_STATES,
    PaddleSubscription,
    SubscriptionState,
    get_price_id_for_tier,
    get_tier_for_price_id,
    subscription_from_api,
    sync_tenant_subscription,
    verify_webhook_signature,
)

_SECRET = "pdl_ntfset_test_secret"
_NOW = datetime(2026, 9, 2, tzinfo=UTC)


def _sign(body: bytes, secret: str = _SECRET, ts: int | None = None) -> str:
    """Build a Paddle-Signature header the way Paddle builds it."""
    if ts is None:
        ts = int(datetime.now(UTC).timestamp())
    digest = hmac.new(
        secret.encode(), f"{ts}:".encode() + body, hashlib.sha256
    ).hexdigest()
    return f"ts={ts};h1={digest}"


class TestSignatureVerification:
    """The gate that decides whether an event is real."""

    def test_accepts_a_genuine_signature(self):
        body = b'{"event_id":"evt_1","event_type":"subscription.created"}'
        assert verify_webhook_signature(body, _sign(body), secret=_SECRET) is True

    def test_signs_over_the_raw_body_not_reserialised_json(self):
        """Byte-for-byte, including key order and whitespace.

        This is the pitfall that breaks integrations which parse the body first
        and re-serialise it to verify: the JSON is equivalent but the bytes
        differ, so the digest never matches.
        """
        body = b'{"b":2,  "a":1}'
        header = _sign(body)
        assert verify_webhook_signature(body, header, secret=_SECRET) is True
        assert (
            verify_webhook_signature(b'{"a":1,"b":2}', header, secret=_SECRET) is False
        )

    def test_rejects_a_tampered_body(self):
        body = b'{"event_id":"evt_1","amount":"100"}'
        header = _sign(body)
        assert (
            verify_webhook_signature(
                b'{"event_id":"evt_1","amount":"999999"}', header, secret=_SECRET
            )
            is False
        )

    def test_rejects_the_wrong_secret(self):
        """Sandbox and live destinations have different secrets."""
        body = b'{"event_id":"evt_1"}'
        header = _sign(body, secret="pdl_ntfset_a_different_secret")
        assert verify_webhook_signature(body, header, secret=_SECRET) is False

    def test_rejects_a_stale_timestamp(self):
        """Bounds replay of a captured request."""
        body = b'{"event_id":"evt_1"}'
        old = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        header = _sign(body, ts=old)
        assert verify_webhook_signature(body, header, secret=_SECRET) is False

    def test_tolerance_is_configurable_so_clock_skew_is_recoverable(self):
        """The one knob that can reject 100% of webhooks.

        A host whose clock has drifted past the window fails every signature,
        and Paddle reports only "your endpoint rejected it". Widening must be
        possible without a code change.
        """
        body = b'{"event_id":"evt_1"}'
        skewed = int((datetime.now(UTC) - timedelta(seconds=120)).timestamp())
        header = _sign(body, ts=skewed)

        assert verify_webhook_signature(body, header, secret=_SECRET) is False
        assert (
            verify_webhook_signature(
                body, header, secret=_SECRET, tolerance_seconds=600
            )
            is True
        )

    @pytest.mark.parametrize(
        "header",
        ["", "garbage", "ts=;h1=", "h1=abc", "ts=notanumber;h1=abc", "ts=123"],
    )
    def test_malformed_headers_fail_closed_without_raising(self, header):
        """A malformed header is a failed verification, not a 500."""
        assert verify_webhook_signature(b"{}", header, secret=_SECRET) is False

    def test_missing_secret_fails_closed(self):
        body = b"{}"
        assert verify_webhook_signature(body, _sign(body), secret="") is False


class TestPriceMapping:
    """Both prices of a tier must resolve back to that tier."""

    def test_base_and_trial_prices_both_map_to_their_tier(self):
        with patch.multiple(
            settings,
            paddle_starter_price_id="pri_starter",
            paddle_starter_trial_price_id="pri_starter_trial",
            paddle_professional_price_id="pri_pro",
            paddle_professional_trial_price_id="pri_pro_trial",
            paddle_enterprise_price_id=None,
        ):
            assert get_tier_for_price_id("pri_starter") is SubscriptionTier.STARTER
            # The one that matters: a tenant who converts off a trial keeps
            # their plan only if the trial price still maps to the tier.
            assert (
                get_tier_for_price_id("pri_starter_trial") is SubscriptionTier.STARTER
            )
            assert get_tier_for_price_id("pri_pro") is SubscriptionTier.PROFESSIONAL
            assert (
                get_tier_for_price_id("pri_pro_trial") is SubscriptionTier.PROFESSIONAL
            )

    def test_unknown_and_empty_prices_map_to_nothing(self):
        with patch.multiple(
            settings,
            paddle_starter_price_id="pri_starter",
            paddle_starter_trial_price_id="pri_starter_trial",
            paddle_professional_price_id="pri_pro",
            paddle_professional_trial_price_id="pri_pro_trial",
            paddle_enterprise_price_id=None,
        ):
            assert get_tier_for_price_id("pri_someone_elses") is None
            assert get_tier_for_price_id("") is None

    def test_unset_price_ids_never_match(self):
        """An unconfigured tier must not swallow every unmapped price.

        With Enterprise unset, a naive equality check against None would make
        any price whose lookup returned None resolve to Enterprise.
        """
        with patch.multiple(
            settings,
            paddle_starter_price_id=None,
            paddle_starter_trial_price_id=None,
            paddle_professional_price_id=None,
            paddle_professional_trial_price_id=None,
            paddle_enterprise_price_id=None,
        ):
            assert get_tier_for_price_id("pri_anything") is None

    def test_enterprise_has_no_self_serve_price(self):
        """Which is what makes checkout refuse it and route to sales."""
        with patch.object(settings, "paddle_enterprise_price_id", None):
            assert get_price_id_for_tier(SubscriptionTier.ENTERPRISE) is None

    def test_trial_selection_picks_the_trial_price(self):
        with patch.multiple(
            settings,
            paddle_starter_price_id="pri_starter",
            paddle_starter_trial_price_id="pri_starter_trial",
        ):
            assert (
                get_price_id_for_tier(SubscriptionTier.STARTER, with_trial=False)
                == "pri_starter"
            )
            assert (
                get_price_id_for_tier(SubscriptionTier.STARTER, with_trial=True)
                == "pri_starter_trial"
            )


class TestEntitlement:
    """Which states grant a paid plan."""

    def test_only_active_trialing_and_past_due_entitle(self):
        assert ENTITLING_STATES == frozenset(
            {
                SubscriptionState.ACTIVE,
                SubscriptionState.TRIALING,
                SubscriptionState.PAST_DUE,
            }
        )

    def test_paused_does_not_entitle(self):
        """A paused subscription is not billing.

        Paddle keeps the row alive across a pause, so treating paused as
        entitling would leave a non-paying tenant on a paid plan indefinitely.
        """
        assert SubscriptionState.PAUSED not in ENTITLING_STATES

    def test_canceled_does_not_entitle(self):
        assert SubscriptionState.CANCELED not in ENTITLING_STATES


def _subscription(status=SubscriptionState.ACTIVE, tier=SubscriptionTier.PROFESSIONAL):
    return PaddleSubscription(
        id="sub_test",
        customer_id="ctm_test",
        status=status,
        tier=tier,
        price_id="pri_test",
        current_period_start=_NOW,
        current_period_end=_NOW + timedelta(days=30),
        cancel_at_period_end=False,
        canceled_at=None,
        trial_end=None,
    )


def _db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    return db


class TestTenantSync:
    """The service writes; the caller decides the outcome."""

    @pytest.mark.asyncio
    async def test_issues_the_update_but_does_not_commit(self):
        db = _db()
        await sync_tenant_subscription(db, 1, _subscription())
        assert db.execute.await_count == 1, "the UPDATE must still be issued"
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_entitling_state_with_unmapped_price_changes_nothing(self):
        """Guessing would either over-grant or strip a paying customer's plan."""
        db = _db()
        await sync_tenant_subscription(db, 1, _subscription(tier=None))
        db.execute.assert_not_awaited()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_entitling_state_downgrades_to_free(self):
        db = _db()
        await sync_tenant_subscription(
            db, 1, _subscription(status=SubscriptionState.CANCELED)
        )
        values = db.execute.await_args[0][0].compile().params
        assert values["plan"] == "free"


class TestSubscriptionProjection:
    """Paddle payload shapes that would otherwise raise mid-webhook."""

    def test_canceled_subscription_without_a_billing_period_does_not_raise(self):
        """Paddle omits current_billing_period once a subscription ends.

        sync_tenant_subscription calls .isoformat() on the period end, so a None
        here would 500 the webhook and make Paddle retry the same event forever.
        """
        projected = subscription_from_api(
            {
                "id": "sub_1",
                "customer_id": "ctm_1",
                "status": "canceled",
                "canceled_at": "2026-09-02T00:00:00Z",
                "items": [{"price": {"id": "pri_x"}}],
            }
        )
        assert projected.current_period_end is not None
        assert projected.canceled_at is not None

    def test_scheduled_cancellation_is_reported_as_cancel_at_period_end(self):
        """Paddle models this as a scheduled change, not a status change."""
        projected = subscription_from_api(
            {
                "id": "sub_1",
                "customer_id": "ctm_1",
                "status": "active",
                "scheduled_change": {
                    "action": "cancel",
                    "effective_at": "2026-10-01T00:00:00Z",
                },
                "current_billing_period": {
                    "starts_at": "2026-09-02T00:00:00Z",
                    "ends_at": "2026-10-01T00:00:00Z",
                },
                "items": [{"price": {"id": "pri_x"}}],
            }
        )
        assert projected.cancel_at_period_end is True
        assert projected.status is SubscriptionState.ACTIVE

    def test_a_pause_schedule_is_not_mistaken_for_a_cancellation(self):
        projected = subscription_from_api(
            {
                "id": "sub_1",
                "customer_id": "ctm_1",
                "status": "active",
                "scheduled_change": {"action": "pause"},
                "current_billing_period": {
                    "starts_at": "2026-09-02T00:00:00Z",
                    "ends_at": "2026-10-01T00:00:00Z",
                },
                "items": [{"price": {"id": "pri_x"}}],
            }
        )
        assert projected.cancel_at_period_end is False


class TestGatewayInterface:
    """paddle_service must stay substitutable for stripe_service."""

    def test_exposes_the_uniform_aliases_payments_dispatches_through(self):
        assert paddle_service.GATEWAY_NAME == "paddle"
        assert paddle_service.TENANT_CUSTOMER_FIELD == "paddle_customer_id"
        assert callable(paddle_service.sync_tenant_customer)

    def test_matches_the_stripe_gateway_surface(self):
        """Anything payments.py calls must exist on both modules."""
        from app.services import stripe_service

        required = (
            "CONFIGURED",
            "GATEWAY_NAME",
            "TENANT_CUSTOMER_FIELD",
            "sync_tenant_customer",
            "create_customer",
            "create_checkout_session",
            "create_portal_session",
            "get_customer_subscriptions",
            "update_subscription_tier",
            "cancel_subscription",
            "reactivate_subscription",
            "get_customer_invoices",
            "get_upcoming_invoice",
            "get_customer_payment_methods",
            "sync_tenant_subscription",
        )
        missing = [
            name
            for name in required
            if not hasattr(paddle_service, name) or not hasattr(stripe_service, name)
        ]
        assert missing == [], f"gateway surface mismatch: {missing}"
