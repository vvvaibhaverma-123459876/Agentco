from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set - real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]


def _sql(path: str) -> str:
    return (ROOT / path).read_text()


def _apply_migrations(cur) -> None:
    for tbl in (
        "resolution_evidence_snapshots",
        "calibration_credentials",
        "credential_domains",
        "prediction_ledger",
    ):
        cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    cur.execute(_sql("backend/src/db/migrations/011_prediction_ledger.sql"))
    cur.execute(_sql("reserve/migrations/001_reserve_extension.sql"))
    cur.execute(_sql("reserve/migrations/004_ed25519_signature.sql"))
    cur.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
        "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
    )
    cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
    cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    cur.execute(_sql("backend/src/db/migrations/017_resolution_evidence_snapshots.sql"))


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        _apply_migrations(cur)
    yield conn
    with conn.cursor() as cur:
        for tbl in (
            "resolution_evidence_snapshots",
            "calibration_credentials",
            "credential_domains",
            "prediction_ledger",
        ):
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    conn.close()


def _seed_resolved_prediction(db, agent_id: str) -> None:
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration

    cal = create_calibration_engine(db=db)
    pid = cal["ledger"].pre_register(
        PredictionRegistration(
            claim="Canonical credential issuer fixture resolves true.",
            probability=0.7,
            confidence_basis={"fixture": "canonical_issuer"},
            producing_agent_id=agent_id,
            producing_prompt_version="test",
            resolution_criterion="external fixture resolves true",
            resolution_date=datetime.now(timezone.utc) - timedelta(days=1),
            ground_truth_source="https://truth.example/canonical-issuer",
            horizon_class="short",
            domain="credential_test",
            claim_type="forecast",
            claim_source_url="https://claims.example/canonical-issuer",
        )
    )

    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    res_cal = create_calibration_engine(db=res_conn)
    resolved = res_cal["resolution"].resolve(
        prediction_id=pid,
        outcome=True,
        ground_truth_source="https://truth.example/canonical-issuer",
        evidence={"source_url": "https://truth.example/canonical-issuer"},
        resolver_id="credential-test-resolution-service",
        resolver_type="service",
        claim_source_url="https://claims.example/canonical-issuer",
        resolution_url="https://truth.example/canonical-issuer",
    )
    res_cal["ledger"].persist_resolution(resolved)
    res_conn.close()


def test_canonical_issuer_creates_persisted_credential(db):
    from scripts.issue_canonical_credential import issue_for_agent

    agent_id = "canonical-issuer-agent"
    _seed_resolved_prediction(db, agent_id)

    issued = issue_for_agent(agent_id, DSN)

    credential = issued["credential"]
    assert credential["agent_id"] == agent_id
    assert credential["sample_count"] == 1
    assert credential["algorithm"] == "log_score+brier/hardness_weighted/v1"
    assert issued["verification"]["canonical_source"] == "reserve/credentials/proof_of_calibration.py"

    with db.cursor() as cur:
        cur.execute(
            "SELECT agent_id, sample_count, algorithm FROM calibration_credentials WHERE credential_id = %s",
            (credential["credential_id"],),
        )
        row = cur.fetchone()
    assert row == (agent_id, 1, "log_score+brier/hardness_weighted/v1")


def test_canonical_issuer_matches_recompute_tool(db):
    from reserve.tools.recompute_credential import _fetch_rows, recompute
    from scripts.issue_canonical_credential import issue_for_agent

    agent_id = "canonical-recompute-agent"
    _seed_resolved_prediction(db, agent_id)

    issued = issue_for_agent(agent_id, DSN)
    recomputed = recompute(_fetch_rows(DSN, agent_id))

    assert issued["credential"]["sample_count"] == recomputed["total_sample_count"]
    assert issued["credential"]["overall_log_score"] == pytest.approx(recomputed["overall_log_score"])
    assert issued["credential"]["overall_brier_score"] == pytest.approx(recomputed["overall_brier_score"])


def test_canonical_issuer_fails_without_resolved_predictions(db):
    from scripts.issue_canonical_credential import issue_for_agent

    with pytest.raises(LookupError, match="no resolved non-post-hoc predictions"):
        issue_for_agent("no-resolved-agent", DSN)
