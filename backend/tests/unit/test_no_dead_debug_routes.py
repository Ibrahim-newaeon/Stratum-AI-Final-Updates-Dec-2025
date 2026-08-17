# =============================================================================
# Stratum AI - Debug Surface Inventory
# =============================================================================
"""The memory-debug surface is gone, and stays gone.

``app/api/v1/endpoints/memory_debug.py`` carried 14 memory-profiling endpoints
behind a superadmin dependency, with 404 stubs in production unless
``ENABLE_MEMORY_DEBUG`` was set. None of it was reachable: the router was never
passed to ``api_router.include_router``, *and* ``init_debug_endpoints()`` — the
only thing that supplies the auditor those handlers dereference — was never
called. Mounting it as-written would have answered 503
"Memory auditor not initialized" on every path.

The module was deleted rather than wired (2026-08-17). This is a guard, not a
red-first test: the assertion held before the deletion too, because the routes
were never registered. It exists so that re-introducing a `/debug/*` surface
has to be a deliberate act that updates this file, rather than a stray
``include_router`` nobody notices.
"""

from app.main import app


def _paths() -> set:
    """Every path the assembled app actually serves.

    Read off the app rather than ``api_router``: on this FastAPI version
    ``api_router.routes`` also holds ``_IncludedRouter`` markers, which carry no
    ``.path`` — enumerating those raises AttributeError instead of reporting
    what is mounted.
    """
    return {p for p in (getattr(r, "path", None) for r in app.routes) if p}


def test_no_memory_debug_routes_are_registered():
    offenders = {p for p in _paths() if "/debug/memory" in p}
    assert not offenders, f"memory_debug was re-mounted: {sorted(offenders)}"


def test_no_debug_surface_is_served():
    """Nothing under a /debug segment is served at all."""
    offenders = {p for p in _paths() if "/debug" in p}
    assert not offenders, f"unexpected debug routes: {sorted(offenders)}"
