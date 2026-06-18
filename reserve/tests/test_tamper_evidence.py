"""
Phase C — Tamper-Evidence Test.

Proves that "the operator cannot rig a score undetected" is a tested property,
not a promise.

PROPERTY: if any resolved prediction underlying a committed credential is
altered, dropped, or back-dated in prediction_ledger, the recomputed chain
head diverges from the stored chain head — proving tampering to any third
party with read access to the public ledger rows.

Real Postgres, no mocks.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set — real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in ("prediction_chain_log", "calibration_credentials",
                    "credential_domains", "prediction_ledger"):
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "backend/src/db/migrations/011_prediction_ledger.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/001_reserve_extension.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/004_ed25519_signature.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/005_prediction_chain.sql").read_text())
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    yield conn
    with conn.cursor() as cur:
        for tbl in ("prediction_chain_log", "calibration_credentials",
                    "credential_domains", "prediction_ledger"):
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_resolved_predictions(db, agent_id: str, n: int = 3) -> list[str]:
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration

    cal = create_calibration_engine(db=db)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    pids = []
    for i in range(n):
        pid = cal["ledger"].pre_register(PredictionRegistration(
            claim=f"tamper-test claim {i}",
            probability=0.70,
            confidence_basis={},
            producing_agent_id=agent_id,
            producing_prompt_version="1.0.0",
            resolution_criterion="criterion",
            resolution_date=past,
            ground_truth_source="external_test",
            horizon_class="short",
            domain="tamper_test",
            claim_type="forecast",
        ))
        pids.append(pid)

    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    res_cal = create_calibration_engine(db=res_conn)
    for pid in pids:
        rec = cal["ledger"].get(pid)
        res_cal["ledger"]._in_memory[pid] = rec
        res_cal["resolution"].resolve(
            prediction_id=pid,
            outcome=True,
            ground_truth_source="external_test",
            evidence={"src": "tamper_test"},
        )
        res_cal["ledger"].persist_resolution(res_cal["ledger"].get(pid))
    res_conn.close()
    return pids


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_chain_integrity_holds_for_honest_data(db):
    """After committing resolved predictions, verify_chain() returns True."""
    from reserve.chain.commitment_chain import commit_prediction, verify_chain

    agent_id = "tamper-evidence-agent-honest"
    pids = _seed_resolved_predictions(db, agent_id, n=3)

    for pid in pids:
        commit_prediction(pid, db)

    assert verify_chain(db), "Chain must verify cleanly when data is unaltered"
    print(f"\n[tamper] {len(pids)} predictions committed; chain verified ✓")


def test_tampering_with_resolved_outcome_is_detected(db):
    """
    A direct UPDATE to resolved_outcome (bypassing normal resolution path)
    changes the underlying data the chain was computed over. The recomputed
    chain head will diverge from the stored head — proving the tampering.

    This simulates an operator trying to rig a score by flipping an outcome
    after commitment.
    """
    from reserve.chain.commitment_chain import (
        commit_prediction, get_chain_head, recompute_chain_head, verify_chain,
    )

    agent_id = "tamper-evidence-agent-rigged"
    pids = _seed_resolved_predictions(db, agent_id, n=3)

    for pid in pids:
        commit_prediction(pid, db)

    # Chain is clean before tampering.
    head_before = get_chain_head(db)
    assert verify_chain(db), "Precondition: chain must be clean before tampering"

    # Operator directly alters an outcome in prediction_ledger.
    # The prediction_ledger's BEFORE UPDATE trigger would normally block this
    # for the resolution columns — but the chain's tamper-evidence is a
    # SECOND LINE of defence: even if the ledger trigger were bypassed,
    # the chain would catch the alteration.
    # We disable the trigger here purely to simulate the bypass scenario.
    victim_pid = pids[0]
    with db.cursor() as cur:
        cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL;")
        cur.execute(
            "UPDATE prediction_ledger SET resolved_outcome = FALSE WHERE prediction_id = %s;",
            (victim_pid,),
        )
        cur.execute("ALTER TABLE prediction_ledger ENABLE TRIGGER ALL;")

    # Now recompute the chain from the tampered ledger rows.
    recomputed = recompute_chain_head(db)
    stored = get_chain_head(db)

    assert recomputed != stored or (recomputed is not None and recomputed.startswith("TAMPERED")), (
        "Recomputed chain head MUST diverge from stored head after tampering"
    )
    assert not verify_chain(db), "verify_chain() must return False after tampering"

    print(f"\n[tamper] stored   chain head: {stored[:16]}...")
    print(f"[tamper] recomputed head:     {str(recomputed)[:16]}...")
    print(f"[tamper] verify_chain() = False — tampering DETECTED ✓")

    # Restore the prediction so later tests have clean state.
    with db.cursor() as cur:
        cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL;")
        cur.execute(
            "UPDATE prediction_ledger SET resolved_outcome = TRUE WHERE prediction_id = %s;",
            (victim_pid,),
        )
        cur.execute("ALTER TABLE prediction_ledger ENABLE TRIGGER ALL;")


def test_chain_log_is_itself_append_only(db):
    """The prediction_chain_log table's own BEFORE UPDATE trigger rejects alterations."""
    from reserve.chain.commitment_chain import commit_prediction

    agent_id = "tamper-evidence-agent-chain-immutable"
    pids = _seed_resolved_predictions(db, agent_id, n=1)
    commit_prediction(pids[0], db)

    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE prediction_chain_log SET row_hash = 'aaaa' "
                "WHERE prediction_id = %s;",
                (pids[0],),
            )
    assert "CHAIN IMMUTABILITY" in str(exc.value)
    print("\n[tamper] prediction_chain_log UPDATE correctly blocked ✓")


def test_recomputed_score_diverges_after_tampering(db):
    """
    After altering a prediction's probability in the ledger, the recomputed
    credential score differs from the stored credential score, exposing the
    rigged score to any independent auditor.

    This is the direct proof of "operator cannot rig a score undetected":
    the stored credential says X; recomputation says Y; they diverge; rigged.
    """
    from calibration import create_calibration_engine
    from reserve import create_reserve_engine
    from reserve.tools.recompute_credential import _fetch_rows, recompute as raw_recompute

    agent_id = "tamper-evidence-agent-score-rig"
    pids = _seed_resolved_predictions(db, agent_id, n=3)

    # Issue and persist the honest credential.
    cal = create_calibration_engine(db=db)
    engine = create_reserve_engine(ledger=cal["ledger"], db=db)
    honest_cred = engine.refresh_credential(agent_id)

    # Operator alters the probability of one prediction (tries to rig the score).
    with db.cursor() as cur:
        cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL;")
        cur.execute(
            "UPDATE prediction_ledger SET probability = 0.999 WHERE prediction_id = %s;",
            (pids[0],),
        )
        cur.execute("ALTER TABLE prediction_ledger ENABLE TRIGGER ALL;")

    # Independent recomputation from current ledger rows detects the tampered input.
    rows_after = _fetch_rows(DSN, agent_id)
    recomputed_after = raw_recompute(rows_after)

    stored_log = honest_cred.overall_log_score
    recomputed_log = recomputed_after["overall_log_score"]

    assert abs(stored_log - recomputed_log) > 1e-4, (
        f"Recomputed score must diverge from stored score after probability alteration: "
        f"stored={stored_log:.6f} recomputed={recomputed_log:.6f}"
    )

    print(f"\n[tamper] honest   stored credential overall_log_score: {stored_log:.6f}")
    print(f"[tamper] recomputed from tampered rows overall_log_score: {recomputed_log:.6f}")
    print(f"[tamper] delta = {abs(stored_log - recomputed_log):.6f} > 1e-4 — rigging EXPOSED ✓")

    # Restore.
    with db.cursor() as cur:
        cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL;")
        cur.execute(
            "UPDATE prediction_ledger SET probability = 0.70 WHERE prediction_id = %s;",
            (pids[0],),
        )
        cur.execute("ALTER TABLE prediction_ledger ENABLE TRIGGER ALL;")
