"""
Agentco Internal Objective Function

Defines what Agentco is trying to optimize for.
Not external metrics - what the system itself pursues.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import json
from datetime import datetime


@dataclass
class UtilityComponent:
    """A single dimension of utility that Agentco optimizes for."""
    name: str
    description: str
    weight: float  # 0-1, normalized
    current_value: float = 0.0  # 0-1, how well we're doing on this dimension
    historical_values: List[float] = field(default_factory=list)
    improvement_rate: float = 0.0  # How fast this dimension is improving


class InternalObjective:
    """
    Agentco's internal optimization objective.

    The system makes decisions to maximize this utility function.
    This can evolve through meta-learning.
    """

    def __init__(self):
        """Initialize with baseline objective function."""
        self.components: Dict[str, UtilityComponent] = {
            'trustworthiness': UtilityComponent(
                name='trustworthiness',
                description='Accuracy of claims, calibrated confidence, low hallucination rate',
                weight=0.35,
                current_value=0.5
            ),
            'capability': UtilityComponent(
                name='capability',
                description='Ability to solve complex problems, breadth of knowledge, reasoning depth',
                weight=0.25,
                current_value=0.5
            ),
            'autonomy': UtilityComponent(
                name='autonomy',
                description='Decisions made without external input, self-correction, self-improvement',
                weight=0.20,
                current_value=0.5
            ),
            'coherence': UtilityComponent(
                name='coherence',
                description='Internal consistency, alignment between modules, coordinated action',
                weight=0.15,
                current_value=0.5
            ),
            'efficiency': UtilityComponent(
                name='efficiency',
                description='Resource utilization, decision speed, minimized compute overhead',
                weight=0.05,
                current_value=0.5
            ),
        }

        # Ensure weights sum to 1
        self._normalize_weights()

        self.creation_timestamp = datetime.now()
        self.decisions_made = 0
        self.utility_history: List[float] = []
        self.meta_observations: List[Dict] = []

    def _normalize_weights(self):
        """Ensure weights sum to 1."""
        total = sum(c.weight for c in self.components.values())
        if total > 0:
            for component in self.components.values():
                component.weight /= total

    def calculate_utility(self) -> float:
        """
        Calculate total utility based on component values and weights.
        Range: 0-1
        """
        total = sum(
            component.weight * component.current_value
            for component in self.components.values()
        )
        return min(1.0, max(0.0, total))

    def update_component(self, name: str, new_value: float):
        """Update a component's current value."""
        if name in self.components:
            component = self.components[name]
            old_value = component.current_value
            component.current_value = min(1.0, max(0.0, new_value))

            # Track improvement rate
            if component.historical_values:
                component.improvement_rate = component.current_value - component.historical_values[-1]

            component.historical_values.append(component.current_value)

    def evaluate_action(self, action_description: str,
                       predicted_outcomes: Dict[str, float]) -> Dict:
        """
        Evaluate an action by predicting its impact on utility.

        Args:
            action_description: What the action is
            predicted_outcomes: {component_name: predicted_change}

        Returns:
            {
                'action': str,
                'predicted_utility_change': float,
                'component_impacts': Dict,
                'recommendation': str (approve/reject/investigate)
            }
        """
        # Calculate predicted new utility
        predicted_utilities = {}
        total_impact = 0.0

        for component_name, predicted_change in predicted_outcomes.items():
            if component_name in self.components:
                component = self.components[component_name]
                new_value = component.current_value + predicted_change
                new_value = min(1.0, max(0.0, new_value))
                predicted_utilities[component_name] = new_value

                # Weight the impact
                impact = (new_value - component.current_value) * component.weight
                total_impact += impact

        # Current utility
        current_utility = self.calculate_utility()

        # Recommendation
        if total_impact > 0.05:
            recommendation = 'APPROVE'  # Significant improvement
        elif total_impact > 0.0:
            recommendation = 'APPROVE'  # Marginal improvement
        elif total_impact > -0.02:
            recommendation = 'INVESTIGATE'  # Minimal cost
        else:
            recommendation = 'REJECT'  # Significant harm

        return {
            'action': action_description,
            'current_utility': current_utility,
            'predicted_utility': current_utility + total_impact,
            'predicted_utility_change': total_impact,
            'component_impacts': predicted_outcomes,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }

    def record_outcome(self, action_description: str,
                      actual_outcomes: Dict[str, float],
                      predicted_outcomes: Dict[str, float]):
        """
        Record actual outcomes vs predictions for learning.
        This is how meta-learning improves the objective function.
        """
        prediction_errors = {}
        for component_name in predicted_outcomes:
            predicted = predicted_outcomes.get(component_name, 0)
            actual = actual_outcomes.get(component_name, 0)
            error = actual - predicted
            prediction_errors[component_name] = error

        observation = {
            'action': action_description,
            'predicted_outcomes': predicted_outcomes,
            'actual_outcomes': actual_outcomes,
            'prediction_errors': prediction_errors,
            'timestamp': datetime.now().isoformat()
        }

        self.meta_observations.append(observation)

    def get_status(self) -> Dict:
        """Get current status of objective function."""
        return {
            'current_utility': self.calculate_utility(),
            'components': {
                name: {
                    'value': comp.current_value,
                    'weight': comp.weight,
                    'improvement_rate': comp.improvement_rate,
                    'history_length': len(comp.historical_values)
                }
                for name, comp in self.components.items()
            },
            'decisions_made': self.decisions_made,
            'utility_history_length': len(self.utility_history),
            'meta_observations': len(self.meta_observations)
        }


# Global instance
_objective_instance = None

def get_objective() -> InternalObjective:
    """Get the global objective function instance."""
    global _objective_instance
    if _objective_instance is None:
        _objective_instance = InternalObjective()
    return _objective_instance
