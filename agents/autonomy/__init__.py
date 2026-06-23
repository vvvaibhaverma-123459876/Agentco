"""
Autonomy Specialist Agents
==========================
Specialized autonomous agents spawned by the orchestrator.
Each agent handles a specific role with bounded budgets and HTTP communication.
"""

from .specialist_agent import SpecialistAgent

__all__ = ['SpecialistAgent']
