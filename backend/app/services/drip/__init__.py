# =============================================================================
# Stratum AI - Drip Campaign Services
# =============================================================================
"""Execution services for drip (email sequence) campaigns.

``interpreter`` walks a frozen flow graph and decides what happens next.
``enrollment`` puts recipients into a sequence and takes them back out.

Both are pure of Celery: the worker in ``app.workers.drip_tasks`` owns the
scheduling, and these own the decisions, so the decisions stay unit-testable
without a broker or a database.
"""

from app.services.drip.interpreter import (
    ACTION_NONE,
    ACTION_NOTIFY,
    ACTION_SEND_EMAIL,
    ConditionContext,
    GraphIndex,
    StepResult,
    index_graph,
    step,
    validate_graph,
)

__all__ = [
    "ACTION_NONE",
    "ACTION_NOTIFY",
    "ACTION_SEND_EMAIL",
    "ConditionContext",
    "GraphIndex",
    "StepResult",
    "index_graph",
    "step",
    "validate_graph",
]
