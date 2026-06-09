# =============================================================================
# Stratum AI - AI Reports unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.ai_reports.

Pure aggregation + narrative generation (no DB/HTTP). Exercises the formatting
helpers, grading, platform analysis, highlights, insight/recommendation
generation, and the build_ai_report entry point across branches.
"""

import pytest

from app.analytics.logic import ai_reports as air
from app.analytics.logic.ai_reports import (
    AIReportResponse,
    PlatformBreakdown,
    build_ai_report,
)

pytestmark = pytest.mark.unit


def _campaign(cid, name, platform, spend, revenue, conversions):
    return {
        "id": cid,
        "name": name,
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Formatting helpers
# =============================================================================
class TestFormatting:
    @pytest.mark.parametrize(
        "value,expected",
        [(500.0, "$500.00"), (1_500.0, "$1.5K"), (2_000_000.0, "$2.0M")],
    )
    def test_format_currency(self, value, expected):
        assert air._format_currency(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [(500, "500"), (1_500, "1.5K"), (3_000_000, "3.0M")],
    )
    def test_format_number(self, value, expected):
        assert air._format_number(value) == expected


# =============================================================================
# Grading
# =============================================================================
class TestGrade:
    @pytest.mark.parametrize(
        "roas,spend,conv,grade,label",
        [
            (4.0, 1000, 100, "A", "Excellent"),
            (3.0, 1000, 50, "B", "Strong"),
            (2.0, 1000, 20, "C", "Average"),
            (1.0, 1000, 5, "D", "Below Average"),
            (0.5, 1000, 5, "F", "Critical"),
        ],
    )
    def test_grades(self, roas, spend, conv, grade, label):
        assert air._calculate_grade(roas, spend, conv) == (grade, label)

    def test_high_roas_low_conversions_not_grade_a(self):
        # roas>=4 but conv<100 -> falls to B (roas>=3 and conv>=50)
        assert air._calculate_grade(4.0, 1000, 50) == ("B", "Strong")


# =============================================================================
# Executive summary
# =============================================================================
class TestExecutiveSummary:
    def test_full_summary_includes_all_parts(self):
        s = air._build_executive_summary(
            total_spend=1000, total_revenue=4000, roas=4.0,
            total_conversions=100, n_campaigns=5, n_platforms=2,
            prev_spend=800, prev_revenue=3000, grade="A", grade_label="Excellent",
        )
        assert "4.00x ROAS" in s
        assert "Spend increased" in s
        assert "CPA" in s
        assert "grade: A (Excellent)" in s

    def test_no_prev_spend_omits_change(self):
        s = air._build_executive_summary(
            1000, 4000, 4.0, 100, 5, 1, 0, 0, "A", "Excellent"
        )
        assert "period-over-period" not in s
        # singular "platform" (no trailing 's') when n_platforms == 1
        assert "on 1 platform," in s

    def test_zero_conversions_omits_cpa(self):
        s = air._build_executive_summary(
            1000, 4000, 4.0, 0, 5, 2, 0, 0, "A", "Excellent"
        )
        assert "CPA" not in s

    def test_spend_decrease_direction(self):
        s = air._build_executive_summary(
            800, 3000, 3.75, 50, 5, 2, 1000, 2000, "B", "Strong"
        )
        assert "decreased" in s


# =============================================================================
# Platform analysis
# =============================================================================
class TestAnalyzePlatforms:
    def test_aggregates_and_sorts_by_spend(self):
        campaigns = [
            _campaign(1, "A", "Meta", 1000, 5000, 100),
            _campaign(2, "B", "Google", 500, 1500, 30),
            _campaign(3, "C", "Meta", 200, 800, 10),
        ]
        result = air._analyze_platforms(campaigns, total_spend=1700)
        assert [p.platform for p in result] == ["Meta", "Google"]
        meta = result[0]
        assert meta.spend == 1200
        assert meta.revenue == 5800
        assert meta.campaigns == 2
        assert meta.spend_share_pct == pytest.approx(70.6, abs=0.2)

    @pytest.mark.parametrize(
        "revenue,fragment",
        [
            (500, "Exceptional"),     # 5x
            (350, "Strong returns"),  # 3.5x
            (250, "Moderate"),        # 2.5x
            (120, "Marginal"),        # 1.2x
            (50, "Below breakeven"),  # 0.5x
        ],
    )
    def test_narrative_tiers(self, revenue, fragment):
        campaigns = [_campaign(1, "A", "Meta", 100, revenue, 10)]
        result = air._analyze_platforms(campaigns, total_spend=100)
        assert fragment in result[0].change_summary

    def test_zero_total_spend_share_is_zero(self):
        campaigns = [_campaign(1, "A", "Meta", 0, 0, 0)]
        result = air._analyze_platforms(campaigns, total_spend=0)
        assert result[0].spend_share_pct == 0


# =============================================================================
# Highlights
# =============================================================================
class TestHighlights:
    def test_top_and_bottom_ordering(self):
        campaigns = [
            _campaign(1, "Best", "Meta", 100, 600, 50),   # 6x
            _campaign(2, "Mid", "Google", 100, 250, 20),  # 2.5x
            _campaign(3, "Worst", "TikTok", 100, 50, 1),  # 0.5x
        ]
        top, bottom = air._find_highlights(campaigns)
        assert top[0].campaign_name == "Best"
        assert bottom[-1].campaign_name == "Worst"

    def test_zero_spend_skipped(self):
        campaigns = [
            _campaign(1, "Real", "Meta", 100, 300, 10),
            _campaign(2, "Free", "Meta", 0, 0, 0),
        ]
        top, _ = air._find_highlights(campaigns)
        names = {c.campaign_name for c in top}
        assert "Free" not in names

    def test_below_breakeven_insight(self):
        campaigns = [_campaign(1, "Loser", "Meta", 200, 50, 1)]  # 0.25x
        _, bottom = air._find_highlights(campaigns)
        assert "below breakeven" in bottom[-1].insight.lower()

    def test_strong_top_insight_mentions_scaling(self):
        campaigns = [_campaign(1, "Winner", "Meta", 100, 500, 50)]  # 5x
        top, _ = air._find_highlights(campaigns)
        assert "scaling" in top[0].insight.lower()


# =============================================================================
# Insights
# =============================================================================
class TestInsights:
    def test_concentration_risk(self):
        campaigns = [
            _campaign(1, "A", "Meta", 900, 1800, 50),
            _campaign(2, "B", "Google", 100, 200, 5),
        ]
        platforms = air._analyze_platforms(campaigns, 1000)
        insights = air._generate_insights(campaigns, 1000, 2000, 2.0, platforms)
        assert any("Concentration" in i.title for i in insights)

    def test_high_roas_opportunity(self):
        campaigns = [_campaign(1, "A", "Meta", 100, 500, 50)]  # 5x
        platforms = air._analyze_platforms(campaigns, 100)
        insights = air._generate_insights(campaigns, 100, 500, 5.0, platforms)
        assert any(i.category == "opportunity" for i in insights)
        assert any("ROAS Exceeds 4x" in i.title for i in insights)

    def test_low_conversion_risk(self):
        campaigns = [_campaign(1, "A", "Meta", 500, 600, 2)]  # spend>100, conv<5
        platforms = air._analyze_platforms(campaigns, 500)
        insights = air._generate_insights(campaigns, 500, 600, 1.2, platforms)
        assert any("Low Conversions" in i.title for i in insights)

    def test_below_target_roas_is_critical(self):
        campaigns = [_campaign(1, "A", "Meta", 1000, 1000, 10)]  # 1.0x
        platforms = air._analyze_platforms(campaigns, 1000)
        insights = air._generate_insights(campaigns, 1000, 1000, 1.0, platforms)
        below = [i for i in insights if "Below Target" in i.title]
        assert below and below[0].severity == "critical"

    def test_multi_platform_insight(self):
        campaigns = [
            _campaign(1, "A", "Meta", 300, 900, 30),
            _campaign(2, "B", "Google", 300, 1200, 30),
            _campaign(3, "C", "TikTok", 300, 600, 30),
        ]
        platforms = air._analyze_platforms(campaigns, 900)
        insights = air._generate_insights(campaigns, 900, 2700, 3.0, platforms)
        assert any("Cross-Platform" in i.title for i in insights)


# =============================================================================
# Recommendations
# =============================================================================
class TestRecommendations:
    def test_scale_and_cut_recommendations(self):
        campaigns = [
            _campaign(1, "Star", "Meta", 100, 500, 50),   # 5x
            _campaign(2, "Dud", "Google", 200, 50, 1),    # 0.25x
        ]
        platforms = air._analyze_platforms(campaigns, 300)
        top, bottom = air._find_highlights(campaigns)
        insights = air._generate_insights(campaigns, 300, 550, 1.83, platforms)
        recs = air._generate_recommendations(1.83, platforms, top, bottom, insights)
        assert any("Scale budget" in r for r in recs)
        assert any("Reduce or pause" in r for r in recs)
        assert len(recs) <= 5

    def test_fallback_when_no_recommendations(self):
        # Healthy single campaign, roas between 2 and 3, no risks
        campaigns = [_campaign(1, "Steady", "Meta", 100, 250, 30)]  # 2.5x
        platforms = air._analyze_platforms(campaigns, 100)
        top, bottom = air._find_highlights(campaigns)
        recs = air._generate_recommendations(2.5, platforms, top, bottom, [])
        assert recs == ["Portfolio is performing well. Continue monitoring and "
                        "consider incremental budget increases on top performers."]


# =============================================================================
# build_ai_report (entry point)
# =============================================================================
class TestBuildReport:
    def test_empty_campaigns_returns_no_data(self):
        report = build_ai_report([])
        assert isinstance(report, AIReportResponse)
        assert report.health_grade == "F"
        assert report.health_label == "No Data"
        assert "No campaign data" in report.executive_summary

    def test_full_report_structure(self):
        campaigns = [
            _campaign(1, "Alpha", "Meta", 1000, 5000, 120),
            _campaign(2, "Beta", "Google", 500, 1500, 40),
            _campaign(3, "Gamma", "TikTok", 200, 100, 2),
        ]
        report = build_ai_report(campaigns, period_label="Q1")
        assert report.period_label == "Q1"
        assert report.total_campaigns == 3
        assert report.platforms_count == 3
        assert report.overall_roas == pytest.approx(3.88, abs=0.05)
        section_types = {s.section_type for s in report.sections}
        assert {"executive_summary", "kpi_grid", "platform_breakdown",
                "recommendations"} <= section_types
        # KPI grid always has 6 KPIs
        kpi_section = next(s for s in report.sections if s.section_type == "kpi_grid")
        assert len(kpi_section.kpis) == 6
        assert report.top_recommendations

    def test_period_over_period_changes(self):
        current = [_campaign(1, "A", "Meta", 1200, 4800, 100)]
        previous = [_campaign(1, "A", "Meta", 1000, 4000, 80)]
        report = build_ai_report(current, prev_campaigns=previous)
        kpi_section = next(s for s in report.sections if s.section_type == "kpi_grid")
        spend_kpi = next(k for k in kpi_section.kpis if k.label == "Total Spend")
        assert spend_kpi.change_pct == pytest.approx(20.0, abs=0.1)
        assert spend_kpi.trend == "up"

    def test_grade_reflects_performance(self):
        strong = build_ai_report(
            [_campaign(1, "A", "Meta", 1000, 5000, 150)]  # 5x, 150 conv -> A
        )
        assert strong.health_grade == "A"
        weak = build_ai_report(
            [_campaign(1, "A", "Meta", 1000, 400, 5)]  # 0.4x -> F
        )
        assert weak.health_grade == "F"
