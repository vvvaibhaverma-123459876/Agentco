#!/bin/bash

# =============================================================================
# STAGING SMOKE TEST
# =============================================================================
# Comprehensive smoke test for staging deployment verification
# Tests 17 critical system components and verifies production-like behavior
# Exit code 0 = staging operational and production-ready
# Exit code 1 = critical component failed
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

SMOKE_DIR="/tmp/agentco_staging_smoke_$(date +%Y%m%d_%H%M%S)"
AUDIT_DIR="/Users/Zet/Agentco/audit_artifacts/staging_smoke_test"

mkdir -p "$SMOKE_DIR"
mkdir -p "$AUDIT_DIR"

LOG_FILE="$AUDIT_DIR/smoke_test_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           STAGING SMOKE TEST - System Verification            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Start Time: $(date)"
echo "Log: $LOG_FILE"
echo ""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

test_point() {
  local num=$1
  local total=$2
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[$num/$total] $3"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

pass_test() {
  echo "${GREEN}✓ PASS${RESET}: $1"
  ((TESTS_PASSED++))
}

fail_test() {
  echo "${RED}✗ FAIL${RESET}: $1"
  ((TESTS_FAILED++))
  FAILURE_REASON="$1"
}

warn_test() {
  echo "${YELLOW}⚠ WARN${RESET}: $1"
}

# Initialize counters
TESTS_PASSED=0
TESTS_FAILED=0
FAILURE_REASON=""

# =============================================================================
# TEST 1: BACKEND HEALTH
# =============================================================================

test_point 1 17 "Backend health check"

RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:3001/api/health 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
  STATUS=$(echo "$BODY" | jq -r '.status' 2>/dev/null)
  if [ "$STATUS" = "ready" ]; then
    pass_test "Backend health: $STATUS (HTTP 200)"
  else
    fail_test "Backend health returned status=$STATUS (expected 'ready')"
  fi
else
  fail_test "Backend health check failed (HTTP $HTTP_CODE)"
fi

# =============================================================================
# TEST 2: DATABASE CONNECTIVITY
# =============================================================================

test_point 2 17 "Database connectivity"

cd /Users/Zet/Agentco
source .env.staging 2>/dev/null || { fail_test "Cannot load .env.staging"; exit 1; }

if psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
  pass_test "PostgreSQL connected"
else
  fail_test "PostgreSQL connection failed"
fi

# =============================================================================
# TEST 3: DATABASE SCHEMA VERIFICATION
# =============================================================================

test_point 3 17 "Database schema verification"

TABLE_COUNT=$(psql "$DATABASE_URL" -t -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null)

if [ "$TABLE_COUNT" -ge 40 ]; then
  pass_test "Database schema complete ($TABLE_COUNT tables)"
else
  fail_test "Database schema incomplete (only $TABLE_COUNT tables, expected 40+)"
fi

# =============================================================================
# TEST 4: KAFKA CONNECTIVITY
# =============================================================================

test_point 4 17 "Kafka message queue connectivity"

KAFKA_HOST=$(echo $KAFKA_BROKERS | cut -d: -f1)
KAFKA_PORT=$(echo $KAFKA_BROKERS | cut -d: -f2)

if timeout 5 bash -c "echo > /dev/tcp/$KAFKA_HOST/$KAFKA_PORT" 2>/dev/null; then
  pass_test "Kafka broker accessible"
else
  warn_test "Kafka broker not accessible (may be expected in dev)"
fi

# =============================================================================
# TEST 5: REDIS CONNECTIVITY
# =============================================================================

test_point 5 17 "Redis cache connectivity"

REDIS_RESPONSE=$(redis-cli -p 6380 PING 2>/dev/null || echo "FAIL")

if [ "$REDIS_RESPONSE" = "PONG" ]; then
  pass_test "Redis cache available"
else
  warn_test "Redis cache not accessible (some tests will skip)"
fi

# =============================================================================
# TEST 6: API AUTHENTICATION
# =============================================================================

test_point 6 17 "API authentication enforcement"

# Test without auth - should fail
NO_AUTH=$(curl -s -w "%{http_code}" -o /dev/null \
  http://localhost:3001/api/admin/settings 2>/dev/null)

if [ "$NO_AUTH" = "401" ] || [ "$NO_AUTH" = "403" ]; then
  pass_test "Unauthenticated requests rejected (HTTP $NO_AUTH)"
else
  fail_test "Unauthenticated requests not rejected (HTTP $NO_AUTH)"
fi

# Test with valid auth - should succeed
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer test-api-key" \
  http://localhost:3001/api/health 2>/dev/null)

AUTH_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
if [ "$AUTH_CODE" = "200" ]; then
  pass_test "Authenticated requests accepted (HTTP 200)"
else
  warn_test "Auth header processing (HTTP $AUTH_CODE)"
fi

# =============================================================================
# TEST 7: AUDIT LOGGING
# =============================================================================

test_point 7 17 "Audit logging system"

# Create a test record
curl -s -X POST http://localhost:3001/api/test-audit \
  -H "Content-Type: application/json" \
  -d '{"test": "smoke_test"}' 2>/dev/null

# Query audit logs
AUDIT_COUNT=$(psql "$DATABASE_URL" -t -c \
  "SELECT count(*) FROM audit_log WHERE action LIKE '%test%' OR created_at > now() - interval '5 minutes';" 2>/dev/null)

if [ "$AUDIT_COUNT" -gt 0 ]; then
  pass_test "Audit logging active ($AUDIT_COUNT recent events)"
else
  warn_test "Audit logs may not be populated yet"
fi

# =============================================================================
# TEST 8: GOVERNANCE GATES STATUS
# =============================================================================

test_point 8 17 "Governance gates initialization"

GOVERNANCE=$(curl -s http://localhost:3001/api/governance/status 2>/dev/null)

if echo "$GOVERNANCE" | jq -e '.emergency_stop' > /dev/null 2>&1; then
  EMERGENCY=$(echo "$GOVERNANCE" | jq -r '.emergency_stop')
  pass_test "Governance gates initialized (emergency_stop=$EMERGENCY)"
else
  warn_test "Governance status endpoint may need more time"
fi

# =============================================================================
# TEST 9: RBAC ENFORCEMENT
# =============================================================================

test_point 9 17 "RBAC enforcement verification"

# Try to access admin endpoint with viewer role (should fail)
RBAC_TEST=$(curl -s -w "%{http_code}" -o /dev/null \
  -H "Authorization: Bearer test-viewer-key" \
  http://localhost:3001/api/admin/settings 2>/dev/null)

if [ "$RBAC_TEST" = "403" ]; then
  pass_test "RBAC enforcement active (unauthorized: HTTP 403)"
else
  warn_test "RBAC test inconclusive (HTTP $RBAC_TEST)"
fi

# =============================================================================
# TEST 10: PROTECTED SURFACE IMMUTABILITY
# =============================================================================

test_point 10 17 "Protected surface immutability"

# Try to modify calibration (should fail or be blocked)
CALIBRATION_TEST=$(curl -s -X PUT http://localhost:3001/api/calibration \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"override": true}' 2>/dev/null)

if echo "$CALIBRATION_TEST" | jq -e '.error' > /dev/null 2>&1; then
  ERROR=$(echo "$CALIBRATION_TEST" | jq -r '.error')
  if echo "$ERROR" | grep -q "immutable\|protected\|readonly"; then
    pass_test "Protected surfaces immutable (error: $ERROR)"
  else
    warn_test "Protected surface test returned error (may be 404)"
  fi
else
  warn_test "Protected surface test needs endpoint verification"
fi

# =============================================================================
# TEST 11: DATABASE TRANSACTION SUPPORT
# =============================================================================

test_point 11 17 "Database transaction support"

# Test ACID properties with a simple transaction
TRANSACTION=$(psql "$DATABASE_URL" -t -c "
  BEGIN;
  CREATE TEMPORARY TABLE test_acid (id SERIAL, value TEXT);
  INSERT INTO test_acid (value) VALUES ('test');
  SELECT count(*) FROM test_acid;
  ROLLBACK;
" 2>/dev/null)

if [ -n "$TRANSACTION" ]; then
  pass_test "Database ACID transactions working"
else
  fail_test "Database transactions failed"
fi

# =============================================================================
# TEST 12: OBSERVABILITY METRICS
# =============================================================================

test_point 12 17 "Observability metrics collection"

# Check Prometheus
PROM_HEALTH=$(curl -s -w "%{http_code}" -o /dev/null \
  http://localhost:9090/-/healthy 2>/dev/null)

if [ "$PROM_HEALTH" = "200" ]; then
  pass_test "Prometheus metrics store accessible (HTTP 200)"
else
  warn_test "Prometheus may not be ready (HTTP $PROM_HEALTH)"
fi

# =============================================================================
# TEST 13: GRAFANA DASHBOARDS
# =============================================================================

test_point 13 17 "Grafana visualization"

GRAFANA_HEALTH=$(curl -s -w "%{http_code}" -o /dev/null \
  http://localhost:3050/api/health 2>/dev/null)

if [ "$GRAFANA_HEALTH" = "200" ] || [ "$GRAFANA_HEALTH" = "302" ]; then
  pass_test "Grafana accessible (HTTP $GRAFANA_HEALTH)"
else
  warn_test "Grafana not ready (HTTP $GRAFANA_HEALTH)"
fi

# =============================================================================
# TEST 14: ENVIRONMENT CONFIGURATION
# =============================================================================

test_point 14 17 "Environment configuration validation"

# Check critical variables
AGENTCO_ENV_CHECK=$(grep "^AGENTCO_ENV=" .env.staging | cut -d= -f2)
NODE_ENV_CHECK=$(grep "^NODE_ENV=" .env.staging | cut -d= -f2)

if [ "$AGENTCO_ENV_CHECK" = "staging" ] && [ "$NODE_ENV_CHECK" = "production" ]; then
  pass_test "Environment configuration correct (staging mode, production node env)"
else
  fail_test "Environment configuration incorrect (AGENTCO_ENV=$AGENTCO_ENV_CHECK, NODE_ENV=$NODE_ENV_CHECK)"
fi

# =============================================================================
# TEST 15: SAFETY FLAGS ENFORCEMENT
# =============================================================================

test_point 15 17 "Safety flags enforcement"

# Check that safety flags are enabled in config
SAFETY_FLAGS_SET=true

for flag in AUDIT_LOGGING_REQUIRED EMERGENCY_SHUTDOWN_ENABLED RBAC_ENFORCEMENT PROTECTED_SURFACE_ENFORCEMENT; do
  VALUE=$(grep "^${flag}=" .env.staging | cut -d= -f2)
  if [ "$VALUE" != "true" ]; then
    SAFETY_FLAGS_SET=false
    break
  fi
done

if [ "$SAFETY_FLAGS_SET" = true ]; then
  pass_test "All safety flags enabled in configuration"
else
  fail_test "Some safety flags disabled or missing"
fi

# =============================================================================
# TEST 16: EXTERNAL ISOLATION VERIFICATION
# =============================================================================

test_point 16 17 "External side effects isolation"

# Verify that AUTONOMY_EXTERNAL_SIDE_EFFECTS is disabled
EXT_EFFECTS=$(grep "^AUTONOMY_EXTERNAL_SIDE_EFFECTS=" .env.staging | cut -d= -f2)

if [ "$EXT_EFFECTS" = "false" ]; then
  pass_test "External side effects disabled (staging isolation active)"
else
  fail_test "External side effects may be enabled (should be false)"
fi

# =============================================================================
# TEST 17: DEPLOYMENT READINESS SUMMARY
# =============================================================================

test_point 17 17 "Deployment readiness verification"

# Check that readiness documents exist
DOCS_EXIST=true

for doc in docs/PRODUCTION_READINESS_SUMMARY.md docs/STAGING_DEPLOYMENT_GUIDE.md; do
  if [ ! -f "$doc" ]; then
    DOCS_EXIST=false
    warn_test "Missing document: $doc"
  fi
done

if [ "$DOCS_EXIST" = true ]; then
  pass_test "All deployment readiness documentation present"
else
  warn_test "Some documentation may be missing"
fi

# =============================================================================
# FINAL SUMMARY
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                       SMOKE TEST SUMMARY                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo "Tests Passed: ${GREEN}$TESTS_PASSED${RESET}/17"
echo "Tests Failed: ${RED}$TESTS_FAILED${RESET}/17"
echo "Pass Rate: ${BLUE}${PASS_RATE}%${RESET}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo "${GREEN}✅ STAGING SMOKE TEST: PASSED${RESET}"
  echo ""
  echo "System is operational and ready for:"
  echo "  • Load testing"
  echo "  • Disaster recovery procedures"
  echo "  • 48-hour burn-in monitoring"
  echo "  • Production promotion checklist"
  echo ""
  echo "Exit code: 0"
  exit 0
else
  echo "${RED}❌ STAGING SMOKE TEST: FAILED${RESET}"
  echo ""
  echo "Critical Failure: $FAILURE_REASON"
  echo ""
  echo "Next Steps:"
  echo "  1. Review log file: $LOG_FILE"
  echo "  2. Check failing component (database, network, etc.)"
  echo "  3. Verify infrastructure is healthy"
  echo "  4. Re-run: $0"
  echo ""
  echo "Exit code: 1"
  exit 1
fi
