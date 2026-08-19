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

# A string is treated as Cypher if it opens with a clause only Cypher has.
# Scanning every string would catch prose in docstrings describing the very
# patterns this module forbids -- "Returns: ... RETURN fields." is a docstring,
# not a query, so RETURN alone does not qualify.
CYPHER_MARKERS = ("MATCH ", "MERGE ", "CREATE (")


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
                # The placeholder deliberately carries no braces: "{}" would
                # make every interpolated RETURN look like a map literal to the
                # check below, which is exactly the bug it exists to catch.
                text = "".join(
                    part.value if isinstance(part, ast.Constant) else "PLACEHOLDER"
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
    """``AS count`` is a syntax error in AGE. Any other alias works.

    Matched by word boundary rather than by the following character: the first
    version of this test looked for a trailing space or newline and walked
    straight past ``count(*) AS count,`` in the middle of a RETURN list.
    """
    offenders = _offenders(lambda text: re.search(r"\bAS\s+count\b", text) is not None)
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


def test_no_query_calls_datetime_or_duration():
    """AGE implements neither: ``function datetime does not exist``.

    Timestamps go into the graph as ISO-8601 strings (``to_cypher_properties``
    calls ``isoformat()``), so a cutoff computed in Python and compared as a
    string is both correct and cheaper than a temporal function would be.
    """
    offenders = _offenders(
        lambda text: "datetime()" in text or "duration(" in text
    )
    assert offenders == [], (
        "AGE has no datetime()/duration() -- interpolate an ISO cutoff "
        f"computed in Python, at: {offenders}"
    )


def _top_level_items(clause: str) -> list[str]:
    """Split a RETURN body on commas that are not inside brackets."""
    depth, current, items = 0, "", []
    for char in clause:
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        if char == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += char
    if current.strip():
        items.append(current)
    return [item.strip() for item in items]


def _returns_one_map(text: str) -> bool:
    match = re.search(
        r"\bRETURN\b(.*?)(?:\bORDER BY\b|\bLIMIT\b|\bSKIP\b|$)", text, re.S | re.I
    )
    if not match:
        return True  # a write with no RETURN yields no rows to shape
    items = _top_level_items(" ".join(match.group(1).split()))
    if len(items) != 1:
        return False
    only = items[0]
    # A map literal, or a bare alias naming a vertex or edge -- agtype renders
    # both as a mapping, which is what every caller reads. An expression or a
    # scalar aggregate is neither.
    return only.startswith("{") or re.fullmatch(r"\w+", only) is not None


def test_every_query_returns_exactly_one_map():
    """Every call site wraps Cypher as ``AS (result agtype)`` -- one column.

    AGE requires the column definition list to match the RETURN arity, so a
    query returning several columns raises ``return row and column definition
    list do not match``. Returning a single scalar parses, but then hands the
    caller an int where it expects a mapping and raises ``'int' object has no
    attribute 'get'``. One map satisfies both: it matches the single declared
    column and it arrives as the dict every caller already reads.
    """
    offenders = _offenders(lambda text: not _returns_one_map(text))
    assert offenders == [], (
        "each query must RETURN exactly one map, as in "
        f"'RETURN {{a: x, b: y}} AS result', at: {offenders}"
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

    def test_build_returns_a_single_map_for_several_fields(self):
        """``AS (result agtype)`` declares one column; RETURN must match it."""
        from app.services.knowledge_graph.models import NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE)
        query, _ = builder.return_fields(
            ["p.external_id AS profile_id", "p.lifecycle_stage AS lifecycle"]
        ).build()

        assert "RETURN {profile_id: profile_id, lifecycle: lifecycle} AS result" in query

    def test_build_keeps_an_ordering_alias_in_scope(self):
        """Sorting by an alias only the RETURN created would lose it.

        ``segment_revenue_performance`` orders by ``total_revenue_cents``, an
        alias its return fields define, so the projection has to survive into a
        clause ORDER BY can see.
        """
        from app.services.knowledge_graph.models import NodeLabel

        builder = self._builder()
        builder.match_node("r", NodeLabel.REVENUE)
        query, _ = (
            builder.return_fields(["sum(r.amount_cents) AS total_revenue_cents"])
            .order_by("total_revenue_cents", desc=True)
            .build()
        )

        ordering = query.index("ORDER BY total_revenue_cents")
        projection = query.index("AS total_revenue_cents")
        assert projection < ordering, f"alias not in scope when sorted: {query}"

    def test_where_is_emitted_before_optional_match(self):
        """A WHERE after OPTIONAL MATCH filters the optional pattern only.

        ``match_node`` puts the tenant filter in the WHERE clause, so emitting
        it after an OPTIONAL MATCH stops it constraining the required match at
        all -- another tenant's rows come back with the optional half unbound.
        Verified against live AGE: the generated customer_journey query
        returned a second tenant's profile under the same external_id.
        """
        from app.services.knowledge_graph.models import EdgeLabel, NodeLabel

        builder = self._builder()
        builder.match_node("p", NodeLabel.PROFILE, {"external_id": "1"})
        builder.match_edge("p", EdgeLabel.PERFORMED, "e", NodeLabel.EVENT)
        builder.optional_match_edge("e", EdgeLabel.GENERATED, "r", NodeLabel.REVENUE)
        query, _ = builder.return_fields(["p.external_id AS profile_id"]).build()

        assert "WHERE" in query and "OPTIONAL MATCH" in query
        assert query.index("WHERE") < query.index("OPTIONAL MATCH"), (
            f"tenant filter does not constrain the required match: {query}"
        )

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
