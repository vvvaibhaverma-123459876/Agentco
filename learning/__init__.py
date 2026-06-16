"""
AgentCo V2 — Continuous Learning Loop (Phase 3).

6-hour cycle: Intelligence → Scenario → Trainer → Memory
All proposals gated by human approval before becoming active.
No learning update goes live without a human sign-off.
"""
from .intelligence_agent.intelligence_agent import IntelligenceAgent
from .scenario_agent.scenario_agent import ScenarioAgent
from .trainer_agent.trainer_agent import TrainerAgent
from .memory_agent.memory_agent import MemoryAgent
from .learning_loop import LearningLoop

__all__ = ["IntelligenceAgent", "ScenarioAgent", "TrainerAgent", "MemoryAgent", "LearningLoop"]
