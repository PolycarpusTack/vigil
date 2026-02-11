#!/usr/bin/env bash
# E2E test for the Vigil full stack via docker-compose.
# Usage: ./tests/e2e/test_full_stack.sh
#
# Prerequisites: docker, docker compose, curl, jq
# Exit code: 0 = all pass, 1 = any failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASE_URL="http://localhost:8080"
API_KEY="changeme-dev-key"
PASS=0
FAIL=0

# --- Helpers ---

log_pass() {
    echo "  PASS: $1"
    PASS=$((PASS + 1))
}

log_fail() {
    echo "  FAIL: $1 — $2"
    FAIL=$((FAIL + 1))
}

assert_status() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        log_pass "$description"
    else
        log_fail "$description" "expected HTTP $expected, got $actual"
    fi
}

assert_json_field() {
    local description="$1"
    local json="$2"
    local field="$3"
    local expected="$4"
    local actual
    actual=$(echo "$json" | jq -r "$field")
    if [ "$actual" = "$expected" ]; then
        log_pass "$description"
    else
        log_fail "$description" "expected $field=$expected, got $actual"
    fi
}

wait_for_collector() {
    echo "Waiting for collector to be ready..."
    local retries=30
    for i in $(seq 1 $retries); do
        if curl -sf "$BASE_URL/api/v1/health" > /dev/null 2>&1; then
            echo "Collector is ready (attempt $i)"
            return 0
        fi
        sleep 2
    done
    echo "ERROR: Collector did not become ready after $retries attempts"
    return 1
}

# --- Lifecycle ---

cleanup() {
    echo ""
    echo "Tearing down stack..."
    cd "$PROJECT_ROOT"
    docker compose down -v --remove-orphans 2>/dev/null || true
}

trap cleanup EXIT

echo "=== Vigil E2E Tests ==="
echo ""

echo "Starting docker-compose stack..."
cd "$PROJECT_ROOT"
docker compose up -d --build 2>&1

wait_for_collector

echo ""
echo "--- Running tests ---"
echo ""

# --- Test 1: Health check ---
echo "[1] Health check"
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health")
assert_status "GET /api/v1/health returns 200" "200" "$STATUS"

BODY=$(curl -sf "$BASE_URL/api/v1/health")
assert_json_field "Health status is ok" "$BODY" ".status" "ok"

# --- Test 2: Event ingest ---
echo "[2] Event ingest"
EVENT_ID="e2e-test-$(date +%s)"
INGEST_BODY=$(cat <<EOF
{
  "event_id": "$EVENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "version": "1.0.0",
  "action": {"type": "READ", "category": "DATABASE", "operation": "e2e_test"},
  "actor": {"type": "user", "username": "e2e-runner"},
  "metadata": {"application": "e2e-test", "environment": "test"}
}
EOF
)
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/api/v1/events" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$INGEST_BODY")
assert_status "POST /api/v1/events returns 201" "201" "$STATUS"

# --- Test 3: Event retrieval ---
echo "[3] Event retrieval"
RESP=$(curl -sf \
    "$BASE_URL/api/v1/events/$EVENT_ID" \
    -H "Authorization: Bearer $API_KEY")
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    "$BASE_URL/api/v1/events/$EVENT_ID" \
    -H "Authorization: Bearer $API_KEY")
assert_status "GET /api/v1/events/$EVENT_ID returns 200" "200" "$STATUS"
assert_json_field "Retrieved event has correct ID" "$RESP" ".event_id" "$EVENT_ID"

# --- Test 4: Internal metrics ---
echo "[4] Internal metrics"
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/internal/metrics")
assert_status "GET /api/v1/internal/metrics returns 200" "200" "$STATUS"

METRICS=$(curl -sf "$BASE_URL/api/v1/internal/metrics")
# request_count should be > 0 since we've made requests
REQ_COUNT=$(echo "$METRICS" | jq '.request_count')
if [ "$REQ_COUNT" -gt 0 ]; then
    log_pass "request_count > 0"
else
    log_fail "request_count > 0" "got $REQ_COUNT"
fi

UPTIME=$(echo "$METRICS" | jq '.uptime_seconds')
if [ "$(echo "$UPTIME >= 0" | bc -l)" = "1" ]; then
    log_pass "uptime_seconds >= 0"
else
    log_fail "uptime_seconds >= 0" "got $UPTIME"
fi

# --- Test 5: Batch ingest ---
echo "[5] Batch ingest"
BATCH_BODY=$(cat <<EOF
{
  "events": [
    {
      "event_id": "e2e-batch-1-$(date +%s)",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "version": "1.0.0",
      "action": {"type": "WRITE", "category": "API", "operation": "batch_e2e_1"}
    },
    {
      "event_id": "e2e-batch-2-$(date +%s)",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "version": "1.0.0",
      "action": {"type": "EXECUTE", "category": "SYSTEM", "operation": "batch_e2e_2"}
    }
  ]
}
EOF
)
BATCH_RESP=$(curl -sf \
    -X POST "$BASE_URL/api/v1/events/batch" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$BATCH_BODY")
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/api/v1/events/batch" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$BATCH_BODY")
assert_status "POST /api/v1/events/batch returns 201" "201" "$STATUS"
assert_json_field "Batch accepted count is 2" "$BATCH_RESP" ".accepted" "2"

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "FAILED"
    exit 1
else
    echo "ALL PASSED"
    exit 0
fi
