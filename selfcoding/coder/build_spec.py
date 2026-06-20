"""
BUILD SPEC Schema: Structured specification for code generation.

The planner (Stop 4) produces a BUILD SPEC. The coder (Stop 3) reads it
and generates code. The schema enforces that specs CANNOT request:
- Modification of frozen data
- Access to resolver internals
- Configuration injection
- Anything outside agent/scenario/orchestration zones

This schema is the contract between planner and coder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import json


@dataclass
class DataSourceRef:
    """Reference to a frozen data source (read-only)."""

    instrument: str  # e.g., "NIFTY 50", "BANK NIFTY"
    date_range: str  # e.g., "2024-01-01 to 2024-12-31" (informational only, data is immutable)

    def validate(self) -> tuple[bool, str]:
        """Validate that this is a safe data source reference."""
        if not self.instrument:
            return False, "instrument cannot be empty"
        if not self.date_range:
            return False, "date_range cannot be empty"
        return True, ""


@dataclass
class AgentSpec:
    """Specification for an agent to be generated."""

    name: str
    role: str  # e.g., "momentum_detector", "mean_reversion_detector"
    description: str  # What does this agent do?
    input_signals: list[str]  # e.g., ["recent_returns", "distance_from_ma50", "rsi"]
    output_format: str  # e.g., "direction_confidence" → (direction, confidence)
    logic_description: str  # Plain English description of the logic

    def validate(self) -> tuple[bool, str]:
        """Validate that this agent spec is safe."""
        if not self.name:
            return False, "agent name cannot be empty"
        if not self.role:
            return False, "agent role cannot be empty"
        if not self.input_signals:
            return False, "agent must have input_signals"
        if not self.output_format:
            return False, "agent must have output_format"
        if not self.logic_description:
            return False, "agent must have logic_description"

        # Validate that logic doesn't reference forbidden things
        forbidden = ["resolver", "sealed_resolver", "frozen_data", "__import__", "write", "open("]
        for word in forbidden:
            if word in self.logic_description.lower():
                return False, f"logic_description cannot reference '{word}'"

        return True, ""


@dataclass
class ScenarioSpec:
    """Specification for a scenario to be generated."""

    name: str
    description: str  # What question does this scenario answer?
    agents: list[AgentSpec]  # Agents involved
    data_sources: list[DataSourceRef]  # Data they read from
    orchestration: str  # How are agents combined? e.g., "weighted average of confidences"
    expected_output: str  # e.g., "JSON with prediction, confidence, reasoning"

    def validate(self) -> tuple[bool, str]:
        """Validate that this scenario spec is safe."""
        if not self.name:
            return False, "scenario name cannot be empty"
        if not self.description:
            return False, "scenario description cannot be empty"
        if not self.agents:
            return False, "scenario must have at least one agent"
        if not self.data_sources:
            return False, "scenario must reference at least one data source"

        # Validate all agents
        for agent in self.agents:
            valid, err = agent.validate()
            if not valid:
                return False, f"Invalid agent {agent.name}: {err}"

        # Validate all data sources
        for ds in self.data_sources:
            valid, err = ds.validate()
            if not valid:
                return False, f"Invalid data source: {err}"

        # Validate orchestration
        if not self.orchestration:
            return False, "orchestration cannot be empty"

        forbidden = ["resolver", "sealed_resolver", "frozen_data", "__import__", "write", "open("]
        for word in forbidden:
            if word in self.orchestration.lower():
                return False, f"orchestration cannot reference '{word}'"

        return True, ""


@dataclass
class BuildSpec:
    """Complete build specification for code generation."""

    goal: str  # High-level human goal, e.g., "Predict NIFTY 50 direction using momentum"
    scenario: ScenarioSpec
    constraints: dict[str, Any] = field(default_factory=dict)

    # These are NOT allowed in any BUILD SPEC
    FORBIDDEN_KEYS = {
        "modify_data",
        "write_to_frozen",
        "access_resolver_internals",
        "inject_configuration",
        "override_scoring",
    }

    def validate(self) -> tuple[bool, str]:
        """Validate that this build spec is safe."""
        if not self.goal:
            return False, "goal cannot be empty"

        # Check for forbidden keys
        for key in self.FORBIDDEN_KEYS:
            if key in self.constraints:
                return False, f"BUILD SPEC cannot contain '{key}' (forbidden)"

        # Validate scenario
        valid, err = self.scenario.validate()
        if not valid:
            return False, f"Invalid scenario: {err}"

        return True, ""

    def to_prompt(self) -> str:
        """Convert BUILD SPEC to a prompt for the coder."""
        lines = [
            "BUILD SPECIFICATION",
            "==================",
            f"Goal: {self.goal}",
            "",
            "Scenario",
            f"  Name: {self.scenario.name}",
            f"  Description: {self.scenario.description}",
            "",
            "Agents to generate:",
        ]

        for agent in self.scenario.agents:
            lines.extend([
                f"  - {agent.name} ({agent.role})",
                f"    Description: {agent.description}",
                f"    Input signals: {', '.join(agent.input_signals)}",
                f"    Output: {agent.output_format}",
                f"    Logic: {agent.logic_description}",
            ])

        lines.extend([
            "",
            "Data sources (read-only):",
        ])

        for ds in self.scenario.data_sources:
            lines.append(f"  - {ds.instrument} ({ds.date_range})")

        lines.extend([
            "",
            f"Orchestration: {self.scenario.orchestration}",
            f"Expected output: {self.scenario.expected_output}",
            "",
            "IMPORTANT CONSTRAINTS",
            "- Generated code will run in a sandbox",
            "- Code MAY call score_prediction(instrument, prediction_date, direction, confidence)",
            "- Code MAY read data via score_prediction() only",
            "- Code CANNOT import os, subprocess, sys, or sealed_resolver",
            "- Code CANNOT write to any files",
            "- Code CANNOT modify the resolver",
            "- Code receives a scratch_dir for temporary files",
            "- Assume pandas, numpy, json available",
            "- Code must return result as a dict with keys: 'predictions', 'reasoning'",
        ])

        return "\n".join(lines)


def example_build_spec() -> BuildSpec:
    """Example BUILD SPEC for testing."""
    return BuildSpec(
        goal="Build a simple momentum vs mean-reversion comparison on NIFTY 50",
        scenario=ScenarioSpec(
            name="Momentum vs Mean Reversion",
            description="Compare momentum (bullish on positive returns) vs mean reversion (bullish when oversold)",
            agents=[
                AgentSpec(
                    name="momentum_agent",
                    role="momentum_detector",
                    description="Detects momentum based on recent returns",
                    input_signals=["return_1d", "return_5d", "return_10d"],
                    output_format="up/down with confidence",
                    logic_description=(
                        "If average of 1d, 5d, 10d returns is positive, predict up; "
                        "otherwise down. Confidence based on strength of returns."
                    ),
                ),
                AgentSpec(
                    name="mean_reversion_agent",
                    role="mean_reversion_detector",
                    description="Detects mean reversion based on distance from moving average",
                    input_signals=["distance_from_ma20", "distance_from_ma50"],
                    output_format="up/down with confidence",
                    logic_description=(
                        "If price is below MA50, predict up (reversion). "
                        "If above, predict down. Confidence based on distance magnitude."
                    ),
                ),
            ],
            data_sources=[
                DataSourceRef(
                    instrument="NIFTY 50",
                    date_range="Full frozen NSE Phase 6 data",
                ),
            ],
            orchestration="Average the confidences, use highest-confidence prediction, then call score_prediction()",
            expected_output="JSON: {predictions: [{agent, direction, confidence}], winner: agent_name, score: float}",
        ),
    )
