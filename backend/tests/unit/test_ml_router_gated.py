# =============================================================================
# Stratum AI - ML router authorization wiring test (ML-003)
# =============================================================================
"""
The /ml router (model upload / train / delete) operates on the global model
registry and was completely unauthenticated. It must now require super admin.
This asserts the gate is actually wired onto every /ml route so a future
refactor can't silently drop it.

We inspect the fully-built application (app.main.app) rather than the bare
api_router: building the app runs every include_router() deterministically, so
the mounted routes and their dependants are authoritative regardless of test
import order.
"""

import pytest

from app.auth.permissions import require_super_admin
from app.main import app

pytestmark = pytest.mark.unit


def _ml_routes():
    return [r for r in app.routes if getattr(r, "path", "").startswith("/api/v1/ml")]


def _route_deps(route):
    return [d.call for d in route.dependant.dependencies]


def test_ml_routes_exist():
    assert _ml_routes(), "expected /api/v1/ml routes to be registered"


def test_every_ml_route_requires_super_admin():
    for route in _ml_routes():
        assert require_super_admin in _route_deps(
            route
        ), f"/ml route {route.path} is missing the require_super_admin gate"


def test_a_non_ml_public_route_is_not_gated():
    # Sanity check the assertion above isn't vacuously true: an auth route must
    # NOT carry the super-admin gate.
    login = [r for r in app.routes if getattr(r, "path", "").endswith("/auth/login")]
    assert login
    for route in login:
        assert require_super_admin not in _route_deps(route)
