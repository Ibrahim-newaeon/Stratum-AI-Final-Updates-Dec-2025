# =============================================================================
# Stratum AI - PDF Report Generator
# =============================================================================
"""
PDF generation service for reports.

Uses HTML templates rendered to PDF for professional-quality reports.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.models.reporting import ReportTemplate, ReportType

logger = get_logger(__name__)


# HTML Template for reports
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.5;
            color: #333;
            padding: 40px;
        }}
        .header {{
            border-bottom: 2px solid {primary_color};
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 24px;
            color: {primary_color};
            margin-bottom: 5px;
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #666;
        }}
        .header .date-range {{
            font-size: 12px;
            color: #888;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            font-size: 16px;
            color: {primary_color};
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
            margin-bottom: 15px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .summary-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: {primary_color};
        }}
        .summary-card .label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: {primary_color};
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 10px;
            color: #888;
            text-align: center;
        }}
        .chart-placeholder {{
            background: #f0f0f0;
            border: 1px dashed #ccc;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #888;
            margin: 15px 0;
        }}
        .metric-good {{ color: #28a745; }}
        .metric-bad {{ color: #dc3545; }}
        .metric-neutral {{ color: #6c757d; }}
    </style>
</head>
<body>
    {content}
</body>
</html>
"""


class PDFGenerator:
    """
    Generates PDF reports from HTML templates.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.primary_color = "#2563eb"  # Default blue

    async def generate(
        self,
        template: ReportTemplate,
        data: dict[str, Any],
        execution_id: UUID,
    ) -> tuple[str, int]:
        """
        Generate a PDF report.

        Returns:
            Tuple of (file_path, file_size_bytes)
        """
        # Get branding config
        branding = template.config.get("branding", {})
        self.primary_color = branding.get("primary_color", "#2563eb")

        # Generate HTML content
        html_content = self._generate_html(template, data)

        # Convert to PDF
        output_path = Path(f"/tmp/reports/{self.tenant_id}/{execution_id}.pdf")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to use weasyprint for PDF generation
        try:
            from weasyprint import HTML

            HTML(string=html_content).write_pdf(str(output_path))
        except ImportError:
            # Fallback: save as HTML if weasyprint not available
            output_path = output_path.with_suffix(".html")
            with output_path.open("w", encoding="utf-8") as f:
                f.write(html_content)
            logger.warning("weasyprint_not_available", fallback="html")

        file_size = output_path.stat().st_size
        return str(output_path), file_size

    def _generate_html(
        self,
        template: ReportTemplate,
        data: dict[str, Any],
    ) -> str:
        """Generate HTML content based on report type."""
        period = data.get("period", {})
        date_range = f"{period.get('start_date', 'N/A')} to {period.get('end_date', 'N/A')}"

        # Generate content based on report type
        if template.report_type == ReportType.CAMPAIGN_PERFORMANCE:
            content = self._render_campaign_performance(data)
        elif template.report_type == ReportType.ATTRIBUTION_SUMMARY:
            content = self._render_attribution_summary(data)
        elif template.report_type == ReportType.PACING_STATUS:
            content = self._render_pacing_status(data)
        elif template.report_type == ReportType.PROFIT_ROAS:
            content = self._render_profit_roas(data)
        elif template.report_type == ReportType.PIPELINE_METRICS:
            content = self._render_pipeline_metrics(data)
        elif template.report_type == ReportType.EXECUTIVE_SUMMARY:
            content = self._render_executive_summary(data)
        else:
            content = self._render_generic(data)

        # Build full HTML
        full_content = f"""
        <div class="header">
            <h1>{template.name}</h1>
            <div class="subtitle">{template.description or ''}</div>
            <div class="date-range">Report Period: {date_range}</div>
        </div>
        {content}
        <div class="footer">
            Generated by Stratum AI on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
        </div>
        """

        return BASE_TEMPLATE.format(
            title=template.name,
            primary_color=self.primary_color,
            content=full_content,
        )

    def _render_campaign_performance(self, data: dict[str, Any]) -> str:
        """Render campaign performance report."""
        summary = data.get("summary", {})
        campaigns = data.get("campaigns", [])
        by_platform = data.get("by_platform", {})

        html = f"""
        <div class="section">
            <h2>Performance Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">${summary.get('total_spend', 0):,.0f}</div>
                    <div class="label">Total Spend</div>
                </div>
                <div class="summary-card">
                    <div class="value">${summary.get('total_revenue', 0):,.0f}</div>
                    <div class="label">Total Revenue</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('overall_roas', 0):.2f}x</div>
                    <div class="label">Overall ROAS</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('total_conversions', 0):,}</div>
                    <div class="label">Conversions</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Performance by Platform</h2>
            <table>
                <thead>
                    <tr>
                        <th>Platform</th>
                        <th>Spend</th>
                        <th>Revenue</th>
                        <th>ROAS</th>
                        <th>Conversions</th>
                    </tr>
                </thead>
                <tbody>
        """

        for platform, metrics in by_platform.items():
            roas = metrics["revenue"] / metrics["spend"] if metrics["spend"] > 0 else 0
            html += f"""
                    <tr>
                        <td>{platform.upper()}</td>
                        <td>${metrics['spend']:,.0f}</td>
                        <td>${metrics['revenue']:,.0f}</td>
                        <td>{roas:.2f}x</td>
                        <td>{metrics['conversions']:,}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Top Campaigns</h2>
            <table>
                <thead>
                    <tr>
                        <th>Campaign</th>
                        <th>Platform</th>
                        <th>Spend</th>
                        <th>Revenue</th>
                        <th>ROAS</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Sort by revenue and show top 10
        sorted_campaigns = sorted(campaigns, key=lambda x: x.get("revenue", 0), reverse=True)[:10]
        for c in sorted_campaigns:
            roas_class = (
                "metric-good"
                if c.get("roas", 0) >= 2
                else "metric-neutral"
                if c.get("roas", 0) >= 1
                else "metric-bad"
            )
            html += f"""
                    <tr>
                        <td>{c.get('name', 'N/A')}</td>
                        <td>{c.get('platform', 'N/A').upper()}</td>
                        <td>${c.get('spend', 0):,.0f}</td>
                        <td>${c.get('revenue', 0):,.0f}</td>
                        <td class="{roas_class}">{c.get('roas', 0):.2f}x</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        return html

    def _render_attribution_summary(self, data: dict[str, Any]) -> str:
        """Render attribution summary report."""
        summary = data.get("summary", {})
        by_platform = data.get("by_platform", {})

        html = f"""
        <div class="section">
            <h2>Attribution Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">{summary.get('total_deals', 0):,}</div>
                    <div class="label">Deals Won</div>
                </div>
                <div class="summary-card">
                    <div class="value">${summary.get('total_revenue', 0):,.0f}</div>
                    <div class="label">Total Revenue</div>
                </div>
                <div class="summary-card">
                    <div class="value">${summary.get('avg_deal_size', 0):,.0f}</div>
                    <div class="label">Avg Deal Size</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Revenue by Platform</h2>
            <table>
                <thead>
                    <tr>
                        <th>Platform</th>
                        <th>Deals</th>
                        <th>Revenue</th>
                        <th>% of Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        total_rev = summary.get("total_revenue", 1)
        for platform, metrics in sorted(
            by_platform.items(), key=lambda x: x[1]["revenue"], reverse=True
        ):
            pct = (metrics["revenue"] / total_rev * 100) if total_rev > 0 else 0
            html += f"""
                    <tr>
                        <td>{platform.upper()}</td>
                        <td>{metrics['deals']:,}</td>
                        <td>${metrics['revenue']:,.0f}</td>
                        <td>{pct:.1f}%</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        return html

    def _render_pacing_status(self, data: dict[str, Any]) -> str:
        """Render pacing status report."""
        summary = data.get("summary", {})
        targets = data.get("targets", [])
        alerts = data.get("recent_alerts", [])

        html = f"""
        <div class="section">
            <h2>Pacing Overview</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">{summary.get('total_targets', 0)}</div>
                    <div class="label">Active Targets</div>
                </div>
                <div class="summary-card">
                    <div class="value class="metric-good">{summary.get('on_track', 0)}</div>
                    <div class="label">On Track</div>
                </div>
                <div class="summary-card">
                    <div class="value class="metric-neutral">{summary.get('at_risk', 0)}</div>
                    <div class="label">At Risk</div>
                </div>
                <div class="summary-card">
                    <div class="value class="metric-bad">{summary.get('off_track', 0)}</div>
                    <div class="label">Off Track</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Target Progress</h2>
            <table>
                <thead>
                    <tr>
                        <th>Target</th>
                        <th>Metric</th>
                        <th>Current</th>
                        <th>Target</th>
                        <th>Progress</th>
                    </tr>
                </thead>
                <tbody>
        """

        for t in targets:
            progress = t.get("progress_pct", 0)
            progress_class = (
                "metric-good"
                if progress >= 90
                else "metric-neutral"
                if progress >= 70
                else "metric-bad"
            )
            html += f"""
                    <tr>
                        <td>{t.get('name', 'N/A')}</td>
                        <td>{t.get('metric', 'N/A')}</td>
                        <td>{t.get('current_value', 0):,.0f}</td>
                        <td>{t.get('target_value', 0):,.0f}</td>
                        <td class="{progress_class}">{progress:.1f}%</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        if alerts:
            html += """
        <div class="section">
            <h2>Recent Alerts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Severity</th>
                        <th>Message</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
            """
            for a in alerts[:5]:
                html += f"""
                    <tr>
                        <td>{a.get('type', 'N/A')}</td>
                        <td>{a.get('severity', 'N/A')}</td>
                        <td>{a.get('message', '')}</td>
                        <td>{a.get('created_at', 'N/A')[:10]}</td>
                    </tr>
                """
            html += """
                </tbody>
            </table>
        </div>
            """

        return html

    def _render_profit_roas(self, data: dict[str, Any]) -> str:
        """Render profit ROAS report."""
        summary = data.get("summary", {})

        html = f"""
        <div class="section">
            <h2>Profit & ROAS Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">${summary.get('total_revenue', 0):,.0f}</div>
                    <div class="label">Total Revenue</div>
                </div>
                <div class="summary-card">
                    <div class="value">${summary.get('total_gross_profit', 0):,.0f}</div>
                    <div class="label">Gross Profit</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('gross_margin_pct', 0):.1f}%</div>
                    <div class="label">Gross Margin</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('profit_roas', 0):.2f}x</div>
                    <div class="label">Profit ROAS</div>
                </div>
            </div>
        </div>
        """

        return html

    def _render_pipeline_metrics(self, data: dict[str, Any]) -> str:
        """Render pipeline metrics report."""
        summary = data.get("summary", {})
        funnel = data.get("funnel", {})

        html = f"""
        <div class="section">
            <h2>Pipeline Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">{summary.get('total_leads', 0):,}</div>
                    <div class="label">Total Leads</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('total_mqls', 0):,}</div>
                    <div class="label">MQLs</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('total_sqls', 0):,}</div>
                    <div class="label">SQLs</div>
                </div>
                <div class="summary-card">
                    <div class="value">{summary.get('total_won', 0):,}</div>
                    <div class="label">Deals Won</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Funnel Conversion Rates</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">{funnel.get('lead_to_mql', 0):.1f}%</div>
                    <div class="label">Lead → MQL</div>
                </div>
                <div class="summary-card">
                    <div class="value">{funnel.get('mql_to_sql', 0):.1f}%</div>
                    <div class="label">MQL → SQL</div>
                </div>
                <div class="summary-card">
                    <div class="value">{funnel.get('sql_to_won', 0):.1f}%</div>
                    <div class="label">SQL → Won</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Pipeline Value</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">${summary.get('total_pipeline_value', 0):,.0f}</div>
                    <div class="label">Pipeline Value</div>
                </div>
                <div class="summary-card">
                    <div class="value">${summary.get('total_won_revenue', 0):,.0f}</div>
                    <div class="label">Won Revenue</div>
                </div>
            </div>
        </div>
        """

        return html

    def _render_executive_summary(self, data: dict[str, Any]) -> str:
        """Render executive summary report."""
        highlights = data.get("highlights", {})

        html = f"""
        <div class="section">
            <h2>Executive Highlights</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="value">${highlights.get('total_spend', 0):,.0f}</div>
                    <div class="label">Total Spend</div>
                </div>
                <div class="summary-card">
                    <div class="value">${highlights.get('total_revenue', 0):,.0f}</div>
                    <div class="label">Total Revenue</div>
                </div>
                <div class="summary-card">
                    <div class="value">{highlights.get('overall_roas', 0):.2f}x</div>
                    <div class="label">Overall ROAS</div>
                </div>
                <div class="summary-card">
                    <div class="value">{highlights.get('deals_won', 0):,}</div>
                    <div class="label">Deals Won</div>
                </div>
            </div>
        </div>
        """

        # Include campaign section
        if "campaigns" in data:
            html += self._render_campaign_performance(data["campaigns"])

        return html

    def _render_generic(self, data: dict[str, Any]) -> str:
        """Render generic JSON data as a table."""
        import json

        return f"""
        <div class="section">
            <h2>Report Data</h2>
            <pre style="background: #f8f9fa; padding: 15px; overflow: auto;">
{json.dumps(data, indent=2, default=str)}
            </pre>
        </div>
        """
