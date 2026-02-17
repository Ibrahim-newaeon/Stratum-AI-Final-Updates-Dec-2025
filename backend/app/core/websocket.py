# =============================================================================
# Stratum AI - WebSocket Connection Manager
# =============================================================================
"""
WebSocket connection manager for real-time updates.

Handles:
- Client connections with tenant isolation
- Message broadcasting to specific tenants/channels
- Action status updates
- EMQ score changes
- Incident notifications
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    # EMQ updates
    EMQ_UPDATE = "emq_update"
    EMQ_DRIVER_UPDATE = "emq_driver_update"

    # Incidents
    INCIDENT_OPENED = "incident_opened"
    INCIDENT_CLOSED = "incident_closed"

    # Autopilot
    AUTOPILOT_MODE_CHANGE = "autopilot_mode_change"
    ACTION_RECOMMENDATION = "action_recommendation"
    ACTION_STATUS_UPDATE = "action_status_update"

    # Platform status
    PLATFORM_STATUS = "platform_status"

    # System
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        })

    @classmethod
    def from_json(cls, data: str) -> "WebSocketMessage":
        parsed = json.loads(data)
        return cls(
            type=parsed.get("type", "unknown"),
            payload=parsed.get("payload", {}),
            timestamp=parsed.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        )


@dataclass
class ConnectedClient:
    """Represents a connected WebSocket client."""
    websocket: WebSocket
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    subscribed_channels: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - Tenant-isolated connections
    - Channel-based subscriptions
    - Redis Pub/Sub for multi-instance support
    - Automatic heartbeat
    - Connection cleanup
    """

    def __init__(self):
        self._connections: Dict[str, ConnectedClient] = {}
        self._tenant_connections: Dict[int, Set[str]] = {}
        self._channel_subscriptions: Dict[str, Set[str]] = {}
        self._redis: Optional[redis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Initialize the WebSocket manager."""
        if self._running:
            return

        self._running = True

        # Try to connect to Redis for cross-instance pub/sub
        try:
            self._redis = redis.from_url(settings.redis_url)
            await self._redis.ping()  # Verify connectivity
            self._pubsub_task = asyncio.create_task(self._redis_listener())
            logger.info("websocket_redis_connected")
        except Exception as e:
            logger.warning(
                "websocket_redis_unavailable",
                error=str(e),
                detail="Operating in local-only mode without cross-instance pub/sub",
            )
            self._redis = None  # Operate without Redis

        # Heartbeat runs regardless of Redis availability
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("websocket_manager_started")

    async def stop(self):
        """Shutdown the WebSocket manager."""
        self._running = False

        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for client_id in list(self._connections.keys()):
            await self.disconnect(client_id)

        if self._redis:
            await self._redis.close()

        logger.info("websocket_manager_stopped")

    def _generate_client_id(self) -> str:
        """Generate a unique client ID."""
        import uuid
        return str(uuid.uuid4())

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Register a new WebSocket connection.

        Returns the client ID for future reference.
        """
        await websocket.accept()

        client_id = self._generate_client_id()
        client = ConnectedClient(
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        self._connections[client_id] = client

        # Track by tenant
        if tenant_id:
            if tenant_id not in self._tenant_connections:
                self._tenant_connections[tenant_id] = set()
            self._tenant_connections[tenant_id].add(client_id)

        logger.info(
            "websocket_client_connected",
            client_id=client_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return client_id

    async def disconnect(self, client_id: str):
        """Disconnect and cleanup a WebSocket client."""
        client = self._connections.pop(client_id, None)
        if not client:
            return

        # Remove from tenant tracking
        if client.tenant_id and client.tenant_id in self._tenant_connections:
            self._tenant_connections[client.tenant_id].discard(client_id)
            if not self._tenant_connections[client.tenant_id]:
                del self._tenant_connections[client.tenant_id]

        # Remove from channel subscriptions
        for channel in client.subscribed_channels:
            if channel in self._channel_subscriptions:
                self._channel_subscriptions[channel].discard(client_id)

        # Close the connection
        try:
            if client.websocket.client_state == WebSocketState.CONNECTED:
                await client.websocket.close()
        except Exception:
            pass

        logger.info(
            "websocket_client_disconnected",
            client_id=client_id,
            tenant_id=client.tenant_id,
        )

    async def subscribe(self, client_id: str, channel: str):
        """Subscribe a client to a channel."""
        client = self._connections.get(client_id)
        if not client:
            return

        client.subscribed_channels.add(channel)

        if channel not in self._channel_subscriptions:
            self._channel_subscriptions[channel] = set()
        self._channel_subscriptions[channel].add(client_id)

        logger.debug(
            "websocket_subscribed",
            client_id=client_id,
            channel=channel,
        )

    async def unsubscribe(self, client_id: str, channel: str):
        """Unsubscribe a client from a channel."""
        client = self._connections.get(client_id)
        if not client:
            return

        client.subscribed_channels.discard(channel)

        if channel in self._channel_subscriptions:
            self._channel_subscriptions[channel].discard(client_id)

    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send a message to a specific client."""
        client = self._connections.get(client_id)
        if not client:
            return

        try:
            await client.websocket.send_text(message.to_json())
        except Exception as e:
            logger.warning(
                "websocket_send_failed",
                client_id=client_id,
                error=str(e),
            )
            await self.disconnect(client_id)

    async def broadcast_to_tenant(
        self,
        tenant_id: int,
        message_type: str,
        payload: Any,
    ):
        """Broadcast a message to all clients of a specific tenant."""
        message = WebSocketMessage(type=message_type, payload=payload)

        client_ids = self._tenant_connections.get(tenant_id, set()).copy()
        for client_id in client_ids:
            await self.send_to_client(client_id, message)

        # Also publish to Redis for multi-instance support
        await self._publish_to_redis(f"tenant:{tenant_id}", message)

    async def broadcast_to_channel(
        self,
        channel: str,
        message_type: str,
        payload: Any,
    ):
        """Broadcast a message to all clients subscribed to a channel."""
        message = WebSocketMessage(type=message_type, payload=payload)

        client_ids = self._channel_subscriptions.get(channel, set()).copy()
        for client_id in client_ids:
            await self.send_to_client(client_id, message)

        # Also publish to Redis
        await self._publish_to_redis(f"channel:{channel}", message)

    async def broadcast_all(self, message_type: str, payload: Any):
        """Broadcast a message to all connected clients."""
        message = WebSocketMessage(type=message_type, payload=payload)

        for client_id in list(self._connections.keys()):
            await self.send_to_client(client_id, message)

    async def _publish_to_redis(self, channel: str, message: WebSocketMessage):
        """Publish a message to Redis for multi-instance support."""
        if not self._redis:
            return

        try:
            await self._redis.publish(
                f"ws:{channel}",
                message.to_json(),
            )
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    async def _redis_listener(self):
        """Listen for messages from Redis pubsub."""
        if not self._redis:
            return

        pubsub = self._redis.pubsub()
        await pubsub.psubscribe("ws:*")

        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message and message["type"] == "pmessage":
                    await self._handle_redis_message(message)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.punsubscribe("ws:*")
            await pubsub.close()

    async def _handle_redis_message(self, message: Dict):
        """Handle a message received from Redis."""
        try:
            channel = message["channel"].decode("utf-8")
            data = message["data"].decode("utf-8")
            ws_message = WebSocketMessage.from_json(data)

            # Determine target clients
            if channel.startswith("ws:tenant:"):
                tenant_id = int(channel.split(":")[-1])
                client_ids = self._tenant_connections.get(tenant_id, set()).copy()
            elif channel.startswith("ws:channel:"):
                channel_name = channel.replace("ws:channel:", "")
                client_ids = self._channel_subscriptions.get(channel_name, set()).copy()
            else:
                client_ids = set(self._connections.keys())

            for client_id in client_ids:
                await self.send_to_client(client_id, ws_message)

        except Exception as e:
            logger.warning("redis_message_handling_failed", error=str(e))

    async def _heartbeat_loop(self):
        """Send heartbeat messages to all clients periodically."""
        try:
            while self._running:
                await asyncio.sleep(30)

                message = WebSocketMessage(
                    type=MessageType.HEARTBEAT.value,
                    payload={"status": "alive"},
                )

                for client_id in list(self._connections.keys()):
                    await self.send_to_client(client_id, message)
        except asyncio.CancelledError:
            pass

    async def handle_client_message(self, client_id: str, data: str):
        """Handle an incoming message from a client."""
        try:
            message = WebSocketMessage.from_json(data)

            if message.type == MessageType.SUBSCRIBE.value:
                channel = message.payload.get("channel")
                if channel:
                    await self.subscribe(client_id, channel)

            elif message.type == MessageType.UNSUBSCRIBE.value:
                channel = message.payload.get("channel")
                if channel:
                    await self.unsubscribe(client_id, channel)

            else:
                logger.debug(
                    "websocket_message_received",
                    client_id=client_id,
                    message_type=message.type,
                )

        except json.JSONDecodeError:
            error_msg = WebSocketMessage(
                type=MessageType.ERROR.value,
                payload={"error": "Invalid JSON message"},
            )
            await self.send_to_client(client_id, error_msg)

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self._connections),
            "tenants_connected": len(self._tenant_connections),
            "channels_active": len(self._channel_subscriptions),
            "connections_by_tenant": {
                tid: len(clients)
                for tid, clients in self._tenant_connections.items()
            },
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()


# =============================================================================
# Helper Functions for Publishing Events
# =============================================================================

async def publish_action_status_update(
    tenant_id: int,
    action_id: str,
    status: str,
    before_value: Optional[Any] = None,
    after_value: Optional[Any] = None,
):
    """Publish an action status update to relevant clients."""
    await ws_manager.broadcast_to_tenant(
        tenant_id=tenant_id,
        message_type=MessageType.ACTION_STATUS_UPDATE.value,
        payload={
            "tenantId": tenant_id,
            "actionId": action_id,
            "status": status,
            "beforeValue": before_value,
            "afterValue": after_value,
        },
    )


async def publish_emq_update(
    tenant_id: int,
    score: float,
    previous_score: Optional[float] = None,
    confidence_band: Optional[str] = None,
):
    """Publish an EMQ score update to relevant clients."""
    await ws_manager.broadcast_to_tenant(
        tenant_id=tenant_id,
        message_type=MessageType.EMQ_UPDATE.value,
        payload={
            "tenantId": tenant_id,
            "score": score,
            "previousScore": previous_score,
            "confidenceBand": confidence_band,
        },
    )


async def publish_incident(
    tenant_id: int,
    incident_type: str,
    incident_id: str,
    title: str,
    severity: str,
    platform: Optional[str] = None,
):
    """Publish an incident notification to relevant clients."""
    message_type = (
        MessageType.INCIDENT_OPENED.value
        if incident_type in ("incident_opened", "degradation")
        else MessageType.INCIDENT_CLOSED.value
    )

    await ws_manager.broadcast_to_tenant(
        tenant_id=tenant_id,
        message_type=message_type,
        payload={
            "tenantId": tenant_id,
            "incidentId": incident_id,
            "title": title,
            "severity": severity,
            "platform": platform,
        },
    )


async def publish_autopilot_mode_change(
    tenant_id: int,
    mode: str,
    reason: str,
):
    """Publish an autopilot mode change notification."""
    await ws_manager.broadcast_to_tenant(
        tenant_id=tenant_id,
        message_type=MessageType.AUTOPILOT_MODE_CHANGE.value,
        payload={
            "tenantId": tenant_id,
            "mode": mode,
            "reason": reason,
        },
    )
