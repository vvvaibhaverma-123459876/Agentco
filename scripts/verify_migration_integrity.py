#!/usr/bin/env python3
"""Validate active database migrations structurally and against a live database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "backend" / "src" / "db" / "migrations"
EXPECTED_TABLES = {
    "schema_migrations",
    "decision_log",
    "event_outbox",
    "event_bus_outbox",
    "runtime_evaluation_records",
    "runtime_learning_artifacts",
    "runtime_improvement_experiments",
    "civilization_resource_accounts",
    "civilization_resource_reservations",
    "autonomy_evidence",
}


@dataclass(frozen=True)
class MigrationFile:
    filename: str
    order_key: tuple[int, str, str]
    content_hash: str
    has_effect: bool


@dataclass(frozen=True)
class Finding:
    rule: str
    detail: str
    file: str | None = None


def list_migrations(directory: Path) -> list[MigrationFile]:
    files: list[MigrationFile] = []
    for path in sorted(directory.glob("*.sql")):
        match = re.match(r"^(\d+)([a-z]?)_[a-z0-9_]+\.sql$", path.name)
        if not match:
            raise ValueError(f"migration lacks deterministic ordered prefix: {path.name}")
        text = path.read_text()
        files.append(
            MigrationFile(
                filename=path.name,
                order_key=(int(match.group(1)), match.group(2), path.name),
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                has_effect=bool(
                    re.search(
                        r"\b(CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|GRANT|REVOKE|COMMENT|DO)\b",
                        text,
                        re.IGNORECASE,
                    )
                ),
            )
        )
    return files


def validate_static(directory: Path) -> list[Finding]:
    findings: list[Finding] = []
    migrations = list_migrations(directory)
    names = [item.filename for item in migrations]
    if not migrations:
        findings.append(Finding("NO_MIGRATIONS", "No active migration files were found."))
    if names != sorted(names):
        findings.append(Finding("NON_DETERMINISTIC_ORDER", "Filesystem migration order differs from lexical order."))
    if len(names) != len(set(names)):
        findings.append(Finding("DUPLICATE_FILENAME", "Duplicate migration filename detected."))
    seen_keys: dict[tuple[int, str, str], str] = {}
    for item in migrations:
        if item.order_key in seen_keys:
            findings.append(Finding("DUPLICATE_ORDER_KEY", f"Duplicate migration order key also used by {seen_keys[item.order_key]}.", item.filename))
        seen_keys[item.order_key] = item.filename
        if not item.has_effect:
            findings.append(Finding("NO_SCHEMA_EFFECT", "Migration has no schema/data effect statement.", item.filename))
    if [item.order_key for item in migrations] != sorted(item.order_key for item in migrations):
        findings.append(Finding("AMBIGUOUS_ORDER", "Migration order keys are not sorted."))
    return findings


def psql(database_url: str, sql: str) -> str:
    return subprocess.check_output(
        ["psql", database_url, "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def app_tables(database_url: str) -> list[str]:
    output = psql(
        database_url,
        """
        SELECT table_schema || '.' || table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_type = 'BASE TABLE'
        ORDER BY 1
        """,
    )
    return [line for line in output.splitlines() if line]


def schema_dump(database_url: str) -> str:
    with tempfile.NamedTemporaryFile("w+", delete=False) as handle:
        dump_path = Path(handle.name)
    try:
        subprocess.check_call(
            ["pg_dump", "--schema-only", "--no-owner", "--no-privileges", "--file", str(dump_path), database_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        return "\n".join(
            line
            for line in dump_path.read_text(errors="replace").splitlines()
            if not line.startswith("--") and "Dumped from database version" not in line
            and not line.startswith("\\restrict ")
            and not line.startswith("\\unrestrict ")
        )
    finally:
        dump_path.unlink(missing_ok=True)


def schema_fingerprint(database_url: str) -> str:
    return hashlib.sha256(schema_dump(database_url).encode()).hexdigest()


def validate_database(database_url: str, expect_empty: bool, after_migration: bool) -> tuple[list[Finding], dict[str, object]]:
    findings: list[Finding] = []
    summary: dict[str, object] = {}
    tables = app_tables(database_url)
    summary["tables"] = tables
    if expect_empty and tables:
        findings.append(Finding("DATABASE_NOT_EMPTY", "Clean-room database already contains application tables."))
    if after_migration:
        migration_files = [item.filename for item in list_migrations(MIGRATIONS_DIR)]
        rows = psql(database_url, "SELECT filename FROM schema_migrations ORDER BY filename")
        applied = [line for line in rows.splitlines() if line]
        summary["applied_migrations"] = applied
        missing = sorted(set(migration_files) - set(applied))
        unexpected = sorted(set(applied) - set(migration_files))
        if missing:
            findings.append(Finding("MISSING_MIGRATION_RECORD", f"Missing migration records: {missing[:10]}"))
        if unexpected:
            findings.append(Finding("UNEXPECTED_MIGRATION_RECORD", f"Unexpected migration records: {unexpected[:10]}"))
        table_set = {item.split(".", 1)[1] for item in tables}
        missing_tables = sorted(EXPECTED_TABLES - table_set)
        if missing_tables:
            findings.append(Finding("MISSING_EXPECTED_TABLE", f"Expected migrated tables absent: {missing_tables}"))
    return findings, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrations-dir", type=Path, default=MIGRATIONS_DIR)
    parser.add_argument("--database-url")
    parser.add_argument("--expect-empty", action="store_true")
    parser.add_argument("--after-migration", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    findings = validate_static(args.migrations_dir.resolve())
    summary: dict[str, object] = {
        "migration_count": len(list_migrations(args.migrations_dir.resolve())),
        "static_success": not findings,
    }
    if args.database_url:
        db_findings, db_summary = validate_database(args.database_url, args.expect_empty, args.after_migration)
        findings.extend(db_findings)
        summary.update(db_summary)
    result = {"success": not findings, "findings": [asdict(item) for item in findings], "summary": summary}
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": result["success"], "findings": len(findings)}, sort_keys=True))
    return 0 if result["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
