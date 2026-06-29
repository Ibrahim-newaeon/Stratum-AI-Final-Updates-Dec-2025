# =============================================================================
# Stratum AI - Markov Attribution Unit Tests
# =============================================================================
"""Unit tests for ``MarkovChainModel`` in
app.services.attribution.markov_attribution — pure removal-effect math.

The DB-backed MarkovAttributionService is out of scope here.
"""

import pytest

from app.services.attribution.markov_attribution import MarkovChainModel

pytestmark = pytest.mark.unit


class TestEmptyModel:
    def test_no_journeys(self):
        model = MarkovChainModel()
        assert model.calculate_attribution_weights() == {}
        stats = model.get_model_stats()
        assert stats["journey_count"] == 0

    def test_empty_channels_is_noop(self):
        model = MarkovChainModel()
        model.add_journey([], converted=True)
        assert model.get_model_stats()["journey_count"] == 0


class TestTransitions:
    def test_probabilities_in_unit_range(self):
        model = MarkovChainModel()
        model.add_journey(["email", "ads"], converted=True)
        model.add_journey(["email"], converted=False)
        matrix = model.get_transition_matrix()
        for _from, targets in matrix.items():
            for _to, p in targets.items():
                assert 0.0 <= p <= 1.0

    def test_unknown_transition_is_zero(self):
        model = MarkovChainModel()
        model.add_journey(["email"], converted=True)
        assert model.get_transition_probability("nonexistent", "other") == 0.0


class TestAttributionWeights:
    def _model(self) -> MarkovChainModel:
        model = MarkovChainModel()
        model.add_journey(["email", "ads"], converted=True)
        model.add_journey(["email"], converted=True)
        model.add_journey(["ads"], converted=False)
        model.add_journey(["email", "social"], converted=True)
        return model

    def test_weights_normalize_to_one(self):
        weights = self._model().calculate_attribution_weights()
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(w >= 0 for w in weights.values())

    def test_stats(self):
        model = self._model()
        stats = model.get_model_stats()
        assert stats["journey_count"] == 4
        assert stats["converting_journeys"] == 3
        assert stats["conversion_rate"] == pytest.approx(0.75)

    def test_to_dict_is_serializable(self):
        assert isinstance(self._model().to_dict(), dict)
