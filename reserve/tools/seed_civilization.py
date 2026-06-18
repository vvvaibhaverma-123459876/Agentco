"""
Seed additional institutions into a running Agentco database.

Usage:
    AGENTCO_TEST_DATABASE_URL=<dsn> python3 reserve/tools/seed_civilization.py

Idempotent: skips institutions whose name already exists (active).
Only seeds at the Institution + Department level — no Society/Civilization entities.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import psycopg2

from civilization.services.institution_service import create_institution, load_contract

# Additional institutions beyond Engineering and Security.
# Add names here; each must have a matching YAML in civilization/contracts/.
SEED_INSTITUTIONS = [
    "Engineering",
    "Security",
]

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not DSN:
    print("ERROR: set AGENTCO_TEST_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)

conn = psycopg2.connect(DSN)
conn.autocommit = True

for name in SEED_INSTITUTIONS:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM institutions WHERE name = %s AND status = 'active'", (name,)
        )
        if cur.fetchone():
            print(f"[seed] {name}: already exists, skipping")
            continue
    contract = load_contract(name)
    result = create_institution(name, contract, conn)
    print(f"[seed] {name}: created institution_id={result['institution_id'][:8]} "
          f"depts={list(result['department_ids'].keys())}")

conn.close()
print("[seed] done")
