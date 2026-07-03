# =============================================================================
# Stratum AI - CDP Segment Service unit tests (evaluation + DB paths)
# =============================================================================
"""Unit tests for ``app.services.cdp.segment_service`` (issue #342, batch 3).

Complements ``test_segment_evaluator.py`` (pure ``_compare_values`` / field
extraction) with:

- ``SegmentEvaluator.evaluate_profile`` logic (and/or, nested groups, score
  averaging) and ``_evaluate_condition`` dispatch across every field prefix
- ``_get_identifier_value`` and the in-memory branch of ``_get_event_value``
- All ``SegmentService`` DB paths against a mocked ``AsyncSession``:
  CRUD, ``compute_segment`` add/reactivate/remove/error branches,
  ``preview_segment``, and membership management

No Postgres/Redis -- ``db.execute`` is an ``AsyncMock`` fed a ``side_effect``
list of stub results in query order (same recipe as
``test_autopilot_service.py``).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.cdp import CDPSegmentMembership, SegmentStatus, SegmentType
from app.services.cdp.segment_service import SegmentEvaluator, SegmentService

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers
# =============================================================================


def _make_db(execute_results: Optional[List[Any]] = None) -> MagicMock:
    """Mock AsyncSession: sync ``add``, async everything else."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    if execute_results is None:
        db.execute = AsyncMock(return_value=MagicMock())
    else:
        db.execute = AsyncMock(side_effect=list(execute_results))
    return db


def _scalar(value: Any) -> MagicMock:
    """Result stub for ``.scalar()`` / ``.scalar_one_or_none()``."""
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def _scalars(items: List[Any]) -> MagicMock:
    """Result stub for ``.scalars().all()``."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _profile(**overrides: Any) -> SimpleNamespace:
    """Duck-typed CDPProfile."""
    base = dict(
        id=uuid4(),
        lifecycle_stage="customer",
        total_events=10,
        total_sessions=3,
        total_purchases=2,
        total_revenue=Decimal("150.00"),
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 6, 1, tzinfo=UTC),
        external_id="ext-1",
        computed_traits={"ltv": 500},
        profile_data={"address": {"city": "NYC"}},
        identifiers=[SimpleNamespace(identifier_type="email")],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _event(name: str = "Purchase", ts: Optional[datetime] = None, **props: Any):
    return SimpleNamespace(
        event_name=name,
        event_time=ts or datetime(2026, 6, 1, tzinfo=UTC),
        properties=props,
    )


def _segment(**overrides: Any) -> SimpleNamespace:
    """Duck-typed CDPSegment with writable computed fields."""
    base = dict(
        id=uuid4(),
        tenant_id=1,
        name="Seg",
        rules={"logic": "and", "conditions": []},
        segment_type=SegmentType.DYNAMIC.value,
        status=SegmentStatus.DRAFT.value,
        auto_refresh=True,
        refresh_interval_hours=24,
        profile_count=0,
        last_computed_at=None,
        computation_duration_ms=None,
        next_refresh_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def evaluator() -> SegmentEvaluator:
    return SegmentEvaluator(db=None, tenant_id=1)


# =============================================================================
# SegmentEvaluator.evaluate_profile
# =============================================================================


class TestEvaluateProfile:
    async def test_empty_rules_no_match(self, evaluator: SegmentEvaluator) -> None:
        assert await evaluator.evaluate_profile(_profile(), {}) == (False, None)
        assert await evaluator.evaluate_profile(
            _profile(), {"logic": "and", "conditions": [], "groups": []}
        ) == (False, None)

    async def test_and_logic_all_must_match(self, evaluator: SegmentEvaluator) -> None:
        rules = {
            "logic": "and",
            "conditions": [
                {
                    "field": "profile.lifecycle_stage",
                    "operator": "equals",
                    "value": "customer",
                },
                {
                    "field": "profile.total_purchases",
                    "operator": "greater_than",
                    "value": 5,
                },
            ],
        }
        matches, score = await evaluator.evaluate_profile(_profile(), rules)
        assert matches is False
        assert score == pytest.approx(0.5)  # [1.0 match, 0.0 miss] averaged

    async def test_or_logic_any_matches(self, evaluator: SegmentEvaluator) -> None:
        rules = {
            "logic": "or",
            "conditions": [
                {
                    "field": "profile.lifecycle_stage",
                    "operator": "equals",
                    "value": "lead",
                },
                {
                    "field": "profile.total_purchases",
                    "operator": "greater_than",
                    "value": 1,
                },
            ],
        }
        matches, score = await evaluator.evaluate_profile(_profile(), rules)
        assert matches is True
        assert score == pytest.approx(0.5)

    async def test_nested_group_recursion_and_score_average(
        self, evaluator: SegmentEvaluator
    ) -> None:
        rules = {
            "logic": "and",
            "conditions": [
                {
                    "field": "profile.lifecycle_stage",
                    "operator": "equals",
                    "value": "customer",
                }
            ],
            "groups": [
                {
                    "logic": "or",
                    "conditions": [
                        {
                            "field": "trait.ltv",
                            "operator": "greater_than",
                            "value": 1000,
                        },
                        {
                            "field": "trait.ltv",
                            "operator": "greater_than",
                            "value": 100,
                        },
                    ],
                }
            ],
        }
        matches, score = await evaluator.evaluate_profile(_profile(), rules)
        assert matches is True
        # Top-level condition scores 1.0; group averages [0.0, 1.0] -> 0.5.
        assert score == pytest.approx((1.0 + 0.5) / 2)


# =============================================================================
# SegmentEvaluator._evaluate_condition dispatch
# =============================================================================


class TestEvaluateConditionDispatch:
    async def test_profile_prefix(self, evaluator: SegmentEvaluator) -> None:
        cond = {
            "field": "profile.total_revenue",
            "operator": "greater_than",
            "value": 100,
        }
        assert (await evaluator._evaluate_condition(_profile(), cond))[0] is True

    async def test_trait_prefix(self, evaluator: SegmentEvaluator) -> None:
        cond = {"field": "trait.ltv", "operator": "equals", "value": 500}
        assert (await evaluator._evaluate_condition(_profile(), cond))[0] is True

    async def test_identifier_prefix(self, evaluator: SegmentEvaluator) -> None:
        cond = {"field": "identifier.email", "operator": "equals", "value": True}
        assert (await evaluator._evaluate_condition(_profile(), cond))[0] is True

    async def test_event_prefix_with_in_memory_events(
        self, evaluator: SegmentEvaluator
    ) -> None:
        cond = {
            "field": "event.Purchase.count",
            "operator": "greater_or_equal",
            "value": 2,
        }
        events = [_event(), _event()]
        assert (await evaluator._evaluate_condition(_profile(), cond, events))[
            0
        ] is True

    async def test_data_prefix_nested(self, evaluator: SegmentEvaluator) -> None:
        cond = {"field": "data.address.city", "operator": "equals", "value": "NYC"}
        assert (await evaluator._evaluate_condition(_profile(), cond))[0] is True

    async def test_short_field_path_guard(self, evaluator: SegmentEvaluator) -> None:
        cond = {"field": "lifecycle_stage", "operator": "equals", "value": "x"}
        assert await evaluator._evaluate_condition(_profile(), cond) == (False, None)

    async def test_unknown_field_type(self, evaluator: SegmentEvaluator) -> None:
        cond = {"field": "bogus.thing", "operator": "equals", "value": "x"}
        assert await evaluator._evaluate_condition(_profile(), cond) == (False, None)

    async def test_exception_is_caught_and_warned(
        self, evaluator: SegmentEvaluator
    ) -> None:
        # identifiers=5 is truthy but not iterable -> TypeError inside try.
        profile = _profile(identifiers=5)
        cond = {"field": "identifier.email", "operator": "equals", "value": True}
        assert await evaluator._evaluate_condition(profile, cond) == (False, None)


# =============================================================================
# _compare_values / _parse_datetime edge paths not covered elsewhere
# =============================================================================


class TestCompareValuesEdges:
    def test_within_last_unparseable_actual_is_false(
        self, evaluator: SegmentEvaluator
    ) -> None:
        # An int is neither datetime nor ISO string -> parse fails -> False.
        assert evaluator._compare_values(12345, "within_last", 7)[0] is False

    def test_numeric_comparison_type_error_is_warned(
        self, evaluator: SegmentEvaluator
    ) -> None:
        # float("abc") raises ValueError -> caught -> (False, None).
        assert evaluator._compare_values("abc", "greater_than", 10) == (False, None)

    def test_parse_datetime_non_string_non_datetime(
        self, evaluator: SegmentEvaluator
    ) -> None:
        assert evaluator._parse_datetime(12345) is None


# =============================================================================
# _get_identifier_value / _get_event_value (in-memory branch)
# =============================================================================


class TestIdentifierAndEventValues:
    async def test_identifier_present(self, evaluator: SegmentEvaluator) -> None:
        assert await evaluator._get_identifier_value(_profile(), "email") is True

    async def test_identifier_absent(self, evaluator: SegmentEvaluator) -> None:
        assert await evaluator._get_identifier_value(_profile(), "phone") is False

    async def test_identifier_none_list(self, evaluator: SegmentEvaluator) -> None:
        assert (
            await evaluator._get_identifier_value(_profile(identifiers=None), "email")
            is False
        )

    async def test_event_short_path_is_none(self, evaluator: SegmentEvaluator) -> None:
        assert await evaluator._get_event_value(_profile(), ["Purchase"], []) is None

    async def test_event_aggregations_in_memory(
        self, evaluator: SegmentEvaluator
    ) -> None:
        newest = _event(ts=datetime(2026, 6, 2, tzinfo=UTC), amount=42)
        oldest = _event(ts=datetime(2026, 5, 1, tzinfo=UTC), amount=7)
        other = _event(name="PageView")
        events = [newest, oldest, other]  # newest-first, mixed names
        profile = _profile()

        get = evaluator._get_event_value
        assert await get(profile, ["Purchase", "count"], events) == 2
        assert await get(profile, ["Purchase", "exists"], events) is True
        assert await get(profile, ["Purchase", "last"], events) == newest.event_time
        assert await get(profile, ["Purchase", "first"], events) == oldest.event_time
        assert await get(profile, ["Purchase", "property", "amount"], events) == 42

    async def test_event_unknown_aggregation_and_empty(
        self, evaluator: SegmentEvaluator
    ) -> None:
        get = evaluator._get_event_value
        assert await get(_profile(), ["Purchase", "median"], [_event()]) is None
        assert await get(_profile(), ["Purchase", "last"], []) is None
        assert await get(_profile(), ["Purchase", "exists"], []) is False

    async def test_event_db_fetch_branch(self) -> None:
        events = [_event(), _event()]
        db = _make_db([_scalars(events)])
        evaluator = SegmentEvaluator(db=db, tenant_id=1)

        count = await evaluator._get_event_value(
            _profile(), ["Purchase", "count"], None
        )

        assert count == 2
        db.execute.assert_awaited_once()


# =============================================================================
# SegmentService CRUD
# =============================================================================


class TestSegmentCrud:
    async def test_create_segment_defaults_and_slug(self) -> None:
        db = _make_db()
        service = SegmentService(db=db, tenant_id=1)

        segment = await service.create_segment(
            name="High Value Customers!",
            rules={"logic": "and", "conditions": []},
            description="d",
            tags=["vip"],
            created_by_user_id=7,
        )

        assert segment.slug == "high-value-customers"
        assert segment.tenant_id == 1
        assert segment.status == SegmentStatus.DRAFT.value
        assert segment.segment_type == SegmentType.DYNAMIC.value
        assert segment.tags == ["vip"]
        db.add.assert_called_once_with(segment)
        db.flush.assert_awaited()

    async def test_get_segment(self) -> None:
        seg = _segment()
        service = SegmentService(db=_make_db([_scalar(seg)]), tenant_id=1)
        assert await service.get_segment(seg.id) is seg

    async def test_list_segments_with_filters(self) -> None:
        segs = [_segment(), _segment()]
        db = _make_db([_scalar(3), _scalars(segs)])
        service = SegmentService(db=db, tenant_id=1)

        result, total = await service.list_segments(
            status=SegmentStatus.ACTIVE.value,
            segment_type=SegmentType.DYNAMIC.value,
            limit=10,
            offset=0,
        )

        assert result == segs
        assert total == 3

    async def test_list_segments_none_count_coerced_to_zero(self) -> None:
        db = _make_db([_scalar(None), _scalars([])])
        service = SegmentService(db=db, tenant_id=1)
        result, total = await service.list_segments()
        assert (result, total) == ([], 0)

    async def test_update_segment_rules_marks_stale(self) -> None:
        seg = _segment(status=SegmentStatus.ACTIVE.value)
        db = _make_db([_scalar(seg)])
        service = SegmentService(db=db, tenant_id=1)

        updated = await service.update_segment(
            seg.id, name="Renamed", rules={"logic": "or"}, not_a_field="ignored"
        )

        assert updated is seg
        assert seg.name == "Renamed"
        assert seg.rules == {"logic": "or"}
        assert seg.status == SegmentStatus.STALE.value
        assert not hasattr(seg, "not_a_field")
        db.flush.assert_awaited()

    async def test_update_segment_without_rules_keeps_status(self) -> None:
        seg = _segment(status=SegmentStatus.ACTIVE.value)
        service = SegmentService(db=_make_db([_scalar(seg)]), tenant_id=1)
        await service.update_segment(seg.id, name="Renamed")
        assert seg.status == SegmentStatus.ACTIVE.value

    async def test_update_segment_not_found(self) -> None:
        service = SegmentService(db=_make_db([_scalar(None)]), tenant_id=1)
        assert await service.update_segment(uuid4(), name="x") is None

    async def test_delete_segment(self) -> None:
        seg = _segment()
        db = _make_db([_scalar(seg)])
        service = SegmentService(db=db, tenant_id=1)
        assert await service.delete_segment(seg.id) is True
        db.delete.assert_awaited_once_with(seg)

    async def test_delete_segment_not_found(self) -> None:
        service = SegmentService(db=_make_db([_scalar(None)]), tenant_id=1)
        assert await service.delete_segment(uuid4()) is False


# =============================================================================
# compute_segment
# =============================================================================


class TestComputeSegment:
    async def test_compute_segment_not_found(self) -> None:
        service = SegmentService(db=_make_db([_scalar(None)]), tenant_id=1)
        assert await service.compute_segment(uuid4()) == (0, 0)

    async def test_compute_add_reactivate_keep_remove(self) -> None:
        """One batch of four profiles covering every membership branch."""
        seg = _segment(auto_refresh=True, refresh_interval_hours=24)
        profiles = [_profile() for _ in range(4)]
        inactive = SimpleNamespace(
            is_active=False,
            removed_at=datetime(2026, 1, 1, tzinfo=UTC),
            match_score=None,
        )
        active_keep = SimpleNamespace(is_active=True, removed_at=None, match_score=None)
        active_remove = SimpleNamespace(
            is_active=True, removed_at=None, match_score=None
        )

        db = _make_db(
            [
                _scalar(seg),  # get_segment
                _scalars(profiles),  # batch 1
                _scalar(None),  # p1 membership -> add
                _scalar(inactive),  # p2 membership -> reactivate
                _scalar(active_keep),  # p3 membership -> already active
                _scalar(active_remove),  # p4 membership -> remove
                _scalars([]),  # batch 2 ends the loop
                _scalar(3),  # final active count
            ]
        )
        service = SegmentService(db=db, tenant_id=1)
        service.evaluator.evaluate_profile = AsyncMock(
            side_effect=[(True, 0.8), (True, None), (True, 0.9), (False, None)]
        )

        before = datetime.now(UTC)
        added, removed = await service.compute_segment(seg.id, batch_size=1000)

        assert (added, removed) == (2, 1)
        # New membership row -> Decimal conversion of the 0.8 score.
        new_membership = db.add.call_args[0][0]
        assert isinstance(new_membership, CDPSegmentMembership)
        assert new_membership.match_score == Decimal("0.8")
        # Reactivated membership: score None -> match_score stays None.
        assert inactive.is_active is True
        assert inactive.removed_at is None
        assert inactive.match_score is None
        # Removed membership flagged with a removal timestamp.
        assert active_remove.is_active is False
        assert active_remove.removed_at >= before
        # Untouched active member.
        assert active_keep.is_active is True
        # Segment metadata refreshed.
        assert seg.status == SegmentStatus.ACTIVE.value
        assert seg.profile_count == 3
        assert seg.last_computed_at >= before
        assert isinstance(seg.computation_duration_ms, int)
        assert seg.next_refresh_at >= before + timedelta(hours=23)

    async def test_compute_without_auto_refresh_skips_next_refresh(self) -> None:
        seg = _segment(auto_refresh=False)
        db = _make_db(
            [
                _scalar(seg),
                _scalars([]),  # no profiles at all
                _scalar(0),
            ]
        )
        service = SegmentService(db=db, tenant_id=1)

        assert await service.compute_segment(seg.id) == (0, 0)
        assert seg.next_refresh_at is None
        assert seg.status == SegmentStatus.ACTIVE.value

    async def test_compute_error_marks_stale_and_reraises(self) -> None:
        seg = _segment()
        db = _make_db([_scalar(seg), _scalars([_profile()])])
        service = SegmentService(db=db, tenant_id=1)
        service.evaluator.evaluate_profile = AsyncMock(side_effect=ValueError("boom"))

        with pytest.raises(ValueError, match="boom"):
            await service.compute_segment(seg.id)

        assert seg.status == SegmentStatus.STALE.value
        db.flush.assert_awaited()


# =============================================================================
# preview_segment
# =============================================================================


class TestPreviewSegment:
    async def test_preview_estimates_from_match_rate(self) -> None:
        p1, p2 = _profile(), _profile()
        db = _make_db(
            [
                _scalars([p1, p2]),  # batch 1
                _scalars([]),  # batch 2 -> stop sampling
                _scalar(10),  # total profile count
            ]
        )
        service = SegmentService(db=db, tenant_id=1)
        service.evaluator.evaluate_profile = AsyncMock(
            side_effect=[(True, None), (False, None)]
        )

        estimated, sample = await service.preview_segment({"logic": "and"}, limit=100)

        assert estimated == 5  # 1/2 match rate x 10 profiles
        assert sample == [p1]

    async def test_preview_stops_at_limit(self) -> None:
        p1, p2 = _profile(), _profile()
        db = _make_db(
            [
                _scalars([p1, p2]),
                _scalar(8),  # total count (no second batch needed)
            ]
        )
        service = SegmentService(db=db, tenant_id=1)
        service.evaluator.evaluate_profile = AsyncMock(return_value=(True, None))

        estimated, sample = await service.preview_segment({"logic": "and"}, limit=1)

        assert sample == [p1]
        assert estimated == 4  # 1 match / 2 checked x 8 total
        # Second profile never evaluated after the limit break.
        assert service.evaluator.evaluate_profile.await_count == 1

    async def test_preview_no_profiles(self) -> None:
        service = SegmentService(db=_make_db([_scalars([])]), tenant_id=1)
        assert await service.preview_segment({"logic": "and"}) == (0, [])


# =============================================================================
# Membership management
# =============================================================================


class TestMembership:
    async def test_get_segment_profiles(self) -> None:
        profiles = [_profile()]
        db = _make_db([_scalar(7), _scalars(profiles)])
        service = SegmentService(db=db, tenant_id=1)
        assert await service.get_segment_profiles(uuid4()) == (profiles, 7)

    async def test_get_profile_segments(self) -> None:
        segs = [_segment(), _segment()]
        service = SegmentService(db=_make_db([_scalars(segs)]), tenant_id=1)
        assert await service.get_profile_segments(uuid4()) == segs

    async def test_add_profile_rejects_non_static(self) -> None:
        seg = _segment(segment_type=SegmentType.DYNAMIC.value)
        service = SegmentService(db=_make_db([_scalar(seg)]), tenant_id=1)
        assert await service.add_profile_to_segment(seg.id, uuid4()) is False

    async def test_add_profile_segment_missing(self) -> None:
        service = SegmentService(db=_make_db([_scalar(None)]), tenant_id=1)
        assert await service.add_profile_to_segment(uuid4(), uuid4()) is False

    async def test_add_profile_existing_active_is_noop(self) -> None:
        seg = _segment(segment_type=SegmentType.STATIC.value, profile_count=5)
        existing = SimpleNamespace(
            is_active=True, removed_at=None, added_by_user_id=None
        )
        service = SegmentService(
            db=_make_db([_scalar(seg), _scalar(existing)]), tenant_id=1
        )
        assert await service.add_profile_to_segment(seg.id, uuid4()) is True
        assert seg.profile_count == 5

    async def test_add_profile_reactivates_inactive(self) -> None:
        seg = _segment(segment_type=SegmentType.STATIC.value, profile_count=5)
        existing = SimpleNamespace(
            is_active=False,
            removed_at=datetime(2026, 1, 1, tzinfo=UTC),
            added_by_user_id=None,
        )
        service = SegmentService(
            db=_make_db([_scalar(seg), _scalar(existing)]), tenant_id=1
        )

        assert (
            await service.add_profile_to_segment(seg.id, uuid4(), added_by_user_id=9)
            is True
        )
        assert existing.is_active is True
        assert existing.removed_at is None
        assert existing.added_by_user_id == 9
        assert seg.profile_count == 6

    async def test_add_profile_creates_membership(self) -> None:
        seg = _segment(segment_type=SegmentType.STATIC.value, profile_count=0)
        profile_id = uuid4()
        db = _make_db([_scalar(seg), _scalar(None)])
        service = SegmentService(db=db, tenant_id=1)

        assert (
            await service.add_profile_to_segment(seg.id, profile_id, added_by_user_id=9)
            is True
        )
        membership = db.add.call_args[0][0]
        assert isinstance(membership, CDPSegmentMembership)
        assert membership.profile_id == profile_id
        assert membership.added_by_user_id == 9
        assert seg.profile_count == 1

    async def test_remove_profile_success(self) -> None:
        seg = _segment(profile_count=1)
        membership = SimpleNamespace(is_active=True, removed_at=None)
        service = SegmentService(
            db=_make_db([_scalar(seg), _scalar(membership)]), tenant_id=1
        )

        before = datetime.now(UTC)
        assert await service.remove_profile_from_segment(seg.id, uuid4()) is True
        assert membership.is_active is False
        assert membership.removed_at >= before
        assert seg.profile_count == 0

    async def test_remove_profile_count_never_negative(self) -> None:
        seg = _segment(profile_count=0)
        membership = SimpleNamespace(is_active=True, removed_at=None)
        service = SegmentService(
            db=_make_db([_scalar(seg), _scalar(membership)]), tenant_id=1
        )
        assert await service.remove_profile_from_segment(seg.id, uuid4()) is True
        assert seg.profile_count == 0

    async def test_remove_profile_no_membership(self) -> None:
        seg = _segment()
        service = SegmentService(
            db=_make_db([_scalar(seg), _scalar(None)]), tenant_id=1
        )
        assert await service.remove_profile_from_segment(seg.id, uuid4()) is False

    async def test_remove_profile_segment_missing(self) -> None:
        service = SegmentService(db=_make_db([_scalar(None)]), tenant_id=1)
        assert await service.remove_profile_from_segment(uuid4(), uuid4()) is False
