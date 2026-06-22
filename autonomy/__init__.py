"""
Agentco True Autonomy Layer

Complete, fully-integrated autonomy system with:
- Internal objective function (what the system optimizes for)
- Decision engine (real decision-making via utility maximization)
- Execution layer (translates decisions to real system actions)
- Measurement layer (maps real outcomes to objective components)
- Institutional contracts (explicit interdependencies)
- Feedback loops (closed loops connecting actions to learning)
- Meta-learning (system improving its own reasoning)
- Integration layer (orchestrates all systems into coherent whole)
- LLM Service (provider-agnostic, works with any LLM)
"""

from autonomy.objective import InternalObjective, get_objective
from autonomy.decision_engine import DecisionEngine, get_decision_engine, Action, DecisionType
from autonomy.execution import ExecutionLayer, get_execution_layer, ExecutionResult
from autonomy.measurement import MeasurementLayer, get_measurement_layer, SystemMetrics
from autonomy.institutional_contracts import (
    InstitutionalCouncil, InstitutionalContract,
    ServiceRequirement, ServiceProvision, get_council
)
from autonomy.feedback_loop import (
    FeedbackAnalyzer, LoopCloser, MetaLearner,
    Feedback, FeedbackType, create_complete_feedback_loop
)
from autonomy.integration import AutonomousController, get_autonomous_controller
from autonomy.llm_service import LLMService, LLMServiceFactory, get_llm

__all__ = [
    'InternalObjective', 'get_objective',
    'DecisionEngine', 'get_decision_engine', 'Action', 'DecisionType',
    'ExecutionLayer', 'get_execution_layer', 'ExecutionResult',
    'MeasurementLayer', 'get_measurement_layer', 'SystemMetrics',
    'InstitutionalCouncil', 'InstitutionalContract',
    'ServiceRequirement', 'ServiceProvision', 'get_council',
    'FeedbackAnalyzer', 'LoopCloser', 'MetaLearner',
    'Feedback', 'FeedbackType', 'create_complete_feedback_loop',
    'AutonomousController', 'get_autonomous_controller',
    'LLMService', 'LLMServiceFactory', 'get_llm',
]
