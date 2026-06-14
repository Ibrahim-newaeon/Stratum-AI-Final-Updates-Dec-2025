# =============================================================================
# Stratum AI - Attribution Models (Shapley + Markov) Unit Tests
# =============================================================================
"""Unit tests for the pure, deterministic attribution models embedded in
``app.services.attribution.attribution_service``:

- ``ShapleyAttributionModel`` — game-theoretic fair attribution where the
  caller supplies the conversion function (subset generation, conversion
  caching, and Shapley-value computation)
- ``MarkovAttributionModel.get_attribution_weights`` — the unfitted
  equal-weights fallback path

The stochastic ``MarkovAttributionModel.fit`` (10k-walk simulation) is out
of scope here.
"""

import pytest

from app.services.attribution.attribution_service import (
    MarkovAttributionModel,
    ShapleyAttributionModel,
)

pytestmark = pytest.mark.unit


# =============================================================================
# ShapleyAttributionModel._get_subsets
# =============================================================================
class TestGetSubsets:
    @pytest.fixture
    def model(self) -> ShapleyAttributionModel:
        return ShapleyAttributionModel()

    def test_size_zero_is_empty_subset(self, model):
        assert model._get_subsets(["a", "b"], 0) == [[]]

    def test_size_larger_than_items_is_empty(self, model):
        assert model._get_subsets(["a"], 2) == []

    def test_pairs(self, model):
        assert model._get_subsets(["a", "b", "c"], 2) == [
            ["a", "b"],
            ["a", "c"],
            ["b", "c"],
        ]

    def test_singletons(self, model):
        assert model._get_subsets(["a", "b", "c"], 1) == [["a"], ["b"], ["c"]]


# =============================================================================
# ShapleyAttributionModel._get_cached_conversion
# =============================================================================
class TestConversionCache:
    def test_caches_per_channel_set(self):
        model = ShapleyAttributionModel()
        calls = []

        def conv(channel_set):
            calls.append(frozenset(channel_set))
            return float(len(channel_set))

        key = frozenset({"a", "b"})
        assert model._get_cached_conversion(key, conv) == 2.0
        assert model._get_cached_conversion(key, conv) == 2.0
        # Second lookup is served from cache — conv invoked exactly once.
        assert len(calls) == 1


# =============================================================================
# ShapleyAttributionModel.compute_shapley_values
# =============================================================================
class TestComputeShapleyValues:
    @pytest.fixture
    def model(self) -> ShapleyAttributionModel:
        return ShapleyAttributionModel()

    def test_empty_channels(self, model):
        assert model.compute_shapley_values([], lambda s: 0.0) == {}

    def test_single_channel_gets_all_credit(self, model):
        values = model.compute_shapley_values(["A"], lambda s: 1.0 if "A" in s else 0.0)
        assert values == {"A": 1.0}

    def test_symmetric_channels_split_evenly(self, model):
        # Conversion only happens when BOTH channels are present -> fair 50/50.
        values = model.compute_shapley_values(
            ["A", "B"], lambda s: 1.0 if len(s) == 2 else 0.0
        )
        assert values["A"] == pytest.approx(0.5)
        assert values["B"] == pytest.approx(0.5)

    def test_dominant_channel_takes_all(self, model):
        # Conversion depends only on A -> B contributes nothing.
        values = model.compute_shapley_values(
            ["A", "B"], lambda s: 1.0 if "A" in s else 0.0
        )
        assert values["A"] == pytest.approx(1.0)
        assert values["B"] == pytest.approx(0.0)

    def test_values_sum_to_one(self, model):
        values = model.compute_shapley_values(["A", "B", "C"], lambda s: 0.3 * len(s))
        assert sum(values.values()) == pytest.approx(1.0)


# =============================================================================
# MarkovAttributionModel.get_attribution_weights (unfitted)
# =============================================================================
class TestMarkovUnfittedWeights:
    def test_equal_weights_when_unfitted(self):
        model = MarkovAttributionModel()
        weights = model.get_attribution_weights(["email", "ads", "social"])
        assert weights == {
            "email": pytest.approx(1 / 3),
            "ads": pytest.approx(1 / 3),
            "social": pytest.approx(1 / 3),
        }

    def test_empty_channels(self):
        model = MarkovAttributionModel()
        assert model.get_attribution_weights([]) == {}
