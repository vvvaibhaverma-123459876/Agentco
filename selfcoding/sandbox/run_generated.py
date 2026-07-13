#!/usr/bin/env python3
"""
Sandbox executor for generated scoring code.

This deliberately does not use ``exec``. Python's reflection model makes an
in-process ``exec`` sandbox porous: a bound method leaks ``__self__`` and a
function leaks ``__globals__``. Generated code is parsed as Python syntax, then
interpreted through a small AST whitelist that supports the selfcoding contract:
basic data manipulation, loops, conditionals, and calls to ``score_prediction``.
"""
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FROZEN_DATA_PATH = Path(
    os.environ.get(
        "SELFCODING_FROZEN_DATA_PATH",
        ROOT / "evals" / "experiments" / "nse_phase6_data_frozen",
    )
)
SCRATCH_DIR = Path(
    os.environ.get(
        "SELFCODING_SCRATCH_DIR",
        Path(tempfile.gettempdir()) / "agentco-selfcoding-scratch",
    )
)


class SandboxError(Exception):
    """Raised when generated code leaves the supported safe subset."""


class _SafeEvaluator:
    def __init__(self, score_prediction: Any, scratch_dir: Path):
        self.env: dict[str, Any] = {
            "score_prediction": score_prediction,
            "scratch_dir": scratch_dir,
            "True": True,
            "False": False,
            "None": None,
        }
        self.safe_functions = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
        }

    def run(self, code: str) -> Any:
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as exc:
            raise SandboxError(f"syntax not supported: {exc.msg}") from exc
        for stmt in tree.body:
            self._stmt(stmt)
        return self.env.get("result", {})

    def _stmt(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Assign):
            value = self._expr(node.value)
            for target in node.targets:
                self._assign(target, value)
            return
        if isinstance(node, ast.AnnAssign):
            self._assign(node.target, self._expr(node.value) if node.value else None)
            return
        if isinstance(node, ast.Expr):
            self._expr(node.value)
            return
        if isinstance(node, ast.For):
            if node.orelse:
                raise SandboxError("for/else is not supported")
            for item in self._expr(node.iter):
                self._assign(node.target, item)
                for stmt in node.body:
                    self._stmt(stmt)
            return
        if isinstance(node, ast.If):
            branch = node.body if self._expr(node.test) else node.orelse
            for stmt in branch:
                self._stmt(stmt)
            return
        raise SandboxError(f"statement not allowed: {type(node).__name__}")

    def _assign(self, target: ast.expr, value: Any) -> None:
        if isinstance(target, ast.Name):
            self._validate_name(target.id)
            self.env[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            values = list(value)
            if len(values) != len(target.elts):
                raise SandboxError("unpack length mismatch")
            for sub_target, sub_value in zip(target.elts, values):
                self._assign(sub_target, sub_value)
            return
        if isinstance(target, ast.Subscript):
            container = self._expr(target.value)
            key = self._expr(target.slice)
            container[key] = value
            return
        raise SandboxError(f"assignment target not allowed: {type(target).__name__}")

    def _expr(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self.env:
                return self.env[node.id]
            if node.id in self.safe_functions:
                return self.safe_functions[node.id]
            raise SandboxError(f"name not available: {node.id}")
        if isinstance(node, ast.List):
            return [self._expr(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._expr(item) for item in node.elts)
        if isinstance(node, ast.Set):
            return {self._expr(item) for item in node.elts}
        if isinstance(node, ast.Dict):
            return {self._expr(k): self._expr(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            return self._expr(node.value)[self._expr(node.slice)]
        if isinstance(node, ast.Slice):
            return slice(
                self._expr(node.lower) if node.lower else None,
                self._expr(node.upper) if node.upper else None,
                self._expr(node.step) if node.step else None,
            )
        if isinstance(node, ast.UnaryOp):
            operand = self._expr(node.operand)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
        if isinstance(node, ast.BinOp):
            return self._binop(node)
        if isinstance(node, ast.BoolOp):
            values = [self._expr(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if isinstance(node, ast.Compare):
            return self._compare(node)
        if isinstance(node, ast.IfExp):
            return self._expr(node.body if self._expr(node.test) else node.orelse)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.ListComp):
            return self._listcomp(node)
        raise SandboxError(f"expression not allowed: {type(node).__name__}")

    def _call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute):
            if node.func.attr != "append" or node.keywords:
                raise SandboxError("method call not allowed")
            target = self._expr(node.func.value)
            if not isinstance(target, list):
                raise SandboxError("append target must be a list")
            if len(node.args) != 1:
                raise SandboxError("append expects one argument")
            target.append(self._expr(node.args[0]))
            return None

        if not isinstance(node.func, ast.Name):
            raise SandboxError("call target not allowed")
        name = node.func.id
        if name == "score_prediction":
            args = [self._expr(arg) for arg in node.args]
            kwargs = {kw.arg: self._expr(kw.value) for kw in node.keywords if kw.arg}
            return self.env["score_prediction"](*args, **kwargs)
        if name in self.safe_functions:
            if node.keywords:
                raise SandboxError(f"keyword arguments not allowed for {name}")
            return self.safe_functions[name](*[self._expr(arg) for arg in node.args])
        raise SandboxError(f"function not available: {name}")

    def _listcomp(self, node: ast.ListComp) -> list[Any]:
        if len(node.generators) != 1:
            raise SandboxError("only one-generator list comprehensions are supported")
        generator = node.generators[0]
        if generator.is_async:
            raise SandboxError("async comprehensions are not supported")
        output = []
        for item in self._expr(generator.iter):
            self._assign(generator.target, item)
            if all(self._expr(condition) for condition in generator.ifs):
                output.append(self._expr(node.elt))
        return output

    def _binop(self, node: ast.BinOp) -> Any:
        left = self._expr(node.left)
        right = self._expr(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise SandboxError(f"operator not allowed: {type(node.op).__name__}")

    def _compare(self, node: ast.Compare) -> bool:
        left = self._expr(node.left)
        for operator, comparator in zip(node.ops, node.comparators):
            right = self._expr(comparator)
            if isinstance(operator, ast.Eq):
                ok = left == right
            elif isinstance(operator, ast.NotEq):
                ok = left != right
            elif isinstance(operator, ast.Lt):
                ok = left < right
            elif isinstance(operator, ast.LtE):
                ok = left <= right
            elif isinstance(operator, ast.Gt):
                ok = left > right
            elif isinstance(operator, ast.GtE):
                ok = left >= right
            elif isinstance(operator, ast.In):
                ok = left in right
            elif isinstance(operator, ast.NotIn):
                ok = left not in right
            else:
                raise SandboxError(f"comparison not allowed: {type(operator).__name__}")
            if not ok:
                return False
            left = right
        return True

    @staticmethod
    def _validate_name(name: str) -> None:
        if name.startswith("__") or name in {"resolver", "open", "exec", "eval", "__import__"}:
            raise SandboxError(f"name not allowed: {name}")


def setup_sandbox() -> dict[str, Any]:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    if not FROZEN_DATA_PATH.exists():
        raise SandboxError(f"Frozen data path does not exist: {FROZEN_DATA_PATH}")

    from selfcoding.resolver import get_resolver

    return {
        "resolver": get_resolver(FROZEN_DATA_PATH),
        "scratch_dir": SCRATCH_DIR,
        "frozen_data_path": FROZEN_DATA_PATH,
    }


def run_generated_code(code: str, context: dict[str, Any]) -> dict[str, Any]:
    resolver = context["resolver"]
    try:
        result = _SafeEvaluator(resolver.score_prediction, context["scratch_dir"]).run(code)
        return {"success": True, "output": result, "error": None, "error_type": None}
    except SandboxError as exc:
        return {"success": False, "output": None, "error": str(exc), "error_type": "SandboxError"}
    except Exception as exc:
        return {
            "success": False,
            "output": None,
            "error": f"{type(exc).__name__}: {exc}",
            "error_type": type(exc).__name__,
        }


def main() -> int:
    context = setup_sandbox()
    good = run_generated_code(
        """
results = []
for direction in ["up", "down"]:
    r = score_prediction("NIFTY 50", "2024-10-21", direction, 0.75)
    results.append(r)
result = {"count": len(results), "first": results[0]}
""",
        context,
    )
    blocked = run_generated_code(
        """
result = score_prediction.__globals__
""",
        context,
    )
    print(f"valid_success={good['success']}")
    print(f"reflection_blocked={not blocked['success']}")
    return 0 if good["success"] and not blocked["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
