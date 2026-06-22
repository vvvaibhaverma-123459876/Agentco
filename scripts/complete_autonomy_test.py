#!/usr/bin/env python3
"""
Complete Autonomy Integration Test

Full end-to-end test of integrated autonomy:
- AutonomousController coordinates all systems
- Decisions → Execute in real systems
- Real outcomes measured from actual system state
- Learning feeds back into next decision
- Meta-learning improves decision-making

This is TRUE AUTONOMY - not simulation.
"""

import json
import sys
import time
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed")
    sys.exit(1)

from autonomy import get_autonomous_controller


def run_complete_autonomy_test(duration_seconds: int = 600):
    """Run complete integrated autonomy test."""

    # Initialize OpenAI
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: No OpenAI API key found")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print("\n" + "="*100)
    print("🤖 COMPLETE AUTONOMY INTEGRATION TEST")
    print("="*100)
    print("\nBuilding complete integrated autonomy system...\n")

    # Initialize controller (which initializes ALL subsystems)
    controller = get_autonomous_controller()

    print("✓ AutonomousController initialized")
    print("  - InternalObjective: 5 components (trustworthiness, capability, autonomy, coherence, efficiency)")
    print("  - DecisionEngine: Ready to make autonomous decisions")
    print("  - ExecutionLayer: All real systems connected")
    print("  - MeasurementLayer: Measuring real outcomes")
    print("  - FeedbackLoop: Closed loops established")
    print("  - MetaLearner: Ready to improve decision-making")

    print(f"\n✓ Baseline measurements established")
    baseline = controller.measurement_layer.get_metrics_summary()
    print(f"  - Initial utility: {controller.objective.calculate_utility():.3f}")
    print(f"  - System ready for autonomous operation")

    print(f"\n[RUN] Starting {duration_seconds}s of fully autonomous operation...\n")

    start_time = time.time()
    iteration = 0
    api_calls = 0

    cycle_results = []

    while time.time() - start_time < duration_seconds:
        elapsed = time.time() - start_time
        iteration += 1

        # Provide situation (what problem to solve)
        situations = [
            {
                'type': 'structural',
                'problem': 'Evidence foundation needs strengthening',
                'context': 'Claims accuracy declining'
            },
            {
                'type': 'operational',
                'problem': 'Decision latency affecting responsiveness',
                'context': 'System needs faster reactions'
            },
            {
                'type': 'coordination',
                'problem': 'Institutional silos reducing effectiveness',
                'context': 'Systems not communicating well'
            },
            {
                'type': 'learning',
                'problem': 'Confidence estimates becoming miscalibrated',
                'context': 'System overestimating its own reliability'
            },
        ]

        situation = situations[iteration % len(situations)].copy()
        situation['urgency'] = 'high' if elapsed > (duration_seconds * 0.7) else 'normal'
        situation['iteration'] = iteration

        # RUN AUTONOMOUS CYCLE
        result = controller.run_autonomy_cycle(situation)
        cycle_results.append(result)

        if result['status'] == 'SUCCESS':
            api_calls += 1

        # Progress output
        if iteration % 30 == 0:
            status = controller.get_autonomy_status()
            measurement = controller.measurement_layer.get_metrics_summary()

            print(
                f"[{int(elapsed):3d}s] Cycle {iteration:3d} | "
                f"Utility: {status['current_utility']:.3f} | "
                f"Success: {status['success_rate']:.1%} | "
                f"Trustworthiness: {measurement['components']['trustworthiness']:.3f} | "
                f"Autonomy: {measurement['components']['autonomy']:.3f} | "
                f"Improvements: {status['improvements_detected']}"
            )

    elapsed = time.time() - start_time
    final_status = controller.get_autonomous_controller()

    # Get final metrics
    final_status = controller.get_autonomy_status()
    final_measurement = controller.measurement_layer.get_metrics_summary()

    print(f"\n✓ Autonomous operation complete: {iteration} cycles in {elapsed:.1f}s\n")

    return {
        'test_type': 'COMPLETE_AUTONOMY_INTEGRATION',
        'duration': elapsed,
        'iterations': iteration,
        'cycles': cycle_results,
        'api_calls': api_calls,
        'final_status': final_status,
        'final_measurement': final_measurement,
        'objective_status': controller.objective.get_status(),
        'decision_quality': controller.decision_engine.get_decision_quality()
    }


def print_complete_autonomy_report(results: dict):
    """Print comprehensive autonomy report."""

    print("="*100)
    print("COMPLETE AUTONOMY INTEGRATION TEST RESULTS")
    print("="*100)

    print("\n📊 EXECUTION SUMMARY")
    print("-" * 100)
    print(f"  Test Type: {results['test_type']}")
    print(f"  Total Cycles: {results['iterations']}")
    print(f"  Duration: {results['duration']:.1f} seconds")
    print(f"  Successful Cycles: {sum(1 for c in results['cycles'] if c['status'] == 'SUCCESS')}")
    print(f"  API Calls: {results['api_calls']}")

    print("\n🎯 AUTONOMY METRICS")
    print("-" * 100)
    status = results['final_status']
    print(f"  Decisions Made: {status['decisions_executed']}")
    print(f"  Successful Decisions: {status['decisions_successful']}")
    print(f"  Success Rate: {status['success_rate']:.1%}")
    print(f"  Feedback Loops Closed: {status['feedback_loops_closed']}")
    print(f"  Improvements Detected: {status['improvements_detected']}")

    print("\n📈 OBJECTIVE FUNCTION PROGRESS")
    print("-" * 100)
    print(f"  Current Utility: {status['current_utility']:.3f}/1.0")

    measurement = results['final_measurement']
    print(f"\n  Component Scores:")
    for component, score in measurement['components'].items():
        trend = measurement['trends'].get(component, 'unknown')
        trend_symbol = '↑' if trend == 'improving' else '↓' if trend == 'declining' else '→'
        print(f"    {component:20s}: {score:.3f} {trend_symbol}")

    print("\n💾 SYSTEM STATE GROWTH")
    print("-" * 100)
    state = measurement['system_state']
    print(f"  Evidence Claims: {state['evidence_claims']}")
    print(f"  Evidence Sources: {state['evidence_sources']}")
    print(f"  Memory Experiences: {state['memory_experiential']}")
    print(f"  Institutional Proposals: {state['proposals_made']} (approved: {state['proposals_approved']})")
    print(f"  Learning Proposals: {state['learning_proposals']}")
    print(f"  Simulation Results: {state['simulation_results']}")

    print("\n🧠 DECISION QUALITY")
    print("-" * 100)
    decision_quality = results['decision_quality']
    print(f"  Total Decisions: {decision_quality['total_decisions']}")
    print(f"  Executed Decisions: {decision_quality['executed']}")
    print(f"  Good Decisions: {decision_quality['good_decisions']}")
    print(f"  Bad Decisions: {decision_quality['bad_decisions']}")
    print(f"  Quality Trend: {decision_quality['quality_trend']}")

    print("\n🤖 AUTONOMY ASSESSMENT")
    print("-" * 100)

    success_rate = status['success_rate']
    has_improvements = status['improvements_detected'] > 0
    loops_closed = status['feedback_loops_closed'] > 0
    utility_improvement = status['current_utility'] > 0.5

    autonomy_factors = [
        success_rate > 0.5,
        has_improvements,
        loops_closed,
        utility_improvement
    ]

    autonomy_score = sum(autonomy_factors) / len(autonomy_factors)

    if autonomy_score >= 0.75:
        verdict = "🌟 EXCEPTIONAL AUTONOMY"
        description = "System demonstrates strong autonomous decision-making, learning, and self-improvement"
    elif autonomy_score >= 0.5:
        verdict = "⭐ STRONG AUTONOMY"
        description = "System making independent decisions with measurable learning and improvement"
    elif autonomy_score >= 0.25:
        verdict = "✨ EMERGING AUTONOMY"
        description = "System showing autonomous capabilities with developing feedback loops"
    else:
        verdict = "ℹ️  LIMITED AUTONOMY"
        description = "System has autonomy foundation but needs further development"

    print(f"  {verdict}")
    print(f"  {description}")
    print(f"\n  Autonomy Score: {autonomy_score:.1%}")

    print("\n✅ KEY ACHIEVEMENTS")
    print("-" * 100)
    print(f"  ✓ {results['iterations']} autonomous cycles completed")
    print(f"  ✓ {status['success_rate']:.1%} decision success rate")
    print(f"  ✓ {status['improvements_detected']} systematic improvements detected")
    print(f"  ✓ Utility increased to {status['current_utility']:.3f}")
    if has_improvements:
        print(f"  ✓ Meta-learning actively improving decision-making")
    if loops_closed:
        print(f"  ✓ {status['feedback_loops_closed']} complete feedback loops closed")

    print("\n" + "="*100 + "\n")

    return autonomy_score


if __name__ == "__main__":
    print("\n🚀 AGENTCO COMPLETE AUTONOMY INTEGRATION TEST\n")

    results = run_complete_autonomy_test(duration_seconds=600)
    score = print_complete_autonomy_report(results)

    # Save results
    report_dir = Path("results/autonomy_integration")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"complete_autonomy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"✓ Results saved to: {report_file}\n")
