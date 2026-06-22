# =============================================================================
# Stratum AI - Onboarding Agent Endpoint Integration Tests
# =============================================================================
"""Integration tests for the conversational onboarding agent under
``/api/v1/onboarding-agent/...``: start, message, status, quick-replies, and
session deletion. The agent (``RootAgent``) is a deterministic rule-based state
machine (no LLM), and sessions are persisted in Redis — both available in the
harness.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/onboarding-agent"


async def _start(client: AsyncClient) -> str:
    resp = await client.post(_BASE + "/start", json={"language": "en"})
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


class TestStart:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(_BASE + "/start", json={"language": "en"})
        assert resp.status_code in {401, 403}

    async def test_start_returns_greeting(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            _BASE + "/start", json={"language": "en", "name": "Ada"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["session_id"]
        assert data["message"]
        assert isinstance(data["quick_replies"], list)
        assert 0 <= data["progress_percent"] <= 100


class TestStatus:
    async def test_status_roundtrip(self, authenticated_client: AsyncClient):
        session_id = await _start(authenticated_client)
        resp = await authenticated_client.get(f"{_BASE}/status/{session_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["session_id"] == session_id
        assert "state" in data

    async def test_unknown_session_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/status/does-not-exist")
        assert resp.status_code == 404


class TestMessage:
    async def test_message_advances_conversation(
        self, authenticated_client: AsyncClient
    ):
        session_id = await _start(authenticated_client)
        resp = await authenticated_client.post(
            _BASE + "/message",
            json={"session_id": session_id, "message": "Get Started"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["message"]
        assert "state" in data
        assert isinstance(data["quick_replies"], list)


class TestQuickReplies:
    async def test_quick_replies_for_state(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/quick-replies/greeting")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["state"] == "greeting"
        assert "Get Started" in body["quick_replies"]


class TestSessionDelete:
    async def test_delete_then_status_404(self, authenticated_client: AsyncClient):
        session_id = await _start(authenticated_client)
        deleted = await authenticated_client.delete(f"{_BASE}/session/{session_id}")
        assert deleted.status_code == 200, deleted.text
        gone = await authenticated_client.get(f"{_BASE}/status/{session_id}")
        assert gone.status_code == 404
