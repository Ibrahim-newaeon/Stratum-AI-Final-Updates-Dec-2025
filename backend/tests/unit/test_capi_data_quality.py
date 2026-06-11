# =============================================================================
# Stratum AI - CAPI Data Quality Analyzer unit tests
# =============================================================================
"""Unit tests for app.services.capi.data_quality.

Pure PII-completeness scoring, no I/O. Covers single-event analysis,
batch quality reporting (platform scores, gaps, severities, ROAS-lift
estimates, recommendations), quality-level thresholds, and live insights
with trend detection.
"""

import pytest

from app.services.capi.data_quality import (
    DataGapSeverity,
    DataQualityAnalyzer,
    PlatformQualityScore,
    QualityReport,
)

pytestmark = pytest.mark.unit


def _rich_event():
    return {
        "user_data": {
            "email": "user@example.com",
            "phone": "+15551234567",
            "external_id": "u_123",
            "fbc": "fb.1.123.abc",
            "fbp": "fb.1.456.def",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "client_ip_address": "1.2.3.4",
            "client_user_agent": "Mozilla/5.0",
            "gclid": "gclid_1",
            "ttclid": "ttclid_1",
            "zip": "12345",
            "country": "US",
        }
    }


def _poor_event():
    return {"user_data": {}}


@pytest.fixture()
def analyzer():
    return DataQualityAnalyzer()


# =============================================================================
# analyze_event
# =============================================================================
class TestAnalyzeEvent:
    def test_rich_event_high_score(self, analyzer):
        result = analyzer.analyze_event(_rich_event())
        assert result["overall_score"] >= 80
        assert result["quality_level"] == "Excellent"
        assert set(result["platform_scores"]) == {
            "meta",
            "google",
            "tiktok",
            "snapchat",
        }

    def test_poor_event_low_score(self, analyzer):
        result = analyzer.analyze_event(_poor_event())
        assert result["overall_score"] == 0.0
        assert result["quality_level"] == "Poor"
        assert result["user_data_fields"] == []


# =============================================================================
# analyze_batch
# =============================================================================
class TestAnalyzeBatch:
    def test_rich_batch_excellent_no_gaps(self, analyzer):
        report = analyzer.analyze_batch([_rich_event()] * 5)
        assert isinstance(report, QualityReport)
        assert report.overall_score >= 80
        meta = report.platform_scores["meta"]
        assert isinstance(meta, PlatformQualityScore)
        assert meta.event_match_quality == "Excellent"
        assert meta.data_gaps == []
        assert "em" in meta.fields_present

    def test_poor_batch_critical_gaps(self, analyzer):
        report = analyzer.analyze_batch([_poor_event()] * 5)
        assert report.overall_score == 0.0
        meta = report.platform_scores["meta"]
        assert meta.event_match_quality == "Poor"
        assert meta.data_gaps  # gaps for every weighted field
        # email weight 25, presence 0 -> critical
        email_gap = next(g for g in meta.data_gaps if g.field == "em")
        assert email_gap.severity == DataGapSeverity.CRITICAL
        assert email_gap.affected_events == 5
        assert report.data_gaps_summary["critical"] >= 1

    def test_platform_filter(self, analyzer):
        report = analyzer.analyze_batch([_rich_event()], platforms=["google"])
        assert set(report.platform_scores) == {"google"}

    def test_top_recommendations_deduped_and_ranked(self, analyzer):
        report = analyzer.analyze_batch([_poor_event()] * 5)
        recs = report.top_recommendations
        assert len(recs) <= 5
        # priorities are sequential, fields unique
        assert [r["priority"] for r in recs] == list(range(1, len(recs) + 1))
        assert len({r["field"] for r in recs}) == len(recs)

    def test_roas_improvement_estimated(self, analyzer):
        report = analyzer.analyze_batch([_poor_event()] * 3)
        # poor score -> lift toward excellent (50%)
        assert report.estimated_roas_improvement == pytest.approx(50.0)


# =============================================================================
# Quality level + ROAS lift + gap severity
# =============================================================================
class TestScoringHelpers:
    @pytest.mark.parametrize(
        "score,level",
        [
            (10, "Poor"),
            (50, "Fair"),
            (70, "Good"),
            (90, "Excellent"),
            (80, "Excellent"),
        ],
    )
    def test_quality_level(self, analyzer, score, level):
        assert analyzer._get_quality_level(score) == level

    def test_roas_lift_by_level(self, analyzer):
        assert analyzer._estimate_roas_lift(10) == pytest.approx(50.0)  # Poor->1.0
        assert analyzer._estimate_roas_lift(90) == pytest.approx(0.0)  # Excellent
        # Good multiplier 1.30 -> (1.5-1.3)/1.3*100 = 15.4
        assert analyzer._estimate_roas_lift(70) == pytest.approx(15.4, abs=0.1)

    @pytest.mark.parametrize(
        "weight,rate,expected",
        [
            (25, 0.1, DataGapSeverity.CRITICAL),  # high weight, very low presence
            (20, 0.4, DataGapSeverity.HIGH),  # weight>=15
            (10, 0.4, DataGapSeverity.MEDIUM),
            (5, 0.4, DataGapSeverity.LOW),
            (5, 0.2, DataGapSeverity.HIGH),  # presence<0.3 forces HIGH
        ],
    )
    def test_gap_severity(self, analyzer, weight, rate, expected):
        assert analyzer._get_gap_severity(weight, rate) == expected


# =============================================================================
# Live insights + trend
# =============================================================================
class TestLiveInsights:
    def test_no_data(self, analyzer):
        result = analyzer.get_live_insights([])
        assert result["status"] == "no_data"

    def test_active_insights(self, analyzer):
        result = analyzer.get_live_insights([_poor_event()] * 5, platform="meta")
        assert result["status"] == "active"
        assert result["current_score"] == 0.0
        assert result["quality_level"] == "Poor"
        assert result["action_required"] is True
        assert len(result["top_gaps"]) <= 3

    def test_healthy_no_action(self, analyzer):
        result = analyzer.get_live_insights([_rich_event()] * 5, platform="meta")
        assert result["action_required"] is False
        assert result["current_score"] >= 70

    def test_trend_insufficient_data(self, analyzer):
        assert analyzer._calculate_trend([_rich_event()] * 5, "meta") == (
            "insufficient_data"
        )

    def test_trend_improving(self, analyzer):
        # first half poor, second half rich -> improving
        events = [_poor_event()] * 6 + [_rich_event()] * 6
        assert analyzer._calculate_trend(events, "meta") == "improving"

    def test_trend_declining(self, analyzer):
        events = [_rich_event()] * 6 + [_poor_event()] * 6
        assert analyzer._calculate_trend(events, "meta") == "declining"

    def test_trend_stable(self, analyzer):
        events = [_rich_event()] * 12
        assert analyzer._calculate_trend(events, "meta") == "stable"
