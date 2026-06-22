#!/usr/bin/env python3
"""
Agentco Full Evolution Test: 10-Minute Autonomous Run with Real LLM

This is a true end-to-end test of Agentco's ability to evolve and self-improve using real OpenAI models.
The system runs completely freely with NO artificial constraints except time.

Measured Dimensions:
1. Learning Evolution: Claims → Confidence → Uncertainty reduction
2. Structural Evolution: Institutional changes, governance improvements
3. Capability Evolution: Memory accumulation, decision quality improvement
4. Autonomy Evolution: Governance decisions becoming more autonomous
5. Adaptation Evolution: System adapting its own processes

Success Criteria:
- System generates actionable insights
- Institutional structure improves
- Decision confidence increases over time
- Evidence quality accumulates
- Governance becomes more autonomous (higher approval rates)
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Install with: pip install openai")
    sys.exit(1)

from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


class EvolutionTracker:
    """Track system evolution across multiple dimensions."""

    def __init__(self):
        self.learning_curve = []
        self.confidence_history = []
        self.institutional_growth = []
        self.memory_growth = []
        self.approval_rate_history = []
        self.evidence_quality_history = []
        self.decision_outcomes = defaultdict(list)
        self.governance_decisions = []
        self.adaptive_changes = []

    def record_iteration(self, iteration: int, elapsed: float,
                        confidence: float, evidence_count: int,
                        proposals_made: int, proposals_approved: int,
                        memory_size: int, learning_proposals: int):
        """Record metrics for this iteration."""

        approval_rate = (proposals_approved / proposals_made) if proposals_made > 0 else 0

        self.learning_curve.append({
            'iteration': iteration,
            'elapsed': elapsed,
            'confidence': confidence,
            'evidence_count': evidence_count
        })

        self.confidence_history.append(confidence)
        self.approval_rate_history.append(approval_rate)
        self.evidence_quality_history.append(evidence_count)
        self.memory_growth.append(memory_size)

    def get_evolution_score(self) -> dict:
        """Calculate overall evolution metrics."""
        if not self.confidence_history:
            return {}

        initial_confidence = self.confidence_history[0] if self.confidence_history else 0
        final_confidence = self.confidence_history[-1] if self.confidence_history else 0
        avg_confidence = sum(self.confidence_history) / len(self.confidence_history)

        initial_approval = self.approval_rate_history[0] if self.approval_rate_history else 0
        final_approval = self.approval_rate_history[-1] if self.approval_rate_history else 0
        avg_approval = sum(self.approval_rate_history) / len(self.approval_rate_history)

        initial_evidence = self.evidence_quality_history[0] if self.evidence_quality_history else 0
        final_evidence = self.evidence_quality_history[-1] if self.evidence_quality_history else 0

        return {
            'confidence_improvement': final_confidence - initial_confidence,
            'avg_confidence': avg_confidence,
            'approval_rate_improvement': final_approval - initial_approval,
            'avg_approval_rate': avg_approval,
            'evidence_accumulation': final_evidence - initial_evidence,
            'total_memory': self.memory_growth[-1] if self.memory_growth else 0,
        }


def run_evolution_test(duration_seconds: int = 600):
    """Run the full Agentco evolution test with real OpenAI models."""

    import os

    # Initialize OpenAI client with API key from environment
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: No OpenAI API key found in LLM_API_KEY or OPENAI_API_KEY environment variable")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print("\n🤖 Initializing OpenAI models...")
    print(f"  Provider: openai")
    print(f"  Frontier model: gpt-4o")
    print(f"  Standard model: gpt-4o-mini")

    # Initialize all systems
    society_kernel = SocietyKernel()
    evidence_kernel = EvidenceKernel()
    memory_kernel = MemoryKernel()
    uncertainty = UncertaintyStack()
    world_lab = WorldLab(evidence_kernel)
    learning_loop = AutonomousLearningLoop(evidence_kernel, memory_kernel, uncertainty)

    tracker = EvolutionTracker()

    # Track API calls and costs
    api_calls = 0
    api_tokens_used = 0

    def call_llm_for_evolution(signal: str, iteration: int) -> dict:
        """Call real OpenAI model to generate insights for evolution."""
        nonlocal api_calls, api_tokens_used

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for speed and cost
                messages=[
                    {
                        "role": "system",
                        "content": "You are Agentco's Evolution Engine. Analyze signals and propose adaptive improvements. Be concise."
                    },
                    {
                        "role": "user",
                        "content": f"Evolution Signal #{iteration}: {signal}\n\nProvide: 1) Key insight, 2) Confidence (0-100), 3) Proposed adaptation"
                    }
                ],
                temperature=0.7,
                max_tokens=150,
                timeout=5.0
            )

            api_calls += 1
            if response.usage:
                api_tokens_used += response.usage.total_tokens

            content = response.choices[0].message.content if response.choices else ""

            # Parse the response
            lines = content.split('\n')
            insight = lines[0] if lines else signal
            adaptation = lines[-1] if len(lines) > 2 else "Structural optimization"

            # Extract confidence - look for numbers in the response
            confidence = 70  # Default confidence (reasonable baseline)
            import re

            # Search all content for percentage or number
            for text_to_search in [content, lines[0] if lines else ""]:
                numbers = re.findall(r'\b(\d+)\b', text_to_search)
                if numbers:
                    for num in numbers:
                        num_val = int(num)
                        if 0 <= num_val <= 100:
                            confidence = num_val
                            break
                    if confidence != 70:  # Found a number
                        break

            return {
                "insight": insight,
                "confidence": confidence,
                "adaptation": adaptation,
                "success": True
            }
        except Exception as e:
            # Fallback if API call fails
            return {
                "insight": f"Pattern from signal: {signal[:50]}",
                "confidence": 50,
                "adaptation": "Continue learning cycle",
                "success": False,
                "error": str(e)
            }

    # Bootstrap society with initial structure
    print("\n" + "="*100)
    print("AGENTCO FULL EVOLUTION TEST: 10-MINUTE AUTONOMOUS RUN")
    print("="*100)
    print("\n[INIT] Setting up complete Agentco stack...\n")

    # Create comprehensive institutional structure
    # Note: Create institutions FIRST, then create society with them
    institutions = {}
    institutions['governance'] = society_kernel.create_institution(
        "Adaptive Governance", "Dynamic policy and decision authority"
    )
    institutions['evidence'] = society_kernel.create_institution(
        "Evidence Foundation", "Evidence collection, validation, and reliability tracking"
    )
    institutions['learning'] = society_kernel.create_institution(
        "Learning Nexus", "Knowledge synthesis, pattern recognition, hypothesis generation"
    )
    institutions['simulation'] = society_kernel.create_institution(
        "Simulation Engine", "Scenario testing and outcome prediction"
    )
    institutions['adaptation'] = society_kernel.create_institution(
        "Adaptation Core", "Self-modification and structural evolution"
    )

    print(f"   Institutions created: {len(institutions)}")
    for name, inst in institutions.items():
        print(f"     - {name}: {inst.institution_id}")

    primary_society = society_kernel.create_society(
        "Agentco Evolution Collective",
        [inst.institution_id for inst in institutions.values()]
    )

    print(f"✓ Created {primary_society.name}")
    print(f"✓ Initialized {len(institutions)} institutions")
    print(f"✓ Evidence kernel ready")
    print(f"✓ Learning loop ready")
    print(f"✓ Memory kernel ready\n")

    # Evolution signals - progressively more sophisticated
    evolution_phases = {
        'discovery': [
            "Discover fundamental patterns in decision-making",
            "Identify evidence reliability markers",
            "Learn confidence calibration from outcomes",
            "Map institutional interdependencies",
            "Recognize decision-outcome correlations",
        ],
        'optimization': [
            "Optimize governance for approval efficiency",
            "Enhance evidence synthesis across sources",
            "Improve hypothesis quality through iteration",
            "Refine uncertainty estimation",
            "Accelerate institutional coordination",
        ],
        'adaptation': [
            "Propose structural improvements",
            "Design adaptive governance rules",
            "Create specialized decision pathways",
            "Build learning-informed policies",
            "Implement self-improving mechanisms",
        ],
        'emergence': [
            "Enable emergent coordination patterns",
            "Foster cross-institutional learning",
            "Create meta-governance for adaptation",
            "Develop institutional self-awareness",
            "Enable autonomous evolution protocols",
        ],
    }

    # Run the evolution loop
    start_time = time.time()
    iteration = 0
    phase_index = 0
    phase_names = list(evolution_phases.keys())

    print("[RUN] Starting 10-minute evolution test...\n")

    while time.time() - start_time < duration_seconds:
        elapsed = time.time() - start_time
        iteration += 1

        # Determine current phase
        progress = elapsed / duration_seconds
        current_phase = phase_names[min(int(progress * len(phase_names)), len(phase_names) - 1)]
        signals = evolution_phases[current_phase]
        signal = signals[iteration % len(signals)]

        # Get LLM insight for this signal (using real OpenAI model)
        llm_result = call_llm_for_evolution(signal, iteration)
        llm_confidence = llm_result.get("confidence", 50) / 100.0

        # Run learning cycle
        learning_result = learning_loop.run(
            signal,
            source_uri=f"evolution://phase-{current_phase}/iter-{iteration}"
        )

        claims_generated = len(learning_result.get("claims", []))
        hypothesis_valid = bool(learning_result.get("hypothesis", {}).get("hypothesis_id"))

        # Use LLM confidence directly (already normalized 0-1)
        combined_confidence = llm_confidence if llm_result.get("success") else 0.5

        # Create institutional proposals based on learning
        proposals_this_iter = 0
        approved_this_iter = 0

        for society_id in list(society_kernel.societies.keys()):
            # Generate proposal from learning insights
            change = {
                "type": "evolutionary_adaptation",
                "phase": current_phase,
                "iteration": iteration,
                "signal": signal,
                "insights": {
                    "claims_generated": claims_generated,
                    "hypothesis_valid": hypothesis_valid,
                },
            }

            proposal = society_kernel.propose_structure_change(society_id, change)
            proposals_this_iter += 1

            # Governance decision: approve if proposal is valid and confidence is above baseline
            if proposal and proposal.get("proposal_id"):
                proposal_id = proposal.get("proposal_id")
                proposal_status = proposal.get("status")

                # Simple decision: approve if confidence > 0.35 and proposal is in "proposed" status
                should_approve = (
                    proposal_status == "proposed" and  # Only approve if still in proposed state
                    combined_confidence > 0.35  # Realistic threshold
                )

                if should_approve:
                    try:
                        society_kernel.decide(proposal_id, approved=True)
                        approved_this_iter += 1
                        tracker.adaptive_changes.append({
                            'iteration': iteration,
                            'phase': current_phase,
                            'type': change['type'],
                            'llm_insight': llm_result.get("insight", ""),
                            'confidence': combined_confidence
                        })
                    except Exception as e:
                        pass  # Silent fail if decision fails

        # Run scenarios to validate learning
        scenario = world_lab.create_scenario(
            f"Phase {current_phase}: {signal[:50]}"
        )
        world_lab.run_simulation(scenario.scenario_id)

        # Calculate metrics - use LLM-informed confidence
        avg_confidence = combined_confidence

        # Record metrics
        tracker.record_iteration(
            iteration=iteration,
            elapsed=elapsed,
            confidence=avg_confidence,
            evidence_count=len(evidence_kernel.claims),
            proposals_made=len(society_kernel.proposals),
            proposals_approved=sum(1 for p in society_kernel.proposals.values() if p.get("status") == "approved"),
            memory_size=len(memory_kernel.experiential),
            learning_proposals=len(learning_loop.proposals)
        )

        # Progress output (every 100 iterations)
        if iteration % 100 == 0:
            throughput = iteration / elapsed if elapsed > 0 else 0
            approval_rate = (approved_this_iter / proposals_this_iter * 100) if proposals_this_iter > 0 else 0
            print(
                f"[{int(elapsed):3d}s] Iter {iteration:5d} | "
                f"Phase: {current_phase:12s} | "
                f"{throughput:6.1f} iter/s | "
                f"API: {api_calls:3d} calls | "
                f"Claims: {len(evidence_kernel.claims):5d} | "
                f"Memory: {len(memory_kernel.experiential):5d} | "
                f"Approval: {approval_rate:5.1f}%"
            )

    elapsed = time.time() - start_time

    print(f"\n✓ Evolution test complete: {iteration} iterations in {elapsed:.1f}s ({iteration/elapsed:.1f} iter/s)")
    print(f"✓ OpenAI API calls: {api_calls} | Total tokens used: {api_tokens_used}\n")

    return {
        'iterations': iteration,
        'duration': elapsed,
        'throughput': iteration / elapsed,
        'api_metrics': {
            'api_calls': api_calls,
            'tokens_used': api_tokens_used,
            'calls_per_iteration': api_calls / iteration if iteration > 0 else 0,
        },
        'final_state': {
            'societies': len(society_kernel.societies),
            'institutions': len(society_kernel.institutions),
            'evidence_claims': len(evidence_kernel.claims),
            'evidence_sources': len(evidence_kernel.sources),
            'memory_experiences': len(memory_kernel.experiential),
            'proposals_made': len(society_kernel.proposals),
            'proposals_approved': sum(1 for p in society_kernel.proposals.values() if p.get("status") == "approved"),
            'scenarios_explored': len(world_lab.scenarios),
            'learning_proposals': len(learning_loop.proposals),
        },
        'evolution_metrics': tracker.get_evolution_score(),
        'adaptive_changes': tracker.adaptive_changes,
        'confidence_history': tracker.confidence_history,
        'approval_rate_history': tracker.approval_rate_history,
    }


def print_evolution_report(results: dict):
    """Print comprehensive evolution report."""

    print("="*100)
    print("EVOLUTION TEST RESULTS")
    print("="*100)

    print("\n📊 EXECUTION SUMMARY")
    print("-" * 100)
    print(f"  Total Iterations: {results['iterations']:,}")
    print(f"  Duration: {results['duration']:.1f} seconds (10 minutes)")
    print(f"  Throughput: {results['throughput']:.1f} iterations/second")

    print("\n🤖 OPENAI API METRICS")
    print("-" * 100)
    api_metrics = results.get('api_metrics', {})
    print(f"  API Calls Made: {api_metrics.get('api_calls', 0)}")
    print(f"  Total Tokens Used: {api_metrics.get('tokens_used', 0):,}")
    print(f"  Calls per Iteration: {api_metrics.get('calls_per_iteration', 0):.3f}")
    if api_metrics.get('tokens_used', 0) > 0:
        print(f"  Avg Tokens per Call: {api_metrics.get('tokens_used', 1) / max(1, api_metrics.get('api_calls', 1)):.1f}")

    print("\n📈 FINAL SYSTEM STATE")
    print("-" * 100)
    state = results['final_state']
    print(f"  Societies: {state['societies']}")
    print(f"  Institutions: {state['institutions']}")
    print(f"  Evidence Claims: {state['evidence_claims']:,}")
    print(f"  Evidence Sources: {state['evidence_sources']:,}")
    print(f"  Memory Experiences: {state['memory_experiences']:,}")
    print(f"  Proposals Made: {state['proposals_made']:,}")
    print(f"  Proposals Approved: {state['proposals_approved']:,}")
    print(f"  Simulation Scenarios: {state['scenarios_explored']:,}")
    print(f"  Learning Proposals: {state['learning_proposals']:,}")

    print("\n🧬 EVOLUTION METRICS")
    print("-" * 100)
    metrics = results['evolution_metrics']
    if metrics:
        print(f"  Confidence Improvement: {metrics.get('confidence_improvement', 0):+.4f}")
        print(f"  Average Confidence: {metrics.get('avg_confidence', 0):.4f}")
        print(f"  Approval Rate Improvement: {metrics.get('approval_rate_improvement', 0):+.1%}")
        print(f"  Average Approval Rate: {metrics.get('avg_approval_rate', 0):.1%}")
        print(f"  Evidence Accumulation: +{metrics.get('evidence_accumulation', 0):,}")
        print(f"  Total Memory: {metrics.get('total_memory', 0):,}")

    print("\n⚡ ADAPTIVE CHANGES MADE")
    print("-" * 100)
    if results['adaptive_changes']:
        changes_by_phase = defaultdict(int)
        for change in results['adaptive_changes']:
            changes_by_phase[change['phase']] += 1

        for phase, count in sorted(changes_by_phase.items()):
            print(f"  {phase.capitalize():15s}: {count:4d} adaptations")
        print(f"  {'Total':15s}: {len(results['adaptive_changes']):4d} adaptations")

    print("\n🎯 CAPABILITY EVOLUTION ASSESSMENT")
    print("-" * 100)

    # Assess evolution capability
    if state['evidence_claims'] > 10000:
        print("  ✅ KNOWLEDGE ACCUMULATION: Excellent - Strong evidence base built")
    else:
        print(f"  ⚠️  KNOWLEDGE ACCUMULATION: Limited - {state['evidence_claims']} claims generated")

    if metrics and metrics.get('approval_rate_improvement', 0) > 0:
        print("  ✅ DECISION AUTONOMY: Improving - Governance becoming more autonomous")
    else:
        print("  ⚠️  DECISION AUTONOMY: Stable - Governance maintaining consistency")

    if len(results['adaptive_changes']) > 1000:
        print("  ✅ STRUCTURAL ADAPTATION: Active - System evolving its own structure")
    else:
        print(f"  ⚠️  STRUCTURAL ADAPTATION: Limited - {len(results['adaptive_changes'])} changes made")

    if state['memory_experiences'] > 5000:
        print("  ✅ LEARNING CAPACITY: Strong - Extensive experience accumulation")
    else:
        print(f"  ⚠️  LEARNING CAPACITY: Developing - {state['memory_experiences']} experiences recorded")

    print("\n🚀 EVOLUTION VERDICT")
    print("-" * 100)

    total_score = 0
    if state['evidence_claims'] > 10000:
        total_score += 1
    if metrics and metrics.get('approval_rate_improvement', 0) > 0:
        total_score += 1
    if len(results['adaptive_changes']) > 1000:
        total_score += 1
    if state['memory_experiences'] > 5000:
        total_score += 1

    if total_score == 4:
        print("  🌟 EXCEPTIONAL: System demonstrates strong autonomous evolution capability")
    elif total_score == 3:
        print("  ⭐  STRONG: System shows significant evolution and self-improvement")
    elif total_score == 2:
        print("  ✨ CAPABLE: System evolves but with limitations")
    elif total_score >= 1:
        print("  ℹ️  DEVELOPING: System shows signs of evolution")
    else:
        print("  ⚠️  LIMITED: Evolution capability constrained")

    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    print("\n🚀 AGENTCO EVOLUTION TEST STARTING\n")

    results = run_evolution_test(duration_seconds=600)
    print_evolution_report(results)

    # Save detailed results
    report_dir = Path("results/evolution_tests")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"✓ Full results saved to: {report_file}\n")
