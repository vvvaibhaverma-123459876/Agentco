#!/usr/bin/env python3
"""
Autonomous self-modifying learning: Agentco learns, proposes changes based on insights,
and adapts its own structure for 10 minutes. Feedback loops drive improvement.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure Agentco modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


def capture_state(label: str) -> dict:
    """Capture the current state of all systems."""
    return {
        "timestamp": datetime.now().isoformat(),
        "label": label,
        "metadata": {
            "societies": len(society_kernel.societies),
            "institutions": len(society_kernel.institutions),
            "agent_memberships": len(society_kernel.agent_membership),
            "proposals": len(society_kernel.proposals),
            "proposals_approved": sum(1 for p in society_kernel.proposals.values() if p.get("status") == "approved"),
            "evidence_claims": len(evidence_kernel.claims),
            "evidence_sources": len(evidence_kernel.sources),
            "evidence_resolutions": len(evidence_kernel.resolutions),
            "memory_experiential": len(memory_kernel.experiential),
            "memory_operational": len(memory_kernel.operational),
            "simulation_scenarios": len(world_lab.scenarios),
            "simulation_results": len(world_lab.results),
            "learning_proposals": len(learning_loop.proposals),
        },
    }


def analyze_insights(learning_result: dict) -> dict:
    """Analyze learning loop output to identify improvement areas."""
    claims = learning_result.get("claims", [])
    hypothesis = learning_result.get("hypothesis", {})
    proposal = learning_result.get("adaptation_proposal")

    # Extract improvement priorities from claims and proposals
    proposal_status = proposal.status if proposal else "unknown"
    proposal_risk = proposal.risk_level if proposal else "medium"

    improvements = {
        "evidence_quality": len(claims) > 0,
        "hypothesis_strength": hypothesis.get("hypothesis_id") is not None,
        "governance_ready": proposal_status == "governance_required",
        "risk_level": proposal_risk,
    }

    return improvements


def propose_institutional_change(iteration: int, improvements: dict, learning_result: dict) -> dict:
    """Propose institutional changes based on learning insights."""
    proposal = learning_result.get("adaptation_proposal")
    claims = learning_result.get("claims", [])
    claim = claims[0] if claims else None
    claim_id = claim.claim_id if claim and hasattr(claim, 'claim_id') else None

    change = {
        "type": "learning_based_adaptation",
        "iteration": iteration,
        "insights": improvements,
        "rationale": f"Iteration {iteration}: {len(claims)} claims extracted, "
                     f"hypothesis proposed, risk={improvements.get('risk_level')}",
        "claim_id": claim_id,
        "proposed_by": "autonomous_learning_loop",
    }

    return change


def advance_with_feedback():
    """Run autonomous advancement with real learning feedback loops."""
    start_time = time.time()
    duration_seconds = 600  # 10 minutes
    iteration = 0
    approved_changes = 0
    rejected_changes = 0

    # Adaptive signal generation (evolves based on what's learned)
    base_signals = [
        "Strengthen evidence validation and source reliability",
        "Improve institutional coordination and knowledge sharing",
        "Enhance decision-making calibration accuracy",
        "Propose new governance structures",
        "Integrate feedback from past failures",
        "Accelerate hypothesis validation",
        "Build institutional resilience",
        "Optimize resource allocation",
        "Expand institutional capacity",
        "Foster cross-disciplinary insights",
    ]

    last_learning_focus = None
    learning_streak = 0

    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = time.time() - start_time

        # Adaptive signal: focus on areas with recent learning
        if last_learning_focus and learning_streak < 3:
            signal = f"Deepen: {last_learning_focus} (iteration {iteration})"
            learning_streak += 1
        else:
            signal = base_signals[iteration % len(base_signals)]
            last_learning_focus = signal.split(":")[0] if ":" in signal else signal
            learning_streak = 0

        # ──────────────────────────────────────────────────────────────
        # PHASE 1: LEARN - Run learning loop and extract insights
        # ──────────────────────────────────────────────────────────────
        learning_result = learning_loop.run(signal, source_uri=f"autonomous://iteration-{iteration}")
        insights = analyze_insights(learning_result)

        # ──────────────────────────────────────────────────────────────
        # PHASE 2: SIMULATE - Test improvements in world lab
        # ──────────────────────────────────────────────────────────────
        scenario = world_lab.create_scenario(
            f"Testing: {signal[:50]} (insights: {json.dumps(insights, default=str)[:40]})"
        )
        sim_result = world_lab.run_simulation(scenario.scenario_id)

        # ──────────────────────────────────────────────────────────────
        # PHASE 3: PROPOSE - Create structural changes based on learnings
        # ──────────────────────────────────────────────────────────────
        change = propose_institutional_change(iteration, insights, learning_result)

        # Propose in all societies
        society_proposals = {}
        if society_kernel.societies:
            for society_id in list(society_kernel.societies.keys()):
                proposal = society_kernel.propose_structure_change(society_id, change)
                society_proposals[proposal["proposal_id"]] = proposal

        # ──────────────────────────────────────────────────────────────
        # PHASE 4: DECIDE - Governance approves changes based on evidence
        # ──────────────────────────────────────────────────────────────
        for proposal_id, proposal in society_proposals.items():
            change_data = proposal.get("change", {})

            # Decision criteria: based on learning quality
            claims_generated = len(learning_result.get("claims", []))
            hypothesis_valid = learning_result.get("hypothesis", {}).get("hypothesis_id") is not None
            risk_acceptable = insights.get("risk_level") != "critical"

            # Approve if learning generated good signal
            should_approve = (
                claims_generated > 0
                and hypothesis_valid
                and risk_acceptable
                and proposal_id not in approved_proposals
            )

            if should_approve:
                society_kernel.decide(proposal_id, approved=True)
                approved_proposals.add(proposal_id)
                approved_changes += 1
            else:
                society_kernel.decide(proposal_id, approved=False)
                rejected_proposals.add(proposal_id)
                rejected_changes += 1

        # ──────────────────────────────────────────────────────────────
        # PHASE 5: LEARN FROM OUTCOME - Update memory with results
        # ──────────────────────────────────────────────────────────────
        outcome = {
            "iteration": iteration,
            "signal": signal,
            "claims_generated": len(learning_result.get("claims", [])),
            "proposal_approved": approved_changes,
            "hypothesis_valid": hypothesis_valid,
            "sim_insight": sim_result.get("insight"),
        }

        memory_kernel.write_experience(
            principal_id="autonomous_advancement",
            memory_type="iteration_outcome",
            content=outcome,
            provenance_ref=f"autonomous://iteration-{iteration}",
        )

        # ──────────────────────────────────────────────────────────────
        # Progress reporting (every 30 iterations)
        # ──────────────────────────────────────────────────────────────
        if iteration % 30 == 0:
            throughput = iteration / elapsed if elapsed > 0 else 0
            quality = approved_changes / (approved_changes + rejected_changes) if (approved_changes + rejected_changes) > 0 else 0
            print(
                f"[{int(elapsed):3d}s] Iter {iteration:4d} | "
                f"{throughput:5.1f} iter/s | "
                f"Approved: {approved_changes:3d} | "
                f"Rejected: {rejected_changes:3d} | "
                f"Quality: {quality:.1%} | "
                f"Claims: {len(evidence_kernel.claims):4d} | "
                f"Memory: {len(memory_kernel.experiential):4d}",
                flush=True,
            )

    elapsed = time.time() - start_time
    throughput = iteration / elapsed if elapsed > 0 else 0
    approval_rate = approved_changes / (approved_changes + rejected_changes) if (approved_changes + rejected_changes) > 0 else 0

    print(f"\n✓ 10-minute adaptive learning complete")
    print(f"  Total iterations: {iteration}")
    print(f"  Throughput: {throughput:.1f} iterations/second")
    print(f"  Changes approved: {approved_changes}")
    print(f"  Changes rejected: {rejected_changes}")
    print(f"  Approval rate (quality): {approval_rate:.1%}")

    return iteration, throughput, approved_changes, approval_rate


def generate_comparison(duration_seconds, iterations, throughput, approved_changes, approval_rate):
    """Generate detailed before/after comparison with learning metrics."""
    comparison = {
        "experiment": "Autonomous 10-Minute Self-Modifying Learning",
        "description": "Agentco learns, proposes institutional changes, and adapts structure based on evidence.",
        "timestamp": datetime.now().isoformat(),
        "before": before_state,
        "after": after_state,
        "duration_seconds": duration_seconds,
        "performance": {
            "iterations_completed": iterations,
            "throughput_iterations_per_second": throughput,
            "changes_proposed": approved_changes + len(rejected_proposals),
            "changes_approved": approved_changes,
            "changes_rejected": len(rejected_proposals),
            "approval_rate": approval_rate,
        },
        "advancement": {
            "societies_created": after_state["metadata"]["societies"] - before_state["metadata"]["societies"],
            "institutions_created": after_state["metadata"]["institutions"] - before_state["metadata"]["institutions"],
            "evidence_claims_added": after_state["metadata"]["evidence_claims"] - before_state["metadata"]["evidence_claims"],
            "memory_events_added": after_state["metadata"]["memory_experiential"] - before_state["metadata"]["memory_experiential"],
            "proposals_made": after_state["metadata"]["proposals"] - before_state["metadata"]["proposals"],
            "proposals_approved": after_state["metadata"]["proposals_approved"],
            "simulation_scenarios_run": after_state["metadata"]["simulation_scenarios"] - before_state["metadata"]["simulation_scenarios"],
        },
    }
    return comparison


# ============================================================================
# MAIN: Capture Initial State -> Advance with Feedback -> Capture Final State -> Compare
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("AGENTCO AUTONOMOUS 10-MINUTE SELF-MODIFYING LEARNING")
    print("=" * 100)
    print("Agentco will: LEARN → SIMULATE → PROPOSE → DECIDE → LEARN (feedback loops)")
    print()

    # Initialize systems
    society_kernel = SocietyKernel()
    evidence_kernel = EvidenceKernel()
    memory_kernel = MemoryKernel()
    uncertainty = UncertaintyStack()
    world_lab = WorldLab(evidence_kernel)
    learning_loop = AutonomousLearningLoop(evidence_kernel, memory_kernel, uncertainty)
    approved_proposals = set()
    rejected_proposals = set()

    # Bootstrap: Create initial societal structure
    print("[SETUP] Initializing societal structure...")

    inst_governance = society_kernel.create_institution("Governance Council", "Institutional oversight and policy")
    inst_evidence = society_kernel.create_institution("Evidence Bureau", "Evidence collection and validation")
    inst_learning = society_kernel.create_institution("Learning Institute", "Knowledge synthesis and learning")
    inst_simulation = society_kernel.create_institution("World Lab", "Simulation and scenario testing")

    initial_society = society_kernel.create_society(
        "Prime Society",
        [inst_governance.institution_id, inst_evidence.institution_id,
         inst_learning.institution_id, inst_simulation.institution_id]
    )

    print(f"✓ Created {initial_society.name} with {len(initial_society.institutions)} institutions")

    # Capture initial state
    print("\n[CAPTURE] Capturing initial state...")
    before_state = capture_state("BEFORE_ADVANCEMENT")
    print(f"Initial state:")
    for key, val in before_state["metadata"].items():
        print(f"  {key}: {val}")

    # Run 10-minute adaptive learning advancement
    print("\n[ADVANCEMENT] Running 10-minute adaptive learning loop...")
    print("(Learning loop output drives institutional decisions)\n")
    advancement_start = time.time()
    iterations, throughput, approved_changes, approval_rate = advance_with_feedback()
    advancement_duration = time.time() - advancement_start

    # Capture final state
    print("\n[CAPTURE] Capturing final state...")
    after_state = capture_state("AFTER_ADVANCEMENT")
    print(f"Final state:")
    for key, val in after_state["metadata"].items():
        print(f"  {key}: {val}")

    # Generate comparison
    print("\n[ANALYSIS] Generating comparison report...")
    comparison = generate_comparison(advancement_duration, iterations, throughput, approved_changes, approval_rate)

    # Display summary
    print("\n" + "=" * 100)
    print("ADVANCEMENT SUMMARY")
    print("=" * 100)

    print("\n📊 Performance Metrics:")
    for metric, value in comparison["performance"].items():
        if isinstance(value, float) and metric.endswith("rate"):
            print(f"  {metric}: {value:.1%}")
        else:
            print(f"  {metric}: {value}")

    print("\n🚀 Advancement Achieved:")
    for metric, value in comparison["advancement"].items():
        if value > 0:
            print(f"  {metric}: +{value}")

    print("\n📈 State Comparison:")
    print(f"  Before → After")
    for key in before_state["metadata"]:
        before_val = before_state["metadata"][key]
        after_val = after_state["metadata"][key]
        delta = after_val - before_val
        if delta != 0:
            print(f"  {key}: {before_val} → {after_val} (+{delta})")

    # Save report
    report_dir = Path("results/autonomous_advancement")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"learning_advancement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    print(f"\n✓ Full report saved to: {report_file}")

    # Create markdown summary
    md_file = report_dir / "latest_learning_advancement.md"
    with open(md_file, "w") as f:
        f.write("# Agentco Autonomous 10-Minute Self-Modifying Learning Report\n\n")
        f.write(f"**Experiment:** {comparison['experiment']}\n\n")
        f.write(f"**Description:** {comparison['description']}\n\n")
        f.write(f"**Duration:** {comparison['duration_seconds']:.1f} seconds\n")
        f.write(f"**Timestamp:** {comparison['timestamp']}\n\n")

        f.write("## Performance Metrics\n\n")
        for metric, value in comparison["performance"].items():
            if isinstance(value, float) and metric.endswith("rate"):
                f.write(f"- **{metric}**: {value:.1%}\n")
            else:
                f.write(f"- **{metric}**: {value}\n")

        f.write("\n## Advancement Achieved\n\n")
        for metric, value in comparison["advancement"].items():
            if value > 0:
                f.write(f"- **{metric}**: +{value}\n")

        f.write("\n## State Comparison\n\n")
        f.write("### Before\n```json\n")
        f.write(json.dumps(before_state["metadata"], indent=2))
        f.write("\n```\n\n")

        f.write("### After\n```json\n")
        f.write(json.dumps(after_state["metadata"], indent=2))
        f.write("\n```\n\n")

        f.write("## Key Insights\n\n")
        f.write(f"- Agentco processed **{iterations}** autonomous iterations in 10 minutes\n")
        f.write(f"- Learning loop generated **{after_state['metadata']['evidence_claims']}** new claims from signals\n")
        f.write(f"- Governance approved **{approved_changes}** structural changes ({approval_rate:.1%} approval rate)\n")
        f.write(f"- Memory captured **{after_state['metadata']['memory_experiential']}** learning experiences\n")
        f.write(f"- Simulation explored **{after_state['metadata']['simulation_scenarios']}** scenarios\n\n")

        f.write("## Feedback Loop Architecture\n\n")
        f.write("1. **LEARN**: Learning loop processes signal, extracts claims, creates hypotheses\n")
        f.write("2. **SIMULATE**: World Lab tests proposed improvements via simulation\n")
        f.write("3. **PROPOSE**: Institutional changes generated based on learning insights\n")
        f.write("4. **DECIDE**: Governance approves changes where evidence quality is high\n")
        f.write("5. **REMEMBER**: Outcomes recorded in memory kernel for future learning\n\n")

        f.write("This creates a self-reinforcing loop where better learning → better proposals → better outcomes.\n")

    print(f"✓ Markdown summary saved to: {md_file}")
    print("\n" + "=" * 100)
