#!/usr/bin/env python3
"""Validate AgentCo migration identity and ordering contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "backend" / "src" / "db" / "migrations"
LEDGER_JSON = ROOT / "docs" / "audit" / "current" / "MIGRATION_IDENTITY_LEDGER.json"
LEDGER_MD = ROOT / "docs" / "audit" / "current" / "MIGRATION_IDENTITY_LEDGER.md"

ALLOWED_REUSED_SEQUENCES = {
    51: {
        "filenames": ["051_fix_fk_constraints.sql", "051_team_activations.sql"],
        "contract": "legacy_parallel_sequence_before Batch 02 controls; lexicographic order is stable and both are already part of the audited baseline",
    },
    52: {
        "filenames": ["052_specialist_http_endpoint.sql", "052b_institutions.sql"],
        "contract": "legacy_parallel_sequence_before Batch 02 controls; suffix ordering is stable",
    },
    58: {
        "filenames": ["058_adaptive_strategy.sql", "058_bounded_learning.sql"],
        "contract": "legacy_parallel_sequence_before Batch 02 controls; independent tables and stable lexicographic order",
    },
    59: {
        "filenames": ["059_calibration_framework.sql", "059_governance_reputation_integration.sql"],
        "contract": "legacy_parallel_sequence_before Batch 02 controls; independent tables and stable lexicographic order",
    },
    129: {
        "filenames": ["129_civilization_kernel.sql", "129_longitudinal_mission_evidence.sql"],
        "contract": "Batch 07 reconciliation contract: Version B preserved raw duplicate sequence; Version C treats full filename as stable ID, applies lexicographic order, and requires content-hash tracking",
    },
    140: {
        "filenames": ["140_civilization_os.sql", "140_governed_capability_runtime.sql"],
        "contract": "Batch 08A reconciliation contract: Batch 07 civilization OS and Batch 08 governed capability runtime are independent domains; full filename plus content hash is the stable identity and lexicographic ordering applies both guarded migrations",
    },
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_origin(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    try:
        return subprocess.check_output(["git", "log", "--follow", "--format=%H", "--", rel], cwd=ROOT, text=True).splitlines()[-1]
    except (subprocess.CalledProcessError, IndexError):
        return "unknown"


def schema_object_records(sql: str) -> list[dict[str, Any]]:
    patterns = [
        ("table", r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)"),
        ("index", r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)"),
        ("view", r"CREATE\s+VIEW\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)"),
        ("type", r"CREATE\s+TYPE\s+([a-zA-Z0-9_.]+)"),
    ]
    found: list[dict[str, Any]] = []
    for kind, pattern in patterns:
        for match in re.finditer(pattern, sql, re.IGNORECASE):
            if kind == "type":
                name = match.group(1)
                guarded = "IF NOT EXISTS" in sql[max(0, match.start() - 40):match.end()].upper()
            else:
                guarded = bool(match.group(1))
                name = match.group(2)
            found.append({"kind": kind, "name": name.strip('"'), "guarded": guarded})
    unique = {(item["kind"], item["name"], item["guarded"]): item for item in found}
    return sorted(unique.values(), key=lambda item: (item["kind"], item["name"], str(item["guarded"])))


def parse_sequence(filename: str) -> int | None:
    match = re.match(r"^(\d+)_", filename)
    return int(match.group(1)) if match else None


def build_ledger() -> dict[str, Any]:
    migrations = []
    by_sequence: dict[int, list[str]] = defaultdict(list)
    created_objects: dict[str, list[str]] = defaultdict(list)
    for path in sorted(MIGRATIONS.glob("*.sql")):
        sql = path.read_text()
        sequence = parse_sequence(path.name)
        if sequence is not None:
            by_sequence[sequence].append(path.name)
        object_records = schema_object_records(sql)
        for obj in object_records:
            created_objects[obj["name"]].append({"filename": path.name, "sequence": sequence, "guarded": obj["guarded"], "kind": obj["kind"]})
        migrations.append(
            {
                "stable_migration_id": path.name,
                "filename": path.name,
                "sequence": sequence,
                "content_hash": sha256_text(sql),
                "origin_commit": git_origin(path),
                "schema_objects_created": [item["name"] for item in object_records],
                "upgrade_prerequisites": [],
                "rollback_classification": "forward_fix_required",
                "already_applied_compatibility_rule": "filename and content_hash must match; legacy null hashes are backfilled once by the migration runner",
            }
        )
    reused = {
        str(sequence): {
            "filenames": files,
            "contract": ALLOWED_REUSED_SEQUENCES.get(sequence, {}).get("contract"),
        }
        for sequence, files in sorted(by_sequence.items())
        if len(files) > 1
    }
    conflicts = {}
    for obj, records in sorted(created_objects.items()):
        if len(records) > 1:
            conflicts[obj] = records
    return {
        "ledger_version": "migration-identity-ledger-v1",
        "migration_directory": str(MIGRATIONS.relative_to(ROOT)),
        "migration_count": len(migrations),
        "migrations": migrations,
        "reused_sequence_contracts": reused,
        "conflicting_object_creations": conflicts,
    }


def validate(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    by_sequence: dict[int, list[str]] = defaultdict(list)
    for migration in ledger["migrations"]:
        stable_id = migration["stable_migration_id"]
        if stable_id in seen_ids:
            errors.append(f"DUPLICATE_STABLE_ID:{stable_id}")
        seen_ids.add(stable_id)
        sequence = migration.get("sequence")
        if sequence is not None:
            by_sequence[int(sequence)].append(migration["filename"])
    for sequence, files in by_sequence.items():
        if len(files) <= 1:
            continue
        contract = ALLOWED_REUSED_SEQUENCES.get(sequence)
        if not contract:
            errors.append(f"REUSED_SEQUENCE_WITHOUT_CONTRACT:{sequence}:{','.join(files)}")
            continue
        if sorted(contract["filenames"]) != sorted(files):
            errors.append(f"REUSED_SEQUENCE_CONTRACT_MISMATCH:{sequence}:{','.join(files)}")
    for obj, records in ledger.get("conflicting_object_creations", {}).items():
        current_lineage = any(int(record.get("sequence") or 0) >= 129 for record in records)
        if current_lineage and not all(record.get("guarded") for record in records):
            errors.append(f"CONFLICTING_OBJECT_CREATION:{obj}:{','.join(record['filename'] for record in records)}")
    return errors


def write_outputs(ledger: dict[str, Any]) -> None:
    LEDGER_JSON.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_JSON.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Migration Identity Ledger",
        "",
        f"- Migration count: `{ledger['migration_count']}`",
        f"- Directory: `{ledger['migration_directory']}`",
        "",
        "## Reused Sequence Contracts",
        "",
    ]
    for sequence, contract in ledger["reused_sequence_contracts"].items():
        lines.append(f"- `{sequence}`: {', '.join(contract['filenames'])} — {contract['contract']}")
    lines.extend(["", "## Migrations", "", "| Sequence | Stable ID | Content hash | Origin commit |", "|---:|---|---|---|"])
    for migration in ledger["migrations"]:
        lines.append(
            f"| {migration['sequence']} | `{migration['stable_migration_id']}` | `{migration['content_hash'][:16]}` | `{migration['origin_commit'][:12]}` |"
        )
    LEDGER_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ledger = build_ledger()
    errors = validate(ledger)
    if args.check:
        if not LEDGER_JSON.exists():
            print("MIGRATION_IDENTITY_LEDGER_MISSING")
            return 2
        existing = json.loads(LEDGER_JSON.read_text())
        if existing != ledger:
            print("MIGRATION_IDENTITY_LEDGER_STALE")
            return 2
        print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
        return 0 if not errors else 2
    write_outputs(ledger)
    print(json.dumps({"success": not errors, "errors": errors, "migration_count": ledger["migration_count"]}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
