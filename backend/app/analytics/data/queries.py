# =============================================================================
# Analytics SQL Queries
# =============================================================================
"""
Common SQL queries for analytics operations.
Based on Data_Schema_Events_and_Tables.md requirements.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Blended ROAS Query
# =============================================================================
BLENDED_ROAS_BY_DAY = """
    SELECT
        fpd.date,
        fpd.platform,
        SUM(fpd.spend) as total_spend,
        SUM(fpd.revenue) as platform_revenue,
        SUM(COALESCE(fg.revenue, 0)) as ga4_revenue,
        CASE
            WHEN SUM(fpd.spend) > 0 THEN SUM(fpd.revenue) / SUM(fpd.spend)
            ELSE 0
        END as platform_roas,
        CASE
            WHEN SUM(fpd.spend) > 0 THEN SUM(COALESCE(fg.revenue, 0)) / SUM(fpd.spend)
            ELSE 0
        END as ga4_roas,
        CASE
            WHEN SUM(fpd.spend) > 0 THEN
                (SUM(fpd.revenue) + SUM(COALESCE(fg.revenue, 0))) / 2 / SUM(fpd.spend)
            ELSE 0
        END as blended_roas
    FROM fact_platform_daily fpd
    LEFT JOIN fact_ga4_daily fg ON
        fpd.date = fg.date
        AND fpd.tenant_id = fg.tenant_id
        AND fpd.campaign_id = fg.utm_campaign
    WHERE fpd.tenant_id = :tenant_id
        AND fpd.date BETWEEN :start_date AND :end_date
    GROUP BY fpd.date, fpd.platform
    ORDER BY fpd.date DESC
"""


# =============================================================================
# Performance Table by Campaign
# =============================================================================
CAMPAIGN_PERFORMANCE = """
    WITH campaign_metrics AS (
        SELECT
            campaign_id,
            SUM(spend) as total_spend,
            SUM(revenue) as total_revenue,
            SUM(impressions) as total_impressions,
            SUM(clicks) as total_clicks,
            SUM(conversions) as total_conversions,
            AVG(frequency) as avg_frequency
        FROM fact_platform_daily
        WHERE tenant_id = :tenant_id
            AND date BETWEEN :start_date AND :end_date
            AND campaign_id IS NOT NULL
        GROUP BY campaign_id
    ),
    campaign_scoring AS (
        SELECT
            entity_id as campaign_id,
            AVG(score) as avg_score,
            MAX(action) as last_action
        FROM fact_scaling_scores
        WHERE tenant_id = :tenant_id
            AND date BETWEEN :start_date AND :end_date
            AND entity_level = 'campaign'
        GROUP BY entity_id
    )
    SELECT
        c.id,
        c.name,
        c.platform,
        cm.total_spend,
        cm.total_revenue,
        CASE WHEN cm.total_spend > 0 THEN cm.total_revenue / cm.total_spend ELSE 0 END as roas,
        cm.total_impressions,
        cm.total_clicks,
        cm.total_conversions,
        CASE WHEN cm.total_impressions > 0 THEN cm.total_clicks::float / cm.total_impressions * 100 ELSE 0 END as ctr,
        CASE WHEN cm.total_conversions > 0 THEN cm.total_spend / cm.total_conversions ELSE 0 END as cpa,
        cm.avg_frequency,
        cs.avg_score as scaling_score,
        cs.last_action as recommended_action
    FROM campaigns c
    LEFT JOIN campaign_metrics cm ON c.id::text = cm.campaign_id
    LEFT JOIN campaign_scoring cs ON c.id::text = cs.campaign_id
    WHERE c.tenant_id = :tenant_id
        AND c.is_deleted = false
    ORDER BY cm.total_spend DESC NULLS LAST
"""


# =============================================================================
# Creative Fatigue Dashboard
# =============================================================================
CREATIVE_FATIGUE_DASHBOARD = """
    SELECT
        fcd.creative_id,
        dc.creative_name,
        dc.format,
        fcd.date,
        fcd.spend,
        fcd.impressions,
        fcd.clicks,
        fcd.ctr,
        fcd.roas,
        fcd.frequency,
        fcd.fatigue_score,
        fcd.fatigue_state,
        -- Calculate 7-day average for comparison
        AVG(fcd.ctr) OVER (
            PARTITION BY fcd.creative_id
            ORDER BY fcd.date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) as ctr_7d_avg,
        AVG(fcd.roas) OVER (
            PARTITION BY fcd.creative_id
            ORDER BY fcd.date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) as roas_7d_avg
    FROM fact_creative_daily fcd
    LEFT JOIN dim_creative dc ON
        fcd.creative_id = dc.creative_id
        AND fcd.platform = dc.platform
        AND fcd.tenant_id = dc.tenant_id
    WHERE fcd.tenant_id = :tenant_id
        AND fcd.date BETWEEN :start_date AND :end_date
    ORDER BY fcd.fatigue_score DESC, fcd.date DESC
"""


# =============================================================================
# Anomaly Detection History
# =============================================================================
ANOMALY_HISTORY = """
    SELECT
        date,
        alert_type,
        severity,
        entity_level,
        entity_id,
        metric,
        current_value,
        baseline_value,
        zscore,
        message,
        resolved,
        resolved_time
    FROM fact_alerts
    WHERE tenant_id = :tenant_id
        AND date BETWEEN :start_date AND :end_date
        AND alert_type = 'anomaly'
    ORDER BY
        CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'low' THEN 4
            ELSE 5
        END,
        date DESC
"""


# =============================================================================
# Signal Health History
# =============================================================================
SIGNAL_HEALTH_HISTORY = """
    SELECT
        date,
        severity,
        message,
        resolved,
        resolved_time,
        acknowledged
    FROM fact_alerts
    WHERE tenant_id = :tenant_id
        AND alert_type = 'emq_degraded'
        AND date BETWEEN :start_date AND :end_date
    ORDER BY event_time DESC
"""


# =============================================================================
# Budget Actions Summary
# =============================================================================
BUDGET_ACTIONS_SUMMARY = """
    SELECT
        date,
        action,
        COUNT(*) as action_count,
        SUM(amount) as total_amount,
        AVG(scaling_score) as avg_score,
        SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) as executed_count
    FROM fact_budget_actions
    WHERE tenant_id = :tenant_id
        AND date BETWEEN :start_date AND :end_date
    GROUP BY date, action
    ORDER BY date DESC
"""


# =============================================================================
# Query Executor Functions
# =============================================================================
async def get_blended_roas(
    db: AsyncSession,
    tenant_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get blended ROAS by day."""
    result = await db.execute(
        text(BLENDED_ROAS_BY_DAY),
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def get_campaign_performance(
    db: AsyncSession,
    tenant_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get campaign performance table."""
    result = await db.execute(
        text(CAMPAIGN_PERFORMANCE),
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def get_creative_fatigue(
    db: AsyncSession,
    tenant_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get creative fatigue dashboard data."""
    result = await db.execute(
        text(CREATIVE_FATIGUE_DASHBOARD),
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def get_anomaly_history(
    db: AsyncSession,
    tenant_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get anomaly detection history."""
    result = await db.execute(
        text(ANOMALY_HISTORY),
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def get_budget_actions(
    db: AsyncSession,
    tenant_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get budget actions summary."""
    result = await db.execute(
        text(BUDGET_ACTIONS_SUMMARY),
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    )
    return [dict(row._mapping) for row in result.fetchall()]
