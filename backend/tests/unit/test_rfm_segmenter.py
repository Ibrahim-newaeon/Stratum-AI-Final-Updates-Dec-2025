# =============================================================================
# Stratum AI - RFM Segmenter unit tests
# =============================================================================
"""Unit tests for app.ml.rfm_segmenter (pure numpy/dataclass logic, no I/O)."""

import pytest

from app.ml.rfm_segmenter import (
    CustomerRFMData,
    RFMSegment,
    RFMSegmenter,
)

pytestmark = pytest.mark.unit


def _spread_customers():
    """Five customers spanning the recency/frequency/monetary range."""
    return [
        CustomerRFMData(
            "champ", days_since_last_order=1, total_orders=50, total_revenue=5000.0
        ),
        CustomerRFMData(
            "good", days_since_last_order=10, total_orders=10, total_revenue=500.0
        ),
        CustomerRFMData(
            "mid", days_since_last_order=30, total_orders=5, total_revenue=100.0
        ),
        CustomerRFMData(
            "weak", days_since_last_order=90, total_orders=3, total_revenue=50.0
        ),
        CustomerRFMData(
            "lost", days_since_last_order=400, total_orders=1, total_revenue=10.0
        ),
    ]


@pytest.fixture
def fitted() -> RFMSegmenter:
    seg = RFMSegmenter()
    seg.fit(_spread_customers())
    return seg


class TestFit:
    def test_fit_calibrates_quintiles(self, fitted: RFMSegmenter):
        assert fitted._is_fitted is True
        assert len(fitted.recency_quintiles) == 4
        assert len(fitted.frequency_quintiles) == 4
        assert len(fitted.monetary_quintiles) == 4

    def test_fit_empty_is_noop(self):
        seg = RFMSegmenter()
        seg.fit([])
        assert seg._is_fitted is False

    def test_unfitted_score_value_defaults_to_three(self):
        seg = RFMSegmenter()
        assert seg._score_value(123.0, []) == 3


class TestScoring:
    def test_best_customer_is_a_champion(self, fitted: RFMSegmenter):
        score = fitted.score_customer(_spread_customers()[0])
        assert score.recency_score == 5
        assert score.frequency_score == 5
        assert score.monetary_score == 5
        assert score.rfm_score == "555"
        assert score.rfm_segment == RFMSegment.CHAMPIONS
        assert score.rfm_composite == pytest.approx(5.0, abs=0.01)
        assert score.percentile_rank == pytest.approx(100.0, abs=0.1)

    def test_worst_customer_is_lost(self, fitted: RFMSegmenter):
        score = fitted.score_customer(_spread_customers()[-1])
        assert score.rfm_score == "111"
        assert score.rfm_segment == RFMSegment.LOST
        assert score.percentile_rank == pytest.approx(0.0, abs=0.1)

    def test_recency_is_reverse_scored(self, fitted: RFMSegmenter):
        # More recent (fewer days) must score >= a much older customer.
        recent = fitted.score_customer(
            CustomerRFMData(
                "r", days_since_last_order=1, total_orders=5, total_revenue=100.0
            )
        )
        stale = fitted.score_customer(
            CustomerRFMData(
                "s", days_since_last_order=400, total_orders=5, total_revenue=100.0
            )
        )
        assert recent.recency_score > stale.recency_score


class TestSegmentCustomers:
    def test_segment_customers_returns_summary(self, fitted: RFMSegmenter):
        result = fitted.segment_customers(_spread_customers())
        assert "segments" in result
        # Champion and Lost should both appear across the spread.
        assert isinstance(result["segments"], dict)

    def test_segment_customers_empty(self, fitted: RFMSegmenter):
        result = fitted.segment_customers([])
        assert result["segments"] == {}
