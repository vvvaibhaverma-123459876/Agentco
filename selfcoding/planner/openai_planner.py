#!/usr/bin/env python3
"""
OPENAI PLANNER: Converts human goals to BUILD SPEC.

Takes: Human goal ("build a momentum detector")
Produces: Structured BUILD SPEC for the coder
Uses: OpenAI gpt-4o-mini (cheap, reasoning)

The planner NEVER executes code, touches data, or modifies the resolver.
It only produces BUILD SPEC. The coder consumes it. The sandbox executes it.
"""
from __future__ import annotations

import json
import os
from typing import Any

from selfcoding.coder.build_spec import (
    AgentSpec,
    BuildSpec,
    DataSourceRef,
    ScenarioSpec,
)


class PlannerError(Exception):
    """Raised when planning fails."""
    pass


class OpenAIPlanHandler:
    """Planner using OpenAI gpt-4o-mini."""

    def __init__(self, api_key: str | None = None):
        """Initialize the planner with OpenAI API key."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise PlannerError("OPENAI_API_KEY not set")

    def plan(self, human_goal: str) -> BuildSpec:
        """
        Convert a human goal to a BUILD SPEC.

        Args:
            human_goal: User's high-level goal, e.g., "Build a momentum detector for NIFTY 50"

        Returns:
            BuildSpec ready for code generation

        Raises:
            PlannerError: If planning fails
        """
        # This would call OpenAI to reason about the goal and produce a spec
        # For now, return a template that demonstrates the structure
        raise NotImplementedError("OpenAI integration requires API key setup")


# Hardcoded example specs for demonstration
EXAMPLE_SPECS = {
    "momentum": lambda: BuildSpec(
        goal="Detect momentum-based price movement in NIFTY 50",
        scenario=ScenarioSpec(
            name="Momentum Detector",
            description="Predicts market direction based on recent momentum",
            agents=[
                AgentSpec(
                    name="momentum_agent",
                    role="momentum_detector",
                    description="Detects uptrend/downtrend from recent returns",
                    input_signals=["return_1d", "return_5d", "return_10d"],
                    output_format="up/down with confidence",
                    logic_description=(
                        "Calculate average of 1d, 5d, 10d returns. "
                        "If positive, predict up; if negative, predict down. "
                        "Confidence = |avg_return| / 0.01 (normalized)."
                    ),
                ),
            ],
            data_sources=[
                DataSourceRef(
                    instrument="NIFTY 50",
                    date_range="Full frozen NSE Phase 6 dataset",
                ),
            ],
            orchestration="Single agent; call score_prediction with its prediction",
            expected_output="JSON: {agent: 'momentum_agent', direction, confidence, score}",
        ),
    ),
    "mean_reversion": lambda: BuildSpec(
        goal="Detect mean-reversion opportunities in NIFTY 50",
        scenario=ScenarioSpec(
            name="Mean Reversion Detector",
            description="Predicts bounce-back when price deviates from moving average",
            agents=[
                AgentSpec(
                    name="mean_reversion_agent",
                    role="mean_reversion_detector",
                    description="Detects when price is far from moving average",
                    input_signals=["ma20_distance", "ma50_distance"],
                    output_format="up/down with confidence",
                    logic_description=(
                        "Calculate average distance from MA20 and MA50. "
                        "If negative (below MAs), predict up (bounce up). "
                        "If positive (above MAs), predict down (pull down). "
                        "Confidence = |distance| / 0.05 (normalized)."
                    ),
                ),
            ],
            data_sources=[
                DataSourceRef(
                    instrument="NIFTY 50",
                    date_range="Full frozen NSE Phase 6 dataset",
                ),
            ],
            orchestration="Single agent; call score_prediction with its prediction",
            expected_output="JSON: {agent: 'mean_reversion_agent', direction, confidence, score}",
        ),
    ),
}


def get_example_spec(scenario_type: str) -> BuildSpec:
    """Get a predefined example spec for testing."""
    if scenario_type not in EXAMPLE_SPECS:
        raise PlannerError(f"Unknown scenario: {scenario_type}. Options: {list(EXAMPLE_SPECS.keys())}")
    return EXAMPLE_SPECS[scenario_type]()


def main() -> int:
    """Demo: Show available example specs."""
    print("OpenAI Planner - Example Specifications")
    print("=" * 80)

    for scenario_type in EXAMPLE_SPECS:
        spec = get_example_spec(scenario_type)
        print(f"\nScenario: {spec.scenario.name}")
        print(f"Goal: {spec.goal}")
        print(f"Agents: {len(spec.scenario.agents)}")
        for agent in spec.scenario.agents:
            print(f"  - {agent.name}: {agent.description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
