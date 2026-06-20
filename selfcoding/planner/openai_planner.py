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
import time
from typing import Any

import requests

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
        prompt = self._build_planning_prompt(human_goal)

        print(f"[Planner] Goal: {human_goal}")
        print(f"[Planner] Calling OpenAI gpt-4o-mini...")

        start_time = time.time()

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert at converting high-level goals into structured specifications. "
                                "You produce ONLY valid JSON matching the BUILD SPEC schema. No markdown, no explanations."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                timeout=30,
            )

            if response.status_code != 200:
                raise PlannerError(
                    f"OpenAI API error: {response.status_code} {response.text[:200]}"
                )

            result = response.json()
            if "error" in result:
                raise PlannerError(f"OpenAI error: {result['error']}")

            # Extract the spec JSON from the response
            spec_json_str = result["choices"][0]["message"]["content"].strip()

            # Parse the JSON
            spec_dict = json.loads(spec_json_str)

            elapsed = time.time() - start_time
            tokens = result.get("usage", {}).get("total_tokens", 0)

            print(f"[Planner] ✓ Spec generated ({tokens} tokens, {elapsed:.2f}s)")

            # Convert dict to BuildSpec and validate
            build_spec = self._dict_to_build_spec(spec_dict, human_goal)

            valid, err = build_spec.validate()
            if not valid:
                raise PlannerError(f"Generated spec failed validation: {err}")

            print(f"[Planner] ✓ Spec validated")
            return build_spec

        except json.JSONDecodeError as e:
            raise PlannerError(f"Failed to parse OpenAI response as JSON: {e}") from e
        except requests.RequestException as e:
            raise PlannerError(f"Failed to call OpenAI: {e}") from e

    def _build_planning_prompt(self, human_goal: str) -> str:
        """Build the prompt for the planner."""
        return f"""Convert this goal into a BUILD SPEC:

Goal: {human_goal}

You MUST produce ONLY valid JSON (no markdown, no explanations). The JSON must match this schema exactly:

{{
  "goal": "The user's goal",
  "scenario": {{
    "name": "Scenario name",
    "description": "What question does this scenario answer?",
    "agents": [
      {{
        "name": "agent_name",
        "role": "agent_role",
        "description": "What does this agent do?",
        "input_signals": ["signal1", "signal2"],
        "output_format": "format description",
        "logic_description": "Plain English description of the agent logic"
      }}
    ],
    "data_sources": [
      {{
        "instrument": "NIFTY 50",
        "date_range": "Full frozen NSE Phase 6 dataset"
      }}
    ],
    "orchestration": "How are agents combined?",
    "expected_output": "What format is the output?"
  }}
}}

CONSTRAINTS:
- Agents must have 1-3 input signals from: return_1d, return_5d, return_10d, ma20_distance, ma50_distance, rsi, volume_ratio, volatility
- Data sources can be: NIFTY 50, BANK NIFTY, HDFCBANK, ICICIBANK, INFY, RELIANCE, TCS
- logic_description CANNOT mention: resolver, sealed_resolver, frozen_data, __import__, write, open(
- The spec CANNOT contain any forbidden keys

Return ONLY the JSON, no other text."""

    def _dict_to_build_spec(self, spec_dict: dict, human_goal: str) -> BuildSpec:
        """Convert a dict from OpenAI to a BuildSpec instance."""
        scenario_dict = spec_dict.get("scenario", {})

        agents = []
        for agent_dict in scenario_dict.get("agents", []):
            agents.append(
                AgentSpec(
                    name=agent_dict.get("name", ""),
                    role=agent_dict.get("role", ""),
                    description=agent_dict.get("description", ""),
                    input_signals=agent_dict.get("input_signals", []),
                    output_format=agent_dict.get("output_format", ""),
                    logic_description=agent_dict.get("logic_description", ""),
                )
            )

        data_sources = []
        for ds_dict in scenario_dict.get("data_sources", []):
            data_sources.append(
                DataSourceRef(
                    instrument=ds_dict.get("instrument", ""),
                    date_range=ds_dict.get("date_range", ""),
                )
            )

        scenario = ScenarioSpec(
            name=scenario_dict.get("name", ""),
            description=scenario_dict.get("description", ""),
            agents=agents,
            data_sources=data_sources,
            orchestration=scenario_dict.get("orchestration", ""),
            expected_output=scenario_dict.get("expected_output", ""),
        )

        return BuildSpec(
            goal=human_goal,
            scenario=scenario,
            constraints=spec_dict.get("constraints", {}),
        )


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
