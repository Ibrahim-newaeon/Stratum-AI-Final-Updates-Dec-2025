# =============================================================================
# Stratum AI - Celery Beat Registration Tests
# =============================================================================
"""Guard against beat-schedule entries that dispatch to nothing.

When ``app/workers/tasks.py`` was split into a package, the auto-generated
task names gained a submodule segment (``app.workers.tasks.rules.evaluate_all_rules``)
while the beat schedule kept the old flat names. Celery does not fail on
this: beat happily sends the message every interval and the worker logs an
"unregistered task" error, so five periodic pipelines were silently dead.
This test imports everything the worker would and asserts each beat entry
resolves to a registered task.
"""

import importlib

import pytest


@pytest.fixture(scope="module")
def finalized_celery_app():
    """The Celery app with all task modules imported, as a worker would."""
    from app.workers.celery_app import celery_app

    for module in celery_app.conf.include:
        importlib.import_module(module)
    celery_app.finalize()
    return celery_app


def test_beat_schedule_tasks_are_registered(finalized_celery_app):
    """Every beat schedule entry must reference a registered task name."""
    registered = set(finalized_celery_app.tasks.keys())

    missing = {
        entry_name: entry["task"]
        for entry_name, entry in finalized_celery_app.conf.beat_schedule.items()
        if entry["task"] not in registered
    }

    assert not missing, (
        "Beat schedule entries reference unregistered task names "
        f"(worker will log 'unregistered task' and drop them): {missing}"
    )


def test_autopilot_execution_tasks_are_registered(finalized_celery_app):
    """The autopilot execution pipeline tasks must stay registered."""
    registered = set(finalized_celery_app.tasks.keys())

    for name in (
        "tasks.apply_actions_queue",
        "tasks.apply_single_action",
        "tasks.schedule_apply_actions_queue",
    ):
        assert name in registered, f"{name} is not registered with the Celery app"


def test_signal_health_rollup_tasks_are_registered(finalized_celery_app):
    """The Trust Engine signal-health rollup tasks must stay registered.

    These populate FactSignalHealthDaily — the table the trust gate, the
    dashboard trust layer, and the autopilot execution-path health check
    all read. They sat unregistered (module missing from the Celery
    include list) from their creation until 2026-07-02.
    """
    registered = set(finalized_celery_app.tasks.keys())

    for name in (
        "tasks.signal_health_rollup",
        "tasks.schedule_signal_health_rollup",
    ):
        assert name in registered, f"{name} is not registered with the Celery app"
