#!/usr/bin/env python3
"""Issue a canonical Python Reserve Proof-of-Calibration credential.

Usage:
    python3 scripts/issue_canonical_credential.py <agent_id> [dsn]
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calibration import create_calibration_engine
from reserve.credentials.proof_of_calibration import (
    build_last_contacts,
    issue_credential,
    persist_credential,
)
from reserve.scoring.scoring_function import score_agent


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def issue_for_agent(agent_id: str, dsn: str) -> dict:
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError("psycopg2 not installed - cannot issue credential from Postgres")

    conn = psycopg2.connect(dsn)
    try:
        cal = create_calibration_engine(db=conn)
        records = cal["ledger"].list_by_agent(agent_id)
        score = score_agent(records, agent_id)
        if score.total_sample_count == 0:
            raise LookupError(f"no resolved non-post-hoc predictions for agent_id={agent_id!r}")
        credential = issue_credential(score, build_last_contacts(records))
        persist_credential(credential, conn)
        return {
            "credential": asdict(credential),
            "verification": {
                "correctness": "recompute from resolved, non-post-hoc prediction_ledger rows",
                "authorship": "verify Ed25519 signature with reserve/keys/agentco_reserve_public.pem when ed25519_signature is present",
                "recompute_command": f"python3 reserve/tools/recompute_credential.py {agent_id}",
                "canonical_source": "reserve/credentials/proof_of_calibration.py",
                "issued_by": "scripts/issue_canonical_credential.py",
            },
        }
    finally:
        conn.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    agent_id = sys.argv[1]
    dsn = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
        "DATABASE_URL",
        os.environ.get("AGENTCO_TEST_DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco"),
    )
    try:
        result = issue_for_agent(agent_id, dsn)
    except LookupError as exc:
        print(json.dumps({"error": str(exc), "agent_id": agent_id}), file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "agent_id": agent_id}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
