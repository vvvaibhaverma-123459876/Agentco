#!/usr/bin/env python3
"""
Run integrated learning layer for 5 minutes.
Uses the newly integrated AutonomousLearningLoop with TypeScript backend bridge.
Captures before/after state showing learning advancement.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


def capture_state(label: str, duration: float = 0) -> dict:
    """Capture current system state."""
    return {
        "timestamp": datetime.now().isoformat(),
        "label": label,
        "duration_seconds": duration,
        "state": {
            "societies": len(society_kernel.societies),
            "institutions": len(society_kernel.institutions),
            "agent_memberships": len(society_kernel.agent_membership),
            "proposals_made": len(society_kernel.proposals),
            "proposals_approved": sum(1 for p in society_kernel.proposals.values() if p.get("status") == "approved"),
            "evidence_claims": len(evidence_kernel.claims),
            "evidence_sources": len(evidence_kernel.sources),
            "evidence_resolutions": len(evidence_kernel.resolutions),
            "memory_experiences": len(memory_kernel.experiential),
            "memory_operational": len(memory_kernel.operational),
            "learning_proposals": len(learning_loop.proposals),
            "learning_proposals_approved": sum(1 for p in learning_loop.proposals if p.status == "approved"),
            "simulation_scenarios": len(world_lab.scenarios),
            "simulation_results": len(world_lab.results),
        }
    }


def run_learning_system(duration_seconds: int):
    """Run the integrated learning system for specified duration."""
    start_time = time.time()
    iteration = 0

    signals = [
        "Strengthen evidence validation through learning",
        "Improve institutional coordination",
        "Enhance decision calibration accuracy",
        "Validate hypotheses systematically",
        "Integrate feedback from past outcomes",
        "Build resilient governance structures",
        "Optimize evidence sourcing",
        "Improve agent decision quality",
        "Enhance trust and confidence measurement",
        "Refine institutional policies",
    ]

    print(f"\n🚀 Running integrated learning system for {duration_seconds} seconds...")
    print("   (Learning loop processes signals, generates insights, proposes improvements)\n")

    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = time.time() - start_time
        signal = signals[iteration % len(signals)]

        # Run learning loop
        result = learning_loop.run(signal, source_uri=f"integrated://signal-{iteration}")

        # Create scenarios
        scenario = world_lab.create_scenario(f"Testing: {signal[:40]}")
        world_lab.run_simulation(scenario.scenario_id)

        # Propose institutional improvements
        if society_kernel.societies:
            for society_id in list(society_kernel.societies.keys()):
                change = {
                    "type": "learning_based",
                    "iteration": iteration,
                    "signal": signal,
                    "claims": len(result.get("claims", [])),
                }
                proposal = society_kernel.propose_structure_change(society_id, change)

                # Approve high-confidence changes (use society proposal ID)
                if proposal and proposal.get("status") == "proposed":
                    proposal_id = proposal.get("proposal_id")
                    if proposal_id:
                        society_kernel.decide(proposal_id, approved=True)

        # Progress (every 10 iterations)
        if iteration % 10 == 0:
            throughput = iteration / elapsed if elapsed > 0 else 0
            print(
                f"[{int(elapsed):2d}s] Iter {iteration:3d} | "
                f"{throughput:6.1f} iter/s | "
                f"Claims: {len(evidence_kernel.claims):3d} | "
                f"Proposals: {len(society_kernel.proposals):3d} | "
                f"Memory: {len(memory_kernel.experiential):4d}"
            )

    elapsed = time.time() - start_time
    throughput = iteration / elapsed if elapsed > 0 else 0

    print(f"\n✓ Learning run complete: {iteration} iterations in {elapsed:.1f}s ({throughput:.1f} iter/s)\n")
    return iteration, throughput


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 90)
    print("AGENTCO INTEGRATED LEARNING: 5-MINUTE RUN")
    print("=" * 90)

    # Initialize systems
    society_kernel = SocietyKernel()
    evidence_kernel = EvidenceKernel()
    memory_kernel = MemoryKernel()
    uncertainty = UncertaintyStack()
    world_lab = WorldLab(evidence_kernel)
    learning_loop = AutonomousLearningLoop(evidence_kernel, memory_kernel, uncertainty)

    # Bootstrap society
    print("\n[SETUP] Initializing institutional structure...")
    inst_gov = society_kernel.create_institution("Governance", "Oversight")
    inst_ev = society_kernel.create_institution("Evidence Bureau", "Evidence")
    inst_learn = society_kernel.create_institution("Learning Institute", "Learning")
    inst_sim = society_kernel.create_institution("World Lab", "Simulation")

    society = society_kernel.create_society(
        "Agentco",
        [inst_gov.institution_id, inst_ev.institution_id, inst_learn.institution_id, inst_sim.institution_id]
    )
    print(f"✓ Created {society.name} with {len(society.institutions)} institutions")

    # Capture initial state
    print("\n[BEFORE] Capturing initial state...")
    before_state = capture_state("BEFORE_5MIN_RUN", 0)
    print("Initial state:")
    for key, val in before_state["state"].items():
        print(f"  {key}: {val}")

    # Run learning system for 5 minutes
    print("\n[RUN] Starting 5-minute learning run...")
    iterations, throughput = run_learning_system(300)  # 300 seconds = 5 minutes

    # Capture final state
    print("[AFTER] Capturing final state...")
    after_state = capture_state("AFTER_5MIN_RUN", 300)
    print("Final state:")
    for key, val in after_state["state"].items():
        print(f"  {key}: {val}")

    # Generate comparison
    print("\n" + "=" * 90)
    print("BEFORE → AFTER COMPARISON")
    print("=" * 90)

    print("\n📊 State Changes:")
    print(f"{'Metric':<30} {'Before':>10} {'After':>10} {'Change':>10}")
    print("-" * 62)

    total_change = 0
    for key in before_state["state"]:
        before_val = before_state["state"][key]
        after_val = after_state["state"][key]
        change = after_val - before_val
        total_change += change

        if change > 0:
            print(f"{key:<30} {before_val:>10} {after_val:>10} +{change:>9}")

    print("\n📈 Performance Metrics:")
    print(f"  Total Iterations: {iterations}")
    print(f"  Throughput: {throughput:.1f} iterations/second")
    print(f"  Total State Growth: {total_change} units")
    print(f"  Avg Growth per Iteration: {total_change/iterations if iterations > 0 else 0:.2f} units")

    print("\n🧠 Learning Advancement:")
    print(f"  Claims Generated: {after_state['state']['evidence_claims']} " +
          f"(+{after_state['state']['evidence_claims'] - before_state['state']['evidence_claims']})")
    print(f"  Proposals Made: {after_state['state']['proposals_made']} " +
          f"(+{after_state['state']['proposals_made'] - before_state['state']['proposals_made']})")
    print(f"  Proposals Approved: {after_state['state']['proposals_approved']} " +
          f"(+{after_state['state']['proposals_approved'] - before_state['state']['proposals_approved']})")
    print(f"  Memory Experiences: {after_state['state']['memory_experiences']} " +
          f"(+{after_state['state']['memory_experiences'] - before_state['state']['memory_experiences']})")
    print(f"  Simulation Scenarios: {after_state['state']['simulation_scenarios']} " +
          f"(+{after_state['state']['simulation_scenarios'] - before_state['state']['simulation_scenarios']})")

    print("\n✅ Learning System Status:")
    approval_rate = (
        after_state['state']['proposals_approved'] /
        after_state['state']['proposals_made']
        if after_state['state']['proposals_made'] > 0 else 0
    )
    print(f"  Proposal Approval Rate: {approval_rate:.1%}")
    print(f"  Active Learning Proposals: {after_state['state']['learning_proposals_approved']}")
    print(f"  Evidence Quality (sources): {after_state['state']['evidence_sources']}")

    # Save detailed report
    report = {
        "experiment": "Agentco Integrated Learning 5-Min Run",
        "duration": 300,
        "iterations": iterations,
        "throughput": throughput,
        "before": before_state,
        "after": after_state,
        "changes": {
            key: after_state['state'][key] - before_state['state'][key]
            for key in before_state['state']
        }
    }

    report_dir = Path("results/learning_runs")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"integrated_5min_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report saved: {report_file}")
    print("\n" + "=" * 90)
