"""
Measurement Layer - Measures real outcomes from executed decisions.

Maps real system metrics to objective function components.
"""

from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomy.execution import get_execution_layer
from autonomy.objective import get_objective


@dataclass
class SystemMetrics:
    """Snapshot of system metrics at a point in time."""
    timestamp: datetime
    trustworthiness_score: float  # 0-1
    capability_score: float  # 0-1
    autonomy_score: float  # 0-1
    coherence_score: float  # 0-1
    efficiency_score: float  # 0-1
    system_state: Dict[str, int]


class MeasurementLayer:
    """
    Measures real outcomes from executed decisions.
    Maps execution results to objective function components.
    """

    def __init__(self):
        self.execution_layer = get_execution_layer()
        self.objective = get_objective()
        self.measurement_history = []
        self.baseline_state = None

    def establish_baseline(self):
        """Establish baseline metrics before any autonomous decisions."""
        state = self.execution_layer.get_system_state()
        self.baseline_state = state
        return state

    def measure_outcomes(self, execution_result: Dict) -> Dict[str, float]:
        """
        Measure the outcomes of an executed decision.
        Returns: {component_name: outcome_value}
        """
        current_state = self.execution_layer.get_system_state()

        # Calculate component scores based on real system metrics
        trustworthiness = self._measure_trustworthiness(current_state)
        capability = self._measure_capability(current_state)
        autonomy = self._measure_autonomy(current_state)
        coherence = self._measure_coherence(current_state)
        efficiency = self._measure_efficiency(current_state)

        outcomes = {
            'trustworthiness': trustworthiness,
            'capability': capability,
            'autonomy': autonomy,
            'coherence': coherence,
            'efficiency': efficiency,
        }

        # Record metrics
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            trustworthiness_score=trustworthiness,
            capability_score=capability,
            autonomy_score=autonomy,
            coherence_score=coherence,
            efficiency_score=efficiency,
            system_state=current_state
        )
        self.measurement_history.append(metrics)

        return outcomes

    def _measure_trustworthiness(self, state: Dict) -> float:
        """
        Measure trustworthiness from:
        - Evidence quality (more sources → better)
        - Evidence validation (more claims → more validation)
        - Proposal approval rate (better governance → higher rate)
        """
        if not self.baseline_state:
            return 0.5

        # Evidence growth indicates better validation
        evidence_growth = min(
            1.0,
            (state['evidence_sources'] / max(1, self.baseline_state['evidence_sources'] + 10))
        )

        # Claims generation shows evidence processing
        claims_growth = min(
            1.0,
            (state['evidence_claims'] / max(1, self.baseline_state['evidence_claims'] + 20))
        )

        # Proposal approval rate
        approval_rate = 0.0
        if state['proposals_made'] > 0:
            approval_rate = state['proposals_approved'] / state['proposals_made']

        return (evidence_growth * 0.3 + claims_growth * 0.3 + approval_rate * 0.4)

    def _measure_capability(self, state: Dict) -> float:
        """
        Measure capability from:
        - Memory accumulation (more experiences → more capable)
        - Learning proposals (more hypotheses → more capability)
        - Simulation results (more testing → more capability)
        """
        if not self.baseline_state:
            return 0.5

        # Memory growth shows accumulated knowledge
        memory_growth = min(
            1.0,
            (state['memory_experiential'] / max(1, self.baseline_state['memory_experiential'] + 50))
        )

        # Learning proposals show hypothesis generation
        learning_growth = min(
            1.0,
            (state['learning_proposals'] / max(1, self.baseline_state['learning_proposals'] + 10))
        )

        # Simulation results show testing capability
        sim_growth = min(
            1.0,
            (state['simulation_results'] / max(1, self.baseline_state['simulation_results'] + 20))
        )

        return (memory_growth * 0.4 + learning_growth * 0.3 + sim_growth * 0.3)

    def _measure_autonomy(self, state: Dict) -> float:
        """
        Measure autonomy from:
        - Proposals made (system initiating changes)
        - Approval rate (system making decisions)
        - Institutional growth (system adapting structure)
        """
        if not self.baseline_state:
            return 0.5

        # Proposals per iteration show decision-making
        proposals_intensity = min(
            1.0,
            (state['proposals_made'] / max(1, self.baseline_state['proposals_made'] + 30))
        )

        # Approval rate shows governance autonomy
        approval_rate = 0.0
        if state['proposals_made'] > 0:
            approval_rate = state['proposals_approved'] / state['proposals_made']

        # Institutional growth shows structural autonomy
        institutional_growth = min(
            1.0,
            (state['institutions'] / max(1, self.baseline_state['institutions'] + 2))
        )

        return (proposals_intensity * 0.4 + approval_rate * 0.4 + institutional_growth * 0.2)

    def _measure_coherence(self, state: Dict) -> float:
        """
        Measure coherence from:
        - Proposal approval rate (governance coherence)
        - Evidence-learning integration (all systems aligned)
        - Institutional coordination (institutions working together)
        """
        if not self.baseline_state:
            return 0.5

        # Approval rate shows internal consistency
        approval_rate = 0.0
        if state['proposals_made'] > 0:
            approval_rate = state['proposals_approved'] / state['proposals_made']

        # Integration measure: are all systems growing proportionally?
        evidence_ratio = state['evidence_claims'] / max(1, state['evidence_sources'] + 1)
        learning_ratio = state['memory_experiential'] / max(1, state['learning_proposals'] + 1)

        # Higher ratios suggest good integration
        integration_coherence = min(1.0, (evidence_ratio + learning_ratio) / 4.0)

        # Institutional coherence: proposals across multiple institutions
        institutional_diversity = min(
            1.0,
            (state['institutions'] / 5.0)  # Expecting up to 5 institutions
        )

        return (approval_rate * 0.4 + integration_coherence * 0.3 + institutional_diversity * 0.3)

    def _measure_efficiency(self, state: Dict) -> float:
        """
        Measure efficiency from:
        - Throughput (proposals per resources used)
        - Resource utilization
        - Lean operations
        """
        # Simplified efficiency: are we getting results without explosion?
        total_activity = (
            state['proposals_made'] +
            state['learning_proposals'] +
            state['simulation_results']
        )

        # Efficiency: proposals per unit of memory/evidence used
        total_resources = (
            state['evidence_claims'] +
            state['memory_experiential'] +
            state['simulation_results']
        ) + 1  # Avoid division by zero

        efficiency = min(1.0, total_activity / (total_resources * 2.0))

        return efficiency

    def get_metrics_summary(self) -> Dict:
        """Get summary of all measurements."""
        if not self.measurement_history:
            return {
                'measurements': 0,
                'components': {}
            }

        latest = self.measurement_history[-1]

        return {
            'measurements': len(self.measurement_history),
            'latest_timestamp': latest.timestamp.isoformat(),
            'components': {
                'trustworthiness': latest.trustworthiness_score,
                'capability': latest.capability_score,
                'autonomy': latest.autonomy_score,
                'coherence': latest.coherence_score,
                'efficiency': latest.efficiency_score,
            },
            'system_state': latest.system_state,
            'trends': self._calculate_trends()
        }

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate trends over time."""
        if len(self.measurement_history) < 2:
            return {}

        latest = self.measurement_history[-1]
        previous = self.measurement_history[-2]

        trends = {}
        for component in ['trustworthiness', 'capability', 'autonomy', 'coherence', 'efficiency']:
            latest_val = getattr(latest, f'{component}_score')
            prev_val = getattr(previous, f'{component}_score')

            if latest_val > prev_val:
                trends[component] = 'improving'
            elif latest_val < prev_val:
                trends[component] = 'declining'
            else:
                trends[component] = 'stable'

        return trends


# Global instance
_measurement_layer = None


def get_measurement_layer() -> MeasurementLayer:
    """Get the global measurement layer."""
    global _measurement_layer
    if _measurement_layer is None:
        _measurement_layer = MeasurementLayer()
    return _measurement_layer
