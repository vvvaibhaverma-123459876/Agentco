"""
Execution Layer - Translates decisions into real system actions.

DecisionEngine decides → ExecutionLayer executes in real systems.
"""

from typing import Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


@dataclass
class ExecutionResult:
    """Result of executing a decision."""
    action_name: str
    executed: bool
    status: str
    outputs: Dict[str, Any]
    timestamp: datetime


class ExecutionLayer:
    """
    Translates autonomous decisions into real system actions.
    """

    def __init__(self):
        # Initialize all systems
        self.society_kernel = SocietyKernel()
        self.evidence_kernel = EvidenceKernel()
        self.memory_kernel = MemoryKernel()
        self.uncertainty = UncertaintyStack()
        self.world_lab = WorldLab(self.evidence_kernel)
        self.learning_loop = AutonomousLearningLoop(
            self.evidence_kernel,
            self.memory_kernel,
            self.uncertainty
        )

        # Create institutional structure
        self._setup_institutions()

        # Action executors
        self.executors: Dict[str, Callable] = {
            'improve_evidence_sources': self._execute_improve_evidence,
            'optimize_decision_process': self._execute_optimize_decisions,
            'strengthen_institutional_coordination': self._execute_strengthen_coordination,
            'implement_meta_learning': self._execute_implement_meta_learning,
        }

    def _setup_institutions(self):
        """Create initial institutional structure."""
        self.institutions = {
            'governance': self.society_kernel.create_institution(
                "Adaptive Governance", "Policy and decision authority"
            ),
            'evidence': self.society_kernel.create_institution(
                "Evidence Foundation", "Evidence collection and validation"
            ),
            'learning': self.society_kernel.create_institution(
                "Learning Nexus", "Knowledge synthesis and pattern recognition"
            ),
            'simulation': self.society_kernel.create_institution(
                "Simulation Engine", "Scenario testing and prediction"
            ),
            'adaptation': self.society_kernel.create_institution(
                "Adaptation Core", "Self-modification and evolution"
            ),
        }

        self.primary_society = self.society_kernel.create_society(
            "Agentco Collective",
            [inst.institution_id for inst in self.institutions.values()]
        )

    def execute_decision(self, action_name: str, action_data: Dict) -> ExecutionResult:
        """
        Execute a decision in the real systems.
        """
        if action_name not in self.executors:
            return ExecutionResult(
                action_name=action_name,
                executed=False,
                status=f"Unknown action: {action_name}",
                outputs={},
                timestamp=datetime.now()
            )

        try:
            executor = self.executors[action_name]
            outputs = executor(action_data)

            return ExecutionResult(
                action_name=action_name,
                executed=True,
                status="SUCCESS",
                outputs=outputs,
                timestamp=datetime.now()
            )
        except Exception as e:
            return ExecutionResult(
                action_name=action_name,
                executed=False,
                status=f"EXECUTION_ERROR: {str(e)}",
                outputs={},
                timestamp=datetime.now()
            )

    def _execute_improve_evidence(self, action_data: Dict) -> Dict:
        """
        Execute: Add more diverse evidence sources.
        """
        # Create multiple learning cycles with different signals
        signals = [
            "Strengthen evidence validation methodology",
            "Add cross-domain evidence sources",
            "Improve evidence reliability assessment",
        ]

        results = []
        for signal in signals:
            result = self.learning_loop.run(
                signal,
                source_uri="decision://improve_evidence"
            )
            results.append(result)

        # Measure evidence kernel growth
        evidence_before = len(self.evidence_kernel.claims)
        evidence_sources = len(self.evidence_kernel.sources)

        return {
            'learning_cycles': len(signals),
            'claims_generated': sum(len(r.get('claims', [])) for r in results),
            'evidence_sources': evidence_sources,
            'total_claims': len(self.evidence_kernel.claims),
            'claims_generated_this_action': len(self.evidence_kernel.claims) - evidence_before
        }

    def _execute_optimize_decisions(self, action_data: Dict) -> Dict:
        """
        Execute: Refine decision-making logic.
        Increase learning loop frequency and improve hypothesis generation.
        """
        signals = [
            "Optimize decision pathway efficiency",
            "Improve decision latency",
            "Enhance decision quality metrics",
        ]

        results = []
        for signal in signals:
            result = self.learning_loop.run(
                signal,
                source_uri="decision://optimize_decisions"
            )
            results.append(result)

        hypothesis_count = sum(1 for r in results if r.get('hypothesis'))

        return {
            'optimization_cycles': len(signals),
            'hypotheses_generated': hypothesis_count,
            'learning_proposals': len(self.learning_loop.proposals),
            'memory_growth': len(self.memory_kernel.experiential)
        }

    def _execute_strengthen_coordination(self, action_data: Dict) -> Dict:
        """
        Execute: Create institutional contracts and coordination.
        """
        # Create proposals for institutional improvement
        proposals = []
        society_id = self.primary_society.society_id

        coordination_changes = [
            {
                "type": "institutional_contract",
                "consumer": "governance",
                "provider": "learning",
                "service": "decision_guidance"
            },
            {
                "type": "institutional_contract",
                "consumer": "learning",
                "provider": "evidence",
                "service": "validated_claims"
            },
            {
                "type": "institutional_contract",
                "consumer": "adaptation",
                "provider": "memory",
                "service": "experience_records"
            },
        ]

        for change in coordination_changes:
            proposal = self.society_kernel.propose_structure_change(
                society_id,
                change
            )
            if proposal:
                # Auto-approve coordination improvements
                prop_id = proposal.get('proposal_id')
                if prop_id:
                    self.society_kernel.decide(prop_id, approved=True)
                    proposals.append(proposal)

        return {
            'coordination_proposals': len(proposals),
            'proposals_approved': len(proposals),
            'total_society_proposals': len(self.society_kernel.proposals)
        }

    def _execute_implement_meta_learning(self, action_data: Dict) -> Dict:
        """
        Execute: Enhance meta-learning capabilities.
        """
        signals = [
            "Implement meta-learning framework",
            "Improve confidence calibration",
            "Enable self-correction mechanisms",
            "Build learning improvement detection",
        ]

        results = []
        for signal in signals:
            result = self.learning_loop.run(
                signal,
                source_uri="decision://meta_learning"
            )
            results.append(result)

        # Run world simulations to test hypotheses
        scenarios = []
        for i, result in enumerate(results):
            if result.get('hypothesis'):
                scenario = self.world_lab.create_scenario(
                    f"Meta-learning hypothesis {i}"
                )
                self.world_lab.run_simulation(scenario.scenario_id)
                scenarios.append(scenario)

        return {
            'meta_learning_cycles': len(signals),
            'hypotheses_tested': len(scenarios),
            'simulation_results': len(self.world_lab.results),
            'learning_insights': sum(len(r.get('insights', [])) for r in results)
        }

    def get_system_state(self) -> Dict:
        """Get current state of all systems."""
        return {
            'societies': len(self.society_kernel.societies),
            'institutions': len(self.society_kernel.institutions),
            'evidence_claims': len(self.evidence_kernel.claims),
            'evidence_sources': len(self.evidence_kernel.sources),
            'memory_experiential': len(self.memory_kernel.experiential),
            'memory_operational': len(self.memory_kernel.operational),
            'proposals_made': len(self.society_kernel.proposals),
            'proposals_approved': sum(
                1 for p in self.society_kernel.proposals.values()
                if p.get('status') == 'approved'
            ),
            'scenarios_created': len(self.world_lab.scenarios),
            'simulation_results': len(self.world_lab.results),
            'learning_proposals': len(self.learning_loop.proposals)
        }


# Global instance
_execution_layer = None


def get_execution_layer() -> ExecutionLayer:
    """Get the global execution layer."""
    global _execution_layer
    if _execution_layer is None:
        _execution_layer = ExecutionLayer()
    return _execution_layer
