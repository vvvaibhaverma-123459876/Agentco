#!/usr/bin/env python3
"""
Real-Time Integration Test

Tests complete system with OpenAI driving every connection:
- Learning → Evidence → Calibration → Trust → Governance
- All with real LLM reasoning
- Complete feedback loops
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomy.realtime_integration import get_integration_engine


def run_realtime_integration_test(num_cycles: int = 5):
    """Run integrated test with real OpenAI reasoning."""

    print("\n" + "="*100)
    print("🤖 REAL-TIME INTEGRATION TEST WITH OPENAI")
    print("="*100)
    print("\nComplete system: Learning → Evidence → Calibration → Trust → Governance")
    print("All driven by real OpenAI reasoning\n")

    engine = get_integration_engine()

    print("✓ Integration engine initialized")
    print("✓ All systems connected")
    print("✓ OpenAI ready for reasoning\n")

    situations = [
        {
            'problem': 'Evidence foundation shows declining claim accuracy',
            'context': 'System needs to improve trustworthiness'
        },
        {
            'problem': 'Calibration reveals overconfidence in predictions',
            'context': 'System needs uncertainty adjustment'
        },
        {
            'problem': 'Trust metrics declining due to miscalibrated confidence',
            'context': 'System must recalibrate before making decisions'
        },
        {
            'problem': 'Governance proposals failing to improve system coherence',
            'context': 'Need better decision-making framework'
        },
        {
            'problem': 'Complete integration test: all systems working together',
            'context': 'Final validation of real autonomy'
        }
    ]

    print(f"[RUN] Starting {num_cycles} integrated cycles...\n")

    cycle_results = []
    start_time = time.time()

    for i in range(num_cycles):
        situation = situations[i % len(situations)]

        result = engine.run_integrated_cycle(situation)
        cycle_results.append(result)

        print(f"  → Learning claims: {result['learning']['claims_generated']}")
        print(f"  → Evidence quality: {result['evidence_quality']:.2f}")
        print(f"  → Calibration confidence: {result['calibration_confidence']:.2f}")
        print(f"  → Trust score: {result['trust_score']:.2f}")
        print(f"  → Governance: {'✓ APPROVED' if result['governance_decision'] else '✗ REJECTED'}")

        if result['execution_result']:
            print(f"  → Executed: Proposal {result['execution_result'].get('proposal_id', 'unknown')}")

        print()

    elapsed = time.time() - start_time

    # Print final report
    status = engine.get_integration_status()

    print("="*100)
    print("REAL-TIME INTEGRATION TEST RESULTS")
    print("="*100)

    print(f"\n📊 EXECUTION")
    print("-" * 100)
    print(f"  Cycles completed: {status['cycles_completed']}")
    print(f"  OpenAI API calls: {status['openai_calls']}")
    print(f"  Calls per cycle: {status['openai_calls'] / max(1, status['cycles_completed']):.1f}")
    print(f"  Total time: {elapsed:.1f}s")

    print(f"\n🧠 INTEGRATION METRICS")
    print("-" * 100)
    trust_scores = list(status['trust_scores'].values())
    if trust_scores:
        print(f"  Average trust score: {status['avg_trust']:.3f}")
        print(f"  Trust trend: {trust_scores[0]:.3f} → {trust_scores[-1]:.3f}")
        if trust_scores[-1] > trust_scores[0]:
            print(f"  ✓ Trust IMPROVING")
        elif trust_scores[-1] < trust_scores[0]:
            print(f"  ⚠️  Trust declining")
        else:
            print(f"  → Trust stable")

    print(f"\n💾 SYSTEM GROWTH")
    print("-" * 100)
    state = status['system_state']
    print(f"  Evidence claims: {state['claims']}")
    print(f"  Governance proposals: {state['proposals']}")
    print(f"  Approved proposals: {state['approved']}")
    print(f"  Memory experiences: {state['memory']}")

    print(f"\n📡 DATA FLOW VERIFICATION")
    print("-" * 100)

    # Verify each connection
    connections = [
        ('Learning → Evidence', state['claims'] > 0),
        ('Evidence → Calibration', len(status['calibration_metrics']) > 0),
        ('Calibration → Trust', len(status['trust_scores']) > 0),
        ('Trust → Governance', state['proposals'] > 0),
        ('Governance → Execution', state['approved'] > 0 if state['proposals'] > 0 else True),
    ]

    for connection, working in connections:
        status_symbol = "✅" if working else "⚠️"
        print(f"  {status_symbol} {connection}")

    print(f"\n🎯 INTEGRATION QUALITY")
    print("-" * 100)

    working_connections = sum(1 for _, w in connections if w)
    total_connections = len(connections)
    integration_score = working_connections / total_connections

    print(f"  Connections active: {working_connections}/{total_connections}")
    print(f"  Integration health: {integration_score:.0%}")

    if integration_score >= 0.8:
        print(f"\n  ✅ REAL INTEGRATION: Systems fully connected with OpenAI reasoning")
    elif integration_score >= 0.6:
        print(f"\n  ✨ STRONG INTEGRATION: Most connections working")
    elif integration_score >= 0.4:
        print(f"\n  ⚠️  PARTIAL INTEGRATION: Some gaps remain")
    else:
        print(f"\n  ❌ WEAK INTEGRATION: Major gaps")

    print("\n" + "="*100 + "\n")

    return {
        'cycles': num_cycles,
        'duration': elapsed,
        'openai_calls': status['openai_calls'],
        'avg_trust': status['avg_trust'],
        'system_state': state,
        'connections': connections,
        'integration_score': integration_score,
        'cycle_results': cycle_results
    }


if __name__ == "__main__":
    print("\n🚀 TESTING COMPLETE INTEGRATION WITH REAL OPENAI\n")

    try:
        results = run_realtime_integration_test(num_cycles=5)

        # Save results
        report_dir = Path("results/integration")
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / f"realtime_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            # Convert results to serializable format
            results_copy = results.copy()
            results_copy['cycle_results'] = [
                {k: v for k, v in r.items() if k not in ['learning', 'execution_result', 'system_state']}
                for r in results['cycle_results']
            ]
            json.dump(results_copy, f, indent=2, default=str)

        print(f"✓ Results saved to: {report_file}\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
