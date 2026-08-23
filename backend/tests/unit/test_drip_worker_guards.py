# =============================================================================
# Stratum AI - Drip Worker Guards
# =============================================================================
"""The checks ``advance_drip_enrollment`` makes before it touches anything.

Each one exists because the alternative is a duplicate or an unwanted send:

* a duplicate dispatch must not run a step twice
* an archived sequence must stop mailing immediately, not at the end
* an unsubscribe must take effect at the very next step, not at the next send
* a graph that loops must terminate, not spin

The session is mocked rather than real. These are ordering and precedence
rules — which check runs before which — and a real database would test
SQLAlchemy rather than the decision.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.drip import (
    ENROLLMENT_ACTIVE,
    ENROLLMENT_CANCELLED,
    ENROLLMENT_COMPLETED,
    ENROLLMENT_FAILED,
    ENROLLMENT_WAITING,
    MAX_ENROLLMENT_STEPS,
)


def make_enrollment(**overrides):
    enrollment = SimpleNamespace(
        id="enroll_1",
        tenant_id=1,
        sequence_id="drip_1",
        version_id="dripv_1",
        status=ENROLLMENT_ACTIVE,
        current_node_id="t1",
        next_due_at=None,
        steps_completed=0,
        attempt_count=0,
        claimed_at=None,
        claimed_by=None,
        profile_id=None,
        recipient_hash="a" * 64,
        recipient_email="person@example.com",
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        cancel_reason=None,
        last_error=None,
    )
    for key, value in overrides.items():
        setattr(enrollment, key, value)
    return enrollment


def make_sequence(status="active"):
    return SimpleNamespace(
        id="drip_1",
        tenant_id=1,
        status=status,
        entry_count=1,
        active_recipient_count=0,
        completion_rate=0.0,
    )


def make_version(nodes=None, edges=None):
    return SimpleNamespace(
        id="dripv_1",
        entry_node_id="t1",
        nodes=nodes
        if nodes is not None
        else [
            {"id": "t1", "type": "trigger", "data": {}},
            {"id": "w1", "type": "wait", "data": {"delay_hours": 6}},
            {"id": "x1", "type": "end", "data": {}},
        ],
        edges=edges
        if edges is not None
        else [
            {"id": "e1", "source": "t1", "target": "w1"},
            {"id": "e2", "source": "w1", "target": "x1"},
        ],
    )


class Harness:
    """Minimal stand-in for the session the task opens."""

    def __init__(self, enrollment, sequence=None, version=None):
        self.enrollment = enrollment
        self.sequence = sequence if sequence is not None else make_sequence()
        self.version = version if version is not None else make_version()
        self.committed = 0
        self.suppressed = False

        self.db = MagicMock()
        self.db.commit.side_effect = self._commit
        self.db.close = MagicMock()
        self.db.rollback = MagicMock()
        self.db.get.side_effect = self._get
        self.db.execute.side_effect = self._execute

    def _commit(self):
        self.committed += 1

    def _get(self, model, key):
        name = getattr(model, "__name__", "")
        if name == "DripSequence":
            return self.sequence
        if name == "DripSequenceVersion":
            return self.version
        return None

    def _execute(self, *_args, **_kwargs):
        result = MagicMock()
        result.scalar_one_or_none.return_value = self.enrollment
        result.first.return_value = None
        result.scalar.return_value = None
        return result

    def run(self):
        from app.workers import drip_tasks

        with (
            patch("app.db.session.SyncSessionLocal", return_value=self.db),
            patch.object(
                drip_tasks, "_condition_context", return_value=_empty_context()
            ),
            patch(
                "app.services.drip.enrollment.is_suppressed_sync",
                return_value=self.suppressed,
            ),
            # No broker in a unit test. Chaining a zero-wait step is a real
            # dispatch, so it is captured rather than attempted.
            patch.object(
                drip_tasks.advance_drip_enrollment, "apply_async"
            ) as self.chained,
        ):
            return drip_tasks.advance_drip_enrollment.run("enroll_1")


def _empty_context():
    from app.services.drip.interpreter import ConditionContext

    return ConditionContext()


# ---------------------------------------------------------------------------


class TestClaimGuard:
    def test_refuses_an_enrollment_it_does_not_hold(self):
        """A duplicate dispatch must not run the step a second time.

        The sweep sets `active` when it claims. Anything else means another
        worker already finished it, or it was cancelled in between.
        """
        harness = Harness(make_enrollment(status=ENROLLMENT_WAITING))
        assert harness.run()["status"] == "not_claimed"
        assert harness.committed == 0

    @pytest.mark.parametrize(
        "status", [ENROLLMENT_COMPLETED, ENROLLMENT_CANCELLED, ENROLLMENT_FAILED]
    )
    def test_refuses_terminal_enrollments(self, status):
        harness = Harness(make_enrollment(status=status))
        assert harness.run()["status"] == "not_claimed"

    def test_handles_a_deleted_enrollment(self):
        harness = Harness(None)
        assert harness.run()["status"] == "gone"


class TestSequenceGates:
    def test_archived_sequence_cancels_the_enrollment(self):
        harness = Harness(make_enrollment(), sequence=make_sequence("archived"))
        result = harness.run()
        assert result["status"] == "cancelled"
        assert result["reason"] == "sequence_archived"
        assert harness.enrollment.status == ENROLLMENT_CANCELLED

    def test_paused_sequence_parks_rather_than_abandons(self):
        """Pause means "no new steps", not "throw these people away"."""
        harness = Harness(make_enrollment(), sequence=make_sequence("paused"))
        assert harness.run()["status"] == "paused"
        assert harness.enrollment.status == ENROLLMENT_WAITING
        assert harness.enrollment.next_due_at is not None

    def test_missing_version_fails_the_enrollment(self):
        harness = Harness(make_enrollment())
        harness.version = None
        result = harness.run()
        assert result["status"] == ENROLLMENT_FAILED


class TestConsentIsRecheckedEveryStep:
    def test_unsubscribe_mid_sequence_cancels_at_the_next_step(self):
        """Checked per step, not only at enrollment — someone can opt out on
        day 2 of a fourteen-day sequence, and the rest must stop."""
        harness = Harness(make_enrollment())
        harness.suppressed = True
        result = harness.run()
        assert result["status"] == "cancelled"
        assert result["reason"] == "unsubscribed"

    def test_consent_is_checked_before_the_step_runs(self):
        harness = Harness(make_enrollment())
        harness.suppressed = True
        harness.run()
        # Nothing advanced: the enrollment never moved off the trigger node.
        assert harness.enrollment.steps_completed == 0


class TestLoopCeiling:
    def test_enrollment_past_the_ceiling_fails(self):
        harness = Harness(make_enrollment(steps_completed=MAX_ENROLLMENT_STEPS))
        result = harness.run()
        assert result["status"] == ENROLLMENT_FAILED
        assert "loops" in harness.enrollment.last_error

    def test_just_below_the_ceiling_still_runs(self):
        harness = Harness(make_enrollment(steps_completed=MAX_ENROLLMENT_STEPS - 1))
        assert harness.run()["status"] != ENROLLMENT_FAILED


class TestHappyPath:
    def test_trigger_advances_to_the_next_node(self):
        harness = Harness(make_enrollment())
        result = harness.run()
        assert result["status"] == ENROLLMENT_WAITING
        assert harness.enrollment.current_node_id == "w1"
        assert harness.enrollment.steps_completed == 1
        assert harness.enrollment.started_at is not None

    def test_wait_node_parks_for_its_delay(self):
        harness = Harness(make_enrollment(current_node_id="w1", steps_completed=1))
        result = harness.run()
        assert result["wait_seconds"] == 6 * 3600
        assert harness.enrollment.current_node_id == "x1"

    def test_end_node_completes(self):
        harness = Harness(make_enrollment(current_node_id="x1", steps_completed=2))
        result = harness.run()
        assert result["status"] == ENROLLMENT_COMPLETED
        assert harness.enrollment.completed_at is not None
        assert harness.enrollment.next_due_at is None

    def test_claim_is_released_on_every_outcome(self):
        # A claim left behind would keep the row out of the due index until the
        # stale sweep noticed it.
        harness = Harness(make_enrollment(claimed_by="sweep-1"))
        harness.run()
        assert harness.enrollment.claimed_by is None
        assert harness.enrollment.claimed_at is None

    def test_zero_wait_step_chains_itself(self):
        """Otherwise a trigger -> email run waits for the next five-minute
        sweep before sending anything."""
        harness = Harness(make_enrollment())
        harness.run()
        harness.chained.assert_called_once()

    def test_a_wait_step_does_not_chain(self):
        harness = Harness(make_enrollment(current_node_id="w1", steps_completed=1))
        harness.run()
        harness.chained.assert_not_called()

    def test_a_broker_failure_does_not_fail_a_committed_step(self):
        """The step already succeeded and the row is due now — the sweep will
        pick it up. Raising here would fail work that actually happened."""
        harness = Harness(make_enrollment())
        from app.workers import drip_tasks

        with (
            patch("app.db.session.SyncSessionLocal", return_value=harness.db),
            patch.object(
                drip_tasks, "_condition_context", return_value=_empty_context()
            ),
            patch(
                "app.services.drip.enrollment.is_suppressed_sync", return_value=False
            ),
            patch.object(
                drip_tasks.advance_drip_enrollment,
                "apply_async",
                side_effect=ConnectionError("broker down"),
            ),
        ):
            result = drip_tasks.advance_drip_enrollment.run("enroll_1")

        assert result["status"] == ENROLLMENT_WAITING
        assert harness.enrollment.current_node_id == "w1"


class TestBrokenGraph:
    def test_node_missing_from_the_pinned_version_fails(self):
        harness = Harness(make_enrollment(current_node_id="ghost"))
        result = harness.run()
        assert result["status"] == ENROLLMENT_FAILED
        assert "not in this sequence version" in harness.enrollment.last_error

    def test_dead_end_fails_rather_than_completing(self):
        """Silently completing would report a sequence that finished when it
        was actually broken."""
        version = make_version(
            nodes=[
                {"id": "t1", "type": "trigger", "data": {}},
                {"id": "e1", "type": "email", "data": {}},
            ],
            edges=[{"id": "x", "source": "t1", "target": "e1"}],
        )
        harness = Harness(make_enrollment(current_node_id="e1"), version=version)
        result = harness.run()
        assert result["status"] == ENROLLMENT_FAILED
