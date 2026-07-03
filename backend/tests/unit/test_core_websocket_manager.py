# =============================================================================
# Stratum AI - WebSocket Manager Unit Tests
# =============================================================================
"""Unit tests for the in-process half of ``app.core.websocket``.

Uses a fresh ``WebSocketManager`` per test (never the module-global
``ws_manager``) with ``_redis=None`` and AsyncMock sockets, so no network,
Redis, or background tasks are involved. The Redis-connected paths
(``start``/``stop``/``_redis_listener``/``_heartbeat_loop``/
``_publish_to_redis``/``_handle_redis_message``) are integration-tested
elsewhere.
"""

import json
from typing import Optional
from unittest.mock import AsyncMock

import pytest

import app.core.websocket as ws_module
from app.core.websocket import MessageType, WebSocketManager, WebSocketMessage

pytestmark = pytest.mark.unit


@pytest.fixture
def manager() -> WebSocketManager:
    """Fresh manager with no Redis and no background tasks."""
    return WebSocketManager()


def _socket() -> AsyncMock:
    """AsyncMock standing in for a starlette WebSocket."""
    return AsyncMock()


async def _connect(
    manager: WebSocketManager,
    tenant_id: Optional[int] = 1,
    user_id: Optional[int] = None,
) -> tuple[str, AsyncMock]:
    """Connect a mock socket and return (client_id, socket)."""
    sock = _socket()
    client_id = await manager.connect(sock, tenant_id=tenant_id, user_id=user_id)
    return client_id, sock


def _sent_types(sock: AsyncMock) -> list[str]:
    """Message types sent over a mock socket, in order."""
    return [json.loads(c.args[0])["type"] for c in sock.send_text.await_args_list]


# =============================================================================
# connect / disconnect
# =============================================================================


class TestConnectDisconnect:
    async def test_connect_accepts_and_tracks_tenant(
        self, manager: WebSocketManager
    ) -> None:
        """Connecting accepts the socket and indexes the client by tenant."""
        client_id, sock = await _connect(manager, tenant_id=7, user_id=3)

        sock.accept.assert_awaited_once()
        assert client_id in manager._connections
        assert client_id in manager._tenant_connections[7]
        assert manager._connections[client_id].user_id == 3

    async def test_connect_without_tenant_skips_tenant_index(
        self, manager: WebSocketManager
    ) -> None:
        """Anonymous connections are not tenant-indexed."""
        client_id, _ = await _connect(manager, tenant_id=None)

        assert client_id in manager._connections
        assert manager._tenant_connections == {}

    async def test_disconnect_cleans_tenant_and_channel_state(
        self, manager: WebSocketManager
    ) -> None:
        """Disconnect closes the socket and removes every index entry."""
        client_id, sock = await _connect(manager, tenant_id=7)
        await manager.subscribe(client_id, "emq")

        await manager.disconnect(client_id)

        sock.close.assert_awaited_once()
        assert client_id not in manager._connections
        assert 7 not in manager._tenant_connections  # empty set removed
        assert client_id not in manager._channel_subscriptions.get("emq", set())

    async def test_disconnect_swallows_close_errors(
        self, manager: WebSocketManager
    ) -> None:
        """A socket that is already gone does not break cleanup."""
        client_id, sock = await _connect(manager)
        sock.close.side_effect = RuntimeError("already closed")

        await manager.disconnect(client_id)
        assert client_id not in manager._connections

    async def test_disconnect_unknown_client_is_a_noop(
        self, manager: WebSocketManager
    ) -> None:
        """Disconnecting a never-connected id must not raise."""
        await manager.disconnect("no-such-client")

    async def test_disconnect_anonymous_client(self, manager: WebSocketManager) -> None:
        """Clients without a tenant disconnect cleanly."""
        client_id, sock = await _connect(manager, tenant_id=None)

        await manager.disconnect(client_id)

        sock.close.assert_awaited_once()
        assert client_id not in manager._connections

    async def test_disconnect_keeps_tenant_entry_for_remaining_clients(
        self, manager: WebSocketManager
    ) -> None:
        """The tenant index survives while other clients remain connected."""
        id_a, _ = await _connect(manager, tenant_id=7)
        id_b, _ = await _connect(manager, tenant_id=7)

        await manager.disconnect(id_a)

        assert manager._tenant_connections[7] == {id_b}

    async def test_disconnect_tolerates_stale_channel_reference(
        self, manager: WebSocketManager
    ) -> None:
        """A subscribed channel missing from the index does not break cleanup."""
        client_id, _ = await _connect(manager)
        manager._connections[client_id].subscribed_channels.add("phantom")

        await manager.disconnect(client_id)
        assert client_id not in manager._connections


# =============================================================================
# subscribe / unsubscribe
# =============================================================================


class TestSubscriptions:
    async def test_subscribe_registers_both_directions(
        self, manager: WebSocketManager
    ) -> None:
        """Subscription is tracked on the client and in the channel index."""
        client_id, _ = await _connect(manager)

        await manager.subscribe(client_id, "incidents")

        assert "incidents" in manager._connections[client_id].subscribed_channels
        assert client_id in manager._channel_subscriptions["incidents"]

    async def test_unsubscribe_removes_both_directions(
        self, manager: WebSocketManager
    ) -> None:
        """Unsubscribing clears the client and channel index."""
        client_id, _ = await _connect(manager)
        await manager.subscribe(client_id, "incidents")

        await manager.unsubscribe(client_id, "incidents")

        assert "incidents" not in manager._connections[client_id].subscribed_channels
        assert client_id not in manager._channel_subscriptions["incidents"]

    async def test_second_subscriber_joins_existing_channel(
        self, manager: WebSocketManager
    ) -> None:
        """A second subscriber is added to the already-created channel set."""
        id_a, _ = await _connect(manager)
        id_b, _ = await _connect(manager)

        await manager.subscribe(id_a, "incidents")
        await manager.subscribe(id_b, "incidents")

        assert manager._channel_subscriptions["incidents"] == {id_a, id_b}

    async def test_unsubscribe_from_unknown_channel_is_a_noop(
        self, manager: WebSocketManager
    ) -> None:
        """Unsubscribing from a channel that never existed must not raise."""
        client_id, _ = await _connect(manager)
        await manager.unsubscribe(client_id, "never-created")

    async def test_subscribe_unknown_client_is_a_noop(
        self, manager: WebSocketManager
    ) -> None:
        """Subscribing an unknown client changes nothing."""
        await manager.subscribe("ghost", "incidents")
        assert "incidents" not in manager._channel_subscriptions

    async def test_unsubscribe_unknown_client_is_a_noop(
        self, manager: WebSocketManager
    ) -> None:
        """Unsubscribing an unknown client must not raise."""
        await manager.unsubscribe("ghost", "incidents")


# =============================================================================
# send_to_client
# =============================================================================


class TestSendToClient:
    async def test_sends_serialized_message(self, manager: WebSocketManager) -> None:
        """The message reaches the socket as its JSON serialization."""
        client_id, sock = await _connect(manager)
        message = WebSocketMessage(type="emq_update", payload={"score": 88})

        await manager.send_to_client(client_id, message)

        sock.send_text.assert_awaited_once_with(message.to_json())

    async def test_unknown_client_is_a_noop(self, manager: WebSocketManager) -> None:
        """Sending to an unknown id is silently ignored."""
        await manager.send_to_client("ghost", WebSocketMessage(type="x", payload={}))

    async def test_send_failure_auto_disconnects(
        self, manager: WebSocketManager
    ) -> None:
        """A dead socket is disconnected instead of raising."""
        client_id, sock = await _connect(manager, tenant_id=9)
        sock.send_text.side_effect = RuntimeError("broken pipe")

        await manager.send_to_client(client_id, WebSocketMessage(type="x", payload={}))

        assert client_id not in manager._connections
        assert 9 not in manager._tenant_connections


# =============================================================================
# broadcasts
# =============================================================================


class TestBroadcasts:
    async def test_broadcast_to_tenant_is_isolated(
        self, manager: WebSocketManager
    ) -> None:
        """Only the target tenant's clients receive the broadcast."""
        _, sock_a = await _connect(manager, tenant_id=1)
        _, sock_b = await _connect(manager, tenant_id=1)
        _, sock_other = await _connect(manager, tenant_id=2)

        await manager.broadcast_to_tenant(1, "emq_update", {"score": 90})

        sock_a.send_text.assert_awaited_once()
        sock_b.send_text.assert_awaited_once()
        sock_other.send_text.assert_not_awaited()
        assert json.loads(sock_a.send_text.await_args.args[0])["payload"] == {
            "score": 90
        }

    async def test_broadcast_to_channel_targets_subscribers(
        self, manager: WebSocketManager
    ) -> None:
        """Only channel subscribers receive channel broadcasts."""
        sub_id, sock_sub = await _connect(manager)
        _, sock_nosub = await _connect(manager)
        await manager.subscribe(sub_id, "alerts")

        await manager.broadcast_to_channel("alerts", "platform_status", {"ok": True})

        sock_sub.send_text.assert_awaited_once()
        sock_nosub.send_text.assert_not_awaited()

    async def test_broadcast_all_reaches_every_client(
        self, manager: WebSocketManager
    ) -> None:
        """broadcast_all fans out to every connection, tenants regardless."""
        _, sock_a = await _connect(manager, tenant_id=1)
        _, sock_b = await _connect(manager, tenant_id=2)

        await manager.broadcast_all("heartbeat", {"status": "alive"})

        sock_a.send_text.assert_awaited_once()
        sock_b.send_text.assert_awaited_once()


# =============================================================================
# handle_client_message
# =============================================================================


class TestHandleClientMessage:
    async def test_subscribe_message_subscribes(
        self, manager: WebSocketManager
    ) -> None:
        """A subscribe message registers the requested channel."""
        client_id, _ = await _connect(manager)
        data = json.dumps({"type": "subscribe", "payload": {"channel": "emq"}})

        await manager.handle_client_message(client_id, data)

        assert client_id in manager._channel_subscriptions["emq"]

    async def test_subscribe_without_channel_is_ignored(
        self, manager: WebSocketManager
    ) -> None:
        """A subscribe message missing the channel does nothing."""
        client_id, _ = await _connect(manager)
        data = json.dumps({"type": "subscribe", "payload": {}})

        await manager.handle_client_message(client_id, data)

        assert manager._channel_subscriptions == {}

    async def test_unsubscribe_message_unsubscribes(
        self, manager: WebSocketManager
    ) -> None:
        """An unsubscribe message removes the channel registration."""
        client_id, _ = await _connect(manager)
        await manager.subscribe(client_id, "emq")
        data = json.dumps({"type": "unsubscribe", "payload": {"channel": "emq"}})

        await manager.handle_client_message(client_id, data)

        assert client_id not in manager._channel_subscriptions["emq"]

    async def test_unsubscribe_without_channel_is_ignored(
        self, manager: WebSocketManager
    ) -> None:
        """An unsubscribe message missing the channel does nothing."""
        client_id, _ = await _connect(manager)
        await manager.subscribe(client_id, "emq")
        data = json.dumps({"type": "unsubscribe", "payload": {}})

        await manager.handle_client_message(client_id, data)

        assert client_id in manager._channel_subscriptions["emq"]

    async def test_invalid_json_sends_error_message(
        self, manager: WebSocketManager
    ) -> None:
        """Malformed JSON is answered with an error frame, not an exception."""
        client_id, sock = await _connect(manager)

        await manager.handle_client_message(client_id, "{not-json")

        assert _sent_types(sock) == [MessageType.ERROR.value]
        payload = json.loads(sock.send_text.await_args.args[0])["payload"]
        assert "Invalid JSON" in payload["error"]

    async def test_unknown_type_is_logged_not_fatal(
        self, manager: WebSocketManager
    ) -> None:
        """Unknown message types are tolerated."""
        client_id, sock = await _connect(manager)
        data = json.dumps({"type": "mystery", "payload": {}})

        await manager.handle_client_message(client_id, data)

        sock.send_text.assert_not_awaited()


# =============================================================================
# stats & ids
# =============================================================================


class TestStatsAndIds:
    async def test_get_stats_counts_connections(
        self, manager: WebSocketManager
    ) -> None:
        """Stats reflect connections, tenants, and active channels."""
        id_a, _ = await _connect(manager, tenant_id=1)
        await _connect(manager, tenant_id=1)
        await _connect(manager, tenant_id=2)
        await manager.subscribe(id_a, "emq")

        stats = manager.get_stats()

        assert stats["total_connections"] == 3
        assert stats["tenants_connected"] == 2
        assert stats["channels_active"] == 1
        assert stats["connections_by_tenant"] == {1: 2, 2: 1}

    def test_generate_client_id_is_unique_string(
        self, manager: WebSocketManager
    ) -> None:
        """Client ids are unique non-empty strings."""
        ids = {manager._generate_client_id() for _ in range(50)}
        assert len(ids) == 50
        assert all(isinstance(i, str) and i for i in ids)


# =============================================================================
# publish_* helpers (module-level, use the global ws_manager)
# =============================================================================


@pytest.fixture
def broadcast_mock(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Intercept the global manager's tenant broadcast."""
    mock = AsyncMock()
    monkeypatch.setattr(ws_module.ws_manager, "broadcast_to_tenant", mock)
    return mock


class TestPublishHelpers:
    async def test_publish_action_status_update(
        self, broadcast_mock: AsyncMock
    ) -> None:
        """Action updates map onto ACTION_STATUS_UPDATE with camelCase payload."""
        await ws_module.publish_action_status_update(
            tenant_id=4,
            action_id="act-1",
            status="executed",
            before_value=100,
            after_value=120,
        )

        kwargs = broadcast_mock.await_args.kwargs
        assert kwargs["tenant_id"] == 4
        assert kwargs["message_type"] == MessageType.ACTION_STATUS_UPDATE.value
        assert kwargs["payload"] == {
            "tenantId": 4,
            "actionId": "act-1",
            "status": "executed",
            "beforeValue": 100,
            "afterValue": 120,
        }

    async def test_publish_emq_update(self, broadcast_mock: AsyncMock) -> None:
        """EMQ updates map onto EMQ_UPDATE with score fields."""
        await ws_module.publish_emq_update(
            tenant_id=4, score=71.0, previous_score=68.0, confidence_band="reliable"
        )

        kwargs = broadcast_mock.await_args.kwargs
        assert kwargs["message_type"] == MessageType.EMQ_UPDATE.value
        assert kwargs["payload"] == {
            "tenantId": 4,
            "score": 71.0,
            "previousScore": 68.0,
            "confidenceBand": "reliable",
        }

    @pytest.mark.parametrize(
        "incident_type,expected",
        [
            ("incident_opened", MessageType.INCIDENT_OPENED.value),
            ("degradation", MessageType.INCIDENT_OPENED.value),
            ("incident_closed", MessageType.INCIDENT_CLOSED.value),
            ("resolved", MessageType.INCIDENT_CLOSED.value),
        ],
    )
    async def test_publish_incident_opened_vs_closed(
        self, broadcast_mock: AsyncMock, incident_type: str, expected: str
    ) -> None:
        """Opened/degradation map to INCIDENT_OPENED; everything else closes."""
        await ws_module.publish_incident(
            tenant_id=4,
            incident_type=incident_type,
            incident_id="inc-1",
            title="EMQ drop",
            severity="high",
            platform="meta",
        )

        kwargs = broadcast_mock.await_args.kwargs
        assert kwargs["message_type"] == expected
        assert kwargs["payload"]["incidentId"] == "inc-1"
        assert kwargs["payload"]["severity"] == "high"

    async def test_publish_autopilot_mode_change(
        self, broadcast_mock: AsyncMock
    ) -> None:
        """Mode changes map onto AUTOPILOT_MODE_CHANGE with mode + reason."""
        await ws_module.publish_autopilot_mode_change(
            tenant_id=4, mode="frozen", reason="signal health < 40"
        )

        kwargs = broadcast_mock.await_args.kwargs
        assert kwargs["message_type"] == MessageType.AUTOPILOT_MODE_CHANGE.value
        assert kwargs["payload"] == {
            "tenantId": 4,
            "mode": "frozen",
            "reason": "signal health < 40",
        }
