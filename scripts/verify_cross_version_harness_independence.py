#!/usr/bin/env python3
"""Fail closed when cross-version scoring/output logic depends on subject identity."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_cross_version_campaign.py"
FORBIDDEN_STRINGS = {
    "CIVILIZATION_BUILD_LEDGER.yaml",
    "has_civilization_layer",
    "has_migration_identity_validator",
    "has_hashing_migration_runner",
    "fb27dc0529d3c5d11480503bfbcf6f2d156f5b04",
    "651794a41513db1e40930f08c253ef261af7c1e7",
    "81cd17431f826d9d3cda06b9127758751e44b798",
}
FORBIDDEN_FUNCTION_NAMES = {"deterministic_output", "subject_features"}
SCORING_FUNCTIONS = {"score_response", "aggregate", "compare"}


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous = self.current_function
        self.current_function = node.name
        if node.name in FORBIDDEN_FUNCTION_NAMES:
            self.errors.append(f"FORBIDDEN_FUNCTION:{node.name}")
        self.generic_visit(node)
        self.current_function = previous

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            if node.value in {"version-a", "version-b", "version-c"} and self.current_function in SCORING_FUNCTIONS:
                self.errors.append(f"SUBJECT_LABEL_IN_SCORING:{self.current_function}:{node.value}")
            for forbidden in FORBIDDEN_STRINGS:
                if forbidden in node.value:
                    self.errors.append(f"FORBIDDEN_SUBJECT_FEATURE_REFERENCE:{forbidden}")
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        text = ast.unparse(node.test)
        if any(label in text for label in ("version-a", "version-b", "version-c")):
            self.errors.append(f"SUBJECT_LABEL_BRANCH:{text}")
        self.generic_visit(node)


def validate(path: Path = RUNNER) -> list[str]:
    tree = ast.parse(path.read_text())
    visitor = Visitor()
    visitor.visit(tree)
    return sorted(set(visitor.errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = validate()
    print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
