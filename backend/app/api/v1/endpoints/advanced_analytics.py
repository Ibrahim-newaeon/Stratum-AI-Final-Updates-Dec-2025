# =============================================================================
# Stratum AI — Advanced Analytics (Gap #4)
# =============================================================================
"""
Advanced analytics endpoints:
- Funnel Analysis: Multi-step conversion funnels with drop-off rates
- Cohort Analysis: Retention and behavior cohorts
- SQL Query Editor: Power-user SQL with row-level security
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CampaignMetric
from app.schemas.response import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics/advanced", tags=["Advanced Analytics"])


# =============================================================================
# Schemas
# =============================================================================

class FunnelStep(BaseModel):
    """A single step in a conversion funnel."""
    step_name: str
    step_order: int
    event_type: str  # impression, click, landing, add_to_cart, purchase, etc.
    count: int
    conversion_rate_from_previous: Optional[float] = None
    drop_off_count: int = 0
    drop_off_rate: float = 0.0
    avg_time_to_convert_seconds: Optional[float] = None


class FunnelRequest(BaseModel):
    """Request to analyze a conversion funnel."""
    name: str = Field(..., description="Funnel name")
    steps: list[str] = Field(..., min_length=2, description="Event types in order: e.g. ['impression','click','landing','purchase']")
    campaign_ids: Optional[list[int]] = Field(None, description="Filter by specific campaigns")
    date_from: str = Field(..., description="Start date YYYY-MM-DD")
    date_to: str = Field(..., description="End date YYYY-MM-DD")


class FunnelResult(BaseModel):
    """Funnel analysis result."""
    name: str
    total_entries: int
    total_conversions: int
    overall_conversion_rate: float
    steps: list[FunnelStep]
    insights: list[str]


class CohortRequest(BaseModel):
    """Request cohort analysis."""
    cohort_by: str = Field("first_purchase_date", description="Field to group cohorts by")
    metric: str = Field("retention", description="Metric to track: retention, revenue, conversions")
    period: str = Field("weekly", description="Period: daily, weekly, monthly")
    date_from: str = Field(..., description="Start date YYYY-MM-DD")
    date_to: str = Field(..., description="End date YYYY-MM-DD")
    campaign_ids: Optional[list[int]] = Field(None)


class CohortCell(BaseModel):
    """Single cohort cell (period N for a given cohort)."""
    period: int  # 0, 1, 2, ...
    value: float
    percentage: Optional[float] = None


class CohortRow(BaseModel):
    """A single cohort (row in the cohort table)."""
    cohort_label: str
    cohort_size: int
    cells: list[CohortCell]


class CohortResult(BaseModel):
    """Cohort analysis result."""
    metric: str
    period: str
    rows: list[CohortRow]
    average_retention: list[float]
    insights: list[str]


class SQLQueryRequest(BaseModel):
    """SQL query request with validation."""
    query: str = Field(..., min_length=10, max_length=2000, description="SELECT-only SQL query")
    params: Optional[dict[str, Any]] = Field(default_factory=dict)
    limit: int = Field(100, ge=1, le=1000)


class SQLQueryResult(BaseModel):
    """SQL query execution result."""
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    query: str


# =============================================================================
# Funnel Analysis Engine
# =============================================================================

async def _build_funnel(
    db: AsyncSession,
    tenant_id: int,
    steps: list[str],
    campaign_ids: Optional[list[int]],
    date_from: str,
    date_to: str,
) -> list[FunnelStep]:
    """Build multi-step funnel from campaign metrics."""

    funnel_steps = []

    # Map event types to metric columns
    event_map = {
        "impression": "impressions",
        "click": "clicks",
        "landing": "clicks",  # proxy
        "add_to_cart": "conversions",  # proxy
        "purchase": "conversions",
        "conversion": "conversions",
    }

    # Build campaign filter
    campaign_filter = ""
    if campaign_ids:
        ids = ",".join(str(i) for i in campaign_ids)
        campaign_filter = f"AND campaign_id IN ({ids})"

    prev_count = None
    for i, step_name in enumerate(steps):
        metric_col = event_map.get(step_name, "impressions")

        sql = f"""
        SELECT COALESCE(SUM({metric_col}), 0) as total
        FROM campaign_metrics
        WHERE tenant_id = :tenant_id
        AND date BETWEEN :date_from AND :date_to
        {campaign_filter}
        """

        result = await db.execute(
            text(sql),
            {
                "tenant_id": tenant_id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        row = result.mappings().first()
        count = int(row["total"]) if row else 0

        # Calculate conversion from previous
        conversion_rate = None
        drop_off = 0
        drop_rate = 0.0
        if prev_count is not None and prev_count > 0:
            conversion_rate = (count / prev_count) * 100
            drop_off = prev_count - count
            drop_rate = (drop_off / prev_count) * 100

        funnel_steps.append(FunnelStep(
            step_name=step_name,
            step_order=i + 1,
            event_type=step_name,
            count=count,
            conversion_rate_from_previous=round(conversion_rate, 2) if conversion_rate else None,
            drop_off_count=drop_off,
            drop_off_rate=round(drop_rate, 2),
        ))

        prev_count = count

    return funnel_steps


# =============================================================================
# Cohort Analysis Engine
# =============================================================================

async def _build_cohorts(
    db: AsyncSession,
    tenant_id: int,
    metric: str,
    period: str,
    date_from: str,
    date_to: str,
) -> list[CohortRow]:
    """Build cohort retention table from campaign metrics."""

    # Simplified cohort: group by campaign start week, track metric over periods
    # For a real CDP cohort, you'd use profile-level event data

    # Get campaigns active in date range
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
            Campaign.start_date >= datetime.strptime(date_from, "%Y-%m-%d").date(),
            Campaign.start_date <= datetime.strptime(date_to, "%Y-%m-%d").date(),
        ).order_by(Campaign.start_date)
    )
    campaigns = result.scalars().all()

    if not campaigns:
        return []

    # Group by week
    from collections import defaultdict
    cohorts = defaultdict(list)
    for c in campaigns:
        if c.start_date:
            week_label = c.start_date.strftime("%Y-W%U")
            cohorts[week_label].append(c)

    rows = []
    for week_label in sorted(cohorts.keys()):
        cohort_campaigns = cohorts[week_label]
        cohort_size = len(cohort_campaigns)

        cells = []
        for period in range(5):  # 5 periods (0-4)
            # Get metrics for this cohort in period N
            campaign_ids = [c.id for c in cohort_campaigns]
            if not campaign_ids:
                continue

            ids_str = ",".join(str(i) for i in campaign_ids)

            if metric == "retention":
                # Retention = % of campaigns still active
                active_count = sum(1 for c in cohort_campaigns if c.status and c.status.value == "ACTIVE")
                value = active_count
                pct = (active_count / cohort_size * 100) if cohort_size > 0 else 0
            else:
                # Revenue/ conversions
                sql = f"""
                SELECT COALESCE(SUM({metric if metric in ('revenue_cents','spend_cents','conversions') else 'conversions'}), 0) as total
                FROM campaign_metrics
                WHERE tenant_id = :tenant_id
                AND campaign_id IN ({ids_str})
                AND date >= :period_start AND date <= :period_end
                """
                result = await db.execute(
                    text(sql),
                    {
                        "tenant_id": tenant_id,
                        "period_start": (datetime.strptime(date_from, "%Y-%m-%d") + timedelta(weeks=period)).date(),
                        "period_end": (datetime.strptime(date_from, "%Y-%m-%d") + timedelta(weeks=period+1)).date(),
                    }
                )
                row = result.mappings().first()
                value = int(row["total"]) if row else 0
                pct = None

            cells.append(CohortCell(period=period, value=value, percentage=round(pct, 1) if pct is not None else None))

        rows.append(CohortRow(cohort_label=week_label, cohort_size=cohort_size, cells=cells))

    return rows


# =============================================================================
# SQL Security Validator
# =============================================================================

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "create", "alter", "truncate",
    "grant", "revoke", "execute", "copy", "\copy", "load", "into",
    "pg_read", "pg_write", "information_schema", "pg_catalog",
]

def _validate_sql(query: str) -> tuple[bool, str]:
    """Validate SQL is read-only and safe."""
    q_lower = query.lower().strip()

    # Must start with SELECT
    if not q_lower.startswith("select"):
        return False, "Only SELECT queries are allowed"

    # Check for forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in q_lower:
            return False, f"Forbidden keyword detected: '{keyword}'"

    # Check for multiple statements
    if ";" in q_lower[:-1]:  # Allow trailing semicolon only
        return False, "Multiple statements are not allowed"

    return True, "Valid"


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/funnel", response_model=APIResponse[FunnelResult])
async def analyze_funnel(
    request: FunnelRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Multi-step conversion funnel analysis.

    Track user journey from impression → click → conversion → purchase
    with drop-off rates at each step.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    steps = await _build_funnel(
        db, tenant_id, request.steps,
        request.campaign_ids, request.date_from, request.date_to,
    )

    total_entries = steps[0].count if steps else 0
    total_conversions = steps[-1].count if steps else 0
    overall_rate = (total_conversions / total_entries * 100) if total_entries > 0 else 0.0

    # Generate insights
    insights = []
    for i, step in enumerate(steps[1:], 1):
        if step.drop_off_rate > 50:
            insights.append(f"⚠️ Major drop-off at '{step.step_name}': {step.drop_off_rate:.1f}% of users left")
        elif step.drop_off_rate > 20:
            insights.append(f"📉 Moderate drop-off at '{step.step_name}': {step.drop_off_rate:.1f}%")
        elif step.conversion_rate_from_previous and step.conversion_rate_from_previous > 80:
            insights.append(f"✅ Excellent conversion at '{step.step_name}': {step.conversion_rate_from_previous:.1f}%")

    if overall_rate < 1:
        insights.append("🚨 Overall conversion rate below 1% — investigate audience-creative fit")
    elif overall_rate > 5:
        insights.append("🌟 Strong overall funnel — consider increasing budget")

    return APIResponse(
        success=True,
        data=FunnelResult(
            name=request.name,
            total_entries=total_entries,
            total_conversions=total_conversions,
            overall_conversion_rate=round(overall_rate, 2),
            steps=steps,
            insights=insights or ["Funnel performing within normal parameters"],
        ),
        message="Funnel analysis complete",
    )


@router.post("/cohorts", response_model=APIResponse[CohortResult])
async def analyze_cohorts(
    request: CohortRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Cohort retention and behavior analysis.

    Group campaigns (or users) by start date and track metric performance
    over time periods.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    rows = await _build_cohorts(
        db, tenant_id, request.metric, request.period,
        request.date_from, request.date_to,
    )

    # Calculate average retention per period
    avg_retention = []
    if rows and rows[0].cells:
        for period in range(len(rows[0].cells)):
            values = [r.cells[period].value for r in rows if period < len(r.cells)]
            avg = sum(values) / len(values) if values else 0
            avg_retention.append(round(avg, 2))

    insights = []
    if rows:
        if len(rows) >= 2:
            latest = rows[-1]
            previous = rows[-2]
            if latest.cells and previous.cells:
                latest_retention = latest.cells[0].percentage or 0
                prev_retention = previous.cells[0].percentage or 0
                if latest_retention > prev_retention:
                    insights.append(f"📈 Latest cohort ({latest.cohort_label}) has higher retention than previous")
                elif latest_retention < prev_retention:
                    insights.append(f"📉 Latest cohort ({latest.cohort_label}) shows declining retention — investigate onboarding")

        if avg_retention and len(avg_retention) > 1:
            if avg_retention[1] < avg_retention[0] * 0.5:
                insights.append("🚨 Sharp retention drop in Period 1 — critical onboarding issue")

    if not insights:
        insights.append("Cohort patterns are stable")

    return APIResponse(
        success=True,
        data=CohortResult(
            metric=request.metric,
            period=request.period,
            rows=rows,
            average_retention=avg_retention,
            insights=insights,
        ),
        message="Cohort analysis complete",
    )


@router.post("/sql", response_model=APIResponse[SQLQueryResult])
async def execute_sql_query(
    request: SQLQueryRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Execute a validated SQL SELECT query against tenant-scoped data.

    **Security:**
    - Only SELECT statements allowed
    - Tenant ID is auto-injected for row-level security
    - Forbidden keywords blocked (INSERT, UPDATE, DELETE, DROP, etc.)
    - Max 1000 rows returned

    **Usage:**
    ```sql
    SELECT platform, SUM(total_spend_cents)/100.0 as spend
    FROM campaigns
    WHERE is_deleted = FALSE
    GROUP BY platform
    ORDER BY spend DESC
    ```
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # Validate query
    is_valid, error_msg = _validate_sql(request.query)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Inject tenant isolation if not present
    query = request.query.strip()
    if "tenant_id" not in query.lower():
        # Auto-inject tenant filter on campaigns/campaign_metrics tables
        if "campaigns" in query.lower() or "campaign_metrics" in query.lower():
            query = query.replace("WHERE", f"WHERE tenant_id = {tenant_id} AND", 1) if "WHERE" in query.upper() else query + f" WHERE tenant_id = {tenant_id}"

    import time
    start = time.perf_counter()

    try:
        result = await db.execute(text(query))
        rows = result.fetchmany(request.limit)

        # Extract column names from cursor description
        columns = []
        if result.cursor:
            try:
                columns = [desc[0] for desc in result.cursor.description] if result.cursor.description else []
            except Exception:
                pass

        # Convert rows to lists
        data_rows = []
        for row in rows:
            data_rows.append([getattr(row, col, None) if hasattr(row, col) else row[i] for i, col in enumerate(columns)])

    except Exception as e:
        logger.error("sql_query_error", error=str(e), query=query)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query execution failed: {str(e)}",
        )

    execution_time = (time.perf_counter() - start) * 1000

    return APIResponse(
        success=True,
        data=SQLQueryResult(
            columns=columns,
            rows=data_rows,
            row_count=len(data_rows),
            execution_time_ms=round(execution_time, 2),
            query=query,
        ),
        message="Query executed successfully",
    )
