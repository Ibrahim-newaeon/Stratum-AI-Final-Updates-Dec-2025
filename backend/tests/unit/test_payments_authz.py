# =============================================================================
# Stratum AI - Billing Endpoint Authorization Tests
# =============================================================================
"""Role gating on /api/v1/payments.

Every endpoint in payments.py used to authorize on `request.state.tenant_id`
alone — "do you hold any valid JWT for this tenant". A viewer could cancel the
subscription, raise the plan, read every invoice, and mint a Stripe Customer
Portal session, which is a complete billing-management surface.

The Permission enum has carried BILLING_READ / BILLING_WRITE / BILLING_MANAGE
since the roles were defined, and ROLE_PERMISSIONS already says viewer and
analyst get none of them. Only the endpoints never asked.

Gates run before the handler, so these tests are meaningful with Stripe
unconfigured: an authorized caller gets past the gate and fails later (503),
which is simply "not 401 and not 403".
"""

import pytest

from tests.unit.conftest import make_auth_headers

pytestmark = pytest.mark.asyncio

_BASE = "/api/v1/payments"

# (method, path) for every gated endpoint, split by the permission it needs.
_READ_ENDPOINTS = [
    ("get", "/overview"),
    ("get", "/subscription"),
    ("get", "/invoices"),
    ("get", "/payment-methods"),
]

_WRITE_ENDPOINTS = [
    ("post", "/checkout"),
    ("post", "/portal"),
    ("post", "/subscription/upgrade"),
    ("post", "/subscription/cancel"),
    ("post", "/subscription/reactivate"),
]

_ALL_ENDPOINTS = _READ_ENDPOINTS + _WRITE_ENDPOINTS


async def _call(client, method: str, path: str, headers: dict | None = None):
    """Issue the request with a body that satisfies request-model validation.

    The bodies are deliberately well-formed: a 422 would mask the 403 this
    suite is asserting, and FastAPI validates the body before dependencies on
    some paths.
    """
    bodies = {
        "/checkout": {
            "tier": "starter",
            "success_url": "https://app.stratumai.app/ok",
            "cancel_url": "https://app.stratumai.app/no",
        },
        "/portal": {"return_url": "https://app.stratumai.app/billing"},
        "/subscription/upgrade": {"tier": "professional"},
    }
    kwargs = {"headers": headers} if headers else {}
    if method == "post":
        kwargs["json"] = bodies.get(path, {})
    return await getattr(client, method)(f"{_BASE}{path}", **kwargs)


class TestUnauthenticated:
    @pytest.mark.parametrize("method,path", _ALL_ENDPOINTS)
    async def test_requires_authentication(self, api_client, method, path):
        resp = await _call(api_client, method, path)
        assert resp.status_code == 401, f"{method} {path}: {resp.text}"


class TestViewerIsRefused:
    """viewer holds no billing permission at all."""

    @pytest.mark.parametrize("method,path", _ALL_ENDPOINTS)
    async def test_viewer_gets_403(self, api_client, viewer_headers, method, path):
        resp = await _call(api_client, method, path, viewer_headers)
        assert resp.status_code == 403, f"{method} {path}: {resp.text}"


class TestManagerIsReadOnly:
    """manager holds BILLING_READ but not BILLING_WRITE."""

    @pytest.mark.parametrize("method,path", _READ_ENDPOINTS)
    async def test_manager_may_read(self, api_client, method, path):
        headers = make_auth_headers(role="manager")
        resp = await _call(api_client, method, path, headers)
        assert resp.status_code not in (401, 403), f"{method} {path}: {resp.text}"

    @pytest.mark.parametrize("method,path", _WRITE_ENDPOINTS)
    async def test_manager_may_not_write(self, api_client, method, path):
        headers = make_auth_headers(role="manager")
        resp = await _call(api_client, method, path, headers)
        assert resp.status_code == 403, f"{method} {path}: {resp.text}"


class TestAdminIsAllowed:
    """admin holds BILLING_READ and BILLING_WRITE."""

    @pytest.mark.parametrize("method,path", _ALL_ENDPOINTS)
    async def test_admin_passes_the_gate(self, api_client, admin_headers, method, path):
        resp = await _call(api_client, method, path, admin_headers)
        assert resp.status_code not in (401, 403), f"{method} {path}: {resp.text}"


class TestConfigIsNotBillingGated:
    """/config carries no billing permission, deliberately.

    It returns the Stripe publishable key and the public tier pricing table —
    the things a browser needs to render a plan picker, and nothing tied to a
    particular customer. So every authenticated role may read it, including
    viewer. Asserted here so a future sweep does not gate it by reflex.

    It is not reachable anonymously: TenantMiddleware does not list it in
    PUBLIC_ENDPOINTS, so an unauthenticated call is refused before the route
    is reached. That is middleware behaviour rather than anything payments.py
    asks for, and it is pinned here because the endpoint's own docstring calls
    the response "public" and reads like it should be.
    """

    async def test_config_requires_authentication(self, api_client):
        resp = await api_client.get(f"{_BASE}/config")
        assert resp.status_code in (401, 403), resp.text

    async def test_viewer_may_read_config(self, api_client, viewer_headers):
        resp = await api_client.get(f"{_BASE}/config", headers=viewer_headers)
        assert resp.status_code == 200, resp.text
        assert "publishable_key" in resp.json()
