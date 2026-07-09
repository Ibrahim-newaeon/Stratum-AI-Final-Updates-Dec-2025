# =============================================================================
# Stratum AI - EMQ Service Deep Integration Tests
# =============================================================================
"""DB-backed integration tests for ``app.services.emq_service``.

Covers the data-backed paths the endpoint suite (test_api_emq / test_emq_v2_api)
never reaches with seeded rows:

- ``EmqService.get_emq_score`` record path: multi-platform averaging,
  previous-day comparison, driver status/trend matrix, confidence bands,
  null-score filtering, and the attribution-variance fallback body
  (accuracy math + band selection).
- ``get_incidents`` loop body: status -> type/severity mapping, issues JSON
  parsing into title/description, EMQ impact math.
- ``get_volatility`` computed path: weekly stddev aggregation, SVI, the
  increasing/decreasing/stable trend matrix, null-stddev and null-avg weeks.
- ``get_autopilot_state`` mode matrix (normal/limited/cuts_only/frozen) and
  queued-action budget-at-risk estimate.
- ``get_impact`` computed path: per-platform ROAS aggregation, revenue impact
  estimate, zero-GA4-revenue exclusion.
- ``EmqAdminService.get_benchmarks`` percentile path + platform filter, and
  ``get_portfolio`` band bucketing across tenants.

Behaviors corrected in #540 and asserted here:
- Timestamps are valid ISO-8601 with a ``Z`` suffix (no ``+00:00Z``).
- An ``emq_score`` of exactly 0.0 is a real score (worst case), counted in
  previous-score averaging and yielding the full -80 incident impact.
- Benchmarks ``percentile`` is a real percentile rank across platform averages.
"""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.base_models import Tenant
from app.models.trust_layer import (
    FactActionsQueue,
    FactAttributionVarianceDaily,
    FactSignalHealthDaily,
    SignalHealthStatus,
)
from app.services.emq_service import EmqAdminService, EmqService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Fixed anchors so the math is deterministic and independent of run date.
TARGET = date(2026, 6, 15)
PREV = date(2026, 6, 14)
BM_DATE = date(2026, 5, 10)
PF_DATE = date(2026, 5, 12)


# =============================================================================
# Seed helpers
# =============================================================================


def _shd(
    tenant_id: int,
    d: date,
    *,
    platform: str = "meta",
    emq: float | None = 85.0,
    status: SignalHealthStatus = SignalHealthStatus.OK,
    issues: list[str] | None = None,
) -> FactSignalHealthDaily:
    return FactSignalHealthDaily(
        tenant_id=tenant_id,
        date=d,
        platform=platform,
        emq_score=emq,
        event_loss_pct=2.0,
        freshness_minutes=30,
        api_error_rate=0.5,
        status=status,
        issues=json.dumps(issues) if issues is not None else None,
    )


def _variance(
    tenant_id: int,
    d: date,
    *,
    platform: str = "meta",
    delta_pct: float = 10.0,
    platform_revenue: float = 0.0,
    ga4_revenue: float = 0.0,
    platform_conversions: int = 0,
    ga4_conversions: int = 0,
    confidence: float = 0.8,
) -> FactAttributionVarianceDaily:
    return FactAttributionVarianceDaily(
        tenant_id=tenant_id,
        date=d,
        platform=platform,
        ga4_revenue=ga4_revenue,
        platform_revenue=platform_revenue,
        revenue_delta_abs=abs(platform_revenue - ga4_revenue),
        revenue_delta_pct=delta_pct,
        ga4_conversions=ga4_conversions,
        platform_conversions=platform_conversions,
        conversion_delta_abs=abs(platform_conversions - ga4_conversions),
        conversion_delta_pct=0.0,
        confidence=confidence,
    )


async def _mk_tenant(db_session, slug: str) -> int:
    tenant = Tenant(
        name=f"EMQ {slug}",
        slug=slug,
        plan="professional",
        max_users=10,
        max_campaigns=100,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant.id


@pytest_asyncio.fixture
async def emq_service(db_session) -> EmqService:
    return EmqService(db_session)


@pytest_asyncio.fixture
async def admin_service(db_session) -> EmqAdminService:
    return EmqAdminService(db_session)


# =============================================================================
# get_emq_score — signal-health record path
# =============================================================================


class TestGetEmqScoreFromRecords:
    async def test_multi_platform_average_with_previous_day(
        self, emq_service, db_session, test_tenant
    ):
        """Score is the mean across platforms; previous day averaged the same way."""
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _shd(tid, TARGET, platform="meta", emq=80.0),
                _shd(tid, TARGET, platform="google", emq=90.0),
                _shd(tid, PREV, platform="meta", emq=78.0),
                _shd(tid, PREV, platform="google", emq=84.0),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 85.0
        assert data["previousScore"] == 81.0
        assert data["confidenceBand"] == "reliable"
        assert len(data["drivers"]) == 5
        # score (85) > previous (81) + 2 -> every driver trends up
        assert {d["trend"] for d in data["drivers"]} == {"up"}
        # Driver status matrix for base 85 avg:
        # EMR 89.25 good, PC 93.5 good, CL 72.25 warning, AA 80.75 warning,
        # DF 97.75 good.
        statuses = {d["name"]: d["status"] for d in data["drivers"]}
        assert statuses == {
            "Event Match Rate": "good",
            "Pixel Coverage": "good",
            "Conversion Latency": "warning",
            "Attribution Accuracy": "warning",
            "Data Freshness": "good",
        }
        weights = {d["name"]: d["weight"] for d in data["drivers"]}
        assert weights["Event Match Rate"] == 0.30
        assert sum(weights.values()) == pytest.approx(1.0)

    async def test_downward_trend_and_directional_band(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _shd(tid, TARGET, platform="meta", emq=70.0),
                _shd(tid, PREV, platform="meta", emq=80.0),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 70.0
        assert data["previousScore"] == 80.0
        assert data["confidenceBand"] == "directional"
        assert {d["trend"] for d in data["drivers"]} == {"down"}

    async def test_unsafe_band_and_critical_driver_status(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(
            _shd(
                tid,
                TARGET,
                platform="meta",
                emq=50.0,
                status=SignalHealthStatus.DEGRADED,
                issues=["pixel outage"],  # exercises the issues JSON parse
            )
        )
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 50.0
        assert data["confidenceBand"] == "unsafe"
        statuses = {d["name"]: d["status"] for d in data["drivers"]}
        # base 50: CL 42.5 and AA 47.5 are critical (<70)
        assert statuses["Conversion Latency"] == "critical"
        assert statuses["Attribution Accuracy"] == "critical"

    async def test_no_previous_day_falls_back_to_score_minus_two(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(_shd(tid, TARGET, platform="meta", emq=83.0))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 83.0
        assert data["previousScore"] == 81.0
        # flat: 83 is within +/-2 of the synthetic 81 previous
        assert {d["trend"] for d in data["drivers"]} == {"flat"}

    async def test_null_scores_are_skipped_in_average(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _shd(tid, TARGET, platform="meta", emq=None),
                _shd(tid, TARGET, platform="google", emq=80.0),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 80.0

    async def test_all_null_scores_return_default_response(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(_shd(tid, TARGET, platform="meta", emq=None))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 75.0
        assert data["previousScore"] == 73.0
        assert data["confidenceBand"] == "directional"

    async def test_last_updated_is_valid_iso8601_utc(
        self, emq_service, db_session, test_tenant
    ):
        """Timestamp is valid ISO-8601: tz-aware isoformat with the +00:00
        offset rendered as a ``Z`` suffix, never the invalid ``+00:00Z``."""
        tid = test_tenant["id"]
        db_session.add(_shd(tid, TARGET, platform="meta", emq=88.0))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["lastUpdated"].endswith("Z")
        assert "+00:00" not in data["lastUpdated"]
        # Parseable as ISO-8601 (Python accepts the Z suffix from 3.11+).
        datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00"))


# =============================================================================
# get_emq_score — attribution-variance fallback path
# =============================================================================


class TestGetEmqScoreFromVariance:
    async def test_variance_fallback_reliable_band(
        self, emq_service, db_session, test_tenant
    ):
        """5% variance -> accuracy 90 -> estimated EMQ 99 -> reliable."""
        tid = test_tenant["id"]
        db_session.add(_variance(tid, TARGET, delta_pct=5.0))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 99.0
        assert data["previousScore"] == 97.0
        assert data["confidenceBand"] == "reliable"
        assert len(data["drivers"]) == 5
        assert data["lastUpdated"].endswith("Z")

    async def test_variance_fallback_directional_band(
        self, emq_service, db_session, test_tenant
    ):
        """20% variance -> accuracy 60 -> estimated 66 -> directional."""
        tid = test_tenant["id"]
        db_session.add(_variance(tid, TARGET, delta_pct=20.0))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 66.0
        assert data["confidenceBand"] == "directional"

    async def test_variance_fallback_unsafe_band_and_negative_delta(
        self, emq_service, db_session, test_tenant
    ):
        """Negative deltas are abs()'d; 40% -> accuracy 20 -> 22 -> unsafe."""
        tid = test_tenant["id"]
        db_session.add(_variance(tid, TARGET, delta_pct=-40.0))
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 22.0
        assert data["confidenceBand"] == "unsafe"

    async def test_variance_fallback_averages_multiple_records(
        self, emq_service, db_session, test_tenant
    ):
        """delta 10 and 30 -> accuracies 80 and 40 -> avg 60 -> estimated 66."""
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _variance(tid, TARGET, platform="meta", delta_pct=10.0),
                _variance(tid, TARGET, platform="google", delta_pct=30.0),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_emq_score(tid, TARGET)

        assert data["score"] == 66.0

    async def test_no_data_at_all_returns_default(
        self, emq_service, db_session, test_tenant
    ):
        data = await emq_service.get_emq_score(test_tenant["id"], TARGET)

        assert data["score"] == 75.0
        assert data["previousScore"] == 73.0
        assert data["confidenceBand"] == "directional"

    async def test_records_helper_defensive_empty_guard(self, emq_service):
        """The private record calculator has its own empty-input guard
        (unreachable via get_emq_score, which falls back to variance first)."""
        data = emq_service._calculate_emq_from_records([], [])

        assert data["score"] == 75.0
        assert data["confidenceBand"] == "directional"


# =============================================================================
# get_confidence_data
# =============================================================================


class TestGetConfidenceData:
    async def test_factors_positive_for_high_score(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(_shd(tid, TARGET, platform="meta", emq=90.0))
        await db_session.flush()

        data = await emq_service.get_confidence_data(tid, TARGET)

        assert data["band"] == "reliable"
        assert data["score"] == 90.0
        assert data["thresholds"] == {"reliable": 80.0, "directional": 60.0}
        by_name = {f["name"]: f for f in data["factors"]}
        # base 90: EMR 94.5, PC 99, DF capped 100 -> positive; CL 76.5 neutral
        assert by_name["Event Match Rate"]["status"] == "positive"
        assert by_name["Pixel Coverage"]["status"] == "positive"
        assert by_name["Data Freshness"]["status"] == "positive"
        assert by_name["Conversion Latency"]["status"] == "neutral"
        # contribution = value * weight
        assert by_name["Data Freshness"]["contribution"] == pytest.approx(
            100.0 * 0.10, abs=0.1
        )

    async def test_factors_negative_for_low_score(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(_shd(tid, TARGET, platform="meta", emq=60.0))
        await db_session.flush()

        data = await emq_service.get_confidence_data(tid, TARGET)

        assert data["band"] == "directional"
        by_name = {f["name"]: f for f in data["factors"]}
        # base 60: CL 51 and AA 57 fall under 60 -> negative
        assert by_name["Conversion Latency"]["status"] == "negative"
        assert by_name["Attribution Accuracy"]["status"] == "negative"
        assert by_name["Event Match Rate"]["status"] == "neutral"


# =============================================================================
# get_incidents
# =============================================================================


class TestGetIncidents:
    async def test_status_type_severity_matrix(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _shd(
                    tid,
                    TARGET,
                    platform="meta",
                    emq=65.0,
                    status=SignalHealthStatus.CRITICAL,
                    issues=["Pixel dropped", "detail A", "detail B"],
                ),
                _shd(
                    tid,
                    TARGET - timedelta(days=1),
                    platform="google",
                    emq=None,
                    status=SignalHealthStatus.DEGRADED,
                ),
                _shd(
                    tid,
                    TARGET - timedelta(days=2),
                    platform="tiktok",
                    emq=72.0,
                    status=SignalHealthStatus.RISK,
                    issues=["Latency spike"],
                ),
                # OK rows are not incidents
                _shd(tid, TARGET, platform="snapchat", emq=90.0),
            ]
        )
        await db_session.flush()

        incidents = await emq_service.get_incidents(
            tid, TARGET - timedelta(days=7), TARGET
        )

        assert len(incidents) == 3
        # Ordered by date desc: critical (TARGET) first, risk (TARGET-2) last.
        crit, degr, risk = incidents

        assert crit["type"] == "incident_opened"
        assert crit["severity"] == "critical"
        assert crit["title"] == "Pixel dropped"
        assert crit["description"] == "detail A; detail B"
        assert crit["platform"] == "meta"
        assert crit["emqImpact"] == -15.0  # 65 - 80
        assert crit["recoveryHours"] is None
        assert crit["timestamp"].endswith("Z")

        assert degr["type"] == "degradation"
        assert degr["severity"] == "high"
        assert degr["title"] == "Signal health degraded"  # no issues JSON
        assert degr["description"] is None
        assert degr["emqImpact"] == -10.0  # null score fallback

        assert risk["type"] == "degradation"
        assert risk["severity"] == "medium"
        assert risk["title"] == "Latency spike"
        assert risk["description"] is None  # single issue -> no description

    async def test_zero_emq_score_gives_full_impact(
        self, emq_service, db_session, test_tenant
    ):
        """An emq_score of exactly 0.0 is a real (worst) score, not missing:
        impact is 0 - 80 = -80, not the -10 null fallback."""
        tid = test_tenant["id"]
        db_session.add(
            _shd(
                tid,
                TARGET,
                platform="meta",
                emq=0.0,
                status=SignalHealthStatus.CRITICAL,
            )
        )
        await db_session.flush()

        incidents = await emq_service.get_incidents(tid, TARGET, TARGET)

        assert len(incidents) == 1
        assert incidents[0]["emqImpact"] == -80.0

    async def test_out_of_range_dates_excluded(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add(
            _shd(
                tid,
                TARGET - timedelta(days=30),
                platform="meta",
                emq=50.0,
                status=SignalHealthStatus.CRITICAL,
            )
        )
        await db_session.flush()

        incidents = await emq_service.get_incidents(
            tid, TARGET - timedelta(days=7), TARGET
        )

        assert incidents == []


# =============================================================================
# get_volatility
# =============================================================================


def _seed_week(db_session, tenant_id: int, d: date, scores: list[float | None]):
    """Seed several same-day records so they land in one date_trunc week."""
    for i, s in enumerate(scores):
        platform = ["meta", "google", "tiktok", "snapchat"][i % 4]
        db_session.add(_shd(tenant_id, d, platform=platform, emq=s))


class TestGetVolatility:
    async def test_decreasing_trend(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        today = date.today()
        _seed_week(db_session, tid, today - timedelta(days=21), [50.0, 90.0])
        _seed_week(db_session, tid, today - timedelta(days=14), [60.0, 95.0])
        _seed_week(db_session, tid, today - timedelta(days=7), [70.0, 71.0])
        _seed_week(db_session, tid, today, [80.0, 81.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert data["trend"] == "decreasing"
        assert len(data["weeklyData"]) == 4
        assert data["svi"] > 0
        # oldest weeks have high stddev, newest low
        assert data["weeklyData"][0]["value"] > data["weeklyData"][-1]["value"]

    async def test_increasing_trend(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        today = date.today()
        _seed_week(db_session, tid, today - timedelta(days=21), [80.0, 81.0])
        _seed_week(db_session, tid, today - timedelta(days=14), [70.0, 71.0])
        _seed_week(db_session, tid, today - timedelta(days=7), [60.0, 95.0])
        _seed_week(db_session, tid, today, [50.0, 90.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert data["trend"] == "increasing"

    async def test_stable_trend(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        today = date.today()
        for offset in (21, 14, 7, 0):
            _seed_week(db_session, tid, today - timedelta(days=offset), [70.0, 80.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert data["trend"] == "stable"
        assert all(p["value"] == pytest.approx(7.1) for p in data["weeklyData"])

    async def test_single_row_weeks_have_null_stddev(
        self, emq_service, db_session, test_tenant
    ):
        """One record per week -> stddev NULL -> SVI falls back to 10.0."""
        tid = test_tenant["id"]
        today = date.today()
        _seed_week(db_session, tid, today - timedelta(days=7), [75.0])
        _seed_week(db_session, tid, today, [85.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert data["svi"] == 10.0
        assert [p["value"] for p in data["weeklyData"]] == [0.0, 0.0]
        assert data["trend"] == "stable"

    async def test_single_week_yields_stable_trend(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        _seed_week(db_session, tid, date.today(), [60.0, 90.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert len(data["weeklyData"]) == 1
        assert data["trend"] == "stable"

    async def test_all_null_week_excluded_from_datapoints(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        today = date.today()
        _seed_week(db_session, tid, today - timedelta(days=14), [70.0, 90.0])
        _seed_week(db_session, tid, today - timedelta(days=7), [None, None])
        _seed_week(db_session, tid, today, [75.0, 85.0])
        await db_session.flush()

        data = await emq_service.get_volatility(tid, weeks=8)

        assert len(data["weeklyData"]) == 2

    async def test_no_data_returns_synthetic_default(
        self, emq_service, db_session, test_tenant
    ):
        data = await emq_service.get_volatility(test_tenant["id"], weeks=6)

        assert data["svi"] == 15.3
        assert data["trend"] == "decreasing"
        assert len(data["weeklyData"]) == 6


# =============================================================================
# get_autopilot_state
# =============================================================================


class TestGetAutopilotState:
    async def _seed_today(self, db_session, tid: int, emq: float):
        db_session.add(_shd(tid, date.today(), platform="meta", emq=emq))
        await db_session.flush()

    async def test_normal_mode_at_high_emq(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        await self._seed_today(db_session, tid, 90.0)

        data = await emq_service.get_autopilot_state(tid)

        assert data["mode"] == "normal"
        assert data["restrictedActions"] == []
        assert "increase_budget" in data["allowedActions"]
        assert data["budgetAtRisk"] == 0.0

    async def test_limited_mode_with_default_score(
        self, emq_service, db_session, test_tenant
    ):
        """No data -> default score 75 -> limited mode."""
        data = await emq_service.get_autopilot_state(test_tenant["id"])

        assert data["mode"] == "limited"
        assert "increase_budget" in data["restrictedActions"]
        assert "pause_underperforming" in data["allowedActions"]

    async def test_cuts_only_mode(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        await self._seed_today(db_session, tid, 50.0)

        data = await emq_service.get_autopilot_state(tid)

        assert data["mode"] == "cuts_only"
        assert data["allowedActions"] == ["pause_underperforming", "reduce_budget"]

    async def test_frozen_mode(self, emq_service, db_session, test_tenant):
        tid = test_tenant["id"]
        await self._seed_today(db_session, tid, 30.0)

        data = await emq_service.get_autopilot_state(tid)

        assert data["mode"] == "frozen"
        assert data["allowedActions"] == []
        assert len(data["restrictedActions"]) == 6

    async def test_budget_at_risk_counts_only_queued_actions(
        self, emq_service, db_session, test_tenant, test_user
    ):
        tid = test_tenant["id"]

        def _action(status: str) -> FactActionsQueue:
            return FactActionsQueue(
                tenant_id=tid,
                date=date.today(),
                action_type="budget_increase",
                entity_type="campaign",
                entity_id="c1",
                platform="meta",
                action_json=json.dumps({"amount": 100}),
                status=status,
                created_by_user_id=test_user["id"],
            )

        db_session.add_all([_action("queued"), _action("queued"), _action("applied")])
        await db_session.flush()

        data = await emq_service.get_autopilot_state(tid)

        assert data["budgetAtRisk"] == 10000.0  # 2 queued * 5000


# =============================================================================
# get_impact
# =============================================================================


class TestGetImpact:
    async def test_per_platform_roas_impact_math(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                # meta split across two rows to prove aggregation:
                # totals platform 3000 / ga4 1000 -> ROAS 3.0, est 3.45
                _variance(
                    tid,
                    TARGET,
                    platform="meta",
                    platform_revenue=1500.0,
                    ga4_revenue=500.0,
                    platform_conversions=10,
                    ga4_conversions=12,
                    confidence=0.8,
                ),
                _variance(
                    tid,
                    TARGET - timedelta(days=1),
                    platform="meta",
                    platform_revenue=1500.0,
                    ga4_revenue=500.0,
                    platform_conversions=10,
                    ga4_conversions=12,
                    confidence=0.9,
                ),
                # tiktok has zero GA4 revenue -> excluded from breakdown
                _variance(
                    tid,
                    TARGET,
                    platform="tiktok",
                    platform_revenue=800.0,
                    ga4_revenue=0.0,
                    confidence=0.5,
                ),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_impact(tid, TARGET - timedelta(days=7), TARGET)

        assert data["currency"] == "USD"
        assert len(data["breakdown"]) == 1
        meta = data["breakdown"][0]
        assert meta["platform"] == "Meta"
        assert meta["actualRoas"] == 3.0
        assert meta["estimatedRoas"] == 3.45
        assert meta["confidence"] == pytest.approx(0.85)
        # (3.45 - 3.0) * 1000 * 0.1 = 45.0
        assert meta["revenueImpact"] == pytest.approx(45.0)
        assert data["totalImpact"] == pytest.approx(45.0)

    async def test_multiple_platforms_sum_total_impact(
        self, emq_service, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        db_session.add_all(
            [
                _variance(
                    tid,
                    TARGET,
                    platform="meta",
                    platform_revenue=3000.0,
                    ga4_revenue=1000.0,
                    confidence=0.8,
                ),
                _variance(
                    tid,
                    TARGET,
                    platform="google",
                    platform_revenue=4000.0,
                    ga4_revenue=2000.0,
                    confidence=0.9,
                ),
            ]
        )
        await db_session.flush()

        data = await emq_service.get_impact(tid, TARGET, TARGET)

        assert len(data["breakdown"]) == 2
        platforms = {b["platform"] for b in data["breakdown"]}
        assert platforms == {"Meta", "Google"}
        # meta 45.0 + google (2.3-2.0)*2000*0.1 = 60.0 -> 105.0
        assert data["totalImpact"] == pytest.approx(105.0)

    async def test_no_records_returns_default_impact(
        self, emq_service, db_session, test_tenant
    ):
        data = await emq_service.get_impact(test_tenant["id"], TARGET, TARGET)

        assert data["totalImpact"] == 24350.00
        assert len(data["breakdown"]) == 3


# =============================================================================
# EmqAdminService.get_benchmarks
# =============================================================================


class TestAdminBenchmarks:
    async def test_percentiles_across_tenants(self, admin_service, db_session):
        t1 = await _mk_tenant(db_session, "emq-bm-a")
        t2 = await _mk_tenant(db_session, "emq-bm-b")
        db_session.add_all(
            [
                _shd(t1, BM_DATE, platform="meta", emq=60.0),
                _shd(t1, BM_DATE, platform="meta", emq=70.0),
                _shd(t2, BM_DATE, platform="meta", emq=80.0),
                _shd(t2, BM_DATE, platform="meta", emq=90.0),
                _shd(t2, BM_DATE, platform="google", emq=50.0),
                # null EMQ ignored
                _shd(t1, BM_DATE, platform="meta", emq=None),
            ]
        )
        await db_session.flush()

        benchmarks = await admin_service.get_benchmarks(target_date=BM_DATE)

        by_platform = {b["platform"]: b for b in benchmarks}
        assert set(by_platform) == {"Meta", "Google"}
        meta = by_platform["Meta"]
        # percentile_cont over [60, 70, 80, 90]
        assert meta["p25"] == 67.5
        assert meta["p50"] == 75.0
        assert meta["p75"] == 82.5
        assert meta["tenantScore"] == 75.0
        # Real percentile rank: share of platform averages at or below this
        # platform's average. Meta avg 75 vs Google avg 50 -> both <= 75 -> 100.
        assert meta["percentile"] == 100.0

        google = by_platform["Google"]
        assert google["p25"] == google["p50"] == google["p75"] == 50.0
        # Google avg 50 -> only itself is <= 50 of the two -> 50th percentile.
        assert google["percentile"] == 50.0

    async def test_platform_filter_is_case_insensitive(self, admin_service, db_session):
        t1 = await _mk_tenant(db_session, "emq-bm-filter")
        db_session.add_all(
            [
                _shd(t1, BM_DATE, platform="meta", emq=75.0),
                _shd(t1, BM_DATE, platform="google", emq=85.0),
            ]
        )
        await db_session.flush()

        benchmarks = await admin_service.get_benchmarks(
            target_date=BM_DATE, platform="META"
        )

        assert len(benchmarks) == 1
        assert benchmarks[0]["platform"] == "Meta"

    async def test_default_target_date_is_today(self, admin_service):
        """Omitting target_date defaults to today (empty scratch DB -> defaults)."""
        benchmarks = await admin_service.get_benchmarks()

        assert isinstance(benchmarks, list)
        assert len(benchmarks) >= 1

    async def test_no_rows_returns_defaults(self, admin_service):
        benchmarks = await admin_service.get_benchmarks(target_date=date(2020, 1, 1))

        assert len(benchmarks) == 4
        assert {b["platform"] for b in benchmarks} == {
            "Meta",
            "Google Ads",
            "TikTok",
            "LinkedIn",
        }

    async def test_no_rows_with_platform_filter_returns_matching_default(
        self, admin_service
    ):
        benchmarks = await admin_service.get_benchmarks(
            target_date=date(2020, 1, 1), platform="tiktok"
        )
        assert len(benchmarks) == 1
        assert benchmarks[0]["platform"] == "TikTok"

        none_match = await admin_service.get_benchmarks(
            target_date=date(2020, 1, 1), platform="pinterest"
        )
        assert none_match == []


# =============================================================================
# EmqAdminService.get_portfolio
# =============================================================================


class TestAdminPortfolio:
    async def test_band_bucketing_across_tenants(self, admin_service, db_session):
        t_reliable = await _mk_tenant(db_session, "emq-pf-reliable")
        t_directional = await _mk_tenant(db_session, "emq-pf-directional")
        t_unsafe = await _mk_tenant(db_session, "emq-pf-unsafe")
        db_session.add_all(
            [
                _shd(t_reliable, PF_DATE, platform="meta", emq=85.0),
                _shd(t_directional, PF_DATE, platform="meta", emq=70.0),
                _shd(t_unsafe, PF_DATE, platform="meta", emq=50.0),
            ]
        )
        await db_session.flush()

        data = await admin_service.get_portfolio(target_date=PF_DATE)

        assert data["totalTenants"] == 3
        assert data["byBand"] == {"reliable": 1, "directional": 1, "unsafe": 1}
        # (directional 1 + unsafe 1 * 2) * 50000
        assert data["atRiskBudget"] == 150000
        assert data["avgScore"] == 68.3  # (85+70+50)/3 rounded
        assert len(data["topIssues"]) == 5
        assert data["topIssues"][0] == {
            "driver": "iOS Signal Loss",
            "affectedTenants": 1,  # int(3 * 0.5)
        }

    async def test_no_rows_returns_default_portfolio(self, admin_service):
        data = await admin_service.get_portfolio(target_date=date(2020, 1, 1))

        assert data["totalTenants"] == 156
        assert data["byBand"] == {"reliable": 89, "directional": 52, "unsafe": 15}
        assert data["avgScore"] == 76.8

    async def test_default_target_date_is_today(self, admin_service):
        """Omitting target_date defaults to today."""
        data = await admin_service.get_portfolio()

        assert "totalTenants" in data
        assert "byBand" in data
