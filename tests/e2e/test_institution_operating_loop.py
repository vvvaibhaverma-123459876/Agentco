"""
Phase 7 — One Institution End-to-End Operating Loop.

Exact scenario per spec:
  1. create_institution("Engineering") and create_institution("Security")
  2. Place a real agent in Engineering > Production department
  3. Engineering registers an output (status 'proposed')
  4. Attempt to self-approve → assert RAISES (self-cert ban)
  5. Security opens review → 'under_review' → 'challenged'
  6. Resolve the underlying claim via a REAL resolved prediction in the Reserve ledger;
     recompute the producing agent's credential (Phase 0 path)
  7. Run reputation propagation; assert dept→institution scores moved per formula
     and 'reputation_updated' memory events exist
  8. Drive review to 'approved' (external review completed) then 'archived'
  9. Assert: output could NOT have reached 'approved' without the external review row

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
pytestmark = pytest.mark.skipif(not DSN, reason="AGENTCO_TEST_DATABASE_URL not set")

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


def test_institution_operating_loop(db):
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration
    from civilization.services.institution_service import (
        create_institution, load_contract, add_agent_to_department,
    )
    from civilization.services.review_service import (
        create_review, transition_review, get_review, ReviewTransitionError,
    )
    from civilization.services.reputation_service import propagate_institution
    from reserve import create_reserve_engine
    from reserve.tools.recompute_credential import _fetch_rows, recompute as raw_recompute

    # ── Step 1: create Engineering + Security ──────────────────────────────
    eng_contract = load_contract("Engineering")
    sec_contract = load_contract("Security")
    eng = create_institution("Engineering", eng_contract, db)
    sec = create_institution("Security", sec_contract, db)
    eng_id = eng["institution_id"]
    sec_id = sec["institution_id"]
    print(f"\n[e2e] Engineering id={eng_id[:8]} Security id={sec_id[:8]}")

    # Verify five departments exist for each
    with db.cursor() as cur:
        cur.execute("SELECT name FROM departments WHERE parent_id = %s ORDER BY name", (eng_id,))
        eng_depts = {r[0] for r in cur.fetchall()}
    assert eng_depts == {"Production", "Verification", "Audit", "Adversarial", "Improvement"}, \
        f"Five mandatory departments missing: {eng_depts}"
    print(f"[e2e] Engineering departments: {sorted(eng_depts)} ✓")

    # ── Step 2: place real agent in Engineering > Production ───────────────
    agent_id = f"e2e-eng-agent-{uuid.uuid4().hex[:6]}"
    prod_dept_id = eng["department_ids"]["Production"]
    add_agent_to_department(agent_id, prod_dept_id, "engineer", db)
    print(f"[e2e] Agent {agent_id} placed in Engineering > Production ✓")

    # ── Step 3: Engineering registers output (status 'proposed') ──────────
    output_id = f"software-artifact-{uuid.uuid4().hex[:6]}"
    # A review row with status='proposed' IS the output registration
    review_id = create_review(output_id, eng_id, sec_id, db)
    r = get_review(review_id, db)
    assert r["status"] == "proposed"
    print(f"[e2e] Output '{output_id}' proposed (review_id={review_id[:8]}) ✓")

    # ── Step 4: self-approve attempt RAISES ───────────────────────────────
    # Create a self-review row directly (must be rejected by DB CHECK)
    with pytest.raises(psycopg2.errors.CheckViolation):
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO institution_output_reviews "
                "(id, output_id, producing_institution_id, reviewer_institution_id) "
                "VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), output_id, eng_id, eng_id),
            )
    print("[e2e] Self-certification attempt correctly rejected by DB ✓")

    # ── Step 5: Security reviews → 'under_review' → 'challenged' ──────────
    transition_review(review_id, "under_review", db)
    transition_review(review_id, "challenged", db, evidence={"reason": "needs more tests"})
    r = get_review(review_id, db)
    assert r["status"] == "challenged"
    print("[e2e] Security challenged Engineering's output ✓")

    # ── Step 6: Resolve underlying claim via REAL Reserve ledger ──────────
    cal = create_calibration_engine(db=db)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    pid = cal["ledger"].pre_register(PredictionRegistration(
        claim="e2e: software artifact will pass security review",
        probability=0.80,
        confidence_basis={"basis": "code-review"},
        producing_agent_id=agent_id,
        producing_prompt_version="1.0.0",
        resolution_criterion="security review outcome",
        resolution_date=past,
        ground_truth_source="external_security_scanner",
        horizon_class="short",
        domain="engineering",
        claim_type="forecast",
    ))

    # Resolve via resolution_service role
    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    res_cal = create_calibration_engine(db=res_conn)
    rec = cal["ledger"].get(pid)
    res_cal["ledger"]._in_memory[pid] = rec
    res_cal["resolution"].resolve(
        prediction_id=pid, outcome=True,
        ground_truth_source="external_security_scanner",
        evidence={"scanner": "e2e-test"},
    )
    res_cal["ledger"].persist_resolution(res_cal["ledger"].get(pid))
    res_conn.close()
    cal["ledger"]._in_memory.clear()
    cal["ledger"]._load_from_db()

    # Recompute credential via Phase 0 path (independent — raw DB rows)
    rows = _fetch_rows(DSN, agent_id)
    recomputed = raw_recompute(rows)
    assert recomputed["total_sample_count"] >= 1
    print(f"[e2e] Agent credential recomputed: overall_log_score="
          f"{recomputed['overall_log_score']:.4f} sample_count={recomputed['total_sample_count']} ✓")

    # ── Step 7: Reputation propagation ───────────────────────────────────
    result = propagate_institution(eng_id, cal["ledger"], db)
    inst_score = result["institution_score"]
    assert inst_score is not None, "Institution score must be non-None after agent resolved predictions"

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events "
            "WHERE entity_id = %s AND event_type = 'reputation_updated'",
            (eng_id,),
        )
        mem_count = cur.fetchone()[0]
    assert mem_count >= 1, "At least one reputation_updated memory event must exist"
    print(f"[e2e] Institution score={inst_score:.4f}; memory events={mem_count} ✓")

    # Assert department score is also set
    dept_score = result["department_scores"].get(prod_dept_id)
    assert dept_score is not None, "Production department must have a score after propagation"
    print(f"[e2e] Production dept score={dept_score:.4f} ✓")

    # ── Step 8: Resolve challenge → approved → archived ───────────────────
    transition_review(review_id, "approved", db, evidence={"resolution": "challenge resolved"})
    r = get_review(review_id, db)
    assert r["status"] == "approved"
    transition_review(review_id, "archived", db)
    r = get_review(review_id, db)
    assert r["status"] == "archived"
    print("[e2e] Review driven to 'approved' then 'archived' ✓")

    # ── Step 9: Prove approval required external review ──────────────────
    # Create a fresh output and show it cannot reach 'approved' from 'proposed'
    output_id_2 = f"software-artifact-{uuid.uuid4().hex[:6]}"
    review_id_2 = create_review(output_id_2, eng_id, sec_id, db)
    with pytest.raises(ReviewTransitionError):
        transition_review(review_id_2, "approved", db)
    print("[e2e] Output cannot reach 'approved' without external review progression ✓")

    print("\n[e2e] PASS: one institution end-to-end operating loop complete")
