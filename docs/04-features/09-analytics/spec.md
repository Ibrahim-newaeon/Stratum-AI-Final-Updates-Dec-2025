# Analytics Dashboard Specification

## Overview

The Analytics Dashboard provides comprehensive performance insights across all advertising platforms with trend analysis, demographic breakdowns, and executive summaries.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ANALYTICS ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   DATA SOURCES                            │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   Meta   │ │  Google  │ │  TikTok  │ │ Snapchat │   │  │
│  │  │   Ads    │ │   Ads    │ │   Ads    │ │   Ads    │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  │       └──────────┬─┴───────────┬┴────────────┘          │  │
│  └──────────────────┼─────────────┼────────────────────────┘  │
│                     ▼             ▼                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  DATA AGGREGATION                         │  │
│  │                                                          │  │
│  │  • Campaign metrics collection                           │  │
│  │  • Time-series aggregation                               │  │
│  │  • Cross-platform normalization                          │  │
│  │  • Trend calculation                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   ANALYTICS VIEWS                         │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   KPI    │ │ Demo-    │ │ Platform │ │Executive │   │  │
│  │  │  Tiles   │ │ graphics │ │ Breakdown│ │ Summary  │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  │  ┌──────────┐ ┌──────────┐                             │  │
│  │  │ Heatmap  │ │  Trends  │                             │  │
│  │  │  Chart   │ │  Chart   │                             │  │
│  │  └──────────┘ └──────────┘                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Period Types

```python
class AnalyticsPeriod(str, Enum):
    TODAY = "today"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
```

### KPI Tile

```python
class KPITile:
    metric: str                    # Metric name (spend, revenue, roas, etc.)
    value: float                   # Current value
    previous_value: float          # Previous period value
    trend: float                   # Percentage change
    trend_direction: str           # up, down, flat
    format: str                    # currency, percentage, number
```

### Demographics Data

```python
class DemographicsBreakdown:
    age_groups: list[AgeGroupMetrics]
    genders: list[GenderMetrics]
    locations: list[LocationMetrics]
    devices: list[DeviceMetrics]

class AgeGroupMetrics:
    age_group: str                 # 18-24, 25-34, etc.
    impressions: int
    clicks: int
    conversions: int
    spend_cents: int
    revenue_cents: int
```

### Heatmap Data

```python
class HeatmapData:
    day_of_week: int               # 0-6 (Monday-Sunday)
    hour: int                      # 0-23
    metric: str                    # Metric being displayed
    value: float                   # Metric value
    intensity: float               # 0-1 normalized intensity
```

### Platform Breakdown

```python
class PlatformBreakdown:
    platform: str                  # meta, google, tiktok, snapchat
    campaigns_count: int
    active_campaigns: int
    spend_cents: int
    revenue_cents: int
    roas: float
    impressions: int
    clicks: int
    conversions: int
    ctr: float
    cpc_cents: int
```

### Executive Summary

```python
class ExecutiveSummary:
    period: AnalyticsPeriod
    total_spend_cents: int
    total_revenue_cents: int
    overall_roas: float
    total_campaigns: int
    active_campaigns: int
    top_performers: list[CampaignSummary]
    underperformers: list[CampaignSummary]
    recommendations: list[str]
    health_score: float            # Overall account health
```

---

## KPI Metrics

### Core Metrics

| Metric | Calculation | Format |
|--------|-------------|--------|
| `total_spend` | Sum of campaign spend | Currency |
| `total_revenue` | Sum of campaign revenue | Currency |
| `roas` | Revenue / Spend | Ratio (X.XX) |
| `impressions` | Sum of impressions | Number |
| `clicks` | Sum of clicks | Number |
| `conversions` | Sum of conversions | Number |
| `ctr` | Clicks / Impressions × 100 | Percentage |
| `cpc` | Spend / Clicks | Currency |
| `cpm` | Spend / Impressions × 1000 | Currency |
| `cpa` | Spend / Conversions | Currency |
| `conversion_rate` | Conversions / Clicks × 100 | Percentage |

### Trend Calculation

```python
def calculate_trend(current: float, previous: float) -> tuple[float, str]:
    """Calculate trend percentage and direction."""
    if previous == 0:
        return (0, "flat") if current == 0 else (100, "up")

    change = ((current - previous) / previous) * 100

    if change > 1:
        direction = "up"
    elif change < -1:
        direction = "down"
    else:
        direction = "flat"

    return (round(change, 2), direction)
```

### Period Comparison

```python
def get_comparison_period(period: AnalyticsPeriod) -> tuple[datetime, datetime]:
    """Get previous period for comparison."""
    today = datetime.now(timezone.utc).date()

    if period == AnalyticsPeriod.TODAY:
        current_start = today
        previous_start = today - timedelta(days=1)
    elif period == AnalyticsPeriod.LAST_7_DAYS:
        current_start = today - timedelta(days=7)
        previous_start = today - timedelta(days=14)
    elif period == AnalyticsPeriod.LAST_30_DAYS:
        current_start = today - timedelta(days=30)
        previous_start = today - timedelta(days=60)
    elif period == AnalyticsPeriod.LAST_90_DAYS:
        current_start = today - timedelta(days=90)
        previous_start = today - timedelta(days=180)

    return (current_start, previous_start)
```

---

## Views

### Dashboard Overview

Primary view showing KPI tiles with trends.

**Components:**
- 6-8 KPI tiles with sparklines
- Period selector
- Quick filters (platform, campaign status)

### Demographics View

Audience breakdown across dimensions.

**Components:**
- Age group bar chart
- Gender pie chart
- Location heat map
- Device breakdown

### Performance Heatmap

Time-based performance visualization.

**Components:**
- 7×24 grid (day × hour)
- Color intensity for metric values
- Metric selector (CTR, CPC, Conversions)

### Platform Breakdown

Cross-platform comparison view.

**Components:**
- Platform comparison table
- Spend allocation pie chart
- ROAS by platform bar chart
- Campaign distribution

### Trends View

Time-series performance charts.

**Components:**
- Multi-line trend chart
- Metric selector (multi-select)
- Date range picker
- Annotation markers for events

### Executive Summary

High-level performance report.

**Components:**
- Key metrics summary
- Top/bottom performers
- AI-generated recommendations
- Health score indicator

---

## Aggregation Strategy

### Real-Time vs Cached

| Data Type | Strategy | TTL |
|-----------|----------|-----|
| KPI Tiles | Cached | 5 minutes |
| Demographics | Cached | 15 minutes |
| Heatmap | Cached | 30 minutes |
| Platform Breakdown | Cached | 10 minutes |
| Trends | Cached | 5 minutes |
| Executive Summary | Cached | 1 hour |

### Caching Implementation

```python
async def get_kpi_tiles(tenant_id: int, period: str) -> list[KPITile]:
    cache_key = f"analytics:kpis:{tenant_id}:{period}"

    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute from database
    tiles = await compute_kpi_tiles(tenant_id, period)

    # Cache result
    await redis.setex(cache_key, 300, json.dumps(tiles))

    return tiles
```

---

## Superadmin Analytics

### Tenant Overview

Cross-tenant performance metrics for platform administrators.

```python
class TenantOverview:
    tenant_id: int
    tenant_name: str
    total_campaigns: int
    active_campaigns: int
    total_spend_30d_cents: int
    total_revenue_30d_cents: int
    avg_roas: float
    last_activity: datetime
    health_status: str             # healthy, degraded, inactive
```

### Platform-Wide Metrics

- Total active tenants
- Total campaigns across all tenants
- Platform-wide spend/revenue
- Average ROAS across platform
- Tenant health distribution

---

## Export Capabilities

### Report Formats

| Format | Content | Use Case |
|--------|---------|----------|
| PDF | Executive summary | Stakeholder reports |
| CSV | Raw metrics | Data analysis |
| Excel | Multi-sheet workbook | Detailed reporting |

### Scheduled Reports

```python
class ScheduledReport:
    id: int
    tenant_id: int
    name: str
    report_type: str               # executive, detailed, custom
    schedule: str                  # daily, weekly, monthly
    recipients: list[str]          # Email addresses
    format: str                    # pdf, csv, excel
    filters: dict                  # Platform, campaign filters
    last_sent: datetime
    next_send: datetime
```

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
