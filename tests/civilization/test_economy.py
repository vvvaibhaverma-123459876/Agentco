from __future__ import annotations

import os
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in ["economic_policies", "budget_allocations", "resource_transactions", "resource_accounts"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/010_economy.sql").read_text())
    yield conn
    conn.close()


def test_output_creation_consumes_and_locks_budget(db) -> None:
    from civilization.services.economy_service import allocate_budget, balance, create_output, resolve_output

    allocate_budget("institution", "inst-1", "compute_budget", 10, "governance", db)
    create_output("institution", "inst-1", "out-1", 3, db)
    assert balance("institution", "inst-1", "compute_budget", db)["locked"] == 3
    resolve_output("institution", "inst-1", "out-1", 3, True, db)
    assert balance("institution", "inst-1", "compute_budget", db)["balance"] == 7


def test_insufficient_budget_blocks_action(db) -> None:
    from civilization.services.economy_service import EconomyError, allocate_budget, create_output

    allocate_budget("institution", "inst-1", "compute_budget", 1, "governance", db)
    with pytest.raises(EconomyError, match="insufficient"):
        create_output("institution", "inst-1", "out-1", 3, db)


def test_valid_review_and_challenge_rewards_false_challenge_penalty(db) -> None:
    from civilization.services.economy_service import balance, penalize_false_challenge, reward_challenge, reward_review

    reward_review("institution", "inst-1", 2, db)
    reward_challenge("institution", "inst-1", 3, db)
    penalize_false_challenge("institution", "inst-1", 1, db)
    assert balance("institution", "inst-1", "review_credits", db)["balance"] == 4


def test_repeated_failures_reduce_budget_and_governance_allocates(db) -> None:
    from civilization.services.economy_service import allocate_budget, balance, repeated_failure_reduces_budget

    allocate_budget("institution", "inst-1", "risk_budget", 5, "governance", db)
    repeated_failure_reduces_budget("institution", "inst-1", 2, db)
    assert balance("institution", "inst-1", "risk_budget", db)["balance"] == 3


def test_unauthorized_budget_allocation_rejected(db) -> None:
    from civilization.services.economy_service import EconomyError, allocate_budget

    with pytest.raises(EconomyError, match="unauthorized"):
        allocate_budget("institution", "inst-1", "compute_budget", 5, "inst-1", db)
