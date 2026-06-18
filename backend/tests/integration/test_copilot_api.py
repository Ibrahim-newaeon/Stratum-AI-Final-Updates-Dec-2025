# =============================================================================
# Stratum AI - Copilot Endpoint Integration Tests
# =============================================================================
"""Integration tests for the AI Copilot chat endpoint under
``/api/v1/copilot/chat``.

The copilot runs a deterministic keyword classifier first (intent, suggestion
chips, data cards) and only *additionally* swaps in an LLM-generated message
when ``copilot_llm_enabled`` + an Anthropic key are present. With no key (the
test env) the LLM/RAG bridges fail open, so the endpoint returns the
deterministic template response — which is what these tests assert.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CHAT = "/api/v1/copilot/chat"


class TestCopilotChat:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(_CHAT, json={"message": "How is my ROAS?"})
        assert resp.status_code in {401, 403}

    async def test_chat_returns_deterministic_response(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            _CHAT, json={"message": "How is my ROAS this week?"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["message"]
        assert data["intent"]
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["data_cards"], list)
        # No LLM key in the test env -> RAG/citations bridge yields nothing.
        assert data["citations"] == []
        assert data["session_id"]
