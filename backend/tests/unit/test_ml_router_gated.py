# =============================================================================
# Stratum AI - ML router authorization wiring test (ML-003)
# =============================================================================
"""
The /ml router (model upload / train / delete) operates on the global model
registry and was completely unauthenticated. It must now require super admin.
This asserts the gate is actually wired onto every /ml route so a future
refactor can't silently drop it.
"""

import pytest

from app.api.v1 import api_router
from app.auth.permissions import require_super_admin

pytestmark = pytest.mark.unit


def _ml_routes():
    return [r for r in api_router.routes if getattr(r, "path", "").startswith("/ml")]


def test_ml_routes_exist():
    assert _ml_routes(), "expected /ml routes to be registered"


def test_every_ml_route_requires_super_admin():
    for route in _ml_routes():
        calls = [d.call for d in route.dependant.dependencies]
        assert (
            require_super_admin in calls
        ), f"/ml route {route.path} is missing the require_super_admin gate"


def test_a_non_ml_public_route_is_not_gated():
    # Sanity check the assertion above isn't vacuously true: an auth route must
    # NOT carry the super-admin gate.
    login = [
        r for r in api_router.routes if getattr(r, "path", "").endswith("/auth/login")
    ]
    assert login
    for route in login:
        calls = [d.call for d in route.dependant.dependencies]
        assert require_super_admin not in calls
