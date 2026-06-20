#!/usr/bin/env python3
"""
QWEN CODER: Generates Python code from BUILD SPEC.

Uses Qwen2.5-coder (local, via Ollama) to generate code that:
- Takes a BUILD SPEC and produces safe, executable Python code
- Can only generate agents, scenarios, and orchestration
- Cannot generate code that accesses resolver internals or modifies data
- Validates output to ensure no forbidden imports/calls

Cost: Free (runs locally on Ollama)
"""
from __future__ import annotations

import json
import re
from typing import Any

import requests

from selfcoding.coder.build_spec import BuildSpec


class CoderError(Exception):
    """Raised when code generation fails."""
    pass


class QwenCoder:
    """Code generator using Qwen2.5-coder."""

    OLLAMA_API = "http://localhost:11434/api/generate"
    MODEL = "qwen3:8b"
    FORBIDDEN_IN_OUTPUT = {
        "import os",
        "import subprocess",
        "import sys",
        "from os",
        "from subprocess",
        "from sys",
        "sealed_resolver",
        "SealedResolver",
        "__import__",
        "exec(",
        "eval(",
        "open(",
        "write",
        "chmod",
    }

    def __init__(self, verbose: bool = False):
        """Initialize the coder."""
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[QwenCoder] {msg}")

    def generate_code(self, build_spec: BuildSpec) -> str:
        """
        Generate Python code from a BUILD SPEC.

        Args:
            build_spec: Validated BuildSpec instance

        Returns:
            Generated Python code as a string

        Raises:
            CoderError: If generation fails or output contains forbidden code
        """
        # Validate spec first
        valid, err = build_spec.validate()
        if not valid:
            raise CoderError(f"Invalid BUILD SPEC: {err}")

        self._log(f"Generating code for: {build_spec.goal}")

        # Build the prompt
        prompt = self._build_prompt(build_spec)
        self._log(f"Prompt length: {len(prompt)} chars")

        # Call Qwen
        self._log("Calling Qwen via Ollama...")
        response = self._call_qwen(prompt)

        # Validate output
        self._log("Validating generated code...")
        self._validate_output(response)

        self._log("Code generation successful")
        return response

    def _build_prompt(self, build_spec: BuildSpec) -> str:
        """Build a prompt for Qwen from the BUILD SPEC."""
        spec_prompt = build_spec.to_prompt()

        return f"""{spec_prompt}

GENERATE PYTHON CODE

Generate well-structured Python code that implements the scenario above. The code will run
in a sandbox with the following capabilities:

AVAILABLE:
- Function: score_prediction(instrument, prediction_date, predicted_direction, confidence)
  Returns: dict with keys hit, score, actual_open, actual_close, actual_direction
- Modules: pandas, numpy, json, math, statistics, datetime, collections
- Variable: scratch_dir (Path for temporary files)

FORBIDDEN:
- Imports: os, subprocess, sys, importlib, sealed_resolver
- Functions: open(), exec(), eval(), __import__()
- Access to resolver internals
- Writing to frozen data

CODE STRUCTURE:
1. Define agent functions (one per agent in the spec)
   - Each takes input signals as dict, returns {{"direction": "up"|"down", "confidence": 0.0-1.0}}
2. Define orchestration function
   - Takes list of agent predictions, returns {{winner_agent, final_prediction}}
3. Main execution block
   - Load data by calling score_prediction()
   - Call agents
   - Call orchestration
   - Return result dict with keys: predictions, winner, score, reasoning

OUTPUT FORMAT:
Return only valid Python code, no markdown, no explanations.
Code must be syntactically correct and runnable.
Code must NOT import or reference forbidden modules/functions.

BEGIN CODE:
"""

    def _call_qwen(self, prompt: str) -> str:
        """Call Qwen via Ollama to generate code."""
        try:
            self._log(f"POST {self.OLLAMA_API}")
            response = requests.post(
                self.OLLAMA_API,
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "top_p": 0.9,
                },
                timeout=300,
            )

            if response.status_code != 200:
                raise CoderError(f"Ollama API error: {response.status_code} {response.text[:200]}")

            result = response.json()
            if "error" in result:
                raise CoderError(f"Ollama error: {result['error']}")

            code = result.get("response", "").strip()
            if not code:
                raise CoderError("Empty response from Qwen")

            return code

        except requests.RequestException as e:
            raise CoderError(f"Failed to call Ollama: {e}") from e
        except json.JSONDecodeError as e:
            raise CoderError(f"Failed to parse Ollama response: {e}") from e

    def _validate_output(self, code: str) -> None:
        """Validate that generated code doesn't contain forbidden patterns."""
        code_upper = code.upper()

        for forbidden in self.FORBIDDEN_IN_OUTPUT:
            if forbidden in code or forbidden.upper() in code_upper:
                raise CoderError(
                    f"Generated code contains forbidden pattern: {forbidden}"
                )

        # Check for attempt to break out via comments or strings
        if "exec(" in code or "eval(" in code or "__import__" in code:
            raise CoderError("Generated code attempted to use dangerous functions")

        # Verify it's valid Python by doing a syntax check
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            raise CoderError(f"Generated code has syntax error: {e}") from e

        self._log("Output validation passed")


def generate_from_spec(build_spec: BuildSpec, verbose: bool = False) -> str:
    """
    Convenience function to generate code from a BUILD SPEC.

    Args:
        build_spec: BuildSpec instance
        verbose: If True, print debug info

    Returns:
        Generated Python code

    Raises:
        CoderError: If generation fails
    """
    coder = QwenCoder(verbose=verbose)
    return coder.generate_code(build_spec)


def main() -> int:
    """Quick test of the coder."""
    from selfcoding.coder.build_spec import example_build_spec

    print("Testing Qwen Coder")
    print("=" * 80)

    spec = example_build_spec()
    print(f"BUILD SPEC: {spec.goal}")
    print()

    try:
        code = generate_from_spec(spec, verbose=True)
        print("=" * 80)
        print("GENERATED CODE")
        print("=" * 80)
        print(code)
        return 0
    except CoderError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
