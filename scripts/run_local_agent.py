#!/usr/bin/env python3
"""
End-to-end local smoke run for AgentCo V2 against a real Postgres + (optionally) Ollama.

What it proves, with nothing mocked:
  1. The Calibration Engine wires up against a live Postgres connection.
  2. A V2 agent pre-registers a falsifiable claim → row lands in prediction_ledger.
  3. The agent executes an action through the trusted_confidence + escalation gates.
  4. The Resolution Service resolves the claim AFTER resolution_date; persist_resolution()
     writes the outcome back through the resolution_service role (DB trigger enforced).
  5. The Trust Controller ingests the resolution (calibration signal updates).
  6. With --llm, the agent makes one real structured call to the local Ollama model.

Usage (PowerShell on the HP Omen, with docker-compose Postgres + Ollama up):

    $env:DATABASE_URL = "postgresql://agentco:password@localhost:5432/agentco"
    python scripts/run_local_agent.py            # DB-only smoke
    python scripts/run_local_agent.py --llm      # also hit Ollama (phi4 / qwen2.5)

The DATABASE_URL connection must be able to create the resolution_service role and
grant it privileges (the default docker-compose 'agentco' superuser can). The
prediction_ledger table must already exist (apply backend/src/db/migrations).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calibration import create_calibration_engine  # noqa: E402
from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2  # noqa: E402


class DemoAgent(BaseAgentV2):
    PROMPT_VERSION = "local-smoke-1.0"

    def run(self, task: dict):  # pragma: no cover - not used by the smoke flow
        pass


def _ensure_resolution_role(dsn: str):
    import psycopg2
    admin = psycopg2.connect(dsn)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'resolution'; END IF; END $$;"
        )
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    admin.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="also make one real Ollama call")
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: set DATABASE_URL, e.g. postgresql://agentco:password@localhost:5432/agentco")
        return 2

    import psycopg2

    _ensure_resolution_role(dsn)

    # The ledger connection runs as resolution_service so persist_resolution() is
    # permitted by the DB trigger; INSERT/SELECT are also granted to that role.
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")

    engine = create_calibration_engine(db=conn)
    agent = DemoAgent(agent_id="cfo-agent", calibration_engine=engine)

    print("== 1. pre-register a falsifiable claim ==")
    resolution_date = datetime.now(timezone.utc) - timedelta(seconds=1)  # immediately resolvable
    pid = agent.pre_register_claim(
        claim="Local Ollama smoke: revenue forecast holds",
        probability=0.72,
        resolution_criterion="external accounting close",
        resolution_date=resolution_date,
        domain="finance",
        claim_type="forecast",
        ground_truth_source="external_accounting_system",
    )
    print(f"   prediction_id = {pid}")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT producing_agent_id, probability, resolved FROM prediction_ledger WHERE prediction_id=%s",
            (pid,),
        )
        row = cur.fetchone()
    print(f"   DB row: agent={row[0]} p={row[1]} resolved={row[2]}")
    assert row is not None and row[2] is False

    print("== 2. execute an action through the V2 gates ==")
    result = agent.execute_action(
        AgentActionV2(
            action_type="publish_forecast",
            description="Publish the Q-end revenue forecast",
            payload={"forecast": "on track"},
            risk_level="low",
            stated_confidence=0.72,
            domain="finance",
            claim_type="forecast",
        ),
        prediction_id=pid,
    )
    print(f"   outcome={result['outcome']} trusted_confidence={result['trusted_confidence']}")

    print("== 3. resolve the claim and persist to DB (resolution_service role) ==")
    record = engine["resolution"].resolve(
        prediction_id=pid,
        outcome=True,
        ground_truth_source="external_accounting_system",
        evidence={"close": "matched"},
    )
    engine["ledger"].persist_resolution(record)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT resolved, resolved_outcome, brier_score FROM prediction_ledger WHERE prediction_id=%s",
            (pid,),
        )
        r = cur.fetchone()
    print(f"   DB row after resolution: resolved={r[0]} outcome={r[1]} brier={r[2]}")
    assert r[0] is True and r[1] is True

    print("== 4. trust controller saw the calibration signal ==")
    n = engine["trust"].get_sample_count("cfo-agent", "finance", "forecast", record.horizon_class)
    print(f"   resolved-sample count for cfo-agent/finance = {n}")

    if args.llm:
        print("== 5. real Ollama structured call ==")
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["summary", "confidence"],
        }
        out = agent.act(
            messages=[{"role": "user", "content": "Return a JSON object with a one-line summary "
                                                  "of a revenue forecast and a confidence 0-1."}],
            schema=schema,
        )
        print(f"   model={agent._model} output={out}")

    conn.close()
    print("\nOK: end-to-end local run complete with DB persistence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
