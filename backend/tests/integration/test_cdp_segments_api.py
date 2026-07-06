# =============================================================================
# Stratum AI - CDP Segments API Integration Tests
# =============================================================================
"""Integration tests for the CDP segments API.

Exercises the real ASGI app against Postgres + Redis: segment creation,
listing, detail (200/404), update, membership compute, preview, and
delete (204/404), plus auth enforcement and type validation.

Complements ``test_cdp.py`` (events / profiles / sources) by covering
the segment lifecycle, which it does not touch.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


_RULES = {
    "logic": "and",
    "conditions": [
        {"field": "profile.lifecycle_stage", "operator": "equals", "value": "customer"}
    ],
}


def _segment(name="High-value customers", segment_type="dynamic", **extra):
    body = {"name": name, "segment_type": segment_type, "rules": _RULES}
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cdp/segments", json=_segment(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()


# =============================================================================
# Create
# =============================================================================
class TestCreateSegment:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cdp/segments", json=_segment())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="VIPs")
        assert data["name"] == "VIPs"
        assert data["segment_type"] == "dynamic"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_invalid_type_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments", json=_segment(segment_type="not_a_type")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_name_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments", json={"segment_type": "dynamic", "rules": _RULES}
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Seg A")
        await _create(authenticated_client, name="Seg B")
        resp = await authenticated_client.get("/api/v1/cdp/segments")
        assert resp.status_code == 200
        body = resp.json()
        names = {s["name"] for s in body["segments"]}
        assert {"Seg A", "Seg B"} <= names
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail Seg")
        resp = await authenticated_client.get(f"/api/v1/cdp/segments/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Seg"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/cdp/segments/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


# =============================================================================
# Update + compute + delete
# =============================================================================
class TestMutationsAndCompute:
    @pytest.mark.asyncio
    async def test_update_name(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/segments/{created['id']}", json={"name": "After"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    @pytest.mark.asyncio
    async def test_compute_membership(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Computable")
        resp = await authenticated_client.post(
            f"/api/v1/cdp/segments/{created['id']}/compute"
        )
        # Recompute succeeds even with zero matching profiles.
        assert resp.status_code == 200
        assert "profile_count" in resp.json()

    @pytest.mark.asyncio
    async def test_preview(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments/preview", json={"rules": _RULES, "limit": 50}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed Seg")
        sid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/cdp/segments/{sid}")
        assert deleted.status_code == 204
        gone = await authenticated_client.get(f"/api/v1/cdp/segments/{sid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            "/api/v1/cdp/segments/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


# =============================================================================
# List filters + extended update (issue #342 batch 2)
# =============================================================================
async def _make_profile(client: AsyncClient) -> str:
    """Create a CDP profile via event ingestion and return its id."""
    resp = await client.post(
        "/api/v1/cdp/events",
        json={
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {
                            "type": "anonymous_id",
                            "value": f"anon_seg_{uuid4().hex[:10]}",
                        }
                    ],
                }
            ]
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["results"][0]["profile_id"]


class TestListFiltersAndUpdate:
    @pytest.mark.asyncio
    async def test_list_with_filters(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Filtered dynamic")
        resp = await authenticated_client.get(
            "/api/v1/cdp/segments",
            params={"segment_type": "dynamic", "limit": 10, "offset": 0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(s["segment_type"] == "dynamic" for s in body["segments"])

    @pytest.mark.asyncio
    async def test_list_with_nonmatching_type(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Dynamic only")
        resp = await authenticated_client.get(
            "/api/v1/cdp/segments", params={"segment_type": "static"}
        )
        assert resp.status_code == 200
        assert all(s["segment_type"] == "static" for s in resp.json()["segments"])

    @pytest.mark.asyncio
    async def test_update_all_optional_fields(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Full update")
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/segments/{created['id']}",
            json={
                "description": "Updated description",
                "rules": {
                    "logic": "or",
                    "conditions": [
                        {
                            "field": "profile.total_events",
                            "operator": "greater_than",
                            "value": 5,
                        }
                    ],
                },
                "tags": ["vip", "updated"],
                "auto_refresh": False,
                "refresh_interval_hours": 48,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Updated description"
        assert body["tags"] == ["vip", "updated"]
        assert body["auto_refresh"] is False
        assert body["refresh_interval_hours"] == 48

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/segments/{_MISSING}", json={"name": "Nope"}
        )
        assert resp.status_code == 404


# =============================================================================
# Membership endpoints (static segments + profile segments)
# =============================================================================
class TestSegmentMembership:
    @pytest.mark.asyncio
    async def test_segment_profiles_empty(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Empty membership")
        resp = await authenticated_client.get(
            f"/api/v1/cdp/segments/{created['id']}/profiles"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["profiles"] == []

    @pytest.mark.asyncio
    async def test_add_and_remove_profile_static_segment(
        self, authenticated_client: AsyncClient
    ):
        segment = await _create(
            authenticated_client, name="Static seg", segment_type="static"
        )
        profile_id = await _make_profile(authenticated_client)
        sid = segment["id"]

        added = await authenticated_client.post(
            f"/api/v1/cdp/segments/{sid}/profiles/{profile_id}"
        )
        assert added.status_code == 201
        assert added.json()["success"] is True

        # Membership is visible from both directions
        members = await authenticated_client.get(f"/api/v1/cdp/segments/{sid}/profiles")
        assert members.status_code == 200
        assert members.json()["total"] >= 1

        profile_segments = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/segments"
        )
        assert profile_segments.status_code == 200
        segment_ids = {s["id"] for s in profile_segments.json()["segments"]}
        assert sid in segment_ids

        removed = await authenticated_client.delete(
            f"/api/v1/cdp/segments/{sid}/profiles/{profile_id}"
        )
        assert removed.status_code == 204

        # Removing again is a 404
        again = await authenticated_client.delete(
            f"/api/v1/cdp/segments/{sid}/profiles/{profile_id}"
        )
        assert again.status_code == 404

    @pytest.mark.asyncio
    async def test_add_profile_to_dynamic_segment_rejected(
        self, authenticated_client: AsyncClient
    ):
        segment = await _create(authenticated_client, name="Dynamic no-add")
        profile_id = await _make_profile(authenticated_client)

        resp = await authenticated_client.post(
            f"/api/v1/cdp/segments/{segment['id']}/profiles/{profile_id}"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_add_profile_to_missing_segment_rejected(
        self, authenticated_client: AsyncClient
    ):
        profile_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/cdp/segments/{_MISSING}/profiles/{profile_id}"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_profile_segments_empty(self, authenticated_client: AsyncClient):
        profile_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/segments"
        )
        assert resp.status_code == 200
        assert resp.json()["segments"] == []
