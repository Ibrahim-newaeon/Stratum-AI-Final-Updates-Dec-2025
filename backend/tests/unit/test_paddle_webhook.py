# =============================================================================
# Stratum AI - Paddle Webhook Endpoint
# =============================================================================
"""The full webhook path, end to end, without a tunnel.

This is the one path a sandbox checkout would exercise that nothing else does:
signature -> claim -> dispatch -> tenant resolution -> plan update. Every failure
mode here is silent in production — Paddle reports only "your endpoint rejected
it", or nothing at all when we wrongly answer 200 — so each one is pinned.

Mirrors ``test_stripe_webhook_idempotency.py``: a FakeRedis honouring SET NX,
because the claim's whole purpose is that two ``uvicorn`` workers handling the
same retry cannot both run the handlers.
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import paddle_webhook
from app.core.config import settings
from app.core.tiers import SubscriptionTier

pytestmark = pytest.mark.asyncio

_SECRET = "pdl_ntfset_test_secret"


class FakeRedis:
    """Honours SET NX semantics, which is the whole point of the claim.

    Returns `str` from get(), matching the real pool built with
    `decode_responses=True`. An earlier version returned bytes, which made the
    staleness guard's tests pass against behaviour the real client never had —
    the guard was a no-op in production and only an end-to-end run found it.
    """

    def __init__(self):
        self.store = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None  # redis-py returns None when NX loses
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)
        return 1


def _sign(body: bytes, secret: str = _SECRET, ts: int | None = None) -> str:
    if ts is None:
        ts = int(datetime.now(UTC).timestamp())
    digest = hmac.new(
        secret.encode(), f"{ts}:".encode() + body, hashlib.sha256
    ).hexdigest()
    return f"ts={ts};h1={digest}"


def _subscription_event(
    event_id="evt_1",
    event_type="subscription.activated",
    status="active",
    tenant_id="7",
    price_id="pri_pro",
    occurred_at="2026-09-02T00:00:00Z",
):
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "data": {
            "id": "sub_1",
            "customer_id": "ctm_1",
            "status": status,
            "custom_data": {"tenant_id": tenant_id},
            "current_billing_period": {
                "starts_at": "2026-09-02T00:00:00Z",
                "ends_at": "2026-10-02T00:00:00Z",
            },
            "items": [{"price": {"id": price_id}}],
        },
    }


def _request(body: bytes, signature: str | None = None):
    """A Request double carrying raw bytes — what the signature is computed over."""
    request = MagicMock()
    request.body = AsyncMock(return_value=body)
    request.json = AsyncMock(return_value=json.loads(body))
    request.headers = {
        "paddle-signature": signature if signature is not None else _sign(body)
    }
    request.client = MagicMock()
    request.client.host = "34.237.3.244"  # a published Paddle address
    return request


class _Ctx:
    """Patches everything the endpoint touches outside its own logic."""

    def __init__(self, redis=None, tenant=None, db=None):
        self.redis = redis or FakeRedis()
        self.tenant = (
            tenant if tenant is not None else MagicMock(id=7, paddle_customer_id=None)
        )
        self.db = db or AsyncMock()
        self.db.commit = AsyncMock()
        self.db.rollback = AsyncMock()
        self.synced = []

    def __enter__(self):
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=self.db)
        session.__aexit__ = AsyncMock(return_value=False)

        async def _sync(db, tenant_id, subscription):
            self.synced.append((tenant_id, subscription))

        self._patches = [
            patch.object(settings, "paddle_webhook_secret", _SECRET),
            patch.object(settings, "paddle_starter_price_id", "pri_starter"),
            patch.object(settings, "paddle_professional_price_id", "pri_pro"),
            patch.object(
                paddle_webhook, "get_redis_pool", AsyncMock(return_value=self.redis)
            ),
            patch.object(
                paddle_webhook, "async_session_maker", MagicMock(return_value=session)
            ),
            patch.object(
                paddle_webhook, "get_tenant_by_id", AsyncMock(return_value=self.tenant)
            ),
            patch.object(
                paddle_webhook,
                "get_tenant_by_customer_id",
                AsyncMock(return_value=self.tenant),
            ),
            # The IP list is fetched over the network; pin it so the test is hermetic.
            patch.object(
                paddle_webhook,
                "_fetch_paddle_ips",
                AsyncMock(return_value=["34.237.3.244/32"]),
            ),
            patch.object(
                paddle_webhook.paddle_service, "sync_tenant_subscription", _sync
            ),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        return False


class TestSignatureGatesEverything:
    async def test_a_valid_event_is_processed(self):
        body = json.dumps(_subscription_event()).encode()
        with _Ctx() as ctx:
            result = await paddle_webhook.paddle_webhook(_request(body))
        assert result["status"] == "received"
        assert len(ctx.synced) == 1
        tenant_id, sub = ctx.synced[0]
        assert tenant_id == 7
        assert sub.tier is SubscriptionTier.PROFESSIONAL
        ctx.db.commit.assert_awaited()

    async def test_a_forged_signature_is_rejected_before_any_work(self):
        body = json.dumps(_subscription_event()).encode()
        with _Ctx() as ctx:
            with pytest.raises(Exception) as exc:
                await paddle_webhook.paddle_webhook(_request(body, "ts=1;h1=deadbeef"))
        assert exc.value.status_code == 400
        assert ctx.synced == [], "no handler may run for an unverified event"
        ctx.db.commit.assert_not_awaited()

    async def test_a_tampered_body_is_rejected(self):
        """Signature covers the raw bytes, so an edited amount fails."""
        original = json.dumps(_subscription_event()).encode()
        signature = _sign(original)
        tampered = json.dumps(_subscription_event(tenant_id="999")).encode()
        with _Ctx() as ctx:
            with pytest.raises(Exception) as exc:
                await paddle_webhook.paddle_webhook(_request(tampered, signature))
        assert exc.value.status_code == 400
        assert ctx.synced == []

    async def test_missing_signature_header_is_rejected(self):
        body = json.dumps(_subscription_event()).encode()
        with _Ctx():
            with pytest.raises(Exception) as exc:
                await paddle_webhook.paddle_webhook(_request(body, ""))
        assert exc.value.status_code == 400


class TestIdempotency:
    async def test_a_retry_of_a_processed_event_is_skipped(self):
        """Paddle re-sends the same event_id for up to ~3 days."""
        body = json.dumps(_subscription_event()).encode()
        redis = FakeRedis()
        with _Ctx(redis=redis) as ctx:
            first = await paddle_webhook.paddle_webhook(_request(body))
            second = await paddle_webhook.paddle_webhook(_request(body))
        assert first["status"] == "received"
        assert second["status"] == "already_processed"
        assert len(ctx.synced) == 1, "the handler must not run twice"

    async def test_distinct_events_both_process(self):
        redis = FakeRedis()
        with _Ctx(redis=redis) as ctx:
            await paddle_webhook.paddle_webhook(
                _request(json.dumps(_subscription_event(event_id="evt_a")).encode())
            )
            await paddle_webhook.paddle_webhook(
                _request(
                    json.dumps(
                        _subscription_event(
                            event_id="evt_b", occurred_at="2026-09-02T01:00:00Z"
                        )
                    ).encode()
                )
            )
        assert len(ctx.synced) == 2

    async def test_redis_outage_refuses_the_event_rather_than_double_applying(self):
        """Fail closed: Paddle retries a 503, so an outage delays billing."""
        body = json.dumps(_subscription_event()).encode()
        with _Ctx() as ctx:
            with patch.object(
                paddle_webhook,
                "get_redis_pool",
                AsyncMock(side_effect=ConnectionError("down")),
            ):
                with pytest.raises(Exception) as exc:
                    await paddle_webhook.paddle_webhook(_request(body))
        assert exc.value.status_code == 503
        assert ctx.synced == []


class TestFailureAsksPaddleToRetry:
    async def test_handler_error_returns_5xx_and_rolls_back(self):
        """Answering 2xx on a failure is the one status that loses the event."""
        body = json.dumps(_subscription_event()).encode()
        with _Ctx() as ctx:
            with patch.object(
                paddle_webhook,
                "handle_subscription_event",
                AsyncMock(side_effect=KeyError("unexpected payload shape")),
            ):
                with pytest.raises(Exception) as exc:
                    await paddle_webhook.paddle_webhook(_request(body))
        assert exc.value.status_code == 500
        ctx.db.rollback.assert_awaited()
        ctx.db.commit.assert_not_awaited()

    async def test_a_failed_events_claim_is_released_so_the_retry_runs(self):
        """Otherwise the retry is skipped as a duplicate — losing the event."""
        body = json.dumps(_subscription_event()).encode()
        redis = FakeRedis()
        with _Ctx(redis=redis):
            with patch.object(
                paddle_webhook,
                "handle_subscription_event",
                AsyncMock(side_effect=RuntimeError("boom")),
            ):
                with pytest.raises(Exception):
                    await paddle_webhook.paddle_webhook(_request(body))
        assert not any(
            k.startswith("paddle:event:") for k in redis.store
        ), "the claim must be released so Paddle's retry is not skipped"


class TestOrdering:
    async def test_a_retried_older_event_cannot_regress_newer_state(self):
        """Paddle does not order deliveries and retries re-send the ORIGINAL
        payload, so a late `subscription.created` can arrive after a newer
        `subscription.updated`."""
        redis = FakeRedis()
        newer = json.dumps(
            _subscription_event(event_id="evt_new", occurred_at="2026-09-02T12:00:00Z")
        ).encode()
        older = json.dumps(
            _subscription_event(
                event_id="evt_old",
                event_type="subscription.created",
                occurred_at="2026-09-02T09:00:00Z",
            )
        ).encode()
        with _Ctx(redis=redis) as ctx:
            await paddle_webhook.paddle_webhook(_request(newer))
            await paddle_webhook.paddle_webhook(_request(older))
        assert len(ctx.synced) == 1, "the stale event must not be applied"


class TestUnknownEvents:
    async def test_an_unhandled_event_type_is_acknowledged_not_retried_forever(self):
        body = json.dumps(
            {
                "event_id": "evt_x",
                "event_type": "report.updated",
                "data": {"id": "rep_1"},
            }
        ).encode()
        with _Ctx() as ctx:
            result = await paddle_webhook.paddle_webhook(_request(body))
        assert result["status"] == "received"
        assert ctx.synced == []

    async def test_a_malformed_envelope_is_rejected(self):
        body = json.dumps({"data": {"id": "sub_1"}}).encode()  # no event_id/type
        with _Ctx():
            with pytest.raises(Exception) as exc:
                await paddle_webhook.paddle_webhook(_request(body))
        assert exc.value.status_code == 400


class TestIpAllowlistIsEnvironmentAware:
    """Sandbox and production deliver from different address ranges.

    Found by rehearsal, not by reading docs: Paddle's own simulation arrived
    from 3.208.120.145, which is published in the sandbox list and absent from
    the production one. The handler originally fetched the production list
    unconditionally, so enabling enforcement while pointed at sandbox would
    have rejected every genuine, correctly-signed delivery.
    """

    async def test_each_environment_fetches_its_own_list(self):
        with patch.object(settings, "paddle_environment", "sandbox"):
            assert paddle_webhook._ips_url() == "https://sandbox-api.paddle.com/ips"
        with patch.object(settings, "paddle_environment", "production"):
            assert paddle_webhook._ips_url() == "https://api.paddle.com/ips"

    async def test_the_cache_key_is_per_environment(self):
        """Otherwise a switch serves the other environment's addresses."""
        with patch.object(settings, "paddle_environment", "sandbox"):
            sandbox_key = paddle_webhook._ips_cache_key()
        with patch.object(settings, "paddle_environment", "production"):
            production_key = paddle_webhook._ips_cache_key()
        assert sandbox_key != production_key

    async def test_an_unevaluable_list_does_not_reject_the_delivery(self):
        """Losing the list must not take billing down for a Paddle outage.

        The signature check is the real gate; the allowlist is defence in
        depth, so "cannot evaluate" has to mean allow.
        """
        request = _request(json.dumps(_subscription_event()).encode())
        with patch.object(
            paddle_webhook, "_fetch_paddle_ips", AsyncMock(return_value=[])
        ):
            assert await paddle_webhook._check_source_ip(request) is True
