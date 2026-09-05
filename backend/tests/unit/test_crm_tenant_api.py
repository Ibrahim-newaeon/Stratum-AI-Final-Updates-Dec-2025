# =============================================================================
# Stratum AI - Tenant-facing CRM surface tests
# =============================================================================
"""Guards for the ``/integrations/crm`` router and its service.

Two failure modes are covered, because the bug this code fixes was both at
once: routes the frontend calls that do not exist, and queries that could
return another tenant's rows.

The route test is the one that would have caught the original defect.
``frontend/src/api/crm.ts`` called ``/integrations/crm/*`` from the day it was
written and no such route was ever mounted, so the Settings > Integrations
views 404'd in silence — nothing in either test suite asserted that the paths
the client calls are paths the server serves.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services import crm_tenant_service

# The exact paths frontend/src/api/crm.ts requests. Kept as literals rather
# than derived from the router: a test that reads the router would pass no
# matter what the router said, which is how the original gap survived.
FRONTEND_PATHS = {
    ("GET", "/integrations/crm/connections"),
    ("POST", "/integrations/crm/connections/{connection_id}/sync"),
    ("GET", "/integrations/crm/contacts"),
    ("GET", "/integrations/crm/deals"),
    ("GET", "/integrations/crm/pipeline/summary"),
    ("GET", "/integrations/crm/writeback/config"),
    ("PUT", "/integrations/crm/writeback/config"),
}


def _resolve(router) -> set[tuple[str, str]]:
    """Flatten a router tree into {(method, path)}.

    ``include_router`` in this FastAPI version stores an ``_IncludedRouter``
    proxy rather than copying routes, so ``router.routes`` is not the route
    list and has to be walked through ``original_router``.
    """
    found: set[tuple[str, str]] = set()
    for route in getattr(router, "routes", []):
        original = getattr(route, "original_router", None)
        if original is not None:
            found |= _resolve(original)
        elif hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods - {"HEAD", "OPTIONS"}:
                found.add((method, route.path))
    return found


@pytest.fixture(scope="module")
def registered_routes() -> set[tuple[str, str]]:
    from app.api.v1 import api_router

    return _resolve(api_router)


def test_every_frontend_crm_path_is_served(registered_routes):
    """Each path api/crm.ts calls must resolve to a mounted route."""
    missing = FRONTEND_PATHS - registered_routes
    assert not missing, (
        "frontend/src/api/crm.ts calls paths the API does not serve "
        f"(these 404 at runtime): {sorted(missing)}"
    )


def test_the_route_walker_is_not_vacuous(registered_routes):
    """Sanity check: the walker resolves real routes, so absence means absence.

    Without this, a walker that silently returned everything — or a set that
    happened to contain the paths for an unrelated reason — would make the
    test above pass while the routes were still missing.
    """
    assert ("GET", "/integrations/hubspot/status") in registered_routes
    assert ("GET", "/integrations/crm/definitely-not-a-route") not in registered_routes


@pytest.mark.asyncio
async def test_get_connection_filters_by_tenant():
    """The tenant filter must be in the WHERE clause, not a post-hoc check.

    A lookup by id alone that checks ownership afterwards leaks existence: the
    caller can tell a foreign id from a nonexistent one by the error. It also
    breaks the moment someone forgets the check.
    """
    captured = {}

    async def capture(stmt):
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=capture)

    await crm_tenant_service.get_connection(db, tenant_id=7, connection_id=uuid4())

    where = captured["sql"].split("WHERE", 1)[1]
    assert "tenant_id" in where
    assert "crm_connections.id" in where


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda db: crm_tenant_service.list_connections(db, 7),
        lambda db: crm_tenant_service.list_contacts(db, 7),
        lambda db: crm_tenant_service.list_deals(db, 7),
    ],
)
async def test_list_queries_are_tenant_scoped(call):
    """Every list query filters on tenant_id."""
    statements = []

    async def capture(stmt):
        statements.append(str(stmt))
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=capture)
    db.scalar = AsyncMock(return_value=0)

    await call(db)

    assert statements, "no query was issued"
    for sql in statements:
        assert "tenant_id" in sql.split("WHERE", 1)[-1], f"unscoped query: {sql}"


@pytest.mark.asyncio
async def test_pipeline_summary_reports_not_connected_without_a_connection():
    """A tenant with no CRM gets not_connected, not a page of zeroes.

    The view branches on this to show an empty state; zeroes would read as
    "your pipeline is empty" to someone who simply has not connected a CRM.
    """
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock()

    summary = await crm_tenant_service.get_pipeline_summary(db, tenant_id=7)

    assert summary == {"status": "not_connected"}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_writeback_update_leaves_unsent_fields_alone():
    """A partial update must not reset the toggles it does not mention."""
    from app.schemas.crm import WritebackConfigUpdate

    config = MagicMock()
    config.enabled = False
    config.sync_contacts = True
    config.sync_deals = True

    async def fake_get(db, tenant_id):
        return config

    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    original = crm_tenant_service.get_writeback_config
    crm_tenant_service.get_writeback_config = fake_get
    try:
        await crm_tenant_service.update_writeback_config(
            db, 7, WritebackConfigUpdate(enabled=True)
        )
    finally:
        crm_tenant_service.get_writeback_config = original

    assert config.enabled is True
    # Untouched, rather than reset to the schema defaults.
    assert config.sync_contacts is True
    assert config.sync_deals is True


@pytest.mark.asyncio
async def test_sync_is_not_dispatched_for_another_tenants_connection():
    """trigger_sync returns None for a foreign connection and queues nothing."""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    assert await crm_tenant_service.trigger_sync(db, 7, uuid4()) is None
