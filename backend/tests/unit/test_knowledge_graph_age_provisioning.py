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

    assert heads == [AGE_REVISION], f"expected a single head, found {heads}"


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
    """Provisioned, but still gated -- and not for the original reason.

    AGE is installed and the graph exists, so the routes would resolve rather
    than 500. What is missing is a writer: enabling this now would answer
    "no problems found" when the truth is "no data has ever been loaded",
    and a confident wrong answer is worse than an honest 503.
    """
    assert settings.feature_knowledge_graph is False


def test_nothing_populates_the_graph_yet():
    """The reason the flag is off, pinned as an executable fact.

    KnowledgeGraphSyncService has seven populate methods and a full_sync
    orchestrator, and nothing instantiates it -- no Celery task, no beat entry,
    and every KG route is a GET.

    When this test fails, a writer has appeared, and that is the moment to flip
    feature_knowledge_graph to True. It is a reminder, not a prohibition.
    """
    workers = BACKEND_DIR / "app" / "workers"
    referencing = [
        path.relative_to(BACKEND_DIR).as_posix()
        for path in workers.rglob("*.py")
        if "knowledge_graph" in path.read_text(encoding="utf-8")
    ]

    assert referencing == [], (
        "A worker now references the knowledge graph, so something may finally "
        f"populate it: {referencing}. If so, turn feature_knowledge_graph on "
        "and delete this test."
    )
