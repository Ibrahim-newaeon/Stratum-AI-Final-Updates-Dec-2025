-- =============================================================================
-- Stratum AI - Seed Demo Data for Tenant 1
-- =============================================================================
-- 14 campaigns across 5 platforms with 90 days of daily metrics
-- Run via: railway connect Postgres < backend/scripts/seed_data.sql

BEGIN;

-- Verify tenant 1 exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1) THEN
    RAISE EXCEPTION 'Tenant 1 does not exist';
  END IF;
END $$;

-- Clean up existing demo data (idempotent)
DELETE FROM fact_platform_daily WHERE tenant_id = 1;
DELETE FROM campaign_metrics WHERE tenant_id = 1;
DELETE FROM campaigns WHERE tenant_id = 1;
DELETE FROM tenant_ad_account WHERE tenant_id = 1;
DELETE FROM tenant_platform_connection WHERE tenant_id = 1;
DELETE FROM tenant_onboarding WHERE tenant_id = 1;

-- =============================================================================
-- Platform Connections
-- =============================================================================
INSERT INTO tenant_platform_connection (id, tenant_id, platform, status, connected_at, created_at, updated_at)
VALUES
  (gen_random_uuid(), 1, 'meta',     'connected', NOW() - INTERVAL '60 days', NOW(), NOW()),
  (gen_random_uuid(), 1, 'google',   'connected', NOW() - INTERVAL '55 days', NOW(), NOW()),
  (gen_random_uuid(), 1, 'tiktok',   'connected', NOW() - INTERVAL '45 days', NOW(), NOW()),
  (gen_random_uuid(), 1, 'snapchat', 'connected', NOW() - INTERVAL '30 days', NOW(), NOW()),
  (gen_random_uuid(), 1, 'linkedin', 'connected', NOW() - INTERVAL '20 days', NOW(), NOW());

-- =============================================================================
-- Onboarding (completed)
-- =============================================================================
INSERT INTO tenant_onboarding (
  tenant_id, status, current_step, completed_steps,
  industry, monthly_ad_spend, team_size, primary_kpi,
  target_roas, automation_mode, started_at, completed_at
) VALUES (
  1, 'completed', 'trust_gate_config',
  '["business_profile","platform_selection","goals_setup","automation_preferences","trust_gate_config"]',
  'ecommerce', '50k_100k', '6_15', 'roas',
  3.0, 'autopilot', NOW() - INTERVAL '60 days', NOW() - INTERVAL '59 days'
);

-- =============================================================================
-- Campaigns (14 campaigns across platforms)
-- =============================================================================

-- Helper: We'll insert campaigns with computed aggregate metrics
-- Each campaign gets 90 days of daily data generated below

-- HIGH PERFORMERS (ROAS 3.0-5.0)
INSERT INTO campaigns (tenant_id, platform, external_id, account_id, name, status, objective, daily_budget_cents, total_spend_cents, impressions, clicks, conversions, revenue_cents, ctr, roas, start_date, currency, labels)
VALUES
(1, 'meta',   'camp_meta_001',   'act_100001', 'Summer Sale - Lookalike Audiences',    'active', 'conversions', 15000, 1350000, 2800000, 56000, 1680, 5400000, 2.0, 4.0, CURRENT_DATE - 90, 'USD', '["high-performer","retargeting"]'),
(1, 'google', 'camp_goog_001',   'act_200001', 'Brand Search - Exact Match',           'active', 'conversions', 12000, 1080000, 1500000, 105000, 3150, 4320000, 7.0, 4.0, CURRENT_DATE - 90, 'USD', '["brand","search"]'),
(1, 'meta',   'camp_meta_002',   'act_100001', 'Retargeting - Cart Abandoners',        'active', 'conversions', 8000, 720000, 1200000, 36000, 1440, 2880000, 3.0, 4.0, CURRENT_DATE - 90, 'USD', '["retargeting"]'),

-- MEDIUM PERFORMERS (ROAS 1.5-2.8)
(1, 'google', 'camp_goog_002',   'act_200001', 'Shopping - Product Listing Ads',       'active', 'sales',       20000, 1800000, 3500000, 52500, 1050, 3960000, 1.5, 2.2, CURRENT_DATE - 90, 'USD', '["shopping"]'),
(1, 'tiktok', 'camp_tik_001',    'act_300001', 'UGC Creative - Gen Z Audience',        'active', 'conversions', 10000, 900000, 4500000, 67500, 900, 1800000, 1.5, 2.0, CURRENT_DATE - 90, 'USD', '["ugc","genZ"]'),
(1, 'meta',   'camp_meta_003',   'act_100001', 'Video Views - Product Demo',           'active', 'video_views', 6000, 540000, 3200000, 32000, 480, 1080000, 1.0, 2.0, CURRENT_DATE - 90, 'USD', '["video","awareness"]'),
(1, 'snapchat','camp_snap_001',  'act_400001', 'Story Ads - Flash Sale',               'active', 'conversions', 7000, 630000, 2100000, 42000, 630, 1260000, 2.0, 2.0, CURRENT_DATE - 90, 'USD', '["stories"]'),
(1, 'linkedin','camp_li_001',    'act_500001', 'Lead Gen - Decision Makers',           'active', 'leads',       15000, 1350000, 800000, 8000, 400, 2700000, 1.0, 2.0, CURRENT_DATE - 90, 'USD', '["b2b","leads"]'),
(1, 'google', 'camp_goog_003',   'act_200001', 'Display - Remarketing',                'active', 'conversions', 5000, 450000, 5000000, 25000, 375, 900000, 0.5, 2.0, CURRENT_DATE - 90, 'USD', '["display","remarketing"]'),
(1, 'tiktok', 'camp_tik_002',    'act_300001', 'Spark Ads - Influencer Collab',        'active', 'engagement',  8000, 720000, 3800000, 57000, 570, 1440000, 1.5, 2.0, CURRENT_DATE - 90, 'USD', '["influencer"]'),

-- LOW PERFORMERS (ROAS 0.3-1.2)
(1, 'meta',   'camp_meta_004',   'act_100001', 'Cold Audience - Interest Targeting',   'active', 'conversions', 12000, 1080000, 2000000, 20000, 200, 540000, 1.0, 0.5, CURRENT_DATE - 90, 'USD', '["prospecting"]'),
(1, 'snapchat','camp_snap_002',  'act_400001', 'AR Lens - Brand Awareness',            'paused', 'awareness',   9000, 810000, 1800000, 9000, 90, 324000, 0.5, 0.4, CURRENT_DATE - 90, 'USD', '["ar","awareness"]'),
(1, 'google', 'camp_goog_004',   'act_200001', 'Broad Match - New Markets',            'active', 'conversions', 10000, 900000, 1800000, 18000, 180, 720000, 1.0, 0.8, CURRENT_DATE - 90, 'USD', '["expansion"]'),
(1, 'tiktok', 'camp_tik_003',    'act_300001', 'Hashtag Challenge - Brand Launch',     'paused', 'awareness',   15000, 1350000, 6000000, 60000, 300, 675000, 1.0, 0.5, CURRENT_DATE - 90, 'USD', '["hashtag","brand"]');

-- =============================================================================
-- Daily Campaign Metrics (90 days per campaign)
-- =============================================================================
-- Uses generate_series + random variation around campaign baselines

INSERT INTO campaign_metrics (tenant_id, campaign_id, date, impressions, clicks, conversions, spend_cents, revenue_cents)
SELECT
  1 AS tenant_id,
  c.id AS campaign_id,
  d.date,
  -- Daily impressions: base from campaign total/90 with ±30% variation
  GREATEST(100, (c.impressions / 90.0 * (0.7 + random() * 0.6))::INT) AS impressions,
  -- Daily clicks: base from campaign total/90 with ±30% variation
  GREATEST(10, (c.clicks / 90.0 * (0.7 + random() * 0.6))::INT) AS clicks,
  -- Daily conversions: base from campaign total/90 with ±40% variation
  GREATEST(0, (c.conversions / 90.0 * (0.6 + random() * 0.8))::INT) AS conversions,
  -- Daily spend: base from campaign total/90 with ±25% variation
  GREATEST(100, (c.total_spend_cents / 90.0 * (0.75 + random() * 0.5))::INT) AS spend_cents,
  -- Daily revenue: base from campaign total/90 with ±35% variation
  GREATEST(0, (c.revenue_cents / 90.0 * (0.65 + random() * 0.7))::INT) AS revenue_cents
FROM campaigns c
CROSS JOIN generate_series(CURRENT_DATE - 89, CURRENT_DATE, '1 day'::interval) AS d(date)
WHERE c.tenant_id = 1;

-- =============================================================================
-- Fact Platform Daily (analytics warehouse - aggregate by platform+date)
-- =============================================================================
INSERT INTO fact_platform_daily (date, platform, tenant_id, account_id, campaign_id, spend, impressions, clicks, conversions, revenue, ctr, cvr, cpm, cpc, cpa, roas, ingestion_time)
SELECT
  cm.date,
  c.platform::TEXT,
  1,
  c.account_id,
  c.external_id,
  cm.spend_cents / 100.0,
  cm.impressions,
  cm.clicks,
  cm.conversions,
  cm.revenue_cents / 100.0,
  CASE WHEN cm.impressions > 0 THEN ROUND((cm.clicks::NUMERIC / cm.impressions * 100)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.clicks > 0 THEN ROUND((cm.conversions::NUMERIC / cm.clicks * 100)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.impressions > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.impressions * 1000)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.clicks > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.clicks)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.conversions > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.conversions)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.spend_cents > 0 THEN ROUND((cm.revenue_cents::NUMERIC / cm.spend_cents)::NUMERIC, 2) ELSE 0 END,
  NOW()
FROM campaign_metrics cm
JOIN campaigns c ON c.id = cm.campaign_id
WHERE cm.tenant_id = 1;

-- =============================================================================
-- Update campaign aggregate metrics from daily data
-- =============================================================================
UPDATE campaigns SET
  total_spend_cents = sub.total_spend,
  impressions = sub.total_impressions,
  clicks = sub.total_clicks,
  conversions = sub.total_conversions,
  revenue_cents = sub.total_revenue,
  ctr = CASE WHEN sub.total_impressions > 0 THEN ROUND((sub.total_clicks::NUMERIC / sub.total_impressions * 100)::NUMERIC, 2) ELSE 0 END,
  roas = CASE WHEN sub.total_spend > 0 THEN ROUND((sub.total_revenue::NUMERIC / sub.total_spend)::NUMERIC, 2) ELSE 0 END,
  last_synced_at = NOW(),
  updated_at = NOW()
FROM (
  SELECT
    campaign_id,
    SUM(spend_cents) AS total_spend,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(conversions) AS total_conversions,
    SUM(revenue_cents) AS total_revenue
  FROM campaign_metrics
  WHERE tenant_id = 1
  GROUP BY campaign_id
) sub
WHERE campaigns.id = sub.campaign_id AND campaigns.tenant_id = 1;

COMMIT;

-- Summary
SELECT 'Campaigns seeded:' AS info, COUNT(*) AS count FROM campaigns WHERE tenant_id = 1
UNION ALL
SELECT 'Daily metrics rows:', COUNT(*) FROM campaign_metrics WHERE tenant_id = 1
UNION ALL
SELECT 'Fact rows:', COUNT(*) FROM fact_platform_daily WHERE tenant_id = 1;
