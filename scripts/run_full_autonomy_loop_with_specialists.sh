#!/bin/bash
# Full Autonomy Loop with Specialist Delegation
# ============================================
# Complete end-to-end test of the autonomy system with 17 specialists.
#
# Prerequisites:
# - PostgreSQL running locally (port 5432)
# - All database migrations applied
# - LLM_API_KEY set (OpenAI API key)
# - Node.js and npm installed
# - Python 3.8+ with psycopg2 installed

set -e

echo "=========================================="
echo "Full Autonomy Loop with Specialists"
echo "=========================================="
echo ""

# Check prerequisites
echo "[1/6] Checking prerequisites..."
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL client not found"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Prerequisites found"
echo ""

# Check environment variables
echo "[2/6] Checking environment variables..."
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set"
    echo "   Set it with: export DATABASE_URL='postgresql://user:password@localhost:5432/agentco'"
    exit 1
fi

if [ -z "$LLM_API_KEY" ]; then
    echo "⚠️  LLM_API_KEY not set (will use mock LLM if available)"
fi

echo "✅ Environment variables configured"
echo ""

# Build backend
echo "[3/6] Building backend TypeScript..."
cd backend
npm run build > /dev/null 2>&1
echo "✅ Backend built successfully"
echo ""

# Start backend in background
echo "[4/6] Starting backend server..."
npm start > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
sleep 3  # Wait for server to start

# Test API connectivity
echo "[5/6] Testing API connectivity..."
if curl -s http://localhost:3001/health > /dev/null 2>&1; then
    echo "✅ API is responding"
else
    echo "❌ API not responding on port 3001"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo ""

# Run autonomy loop
echo "[6/6] Running autonomy action loop with specialist delegation..."
echo ""
echo "Goal: 'Research the latest advancements in autonomous agents'"
echo "Expected behavior:"
echo "  - Planner evaluates if specialist needed"
echo "  - If evidence found, recommends background_researcher specialist"
echo "  - Spawns subprocess with HTTP server"
echo "  - Executes WEB_SEARCH and FETCH_PAGE actions"
echo "  - Persists results to database"
echo "  - Next iteration uses specialist findings for claim generation"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:3001/api/autonomy/action-loop \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Research the latest advancements in autonomous agents and their real-world applications",
    "maxIterations": 15,
    "idempotencyKey": "full-autonomy-test-'$(date +%s)'"
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Parse results
GOAL_ID=$(echo "$RESPONSE" | grep -o '"goalId":"[^"]*' | cut -d'"' -f4 | head -1)
if [ -n "$GOAL_ID" ]; then
    echo "✅ Autonomy loop completed"
    echo "   Goal ID: $GOAL_ID"
    echo ""
    echo "Checking results..."

    # Query evidence collected
    EVIDENCE_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM autonomy_evidence WHERE goal_id='$GOAL_ID';" 2>/dev/null || echo "?")
    CLAIMS_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM autonomy_claims WHERE goal_id='$GOAL_ID';" 2>/dev/null || echo "?")
    ACTIONS_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM autonomy_actions WHERE goal_id='$GOAL_ID';" 2>/dev/null || echo "?")

    echo "   Evidence collected: $EVIDENCE_COUNT"
    echo "   Claims generated: $CLAIMS_COUNT"
    echo "   Actions executed: $ACTIONS_COUNT"
    echo ""

    # Check for specialist spawning
    SPECIALIST_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM autonomy_team_activations WHERE parent_goal_id='$GOAL_ID';" 2>/dev/null || echo "?")
    echo "   Specialists spawned: $SPECIALIST_COUNT"
    echo ""

    if [ "$SPECIALIST_COUNT" -gt 0 ]; then
        echo "✅ Specialist delegation successful!"
        psql $DATABASE_URL -c "SELECT specialist_id, specialist_role, status FROM autonomy_team_activations WHERE parent_goal_id='$GOAL_ID';" 2>/dev/null || true
    fi
else
    echo "❌ Autonomy loop failed"
    echo "Check /tmp/backend.log for details"
fi

echo ""
echo "Cleaning up..."
kill $BACKEND_PID 2>/dev/null || true
echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
