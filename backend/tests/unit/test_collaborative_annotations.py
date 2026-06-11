# =============================================================================
# Stratum AI - Collaborative Annotations unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.collaborative_annotations.

Pure annotation-generation logic, no I/O. Covers the empty-data path,
overall/platform/spend/strategy annotation generation, author-initial
derivation, stats aggregation, and insight generation.
"""

import pytest

from app.analytics.logic.collaborative_annotations import (
    CollaborativeAnnotationsResponse,
    build_collaborative_annotations,
)

pytestmark = pytest.mark.unit


def _campaign(platform, spend, revenue, conversions=50):
    return {
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Empty / entry contract
# =============================================================================
class TestEmpty:
    def test_no_campaigns(self):
        resp = build_collaborative_annotations([])
        assert isinstance(resp, CollaborativeAnnotationsResponse)
        assert "No campaign data" in resp.summary
        assert resp.annotations == []


# =============================================================================
# Annotation generation
# =============================================================================
class TestGeneration:
    def test_strong_roas_overall_note(self):
        # overall ROAS 4x -> strong-performance note, not pinned
        resp = build_collaborative_annotations(
            [_campaign("meta", 1000.0, 4000.0)], user_name="Ada Lovelace"
        )
        roas_note = next(a for a in resp.annotations if a.target_id == "roas")
        assert "Strong performance" in roas_note.content
        assert roas_note.pinned is False
        assert roas_note.author.name == "Stratum AI"

    def test_weak_roas_overall_note_pinned(self):
        resp = build_collaborative_annotations(
            [_campaign("meta", 1000.0, 1500.0)]  # 1.5x -> below 2 -> pinned
        )
        roas_note = next(a for a in resp.annotations if a.target_id == "roas")
        assert "Below target" in roas_note.content
        assert roas_note.pinned is True

    def test_low_platform_roas_alert(self):
        resp = build_collaborative_annotations(
            [_campaign("tiktok", 1000.0, 1000.0)]  # 1.0x < 1.5 -> alert
        )
        alert = next(a for a in resp.annotations if a.tag == "alert")
        assert alert.target_type == "platform"
        assert "below breakeven" in alert.content

    def test_high_platform_roas_strategy(self):
        resp = build_collaborative_annotations(
            [_campaign("google", 1000.0, 5000.0)]  # 5x >= 4 -> scale strategy
        )
        strat = next(
            a
            for a in resp.annotations
            if a.target_type == "platform" and a.tag == "strategy"
        )
        assert "Opportunity to scale" in strat.content
        assert strat.pinned is True

    def test_spend_note_present(self):
        resp = build_collaborative_annotations([_campaign("meta", 2500.0, 5000.0)])
        spend_note = next(a for a in resp.annotations if a.target_id == "spend")
        assert "Total spend" in spend_note.content
        assert "$2,500" in spend_note.content

    def test_author_initials_derived(self):
        resp = build_collaborative_annotations(
            [_campaign("meta", 1000.0, 5000.0)], user_name="Grace Hopper", user_id=7
        )
        spend_note = next(a for a in resp.annotations if a.target_id == "spend")
        assert spend_note.author.initials == "GH"
        assert spend_note.author.user_id == 7

    def test_default_author_when_no_name(self):
        resp = build_collaborative_annotations([_campaign("meta", 1000.0, 5000.0)])
        spend_note = next(a for a in resp.annotations if a.target_id == "spend")
        assert spend_note.author.name == "Team Member"
        assert spend_note.author.initials == "U"


# =============================================================================
# Stats + insights
# =============================================================================
class TestStatsAndInsights:
    def test_stats_aggregate(self):
        resp = build_collaborative_annotations(
            [_campaign("meta", 1000.0, 5000.0), _campaign("tiktok", 800.0, 600.0)],
            user_name="Ada Lovelace",
            user_id=3,
        )
        assert resp.stats.total == len(resp.annotations)
        assert resp.stats.pinned >= 1
        # AI (user_id 0) + the human author -> 2 contributors
        assert resp.stats.contributors == 2
        assert sum(resp.stats.by_tag.values()) == resp.stats.total

    def test_pinned_insight(self):
        resp = build_collaborative_annotations([_campaign("google", 1000.0, 5000.0)])
        assert any("pinned note" in i.title for i in resp.insights)

    def test_alert_insight(self):
        resp = build_collaborative_annotations([_campaign("tiktok", 1000.0, 1000.0)])
        alert_insight = next(i for i in resp.insights if "alert" in i.title)
        assert alert_insight.severity == "warning"

    def test_active_discussions_counted(self):
        resp = build_collaborative_annotations([_campaign("meta", 1000.0, 5000.0)])
        # roas + strategy notes carry replies -> reply_count > 0
        assert resp.active_discussions >= 2
        assert resp.team_members_active == resp.stats.contributors

    def test_summary_text(self):
        resp = build_collaborative_annotations([_campaign("meta", 1000.0, 5000.0)])
        assert "annotations across" in resp.summary
        assert "pinned" in resp.summary
