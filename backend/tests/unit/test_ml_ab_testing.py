# =============================================================================
# Stratum AI - Model A/B Testing service unit tests
# =============================================================================
"""Unit tests for app.ml.ab_testing.

In-memory model A/B-test orchestration, no I/O. Covers ExperimentMetrics
accumulation, experiment lifecycle (create/start/stop), deterministic
hash-based traffic splitting, active-variant lookup, and prediction recording.
"""

import pytest

from app.ml.ab_testing import (
    ExperimentMetrics,
    ExperimentStatus,
    ModelABTestingService,
    ModelVariant,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> ModelABTestingService:
    return ModelABTestingService()


# =============================================================================
# ExperimentMetrics
# =============================================================================
class TestExperimentMetrics:
    def test_prediction_without_actual(self):
        m = ExperimentMetrics(variant=ModelVariant.CHAMPION)
        m.add_prediction(10.0)
        assert m.predictions_count == 1
        assert m.actuals_collected == 0
        assert m.mae == 0.0

    def test_mae_and_rmse(self):
        m = ExperimentMetrics(variant=ModelVariant.CHAMPION)
        m.add_prediction(10.0, 8.0)  # error 2
        m.add_prediction(10.0, 12.0)  # error -2
        assert m.actuals_collected == 2
        assert m.mae == pytest.approx(2.0)
        assert m.rmse == pytest.approx(2.0)  # sqrt((4+4)/2)


# =============================================================================
# Lifecycle
# =============================================================================
class TestLifecycle:
    def test_create_is_draft(self, service):
        exp = service.create_experiment("t", "roas_predictor", "2.0", "2.1")
        assert exp.status == ExperimentStatus.DRAFT
        assert exp.experiment_id in service._experiments

    def test_start_moves_to_running(self, service):
        exp = service.create_experiment("t", "m", "1", "2")
        assert service.start_experiment(exp.experiment_id) is True
        assert exp.status == ExperimentStatus.RUNNING

    def test_start_unknown_returns_false(self, service):
        assert service.start_experiment("nope") is False

    def test_start_non_draft_returns_false(self, service):
        exp = service.create_experiment("t", "m", "1", "2")
        service.start_experiment(exp.experiment_id)
        # already running -> cannot start again
        assert service.start_experiment(exp.experiment_id) is False

    def test_starting_second_stops_first_on_same_model(self, service):
        # IDs embed a second-precision timestamp, so force distinct ids to
        # avoid same-second collisions when both target the same model.
        a = service.create_experiment("a", "shared", "1", "2")
        service._experiments.pop(a.experiment_id, None)
        a.experiment_id = "exp_shared_a"
        service._experiments["exp_shared_a"] = a

        b = service.create_experiment("b", "shared", "1", "3")
        service._experiments.pop(b.experiment_id, None)
        b.experiment_id = "exp_shared_b"
        service._experiments["exp_shared_b"] = b

        service.start_experiment("exp_shared_a")
        service.start_experiment("exp_shared_b")  # should stop a
        assert a.status == ExperimentStatus.PAUSED
        assert service._active_experiments["shared"] == "exp_shared_b"

    def test_stop_sets_status_and_clears_active(self, service):
        exp = service.create_experiment("t", "m", "1", "2")
        service.start_experiment(exp.experiment_id)
        assert service.stop_experiment(exp.experiment_id) is True
        assert exp.status == ExperimentStatus.PAUSED
        assert "m" not in service._active_experiments


# =============================================================================
# Traffic splitting
# =============================================================================
class TestVariantAssignment:
    def test_not_running_returns_champion(self, service):
        exp = service.create_experiment("t", "m", "1", "2")  # DRAFT
        assert service.get_variant(exp.experiment_id, "e1") == ModelVariant.CHAMPION

    def test_deterministic_assignment(self, service):
        exp = service.create_experiment("t", "m", "1", "2", traffic_split=0.5)
        service.start_experiment(exp.experiment_id)
        v1 = service.get_variant(exp.experiment_id, "entity_42")
        v2 = service.get_variant(exp.experiment_id, "entity_42")
        assert v1 == v2

    def test_full_split_always_challenger(self, service):
        exp = service.create_experiment("t", "m", "1", "2", traffic_split=1.0)
        service.start_experiment(exp.experiment_id)
        assert (
            service.get_variant(exp.experiment_id, "anything")
            == ModelVariant.CHALLENGER
        )

    def test_zero_split_always_champion(self, service):
        exp = service.create_experiment("t", "m", "1", "2", traffic_split=0.0)
        service.start_experiment(exp.experiment_id)
        assert (
            service.get_variant(exp.experiment_id, "anything") == ModelVariant.CHAMPION
        )

    def test_active_variant_lookup(self, service):
        # no active experiment for this model
        variant, exp_id = service.get_active_variant("ghost_model", "e")
        assert variant == ModelVariant.CHAMPION
        assert exp_id is None
        # with a running experiment
        exp = service.create_experiment("t", "live_model", "1", "2", traffic_split=1.0)
        service.start_experiment(exp.experiment_id)
        variant, exp_id = service.get_active_variant("live_model", "e")
        assert exp_id == exp.experiment_id
        assert variant == ModelVariant.CHALLENGER


# =============================================================================
# Prediction recording
# =============================================================================
class TestRecording:
    def test_record_routes_to_correct_variant(self, service):
        exp = service.create_experiment("t", "m", "1", "2", traffic_split=0.5)
        service.start_experiment(exp.experiment_id)
        service.record_prediction(exp.experiment_id, ModelVariant.CHAMPION, 2.5, 2.0)
        service.record_prediction(exp.experiment_id, ModelVariant.CHALLENGER, 3.0, 3.0)
        assert exp.champion_metrics.predictions_count == 1
        assert exp.champion_metrics.mae == pytest.approx(0.5)
        assert exp.challenger_metrics.predictions_count == 1

    def test_record_unknown_experiment_is_noop(self, service):
        # must not raise
        service.record_prediction("nope", ModelVariant.CHAMPION, 1.0, 1.0)
