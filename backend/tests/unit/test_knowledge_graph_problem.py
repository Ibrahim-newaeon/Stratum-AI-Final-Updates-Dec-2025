# =============================================================================
# Stratum AI - Knowledge Graph Problem Serialization Unit Tests
# =============================================================================
"""Unit tests for the pure dataclass serialization in
``app.services.knowledge_graph``: ``Problem.to_dict`` (including nested
``Solution`` flattening) and the ``ProblemSeverity`` / ``ProblemCategory``
enums. The DB-backed KnowledgeGraphService is out of scope here.
"""

from datetime import datetime, timezone

import pytest

from app.services.knowledge_graph import (
    Problem,
    ProblemCategory,
    ProblemSeverity,
    Solution,
)

pytestmark = pytest.mark.unit


def _solution(**overrides) -> Solution:
    base = dict(
        title="Reconnect Meta",
        description="OAuth token expired",
        action_type="reconnect_integration",
        priority=1,
        steps=["Open Integrations", "Click Reconnect"],
        affected_entities=[{"type": "integration", "id": "meta"}],
    )
    base.update(overrides)
    return Solution(**base)


def _problem(**overrides) -> Problem:
    base = dict(
        id="prob_1",
        category=ProblemCategory.SIGNAL_DEGRADED,
        severity=ProblemSeverity.CRITICAL,
        title="Signal health dropped",
        description="EMQ fell below threshold",
        detected_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return Problem(**base)


class TestProblemToDict:
    def test_serializes_enums_to_values(self):
        d = _problem().to_dict()
        assert d["category"] == "signal_degraded"
        assert d["severity"] == "critical"
        assert d["id"] == "prob_1"

    def test_defaults_are_empty_collections(self):
        d = _problem().to_dict()
        assert d["root_cause_path"] == []
        assert d["affected_nodes"] == []
        assert d["metrics"] == {}
        assert d["solutions"] == []

    def test_nested_solutions_are_flattened(self):
        d = _problem(solutions=[_solution(auto_fixable=True)]).to_dict()
        assert len(d["solutions"]) == 1
        sol = d["solutions"][0]
        assert sol["title"] == "Reconnect Meta"
        assert sol["action_type"] == "reconnect_integration"
        assert sol["priority"] == 1
        assert sol["auto_fixable"] is True
        assert sol["estimated_impact"] is None


class TestEnums:
    def test_severity_values(self):
        assert {s.value for s in ProblemSeverity} == {
            "critical",
            "high",
            "medium",
            "low",
        }

    def test_category_contains_known_members(self):
        values = {c.value for c in ProblemCategory}
        assert {"revenue_decline", "signal_degraded", "attribution_gap"} <= values
