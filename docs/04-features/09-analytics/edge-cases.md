# Analytics Dashboard Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Analytics Dashboard.

---

## Edge Cases

### 1. No Campaign Data

**Scenario**: New tenant with no campaigns or data.

**Behavior**:
- KPI tiles show zero values
- Charts display empty state
- No trends available

**Response**:
```json
{
  "success": true,
  "data": {
    "tiles": [
      {
        "metric": "total_spend",
        "value": 0,
        "previous_value": 0,
        "trend": 0,
        "trend_direction": "flat"
      }
    ],
    "message": "No campaign data available for this period"
  }
}
```

**UI Handling**:
```
┌─────────────────────────────────────────────────────────────┐
│                    No Data Yet                              │
│                                                             │
│   You haven't run any campaigns in the selected period.    │
│                                                             │
│   [Create Your First Campaign]                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. Division by Zero in Metrics

**Scenario**: Computing CTR/CPC/CPA with zero denominator.

**Behavior**:
- Handled gracefully at calculation time
- Returns null or 0 for undefined metrics
- Does not affect other calculations

**Handling**:
```python
def calculate_ctr(clicks: int, impressions: int) -> float | None:
    if impressions == 0:
        return None
    return round((clicks / impressions) * 100, 2)

def calculate_cpa(spend_cents: int, conversions: int) -> float | None:
    if conversions == 0:
        return None
    return round(spend_cents / conversions / 100, 2)
```

**Response**:
```json
{
  "metric": "cpa",
  "value": null,
  "label": "CPA",
  "format": "currency",
  "note": "No conversions in period"
}
```

---

### 3. Trend Calculation Edge Cases

**Scenario**: Previous period has zero value.

**Behavior**:
- If both periods are zero: trend = 0, flat
- If previous is zero, current is positive: trend = 100, up
- If previous is zero, current is negative: handled for revenue refunds

**Handling**:
```python
def calculate_trend(current: float, previous: float) -> tuple[float, str]:
    if previous == 0:
        if current == 0:
            return (0, "flat")
        elif current > 0:
            return (100, "up")  # New metric, 100% increase
        else:
            return (-100, "down")  # Edge case for negative values

    change = ((current - previous) / abs(previous)) * 100
    direction = "up" if change > 1 else ("down" if change < -1 else "flat")

    return (round(change, 2), direction)
```

---

### 4. Large Data Volume

**Scenario**: Tenant with 500+ campaigns over 90 days.

**Behavior**:
- Query optimization with proper indexing
- Aggregation at database level
- Pagination for detailed views

**Mitigation**:
```python
async def get_analytics_optimized(tenant_id: int, period: str):
    # Use materialized view for large tenants
    if await count_campaigns(tenant_id) > 100:
        return await get_from_materialized_view(tenant_id, period)

    # Direct query for smaller tenants
    return await calculate_analytics_direct(tenant_id, period)
```

---

### 5. Cache Invalidation

**Scenario**: Campaign data updated but cache not refreshed.

**Behavior**:
- Time-based expiration (5-30 min TTL)
- Manual cache invalidation on significant events
- User can force refresh

**Handling**:
```python
async def invalidate_analytics_cache(tenant_id: int):
    patterns = [
        f"analytics:kpis:{tenant_id}:*",
        f"analytics:trends:{tenant_id}:*",
        f"analytics:platform:{tenant_id}:*"
    ]
    for pattern in patterns:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
```

**Response with refresh**:
```json
{
  "success": true,
  "data": { "...": "..." },
  "cache": {
    "hit": false,
    "generated_at": "2024-01-15T14:30:00Z",
    "expires_at": "2024-01-15T14:35:00Z"
  }
}
```

---

### 6. Cross-Platform Data Sync Delays

**Scenario**: Platform API data not yet synced.

**Behavior**:
- Show last sync timestamp
- Indicate stale data
- Continue with available data

**Response**:
```json
{
  "success": true,
  "data": { "...": "..." },
  "data_freshness": {
    "meta": {
      "last_sync": "2024-01-15T14:00:00Z",
      "status": "fresh"
    },
    "google": {
      "last_sync": "2024-01-15T12:00:00Z",
      "status": "stale",
      "warning": "Data may be up to 2 hours old"
    }
  }
}
```

---

### 7. Export Large Dataset

**Scenario**: Exporting 90 days of granular data.

**Behavior**:
- Async export processing
- Email notification when complete
- Download link with expiration

**Response**:
```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "queued",
    "estimated_time_seconds": 120,
    "notification_email": "user@company.com"
  },
  "message": "Export started. You'll receive an email when it's ready."
}
```

---

### 8. Timezone Handling

**Scenario**: User in different timezone than campaign data.

**Behavior**:
- All dates stored in UTC
- Display converted to user timezone
- Period boundaries calculated in user timezone

**Handling**:
```python
def get_period_boundaries(period: str, timezone: str) -> tuple[datetime, datetime]:
    user_tz = pytz.timezone(timezone)
    now_local = datetime.now(user_tz)

    if period == "today":
        start = now_local.replace(hour=0, minute=0, second=0)
        end = now_local
    elif period == "7d":
        start = (now_local - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        end = now_local

    # Convert to UTC for query
    return (start.astimezone(pytz.UTC), end.astimezone(pytz.UTC))
```

---

### 9. Heatmap With Sparse Data

**Scenario**: Not enough data points for meaningful heatmap.

**Behavior**:
- Minimum data threshold check
- Show warning if insufficient
- Still display available data

**Response**:
```json
{
  "success": true,
  "data": {
    "data": [ "..." ],
    "coverage": 0.35,
    "warning": "Limited data coverage (35%). Heatmap may not be representative."
  }
}
```

---

### 10. Scheduled Report Delivery Failure

**Scenario**: Email delivery fails for scheduled report.

**Behavior**:
- Retry up to 3 times with backoff
- Log failure for admin review
- Mark as failed after retries

**Handling**:
```python
async def send_scheduled_report(report_id: int, retry_count: int = 0):
    try:
        report = await generate_report(report_id)
        await send_email(report.recipients, report)
        await mark_report_sent(report_id)
    except EmailDeliveryError as e:
        if retry_count < 3:
            delay = 60 * (2 ** retry_count)  # Exponential backoff
            await schedule_retry(report_id, delay, retry_count + 1)
        else:
            await mark_report_failed(report_id, str(e))
            await notify_admin(report_id, e)
```

---

### 11. Demographics Data Not Available

**Scenario**: Platform doesn't provide demographic breakdown.

**Behavior**:
- Return partial data for available platforms
- Indicate missing data source
- Aggregate from available sources only

**Response**:
```json
{
  "success": true,
  "data": {
    "dimension": "age",
    "breakdown": [ "..." ],
    "data_sources": {
      "meta": "available",
      "google": "available",
      "tiktok": "limited",
      "snapchat": "not_available"
    },
    "note": "Demographics based on Meta and Google data only"
  }
}
```

---

### 12. Executive Summary Generation Timeout

**Scenario**: AI recommendations take too long to generate.

**Behavior**:
- Return summary without recommendations
- Queue recommendations for async delivery
- Indicate partial result

**Response**:
```json
{
  "success": true,
  "data": {
    "summary": { "...": "..." },
    "recommendations": null,
    "recommendations_status": "processing",
    "note": "AI recommendations will be available shortly"
  }
}
```

---

## Known Limitations

### 1. Real-Time Data Not Available

**Limitation**: Data refreshes every 15-60 minutes.

**Impact**: Recent changes may not immediately appear.

**Workaround**: Manual refresh available; tooltip shows last sync time.

---

### 2. Cross-Platform Attribution

**Limitation**: Cannot track cross-platform customer journeys.

**Impact**: May undercount conversions from multi-touch paths.

**Planned**: Cross-platform attribution model.

---

### 3. Custom Date Ranges

**Limitation**: Only predefined periods (today, 7d, 30d, 90d).

**Impact**: Cannot select arbitrary date ranges.

**Planned**: Custom date picker with range selection.

---

### 4. Limited Historical Data

**Limitation**: Analytics retained for 13 months.

**Impact**: Cannot view data older than 13 months.

**Workaround**: Export data before expiration for long-term storage.

---

## Error Recovery

### Data Errors

| Error | Recovery |
|-------|----------|
| Database timeout | Retry with cached data fallback |
| Platform API error | Show last known data with warning |
| Calculation error | Skip metric, log error, continue |

### Export Errors

| Error | Recovery |
|-------|----------|
| Generation timeout | Retry with smaller date range |
| Storage error | Retry, notify user |
| Email delivery failed | Retry, provide download link |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Dashboard load time | > 3 seconds |
| Cache hit rate | < 80% |
| Export success rate | < 95% |
| Scheduled report delivery | < 98% |
| Data freshness | > 4 hours stale |

### Health Checks

```python
async def analytics_health():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "redis": await check_redis(),
            "data_freshness": await check_data_freshness(),
            "export_queue": await check_export_queue(),
            "scheduled_reports": await check_scheduled_reports()
        }
    }
```

---

## Performance Optimization

### Query Optimization

- Materialized views for aggregations
- Proper indexing on tenant_id, created_at
- Query result caching

### Caching Strategy

| Data Type | Cache TTL | Invalidation |
|-----------|-----------|--------------|
| KPIs | 5 min | On campaign update |
| Demographics | 15 min | Time-based |
| Heatmap | 30 min | Time-based |
| Trends | 5 min | On campaign update |
| Executive Summary | 1 hour | Manual |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
