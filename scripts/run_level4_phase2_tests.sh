#!/bin/bash
set -e

echo ""
echo "================================================================================"
echo "🎯 LEVEL_4 Phase 2: Safety Hardening Full Test Suite"
echo "================================================================================"
echo ""
echo "Running comprehensive tests for Areas 4-7:"
echo "  Area 4: Evaluation Gate Hardening"
echo "  Area 5: Rollback Hardening"
echo "  Area 6: RBAC Hardening"
echo "  Area 7: Protected Surface Hardening"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Track results
PASSED=0
FAILED=0
TOTAL=0

run_test() {
    local test_name="$1"
    local test_script="$2"

    TOTAL=$((TOTAL + 1))
    echo ""
    echo "───────────────────────────────────────────────────────────────────────────"
    echo "Running: $test_name"
    echo "───────────────────────────────────────────────────────────────────────────"

    if python3 "$test_script" 2>&1; then
        PASSED=$((PASSED + 1))
        echo "✅ $test_name PASSED"
    else
        FAILED=$((FAILED + 1))
        echo "❌ $test_name FAILED"
    fi
}

# Run all Phase 2 tests
run_test "Area 4: Eval Gate Hardening" "$SCRIPT_DIR/test_eval_gates.py"
run_test "Area 5: Rollback Hardening" "$SCRIPT_DIR/test_rollback.py"
run_test "Area 6: RBAC Hardening" "$SCRIPT_DIR/test_rbac.py"
run_test "Area 7: Protected Surface Hardening" "$SCRIPT_DIR/test_protected_surfaces.py"

# Summary
echo ""
echo "================================================================================"
echo "📊 LEVEL_4 Phase 2 Test Summary"
echo "================================================================================"
echo ""
echo "Results: $PASSED/$TOTAL tests passed"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ PHASE 2 HARDENING COMPLETE"
    echo ""
    echo "All safety hardening tests passed:"
    echo "  ✅ Area 4: Evaluation gates working (safety hard floor, protected surfaces)"
    echo "  ✅ Area 5: Rollback service operational (atomic updates, audit trail)"
    echo "  ✅ Area 6: RBAC enforced (role-based access control)"
    echo "  ✅ Area 7: Protected surfaces blocked (calibration, resolution, audit, rbac, governance, safety, policy)"
    echo ""
    echo "Next Steps:"
    echo "  1. Commit Phase 2 implementation: git commit -m 'feat: LEVEL_4 Phase 2 Areas 4-7'"
    echo "  2. Proceed to Phase 3: Observability Hardening (Areas 8-10)"
    echo ""
    exit 0
else
    echo "❌ PHASE 2 HARDENING INCOMPLETE"
    echo ""
    echo "Failed tests: $FAILED"
    echo ""
    echo "Remediation:"
    echo "  1. Review test output above for failures"
    echo "  2. Check API endpoints are properly wired"
    echo "  3. Verify database schema matches expectations"
    echo "  4. Run individual tests for debugging"
    echo ""
    exit 1
fi
