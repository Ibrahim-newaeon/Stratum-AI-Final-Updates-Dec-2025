// =============================================================================
// Stratum AI - API Service Layer
// =============================================================================

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Auth token (in production, this would come from a secure storage)
let authToken = localStorage.getItem('stratum-auth-token') || 'demo-token';
let tenantId = localStorage.getItem('stratum-tenant-id') || 1;

// =============================================================================
// HTTP Client
// =============================================================================
async function request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        'X-Tenant-ID': tenantId,
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

// =============================================================================
// API Methods
// =============================================================================
const API = {
    // -------------------------------------------------------------------------
    // Dashboard KPIs
    // -------------------------------------------------------------------------
    async getKPIs(period = '30d') {
        try {
            return await request(`/analytics/kpis?period=${period}`);
        } catch {
            // Return mock data for demo
            return {
                success: true,
                data: [
                    { metric: 'revenue', value: 2400000, change_percent: 23 },
                    { metric: 'roas', value: 4.2, change_percent: 8 },
                    { metric: 'conversions', value: 8547, change_percent: 12 },
                    { metric: 'spend', value: 571428, change_percent: 15 }
                ]
            };
        }
    },

    // -------------------------------------------------------------------------
    // Trust Layer / EMQ
    // -------------------------------------------------------------------------
    async getEMQScore(date = null) {
        try {
            const params = date ? `?date=${date}` : '';
            return await request(`/tenants/${tenantId}/emq/score${params}`);
        } catch {
            return {
                success: true,
                data: {
                    score: 87,
                    previousScore: 84,
                    confidenceBand: 'reliable',
                    drivers: [
                        { name: 'Event Match Rate', value: 92, weight: 30, status: 'good', trend: 'up' },
                        { name: 'Pixel Coverage', value: 88, weight: 25, status: 'good', trend: 'stable' },
                        { name: 'Conversion Latency', value: 74, weight: 20, status: 'warning', trend: 'up' },
                        { name: 'Attribution Accuracy', value: 85, weight: 15, status: 'good', trend: 'up' },
                        { name: 'Data Freshness', value: 95, weight: 10, status: 'good', trend: 'stable' }
                    ],
                    lastUpdated: new Date().toISOString()
                }
            };
        }
    },

    async getEMQPlaybook() {
        try {
            return await request(`/tenants/${tenantId}/emq/playbook`);
        } catch {
            return {
                success: true,
                data: [
                    {
                        id: '1',
                        title: 'Enable Enhanced Conversions',
                        description: 'Implement Google Enhanced Conversions to improve match rates by 15-25%',
                        priority: 'critical',
                        estimatedImpact: 8.5,
                        estimatedTime: '2-4 hours',
                        platform: 'Google Ads',
                        status: 'pending'
                    },
                    {
                        id: '2',
                        title: 'Fix Meta CAPI Event Deduplication',
                        description: 'Configure event_id parameter to prevent duplicate conversions',
                        priority: 'high',
                        estimatedImpact: 5.2,
                        estimatedTime: '1-2 hours',
                        platform: 'Meta',
                        status: 'pending'
                    }
                ]
            };
        }
    },

    async getEMQVolatility(weeks = 8) {
        try {
            return await request(`/tenants/${tenantId}/emq/volatility?weeks=${weeks}`);
        } catch {
            return {
                success: true,
                data: {
                    svi: 12.5,
                    trend: 'decreasing',
                    weeklyData: Array.from({ length: weeks }, (_, i) => ({
                        week: `W${i + 1}`,
                        score: 80 + Math.random() * 15,
                        volatility: 10 + Math.random() * 10
                    }))
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Platform Status
    // -------------------------------------------------------------------------
    async getPlatformStatus() {
        try {
            return await request('/connectors/status');
        } catch {
            return {
                success: true,
                data: [
                    { id: 'meta', name: 'Meta Ads', icon: 'META', status: 'connected', lastSync: 'Last sync: 2 min ago' },
                    { id: 'google', name: 'Google Ads', icon: 'G', status: 'connected', lastSync: 'Last sync: 5 min ago' },
                    { id: 'tiktok', name: 'TikTok Ads', icon: 'TT', status: 'connected', lastSync: 'Last sync: 8 min ago' },
                    { id: 'snap', name: 'Snapchat', icon: 'SC', status: 'partial', lastSync: 'Missing: Conversion API' },
                    { id: 'linkedin', name: 'LinkedIn', icon: 'in', status: 'connected', lastSync: 'Last sync: 15 min ago' }
                ]
            };
        }
    },

    async getConnectorDetails(platform) {
        try {
            return await request(`/connectors/${platform}`);
        } catch {
            return {
                success: true,
                data: {
                    id: platform,
                    name: platform.charAt(0).toUpperCase() + platform.slice(1),
                    status: 'connected',
                    accountId: 'act_123456789',
                    lastSync: new Date().toISOString(),
                    syncInterval: 15,
                    metrics: {
                        campaigns: 24,
                        adsets: 86,
                        ads: 342,
                        spend_mtd: 125000
                    }
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Predictions
    // -------------------------------------------------------------------------
    async getPredictions(refresh = false) {
        try {
            return await request(`/predictions/live?refresh=${refresh}`);
        } catch {
            return {
                success: true,
                data: {
                    prediction: {
                        portfolio: {
                            total_spend: 571428,
                            total_revenue: 2400000,
                            portfolio_roas: 4.2,
                            campaign_count: 24,
                            avg_health_score: 72,
                            potential_uplift: { revenue: 360000, roas: 0.6 }
                        },
                        campaigns: [
                            { campaign_id: 1, campaign_name: 'Summer Sale Meta', health_score: 85, status: 'healthy', current_roas: 5.2 },
                            { campaign_id: 2, campaign_name: 'Brand Awareness', health_score: 62, status: 'needs_attention', current_roas: 2.1 },
                            { campaign_id: 3, campaign_name: 'Retargeting', health_score: 91, status: 'healthy', current_roas: 8.4 }
                        ]
                    },
                    alerts: [
                        { campaign_id: 2, campaign_name: 'Brand Awareness', type: 'low_roas', severity: 'high', message: 'ROAS below target' }
                    ],
                    cached: false,
                    generated_at: new Date().toISOString()
                }
            };
        }
    },

    async getBudgetOptimization() {
        try {
            return await request('/predictions/optimize/budget');
        } catch {
            return {
                success: true,
                data: {
                    budget_reallocation: [
                        { campaign_id: 1, campaign_name: 'Summer Sale Meta', current_budget: 5000, suggested_budget: 6500, change: 30 },
                        { campaign_id: 2, campaign_name: 'Brand Awareness', current_budget: 3000, suggested_budget: 2000, change: -33 },
                        { campaign_id: 3, campaign_name: 'Retargeting', current_budget: 2000, suggested_budget: 2500, change: 25 }
                    ],
                    potential_uplift: { revenue: 45000, roas: 0.4 }
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Alerts
    // -------------------------------------------------------------------------
    async getAlerts(severity = null, limit = 50) {
        try {
            const params = new URLSearchParams({ limit });
            if (severity) params.append('severity', severity);
            return await request(`/predictions/alerts?${params}`);
        } catch {
            return {
                success: true,
                data: {
                    alerts: [
                        { severity: 'critical', title: 'ROAS Drop Detected', description: 'Campaign "Summer Sale" down 32%', time: '2m ago' },
                        { severity: 'warning', title: 'Budget Pacing Alert', description: 'Meta overspending by 15%', time: '15m ago' },
                        { severity: 'info', title: 'EMQ Score Improved', description: 'Google Ads EMQ now at 92', time: '1h ago' }
                    ]
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Attribution
    // -------------------------------------------------------------------------
    async getAttributionSummary(startDate, endDate, model = 'last_touch', groupBy = 'platform') {
        try {
            return await request(`/attribution/summary?start_date=${startDate}&end_date=${endDate}&model=${model}&group_by=${groupBy}`);
        } catch {
            return {
                success: true,
                data: [
                    { key: 'meta', name: 'Meta', attributed_revenue: 890000, attributed_conversions: 3420, deals_count: 156 },
                    { key: 'google', name: 'Google', attributed_revenue: 720000, attributed_conversions: 2810, deals_count: 128 },
                    { key: 'tiktok', name: 'TikTok', attributed_revenue: 450000, attributed_conversions: 1580, deals_count: 72 },
                    { key: 'snapchat', name: 'Snapchat', attributed_revenue: 210000, attributed_conversions: 620, deals_count: 34 }
                ]
            };
        }
    },

    async getConversionPaths(startDate, endDate, limit = 20) {
        try {
            return await request(`/attribution/journeys/conversion-paths?start_date=${startDate}&end_date=${endDate}&limit=${limit}`);
        } catch {
            return {
                success: true,
                data: [
                    { path: 'Meta → Google → Meta', conversions: 842, total_revenue: 425000, avg_revenue: 505 },
                    { path: 'Google → Meta', conversions: 621, total_revenue: 312000, avg_revenue: 502 },
                    { path: 'TikTok → Meta → Google', conversions: 384, total_revenue: 198000, avg_revenue: 516 }
                ]
            };
        }
    },

    async getJourneyMetrics(startDate, endDate) {
        try {
            return await request(`/attribution/journeys/metrics?start_date=${startDate}&end_date=${endDate}`);
        } catch {
            return {
                success: true,
                data: {
                    avg_touches_per_conversion: 3.2,
                    avg_time_to_conversion_hours: 72,
                    unique_paths: 847,
                    multi_touch_conversions_pct: 68
                }
            };
        }
    },

    async getAttributionModels() {
        try {
            return await request('/attribution/models');
        } catch {
            return {
                success: true,
                models: [
                    { value: 'first_touch', name: 'First Touch', description: '100% credit to first interaction' },
                    { value: 'last_touch', name: 'Last Touch', description: '100% credit to last interaction' },
                    { value: 'linear', name: 'Linear', description: 'Equal credit across all touchpoints' },
                    { value: 'position_based', name: 'Position-Based', description: '40/20/40 distribution' },
                    { value: 'time_decay', name: 'Time Decay', description: 'More credit to recent interactions' },
                    { value: 'data_driven', name: 'Data-Driven', description: 'ML-based attribution' }
                ]
            };
        }
    },

    // -------------------------------------------------------------------------
    // Profit
    // -------------------------------------------------------------------------
    async getProfitSummary(period = '30d') {
        try {
            const endDate = new Date().toISOString().split('T')[0];
            const days = period === '7d' ? 7 : period === '90d' ? 90 : 30;
            const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            return await request(`/profit/roas?start_date=${startDate}&end_date=${endDate}`);
        } catch {
            return {
                success: true,
                data: {
                    netProfit: 486972,
                    margin: 31.2,
                    revenue: 2400000,
                    cogs: 1008000,
                    cogsPercent: 42,
                    adSpend: 571428,
                    overhead: 333600,
                    overheadPercent: 14,
                    grossProfitRoas: 2.43,
                    netProfitRoas: 0.85,
                    breakevenRoas: 1.72
                }
            };
        }
    },

    async getProfitByProduct(startDate, endDate, limit = 20) {
        try {
            return await request(`/profit/by-product?start_date=${startDate}&end_date=${endDate}&limit=${limit}`);
        } catch {
            return {
                success: true,
                data: {
                    products: [
                        { sku: 'PRD-001', name: 'Premium Widget', revenue: 450000, cogs: 180000, gross_profit: 270000, margin: 60 },
                        { sku: 'PRD-002', name: 'Standard Widget', revenue: 320000, cogs: 160000, gross_profit: 160000, margin: 50 },
                        { sku: 'PRD-003', name: 'Basic Widget', revenue: 280000, cogs: 168000, gross_profit: 112000, margin: 40 }
                    ]
                }
            };
        }
    },

    async getProfitByCampaign(startDate, endDate) {
        try {
            return await request(`/profit/by-campaign?start_date=${startDate}&end_date=${endDate}`);
        } catch {
            return {
                success: true,
                data: {
                    campaigns: [
                        { id: 1, name: 'Summer Sale Meta', revenue: 890000, spend: 171000, profit_roas: 3.2, net_profit: 286000 },
                        { id: 2, name: 'Google Search Brand', revenue: 520000, spend: 85000, profit_roas: 4.1, net_profit: 218000 },
                        { id: 3, name: 'Retargeting All', revenue: 340000, spend: 45000, profit_roas: 5.5, net_profit: 186000 }
                    ]
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Campaigns
    // -------------------------------------------------------------------------
    async getCampaigns(page = 1, pageSize = 20, filters = {}) {
        try {
            const params = new URLSearchParams({ page, page_size: pageSize });
            Object.entries(filters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });
            return await request(`/campaigns?${params}`);
        } catch {
            return {
                success: true,
                data: {
                    items: [
                        { id: 1, name: 'Summer Sale Meta', platform: 'meta', status: 'active', total_spend_cents: 17100000, impressions: 2450000, clicks: 86000, conversions: 3420, roas: 5.2 },
                        { id: 2, name: 'Google Search Brand', platform: 'google', status: 'active', total_spend_cents: 8500000, impressions: 1820000, clicks: 54000, conversions: 2810, roas: 6.1 },
                        { id: 3, name: 'TikTok Awareness', platform: 'tiktok', status: 'paused', total_spend_cents: 4500000, impressions: 5400000, clicks: 162000, conversions: 1580, roas: 3.5 }
                    ],
                    total: 24,
                    page: 1,
                    page_size: 20,
                    total_pages: 2
                }
            };
        }
    },

    async getCampaign(campaignId) {
        try {
            return await request(`/campaigns/${campaignId}`);
        } catch {
            return {
                success: true,
                data: {
                    id: campaignId,
                    name: 'Summer Sale Meta',
                    platform: 'meta',
                    status: 'active',
                    objective: 'conversions',
                    daily_budget_cents: 500000,
                    total_spend_cents: 17100000,
                    impressions: 2450000,
                    clicks: 86000,
                    conversions: 3420,
                    revenue_cents: 89000000,
                    roas: 5.2,
                    ctr: 3.51,
                    cpc_cents: 199,
                    cpa_cents: 5000,
                    start_date: '2024-01-01',
                    labels: ['sale', 'q1']
                }
            };
        }
    },

    async getCampaignMetrics(campaignId, startDate, endDate) {
        try {
            return await request(`/campaigns/${campaignId}/metrics?start_date=${startDate}&end_date=${endDate}`);
        } catch {
            return {
                success: true,
                data: {
                    campaign_id: campaignId,
                    date_range: { start: startDate, end: endDate },
                    metrics: Array.from({ length: 30 }, (_, i) => ({
                        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        impressions: 80000 + Math.random() * 20000,
                        clicks: 2500 + Math.random() * 1000,
                        conversions: 100 + Math.random() * 50,
                        spend_cents: 500000 + Math.random() * 100000,
                        revenue_cents: 2800000 + Math.random() * 500000
                    })),
                    aggregated: {
                        impressions: 2450000,
                        clicks: 86000,
                        conversions: 3420,
                        spend_cents: 17100000,
                        revenue_cents: 89000000,
                        ctr: 3.51,
                        roas: 5.2
                    }
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // WhatsApp
    // -------------------------------------------------------------------------
    async getWhatsAppStats() {
        try {
            return await request('/whatsapp/stats');
        } catch {
            return {
                success: true,
                data: {
                    contacts: 247,
                    sent: 1842,
                    deliveredRate: 94,
                    readRate: 78,
                    templates: 12,
                    activeConversations: 18,
                    recentMessages: [
                        { status: 'delivered', text: 'Daily digest sent to Marketing Team', time: '9:00 AM' },
                        { status: 'delivered', text: 'ROAS alert sent to John Doe', time: '8:45 AM' },
                        { status: 'sent', text: 'Budget alert queued', time: '8:30 AM' }
                    ]
                }
            };
        }
    },

    async getWhatsAppContacts(page = 1, pageSize = 20) {
        try {
            return await request(`/whatsapp/contacts?page=${page}&page_size=${pageSize}`);
        } catch {
            return {
                success: true,
                data: {
                    items: [
                        { id: 1, phone_number: '+1234567890', display_name: 'John Doe', opt_in_status: 'opted_in', message_count: 42 },
                        { id: 2, phone_number: '+0987654321', display_name: 'Jane Smith', opt_in_status: 'opted_in', message_count: 28 },
                        { id: 3, phone_number: '+1122334455', display_name: 'Marketing Team', opt_in_status: 'opted_in', message_count: 156 }
                    ],
                    total: 247,
                    page: 1,
                    page_size: 20
                }
            };
        }
    },

    async getWhatsAppTemplates(page = 1, pageSize = 20) {
        try {
            return await request(`/whatsapp/templates?page=${page}&page_size=${pageSize}`);
        } catch {
            return {
                success: true,
                data: {
                    items: [
                        { id: 1, name: 'daily_digest', category: 'utility', status: 'approved', usage_count: 842 },
                        { id: 2, name: 'roas_alert', category: 'utility', status: 'approved', usage_count: 326 },
                        { id: 3, name: 'budget_warning', category: 'utility', status: 'approved', usage_count: 158 }
                    ],
                    total: 12,
                    page: 1
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Users & RBAC
    // -------------------------------------------------------------------------
    async getUsers(page = 1, pageSize = 20) {
        try {
            return await request(`/users?page=${page}&page_size=${pageSize}`);
        } catch {
            return {
                success: true,
                data: {
                    items: [
                        { id: 1, email: 'admin@stratum.ai', name: 'Super Admin', role: 'admin', status: 'active', last_login: new Date().toISOString() },
                        { id: 2, email: 'john@company.com', name: 'John Doe', role: 'manager', status: 'active', last_login: new Date().toISOString() },
                        { id: 3, email: 'jane@company.com', name: 'Jane Smith', role: 'analyst', status: 'active', last_login: new Date().toISOString() }
                    ],
                    total: 8,
                    page: 1
                }
            };
        }
    },

    async getRoles() {
        try {
            return await request('/roles');
        } catch {
            return {
                success: true,
                data: [
                    { id: 1, name: 'admin', display_name: 'Administrator', permissions: ['*'] },
                    { id: 2, name: 'manager', display_name: 'Manager', permissions: ['campaigns:*', 'analytics:read', 'reports:*'] },
                    { id: 3, name: 'analyst', display_name: 'Analyst', permissions: ['analytics:read', 'reports:read'] },
                    { id: 4, name: 'viewer', display_name: 'Viewer', permissions: ['analytics:read'] }
                ]
            };
        }
    },

    // -------------------------------------------------------------------------
    // Audit Log
    // -------------------------------------------------------------------------
    async getAuditLogs(page = 1, pageSize = 50, filters = {}) {
        try {
            const params = new URLSearchParams({ page, page_size: pageSize });
            Object.entries(filters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });
            return await request(`/audit-log?${params}`);
        } catch {
            return {
                success: true,
                data: {
                    items: [
                        { id: 1, action: 'campaign.update', user: 'John Doe', resource: 'Campaign #42', timestamp: new Date().toISOString(), details: { field: 'budget', old_value: 5000, new_value: 6500 } },
                        { id: 2, action: 'user.login', user: 'Jane Smith', resource: null, timestamp: new Date(Date.now() - 3600000).toISOString(), details: { ip: '192.168.1.1' } },
                        { id: 3, action: 'connector.sync', user: 'System', resource: 'Meta Ads', timestamp: new Date(Date.now() - 7200000).toISOString(), details: { campaigns_synced: 24 } }
                    ],
                    total: 1250,
                    page: 1
                }
            };
        }
    },

    // -------------------------------------------------------------------------
    // Analytics
    // -------------------------------------------------------------------------
    async getAnalyticsOverview(startDate, endDate) {
        try {
            return await request(`/analytics/overview?start_date=${startDate}&end_date=${endDate}`);
        } catch {
            return {
                success: true,
                data: {
                    revenue: { value: 2400000, change: 23 },
                    spend: { value: 571428, change: 15 },
                    roas: { value: 4.2, change: 8 },
                    conversions: { value: 8547, change: 12 },
                    impressions: { value: 15200000, change: 18 },
                    clicks: { value: 486000, change: 14 },
                    ctr: { value: 3.2, change: -2 },
                    cpa: { value: 66.85, change: -8 }
                }
            };
        }
    },

    async getAnalyticsTrend(metric, startDate, endDate, granularity = 'daily') {
        try {
            return await request(`/analytics/trend?metric=${metric}&start_date=${startDate}&end_date=${endDate}&granularity=${granularity}`);
        } catch {
            const days = Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
            return {
                success: true,
                data: Array.from({ length: days }, (_, i) => ({
                    date: new Date(new Date(startDate).getTime() + i * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                    value: Math.random() * 100000 + 50000
                }))
            };
        }
    },

    // -------------------------------------------------------------------------
    // Settings
    // -------------------------------------------------------------------------
    async getSettings() {
        try {
            return await request('/settings');
        } catch {
            return {
                success: true,
                data: {
                    company: { name: 'Demo Company', industry: 'E-commerce', timezone: 'America/New_York' },
                    notifications: { email: true, whatsapp: true, slack: false },
                    alerts: { roas_threshold: 2.0, budget_alert_pct: 80, emq_threshold: 70 },
                    reporting: { default_period: '30d', currency: 'USD' }
                }
            };
        }
    },

    async updateSettings(settings) {
        try {
            return await request('/settings', {
                method: 'PATCH',
                body: JSON.stringify(settings)
            });
        } catch {
            return { success: true, message: 'Settings updated' };
        }
    }
};

// Export for use in other files
if (typeof window !== 'undefined') {
    window.API = API;
}
