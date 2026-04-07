/**
 * Stratum AI - Trust Layer Load Test
 *
 * Tests the Trust Layer and EMQ (Event Match Quality) endpoints under load.
 *
 * Endpoints tested:
 * - GET /tenant/{id}/signal-health
 * - GET /tenant/{id}/signal-health/history
 * - GET /tenant/{id}/attribution-variance
 * - GET /tenant/{id}/trust-status
 * - GET /tenants/{id}/emq/score
 * - GET /tenants/{id}/emq/confidence
 * - GET /tenants/{id}/emq/playbook
 * - GET /tenants/{id}/emq/volatility
 * - GET /tenants/{id}/emq/autopilot-state
 *
 * Usage:
 *   docker run --rm -i --network stratum-ai-final-updates-dec-2025-main_stratum_network \
 *     -e SCENARIO=smoke grafana/k6 run - < tests/load/trust-layer-load-test.js
 *
 * Scenarios:
 *   SCENARIO=smoke   - 1 VU for 30s (baseline)
 *   SCENARIO=load    - Ramp to 25 VUs over 3m30s
 *   SCENARIO=stress  - Ramp to 100 VUs over 5m30s
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://api:8000';
const API_V1 = `${BASE_URL}/api/v1`;

// Test credentials - supports multiple users
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';
const TEST_TENANT_ID = __ENV.TEST_TENANT_ID || '1';
const NUM_TEST_USERS = parseInt(__ENV.NUM_TEST_USERS || '25');

function getTestEmail(vuIndex) {
    if (vuIndex === 0) {
        return 'admin@test-tenant.com';
    }
    return `loadtest${vuIndex}@test-tenant.com`;
}

// =============================================================================
// Custom Metrics
// =============================================================================

// Counters
const signalHealthSuccess = new Counter('signal_health_success');
const signalHealthFailure = new Counter('signal_health_failure');
const trustStatusSuccess = new Counter('trust_status_success');
const trustStatusFailure = new Counter('trust_status_failure');
const emqScoreSuccess = new Counter('emq_score_success');
const emqScoreFailure = new Counter('emq_score_failure');
const emqConfidenceSuccess = new Counter('emq_confidence_success');
const emqConfidenceFailure = new Counter('emq_confidence_failure');
const loginAttempts = new Counter('login_attempts');
const loginSuccess = new Counter('login_success');

// Rates
const errorRate = new Rate('errors');
const authErrorRate = new Rate('auth_errors');
const rateLimitedRate = new Rate('rate_limited');

// Trends
const signalHealthDuration = new Trend('signal_health_duration', true);
const trustStatusDuration = new Trend('trust_status_duration', true);
const emqScoreDuration = new Trend('emq_score_duration', true);
const emqConfidenceDuration = new Trend('emq_confidence_duration', true);
const emqPlaybookDuration = new Trend('emq_playbook_duration', true);
const emqVolatilityDuration = new Trend('emq_volatility_duration', true);
const emqAutopilotDuration = new Trend('emq_autopilot_duration', true);
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
            { duration: '30s', target: 5 },
            { duration: '1m', target: 15 },
            { duration: '1m', target: 25 },
            { duration: '30s', target: 25 },
            { duration: '30s', target: 0 },
        ],
        gracefulRampDown: '30s',
    },
    stress: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '30s', target: 10 },
            { duration: '1m', target: 30 },
            { duration: '1m', target: 60 },
            { duration: '1m', target: 100 },
            { duration: '1m', target: 100 },
            { duration: '30s', target: 50 },
            { duration: '30s', target: 0 },
        ],
        gracefulRampDown: '30s',
    },
};

const selectedScenario = __ENV.SCENARIO || 'load';

export const options = {
    scenarios: {
        trust_layer: scenarios[selectedScenario] || scenarios.load,
    },
    thresholds: {
        http_req_duration: ['p(95)<500', 'p(99)<1000'],
        http_req_failed: ['rate<0.95'],
        errors: ['rate<0.10'],
        signal_health_duration: ['p(95)<400'],
        trust_status_duration: ['p(95)<500'],
        emq_score_duration: ['p(95)<400'],
        emq_confidence_duration: ['p(95)<400'],
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

function login(email) {
    loginAttempts.add(1);
    const startTime = Date.now();

    const loginRes = http.post(
        `${API_V1}/auth/login`,
        JSON.stringify({
            email: email,
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

// =============================================================================
// VU-level token cache
// =============================================================================

let vuToken = null;
let vuTokenExpiry = 0;
let vuEmail = null;
const TOKEN_TTL_MS = 25 * 60 * 1000;

function getToken() {
    const now = Date.now();
    const userIndex = (__VU - 1) % NUM_TEST_USERS;
    const email = getTestEmail(userIndex);

    if (vuToken && now < vuTokenExpiry && vuEmail === email) {
        return vuToken;
    }

    vuEmail = email;
    vuToken = login(email);
    if (vuToken) {
        vuTokenExpiry = now + TOKEN_TTL_MS;
    }

    return vuToken;
}

function isRateLimited(res) {
    return res.status === 429;
}

function handleRateLimit(res) {
    rateLimitedRate.add(1);
    const retryAfter = res.headers['Retry-After']
        ? parseInt(res.headers['Retry-After'], 10)
        : 1;
    sleep(Math.min(retryAfter, 5));
}

// =============================================================================
// Test Functions - Trust Layer
// =============================================================================

function testSignalHealth(token, tenantId) {
    const res = http.get(
        `${API_V1}/trust/tenant/${tenantId}/signal-health`,
        { headers: getHeaders(token), tags: { name: 'signal_health' } }
    );

    signalHealthDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'signal_health: status 200 or 403': (r) => r.status === 200 || r.status === 403,
        'signal_health: has response': (r) => {
            if (r.status === 403) return true; // Feature may be disabled
            try {
                const body = JSON.parse(r.body);
                return body.success === true;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        signalHealthSuccess.add(1);
    } else {
        signalHealthFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            if (res.status === 401) {
                vuToken = null;
                vuTokenExpiry = 0;
            }
        }
    }

    return res;
}

function testSignalHealthHistory(token, tenantId) {
    const res = http.get(
        `${API_V1}/trust/tenant/${tenantId}/signal-health/history?days=7`,
        { headers: getHeaders(token), tags: { name: 'signal_health_history' } }
    );

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'signal_health_history: status 200 or 403': (r) => r.status === 200 || r.status === 403,
    });

    return res;
}

function testAttributionVariance(token, tenantId) {
    const res = http.get(
        `${API_V1}/trust/tenant/${tenantId}/attribution-variance`,
        { headers: getHeaders(token), tags: { name: 'attribution_variance' } }
    );

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'attribution_variance: status 200 or 403': (r) => r.status === 200 || r.status === 403,
    });

    return res;
}

function testTrustStatus(token, tenantId) {
    const res = http.get(
        `${API_V1}/trust/tenant/${tenantId}/trust-status`,
        { headers: getHeaders(token), tags: { name: 'trust_status' } }
    );

    trustStatusDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'trust_status: status 200': (r) => r.status === 200,
        'trust_status: has overall_status': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.overall_status !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        trustStatusSuccess.add(1);
    } else {
        trustStatusFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            if (res.status === 401) {
                vuToken = null;
                vuTokenExpiry = 0;
            }
        }
    }

    return res;
}

// =============================================================================
// Test Functions - EMQ
// =============================================================================

function testEmqScore(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenants/${tenantId}/emq/score`,
        { headers: getHeaders(token), tags: { name: 'emq_score' } }
    );

    emqScoreDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'emq_score: status 200': (r) => r.status === 200,
        'emq_score: has score': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.score !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        emqScoreSuccess.add(1);
    } else {
        emqScoreFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            if (res.status === 401) {
                vuToken = null;
                vuTokenExpiry = 0;
            }
        }
    }

    return res;
}

function testEmqConfidence(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenants/${tenantId}/emq/confidence`,
        { headers: getHeaders(token), tags: { name: 'emq_confidence' } }
    );

    emqConfidenceDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    const success = check(res, {
        'emq_confidence: status 200': (r) => r.status === 200,
        'emq_confidence: has band': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.band !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (success) {
        emqConfidenceSuccess.add(1);
    } else {
        emqConfidenceFailure.add(1);
        errorRate.add(1);

        if (res.status === 401 || res.status === 403) {
            authErrorRate.add(1);
            if (res.status === 401) {
                vuToken = null;
                vuTokenExpiry = 0;
            }
        }
    }

    return res;
}

function testEmqPlaybook(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenants/${tenantId}/emq/playbook`,
        { headers: getHeaders(token), tags: { name: 'emq_playbook' } }
    );

    emqPlaybookDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'emq_playbook: status 200': (r) => r.status === 200,
        'emq_playbook: is array': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && Array.isArray(body.data);
            } catch {
                return false;
            }
        },
    });

    return res;
}

function testEmqVolatility(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenants/${tenantId}/emq/volatility?weeks=8`,
        { headers: getHeaders(token), tags: { name: 'emq_volatility' } }
    );

    emqVolatilityDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'emq_volatility: status 200': (r) => r.status === 200,
        'emq_volatility: has svi': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.svi !== undefined;
            } catch {
                return false;
            }
        },
    });

    return res;
}

function testEmqAutopilotState(token, tenantId) {
    const res = http.get(
        `${API_V1}/tenants/${tenantId}/emq/autopilot-state`,
        { headers: getHeaders(token), tags: { name: 'emq_autopilot_state' } }
    );

    emqAutopilotDuration.add(res.timings.duration);

    if (isRateLimited(res)) {
        handleRateLimit(res);
        return res;
    }

    check(res, {
        'emq_autopilot_state: status 200': (r) => r.status === 200,
        'emq_autopilot_state: has mode': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.success === true && body.data?.mode !== undefined;
            } catch {
                return false;
            }
        },
    });

    return res;
}

// =============================================================================
// Main Test Function
// =============================================================================

export default function () {
    const token = getToken();

    if (!token) {
        errorRate.add(1);
        authErrorRate.add(1);
        console.error(`VU ${__VU}: Failed to authenticate`);
        sleep(2);
        return;
    }

    const tenantId = TEST_TENANT_ID;

    // Trust Layer Endpoints
    group('Trust Layer', function () {
        testSignalHealth(token, tenantId);
        sleep(0.2);

        testSignalHealthHistory(token, tenantId);
        sleep(0.2);

        testAttributionVariance(token, tenantId);
        sleep(0.2);

        testTrustStatus(token, tenantId);
        sleep(0.3);
    });

    // EMQ Endpoints
    group('EMQ Score & Status', function () {
        testEmqScore(token, tenantId);
        sleep(0.2);

        testEmqConfidence(token, tenantId);
        sleep(0.2);

        testEmqAutopilotState(token, tenantId);
        sleep(0.2);
    });

    group('EMQ Analysis', function () {
        testEmqPlaybook(token, tenantId);
        sleep(0.2);

        testEmqVolatility(token, tenantId);
        sleep(0.2);
    });

    // Think time between iterations
    sleep(0.5 + Math.random());
}

// =============================================================================
// Setup and Teardown
// =============================================================================

export function setup() {
    console.log(`Starting Trust Layer Load Test`);
    console.log(`Scenario: ${selectedScenario}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Tenant ID: ${TEST_TENANT_ID}`);
    console.log(`Number of test users: ${NUM_TEST_USERS}`);

    const healthRes = http.get(`${BASE_URL}/health`);
    if (healthRes.status !== 200) {
        throw new Error(`API not healthy: ${healthRes.status}`);
    }

    const token = login(getTestEmail(0));
    if (!token) {
        throw new Error('Failed to authenticate during setup');
    }

    console.log('Setup complete - authentication verified');
    return { setupToken: token };
}

export function teardown(data) {
    console.log('Trust Layer Load Test Complete');
}
