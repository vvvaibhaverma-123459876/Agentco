#!/bin/bash
# ============================================================
# LEVEL_3 Functional Verification Runner
# ============================================================
# One-command test of LEVEL_3 autonomy implementation.
#
# This script:
#   1. Starts Docker Postgres
#   2. Waits for database to be ready
#   3. Applies migrations
#   4. Starts backend server
#   5. Waits for backend health check
#   6. Runs LEVEL_3 smoke test
#   7. Verifies database evidence
#   8. Reports results
#
# Exit codes:
#   0 = LEVEL_3 FUNCTIONALLY VERIFIED ✅
#   1 = LEVEL_3 FAILED ❌
#   2 = External environment blocker

set -e
set -o pipefail

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
BACKEND_DIR="$REPO_ROOT/backend"
ARTIFACTS_DIR="$REPO_ROOT/audit_artifacts/level3_functional_verification"
TEST_ENV_FILE="$REPO_ROOT/.env.level3.test"

# Create artifacts directory
mkdir -p "$ARTIFACTS_DIR"

# Load test environment
if [ ! -f "$TEST_ENV_FILE" ]; then
    echo "❌ Test environment file not found: $TEST_ENV_FILE"
    exit 1
fi

export $(grep -v '^#' "$TEST_ENV_FILE" | xargs)

echo "================================================================================"
echo "LEVEL_3 AUTONOMY FUNCTIONAL VERIFICATION"
echo "================================================================================"
echo ""
echo "📋 Test Configuration:"
echo "   Database: $DATABASE_URL"
echo "   Backend: $BACKEND_HOST:$BACKEND_PORT"
echo "   Artifacts: $ARTIFACTS_DIR"
echo "   Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ========== STEP 1: START POSTGRES ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Starting PostgreSQL..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "   Required: Docker with docker-compose support"
    exit 2
fi

cd "$REPO_ROOT"

# Check if docker daemon is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running"
    echo "   Please start Docker and try again"
    exit 2
fi

# Start postgres (and other services)
echo "   Starting docker-compose services..."
docker compose up -d postgres redis zookeeper kafka 2>&1 | tee -a "$ARTIFACTS_DIR/docker_startup.log"

echo "   ✅ Docker services started"
echo ""

# ========== STEP 2: WAIT FOR POSTGRES ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Waiting for PostgreSQL health check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! bash "$SCRIPTS_DIR/wait_for_postgres.sh" 2>&1 | tee -a "$ARTIFACTS_DIR/postgres_wait.log"; then
    echo ""
    echo "❌ PostgreSQL failed to become ready"
    echo "   Check: docker logs agentco-postgres"
    exit 1
fi

echo ""

# ========== STEP 3: RUN MIGRATIONS ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Applying database migrations..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$BACKEND_DIR"

if ! npm install > /dev/null 2>&1; then
    echo "⚠️  npm install had issues (may be non-fatal)"
fi

if ! npm run db:migrate 2>&1 | tee -a "$ARTIFACTS_DIR/migrations.log"; then
    echo ""
    echo "❌ Database migrations failed"
    exit 1
fi

echo "   ✅ Migrations applied successfully"
echo ""

# ========== STEP 4: START BACKEND ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Starting backend server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$BACKEND_DIR"

# Start backend in background
npm run dev > "$ARTIFACTS_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "   Backend process started (PID: $BACKEND_PID)"
echo "   Waiting for server to initialize..."

# ========== STEP 5: WAIT FOR BACKEND HEALTH ==========
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Waiting for backend health check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HEALTH_URL="http://$BACKEND_HOST:$BACKEND_PORT/health"
MAX_HEALTH_RETRIES=30
HEALTH_RETRY_INTERVAL=2

retry_count=0
while [ $retry_count -lt $MAX_HEALTH_RETRIES ]; do
    if curl -s "$HEALTH_URL" > /dev/null 2>&1; then
        echo "   ✅ Backend is healthy"
        break
    fi

    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "   ❌ Backend process died"
        echo ""
        echo "Backend logs:"
        tail -50 "$ARTIFACTS_DIR/backend.log"
        exit 1
    fi

    echo -n "."
    sleep $HEALTH_RETRY_INTERVAL
    retry_count=$((retry_count + 1))
done

if [ $retry_count -ge $MAX_HEALTH_RETRIES ]; then
    echo ""
    echo "   ❌ Backend failed to become healthy"
    echo ""
    echo "Backend logs (last 50 lines):"
    tail -50 "$ARTIFACTS_DIR/backend.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
sleep 5  # Extra time for backend to fully initialize
echo ""

# Check if backend is really listening
echo "   Checking backend connectivity..."
if curl -s "http://$BACKEND_HOST:$BACKEND_PORT/health" > /dev/null; then
    echo "   ✅ Backend is responding to requests"
else
    echo "   ⚠️  Backend health check failed"
fi

echo ""

# ========== STEP 6: RUN SMOKE TEST ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Running LEVEL_3 smoke test..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$REPO_ROOT"

# Run smoke test - capture exit status properly with pipefail
SMOKE_EXIT_CODE=0
python3 "$SCRIPTS_DIR/run_level3_real_smoke.py" 2>&1 | tee -a "$ARTIFACTS_DIR/smoke_test.log"
SMOKE_EXIT_CODE=${PIPESTATUS[0]}

echo ""

# ========== STEP 7: VERIFY DATABASE EVIDENCE ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 7: Verifying database evidence..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$REPO_ROOT"

# Run database verification
DB_VERIFY_EXIT_CODE=0
if python3 "$SCRIPTS_DIR/verify_level3_db_evidence.py" 2>&1 | tee -a "$ARTIFACTS_DIR/db_verification.log"; then
    echo "   ✅ Database evidence verified"
else
    DB_VERIFY_EXIT_CODE=1
    echo "   ⚠️  Database verification had issues"
fi

echo ""

# ========== CLEANUP ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CLEANUP: Shutting down backend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

kill $BACKEND_PID 2>/dev/null || true
sleep 2

# Optional: Keep docker services running for manual inspection, or stop them
# Uncomment to stop services:
# docker compose down

echo "   ✅ Backend stopped"
echo ""

# ========== RESULTS ==========
echo "================================================================================"
if [ $SMOKE_EXIT_CODE -eq 0 ] && [ $DB_VERIFY_EXIT_CODE -eq 0 ]; then
    echo "✅ LEVEL_3 SMOKE TEST PASSED"
    echo "================================================================================"
    echo ""
    echo "VERIFICATION SUCCESSFUL"
    echo "├─ Postgres running and healthy"
    echo "├─ Migrations applied successfully"
    echo "├─ Backend started and healthy"
    echo "├─ Smoke test passed"
    echo "└─ Database evidence verified"
    echo ""
    echo "Results saved to: $ARTIFACTS_DIR/"
    echo ""
    exit 0
else
    echo "❌ LEVEL_3 SMOKE TEST FAILED"
    echo "================================================================================"
    echo ""
    echo "VERIFICATION FAILED"

    if [ $SMOKE_EXIT_CODE -ne 0 ]; then
        echo "├─ ❌ Smoke test failed"
    else
        echo "├─ ✅ Smoke test passed"
    fi

    if [ $DB_VERIFY_EXIT_CODE -ne 0 ]; then
        echo "├─ ❌ Database verification failed"
    else
        echo "├─ ✅ Database evidence verified"
    fi

    echo "└─ Check logs in: $ARTIFACTS_DIR/"
    echo ""
    echo "Recent logs:"
    echo ""
    tail -30 "$ARTIFACTS_DIR/smoke_test.log"
    echo ""
    exit 1
fi
