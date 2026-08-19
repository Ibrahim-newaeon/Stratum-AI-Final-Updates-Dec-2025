# =============================================================================
# Stratum AI - Knowledge graph coverage gaps are declared, not silent
# =============================================================================
"""Routes whose relationships have no writer say so.

The backfill populates eight node labels and three edge types: PERFORMED,
GENERATED and BELONGS_TO. The read path traverses five more that nothing
creates, plus two node labels nothing creates. That is not an oversight in the
backfill — the relationships do not exist in the relational schema to be
copied:

* ``TrustGate -> Automation`` (BLOCKED / TRIGGERED). ``enforcement_audit_logs``
  records ``(entity_type, entity_id, action_type, timestamp)`` — the *platform*
  entity, e.g. a campaign id — with no FK to ``fact_actions_queue``. The
  enforcer runs as a pre-flight check on a proposed action, so the queue row
  does not exist yet and its id is not in scope to record. Joining on
  ``(entity_id, action_type)`` inside a time window would guess which
  automation a gate blocked whenever a tenant touched the same campaign twice
  in a day.

* ``Signal -> TrustGate`` (EVALUATED_BY). ``fact_signal_health_daily`` is keyed
  ``(tenant, platform, date)`` and the audit log has no platform column, so
  there is no way to say which signal informed a gate.

* ``Revenue -> Channel`` (ATTRIBUTED_TO) and the Channel/Touchpoint nodes.
  Sources exist (``conversion_paths``, ``channel_interactions``,
  ``daily_attributed_revenue``) but are not yet loaded.

The failure mode this file prevents is the one the whole feature was gated for:
after a *successful* backfill these surfaces would return ``[]``, and "no
automations were blocked" is indistinguishable from "we never loaded the edge
that would show one". Declaring the gap costs a 501; hiding it costs trust in
every number on the page.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.knowledge_graph import coverage

pytestmark = pytest.mark.unit

KG_DIR = Path(__file__).resolve().parents[2] / "app" / "services" / "knowledge_graph"


# =============================================================================
# The declaration itself
# =============================================================================
class TestDeclaration:
    def test_backfilled_edges_are_the_three_the_writer_creates(self):
        assert coverage.BACKFILLED_EDGES == frozenset(
            {"PERFORMED", "GENERATED", "BELONGS_TO"}
        )

    def test_every_gap_explains_itself(self):
        """A 501 with no reason is only marginally better than an empty list."""
        for gap in coverage.GAPS.values():
            assert gap.reason
            assert gap.requires
            # The reason has to name the missing linkage, not just restate the
            # symptom, or the next reader re-derives this whole investigation.
            assert len(gap.reason) > 60

    def test_gaps_cover_the_surfaces_that_cannot_answer(self):
        assert set(coverage.GAPS) >= {
            "blocked_automations",
            "automation_trace",
            "revenue_by_channel",
            "trust_gate_bottlenecks",
            "channel_inefficiency",
        }


# =============================================================================
# Routes
# =============================================================================
class TestRouteGuard:
    def test_raises_501_not_an_empty_list(self):
        """501 Not Implemented: the server understands it and has no source.

        Deliberately not 404 (the tenant exists), not 503 (nothing is
        temporarily down), and emphatically not 200 with [].
        """
        with pytest.raises(HTTPException) as exc:
            coverage.require_supported("blocked_automations")

        assert exc.value.status_code == 501

    def test_the_detail_names_the_missing_linkage(self):
        with pytest.raises(HTTPException) as exc:
            coverage.require_supported("blocked_automations")

        detail = str(exc.value.detail)
        assert "enforcement_audit_logs" in detail
        assert "fact_actions_queue" in detail

    def test_a_supported_surface_passes_through(self):
        assert coverage.require_supported("revenue_by_segment") is None

    def test_unknown_keys_are_a_programming_error_not_a_gap(self):
        """Fail loudly rather than silently treating a typo as supported."""
        with pytest.raises(KeyError):
            coverage.require_supported("revenue_by_bananas", strict=True)


# =============================================================================
# Detectors
# =============================================================================
class TestDetectorReporting:
    def test_unavailable_detectors_are_named(self):
        names = coverage.unavailable_detectors()

        assert set(names) == {
            "blocked_automations",
            "trust_gate_bottlenecks",
            "channel_inefficiency",
        }

    def test_each_carries_its_reason(self):
        reported = coverage.unavailable_report()

        assert len(reported) == 3
        for entry in reported:
            assert entry["key"]
            assert entry["reason"]
            assert entry["requires"]


# =============================================================================
# The declaration must not drift from the code
# =============================================================================
class TestDeclarationMatchesReality:
    """Derives the gap from the source instead of trusting the constant.

    This is the audit that found the problem, kept executable. It fails in both
    directions, which is the point: add a writer for an edge and the stale GAPS
    entry starts suppressing a surface that now works; add a query traversing
    an edge nothing writes and it goes undeclared.
    """

    @staticmethod
    def _edges_written() -> set[str]:
        import re

        import app.services.knowledge_graph.models as m

        sync = (KG_DIR / "sync.py").read_text(encoding="utf-8")
        batch = sync[: sync.index("# REAL-TIME SYNC HOOKS")]
        cls_to_label = {
            name: getattr(getattr(m, name).model_fields["label"].default, "value", None)
            for name in dir(m)
            if isinstance(getattr(m, name), type)
            and issubclass(getattr(m, name), m.GraphEdge)
            and getattr(m, name) is not m.GraphEdge
        }
        return {
            cls_to_label[n]
            for n in re.findall(r"\b(\w+Edge)\(", batch)
            if cls_to_label.get(n)
        }

    def test_backfilled_edges_constant_matches_the_writer(self):
        assert coverage.BACKFILLED_EDGES == frozenset(self._edges_written()), (
            "BACKFILLED_EDGES no longer matches what sync.py's batch pass "
            "creates. If an edge gained a writer, drop the matching entry from "
            "GAPS in the same change."
        )

    def test_no_query_traverses_an_unwritten_edge_undeclared(self):
        import re

        traversed: set[str] = set()
        for name in ("queries.py", "insights.py", "service.py"):
            text = (KG_DIR / name).read_text(encoding="utf-8")
            traversed |= set(re.findall(r"-\[\w*:(\w+)\]", text))

        # Edges the real-time hooks create are equally unreachable today —
        # nothing calls the hooks either.
        hook_only = {"BLOCKED", "TRIGGERED", "MERGED_INTO"}
        unreachable = traversed - set(coverage.BACKFILLED_EDGES) - {"", "r"}

        declared = {req for gap in coverage.GAPS.values() for req in gap.requires}
        undeclared = {
            edge for edge in unreachable if not any(edge in req for req in declared)
        }

        assert undeclared == set(), (
            f"these edge types are traversed but never written, and no "
            f"CoverageGap declares them: {sorted(undeclared)}. Either write "
            f"them in the backfill or add them to GAPS. (hook-only, also "
            f"unreachable: {sorted(hook_only & traversed)})"
        )
