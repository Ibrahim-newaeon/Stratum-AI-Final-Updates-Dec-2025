# =============================================================================
# Stratum AI - Pacing/Profit Route Prefix Tests
# =============================================================================
"""
Tests for removing the doubled URL prefix on the pacing and profit routers
(Tier 3, mechanical slice).

Both routers are mounted with a prefix (``/pacing`` / ``/profit``) yet several
routes ALSO started with that segment (``@router.get("/profit/roas")``),
yielding ``/api/v1/profit/profit/roas``. The routes are now relative so the
real endpoints sit at sane single-prefixed paths. (The deeper FE<->BE surface
reconcile — endpoints the FE calls that the BE never implemented — is a
separate follow-up.)
"""

from app.api.v1.endpoints.pacing import router as pacing_router
from app.api.v1.endpoints.profit import router as profit_router


def _paths(router) -> set:
    return {route.path for route in router.routes}


def test_profit_router_has_no_double_prefix():
    paths = _paths(profit_router)
    # No route on the /profit-prefixed router should itself start with /profit.
    assert not any(p.startswith("/profit/") or p == "/profit" for p in paths), paths
    # The de-doubled analytics routes are present.
    assert "/roas" in paths
    assert "/trend" in paths
    assert "/by-product" in paths


def test_pacing_router_has_no_double_prefix():
    paths = _paths(pacing_router)
    assert not any(p.startswith("/pacing/") or p == "/pacing" for p in paths), paths
    assert "/all" in paths
    assert "/target/{target_id}" in paths
    assert "/snapshot" in paths
