# =============================================================================
# Stratum AI - Mock Ad Network Client unit tests
# =============================================================================
"""Unit tests for app.services.mock_client.

Pure seeded data generation, no I/O. Covers deterministic seeding,
campaign generation invariants (budgets, targeting, naming), metric
correlations (spend -> impressions -> clicks -> conversions), demographic
breakdowns, time-series generation, and the async manager facade.
"""

import asyncio
from datetime import date, timedelta

import pytest

from app.models import AdPlatform, CampaignStatus
from app.services.mock_client import (
    AGE_RANGES,
    LOCATIONS,
    MockAdNetwork,
    MockAdNetworkManager,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def network():
    return MockAdNetwork(seed=1234)


# =============================================================================
# Determinism
# =============================================================================
class TestDeterminism:
    def test_same_seed_same_campaigns(self):
        a = MockAdNetwork(seed=7).generate_campaigns(tenant_id=1, count=5)
        b = MockAdNetwork(seed=7).generate_campaigns(tenant_id=1, count=5)
        assert [c.name for c in a] == [c.name for c in b]
        assert [c.metrics for c in a] == [c.metrics for c in b]

    def test_different_tenants_differ(self):
        network = MockAdNetwork(seed=7)
        a = network.generate_campaigns(tenant_id=1, count=5)
        b = network.generate_campaigns(tenant_id=2, count=5)
        assert [c.name for c in a] != [c.name for c in b]

    def test_default_seed_is_42(self):
        assert MockAdNetwork().seed == 42


# =============================================================================
# Campaign generation invariants
# =============================================================================
class TestGenerateCampaigns:
    def test_count_and_ids(self, network):
        campaigns = network.generate_campaigns(tenant_id=3, count=10)
        assert len(campaigns) == 10
        assert campaigns[0].external_id.endswith("_3_0000")
        assert campaigns[9].external_id.endswith("_3_0009")
        assert all(c.account_id.startswith("act_3_") for c in campaigns)

    def test_platform_restriction(self, network):
        campaigns = network.generate_campaigns(
            tenant_id=3, count=8, platforms=[AdPlatform.TIKTOK]
        )
        assert all(c.platform == AdPlatform.TIKTOK for c in campaigns)

    def test_budget_bounds(self, network):
        campaigns = network.generate_campaigns(tenant_id=5, count=30)
        for c in campaigns:
            assert 1000 <= c.daily_budget_cents <= 50000
            if c.lifetime_budget_cents is not None:
                assert c.lifetime_budget_cents == c.daily_budget_cents * 30

    def test_targeting_invariants(self, network):
        campaigns = network.generate_campaigns(tenant_id=5, count=30)
        for c in campaigns:
            assert c.targeting_age_min in {18, 21, 25, 30, 35}
            assert c.targeting_age_max > c.targeting_age_min
            assert 1 <= len(c.targeting_locations) <= 5
            assert all(set(loc) == {"code", "name"} for loc in c.targeting_locations)
            assert set(c.targeting_genders) <= {"male", "female", "unknown"}

    def test_completed_campaigns_have_end_date(self, network):
        campaigns = network.generate_campaigns(tenant_id=9, count=60)
        completed = [c for c in campaigns if c.status == CampaignStatus.COMPLETED]
        assert completed  # 15% of 60 makes this overwhelmingly likely
        assert all(c.end_date is not None for c in completed)
        assert all(c.end_date > c.start_date for c in completed)

    def test_linkedin_supported(self, network):
        # Regression: LINKEDIN was added to AdPlatform but not to the mock
        # templates/params maps -> KeyError on default generate_campaigns()
        campaigns = network.generate_campaigns(
            tenant_id=3, count=5, platforms=[AdPlatform.LINKEDIN]
        )
        assert all(c.platform == AdPlatform.LINKEDIN for c in campaigns)
        assert all(c.metrics["impressions"] > 0 for c in campaigns)

    def test_name_format(self, network):
        campaign = network.generate_campaigns(tenant_id=3, count=1)[0]
        parts = campaign.name.split(" | ")
        assert len(parts) == 4
        assert parts[3].startswith("Q")
        assert parts[3].endswith("-2024")


# =============================================================================
# Metric correlations
# =============================================================================
class TestMetrics:
    def test_funnel_ordering_and_derived_fields(self, network):
        campaigns = network.generate_campaigns(tenant_id=11, count=30)
        for c in campaigns:
            m = c.metrics
            assert m["total_spend_cents"] > 0
            assert m["impressions"] > 0
            assert m["clicks"] <= m["impressions"]
            assert m["conversions"] <= m["clicks"]
            if m["clicks"] > 0:
                assert m["cpc_cents"] == int(m["total_spend_cents"] / m["clicks"])
            if m["conversions"] > 0:
                assert m["cpa_cents"] == int(m["total_spend_cents"] / m["conversions"])
            assert m["roas"] == pytest.approx(
                m["revenue_cents"] / m["total_spend_cents"], abs=0.01
            )

    def test_google_never_has_video(self, network):
        campaigns = network.generate_campaigns(
            tenant_id=11, count=20, platforms=[AdPlatform.GOOGLE]
        )
        assert all(c.metrics["video_views"] is None for c in campaigns)

    def test_video_completions_bounded_by_views(self, network):
        campaigns = network.generate_campaigns(
            tenant_id=11, count=40, platforms=[AdPlatform.META, AdPlatform.TIKTOK]
        )
        with_video = [c for c in campaigns if c.metrics["video_views"]]
        assert with_video  # ~60% of campaigns
        for c in with_video:
            assert c.metrics["video_completions"] <= c.metrics["video_views"]


# =============================================================================
# Demographics
# =============================================================================
class TestDemographics:
    def test_breakdown_structure(self, network):
        campaign = network.generate_campaigns(tenant_id=13, count=1)[0]
        demo = campaign.demographics
        assert set(demo["age"]) == set(AGE_RANGES)
        assert set(demo["gender"]) == {"male", "female", "unknown"}
        assert set(demo["location"]) == set(LOCATIONS)

    def test_segment_impressions_bounded_by_total(self, network):
        campaign = network.generate_campaigns(tenant_id=13, count=1)[0]
        total = campaign.metrics["impressions"]
        age_total = sum(d["impressions"] for d in campaign.demographics["age"].values())
        # int truncation means segments sum to at most the total
        assert age_total <= total
        for d in campaign.demographics["age"].values():
            assert d["conversions"] <= d["clicks"] <= d["impressions"]


# =============================================================================
# Time series
# =============================================================================
class TestTimeSeries:
    def _series(self, network, days=14):
        start = date(2026, 5, 1)
        end = start + timedelta(days=days - 1)
        base = {
            "impressions": 140000,
            "clicks": 2800,
            "conversions": 140,
            "total_spend_cents": 140000,
            "revenue_cents": 420000,
            "video_views": 50000,
        }
        return network.generate_time_series("camp_1", start, end, base)

    def test_one_entry_per_day(self, network):
        series = self._series(network, days=14)
        assert len(series) == 14
        assert series[0]["date"] == date(2026, 5, 1)
        assert series[-1]["date"] == date(2026, 5, 14)

    def test_no_negative_values(self, network):
        for day in self._series(network):
            for key in (
                "impressions",
                "clicks",
                "conversions",
                "spend_cents",
                "revenue_cents",
            ):
                assert day[key] >= 0

    def test_video_metrics_follow_base(self, network):
        with_video = self._series(network)
        assert all("video_views" in d for d in with_video)
        assert all(d["video_completions"] <= d["video_views"] for d in with_video)

        start = date(2026, 5, 1)
        base_no_video = {
            "impressions": 1000,
            "clicks": 10,
            "conversions": 1,
            "total_spend_cents": 1000,
            "revenue_cents": 2000,
        }
        no_video = network.generate_time_series(
            "camp_2", start, start + timedelta(days=2), base_no_video
        )
        assert all("video_views" not in d for d in no_video)

    def test_deterministic_per_campaign_id(self):
        a = MockAdNetwork(seed=5)
        b = MockAdNetwork(seed=5)
        start, end = date(2026, 5, 1), date(2026, 5, 7)
        base = {
            "impressions": 7000,
            "clicks": 140,
            "conversions": 7,
            "total_spend_cents": 7000,
            "revenue_cents": 21000,
        }
        assert a.generate_time_series(
            "camp_x", start, end, base
        ) == b.generate_time_series("camp_x", start, end, base)


# =============================================================================
# Manager facade
# =============================================================================
class TestManager:
    def test_sync_all_platforms(self):
        manager = MockAdNetworkManager(tenant_id=21)
        result = asyncio.run(manager.sync_all_platforms())
        assert len(result["campaigns"]) == 25
        assert set(result["platform_status"].values()) == {"success"}
        assert result["synced_at"] is not None

    def test_get_campaign_details_roundtrip(self):
        manager = MockAdNetworkManager(tenant_id=21)
        known = manager.network.generate_campaigns(21, count=30)[0]
        found = asyncio.run(manager.get_campaign_details(known.external_id))
        assert found is not None
        assert found.name == known.name

    def test_get_campaign_details_unknown(self):
        manager = MockAdNetworkManager(tenant_id=21)
        assert asyncio.run(manager.get_campaign_details("nope_999")) is None
