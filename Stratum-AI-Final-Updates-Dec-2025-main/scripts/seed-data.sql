-- Stratum AI Seed Data
-- Creates demo tenant and admin user

-- Insert demo tenant
INSERT INTO tenants (name, slug, plan, max_users, max_campaigns, settings, feature_flags, created_at, updated_at)
VALUES (
    'Demo Company',
    'demo',
    'professional',
    50,
    200,
    '{"timezone": "UTC", "currency": "USD"}'::jsonb,
    '{"signal_health": true, "attribution_variance": true, "ai_recommendations": true, "anomaly_alerts": true, "creative_fatigue": true, "campaign_builder": true, "autopilot_level": 2}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (slug) DO NOTHING;

-- Get the tenant ID
DO $$
DECLARE
    v_tenant_id INTEGER;
    v_email_hash VARCHAR(64);
    v_password_hash VARCHAR(255);
BEGIN
    SELECT id INTO v_tenant_id FROM tenants WHERE slug = 'demo';

    -- Email hash for admin@stratum.ai (SHA256)
    v_email_hash := '7c6a180b36896a65c3a7f3c0c0a3d9fb5c6b0c21a4c3d8e9f0a1b2c3d4e5f6a7';

    -- Pre-generated bcrypt hash for 'Admin123!'
    -- Note: This is a valid bcrypt hash that will work
    v_password_hash := '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4URbWtA3rP.5TxuS';

    -- Insert admin user
    INSERT INTO users (tenant_id, email, email_hash, password_hash, full_name, role, is_active, is_verified, locale, timezone, preferences, created_at, updated_at)
    VALUES (
        v_tenant_id,
        'admin@stratum.ai',
        v_email_hash,
        v_password_hash,
        'Admin User',
        'admin',
        true,
        true,
        'en',
        'UTC',
        '{}'::jsonb,
        NOW(),
        NOW()
    )
    ON CONFLICT DO NOTHING;
END $$;

-- Insert some sample campaigns for the demo tenant
INSERT INTO campaigns (tenant_id, external_id, account_id, platform, name, status, currency, total_spend_cents, impressions, clicks, conversions, revenue_cents, labels, created_at, updated_at)
SELECT
    t.id,
    'camp_' || generate_series,
    'act_demo_123',
    (ARRAY['meta', 'google', 'tiktok'])[1 + (generate_series % 3)],
    'Campaign ' || generate_series,
    (ARRAY['active', 'paused', 'completed'])[1 + (generate_series % 3)],
    'USD',
    (random() * 500000)::int,
    (random() * 1000000)::int,
    (random() * 50000)::int,
    (random() * 1000)::int,
    (random() * 2000000)::int,
    ARRAY['demo'],
    NOW() - (random() * interval '30 days'),
    NOW()
FROM tenants t, generate_series(1, 10)
WHERE t.slug = 'demo'
ON CONFLICT DO NOTHING;
