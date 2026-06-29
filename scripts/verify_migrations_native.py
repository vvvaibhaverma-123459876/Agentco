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


def run_psql(sql: str) -> tuple[int, str]:
    if not shutil.which("psql"):
        return 127, "psql not found"
    proc = subprocess.run(["psql", DB_URL, "-Atc", sql], cwd=ROOT, text=True, capture_output=True, timeout=12, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    pkg = json.loads((ROOT / "backend" / "package.json").read_text())
    migration_script = pkg.get("scripts", {}).get("db:migrate", "")
    conn_code, conn_out = run_psql("select current_database(), current_user")
    schema_sql = (
        "select table_name from information_schema.tables "
        "where table_schema='public' and table_name in "
        "('prediction_ledger','decision_log','override_queue','audit_logs','memory_records') "
        "order by table_name"
    )
    schema_code, schema_out = run_psql(schema_sql) if conn_code == 0 else (conn_code, conn_out)
    tables = [line for line in schema_out.splitlines() if line]
    required = {"prediction_ledger", "decision_log", "override_queue"}
    report = {
        "success": conn_code == 0 and schema_code == 0 and required.issubset(set(tables)) and "ts-node src/db/migrate.ts" in migration_script,
        "postgres_connectivity": "real" if conn_code == 0 else "blocked",
        "migration_runner": migration_script,
        "migration_dependency_status": "real" if "ts-node src/db/migrate.ts" in migration_script else "broken",
        "core_schema_status": "real" if required.issubset(set(tables)) else "missing",
        "core_tables_found": tables,
        "required_tables": sorted(required),
        "detail": "existing schema accepted if required tables are present" if conn_code == 0 else conn_out[:300],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": report["success"], "postgres_connectivity": report["postgres_connectivity"], "core_schema_status": report["core_schema_status"]}, sort_keys=True))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
