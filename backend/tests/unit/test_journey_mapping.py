# =============================================================================
# Stratum AI - Journey Mapping unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.journey_mapping.

Pure cross-channel journey assembly + attribution, no I/O. Covers the
build_journey_map entry point: per-platform first/last/assist attribution,
assisted/direct revenue split, journey-path generation, and entry/closing
channel selection.
"""

import pytest

from app.analytics.logic.journey_mapping import JourneyMapResponse, build_journey_map

pytestmark = pytest.mark.unit


def _campaign(
    platform, spend=1000, revenue=5000, conversions=100, impressions=50000, clicks=2000
):
    return {
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
        "impressions": impressions,
        "clicks": clicks,
    }


class TestBuildJourneyMap:
    def test_empty(self):
        resp = build_journey_map([])
        assert isinstance(resp, JourneyMapResponse)
        assert "No campaign data" in resp.summary

    def test_meta_attribution_split(self):
        resp = build_journey_map([_campaign("meta", revenue=5000)])
        meta = next(c for c in resp.channel_contributions if c.platform == "Meta")
        assert meta.first_touch_pct == 35.0
        assert meta.last_touch_pct == 25.0
        assert meta.assist_pct == 40.0
        assert meta.assisted_revenue == 2000.0  # 5000 * 40%
        assert meta.direct_revenue == 1250.0  # 5000 * 25%

    def test_google_attribution_split(self):
        resp = build_journey_map([_campaign("google")])
        g = next(c for c in resp.channel_contributions if c.platform == "Google")
        assert g.first_touch_pct == 20.0
        assert g.last_touch_pct == 45.0

    def test_full_structure_and_channel_selection(self):
        resp = build_journey_map(
            [_campaign("meta", spend=2000), _campaign("google", spend=1000)]
        )
        assert resp.top_paths  # journey templates generate paths
        assert resp.insights
        assert resp.total_journeys_analyzed == 200
        # meta has highest first-touch -> top entry; google highest last-touch
        assert resp.top_entry_channel == "Meta"
        assert resp.top_closing_channel == "Google"
        assert 0 <= resp.single_touch_pct <= 100
        assert resp.multi_touch_pct == pytest.approx(100 - resp.single_touch_pct)
