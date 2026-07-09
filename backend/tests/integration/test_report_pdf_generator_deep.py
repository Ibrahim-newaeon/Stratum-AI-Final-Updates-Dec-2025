# =============================================================================
# Stratum AI - PDF Report Generator Deep Integration Tests (#342 Batch 4)
# =============================================================================
"""Deep coverage for ``app.services.reporting.pdf_generator``.

The generator renders plain dicts into HTML and (when weasyprint's native
libraries are present) into PDF bytes under ``/tmp/reports/{tenant}/``.
``ReportTemplate`` instances are constructed in memory — the generator only
reads ``name`` / ``description`` / ``report_type`` / ``config`` — so no DB
rows are needed here (the shared conftest still migrates the scratch DB).

Regression coverage for the #537 fix:

* BUG-5 pdf_generator.py:175-184 — the weasyprint fallback now catches
  ``(ImportError, OSError)``. In the shipped Docker image ``import
  weasyprint`` raises ``OSError`` ("cannot load library 'libgobject-2.0-0'")
  because the native pango/gobject libraries are not installed; the widened
  except means PDF generation degrades gracefully to the documented HTML
  fallback instead of failing every ReportFormat.PDF execution.

For deterministic branch coverage the real-PDF path uses a stub weasyprint
module injected into ``sys.modules`` (the real library cannot load in this
container), and the HTML-fallback path uses ``sys.modules['weasyprint'] =
None`` to force ``ImportError``.
"""

import os
import sys
import types
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.models.reporting import ReportTemplate, ReportType
from app.services.reporting.pdf_generator import BASE_TEMPLATE, PDFGenerator

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

TODAY = date(2026, 7, 1)
START = TODAY - timedelta(days=6)

TENANT_ID = 424242


# =============================================================================
# Helpers
# =============================================================================


def _weasyprint_import_error():
    """Return the exception ``import weasyprint`` currently raises (or None)."""
    try:
        import weasyprint  # noqa: F401

        return None
    except Exception as exc:  # ImportError or OSError (missing native libs)
        return exc


_WEASYPRINT_ERROR = _weasyprint_import_error()


def _template(report_type, config=None, name="Deep Report", description="A report"):
    """In-memory template; never added to a session."""
    return ReportTemplate(
        name=name,
        description=description,
        report_type=report_type,
        config=config if config is not None else {},
    )


def _stub_weasyprint(captured: dict):
    """A fake weasyprint module that writes deterministic PDF bytes."""
    module = types.ModuleType("weasyprint")

    class HTML:
        def __init__(self, string):
            captured["html"] = string
            self._string = string

        def write_pdf(self, target):
            with open(target, "wb") as f:
                f.write(b"%PDF-1.4 stub\n")

    module.HTML = HTML
    return module


def _period():
    return {"start_date": START.isoformat(), "end_date": TODAY.isoformat()}


def _campaign_data():
    """Covers roas classes good (>=2), neutral (>=1), bad (<1), zero-spend
    platform, and the top-10 slice (11 campaigns, one must be dropped)."""
    campaigns = [
        {
            "name": f"Filler {i}",
            "platform": "meta",
            "spend": 10.0,
            "revenue": 100.0 + i,
            "roas": 2.5,
            "conversions": 1,
        }
        for i in range(8)
    ]
    campaigns += [
        {
            "name": "Top Dog",
            "platform": "meta",
            "spend": 100.0,
            "revenue": 9000.0,
            "roas": 90.0,  # metric-good
            "conversions": 42,
        },
        {
            "name": "Middling",
            "platform": "google",
            "spend": 100.0,
            "revenue": 150.0,
            "roas": 1.5,  # metric-neutral
            "conversions": 3,
        },
        {
            "name": "Dud Eleven",
            "platform": "tiktok",
            "spend": 100.0,
            "revenue": 10.0,
            "roas": 0.1,  # metric-bad — lowest revenue -> sliced out of top 10
            "conversions": 0,
        },
    ]
    return {
        "summary": {
            "total_spend": 1080.0,
            "total_revenue": 10000.0,
            "overall_roas": 9.26,
            "total_conversions": 53,
        },
        "by_platform": {
            "meta": {"spend": 180.0, "revenue": 9800.0, "conversions": 50},
            "google": {"spend": 0, "revenue": 150.0, "conversions": 3},  # roas 0
        },
        "campaigns": campaigns,
        "period": _period(),
    }


# =============================================================================
# generate(): file output branches
# =============================================================================


class TestGenerateFileOutput:
    async def test_writes_pdf_via_weasyprint(self, monkeypatch):
        captured: dict = {}
        monkeypatch.setitem(sys.modules, "weasyprint", _stub_weasyprint(captured))

        template = _template(
            ReportType.PROFIT_ROAS,
            config={"branding": {"primary_color": "#ff5a1f"}},
        )
        data = {
            "summary": {
                "total_revenue": 1000.0,
                "total_gross_profit": 600.0,
                "gross_margin_pct": 60.0,
                "profit_roas": 1.2,
            },
            "period": _period(),
        }

        generator = PDFGenerator(TENANT_ID)
        execution_id = uuid4()
        file_path, file_size = await generator.generate(template, data, execution_id)

        assert file_path == f"/tmp/reports/{TENANT_ID}/{execution_id}.pdf"
        assert os.path.getsize(file_path) == file_size > 0
        with open(file_path, "rb") as f:
            assert f.read().startswith(b"%PDF")

        # branding color flowed into the rendered HTML
        assert generator.primary_color == "#ff5a1f"
        assert "#ff5a1f" in captured["html"]
        assert "Deep Report" in captured["html"]

    async def test_falls_back_to_html_when_weasyprint_missing(self, monkeypatch):
        # None in sys.modules forces a plain ImportError on import.
        monkeypatch.setitem(sys.modules, "weasyprint", None)

        template = _template(ReportType.PIPELINE_METRICS, name="Fallback Report")
        data = {
            "summary": {
                "total_leads": 10,
                "total_mqls": 5,
                "total_sqls": 2,
                "total_won": 1,
                "total_pipeline_value": 2500.0,
                "total_won_revenue": 1000.0,
            },
            "funnel": {"lead_to_mql": 50.0, "mql_to_sql": 40.0, "sql_to_won": 50.0},
            "period": _period(),
        }

        generator = PDFGenerator(TENANT_ID)
        execution_id = uuid4()
        file_path, file_size = await generator.generate(template, data, execution_id)

        assert file_path == f"/tmp/reports/{TENANT_ID}/{execution_id}.html"
        assert os.path.getsize(file_path) == file_size > 0
        with open(file_path, encoding="utf-8") as f:
            html = f.read()
        assert "Fallback Report" in html
        assert "#2563eb" in html  # default branding color (no branding config)

    @pytest.mark.skipif(
        _WEASYPRINT_ERROR is None or isinstance(_WEASYPRINT_ERROR, ImportError),
        reason="weasyprint imports cleanly (or is absent); the OSError "
        "fallback path is not reproducible in this environment",
    )
    async def test_native_lib_oserror_falls_back_to_html(self):
        """BUG-5 fixed: in the shipped image `from weasyprint import HTML`
        raises OSError (missing libgobject/pango); the widened
        ``(ImportError, OSError)`` except now engages the HTML fallback
        instead of crashing generate()."""
        template = _template(ReportType.CUSTOM, name="OSError Repro")
        generator = PDFGenerator(TENANT_ID)

        file_path, file_size = await generator.generate(
            template, {"period": _period()}, uuid4()
        )

        assert file_path.endswith(".html")
        assert os.path.getsize(file_path) == file_size > 0
        with open(file_path, encoding="utf-8") as f:
            assert "OSError Repro" in f.read()


# =============================================================================
# _generate_html dispatch + header/footer chrome
# =============================================================================


class TestGenerateHtmlDispatch:
    def _html(self, report_type, data, **template_kwargs):
        generator = PDFGenerator(TENANT_ID)
        return generator._generate_html(_template(report_type, **template_kwargs), data)

    @pytest.mark.parametrize(
        "report_type,data,marker",
        [
            (ReportType.CAMPAIGN_PERFORMANCE, _campaign_data(), "Performance Summary"),
            (
                ReportType.ATTRIBUTION_SUMMARY,
                {
                    "summary": {
                        "total_deals": 2,
                        "total_revenue": 1500.0,
                        "avg_deal_size": 750.0,
                    },
                    "by_platform": {"meta": {"deals": 2, "revenue": 1500.0}},
                    "period": _period(),
                },
                "Attribution Summary",
            ),
            (
                ReportType.PACING_STATUS,
                {
                    "summary": {
                        "total_targets": 1,
                        "on_track": 1,
                        "at_risk": 0,
                        "off_track": 0,
                    },
                    "targets": [],
                    "recent_alerts": [],
                    "period": _period(),
                },
                "Pacing Overview",
            ),
            (
                ReportType.PROFIT_ROAS,
                {
                    "summary": {
                        "total_revenue": 1.0,
                        "total_gross_profit": 1.0,
                        "gross_margin_pct": 1.0,
                        "profit_roas": 1.0,
                    },
                    "period": _period(),
                },
                "Profit & ROAS Summary",
            ),
            (
                ReportType.PIPELINE_METRICS,
                {
                    "summary": {
                        "total_leads": 0,
                        "total_mqls": 0,
                        "total_sqls": 0,
                        "total_won": 0,
                        "total_pipeline_value": 0,
                        "total_won_revenue": 0,
                    },
                    "funnel": {},
                    "period": _period(),
                },
                "Pipeline Summary",
            ),
            (
                ReportType.EXECUTIVE_SUMMARY,
                {"highlights": {}, "period": _period()},
                "Executive Highlights",
            ),
            (ReportType.CUSTOM, {"any": "thing", "period": _period()}, "Report Data"),
        ],
    )
    def test_each_report_type_renders_its_section(self, report_type, data, marker):
        html = self._html(report_type, data)
        assert marker in html
        # header chrome
        assert "Deep Report" in html
        assert "A report" in html
        assert f"Report Period: {START.isoformat()} to {TODAY.isoformat()}" in html
        # footer chrome
        assert "Generated by Stratum AI on" in html

    def test_missing_period_renders_na_range(self):
        html = self._html(ReportType.CUSTOM, {})
        assert "Report Period: N/A to N/A" in html

    def test_none_description_renders_empty_subtitle(self):
        html = self._html(ReportType.CUSTOM, {}, description=None)
        assert '<div class="subtitle"></div>' in html

    def test_base_template_and_branding_color_applied(self):
        generator = PDFGenerator(TENANT_ID)
        generator.primary_color = "#123456"
        html = generator._generate_html(_template(ReportType.CUSTOM), {})
        assert html.startswith(BASE_TEMPLATE[:30])
        assert "#123456" in html
        assert "<title>Deep Report</title>" in html


# =============================================================================
# Section renderers
# =============================================================================


class TestRenderCampaignPerformance:
    def test_summary_platform_table_and_top10(self):
        generator = PDFGenerator(TENANT_ID)
        html = generator._render_campaign_performance(_campaign_data())

        # summary cards
        assert "$1,080" in html
        assert "$10,000" in html
        assert "9.26x" in html
        assert "53" in html

        # platform table: computed roas + zero-spend guard
        assert "META" in html
        assert "GOOGLE" in html
        assert f"{9800.0 / 180.0:.2f}x" in html  # 54.44x
        assert "0.00x" in html  # google spend == 0 -> roas 0

        # roas CSS classes
        assert "metric-good" in html
        assert "metric-neutral" in html

        # top-10 slice sorted by revenue: lowest-revenue campaign dropped
        assert "Top Dog" in html
        assert "Dud Eleven" not in html
        assert "metric-bad" not in html  # the only bad-roas row was sliced off
        # highest revenue listed before the fillers
        assert html.index("Top Dog") < html.index("Filler 0")

    def test_bad_roas_class_when_in_top10(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "summary": {},
            "by_platform": {},
            "campaigns": [
                {
                    "name": "Loser",
                    "platform": "meta",
                    "spend": 100.0,
                    "revenue": 10.0,
                    "roas": 0.1,
                    "conversions": 0,
                }
            ],
        }
        html = generator._render_campaign_performance(data)
        assert "metric-bad" in html
        assert "Loser" in html

    def test_defaults_with_empty_data(self):
        generator = PDFGenerator(TENANT_ID)
        html = generator._render_campaign_performance({})
        assert "$0" in html
        assert "0.00x" in html


class TestRenderAttributionSummary:
    def test_platforms_sorted_by_revenue_with_percentages(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "summary": {
                "total_deals": 3,
                "total_revenue": 3000.0,
                "avg_deal_size": 1000.0,
            },
            "by_platform": {
                "google": {"deals": 1, "revenue": 1000.0},
                "meta": {"deals": 2, "revenue": 2000.0},
            },
        }
        html = generator._render_attribution_summary(data)

        assert "$3,000" in html
        assert "$1,000" in html
        assert "66.7%" in html
        assert "33.3%" in html
        assert html.index("META") < html.index("GOOGLE")  # revenue desc

    def test_zero_total_revenue_yields_zero_pct(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "summary": {"total_deals": 1, "total_revenue": 0, "avg_deal_size": 0},
            "by_platform": {"meta": {"deals": 1, "revenue": 0}},
        }
        html = generator._render_attribution_summary(data)
        assert "0.0%" in html


class TestRenderPacingStatus:
    def test_progress_classes_and_alert_table_capped_at_five(self):
        generator = PDFGenerator(TENANT_ID)
        targets = [
            {
                "name": "Green",
                "metric": "spend",
                "current_value": 95.0,
                "target_value": 100.0,
                "progress_pct": 95.0,  # metric-good
            },
            {
                "name": "Yellow",
                "metric": "revenue",
                "current_value": 80.0,
                "target_value": 100.0,
                "progress_pct": 80.0,  # metric-neutral
            },
            {
                "name": "Red",
                "metric": "roas",
                "current_value": 10.0,
                "target_value": 100.0,
                "progress_pct": 10.0,  # metric-bad
            },
        ]
        alerts = [
            {
                "type": "overpacing_spend",
                "severity": "warning",
                "message": f"alert-{i}",
                "created_at": f"2026-07-0{i + 1}T08:00:00+00:00",
            }
            for i in range(6)
        ]
        data = {
            "summary": {
                "total_targets": 3,
                "on_track": 1,
                "at_risk": 1,
                "off_track": 1,
            },
            "targets": targets,
            "recent_alerts": alerts,
        }

        html = generator._render_pacing_status(data)

        assert "metric-good" in html
        assert "metric-neutral" in html
        assert "metric-bad" in html
        assert "95.0%" in html and "80.0%" in html and "10.0%" in html

        assert "Recent Alerts" in html
        assert "alert-0" in html and "alert-4" in html
        assert "alert-5" not in html  # capped at 5
        assert "2026-07-01" in html  # created_at sliced to date

    def test_alert_section_omitted_when_no_alerts(self):
        generator = PDFGenerator(TENANT_ID)
        data = {"summary": {}, "targets": [], "recent_alerts": []}
        html = generator._render_pacing_status(data)
        assert "Recent Alerts" not in html
        assert "Pacing Overview" in html


class TestRenderProfitRoas:
    def test_summary_cards(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "summary": {
                "total_revenue": 12345.0,
                "total_gross_profit": 6789.0,
                "gross_margin_pct": 55.0,
                "profit_roas": 1.35,
            }
        }
        html = generator._render_profit_roas(data)
        assert "$12,345" in html
        assert "$6,789" in html
        assert "55.0%" in html
        assert "1.35x" in html


class TestRenderPipelineMetrics:
    def test_summary_funnel_and_value_sections(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "summary": {
                "total_leads": 100,
                "total_mqls": 40,
                "total_sqls": 20,
                "total_won": 5,
                "total_pipeline_value": 250000.0,
                "total_won_revenue": 50000.0,
            },
            "funnel": {"lead_to_mql": 40.0, "mql_to_sql": 50.0, "sql_to_won": 25.0},
        }
        html = generator._render_pipeline_metrics(data)
        assert "100" in html and "40" in html and "20" in html
        assert "40.0%" in html and "50.0%" in html and "25.0%" in html
        assert "$250,000" in html
        assert "$50,000" in html
        assert "Lead → MQL" in html


class TestRenderExecutiveSummary:
    def test_highlights_with_nested_campaign_section(self):
        generator = PDFGenerator(TENANT_ID)
        data = {
            "highlights": {
                "total_spend": 1000.0,
                "total_revenue": 3000.0,
                "overall_roas": 3.0,
                "deals_won": 7,
            },
            "campaigns": _campaign_data(),
        }
        html = generator._render_executive_summary(data)
        assert "Executive Highlights" in html
        assert "3.00x" in html
        # nested campaign performance rendered from data["campaigns"]
        assert "Performance Summary" in html
        assert "Top Dog" in html

    def test_without_campaigns_key_skips_nested_section(self):
        generator = PDFGenerator(TENANT_ID)
        html = generator._render_executive_summary({"highlights": {}})
        assert "Executive Highlights" in html
        assert "Performance Summary" not in html


class TestRenderGeneric:
    def test_dumps_payload_as_json_pre_block(self):
        generator = PDFGenerator(TENANT_ID)
        html = generator._render_generic({"nested": {"k": 1}, "when": TODAY})
        assert "Report Data" in html
        assert '"nested"' in html
        assert TODAY.isoformat() in html  # default=str for dates
        assert "<pre" in html
