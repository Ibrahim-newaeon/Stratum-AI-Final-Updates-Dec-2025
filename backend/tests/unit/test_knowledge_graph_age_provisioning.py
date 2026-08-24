# =============================================================================
# Stratum AI - Apache AGE provisioning for the Knowledge Graph
# =============================================================================
"""The knowledge graph runs on Apache AGE, and three things have to line up
before a single route works: the extension has to be installed, the named graph
and its labels have to exist, and every session issuing Cypher has to have AGE
loaded with ag_catalog on its search_path.

These tests pin all three, because each failed silently in a different way
before. The extension was never provisioned (the flag existed to 503 around
it), the migration that would have created the graph sat in
``backend/alembic/versions/`` -- a directory ``alembic.ini`` does not read, so
it had never run against any environment -- and nothing put ag_catalog on the
path, which would leave ``cypher(...)`` unresolvable even once the extension
was in place.
"""

import ast
import re
from pathlib import Path
from typing import Any, Optional

import pytest

from app.core.config import settings
from app.services.knowledge_graph import KnowledgeGraphService

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations" / "versions"

AGE_REVISION = "065_add_age_knowledge_graph"


# =============================================================================
# Session preparation
# =============================================================================
class _RecordingSession:
    """Records the SQL a service issues, in order, without a database."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement: Any) -> Any:
        self.statements.append(str(statement).strip())
        return _EmptyResult()


class _EmptyResult:
    def fetchone(self) -> None:
        return None

    def __iter__(self):
        return iter(())


class TestSessionPreparation:
    async def test_loads_age_and_sets_search_path_before_the_query(self):
        """Order matters and is the whole point.

        AGE installs the parse hooks Cypher depends on when its library loads,
        so LOAD has to happen before the statement needing them is parsed --
        Postgres' own on-demand loading fires at first function call, which is
        already too late.
        """
        session = _RecordingSession()
        service = KnowledgeGraphService(session)

        await service._execute_graph("SELECT 1")

        assert session.statements[0] == "LOAD 'age'"
        assert session.statements[1].startswith("SET LOCAL search_path")
        assert "ag_catalog" in session.statements[1]
        assert session.statements[2] == "SELECT 1"

    async def test_search_path_is_transaction_local(self):
        """SET LOCAL, not SET.

        These run on pooled connections. A plain SET would follow the
        connection back into the pool and quietly change name resolution for
        every unrelated query that reused it.
        """
        session = _RecordingSession()
        service = KnowledgeGraphService(session)

        await service._execute_graph("SELECT 1")

        assert "SET LOCAL" in session.statements[1]

    async def test_public_query_methods_route_through_the_helper(self):
        """A method reaching the graph without going through _execute_graph
        gets an unprepared session and fails at runtime, so exercise a real
        caller rather than only the helper itself."""
        session = _RecordingSession()
        service = KnowledgeGraphService(session)

        await service.health_check()

        assert session.statements[0] == "LOAD 'age'"
        assert any("cypher(" in statement for statement in session.statements)


def test_no_cypher_bypasses_the_helper():
    """Guards the pattern, not one call site.

    Every Cypher statement in the service goes through _execute_graph. A raw
    ``self.session.execute(text(query))`` would skip LOAD and the search_path
    and then fail only when that one route is exercised.
    """
    source = (
        BACKEND_DIR / "app" / "services" / "knowledge_graph" / "service.py"
    ).read_text(encoding="utf-8")

    # The helper itself is the one legitimate raw execute of `query`.
    assert source.count("await self.session.execute(text(query))") == 1
    assert source.count("await self._execute_graph(query)") >= 1


# =============================================================================
# Migration chain
# =============================================================================
def _module_assignments(path: Path) -> dict[str, Any]:
    """Read revision metadata without importing the module.

    Parsed rather than regexed because merge migrations spell down_revision as
    a multi-line tuple.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        else:
            continue
        if node.value is None:
            continue
        for name in targets:
            if name in ("revision", "down_revision"):
                try:
                    found[name] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    return found


def _revision_map() -> dict[str, dict[str, Any]]:
    return {
        meta["revision"]: meta
        for path in sorted(MIGRATIONS_DIR.glob("*.py"))
        for meta in [_module_assignments(path)]
        if "revision" in meta
    }


def test_age_migration_lives_in_the_directory_alembic_reads():
    """alembic.ini sets script_location = migrations.

    The earlier AGE migration was written into backend/alembic/versions/, which
    Alembic never reads, so it had never run anywhere.
    """
    script_location = None
    for line in (BACKEND_DIR / "alembic.ini").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("script_location"):
            script_location = line.split("=", 1)[1].strip()

    assert script_location == "migrations"
    assert AGE_REVISION in _revision_map()


def test_age_migration_extends_the_existing_chain():
    revisions = _revision_map()

    assert revisions[AGE_REVISION]["down_revision"] == "064_widen_cdp_identifier_value"


def test_migrations_have_exactly_one_head():
    """A second head makes `alembic upgrade head` ambiguous, and it fails.

    Cheap to assert here; otherwise it surfaces during a deploy.

    Asserts the count, not the identity. This used to pin the head to the AGE
    revision, which made every later migration fail a knowledge-graph test for
    doing nothing wrong — and taught whoever hit it to edit the expected value,
    which is exactly the reflex that lets a genuine second head through. That
    the AGE migration sits on the chain is still covered, by
    ``test_age_migration_extends_the_existing_chain``.
    """
    revisions = _revision_map()
    referenced: set[str] = set()
    for meta in revisions.values():
        down = meta.get("down_revision")
        if isinstance(down, (tuple, list)):
            referenced.update(down)
        elif down is not None:
            referenced.add(down)

    heads = sorted(set(revisions) - referenced)

    assert len(heads) == 1, f"expected a single head, found {heads}"
    assert AGE_REVISION in revisions


# =============================================================================
# Image provisioning
# =============================================================================
def test_database_image_builds_age_and_pgvector():
    """Neither published image carries both extensions.

    pgvector is required by migration 049, AGE by 065. Losing either breaks
    `alembic upgrade head` on a fresh environment.
    """
    dockerfile = (BACKEND_DIR / "Dockerfile.postgres").read_text(encoding="utf-8")

    assert "pgvector/pgvector:pg16" in dockerfile
    assert "github.com/apache/age.git" in dockerfile
    # Pinned tag, not a moving branch.
    assert "AGE_REF=PG16/" in dockerfile


def test_compose_db_service_builds_that_image():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "dockerfile: Dockerfile.postgres" in compose
    # The stock image no longer satisfies the stack; catching a revert here is
    # cheaper than catching it when CREATE EXTENSION age fails mid-migration.
    assert "image: pgvector/pgvector:pg16" not in compose


def _db_service_image(compose_path: Path) -> Optional[str]:
    """Return the ``image:`` a compose file pins for its own ``db`` service.

    None means the file either has no ``db`` service or builds one rather than
    pulling it. Parsed by indentation rather than with a YAML library because
    the test suite does not depend on one, and the shape being checked is two
    levels deep and stable.
    """
    in_db = False
    for line in compose_path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^  [a-z_-]+:\s*$", line):
            in_db = line.strip().rstrip(":") in ("db", "postgres", "database")
            continue
        if in_db and (match := re.match(r"^    image:\s*(\S+)", line)):
            return match.group(1)
    return None


def test_no_compose_file_pins_a_postgres_without_the_extensions():
    """Every environment's database needs pgvector AND AGE, not just the default.

    ``docker-compose.staging.yml`` is standalone -- its usage line is ``docker
    compose -f docker-compose.staging.yml up -d`` with its own api, worker and
    frontend -- so it inherits nothing from ``docker-compose.yml`` and pinned
    ``postgres:16-alpine``. That image carries neither extension, which fails
    ``CREATE EXTENSION vector`` in migration 049 before AGE is even reached.

    Checked across every compose file rather than staging alone: the next
    environment file added would otherwise repeat the same mistake silently.
    """
    offenders = {}
    for compose in sorted(REPO_ROOT.glob("docker-compose*.yml")):
        image = _db_service_image(compose)
        if image is None:
            continue
        if not image.startswith("stratum-postgres:"):
            offenders[compose.name] = image

    assert offenders == {}, (
        "these compose files pull a Postgres image without pgvector/AGE: "
        f"{offenders}. Build from backend/Dockerfile.postgres instead."
    )


# =============================================================================
# Flag
# =============================================================================
def test_knowledge_graph_flag_stays_off():
    """Provisioned and writable, and still gated -- for the third reason now.

    AGE is installed, the graph exists, and a writer exists: the backfill
    script plus a beat-scheduled incremental sync. What is still true is that
    running the backfill is a *deploy step*, performed per environment. Until
    it has run against a given database, that database's graph is empty, and
    the routes there would answer "no problems found" when the truth is "no
    data has ever been loaded".

    So this flag is flipped per environment after the backfill, not once in
    source. The default stays off because the default environment is the one
    where nobody has run it yet.
    """
    assert settings.feature_knowledge_graph is False


def test_freshness_is_wired_to_the_same_flag():
    """Replaces test_nothing_populates_the_graph_yet, which has served its purpose.

    That test scanned app/workers/ for any knowledge-graph reference and failed
    the moment one appeared, on the theory that a writer appearing was the
    moment to flip the flag. A writer has appeared, and the theory was only
    half right: population is still per environment, so the flag did not move.

    What replaces it is the invariant that actually matters now. Enabling the
    graph has to enable its upkeep in the same breath -- a graph that is
    switched on without the incremental sync scheduled is a snapshot that
    starts decaying immediately, and stale nodes are answered from just as
    confidently as fresh ones. See test_knowledge_graph_incremental_task.py.
    """
    celery_app_source = (BACKEND_DIR / "app" / "workers" / "celery_app.py").read_text(
        encoding="utf-8"
    )

    assert "sync-knowledge-graph" in celery_app_source, (
        "the incremental sync lost its beat entry; the graph would go stale "
        "the moment the backfill finished"
    )
    assert "app.workers.tasks.sync_knowledge_graph_incremental" in celery_app_source
