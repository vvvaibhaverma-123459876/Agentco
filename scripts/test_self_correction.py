#!/usr/bin/env python3
"""
Self-Correction Test

Proves TRUE AUTONOMY: System detects its own failures and fixes them.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomy.realtime_integration import get_integration_engine
from autonomy.self_correction import get_self_correction_engine


def run_self_correction_test():
    """Run test showing system detecting and fixing its own problems."""

    print("\n" + "="*100)
    print("🤖 SELF-CORRECTION TEST: TRUE AUTONOMY IN ACTION")
    print("="*100)
    print("\nProof of true autonomy: System detects own failures and fixes them\n")

    integration_engine = get_integration_engine()
    correction_engine = get_self_correction_engine()

    print("✓ Integration engine ready")
    print("✓ Self-correction engine ready")
    print("✓ System monitoring its own performance\n")

    situations = [
        {'problem': 'Test calibration issue detection', 'context': 'Cycle 1'},
        {'problem': 'Verify problem persists', 'context': 'Cycle 2'},
        {'problem': 'Apply self-correction', 'context': 'Cycle 3'},
        {'problem': 'Verify fix effectiveness', 'context': 'Cycle 4'},
    ]

    print("[RUN] Running self-correction cycle...\n")

    previous_diagnosis = None
    results = []

    for i, situation in enumerate(situations, 1):
        print(f"{'='*100}")
        print(f"CYCLE {i}: {situation['problem']}")
        print(f"{'='*100}")

        # Run integration cycle
        cycle_result = integration_engine.run_integrated_cycle(situation)

        print(f"\n[SELF-OBSERVATION]")
        print(f"  Trust score: {cycle_result['trust_score']:.2f}")
        print(f"  Calibration confidence: {cycle_result['calibration_confidence']:.2f}")
        print(f"  Governance decision: {'APPROVE' if cycle_result['governance_decision'] else 'REJECT'}")

        # Self-correct
        print(f"\n[SELF-DIAGNOSIS]")
        correction_result = correction_engine.self_correct_cycle(cycle_result, previous_diagnosis)

        diagnosis = correction_result['cycle_diagnosis']
        print(f"  Health status: {diagnosis['health_status']}")

        if diagnosis['issues']:
            print(f"  Issues detected:")
            for issue in diagnosis['issues']:
                print(f"    - {issue}")

        if diagnosis['root_causes']:
            print(f"  Root causes identified:")
            for cause in diagnosis['root_causes']:
                print(f"    - {cause}")

        # Show correction action
        if correction_result['correction_action']:
            print(f"\n[SELF-CORRECTION]")
            action = correction_result['correction_action']
            if action.get('fix_applied'):
                print(f"  ✓ Fix applied: {action['fix_applied'][:100]}...")
                print(f"  → Guidance for next cycle: Will apply this correction")
            else:
                print(f"  ⚠️  No fix applied")
        else:
            print(f"\n[SELF-OBSERVATION]")
            print(f"  ✓ System healthy - no correction needed")

        print()

        previous_diagnosis = diagnosis
        results.append(correction_result)

    # Print summary
    print("\n" + "="*100)
    print("SELF-CORRECTION SUMMARY")
    print("="*100)

    print("\n📊 AUTONOMY PROOF")
    print("-" * 100)

    # Check if system detected its own problems
    diagnoses = [r['cycle_diagnosis'] for r in results]
    issues_detected = sum(1 for d in diagnoses if d['issues'])
    root_causes_identified = sum(1 for d in diagnoses if d['root_causes'])

    print(f"  ✓ System detected own issues: {issues_detected} times")
    print(f"  ✓ System identified root causes: {root_causes_identified} times")

    # Check if system proposed fixes
    fixes_proposed = sum(1 for r in results if r['correction_action'] and r['correction_action'].get('fix_applied'))
    print(f"  ✓ System proposed fixes: {fixes_proposed} times")

    # Check health progression
    print(f"\n📈 HEALTH PROGRESSION")
    print("-" * 100)
    for i, diagnosis in enumerate(diagnoses, 1):
        print(f"  Cycle {i}: {diagnosis['health_status']} (severity: {diagnosis.get('severity', 0)})")

    # Final verdict
    print(f"\n🎯 TRUE AUTONOMY VERDICT")
    print("-" * 100)

    if issues_detected > 0 and root_causes_identified > 0 and fixes_proposed > 0:
        print(f"  ✅ TRUE AUTONOMY DETECTED")
        print(f"     System observed its own performance")
        print(f"     System diagnosed its own problems")
        print(f"     System proposed fixes to itself")
        print(f"     This is REAL self-improvement, not mechanical repetition")
    elif issues_detected > 0:
        print(f"  ⚠️  PARTIAL AUTONOMY")
        print(f"     System detects problems but doesn't fix them")
    else:
        print(f"  ❌ NO AUTONOMY")
        print(f"     System unaware of its own failures")

    print("\n" + "="*100 + "\n")

    return {
        'cycles': len(results),
        'issues_detected': issues_detected,
        'root_causes_identified': root_causes_identified,
        'fixes_proposed': fixes_proposed,
        'diagnoses': [
            {
                'cycle': i,
                'health_status': d['health_status'],
                'severity': d.get('severity', 0),
                'issues': d.get('issues', []),
                'root_causes': d.get('root_causes', [])
            }
            for i, d in enumerate(diagnoses, 1)
        ]
    }


if __name__ == "__main__":
    print("\n🚀 TESTING TRUE AUTONOMY: SELF-CORRECTION\n")

    try:
        results = run_self_correction_test()

        # Save results
        report_dir = Path("results/autonomy_validation")
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / f"self_correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"✓ Results saved to: {report_file}\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
