/**
 * =============================================================================
 * Stratum AI Platform - Autopilot Enforcement Load Test
 * =============================================================================
 *
 * Load testing for Autopilot Enforcement API endpoints.
 * Tests settings management, enforcement checks, and soft-block workflows.
 *
 * Usage:
 *   k6 run autopilot-enforcement-load-test.js                    # Default load test
 *   k6 run --env SCENARIO=smoke autopilot-enforcement-load-test.js  # Smoke test
 *   k6 run --env SCENARIO=stress autopilot-enforcement-load-test.js # Stress test
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://api:8000';
const API_V1 = `${BASE_URL}/api/v1`;

// Test credentials
const TEST_EMAIL = __ENV.TEST_EMAIL || 'admin@test-tenant.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';
const TEST_TENANT_ID = __ENV.TEST_TENANT_ID || '1';

// =============================================================================
// Custom Metrics
// =============================================================================

// Counters
const getSettingsSuccess = new Counter('get_settings_success');
const getSettingsFailure = new Counter('get_settings_failure');
const updateSettingsSuccess = new Counter('update_settings_success');
const updateSettingsFailure = new Counter('update_settings_failure');
const checkActionSuccess = new Counter('check_action_success');
const checkActionFailure = new Counter('check_action_failure');
const confirmActionSuccess = new Counter('confirm_action_success');
const confirmActionFailure = new Counter('confirm_action_failure');
const killSwitchSuccess = new Counter('kill_switch_success');
const killSwitchFailure = new Counter('kill_switch_failure');
const auditLogSuccess = new Counter('audit_log_success');
const auditLogFailure = new Counter('audit_log_failure');
const addRuleSuccess = new Counter('add_rule_success');
const addRuleFailure = new Counter('add_rule_failure');
const loginAttempts = new Counter('login_attempts');
const loginSuccess = new Counter('login_success');

// Rates
const errorRate = new Rate('errors');
const authErrorRate = new Rate('auth_errors');
const rateLimitedRate = new Rate('rate_limited');

// Trends
const getSettingsDuration = new Trend('get_settings_duration', true);
const updateSettingsDuration = new Trend('update_settings_duration', true);
const checkActionDuration = new Trend('check_action_duration', true);
const confirmActionDuration = new Trend('confirm_action_duration', true);
const killSwitchDuration = new Trend('kill_switch_duration', true);
const auditLogDuration = new Trend('audit_log_duration', true);
const addRuleDuration = new Trend('add_rule_duration', true);
const loginDuration = new Trend('login_duration', true);

// =============================================================================
// Test Scenarios
// =============================================================================

const scenarios = {
    smoke: {
        executor: 'constant-vus',
        vus: 1,
        duration: '30s',
    },
    load: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '30s', target: 10 },
            { duration: '1m', target: 10 },
            { duration: '30s', target: 25 },
            { duration: '1m', target: 25 },
            { duration: '30s', target: 0 },
        ],
    },
    stress: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '30s', target: 25 },
            { duration: '1m', target: 25 },
            { duration: '30s', target: 50 },
            { duration: '1m', target: 50 },
            { duration: '30s', target: 100 },
            { duration: '1m', target: 100 },
            { duration: '1m', target: 0 },
        ],
    },
};

// Select scenario from environment
const selectedScenario = __ENV.SCENARIO || 'load';

export const options = {
    scenarios: {
        autopilot_enforcement: scenarios[selectedScenario] || scenarios.load,
    },
    thresholds: {
        http_req_duration: ['p(95)<500', 'p(99)<1000'],
        // Allow high http_req_failed since 429s (rate limits) are counted as failures by k6
        // Note: With a single test user (100 req/min limit), high rate limiting is expected
        http_req_failed: ['rate<0.95'],
        // Application errors (not counting rate limits) - must be < 10%
        errors: ['rate<0.10'],
        get_settings_duration: ['p(95)<300'],
        update_settings_duration: ['p(95)<500'],
        check_action_duration: ['p(95)<300'],
        audit_log_duration: ['p(95)<500'],
    },
};

// =============================================================================
// Helper Functions
// =============================================================================

function getHeaders(token = null) {
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

function login() {
    loginAttempts.add(1);
    const startTime = Date.now();

    const loginRes = http.post(
        `${API_V1}/auth/login`,
        JSON.stringify({
            email: TEST_EMAIL,
            password: TEST_PASSWORD,
        }),
        { headers: getHeaders(), tags: { name: 'login' } }
    );

    loginDuration.add(Date.now() - startTime);

    if (loginRes.status === 200) {
        try {
            const body = JSON.parse(loginRes.body);
            const token = body.data?.access_token || body.access_token;
            if (token) {
                loginSuccess.add(1);
                return token;
            }
        } catch (e) {
            // Parse error
        }
    }
    return null;
}

function randomCampaignId() {
    return `camp_${Math.random().toString(36).substring(7)}`;
}

function randomBudget(min = 100, max = 10000) {
    return Math.floor(Math.random() * (max - min) + min);
}

// =============================================================================
// VU-level token cache
// =============================================================================

// Store token per VU to avoid repeated logins
let vuToken = null;
let vuTokenExpiry = 0;
const TOKEN_TTL_MS = 25 * 60 * 1000; // 25 minutes (tokens typically valid for 30 min)

function getToken() {
    const now = Date.now();

    // Return cached token if still valid
    if (vuToken && now < vuTokenExpiry) {
        return vuToken;
    }

    // Login and cache new token
    vuToken = login();
    if (vuToken) {
        vuTokenExpiry = now + TOKEN_TTL_MS;
    }

    return vuToken;
}

// Check if response is rate limited (429)
function isRateLimited(res) {
    return res.status === 429;
}

// Handle rate limit backoff
function handleRateLimit(res) {
    rateLimitedRate.add(1);
    // Get retry-after from header or default to 1 second
    const retryAfter = res.headers['Retry-After']
        ? parseInt(res.headers['Retry-After'], 10)
        : 1;
    sleep(Math.min(retryAfter, 5)); // Cap at 5 seconds
}

// =============================================================================
// Test Functions
// =============================================================================

function testGetSettings(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/settings`,
        { headers: getHeaders(token), tags: { name: 'get_settings' } }
    );

    getSettingsDuration.add(res.timings.duration);

    // Handle rate limiting separately (not counted as error)
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'get_settings: status 200 or 429': (r) => r.status === 200 || r.status === 429,
        'get_settings: has settings': (r) => {
            if (r.status === 429) return true; // Skip for rate limited
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.settings !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        getSettingsSuccess.add(1);
    } else {
        getSettingsFailure.add(1);
        errorRate.add(1);

        // Check if auth error
        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            // Invalidate token cache
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    return res;
}

function testUpdateSettings(token, tenantId) {
    const res = http.put(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/settings`,
        JSON.stringify({
            max_campaign_budget: randomBudget(5000, 20000),
            min_roas_threshold: 1.0 + Math.random(),
            default_mode: ['advisory', 'soft_block'][Math.floor(Math.random() * 2)],
        }),
        { headers: getHeaders(token), tags: { name: 'update_settings' } }
    );

    updateSettingsDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'update_settings: status 200': (r) => r.status === 200,
        'update_settings: success true': (r) => {
            try {
                return JSON.parse(r.body).success === true;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        updateSettingsSuccess.add(1);
    } else {
        updateSettingsFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    return res;
}

function testCheckAction(token, tenantId) {
    const campaignId = randomCampaignId();
    const proposedBudget = randomBudget(500, 15000);

    const res = http.post(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/check`,
        JSON.stringify({
            action_type: 'set_budget',
            entity_type: 'campaign',
            entity_id: campaignId,
            proposed_value: { budget: proposedBudget },
            current_value: { budget: proposedBudget * 0.5 },
            metrics: { roas: 1.5 + Math.random() * 2, spend: proposedBudget * 0.3 },
        }),
        { headers: getHeaders(token), tags: { name: 'check_action' } }
    );

    checkActionDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return null;
    }

    const success = check(res, {
        'check_action: status 200': (r) => r.status === 200,
        'check_action: has allowed field': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.allowed !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        checkActionSuccess.add(1);
    } else {
        checkActionFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    // Return token for potential soft-block confirmation
    try {
        const body = JSON.parse(res.body);
        return body.data?.confirmation_token || null;
    } catch {
        return null;
    }
}

function testConfirmAction(token, tenantId, confirmationToken) {
    if (!confirmationToken) return null;

    const res = http.post(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/confirm`,
        JSON.stringify({
            confirmation_token: confirmationToken,
            override_reason: 'Load test override',
        }),
        { headers: getHeaders(token), tags: { name: 'confirm_action' } }
    );

    confirmActionDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'confirm_action: status 200 or 400': (r) => r.status === 200 || r.status === 400,
    });

    if (success && res.status === 200) {
        confirmActionSuccess.add(1);
    } else {
        confirmActionFailure.add(1);
    }

    return res;
}

function testKillSwitch(token, tenantId) {
    const enabled = Math.random() > 0.5;

    const res = http.post(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/kill-switch`,
        JSON.stringify({
            enabled: enabled,
            reason: 'Load test toggle',
        }),
        { headers: getHeaders(token), tags: { name: 'kill_switch' } }
    );

    killSwitchDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'kill_switch: status 200': (r) => r.status === 200,
        'kill_switch: success true': (r) => {
            try {
                return JSON.parse(r.body).success === true;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        killSwitchSuccess.add(1);
    } else {
        killSwitchFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    return res;
}

function testAuditLog(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/audit-log?days=7&limit=50`,
        { headers: getHeaders(token), tags: { name: 'audit_log' } }
    );

    auditLogDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'audit_log: status 200': (r) => r.status === 200,
        'audit_log: has logs array': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && Array.isArray(body.data?.logs);
            } catch {
                return false;
            }
        },
    });

    if (success) {
        auditLogSuccess.add(1);
    } else {
        auditLogFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    return res;
}

function testAddRule(token, tenantId) {
    const ruleId = `rule_${__VU}_${__ITER}_${Math.random().toString(36).substring(7)}`;

    const res = http.post(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/rules`,
        JSON.stringify({
            rule_id: ruleId,
            rule_type: 'budget_exceeded',
            threshold_value: randomBudget(1000, 5000),
            enforcement_mode: 'soft_block',
            enabled: true,
            description: `Load test rule ${ruleId}`,
        }),
        { headers: getHeaders(token), tags: { name: 'add_rule' } }
    );

    addRuleDuration.add(res.timings.duration);

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return null; // Can't return ruleId if rate limited
    }

    const success = check(res, {
        'add_rule: status 200': (r) => r.status === 200,
        'add_rule: success true': (r) => {
            try {
                return JSON.parse(r.body).success === true;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        addRuleSuccess.add(1);
    } else {
        addRuleFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            vuToken = null;
            vuTokenExpiry = 0;
        }
    }

    return ruleId;
}

function testDeleteRule(token, tenantId, ruleId) {
    if (!ruleId) return null;

    const res = http.del(
        `${API_V1}/tenant/${tenantId}/autopilot/enforcement/rules/${ruleId}`,
        null,
        { headers: getHeaders(token), tags: { name: 'delete_rule' } }
    );

    // Handle rate limiting separately
    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'delete_rule: status 200 or 404': (r) => r.status === 200 || r.status === 404,
    });

    return res;
}

// =============================================================================
// Main Test Function
// =============================================================================

export default function () {
    // Get cached token (logs in only once per VU, caches for 25 min)
    const token = getToken();

    if (!token) {
        errorRate.add(1);
        authErrorRate.add(1);
        console.error(`VU ${__VU}: Failed to authenticate`);
        sleep(2); // Wait before retry
        return;
    }

    const tenantId = TEST_TENANT_ID;

    // Run test groups
    group('Settings Operations', function () {
        testGetSettings(token, tenantId);
        sleep(0.3);

        testUpdateSettings(token, tenantId);
        sleep(0.3);
    });

    group('Enforcement Checks', function () {
        // Run multiple check actions
        for (let i = 0; i < 3; i++) {
            const confirmToken = testCheckAction(token, tenantId);
            sleep(0.2);

            // Occasionally confirm soft-blocked actions
            if (confirmToken && Math.random() > 0.7) {
                testConfirmAction(token, tenantId, confirmToken);
                sleep(0.1);
            }
        }
    });

    group('Kill Switch', function () {
        // Only test kill switch occasionally to avoid disrupting other tests
        if (Math.random() > 0.9) {
            testKillSwitch(token, tenantId);
            sleep(0.3);

            // Re-enable enforcement
            http.post(
                `${API_V1}/tenant/${tenantId}/autopilot/enforcement/kill-switch`,
                JSON.stringify({ enabled: true, reason: 'Re-enable after test' }),
                { headers: getHeaders(token), tags: { name: 'kill_switch_reenable' } }
            );
            sleep(0.2);
        }
    });

    group('Audit Log', function () {
        testAuditLog(token, tenantId);
        sleep(0.3);
    });

    group('Custom Rules', function () {
        // Only test rules occasionally to avoid creating too many
        if (Math.random() > 0.8) {
            const ruleId = testAddRule(token, tenantId);
            sleep(0.2);

            // Clean up rule
            testDeleteRule(token, tenantId, ruleId);
            sleep(0.2);
        }
    });

    // Think time between iterations (reduced for higher throughput)
    sleep(0.5 + Math.random());
}

// =============================================================================
// Setup and Teardown
// =============================================================================

export function setup() {
    console.log(`Starting Autopilot Enforcement Load Test`);
    console.log(`Scenario: ${selectedScenario}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Tenant ID: ${TEST_TENANT_ID}`);

    // Verify API is reachable
    const healthRes = http.get(`${BASE_URL}/health`);
    if (healthRes.status !== 200) {
        throw new Error(`API not healthy: ${healthRes.status}`);
    }

    // Verify authentication works
    const token = login();
    if (!token) {
        throw new Error('Failed to authenticate during setup');
    }

    console.log('Setup complete - authentication verified');
    return { setupToken: token };
}

export function teardown(data) {
    console.log('Autopilot Enforcement Load Test Complete');
    console.log(`Setup token was: ${data.setupToken ? 'valid' : 'invalid'}`);
}
