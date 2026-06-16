"""
AgentCo V2 — Cross-Domain Synthesis (Phase 4).

Synthesis-Agent discovers cross-domain patterns.
All principles enter as provisional, firewalled.
Theory engine routes principles through the Reality/Simulation Firewall.
Nothing in synthesis reaches reality_validated without pre-registered,
externally-scored predictions resolved by an independent source.
"""
from .synthesis_agent.synthesis_agent import SynthesisAgent
from .principle_library.principle_library import PrincipleLibrary, Principle
from .theory_engine.theory_engine import TheoryEngine

__all__ = ["SynthesisAgent", "PrincipleLibrary", "Principle", "TheoryEngine"]
