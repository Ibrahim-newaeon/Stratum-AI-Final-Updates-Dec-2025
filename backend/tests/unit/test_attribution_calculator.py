# =============================================================================
# Stratum AI - Attribution Calculator Unit Tests
# =============================================================================
"""Unit tests for the pure attribution-weight math in
``app.services.attribution.attribution_service``:

- ``AttributionCalculator`` model weights (first/last/linear/position/
  time-decay/w-shaped/custom) + the ``get_weights`` dispatcher
- ``get_platform_attribution_config`` window lookup

All calculators are pure staticmethods returning weights that sum to 1.0;
the DB-backed ``AttributionService`` is out of scope here.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.crm import AttributionModel
from app.services.attribution.attribution_service import (
    AttributionCalculator,
    get_platform_attribution_config,
)

pytestmark = pytest.mark.unit


def _sums_to_one(weights):
    return sum(weights) == pytest.approx(1.0)


# =============================================================================
# Single-model calculators
# =============================================================================
class TestFirstLastLinear:
    def test_first_touch(self):
        w = AttributionCalculator.first_touch(4)
        assert w == [1.0, 0.0, 0.0, 0.0]

    def test_last_touch(self):
        w = AttributionCalculator.last_touch(4)
        assert w == [0.0, 0.0, 0.0, 1.0]

    def test_linear(self):
        w = AttributionCalculator.linear(4)
        assert w == [0.25, 0.25, 0.25, 0.25]
        assert _sums_to_one(w)

    @pytest.mark.parametrize("fn", ["first_touch", "last_touch", "linear"])
    def test_empty_is_empty(self, fn):
        assert getattr(AttributionCalculator, fn)(0) == []


class TestPositionBased:
    def test_single(self):
        assert AttributionCalculator.position_based(1) == [1.0]

    def test_two(self):
        assert AttributionCalculator.position_based(2) == [0.5, 0.5]

    def test_u_shape_endpoints_and_middle(self):
        w = AttributionCalculator.position_based(4)
        assert w[0] == pytest.approx(0.4)
        assert w[-1] == pytest.approx(0.4)
        # Remaining 20% split across the 2 middle touchpoints.
        assert w[1] == pytest.approx(0.1)
        assert w[2] == pytest.approx(0.1)
        assert _sums_to_one(w)


class TestWShaped:
    def test_three_touch_even_split(self):
        assert AttributionCalculator.w_shaped(3) == [0.333, 0.334, 0.333]

    def test_endpoints_and_lead_creation(self):
        w = AttributionCalculator.w_shaped(5)
        assert w[0] == pytest.approx(0.3)
        assert w[-1] == pytest.approx(0.3)
        # Default lead-creation index is the middle (5 // 2 == 2).
        assert w[2] == pytest.approx(0.3)
        assert _sums_to_one(w)

    def test_explicit_lead_creation_index(self):
        w = AttributionCalculator.w_shaped(5, lead_creation_index=1)
        assert w[1] == pytest.approx(0.3)
        assert _sums_to_one(w)


class TestTimeDecay:
    def test_single_touch(self):
        assert AttributionCalculator.time_decay(1) == [1.0]

    def test_geometric_when_no_timestamps(self):
        w = AttributionCalculator.time_decay(3)
        # raw 1,2,4 -> /7
        assert w == pytest.approx([1 / 7, 2 / 7, 4 / 7])
        assert _sums_to_one(w)
        # More recent touchpoints get strictly more credit.
        assert w[0] < w[1] < w[2]

    def test_timestamp_based_recency_bias(self):
        conv = datetime(2026, 6, 10, tzinfo=timezone.utc)
        times = [conv - timedelta(days=14), conv - timedelta(days=0)]
        w = AttributionCalculator.time_decay(
            2, half_life_days=7.0, touchpoint_times=times, conversion_time=conv
        )
        assert _sums_to_one(w)
        # The touchpoint at conversion time outweighs the 14-day-old one.
        assert w[1] > w[0]

    def test_zero_total_falls_back_to_linear(self):
        # Degenerate timestamps that would decay to ~0 still normalize safely.
        conv = datetime(2026, 6, 10, tzinfo=timezone.utc)
        w = AttributionCalculator.time_decay(
            2,
            half_life_days=7.0,
            touchpoint_times=[conv, conv],
            conversion_time=conv,
        )
        assert _sums_to_one(w)


class TestCustom:
    def test_normalizes(self):
        assert AttributionCalculator.custom([1, 1, 2]) == pytest.approx(
            [0.25, 0.25, 0.5]
        )

    def test_empty(self):
        assert AttributionCalculator.custom([]) == []

    def test_all_zero_falls_back_to_linear(self):
        assert AttributionCalculator.custom([0, 0]) == [0.5, 0.5]


# =============================================================================
# get_weights dispatcher
# =============================================================================
class TestGetWeights:
    @pytest.mark.parametrize(
        "model,expected",
        [
            (AttributionModel.FIRST_TOUCH, [1.0, 0.0, 0.0]),
            (AttributionModel.LAST_TOUCH, [0.0, 0.0, 1.0]),
            (AttributionModel.LINEAR, [1 / 3, 1 / 3, 1 / 3]),
        ],
    )
    def test_dispatch_simple_models(self, model, expected):
        assert AttributionCalculator.get_weights(model, 3) == pytest.approx(expected)

    def test_dispatch_position_based(self):
        w = AttributionCalculator.get_weights(AttributionModel.POSITION_BASED, 2)
        assert w == [0.5, 0.5]

    def test_dispatch_time_decay(self):
        w = AttributionCalculator.get_weights(AttributionModel.TIME_DECAY, 3)
        assert _sums_to_one(w)


# =============================================================================
# Platform window config
# =============================================================================
class TestPlatformConfig:
    def test_known_platform(self):
        cfg = get_platform_attribution_config("google")
        assert cfg["click_window"] == 30
        assert cfg["max_lookback"] == 90

    def test_case_insensitive(self):
        assert get_platform_attribution_config("META") == (
            get_platform_attribution_config("meta")
        )

    def test_unknown_falls_back_to_default(self):
        assert get_platform_attribution_config("myspace") == (
            get_platform_attribution_config("default")
        )

    def test_none_uses_default(self):
        cfg = get_platform_attribution_config(None)
        assert cfg["click_window"] == 7
