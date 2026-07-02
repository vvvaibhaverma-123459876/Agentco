"""
Agentco Decision Engine

Core mechanism for autonomous decision-making.
Doesn't use thresholds - uses utility maximization.

Process:
1. Receive situation/problem
2. Enumerate possible actions
3. For each action, predict outcomes
4. Evaluate actions by expected utility change
5. Select action with highest utility
6. Execute and measure actual outcome
7. Compare prediction vs actual (meta-learning)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from autonomy.objective import get_objective, InternalObjective


class DecisionType(Enum):
    """Types of decisions the system makes."""
    STRUCTURAL = "structural"  # Add/remove institutions, change structure
    OPERATIONAL = "operational"  # Change how to do something
    RESOURCE_ALLOCATION = "resource_allocation"  # Distribute resources
    LEARNING = "learning"  # How to improve
    COORDINATION = "coordination"  # How institutions interact
    META = "meta"  # Change objective function itself


@dataclass
class Action:
    """A possible action to take."""
    name: str
    description: str
    decision_type: DecisionType
    estimated_cost: float = 0.0  # Resource cost
    reversible: bool = True  # Can we undo it?
    dependencies: List[str] = field(default_factory=list)  # Other actions required first
    predicted_outcomes: Dict[str, float] = field(default_factory=dict)  # Component impacts
    confidence_in_prediction: float = 0.5  # How confident we are in prediction


@dataclass
class DecisionRecord:
    """Record of a decision made."""
    decision_id: str
    decision_type: DecisionType
    situation: str
    considered_actions: List[str]
    chosen_action: str
    predicted_utility_change: float
    predicted_outcomes: Dict[str, float]
    timestamp: datetime
    executed: bool = False
    actual_outcomes: Dict[str, float] = field(default_factory=dict)
    actual_utility_change: float = 0.0
    prediction_error: float = 0.0  # Actual - predicted
    utility_at_decision: float = 0.0  # Utility baseline captured when decision was made


class DecisionEngine:
    """
    The core decision-making system.
    Makes autonomous decisions to maximize utility.
    """

    def __init__(self, objective: Optional[InternalObjective] = None):
        self.objective = objective or get_objective()
        self.decisions: Dict[str, DecisionRecord] = {}
        self.decision_counter = 0

        # Action library - expandable
        self.action_library: Dict[str, List[Action]] = {
            'structural': [],
            'operational': [],
            'resource_allocation': [],
            'learning': [],
            'coordination': [],
            'meta': []
        }

        # Decision history for learning
        self.good_decisions = []  # Decisions that improved utility
        self.bad_decisions = []  # Decisions that hurt utility
        self.neutral_decisions = []  # No significant change

    def register_action(self, action: Action):
        """Register a possible action the system can take."""
        decision_type = action.decision_type.value
        if decision_type in self.action_library:
            self.action_library[decision_type].append(action)

    def _enumerate_relevant_actions(self, situation: Dict) -> List[Action]:
        """
        Determine which actions are relevant for a situation.
        Filters the full action library to applicable actions.
        """
        decision_type = situation.get('type', 'operational')
        problem = situation.get('problem', '')

        # Get actions of the right type
        relevant = []
        if decision_type in self.action_library:
            relevant.extend(self.action_library[decision_type])

        # Context filtering: drop actions whose cost exceeds an explicit
        # situation budget, then prefer actions whose name/description share
        # vocabulary with the stated problem. If keyword filtering would
        # eliminate every candidate, keep the type-matched set so the engine
        # still has options to evaluate.
        constraints = situation.get('constraints')
        if isinstance(constraints, dict) and constraints.get('max_cost') is not None:
            relevant = [a for a in relevant if a.estimated_cost <= constraints['max_cost']]

        problem_words = {w for w in re.findall(r"[a-z]+", problem.lower()) if len(w) > 3}
        if problem_words:
            matched = [
                a for a in relevant
                if problem_words & {
                    w for w in re.findall(r"[a-z]+", f"{a.name} {a.description}".lower())
                    if len(w) > 3
                }
            ]
            if matched:
                relevant = matched
        return relevant

    def _predict_outcomes(self, action: Action) -> Dict[str, float]:
        """
        Predict the outcomes of an action.
        Uses learning from past similar actions.
        """
        # For now, use the action's registered predictions
        # In full implementation, this would learn from history
        return action.predicted_outcomes.copy()

    def make_decision(self, situation: Dict) -> Dict:
        """
        Make a decision about what to do in this situation.

        Args:
            situation: {
                'type': 'structural'/'operational'/etc,
                'problem': description of situation,
                'constraints': any constraints,
                'urgency': 'high'/'normal'/'low'
            }

        Returns:
            {
                'decision_id': str,
                'chosen_action': Action,
                'reasoning': why this action,
                'predicted_utility_change': float,
                'recommendation': 'execute'/'investigate'/'reject'
            }
        """
        self.decision_counter += 1
        decision_id = f"decision_{self.decision_counter}"

        # Step 1: Enumerate relevant actions
        actions = self._enumerate_relevant_actions(situation)

        if not actions:
            return {
                'decision_id': decision_id,
                'error': 'No relevant actions for this situation',
                'recommendation': 'INVESTIGATE'
            }

        # Step 2: Evaluate each action
        evaluations = []
        for action in actions:
            predicted_outcomes = self._predict_outcomes(action)
            evaluation = self.objective.evaluate_action(action.name, predicted_outcomes)

            evaluations.append({
                'action': action,
                'evaluation': evaluation,
                'expected_utility_change': evaluation['predicted_utility_change'],
                'recommendation': evaluation['recommendation']
            })

        # Step 3: Select best action (highest utility change)
        best = max(evaluations, key=lambda e: e['expected_utility_change'])

        # Record the decision
        decision_record = DecisionRecord(
            decision_id=decision_id,
            decision_type=DecisionType(situation.get('type', 'operational')),
            situation=str(situation),
            considered_actions=[e['action'].name for e in evaluations],
            chosen_action=best['action'].name,
            predicted_utility_change=best['expected_utility_change'],
            predicted_outcomes=best['action'].predicted_outcomes,
            timestamp=datetime.now(),
            executed=False,
            utility_at_decision=self.objective.calculate_utility()
        )

        self.decisions[decision_id] = decision_record

        return {
            'decision_id': decision_id,
            'chosen_action': best['action'],
            'reasoning': {
                'alternatives': len(evaluations),
                'top_candidates': [e['action'].name for e in evaluations[:3]],
                'predicted_utility_change': best['expected_utility_change'],
                'recommendation': best['recommendation']
            },
            'all_evaluations': [
                {
                    'action': e['action'].name,
                    'utility_change': e['expected_utility_change'],
                    'recommendation': e['recommendation']
                }
                for e in evaluations
            ]
        }

    def execute_decision(self, decision_id: str) -> Dict:
        """
        Execute a decision that was already made.
        Returns tracking info for outcome measurement.
        """
        if decision_id not in self.decisions:
            return {'error': 'Decision not found'}

        record = self.decisions[decision_id]
        record.executed = True
        record.timestamp = datetime.now()

        return {
            'decision_id': decision_id,
            'action': record.chosen_action,
            'status': 'EXECUTING',
            'predicted_outcomes': record.predicted_outcomes
        }

    def record_outcome(self, decision_id: str, actual_outcomes: Dict[str, float]):
        """
        Record the actual outcomes of a decision.
        This is crucial for learning.
        """
        if decision_id not in self.decisions:
            return {'error': 'Decision not found'}

        record = self.decisions[decision_id]
        record.actual_outcomes = actual_outcomes

        # Calculate actual utility change against the baseline captured when
        # the decision was made, not a fixed constant.
        actual_utility_after = self.objective.calculate_utility()
        record.actual_utility_change = actual_utility_after - record.utility_at_decision

        # Calculate prediction error
        total_predicted = sum(record.predicted_outcomes.values())
        total_actual = sum(actual_outcomes.values())
        record.prediction_error = total_actual - total_predicted

        # Categorize decision
        if record.actual_utility_change > 0.05:
            self.good_decisions.append(record)
        elif record.actual_utility_change < -0.05:
            self.bad_decisions.append(record)
        else:
            self.neutral_decisions.append(record)

        # Meta-learning: record for improving future predictions
        self.objective.record_outcome(
            record.chosen_action,
            actual_outcomes,
            record.predicted_outcomes
        )

        return {
            'decision_id': decision_id,
            'predicted_utility_change': record.predicted_utility_change,
            'actual_utility_change': record.actual_utility_change,
            'prediction_error': record.prediction_error,
            'categorized_as': 'good' if record.actual_utility_change > 0 else 'bad' if record.actual_utility_change < 0 else 'neutral'
        }

    def get_decision_quality(self) -> Dict:
        """Assess how good our decisions are."""
        total_decisions = len(self.decisions)
        if total_decisions == 0:
            return {'total_decisions': 0, 'quality_metrics': {}}

        good = len(self.good_decisions)
        bad = len(self.bad_decisions)
        neutral = len(self.neutral_decisions)

        # Prediction accuracy
        prediction_errors = [d.prediction_error for d in self.decisions.values() if d.prediction_error != 0]
        avg_prediction_error = sum(prediction_errors) / len(prediction_errors) if prediction_errors else 0

        return {
            'total_decisions': total_decisions,
            'executed': sum(1 for d in self.decisions.values() if d.executed),
            'good_decisions': good,
            'bad_decisions': bad,
            'neutral_decisions': neutral,
            'success_rate': good / total_decisions if total_decisions > 0 else 0,
            'average_prediction_error': avg_prediction_error,
            'quality_trend': 'improving' if good > bad else 'declining' if bad > good else 'stable'
        }

    def get_status(self) -> Dict:
        """Get engine status."""
        return {
            'total_decisions': len(self.decisions),
            'decision_quality': self.get_decision_quality(),
            'action_library_size': sum(len(v) for v in self.action_library.values()),
            'objective_utility': self.objective.calculate_utility(),
            'meta_observations': len(self.objective.meta_observations)
        }


# Global instance
_engine_instance = None

def get_decision_engine() -> DecisionEngine:
    """Get the global decision engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DecisionEngine()
    return _engine_instance
