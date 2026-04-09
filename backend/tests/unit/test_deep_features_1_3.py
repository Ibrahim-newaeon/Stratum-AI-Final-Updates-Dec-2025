# =============================================================================
# Stratum AI - Deep Endpoint Tests for Features 1-3
# =============================================================================
"""
Deep endpoint tests exercising the FULL request/response cycle via
httpx.AsyncClient.  Requests flow through TenantMiddleware (JWT decode,
tenant extraction) while services/DB are mocked at the handler level.

Feature 1: Trust Engine  (trust_layer.py, emq_v2.py)
Feature 2: CDP           (cdp.py)
Feature 3: Autopilot Enforcement  (autopilot_enforcement.py, autopilot.py)
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


# ============================================================================
# FEATURE 1 — TRUST ENGINE
# ============================================================================

# ---------------------------------------------------------------------------
# Trust Layer: Signal Health  GET /api/v1/trust/tenant/{tenant_id}/signal-health
# ---------------------------------------------------------------------------
class TestTrustLayerSignalHealth:
    URL = "/api/v1/trust/tenant/1/signal-health"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "app.api.v1.endpoints.trust_layer.SignalHealthService"
        ) as MockSvc:
            MockSvc.return_value.get_signal_health = AsyncMock(
                return_value={
                    "status": "ok",
                    "automation_blocked": False,
                    "cards": [],
                    "platform_rows": [],
                    "banners": [],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["status"] == "ok"

    async def test_feature_disabled_returns_403(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 403

    async def test_service_error_propagates(self, api_client, admin_headers, mock_db):
        """When a service raises, the exception propagates (no global handler)."""
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "app.api.v1.endpoints.trust_layer.SignalHealthService"
        ) as MockSvc:
            MockSvc.return_value.get_signal_health = AsyncMock(
                side_effect=Exception("db timeout")
            )
            with pytest.raises(Exception, match="db timeout"):
                await api_client.get(self.URL, headers=admin_headers)


# ---------------------------------------------------------------------------
# Trust Layer: Signal Health History
# GET /api/v1/trust/tenant/{tenant_id}/signal-health/history
# ---------------------------------------------------------------------------
class TestTrustLayerSignalHealthHistory:
    URL = "/api/v1/trust/tenant/1/signal-health/history"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "history" in body["data"]

    async def test_feature_disabled_returns_403(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Trust Layer: Signal Health By Account
# GET /api/v1/trust/tenant/{tenant_id}/signal-health/by-account
# ---------------------------------------------------------------------------
class TestTrustLayerSignalHealthByAccount:
    URL = "/api/v1/trust/tenant/1/signal-health/by-account"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path_empty(self, api_client, admin_headers, mock_db):
        """With no DB records the endpoint returns an empty accounts list."""
        # mock_db already returns empty results by default
        # We need can_access_feature to return True
        # Also need the second db.execute (for TenantAdAccount) to return empty
        mock_account_result = MagicMock()
        mock_account_result.all.return_value = []
        mock_signal_result = MagicMock()
        mock_signal_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_signal_result, mock_account_result]
        )
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["total_accounts"] == 0
            assert body["data"]["overall_status"] == "ok"


# ---------------------------------------------------------------------------
# Trust Layer: Attribution Variance
# GET /api/v1/trust/tenant/{tenant_id}/attribution-variance
# ---------------------------------------------------------------------------
class TestTrustLayerAttributionVariance:
    URL = "/api/v1/trust/tenant/1/attribution-variance"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "app.api.v1.endpoints.trust_layer.AttributionVarianceService"
        ) as MockSvc:
            MockSvc.return_value.get_attribution_variance = AsyncMock(
                return_value={
                    "status": "healthy",
                    "overall_revenue_variance_pct": 3.2,
                    "cards": [],
                    "platform_rows": [],
                    "banners": [],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["status"] == "healthy"

    async def test_feature_disabled_returns_403(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Trust Layer: Trust Status
# GET /api/v1/trust/tenant/{tenant_id}/trust-status
# ---------------------------------------------------------------------------
class TestTrustLayerTrustStatus:
    URL = "/api/v1/trust/tenant/1/trust-status"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path_both_features_enabled(
        self, api_client, admin_headers, mock_db
    ):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "app.api.v1.endpoints.trust_layer.SignalHealthService"
        ) as MockSH, patch(
            "app.api.v1.endpoints.trust_layer.AttributionVarianceService"
        ) as MockAV:
            MockSH.return_value.get_signal_health = AsyncMock(
                return_value={
                    "status": "ok",
                    "automation_blocked": False,
                    "cards": [],
                    "platform_rows": [],
                    "banners": [],
                }
            )
            MockAV.return_value.get_attribution_variance = AsyncMock(
                return_value={
                    "status": "healthy",
                    "overall_revenue_variance_pct": 2.1,
                    "cards": [],
                    "platform_rows": [],
                    "banners": [],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["overall_status"] == "ok"
            assert body["data"]["automation_allowed"] is True

    async def test_no_features_enabled(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.trust_layer.can_access_feature",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["signal_health"] is None
            assert body["data"]["attribution_variance"] is None


# ---------------------------------------------------------------------------
# EMQ v2: Score  GET /api/v1/tenants/{tenant_id}/emq/score
# ---------------------------------------------------------------------------
class TestEmqScore:
    URL = "/api/v1/tenants/1/emq/score"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_emq_score = AsyncMock(
                return_value={
                    "score": 82,
                    "previousScore": 78,
                    "confidenceBand": "reliable",
                    "drivers": [
                        {
                            "name": "Event Match Rate",
                            "value": 90,
                            "weight": 0.35,
                            "status": "good",
                            "trend": "up",
                        },
                    ],
                    "lastUpdated": "2025-01-15T12:00:00Z",
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["score"] == 82


# ---------------------------------------------------------------------------
# EMQ v2: Confidence  GET /api/v1/tenants/{tenant_id}/emq/confidence
# ---------------------------------------------------------------------------
class TestEmqConfidence:
    URL = "/api/v1/tenants/1/emq/confidence"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_confidence_data = AsyncMock(
                return_value={
                    "band": "reliable",
                    "score": 85,
                    "thresholds": {
                        "reliable": 80,
                        "directional": 60,
                    },
                    "factors": [
                        {
                            "name": "Event Coverage",
                            "status": "positive",
                            "contribution": 0.35,
                        },
                    ],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["band"] == "reliable"


# ---------------------------------------------------------------------------
# EMQ v2: Playbook  GET /api/v1/tenants/{tenant_id}/emq/playbook
# ---------------------------------------------------------------------------
class TestEmqPlaybook:
    URL = "/api/v1/tenants/1/emq/playbook"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_emq_score = AsyncMock(
                return_value={
                    "score": 70,
                    "previousScore": 65,
                    "confidenceBand": "directional",
                    "drivers": [
                        {
                            "name": "Event Match Rate",
                            "value": 80,
                            "weight": 0.35,
                            "status": "warning",
                            "trend": "down",
                        },
                        {
                            "name": "Pixel Coverage",
                            "value": 88,
                            "weight": 0.25,
                            "status": "warning",
                            "trend": "flat",
                        },
                        {
                            "name": "Conversion Latency",
                            "value": 65,
                            "weight": 0.20,
                            "status": "critical",
                            "trend": "down",
                        },
                    ],
                    "lastUpdated": "2025-01-15T12:00:00Z",
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            # low drivers should generate playbook items
            assert len(body["data"]) > 0


# ---------------------------------------------------------------------------
# EMQ v2: Playbook Item Update
# PATCH /api/v1/tenants/{tenant_id}/emq/playbook/{item_id}
# ---------------------------------------------------------------------------
class TestEmqPlaybookUpdate:
    URL = "/api/v1/tenants/1/emq/playbook/some-item-id"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.patch(self.URL, json={"status": "in_progress"})
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.patch(
            self.URL,
            headers=tenant2_headers,
            json={"status": "in_progress"},
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        resp = await api_client.patch(
            self.URL,
            headers=admin_headers,
            json={"status": "in_progress", "owner": "user@example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "in_progress"


# ---------------------------------------------------------------------------
# EMQ v2: Incidents  GET /api/v1/tenants/{tenant_id}/emq/incidents
# ---------------------------------------------------------------------------
class TestEmqIncidents:
    URL = "/api/v1/tenants/1/emq/incidents"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(
            self.URL, params={"start_date": "2025-01-01", "end_date": "2025-01-31"}
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(
            self.URL,
            headers=tenant2_headers,
            params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_incidents = AsyncMock(return_value=[])
            resp = await api_client.get(
                self.URL,
                headers=admin_headers,
                params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"] == []


# ---------------------------------------------------------------------------
# EMQ v2: Impact  GET /api/v1/tenants/{tenant_id}/emq/impact
# ---------------------------------------------------------------------------
class TestEmqImpact:
    URL = "/api/v1/tenants/1/emq/impact"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(
            self.URL, params={"start_date": "2025-01-01", "end_date": "2025-01-31"}
        )
        assert resp.status_code == 401

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_impact = AsyncMock(
                return_value={
                    "totalImpact": 12500.0,
                    "currency": "USD",
                    "breakdown": [],
                }
            )
            resp = await api_client.get(
                self.URL,
                headers=admin_headers,
                params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["totalImpact"] == 12500.0


# ---------------------------------------------------------------------------
# EMQ v2: Volatility  GET /api/v1/tenants/{tenant_id}/emq/volatility
# ---------------------------------------------------------------------------
class TestEmqVolatility:
    URL = "/api/v1/tenants/1/emq/volatility"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_volatility = AsyncMock(
                return_value={
                    "svi": 12.3,
                    "trend": "stable",
                    "weeklyData": [],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["svi"] == 12.3


# ---------------------------------------------------------------------------
# EMQ v2: Autopilot State  GET /api/v1/tenants/{tenant_id}/emq/autopilot-state
# ---------------------------------------------------------------------------
class TestEmqAutopilotState:
    URL = "/api/v1/tenants/1/emq/autopilot-state"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqService") as MockSvc:
            MockSvc.return_value.get_autopilot_state = AsyncMock(
                return_value={
                    "mode": "normal",
                    "reason": "EMQ score healthy",
                    "budgetAtRisk": 0.0,
                    "allowedActions": ["pause_underperforming", "reduce_budget"],
                    "restrictedActions": [],
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["mode"] == "normal"


# ---------------------------------------------------------------------------
# EMQ v2: Update Autopilot Mode  PUT /api/v1/tenants/{tenant_id}/emq/autopilot-mode
# ---------------------------------------------------------------------------
class TestEmqUpdateAutopilotMode:
    URL = "/api/v1/tenants/1/emq/autopilot-mode"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.put(self.URL, json={"mode": "limited"})
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.put(
            self.URL, headers=tenant2_headers, json={"mode": "limited"}
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        resp = await api_client.put(
            self.URL,
            headers=admin_headers,
            json={"mode": "limited", "reason": "testing"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["mode"] == "limited"

    async def test_invalid_mode_returns_422(self, api_client, admin_headers, mock_db):
        """Pydantic rejects mode values outside the Literal set."""
        resp = await api_client.put(
            self.URL,
            headers=admin_headers,
            json={"mode": "invalid_mode"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# EMQ v2: Benchmarks  GET /api/v1/emq/benchmarks  (superadmin only)
# ---------------------------------------------------------------------------
class TestEmqBenchmarks:
    URL = "/api/v1/emq/benchmarks"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_superadmin_happy_path(self, api_client, superadmin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqAdminService") as MockSvc:
            MockSvc.return_value.get_benchmarks = AsyncMock(return_value=[])
            resp = await api_client.get(self.URL, headers=superadmin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"] == []


# ---------------------------------------------------------------------------
# EMQ v2: Portfolio  GET /api/v1/emq/portfolio  (superadmin only)
# ---------------------------------------------------------------------------
class TestEmqPortfolio:
    URL = "/api/v1/emq/portfolio"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_superadmin_happy_path(self, api_client, superadmin_headers, mock_db):
        with patch("app.api.v1.endpoints.emq_v2.EmqAdminService") as MockSvc:
            MockSvc.return_value.get_portfolio = AsyncMock(
                return_value={
                    "totalTenants": 10,
                    "byBand": {
                        "reliable": 6,
                        "directional": 3,
                        "unsafe": 1,
                    },
                    "atRiskBudget": 50000.0,
                    "avgScore": 75.0,
                    "topIssues": [],
                }
            )
            resp = await api_client.get(self.URL, headers=superadmin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["totalTenants"] == 10


# ============================================================================
# FEATURE 2 — CDP
# ============================================================================
# CDP endpoints rely on get_current_user (which queries the DB for a User
# object AND checks Redis for token blacklisting).  We override the
# dependency at the FastAPI app level so it returns a lightweight mock.
# ============================================================================

def _make_cdp_current_user(tenant_id: int = 1, user_id: int = 1):
    """Build a minimal mock matching the CurrentUser interface used by CDP."""
    user = MagicMock()
    user.tenant_id = tenant_id
    user.id = user_id
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    user.permissions = {}
    user.cms_role = None
    cu = MagicMock()
    cu.tenant_id = tenant_id
    cu.id = user_id
    cu.user = user
    cu.role = "admin"
    cu.is_active = True
    cu.email = "test@example.com"
    return cu


import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def cdp_client(test_app, mock_db):
    """
    httpx.AsyncClient for CDP endpoints.

    Overrides get_current_user (which normally hits Redis + DB) with a
    lightweight mock so CDP endpoints can be tested without external services.
    """
    from app.auth.deps import get_current_user
    from app.db.session import get_async_session, get_db

    mock_user = _make_cdp_current_user()

    async def override_session():
        yield mock_db

    async def override_current_user():
        return mock_user

    test_app.dependency_overrides[get_async_session] = override_session
    test_app.dependency_overrides[get_db] = override_session
    test_app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CDP: Health  GET /api/v1/cdp/health
# ---------------------------------------------------------------------------
class TestCdpHealth:
    URL = "/api/v1/cdp/health"

    async def test_no_auth_returns_401(self, api_client):
        """CDP health requires auth via TenantMiddleware."""
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        resp = await api_client.get(self.URL, headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["module"] == "cdp"


# ---------------------------------------------------------------------------
# CDP: List Sources  GET /api/v1/cdp/sources
# ---------------------------------------------------------------------------
class TestCdpListSources:
    URL = "/api/v1/cdp/sources"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_happy_path(self, cdp_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.cdp.check_source_rate_limit",
            return_value=None,
        ):
            resp = await cdp_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["sources"] == []
            assert body["total"] == 0


# ---------------------------------------------------------------------------
# CDP: Create Source  POST /api/v1/cdp/sources
# ---------------------------------------------------------------------------
class TestCdpCreateSource:
    URL = "/api/v1/cdp/sources"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(
            self.URL,
            json={"name": "Test", "source_type": "api"},
        )
        assert resp.status_code == 401

    async def test_happy_path(self, cdp_client, admin_headers, mock_db):
        fake_source = MagicMock()
        fake_source.id = uuid.uuid4()
        fake_source.name = "Test Source"
        fake_source.source_type = "website"
        fake_source.source_key = "cdp_test_key"
        fake_source.config = {}
        fake_source.is_active = True
        fake_source.event_count = 0
        fake_source.last_event_at = None
        fake_source.created_at = datetime.now(timezone.utc)
        fake_source.updated_at = datetime.now(timezone.utc)

        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        with patch(
            "app.api.v1.endpoints.cdp.check_source_rate_limit",
            return_value=None,
        ), patch(
            "app.api.v1.endpoints.cdp.CDPSource",
            return_value=fake_source,
        ):
            resp = await cdp_client.post(
                self.URL,
                headers=admin_headers,
                json={"name": "Test Source", "source_type": "website"},
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["name"] == "Test Source"


# ---------------------------------------------------------------------------
# CDP: Lookup Profile  GET /api/v1/cdp/profiles
# ---------------------------------------------------------------------------
class TestCdpLookupProfile:
    URL = "/api/v1/cdp/profiles"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(
            self.URL,
            params={"identifier_type": "email", "identifier_value": "a@b.com"},
        )
        assert resp.status_code == 401

    async def test_profile_not_found(self, cdp_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.cdp.check_profile_rate_limit",
            return_value=None,
        ), patch(
            "app.api.v1.endpoints.cdp._profile_cache"
        ) as mock_cache:
            mock_cache.get_by_lookup.return_value = None
            # mock_db.execute already returns scalar_one_or_none = None
            resp = await cdp_client.get(
                self.URL,
                headers=admin_headers,
                params={"identifier_type": "email", "identifier_value": "a@b.com"},
            )
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CDP: Segments  GET /api/v1/cdp/segments
# ---------------------------------------------------------------------------
class TestCdpListSegments:
    URL = "/api/v1/cdp/segments"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_happy_path(self, cdp_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.cdp.check_segment_rate_limit",
            return_value=None,
        ):
            # mock_db.execute returns empty scalars by default
            resp = await cdp_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["segments"] == []
            assert body["total"] == 0


# ---------------------------------------------------------------------------
# CDP: Event Ingestion  POST /api/v1/cdp/events
# ---------------------------------------------------------------------------
class TestCdpIngestEvents:
    URL = "/api/v1/cdp/events"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL, json={"events": []})
        assert resp.status_code == 401

    async def test_empty_batch_returns_422(self, cdp_client, admin_headers, mock_db):
        """EventBatchInput requires min_length=1 events."""
        resp = await cdp_client.post(
            self.URL,
            headers=admin_headers,
            json={"events": []},
        )
        assert resp.status_code == 422

    async def test_happy_path_single_event(self, cdp_client, admin_headers, mock_db):
        fake_profile = MagicMock()
        fake_profile.id = uuid.uuid4()
        fake_profile.lifecycle_stage = "known"
        fake_profile.total_events = 0
        fake_profile.last_seen_at = None

        with patch(
            "app.api.v1.endpoints.cdp.check_event_rate_limit",
            return_value=None,
        ), patch(
            "app.api.v1.endpoints.cdp.validate_source_key",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.endpoints.cdp.find_or_create_profile",
            new_callable=AsyncMock,
            return_value=(fake_profile, False),
        ), patch(
            "app.api.v1.endpoints.cdp.link_identifiers_to_profile",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.endpoints.cdp._profile_cache",
        ):
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            resp = await cdp_client.post(
                self.URL,
                headers=admin_headers,
                json={
                    "events": [
                        {
                            "event_name": "page_view",
                            "event_time": "2025-01-15T12:00:00Z",
                            "identifiers": [
                                {"type": "email", "value": "test@example.com"}
                            ],
                        }
                    ]
                },
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["accepted"] == 1


# ============================================================================
# FEATURE 3 — AUTOPILOT ENFORCEMENT
# ============================================================================

# ---------------------------------------------------------------------------
# Enforcement: Get Settings
# GET /api/v1/tenant/{tenant_id}/autopilot/enforcement/settings
# ---------------------------------------------------------------------------
class TestEnforcementGetSettings:
    URL = "/api/v1/tenant/1/autopilot/enforcement/settings"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_settings = MagicMock()
            mock_settings.enforcement_enabled = True
            mock_settings.default_mode = "advisory"
            mock_settings.max_daily_budget = 10000.0
            mock_settings.max_campaign_budget = 5000.0
            mock_settings.budget_increase_limit_pct = 20.0
            mock_settings.min_roas_threshold = 2.0
            mock_settings.roas_lookback_days = 7
            mock_settings.max_budget_changes_per_day = 5
            mock_settings.min_hours_between_changes = 4
            mock_settings.rules = []
            MockEnf.return_value.get_settings = AsyncMock(
                return_value=mock_settings
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["settings"]["enforcement_enabled"] is True

    async def test_service_error_propagates(self, api_client, admin_headers, mock_db):
        """When the enforcer raises, the exception propagates (no global handler)."""
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            MockEnf.return_value.get_settings = AsyncMock(
                side_effect=Exception("db error")
            )
            with pytest.raises(Exception, match="db error"):
                await api_client.get(self.URL, headers=admin_headers)


# ---------------------------------------------------------------------------
# Enforcement: Update Settings
# PUT /api/v1/tenant/{tenant_id}/autopilot/enforcement/settings
# ---------------------------------------------------------------------------
class TestEnforcementUpdateSettings:
    URL = "/api/v1/tenant/1/autopilot/enforcement/settings"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.put(
            self.URL, json={"enforcement_enabled": False}
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.put(
            self.URL,
            headers=tenant2_headers,
            json={"enforcement_enabled": False},
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_settings = MagicMock()
            mock_settings.enforcement_enabled = False
            mock_settings.default_mode = "advisory"
            mock_settings.max_daily_budget = 10000.0
            mock_settings.max_campaign_budget = 5000.0
            mock_settings.budget_increase_limit_pct = 20.0
            mock_settings.min_roas_threshold = 2.0
            MockEnf.return_value.update_settings = AsyncMock(
                return_value=mock_settings
            )
            resp = await api_client.put(
                self.URL,
                headers=admin_headers,
                json={"enforcement_enabled": False},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "Settings updated" in body["data"]["message"]


# ---------------------------------------------------------------------------
# Enforcement: Check Action
# POST /api/v1/tenant/{tenant_id}/autopilot/enforcement/check
# ---------------------------------------------------------------------------
class TestEnforcementCheckAction:
    URL = "/api/v1/tenant/1/autopilot/enforcement/check"
    PAYLOAD = {
        "action_type": "budget_increase",
        "entity_type": "campaign",
        "entity_id": "camp_123",
        "proposed_value": {"budget": 5000},
    }

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL, json=self.PAYLOAD)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL, headers=tenant2_headers, json=self.PAYLOAD
        )
        assert resp.status_code == 403

    async def test_happy_path_allowed(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {
                "allowed": True,
                "mode": "advisory",
                "violations": [],
                "warnings": [],
                "requires_confirmation": False,
                "confirmation_token": None,
            }
            MockEnf.return_value.check_action = AsyncMock(
                return_value=mock_result
            )
            resp = await api_client.post(
                self.URL, headers=admin_headers, json=self.PAYLOAD
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["allowed"] is True


# ---------------------------------------------------------------------------
# Enforcement: Confirm Soft-Blocked Action
# POST /api/v1/tenant/{tenant_id}/autopilot/enforcement/confirm
# ---------------------------------------------------------------------------
class TestEnforcementConfirmAction:
    URL = "/api/v1/tenant/1/autopilot/enforcement/confirm"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(
            self.URL, json={"confirmation_token": "tok_123"}
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL,
            headers=tenant2_headers,
            json={"confirmation_token": "tok_123"},
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            MockEnf.return_value.confirm_action = AsyncMock(
                return_value=(True, None)
            )
            resp = await api_client.post(
                self.URL,
                headers=admin_headers,
                json={
                    "confirmation_token": "tok_123",
                    "override_reason": "testing",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["override_logged"] is True

    async def test_invalid_token_returns_400(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            MockEnf.return_value.confirm_action = AsyncMock(
                return_value=(False, "Invalid or expired token")
            )
            resp = await api_client.post(
                self.URL,
                headers=admin_headers,
                json={"confirmation_token": "bad_token"},
            )
            assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Enforcement: Kill Switch
# POST /api/v1/tenant/{tenant_id}/autopilot/enforcement/kill-switch
# ---------------------------------------------------------------------------
class TestEnforcementKillSwitch:
    URL = "/api/v1/tenant/1/autopilot/enforcement/kill-switch"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(
            self.URL, json={"enabled": False}
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL,
            headers=tenant2_headers,
            json={"enabled": False},
        )
        assert resp.status_code == 403

    async def test_happy_path_disable(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_settings = MagicMock()
            mock_settings.enforcement_enabled = False
            MockEnf.return_value.set_kill_switch = AsyncMock(
                return_value=mock_settings
            )
            resp = await api_client.post(
                self.URL,
                headers=admin_headers,
                json={"enabled": False, "reason": "maintenance"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["enforcement_enabled"] is False

    async def test_happy_path_enable(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_settings = MagicMock()
            mock_settings.enforcement_enabled = True
            MockEnf.return_value.set_kill_switch = AsyncMock(
                return_value=mock_settings
            )
            resp = await api_client.post(
                self.URL,
                headers=admin_headers,
                json={"enabled": True},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["enforcement_enabled"] is True


# ---------------------------------------------------------------------------
# Enforcement: Audit Log
# GET /api/v1/tenant/{tenant_id}/autopilot/enforcement/audit-log
# ---------------------------------------------------------------------------
class TestEnforcementAuditLog:
    URL = "/api/v1/tenant/1/autopilot/enforcement/audit-log"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            MockEnf.return_value.get_intervention_log = AsyncMock(
                return_value=[
                    {
                        "id": "log_1",
                        "action": "budget_increase_blocked",
                        "timestamp": "2025-01-15T12:00:00Z",
                    },
                ]
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["count"] == 1
            assert len(body["data"]["logs"]) == 1


# ---------------------------------------------------------------------------
# Enforcement: Add Custom Rule
# POST /api/v1/tenant/{tenant_id}/autopilot/enforcement/rules
# ---------------------------------------------------------------------------
class TestEnforcementAddRule:
    URL = "/api/v1/tenant/1/autopilot/enforcement/rules"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(
            self.URL,
            json={
                "rule_id": "r1",
                "rule_type": "budget_exceeded",
                "threshold_value": 1000,
            },
        )
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL,
            headers=tenant2_headers,
            json={
                "rule_id": "r1",
                "rule_type": "budget_exceeded",
                "threshold_value": 1000,
            },
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf, patch(
            "app.api.v1.endpoints.autopilot_enforcement.ViolationType"
        ) as MockVT, patch(
            "app.api.v1.endpoints.autopilot_enforcement.EnforcementMode"
        ) as MockEM, patch(
            "app.api.v1.endpoints.autopilot_enforcement.EnforcementRule"
        ) as MockRule:
            MockVT.side_effect = lambda x: x
            MockEM.side_effect = lambda x: x
            mock_rule_inst = MagicMock()
            mock_rule_inst.dict.return_value = {
                "rule_id": "r1",
                "rule_type": "budget_exceeded",
                "threshold_value": 1000.0,
                "enforcement_mode": "advisory",
                "enabled": True,
                "description": None,
            }
            MockRule.return_value = mock_rule_inst

            mock_settings = MagicMock()
            mock_settings.rules = []
            MockEnf.return_value.get_settings = AsyncMock(
                return_value=mock_settings
            )
            MockEnf.return_value.update_settings = AsyncMock()

            resp = await api_client.post(
                self.URL,
                headers=admin_headers,
                json={
                    "rule_id": "r1",
                    "rule_type": "budget_exceeded",
                    "threshold_value": 1000,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "r1" in body["data"]["message"]


# ---------------------------------------------------------------------------
# Enforcement: Delete Custom Rule
# DELETE /api/v1/tenant/{tenant_id}/autopilot/enforcement/rules/{rule_id}
# ---------------------------------------------------------------------------
class TestEnforcementDeleteRule:
    URL = "/api/v1/tenant/1/autopilot/enforcement/rules/r1"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.delete(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.delete(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_rule_not_found_returns_404(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot_enforcement.AutopilotEnforcer"
        ) as MockEnf:
            mock_settings = MagicMock()
            mock_settings.rules = []  # no rules => rule_id won't be found
            MockEnf.return_value.get_settings = AsyncMock(
                return_value=mock_settings
            )
            resp = await api_client.delete(self.URL, headers=admin_headers)
            assert resp.status_code == 404


# ============================================================================
# FEATURE 3 — AUTOPILOT (action queue / approval)
# ============================================================================

# ---------------------------------------------------------------------------
# Autopilot: Status
# GET /api/v1/autopilot/tenant/{tenant_id}/autopilot/status
# ---------------------------------------------------------------------------
class TestAutopilotStatus:
    URL = "/api/v1/autopilot/tenant/1/autopilot/status"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot.get_tenant_features",
            new_callable=AsyncMock,
            return_value={"autopilot_level": 1},
        ), patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc, patch(
            "app.features.flags.get_autopilot_caps",
            return_value={
                "max_daily_budget_change": 500,
                "max_single_change_pct": 20,
            },
        ):
            MockSvc.return_value.get_action_summary = AsyncMock(
                return_value={"pending_approval": 3, "approved": 10, "failed": 1}
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["autopilot_level"] == 1
            assert body["data"]["pending_actions"] == 3
            assert body["data"]["enabled"] is True


# ---------------------------------------------------------------------------
# Autopilot: List Actions
# GET /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions
# ---------------------------------------------------------------------------
class TestAutopilotListActions:
    URL = "/api/v1/autopilot/tenant/1/autopilot/actions"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.get_queued_actions = AsyncMock(return_value=[])
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["actions"] == []
            assert body["data"]["count"] == 0


# ---------------------------------------------------------------------------
# Autopilot: Actions Summary
# GET /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions/summary
# ---------------------------------------------------------------------------
class TestAutopilotActionsSummary:
    URL = "/api/v1/autopilot/tenant/1/autopilot/actions/summary"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.get(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.get_action_summary = AsyncMock(
                return_value={
                    "pending_approval": 2,
                    "approved": 5,
                    "applied": 3,
                    "failed": 0,
                    "dismissed": 1,
                }
            )
            resp = await api_client.get(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["pending_approval"] == 2


# ---------------------------------------------------------------------------
# Autopilot: Queue Action
# POST /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions
# ---------------------------------------------------------------------------
class TestAutopilotQueueAction:
    URL = "/api/v1/autopilot/tenant/1/autopilot/actions"
    PAYLOAD = {
        "action_type": "budget_decrease",
        "entity_type": "campaign",
        "entity_id": "camp_99",
        "entity_name": "Test Campaign",
        "platform": "meta",
        "action_json": {"new_budget": 100},
    }

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL, json=self.PAYLOAD)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL, headers=tenant2_headers, json=self.PAYLOAD
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        fake_action = MagicMock()
        fake_action.id = uuid.uuid4()
        fake_action.date = date.today()
        fake_action.action_type = "budget_decrease"
        fake_action.entity_type = "campaign"
        fake_action.entity_id = "camp_99"
        fake_action.entity_name = "Test Campaign"
        fake_action.platform = "meta"
        fake_action.action_json = '{"new_budget": 100}'
        fake_action.before_value = None
        fake_action.after_value = None
        fake_action.status = "queued"
        fake_action.created_at = datetime.now(timezone.utc)
        fake_action.approved_at = None
        fake_action.applied_at = None
        fake_action.error = None

        with patch(
            "app.api.v1.endpoints.autopilot.get_tenant_features",
            new_callable=AsyncMock,
            return_value={"autopilot_level": 0},
        ), patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            svc_instance = MockSvc.return_value
            svc_instance.can_auto_execute.return_value = (False, "suggest-only mode")
            svc_instance.queue_action = AsyncMock(return_value=fake_action)

            resp = await api_client.post(
                self.URL, headers=admin_headers, json=self.PAYLOAD
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["requires_approval"] is True
            assert body["data"]["auto_approved"] is False


# ---------------------------------------------------------------------------
# Autopilot: Approve Action
# POST /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions/{id}/approve
# ---------------------------------------------------------------------------
class TestAutopilotApproveAction:
    ACTION_ID = str(uuid.uuid4())
    URL_TEMPLATE = "/api/v1/autopilot/tenant/1/autopilot/actions/{}/approve"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL_TEMPLATE.format(self.ACTION_ID))
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(
            self.URL_TEMPLATE.format(self.ACTION_ID), headers=tenant2_headers
        )
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        fake_action = MagicMock()
        fake_action.id = uuid.UUID(self.ACTION_ID)
        fake_action.date = date.today()
        fake_action.action_type = "budget_decrease"
        fake_action.entity_type = "campaign"
        fake_action.entity_id = "camp_99"
        fake_action.entity_name = "Test Campaign"
        fake_action.platform = "meta"
        fake_action.action_json = '{"new_budget": 100}'
        fake_action.before_value = None
        fake_action.after_value = None
        fake_action.status = "approved"
        fake_action.created_at = datetime.now(timezone.utc)
        fake_action.approved_at = datetime.now(timezone.utc)
        fake_action.applied_at = None
        fake_action.error = None

        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.approve_action = AsyncMock(
                return_value=fake_action
            )
            resp = await api_client.post(
                self.URL_TEMPLATE.format(self.ACTION_ID),
                headers=admin_headers,
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "approved" in body["data"]["message"].lower()

    async def test_action_not_found_returns_404(
        self, api_client, admin_headers, mock_db
    ):
        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.approve_action = AsyncMock(return_value=None)
            resp = await api_client.post(
                self.URL_TEMPLATE.format(self.ACTION_ID),
                headers=admin_headers,
            )
            assert resp.status_code == 404

    async def test_invalid_uuid_returns_400(self, api_client, admin_headers, mock_db):
        resp = await api_client.post(
            self.URL_TEMPLATE.format("not-a-uuid"),
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Autopilot: Dismiss Action
# POST /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions/{id}/dismiss
# ---------------------------------------------------------------------------
class TestAutopilotDismissAction:
    ACTION_ID = str(uuid.uuid4())
    URL_TEMPLATE = "/api/v1/autopilot/tenant/1/autopilot/actions/{}/dismiss"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL_TEMPLATE.format(self.ACTION_ID))
        assert resp.status_code == 401

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        fake_action = MagicMock()
        fake_action.id = uuid.UUID(self.ACTION_ID)
        fake_action.date = date.today()
        fake_action.action_type = "budget_decrease"
        fake_action.entity_type = "campaign"
        fake_action.entity_id = "camp_99"
        fake_action.entity_name = "Test Campaign"
        fake_action.platform = "meta"
        fake_action.action_json = '{"new_budget": 100}'
        fake_action.before_value = None
        fake_action.after_value = None
        fake_action.status = "dismissed"
        fake_action.created_at = datetime.now(timezone.utc)
        fake_action.approved_at = None
        fake_action.applied_at = None
        fake_action.error = None

        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.dismiss_action = AsyncMock(
                return_value=fake_action
            )
            resp = await api_client.post(
                self.URL_TEMPLATE.format(self.ACTION_ID),
                headers=admin_headers,
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "dismissed" in body["data"]["message"].lower()


# ---------------------------------------------------------------------------
# Autopilot: Get Single Action
# GET /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions/{id}
# ---------------------------------------------------------------------------
class TestAutopilotGetAction:
    ACTION_ID = str(uuid.uuid4())
    URL_TEMPLATE = "/api/v1/autopilot/tenant/1/autopilot/actions/{}"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.get(self.URL_TEMPLATE.format(self.ACTION_ID))
        assert resp.status_code == 401

    async def test_not_found(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.get_action_by_id = AsyncMock(return_value=None)
            resp = await api_client.get(
                self.URL_TEMPLATE.format(self.ACTION_ID),
                headers=admin_headers,
            )
            assert resp.status_code == 404

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        fake_action = MagicMock()
        fake_action.id = uuid.UUID(self.ACTION_ID)
        fake_action.date = date.today()
        fake_action.action_type = "budget_decrease"
        fake_action.entity_type = "campaign"
        fake_action.entity_id = "camp_99"
        fake_action.entity_name = "Test Campaign"
        fake_action.platform = "meta"
        fake_action.action_json = '{"new_budget": 100}'
        fake_action.before_value = None
        fake_action.after_value = None
        fake_action.status = "queued"
        fake_action.created_at = datetime.now(timezone.utc)
        fake_action.approved_at = None
        fake_action.applied_at = None
        fake_action.error = None

        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.get_action_by_id = AsyncMock(
                return_value=fake_action
            )
            resp = await api_client.get(
                self.URL_TEMPLATE.format(self.ACTION_ID),
                headers=admin_headers,
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["action"]["status"] == "queued"


# ---------------------------------------------------------------------------
# Autopilot: Approve All Actions
# POST /api/v1/autopilot/tenant/{tenant_id}/autopilot/actions/approve-all
# ---------------------------------------------------------------------------
class TestAutopilotApproveAll:
    URL = "/api/v1/autopilot/tenant/1/autopilot/actions/approve-all"

    async def test_no_auth_returns_401(self, api_client):
        resp = await api_client.post(self.URL)
        assert resp.status_code == 401

    async def test_wrong_tenant_returns_403(self, api_client, tenant2_headers):
        resp = await api_client.post(self.URL, headers=tenant2_headers)
        assert resp.status_code == 403

    async def test_happy_path(self, api_client, admin_headers, mock_db):
        with patch(
            "app.api.v1.endpoints.autopilot.AutopilotService"
        ) as MockSvc:
            MockSvc.return_value.approve_all_queued = AsyncMock(return_value=5)
            resp = await api_client.post(self.URL, headers=admin_headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["approved_count"] == 5
