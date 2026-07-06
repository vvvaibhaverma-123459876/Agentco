#!/usr/bin/env python3
"""
Adversarial wall tests for the generated-code sandbox.

These tests intentionally exercise the escape routes that are common in Python
``exec`` sandboxes. The expected result is structural rejection by the AST
interpreter, not accidental NameError/PermissionError from a partial runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from selfcoding.sandbox.run_generated import run_generated_code, setup_sandbox


class TestSandboxWall:
    @classmethod
    def setup_class(cls) -> None:
        cls.context = setup_sandbox()

    def run_code(self, code: str) -> dict[str, Any]:
        return run_generated_code(code, self.context)

    def assert_blocked(self, code: str) -> None:
        result = self.run_code(code)
        assert result["success"] is False, result
        assert result["error_type"] in {"SandboxError", "NameError", "ValueError"}, result

    def test_valid_usage_score_prediction(self) -> None:
        result = self.run_code(
            """
result = score_prediction(
    instrument="NIFTY 50",
    prediction_date="2024-10-21",
    predicted_direction="down",
    confidence=0.75
)
"""
        )

        assert result["success"] is True, result
        assert result["output"]["instrument"] == "NIFTY 50"
        assert "score" in result["output"]

    def test_valid_loop_and_list_append(self) -> None:
        result = self.run_code(
            """
results = []
for direction in ["up", "down"]:
    for conf in [0.5, 0.75, 0.9]:
        r = score_prediction("NIFTY 50", "2024-10-21", direction, conf)
        results.append(r)

result = {"predictions_scored": len(results), "sample": results[0]}
"""
        )

        assert result["success"] is True, result
        assert result["output"]["predictions_scored"] == 6
        assert "hit" in result["output"]["sample"]

    def test_bound_method_self_escape_is_blocked(self) -> None:
        self.assert_blocked(
            """
result = score_prediction.__self__
"""
        )

    def test_function_globals_escape_is_blocked(self) -> None:
        self.assert_blocked(
            """
result = score_prediction.__globals__["os"].system("id")
"""
        )

    def test_class_hierarchy_escape_is_blocked(self) -> None:
        self.assert_blocked(
            """
result = ().__class__.__base__.__subclasses__()
"""
        )

    def test_import_is_blocked(self) -> None:
        self.assert_blocked(
            """
import os
result = {"breach": True}
"""
        )

    def test_file_write_is_blocked_before_runtime(self) -> None:
        self.assert_blocked(
            """
path = "/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/nifty_50_REAL.csv"
f = open(path, "w")
result = {"breach": True}
"""
        )

    def test_resolver_import_is_blocked(self) -> None:
        self.assert_blocked(
            """
from selfcoding.resolver.sealed_resolver import SealedResolver
result = {"breach": True}
"""
        )

    def test_function_definition_is_blocked(self) -> None:
        self.assert_blocked(
            """
def fake_score_prediction(*args, **kwargs):
    return {"hit": True, "score": 999}
score_prediction = fake_score_prediction
result = score_prediction("NIFTY 50", "2024-10-21", "up", 0.75)
"""
        )

    def test_invalid_answer_smuggling_fails_closed(self) -> None:
        result = self.run_code(
            """
result = score_prediction("NIFTY 50", "2024-10-21", "precomputed_answer", 0.75)
"""
        )

        assert result["success"] is False, result
        assert result["error_type"] == "ValueError"


def main() -> int:
    tester = TestSandboxWall()
    tester.setup_class()
    tests = [
        method
        for name, method in sorted(TestSandboxWall.__dict__.items())
        if name.startswith("test_") and callable(method)
    ]
    passed = 0
    for test in tests:
        try:
            test(tester)
            print(f"PASS {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
