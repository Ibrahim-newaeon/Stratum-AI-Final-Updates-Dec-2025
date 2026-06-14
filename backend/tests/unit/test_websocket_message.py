# =============================================================================
# Stratum AI - WebSocket Message Unit Tests
# =============================================================================
"""Unit tests for the pure ``WebSocketMessage`` (de)serialization in
``app.core.websocket``. The async WebSocketManager (Redis-backed) is out
of scope here."""

import json

import pytest

from app.core.websocket import WebSocketMessage

pytestmark = pytest.mark.unit


class TestWebSocketMessage:
    def test_to_json_includes_fields(self):
        msg = WebSocketMessage(type="emq_update", payload={"score": 87})
        data = json.loads(msg.to_json())
        assert data["type"] == "emq_update"
        assert data["payload"] == {"score": 87}
        assert "timestamp" in data

    def test_round_trip_preserves_type_and_payload(self):
        original = WebSocketMessage(type="alert", payload={"id": 1, "level": "high"})
        restored = WebSocketMessage.from_json(original.to_json())
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.timestamp == original.timestamp

    def test_from_json_defaults_for_missing_fields(self):
        restored = WebSocketMessage.from_json(json.dumps({}))
        assert restored.type == "unknown"
        assert restored.payload == {}
        assert restored.timestamp  # defaulted, non-empty
