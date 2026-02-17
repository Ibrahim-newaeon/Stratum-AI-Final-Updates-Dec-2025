/**
 * =============================================================================
 * Stratum AI Platform - k6 Load Testing Script
 * =============================================================================
 *
 * Comprehensive load testing for Stratum AI API endpoints.
 * Tests health checks, authentication, and key business endpoints.
 *
 * Usage:
 *   k6 run api-load-test.js                          # Default load test
 *   k6 run --env SCENARIO=smoke api-load-test.js    # Smoke test
 *   k6 run --env SCENARIO=stress api-load-test.js  # Stress test
 *   k6 run --env SCENARIO=soak api-load-test.js    # Soak test
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// =============================================================================
// Configuration
// =============================================================================

// Base URL - override with environment variable
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_V1 = `${BASE_URL}/api/v1`;

// Test credentials (override via environment)
const TEST_EMAIL = __ENV.TEST_EMAIL || 'admin@test-tenant.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';
const TEST_TENANT_ID = __ENV.TEST_TENANT_ID || '1';

// =============================================================================
// Custom Metrics
// =============================================================================

// Counters
const healthCheckSuccess = new Counter('health_check_success');
const healthCheckFailure = new Counter('health_check_failure');
const loginSuccess = new Counter('login_success');
const loginFailure = new Counter('login_failure');
const emqScoreSuccess = new Counter('emq_score_success');
const emqScoreFailure = new Counter('emq_score_failure');
const campaignsSuccess = new Counter('campaigns_success');
const campaignsFailure = new Counter('campaigns_failure');

// Rates
const errorRate = new Rate('errors');
const authErrorRate = new Rate('auth_errors');

// Trends
const healthCheckDuration = new Trend('health_check_duration', true);
const loginDuration = new Trend('login_duration', true);
const emqScoreDuration = new Trend('emq_score_duration', true);
const campaignsDuration = new Trend('campaigns_duration', true);

// =============================================================================
// Test Scenarios
// =============================================================================

const scenarios = {
    // Smoke test - minimal load to verify system works
    smoke: {
        executor: 'constant-vus',
        vus: 1,
        duration: '1m',
    },

    // Load test - typical expected load
    load: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '2m', target: 50 },   // Ramp up to 50 users
            { duration: '5m', target: 50 },   // Stay at 50 users
            { duration: '2m', target: 100 },  // Ramp up to 100 users
            { duration: '5m', target: 100 },  // Stay at 100 users
            { duration: '2m', target: 0 },    // Ramp down to 0
        ],
    },

    // Stress test - push system beyond normal capacity
    stress: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '2m', target: 100 },  // Ramp up quickly
            { duration: '5m', target: 100 },  // Hold at 100
            { duration: '2m', target: 200 },  // Push to 200
            { duration: '5m', target: 200 },  // Hold at 200
            { duration: '2m', target: 300 },  // Push to breaking point
            { duration: '5m', target: 300 },  // Hold at breaking point
            { duration: '5m', target: 0 },    // Recovery ramp down
        ],
    },

    // Spike test - sudden traffic spike
    spike: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '10s', target: 100 }, // Instant spike
            { duration: '1m', target: 100 },  // Hold spike
            { duration: '10s', target: 400 }, // Massive spike
            { duration: '3m', target: 400 },  // Hold massive spike
            { duration: '10s', target: 100 }, // Drop back
            { duration: '3m', target: 100 },  // Hold
            { duration: '10s', target: 0 },   // Ramp down
        ],
    },

    // Soak test - extended duration for memory leaks
    soak: {
        executor: 'constant-vus',
        vus: 50,
        duration: '30m',
    },
};

// Select scenario based on environment variable
const selectedScenario = __ENV.SCENARIO || 'load';

export const options = {
    scenarios: {
        default: scenarios[selectedScenario] || scenarios.load,
    },

    // Global thresholds
    thresholds: {
        // Response time thresholds
        http_req_duration: [
            'p(95)<500',    // 95th percentile < 500ms
            'p(99)<1000',   // 99th percentile < 1000ms
        ],

        // Error rate threshold
        http_req_failed: ['rate<0.01'],  // Error rate < 1%

        // Custom metric thresholds
        health_check_duration: ['p(95)<200'],   // Health check < 200ms
        login_duration: ['p(95)<1000'],          // Login < 1s
        emq_score_duration: ['p(95)<500'],       // EMQ score < 500ms
        campaigns_duration: ['p(95)<500'],       // Campaigns list < 500ms

        // Error rates
        errors: ['rate<0.01'],           // Overall error rate < 1%
        auth_errors: ['rate<0.05'],      // Auth error rate < 5%
    },

    // Summary output configuration
    summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// =============================================================================
// Setup Function
// =============================================================================

export function setup() {
    console.log(`Starting ${selectedScenario} test against ${BASE_URL}`);
    console.log(`Test tenant ID: ${TEST_TENANT_ID}`);

    // Verify health endpoint is accessible
    const healthRes = http.get(`${BASE_URL}/health`);
    if (healthRes.status !== 200) {
        throw new Error(`Health check failed during setup: ${healthRes.status}`);
    }

    // Attempt login to get auth token for authenticated tests
    let authToken = null;
    const loginPayload = JSON.stringify({
        email: TEST_EMAIL,
        password: TEST_PASSWORD,
    });

    const loginRes = http.post(`${API_V1}/auth/login`, loginPayload, {
        headers: { 'Content-Type': 'application/json' },
    });

    if (loginRes.status === 200) {
        try {
            const body = JSON.parse(loginRes.body);
            authToken = body.data?.access_token || null;
            console.log('Setup login successful');
        } catch (e) {
            console.log('Setup login response parsing failed');
        }
    } else {
        console.log(`Setup login failed with status ${loginRes.status} - continuing with unauthenticated tests`);
    }

    return {
        authToken: authToken,
        tenantId: TEST_TENANT_ID,
    };
}

// =============================================================================
// Main Test Function
// =============================================================================

export default function (data) {
    const authHeaders = data.authToken
        ? {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${data.authToken}`,
          }
        : {
              'Content-Type': 'application/json',
          };

    // -------------------------------------------------------------------------
    // Group 1: Health Check Endpoints
    // -------------------------------------------------------------------------
    group('Health Checks', function () {
        // Basic health check
        const healthRes = http.get(`${BASE_URL}/health`, {
            tags: { name: 'GET /health' },
        });

        healthCheckDuration.add(healthRes.timings.duration);

        const healthOk = check(healthRes, {
            'health: status is 200': (r) => r.status === 200,
            'health: response has status field': (r) => {
                try {
                    return JSON.parse(r.body).status !== undefined;
                } catch {
                    return false;
                }
            },
            'health: status is healthy': (r) => {
                try {
                    return JSON.parse(r.body).status === 'healthy';
                } catch {
                    return false;
                }
            },
        });

        if (healthOk) {
            healthCheckSuccess.add(1);
        } else {
            healthCheckFailure.add(1);
            errorRate.add(1);
        }

        // Readiness probe
        const readyRes = http.get(`${BASE_URL}/health/ready`, {
            tags: { name: 'GET /health/ready' },
        });

        check(readyRes, {
            'ready: status is 200 or 503': (r) => r.status === 200 || r.status === 503,
        });

        // Liveness probe
        const liveRes = http.get(`${BASE_URL}/health/live`, {
            tags: { name: 'GET /health/live' },
        });

        check(liveRes, {
            'live: status is 200': (r) => r.status === 200,
        });

        sleep(0.5);
    });

    // -------------------------------------------------------------------------
    // Group 2: Authentication Endpoints
    // -------------------------------------------------------------------------
    group('Authentication', function () {
        // Login attempt
        const loginPayload = JSON.stringify({
            email: TEST_EMAIL,
            password: TEST_PASSWORD,
        });

        const loginRes = http.post(`${API_V1}/auth/login`, loginPayload, {
            headers: { 'Content-Type': 'application/json' },
            tags: { name: 'POST /api/v1/auth/login' },
        });

        loginDuration.add(loginRes.timings.duration);

        const loginOk = check(loginRes, {
            'login: status is 200 or 401': (r) => r.status === 200 || r.status === 401,
            'login: response time < 1s': (r) => r.timings.duration < 1000,
        });

        if (loginRes.status === 200) {
            loginSuccess.add(1);

            const loginSuccessCheck = check(loginRes, {
                'login: has access_token': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.data?.access_token !== undefined;
                    } catch {
                        return false;
                    }
                },
                'login: has refresh_token': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.data?.refresh_token !== undefined;
                    } catch {
                        return false;
                    }
                },
            });

            if (!loginSuccessCheck) {
                errorRate.add(1);
            }
        } else if (loginRes.status === 401) {
            // Expected for invalid credentials
            authErrorRate.add(1);
            loginFailure.add(1);
        } else {
            loginFailure.add(1);
            errorRate.add(1);
        }

        // Invalid login attempt (should return 401)
        const invalidLoginPayload = JSON.stringify({
            email: 'invalid@invalid.com',
            password: 'wrongpassword',
        });

        const invalidLoginRes = http.post(`${API_V1}/auth/login`, invalidLoginPayload, {
            headers: { 'Content-Type': 'application/json' },
            tags: { name: 'POST /api/v1/auth/login (invalid)' },
        });

        check(invalidLoginRes, {
            'invalid login: returns 401': (r) => r.status === 401,
            'invalid login: response time < 1s': (r) => r.timings.duration < 1000,
        });

        sleep(0.5);
    });

    // -------------------------------------------------------------------------
    // Group 3: EMQ Score Endpoint (Authenticated)
    // -------------------------------------------------------------------------
    group('EMQ Score', function () {
        const emqRes = http.get(
            `${API_V1}/tenants/${data.tenantId}/emq/score`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/tenant/{id}/emq/score' },
            }
        );

        emqScoreDuration.add(emqRes.timings.duration);

        // Accept 200 (success), 401/403 (auth issues), or 404 (tenant not found)
        const emqOk = check(emqRes, {
            'emq: status is valid': (r) => [200, 401, 403, 404].includes(r.status),
            'emq: response time < 500ms': (r) => r.timings.duration < 500,
        });

        if (emqRes.status === 200) {
            emqScoreSuccess.add(1);

            check(emqRes, {
                'emq: has score field': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.data?.score !== undefined;
                    } catch {
                        return false;
                    }
                },
                'emq: score is valid number': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        const score = body.data?.score;
                        return typeof score === 'number' && score >= 0 && score <= 100;
                    } catch {
                        return false;
                    }
                },
                'emq: has confidence band': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.data?.confidenceBand !== undefined;
                    } catch {
                        return false;
                    }
                },
            });
        } else if (emqRes.status === 401 || emqRes.status === 403) {
            authErrorRate.add(1);
            emqScoreFailure.add(1);
        } else {
            emqScoreFailure.add(1);
            if (emqRes.status !== 404) {
                errorRate.add(1);
            }
        }

        sleep(0.5);
    });

    // -------------------------------------------------------------------------
    // Group 4: Campaigns Endpoint (Authenticated)
    // -------------------------------------------------------------------------
    group('Campaigns', function () {
        // List campaigns
        const campaignsRes = http.get(
            `${API_V1}/campaigns?page=1&page_size=20`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/campaigns' },
            }
        );

        campaignsDuration.add(campaignsRes.timings.duration);

        const campaignsOk = check(campaignsRes, {
            'campaigns: status is valid': (r) => [200, 401, 403].includes(r.status),
            'campaigns: response time < 500ms': (r) => r.timings.duration < 500,
        });

        if (campaignsRes.status === 200) {
            campaignsSuccess.add(1);

            check(campaignsRes, {
                'campaigns: has items array': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return Array.isArray(body.data?.items);
                    } catch {
                        return false;
                    }
                },
                'campaigns: has pagination info': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.data?.total !== undefined && body.data?.page !== undefined;
                    } catch {
                        return false;
                    }
                },
            });
        } else if (campaignsRes.status === 401 || campaignsRes.status === 403) {
            authErrorRate.add(1);
            campaignsFailure.add(1);
        } else {
            campaignsFailure.add(1);
            errorRate.add(1);
        }

        // Campaign with specific ID (should handle 404 gracefully)
        const campaignDetailRes = http.get(
            `${API_V1}/campaigns/1`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/campaigns/{id}' },
            }
        );

        check(campaignDetailRes, {
            'campaign detail: status is valid': (r) => [200, 401, 403, 404].includes(r.status),
            'campaign detail: response time < 500ms': (r) => r.timings.duration < 500,
        });

        sleep(0.5);
    });

    // -------------------------------------------------------------------------
    // Group 5: Additional EMQ Endpoints (Authenticated)
    // -------------------------------------------------------------------------
    group('EMQ Additional Endpoints', function () {
        // Confidence data
        const confidenceRes = http.get(
            `${API_V1}/tenants/${data.tenantId}/emq/confidence`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/tenant/{id}/emq/confidence' },
            }
        );

        check(confidenceRes, {
            'confidence: status is valid': (r) => [200, 401, 403, 404].includes(r.status),
            'confidence: response time < 500ms': (r) => r.timings.duration < 500,
        });

        // Playbook
        const playbookRes = http.get(
            `${API_V1}/tenants/${data.tenantId}/emq/playbook`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/tenant/{id}/emq/playbook' },
            }
        );

        check(playbookRes, {
            'playbook: status is valid': (r) => [200, 401, 403, 404].includes(r.status),
            'playbook: response time < 500ms': (r) => r.timings.duration < 500,
        });

        // Autopilot state
        const autopilotRes = http.get(
            `${API_V1}/tenants/${data.tenantId}/emq/autopilot-state`,
            {
                headers: authHeaders,
                tags: { name: 'GET /api/v1/tenant/{id}/emq/autopilot-state' },
            }
        );

        check(autopilotRes, {
            'autopilot: status is valid': (r) => [200, 401, 403, 404].includes(r.status),
            'autopilot: response time < 500ms': (r) => r.timings.duration < 500,
        });

        sleep(0.5);
    });

    // Think time between iterations
    sleep(Math.random() * 2 + 1); // 1-3 seconds
}

// =============================================================================
// Teardown Function
// =============================================================================

export function teardown(data) {
    console.log(`${selectedScenario} test completed`);
    console.log('Review the summary for detailed metrics and threshold results');
}

// =============================================================================
// Handle Summary
// =============================================================================

export function handleSummary(data) {
    const now = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `load-test-results-${selectedScenario}-${now}.json`;

    return {
        'stdout': textSummary(data, { indent: '  ', enableColors: true }),
        [filename]: JSON.stringify(data, null, 2),
    };
}

// Text summary helper
function textSummary(data, options) {
    const { metrics, root_group } = data;
    let output = '\n';

    output += '='.repeat(70) + '\n';
    output += `  Stratum AI Load Test Summary - ${selectedScenario.toUpperCase()}\n`;
    output += '='.repeat(70) + '\n\n';

    // Thresholds summary
    output += 'THRESHOLDS:\n';
    for (const [name, threshold] of Object.entries(data.metrics)) {
        if (threshold.thresholds) {
            for (const [condition, passed] of Object.entries(threshold.thresholds)) {
                const status = passed ? 'PASS' : 'FAIL';
                const symbol = passed ? '+' : '-';
                output += `  [${symbol}] ${name}: ${condition} - ${status}\n`;
            }
        }
    }

    output += '\n' + '-'.repeat(70) + '\n';
    output += 'KEY METRICS:\n';

    // HTTP metrics
    const httpDuration = metrics.http_req_duration;
    if (httpDuration) {
        output += `\n  HTTP Request Duration:\n`;
        output += `    avg: ${httpDuration.values.avg?.toFixed(2)}ms\n`;
        output += `    p(95): ${httpDuration.values['p(95)']?.toFixed(2)}ms\n`;
        output += `    p(99): ${httpDuration.values['p(99)']?.toFixed(2)}ms\n`;
    }

    const httpFailed = metrics.http_req_failed;
    if (httpFailed) {
        output += `\n  Error Rate: ${(httpFailed.values.rate * 100).toFixed(2)}%\n`;
    }

    const httpReqs = metrics.http_reqs;
    if (httpReqs) {
        output += `  Total Requests: ${httpReqs.values.count}\n`;
        output += `  Requests/sec: ${httpReqs.values.rate?.toFixed(2)}\n`;
    }

    output += '\n' + '='.repeat(70) + '\n';

    return output;
}
