#!/bin/bash
# =============================================================================
# Stratum AI - Staging/Production Smoke Tests
# =============================================================================
# Usage: BASE_URL=https://api.stratum.ai ./scripts/smoke_test.sh
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FAILED=0
PASSED=0

check() {
  local name="$1" url="$2" expected="$3"
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected" ]; then
    echo "  PASS: $name ($status)"
    PASSED=$((PASSED + 1))
  else
    echo "  FAIL: $name (expected $expected, got $status)"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== Stratum AI Smoke Tests ==="
echo "Target: $BASE_URL"
echo ""

# --- Health Checks ---
echo "[Health Checks]"
check "Liveness (/health/live)"   "$BASE_URL/health/live"  "200"
check "Readiness (/health/ready)" "$BASE_URL/health/ready" "200"
check "Full health (/health)"     "$BASE_URL/health"       "200"

# --- Auth Endpoints (422 = endpoint works but missing body) ---
echo ""
echo "[Auth Endpoints]"
check "POST /auth/login (no body)"    "$BASE_URL/api/v1/auth/login"    "422"
check "POST /auth/register (no body)" "$BASE_URL/api/v1/auth/register" "422"

# --- Protected Endpoints (401 = auth required) ---
echo ""
echo "[Protected Endpoints]"
check "GET /dashboard/overview (unauthed)" "$BASE_URL/api/v1/dashboard/overview" "401"
check "GET /campaigns (unauthed)"          "$BASE_URL/api/v1/campaigns"          "401"

# --- Metrics ---
echo ""
echo "[Observability]"
check "Prometheus /metrics" "$BASE_URL/metrics" "200"

# --- Database Connectivity (via health endpoint) ---
echo ""
echo "[Database Connectivity]"
health_body=$(curl -s --max-time 10 "$BASE_URL/health" 2>/dev/null || echo "{}")
db_status=$(echo "$health_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database','unknown'))" 2>/dev/null || echo "unknown")
if [ "$db_status" = "healthy" ]; then
  echo "  PASS: Database connectivity ($db_status)"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Database connectivity ($db_status)"
  FAILED=$((FAILED + 1))
fi

redis_status=$(echo "$health_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('redis','unknown'))" 2>/dev/null || echo "unknown")
if [ "$redis_status" = "healthy" ]; then
  echo "  PASS: Redis connectivity ($redis_status)"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Redis connectivity ($redis_status)"
  FAILED=$((FAILED + 1))
fi

# --- Summary ---
echo ""
echo "=== Results: $PASSED passed, $FAILED failed ==="
if [ $FAILED -gt 0 ]; then
  echo "SMOKE TESTS FAILED"
  exit 1
else
  echo "ALL SMOKE TESTS PASSED"
fi
