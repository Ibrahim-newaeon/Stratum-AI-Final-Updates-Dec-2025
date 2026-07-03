# =============================================================================
# Stratum AI - RFM Segmenter extended unit tests
# =============================================================================
"""Extended unit tests for ``app.ml.rfm_segmenter`` (issue #342, batch 3).

Complements ``test_rfm_segmenter.py`` (RFMSegmenter fit/score basics) with:

- ``_get_segment`` rules-fallback elif ladder for triples absent from
  ``SEGMENT_MAPPING``
- ``get_segment_customers`` / ``get_high_value_at_risk`` auto-fit + filters
- ``segment_customers`` zero-revenue value-share branch, sort order, and
  quintile threshold reporting
- Module-level convenience functions ``segment_customers_rfm`` and
  ``get_customer_rfm_score`` (the latter uses the module-global, unfitted
  singleton -> default score of 3 on every dimension)
- ``SegmentTransitionTracker`` snapshot/transition/matrix/risk/campaign logic
- ``CLVPredictor`` CLV projection, confidence tiers, and segment summaries

Everything here is pure numpy/dataclass logic -- no I/O, no DB.
"""

from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from app.ml.rfm_segmenter import (
    CLVPredictor,
    CustomerRFMData,
    RFMScore,
    RFMSegment,
    RFMSegmenter,
    SegmentTransition,
    SegmentTransitionTracker,
    get_customer_rfm_score,
    segment_customers_rfm,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers
# =============================================================================


def _spread_customers() -> List[CustomerRFMData]:
    """Customers spanning the recency/frequency/monetary range."""
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


def _score(
    customer_id: str,
    segment: RFMSegment,
    composite: float = 3.0,
    rfm: str = "333",
) -> RFMScore:
    """Build a minimal RFMScore pinned to a given segment."""
    return RFMScore(
        customer_id=customer_id,
        recency_days=30,
        frequency=5,
        monetary=100.0,
        recency_score=int(rfm[0]),
        frequency_score=int(rfm[1]),
        monetary_score=int(rfm[2]),
        rfm_score=rfm,
        rfm_segment=segment,
        rfm_composite=composite,
        percentile_rank=50.0,
    )


def _dt(day: int, month: int = 1, year: int = 2026) -> datetime:
    """Timezone-aware datetime shorthand."""
    return datetime(year, month, day, tzinfo=timezone.utc)


# =============================================================================
# _get_segment fallback elif ladder
# =============================================================================


class TestGetSegmentFallback:
    """Triples deliberately absent from SEGMENT_MAPPING to force the rules."""

    @pytest.mark.parametrize(
        "r,f,m,expected",
        [
            # r>=4 and (f>=3 or m>=4) -> LOYAL (not mapped: (4,3,4))
            (4, 3, 4, RFMSegment.LOYAL_CUSTOMERS),
            # A first-order but high-monetary customer falls to LOYAL via
            # the m>=4 arm -- the dedicated NEW_CUSTOMERS fallback below it
            # (r == 5 and f == 1) is unreachable because every r >= 4 value
            # is consumed by the earlier r>=4 branches. Documented behavior.
            (5, 1, 4, RFMSegment.LOYAL_CUSTOMERS),
            # r>=4 only -> POTENTIAL (not mapped: (4,2,2))
            (4, 2, 2, RFMSegment.POTENTIAL_LOYALISTS),
            # r<=2 and f>=4 -> CANT_LOSE (not mapped: (2,4,1))
            (2, 4, 1, RFMSegment.CANT_LOSE),
            # r<=2 and f>=3 -> AT_RISK (not mapped: (2,3,1))
            (2, 3, 1, RFMSegment.AT_RISK),
            # r<=2 and avg<2 -> LOST (not mapped: (1,1,3) avg=1.67)
            (1, 1, 3, RFMSegment.LOST),
            # r<=2, avg>=2 -> HIBERNATING (not mapped: (2,2,3) avg=2.33)
            (2, 2, 3, RFMSegment.HIBERNATING),
            # r==3, avg>=3 -> NEED_ATTENTION (not mapped: (3,4,4))
            (3, 4, 4, RFMSegment.NEED_ATTENTION),
            # r==3, avg<3 -> ABOUT_TO_SLEEP (not mapped: (3,2,1) avg=2)
            (3, 2, 1, RFMSegment.ABOUT_TO_SLEEP),
        ],
    )
    def test_fallback_rules(self, r: int, f: int, m: int, expected: RFMSegment) -> None:
        seg = RFMSegmenter()
        assert (r, f, m) not in RFMSegmenter.SEGMENT_MAPPING
        assert seg._get_segment(r, f, m) is expected

    def test_fallback_champions_requires_out_of_range_scores(self) -> None:
        """Every in-range {4,5}^3 triple is in SEGMENT_MAPPING, so the
        CHAMPIONS fallback rule only fires for out-of-range scores."""
        seg = RFMSegmenter()
        in_range = [(r, f, m) for r in (4, 5) for f in (4, 5) for m in (4, 5)]
        assert all(t in RFMSegmenter.SEGMENT_MAPPING for t in in_range)
        assert seg._get_segment(6, 5, 5) is RFMSegment.CHAMPIONS

    def test_exact_mapping_still_wins(self) -> None:
        seg = RFMSegmenter()
        assert seg._get_segment(5, 5, 5) is RFMSegment.CHAMPIONS
        assert seg._get_segment(1, 1, 1) is RFMSegment.LOST


# =============================================================================
# get_segment_customers / get_high_value_at_risk
# =============================================================================


class TestSegmentFilters:
    def test_get_segment_customers_auto_fits_and_filters(self) -> None:
        seg = RFMSegmenter()
        customers = _spread_customers()
        champions = seg.get_segment_customers(customers, RFMSegment.CHAMPIONS)

        assert seg._is_fitted is True
        assert [s.customer_id for s in champions] == ["champ"]
        assert all(s.rfm_segment is RFMSegment.CHAMPIONS for s in champions)

    def test_get_segment_customers_empty_segment(self) -> None:
        seg = RFMSegmenter()
        assert (
            seg.get_segment_customers(_spread_customers(), RFMSegment.PROMISING) == []
        )

    def test_get_segment_customers_skips_refit_when_fitted(self) -> None:
        seg = RFMSegmenter()
        customers = _spread_customers()
        seg.fit(customers)
        quintiles = list(seg.recency_quintiles)
        # A second call with different data must not recalibrate.
        seg.get_segment_customers(customers[:2], RFMSegment.CHAMPIONS)
        assert seg.recency_quintiles == quintiles

    def test_get_high_value_at_risk_skips_refit_when_fitted(self) -> None:
        seg = RFMSegmenter()
        customers = _spread_customers()
        seg.fit(customers)
        quintiles = list(seg.monetary_quintiles)
        seg.get_high_value_at_risk(customers[:2])
        assert seg.monetary_quintiles == quintiles

    def test_get_high_value_at_risk_auto_fits(self) -> None:
        seg = RFMSegmenter()
        customers = _spread_customers() + [
            # High frequency/monetary but ancient recency -> churn risk.
            CustomerRFMData(
                "whale",
                days_since_last_order=400,
                total_orders=50,
                total_revenue=5000.0,
            )
        ]
        at_risk = seg.get_high_value_at_risk(customers)
        at_risk_segments = {
            RFMSegment.AT_RISK,
            RFMSegment.CANT_LOSE,
            RFMSegment.ABOUT_TO_SLEEP,
        }

        assert seg._is_fitted is True
        assert len(at_risk) >= 1
        assert all(s.rfm_segment in at_risk_segments for s in at_risk)
        assert "whale" in {s.customer_id for s in at_risk}


# =============================================================================
# segment_customers extras
# =============================================================================


class TestSegmentCustomersExtras:
    def test_zero_revenue_value_share_branch(self) -> None:
        seg = RFMSegmenter()
        customers = [
            CustomerRFMData(
                f"c{i}",
                days_since_last_order=i * 10,
                total_orders=i + 1,
                total_revenue=0.0,
            )
            for i in range(4)
        ]

        result = seg.segment_customers(customers)

        assert result["total_revenue"] == 0.0
        for insight in result["segments"].values():
            assert insight["value_share_percent"] == 0

    def test_segments_sorted_by_total_value_desc(self) -> None:
        seg = RFMSegmenter()
        result = seg.segment_customers(_spread_customers())
        totals = [s["total_value"] for s in result["segments"].values()]
        assert totals == sorted(totals, reverse=True)

    def test_quintile_thresholds_reported(self) -> None:
        seg = RFMSegmenter()
        result = seg.segment_customers(_spread_customers())
        thresholds = result["quintile_thresholds"]
        assert len(thresholds["recency_days"]) == 4
        assert len(thresholds["frequency"]) == 4
        assert len(thresholds["monetary"]) == 4
        assert result["segment_count"] == len(result["segments"])

    def test_no_auto_fit_when_disabled(self) -> None:
        seg = RFMSegmenter()
        result = seg.segment_customers(_spread_customers(), auto_fit=False)
        # Unfitted -> every dimension scores 3 -> single NEED_ATTENTION bucket.
        assert seg._is_fitted is False
        assert list(result["segments"].keys()) == [RFMSegment.NEED_ATTENTION.value]


# =============================================================================
# Module-level convenience functions
# =============================================================================


class TestConvenienceFunctions:
    def test_segment_customers_rfm_with_full_dicts(self) -> None:
        customers = [
            {
                "customer_id": "a",
                "days_since_last_order": 5,
                "total_orders": 20,
                "total_revenue": 2000.0,
            },
            {
                "customer_id": "b",
                "days_since_last_order": 200,
                "total_orders": 1,
                "total_revenue": 20.0,
            },
        ]
        result = segment_customers_rfm(customers)
        assert result["total_customers"] == 2
        assert result["total_revenue"] == 2020.0

    def test_segment_customers_rfm_missing_key_defaults(self) -> None:
        # Only customer_id is required; the rest default to 0/1/0.
        result = segment_customers_rfm([{"customer_id": "bare"}])
        assert result["total_customers"] == 1
        assert result["total_revenue"] == 0.0

    def test_get_customer_rfm_score_uses_unfitted_singleton(self) -> None:
        """The module-global singleton is never fitted here, so every
        dimension scores the default 3 -> "333" -> NEED_ATTENTION."""
        result = get_customer_rfm_score(
            customer_id="solo",
            days_since_last_order=10,
            total_orders=5,
            total_revenue=500.0,
        )
        assert result["customer_id"] == "solo"
        assert result["rfm_score"] == "333"
        assert result["segment"] == RFMSegment.NEED_ATTENTION.value
        assert result["scores"] == {"recency": 3, "frequency": 3, "monetary": 3}
        assert result["composite_score"] == pytest.approx(3.0)
        assert result["percentile_rank"] == pytest.approx(50.0)
        assert "recommended_action" in result


# =============================================================================
# SegmentTransitionTracker
# =============================================================================


class TestSegmentTransitionTracker:
    def test_first_snapshot_records_history_without_transitions(self) -> None:
        tracker = SegmentTransitionTracker()
        transitions = tracker.record_snapshot(
            _dt(1), [_score("c1", RFMSegment.LOYAL_CUSTOMERS)]
        )
        assert transitions == []
        assert tracker.customer_segment_history["c1"] == [
            (_dt(1), RFMSegment.LOYAL_CUSTOMERS)
        ]

    def test_segment_change_detected_with_days_elapsed(self) -> None:
        tracker = SegmentTransitionTracker()
        tracker.record_snapshot(_dt(1), [_score("c1", RFMSegment.LOYAL_CUSTOMERS)])
        transitions = tracker.record_snapshot(
            _dt(8), [_score("c1", RFMSegment.CHAMPIONS)]
        )

        assert len(transitions) == 1
        t = transitions[0]
        assert t.from_segment is RFMSegment.LOYAL_CUSTOMERS
        assert t.to_segment is RFMSegment.CHAMPIONS
        assert t.days_in_previous_segment == 7
        assert tracker.transition_history == transitions

    def test_same_segment_is_not_a_transition(self) -> None:
        tracker = SegmentTransitionTracker()
        tracker.record_snapshot(_dt(1), [_score("c1", RFMSegment.CHAMPIONS)])
        transitions = tracker.record_snapshot(
            _dt(8), [_score("c1", RFMSegment.CHAMPIONS)]
        )
        assert transitions == []
        assert len(tracker.customer_segment_history["c1"]) == 2

    def test_transition_matrix_counts(self) -> None:
        tracker = SegmentTransitionTracker()
        tracker.record_snapshot(
            _dt(1),
            [
                _score("c1", RFMSegment.LOYAL_CUSTOMERS),
                _score("c2", RFMSegment.LOYAL_CUSTOMERS),
            ],
        )
        tracker.record_snapshot(
            _dt(8),
            [
                _score("c1", RFMSegment.AT_RISK),
                _score("c2", RFMSegment.CHAMPIONS),
            ],
        )

        matrix = tracker.get_transition_matrix()
        loyal = RFMSegment.LOYAL_CUSTOMERS.value
        assert matrix[loyal][RFMSegment.AT_RISK.value] == 1
        assert matrix[loyal][RFMSegment.CHAMPIONS.value] == 1
        # Every segment pair is present, untouched cells are zero.
        assert matrix[RFMSegment.LOST.value][RFMSegment.CHAMPIONS.value] == 0
        assert set(matrix) == {s.value for s in RFMSegment}

    def test_transition_probabilities_including_zero_total(self) -> None:
        tracker = SegmentTransitionTracker()
        tracker.record_snapshot(
            _dt(1),
            [
                _score("c1", RFMSegment.LOYAL_CUSTOMERS),
                _score("c2", RFMSegment.LOYAL_CUSTOMERS),
                _score("c3", RFMSegment.LOYAL_CUSTOMERS),
            ],
        )
        tracker.record_snapshot(
            _dt(8),
            [
                _score("c1", RFMSegment.AT_RISK),
                _score("c2", RFMSegment.AT_RISK),
                _score("c3", RFMSegment.CHAMPIONS),
            ],
        )

        probs = tracker.get_transition_probabilities()
        loyal = probs[RFMSegment.LOYAL_CUSTOMERS.value]
        assert loyal[RFMSegment.AT_RISK.value] == pytest.approx(2 / 3)
        assert loyal[RFMSegment.CHAMPIONS.value] == pytest.approx(1 / 3)
        assert sum(loyal.values()) == pytest.approx(1.0)
        # Zero-total rows fall to the all-zero branch.
        lost_row = probs[RFMSegment.LOST.value]
        assert all(v == 0 for v in lost_row.values())

    def test_get_at_risk_customers_threshold_and_sort(self) -> None:
        tracker = SegmentTransitionTracker()
        # LOYAL -> AT_RISK twice (negative), LOYAL -> CHAMPIONS once (positive)
        # => negative probability 2/3 for LOYAL residents.
        tracker.record_snapshot(
            _dt(1),
            [
                _score("c1", RFMSegment.LOYAL_CUSTOMERS),
                _score("c2", RFMSegment.LOYAL_CUSTOMERS),
                _score("c3", RFMSegment.LOYAL_CUSTOMERS),
                _score("c4", RFMSegment.CANT_LOSE),
            ],
        )
        tracker.record_snapshot(
            _dt(8),
            [
                _score("c1", RFMSegment.AT_RISK),
                _score("c2", RFMSegment.AT_RISK),
                _score("c3", RFMSegment.CHAMPIONS),
                # CANT_LOSE -> LOST is a negative transition with prob 1.0.
                _score("c4", RFMSegment.LOST),
            ],
        )

        current = [
            _score("loyal-now", RFMSegment.LOYAL_CUSTOMERS),
            _score("cantlose-now", RFMSegment.CANT_LOSE),
            # CHAMPIONS row has no history -> risk 0 -> below threshold.
            _score("champ-now", RFMSegment.CHAMPIONS),
        ]
        at_risk = tracker.get_at_risk_customers(current)

        assert [c["customer_id"] for c in at_risk] == ["cantlose-now", "loyal-now"]
        assert at_risk[0]["churn_risk"] == pytest.approx(1.0)
        assert at_risk[1]["churn_risk"] == pytest.approx(0.67)
        assert at_risk[0]["current_segment"] == RFMSegment.CANT_LOSE.value
        assert all("recommended_action" in c for c in at_risk)

    def test_analyze_campaign_impact_sentiment_buckets(self) -> None:
        tracker = SegmentTransitionTracker()

        def _transition(
            to_segment: RFMSegment,
            day: int,
            from_segment: RFMSegment = RFMSegment.AT_RISK,
        ) -> SegmentTransition:
            return SegmentTransition(
                customer_id="c",
                from_segment=from_segment,
                to_segment=to_segment,
                transition_date=_dt(day),
                days_in_previous_segment=7,
                monetary_change=0,
                frequency_change=0,
            )

        tracker.transition_history = [
            _transition(RFMSegment.NEED_ATTENTION, 5),  # positive
            _transition(RFMSegment.CANT_LOSE, 6),  # negative
            _transition(RFMSegment.LOST, 7),  # unmapped pair -> neutral
            _transition(
                RFMSegment.NEED_ATTENTION, 5, RFMSegment.CHAMPIONS
            ),  # wrong from
            _transition(RFMSegment.NEED_ATTENTION, 15, RFMSegment.AT_RISK),  # in window
        ]
        # Push one transition outside the campaign window.
        tracker.transition_history.append(
            SegmentTransition(
                customer_id="late",
                from_segment=RFMSegment.AT_RISK,
                to_segment=RFMSegment.NEED_ATTENTION,
                transition_date=_dt(1, month=3),
                days_in_previous_segment=7,
                monetary_change=0,
                frequency_change=0,
            )
        )

        result = tracker.analyze_campaign_impact(
            campaign_start=_dt(1),
            campaign_end=_dt(31),
            target_segment=RFMSegment.AT_RISK,
        )

        assert result["target_segment"] == RFMSegment.AT_RISK.value
        assert result["total_transitions"] == 4
        assert result["positive_transitions"] == 2
        assert result["negative_transitions"] == 1
        assert result["neutral_transitions"] == 1
        assert result["net_positive_rate"] == pytest.approx(0.25)

    def test_analyze_campaign_impact_empty_window(self) -> None:
        tracker = SegmentTransitionTracker()
        result = tracker.analyze_campaign_impact(
            campaign_start=_dt(1),
            campaign_end=_dt(31),
            target_segment=RFMSegment.LOST,
        )
        assert result["total_transitions"] == 0
        assert result["net_positive_rate"] == 0


# =============================================================================
# CLVPredictor
# =============================================================================


class TestCLVPredictor:
    def test_predict_clv_defaults_without_first_order_date(self) -> None:
        """No first_order_date -> months_as_customer defaults to 12."""
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c1", days_since_last_order=5, total_orders=12, total_revenue=1200.0
        )
        score = _score("c1", RFMSegment.CHAMPIONS, composite=4.8, rfm="555")

        clv = predictor.predict_clv(customer, score)

        assert clv.customer_id == "c1"
        assert clv.rfm_segment is RFMSegment.CHAMPIONS
        assert clv.historical_value == 1200.0
        # avg_monthly = 1200 / 12 = 100; CHAMPIONS multiplier 1.5.
        assert clv.monthly_expected_value == pytest.approx(150.0)
        assert clv.predicted_clv > 0
        # CHAMPIONS retention 0.95 -> expected lifetime int(1 / 0.05).
        assert clv.expected_lifetime_months == int(1 / (1 - 0.95))
        assert clv.acquisition_cost is None
        assert clv.clv_to_cac_ratio is None

    def test_predict_clv_with_first_order_date_uses_recency_months(self) -> None:
        """first_order_date present -> months = max(1, days_since_last_order/30)."""
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c2",
            days_since_last_order=60,
            total_orders=4,
            total_revenue=600.0,
            first_order_date=datetime.now(timezone.utc) - timedelta(days=200),
        )
        score = _score("c2", RFMSegment.NEED_ATTENTION)

        clv = predictor.predict_clv(customer, score)

        # months = 60 / 30 = 2 -> avg_monthly 300; multiplier 0.9.
        assert clv.monthly_expected_value == pytest.approx(270.0)

    def test_predict_clv_cac_ratio(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c3", days_since_last_order=5, total_orders=10, total_revenue=1000.0
        )
        score = _score("c3", RFMSegment.LOYAL_CUSTOMERS, composite=4.2, rfm="544")

        clv = predictor.predict_clv(customer, score, acquisition_cost=100.0)

        assert clv.acquisition_cost == 100.0
        assert clv.clv_to_cac_ratio == pytest.approx(
            round((1000.0 + clv.predicted_clv) / 100.0, 2)
        )

    def test_predict_clv_zero_acquisition_cost_skips_ratio(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c4", days_since_last_order=5, total_orders=1, total_revenue=50.0
        )
        clv = predictor.predict_clv(
            customer, _score("c4", RFMSegment.NEW_CUSTOMERS), acquisition_cost=0.0
        )
        assert clv.clv_to_cac_ratio is None

    def test_expected_lifetime_guard_retention_one(self, monkeypatch) -> None:
        """retention == 1.0 skips the geometric-lifetime formula."""
        predictor = CLVPredictor(prediction_horizon_months=24)
        monkeypatch.setitem(CLVPredictor.SEGMENT_RETENTION_RATES, RFMSegment.LOST, 1.0)
        customer = CustomerRFMData(
            "c5", days_since_last_order=400, total_orders=1, total_revenue=10.0
        )
        clv = predictor.predict_clv(customer, _score("c5", RFMSegment.LOST))
        assert clv.expected_lifetime_months == 24

    def test_expected_lifetime_guard_retention_zero(self, monkeypatch) -> None:
        """retention == 0.0 also falls back to the horizon; CLV is zero."""
        predictor = CLVPredictor(prediction_horizon_months=24)
        monkeypatch.setitem(CLVPredictor.SEGMENT_RETENTION_RATES, RFMSegment.LOST, 0.0)
        customer = CustomerRFMData(
            "c6", days_since_last_order=400, total_orders=1, total_revenue=10.0
        )
        clv = predictor.predict_clv(customer, _score("c6", RFMSegment.LOST))
        assert clv.expected_lifetime_months == 24
        assert clv.predicted_clv == 0

    # -------------------------------------------------------------------------
    # _calculate_confidence
    # -------------------------------------------------------------------------

    def test_confidence_base_case(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c", days_since_last_order=5, total_orders=1, total_revenue=10.0
        )
        assert predictor._calculate_confidence(
            customer, _score("c", RFMSegment.NEW_CUSTOMERS, composite=2.0)
        ) == pytest.approx(0.5)

    def test_confidence_mid_order_tier(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c", days_since_last_order=5, total_orders=5, total_revenue=100.0
        )
        assert predictor._calculate_confidence(
            customer, _score("c", RFMSegment.NEED_ATTENTION, composite=3.0)
        ) == pytest.approx(0.6)

    def test_confidence_short_history_adds_nothing(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c",
            days_since_last_order=5,
            total_orders=1,
            total_revenue=10.0,
            first_order_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        assert predictor._calculate_confidence(
            customer, _score("c", RFMSegment.NEW_CUSTOMERS, composite=2.0)
        ) == pytest.approx(0.5)

    def test_confidence_mid_history_tier(self) -> None:
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c",
            days_since_last_order=5,
            total_orders=1,
            total_revenue=10.0,
            first_order_date=datetime.now(timezone.utc) - timedelta(days=200),
        )
        assert predictor._calculate_confidence(
            customer, _score("c", RFMSegment.NEW_CUSTOMERS, composite=2.0)
        ) == pytest.approx(0.6)

    def test_confidence_all_tiers_capped_at_095(self) -> None:
        """0.5 + 0.2 (orders) + 0.15 (1y+ history) + 0.1 (composite) caps."""
        predictor = CLVPredictor()
        customer = CustomerRFMData(
            "c",
            days_since_last_order=5,
            total_orders=25,
            total_revenue=5000.0,
            first_order_date=datetime.now(timezone.utc) - timedelta(days=400),
        )
        assert predictor._calculate_confidence(
            customer, _score("c", RFMSegment.CHAMPIONS, composite=4.5, rfm="555")
        ) == pytest.approx(0.95)

    # -------------------------------------------------------------------------
    # segment_clv_summary
    # -------------------------------------------------------------------------

    def test_segment_clv_summary_aggregates_by_segment(self) -> None:
        predictor = CLVPredictor()
        customers = [
            CustomerRFMData(
                "a", days_since_last_order=5, total_orders=20, total_revenue=2000.0
            ),
            CustomerRFMData(
                "b", days_since_last_order=5, total_orders=15, total_revenue=1500.0
            ),
            CustomerRFMData(
                "z", days_since_last_order=400, total_orders=1, total_revenue=10.0
            ),
        ]
        scores = [
            _score("a", RFMSegment.CHAMPIONS, composite=4.8, rfm="555"),
            _score("b", RFMSegment.CHAMPIONS, composite=4.5, rfm="554"),
            _score("z", RFMSegment.LOST, composite=1.0, rfm="111"),
        ]

        summary = predictor.segment_clv_summary(customers, scores)

        champs = summary["segments"][RFMSegment.CHAMPIONS.value]
        lost = summary["segments"][RFMSegment.LOST.value]
        assert champs["customer_count"] == 2
        assert champs["total_historical_value"] == pytest.approx(3500.0)
        assert champs["avg_predicted_clv"] == pytest.approx(
            champs["total_predicted_clv"] / 2, abs=0.01
        )
        assert lost["customer_count"] == 1
        assert summary["total_portfolio_clv"] == pytest.approx(
            champs["total_portfolio_value"] + lost["total_portfolio_value"], abs=0.01
        )
