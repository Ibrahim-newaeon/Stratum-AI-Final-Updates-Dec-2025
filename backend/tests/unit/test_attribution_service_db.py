# =============================================================================
# Stratum AI - Attribution Service unit tests (DB paths + reconciliation)
# =============================================================================
"""Unit tests for ``app.services.attribution.attribution_service`` (issue
#342, batch 3).

The pure weight calculators (AttributionCalculator, Markov, Shapley,
platform config) are already covered by ``test_attribution_calculator.py``,
``test_markov_attribution.py``, ``test_shapley_attribution.py``, and
``test_attribution_models.py`` -- this file covers what they don't:

- ``AttributionService._calculate_confidence`` tiering
- ``attribute_deal`` / ``attribute_deal_with_platform_windows`` early
  returns, happy paths, window filtering, and the filter-everything fallback
- ``batch_attribute_deals`` success/failure/exception accounting
- ``compare_attribution_models``, ``get_campaign_attribution``,
  ``get_attribution_summary`` group_by matrix
- ``CrossPlatformAttributor`` claim reconciliation, over-claim rate,
  ``_get_actual_conversions`` row unpacking, and ``get_unified_attribution``
- ``AttributionCalculator.get_weights`` DATA_DRIVEN fallthrough (documents
  current behavior: falls back to last-touch)

DB access is a mocked ``AsyncSession`` fed side_effect result stubs in query
order; deals and touchpoints are writable ``SimpleNamespace`` stubs.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.crm import AttributionModel
from app.services.attribution.attribution_service import (
    AttributionCalculator,
    AttributionService,
    CrossPlatformAttributor,
    MarkovAttributionModel,
)

pytestmark = pytest.mark.unit

CONVERSION = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


# =============================================================================
# Helpers
# =============================================================================


def _make_db(execute_results: Optional[List[Any]] = None) -> MagicMock:
    """Mock AsyncSession: sync ``add``, async execute/commit/flush."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    if execute_results is None:
        db.execute = AsyncMock(return_value=MagicMock())
    else:
        db.execute = AsyncMock(side_effect=list(execute_results))
    return db


def _scalar(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def _scalars(items: List[Any]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _tp(
    days_before: float = 1.0,
    source: str = "meta",
    campaign_id: str = "camp-1",
    **overrides: Any,
) -> SimpleNamespace:
    """Writable Touchpoint stub, ``days_before`` relative to CONVERSION."""
    base = dict(
        id=uuid4(),
        contact_id=uuid4(),
        event_ts=CONVERSION - timedelta(days=days_before),
        source=source,
        campaign_id=campaign_id,
        campaign_name=f"Campaign {campaign_id}",
        adset_id="adset-1",
        adset_name="Adset 1",
        ad_id="ad-1",
        gclid=None,
        fbclid=None,
        ttclid=None,
        sclid=None,
        click_id=None,
        email_hash=None,
        phone_hash=None,
        visitor_id=None,
        ga_client_id=None,
        attribution_weight=None,
        is_converting_touch=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _deal(**overrides: Any) -> SimpleNamespace:
    """Writable CRMDeal stub."""
    base = dict(
        id=uuid4(),
        contact_id=uuid4(),
        amount=1000.0,
        won_at=CONVERSION,
        crm_updated_at=None,
        is_won=True,
        attributed_touchpoint_id=None,
        attributed_campaign_id=None,
        attributed_adset_id=None,
        attributed_ad_id=None,
        attributed_platform=None,
        attribution_model=None,
        attribution_confidence=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _service(results: Optional[List[Any]] = None) -> AttributionService:
    return AttributionService(db=_make_db(results), tenant_id=1)


# =============================================================================
# get_weights DATA_DRIVEN fallthrough (documents current behavior)
# =============================================================================


class TestGetWeightsDataDriven:
    def test_data_driven_falls_through_to_last_touch(self) -> None:
        """DATA_DRIVEN has no branch in get_weights -> last-touch default."""
        weights = AttributionCalculator.get_weights(
            AttributionModel.DATA_DRIVEN, touchpoint_count=4
        )
        assert weights == AttributionCalculator.last_touch(4)
        assert weights == [0.0, 0.0, 0.0, 1.0]


# =============================================================================
# _calculate_confidence
# =============================================================================


class TestCalculateConfidence:
    def test_empty_touchpoints(self) -> None:
        assert _service()._calculate_confidence([]) == 0.0

    def test_base_plus_touch_bonus_only(self) -> None:
        # 1 touchpoint, no identifiers: 0.5 + 0.05.
        assert _service()._calculate_confidence([_tp()]) == pytest.approx(0.55)

    def test_click_id_tier(self) -> None:
        tps = [_tp(gclid="g-1"), _tp()]
        # 0.5 + 2*0.05 + 0.3
        assert _service()._calculate_confidence(tps) == pytest.approx(0.9)

    def test_email_hash_tier(self) -> None:
        tps = [_tp(email_hash="abc")]
        assert _service()._calculate_confidence(tps) == pytest.approx(0.75)

    def test_visitor_id_tier(self) -> None:
        tps = [_tp(visitor_id="v-1")]
        assert _service()._calculate_confidence(tps) == pytest.approx(0.65)

    def test_click_beats_lower_tiers(self) -> None:
        tps = [_tp(visitor_id="v-1"), _tp(email_hash="e"), _tp(sclid="s-1")]
        # 0.5 + 0.15 + 0.3
        assert _service()._calculate_confidence(tps) == pytest.approx(0.95)

    def test_capped_at_one(self) -> None:
        tps = [_tp(fbclid="f") for _ in range(10)]
        # touch bonus caps at 0.2: min(1.0, 0.5 + 0.2 + 0.3).
        assert _service()._calculate_confidence(tps) == 1.0


# =============================================================================
# attribute_deal
# =============================================================================


class TestAttributeDeal:
    async def test_deal_not_found(self) -> None:
        service = _service([_scalar(None)])
        assert await service.attribute_deal(uuid4()) == {
            "success": False,
            "error": "deal_not_found",
        }

    async def test_no_contact_linked(self) -> None:
        service = _service([_scalar(_deal(contact_id=None))])
        assert (await service.attribute_deal(uuid4()))["error"] == "no_contact_linked"

    async def test_no_touchpoints(self) -> None:
        service = _service([_scalar(_deal()), _scalars([])])
        assert (await service.attribute_deal(uuid4()))["error"] == "no_touchpoints"

    async def test_last_touch_happy_path(self) -> None:
        deal = _deal(amount=1000.0)
        tps = [
            _tp(days_before=5.0, gclid="g"),
            _tp(days_before=3.0),
            _tp(days_before=1.0),
        ]
        db = _make_db([_scalar(deal), _scalars(tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal(deal.id, AttributionModel.LAST_TOUCH)

        assert result["success"] is True
        assert result["model"] == "last_touch"
        assert result["touchpoint_count"] == 3
        assert result["total_revenue"] == 1000.0
        weights = [b["weight"] for b in result["breakdown"]]
        assert weights == [0.0, 0.0, 1.0]
        assert result["breakdown"][2]["attributed_revenue"] == 1000.0
        # Primary attribution goes to the LAST touchpoint.
        assert deal.attributed_touchpoint_id == tps[-1].id
        assert deal.attributed_campaign_id == tps[-1].campaign_id
        assert deal.attributed_platform == tps[-1].source
        assert deal.attribution_model is AttributionModel.LAST_TOUCH
        assert deal.attribution_confidence == pytest.approx(0.95)  # gclid + 3 touches
        assert tps[-1].attribution_weight == 1.0
        assert all(tp.is_converting_touch for tp in tps)
        db.commit.assert_awaited_once()

    async def test_first_touch_primary_is_first(self) -> None:
        deal = _deal()
        tps = [_tp(days_before=5.0), _tp(days_before=1.0)]
        db = _make_db([_scalar(deal), _scalars(tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal(deal.id, AttributionModel.FIRST_TOUCH)

        assert result["success"] is True
        assert deal.attributed_touchpoint_id == tps[0].id
        assert [b["weight"] for b in result["breakdown"]] == [1.0, 0.0]


# =============================================================================
# attribute_deal_with_platform_windows
# =============================================================================


class TestAttributeDealWithPlatformWindows:
    async def test_deal_not_found(self) -> None:
        service = _service([_scalar(None)])
        result = await service.attribute_deal_with_platform_windows(uuid4())
        assert result == {"success": False, "error": "deal_not_found"}

    async def test_no_contact_and_no_touchpoints(self) -> None:
        service = _service([_scalar(_deal(contact_id=None))])
        result = await service.attribute_deal_with_platform_windows(uuid4())
        assert result["error"] == "no_contact_linked"

        service = _service([_scalar(_deal()), _scalars([])])
        result = await service.attribute_deal_with_platform_windows(uuid4())
        assert result["error"] == "no_touchpoints"

    async def test_meta_click_and_view_window_filtering(self) -> None:
        """Meta: 7d click window, 1d view window, 28d max lookback."""
        deal = _deal()
        kept_click = _tp(days_before=3.0, fbclid="f-1")
        dropped_click = _tp(days_before=10.0, fbclid="f-2")  # beyond click window
        kept_view = _tp(days_before=0.5)
        dropped_view = _tp(days_before=2.0)  # beyond view window
        beyond_lookback = _tp(days_before=40.0, fbclid="f-3")  # beyond max lookback
        all_tps = [beyond_lookback, dropped_click, kept_click, dropped_view, kept_view]

        db = _make_db([_scalar(deal), _scalars(all_tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal_with_platform_windows(
            deal.id, model=AttributionModel.TIME_DECAY, platform="meta"
        )

        assert result["success"] is True
        assert result["platform"] == "meta"
        assert result["platform_config"]["click_window_days"] == 7
        assert result["platform_config"]["view_window_days"] == 1
        assert result["filtered_from"] == 5
        assert result["touchpoint_count"] == 2
        kept_ids = {b["touchpoint_id"] for b in result["breakdown"]}
        assert kept_ids == {str(kept_click.id), str(kept_view.id)}
        types = {b["touchpoint_id"]: b["touchpoint_type"] for b in result["breakdown"]}
        assert types[str(kept_click.id)] == "click"
        assert types[str(kept_view.id)] == "view"
        assert sum(b["weight"] for b in result["breakdown"]) == pytest.approx(1.0)
        db.commit.assert_awaited_once()

    async def test_platform_auto_detected_from_majority(self) -> None:
        """Google majority -> google config; view_window=0 drops all views."""
        deal = _deal()
        tps = [
            _tp(days_before=2.0, source="google", gclid="g-1"),
            _tp(days_before=4.0, source="google", gclid="g-2"),
            _tp(days_before=0.5, source="meta"),  # view tp, google view_window=0
        ]
        db = _make_db([_scalar(deal), _scalars(tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal_with_platform_windows(deal.id)

        assert result["platform"] == "google"
        assert result["platform_config"]["view_window_days"] == 0
        assert result["touchpoint_count"] == 2  # the meta view was filtered

    async def test_fallback_when_all_filtered(self) -> None:
        """Clicks inside lookback but outside the click window -> fallback."""
        deal = _deal()
        tps = [
            _tp(days_before=20.0, fbclid="f-1"),
            _tp(days_before=15.0, fbclid="f-2"),
        ]
        db = _make_db([_scalar(deal), _scalars(tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal_with_platform_windows(
            deal.id, platform="meta"
        )

        assert result["success"] is True
        assert result["touchpoint_count"] == 2  # fell back to all touchpoints
        assert result["filtered_from"] == 2

    async def test_first_touch_primary_in_window_variant(self) -> None:
        deal = _deal()
        tps = [_tp(days_before=5.0, gclid="a"), _tp(days_before=1.0, gclid="b")]
        db = _make_db([_scalar(deal), _scalars(tps)])
        service = AttributionService(db=db, tenant_id=1)

        result = await service.attribute_deal_with_platform_windows(
            deal.id, model=AttributionModel.FIRST_TOUCH, platform="google"
        )

        assert result["success"] is True
        assert deal.attributed_touchpoint_id == tps[0].id


# =============================================================================
# batch_attribute_deals
# =============================================================================


class TestBatchAttributeDeals:
    async def test_success_failure_and_exception_accounting(self) -> None:
        deals = [_deal(), _deal(), _deal()]
        service = _service([_scalars(deals)])
        service.attribute_deal = AsyncMock(
            side_effect=[
                {"success": True},
                {"success": False, "error": "no_touchpoints"},
                ValueError("boom"),
            ]
        )

        results = await service.batch_attribute_deals()

        assert results["total"] == 3
        assert results["attributed"] == 1
        assert results["failed"] == 2
        assert [e["error"] for e in results["errors"]] == ["no_touchpoints", "boom"]

    async def test_deal_ids_and_date_filters(self) -> None:
        deal = _deal()
        service = _service([_scalars([deal])])
        service.attribute_deal = AsyncMock(return_value={"success": True})

        results = await service.batch_attribute_deals(
            model=AttributionModel.LINEAR,
            deal_ids=[deal.id],
            start_date=CONVERSION - timedelta(days=30),
            end_date=CONVERSION,
        )

        assert results == {"total": 1, "attributed": 1, "failed": 0, "errors": []}
        service.attribute_deal.assert_awaited_once_with(
            deal.id, AttributionModel.LINEAR
        )


# =============================================================================
# compare_attribution_models
# =============================================================================


class TestCompareAttributionModels:
    async def test_two_models_and_touchpointless_deal(self) -> None:
        d1 = _deal(amount=100.0)
        d2 = _deal(amount=50.0)  # no touchpoints -> skipped
        d3 = _deal(amount=40.0)  # same journey -> exercises existing-key adds
        tps = [
            _tp(days_before=5.0, source="google", campaign_id="A"),
            _tp(days_before=1.0, source="meta", campaign_id="B"),
        ]
        service = _service(
            [
                _scalars([d1, d2, d3]),  # deals query (once)
                _scalars(tps),  # d1 touchpoints, FIRST_TOUCH
                _scalars([]),  # d2 touchpoints, FIRST_TOUCH
                _scalars(tps),  # d3 touchpoints, FIRST_TOUCH
                _scalars(tps),  # d1 touchpoints, LAST_TOUCH
                _scalars([]),  # d2 touchpoints, LAST_TOUCH
                _scalars(tps),  # d3 touchpoints, LAST_TOUCH
            ]
        )

        result = await service.compare_attribution_models(
            start_date=CONVERSION - timedelta(days=30),
            end_date=CONVERSION,
            models=[AttributionModel.FIRST_TOUCH, AttributionModel.LAST_TOUCH],
        )

        assert result["deals_analyzed"] == 3
        assert result["total_revenue"] == 190.0

        first = result["models"]["first_touch"]["by_campaign"]
        assert first[0]["campaign_id"] == "A"
        assert first[0]["attributed_revenue"] == pytest.approx(140.0)
        last = result["models"]["last_touch"]["by_campaign"]
        assert last[0]["campaign_id"] == "B"
        assert last[0]["attributed_revenue"] == pytest.approx(140.0)

        by_platform = result["models"]["last_touch"]["by_platform"]
        assert by_platform[0]["platform"] == "meta"

    async def test_default_model_list_used_when_none(self) -> None:
        service = _service([_scalars([])])  # no deals -> no touchpoint queries
        result = await service.compare_attribution_models(
            start_date=CONVERSION - timedelta(days=7), end_date=CONVERSION
        )
        assert set(result["models"]) == {
            "first_touch",
            "last_touch",
            "linear",
            "position_based",
            "time_decay",
        }


# =============================================================================
# get_campaign_attribution
# =============================================================================


class TestGetCampaignAttribution:
    async def test_no_contacts_early_return(self) -> None:
        tps = [_tp(contact_id=None), _tp(contact_id=None)]
        service = _service([_scalars(tps)])

        result = await service.get_campaign_attribution(
            "camp-1", CONVERSION - timedelta(days=30), CONVERSION
        )

        assert result["contacts_reached"] == 0
        assert result["deals_attributed"] == 0
        assert result["attributed_revenue"] == 0
        assert result["touchpoints"] == 2

    async def test_campaign_index_weighting(self) -> None:
        contact_id = uuid4()
        campaign_tp = _tp(days_before=5.0, campaign_id="X", contact_id=contact_id)
        other_tp = _tp(days_before=1.0, campaign_id="Y", contact_id=contact_id)
        deal = _deal(amount=100.0, contact_id=contact_id)
        no_match_deal = _deal(amount=999.0, contact_id=contact_id)
        empty_journey_deal = _deal(amount=555.0, contact_id=contact_id)

        service = _service(
            [
                _scalars([campaign_tp]),  # campaign touchpoints
                _scalars([deal, no_match_deal, empty_journey_deal]),  # deals
                _scalars([campaign_tp, other_tp]),  # deal 1 journey
                _scalars([other_tp]),  # deal 2 journey (campaign absent)
                _scalars([]),  # deal 3 journey (no touchpoints)
            ]
        )

        result = await service.get_campaign_attribution(
            "X",
            CONVERSION - timedelta(days=30),
            CONVERSION,
            model=AttributionModel.LINEAR,
        )

        # Linear over 2 touchpoints -> campaign X owns 0.5 of deal 1 only.
        assert result["attributed_revenue"] == pytest.approx(50.0)
        assert result["deals_attributed"] == pytest.approx(0.5)
        assert result["contacts_reached"] == 1


# =============================================================================
# get_attribution_summary
# =============================================================================


class TestGetAttributionSummary:
    @pytest.mark.parametrize(
        "group_by,expected_key",
        [
            ("platform", "meta"),
            ("campaign", "camp-1"),
            ("adset", "adset-1"),
            ("day", (CONVERSION - timedelta(days=1)).date().isoformat()),
            ("bogus", "meta"),  # unknown group_by falls back to platform
        ],
    )
    async def test_group_by_matrix(self, group_by: str, expected_key: str) -> None:
        deal = _deal(amount=200.0)
        skipped_deal = _deal(amount=999.0)  # no touchpoints -> skipped
        # Two touchpoints on the same day/campaign/adset/platform so every
        # group_by folds them into one bucket (existing-key branch).
        tps = [_tp(days_before=1.25), _tp(days_before=1.0)]
        service = _service(
            [_scalars([deal, skipped_deal]), _scalars(tps), _scalars([])]
        )

        rows = await service.get_attribution_summary(
            CONVERSION - timedelta(days=30),
            CONVERSION,
            model=AttributionModel.LAST_TOUCH,
            group_by=group_by,
        )

        assert len(rows) == 1
        assert rows[0]["key"] == expected_key
        assert rows[0]["attributed_revenue"] == pytest.approx(200.0)
        assert rows[0]["attributed_deals"] == pytest.approx(1.0)
        assert rows[0]["touchpoint_count"] == 2
        assert rows[0]["unique_contacts"] == 1

    async def test_sorted_by_revenue_desc_and_direct_fallbacks(self) -> None:
        deal = _deal(amount=100.0)
        tps = [
            _tp(days_before=2.0, campaign_id=None, campaign_name=None),
            _tp(days_before=1.0, campaign_id="big"),
        ]
        service = _service([_scalars([deal]), _scalars(tps)])

        rows = await service.get_attribution_summary(
            CONVERSION - timedelta(days=30),
            CONVERSION,
            model=AttributionModel.LINEAR,
            group_by="campaign",
        )

        assert [r["key"] for r in rows] == ["big", "direct"] or [
            r["key"] for r in rows
        ] == ["direct", "big"]
        revenues = [r["attributed_revenue"] for r in rows]
        assert revenues == sorted(revenues, reverse=True)


# =============================================================================
# In-service MarkovAttributionModel (invariant-only assertions)
# =============================================================================
# The random-walk simulation keys off hash(), which varies with
# PYTHONHASHSEED across processes -- so these tests assert seed-independent
# invariants only (ranges, normalization, fallbacks), never exact values.


class TestMarkovAttributionModelInService:
    def test_unfitted_equal_weights(self) -> None:
        model = MarkovAttributionModel()
        weights = model.get_attribution_weights(["a", "b"])
        assert weights == {"a": 0.5, "b": 0.5}

    def test_unfitted_empty_channels(self) -> None:
        assert MarkovAttributionModel().get_attribution_weights([]) == {}

    def test_removal_effect_unfitted_guard(self) -> None:
        assert MarkovAttributionModel()._calculate_removal_effect("a") == 0.0

    def test_fit_empty_journeys_baseline_zero(self) -> None:
        model = MarkovAttributionModel().fit([], [])
        assert model._is_fitted is True
        assert model.conversion_probs["baseline"] == 0.0
        assert model.removal_effects == {}

    def test_fitted_zero_effects_falls_back_to_equal(self) -> None:
        model = MarkovAttributionModel().fit([], [])
        weights = model.get_attribution_weights(["a", "b"])
        assert weights == {"a": 0.5, "b": 0.5}

    def test_fit_three_channel_invariants(self) -> None:
        """Three single-touch channels, each with converting and
        non-converting journeys, so every graph node keeps >= 2 outgoing
        edges during removal simulation."""
        journeys = [["a"], ["a"], ["b"], ["b"], ["c"], ["c"]]
        converted = [True, False, True, False, True, False]

        model = MarkovAttributionModel().fit(journeys, converted)

        assert model._is_fitted is True
        # Transition rows are probability distributions.
        for row in model.transition_matrix.values():
            assert sum(row.values()) == pytest.approx(1.0)
            assert all(0.0 <= p <= 1.0 for p in row.values())
        assert 0.0 <= model.conversion_probs["baseline"] <= 1.0
        assert set(model.removal_effects) == {"a", "b", "c"}
        assert all(0.0 <= e <= 1.0 for e in model.removal_effects.values())

        weights = model.get_attribution_weights(["a", "b", "c"])
        assert set(weights) == {"a", "b", "c"}
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(w >= 0 for w in weights.values())


# =============================================================================
# _get_contact_touchpoints (no before_time branch)
# =============================================================================


class TestGetContactTouchpoints:
    async def test_without_before_time(self) -> None:
        tps = [_tp()]
        service = _service([_scalars(tps)])
        assert await service._get_contact_touchpoints(uuid4()) == tps


# =============================================================================
# CrossPlatformAttributor
# =============================================================================


class TestReconcileClaims:
    @pytest.fixture
    def attributor(self) -> CrossPlatformAttributor:
        return CrossPlatformAttributor(db=None, tenant_id=1)

    def test_zero_claims_guard(self, attributor: CrossPlatformAttributor) -> None:
        claims = {
            "meta": {"conversions": 0, "revenue": 0, "spend": 0},
            "google": {"conversions": 0, "revenue": 0, "spend": 0},
        }
        result = attributor._reconcile_claims(
            claims, {"count": 10, "revenue": 1000}, "linear"
        )
        assert result == {
            "meta": {"conversions": 0, "revenue": 0, "share": 0},
            "google": {"conversions": 0, "revenue": 0, "share": 0},
        }

    def test_proportional(self, attributor: CrossPlatformAttributor) -> None:
        claims = {
            "meta": {"conversions": 30, "revenue": 0, "spend": 0},
            "google": {"conversions": 10, "revenue": 0, "spend": 0},
        }
        result = attributor._reconcile_claims(
            claims, {"count": 20, "revenue": 2000.0}, "proportional"
        )
        assert result["meta"]["share"] == pytest.approx(0.75)
        assert result["meta"]["conversions"] == pytest.approx(15.0)
        assert result["google"]["revenue"] == pytest.approx(500.0)
        assert result["meta"]["original_claim"] == 30

    def test_spend_weighted(self, attributor: CrossPlatformAttributor) -> None:
        claims = {
            "meta": {"conversions": 5, "revenue": 0, "spend": 300.0},
            "google": {"conversions": 5, "revenue": 0, "spend": 100.0},
        }
        result = attributor._reconcile_claims(
            claims, {"count": 8, "revenue": 800.0}, "spend_weighted"
        )
        assert result["meta"]["share"] == pytest.approx(0.75)
        assert result["google"]["conversions"] == pytest.approx(2.0)

    def test_spend_weighted_zero_spend_guard(
        self, attributor: CrossPlatformAttributor
    ) -> None:
        claims = {"meta": {"conversions": 5, "revenue": 0, "spend": 0}}
        result = attributor._reconcile_claims(
            claims, {"count": 8, "revenue": 800.0}, "spend_weighted"
        )
        assert result["meta"]["share"] == 0

    def test_linear_default(self, attributor: CrossPlatformAttributor) -> None:
        claims = {
            "meta": {"conversions": 9, "revenue": 0, "spend": 0},
            "google": {"conversions": 1, "revenue": 0, "spend": 0},
        }
        result = attributor._reconcile_claims(
            claims, {"count": 10, "revenue": 100.0}, "linear"
        )
        assert result["meta"]["share"] == pytest.approx(0.5)
        assert result["google"]["share"] == pytest.approx(0.5)

    def test_over_claim_rate(self, attributor: CrossPlatformAttributor) -> None:
        claims = {"meta": {"conversions": 30}, "google": {"conversions": 20}}
        rate = attributor._calculate_over_claim_rate(claims, {"count": 25})
        assert rate == pytest.approx(100.0)  # (50 - 25) / 25 * 100

    def test_over_claim_rate_zero_actual(
        self, attributor: CrossPlatformAttributor
    ) -> None:
        assert (
            attributor._calculate_over_claim_rate(
                {"meta": {"conversions": 10}}, {"count": 0}
            )
            == 0.0
        )

    def test_over_claim_rate_under_claim_floors_at_zero(
        self, attributor: CrossPlatformAttributor
    ) -> None:
        assert (
            attributor._calculate_over_claim_rate(
                {"meta": {"conversions": 5}}, {"count": 10}
            )
            == 0.0
        )


class TestActualConversionsAndUnified:
    async def test_get_actual_conversions_unpacks_row_tuple(self) -> None:
        # result.first() returns a (count, sum) 2-tuple.
        row_result = MagicMock()
        row_result.first.return_value = (3, Decimal("500.50"))
        attributor = CrossPlatformAttributor(db=_make_db([row_result]), tenant_id=1)

        actual = await attributor._get_actual_conversions(
            CONVERSION - timedelta(days=30), CONVERSION
        )

        assert actual == {"count": 3, "revenue": 500.5}

    async def test_get_actual_conversions_null_row_values(self) -> None:
        row_result = MagicMock()
        row_result.first.return_value = (None, None)
        attributor = CrossPlatformAttributor(db=_make_db([row_result]), tenant_id=1)

        actual = await attributor._get_actual_conversions(
            CONVERSION - timedelta(days=30), CONVERSION
        )

        assert actual == {"count": 0, "revenue": 0.0}

    async def test_get_unified_attribution(self) -> None:
        attributor = CrossPlatformAttributor(db=_make_db(), tenant_id=1)
        attributor._get_actual_conversions = AsyncMock(
            return_value={"count": 10, "revenue": 1000.0}
        )

        report = await attributor.get_unified_attribution(
            CONVERSION - timedelta(days=30), CONVERSION, normalization_method="linear"
        )

        assert report["actual_conversions"] == 10
        assert report["actual_revenue"] == 1000.0
        assert report["methodology"] == "linear"
        # Stubbed platform claims are all zero -> zero-claim reconciliation.
        assert set(report["platform_claims"]) == {"meta", "google", "tiktok"}
        assert all(
            v == {"conversions": 0, "revenue": 0, "share": 0}
            for v in report["reconciled_attribution"].values()
        )
        assert report["over_claim_rate"] == 0.0
