#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "system_run" / "latest" / "migration_verification.json"
DB_URL = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or "postgresql://agentco:password@localhost:5432/agentco"
REQUIRED_TABLES = {
    "prediction_ledger",
    "decision_log",
    "override_queue",
    "agent_tasks",
    "agent_task_events",
    "departments",
    "eval_runs",
    "eval_scorecards",
    "eval_suites",
    "institution_work_requests",
    "institution_specialist_assignments",
    "specialist_allocation_history",
    "autonomy_goals",
    "learner_candidates",
    "reward_calculations",
    "reward_functions",
}
REQUIRED_COLUMNS = {
    "prediction_ledger": {"prediction_id", "hardness", "consequence"},
    "departments": {"id", "institution_id", "parent_id", "entity_type", "authority_scope", "metadata"},
    "eval_suites": {"id", "name", "active", "eval_type", "total_cases"},
    "eval_runs": {
        "id",
        "suite_id",
        "run_timestamp",
        "status",
        "run_status",
        "total_cases",
        "started_at",
        "completed_at",
        "target_type",
        "target_id",
        "baseline_ref",
        "candidate_ref",
        "trace_id",
    },
    "eval_scorecards": {"id", "eval_run_id", "overall_score", "promotion_eligible", "decision_reason"},
    "institution_work_requests": {"id", "institution_id", "department_id", "status"},
    "institution_specialist_assignments": {"id", "institution_id", "department_id", "specialist_role"},
    "specialist_allocation_history": {"id", "work_request_id", "department_id", "specialist_role"},
    "autonomy_goals": {"id", "institution_id", "depth", "goal_depth", "goal_path", "rollup_status"},
    "learner_candidates": {"id", "learner_run_id", "risk_level", "simulation_trained", "artifact_json"},
    "reward_calculations": {
        "id",
        "function_id",
        "reward_function_id",
        "reward_value",
        "reward_score",
        "regret_score",
        "metrics_json",
        "components_json",
        "calculation_details_json",
    },
    "reward_functions": {"id", "name", "function_type", "domain", "version", "formula_json", "owner", "risk_level", "created_by"},
}


def run_psql(sql: str) -> tuple[int, str]:
    if not shutil.which("psql"):
        return 127, "psql not found"
    proc = subprocess.run(["psql", DB_URL, "-Atc", sql], cwd=ROOT, text=True, capture_output=True, timeout=12, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def parse_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line]


def parse_column_rows(output: str) -> dict[str, set[str]]:
    columns: dict[str, set[str]] = {}
    for line in parse_lines(output):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        table, column = parts
        columns.setdefault(table, set()).add(column)
    return columns


def find_missing_columns(found: dict[str, set[str]]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for table, required_columns in REQUIRED_COLUMNS.items():
        absent = sorted(required_columns - found.get(table, set()))
        if absent:
            missing[table] = absent
    return missing


def build_report(
    *,
    migration_script: str,
    conn_code: int,
    conn_out: str,
    table_code: int,
    table_out: str,
    column_code: int,
    column_out: str,
) -> dict:
    tables = parse_lines(table_out)
    found_columns = parse_column_rows(column_out)
    missing_tables = sorted(REQUIRED_TABLES - set(tables))
    missing_columns = find_missing_columns(found_columns)
    migration_ok = "ts-node src/db/migrate.ts" in migration_script
    schema_ok = not missing_tables and not missing_columns
    report = {
        "success": conn_code == 0 and table_code == 0 and column_code == 0 and schema_ok and migration_ok,
        "postgres_connectivity": "real" if conn_code == 0 else "blocked",
        "migration_runner": migration_script,
        "migration_dependency_status": "real" if migration_ok else "broken",
        "core_schema_status": "real" if schema_ok else "missing",
        "core_tables_found": tables,
        "required_tables": sorted(REQUIRED_TABLES),
        "missing_tables": missing_tables,
        "required_columns": {table: sorted(columns) for table, columns in REQUIRED_COLUMNS.items()},
        "missing_columns": missing_columns,
        "detail": "existing schema accepted if required tables and columns are present"
        if conn_code == 0
        else conn_out[:300],
    }
    return report


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    pkg = json.loads((ROOT / "backend" / "package.json").read_text())
    migration_script = pkg.get("scripts", {}).get("db:migrate", "")
    conn_code, conn_out = run_psql("select current_database(), current_user")
    schema_sql = (
        "select table_name from information_schema.tables "
        "where table_schema='public' and table_name in "
        f"({','.join(repr(table) for table in sorted(REQUIRED_TABLES))}) "
        "order by table_name"
    )
    column_sql = (
        "select table_name || '|' || column_name from information_schema.columns "
        "where table_schema='public' and table_name in "
        f"({','.join(repr(table) for table in sorted(REQUIRED_COLUMNS))}) "
        "order by table_name, column_name"
    )
    schema_code, schema_out = run_psql(schema_sql) if conn_code == 0 else (conn_code, conn_out)
    column_code, column_out = run_psql(column_sql) if conn_code == 0 else (conn_code, conn_out)
    report = build_report(
        migration_script=migration_script,
        conn_code=conn_code,
        conn_out=conn_out,
        table_code=schema_code,
        table_out=schema_out,
        column_code=column_code,
        column_out=column_out,
    )
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": report["success"], "postgres_connectivity": report["postgres_connectivity"], "core_schema_status": report["core_schema_status"]}, sort_keys=True))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
