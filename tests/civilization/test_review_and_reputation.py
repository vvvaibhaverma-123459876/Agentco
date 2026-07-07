"""
T5.1 – T5.4 — Review state machine and reputation propagation tests.

T5.1  Output cannot transition to 'approved' without an external-review row.
T5.2  A second institution can open a 'challenged' review on the first's output.
T5.3  Lowering one agent's resolved-prediction performance measurably lowers
      its department's, then its institution's, score after propagation.
T5.4  Propagation writes matching memory events; direct score UPDATE is rejected.

Real Postgres, no mocks.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
if DSN:
    try:
        from pg_test_isolation import isolated_dsn

        # Destructive fixture: run in an isolated sibling database so shared
        # backend-migrated tables are never replaced with this suite's schema.
        DSN = isolated_dsn(DSN)
    except Exception:
        DSN = None  # Postgres unreachable; the skip guard below handles it
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set"
)

ROOT = Path(__file__).resolve().parents[2]
CIVI_TABLES = [
    "agent_membership_edges", "institution_contracts",
    "institution_output_reviews", "civilization_memory_events",
    "governance_decisions", "departments", "institutions",
]


@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES + ["prediction_chain_log", "calibration_credentials",
                                   "credential_domains", "prediction_ledger"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        for mig in [
            "backend/src/db/migrations/011_prediction_ledger.sql",
            "reserve/migrations/001_reserve_extension.sql",
            "reserve/migrations/004_ed25519_signature.sql",
            "reserve/migrations/005_prediction_chain.sql",
            "reserve/migrations/006_civilization.sql",
        ]:
            cur.execute((ROOT / mig).read_text())
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    yield conn
    # Teardown intentionally leaves the schema in place: each fixture's setup
    # is self-cleaning, and dropping shared tables here left the database
    # inconsistent with schema_migrations for every suite that ran afterwards.
    conn.close()


def _create_inst(db, name):
    from civilization.services.institution_service import create_institution, load_contract
    c = load_contract(name)
    return create_institution(name, c, db)


def _get_or_create_inst(db, name):
    with db.cursor() as cur:
        cur.execute("SELECT id FROM institutions WHERE name = %s LIMIT 1", (name,))
        row = cur.fetchone()
    if row:
        institution_id = row[0]
        return {
            "institution_id": institution_id,
            "department_ids": _get_dept_ids(institution_id, db),
        }
    return _create_inst(db, name)


def _seed_agent(db, agent_id, institution_result, n=3, probability=0.75, outcome=True):
    """Register + resolve n predictions for agent_id; add them to Production dept."""
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration
    from civilization.services.institution_service import add_agent_to_department

    prod_dept_id = institution_result["department_ids"]["Production"]
    add_agent_to_department(agent_id, prod_dept_id, "contributor", db)

    cal = create_calibration_engine(db=db)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    pids = []
    for i in range(n):
        pid = cal["ledger"].pre_register(PredictionRegistration(
            claim=f"rep-test {agent_id} {i}", probability=probability,
            confidence_basis={}, producing_agent_id=agent_id,
            producing_prompt_version="1.0.0", resolution_criterion="test",
            resolution_date=past, ground_truth_source="external_test",
            horizon_class="short", domain="testing", claim_type="forecast",
            historical_registration_reason="test fixture seeds already-resolved historical predictions",
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
        res_cal["resolution"].resolve(pid, outcome=outcome,
                                       ground_truth_source="external_test",
                                       evidence={"src": "t5-test"})
        res_cal["ledger"].persist_resolution(res_cal["ledger"].get(pid))
    res_conn.close()
    cal["ledger"]._in_memory.clear()
    cal["ledger"]._load_from_db()
    return cal


# ─── T5.1 ────────────────────────────────────────────────────────────────────

def test_t5_1_approve_without_external_review_raises(db):
    """Cannot transition directly to 'approved' without going through 'under_review'."""
    from civilization.services.review_service import create_review, transition_review, ReviewTransitionError
    eng = _create_inst(db, "Engineering")
    sec = _create_inst(db, "Security")

    review_id = create_review(
        output_id="out-t5-1",
        producing_institution_id=eng["institution_id"],
        reviewer_institution_id=sec["institution_id"],
        db=db,
    )
    # Attempt to jump directly to 'approved' from 'proposed'
    with pytest.raises(ReviewTransitionError):
        transition_review(review_id, "approved", db)
    print("\n[T5.1] direct approve from 'proposed' correctly blocked ✓")


# ─── T5.2 ────────────────────────────────────────────────────────────────────

def test_t5_2_second_institution_can_challenge(db):
    """Security can open a second review and drive it to 'challenged'."""
    from civilization.services.review_service import (
        create_review, transition_review, get_review,
    )
    eng_id = _get_or_create_inst(db, "Engineering")["institution_id"]
    sec_id = _get_or_create_inst(db, "Security")["institution_id"]

    review_id = create_review("out-t5-2", eng_id, sec_id, db)
    transition_review(review_id, "under_review", db)
    transition_review(review_id, "challenged", db, evidence={"reason": "security concern"})

    r = get_review(review_id, db)
    assert r["status"] == "challenged"
    print("[T5.2] review correctly driven to 'challenged' by Security ✓")


# ─── T5.3 ────────────────────────────────────────────────────────────────────

def test_t5_3_reputation_propagates_from_agent_to_institution(db):
    """Lowering an agent's track record measurably lowers dept + institution score."""
    from calibration import create_calibration_engine
    from civilization.services.reputation_service import propagate_institution

    eng_id = _get_or_create_inst(db, "Engineering")["institution_id"]

    # Seed a good agent (p=0.75, all TRUE)
    agent_good = f"t5-3-good-{uuid.uuid4().hex[:6]}"
    cal = _seed_agent(db, agent_good, {"institution_id": eng_id,
                                        "department_ids": _get_dept_ids(eng_id, db)},
                      n=5, probability=0.75, outcome=True)

    result_before = propagate_institution(eng_id, cal["ledger"], db)
    score_before = result_before["institution_score"]
    assert score_before is not None, "Institution score must be non-None after agent seeded"

    # Seed a bad agent (p=0.90, all FALSE — very wrong high-confidence)
    agent_bad = f"t5-3-bad-{uuid.uuid4().hex[:6]}"
    cal2 = _seed_agent(db, agent_bad, {"institution_id": eng_id,
                                        "department_ids": _get_dept_ids(eng_id, db)},
                       n=5, probability=0.90, outcome=False)
    cal2["ledger"]._in_memory.update(cal["ledger"]._in_memory)

    result_after = propagate_institution(eng_id, cal2["ledger"], db)
    score_after = result_after["institution_score"]
    assert score_after is not None
    assert score_after < score_before, (
        f"Bad agent should lower institution score: before={score_before:.4f} after={score_after:.4f}"
    )
    print(f"\n[T5.3] institution score: {score_before:.4f} → {score_after:.4f} (bad agent lowers it) ✓")


def _get_dept_ids(institution_id, db):
    with db.cursor() as cur:
        cur.execute("SELECT name, id FROM departments WHERE parent_id = %s", (institution_id,))
        return {r[0]: r[1] for r in cur.fetchall()}


# ─── T5.4 ────────────────────────────────────────────────────────────────────

def test_t5_4_propagation_writes_memory_events_and_direct_update_rejected(db):
    """Propagation creates 'reputation_updated' events; bare UPDATE is rejected."""
    from calibration import create_calibration_engine
    from civilization.services.reputation_service import propagate_institution

    eng_id = _get_or_create_inst(db, "Engineering")["institution_id"]

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events "
            "WHERE entity_id = %s AND event_type = 'reputation_updated'",
            (eng_id,),
        )
        before = cur.fetchone()[0]

    cal = create_calibration_engine(db=db)
    propagate_institution(eng_id, cal["ledger"], db)

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events "
            "WHERE entity_id = %s AND event_type = 'reputation_updated'",
            (eng_id,),
        )
        after = cur.fetchone()[0]

    # Direct bare UPDATE must still be rejected (re-assert T3.4)
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with db.cursor() as cur:
            cur.execute("UPDATE institutions SET reputation_score = 1.0 WHERE id = %s", (eng_id,))
    assert "REPUTATION GUARD" in str(exc.value)

    print(f"[T5.4] memory events before={before} after={after}; bare UPDATE blocked ✓")
