#!/usr/bin/env python3
"""
AGENTCO REAL-WORLD 2-MINUTE UNCONSTRAINED AUTONOMY RUN
======================================================

Complete observation of AgentCo operating freely in the real world
with real OpenAI API access for 2 minutes.

NO constraints. NO guidance. FULL autonomy.
Capture everything that happens.

Run with: LLM_API_KEY=your-key-here python3 autonomy_real_world_2min_unconstrained.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, '/Users/Zet/Agentco/backend')
sys.path.insert(0, '/Users/Zet/Agentco')

def run_unconstrained_autonomy():
    """
    Run AgentCo completely unconstrained for 2 minutes.
    Observe and log everything.
    """

    print("\n" + "="*70)
    print("  AGENTCO REAL-WORLD 2-MINUTE UNCONSTRAINED RUN")
    print("  No constraints. No guidance. Pure autonomy observation.")
    print("="*70 + "\n")

    # Check for API key
    api_key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERROR: No API key found")
        print("   Set LLM_API_KEY or OPENAI_API_KEY environment variable")
        print("\n   Example:")
        print("   export LLM_API_KEY='sk-...'")
        print("   python3 autonomy_real_world_2min_unconstrained.py")
        return False

    print(f"✅ API Key: Found ({len(api_key)} chars)")
    print(f"   Using: {'LLM_API_KEY' if os.environ.get('LLM_API_KEY') else 'OPENAI_API_KEY'}")

    # Start time
    start_time = time.time()
    timeout = 2 * 60  # 2 minutes

    print(f"\n⏱️  Test Duration: {timeout} seconds (2 minutes)")
    print(f"   Start Time: {datetime.now().isoformat()}")
    print("\n" + "="*70)
    print("  LAUNCHING ORCHESTRATOR...")
    print("="*70 + "\n")

    try:
        # Import orchestrator
        from backend.src.services.autonomy_orchestrator import AutonomyOrchestratorService

        orchestrator = AutonomyOrchestratorService()

        print("✅ Orchestrator initialized")
        print("   Status: Ready for autonomous execution\n")

        # Random goal to let it explore freely
        goals = [
            "Investigate how AI systems learn and adapt to novel situations",
            "Analyze the current state of autonomous agent technology",
            "Research emerging trends in AI safety and alignment",
            "Explore the intersection of machine learning and scientific discovery",
            "Investigate how autonomous systems handle ambiguity and uncertainty",
            "Research the history and future of artificial general intelligence",
            "Analyze real-world applications of autonomous systems in 2026",
            "Investigate how AI systems can improve human decision-making"
        ]

        import random
        goal = random.choice(goals)

        print(f"🎯 Goal (randomly selected for unconstrained exploration):")
        print(f"   \"{goal}\"")
        print(f"\n⏳ Running orchestrator without constraints...")
        print(f"   Max iterations: unlimited (or until timeout/convergence)")
        print("\n" + "-"*70 + "\n")

        # Run autonomy loop with no iteration limit (will be bounded by timeout)
        max_iterations = 1000  # Safety limit

        result = orchestrator.executeAutonomyActionLoop(
            goalText=goal,
            maxIterations=max_iterations,
            idempotencyKey=f"unconstrained_run_{int(start_time)}"
        )

        # Track run time
        elapsed = time.time() - start_time

        print("\n" + "-"*70)
        print("  RUN COMPLETED")
        print("-"*70 + "\n")

        # Display results
        print(f"⏱️  Total Time: {elapsed:.2f} seconds")
        print(f"   Status: {result['status']}")
        print(f"   Goal ID: {result['goalId']}")
        print(f"   Actions Executed: {result['actionsExecuted']}")
        print(f"   Claims Generated: {result['claimsGenerated']}")

        if result.get('reason'):
            print(f"   Termination Reason: {result['reason']}")

        # Detailed analysis
        print("\n" + "="*70)
        print("  DETAILED ANALYSIS")
        print("="*70 + "\n")

        print(f"🔍 Behavior Observations:")
        print(f"   • Autonomy Duration: {elapsed:.2f}s (target: 120s)")
        print(f"   • Autonomy Efficiency: {result['actionsExecuted']/elapsed:.2f} actions/sec")
        print(f"   • Claim Generation Rate: {result['claimsGenerated']/elapsed:.2f} claims/sec")

        if elapsed < 120:
            print(f"\n⚠️  Early Termination: Completed in {elapsed:.2f}s (target: 120s)")
            print(f"   Reason: {result.get('reason', 'Unknown')}")
            print(f"   Actions before termination: {result['actionsExecuted']}")
        else:
            print(f"\n✅ Full 2-minute autonomy run completed")

        # Observations
        print(f"\n📊 System Observations:")
        print(f"   • Total Actions: {result['actionsExecuted']}")
        print(f"   • Claims Generated: {result['claimsGenerated']}")
        print(f"   • Final Status: {result['status']}")

        if result['claimsGenerated'] > 0:
            print(f"   • Avg Claims per Action: {result['claimsGenerated']/result['actionsExecuted']:.2f}")

        # Detect patterns and gaps
        print(f"\n🔎 Autonomy Patterns & Gaps Detected:")

        if result['actionsExecuted'] == 0:
            print(f"   ❌ No actions executed - system may have encountered blocker")
        elif result['actionsExecuted'] < 5:
            print(f"   ⚠️  Very few actions - possible early termination or constraint")
        else:
            print(f"   ✅ Normal action execution rate")

        if result['claimsGenerated'] == 0:
            print(f"   ⚠️  No claims generated - research may not be finding supported claims")
        elif result['claimsGenerated'] < result['actionsExecuted']:
            print(f"   ℹ️  Low claim generation rate ({result['claimsGenerated']}/{result['actionsExecuted']})")
        else:
            print(f"   ✅ Good claim generation")

        # Print raw result
        print(f"\n📋 Raw Result:")
        print(json.dumps(result, indent=2, default=str))

        return True

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print(f"   Make sure you're running from the correct directory")
        return False
    except Exception as e:
        print(f"❌ Error during autonomy run: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    success = run_unconstrained_autonomy()

    print("\n" + "="*70)
    print("  OBSERVATION COMPLETE")
    print("="*70 + "\n")

    if success:
        print("✅ Real-world autonomy observation successful")
    else:
        print("❌ Real-world autonomy observation failed")

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
