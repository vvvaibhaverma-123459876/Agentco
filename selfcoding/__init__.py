"""AgentCo Self-Extension System - Build structural guardrails for self-coding."""

__version__ = "1.0"
__doc__ = """
Self-extension system for AgentCo with structural guardrails.

The system is divided into four stops:
1. SEALED RESOLVER + FROZEN DATA - The wall (immutable resolver, read-only data)
2. SANDBOX + ADVERSARIAL BREACH TEST - Proving the wall holds (12 breach tests)
3. QWEN CODER - Code generation from BUILD SPEC (local, cost-free)
4. OPENAI PLANNER - Goal → BUILD SPEC (cheap reasoning)

The primary deliverable is the structural wall (STOP 1-2).
"""
