# Data Schema (Events + Tables)
Target: Warehouse-first model (BigQuery-style). Works for Meta/Google/TikTok/Snap + GA4.

## A) Event Schema (canonical JSON)

All events share:
- `event_name` (string)
- `event_time` (ISO8601)
- `event_id` (string, dedup)
- `source` ("ga4" | "platform" | "server")
- `platform` ("meta" | "google" | "tiktok" | "snap" | "unknown")
- `account_id`, `campaign_id`, `adset_id`, `ad_id`, `creative_id` (nullable)
- `user` object (hashed identifiers if available)
- `context` object (utm, page, device)
- `value` object (amount, currency)
- `quality` object (emq, event_loss, api_health)

### 1) purchase
```json
{
  "event_name": "purchase",
  "event_time": "2026-01-02T10:20:11Z",
  "event_id": "evt_9f3b...",
  "source": "ga4",
  "platform": "meta",
  "account_id": "act_123",
  "campaign_id": "cmp_456",
  "adset_id": "as_789",
  "ad_id": "ad_111",
  "creative_id": "cr_222",
  "user": {
    "client_id": "GA4.123...",
    "email_sha256": "hash...",
    "phone_sha256": "hash..."
  },
  "context": {
    "utm_source": "facebook",
    "utm_medium": "paid_social",
    "utm_campaign": "CBO_Prospecting",
    "page_location": "https://site.com/checkout/thankyou",
    "device_category": "mobile",
    "geo_country": "SA"
  },
  "value": {
    "revenue": 499.00,
    "currency": "SAR",
    "items": 2
  },
  "quality": {
    "emq_score": 94,
    "event_loss_pct": 2.1,
    "api_health": "good"
  }
}
```

### 2) lead_submit
```json
{
  "event_name": "lead_submit",
  "event_time": "2026-01-02T10:05:00Z",
  "event_id": "evt_11aa...",
  "source": "platform",
  "platform": "tiktok",
  "account_id": "tt_123",
  "campaign_id": "tt_cmp_1",
  "adset_id": "tt_ag_9",
  "ad_id": "tt_ad_7",
  "user": { "email_sha256": "hash..." },
  "context": { "form_id": "instant_form_22", "utm_source": "tiktok" },
  "value": { "lead_value": 0, "currency": "SAR" },
  "quality": { "emq_score": null, "event_loss_pct": null, "api_health": "good" }
}
```

### 3) roas_alert
```json
{
  "event_name": "roas_alert",
  "event_time": "2026-01-02T12:00:00Z",
  "event_id": "evt_roas_...",
  "source": "server",
  "platform": "unknown",
  "account_id": "act_123",
  "context": { "window_days": 7, "threshold": 2.0 },
  "value": { "roas": 1.62, "spend": 25000, "revenue": 40500, "currency": "SAR" },
  "quality": { "api_health": "good" }
}
```

### 4) emq_degraded
```json
{
  "event_name": "emq_degraded",
  "event_time": "2026-01-02T09:30:00Z",
  "event_id": "evt_emq_...",
  "source": "server",
  "platform": "meta",
  "account_id": "act_123",
  "context": { "emq_target": 90, "event_loss_target": 5 },
  "value": { "emq_score": 78, "event_loss_pct": 11.4 },
  "quality": { "api_health": "good" }
}
```

### 5) auto_resolve_applied
```json
{
  "event_name": "auto_resolve_applied",
  "event_time": "2026-01-02T09:45:00Z",
  "event_id": "evt_fix_...",
  "source": "server",
  "platform": "meta",
  "account_id": "act_123",
  "context": { "playbook": "pause_automation_and_notify", "run_id": "run_555" },
  "value": { "actions": ["suspend_automation", "create_ticket", "notify_slack"] },
  "quality": { "api_health": "good" }
}
```

---

## B) Warehouse Tables (BigQuery-style DDL)

### Dimensions
- `dim_date`
- `dim_platform`
- `dim_account`
- `dim_campaign`
- `dim_adgroup` (adset/adgroup)
- `dim_ad`
- `dim_creative`

### Facts
- `fact_platform_daily` (platform KPIs by entity)
- `fact_ga4_daily` (GA4 KPIs by entity)
- `fact_funnel_daily` (stage metrics)
- `fact_creative_daily` (creative metrics + fatigue score)
- `fact_alerts` (anomalies + system alerts)
- `fact_events_raw` (canonical JSON events, optional)

See `schema.sql` for full DDL.

---

## C) Key joins
- Join on `{platform, account_id, campaign_id, adgroup_id, ad_id, creative_id, date}`
- If GA4 cannot map ad_id/creative_id, fallback to `{utm_campaign, utm_content, gclid/fbclid}` mapping table.
