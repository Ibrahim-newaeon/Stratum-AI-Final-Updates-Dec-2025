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


async def _seed_completed_session(tenant_id: int) -> str:
    """Persist a fully-walked (COMPLETED) onboarding session to Redis."""
    from uuid import uuid4

    from app.api.v1.endpoints.onboarding_agent import get_redis_client, save_session
    from app.services.agents import (
        ConversationContext,
        ConversationState,
        UserContext,
    )
    from app.services.agents.root_agent import OnboardingData

    session_id = str(uuid4())
    context = ConversationContext(
        session_id=session_id,
        user_context=UserContext(tenant_id=str(tenant_id), is_new_user=False),
        state=ConversationState.COMPLETED,
        onboarding_data=OnboardingData(
            company_name="Acme Co",
            industry="ecommerce",
            timezone="UTC",
            currency="USD",
            selected_platforms=["meta", "google"],
            healthy_threshold=70,
            degraded_threshold=40,
        ),
    )
    redis = await get_redis_client()
    try:
        await save_session(session_id, context, redis)
    finally:
        await redis.aclose()
    return session_id


class TestComplete:
    async def test_unknown_session_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/complete/does-not-exist")
        assert resp.status_code == 404

    async def test_not_completed_400(self, authenticated_client: AsyncClient):
        # A freshly-started session is in GREETING, not COMPLETED.
        session_id = await _start(authenticated_client)
        resp = await authenticated_client.post(f"{_BASE}/complete/{session_id}")
        assert resp.status_code == 400, resp.text

    async def test_complete_persists_and_clears_session(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        session_id = await _seed_completed_session(test_tenant["id"])

        resp = await authenticated_client.post(f"{_BASE}/complete/{session_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

        # Collected data was persisted to the tenant.
        from sqlalchemy import select

        from app.base_models import Tenant

        row = await db_session.execute(
            select(Tenant).where(Tenant.id == test_tenant["id"])
        )
        tenant = row.scalar_one()
        assert tenant.settings.get("onboarding_completed") is True
        assert tenant.settings.get("selected_platforms") == ["meta", "google"]

        # Session is cleared after completion.
        gone = await authenticated_client.get(f"{_BASE}/status/{session_id}")
        assert gone.status_code == 404
