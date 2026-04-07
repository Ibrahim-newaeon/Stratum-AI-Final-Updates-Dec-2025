# Analytics Dashboard API Contracts

## Overview

Tenant-scoped API endpoints for analytics and reporting.

**Base URL**: `/api/v1/tenant/{tenant_id}/analytics`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## KPIs

### GET /analytics/kpis

Get KPI tiles with trends.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: today, 7d, 30d, 90d (default: 7d) |
| `platform` | string | Filter by platform (optional) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "7d",
    "comparison_period": "previous_7d",
    "tiles": [
      {
        "metric": "total_spend",
        "label": "Total Spend",
        "value": 45230.00,
        "previous_value": 40200.00,
        "trend": 12.5,
        "trend_direction": "up",
        "format": "currency"
      },
      {
        "metric": "total_revenue",
        "label": "Total Revenue",
        "value": 98450.00,
        "previous_value": 83200.00,
        "trend": 18.3,
        "trend_direction": "up",
        "format": "currency"
      },
      {
        "metric": "roas",
        "label": "ROAS",
        "value": 2.18,
        "previous_value": 2.07,
        "trend": 5.2,
        "trend_direction": "up",
        "format": "ratio"
      },
      {
        "metric": "impressions",
        "label": "Impressions",
        "value": 2400000,
        "previous_value": 2218000,
        "trend": 8.2,
        "trend_direction": "up",
        "format": "number"
      },
      {
        "metric": "clicks",
        "label": "Clicks",
        "value": 78500,
        "previous_value": 74000,
        "trend": 6.1,
        "trend_direction": "up",
        "format": "number"
      },
      {
        "metric": "conversions",
        "label": "Conversions",
        "value": 1245,
        "previous_value": 1018,
        "trend": 22.4,
        "trend_direction": "up",
        "format": "number"
      },
      {
        "metric": "ctr",
        "label": "CTR",
        "value": 3.27,
        "previous_value": 3.34,
        "trend": -0.8,
        "trend_direction": "down",
        "format": "percentage"
      },
      {
        "metric": "cpa",
        "label": "CPA",
        "value": 36.32,
        "previous_value": 39.49,
        "trend": -8.1,
        "trend_direction": "down",
        "format": "currency"
      }
    ],
    "generated_at": "2024-01-15T14:30:00Z"
  }
}
```

---

## Demographics

### GET /analytics/demographics

Get audience demographics breakdown.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: today, 7d, 30d, 90d (default: 7d) |
| `dimension` | string | age, gender, location, device (default: age) |
| `platform` | string | Filter by platform (optional) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "7d",
    "dimension": "age",
    "breakdown": [
      {
        "group": "18-24",
        "impressions": 768000,
        "clicks": 28320,
        "conversions": 399,
        "spend_cents": 1450000,
        "revenue_cents": 2610000,
        "roas": 1.80,
        "percentage": 32.0
      },
      {
        "group": "25-34",
        "impressions": 1152000,
        "clicks": 40320,
        "conversions": 598,
        "spend_cents": 2170000,
        "revenue_cents": 5208000,
        "roas": 2.40,
        "percentage": 48.0
      },
      {
        "group": "35-44",
        "impressions": 432000,
        "clicks": 15120,
        "conversions": 224,
        "spend_cents": 810000,
        "revenue_cents": 1701000,
        "roas": 2.10,
        "percentage": 18.0
      },
      {
        "group": "45-54",
        "impressions": 48000,
        "clicks": 1680,
        "conversions": 24,
        "spend_cents": 90000,
        "revenue_cents": 108000,
        "roas": 1.20,
        "percentage": 2.0
      }
    ],
    "insights": [
      "25-34 age group drives 48% of spend with best ROAS (2.4x)",
      "Consider reducing 45-54 targeting (low ROAS)"
    ]
  }
}
```

---

## Heatmap

### GET /analytics/heatmap

Get performance heatmap data (day × hour).

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: 7d, 30d (default: 7d) |
| `metric` | string | conversions, clicks, ctr, cpc (default: conversions) |
| `platform` | string | Filter by platform (optional) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "7d",
    "metric": "conversions",
    "data": [
      {
        "day": 0,
        "day_name": "Monday",
        "hours": [
          { "hour": 0, "value": 2, "intensity": 0.05 },
          { "hour": 1, "value": 1, "intensity": 0.02 },
          { "hour": 9, "value": 15, "intensity": 0.38 },
          { "hour": 12, "value": 28, "intensity": 0.70 },
          { "hour": 15, "value": 35, "intensity": 0.88 },
          { "hour": 18, "value": 40, "intensity": 1.00 },
          { "hour": 21, "value": 22, "intensity": 0.55 }
        ]
      },
      {
        "day": 4,
        "day_name": "Friday",
        "hours": [
          { "hour": 18, "value": 42, "intensity": 1.00 },
          { "hour": 19, "value": 45, "intensity": 1.00 },
          { "hour": 20, "value": 48, "intensity": 1.00 },
          { "hour": 21, "value": 38, "intensity": 0.95 }
        ]
      }
    ],
    "max_value": 48,
    "best_times": [
      { "day": "Friday", "hour_range": "18:00-21:00", "avg_value": 43.25 },
      { "day": "Saturday", "hour_range": "19:00-22:00", "avg_value": 39.50 }
    ]
  }
}
```

---

## Platform Breakdown

### GET /analytics/platform-breakdown

Get performance breakdown by platform.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: today, 7d, 30d, 90d (default: 7d) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "7d",
    "platforms": [
      {
        "platform": "meta",
        "platform_name": "Meta",
        "campaigns_count": 12,
        "active_campaigns": 10,
        "spend_cents": 1850000,
        "revenue_cents": 4255000,
        "roas": 2.30,
        "impressions": 1200000,
        "clicks": 40800,
        "conversions": 612,
        "ctr": 3.40,
        "cpc_cents": 453,
        "percentage_of_spend": 40.9
      },
      {
        "platform": "google",
        "platform_name": "Google Ads",
        "campaigns_count": 8,
        "active_campaigns": 7,
        "spend_cents": 1520000,
        "revenue_cents": 3800000,
        "roas": 2.50,
        "impressions": 800000,
        "clicks": 22400,
        "conversions": 448,
        "ctr": 2.80,
        "cpc_cents": 679,
        "percentage_of_spend": 33.6
      },
      {
        "platform": "tiktok",
        "platform_name": "TikTok",
        "campaigns_count": 5,
        "active_campaigns": 5,
        "spend_cents": 850000,
        "revenue_cents": 1445000,
        "roas": 1.70,
        "impressions": 350000,
        "clicks": 14700,
        "conversions": 147,
        "ctr": 4.20,
        "cpc_cents": 578,
        "percentage_of_spend": 18.8
      },
      {
        "platform": "snapchat",
        "platform_name": "Snapchat",
        "campaigns_count": 3,
        "active_campaigns": 2,
        "spend_cents": 303000,
        "revenue_cents": 345000,
        "roas": 1.14,
        "impressions": 50000,
        "clicks": 2550,
        "conversions": 38,
        "ctr": 5.10,
        "cpc_cents": 1188,
        "percentage_of_spend": 6.7
      }
    ],
    "totals": {
      "campaigns_count": 28,
      "active_campaigns": 24,
      "spend_cents": 4523000,
      "revenue_cents": 9845000,
      "roas": 2.18,
      "impressions": 2400000,
      "clicks": 78500,
      "conversions": 1245,
      "ctr": 3.27
    }
  }
}
```

---

## Trends

### GET /analytics/trends

Get time-series performance trends.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: 7d, 30d, 90d (default: 30d) |
| `metrics` | string | Comma-separated: spend, revenue, roas, ctr, conversions |
| `granularity` | string | day, week (default: day) |
| `platform` | string | Filter by platform (optional) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "granularity": "day",
    "metrics": ["spend", "revenue", "roas"],
    "series": [
      {
        "date": "2024-01-01",
        "spend": 1250.00,
        "revenue": 2750.00,
        "roas": 2.20
      },
      {
        "date": "2024-01-02",
        "spend": 1380.00,
        "revenue": 3105.00,
        "roas": 2.25
      },
      {
        "date": "2024-01-15",
        "spend": 1650.00,
        "revenue": 3795.00,
        "roas": 2.30
      }
    ],
    "summary": {
      "spend": { "min": 980.00, "max": 1850.00, "avg": 1507.67 },
      "revenue": { "min": 1960.00, "max": 4255.00, "avg": 3281.67 },
      "roas": { "min": 1.85, "max": 2.50, "avg": 2.18 }
    }
  }
}
```

---

## Executive Summary

### GET /analytics/executive-summary

Get high-level performance summary with recommendations.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: 7d, 30d, 90d (default: 30d) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "health_score": 85,
    "health_status": "healthy",
    "summary": {
      "total_spend_cents": 4523000,
      "total_revenue_cents": 9845000,
      "overall_roas": 2.18,
      "total_campaigns": 28,
      "active_campaigns": 24,
      "total_impressions": 2400000,
      "total_clicks": 78500,
      "total_conversions": 1245
    },
    "trends": {
      "spend_trend": 12.5,
      "revenue_trend": 18.3,
      "roas_trend": 5.2,
      "conversions_trend": 22.4
    },
    "top_performers": [
      {
        "campaign_id": 101,
        "name": "Summer Sale 2024",
        "platform": "meta",
        "spend_cents": 850000,
        "revenue_cents": 2850000,
        "roas": 3.35,
        "conversions": 285
      },
      {
        "campaign_id": 102,
        "name": "Q1 Promo Meta",
        "platform": "meta",
        "spend_cents": 650000,
        "revenue_cents": 1820000,
        "roas": 2.80,
        "conversions": 182
      },
      {
        "campaign_id": 103,
        "name": "Brand Awareness",
        "platform": "google",
        "spend_cents": 504000,
        "revenue_cents": 1210000,
        "roas": 2.40,
        "conversions": 121
      }
    ],
    "underperformers": [
      {
        "campaign_id": 115,
        "name": "Winter Campaign",
        "platform": "google",
        "spend_cents": 150000,
        "revenue_cents": 120000,
        "roas": 0.80,
        "conversions": 12,
        "issue": "ROAS below threshold"
      },
      {
        "campaign_id": 118,
        "name": "Test Campaign TT",
        "platform": "tiktok",
        "spend_cents": 75000,
        "revenue_cents": 45000,
        "roas": 0.60,
        "conversions": 5,
        "issue": "ROAS critically low"
      }
    ],
    "recommendations": [
      {
        "type": "pause",
        "priority": "high",
        "message": "Pause 'Winter Campaign' - ROAS 0.8x is below 1.0 threshold",
        "campaign_id": 115
      },
      {
        "type": "increase_budget",
        "priority": "medium",
        "message": "Increase budget on 'Summer Sale 2024' - strong performer at 3.35x ROAS",
        "campaign_id": 101,
        "suggested_increase_percent": 20
      },
      {
        "type": "review",
        "priority": "medium",
        "message": "Review TikTok targeting - high CTR but low ROAS indicates conversion issues"
      }
    ],
    "generated_at": "2024-01-15T14:30:00Z"
  }
}
```

---

## Tenant Overview (Superadmin)

### GET /admin/analytics/tenant-overview

Get cross-tenant performance overview. **Superadmin only.**

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: 7d, 30d, 90d (default: 30d) |
| `status` | string | Filter by health: healthy, degraded, unhealthy |
| `sort_by` | string | Sort field: spend, roas, campaigns (default: spend) |
| `order` | string | Sort order: asc, desc (default: desc) |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20) |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "tenants": [
      {
        "tenant_id": 1,
        "tenant_name": "Acme Corp",
        "campaigns_total": 28,
        "campaigns_active": 24,
        "spend_cents": 4523000,
        "revenue_cents": 9845000,
        "roas": 2.18,
        "health_status": "healthy",
        "health_score": 85,
        "last_activity": "2024-01-15T14:30:00Z"
      },
      {
        "tenant_id": 2,
        "tenant_name": "TechStart Inc",
        "campaigns_total": 15,
        "campaigns_active": 12,
        "spend_cents": 2810000,
        "revenue_cents": 5479500,
        "roas": 1.95,
        "health_status": "healthy",
        "health_score": 78,
        "last_activity": "2024-01-15T13:45:00Z"
      },
      {
        "tenant_id": 3,
        "tenant_name": "Fashion Brand",
        "campaigns_total": 22,
        "campaigns_active": 18,
        "spend_cents": 5200000,
        "revenue_cents": 7540000,
        "roas": 1.45,
        "health_status": "degraded",
        "health_score": 55,
        "last_activity": "2024-01-15T12:00:00Z"
      }
    ],
    "platform_totals": {
      "active_tenants": 156,
      "total_campaigns": 2450,
      "active_campaigns": 1980,
      "total_spend_cents": 125000000,
      "total_revenue_cents": 231250000,
      "average_roas": 1.85
    },
    "health_distribution": {
      "healthy": 112,
      "degraded": 32,
      "unhealthy": 12
    },
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 156,
      "total_pages": 8
    }
  }
}
```

---

## Export

### POST /analytics/export

Export analytics data.

#### Request

```json
{
  "report_type": "detailed",
  "period": "30d",
  "format": "csv",
  "sections": ["kpis", "demographics", "platform_breakdown", "trends"],
  "filters": {
    "platforms": ["meta", "google"]
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "processing",
    "estimated_completion": "2024-01-15T14:35:00Z"
  }
}
```

### GET /analytics/export/{export_id}

Get export status and download URL.

#### Response

```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "completed",
    "download_url": "https://cdn.stratum.ai/exports/exp_abc123.csv",
    "expires_at": "2024-01-16T14:30:00Z",
    "file_size_bytes": 245678
  }
}
```

---

## Scheduled Reports

### GET /analytics/scheduled-reports

List scheduled reports.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Weekly Executive Report",
      "report_type": "executive",
      "schedule": "weekly",
      "day_of_week": 1,
      "time": "09:00",
      "recipients": ["manager@company.com", "cmo@company.com"],
      "format": "pdf",
      "filters": {},
      "last_sent_at": "2024-01-08T09:00:00Z",
      "next_send_at": "2024-01-15T09:00:00Z",
      "is_active": true
    }
  ]
}
```

### POST /analytics/scheduled-reports

Create scheduled report.

#### Request

```json
{
  "name": "Weekly Executive Report",
  "report_type": "executive",
  "schedule": "weekly",
  "day_of_week": 1,
  "time": "09:00",
  "recipients": ["manager@company.com"],
  "format": "pdf",
  "filters": {
    "platforms": ["meta", "google"]
  }
}
```

### DELETE /analytics/scheduled-reports/{report_id}

Delete scheduled report.

#### Response

```
HTTP 204 No Content
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_PERIOD",
    "message": "Invalid period specified",
    "details": {
      "valid_periods": ["today", "7d", "30d", "90d"]
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_PERIOD` | 400 | Invalid time period specified |
| `INVALID_METRIC` | 400 | Invalid metric name |
| `EXPORT_NOT_FOUND` | 404 | Export job not found |
| `EXPORT_EXPIRED` | 410 | Export download link expired |
| `NO_DATA` | 404 | No data for specified filters |
| `RATE_LIMITED` | 429 | Too many export requests |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 120/min |
| Export creation | 10/hour |
| Scheduled report creation | 20/day |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
