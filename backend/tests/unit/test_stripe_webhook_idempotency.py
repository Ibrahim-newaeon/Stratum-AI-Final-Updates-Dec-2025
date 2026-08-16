# =============================================================================
# Stratum AI - Stripe Webhook Idempotency and Retry Semantics
# =============================================================================
"""Duplicate suppression and what the endpoint tells Stripe when it fails.

Two faults, both of which made the endpoint report success while doing
nothing useful:

1. Idempotency was a module-level `set()`, with a comment conceding "in
   production with multiple workers, use Redis instead" — and production runs
   `uvicorn --workers 4`. A retry had a 3-in-4 chance of hitting a worker that
   had never seen the event, the set died on every restart, and the eviction
   was `.clear()`, dropping all 10,000 entries at once.

2. Handler errors were swallowed and answered 200. A KeyError on an unexpected
   payload discarded the event permanently while telling Stripe it had been
   processed — so a missed invoice.payment_failed left a delinquent account
   with full access and produced no signal anywhere.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints import stripe_webhook

pytestmark = pytest.mark.asyncio


class FakeRedis:
    """Honours SET NX semantics, which is the whole point of the claim."""

    def __init__(self):
        self.store = {}
        self.set_calls = []

    async def set(self, key, value, nx=False, ex=None):
        self.set_calls.append({"key": key, "nx": nx, "ex": ex})
        if nx and key in self.store:
            return None  # redis-py returns None when NX loses
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return 1


class TestClaimIsAtomicAndShared:
    async def test_first_claim_wins_second_loses(self):
        redis = FakeRedis()
        with patch.object(
            stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
        ):
            assert await stripe_webhook._claim_event("evt_1") is True
            assert await stripe_webhook._claim_event("evt_1") is False

    async def test_distinct_events_do_not_collide(self):
        redis = FakeRedis()
        with patch.object(
            stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
        ):
            assert await stripe_webhook._claim_event("evt_1") is True
            assert await stripe_webhook._claim_event("evt_2") is True

    async def test_claim_is_set_nx_with_an_expiry(self):
        """NX is what makes two workers safe; the TTL keeps the key bounded.

        It must outlive Stripe's retry schedule (~3 days) or a late retry
        would be re-processed as if new.
        """
        redis = FakeRedis()
        with patch.object(
            stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
        ):
            await stripe_webhook._claim_event("evt_1")

        call = redis.set_calls[0]
        assert call["nx"] is True
        assert call["key"] == "stripe:event:evt_1"
        assert call["ex"] >= 3 * 24 * 60 * 60

    async def test_release_lets_a_retry_through(self):
        """A failed handler must not leave its event looking processed."""
        redis = FakeRedis()
        with patch.object(
            stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
        ):
            assert await stripe_webhook._claim_event("evt_1") is True
            await stripe_webhook._release_event("evt_1")
            assert await stripe_webhook._claim_event("evt_1") is True


class TestRedisUnavailable:
    """Fails open, and says so.

    The handlers re-fetch state from Stripe and are idempotent, so a duplicate
    is close to harmless. Refusing events while Redis is down would leave
    subscription state stale, which is the worse failure.
    """

    async def test_claim_returns_none_when_redis_is_down(self):
        with patch.object(
            stripe_webhook,
            "get_redis_pool",
            AsyncMock(side_effect=ConnectionError("redis down")),
        ):
            assert await stripe_webhook._claim_event("evt_1") is None

    async def test_release_does_not_raise_when_redis_is_down(self):
        with patch.object(
            stripe_webhook,
            "get_redis_pool",
            AsyncMock(side_effect=ConnectionError("redis down")),
        ):
            await stripe_webhook._release_event("evt_1")  # must not raise


class _FakeSession:
    """async context manager standing in for async_session_maker()."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def _stripe_event(event_id="evt_fail", event_type="invoice.payment_failed"):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=event_id,
        type=event_type,
        data=SimpleNamespace(object={}),
    )


class TestHandlerFailureAsksStripeToRetry:
    """A failing handler must not be reported to Stripe as success.

    The old code caught ValueError/KeyError/TypeError and returned 200 —
    "prevent retries for our app logic errors". For billing that discards the
    event permanently: a missed invoice.payment_failed leaves a delinquent
    account with full access, and Stripe considers the delivery successful, so
    nothing surfaces anywhere.
    """

    @staticmethod
    def _request():
        from unittest.mock import MagicMock

        request = MagicMock()
        request.body = AsyncMock(return_value=b"{}")
        request.headers = {"stripe-signature": "sig"}
        return request

    async def _run_with_failing_handler(self, redis, exc):
        from fastapi import HTTPException

        session = _FakeSession()
        with (
            patch.object(stripe_webhook.stripe_service, "STRIPE_CONFIGURED", True),
            patch.object(stripe_webhook.settings, "stripe_webhook_secret", "whsec_x"),
            patch.object(
                stripe_webhook.stripe.Webhook,
                "construct_event",
                return_value=_stripe_event(),
            ),
            patch.object(
                stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
            ),
            patch.object(stripe_webhook, "async_session_maker", lambda: session),
            patch.object(
                stripe_webhook,
                "handle_invoice_payment_failed",
                AsyncMock(side_effect=exc),
            ),
        ):
            with pytest.raises(HTTPException) as caught:
                await stripe_webhook.stripe_webhook(self._request())
        return caught.value, session

    @pytest.mark.parametrize(
        "exc", [KeyError("customer"), ValueError("bad"), TypeError("nope")]
    )
    async def test_returns_5xx_instead_of_200(self, exc):
        redis = FakeRedis()
        error, session = await self._run_with_failing_handler(redis, exc)
        assert error.status_code >= 500
        assert session.rolled_back is True
        assert session.committed is False

    async def test_claim_is_released_so_the_retry_is_processed(self):
        redis = FakeRedis()
        await self._run_with_failing_handler(redis, KeyError("customer"))

        # The retry must be able to claim the event again.
        with patch.object(
            stripe_webhook, "get_redis_pool", AsyncMock(return_value=redis)
        ):
            assert await stripe_webhook._claim_event("evt_fail") is True


class TestNoProcessLocalState:
    """The per-process set must not come back.

    Pinned by name because the regression is invisible at one worker: with a
    single process the set behaves correctly, and only fans out into missed
    duplicates under `--workers 4`.
    """

    def test_module_has_no_in_memory_event_cache(self):
        assert not hasattr(stripe_webhook, "_processed_events"), (
            "idempotency is back in process memory; it does not survive "
            "restarts and is not shared across uvicorn workers"
        )
        assert hasattr(stripe_webhook, "_claim_event")
