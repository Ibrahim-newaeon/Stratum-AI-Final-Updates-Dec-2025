/**
 * =============================================================================
 * Stratum AI Platform - k6 Configuration Module
 * =============================================================================
 *
 * Shared configuration for all k6 load tests.
 * Import this module to get consistent settings across test files.
 */

// =============================================================================
// Environment Configuration
// =============================================================================

export const config = {
    // Base URLs
    baseUrl: __ENV.BASE_URL || 'http://localhost:8000',
    apiV1: (__ENV.BASE_URL || 'http://localhost:8000') + '/api/v1',

    // Test credentials
    testEmail: __ENV.TEST_EMAIL || 'admin@test-tenant.com',
    testPassword: __ENV.TEST_PASSWORD || 'TestPassword123!',
    testTenantId: __ENV.TEST_TENANT_ID || '1',

    // Timeouts
    requestTimeout: '30s',
    connectionTimeout: '10s',
};

// =============================================================================
// Threshold Presets
// =============================================================================

/**
 * Standard performance thresholds for production APIs.
 * Use these for typical business endpoints.
 */
export const standardThresholds = {
    http_req_duration: [
        'p(95)<500',   // 95th percentile < 500ms
        'p(99)<1000',  // 99th percentile < 1s
    ],
    http_req_failed: ['rate<0.01'],  // Error rate < 1%
};

/**
 * Strict thresholds for critical paths (health checks, auth).
 */
export const strictThresholds = {
    http_req_duration: [
        'p(95)<200',   // 95th percentile < 200ms
        'p(99)<500',   // 99th percentile < 500ms
    ],
    http_req_failed: ['rate<0.001'],  // Error rate < 0.1%
};

/**
 * Relaxed thresholds for complex/heavy endpoints.
 */
export const relaxedThresholds = {
    http_req_duration: [
        'p(95)<2000',  // 95th percentile < 2s
        'p(99)<5000',  // 99th percentile < 5s
    ],
    http_req_failed: ['rate<0.05'],  // Error rate < 5%
};

// =============================================================================
// Scenario Presets
// =============================================================================

/**
 * Get scenario configuration by name.
 * @param {string} name - Scenario name
 * @returns {object} k6 scenario configuration
 */
export function getScenario(name) {
    const scenarios = {
        // Quick validation
        smoke: {
            executor: 'constant-vus',
            vus: 1,
            duration: '1m',
        },

        // Light load for development
        dev: {
            executor: 'constant-vus',
            vus: 5,
            duration: '2m',
        },

        // Standard load test
        load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 50 },
                { duration: '5m', target: 50 },
                { duration: '2m', target: 100 },
                { duration: '5m', target: 100 },
                { duration: '2m', target: 0 },
            ],
        },

        // Average production load
        average: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 100,
            maxVUs: 200,
            stages: [
                { duration: '5m', target: 50 },
                { duration: '10m', target: 50 },
                { duration: '5m', target: 10 },
            ],
        },

        // Stress test
        stress: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 100 },
                { duration: '5m', target: 100 },
                { duration: '2m', target: 200 },
                { duration: '5m', target: 200 },
                { duration: '2m', target: 300 },
                { duration: '5m', target: 300 },
                { duration: '5m', target: 0 },
            ],
        },

        // Spike test
        spike: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '10s', target: 100 },
                { duration: '1m', target: 100 },
                { duration: '10s', target: 400 },
                { duration: '3m', target: 400 },
                { duration: '10s', target: 100 },
                { duration: '3m', target: 100 },
                { duration: '10s', target: 0 },
            ],
        },

        // Soak test
        soak: {
            executor: 'constant-vus',
            vus: 50,
            duration: '30m',
        },

        // Breakpoint test (find maximum capacity)
        breakpoint: {
            executor: 'ramping-arrival-rate',
            startRate: 1,
            timeUnit: '1s',
            preAllocatedVUs: 500,
            maxVUs: 1000,
            stages: [
                { duration: '2m', target: 10 },
                { duration: '2m', target: 50 },
                { duration: '2m', target: 100 },
                { duration: '2m', target: 200 },
                { duration: '2m', target: 300 },
                { duration: '2m', target: 400 },
                { duration: '2m', target: 500 },
            ],
        },
    };

    return scenarios[name] || scenarios.load;
}

// =============================================================================
// HTTP Request Helpers
// =============================================================================

/**
 * Get standard headers for API requests.
 * @param {string|null} authToken - Bearer token for authentication
 * @returns {object} HTTP headers object
 */
export function getHeaders(authToken = null) {
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    return headers;
}

/**
 * Get request params with standard configuration.
 * @param {string} name - Request name for tagging
 * @param {string|null} authToken - Optional auth token
 * @returns {object} k6 request parameters
 */
export function getRequestParams(name, authToken = null) {
    return {
        headers: getHeaders(authToken),
        tags: { name: name },
        timeout: config.requestTimeout,
    };
}

// =============================================================================
// Response Validation Helpers
// =============================================================================

/**
 * Check if response is a success (2xx status).
 * @param {object} response - k6 HTTP response
 * @returns {boolean}
 */
export function isSuccess(response) {
    return response.status >= 200 && response.status < 300;
}

/**
 * Check if response is an auth error.
 * @param {object} response - k6 HTTP response
 * @returns {boolean}
 */
export function isAuthError(response) {
    return response.status === 401 || response.status === 403;
}

/**
 * Parse JSON response body safely.
 * @param {object} response - k6 HTTP response
 * @returns {object|null}
 */
export function parseBody(response) {
    try {
        return JSON.parse(response.body);
    } catch {
        return null;
    }
}

/**
 * Check if response has expected API response structure.
 * @param {object} response - k6 HTTP response
 * @returns {boolean}
 */
export function hasValidStructure(response) {
    const body = parseBody(response);
    return body !== null && typeof body.success === 'boolean';
}

// =============================================================================
// Sleep Utilities
// =============================================================================

/**
 * Random sleep between min and max seconds.
 * @param {number} min - Minimum seconds
 * @param {number} max - Maximum seconds
 */
export function randomSleep(min = 1, max = 3) {
    const duration = Math.random() * (max - min) + min;
    const { sleep } = require('k6');
    sleep(duration);
}

/**
 * Exponential backoff sleep.
 * @param {number} attempt - Current attempt number (1-based)
 * @param {number} baseMs - Base milliseconds
 * @param {number} maxMs - Maximum milliseconds
 */
export function backoffSleep(attempt, baseMs = 100, maxMs = 10000) {
    const { sleep } = require('k6');
    const ms = Math.min(baseMs * Math.pow(2, attempt - 1), maxMs);
    sleep(ms / 1000);
}
