# =============================================================================
# Stratum AI - WhatsApp Webhook Structure Tests
# =============================================================================
"""
Covers the verb-split webhook: GET /webhook is the handshake, POST /webhook
carries events, and the old paths keep answering until Meta's app config is
repointed.

The dispatcher tests matter most. Meta packs delivery statuses and inbound
customer messages under the same `messages` field, and retries anything that
is not a 200 — so an unrecognised field must not raise.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.whatsapp import (
    _dispatch_webhook_change,
    _handle_inbound_messages,
    _handle_status_updates,
)


class TestWebhookDispatch:
    """Routing one changes[] entry to the handler that owns it."""

    @pytest.mark.asyncio
    async def test_messages_field_runs_both_handlers(self):
        """`messages` carries statuses AND inbound messages — both must run."""
        db = AsyncMock()
        change = {"field": "messages", "value": {"statuses": [], "messages": []}}

        with patch(
            "app.api.v1.endpoints.whatsapp._handle_status_updates",
            new=AsyncMock(return_value=0),
        ) as statuses, patch(
            "app.api.v1.endpoints.whatsapp._handle_inbound_messages",
            new=AsyncMock(return_value=0),
        ) as inbound:
            await _dispatch_webhook_change(db, change)

        statuses.assert_awaited_once()
        inbound.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_field_does_not_raise(self):
        """Meta disables subscriptions that keep erroring — never raise here."""
        db = AsyncMock()
        change = {"field": "message_template_status_update", "value": {}}

        await _dispatch_webhook_change(db, change)

    @pytest.mark.asyncio
    async def test_missing_field_does_not_raise(self):
        """A malformed change with no field at all is still a 200."""
        db = AsyncMock()

        await _dispatch_webhook_change(db, {})


class TestStatusHandler:
    """Delivery-status transitions applied to the message they belong to."""

    @pytest.mark.asyncio
    async def test_incomplete_status_is_skipped(self):
        """A status missing id/status/timestamp is logged, not applied."""
        db = AsyncMock()
        value = {"statuses": [{"id": "wamid.1"}]}  # no status, no timestamp

        updated = await _handle_status_updates(db, value)

        assert updated == 0
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_status_for_unknown_message_is_skipped(self):
        """A status for a message we never sent is not an error."""
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        value = {
            "statuses": [
                {
                    "id": "wamid.unknown",
                    "status": "delivered",
                    "timestamp": "1700000000",
                }
            ]
        }

        updated = await _handle_status_updates(db, value)

        assert updated == 0
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delivered_status_sets_timestamp_and_history(self):
        """The happy path writes status, the matching timestamp, and history."""
        db = AsyncMock()
        message = MagicMock()
        message.status_history = None
        result = MagicMock()
        result.scalar_one_or_none.return_value = message
        db.execute.return_value = result

        value = {
            "statuses": [
                {"id": "wamid.1", "status": "delivered", "timestamp": "1700000000"}
            ]
        }

        updated = await _handle_status_updates(db, value)

        assert updated == 1
        assert message.status == "delivered"
        assert message.delivered_at is not None
        assert len(message.status_history) == 1
        assert message.status_history[0]["status"] == "delivered"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_replayed_status_is_idempotent(self):
        """Meta retries on any non-200; a replay must not corrupt state."""
        db = AsyncMock()
        message = MagicMock()
        message.status_history = None
        result = MagicMock()
        result.scalar_one_or_none.return_value = message
        db.execute.return_value = result

        value = {
            "statuses": [{"id": "wamid.1", "status": "read", "timestamp": "1700000000"}]
        }

        await _handle_status_updates(db, value)
        first_read_at = message.read_at

        await _handle_status_updates(db, value)

        assert message.status == "read"
        assert message.read_at == first_read_at


class TestInboundHandler:
    """Inbound customer messages are not stored — but must not vanish."""

    @pytest.mark.asyncio
    async def test_inbound_messages_are_counted_not_dropped(self):
        db = AsyncMock()
        value = {
            "messages": [
                {"id": "wamid.in.1", "from": "44700900000", "type": "text"},
                {"id": "wamid.in.2", "from": "44700900001", "type": "image"},
            ]
        }

        assert await _handle_inbound_messages(db, value) == 2

    @pytest.mark.asyncio
    async def test_no_inbound_messages_returns_zero(self):
        db = AsyncMock()

        assert await _handle_inbound_messages(db, {}) == 0


class TestWebhookRoutes:
    """The canonical paths exist, and the deprecated ones still answer."""

    def test_canonical_and_legacy_paths_registered(self):
        from app.api.v1.endpoints.whatsapp import router

        routes = {
            (path, method)
            for r in router.routes
            for path in [r.path]
            for method in r.methods
            if "webhook" in path
        }

        assert ("/webhook", "GET") in routes
        assert ("/webhook", "POST") in routes
        # Kept until Meta's configured URL is repointed.
        assert ("/webhooks/verify", "GET") in routes
        assert ("/webhooks/verify", "POST") in routes
        assert ("/webhooks/status", "POST") in routes


class TestVerifyHandshake:
    """The handshake compares a shared secret — timing-safe, and mode-checked."""

    @pytest.mark.asyncio
    async def test_correct_token_returns_challenge(self):
        from app.api.v1.endpoints.whatsapp import verify_webhook

        with patch("app.api.v1.endpoints.whatsapp.settings") as mock_settings:
            mock_settings.whatsapp_verify_token = "a-real-token"

            assert await verify_webhook("subscribe", "a-real-token", "12345") == 12345

    @pytest.mark.asyncio
    async def test_wrong_token_is_rejected(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.whatsapp import verify_webhook

        with patch("app.api.v1.endpoints.whatsapp.settings") as mock_settings:
            mock_settings.whatsapp_verify_token = "a-real-token"

            with pytest.raises(HTTPException) as exc:
                await verify_webhook("subscribe", "wrong", "12345")

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_mode_is_rejected(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.whatsapp import verify_webhook

        with patch("app.api.v1.endpoints.whatsapp.settings") as mock_settings:
            mock_settings.whatsapp_verify_token = "a-real-token"

            with pytest.raises(HTTPException) as exc:
                await verify_webhook("unsubscribe", "a-real-token", "12345")

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unset_token_rejects_empty_token(self):
        """An unconfigured deployment must not accept an empty verify token."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.whatsapp import verify_webhook

        with patch("app.api.v1.endpoints.whatsapp.settings") as mock_settings:
            mock_settings.whatsapp_verify_token = None

            with pytest.raises(HTTPException) as exc:
                await verify_webhook("subscribe", "anything", "12345")

        assert exc.value.status_code == 403
