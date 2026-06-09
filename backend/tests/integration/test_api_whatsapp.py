# =============================================================================
# Stratum AI - WhatsApp Contacts API Integration Tests
# =============================================================================
"""
Integration tests for the WhatsApp contact lifecycle: create, list, update,
opt-out/opt-in, and (soft) delete. These exercise real DB writes through the
tenant-scoped endpoints.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/whatsapp/contacts"


async def _create(client: AsyncClient, phone: str = "+12025550101", name: str = "Ada"):
    resp = await client.post(
        BASE,
        json={
            "phone_number": phone,
            "country_code": "US",
            "display_name": name,
            "opt_in_method": "web_form",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestWhatsAppContactLifecycle:
    @pytest.mark.asyncio
    async def test_create_and_list_contact(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client)
        assert created["phone_number"] == "+12025550101"
        assert created["display_name"] == "Ada"

        resp = await authenticated_client.get(BASE)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert any(c["id"] == created["id"] for c in items)

    @pytest.mark.asyncio
    async def test_duplicate_phone_is_rejected(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, phone="+12025550102")
        resp = await authenticated_client.post(
            BASE,
            json={
                "phone_number": "+12025550102",
                "country_code": "US",
                "opt_in_method": "web_form",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_contact_display_name(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, phone="+12025550103")
        resp = await authenticated_client.patch(
            f"{BASE}/{created['id']}",
            json={"display_name": "Grace Hopper"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "Grace Hopper"

    @pytest.mark.asyncio
    async def test_opt_out_then_opt_in(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, phone="+12025550104")

        resp = await authenticated_client.post(f"{BASE}/{created['id']}/opt-out")
        assert resp.status_code == 200

        resp = await authenticated_client.get(BASE)
        contact = next(
            c for c in resp.json()["data"]["items"] if c["id"] == created["id"]
        )
        assert contact["opt_in_status"] == "opted_out"

        resp = await authenticated_client.post(f"{BASE}/{created['id']}/opt-in")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_contact_removes_it_from_list(
        self, authenticated_client: AsyncClient
    ):
        created = await _create(authenticated_client, phone="+12025550105")

        resp = await authenticated_client.delete(f"{BASE}/{created['id']}")
        assert resp.status_code == 200

        resp = await authenticated_client.get(BASE)
        ids = [c["id"] for c in resp.json()["data"]["items"]]
        assert created["id"] not in ids

    @pytest.mark.asyncio
    async def test_update_missing_contact_returns_404(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.patch(
            f"{BASE}/999999", json={"display_name": "Nobody"}
        )
        assert resp.status_code == 404
