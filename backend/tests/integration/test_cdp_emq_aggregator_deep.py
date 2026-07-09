# =============================================================================
# Stratum AI - CDP EMQ Aggregator Deep Integration Tests
# =============================================================================
"""DB-backed integration tests for ``app.services.cdp_emq_aggregator``.

First tests for the module (previously 0% — it is live code, imported by
``app.stratum.core.signal_health``). Covers:

- ``CDPEMQAggregator.get_aggregate_emq``: empty tenant default, healthy stats,
  the full issue matrix (low avg / low min / high variance / stale 24h),
  lookback windowing, null-EMQ events, explicit target_date.
- ``get_emq_trend``: daily grouping, ordering, day-window filter, null-EMQ
  exclusion, empty result.
- ``get_profile_quality_breakdown``: stage distribution, percentages,
  identity resolution rate, empty tenant.
- ``get_consent_metrics``: zero-profile early return, per-type grant rates,
  distinct-profile consent rate.
- ``calculate_cdp_contribution``: every branch of the resolution / recency /
  consent scoring ladders including boundary values and issue emission.
- ``get_cdp_emq_for_signal_health``: end-to-end composition for empty and
  populated tenants.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.cdp import CDPConsent, CDPEvent, CDPProfile
from app.services.cdp_emq_aggregator import (
    CDPEMQAggregator,
    get_cdp_emq_for_signal_health,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# Seed helpers
# =============================================================================


def _event(
    tenant_id: int,
    *,
    emq: float | None = 85.0,
    received_at: datetime | None = None,
    name: str = "page_view",
    profile_id=None,
) -> CDPEvent:
    now = datetime.now(UTC)
    received = received_at or now
    return CDPEvent(
        tenant_id=tenant_id,
        profile_id=profile_id,
        event_name=name,
        event_time=received,
        received_at=received,
        properties={},
        context={},
        identifiers=[],
        emq_score=Decimal(str(emq)) if emq is not None else None,
    )


def _profile(
    tenant_id: int,
    *,
    stage: str = "anonymous",
    total_events: int = 0,
) -> CDPProfile:
    return CDPProfile(
        tenant_id=tenant_id,
        lifecycle_stage=stage,
        profile_data={},
        computed_traits={},
        total_events=total_events,
    )


def _consent(
    tenant_id: int,
    profile_id,
    *,
    consent_type: str = "marketing",
    granted: bool = True,
) -> CDPConsent:
    return CDPConsent(
        tenant_id=tenant_id,
        profile_id=profile_id,
        consent_type=consent_type,
        granted=granted,
        granted_at=datetime.now(UTC) if granted else None,
        revoked_at=None if granted else datetime.now(UTC),
    )


@pytest_asyncio.fixture
async def aggregator(db_session) -> CDPEMQAggregator:
    return CDPEMQAggregator(db_session)


# =============================================================================
# get_aggregate_emq
# =============================================================================


class TestGetAggregateEmq:
    async def test_empty_tenant_returns_default_with_warning(
        self, aggregator, test_tenant
    ):
        data = await aggregator.get_aggregate_emq(test_tenant["id"])

        assert data["aggregate_score"] == 75.0
        assert data["event_count"] == 0
        assert data["profile_count"] == 0
        assert data["recent_event_count"] == 0
        assert data["avg_score"] == 0.0
        assert data["min_score"] == 0.0
        assert data["max_score"] == 0.0
        assert data["lookback_days"] == 7
        assert data["issues"] == [
            "No CDP events in analysis period - using default EMQ"
        ]
        assert "calculated_at" in data

    async def test_healthy_events_produce_no_issues(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _event(tid, emq=88.0),
                _event(tid, emq=90.0),
                _event(tid, emq=92.0),
            ]
        )
        db_session.add(_profile(tid))
        await db_session.flush()

        data = await aggregator.get_aggregate_emq(tid)

        assert data["aggregate_score"] == 90.0
        assert data["event_count"] == 3
        assert data["profile_count"] == 1
        assert data["recent_event_count"] == 3
        assert data["avg_score"] == 90.0
        assert data["min_score"] == 88.0
        assert data["max_score"] == 92.0
        assert data["std_score"] == 2.0  # sample stddev of 88/90/92
        assert data["issues"] == []

    async def test_issue_matrix_low_avg_low_min_high_variance(
        self, aggregator, db_session, test_tenant
    ):
        """Scores [30, 95]: avg 62.5 (<70), min 30 (<50), stddev ~46 (>20)."""
        tid = test_tenant["id"]
        db_session.add_all([_event(tid, emq=30.0), _event(tid, emq=95.0)])
        await db_session.flush()

        data = await aggregator.get_aggregate_emq(tid)

        assert data["aggregate_score"] == 62.5
        issues = data["issues"]
        assert len(issues) == 3
        assert any("CDP EMQ below target: 62.5" in i for i in issues)
        assert any("min EMQ 30.0" in i for i in issues)
        assert any("High EMQ variance" in i for i in issues)

    async def test_stale_data_flagged_when_no_events_last_24h(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        three_days_ago = datetime.now(UTC) - timedelta(days=3)
        db_session.add_all(
            [
                _event(tid, emq=85.0, received_at=three_days_ago),
                _event(tid, emq=87.0, received_at=three_days_ago),
            ]
        )
        await db_session.flush()

        data = await aggregator.get_aggregate_emq(tid)

        assert data["event_count"] == 2
        assert data["recent_event_count"] == 0
        assert data["issues"] == ["No CDP events in last 24 hours - data may be stale"]

    async def test_lookback_window_excludes_older_events(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _event(
                    tid, emq=40.0, received_at=datetime.now(UTC) - timedelta(days=10)
                ),
                _event(tid, emq=90.0),
            ]
        )
        await db_session.flush()

        default_window = await aggregator.get_aggregate_emq(tid)
        assert default_window["event_count"] == 1
        assert default_window["avg_score"] == 90.0

        wide_window = await aggregator.get_aggregate_emq(tid, lookback_days=15)
        assert wide_window["event_count"] == 2
        assert wide_window["avg_score"] == 65.0
        assert wide_window["lookback_days"] == 15
        assert any("min EMQ 40.0" in i for i in wide_window["issues"])

    async def test_null_emq_events_excluded_from_stats_but_counted_recent(
        self, aggregator, db_session, test_tenant
    ):
        """An event without an EMQ score contributes to recency but not stats,
        so the tenant falls back to the default aggregate."""
        tid = test_tenant["id"]
        db_session.add(_event(tid, emq=None))
        await db_session.flush()

        data = await aggregator.get_aggregate_emq(tid)

        assert data["event_count"] == 0
        assert data["recent_event_count"] == 1
        assert data["aggregate_score"] == 75.0
        assert data["issues"] == [
            "No CDP events in analysis period - using default EMQ"
        ]

    async def test_explicit_target_date_in_past_excludes_todays_events(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(_event(tid, emq=90.0))  # received now
        await db_session.flush()

        past = datetime.now(UTC).date() - timedelta(days=30)
        data = await aggregator.get_aggregate_emq(tid, target_date=past)

        assert data["event_count"] == 0
        assert data["aggregate_score"] == 75.0


# =============================================================================
# get_emq_trend
# =============================================================================


class TestGetEmqTrend:
    async def test_daily_grouping_and_ordering(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        now = datetime.now(UTC)
        db_session.add_all(
            [
                _event(tid, emq=90.0, received_at=now),
                _event(tid, emq=80.0, received_at=now),
                _event(tid, emq=70.0, received_at=now - timedelta(days=1)),
                _event(tid, emq=60.0, received_at=now - timedelta(days=5)),
                # null EMQ excluded from the trend entirely
                _event(tid, emq=None, received_at=now),
                # outside the 30-day window
                _event(tid, emq=10.0, received_at=now - timedelta(days=40)),
            ]
        )
        await db_session.flush()

        trend = await aggregator.get_emq_trend(tid, days=30)

        assert len(trend) == 3
        # Ascending by date: 5 days ago, yesterday, today
        assert trend[0]["avg_emq"] == 60.0
        assert trend[0]["event_count"] == 1
        assert trend[1]["avg_emq"] == 70.0
        assert trend[2]["avg_emq"] == 85.0  # (90 + 80) / 2
        assert trend[2]["event_count"] == 2
        assert trend[0]["date"] == str((now - timedelta(days=5)).date())

    async def test_empty_tenant_returns_empty_list(self, aggregator, test_tenant):
        trend = await aggregator.get_emq_trend(test_tenant["id"])
        assert trend == []


# =============================================================================
# get_profile_quality_breakdown
# =============================================================================


class TestProfileQualityBreakdown:
    async def test_stage_distribution_and_resolution_rate(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _profile(tid, stage="anonymous", total_events=2),
                _profile(tid, stage="anonymous", total_events=4),
                _profile(tid, stage="known", total_events=10),
                _profile(tid, stage="customer", total_events=20),
            ]
        )
        await db_session.flush()

        data = await aggregator.get_profile_quality_breakdown(tid)

        assert data["total_profiles"] == 4
        assert data["stages"]["anonymous"]["count"] == 2
        assert data["stages"]["anonymous"]["avg_events"] == 3.0
        assert data["stages"]["anonymous"]["percentage"] == 50.0
        assert data["stages"]["known"]["count"] == 1
        assert data["stages"]["known"]["percentage"] == 25.0
        assert data["stages"]["customer"]["avg_events"] == 20.0
        # (known 1 + customer 1) / 4
        assert data["identity_resolution_rate"] == 50.0

    async def test_empty_tenant(self, aggregator, test_tenant):
        data = await aggregator.get_profile_quality_breakdown(test_tenant["id"])

        assert data["total_profiles"] == 0
        assert data["stages"] == {}
        assert data["identity_resolution_rate"] == 0


# =============================================================================
# get_consent_metrics
# =============================================================================


class TestConsentMetrics:
    async def test_zero_profiles_short_circuits(self, aggregator, test_tenant):
        data = await aggregator.get_consent_metrics(test_tenant["id"])

        assert data == {
            "consent_rate": 0,
            "profiles_with_consent": 0,
            "total_profiles": 0,
            "consent_by_type": {},
        }

    async def test_consent_rates_by_type_and_distinct_profiles(
        self, aggregator, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        p1 = _profile(tid, stage="known")
        p2 = _profile(tid, stage="customer")
        p3 = _profile(tid, stage="anonymous")
        db_session.add_all([p1, p2, p3])
        await db_session.flush()

        db_session.add_all(
            [
                _consent(tid, p1.id, consent_type="marketing", granted=True),
                _consent(tid, p1.id, consent_type="analytics", granted=False),
                _consent(tid, p2.id, consent_type="marketing", granted=False),
                # p3 has no consent records at all
            ]
        )
        await db_session.flush()

        data = await aggregator.get_consent_metrics(tid)

        assert data["total_profiles"] == 3
        assert data["profiles_with_consent"] == 1  # only p1 has a grant
        assert data["consent_rate"] == 33.3
        assert data["consent_by_type"]["marketing"] == {
            "total": 2,
            "granted": 1,
            "rate": 50.0,
        }
        assert data["consent_by_type"]["analytics"] == {
            "total": 1,
            "granted": 0,
            "rate": 0.0,
        }

    async def test_all_profiles_consented(self, aggregator, db_session, test_tenant):
        tid = test_tenant["id"]
        p1 = _profile(tid, stage="known")
        p2 = _profile(tid, stage="customer")
        db_session.add_all([p1, p2])
        await db_session.flush()
        db_session.add_all(
            [
                _consent(tid, p1.id, granted=True),
                _consent(tid, p2.id, granted=True),
            ]
        )
        await db_session.flush()

        data = await aggregator.get_consent_metrics(tid)

        assert data["consent_rate"] == 100.0
        assert data["consent_by_type"]["marketing"]["rate"] == 100.0


# =============================================================================
# calculate_cdp_contribution (pure scoring ladder)
# =============================================================================


class TestCalculateCdpContribution:
    async def test_all_components_at_top_band(self, aggregator):
        score, issues = aggregator.calculate_cdp_contribution(
            aggregate_emq=90.0,
            identity_resolution_rate=60.0,
            recent_event_count=150,
            consent_rate=80.0,
        )
        # 90*0.5 + 100*0.25 + 100*0.15 + 100*0.10
        assert score == 95.0
        assert issues == []

    async def test_mid_band_components(self, aggregator):
        score, issues = aggregator.calculate_cdp_contribution(
            aggregate_emq=80.0,
            identity_resolution_rate=35.0,
            recent_event_count=50,
            consent_rate=50.0,
        )
        # emq 40; resolution 75*0.25=18.75; recency 85*0.15=12.75; consent 75*0.1=7.5
        assert score == 79.0
        assert issues == []

    async def test_low_band_components_emit_all_issues(self, aggregator):
        score, issues = aggregator.calculate_cdp_contribution(
            aggregate_emq=60.0,
            identity_resolution_rate=10.0,
            recent_event_count=0,
            consent_rate=10.0,
        )
        # emq 30; resolution 25*0.25=6.25; recency 40*0.15=6; consent 16.67*0.1=1.67
        assert score == pytest.approx(43.9, abs=0.05)
        assert len(issues) == 3
        assert any("Low identity resolution: 10.0%" in i for i in issues)
        assert any("No recent CDP events" in i for i in issues)
        assert any("Low consent rate: 10.0%" in i for i in issues)

    async def test_consent_between_20_and_30_scores_low_without_issue(self, aggregator):
        score, issues = aggregator.calculate_cdp_contribution(
            aggregate_emq=70.0,
            identity_resolution_rate=55.0,
            recent_event_count=120,
            consent_rate=25.0,
        )
        # emq 35 + resolution 25 + recency 15 + consent 41.67*0.1=4.17
        assert score == pytest.approx(79.2, abs=0.05)
        assert issues == []

    async def test_resolution_boundaries(self, aggregator):
        # Exactly 50 -> full resolution score
        score_hi, _ = aggregator.calculate_cdp_contribution(
            aggregate_emq=0.0,
            identity_resolution_rate=50.0,
            recent_event_count=200,
            consent_rate=100.0,
        )
        assert score_hi == 0.0 + 25.0 + 15.0 + 10.0

        # Exactly 20 -> bottom of the moderate ladder (score 50)
        score_mid, issues_mid = aggregator.calculate_cdp_contribution(
            aggregate_emq=0.0,
            identity_resolution_rate=20.0,
            recent_event_count=200,
            consent_rate=100.0,
        )
        assert score_mid == 12.5 + 15.0 + 10.0
        assert issues_mid == []

    async def test_recency_partial_credit_scales_with_count(self, aggregator):
        score_one, issues = aggregator.calculate_cdp_contribution(
            aggregate_emq=0.0,
            identity_resolution_rate=50.0,
            recent_event_count=1,
            consent_rate=70.0,
        )
        # recency = 70 + (1/100)*30 = 70.3 -> 10.545 component
        assert score_one == pytest.approx(25.0 + 10.545 + 10.0, abs=0.05)
        assert issues == []


# =============================================================================
# get_cdp_emq_for_signal_health (end-to-end composition)
# =============================================================================


class TestGetCdpEmqForSignalHealth:
    async def test_empty_tenant_composition(self, db_session, test_tenant):
        data = await get_cdp_emq_for_signal_health(db_session, test_tenant["id"])

        # aggregate 75 -> 37.5; resolution 0 -> 0; recency 40 -> 6; consent 0 -> 0
        assert data["cdp_score"] == 43.5
        assert data["aggregate_emq"] == 75.0
        assert data["event_count"] == 0
        assert data["profile_count"] == 0
        assert data["identity_resolution_rate"] == 0
        assert data["consent_rate"] == 0
        assert data["consent_by_type"] == {}
        assert data["profile_stages"] == {}
        # 1 aggregate issue + resolution + stale + consent issues
        assert len(data["issues"]) == 4
        assert data["issues"][0] == (
            "No CDP events in analysis period - using default EMQ"
        )

    async def test_populated_tenant_composition(self, db_session, test_tenant):
        tid = test_tenant["id"]
        p1 = _profile(tid, stage="known", total_events=3)
        p2 = _profile(tid, stage="customer", total_events=5)
        db_session.add_all([p1, p2])
        await db_session.flush()

        db_session.add_all(
            [
                _consent(tid, p1.id, granted=True),
                _consent(tid, p2.id, granted=True),
            ]
        )
        for _ in range(3):
            db_session.add(_event(tid, emq=88.0, profile_id=p1.id))
        for _ in range(2):
            db_session.add(_event(tid, emq=92.0, profile_id=p2.id))
        await db_session.flush()

        data = await get_cdp_emq_for_signal_health(db_session, tid)

        # aggregate = (88*3 + 92*2)/5 = 89.6 -> 44.8
        # resolution 100 -> 25; recency 70 + 5/100*30 = 71.5 -> 10.725
        # consent 100 -> 10  => 90.525 -> 90.5
        assert data["aggregate_emq"] == 89.6
        assert data["identity_resolution_rate"] == 100.0
        assert data["consent_rate"] == 100.0
        assert data["event_count"] == 5
        assert data["profile_count"] == 2
        assert data["cdp_score"] == pytest.approx(90.5, abs=0.05)
        assert data["issues"] == []
        assert set(data["profile_stages"]) == {"known", "customer"}
        assert data["consent_by_type"]["marketing"]["granted"] == 2
