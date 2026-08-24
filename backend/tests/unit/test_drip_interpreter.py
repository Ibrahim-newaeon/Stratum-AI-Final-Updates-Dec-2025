# =============================================================================
# Stratum AI - Drip Flow Graph Interpreter
# =============================================================================
"""The interpreter decides what a drip sequence does next.

It is deliberately free of I/O, so every branch is exercised here with plain
dicts — the same JSONB shape the flow builder stores.

The cases that matter most are the negative ones. A drip engine that silently
takes the false branch when it cannot evaluate a condition, or that quietly
completes an enrollment when a node has no outgoing step, looks exactly like a
working sequence while doing nothing. Every one of those paths must produce an
explicit error instead.
"""

from app.services.drip.interpreter import (
    ACTION_NONE,
    ACTION_NOTIFY,
    ACTION_SEND_EMAIL,
    ConditionContext,
    evaluate_condition,
    index_graph,
    step,
    validate_graph,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def node(node_id: str, node_type: str, **data):
    return {"id": node_id, "type": node_type, "position": {}, "data": dict(data)}


def edge(source: str, target: str, label: str | None = None):
    e = {"id": f"e_{source}_{target}", "source": source, "target": target}
    if label is not None:
        e["label"] = label
    return e


def linear_graph():
    """trigger -> email -> wait(24h) -> end."""
    nodes = [
        node("t1", "trigger", trigger_type="user_subscribed"),
        node("e1", "email", subject="Welcome", template_id="tpl_1"),
        node("w1", "wait", delay_hours=24),
        node("x1", "end"),
    ]
    edges = [edge("t1", "e1"), edge("e1", "w1"), edge("w1", "x1")]
    return nodes, edges


def condition_graph(condition="email_opened", **extra):
    """trigger -> email -> condition -> (yes: email2, no: end)."""
    nodes = [
        node("t1", "trigger", trigger_type="user_subscribed"),
        node("e1", "email", subject="First", template_id="a"),
        node("c1", "condition", condition=condition, **extra),
        node("e2", "email", subject="Follow up", template_id="b"),
        node("x1", "end"),
    ]
    edges = [
        edge("t1", "e1"),
        edge("e1", "c1"),
        edge("c1", "e2"),  # first == true branch
        edge("c1", "x1"),  # second == false branch
        edge("e2", "x1"),
    ]
    return nodes, edges


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


class TestIndexGraph:
    def test_finds_the_trigger_as_entry(self):
        index = index_graph(*linear_graph())
        assert index.entry_node_id == "t1"

    def test_preserves_edge_declaration_order(self):
        # The condition fallback depends on this: the builder emits unlabelled
        # edges, so "first edge is the true branch" is the only signal there is.
        index = index_graph(*condition_graph())
        assert [e["target"] for e in index.out_edges["c1"]] == ["e2", "x1"]

    def test_ignores_edges_from_unknown_nodes(self):
        nodes, edges = linear_graph()
        edges.append(edge("ghost", "e1"))
        index = index_graph(nodes, edges)
        assert "ghost" not in index.out_edges

    def test_empty_graph_has_no_entry(self):
        index = index_graph([], [])
        assert index.entry_node_id is None


# ---------------------------------------------------------------------------
# One test per node type
# ---------------------------------------------------------------------------


class TestStepPerNodeType:
    def test_trigger_moves_on_without_side_effect(self):
        index = index_graph(*linear_graph())
        result = step(index, "t1")
        assert result.action == ACTION_NONE
        assert result.next_node_id == "e1"
        assert not result.terminal and not result.failed

    def test_email_asks_the_caller_to_send(self):
        index = index_graph(*linear_graph())
        result = step(index, "e1")
        assert result.action == ACTION_SEND_EMAIL
        assert result.node["data"]["subject"] == "Welcome"
        assert result.next_node_id == "w1"
        assert result.wait_seconds == 0

    def test_wait_parks_for_its_delay(self):
        index = index_graph(*linear_graph())
        result = step(index, "w1")
        assert result.action == ACTION_NONE
        assert result.wait_seconds == 24 * 3600
        assert result.next_node_id == "x1"

    def test_notification_asks_the_caller_to_notify(self):
        nodes = [
            node("t1", "trigger"),
            node("n1", "notification", title="Hi", body="There"),
            node("x1", "end"),
        ]
        index = index_graph(nodes, [edge("t1", "n1"), edge("n1", "x1")])
        result = step(index, "n1")
        assert result.action == ACTION_NOTIFY
        assert result.next_node_id == "x1"

    def test_end_is_terminal(self):
        index = index_graph(*linear_graph())
        result = step(index, "x1")
        assert result.terminal is True
        assert result.next_node_id is None
        assert not result.failed


class TestWaitDelayUnits:
    """The builder emits hours; a graph authored via the API may not."""

    def test_accepts_seconds_minutes_hours_days(self):
        for data, expected in (
            ({"delay_seconds": 90}, 90),
            ({"delay_minutes": 5}, 300),
            ({"delay_hours": 2}, 7200),
            ({"delay_days": 3}, 259200),
        ):
            nodes = [
                node("t1", "trigger"),
                node("w1", "wait", **data),
                node("x1", "end"),
            ]
            index = index_graph(nodes, [edge("t1", "w1"), edge("w1", "x1")])
            assert step(index, "w1").wait_seconds == expected

    def test_unusable_delay_falls_back_to_the_builder_default(self):
        # Not zero: a wait node that fires immediately would turn a drip into a
        # burst, which is worse than being a day late.
        nodes = [
            node("t1", "trigger"),
            node("w1", "wait", delay_hours="not a number"),
            node("x1", "end"),
        ]
        index = index_graph(nodes, [edge("t1", "w1"), edge("w1", "x1")])
        assert step(index, "w1").wait_seconds == 24 * 3600


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


class TestConditionBranching:
    def test_opened_takes_the_true_branch(self):
        index = index_graph(*condition_graph("email_opened"))
        result = step(index, "c1", ConditionContext(email_opened=True))
        assert result.next_node_id == "e2"

    def test_not_opened_takes_the_false_branch(self):
        index = index_graph(*condition_graph("email_opened"))
        result = step(index, "c1", ConditionContext(email_opened=False))
        assert result.next_node_id == "x1"

    def test_negated_condition_inverts(self):
        index = index_graph(*condition_graph("email_not_opened"))
        assert (
            step(index, "c1", ConditionContext(email_opened=False)).next_node_id == "e2"
        )
        assert (
            step(index, "c1", ConditionContext(email_opened=True)).next_node_id == "x1"
        )

    def test_click_conditions(self):
        index = index_graph(*condition_graph("link_clicked"))
        assert (
            step(index, "c1", ConditionContext(link_clicked=True)).next_node_id == "e2"
        )
        index = index_graph(*condition_graph("link_not_clicked"))
        assert (
            step(index, "c1", ConditionContext(link_clicked=True)).next_node_id == "x1"
        )

    def test_labels_win_over_declaration_order(self):
        nodes, edges = condition_graph("email_opened")
        # Reverse the order but label them, so order and labels disagree.
        edges = [e for e in edges if e["source"] != "c1"]
        edges += [edge("c1", "x1", label="yes"), edge("c1", "e2", label="no")]
        index = index_graph(nodes, edges)
        assert (
            step(index, "c1", ConditionContext(email_opened=True)).next_node_id == "x1"
        )

    def test_single_outgoing_edge_means_branches_converge(self):
        nodes, edges = condition_graph("email_opened")
        edges = [e for e in edges if not (e["source"] == "c1" and e["target"] == "x1")]
        index = index_graph(nodes, edges)
        assert (
            step(index, "c1", ConditionContext(email_opened=True)).next_node_id == "e2"
        )
        assert (
            step(index, "c1", ConditionContext(email_opened=False)).next_node_id == "e2"
        )

    def test_roas_threshold_compares(self):
        index = index_graph(*condition_graph("roas_above", threshold=2.0))
        assert step(index, "c1", ConditionContext(roas=3.0)).next_node_id == "e2"
        assert step(index, "c1", ConditionContext(roas=1.0)).next_node_id == "x1"

        index = index_graph(*condition_graph("roas_below", threshold=2.0))
        assert step(index, "c1", ConditionContext(roas=1.0)).next_node_id == "e2"


class TestConditionFailsLoudly:
    """An unevaluable condition must fail, never quietly take a branch."""

    def test_missing_threshold_is_an_error(self):
        index = index_graph(*condition_graph("roas_above"))
        result = step(index, "c1", ConditionContext(roas=3.0))
        assert result.failed
        assert "threshold" in result.error

    def test_missing_roas_value_is_an_error(self):
        index = index_graph(*condition_graph("roas_above", threshold=2.0))
        result = step(index, "c1", ConditionContext(roas=None))
        assert result.failed
        assert "ROAS" in result.error

    def test_unknown_condition_is_an_error(self):
        index = index_graph(*condition_graph("reads_minds"))
        result = step(index, "c1")
        assert result.failed
        assert "Unknown condition" in result.error

    def test_evaluate_condition_returns_reason_not_false(self):
        ok, err = evaluate_condition(
            node("c", "condition", condition="roas_above"), ConditionContext()
        )
        assert ok is None and err is not None


# ---------------------------------------------------------------------------
# Structural failures at runtime
# ---------------------------------------------------------------------------


class TestStepFailsLoudly:
    def test_missing_node_is_an_error(self):
        # The case graph versioning exists to prevent: an enrollment pointing at
        # a node its version no longer contains.
        index = index_graph(*linear_graph())
        result = step(index, "gone")
        assert result.failed
        assert "not in this sequence version" in result.error

    def test_dead_end_is_an_error_not_a_completion(self):
        nodes = [node("t1", "trigger"), node("e1", "email")]
        index = index_graph(nodes, [edge("t1", "e1")])
        result = step(index, "e1")
        assert result.failed
        assert not result.terminal

    def test_unknown_node_type_is_an_error(self):
        nodes = [node("t1", "trigger"), node("z1", "teleport"), node("x1", "end")]
        index = index_graph(nodes, [edge("t1", "z1"), edge("z1", "x1")])
        result = step(index, "z1")
        assert result.failed
        assert "unknown type" in result.error


# ---------------------------------------------------------------------------
# Validation, which runs before a version is published
# ---------------------------------------------------------------------------


class TestValidateGraph:
    def test_a_good_graph_passes(self):
        assert validate_graph(*linear_graph()) == []
        assert validate_graph(*condition_graph()) == []

    def test_empty_graph_is_rejected(self):
        # The bug this whole function exists for: activate used to flip status
        # on any graph at all, including nothing.
        assert validate_graph([], []) == ["Sequence has no nodes."]

    def test_missing_trigger_is_rejected(self):
        nodes, edges = linear_graph()
        nodes = [n for n in nodes if n["type"] != "trigger"]
        edges = [e for e in edges if e["source"] != "t1"]
        errors = validate_graph(nodes, edges)
        assert any("needs a trigger node" in e for e in errors)

    def test_two_triggers_are_rejected(self):
        nodes, edges = linear_graph()
        nodes.append(node("t2", "trigger"))
        edges.append(edge("t2", "e1"))
        assert any("2 trigger nodes" in e for e in validate_graph(nodes, edges))

    def test_edge_to_unknown_node_is_rejected(self):
        nodes, edges = linear_graph()
        edges.append(edge("e1", "nowhere"))
        assert any("unknown node" in e for e in validate_graph(nodes, edges))

    def test_orphan_node_is_rejected(self):
        nodes, edges = linear_graph()
        nodes.append(node("orphan", "email", subject="Nobody sees this"))
        assert any("not reachable" in e for e in validate_graph(nodes, edges))

    def test_duplicate_ids_are_rejected(self):
        nodes, edges = linear_graph()
        nodes.append(node("e1", "email"))
        assert any("Duplicate node id" in e for e in validate_graph(nodes, edges))

    def test_dead_end_is_rejected(self):
        nodes = [node("t1", "trigger"), node("e1", "email")]
        assert any(
            "no outgoing step" in e for e in validate_graph(nodes, [edge("t1", "e1")])
        )

    def test_end_node_with_outgoing_edge_is_rejected(self):
        nodes, edges = linear_graph()
        edges.append(edge("x1", "e1"))
        assert any("must not have outgoing" in e for e in validate_graph(nodes, edges))

    def test_roas_condition_without_threshold_is_rejected_at_publish(self):
        # Caught here so it can never reach the worker, where it could only
        # fail the enrollment after someone had already been enrolled.
        errors = validate_graph(*condition_graph("roas_above"))
        assert any("numeric threshold" in e for e in errors)

    def test_condition_with_three_branches_is_rejected(self):
        nodes, edges = condition_graph()
        nodes.append(node("e3", "email", subject="Third"))
        edges.append(edge("c1", "e3"))
        edges.append(edge("e3", "x1"))
        assert any("one or two outgoing" in e for e in validate_graph(nodes, edges))

    def test_zero_delay_wait_is_rejected(self):
        nodes = [
            node("t1", "trigger"),
            node("w1", "wait", delay_hours=0),
            node("x1", "end"),
        ]
        errors = validate_graph(nodes, [edge("t1", "w1"), edge("w1", "x1")])
        assert any("positive delay" in e for e in errors)

    def test_errors_are_deduplicated_and_ordered(self):
        nodes, edges = linear_graph()
        nodes.append(node("orphan_b", "email"))
        nodes.append(node("orphan_a", "email"))
        errors = validate_graph(nodes, edges)
        assert errors == sorted(errors)
        assert len(errors) == len(set(errors))


class TestLoopDetection:
    def test_loop_without_a_wait_is_rejected(self):
        # A tight cycle is a live spin: the worker would re-run these as fast as
        # it can dequeue them.
        nodes = [
            node("t1", "trigger"),
            node("e1", "email"),
            node("c1", "condition", condition="email_opened"),
            node("x1", "end"),
        ]
        edges = [
            edge("t1", "e1"),
            edge("e1", "c1"),
            edge("c1", "e1"),  # back edge, no wait in between
            edge("c1", "x1"),
        ]
        errors = validate_graph(nodes, edges)
        assert any("Loop with no wait step" in e for e in errors)

    def test_loop_with_a_wait_is_allowed(self):
        # "Check in every week until they buy" is a legitimate drip.
        nodes = [
            node("t1", "trigger"),
            node("e1", "email"),
            node("w1", "wait", delay_days=7),
            node("c1", "condition", condition="link_clicked"),
            node("x1", "end"),
        ]
        edges = [
            edge("t1", "e1"),
            edge("e1", "w1"),
            edge("w1", "c1"),
            edge("c1", "x1"),
            edge("c1", "e1"),
        ]
        assert validate_graph(nodes, edges) == []

    def test_self_loop_without_wait_is_rejected(self):
        nodes = [
            node("t1", "trigger"),
            node("c1", "condition", condition="email_opened"),
            node("x1", "end"),
        ]
        edges = [edge("t1", "c1"), edge("c1", "c1"), edge("c1", "x1")]
        assert any("Loop with no wait step" in e for e in validate_graph(nodes, edges))
