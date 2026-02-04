# =============================================================================
# Stratum AI - Profit Calculation Service
# =============================================================================
"""
Service for calculating Profit ROAS metrics.

Profit ROAS = (Revenue - COGS) / Ad Spend

Features:
- Product-level profit calculations
- Campaign-level aggregations
- Breakeven analysis
- Margin trending
"""

from datetime import UTC, date, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.profit import (
    DailyProfitMetrics,
    MarginRule,
    ProductCatalog,
    ProductMargin,
    ProfitROASReport,
)

logger = get_logger(__name__)


class ProfitCalculationService:
    """
    Service for calculating Profit ROAS and related metrics.

    Calculates:
    - Gross Profit ROAS = Gross Profit / Ad Spend
    - Net Profit ROAS = (Gross Profit - Ad Spend) / Ad Spend
    - Breakeven ROAS threshold
    - Margin percentages
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def calculate_profit_roas(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """
        Calculate Profit ROAS for a date range.

        Args:
            start_date: Start of period
            end_date: End of period
            platform: Optional platform filter
            campaign_id: Optional campaign filter
            product_id: Optional product filter

        Returns:
            Profit ROAS metrics
        """
        # Build query conditions
        conditions = [
            DailyProfitMetrics.tenant_id == self.tenant_id,
            DailyProfitMetrics.date >= start_date,
            DailyProfitMetrics.date <= end_date,
        ]

        if platform:
            conditions.append(DailyProfitMetrics.platform == platform)
        if campaign_id:
            conditions.append(DailyProfitMetrics.campaign_id == campaign_id)
        if product_id:
            conditions.append(DailyProfitMetrics.product_id == product_id)

        # Aggregate metrics
        result = await self.db.execute(
            select(
                func.sum(DailyProfitMetrics.units_sold).label("total_units"),
                func.sum(DailyProfitMetrics.gross_revenue_cents).label("total_revenue"),
                func.sum(DailyProfitMetrics.total_cogs_cents).label("total_cogs"),
                func.sum(DailyProfitMetrics.ad_spend_cents).label("total_ad_spend"),
                func.sum(DailyProfitMetrics.gross_profit_cents).label("total_gross_profit"),
                func.sum(DailyProfitMetrics.net_profit_cents).label("total_net_profit"),
                func.count(func.distinct(DailyProfitMetrics.date)).label("days"),
            ).where(and_(*conditions))
        )
        row = result.fetchone()

        if not row or not row.total_revenue:
            return {
                "status": "no_data",
                "message": "No profit data available for the specified period",
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

        # Convert from cents to dollars
        total_revenue = (row.total_revenue or 0) / 100
        total_cogs = (row.total_cogs or 0) / 100
        total_ad_spend = (row.total_ad_spend or 0) / 100
        total_gross_profit = (row.total_gross_profit or 0) / 100
        total_net_profit = (row.total_net_profit or 0) / 100

        # Calculate ROAS metrics
        revenue_roas = total_revenue / total_ad_spend if total_ad_spend > 0 else 0
        gross_profit_roas = total_gross_profit / total_ad_spend if total_ad_spend > 0 else 0
        net_profit_roas = total_net_profit / total_ad_spend if total_ad_spend > 0 else 0

        # Calculate margins
        gross_margin_pct = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        net_margin_pct = (total_net_profit / total_revenue * 100) if total_revenue > 0 else 0

        # Breakeven analysis
        # Breakeven ROAS = 1 / Gross Margin (as decimal)
        breakeven_roas = 1 / (gross_margin_pct / 100) if gross_margin_pct > 0 else None
        above_breakeven = revenue_roas > breakeven_roas if breakeven_roas else None

        return {
            "status": "success",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": row.days,
            },
            "filters": {
                "platform": platform,
                "campaign_id": campaign_id,
                "product_id": str(product_id) if product_id else None,
            },
            "volume": {
                "units_sold": row.total_units or 0,
            },
            "financials": {
                "revenue": round(total_revenue, 2),
                "cogs": round(total_cogs, 2),
                "gross_profit": round(total_gross_profit, 2),
                "ad_spend": round(total_ad_spend, 2),
                "net_profit": round(total_net_profit, 2),
            },
            "roas": {
                "revenue_roas": round(revenue_roas, 2),
                "gross_profit_roas": round(gross_profit_roas, 2),
                "net_profit_roas": round(net_profit_roas, 2),
            },
            "margins": {
                "gross_margin_pct": round(gross_margin_pct, 1),
                "net_margin_pct": round(net_margin_pct, 1),
            },
            "breakeven": {
                "breakeven_roas": round(breakeven_roas, 2) if breakeven_roas else None,
                "above_breakeven": above_breakeven,
                "margin_of_safety": round(revenue_roas - breakeven_roas, 2)
                if breakeven_roas
                else None,
            },
        }

    async def calculate_daily_profit(
        self,
        revenue_cents: int,
        ad_spend_cents: int,
        product_id: Optional[UUID] = None,
        category: Optional[str] = None,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        units_sold: int = 1,
        calculation_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Calculate profit metrics for a single transaction/day.

        Uses product-specific COGS if available, otherwise falls back to margin rules.

        Args:
            revenue_cents: Total revenue in cents
            ad_spend_cents: Ad spend in cents
            product_id: Optional product ID for COGS lookup
            category: Product category for margin rule fallback
            platform: Platform for margin rule
            campaign_id: Campaign for margin rule
            units_sold: Number of units
            calculation_date: Date for COGS lookup

        Returns:
            Calculated profit metrics
        """
        if calculation_date is None:
            calculation_date = datetime.now(UTC).date()

        # Get COGS
        cogs_result = await self._get_cogs(
            product_id=product_id,
            category=category,
            platform=platform,
            campaign_id=campaign_id,
            revenue_cents=revenue_cents,
            units_sold=units_sold,
            effective_date=calculation_date,
        )

        cogs_cents = cogs_result["cogs_cents"]
        is_estimated = cogs_result["is_estimated"]
        cogs_source = cogs_result["source"]

        # Calculate profits
        gross_profit_cents = revenue_cents - cogs_cents
        net_profit_cents = gross_profit_cents - ad_spend_cents

        # Calculate ROAS
        revenue_roas = revenue_cents / ad_spend_cents if ad_spend_cents > 0 else 0
        gross_profit_roas = gross_profit_cents / ad_spend_cents if ad_spend_cents > 0 else 0
        net_profit_roas = net_profit_cents / ad_spend_cents if ad_spend_cents > 0 else 0

        # Calculate margins
        gross_margin_pct = (gross_profit_cents / revenue_cents * 100) if revenue_cents > 0 else 0

        return {
            "revenue_cents": revenue_cents,
            "cogs_cents": cogs_cents,
            "ad_spend_cents": ad_spend_cents,
            "gross_profit_cents": gross_profit_cents,
            "net_profit_cents": net_profit_cents,
            "units_sold": units_sold,
            "revenue_roas": round(revenue_roas, 2),
            "gross_profit_roas": round(gross_profit_roas, 2),
            "net_profit_roas": round(net_profit_roas, 2),
            "gross_margin_pct": round(gross_margin_pct, 1),
            "is_estimated": is_estimated,
            "cogs_source": cogs_source,
        }

    async def get_profit_trend(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        granularity: str = "daily",
    ) -> dict[str, Any]:
        """
        Get profit ROAS trend over time.

        Args:
            start_date: Start date
            end_date: End date
            platform: Optional platform filter
            campaign_id: Optional campaign filter
            granularity: daily, weekly, or monthly

        Returns:
            Time series of profit metrics
        """
        conditions = [
            DailyProfitMetrics.tenant_id == self.tenant_id,
            DailyProfitMetrics.date >= start_date,
            DailyProfitMetrics.date <= end_date,
        ]

        if platform:
            conditions.append(DailyProfitMetrics.platform == platform)
        if campaign_id:
            conditions.append(DailyProfitMetrics.campaign_id == campaign_id)

        result = await self.db.execute(
            select(DailyProfitMetrics).where(and_(*conditions)).order_by(DailyProfitMetrics.date)
        )
        records = result.scalars().all()

        # Group by date
        daily_data = {}
        for r in records:
            date_key = r.date.isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "date": date_key,
                    "revenue": 0,
                    "cogs": 0,
                    "ad_spend": 0,
                    "gross_profit": 0,
                    "net_profit": 0,
                    "units": 0,
                }
            daily_data[date_key]["revenue"] += (r.gross_revenue_cents or 0) / 100
            daily_data[date_key]["cogs"] += (r.total_cogs_cents or 0) / 100
            daily_data[date_key]["ad_spend"] += (r.ad_spend_cents or 0) / 100
            daily_data[date_key]["gross_profit"] += (r.gross_profit_cents or 0) / 100
            daily_data[date_key]["net_profit"] += (r.net_profit_cents or 0) / 100
            daily_data[date_key]["units"] += r.units_sold or 0

        # Calculate ROAS for each day
        trend = []
        for date_key, data in sorted(daily_data.items()):
            ad_spend = data["ad_spend"]
            trend.append(
                {
                    "date": data["date"],
                    "revenue": round(data["revenue"], 2),
                    "gross_profit": round(data["gross_profit"], 2),
                    "net_profit": round(data["net_profit"], 2),
                    "ad_spend": round(ad_spend, 2),
                    "revenue_roas": round(data["revenue"] / ad_spend, 2) if ad_spend > 0 else 0,
                    "gross_profit_roas": round(data["gross_profit"] / ad_spend, 2)
                    if ad_spend > 0
                    else 0,
                    "net_profit_roas": round(data["net_profit"] / ad_spend, 2)
                    if ad_spend > 0
                    else 0,
                    "units": data["units"],
                }
            )

        return {
            "status": "success",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "granularity": granularity,
            "data_points": len(trend),
            "trend": trend,
        }

    async def get_product_profitability(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "gross_profit",
    ) -> dict[str, Any]:
        """
        Get profitability by product.

        Args:
            start_date: Start date
            end_date: End date
            platform: Optional platform filter
            limit: Max products to return
            sort_by: Sort by gross_profit, net_profit, or gross_profit_roas

        Returns:
            Product-level profitability breakdown
        """
        conditions = [
            DailyProfitMetrics.tenant_id == self.tenant_id,
            DailyProfitMetrics.date >= start_date,
            DailyProfitMetrics.date <= end_date,
            DailyProfitMetrics.product_id.isnot(None),
        ]

        if platform:
            conditions.append(DailyProfitMetrics.platform == platform)

        result = await self.db.execute(
            select(
                DailyProfitMetrics.product_id,
                func.sum(DailyProfitMetrics.units_sold).label("units"),
                func.sum(DailyProfitMetrics.gross_revenue_cents).label("revenue"),
                func.sum(DailyProfitMetrics.total_cogs_cents).label("cogs"),
                func.sum(DailyProfitMetrics.ad_spend_cents).label("ad_spend"),
                func.sum(DailyProfitMetrics.gross_profit_cents).label("gross_profit"),
                func.sum(DailyProfitMetrics.net_profit_cents).label("net_profit"),
            )
            .where(and_(*conditions))
            .group_by(DailyProfitMetrics.product_id)
        )
        rows = result.fetchall()

        # Get product details
        product_ids = [r.product_id for r in rows]
        products_result = await self.db.execute(
            select(ProductCatalog).where(ProductCatalog.id.in_(product_ids))
        )
        products = {p.id: p for p in products_result.scalars().all()}

        # Build product profitability list
        product_data = []
        for r in rows:
            product = products.get(r.product_id)
            revenue = (r.revenue or 0) / 100
            cogs = (r.cogs or 0) / 100
            ad_spend = (r.ad_spend or 0) / 100
            gross_profit = (r.gross_profit or 0) / 100
            net_profit = (r.net_profit or 0) / 100

            product_data.append(
                {
                    "product_id": str(r.product_id),
                    "sku": product.sku if product else "Unknown",
                    "name": product.name if product else "Unknown Product",
                    "category": product.category if product else None,
                    "units": r.units or 0,
                    "revenue": round(revenue, 2),
                    "cogs": round(cogs, 2),
                    "gross_profit": round(gross_profit, 2),
                    "net_profit": round(net_profit, 2),
                    "ad_spend": round(ad_spend, 2),
                    "gross_margin_pct": round(
                        (gross_profit / revenue * 100) if revenue > 0 else 0, 1
                    ),
                    "gross_profit_roas": round(gross_profit / ad_spend, 2) if ad_spend > 0 else 0,
                    "net_profit_roas": round(net_profit / ad_spend, 2) if ad_spend > 0 else 0,
                }
            )

        # Sort
        sort_key = (
            sort_by
            if sort_by in ["gross_profit", "net_profit", "gross_profit_roas"]
            else "gross_profit"
        )
        product_data.sort(key=lambda x: x[sort_key], reverse=True)

        return {
            "status": "success",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_products": len(product_data),
            "products": product_data[:limit],
        }

    async def get_campaign_profitability(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get profitability by campaign.

        Returns:
            Campaign-level profitability breakdown
        """
        conditions = [
            DailyProfitMetrics.tenant_id == self.tenant_id,
            DailyProfitMetrics.date >= start_date,
            DailyProfitMetrics.date <= end_date,
            DailyProfitMetrics.campaign_id.isnot(None),
        ]

        if platform:
            conditions.append(DailyProfitMetrics.platform == platform)

        result = await self.db.execute(
            select(
                DailyProfitMetrics.platform,
                DailyProfitMetrics.campaign_id,
                func.sum(DailyProfitMetrics.units_sold).label("units"),
                func.sum(DailyProfitMetrics.gross_revenue_cents).label("revenue"),
                func.sum(DailyProfitMetrics.total_cogs_cents).label("cogs"),
                func.sum(DailyProfitMetrics.ad_spend_cents).label("ad_spend"),
                func.sum(DailyProfitMetrics.gross_profit_cents).label("gross_profit"),
                func.sum(DailyProfitMetrics.net_profit_cents).label("net_profit"),
            )
            .where(and_(*conditions))
            .group_by(DailyProfitMetrics.platform, DailyProfitMetrics.campaign_id)
        )
        rows = result.fetchall()

        campaigns = []
        for r in rows:
            revenue = (r.revenue or 0) / 100
            ad_spend = (r.ad_spend or 0) / 100
            gross_profit = (r.gross_profit or 0) / 100
            net_profit = (r.net_profit or 0) / 100

            # Breakeven ROAS
            gross_margin_pct = (gross_profit / revenue * 100) if revenue > 0 else 0
            breakeven_roas = 1 / (gross_margin_pct / 100) if gross_margin_pct > 0 else None
            revenue_roas = revenue / ad_spend if ad_spend > 0 else 0

            campaigns.append(
                {
                    "platform": r.platform,
                    "campaign_id": r.campaign_id,
                    "units": r.units or 0,
                    "revenue": round(revenue, 2),
                    "cogs": round((r.cogs or 0) / 100, 2),
                    "gross_profit": round(gross_profit, 2),
                    "net_profit": round(net_profit, 2),
                    "ad_spend": round(ad_spend, 2),
                    "revenue_roas": round(revenue_roas, 2),
                    "gross_profit_roas": round(gross_profit / ad_spend, 2) if ad_spend > 0 else 0,
                    "net_profit_roas": round(net_profit / ad_spend, 2) if ad_spend > 0 else 0,
                    "gross_margin_pct": round(gross_margin_pct, 1),
                    "breakeven_roas": round(breakeven_roas, 2) if breakeven_roas else None,
                    "above_breakeven": revenue_roas > breakeven_roas if breakeven_roas else None,
                }
            )

        # Sort by gross profit
        campaigns.sort(key=lambda x: x["gross_profit"], reverse=True)

        return {
            "status": "success",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_campaigns": len(campaigns),
            "campaigns": campaigns,
        }

    async def generate_profit_report(
        self,
        start_date: date,
        end_date: date,
        report_type: str = "custom",
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ProfitROASReport:
        """
        Generate and save a profit ROAS report.

        Args:
            start_date: Report start date
            end_date: Report end date
            report_type: daily, weekly, monthly, or custom
            platform: Optional platform filter
            campaign_id: Optional campaign filter
            category: Optional category filter
            user_id: User generating report

        Returns:
            Created ProfitROASReport
        """
        # Get aggregated metrics
        profit_data = await self.calculate_profit_roas(
            start_date=start_date,
            end_date=end_date,
            platform=platform,
            campaign_id=campaign_id,
        )

        if profit_data.get("status") != "success":
            # Create empty report
            report = ProfitROASReport(
                tenant_id=self.tenant_id,
                report_type=report_type,
                period_start=start_date,
                period_end=end_date,
                platform=platform,
                campaign_id=campaign_id,
                category=category,
                generated_by_user_id=user_id,
            )
        else:
            financials = profit_data["financials"]
            roas = profit_data["roas"]
            margins = profit_data["margins"]
            breakeven = profit_data["breakeven"]

            report = ProfitROASReport(
                tenant_id=self.tenant_id,
                report_type=report_type,
                period_start=start_date,
                period_end=end_date,
                platform=platform,
                campaign_id=campaign_id,
                category=category,
                total_units=profit_data["volume"]["units_sold"],
                total_revenue_cents=int(financials["revenue"] * 100),
                total_cogs_cents=int(financials["cogs"] * 100),
                total_ad_spend_cents=int(financials["ad_spend"] * 100),
                total_gross_profit_cents=int(financials["gross_profit"] * 100),
                total_net_profit_cents=int(financials["net_profit"] * 100),
                revenue_roas=roas["revenue_roas"],
                gross_profit_roas=roas["gross_profit_roas"],
                net_profit_roas=roas["net_profit_roas"],
                avg_gross_margin_pct=margins["gross_margin_pct"],
                avg_net_margin_pct=margins["net_margin_pct"],
                breakeven_roas=breakeven["breakeven_roas"],
                above_breakeven=breakeven["above_breakeven"],
                generated_by_user_id=user_id,
            )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"Generated profit report {report.id} for {start_date} to {end_date}")
        return report

    async def _get_cogs(
        self,
        product_id: Optional[UUID],
        category: Optional[str],
        platform: Optional[str],
        campaign_id: Optional[str],
        revenue_cents: int,
        units_sold: int,
        effective_date: date,
    ) -> dict[str, Any]:
        """
        Get COGS for a product/transaction.

        Priority:
        1. Product-specific COGS
        2. Margin rules (by priority)
        3. Default 70% COGS assumption
        """
        # Try product-specific COGS first
        if product_id:
            result = await self.db.execute(
                select(ProductMargin)
                .where(
                    and_(
                        ProductMargin.product_id == product_id,
                        ProductMargin.effective_date <= effective_date,
                        or_(
                            ProductMargin.end_date.is_(None),
                            ProductMargin.end_date >= effective_date,
                        ),
                    )
                )
                .order_by(ProductMargin.effective_date.desc())
                .limit(1)
            )
            margin = result.scalar_one_or_none()

            if margin:
                if margin.total_cogs_cents:
                    return {
                        "cogs_cents": margin.total_cogs_cents * units_sold,
                        "is_estimated": False,
                        "source": margin.source.value,
                    }
                elif margin.cogs_cents:
                    return {
                        "cogs_cents": margin.cogs_cents * units_sold,
                        "is_estimated": False,
                        "source": margin.source.value,
                    }
                elif margin.cogs_percentage:
                    return {
                        "cogs_cents": int(revenue_cents * margin.cogs_percentage / 100),
                        "is_estimated": False,
                        "source": margin.source.value,
                    }

        # Try margin rules
        rule = await self._find_margin_rule(category, platform, campaign_id)
        if rule:
            if rule.default_cogs_percentage:
                return {
                    "cogs_cents": int(revenue_cents * rule.default_cogs_percentage / 100),
                    "is_estimated": True,
                    "source": f"rule:{rule.name}",
                    "margin_rule_id": rule.id,
                }
            elif rule.default_margin_percentage:
                cogs_pct = 100 - rule.default_margin_percentage
                return {
                    "cogs_cents": int(revenue_cents * cogs_pct / 100),
                    "is_estimated": True,
                    "source": f"rule:{rule.name}",
                    "margin_rule_id": rule.id,
                }

        # Default: assume 70% COGS (30% margin)
        return {
            "cogs_cents": int(revenue_cents * 0.70),
            "is_estimated": True,
            "source": "default",
        }

    async def _find_margin_rule(
        self,
        category: Optional[str],
        platform: Optional[str],
        campaign_id: Optional[str],
    ) -> Optional[MarginRule]:
        """Find the most specific applicable margin rule."""
        conditions = [
            MarginRule.tenant_id == self.tenant_id,
            MarginRule.is_active == True,
        ]

        # Build OR conditions for matching rules
        match_conditions = []

        if campaign_id:
            match_conditions.append(MarginRule.campaign_id == campaign_id)

        if platform:
            match_conditions.append(
                and_(
                    MarginRule.platform == platform,
                    MarginRule.campaign_id.is_(None),
                )
            )

        if category:
            match_conditions.append(
                and_(
                    MarginRule.category == category,
                    MarginRule.platform.is_(None),
                    MarginRule.campaign_id.is_(None),
                )
            )

        # Default rule (no filters)
        match_conditions.append(
            and_(
                MarginRule.category.is_(None),
                MarginRule.platform.is_(None),
                MarginRule.campaign_id.is_(None),
            )
        )

        if match_conditions:
            conditions.append(or_(*match_conditions))

        result = await self.db.execute(
            select(MarginRule).where(and_(*conditions)).order_by(MarginRule.priority).limit(1)
        )
        return result.scalar_one_or_none()
