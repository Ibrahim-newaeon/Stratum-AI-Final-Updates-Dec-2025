# =============================================================================
# Stratum AI - Launch Readiness API Integration Tests
# =============================================================================
"""
Integration tests for the Launch Readiness go-live wizard.

Covers:
- Auth: superadmin-only access (401 without auth, 403 for non-superadmin)
- Initial state: 12 phases, phase 1 active, phases 2-12 locked
- Phase-gate enforcement: checking outside the current phase returns 409
- Sequential unlock: completing phase N exposes phase N+1
- Re-open: unchecking a completed item relocks downstream phases
- Audit trail: events appended for check/uncheck and phase transitions
- Error paths: 404 for unknown item_key
"""

import pytest
from httpx import AsyncClient

from app.core.launch_readiness_phases import LAUNCH_READINESS_PHASES


pytestmark = pytest.mark.integration

BASE = "/api/v1/superadmin/launch-readiness"


# =============================================================================
# Helpers
# =============================================================================
def _phase_items(phase_number: int):
    """Return the list of item keys for a given phase number."""
    phase = next(p for p in LAUNCH_READINESS_PHASES if p["number"] == phase_number)
    return [i["key"] for i in phase["items"]]


async def _complete_phase(
    client: AsyncClient, headers: dict, phase_number: int
) -> None:
    """Check every item in a phase. Caller must ensure phase is currently active."""
    for key in _phase_items(phase_number):
        response = await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True},
            headers=headers,
        )
        assert response.status_code == 200, (
            f"failed to check {key} in phase {phase_number}: "
            f"{response.status_code} {response.text}"
        )


# =============================================================================
# Auth
# =============================================================================
class TestLaunchReadinessAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_request_is_rejected(self, client: AsyncClient):
        response = await client.get(BASE)
        # TenantMiddleware rejects before reaching the endpoint
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_non_superadmin_cannot_access(
        self, authenticated_client: AsyncClient
    ):
        # authenticated_client uses the test_user fixture (role=admin)
        response = await authenticated_client.get(BASE)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_superadmin_can_access(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        response = await client.get(BASE, headers=superadmin_headers)
        assert response.status_code == 200


# =============================================================================
# Initial state
# =============================================================================
class TestInitialState:
    @pytest.mark.asyncio
    async def test_returns_twelve_phases(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        response = await client.get(BASE, headers=superadmin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

        state = body["data"]
        assert len(state["phases"]) == 12
        assert state["current_phase_number"] == 1
        assert state["overall_completed"] == 0
        assert state["is_launched"] is False

    @pytest.mark.asyncio
    async def test_phase_one_is_active_and_others_locked(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        response = await client.get(BASE, headers=superadmin_headers)
        state = response.json()["data"]

        for phase in state["phases"]:
            if phase["number"] == 1:
                assert phase["is_active"] is True
                assert phase["is_locked"] is False
                assert phase["is_complete"] is False
            else:
                assert phase["is_active"] is False
                assert phase["is_locked"] is True

    @pytest.mark.asyncio
    async def test_all_items_start_unchecked(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        response = await client.get(BASE, headers=superadmin_headers)
        state = response.json()["data"]

        for phase in state["phases"]:
            for item in phase["items"]:
                assert item["is_checked"] is False
                assert item["checked_by_user_id"] is None
                assert item["checked_at"] is None


# =============================================================================
# Phase-gate enforcement
# =============================================================================
class TestPhaseGating:
    @pytest.mark.asyncio
    async def test_check_item_in_current_phase_succeeds(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        key = _phase_items(1)[0]
        response = await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True},
            headers=superadmin_headers,
        )

        assert response.status_code == 200
        state = response.json()["data"]
        toggled = next(i for i in state["phases"][0]["items"] if i["key"] == key)
        assert toggled["is_checked"] is True
        assert toggled["checked_at"] is not None

    @pytest.mark.asyncio
    async def test_check_item_outside_current_phase_returns_409(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        # Phase 2 items are locked until phase 1 is complete
        key = _phase_items(2)[0]
        response = await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True},
            headers=superadmin_headers,
        )

        assert response.status_code == 409
        body = response.json()
        assert "phase" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_unknown_item_key_returns_404(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        response = await client.patch(
            f"{BASE}/items/totally_not_a_real_key",
            json={"checked": True},
            headers=superadmin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_completing_phase_one_unlocks_phase_two(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        await _complete_phase(client, superadmin_headers, 1)

        response = await client.get(BASE, headers=superadmin_headers)
        state = response.json()["data"]

        phase_one = state["phases"][0]
        phase_two = state["phases"][1]

        assert phase_one["is_complete"] is True
        assert phase_one["is_active"] is False
        assert phase_two["is_active"] is True
        assert phase_two["is_locked"] is False
        assert state["current_phase_number"] == 2

    @pytest.mark.asyncio
    async def test_cannot_skip_to_phase_three_without_phase_two(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        await _complete_phase(client, superadmin_headers, 1)

        key = _phase_items(3)[0]
        response = await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True},
            headers=superadmin_headers,
        )
        assert response.status_code == 409


# =============================================================================
# Uncheck / re-open
# =============================================================================
class TestReopen:
    @pytest.mark.asyncio
    async def test_uncheck_in_active_phase_is_allowed(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        key = _phase_items(1)[0]
        await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True},
            headers=superadmin_headers,
        )

        response = await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": False},
            headers=superadmin_headers,
        )

        assert response.status_code == 200
        state = response.json()["data"]
        toggled = next(i for i in state["phases"][0]["items"] if i["key"] == key)
        assert toggled["is_checked"] is False

    @pytest.mark.asyncio
    async def test_uncheck_in_completed_phase_relocks_downstream(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        # Complete phase 1, then uncheck one of its items.
        await _complete_phase(client, superadmin_headers, 1)

        response = await client.get(BASE, headers=superadmin_headers)
        assert response.json()["data"]["current_phase_number"] == 2

        key = _phase_items(1)[0]
        await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": False},
            headers=superadmin_headers,
        )

        response = await client.get(BASE, headers=superadmin_headers)
        state = response.json()["data"]
        assert state["current_phase_number"] == 1
        assert state["phases"][0]["is_active"] is True
        assert state["phases"][1]["is_locked"] is True


# =============================================================================
# Audit trail
# =============================================================================
class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_check_appends_event(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        key = _phase_items(1)[0]
        await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": True, "note": "first check"},
            headers=superadmin_headers,
        )

        response = await client.get(
            f"{BASE}/events", headers=superadmin_headers
        )
        assert response.status_code == 200

        events = response.json()["data"]
        # Most-recent first. Top event should be the 'checked' action.
        assert len(events) >= 1
        top = events[0]
        assert top["action"] == "checked"
        assert top["item_key"] == key
        assert top["note"] == "first check"

    @pytest.mark.asyncio
    async def test_phase_completion_emits_phase_completed_event(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        await _complete_phase(client, superadmin_headers, 1)

        response = await client.get(
            f"{BASE}/events",
            headers=superadmin_headers,
            params={"phase_number": 1},
        )
        events = response.json()["data"]

        actions = [e["action"] for e in events]
        assert "phase_completed" in actions

    @pytest.mark.asyncio
    async def test_uncheck_after_completion_emits_phase_reopened(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        await _complete_phase(client, superadmin_headers, 1)

        key = _phase_items(1)[0]
        await client.patch(
            f"{BASE}/items/{key}",
            json={"checked": False},
            headers=superadmin_headers,
        )

        response = await client.get(
            f"{BASE}/events",
            headers=superadmin_headers,
            params={"phase_number": 1},
        )
        events = response.json()["data"]
        actions = [e["action"] for e in events]
        assert "phase_reopened" in actions

    @pytest.mark.asyncio
    async def test_events_ordered_newest_first(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        items = _phase_items(1)[:3]
        for key in items:
            await client.patch(
                f"{BASE}/items/{key}",
                json={"checked": True},
                headers=superadmin_headers,
            )

        response = await client.get(
            f"{BASE}/events", headers=superadmin_headers, params={"limit": 50}
        )
        events = response.json()["data"]
        timestamps = [e["created_at"] for e in events]
        assert timestamps == sorted(timestamps, reverse=True)
