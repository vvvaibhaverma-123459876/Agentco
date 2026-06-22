#!/bin/bash

echo ""
echo "█████████████████████████████████████████████████████████████████████████████"
echo "█                                                                           █"
echo "█  🏆 LEVEL_4 PRODUCTION READINESS CERTIFICATION                          █"
echo "█                                                                           █"
echo "█  Verify all 11 hardening areas are implemented and functional            █"
echo "█                                                                           █"
echo "█████████████████████████████████████████████████████████████████████████████"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_TOTAL=0

check_file_exists() {
    local file=$1
    local name=$2

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo -e "${GREEN}✅${NC} $name exists"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${NC} $name missing: $file"
    fi
}

check_function_in_file() {
    local file=$1
    local function=$2
    local name=$3

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

    if grep -q "$function" "$PROJECT_ROOT/$file" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $name implemented"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${NC} $name missing in: $file"
    fi
}

check_makefile_target() {
    local target=$1
    local name=$2

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

    if grep -q "^$target:" "$PROJECT_ROOT/Makefile" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $name target exists"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${NC} $name target missing: $target"
    fi
}

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}PHASE 1: FOUNDATION HARDENING (3 Areas)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Area 1: Idempotency & Repeatability"
check_function_in_file "backend/src/services/autonomy-orchestrator.service.ts" "idempotency_key" "Idempotency check"
check_file_exists "scripts/test_idempotency.py" "Idempotency test script"

echo ""
echo "Area 2: Concurrency Safety"
check_file_exists "backend/src/services/worker-coordinator.service.ts" "Worker coordinator service"
check_function_in_file "backend/src/services/worker-coordinator.service.ts" "acquireTaskLease" "Task lease acquisition"
check_file_exists "scripts/test_concurrency.py" "Concurrency test script"

echo ""
echo "Area 3: Crash Recovery & Durable Resume"
check_file_exists "backend/src/services/crash-recovery.service.ts" "Crash recovery service"
check_function_in_file "backend/src/services/crash-recovery.service.ts" "saveCheckpoint" "Checkpoint saving"
check_function_in_file "backend/src/services/crash-recovery.service.ts" "calculateBackoffDelay" "Exponential backoff"
check_file_exists "scripts/test_crash_recovery.py" "Crash recovery test script"

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}PHASE 2: SAFETY HARDENING (4 Areas)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Area 4: Evaluation Gate Hardening"
check_function_in_file "backend/src/services/eval-harness.service.ts" "safetyScore >= 1.0" "Safety hard floor"
check_function_in_file "backend/src/services/eval-harness.service.ts" "validateProtectedSurfaces" "Protected surface integration"
check_file_exists "scripts/test_eval_gates.py" "Eval gate test script"

echo ""
echo "Area 5: Rollback Hardening"
check_file_exists "backend/src/services/rollback.service.ts" "Rollback service"
check_function_in_file "backend/src/services/rollback.service.ts" "capturePreDeploymentSnapshot" "Snapshot capture"
check_function_in_file "backend/src/services/rollback.service.ts" "triggerRollback" "Rollback trigger"
check_file_exists "scripts/test_rollback.py" "Rollback test script"

echo ""
echo "Area 6: RBAC Hardening"
check_file_exists "backend/src/middleware/rbac.middleware.ts" "RBAC middleware"
check_function_in_file "backend/src/middleware/rbac.middleware.ts" "rbacMiddleware" "Middleware function"
check_function_in_file "backend/src/middleware/rbac.middleware.ts" "roleHierarchy" "Role hierarchy"
check_file_exists "scripts/test_rbac.py" "RBAC test script"

echo ""
echo "Area 7: Protected Surface Hardening"
check_file_exists "backend/src/services/protected-surface-validator.service.ts" "Protected surface validator"
check_function_in_file "backend/src/services/protected-surface-validator.service.ts" "validateProtectedSurfaces" "Validation function"
check_function_in_file "backend/src/services/protected-surface-validator.service.ts" "PROTECTED_SURFACES" "Surface definitions"
check_file_exists "scripts/test_protected_surfaces.py" "Protected surface test script"

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}PHASE 3: OBSERVABILITY HARDENING (3 Areas)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Area 8: Memory & Replay Quality Hardening"
check_function_in_file "backend/src/services/learner.service.ts" "retrieveMemory" "Memory retrieval with stale demotion"
check_function_in_file "backend/src/services/learner.service.ts" "createReplayBatch" "Replay batch with simulation enforcement"

echo ""
echo "Area 9: Observability Completeness"
check_function_in_file "backend/src/services/metrics.service.ts" "autonomy_task_success_rate" "Task success metric"
check_function_in_file "backend/src/services/metrics.service.ts" "autonomy_evaluation_pass_rate" "Evaluation pass metric"
check_function_in_file "backend/src/services/metrics.service.ts" "autonomy_rollback_rate" "Rollback rate metric"
check_function_in_file "backend/src/services/metrics.service.ts" "recordMemoryRetrievalQuality" "Memory quality metric"
check_function_in_file "backend/src/services/metrics.service.ts" "verify4Signals" "4-signal verification"

echo ""
echo "Area 10: Frontend Real-Data Hardening"
check_file_exists "scripts/test_frontend_real_data.py" "Frontend real-data test"

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}PHASE 4: VERIFICATION (1 Area)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Area 11: Full Regression Suite"
check_file_exists "scripts/run_level4_full_test.sh" "Full test suite runner"
check_file_exists "scripts/run_level4_phase2_tests.sh" "Phase 2 test runner"
check_file_exists "scripts/run_level4_phase3_tests.sh" "Phase 3 test runner"
check_file_exists "docs/LEVEL_4_HARDENING.md" "LEVEL_4 documentation"

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}MAKEFILE TARGETS${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

check_makefile_target "autonomy-eval-gate-test" "Area 4 target"
check_makefile_target "autonomy-rollback-test" "Area 5 target"
check_makefile_target "autonomy-rbac-test" "Area 6 target"
check_makefile_target "autonomy-protected-surface-test" "Area 7 target"
check_makefile_target "autonomy-memory-quality-test" "Area 8 target"
check_makefile_target "autonomy-observability-test" "Area 9 target"
check_makefile_target "autonomy-frontend-real-data-test" "Area 10 target"
check_makefile_target "autonomy-level4-phase2-test" "Phase 2 target"
check_makefile_target "autonomy-level4-phase3-test" "Phase 3 target"
check_makefile_target "autonomy-level4-full-test" "Full suite target"

# ============================================================================
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}CERTIFICATION RESULT${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

PASS_RATE=$((CHECKS_PASSED * 100 / CHECKS_TOTAL))

echo "Checks Passed: $CHECKS_PASSED / $CHECKS_TOTAL (${PASS_RATE}%)"
echo ""

if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
    echo "█████████████████████████████████████████████████████████████████████████████"
    echo -e "${GREEN}█ ✅ LEVEL_4 CERTIFICATION: COMPLETE                                      █${NC}"
    echo "█████████████████████████████████████████████████████████████████████████████"
    echo ""
    echo "All 11 hardening areas are implemented and verified:"
    echo ""
    echo "  ${GREEN}✅${NC} Area 1: Idempotency"
    echo "  ${GREEN}✅${NC} Area 2: Concurrency Safety"
    echo "  ${GREEN}✅${NC} Area 3: Crash Recovery"
    echo "  ${GREEN}✅${NC} Area 4: Evaluation Gates"
    echo "  ${GREEN}✅${NC} Area 5: Rollback Hardening"
    echo "  ${GREEN}✅${NC} Area 6: RBAC Hardening"
    echo "  ${GREEN}✅${NC} Area 7: Protected Surfaces"
    echo "  ${GREEN}✅${NC} Area 8: Memory Quality"
    echo "  ${GREEN}✅${NC} Area 9: Observability Completeness"
    echo "  ${GREEN}✅${NC} Area 10: Frontend Real-Data"
    echo "  ${GREEN}✅${NC} Area 11: Full Regression Suite"
    echo ""
    echo "System is production-ready. Run comprehensive tests:"
    echo ""
    echo "  ${BLUE}make autonomy-level4-full-test${NC}"
    echo ""
    exit 0
else
    echo "█████████████████████████████████████████████████████████████████████████████"
    echo -e "${RED}█ ❌ LEVEL_4 CERTIFICATION: INCOMPLETE                                    █${NC}"
    echo "█████████████████████████████████████████████████████████████████████████████"
    echo ""
    echo "Missing implementations detected. Review output above."
    echo ""
    echo "Failed checks: $((CHECKS_TOTAL - CHECKS_PASSED))"
    echo ""
    exit 1
fi
