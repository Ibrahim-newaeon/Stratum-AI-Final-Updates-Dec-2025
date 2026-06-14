# =============================================================================
# Stratum AI - RFM Scoring Unit Tests
# =============================================================================
"""Unit tests for the pure RFM scoring logic in
``app.services.cdp.computed_traits_service.RFMAnalysisService``:

- ``_score_recency`` / ``_score_frequency`` / ``_score_monetary`` band math
- ``_determine_segment`` RFM-score → customer-segment mapping

These helpers never touch ``self.db``, so the service is instantiated with
``db=None``. The DB-backed batch RFM pipeline is out of scope here.
"""

import pytest

from app.services.cdp.computed_traits_service import RFMAnalysisService

pytestmark = pytest.mark.unit


@pytest.fixture
def rfm() -> RFMAnalysisService:
    return RFMAnalysisService(db=None, tenant_id=1)


# =============================================================================
# scoring bands
# =============================================================================
class TestRecency:
    @pytest.mark.parametrize(
        "days,score",
        [(0, 5), (7, 5), (8, 4), (30, 4), (31, 3), (90, 3), (180, 2), (181, 1)],
    )
    def test_recency_bands(self, rfm, days, score):
        assert rfm._score_recency(days) == score


class TestFrequency:
    @pytest.mark.parametrize(
        "count,score",
        [(0, 1), (1, 1), (2, 2), (5, 3), (10, 4), (20, 5), (100, 5)],
    )
    def test_frequency_bands(self, rfm, count, score):
        assert rfm._score_frequency(count) == score


class TestMonetary:
    @pytest.mark.parametrize(
        "amount,score",
        [(0.0, 1), (49.99, 1), (50, 2), (200, 3), (500, 4), (1000, 5), (5000, 5)],
    )
    def test_monetary_bands(self, rfm, amount, score):
        assert rfm._score_monetary(amount) == score


# =============================================================================
# segment mapping
# =============================================================================
class TestDetermineSegment:
    @pytest.mark.parametrize(
        "r,f,m,segment",
        [
            (5, 5, 5, "champions"),
            (4, 4, 4, "champions"),
            (3, 5, 3, "loyal_customers"),
            (4, 3, 5, "potential_loyalists"),
            (5, 1, 1, "new_customers"),
            (3, 2, 2, "promising"),
            (3, 3, 4, "need_attention"),
            (1, 3, 3, "about_to_sleep"),
            (2, 1, 5, "at_risk"),
            (2, 1, 1, "hibernating"),
            (3, 1, 1, "other"),
        ],
    )
    def test_segments(self, rfm, r, f, m, segment):
        assert rfm._determine_segment(r, f, m) == segment

    def test_returns_a_string_for_all_score_combinations(self, rfm):
        for r in range(1, 6):
            for f in range(1, 6):
                for m in range(1, 6):
                    assert isinstance(rfm._determine_segment(r, f, m), str)
