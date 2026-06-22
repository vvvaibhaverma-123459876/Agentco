"""
Complete Autonomy Integration Layer

Wires together:
- DecisionEngine (decides what to do)
- ExecutionLayer (does it in real systems)
- MeasurementLayer (measures real outcomes)
- FeedbackLoop (learns from outcomes)
- MetaLearner (improves decision-making)

Creates complete autonomous cycle:
Situation → Decision → Execute → Measure → Learn → Better Next Decision
"""

from typing import Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomy.objective import get_objective
from autonomy.decision_engine import get_decision_engine, Action, DecisionType
from autonomy.execution import get_execution_layer
from autonomy.measurement import get_measurement_layer
from autonomy.feedback_loop import create_complete_feedback_loop
from autonomy.institutional_contracts import get_council


class AutonomousController:
    """
    Complete control plane for Agentco.

    Orchestrates all autonomy systems into a coherent whole.
    """

    def __init__(self):
        self.objective = get_objective()
        self.decision_engine = get_decision_engine()
        self.execution_layer = get_execution_layer()
        self.measurement_layer = get_measurement_layer()
        self.feedback_system = create_complete_feedback_loop()
        self.council = get_council()

        self.autonomy_cycles = []
        self.decisions_executed = 0
        self.decisions_successful = 0

        # Register actions that can be taken
        self._register_actions()

        # Establish baseline
        self.measurement_layer.establish_baseline()

    def _register_actions(self):
        """Register all possible autonomous actions."""
        actions = [
            Action(
                name="improve_evidence_sources",
                description="Add diverse evidence sources and improve calibration",
                decision_type=DecisionType.STRUCTURAL,
                estimated_cost=50.0,
                predicted_outcomes={
                    'trustworthiness': 0.12,
                    'capability': 0.05,
                    'autonomy': -0.03,
                    'coherence': 0.04,
                    'efficiency': -0.10
                },
                confidence_in_prediction=0.75
            ),
            Action(
                name="optimize_decision_process",
                description="Speed up decision-making while maintaining quality",
                decision_type=DecisionType.OPERATIONAL,
                estimated_cost=30.0,
                predicted_outcomes={
                    'trustworthiness': 0.02,
                    'capability': 0.08,
                    'autonomy': 0.10,
                    'coherence': 0.03,
                    'efficiency': 0.15
                },
                confidence_in_prediction=0.65
            ),
            Action(
                name="strengthen_institutional_coordination",
                description="Build contracts between institutions for better collaboration",
                decision_type=DecisionType.COORDINATION,
                estimated_cost=40.0,
                predicted_outcomes={
                    'trustworthiness': 0.05,
                    'capability': 0.07,
                    'autonomy': 0.08,
                    'coherence': 0.15,
                    'efficiency': 0.05
                },
                confidence_in_prediction=0.70
            ),
            Action(
                name="implement_meta_learning",
                description="Enhance system's ability to improve itself",
                decision_type=DecisionType.LEARNING,
                estimated_cost=60.0,
                predicted_outcomes={
                    'trustworthiness': 0.10,
                    'capability': 0.10,
                    'autonomy': 0.15,
                    'coherence': 0.08,
                    'efficiency': -0.05
                },
                confidence_in_prediction=0.60
            ),
            Action(
                name="refine_confidence_calibration",
                description="Improve accuracy of confidence estimates",
                decision_type=DecisionType.LEARNING,
                estimated_cost=35.0,
                predicted_outcomes={
                    'trustworthiness': 0.15,
                    'capability': 0.03,
                    'autonomy': 0.02,
                    'coherence': 0.05,
                    'efficiency': 0.02
                },
                confidence_in_prediction=0.80
            ),
        ]

        for action in actions:
            self.decision_engine.register_action(action)

    def run_autonomy_cycle(self, situation: Dict) -> Dict:
        """
        Run one complete autonomy cycle:
        Decision → Execution → Measurement → Learning
        """

        cycle_id = f"cycle_{len(self.autonomy_cycles) + 1}"
        cycle_start = datetime.now()

        # PHASE 1: DECISION
        decision = self.decision_engine.make_decision(situation)

        if 'error' in decision:
            return {
                'cycle_id': cycle_id,
                'status': 'FAILED',
                'error': decision['error'],
                'timestamp': cycle_start.isoformat()
            }

        decision_id = decision['decision_id']
        chosen_action = decision['chosen_action']

        # PHASE 2: EXECUTION
        execution_result = self.execution_layer.execute_decision(
            chosen_action.name,
            {'decision_id': decision_id}
        )

        if not execution_result.executed:
            return {
                'cycle_id': cycle_id,
                'decision_id': decision_id,
                'status': 'EXECUTION_FAILED',
                'error': execution_result.status,
                'timestamp': cycle_start.isoformat()
            }

        # PHASE 3: MEASUREMENT
        actual_outcomes = self.measurement_layer.measure_outcomes(
            execution_result.__dict__
        )

        # PHASE 4: OUTCOME RECORDING
        # Record in decision engine
        outcome_record = self.decision_engine.record_outcome(
            decision_id,
            actual_outcomes
        )

        # PHASE 5: FEEDBACK & LEARNING
        # Close feedback loop
        loop_result = self.feedback_system['loop_closer'].record_measurement(
            decision_id,
            actual_outcomes
        )

        # PHASE 6: META-LEARNING
        # Update objective function with outcomes
        for component_name, outcome_value in actual_outcomes.items():
            if component_name in self.objective.components:
                current = self.objective.components[component_name].current_value
                new_value = current + (outcome_value * 0.1)  # Weighted update
                self.objective.update_component(component_name, new_value)

        # Record cycle
        cycle_record = {
            'cycle_id': cycle_id,
            'decision_id': decision_id,
            'situation': situation,
            'chosen_action': chosen_action.name,
            'predicted_outcomes': decision['reasoning']['predicted_utility_change'],
            'actual_outcomes': actual_outcomes,
            'execution_status': execution_result.status,
            'execution_outputs': execution_result.outputs,
            'utility_before': self.objective.calculate_utility(),
            'utility_after': self.objective.calculate_utility(),
            'timestamp': cycle_start.isoformat(),
            'duration': (datetime.now() - cycle_start).total_seconds()
        }

        self.autonomy_cycles.append(cycle_record)
        self.decisions_executed += 1

        if outcome_record.get('actual_utility_change', 0) > 0:
            self.decisions_successful += 1

        return {
            'cycle_id': cycle_id,
            'status': 'SUCCESS',
            'decision': chosen_action.name,
            'actual_outcomes': actual_outcomes,
            'outcome_record': outcome_record,
            'utility_change': outcome_record.get('actual_utility_change', 0),
            'timestamp': cycle_start.isoformat()
        }

    def get_autonomy_status(self) -> Dict:
        """Get complete status of autonomous operation."""
        return {
            'cycles_completed': len(self.autonomy_cycles),
            'decisions_executed': self.decisions_executed,
            'decisions_successful': self.decisions_successful,
            'success_rate': self.decisions_successful / max(1, self.decisions_executed),
            'current_utility': self.objective.calculate_utility(),
            'objective_status': self.objective.get_status(),
            'measurement_summary': self.measurement_layer.get_metrics_summary(),
            'decision_engine_quality': self.decision_engine.get_decision_quality(),
            'feedback_loops_closed': len(self.feedback_system['loop_closer'].completed_loops),
            'improvements_detected': len(self.feedback_system['feedback_analyzer'].patterns_detected)
        }

    def run_autonomous_period(self, duration_seconds: int, situations_provider=None):
        """
        Run autonomous cycles for a specified duration.

        Args:
            duration_seconds: How long to run
            situations_provider: Function that returns situations to respond to
        """
        import time

        if situations_provider is None:
            situations_provider = self._default_situations_provider

        start_time = time.time()
        iteration = 0

        print(f"\n{'='*100}")
        print(f"AUTONOMOUS OPERATION: {duration_seconds} seconds")
        print(f"{'='*100}\n")

        while time.time() - start_time < duration_seconds:
            elapsed = time.time() - start_time
            iteration += 1

            # Get next situation
            situation = situations_provider(iteration, elapsed)

            # Run cycle
            result = self.run_autonomy_cycle(situation)

            # Progress output
            if iteration % 25 == 0:
                status = self.get_autonomy_status()
                print(
                    f"[{int(elapsed):3d}s] Cycle {iteration:3d} | "
                    f"Utility: {status['current_utility']:.3f} | "
                    f"Success rate: {status['success_rate']:.1%} | "
                    f"Improvements: {status['improvements_detected']}"
                )

        return self.get_autonomy_status()

    def _default_situations_provider(self, iteration: int, elapsed: float) -> Dict:
        """Default situation provider."""
        situations = [
            {'type': 'structural', 'problem': 'Evidence quality needs improvement'},
            {'type': 'operational', 'problem': 'Decision latency is high'},
            {'type': 'coordination', 'problem': 'Institutional coordination is weak'},
            {'type': 'learning', 'problem': 'System making repeated errors'},
            {'type': 'learning', 'problem': 'Confidence calibration drifting'},
        ]

        # Increase urgency as time progresses
        urgency = 'normal'
        if elapsed > (600 * 0.7):  # Last 30%
            urgency = 'high'
        elif elapsed > (600 * 0.4):  # Middle section
            urgency = 'moderate'

        situation = situations[iteration % len(situations)].copy()
        situation['urgency'] = urgency
        situation['iteration'] = iteration

        return situation


# Global instance
_controller_instance = None


def get_autonomous_controller() -> AutonomousController:
    """Get the global autonomous controller."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = AutonomousController()
    return _controller_instance
