#!/usr/bin/env python3
"""Build ledger status and frontier tooling for AgentCo."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import yaml


LEDGER_PATH = Path("BUILD_LEDGER.yaml")
RUNTIME_DIRS = [
    Path("backend/src"),
    Path("runtime"),
    Path("agents"),
    Path("calibration"),
    Path("learning"),
    Path("synthesis"),
    Path("selfcoding"),
    Path("reserve"),
]
EXCLUDED_PARTS = {"tests", "__tests__", "fixtures", "__pycache__", "unsupported_migrations"}
BANNED_MARKER = re.compile(
    r"\bTODO\b|\bFIXME\b|\bXXX\b|\bHACK\b|NotImplementedError|raise NotImplemented|"
    r"\bplaceholder\b|\bstub\b|\bmock(?!ito)\b|\bfake_|\bdummy\b|to ?be ?done|\blater\b",
    re.IGNORECASE,
)
SIMULATED_REASONING = re.compile(r"method\s*[:=]\s*['\"]simulated['\"]|Simulated answer")
MAX_GATE_FINDINGS = 50


class ScanHit(NamedTuple):
    path: str
    line: int
    marker: str
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line, "marker": self.marker, "excerpt": self.excerpt}


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("BUILD_LEDGER.yaml must parse to a mapping")
    return data


def iter_items(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for layer_name, layer in ledger.get("layers", {}).items():
        for order, item in enumerate(layer.get("items", [])):
            copied = dict(item)
            copied["_layer"] = layer_name
            copied["_order"] = order
            items.append(copied)
    return items


def recompute_rollups(ledger: dict[str, Any]) -> dict[str, Any]:
    items = iter_items(ledger)
    counts = Counter(item.get("status", "unknown") for item in items)
    total = len(items)
    verified = counts.get("verified", 0)
    return {
        "total_items": total,
        "verified": verified,
        "in_progress": counts.get("in_progress", 0),
        "not_started": counts.get("not_started", 0),
        "blocked": counts.get("blocked", 0),
        "percent_verified": round((verified / total) * 100, 2) if total else 0.0,
    }


def scan_runtime(pattern: re.Pattern[str], limit: int | None = None) -> list[ScanHit]:
    hits: list[ScanHit] = []
    for root in RUNTIME_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                match = pattern.search(line)
                if match:
                    hits.append(ScanHit(str(path), line_no, match.group(0), line.strip()[:160]))
                    if limit is not None and len(hits) >= limit:
                        return hits
    return hits


def recompute_gates(ledger: dict[str, Any]) -> dict[str, str]:
    gates = dict(ledger.get("gates", {}))
    marker_hits = scan_runtime(BANNED_MARKER)
    simulated_hits = scan_runtime(SIMULATED_REASONING)
    gates["no_stub"] = "green" if not marker_hits else "red"
    gates["no_simulation"] = "green" if not simulated_hits else "red"
    gates.setdefault("reachability", "unknown")
    gates.setdefault("firewall", "unknown")
    gates.setdefault("sandbox_breach", "unknown")
    gates.setdefault("credential_key_independence", "unknown")
    gates.setdefault("e2e_civilization_slice", "unknown")
    gates["_no_stub_hit_count"] = str(len(marker_hits))
    gates["_no_simulation_hit_count"] = str(len(simulated_hits))
    return gates


def recompute_gate_findings() -> dict[str, list[dict[str, Any]]]:
    return {
        "no_stub": [hit.to_dict() for hit in scan_runtime(BANNED_MARKER, limit=MAX_GATE_FINDINGS)],
        "no_simulation": [hit.to_dict() for hit in scan_runtime(SIMULATED_REASONING, limit=MAX_GATE_FINDINGS)],
    }


def ready_frontier(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    items = iter_items(ledger)
    by_id = {item["id"]: item for item in items}
    ready: list[dict[str, Any]] = []
    for item in items:
        if item.get("status") == "verified" or item.get("status") == "blocked":
            continue
        deps = item.get("depends_on", [])
        if all(by_id.get(dep, {}).get("status") == "verified" for dep in deps):
            ready.append(item)
    return sorted(ready, key=lambda item: (item["_layer"], item["_order"], item["id"]))


def apply_computed_fields(ledger: dict[str, Any]) -> dict[str, Any]:
    ledger = dict(ledger)
    ledger["rollups"] = recompute_rollups(ledger)
    ledger["gates"] = recompute_gates(ledger)
    ledger["gate_findings"] = recompute_gate_findings()
    meta = dict(ledger.get("meta", {}))
    meta["last_updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    meta["termination_predicate_met"] = (
        ledger["rollups"]["total_items"] > 0
        and ledger["rollups"]["verified"] == ledger["rollups"]["total_items"]
        and all(value == "green" for key, value in ledger["gates"].items() if not key.startswith("_"))
    )
    ledger["meta"] = meta
    return ledger


def write_ledger(ledger: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    path.write_text(yaml.safe_dump(ledger, sort_keys=False, width=120))


def cmd_status(args: argparse.Namespace) -> int:
    ledger = apply_computed_fields(load_ledger())
    if args.write:
        write_ledger(ledger)
    if args.json:
        print(json.dumps({"meta": ledger["meta"], "rollups": ledger["rollups"], "gates": ledger["gates"], "gate_findings": ledger["gate_findings"]}, indent=2))
    else:
        rollups = ledger["rollups"]
        print(f"items: {rollups['verified']}/{rollups['total_items']} verified ({rollups['percent_verified']}%)")
        print(f"in_progress: {rollups['in_progress']}  not_started: {rollups['not_started']}  blocked: {rollups['blocked']}")
        for gate, status in ledger["gates"].items():
            print(f"{gate}: {status}")
    return 0


def cmd_remaining(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    frontier = ready_frontier(ledger)
    if args.json:
        print(json.dumps(frontier, indent=2))
    else:
        for item in frontier:
            print(f"{item['id']} [{item.get('status')}] layer={item['_layer']}")
    return 0


def cmd_sync_db(args: argparse.Namespace) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required for build-ledger DB sync", file=sys.stderr)
        return 2
    import psycopg2

    ledger = apply_computed_fields(load_ledger())
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS build_ledger (
                  item_id TEXT PRIMARY KEY,
                  layer TEXT NOT NULL,
                  status TEXT NOT NULL,
                  depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
                  artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
                  tests JSONB NOT NULL DEFAULT '[]'::jsonb,
                  notes TEXT,
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            for item in iter_items(ledger):
                cur.execute(
                    """
                    INSERT INTO build_ledger (item_id, layer, status, depends_on, artifacts, tests, notes, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, now())
                    ON CONFLICT (item_id) DO UPDATE SET
                      layer = EXCLUDED.layer,
                      status = EXCLUDED.status,
                      depends_on = EXCLUDED.depends_on,
                      artifacts = EXCLUDED.artifacts,
                      tests = EXCLUDED.tests,
                      notes = EXCLUDED.notes,
                      updated_at = now()
                    """,
                    (
                        item["id"],
                        item["_layer"],
                        item.get("status", "unknown"),
                        json.dumps(item.get("depends_on", [])),
                        json.dumps(item.get("artifacts", [])),
                        json.dumps(item.get("tests", [])),
                        item.get("notes", ""),
                    ),
                )
    print("build ledger synced to database")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--write", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    remaining = sub.add_parser("remaining")
    remaining.add_argument("--json", action="store_true")
    remaining.set_defaults(func=cmd_remaining)
    sync_db = sub.add_parser("sync-db")
    sync_db.set_defaults(func=cmd_sync_db)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
