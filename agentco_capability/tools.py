from __future__ import annotations

import ast
import csv
import io
import json
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


class ToolDeniedError(RuntimeError):
    pass


SAFE_TOOLS = {
    "calculator",
    "json_transformer",
    "fixture_reader",
    "fixture_sql",
    "fixture_test_runner",
}


def _require_allowed(tool: str, allowlist: list[str]) -> None:
    if tool not in allowlist:
        raise ToolDeniedError(f"tool not allowlisted: {tool}")


def calculator(expression: str) -> dict[str, Any]:
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
    )
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError("calculator expression contains unsupported syntax")
    return {"result": eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, {})}


def json_transformer(payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload.get("mode", "sort_keys")
    data = payload.get("data")
    if mode == "sort_keys" and isinstance(data, dict):
        return {"data": {key: data[key] for key in sorted(data)}}
    if mode == "select" and isinstance(data, dict):
        keys = payload.get("keys") or []
        return {"data": {key: data[key] for key in keys if key in data}}
    raise ValueError("unsupported json_transformer request")


def fixture_reader(root: Path, relative_path: str) -> dict[str, Any]:
    target = (root / relative_path).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ToolDeniedError("fixture_reader path escapes workspace")
    return {"path": relative_path, "content": target.read_text()[:20000]}


def fixture_sql(rows: list[dict[str, Any]], query: str) -> dict[str, Any]:
    if not query.strip().lower().startswith("select "):
        raise ToolDeniedError("fixture_sql only permits SELECT queries")
    if any(token in query.lower() for token in ["attach", "pragma", "insert", "update", "delete", "drop", "alter"]):
        raise ToolDeniedError("fixture_sql query contains prohibited token")
    with sqlite3.connect(":memory:") as conn:
        if rows:
            columns = sorted({key for row in rows for key in row})
            conn.execute("CREATE TABLE data (" + ", ".join(f"{col} TEXT" for col in columns) + ")")
            for row in rows:
                conn.execute(
                    "INSERT INTO data (" + ", ".join(columns) + ") VALUES (" + ", ".join("?" for _ in columns) + ")",
                    [str(row.get(col, "")) for col in columns],
                )
        cur = conn.execute(query)
        return {"rows": [dict(zip([col[0] for col in cur.description], row, strict=True)) for row in cur.fetchall()]}


def fixture_test_runner(files: dict[str, str], test_command: list[str]) -> dict[str, Any]:
    if not test_command or test_command[0] not in {"python3", "python3.13"}:
        raise ToolDeniedError("fixture_test_runner only permits python test commands")
    with tempfile.TemporaryDirectory(prefix="agentco-capability-fixture-") as tmp:
        root = Path(tmp)
        for rel, content in files.items():
            target = (root / rel).resolve()
            if not str(target).startswith(str(root.resolve())):
                raise ToolDeniedError("fixture file escapes workspace")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        started = time.time()
        proc = subprocess.run(test_command, cwd=root, text=True, capture_output=True, timeout=10)
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "wall_clock_ms": round((time.time() - started) * 1000, 3),
        }


def summarize_csv(csv_text: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    numeric: dict[str, list[float]] = {}
    for row in rows:
        for key, value in row.items():
            try:
                numeric.setdefault(key, []).append(float(value))
            except (TypeError, ValueError):
                continue
    return {
        "row_count": len(rows),
        "columns": reader.fieldnames or [],
        "numeric_summary": {
            key: {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}
            for key, values in numeric.items()
            if values
        },
    }


def execute_tool(tool: str, payload: dict[str, Any], allowlist: list[str], fixture_root: Path | None = None) -> dict[str, Any]:
    _require_allowed(tool, allowlist)
    if tool == "calculator":
        return calculator(str(payload.get("expression", "")))
    if tool == "json_transformer":
        return json_transformer(payload)
    if tool == "fixture_reader":
        if fixture_root is None:
            raise ToolDeniedError("fixture_reader requires fixture_root")
        return fixture_reader(fixture_root, str(payload.get("path", "")))
    if tool == "fixture_sql":
        return fixture_sql(list(payload.get("rows") or []), str(payload.get("query", "")))
    if tool == "fixture_test_runner":
        return fixture_test_runner(dict(payload.get("files") or {}), list(payload.get("test_command") or []))
    raise ToolDeniedError(f"unknown tool: {tool}")
