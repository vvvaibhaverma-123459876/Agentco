"""
Feedback Loop System

Closes the autonomy loop:
Action → Outcome Measurement → Comparison → Learning → Better Next Decisions

This is what creates true autonomy - the system learning from its actions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    """Types of feedback."""
    OUTCOME = "outcome"  # Measured results of an action
    PREDICTION_ERROR = "prediction_error"  # Difference between predicted and actual
    SYSTEMIC_BIAS = "systemic_bias"  # Pattern of errors
    EMERGENT_PATTERN = "emergent_pattern"  # New discovery


@dataclass
class Feedback:
    """A piece of feedback about a past decision."""
    feedback_id: str
    feedback_type: FeedbackType
    decision_id: str
    description: str
    severity: float  # 0-1, how important is this
    actionable: bool  # Can we do something about it?
    suggested_adaptation: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)


class FeedbackAnalyzer:
    """
    Analyzes feedback to identify patterns and improve decision-making.
    """

    def __init__(self):
        self.feedback_history: List[Feedback] = []
        self.patterns_detected: List[Dict] = []
        self.adaptations_made: List[Dict] = []

    def add_feedback(self, feedback: Feedback):
        """Add feedback about a decision."""
        self.feedback_history.append(feedback)

        # Immediately analyze for patterns
        self._check_for_patterns()

    def _check_for_patterns(self):
        """
        Look for systematic patterns in feedback.
        This is how the system improves its own reasoning.
        """
        if len(self.feedback_history) < 5:
            return  # Need minimum sample size

        recent = self.feedback_history[-10:]  # Look at recent decisions

        # Check for systematic bias
        bad_outcomes = [f for f in recent if f.feedback_type == FeedbackType.PREDICTION_ERROR
                       and f.severity > 0.3]

        if len(bad_outcomes) >= 3:
            # Pattern detected
            pattern = {
                'type': 'systematic_error',
                'description': f'High prediction errors in {len(bad_outcomes)}/10 recent decisions',
                'severity': sum(f.severity for f in bad_outcomes) / len(bad_outcomes),
                'detected_at': datetime.now().isoformat(),
                'affected_decisions': [f.decision_id for f in bad_outcomes]
            }
            self.patterns_detected.append(pattern)

    def get_improvement_recommendations(self) -> List[Dict]:
        """
        Based on detected patterns, recommend improvements.
        """
        recommendations = []

        for pattern in self.patterns_detected:
            if pattern['type'] == 'systematic_error':
                recommendation = {
                    'pattern': pattern['type'],
                    'severity': pattern['severity'],
                    'recommendation': 'Recalibrate confidence estimation - system overestimates prediction accuracy',
                    'action': 'Add conservative discount factor to all predictions',
                    'expected_impact': 'Reduce future prediction errors by ~30%'
                }
                recommendations.append(recommendation)

        return recommendations


class LoopCloser:
    """
    Closes the feedback loop by connecting actions to learning.

    The autonomous cycle:
    1. Decision Engine makes decision → Execute
    2. Outcome Measurement observes results
    3. Feedback system analyzes outcomes
    4. Identifies patterns and errors
    5. Recommends adaptations
    6. Decision Engine learns from patterns
    7. Next decision uses improved reasoning
    """

    def __init__(self):
        self.feedback_analyzer = FeedbackAnalyzer()
        self.pending_measurements: Dict[str, Dict] = {}  # decision_id -> measurement setup
        self.completed_loops: List[Dict] = []

    def setup_measurement(self, decision_id: str,
                         metrics_to_measure: List[str],
                         measurement_delay: int = 0):
        """
        Setup measurement for a decision that was just executed.
        metrics_to_measure: what we need to measure to know if it worked
        measurement_delay: how long to wait before measuring (in iterations)
        """
        self.pending_measurements[decision_id] = {
            'metrics': metrics_to_measure,
            'delay': measurement_delay,
            'created_at': datetime.now(),
            'measured': False,
            'results': {}
        }

    def record_measurement(self, decision_id: str, measurements: Dict[str, float]):
        """
        Record measurement results for a decision.
        """
        if decision_id not in self.pending_measurements:
            return {'error': 'No measurement setup for this decision'}

        setup = self.pending_measurements[decision_id]
        setup['measured'] = True
        setup['results'] = measurements
        setup['measured_at'] = datetime.now()

        # Close the loop
        return self._close_loop(decision_id, measurements)

    def _close_loop(self, decision_id: str, measurements: Dict[str, float]) -> Dict:
        """
        Close a complete feedback loop.
        Connects decision → outcome → learning → improvement.
        """
        setup = self.pending_measurements[decision_id]

        loop_record = {
            'decision_id': decision_id,
            'setup_at': setup['created_at'].isoformat(),
            'measured_at': setup['measured_at'].isoformat(),
            'measurements': measurements,
            'feedback_generated': False,
            'improvements_identified': []
        }

        # Generate feedback based on measurements
        # (Would compare to predictions here in full system)
        # For now, create feedback and analyze

        feedback = Feedback(
            feedback_id=f"feedback_{decision_id}",
            feedback_type=FeedbackType.OUTCOME,
            decision_id=decision_id,
            description=f"Outcome measurements: {measurements}",
            severity=0.5,
            actionable=True
        )

        self.feedback_analyzer.add_feedback(feedback)
        loop_record['feedback_generated'] = True

        # Check for improvement opportunities
        improvements = self.feedback_analyzer.get_improvement_recommendations()
        if improvements:
            loop_record['improvements_identified'] = improvements

        self.completed_loops.append(loop_record)
        return loop_record

    def get_learning_summary(self) -> Dict:
        """
        What has the system learned from its feedback loops?
        """
        return {
            'total_loops_closed': len(self.completed_loops),
            'patterns_detected': len(self.feedback_analyzer.patterns_detected),
            'improvement_recommendations': len(self.feedback_analyzer.get_improvement_recommendations()),
            'patterns': self.feedback_analyzer.patterns_detected,
            'improvements_proposed': self.feedback_analyzer.get_improvement_recommendations()
        }


class MetaLearner:
    """
    Meta-learning system - learns how to learn better.

    Uses feedback from multiple feedback loops to improve the objective function itself.
    """

    def __init__(self):
        self.learning_history: List[Dict] = []
        self.adaptations_to_objective: List[Dict] = []
        self.adaptations_to_engine: List[Dict] = []

    def analyze_feedback_patterns(self, feedback_analyzer: FeedbackAnalyzer) -> Dict:
        """
        High-level analysis of feedback patterns.
        Returns suggestions for self-improvement.
        """
        patterns = feedback_analyzer.patterns_detected

        if not patterns:
            return {'improvements': []}

        improvements = []

        # Look for consistent prediction errors
        for pattern in patterns:
            if pattern['type'] == 'systematic_error':
                improvement = {
                    'type': 'confidence_calibration',
                    'description': 'System is overconfident in predictions',
                    'action': 'Add Bayesian uncertainty adjustment',
                    'expected_impact': 'Improve decision quality by ~15%',
                    'priority': 'HIGH'
                }
                improvements.append(improvement)

        return {'improvements': improvements}

    def propose_objective_adjustment(self, new_weights: Dict[str, float]) -> Dict:
        """
        Propose adjusting the objective function weights.
        E.g., if trustworthiness keeps failing, increase its weight to prioritize it.
        """
        adjustment = {
            'timestamp': datetime.now().isoformat(),
            'type': 'weight_adjustment',
            'proposed_changes': new_weights,
            'rationale': 'Based on meta-learning analysis',
            'status': 'proposed'
        }
        self.adaptations_to_objective.append(adjustment)
        return adjustment

    def get_status(self) -> Dict:
        """Meta-learner status."""
        return {
            'learning_observations': len(self.learning_history),
            'objective_adjustments_proposed': len(self.adaptations_to_objective),
            'engine_adaptations_proposed': len(self.adaptations_to_engine)
        }


def create_complete_feedback_loop() -> Dict:
    """
    Create and wire up the complete feedback loop system.
    This connects Decision Engine → Feedback → Learning → Improvement.
    """
    return {
        'feedback_analyzer': FeedbackAnalyzer(),
        'loop_closer': LoopCloser(),
        'meta_learner': MetaLearner(),
        'created_at': datetime.now().isoformat()
    }
