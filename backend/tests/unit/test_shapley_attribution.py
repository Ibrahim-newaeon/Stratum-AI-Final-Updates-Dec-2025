# =============================================================================
# Stratum AI - Shapley Attribution Unit Tests
# =============================================================================
"""Unit tests for ``ShapleyValueModel`` in
app.services.attribution.shapley_attribution — pure Shapley-value math.

The DB-backed ShapleyAttributionService is out of scope here.
"""

import pytest

from app.services.attribution.shapley_attribution import ShapleyValueModel

pytestmark = pytest.mark.unit


class TestEmptyModel:
    def test_no_journeys(self):
        model = ShapleyValueModel()
        assert model.calculate_shapley_values() == {}
        assert model.calculate_attribution_weights() == {}
        stats = model.get_model_stats()
        assert stats["journey_count"] == 0
        assert stats["conversion_rate"] == 0

    def test_empty_channels_is_noop(self):
        model = ShapleyValueModel()
        model.add_journey([], converted=True)
        assert model.get_model_stats()["journey_count"] == 0


class TestSingleChannel:
    def test_single_channel_gets_full_weight(self):
        model = ShapleyValueModel()
        for _ in range(5):
            model.add_journey(["email"], converted=True)

        weights = model.calculate_attribution_weights()
        assert set(weights) == {"email"}
        assert weights["email"] == pytest.approx(1.0)


class TestMultiChannel:
    def _model(self) -> ShapleyValueModel:
        model = ShapleyValueModel()
        # Mix of coalitions and outcomes across two channels.
        model.add_journey(["email", "ads"], converted=True)
        model.add_journey(["email"], converted=True)
        model.add_journey(["ads"], converted=False)
        model.add_journey(["email", "ads"], converted=False)
        return model

    def test_weights_normalize_to_one(self):
        weights = self._model().calculate_attribution_weights()
        assert set(weights) == {"email", "ads"}
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(w >= 0 for w in weights.values())

    def test_stats(self):
        model = self._model()
        stats = model.get_model_stats()
        assert stats["journey_count"] == 4
        assert stats["converting_journeys"] == 2
        assert stats["conversion_rate"] == pytest.approx(0.5)
        assert stats["unique_channels"] == 2
        assert set(stats["channels"]) == {"email", "ads"}

    def test_to_dict_is_serializable(self):
        model = self._model()
        d = model.to_dict()
        assert isinstance(d, dict)
