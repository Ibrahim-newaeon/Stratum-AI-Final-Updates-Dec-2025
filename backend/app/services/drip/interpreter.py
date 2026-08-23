# =============================================================================
# Stratum AI - Drip Flow Graph Interpreter
# =============================================================================
"""Walks a drip sequence's flow graph and decides what happens next.

Deliberately free of I/O. Every function here takes plain dicts — the JSONB
``nodes``/``edges`` exactly as the flow builder stores them — and returns a
decision. The caller (``app.workers.drip_tasks``) performs the side effect and
persists the new position. That split is what makes the whole state machine
testable without a broker, a database or an SMTP server.

Node ``data`` shapes follow what ``frontend/src/views/DripCampaignBuilder.tsx``
emits:

===============  ==========================================================
``trigger``      ``{"trigger_type": "user_subscribed"}``
``email``        ``{"subject": str, "template_id": str}``
``wait``         ``{"delay_hours": 24}``
``condition``    ``{"condition": "email_opened", "threshold": float?}``
``notification`` ``{"title": str, "body": str}``
``end``          ``{}``
===============  ==========================================================
"""

from dataclasses import dataclass, field
from typing import Any, Optional

# --- node types -------------------------------------------------------------
NODE_TRIGGER = "trigger"
NODE_EMAIL = "email"
NODE_WAIT = "wait"
NODE_CONDITION = "condition"
NODE_NOTIFICATION = "notification"
NODE_END = "end"

KNOWN_NODE_TYPES = frozenset(
    {
        NODE_TRIGGER,
        NODE_EMAIL,
        NODE_WAIT,
        NODE_CONDITION,
        NODE_NOTIFICATION,
        NODE_END,
    }
)

# --- side effects the caller must perform -----------------------------------
ACTION_NONE = "none"
ACTION_SEND_EMAIL = "send_email"
ACTION_NOTIFY = "notify"

# --- conditions the builder offers ------------------------------------------
COND_EMAIL_OPENED = "email_opened"
COND_EMAIL_NOT_OPENED = "email_not_opened"
COND_LINK_CLICKED = "link_clicked"
COND_LINK_NOT_CLICKED = "link_not_clicked"
COND_ROAS_ABOVE = "roas_above"
COND_ROAS_BELOW = "roas_below"

#: Conditions that compare against a number and therefore need a threshold.
THRESHOLD_CONDITIONS = frozenset({COND_ROAS_ABOVE, COND_ROAS_BELOW})

KNOWN_CONDITIONS = frozenset(
    {
        COND_EMAIL_OPENED,
        COND_EMAIL_NOT_OPENED,
        COND_LINK_CLICKED,
        COND_LINK_NOT_CLICKED,
        COND_ROAS_ABOVE,
        COND_ROAS_BELOW,
    }
)

#: Edge labels the builder may set on a condition's two outgoing edges. It does
#: not set them today (it creates ``{id, source, target}`` only), so the
#: interpreter falls back to declaration order: first edge is the true branch.
TRUE_LABELS = frozenset({"yes", "true", "opened", "clicked"})
FALSE_LABELS = frozenset({"no", "false", "not_opened", "not_clicked"})

#: Applied when a wait node carries no usable delay. One day matches the
#: builder's own default rather than firing the next step immediately.
DEFAULT_WAIT_HOURS = 24


@dataclass(frozen=True)
class GraphIndex:
    """A flow graph in the shape the interpreter needs to walk it."""

    nodes: dict[str, dict[str, Any]]
    #: node id -> outgoing edges, in declaration order (the condition fallback
    #: depends on that order being stable).
    out_edges: dict[str, list[dict[str, Any]]]
    entry_node_id: Optional[str]

    def node(self, node_id: Optional[str]) -> Optional[dict[str, Any]]:
        if node_id is None:
            return None
        return self.nodes.get(node_id)


@dataclass(frozen=True)
class ConditionContext:
    """What the caller knows about this recipient, for condition nodes.

    ``email_opened`` / ``link_clicked`` describe the most recent email step of
    *this* enrollment, which the worker reads from ``drip_execution_logs``.
    """

    email_opened: bool = False
    link_clicked: bool = False
    roas: Optional[float] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepResult:
    """The decision for one node transition."""

    action: str
    node: Optional[dict[str, Any]]
    next_node_id: Optional[str]
    #: Seconds to park before the next node runs. Non-zero only for waits.
    wait_seconds: int = 0
    #: Set when the sequence should stop here.
    terminal: bool = False
    #: Set when the graph or its data is unusable. Terminal, and the caller
    #: records it on the enrollment rather than retrying forever.
    error: Optional[str] = None

    @property
    def failed(self) -> bool:
        return self.error is not None


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def index_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> GraphIndex:
    """Build the lookup structure the walker needs.

    Tolerant by design — a malformed node is indexed rather than raising, so
    :func:`validate_graph` can report every problem at once instead of the
    first one.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes or []:
        node_id = node.get("id")
        if isinstance(node_id, str) and node_id:
            by_id[node_id] = node

    out: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in by_id}
    for edge in edges or []:
        source = edge.get("source")
        if isinstance(source, str) and source in out:
            out[source].append(edge)

    entry = next(
        (nid for nid, n in by_id.items() if n.get("type") == NODE_TRIGGER), None
    )
    return GraphIndex(nodes=by_id, out_edges=out, entry_node_id=entry)


def _successors(index: GraphIndex, node_id: str) -> list[str]:
    """Target ids of a node's outgoing edges, in declaration order."""
    targets = []
    for edge in index.out_edges.get(node_id, []):
        target = edge.get("target")
        if isinstance(target, str) and target in index.nodes:
            targets.append(target)
    return targets


def _reachable(index: GraphIndex) -> set[str]:
    """Every node reachable from the trigger."""
    if index.entry_node_id is None:
        return set()
    seen = {index.entry_node_id}
    stack = [index.entry_node_id]
    while stack:
        for target in _successors(index, stack.pop()):
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def _cycles_without_wait(index: GraphIndex) -> list[list[str]]:
    """Cycles containing no wait node.

    A loop *with* a wait is a legitimate drip pattern — "check in every week
    until they buy". A loop without one is a tight spin: the worker would
    re-run the same nodes as fast as it can dequeue them. Those are rejected at
    publish time rather than being left to the step ceiling at runtime.

    Iterative Tarjan-style DFS; the graphs are small (tens of nodes) but a
    recursive walk would still be a stack risk on hand-crafted input.
    """
    found: list[list[str]] = []
    colour: dict[str, int] = {}  # 0 unvisited, 1 on stack, 2 done
    parent: dict[str, Optional[str]] = {}

    for root in index.nodes:
        if colour.get(root, 0) != 0:
            continue
        stack: list[tuple[str, int]] = [(root, 0)]
        parent[root] = None
        while stack:
            node_id, child_ix = stack[-1]
            if child_ix == 0:
                colour[node_id] = 1
            children = _successors(index, node_id)
            if child_ix < len(children):
                stack[-1] = (node_id, child_ix + 1)
                child = children[child_ix]
                state = colour.get(child, 0)
                if state == 0:
                    parent[child] = node_id
                    stack.append((child, 0))
                elif state == 1:
                    # Back edge: rebuild the cycle from node_id up to child.
                    cycle = [child]
                    walk: Optional[str] = node_id
                    while walk is not None and walk != child:
                        cycle.append(walk)
                        walk = parent.get(walk)
                    cycle.reverse()
                    if not any(
                        index.nodes[c].get("type") == NODE_WAIT
                        for c in cycle
                        if c in index.nodes
                    ):
                        found.append(cycle)
            else:
                colour[node_id] = 2
                stack.pop()
    return found


# ---------------------------------------------------------------------------
# Validation — run before a version is published
# ---------------------------------------------------------------------------


def validate_graph(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> list[str]:
    """Return every reason this graph cannot be activated.

    Empty list means publishable. Called by ``POST /{id}/activate``, which
    today flips status on any graph at all — including an empty one.
    """
    errors: list[str] = []
    nodes = nodes or []
    edges = edges or []

    if not nodes:
        return ["Sequence has no nodes."]

    # -- ids ---------------------------------------------------------------
    ids = [n.get("id") for n in nodes]
    if any(not isinstance(i, str) or not i for i in ids):
        errors.append("Every node needs a non-empty string id.")
    duplicates = {i for i in ids if isinstance(i, str) and ids.count(i) > 1}
    for dup in sorted(duplicates):
        errors.append(f"Duplicate node id: {dup}")

    index = index_graph(nodes, edges)

    # -- node types --------------------------------------------------------
    for node_id, node in index.nodes.items():
        node_type = node.get("type")
        if node_type not in KNOWN_NODE_TYPES:
            errors.append(f"Node {node_id} has unknown type {node_type!r}.")

    # -- exactly one trigger ----------------------------------------------
    triggers = [nid for nid, n in index.nodes.items() if n.get("type") == NODE_TRIGGER]
    if not triggers:
        errors.append("Sequence needs a trigger node.")
    elif len(triggers) > 1:
        errors.append(
            f"Sequence has {len(triggers)} trigger nodes; exactly one is allowed."
        )

    # -- edges resolve -----------------------------------------------------
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source not in index.nodes:
            errors.append(f"Edge {edge.get('id')} starts at unknown node {source!r}.")
        if target not in index.nodes:
            errors.append(f"Edge {edge.get('id')} ends at unknown node {target!r}.")

    # -- reachability ------------------------------------------------------
    reachable = _reachable(index)
    for node_id in sorted(set(index.nodes) - reachable):
        errors.append(f"Node {node_id} is not reachable from the trigger.")

    # -- per-type shape ----------------------------------------------------
    for node_id, node in index.nodes.items():
        node_type = node.get("type")
        successors = _successors(index, node_id)
        data = node.get("data") or {}

        if node_type == NODE_END:
            if successors:
                errors.append(f"End node {node_id} must not have outgoing steps.")
            continue

        if node_type == NODE_CONDITION:
            if len(successors) not in (1, 2):
                errors.append(
                    f"Condition node {node_id} needs one or two outgoing steps, "
                    f"has {len(successors)}."
                )
            condition = data.get("condition")
            if condition not in KNOWN_CONDITIONS:
                errors.append(
                    f"Condition node {node_id} has unknown condition {condition!r}."
                )
            elif condition in THRESHOLD_CONDITIONS and _threshold(data) is None:
                # Caught here so it can never reach the worker, where an
                # unevaluable condition can only fail the enrollment.
                errors.append(
                    f"Condition node {node_id} uses {condition} but has no "
                    f"numeric threshold."
                )
            continue

        if node_type == NODE_WAIT:
            explicit = explicit_delay_seconds(data)
            if explicit is not None and explicit <= 0:
                errors.append(f"Wait node {node_id} needs a positive delay.")

        if node_type in KNOWN_NODE_TYPES and not successors:
            errors.append(
                f"Node {node_id} ({node_type}) has no outgoing step and is not an "
                f"end node."
            )

    # -- tight loops -------------------------------------------------------
    for cycle in _cycles_without_wait(index):
        errors.append(
            "Loop with no wait step: " + " -> ".join(cycle) + ". Add a wait, or "
            "the sequence would run without pause."
        )

    # Stable order, no duplicates, so the API response is deterministic.
    return sorted(dict.fromkeys(errors))


# ---------------------------------------------------------------------------
# Node data helpers
# ---------------------------------------------------------------------------


_DELAY_KEYS = (
    ("delay_seconds", 1),
    ("delay_minutes", 60),
    ("delay_hours", 3600),
    ("delay_days", 86400),
)


def explicit_delay_seconds(data: dict[str, Any]) -> Optional[int]:
    """The delay the author actually wrote, including zero and negatives.

    Returns ``None`` only when no delay key is present or none of them parse as
    a number. Kept separate from :func:`_delay_seconds` so validation can tell
    "the author asked for no wait" (an error) from "no delay was specified"
    (fall back to the builder's own default). Collapsing the two is how
    ``delay_hours=0`` came to mean "wait a day".

    Accepts hours (what the builder emits), plus seconds, minutes and days, so
    a graph authored through the API rather than the UI still works.
    """
    for key, multiplier in _DELAY_KEYS:
        raw = data.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        return int(value * multiplier)
    return None


def _delay_seconds(data: dict[str, Any]) -> int:
    """Seconds a wait node parks for at runtime.

    A non-positive or unusable delay falls back to the builder's default rather
    than firing immediately: a wait node that does not wait turns a drip into a
    burst, which is worse than being a day late. Publishing such a graph is
    blocked by :func:`validate_graph`, so this is the belt to that braces.
    """
    explicit = explicit_delay_seconds(data)
    if explicit is not None and explicit > 0:
        return explicit
    return DEFAULT_WAIT_HOURS * 3600


def _threshold(data: dict[str, Any]) -> Optional[float]:
    """The numeric comparison value on a threshold condition, if usable."""
    for key in ("threshold", "value", "amount"):
        raw = data.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def evaluate_condition(
    node: dict[str, Any], context: ConditionContext
) -> tuple[Optional[bool], Optional[str]]:
    """Evaluate a condition node.

    Returns ``(result, error)``. ``error`` is set when the condition cannot be
    evaluated at all — an unknown condition, or a ROAS comparison with nothing
    to compare. Those fail the enrollment rather than quietly taking the false
    branch, which would look like a working sequence making a real decision.
    """
    data = node.get("data") or {}
    condition = data.get("condition")

    if condition == COND_EMAIL_OPENED:
        return context.email_opened, None
    if condition == COND_EMAIL_NOT_OPENED:
        return not context.email_opened, None
    if condition == COND_LINK_CLICKED:
        return context.link_clicked, None
    if condition == COND_LINK_NOT_CLICKED:
        return not context.link_clicked, None

    if condition in THRESHOLD_CONDITIONS:
        threshold = _threshold(data)
        if threshold is None:
            return None, f"Condition {condition} has no numeric threshold."
        if context.roas is None:
            return None, f"Condition {condition} needs a ROAS value; none available."
        if condition == COND_ROAS_ABOVE:
            return context.roas > threshold, None
        return context.roas < threshold, None

    return None, f"Unknown condition {condition!r}."


def _branch_target(index: GraphIndex, node_id: str, take_true: bool) -> Optional[str]:
    """Pick a condition node's outgoing edge.

    Labels win when present. The builder does not set them today, so the
    fallback is declaration order: first edge is true, second is false. A
    single outgoing edge means both branches converge, which is legal.
    """
    edges = index.out_edges.get(node_id, [])
    valid = [e for e in edges if e.get("target") in index.nodes]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0].get("target")

    wanted = TRUE_LABELS if take_true else FALSE_LABELS
    for edge in valid:
        label = (edge.get("label") or "").strip().lower()
        if label in wanted:
            return edge.get("target")

    return valid[0 if take_true else 1].get("target")


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------


def step(
    index: GraphIndex,
    current_node_id: Optional[str],
    context: Optional[ConditionContext] = None,
) -> StepResult:
    """Decide what executing ``current_node_id`` means and where to go next.

    The caller performs ``result.action``, then stores ``result.next_node_id``
    and parks for ``result.wait_seconds``. A result with ``terminal`` set ends
    the enrollment; a result with ``error`` set fails it.
    """
    context = context or ConditionContext()

    node = index.node(current_node_id)
    if node is None:
        return StepResult(
            action=ACTION_NONE,
            node=None,
            next_node_id=None,
            error=(
                f"Node {current_node_id!r} is not in this sequence version. The "
                f"graph it was published from may have been replaced."
            ),
        )

    node_type = node.get("type")
    successors = _successors(index, current_node_id or "")
    first = successors[0] if successors else None

    # -- end ---------------------------------------------------------------
    if node_type == NODE_END:
        return StepResult(
            action=ACTION_NONE, node=node, next_node_id=None, terminal=True
        )

    # -- condition ---------------------------------------------------------
    if node_type == NODE_CONDITION:
        result, error = evaluate_condition(node, context)
        if error is not None:
            return StepResult(
                action=ACTION_NONE, node=node, next_node_id=None, error=error
            )
        target = _branch_target(index, current_node_id or "", bool(result))
        if target is None:
            return StepResult(
                action=ACTION_NONE,
                node=node,
                next_node_id=None,
                error=f"Condition node {current_node_id} has no usable branch.",
            )
        return StepResult(action=ACTION_NONE, node=node, next_node_id=target)

    # -- everything else needs somewhere to go ----------------------------
    if first is None:
        return StepResult(
            action=ACTION_NONE,
            node=node,
            next_node_id=None,
            error=(
                f"Node {current_node_id} ({node_type}) has no outgoing step and is "
                f"not an end node."
            ),
        )

    if node_type == NODE_TRIGGER:
        return StepResult(action=ACTION_NONE, node=node, next_node_id=first)

    if node_type == NODE_WAIT:
        return StepResult(
            action=ACTION_NONE,
            node=node,
            next_node_id=first,
            wait_seconds=_delay_seconds(node.get("data") or {}),
        )

    if node_type == NODE_EMAIL:
        return StepResult(action=ACTION_SEND_EMAIL, node=node, next_node_id=first)

    if node_type == NODE_NOTIFICATION:
        return StepResult(action=ACTION_NOTIFY, node=node, next_node_id=first)

    return StepResult(
        action=ACTION_NONE,
        node=node,
        next_node_id=None,
        error=f"Node {current_node_id} has unknown type {node_type!r}.",
    )
