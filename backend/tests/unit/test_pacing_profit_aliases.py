# =============================================================================
# Stratum AI - Pacing/Profit Frontend-Alias Route Tests
# =============================================================================
"""
Tests for the frontend-compatibility route aliases (Tier 3, Pacing/Profit
reconcile — path half).

pacing.ts / profit.ts call endpoint names the backend never exposed
(/status, /summary, /targets/{id}/pacing, /alerts/stats; /true-roas,
/metrics/summary, /metrics/daily). Those are now registered as aliases of the
existing handlers via stacked route decorators, so the FE stops 404'ing.

(The response-envelope reconcile — the endpoints return {"status": ...} while
the FE expects {"success", "data"} — and the genuinely-missing endpoints
(reports CRUD, /kpis/daily, /products/{id}/margins) remain a separate follow-up
that needs a running frontend to validate.)
"""

from app.api.v1.endpoints.pacing import router as pacing_router
from app.api.v1.endpoints.profit import router as profit_router


def _paths(router) -> set:
    return {route.path for route in router.routes}


def test_pacing_aliases_registered():
    paths = _paths(pacing_router)
    # FE-expected aliases now resolve.
    assert "/status" in paths
    assert "/summary" in paths
    assert "/targets/{target_id}/pacing" in paths
    assert "/alerts/stats" in paths
    # Originals still present (aliases are additive).
    assert "/all" in paths
    assert "/target/{target_id}" in paths
    assert "/alerts/summary" in paths


def test_profit_aliases_registered():
    paths = _paths(profit_router)
    assert "/true-roas" in paths
    assert "/metrics/summary" in paths
    assert "/metrics/daily" in paths
    # Originals still present.
    assert "/roas" in paths
    assert "/trend" in paths
