# =============================================================================
# Stratum AI - Report Generation Service
# =============================================================================
"""
Service for generating reports from templates.

Collects data from various sources and formats it according to the template.
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, Optional, Tuple
from uuid import UUID
import json

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.reporting import (
    ReportTemplate,
    ReportExecution,
    ReportType,
    ReportFormat,
    ExecutionStatus,
)

logger = get_logger(__name__)


class ReportDataCollector:
    """
    Collects data for different report types.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def collect_campaign_performance(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect campaign performance data."""
        from app.models import Campaign

        # Get metrics
        metrics = config.get("metrics", ["spend", "revenue", "roas", "conversions"])
        platforms = config.get("filters", {}).get("platforms")

        # Query campaigns
        query = select(Campaign).where(
            and_(
                Campaign.tenant_id == self.tenant_id,
                Campaign.is_active == True,
            )
        )
        if platforms:
            query = query.where(Campaign.platform.in_(platforms))

        result = await self.db.execute(query)
        campaigns = result.scalars().all()

        # Build report data
        data = {
            "summary": {
                "total_campaigns": len(campaigns),
                "total_spend": 0,
                "total_revenue": 0,
                "total_conversions": 0,
                "overall_roas": 0,
            },
            "by_platform": {},
            "campaigns": [],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        for campaign in campaigns:
            campaign_data = {
                "id": str(campaign.id),
                "name": campaign.name,
                "platform": campaign.platform.value if campaign.platform else "unknown",
                "status": campaign.status.value if campaign.status else "unknown",
                "spend": float(campaign.total_spend or 0),
                "revenue": float(campaign.total_revenue or 0),
                "conversions": campaign.total_conversions or 0,
                "roas": (
                    float(campaign.total_revenue or 0) / float(campaign.total_spend)
                    if campaign.total_spend and campaign.total_spend > 0 else 0
                ),
            }
            data["campaigns"].append(campaign_data)

            # Update summary
            data["summary"]["total_spend"] += campaign_data["spend"]
            data["summary"]["total_revenue"] += campaign_data["revenue"]
            data["summary"]["total_conversions"] += campaign_data["conversions"]

            # Update by platform
            platform = campaign_data["platform"]
            if platform not in data["by_platform"]:
                data["by_platform"][platform] = {
                    "spend": 0,
                    "revenue": 0,
                    "conversions": 0,
                }
            data["by_platform"][platform]["spend"] += campaign_data["spend"]
            data["by_platform"][platform]["revenue"] += campaign_data["revenue"]
            data["by_platform"][platform]["conversions"] += campaign_data["conversions"]

        # Calculate overall ROAS
        if data["summary"]["total_spend"] > 0:
            data["summary"]["overall_roas"] = round(
                data["summary"]["total_revenue"] / data["summary"]["total_spend"], 2
            )

        return data

    async def collect_attribution_summary(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect attribution summary data."""
        from app.models.crm import CRMDeal

        # Get won deals in period
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= datetime.combine(start_date, datetime.min.time()),
                    CRMDeal.won_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
        )
        deals = deal_result.scalars().all()

        # Build attribution data
        data = {
            "summary": {
                "total_deals": len(deals),
                "total_revenue": sum(d.amount or 0 for d in deals),
                "avg_deal_size": 0,
            },
            "by_platform": {},
            "by_campaign": {},
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        if deals:
            data["summary"]["avg_deal_size"] = data["summary"]["total_revenue"] / len(deals)

        for deal in deals:
            platform = deal.attributed_platform or "unattributed"
            campaign = deal.attributed_campaign_id or "unattributed"

            if platform not in data["by_platform"]:
                data["by_platform"][platform] = {"deals": 0, "revenue": 0}
            data["by_platform"][platform]["deals"] += 1
            data["by_platform"][platform]["revenue"] += deal.amount or 0

            if campaign not in data["by_campaign"]:
                data["by_campaign"][campaign] = {"deals": 0, "revenue": 0}
            data["by_campaign"][campaign]["deals"] += 1
            data["by_campaign"][campaign]["revenue"] += deal.amount or 0

        return data

    async def collect_pacing_status(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect pacing and forecasting data."""
        from app.models.pacing import Target, PacingAlert

        # Get active targets
        target_result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.tenant_id == self.tenant_id,
                    Target.is_active == True,
                )
            )
        )
        targets = target_result.scalars().all()

        # Get recent alerts
        alert_result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.tenant_id == self.tenant_id,
                    PacingAlert.created_at >= datetime.combine(start_date, datetime.min.time()),
                )
            ).order_by(PacingAlert.created_at.desc()).limit(10)
        )
        alerts = alert_result.scalars().all()

        data = {
            "summary": {
                "total_targets": len(targets),
                "on_track": 0,
                "at_risk": 0,
                "off_track": 0,
            },
            "targets": [],
            "recent_alerts": [],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        for target in targets:
            target_data = {
                "id": str(target.id),
                "name": target.name,
                "metric": target.metric.value if target.metric else "unknown",
                "target_value": target.target_value,
                "current_value": target.current_value,
                "progress_pct": (
                    (target.current_value / target.target_value * 100)
                    if target.target_value else 0
                ),
            }
            data["targets"].append(target_data)

        for alert in alerts:
            data["recent_alerts"].append({
                "type": alert.alert_type.value if alert.alert_type else "unknown",
                "severity": alert.severity.value if alert.severity else "unknown",
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
            })

        return data

    async def collect_profit_roas(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect profit ROAS data."""
        from app.models.profit import DailyProfitMetrics

        # Get profit metrics
        result = await self.db.execute(
            select(DailyProfitMetrics).where(
                and_(
                    DailyProfitMetrics.tenant_id == self.tenant_id,
                    DailyProfitMetrics.date >= start_date,
                    DailyProfitMetrics.date <= end_date,
                )
            ).order_by(DailyProfitMetrics.date)
        )
        metrics = result.scalars().all()

        data = {
            "summary": {
                "total_revenue": 0,
                "total_cogs": 0,
                "total_gross_profit": 0,
                "total_spend": 0,
                "profit_roas": 0,
                "gross_margin_pct": 0,
            },
            "daily": [],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        for m in metrics:
            revenue = (m.revenue_cents or 0) / 100
            cogs = (m.cogs_cents or 0) / 100
            spend = (m.spend_cents or 0) / 100
            gross_profit = (m.gross_profit_cents or 0) / 100

            data["daily"].append({
                "date": m.date.isoformat(),
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "spend": spend,
                "profit_roas": m.profit_roas,
            })

            data["summary"]["total_revenue"] += revenue
            data["summary"]["total_cogs"] += cogs
            data["summary"]["total_gross_profit"] += gross_profit
            data["summary"]["total_spend"] += spend

        if data["summary"]["total_spend"] > 0:
            data["summary"]["profit_roas"] = round(
                data["summary"]["total_gross_profit"] / data["summary"]["total_spend"], 2
            )

        if data["summary"]["total_revenue"] > 0:
            data["summary"]["gross_margin_pct"] = round(
                data["summary"]["total_gross_profit"] / data["summary"]["total_revenue"] * 100, 1
            )

        return data

    async def collect_pipeline_metrics(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect CRM pipeline metrics."""
        from app.models.crm import DailyPipelineMetrics

        result = await self.db.execute(
            select(DailyPipelineMetrics).where(
                and_(
                    DailyPipelineMetrics.tenant_id == self.tenant_id,
                    DailyPipelineMetrics.date >= start_date,
                    DailyPipelineMetrics.date <= end_date,
                )
            ).order_by(DailyPipelineMetrics.date)
        )
        metrics = result.scalars().all()

        data = {
            "summary": {
                "total_leads": 0,
                "total_mqls": 0,
                "total_sqls": 0,
                "total_won": 0,
                "total_pipeline_value": 0,
                "total_won_revenue": 0,
            },
            "funnel": {
                "lead_to_mql": 0,
                "mql_to_sql": 0,
                "sql_to_won": 0,
            },
            "daily": [],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        for m in metrics:
            data["daily"].append({
                "date": m.date.isoformat(),
                "leads": m.leads_created,
                "mqls": m.mqls_created,
                "sqls": m.sqls_created,
                "won": m.deals_won,
                "pipeline_value": (m.pipeline_value_cents or 0) / 100,
                "won_revenue": (m.won_revenue_cents or 0) / 100,
            })

            data["summary"]["total_leads"] += m.leads_created or 0
            data["summary"]["total_mqls"] += m.mqls_created or 0
            data["summary"]["total_sqls"] += m.sqls_created or 0
            data["summary"]["total_won"] += m.deals_won or 0
            data["summary"]["total_pipeline_value"] += (m.pipeline_value_cents or 0) / 100
            data["summary"]["total_won_revenue"] += (m.won_revenue_cents or 0) / 100

        # Calculate funnel rates
        if data["summary"]["total_leads"] > 0:
            data["funnel"]["lead_to_mql"] = round(
                data["summary"]["total_mqls"] / data["summary"]["total_leads"] * 100, 1
            )
        if data["summary"]["total_mqls"] > 0:
            data["funnel"]["mql_to_sql"] = round(
                data["summary"]["total_sqls"] / data["summary"]["total_mqls"] * 100, 1
            )
        if data["summary"]["total_sqls"] > 0:
            data["funnel"]["sql_to_won"] = round(
                data["summary"]["total_won"] / data["summary"]["total_sqls"] * 100, 1
            )

        return data

    async def collect_executive_summary(
        self,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect executive summary combining multiple data sources."""
        campaign_data = await self.collect_campaign_performance(start_date, end_date, config)
        attribution_data = await self.collect_attribution_summary(start_date, end_date, config)
        pipeline_data = await self.collect_pipeline_metrics(start_date, end_date, config)

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "highlights": {
                "total_spend": campaign_data["summary"]["total_spend"],
                "total_revenue": campaign_data["summary"]["total_revenue"],
                "overall_roas": campaign_data["summary"]["overall_roas"],
                "deals_won": attribution_data["summary"]["total_deals"],
                "pipeline_value": pipeline_data["summary"]["total_pipeline_value"],
            },
            "campaigns": campaign_data,
            "attribution": attribution_data,
            "pipeline": pipeline_data,
        }


class ReportGenerator:
    """
    Main service for generating reports.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.collector = ReportDataCollector(db, tenant_id)

    async def generate_report(
        self,
        template_id: UUID,
        start_date: date,
        end_date: date,
        format: ReportFormat = ReportFormat.PDF,
        config_override: Optional[Dict[str, Any]] = None,
        triggered_by_user_id: Optional[int] = None,
        schedule_id: Optional[UUID] = None,
        execution_type: str = "manual",
    ) -> Dict[str, Any]:
        """
        Generate a report from a template.

        Returns execution details and file path.
        """
        # Get template
        template_result = await self.db.execute(
            select(ReportTemplate).where(
                and_(
                    ReportTemplate.id == template_id,
                    ReportTemplate.tenant_id == self.tenant_id,
                )
            )
        )
        template = template_result.scalar_one_or_none()

        if not template:
            return {"success": False, "error": "template_not_found"}

        # Create execution record
        execution = ReportExecution(
            tenant_id=self.tenant_id,
            template_id=template_id,
            schedule_id=schedule_id,
            execution_type=execution_type,
            status=ExecutionStatus.RUNNING,
            report_type=template.report_type,
            format=format,
            date_range_start=start_date,
            date_range_end=end_date,
            config_used={**template.config, **(config_override or {})},
            triggered_by_user_id=triggered_by_user_id,
        )
        self.db.add(execution)
        await self.db.flush()

        try:
            # Collect data based on report type
            config = {**template.config, **(config_override or {})}
            data = await self._collect_data(template.report_type, start_date, end_date, config)

            # Generate output
            if format == ReportFormat.PDF:
                from app.services.reporting.pdf_generator import PDFGenerator
                pdf_gen = PDFGenerator(self.tenant_id)
                file_path, file_size = await pdf_gen.generate(
                    template=template,
                    data=data,
                    execution_id=execution.id,
                )
            elif format == ReportFormat.CSV:
                file_path, file_size = await self._generate_csv(template, data, execution.id)
            elif format == ReportFormat.JSON:
                file_path, file_size = await self._generate_json(template, data, execution.id)
            else:
                file_path, file_size = await self._generate_json(template, data, execution.id)

            # Update execution
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.file_path = file_path
            execution.file_size_bytes = file_size
            execution.metrics_summary = data.get("summary")

            await self.db.commit()

            return {
                "success": True,
                "execution_id": str(execution.id),
                "file_path": file_path,
                "file_size_bytes": file_size,
                "duration_seconds": execution.duration_seconds,
            }

        except Exception as e:
            logger.error("report_generation_failed", error=str(e), execution_id=str(execution.id))
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            await self.db.commit()

            return {
                "success": False,
                "execution_id": str(execution.id),
                "error": str(e),
            }

    async def _collect_data(
        self,
        report_type: ReportType,
        start_date: date,
        end_date: date,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect data based on report type."""
        if report_type == ReportType.CAMPAIGN_PERFORMANCE:
            return await self.collector.collect_campaign_performance(start_date, end_date, config)
        elif report_type == ReportType.ATTRIBUTION_SUMMARY:
            return await self.collector.collect_attribution_summary(start_date, end_date, config)
        elif report_type == ReportType.PACING_STATUS:
            return await self.collector.collect_pacing_status(start_date, end_date, config)
        elif report_type == ReportType.PROFIT_ROAS:
            return await self.collector.collect_profit_roas(start_date, end_date, config)
        elif report_type == ReportType.PIPELINE_METRICS:
            return await self.collector.collect_pipeline_metrics(start_date, end_date, config)
        elif report_type == ReportType.EXECUTIVE_SUMMARY:
            return await self.collector.collect_executive_summary(start_date, end_date, config)
        else:
            return {"error": "unsupported_report_type"}

    async def _generate_csv(
        self,
        template: ReportTemplate,
        data: Dict[str, Any],
        execution_id: UUID,
    ) -> Tuple[str, int]:
        """Generate CSV output."""
        import csv
        import io
        import os

        output = io.StringIO()
        writer = csv.writer(output)

        # Write based on data structure
        if "campaigns" in data:
            writer.writerow(["Campaign", "Platform", "Spend", "Revenue", "ROAS", "Conversions"])
            for c in data["campaigns"]:
                writer.writerow([c["name"], c["platform"], c["spend"], c["revenue"], c["roas"], c["conversions"]])
        elif "daily" in data:
            if data["daily"]:
                writer.writerow(data["daily"][0].keys())
                for row in data["daily"]:
                    writer.writerow(row.values())

        content = output.getvalue()
        file_path = f"/tmp/reports/{self.tenant_id}/{execution_id}.csv"

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w") as f:
            f.write(content)

        return file_path, len(content.encode())

    async def _generate_json(
        self,
        template: ReportTemplate,
        data: Dict[str, Any],
        execution_id: UUID,
    ) -> Tuple[str, int]:
        """Generate JSON output."""
        import os

        content = json.dumps(data, indent=2, default=str)
        file_path = f"/tmp/reports/{self.tenant_id}/{execution_id}.json"

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w") as f:
            f.write(content)

        return file_path, len(content.encode())

    @staticmethod
    def parse_date_range(
        date_range_type: str,
        reference_date: Optional[date] = None,
    ) -> Tuple[date, date]:
        """Parse relative date range into absolute dates."""
        ref = reference_date or date.today()

        if date_range_type == "yesterday":
            d = ref - timedelta(days=1)
            return d, d
        elif date_range_type == "last_7_days":
            return ref - timedelta(days=7), ref - timedelta(days=1)
        elif date_range_type == "last_30_days":
            return ref - timedelta(days=30), ref - timedelta(days=1)
        elif date_range_type == "last_month":
            first_of_month = ref.replace(day=1)
            last_month_end = first_of_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start, last_month_end
        elif date_range_type == "month_to_date":
            return ref.replace(day=1), ref
        elif date_range_type == "quarter_to_date":
            quarter_start_month = ((ref.month - 1) // 3) * 3 + 1
            return ref.replace(month=quarter_start_month, day=1), ref
        elif date_range_type == "year_to_date":
            return ref.replace(month=1, day=1), ref
        else:
            # Default to last 30 days
            return ref - timedelta(days=30), ref - timedelta(days=1)
