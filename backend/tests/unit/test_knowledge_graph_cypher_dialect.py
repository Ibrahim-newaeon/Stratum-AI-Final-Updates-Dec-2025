# =============================================================================
# Stratum AI - Cypher dialect constraints for Apache AGE
# =============================================================================
"""AGE speaks a narrower Cypher than openCypher, and the queries reach it
through SQLAlchemy ``text()``, which claims a syntax of its own. Three patterns
are valid Cypher, read as correct in review, and fail at runtime here. All
three shipped, and none was caught until the routes were first run against a
live AGE database -- five of the eight read routes answered 500.

1. ``AS count``. ``RETURN count(n) AS count`` raises ``syntax error at or near
   "count"``. The aggregate is fine; reusing its name as the alias is not.

2. ``-[:REL]->``. SQLAlchemy reads a colon preceded by a non-word character as
   a bind parameter, so ``-[:PERFORMED]->`` never reaches Postgres -- it raises
   ``A value is required for bind parameter 'PERFORMED'``. Node labels survive
   because ``(n:Profile)`` puts a word character before the colon. Naming the
   relationship (``-[x:PERFORMED]->``) is the whole fix.

3. ``reduce(...)``. AGE does not implement it. ``reduce(s = 0, x IN xs | s + x)``
   raises ``syntax error at or near "|"``.

4. ``ORDER BY`` on an alias an aggregating ``WITH`` just produced. AGE raises
   ``could not find rte for <alias>``; the alias only comes into scope for
   sorting once a further ``WITH`` projects it forward.

These are checked against the Cypher string literals themselves rather than by
executing them, because CI's Postgres has no AGE. That makes this a lint with
teeth: it cannot prove a query returns the right answer, but it does prove no
query carries a construct AGE is known to reject -- which is the failure mode
that actually happened.

The writer is in scope, not just the readers. ``sync.py`` carried pattern 2 as
well, and the backfill never revealed it: it was first run against a database
holding zero source rows, so it created no edges and raised nothing.
"""

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SERVICE_DIR = (
    Path(__file__).resolve().parents[2] / "app" / "services" / "knowledge_graph"
)

# A string is treated as Cypher if it contains a clause that only Cypher has.
# Scanning every string would catch prose in docstrings describing the very
# patterns this module forbids.
CYPHER_MARKERS = ("MATCH ", "MERGE ", "RETURN ", "CREATE (")


def _cypher_literals() -> list[tuple[Path, int, str]]:
    """Every Cypher string literal in the service package, with its location.

    f-strings are reassembled from their literal fragments with a placeholder
    standing in for each interpolation, so a pattern written across an
    interpolation boundary is still visible.
    """
    found: list[tuple[Path, int, str]] = []
    for path in sorted(SERVICE_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                text = "".join(
                    part.value if isinstance(part, ast.Constant) else "{}"
                    for part in node.values
                )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
            else:
                continue
            if any(marker in text for marker in CYPHER_MARKERS):
                found.append((path, node.lineno, text))
    return found


def _offenders(predicate) -> list[str]:
    return [
        f"{path.name}:{lineno}"
        for path, lineno, text in _cypher_literals()
        if predicate(text)
    ]


def test_cypher_literals_are_actually_found():
    """Guards the three tests below: a broken scanner would pass them all."""
    assert len(_cypher_literals()) > 20


def test_no_query_aliases_an_aggregate_as_count():
    """``AS count`` is a syntax error in AGE. Any other alias works."""
    offenders = _offenders(lambda text: "AS count\n" in text or "AS count " in text)
    assert offenders == [], (
        f"AGE rejects 'AS count' -- rename the alias at: {offenders}"
    )


def test_no_query_uses_an_anonymous_relationship_pattern():
    """``-[:REL]->`` is eaten by SQLAlchemy's bind-parameter parser."""
    offenders = _offenders(lambda text: "-[:" in text or "-[ :" in text)
    assert offenders == [], (
        "SQLAlchemy reads '-[:REL]' as a bind parameter -- name the "
        f"relationship, as in '-[r:REL]', at: {offenders}"
    )


def test_no_query_uses_reduce():
    """AGE does not implement ``reduce()``."""
    offenders = _offenders(lambda text: "reduce(" in text)
    assert offenders == [], (
        f"AGE does not implement reduce() -- aggregate another way, at: {offenders}"
    )


class TestBuilderNamesEveryRelationship:
    """``CypherQueryBuilder`` assembles patterns at runtime, so the source scan
    above cannot see them. It emitted ``[:LABEL]`` whenever a caller did not
    pass ``edge_alias`` -- which is most callers -- and every query it built
    therefore died on the bind-parameter collision before reaching Postgres.
    """

    @staticmethod
    def _builder():
        from app.services.knowledge_graph.queries import CypherQueryBuilder

        return CypherQueryBuilder(tenant_id=1)

    def test_match_edge_names_the_relationship_without_an_explicit_alias(self):
        from app.services.knowledge_graph.models import EdgeLabel, NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE)
        builder.match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
        query, _ = builder.return_fields(["p"]).build()

        assert "-[:" not in query, f"anonymous relationship in: {query}"

    def test_optional_match_edge_names_the_relationship_too(self):
        from app.services.knowledge_graph.models import EdgeLabel, NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE)
        builder.optional_match_edge("p", EdgeLabel.GENERATED, "r", NodeLabel.REVENUE)
        query, _ = builder.return_fields(["p"]).build()

        assert "-[:" not in query, f"anonymous relationship in: {query}"

    def test_two_relationships_in_one_query_get_distinct_aliases(self):
        """A repeated alias is a different failure, not a fix."""
        from app.services.knowledge_graph.models import EdgeLabel, NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE)
        builder.match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
        builder.match_edge("e", EdgeLabel.GENERATED, "r", NodeLabel.REVENUE)
        query, _ = builder.return_fields(["p"]).build()

        aliases = re.findall(r"-\[(\w+):", query)
        assert len(aliases) == 2
        assert len(set(aliases)) == 2, f"duplicate relationship alias in: {query}"

    def test_return_count_does_not_default_to_the_reserved_alias(self):
        """``return_count`` defaulted to ``AS count``, which AGE rejects."""
        from app.services.knowledge_graph.models import NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE)
        query, _ = builder.return_count("p").build()

        assert "AS count" not in query, f"reserved alias in: {query}"


def _orders_by_alias_from_aggregating_clause(text: str) -> bool:
    """True when ORDER BY names an alias the immediately preceding clause
    produced with an aggregate.

    AGE raises ``could not find rte for <alias>``: the alias is not in scope
    for sorting until another WITH projects it forward.
    """
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if not line.upper().startswith("ORDER BY"):
            continue
        for previous in reversed(lines[:index]):
            upper = previous.upper()
            if not upper.startswith(("WITH ", "RETURN ")):
                continue
            aggregates = re.search(r"\b(sum|count|collect|avg|min|max)\s*\(", previous, re.I)
            alias = re.search(r"\bAS\s+(\w+)\s*$", previous)
            sorted_by = line[len("ORDER BY") :].strip().split()[0].rstrip(",")
            if aggregates and alias and sorted_by == alias.group(1):
                return True
            break
    return False


def test_no_query_sorts_by_an_alias_the_aggregating_clause_just_created():
    """AGE cannot ORDER BY an alias straight out of an aggregating WITH."""
    offenders = _offenders(_orders_by_alias_from_aggregating_clause)
    assert offenders == [], (
        "AGE raises 'could not find rte' here -- project the aliases through "
        f"a plain WITH before ORDER BY, at: {offenders}"
    )
